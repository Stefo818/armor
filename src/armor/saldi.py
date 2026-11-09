"""«Saldi»: i 100 titoli e ETF scesi di più per periodo, con indicatori, causa del calo, punteggio «Salute» 1-100 e report in italiano (PIANO_ESPANSIONE Patch 46).
Pesi e regole in PROTOCOLLO_SALDI.md. Il punteggio misura «salute e probabilità di recupero stimate», non è una previsione né un consiglio.
Le funzioni di calcolo sono pure (testate); `aggiorna()` (lavoro serale) recupera fondamentali, notizie e 8-K dei soli candidati."""
import hashlib
import html as _h
import json

import numpy as np
import pandas as pd

from . import titoli_eventi as ev
from . import titoli_fond as tf
from .config import DATA, ROOT

FILE = DATA / "saldi.json"
REGISTRO = DATA / "saldi_registro.csv"
VERIFICA = DATA / "saldi_verifica.json"
LOG = DATA / "protocollo_saldi_log.csv"
PERIODI = [("1g", "1 giorno"), ("3g", "3 giorni"), ("1s", "1 settimana"), ("1m", "1 mese"), ("3m", "3 mesi"), ("6m", "6 mesi")]
IDX = {"1g": 0, "1s": 1, "1m": 2, "3m": 3, "6m": 4}      # posizione nel vettore r di titoli_top (1g, 1s, 1m, 3m, 6m, 1a)
PESI = {"solidita": 0.30, "qualita": 0.25, "calo": 0.20, "valutazione": 0.15, "fiducia": 0.10}
NOMI_COMP = {"solidita": "Solidità finanziaria", "qualita": "Qualità e tendenza", "calo": "Natura del calo", "valutazione": "Valutazione dopo il calo", "fiducia": "Segnali di fiducia"}
ETF_SETTORE = {"Technology": "XLK", "Communication Services": "XLC", "Consumer Cyclical": "XLY", "Financial Services": "XLF", "Industrials": "XLI", "Energy": "XLE",
               "Basic Materials": "XLB", "Healthcare": "XLV", "Consumer Defensive": "XLP", "Utilities": "XLU", "Real Estate": "XLRE"}
SETTORE_IT = {"Technology": "Tecnologia", "Communication Services": "Comunicazioni", "Consumer Cyclical": "Consumi ciclici", "Financial Services": "Finanza", "Industrials": "Industria",
              "Energy": "Energia", "Basic Materials": "Materiali", "Healthcare": "Salute", "Consumer Defensive": "Beni di consumo base", "Utilities": "Servizi pubblici", "Real Estate": "Immobiliare"}
# punteggio «natura del calo» per tipo di evento (0-100); None = evento neutro
CALO_EVENTO = {"capitale": 40, "sotto_attese": 25, "guid_giu": 15, "crl": 10, "studio_ko": 10, "indagine": 5, "fallimento": 0, "ceo": 35, "richiamo": 35, "causa": 40,
               "downgrade": 40, "regole": 45, "short": 25, "sopra_attese": 70, "guid_su": 70, "upgrade": 70}
TETTO = 15


# ---------------------------------------------------------------- protocollo
def protocollo_hash() -> str:
    f = ROOT / "PROTOCOLLO_SALDI.md"
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:24] if f.exists() else ""


def registra_protocollo() -> str:
    from datetime import datetime, timezone
    h = protocollo_hash()
    if not h:
        return ""
    righe = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else ["data_utc,impronta"]
    if not any(r.endswith("," + h) for r in righe[1:]):
        righe.append(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},{h}")
        LOG.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return h


# ---------------------------------------------------------------- punteggio
def percentile(x, pool, migliore_alto: bool = True) -> float | None:
    """Percentile 0-1 di x nell'insieme `pool`, valori tagliati al 2%-98%; se migliore_alto è False, il valore basso è migliore."""
    if x is None:
        return None
    v = np.array([p for p in pool if p is not None and np.isfinite(p)], float)
    if len(v) < 5 or not np.isfinite(x):
        return None
    lo, hi = np.quantile(v, [0.02, 0.98])
    xc = float(np.clip(x, lo, hi))
    vc = np.clip(v, lo, hi)
    p = float((vc < xc).mean() + 0.5 * (vc == xc).mean())
    return p if migliore_alto else 1 - p


def _voci(ind: dict) -> dict:
    """Voci numeriche (con verso) usate dalle componenti di un titolo; mancanti = None."""
    alt = (ind.get("altman") or {}).get("z")
    pio = (ind.get("piotroski") or {}).get("score")
    cr = (ind.get("ricavi_q_1a") or {}).get("var")
    return {
        "altman": alt, "copertura": ind.get("copertura_interessi"), "leva": ind.get("debito_netto_ebitda"), "current": ind.get("current_ratio"),
        "cassa": ind.get("mesi_cassa"), "diluizione": ind.get("diluizione"),
        "piotroski": pio, "crescita": cr, "margine_lordo": ind.get("margine_lordo"), "margine_fcf": ind.get("margine_fcf"), "roe": ind.get("roe"),
        "ps": ind.get("ps"), "pe": ind.get("pe"), "ps_f": ind.get("ps_f"), "ev_ebitda": ind.get("ev_ebitda"),
    }


VERSO = {"altman": True, "copertura": True, "leva": False, "current": True, "cassa": True, "diluizione": False, "piotroski": True, "crescita": True,
         "margine_lordo": True, "margine_fcf": True, "roe": True, "ps": False, "pe": False, "ps_f": False, "ev_ebitda": False}
COMP_VOCI = {"solidita": ("altman", "copertura", "leva", "current", "cassa", "diluizione"), "qualita": ("piotroski", "crescita", "margine_lordo", "margine_fcf", "roe"),
             "valutazione": ("ps", "pe", "ps_f", "ev_ebitda")}


def calo_score(causa: dict, eventi: list[dict], periodo: str) -> float | None:
    """Natura del calo: settore/mercato o nessuna notizia = positivo; eventi negativi dell'azienda = negativi (peso pieno nei periodi brevi, dimezzato oltre)."""
    if causa is None:
        return None
    if causa["tipo"] == "settore":
        s = 80.0
    elif causa["tipo"] == "ignota":
        s = 70.0
    else:
        negativi = [CALO_EVENTO[e["evento"]] for e in eventi if e["evento"] in CALO_EVENTO and (e.get("saldi") or 0) != "escludi" and isinstance(e.get("saldi"), int) and e["saldi"] < 0]
        s = float(min(negativi)) if negativi else 55.0
    if periodo in ("3m", "6m"):
        s = 0.5 * s + 25
    return s


def fiducia_score(ind: dict, prezzo: float | None) -> float | None:
    parti = []
    if ind.get("insider_acq_90g") is not None:
        parti.append(80.0 if ind["insider_acq_90g"] > 0 else 50.0)
    an = ind.get("analisti") or {}
    if an.get("raccomandazione"):
        parti.append(float(np.clip((5 - an["raccomandazione"]) / 4 * 100, 0, 100)))
    if ind.get("short_float") is not None:
        parti.append(100 - min(ind["short_float"] / 0.2, 1) * 100)
    if an.get("target") and prezzo:
        parti.append(float(np.clip((an["target"] / prezzo - 1) / 0.5, 0, 1) * 100))
    return float(np.mean(parti)) if parti else None


def tetti(ind: dict, eventi: list[dict], eventi_8k: list[dict]) -> list[str]:
    """Motivi per cui il punteggio non può superare 15/100."""
    m = []
    if any(e["evento"] == "fallimento" and "going concern" in (e.get("titolo") or "").lower() for e in eventi):
        m.append("dubbio sulla continuità aziendale")
    for e in eventi_8k or []:
        if e["item"] in ("1.03", "3.01", "4.02"):
            m.append(f"8-K {e['item']}: {e['evento']}")
    if any(e["evento"] == "short" and "fraud" in (e.get("titolo") or "").lower() for e in eventi):
        m.append("rapporto di uno short seller con accuse di frode")
    if ind.get("mesi_cassa") is not None and ind["mesi_cassa"] < 6:
        m.append(f"cassa per meno di 6 mesi ({ind['mesi_cassa']:.0f})")
    return m


def punteggi(cand: dict[str, dict], periodo_di: dict[str, str]) -> dict[str, dict]:
    """cand: ticker → {ind, voci?, causa, eventi, eventi_8k, prezzo, settore}. periodo_di: ticker → periodo di riferimento per il peso del calo.
    Restituisce ticker → {score, comp, usati, tetti}. I percentili sono nell'insieme dei candidati (nel settore per la valutazione se ≥ 8 titoli)."""
    voci = {t: _voci(c["ind"]) for t, c in cand.items()}
    pool = {k: [v[k] for v in voci.values()] for k in VERSO}
    per_sett: dict[str, dict] = {}
    for t, c in cand.items():
        per_sett.setdefault(c.get("settore") or "?", {}).setdefault("t", []).append(t)
    out = {}
    for t, c in cand.items():
        comp = {}
        for nome, chiavi in COMP_VOCI.items():
            ps = []
            for k in chiavi:
                v = voci[t][k]
                if v is None:
                    continue
                gruppo = per_sett.get(c.get("settore") or "?", {}).get("t", [])
                p_ref = [voci[g][k] for g in gruppo] if (nome == "valutazione" and len(gruppo) >= 8) else pool[k]
                p = percentile(v, p_ref, VERSO[k])
                if p is not None:
                    ps.append(p)
            comp[nome] = float(np.mean(ps) * 100) if ps else None
        comp["calo"] = calo_score(c.get("causa"), c.get("eventi", []), periodo_di.get(t, "1s"))
        comp["fiducia"] = fiducia_score(c["ind"], c.get("prezzo"))
        disp = {k: v for k, v in comp.items() if v is not None}
        raw = None
        if len(disp) >= 2:
            w = sum(PESI[k] for k in disp)
            raw = sum(PESI[k] * v for k, v in disp.items()) / w
        out[t] = {"raw": raw, "comp": {k: (None if v is None else round(v)) for k, v in comp.items()}, "usati": len(disp), "tetti": tetti(c["ind"], c.get("eventi", []), c.get("eventi_8k", []))}
    raws = [o["raw"] for o in out.values() if o["raw"] is not None]
    for o in out.values():
        if o["raw"] is None:
            o["score"] = None
            continue
        p = float((np.array(raws) < o["raw"]).mean() + 0.5 * (np.array(raws) == o["raw"]).mean())
        s = int(round(1 + 99 * p))
        o["score"] = min(s, TETTO) if o["tetti"] else s
    return out


# ---------------------------------------------------------------- report in italiano (a regole)
def _pc(x, d=0) -> str:
    return "—" if x is None else f"{x * 100:.{d}f}%".replace(".", ",")


def _v(x, d=1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _mld(x) -> str:
    if x is None:
        return "—"
    return f"{x / 1e9:.1f} mld".replace(".", ",") if abs(x) >= 1e9 else f"{x / 1e6:.0f} mln"


def report(t: dict, ind: dict, causa: dict, eventi: list[dict], periodo: str, nome_periodo: str, r: float | None, r_sett: float | None, tetti_: list[str], mediane: dict | None = None,
           rendimenti: dict | None = None) -> dict:
    """Quattro blocchi: perché è sceso, come sta l'azienda, perché potrebbe essere acquistabile, rischi. Solo frasi supportate dai dati."""
    mediane = mediane or {}
    perche = []
    if rendimenti:
        nomi = dict(PERIODI)
        neg = [f"{_pc(abs(v), 1)} in {nomi[k]}" for k, v in rendimenti.items() if v is not None and v < 0]
        if neg:
            perche.append("Il titolo ha perso " + ", ".join(neg) + ".")
    if r is not None and r_sett is not None:
        base = f"Nel periodo di riferimento ({nome_periodo}) il titolo ha perso il {_pc(abs(r), 1)}"
        if r_sett is not None:
            base += f"; il suo settore {'ha perso il ' + _pc(abs(r_sett), 1) if r_sett < 0 else 'è salito del ' + _pc(r_sett, 1)}"
        perche.append(base + ".")
    elif r is not None and not rendimenti:
        perche.append(f"Il titolo ha perso il {_pc(abs(r), 1)} in {nome_periodo}.")
    perche.append(causa["testo"] if causa else "Causa non identificata.")
    for e in (eventi[1:3] if causa and causa["tipo"] == "azienda" else eventi[:2]):
        if e.get("titolo") and e["evento"] not in ("spam",):
            perche.append(f"Il {e['data'][8:]}/{e['data'][5:7]}: {e['etichetta'].lower()}" + (f" (importo citato {_mld(e['importo'])})" if e.get("importo") else "") + ".")
    sal = []
    ra = ind.get("ricavi_q_1a")
    if ra:
        sal.append(f"Il fatturato dell'ultimo trimestre è {ra['f']} {_pc(abs(ra['var']), 1)} rispetto allo stesso trimestre dell'anno scorso.")
    if ind.get("margine_lordo") is not None or ind.get("margine_fcf") is not None:
        sal.append("Margine lordo " + _pc(ind.get("margine_lordo")) + (f", margine di cassa libera {_pc(ind.get('margine_fcf'))}" if ind.get("margine_fcf") is not None else "") + ".")
    if ind.get("debito_netto_ebitda") is not None:
        sal.append(f"Debito netto pari a {_v(ind['debito_netto_ebitda'])} volte il margine operativo lordo.")
    if ind.get("mesi_cassa") is not None:
        sal.append(f"L'azienda perde cassa: la liquidità basta per circa {ind['mesi_cassa']:.0f} mesi al ritmo attuale.")
    if ind.get("piotroski"):
        sal.append(f"Punteggio di solidità contabile (F-score) {ind['piotroski']['score']} su {ind['piotroski']['su']} criteri valutabili.")
    fav = []
    for k, lab, plurale in (("ps", "fatturato", "volte il fatturato"), ("ps_f", "fatturato atteso", "volte il fatturato atteso")):
        v, m = ind.get(k), mediane.get(k)
        if v and m and v < 0.8 * m:
            fav.append(f"La valutazione è di {_v(v)} {plurale}, contro {_v(m)} della mediana dei candidati di questo settore.")
            break
    if (ind.get("insider_acq_90g") or 0) > 0:
        fav.append("Dirigenti o amministratori hanno comprato azioni sul mercato negli ultimi 90 giorni.")
    rpo = ind.get("rpo")
    if rpo and ind.get("rpo_anni") and ind["rpo_anni"] >= 0.5:
        fav.append(f"Contratti già firmati e non ancora fatturati pari a {_v(ind['rpo_anni'])} anni di fatturato.")
    an = ind.get("analisti") or {}
    if an.get("target") and t.get("prezzo") and an["target"] / t["prezzo"] - 1 > 0.2 and (an.get("n") or 0) >= 5:
        fav.append(f"Il prezzo obiettivo medio degli analisti ({int(an['n'])} stime) è del {_pc(an['target'] / t['prezzo'] - 1)} sopra il prezzo attuale.")
    if causa and causa["tipo"] in ("settore", "ignota"):
        fav.append("Il calo non è legato a notizie negative dell'azienda: storicamente i cali senza notizie si riassorbono più spesso di quelli con notizie.")
    if not fav:
        fav.append("Non emergono punti nettamente favorevoli dai dati disponibili.")
    risc = []
    if tetti_:
        risc.append("Punteggio limitato a 15/100 per: " + "; ".join(tetti_) + ".")
    if causa and causa["tipo"] == "azienda":
        risc.append("Dopo risultati deludenti o previsioni tagliate il calo tende a proseguire per settimane (deriva post-annuncio).")
    if ind.get("altman") and ind["altman"]["zona"] == "critica":
        risc.append("L'indice di rischio di dissesto (Altman) è in zona critica.")
    if (ind.get("diluizione") or 0) > 0.1:
        risc.append(f"Le azioni in circolazione sono aumentate del {_pc(ind['diluizione'])} in un anno (diluizione).")
    if ind.get("rischio_binario"):
        risc.append(ind["rischio_binario"]["testo"])
    if ind.get("short_float") and ind["short_float"] > 0.15:
        risc.append(f"Quota alta di vendite allo scoperto ({_pc(ind['short_float'])} dei titoli in circolazione).")
    risc.append("Su 3-12 mesi i titoli in calo tendono in media a restare in calo (momentum): un titolo «scontato» può diventarlo ancora di più.")
    return {"perche": " ".join(perche), "salute": " ".join(sal) or "Dati di bilancio non disponibili.", "favorevole": " ".join(fav), "rischi": " ".join(risc),
            "nota": "Non è una consulenza: è una sintesi automatica di dati pubblici."}


# ---------------------------------------------------------------- costruzione (pura)
def area_di(ticker: str, paese: str | None) -> str:
    if paese in ("United States", None) and "." not in ticker:
        return "USA"
    if paese in ("Japan", "China", "Hong Kong", "India", "South Korea", "Taiwan", "Australia", "Singapore") or ticker.endswith((".T", ".KS", ".TW", ".HK", ".NS", ".AX", ".SS", ".SZ")):
        return "Asia"
    if paese in ("Germany", "France", "Italy", "United Kingdom", "Netherlands", "Spain", "Switzerland", "Sweden", "Denmark", "Norway", "Finland", "Ireland") or ticker.endswith((".DE", ".MI", ".PA", ".L", ".AS", ".MC", ".SW", ".ST", ".CO", ".OL", ".HE")):
        return "Europa"
    return "USA" if paese == "United States" else "Altri"


def dimensione(cap) -> str:
    if not cap:
        return "n/d"
    return "grandi" if cap > 10e9 else "medie" if cap >= 2e9 else "piccole"


def ritorno(it: dict, periodo: str) -> float | None:
    if periodo == "3g":
        return it.get("x3")
    return it["r"][IDX[periodo]]


def candidati(top: dict, n: int = 100) -> dict[str, list[str]]:
    """Per ogni periodo i n titoli scesi di più (solo rendimenti negativi)."""
    out = {}
    for p, _ in PERIODI:
        v = [(ritorno(i, p), i["t"]) for i in top["items"] if ritorno(i, p) is not None and ritorno(i, p) < 0]
        out[p] = [t for _, t in sorted(v)[:n]]
    return out


def costruisci(top: dict, fond: dict, notizie: dict, etf: list[dict] | None, ret_settori: dict, eurusd: float | None, n: int = 100, eventi_8k: dict | None = None) -> dict:
    """top = titoli_top.json; fond = {ticker: indicatori}; notizie = {ticker: [notizie]}; etf = voci 'etf' di mercati_mondo; ret_settori = {ETF settore: r per periodo}."""
    eventi_8k = eventi_8k or {}
    cls = candidati(top, n)
    ticker = sorted({t for l in cls.values() for t in l})
    by = {i["t"]: i for i in top["items"]}
    periodo_di = {}
    for p, _ in PERIODI:
        for t in cls[p]:
            periodo_di.setdefault(t, p)
    cand, riassunti = {}, {}
    for t in ticker:
        i, ind = by[t], fond.get(t) or {}
        ric = ind.get("ricavi_ttm")
        rs = ev.riassumi(notizie.get(t, []), ric)
        riassunti[t] = rs
        sett = ind.get("settore") or (i.get("s") if i.get("s") != "n/d" else None)
        etfs = ETF_SETTORE.get(sett or "")
        rp = ritorno(i, periodo_di[t])
        r_sett = (ret_settori.get(etfs) or {}).get(periodo_di[t]) if etfs else None
        causa = ev.causa_calo(rp, r_sett, i.get("beta") or 1.0, rs["eventi"]) if rp is not None else None
        ind = dict(ind)
        ind["rischio_binario"] = ev.rischio_binario(ind.get("industria"), ric, None)
        cand[t] = {"ind": ind, "causa": causa, "eventi": rs["eventi"], "eventi_8k": eventi_8k.get(t, []), "prezzo": i["p"], "settore": sett}
    pt = punteggi(cand, periodo_di) if cand else {}
    esclusi = {t for t, r in riassunti.items() if r["escludi"]}
    dett, righe = {}, {}
    for t in ticker:
        if t in esclusi:
            continue
        i, c, s = by[t], cand[t], pt.get(t, {})
        ind = c["ind"]
        sett = c["settore"]
        mediane = {}
        for k in ("ps", "ps_f"):
            vv = [cand[g]["ind"].get(k) for g in ticker if cand[g]["settore"] == sett and cand[g]["ind"].get(k)]
            mediane[k] = float(np.median(vv)) if len(vv) >= 4 else None
        p0 = periodo_di[t]
        rep = report({"prezzo": i["p"]}, ind, c["causa"], c["eventi"], p0, dict(PERIODI)[p0], ritorno(i, p0),
                     (ret_settori.get(ETF_SETTORE.get(sett or "")) or {}).get(p0) if sett else None, s.get("tetti", []), mediane,
                     {p: ritorno(i, p) for p, _ in PERIODI})
        rg = {p: ritorno(i, p) for p, _ in PERIODI}
        righe[t] = {"n": ind.get("nome") or i["n"], "t": t, "tipo": "Azione", "area": area_di(t, ind.get("paese") or i.get("paese")), "dim": dimensione(ind.get("cap") or i.get("cap")),
                    "sett": SETTORE_IT.get(sett or "", sett or "n/d"), "cap": ind.get("cap") or i.get("cap"), "v": i["v"], "p": i["p"], "eur": None if not eurusd or i["v"] != "USD" else round(i["p"] / eurusd, 2),
                    "r": rg, "ric": None if not ind.get("ricavi_q_1a") else {"f": ind["ricavi_q_1a"]["f"], "v": ind["ricavi_q_1a"]["var"]},
                    "ps": ind.get("ps"), "pe": ind.get("pe"), "ps_f": ind.get("ps_f"), "leva": ind.get("debito_netto_ebitda"), "cassa": ind.get("mesi_cassa"),
                    "fs": (ind.get("piotroski") or {}).get("score"), "causa": (c["causa"] or {}).get("tipo", "ignota"), "causa_t": (c["eventi"][0]["etichetta"] if c["eventi"] and (c["causa"] or {}).get("tipo") == "azienda" else
                                                                                                                                  "Calo di settore o di mercato" if (c["causa"] or {}).get("tipo") == "settore" else "Nessuna notizia"),
                    "s": s.get("score"), "comp": s.get("comp"), "usati": s.get("usati"), "tetti": s.get("tetti", []), "k": i.get("k6") or i.get("k")}
        dett[t] = {"ind": {k: ind.get(k) for k in ("ricavi_q", "ricavi_ttm", "ps", "pe", "ps_f", "pe_f", "ev_ebitda", "cap_rpo", "rpo_anni", "copertura_interessi", "debito_netto_ebitda",
                                                    "current_ratio", "margine_lordo", "margine_fcf", "roe", "mesi_cassa", "diluizione", "accruals", "short_float", "insider_acq_90g")}
                   | {"piotroski": (ind.get("piotroski") or {}).get("score"), "altman": (ind.get("altman") or {}).get("z"), "altman_zona": (ind.get("altman") or {}).get("zona"),
                      "target": (ind.get("analisti") or {}).get("target"), "raccomandazione": (ind.get("analisti") or {}).get("raccomandazione")},
                   "notizie": [{"d": e["data"], "t": e["titolo"], "l": e.get("link"), "f": e.get("fonte"), "e": e["etichetta"]} for e in c["eventi"][:5]], "report": rep}
    classifiche = {p: [t for t in cls[p] if t in righe] for p, _ in PERIODI}
    elenco_etf = []
    for e in (etf or []):
        elenco_etf.append({"n": e["n"], "t": e["t"], "tipo": "ETF", "area": "n/d", "dim": "n/d", "sett": e.get("s", ""), "v": e["v"], "p": e["p"],
                           "r": {"1g": e["r"][0], "3g": None, "1s": e["r"][1], "1m": e["r"][2], "3m": e["r"][3], "6m": e["r"][4]}, "k": e.get("k")})
    etf_cls = {p: [x["t"] for x in sorted([y for y in elenco_etf if y["r"][p] is not None and y["r"][p] < 0], key=lambda y: y["r"][p])[:n]] for p, _ in PERIODI}
    return {"periodi": [[k, v] for k, v in PERIODI], "titoli": righe, "dett": dett, "classifiche": classifiche, "etf": {x["t"]: x for x in elenco_etf}, "etf_classifiche": etf_cls,
            "pesi": {NOMI_COMP[k]: v for k, v in PESI.items()}, "escluse_acquisizioni": sorted(esclusi), "asof": top.get("asof"), "protocollo": protocollo_hash()}


# ---------------------------------------------------------------- registro e verifica
def registra(d: dict, data: str, per_periodo: int = 30) -> int:
    """Aggiunge a data/saldi_registro.csv i `per_periodo` titoli più calati per periodo, con punteggio e componenti (una riga per data/ticker/periodo)."""
    esiste = REGISTRO.exists() and REGISTRO.stat().st_size > 0
    gia = set()
    if esiste:
        for r in REGISTRO.read_text(encoding="utf-8").splitlines()[1:]:
            c = r.split(",")
            gia.add((c[0], c[1], c[2]))
    righe = []
    for p, _ in PERIODI:
        for t in d["classifiche"][p][:per_periodo]:
            if (data, t, p) in gia:
                continue
            x = d["titoli"][t]
            c = x.get("comp") or {}
            righe.append(",".join([data, t, p, "" if x["s"] is None else str(x["s"]), str(x["p"])] + ["" if c.get(k) is None else str(c[k]) for k in PESI]))
    if righe:
        with open(REGISTRO, "a", encoding="utf-8") as f:
            if not esiste:
                f.write("data,ticker,periodo,punteggio,prezzo," + ",".join(PESI) + "\n")
            f.write("\n".join(righe) + "\n")
    return len(righe)


FASCE = [(1, 20), (21, 40), (41, 60), (61, 80), (81, 100)]


def verifica(close: pd.DataFrame, ref: pd.Series, registro: pd.DataFrame | None = None) -> dict:
    """«Quanto ha funzionato il punteggio»: per fascia di punteggio, rendimento medio a 1 e 3 mesi (21 e 63 sedute) e % di titoli in rialzo, contro SPY.
    Una riga per data e ticker (periodo più corto). Solo righe già mature."""
    if registro is None:
        if not REGISTRO.exists():
            return {"n": 0}
        registro = pd.read_csv(REGISTRO, parse_dates=["data"])
    r = registro.dropna(subset=["punteggio"]).copy()
    r["ord"] = r["periodo"].map({p: i for i, (p, _) in enumerate(PERIODI)})
    r = r.sort_values("ord").drop_duplicates(["data", "ticker"])
    out = {"n": int(len(r)), "orizzonti": {}}
    idx = close.index
    for nome, h in (("1m", 21), ("3m", 63)):
        righe = []
        for x in r.itertuples():
            if x.ticker not in close:
                continue
            i = idx.searchsorted(pd.Timestamp(x.data))
            if i + h >= len(idx) or idx[i] != pd.Timestamp(x.data):
                continue
            s = close[x.ticker]
            p0, p1 = s.iloc[i], s.iloc[i + h]
            b0, b1 = ref.iloc[i], ref.iloc[i + h]
            if pd.isna(p0) or pd.isna(p1) or pd.isna(b0) or pd.isna(b1):
                continue
            righe.append((x.punteggio, p1 / p0 - 1, b1 / b0 - 1))
        fasce = []
        for lo, hi in FASCE:
            g = [(a, b) for sc, a, b in righe if lo <= sc <= hi]
            fasce.append({"fascia": f"{lo}-{hi}", "n": len(g), "medio": float(np.mean([a for a, _ in g])) if g else None,
                          "su": float(np.mean([a > 0 for a, _ in g])) if g else None, "spy": float(np.mean([b for _, b in g])) if g else None})
        out["orizzonti"][nome] = {"righe": len(righe), "fasce": fasce}
    return out


# ---------------------------------------------------------------- lavoro serale
def arricchisci(tk: list[str], nomi: dict, log=print, giorni_8k: int = 30) -> tuple[dict, dict, dict]:
    """Per un elenco di titoli: indicatori (yfinance con cache 7 giorni + SEC RPO), 8-K recenti e notizie (Google News). Restituisce (ind, ev8k, notizie)."""
    import concurrent.futures as cf

    from . import news

    def uno(t):
        return t, tf.da_yf(t)
    fond = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for t, d in ex.map(uno, tk):
            fond[t] = d
    cik = {}
    try:
        cik = tf.cik_map()
    except Exception as e:  # noqa: BLE001
        log("[sec] non disponibile: " + str(e)[:80])
    ind, ev8k = {}, {}
    for t in tk:
        d = fond.get(t)
        if not d:
            continue
        rpo = None
        c = cik.get(t.upper())
        if c:
            try:
                rpo = tf.rpo_da_facts(tf.sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c}.json") or {})
                ev8k[t] = tf.eventi_8k(tf.sec_json(f"https://data.sec.gov/submissions/CIK{c}.json") or {}, giorni_8k)
            except Exception:  # noqa: BLE001
                pass
        ind[t] = tf.indicatori(d, rpo)

    def notizie_di(t):
        try:
            import requests
            nome = (ind.get(t) or {}).get("nome") or nomi.get(t, t)
            xml = requests.get(news.GOOGLE.format(q=f'"{nome}"+stock'), timeout=30, headers=news.UA).text
            return t, news.parse_rss(xml)[:20]
        except Exception:  # noqa: BLE001
            return t, []
    nz = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for t, n_ in ex.map(notizie_di, tk):
            nz[t] = n_
    return ind, ev8k, nz


def aggiorna(log=print) -> dict:
    from . import titoli
    registra_protocollo()
    top = json.loads((DATA / "titoli_top.json").read_text(encoding="utf-8"))
    mm = json.loads((DATA / "mercati_mondo.json").read_text(encoding="utf-8")) if (DATA / "mercati_mondo.json").exists() else {"items": []}
    cls = candidati(top)
    tk = sorted({t for l in cls.values() for t in l})
    log(f"[saldi] candidati: {len(tk)} titoli")
    ind, ev8k, nz = arricchisci(tk, {i["t"]: i["n"] for i in top["items"]}, log)
    etf = [i for i in mm.get("items", []) if i["c"] == "etf"]
    rs = {}
    for i in mm.get("items", []):
        if i["c"] == "settori" and i["t"] in ETF_SETTORE.values():
            rs[i["t"]] = {"1g": i["r"][0], "1s": i["r"][1], "1m": i["r"][2], "3m": i["r"][3], "6m": i["r"][4]}
    d = costruisci(top, ind, nz, etf, rs, mm.get("eurusd"), eventi_8k=ev8k)
    FILE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=lambda o: None), encoding="utf-8")
    log(f"[saldi] scritto {FILE.name}: {len(d['titoli'])} titoli; registro +{registra(d, d['asof'])}")
    try:
        arch = titoli.carica_prezzi()
        if arch is not None and "SPY" in arch["close"]:
            VERIFICA.write_text(json.dumps(verifica(arch["close"], arch["close"]["SPY"])), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log("[saldi] verifica non calcolata: " + str(e)[:80])
    return d


# ---------------------------------------------------------------- pagina
def carica() -> str | None:
    return FILE.read_text(encoding="utf-8") if FILE.exists() else None


def tabella_verifica() -> str:
    try:
        v = json.loads(VERIFICA.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "<p class='mu'>Il registro è appena partito: la tabella «Quanto ha funzionato il punteggio» compare quando i primi titoli hanno 1 mese di storia.</p>"
    if not v.get("orizzonti"):
        return "<p class='mu'>Nessuna riga matura.</p>"
    h = ""
    for nome, o in v["orizzonti"].items():
        if not o["righe"]:
            continue
        h += (f"<h4>Dopo {'1 mese' if nome == '1m' else '3 mesi'} ({o['righe']} osservazioni)</h4><div class='scroll'><table class='tbl'><tr><th>Punteggio</th><th>Titoli</th><th>Rendimento medio</th><th>In rialzo</th><th>S&amp;P 500 (stessi giorni)</th></tr>"
              + "".join(f"<tr><td>{f['fascia']}</td><td>{f['n']}</td><td>{_pc(f['medio'], 1)}</td><td>{_pc(f['su'])}</td><td>{_pc(f['spy'], 1)}</td></tr>" for f in o["fasce"] if f["n"]) + "</table></div>")
    return h or "<p class='mu'>Nessuna riga matura.</p>"


CSS = """<style>.sdw{margin-top:8px}.sdc{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.sdc button,.sdc select{padding:8px 13px;border:1px solid var(--bd);border-radius:99px;background:var(--card);color:var(--tx);font-weight:600;font-size:14px;cursor:pointer}
.sdc button.on{background:var(--ac);color:#fff;border-color:var(--ac)}.sdl{display:grid;gap:8px}.sdr{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;cursor:pointer}
.sdr .top{display:flex;justify-content:space-between;gap:8px;align-items:center}.sdr .nm{font-weight:700;overflow:hidden;text-overflow:ellipsis}.sdr .tk{color:var(--mu);font-size:12px;font-weight:400}
.sdr .pc{font-weight:800;color:var(--bad);font-size:18px;white-space:nowrap}.sdr .met{display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--mu);margin-top:4px}.sdr .met b{color:var(--tx)}
.sds{display:inline-block;min-width:34px;text-align:center;border-radius:8px;padding:2px 7px;color:#fff;font-weight:800;font-size:13px}.sdd{margin-top:10px;border-top:1px solid var(--bd);padding-top:10px;cursor:default}
.sdd h4{margin:10px 0 4px}.sdd p{margin:4px 0;font-size:14px}.sdk{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:4px 12px;font-size:13px}.sdk div{display:flex;justify-content:space-between;border-bottom:1px dotted var(--bd)}
.sdb{height:8px;background:var(--bd);border-radius:4px;margin:2px 0 6px;overflow:hidden}.sdb i{display:block;height:100%}.sdn a{color:var(--ac)}.sdn div{margin:5px 0;font-size:13px}.etq{font-size:11px;border-radius:99px;padding:1px 8px;background:var(--bd)}</style>"""

IND_INFO = {
    "ps": ("P/S", "Capitalizzazione divisa per i ricavi degli ultimi 12 mesi.", "Più basso = si paga meno ogni euro di fatturato. Va confrontato con quello del settore."),
    "pe": ("P/E", "Capitalizzazione divisa per l'utile degli ultimi 12 mesi (solo se positivo).", "Quanti anni di utili attuali servono per ripagare il prezzo."),
    "ps_f": ("P/S previsto", "Capitalizzazione divisa per i ricavi attesi a 12 mesi (media degli analisti).", "Se è molto più basso del P/S attuale, gli analisti si aspettano ricavi in crescita."),
    "pe_f": ("P/E previsto", "Capitalizzazione divisa per l'utile atteso.", "Come il P/E ma sulle stime degli analisti."),
    "ev_ebitda": ("EV/EBITDA", "Valore dell'impresa (capitalizzazione più debito netto) diviso per il margine operativo lordo.", "Confronta imprese con debito diverso."),
    "piotroski": ("F-score (0-9)", "9 verifiche sui bilanci: utile, cassa, leva, margini, azioni emesse.", "Da 7 in su = bilancio solido; 3 o meno = fragile."),
    "altman": ("Altman Z", "Misura di rischio di dissesto da 5 rapporti di bilancio.", "Sotto 1,8 (o 1,1 per i non manifatturieri) = zona critica; sopra 3 (2,6) = sicura."),
    "debito_netto_ebitda": ("Debito netto / EBITDA", "Anni di margine operativo lordo necessari a ripagare il debito netto.", "Sopra 4 è un debito pesante."),
    "mesi_cassa": ("Mesi di cassa", "Per chi perde soldi: quanti mesi basta la liquidità al ritmo di consumo dell'ultimo trimestre.", "Sotto 6 mesi = l'azienda dovrà probabilmente finanziarsi."),
    "diluizione": ("Diluizione", "Aumento delle azioni in circolazione in un anno.", "Più azioni = ogni azione vale una quota minore."),
    "rpo_anni": ("Anni di fatturato già firmati", "Contratti firmati non ancora fatturati (RPO, dai bilanci SEC) divisi per i ricavi annui.", "Sopra 1 = lavoro già in portafoglio per oltre un anno."),
    "margine_lordo": ("Margine lordo", "Quota dei ricavi che resta dopo i costi diretti.", "Più alto e stabile = più potere di prezzo."),
    "margine_fcf": ("Margine di cassa libera", "Cassa libera diviso ricavi.", "Negativo = l'azienda brucia cassa."),
    "roe": ("ROE", "Utile diviso per il patrimonio netto.", "Quanto rende il capitale degli azionisti."),
    "current_ratio": ("Current ratio", "Attività a breve diviso passività a breve.", "Sotto 1 = possibili tensioni di liquidità."),
    "copertura_interessi": ("Copertura interessi", "Utile operativo diviso interessi pagati.", "Sotto 2 = gli interessi pesano molto."),
}

JS = r"""<script>(function(){var W=document.querySelector('[data-sd]');if(!W||W.dataset.on)return;W.dataset.on=1;
var D=null,PER='1g',TIPO='Azione',AREA='',DIM='',SET='',ORD='r',OPEN=null,INFO=JSON.parse(W.getAttribute('data-ii')||'{}');
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function pc(x,d){if(x==null)return '—';var s=(x*100).toFixed(d==null?1:d).replace('.',',');return (x>0?'+':'')+s+'%'}
function nm(x,d){return x==null?'—':Number(x).toFixed(d==null?1:d).replace('.',',')}
function col(s){if(s==null)return '#64748b';return s>=70?'#16a34a':s>=40?'#d97706':'#dc2626'}
function lista(){var ids=(TIPO==='ETF'?D.etf_classifiche:D.classifiche)[PER]||[],src=TIPO==='ETF'?D.etf:D.titoli;var a=ids.map(function(t){return src[t]}).filter(Boolean);
a=a.filter(function(x){return (!AREA||x.area===AREA)&&(!DIM||x.dim===DIM)&&(!SET||x.sett===SET)});
if(ORD==='s')a.sort(function(p,q){return (q.s==null?-1:q.s)-(p.s==null?-1:p.s)});else a.sort(function(p,q){return p.r[PER]-q.r[PER]});return a}
function info(k,v){var i=INFO[k];if(!i)return '';return '<em class="aii" data-info="'+esc(JSON.stringify({t:i[0],s:[['Cos\'è',i[1]],['Come si legge',i[2]]]}))+'">i</em>'}
function spark(k,w,h){if(!k||k.length<2)return '';var mn=Math.min.apply(null,k),mx=Math.max.apply(null,k),r=mx-mn||1;return '<svg viewBox="0 0 '+w+' '+h+'" style="width:100%;max-width:520px;height:'+h+'px"><polyline fill="none" stroke="#3b82f6" stroke-width="2" points="'+k.map(function(v,i){return (i*(w-2)/(k.length-1)+1).toFixed(1)+','+((h-4)-(v-mn)/r*(h-8)+2).toFixed(1)}).join(' ')+'"/></svg>'}
function det(t){var x=D.titoli[t],d=D.dett[t];if(!d)return '';var r=d.report,I=d.ind,h='<div class="sdd" onclick="event.stopPropagation()">';
h+='<h4>Ultimi 6 mesi</h4>'+spark(x.k,520,110);
if(x.comp){h+='<h4>Salute e probabilità di recupero stimate: '+(x.s==null?'—':x.s+'/100')+' <span class="mu" style="font-weight:400">(dati usati: '+x.usati+' componenti su 5)</span></h4>';Object.keys(D.pesi).forEach(function(n,i){var k=['solidita','qualita','calo','valutazione','fiducia'][i],v=x.comp[k];h+='<div style="font-size:12px">'+n+' ('+Math.round(D.pesi[n]*100)+'%): <b>'+(v==null?'dati insufficienti':v+'/100')+'</b></div><div class="sdb"><i style="width:'+(v||0)+'%;background:'+col(v)+'"></i></div>'});
if(x.tetti&&x.tetti.length)h+='<p class="neg">Punteggio limitato a 15: '+esc(x.tetti.join('; '))+'</p>'}
h+='<h4>Perché è sceso</h4><p>'+esc(r.perche)+'</p><h4>Come sta l\'azienda</h4><p>'+esc(r.salute)+'</p><h4>Perché potrebbe essere acquistabile</h4><p>'+esc(r.favorevole)+'</p><h4>Rischi principali</h4><p>'+esc(r.rischi)+'</p>';
var ks=[['ps','P/S',2],['pe','P/E',1],['ps_f','P/S previsto',2],['pe_f','P/E previsto',1],['ev_ebitda','EV/EBITDA',1],['piotroski','F-score',0],['altman','Altman Z',2],['debito_netto_ebitda','Debito netto / EBITDA',1],['mesi_cassa','Mesi di cassa',0],['diluizione','Diluizione',3],['rpo_anni','Anni di fatturato firmati',1],['margine_lordo','Margine lordo',3],['margine_fcf','Margine cassa libera',3],['roe','ROE',3],['current_ratio','Current ratio',2],['copertura_interessi','Copertura interessi',1]];
h+='<h4>Indicatori</h4><div class="sdk">'+ks.filter(function(k){return I[k[0]]!=null}).map(function(k){var v=I[k[0]];return '<div><span>'+k[1]+info(k[0])+'</span><b>'+nm(k[2]>=3?v*100:v,k[2]>=3?1:k[2])+(k[2]>=3?'%':'')+'</b></div>'}).join('')+'</div>';
if(d.notizie.length)h+='<h4>Notizie che spiegano il calo</h4><div class="sdn">'+d.notizie.map(function(n){return '<div>'+esc(n.d.slice(8)+'/'+n.d.slice(5,7))+' · <span class="etq">'+esc(n.e)+'</span> <a href="'+esc(n.l||'#')+'" target="_blank" rel="noopener">'+esc(n.t)+'</a> <span class="mu">'+esc(n.f||'')+'</span></div>'}).join('')+'</div>';
return h+'<p class="mu">'+esc(r.nota)+'</p></div>'}
function riga(x){var r=x.r[PER],s=x.s,eur=x.eur!=null?' · '+nm(x.eur,2)+' €':'';
var h='<div class="sdr" data-t="'+esc(x.t)+'"><div class="top"><span class="nm">'+esc(x.n)+' <span class="tk">'+esc(x.t)+(x.sett?' · '+esc(x.sett):'')+'</span></span><span class="pc">'+pc(r)+'</span></div><div class="met">';
h+='<span>Prezzo <b>'+nm(x.p,2)+' '+(x.v==='EUR'?'€':x.v)+'</b>'+eur+'</span>';
if(x.tipo==='Azione'){h+='<span>Fatturato trim. <b>'+(x.ric?x.ric.f+' '+pc(Math.abs(x.ric.v),0):'—')+'</b></span><span>P/S <b>'+nm(x.ps,1)+'</b></span><span>P/E <b>'+nm(x.pe,1)+'</b></span><span>P/S prev. <b>'+nm(x.ps_f,1)+'</b></span><span>Deb./EBITDA <b>'+nm(x.leva,1)+'</b></span>'+(x.cassa!=null?'<span>Cassa <b>'+x.cassa+' mesi</b></span>':'')+'<span>F-score <b>'+(x.fs==null?'—':x.fs)+'</b></span><span class="etq">'+esc(x.causa_t)+'</span><span class="sds" style="background:'+col(s)+'" title="Salute e probabilità di recupero stimate">'+(s==null?'—':s)+'</span>'}
else h+='<span class="etq">ETF</span>';
return h+'</div>'+(OPEN===x.t?det(x.t):'')+'</div>'}
function render(){var a=lista(),src=TIPO==='ETF'?D.etf:D.titoli,sets=Object.keys(D.titoli).map(function(t){return D.titoli[t].sett}).filter(function(v,i,s){return v&&s.indexOf(v)===i}).sort();
var h='<div class="sdc">'+D.periodi.map(function(p){return '<button data-p="'+p[0]+'" class="'+(p[0]===PER?'on':'')+'">'+p[1]+'</button>'}).join('')+'</div>';
h+='<div class="sdc"><button data-tp="Azione" class="'+(TIPO==='Azione'?'on':'')+'">Azioni</button><button data-tp="ETF" class="'+(TIPO==='ETF'?'on':'')+'">ETF</button>'+
'<select id="sda"><option value="">Tutte le aree</option>'+['USA','Europa','Asia','Altri'].map(function(v){return '<option'+(AREA===v?' selected':'')+'>'+v+'</option>'}).join('')+'</select>'+
'<select id="sdd"><option value="">Tutte le dimensioni</option>'+[['grandi','Grandi (> 10 mld)'],['medie','Medie (2-10 mld)'],['piccole','Piccole (< 2 mld)']].map(function(v){return '<option value="'+v[0]+'"'+(DIM===v[0]?' selected':'')+'>'+v[1]+'</option>'}).join('')+'</select>'+
'<select id="sds"><option value="">Tutti i settori</option>'+sets.map(function(v){return '<option'+(SET===v?' selected':'')+'>'+esc(v)+'</option>'}).join('')+'</select>'+
'<select id="sdo"><option value="r"'+(ORD==='r'?' selected':'')+'>Ordina per calo</option><option value="s"'+(ORD==='s'?' selected':'')+'>Ordina per punteggio</option></select></div>';
h+='<p class="mu">Dati al '+D.asof.split('-').reverse().join('/')+'. I punteggi dicono <b>salute e probabilità di recupero stimate</b>, non un rimbalzo sicuro. '+a.length+' risultati. Tocca una scheda per il dettaglio e il report.</p><div class="sdl">'+(a.length?a.map(riga).join(''):'<p class="mu">Nessun risultato con questi filtri.</p>')+'</div>';
W.innerHTML=h;
W.querySelectorAll('[data-p]').forEach(function(b){b.onclick=function(){PER=b.dataset.p;OPEN=null;render()}});W.querySelectorAll('[data-tp]').forEach(function(b){b.onclick=function(){TIPO=b.dataset.tp;OPEN=null;render()}});
W.querySelector('#sda').onchange=function(){AREA=this.value;render()};W.querySelector('#sdd').onchange=function(){DIM=this.value;render()};W.querySelector('#sds').onchange=function(){SET=this.value;render()};W.querySelector('#sdo').onchange=function(){ORD=this.value;render()};
W.querySelectorAll('.sdr').forEach(function(r){r.onclick=function(){var t=r.dataset.t;if(TIPO!=='Azione')return;OPEN=OPEN===t?null:t;render()}})}
function go(j){D=j;if(!D||!D.titoli){W.innerHTML='<p class="mu">Dati non ancora disponibili: si generano con il lavoro serale «Motore titoli».</p>';return}render()}
var emb=document.getElementById('armor-sd-data');if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/saldi.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(go).catch(function(){W.innerHTML='<p class="mu">Saldi non disponibili (serve la connessione, oppure il lavoro serale non è ancora girato).</p>'})}
})();</script>"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-sd-data'>{data_json}</script>" if data_json else ""
    ii = _h.escape(json.dumps(IND_INFO, ensure_ascii=False), quote=True)
    return (f"{CSS}<h2>Saldi: i titoli e gli ETF scesi di più</h2><div class='explain'><p>I 100 più calati per periodo, con fatturato, valutazioni, debito, causa del calo e un punteggio di <b>salute e probabilità di recupero stimate</b> (1-100). "
            "Il punteggio nasce da regole scritte in anticipo e viene verificato sui risultati reali (tabella in fondo). <b>Non è una consulenza finanziaria né un consiglio di acquisto</b>: un titolo sceso può continuare a scendere.</p></div>"
            f"{emb}<div class='sdw' data-sd='1' data-ii='{ii}'></div><h3 style='margin-top:22px'>Quanto ha funzionato il punteggio</h3>{tabella_verifica()}"
            "<p class='mu'>La tabella si riempie col tempo: ogni giorno si registrano i 30 titoli più calati per periodo e si misurano i rendimenti reali a 1 e 3 mesi. Un test storico sui bilanci SEC non è ancora stato fatto.</p>"
            f"{JS}")
