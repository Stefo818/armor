# -*- coding: utf-8 -*-
"""Radar degli eventi che possono scuotere il mercato nelle prossime ore.

Tre fonti, tre modi di usarle:
- Calendario (Fed, inflazione, lavoro, conti trimestrali): l'ora esatta dell'uscita e l'ampiezza tipica della scossa, MISURATA sui futures dell'S&P 500 (2024-2026).
- Attese degli analisti (Yahoo): stime di utile e ricavi, revisioni, storico delle sorprese, obiettivi di prezzo. Servono a capire quanto è alta l'asticella.
- Notizie (data/news): temi che possono muovere il mercato senza preavviso. Non entrano nei numeri: se il mercato reagisce, i prezzi lo mostrano subito.

Cosa NON si può fare, provato sui dati: prevedere la direzione. Su 288 trimestrali (12 titoli, dal 2019) i conti battono le stime l'82% delle volte, ma il titolo sale
solo il 48%; né la sorpresa del trimestre precedente né la rincorsa del titolo nel mese prima predicono la reazione.
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from .config import DATA

NY = ZoneInfo("America/New_York")
ROMA = ZoneInfo("Europe/Rome")
FILE_AN = DATA / "radar_analisti.json"
BETA_ES = 0.83
FATTORE_1H = 0.68          # nella prima ora dopo l'uscita si vede circa il 68% della scossa delle tre ore (misurato)
ETA_CACHE_ORE = 6

# Eccesso di movimento dei futures nelle 3 ore dopo l'uscita, rispetto allo stesso orario nei giorni senza evento (deviazione standard, %).
# Misurato su ES 1 ora, luglio 2024 - novembre 2026. Campioni piccoli (19, 15, 27): ordine di grandezza, non precisione.
MACRO = {
    "FOMC": {"nome": "Decisione della Fed sui tassi", "corto": "Fed", "ora": (14, 0), "es": 0.79, "n": 19,
             "cosa": "La banca centrale americana decide i tassi. Muove azioni e obbligazioni: conta più il tono della conferenza stampa (mezz'ora dopo) che la decisione, quasi sempre già attesa."},
    "CPI": {"nome": "Inflazione USA (CPI)", "corto": "Inflazione", "ora": (8, 30), "es": 0.60, "n": 15,
            "cosa": "Se i prezzi salgono più del previsto, il mercato teme tassi alti più a lungo e le azioni scendono; se salgono meno, spesso reagiscono bene."},
    "NFP": {"nome": "Rapporto sul lavoro USA", "corto": "Lavoro USA", "ora": (8, 30), "es": 0.41, "n": 27,
            "cosa": "Posti di lavoro creati e disoccupazione. Dati troppo forti o troppo deboli muovono i tassi e quindi le azioni."},
}
ALTRI = {"es": 0.20, "cosa": "Dato americano di rilievo medio. L'ampiezza è una stima prudente, non misurata."}
TIPI_CAL = {"FOMC": "FOMC", "CPI": "CPI", "Lavoro USA": "NFP"}

# parole chiave per classificare le notizie in temi che possono scuotere il mercato (sul titolo in inglese)
TEMI_SHOCK = {
    "Dazi e commercio": ("tariff", "trade war", "trade deal", "export control", "embargo"),
    "Guerra e geopolitica": ("war ", "missile", "invasion", "sanction", "ceasefire", "airstrike", "taiwan", "iran", "ukraine", "middle east"),
    "Banche e credito": ("bank run", "bankruptcy", "default", "credit crunch", "downgrade", "liquidity", "bailout", "private credit"),
    "Fed e tassi": ("fed ", "powell", "rate cut", "rate hike", "treasury yield", "inflation", "fomc"),
    "Petrolio ed energia": ("oil price", "opec", "crude", "natural gas"),
    "Intelligenza artificiale e chip": ("nvidia", "chip", "semiconductor", "artificial intelligence", " ai ", "data center"),
    "Politica USA": ("shutdown", "debt ceiling", "congress", "election", "white house", "trump"),
}


def _n(x, d=1, segno=False):
    return (f"{x:+.{d}f}" if segno else f"{x:.{d}f}").replace(".", ",")


def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- calendario economico
def rilascio_macro(data: str, chiave: str) -> datetime:
    h, m = MACRO[chiave]["ora"]
    return datetime.strptime(data, "%Y-%m-%d").replace(hour=h, minute=m, tzinfo=NY).astimezone(timezone.utc)


def _evento_macro(chiave: str, quando: datetime, t0: datetime, attese: list[str] | None = None, nome: str | None = None) -> dict:
    d = MACRO.get(chiave)
    es = d["es"] if d else ALTRI["es"]
    return {"tipo": "macro", "ticker": chiave, "nome": nome or (d["nome"] if d else chiave), "corto": d["corto"] if d else (nome or chiave)[:14],
            "quando": quando.strftime("%Y-%m-%dT%H:%MZ"), "gia_uscita": bool(quando <= t0), "sd": round(BETA_ES * es / 100.0, 5),
            "es_eccesso": es, "n_misura": d["n"] if d else 0, "cosa": d["cosa"] if d else ALTRI["cosa"], "attese": attese or [], "misurato": bool(d)}


def macro_da_calendario(t0: datetime, calendario: list[dict], entro_ore: float = 40.0) -> list[dict]:
    out = []
    for e in calendario or []:
        k = TIPI_CAL.get(e.get("tipo"))
        if not k:
            continue
        r = rilascio_macro(e["date"], k)
        if timedelta(hours=-6) <= r - t0 <= timedelta(hours=entro_ore):
            out.append(_evento_macro(k, r, t0))
    return out


def parse_ff(righe: list[dict], t0: datetime, entro_ore: float = 40.0) -> list[dict]:
    """Calendario con previsioni (ForexFactory, gratuito): solo dati USA ad alto impatto. Restituisce eventi con «attese» (previsto e precedente)."""
    gruppi: dict[tuple, dict] = {}
    for r in righe or []:
        try:
            if r.get("country") != "USD" or r.get("impact") != "High":
                continue
            q = datetime.fromisoformat(r["date"]).astimezone(timezone.utc)
            if not (timedelta(hours=-6) <= q - t0 <= timedelta(hours=entro_ore)):
                continue
            t = (r.get("title") or "").strip()
            tl = t.lower()
            if "fomc" in tl or "federal funds" in tl:
                k, nome = "FOMC", None
            elif "cpi" in tl:
                k, nome = "CPI", None
            elif "non-farm" in tl or "unemployment rate" in tl or "nonfarm" in tl:
                k, nome = "NFP", None
            elif "speaks" in tl or "speech" in tl:
                continue
            else:
                k, nome = "ALTRO:" + t, t
            att = f"{t}: previsto {r.get('forecast') or 'n.d.'}, precedente {r.get('previous') or 'n.d.'}"
            g = gruppi.setdefault((k, q.strftime("%Y-%m-%d")), {"q": q, "att": [], "nome": nome})
            g["att"].append(att)
            g["q"] = min(g["q"], q)
        except Exception:  # noqa: BLE001
            continue
    out = []
    for (k, _), g in gruppi.items():
        chiave = k if k in MACRO else "ALTRO"
        e = _evento_macro(chiave, g["q"], t0, g["att"], g["nome"])
        e["ticker"] = k if k in MACRO else "ALTRO"
        out.append(e)
    return out


def leggi_ff(t0: datetime, entro_ore: float = 40.0, get=None) -> list[dict]:
    """Scarica le due settimane dal feed gratuito; silenzioso se non risponde."""
    righe: list[dict] = []
    try:
        import requests
        g = get or (lambda u: requests.get(u, timeout=15, headers={"User-Agent": "Mozilla/5.0"}))
        for nome in ("thisweek", "nextweek"):
            try:
                x = g(f"https://nfs.faireconomy.media/ff_calendar_{nome}.json")
                if getattr(x, "ok", True):
                    righe += x.json()
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        return []
    return parse_ff(righe, t0, entro_ore)


def unisci(base: list[dict], extra: list[dict]) -> list[dict]:
    """Calendario interno + feed con previsioni: se lo stesso evento è in entrambi vince l'orario del feed e si tengono le previsioni."""
    out = {(e["ticker"], e["quando"][:10]): e for e in base}
    for e in extra:
        k = (e["ticker"], e["quando"][:10])
        if k in out and e["ticker"] != "ALTRO":
            out[k].update({"quando": e["quando"], "gia_uscita": e["gia_uscita"], "attese": e["attese"]})
        else:
            out[(e["ticker"] + e["nome"], e["quando"][:10])] = e
    return sorted(out.values(), key=lambda x: x["quando"])


# ---------------------------------------------------------------- storico delle reazioni (dati già salvati da Armor)
def storico(tk: str) -> dict | None:
    """Per un titolo: quante trimestrali, quante volte ha battuto le stime, quante volte il titolo è salito il giorno dopo, mossa media in valore assoluto."""
    try:
        tr = json.loads((DATA / "eventi_trimestrali.json").read_text(encoding="utf-8"))
        s = pd.read_csv(DATA / "azioni" / f"{tk}.csv", parse_dates=["date"]).set_index("date")["value"].dropna()
    except Exception:  # noqa: BLE001
        return None
    reaz, bat = [], 0
    tot = 0
    for v in tr.values():
        if v.get("ticker") != tk or not v.get("stima") or v.get("reale") is None:
            continue
        d = pd.Timestamp(v["data"])
        a, b = s[s.index <= d], s[s.index > d]
        if len(a) < 5 or not len(b) or (d - a.index[-1]).days > 3:
            continue
        tot += 1
        bat += int(v["reale"] > v["stima"])
        reaz.append(float(b.iloc[0] / a.iloc[-1] - 1.0))
    if len(reaz) < 6:
        return None
    return {"n": len(reaz), "battuti": bat, "saliti": sum(1 for x in reaz if x > 0), "media_abs": round(100 * sum(abs(x) for x in reaz) / len(reaz), 1)}


# ---------------------------------------------------------------- attese degli analisti
def snapshot_analisti(tk: str) -> dict:
    """Stime, revisioni, storico delle sorprese e obiettivi di prezzo da Yahoo. Ogni pezzo è opzionale."""
    import yfinance as yf
    t = yf.Ticker(tk)
    o: dict = {}
    try:
        q = t.earnings_estimate.loc["0q"]
        o.update(eps=_num(q["avg"]), eps_basso=_num(q["low"]), eps_alto=_num(q["high"]), eps_anno_fa=_num(q["yearAgoEps"]), eps_cresc=_num(q["growth"]), n=int(q["numberOfAnalysts"]))
    except Exception:  # noqa: BLE001
        pass
    try:
        r = t.revenue_estimate
        o.update(ricavi=_num(r.loc["0q", "avg"]), ricavi_cresc=_num(r.loc["0q", "growth"]))
        if "+1q" in r.index:
            o.update(ricavi_prox=_num(r.loc["+1q", "avg"]), ricavi_prox_cresc=_num(r.loc["+1q", "growth"]))
    except Exception:  # noqa: BLE001
        pass
    try:
        e = t.eps_trend.loc["0q"]
        if _num(e["30daysAgo"]):
            o["rev30"] = float(e["current"]) / float(e["30daysAgo"]) - 1.0
        v = t.eps_revisions.loc["0q"]
        o.update(su30=int(v["upLast30days"]), giu30=int(v["downLast30days"]))
    except Exception:  # noqa: BLE001
        pass
    try:
        p = t.analyst_price_targets
        o.update(obiettivo=_num(p.get("mean")), prezzo=_num(p.get("current")))
    except Exception:  # noqa: BLE001
        pass
    try:
        s = t.recommendations_summary.iloc[0]
        tot = float(s[["strongBuy", "buy", "hold", "sell", "strongSell"]].sum())
        if tot:
            o["compra"] = float(s["strongBuy"] + s["buy"]) / tot
    except Exception:  # noqa: BLE001
        pass
    try:
        h = t.earnings_history.dropna(subset=["epsActual", "epsEstimate"])
        if len(h):
            ult = h.iloc[-1]
            o["ultimo"] = {"trim": str(h.index[-1])[:10], "reale": _num(ult["epsActual"]), "stima": _num(ult["epsEstimate"]), "sorpresa": _num(ult.get("surprisePercent"))}
            o["battuti4"] = int((h["epsActual"].tail(4) > h["epsEstimate"].tail(4)).sum())
            o["n4"] = int(len(h.tail(4)))
            o["media_sorpresa4"] = _num(h["surprisePercent"].tail(4).mean())
    except Exception:  # noqa: BLE001
        pass
    return o


def analisti(tk: str, t0: datetime, forza: bool = False) -> dict:
    """Con cache su file (rinnovata ogni 6 ore) per non interrogare Yahoo a ogni giro."""
    try:
        cache = json.loads(FILE_AN.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cache = {}
    c = cache.get(tk)
    if c and not forza:
        try:
            if (t0 - datetime.strptime(c["_ora"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)) < timedelta(hours=ETA_CACHE_ORE):
                return c
        except Exception:  # noqa: BLE001
            pass
    try:
        nuovo = snapshot_analisti(tk)
    except Exception:  # noqa: BLE001
        return c or {}
    if not nuovo:
        return c or {}
    nuovo["_ora"] = t0.strftime("%Y-%m-%dT%H:%MZ")
    cache[tk] = nuovo
    try:
        FILE_AN.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return nuovo


def lettura_trimestrale(e: dict, an: dict, st: dict | None) -> list[dict]:
    """Frasi semplici con la chiave di lettura. Ogni riga: {t: testo, c: ''|'ok'|'warn'}."""
    nome = e["nome"]
    out = []
    if an.get("eps") is not None:
        t = f"{an.get('n', '?')} analisti si aspettano un utile di {_n(an['eps'], 2)} $ per azione"
        if an.get("eps_cresc") is not None:
            t += f" ({_n(an['eps_cresc'] * 100, 0, True)}% sull'anno scorso)"
        if an.get("ricavi"):
            t += f" e ricavi per {_n(an['ricavi'] / 1e9, 1)} miliardi"
            if an.get("ricavi_cresc") is not None:
                t += f" ({_n(an['ricavi_cresc'] * 100, 0, True)}%)"
        out.append({"t": t + ". Chiave di lettura: questo è il livello già nel prezzo; conta la differenza tra il risultato e queste attese.", "c": ""})
    if an.get("rev30") is not None:
        r = an["rev30"] * 100
        if abs(r) < 1.0:
            out.append({"t": "Nell'ultimo mese le stime sono rimaste praticamente invariate: nessuna corsa a rialzare le attese, l'asticella è quella di un mese fa.", "c": ""})
        elif r > 0:
            out.append({"t": f"Le stime sono state alzate del {_n(r, 1)}% nell'ultimo mese ({an.get('su30', 0)} analisti al rialzo, {an.get('giu30', 0)} al ribasso): l'asticella è più alta, più facile deludere.", "c": "warn"})
        else:
            out.append({"t": f"Le stime sono state abbassate del {_n(abs(r), 1)}% nell'ultimo mese ({an.get('giu30', 0)} analisti al ribasso): l'asticella è più bassa, più facile sorprendere in positivo.", "c": "ok"})
    if an.get("n4"):
        m = f" (in media {_n(an['media_sorpresa4'] * 100, 1, True)}%)" if an.get("media_sorpresa4") is not None else ""
        out.append({"t": f"Negli ultimi {an['n4']} trimestri ha battuto le stime {an['battuti4']} volte{m}.", "c": ""})
    if st:
        out.append({"t": f"Ma battere le stime non basta: dopo i conti il titolo è salito il {_n(100 * st['saliti'] / st['n'], 0)}% delle volte su {st['n']} trimestri, con una mossa media di ±{_n(st['media_abs'])}% il giorno dopo. "
                         "Contano la guida per il trimestre successivo e quanto era già nel prezzo.", "c": "warn"})
    if an.get("ricavi_prox"):
        out.append({"t": f"Cosa guardare per primo: i ricavi attesi per il prossimo trimestre ({_n(an['ricavi_prox'] / 1e9, 1)} miliardi"
                         + (f", {_n(an['ricavi_prox_cresc'] * 100, 0, True)}%" if an.get("ricavi_prox_cresc") is not None else "") + ").", "c": ""})
    if an.get("obiettivo") and an.get("prezzo"):
        up = an["obiettivo"] / an["prezzo"] - 1
        c = f" {_n(an['compra'] * 100, 0)}% di loro consiglia di comprare." if an.get("compra") is not None else ""
        out.append({"t": f"Obiettivo medio degli analisti: {_n(an['obiettivo'], 0)} $ ({_n(up * 100, 0, True)}% sul prezzo di {_n(an['prezzo'], 0)} $).{c}", "c": ""})
    if e.get("gia_uscita") and an.get("ultimo"):
        u = an["ultimo"]
        try:
            fresco = 0 < (datetime.strptime(e["quando"][:10], "%Y-%m-%d") - datetime.strptime(u["trim"], "%Y-%m-%d")).days <= 60
        except Exception:  # noqa: BLE001
            fresco = False
        if fresco and u.get("reale") is not None and u.get("stima"):
            sp = u["reale"] / u["stima"] - 1
            out.insert(0, {"t": f"Conti usciti: utile {_n(u['reale'], 2)} $ contro {_n(u['stima'], 2)} $ attesi ({_n(sp * 100, 1, True)}%). La reazione del prezzo è già nei futures.", "c": "ok" if sp > 0 else "warn"})
    return out


# ---------------------------------------------------------------- notizie
def _tema(titolo_en: str) -> list[str]:
    t = " " + titolo_en.lower() + " "
    return [k for k, parole in TEMI_SHOCK.items() if any(p in t for p in parole)]


def notizie(t0: datetime, news: dict | None = None, ore: float = 24.0, quante: int = 5) -> dict:
    """Notizie delle ultime 24 ore che possono scuotere il mercato: le più importanti, con tema e segno; più il tono medio rispetto agli ultimi giorni."""
    if news is None:
        try:
            from . import news as nw
            news = nw.load_latest()
        except Exception:  # noqa: BLE001
            news = {}
    items = []
    for i in (news or {}).get("items", []):
        try:
            q = datetime.strptime(i["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        if not (timedelta(0) <= t0 - q <= timedelta(hours=ore)):
            continue
        temi = _tema(i.get("title_en") or i.get("title") or "")
        items.append({"titolo": i.get("title"), "fonte": i.get("source"), "quando": i["time"], "sent": float(i.get("sent") or 0), "score": float(i.get("score") or 0), "temi": temi, "link": i.get("link"), "kind": i.get("kind")})
    if not items:
        return {"n": 0, "elenco": [], "tono": None, "temi": {}}
    sc = sorted(items, key=lambda x: (-(bool(x["temi"])), -x["score"]))
    elenco = sorted([x for x in items if x["temi"]], key=lambda x: -x["score"])[:quante] or sc[:quante]
    temi: dict[str, int] = {}
    for x in items:
        for k in x["temi"]:
            temi[k] = temi.get(k, 0) + 1
    macro = [x["sent"] for x in items if x["kind"] == "macro"]
    tono = sum(macro) / len(macro) if macro else None
    base = None
    try:
        from . import news as nw
        h = nw.history_sentiment(14)
        oggi = t0.strftime("%Y-%m-%d")
        prima = [v for k, v in h.items() if k != oggi]
        base = sum(prima) / len(prima) if prima else None
    except Exception:  # noqa: BLE001
        pass
    return {"n": len(items), "elenco": elenco, "tono": tono, "tono_base": base, "temi": dict(sorted(temi.items(), key=lambda kv: -kv[1]))}


def arricchisci(e: dict, t0: datetime, con_rete: bool = True) -> dict:
    """Aggiunge a una trimestrale: storico delle reazioni e attese degli analisti con la lettura; a un dato macro non serve altro."""
    if e.get("tipo") == "macro":
        return e
    tk = e["ticker"]
    st = storico(tk)
    if st:
        e["storico"] = st
    an = analisti(tk, t0) if con_rete else {}
    if an:
        e["analisti"] = {k: v for k, v in an.items() if not k.startswith("_")}
    e["lettura"] = lettura_trimestrale(e, an or {}, st)
    return e
