"""«Opportunità»: ogni settimana le 30 aziende con il punteggio Potenziale più alto (PIANO_ESPANSIONE Patch 47).
Fattori e pesi in PROTOCOLLO_OPPORTUNITA.md. Il punteggio ordina i titoli per somiglianza ai fattori che storicamente hanno dato rendimenti migliori:
non è una previsione. Le fasce di crescita sono fasce di incertezza, non promesse. Lo storico delle settimane si mostra anche quando è negativo."""
import hashlib
import html as _h
import json

import numpy as np
import pandas as pd

from . import brevetti, saldi
from . import titoli_eventi as ev
from .config import DATA, ROOT

FILE = DATA / "opportunita.json"
REGISTRO = DATA / "opportunita_registro.csv"
LOG = DATA / "protocollo_opportunita_log.csv"
RICOSTRUITO = DATA / "opportunita_ricostruito.csv"   # settimane ricostruite (prezzi di allora, bilanci di oggi): non entrano nel riepilogo
PESI = {"revisioni": 0.20, "momentum": 0.15, "crescita": 0.15, "qualita": 0.15, "sorpresa": 0.10, "contratti": 0.10, "catalizzatori": 0.10, "valutazione": 0.05}
NOMI = {"revisioni": "Revisioni delle stime", "momentum": "Momentum", "crescita": "Crescita", "qualita": "Qualità", "sorpresa": "Sorpresa e deriva",
        "contratti": "Contratti e visibilità", "catalizzatori": "Catalizzatori e temi", "valutazione": "Valutazione ragionevole"}
ORIZZONTI = [("1m", 21, 1 / 12), ("3m", 63, 0.25), ("1a", 252, 1.0), ("2a", 504, 2.0)]
CENTRO_ANNUO = 0.07      # ipotesi dichiarata: rendimento mediano annuo del mercato azionario, finché non c'è storico reale
Z80 = 1.2816
MIN_CAP, MIN_CONTROVALORE, MIN_ANALISTI = 300e6, 1e6, 3
VERSO = {"rev30": True, "rev90": True, "revsg": True, "mom": True, "dd52": True, "crescita": True, "qoq": True, "regola40": True,
         "gross": True, "roe": True, "accruals": False, "fscore": True, "sue": True, "rpo_anni": True, "rpo_cap": True, "n101": True, "ctr": True,
         "cataliz": True, "tema": True, "psg": False}
FATTORI = {"revisioni": ("rev30", "rev90", "revsg"), "momentum": ("mom", "dd52"), "crescita": ("crescita", "qoq", "regola40"), "qualita": ("gross", "roe", "accruals", "fscore"),
           "sorpresa": ("sue",), "contratti": ("rpo_anni", "rpo_cap", "n101", "ctr"), "catalizzatori": ("cataliz", "tema"), "valutazione": ("psg",)}
PDUFA = ev.PDUFA
BREVETTI: dict = {}   # ticker → brevetti ultimi 12 mesi (data/brevetti.json), caricato da aggiorna()


# ---------------------------------------------------------------- protocollo
def protocollo_hash() -> str:
    f = ROOT / "PROTOCOLLO_OPPORTUNITA.md"
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


# ---------------------------------------------------------------- fattori
def voci(ind: dict, m: dict, eventi: list[dict], ev8k: list[dict], tema_forza: float | None) -> dict:
    """Voci numeriche (più alto = meglio, tranne dove VERSO dice il contrario) di un titolo; mancanti = None."""
    rpo = ind.get("rpo") or {}
    cap = ind.get("cap")
    ctr = [e["pct_fatturato"] for e in eventi if e.get("evento") == "contratto" and e.get("pct_fatturato")]
    pos = [e for e in eventi if isinstance(e.get("opp"), int) and e["opp"] > 0]
    crescita = ind.get("crescita_ricavi")
    sue = (ind.get("sue") or {}).get("sue")
    rs = (ind.get("rev_su") or 0) - (ind.get("rev_giu") or 0)
    tot = (ind.get("rev_su") or 0) + (ind.get("rev_giu") or 0)
    ps_f = ind.get("ps_f")
    return {
        "rev30": ind.get("rev_eps_30"), "rev90": ind.get("rev_eps_90"), "revsg": (rs / tot) if tot else None,
        "mom": m.get("mom12_1"), "dd52": m.get("dd52"),
        "crescita": crescita, "qoq": (ind.get("ricavi_q_prec") or {}).get("var"),
        "regola40": (crescita + ind["margine_fcf"]) if ind.get("sw") and crescita is not None and ind.get("margine_fcf") is not None else None,
        "gross": ind.get("gross_su_attivo"), "roe": ind.get("roe"), "accruals": ind.get("accruals"), "fscore": (ind.get("piotroski") or {}).get("score"),
        "sue": sue, "rpo_anni": ind.get("rpo_anni") if rpo else None, "rpo_cap": (rpo["rpo"] / cap) if rpo and cap else None,
        "n101": sum(1 for e in (ev8k or []) if e["item"] == "1.01"), "ctr": max(ctr) if ctr else None,
        "cataliz": float(min(sum(e["opp"] for e in pos), 4)) if eventi or pos else 0.0, "tema": tema_forza,
        "psg": (ps_f / (crescita * 100)) if ps_f and crescita and crescita > 0.02 else None,
    }


def punteggi(cand: dict[str, dict]) -> dict[str, dict]:
    """cand: ticker → {voci, area, settore}. Percentili nel gruppo area+settore (≥ 8 titoli) o nell'insieme. Servono ≥ 4 fattori su 8."""
    gruppi: dict[tuple, list[str]] = {}
    for t, c in cand.items():
        gruppi.setdefault((c.get("area"), c.get("settore")), []).append(t)
    pool_all = {k: [c["voci"][k] for c in cand.values()] for k in VERSO}
    out = {}
    for t, c in cand.items():
        g = gruppi[(c.get("area"), c.get("settore"))]
        comp = {}
        for f, chiavi in FATTORI.items():
            ps = []
            for k in chiavi:
                v = c["voci"].get(k)
                if v is None:
                    continue
                ref = [cand[x]["voci"][k] for x in g] if len(g) >= 8 else pool_all[k]
                p = saldi.percentile(v, ref, VERSO[k])
                if p is not None:
                    ps.append(p)
            comp[f] = float(np.mean(ps) * 100) if ps else None
        disp = {k: v for k, v in comp.items() if v is not None}
        raw = None
        if len(disp) >= 4:
            raw = sum(PESI[k] * v for k, v in disp.items()) / sum(PESI[k] for k in disp)
        out[t] = {"raw": raw, "comp": {k: (None if v is None else round(v)) for k, v in comp.items()}, "usati": len(disp)}
    raws = np.array([o["raw"] for o in out.values() if o["raw"] is not None])
    for o in out.values():
        o["score"] = None if o["raw"] is None else int(round(1 + 99 * float((raws < o["raw"]).mean() + 0.5 * (raws == o["raw"]).mean())))
    return out


# ---------------------------------------------------------------- fasce di crescita
def fascia(vol: float | None, t: float, centro: float | None = None) -> dict | None:
    """Mediana e fascia 10-90 (lognormale): centro = rendimento mediano a orizzonte t (se noto dallo storico), altrimenti CENTRO_ANNUO."""
    if vol is None or not np.isfinite(vol) or vol <= 0:
        return None
    mu = np.log(1 + (centro if centro is not None else (1 + CENTRO_ANNUO) ** t - 1))
    s = vol * np.sqrt(t)
    return {"med": float(np.exp(mu) - 1), "lo": float(np.exp(mu - Z80 * s) - 1), "hi": float(np.exp(mu + Z80 * s) - 1), "storico": centro is not None}


def testo_fascia(f: dict | None) -> str:
    """«mediana +8% · 8 casi su 10 tra −15% e +35%»; sopra +100% il limite alto è in multipli, sempre insieme al limite basso."""
    if not f:
        return "—"
    def pc(x):
        return f"{x * 100:+.0f}%".replace("-", "−")
    hi = f"×{1 + f['hi']:.1f}".replace(".", ",") if f["hi"] > 1.0 else pc(f["hi"])
    return f"mediana {pc(f['med'])} · 8 casi su 10 tra {pc(f['lo'])} e {hi}"


def vol_titolo(close: pd.Series) -> float | None:
    lr = np.log(close.dropna()).diff().dropna()
    if len(lr) < 60:
        return None
    v63, v252 = lr.iloc[-63:].std() * np.sqrt(252), lr.iloc[-252:].std() * np.sqrt(252)
    return float((v63 + v252) / 2)


# ---------------------------------------------------------------- motivi, catalizzatori, report
def motivi(c: dict, s: dict, nome_tema: str | None) -> list[str]:
    """I tre motivi principali: tra quelli con un fatto vero da citare, i dei fattori con percentile più alto."""
    v, ind, comp = c["voci"], c["ind"], s["comp"]
    cand = []

    def add(f, testo):
        if comp.get(f) is not None:
            cand.append((comp[f], testo))
    if v["rev30"] is not None and v["rev30"] >= 0.03:
        add("revisioni", f"stime sull'utile alzate del {v['rev30'] * 100:.0f}% in 30 giorni".replace(".", ","))
    ctr = [e for e in c.get("eventi", []) if e.get("evento") == "contratto" and e.get("importo")]
    if ctr:
        e = ctr[0]
        add("contratti", f"contratto da {saldi._mld(e['importo'])}" + (f" = {e['pct_fatturato'] * 100:.0f}% del fatturato annuo" if e.get("pct_fatturato") else "") + f" ({e['data'][8:]}/{e['data'][5:7]})")
    if v["rpo_anni"] is not None and v["rpo_anni"] >= 1:
        add("contratti", f"contratti già firmati pari a {saldi._v(v['rpo_anni'])} anni di fatturato")
    if nome_tema and (v["tema"] or 0) >= 55:
        add("catalizzatori", f"tema «{nome_tema}» in accelerazione (forza {v['tema']:.0f}/100)")
    pos = [e for e in c.get("eventi", []) if isinstance(e.get("opp"), int) and e["opp"] > 0 and e["evento"] != "contratto"]
    if pos:
        add("catalizzatori", f"{pos[0]['etichetta'].lower()} ({pos[0]['data'][8:]}/{pos[0]['data'][5:7]})")
    if v["crescita"] is not None and v["crescita"] >= 0.15:
        add("crescita", f"fatturato in crescita del {v['crescita'] * 100:.0f}% sull'anno".replace(".", ","))
    if v["mom"] is not None and v["mom"] >= 0.25 and (v["dd52"] or -1) > -0.1:
        add("momentum", f"a ridosso dei massimi a 52 settimane, {v['mom'] * 100:+.0f}% a 12 mesi (escluso l'ultimo mese)")
    if v["sue"] is not None and v["sue"] >= 1:
        add("sorpresa", "ultima trimestrale sopra le attese")
    if ind.get("insider_acq_90g"):
        add("qualita", "acquisti di azioni da parte dei dirigenti negli ultimi 90 giorni")
    fr = brevetti.frase(ind.get("brevetti"), ind.get("rd_cap"))
    if fr and (ind["brevetti"].get("crescita") or 0) >= 0.3:
        cand.append((65, fr))
    cand.sort(key=lambda x: -x[0])
    return [t for _, t in cand[:3]]


def catalizzatori(c: dict, oggi: str, studi: list[dict] | None = None) -> list[dict]:
    out = []
    pt = c["ind"].get("prossima_trimestrale")
    if pt:
        try:
            gg = (np.datetime64(pt[:10]) - np.datetime64(oggi)).astype(int)
            if 0 <= gg <= 60:
                out.append({"data": pt[:10], "t": "Prossima trimestrale"})
        except ValueError:
            pass
    for n in c.get("notizie", []):
        m = PDUFA.search((n.get("title") or "") + " " + (n.get("summary") or ""))
        if m:
            out.append({"data": m.group(1), "t": "Data PDUFA (decisione FDA) citata nelle notizie"})
            break
    for s in studi or []:
        out.append({"data": s["data"], "t": f"Fine primaria studio fase {s['fase']} ({s['id']})"})
    return out[:4]


def report(t: dict, c: dict, s: dict, mot: list[str]) -> dict:
    ind, v = c["ind"], c["voci"]
    perche = []
    if mot:
        perche.append("Ecco perché emerge questa settimana: " + "; ".join(mot) + ".")
    top = sorted([(x, NOMI[k]) for k, x in s["comp"].items() if x is not None], reverse=True)[:3]
    if top:
        perche.append("I fattori dove è più forte: " + ", ".join(f"{n} ({x}/100)" for x, n in top) + ".")
    fr = brevetti.frase(ind.get("brevetti"), ind.get("rd_cap"))
    if fr:
        perche.append("Innovazione: " + fr + ".")
    elif ind.get("rd_cap"):
        perche.append(f"Spende in ricerca e sviluppo il {ind['rd_cap'] * 100:.1f}% del proprio valore di Borsa all'anno.".replace(".", ","))
    if ind.get("ricavi_q_1a"):
        perche.append(f"Fatturato dell'ultimo trimestre {ind['ricavi_q_1a']['f']} {saldi._pc(abs(ind['ricavi_q_1a']['var']), 1)} sull'anno prima.")
    storto = []
    if v["psg"] is not None and s["comp"].get("valutazione") is not None and s["comp"]["valutazione"] < 30:
        storto.append("La valutazione è alta rispetto alla crescita: se la crescita delude, il prezzo può scendere molto.")
    if (v["dd52"] or 0) > -0.03 and (v["mom"] or 0) > 0.5:
        storto.append("Il titolo è già salito molto: il momentum può invertirsi.")
    if (ind.get("diluizione") or 0) > 0.05:
        storto.append(f"Le azioni in circolazione sono aumentate del {saldi._pc(ind['diluizione'])} in un anno (diluizione).")
    if ind.get("debito_netto_ebitda") is not None and ind["debito_netto_ebitda"] > 4:
        storto.append(f"Debito alto: {saldi._v(ind['debito_netto_ebitda'])} volte il margine operativo lordo.")
    if ind.get("mesi_cassa") is not None:
        storto.append(f"L'azienda perde cassa: liquidità per circa {ind['mesi_cassa']:.0f} mesi.")
    if ind.get("rischio_binario"):
        storto.append(ind["rischio_binario"]["testo"])
    if ind.get("short_float") and ind["short_float"] > 0.12:
        storto.append(f"Molte vendite allo scoperto ({saldi._pc(ind['short_float'])} dei titoli liberi).")
    storto.append("Un punteggio alto non è una previsione: i titoli scelti possono comunque scendere, e le fasce di crescita indicano quanto è ampia l'incertezza.")
    return {"promettente": " ".join(perche) or "Dati insufficienti per un commento.", "storto": " ".join(storto), "nota": "Non è una consulenza: è una sintesi automatica di dati pubblici."}


# ---------------------------------------------------------------- costruzione
def costruisci(cand: dict, prezzi: dict, vol: dict, temi: list[dict], oggi: str, settimana: str, centri: dict | None = None, eurusd: float | None = None, studi: dict | None = None, n: int = 30) -> dict:
    """cand: ticker → {ind, voci, area, settore, eventi, notizie, tema?, nome_tema?, esclusa?}; prezzi: ticker → {p, v, r7, r1m, k}; vol: ticker → volatilità annua."""
    ok = {t: c for t, c in cand.items() if not c.get("esclusa")}
    pt = punteggi(ok)
    ordine = sorted([t for t in ok if pt[t]["score"] is not None], key=lambda t: (-pt[t]["score"], -(pt[t]["raw"] or 0)))[:n]
    centri = centri or {}
    righe, dett = {}, {}
    for t in ordine:
        c, s, pz = ok[t], pt[t], prezzi[t]
        ind = c["ind"]
        mot = motivi(c, s, c.get("nome_tema"))
        bande = {h: fascia(vol.get(t), tt, centri.get(h)) for h, _, tt in ORIZZONTI}
        an = ind.get("analisti") or {}
        righe[t] = {"n": ind.get("nome") or t, "t": t, "area": c["area"], "dim": saldi.dimensione(ind.get("cap")), "sett": saldi.SETTORE_IT.get(c.get("settore") or "", c.get("settore") or "n/d"),
                    "v": pz["v"], "p": pz["p"], "eur": None if not eurusd or pz["v"] != "USD" else round(pz["p"] / eurusd, 2), "r7": pz.get("r7"), "r1m": pz.get("r1m"),
                    "ric": None if not ind.get("ricavi_q_1a") else {"f": ind["ricavi_q_1a"]["f"], "v": ind["ricavi_q_1a"]["var"]}, "ps": ind.get("ps"), "pe": ind.get("pe"), "ps_f": ind.get("ps_f"),
                    "cap_rpo": ind.get("cap_rpo"), "s": s["score"], "comp": s["comp"], "usati": s["usati"], "mot": mot, "k": pz.get("k"),
                    "fasce": {h: ({**b, "txt": testo_fascia(b)} if b else None) for h, b in bande.items()},
                    "an": {"target": an.get("target"), "min": an.get("target_min"), "max": an.get("target_max"), "n": an.get("n")}}
        rp = report({"prezzo": pz["p"]}, c, s, mot)
        dett[t] = {"report": rp, "cataliz": catalizzatori(c, oggi, (studi or {}).get(t)),
                   "notizie": [{"d": e["data"], "t": e["titolo"], "l": e.get("link"), "f": e.get("fonte"), "e": e["etichetta"]} for e in c.get("eventi", []) if (e.get("opp") or 0) != 0][:5],
                   "ind": {k: ind.get(k) for k in ("ps", "pe", "ps_f", "pe_f", "ev_ebitda", "cap_rpo", "rpo_anni", "margine_lordo", "margine_fcf", "roe", "current_ratio", "debito_netto_ebitda",
                                                   "diluizione", "rev_eps_30", "rev_eps_90", "short_float", "insider_acq_90g", "crescita_ricavi", "rd_cap", "rd_ricavi", "rd_crescita", "brevetti")}
                   | {"piotroski": (ind.get("piotroski") or {}).get("score"), "altman": (ind.get("altman") or {}).get("z"), "tema": c.get("nome_tema")}}
    return {"asof": oggi, "settimana": settimana, "ordine": ordine, "titoli": righe, "dett": dett, "temi": temi, "pesi": {NOMI[k]: v for k, v in PESI.items()},
            "centro_annuo": CENTRO_ANNUO, "centri_reali": centri, "protocollo": protocollo_hash()}


# ---------------------------------------------------------------- registro e storico
def registra(d: dict, settimana: str, file=None) -> int:
    _f = file or REGISTRO
    esiste = _f.exists() and _f.stat().st_size > 0
    gia = {tuple(r.split(",")[:2]) for r in _f.read_text(encoding="utf-8").splitlines()[1:]} if esiste else set()
    righe = []
    for t in d["ordine"]:
        if (settimana, t) in gia:
            continue
        x = d["titoli"][t]
        f = x["fasce"]

        def g(h, k):
            return "" if not f.get(h) else f"{f[h][k]:.4f}"
        righe.append(",".join([settimana, t, str(x["s"]), str(x["p"])] + [g(h, k) for h in ("1m", "3m") for k in ("med", "lo", "hi")]))
    if righe:
        with open(_f, "a", encoding="utf-8") as fh:
            if not esiste:
                fh.write("data,ticker,punteggio,prezzo,m1_med,m1_lo,m1_hi,m3_med,m3_lo,m3_hi\n")
            fh.write("\n".join(righe) + "\n")
    if righe:   # i punteggi dei singoli fattori, per poter capire in seguito quali funzionano davvero (file separato: non cambia il registro)
        ff = _f.with_name(_f.stem + "_fattori.csv")
        nuovo = not (ff.exists() and ff.stat().st_size > 0)
        with open(ff, "a", encoding="utf-8") as fh:
            if nuovo:
                fh.write("data,ticker,fattore,valore\n")
            for t in d["ordine"]:
                if any(r.startswith(f"{settimana},{t},") for r in righe):
                    for k, v in (d["titoli"][t].get("comp") or {}).items():
                        fh.write(f"{settimana},{t},{str(k).replace(',', ' ')},{'' if v is None else v}\n")
    return len(righe)


def storico(close: pd.DataFrame, vt: pd.Series, spy: pd.Series | None = None, registro: pd.DataFrame | None = None) -> dict:
    """Per settimana: previsto (mediana e fascia) e risultato reale a 1 e 3 mesi (21 e 63 sedute). Riepilogo contro VT (MSCI World) e S&P 500 e copertura della fascia 10-90."""
    if registro is None:
        parti = []
        for ric, f in ((False, REGISTRO), (True, RICOSTRUITO)):
            if f.exists() and f.stat().st_size > 0:
                x = pd.read_csv(f, parse_dates=["data"])
                x["ric"] = ric
                parti.append(x)
        if not parti:
            return {"settimane": [], "riepilogo": {}}
        registro = pd.concat(parti)
        reali = set(registro.loc[~registro["ric"], "data"])
        registro = registro[~(registro["ric"] & registro["data"].isin(reali))]
    if "ric" not in registro:
        registro = registro.assign(ric=False)
    idx = close.index
    sett, accum = [], {"1m": [], "3m": []}
    for data, g in registro.groupby("data"):
        i = idx.searchsorted(pd.Timestamp(data))
        ric = bool(g["ric"].iloc[0])
        riga = {"data": str(pd.Timestamp(data).date()), "ric": ric, "scelte": []}
        for x in g.itertuples():
            sc = {"t": x.ticker, "s": int(x.punteggio), "p": float(x.prezzo)}
            for h, off, pre in (("1m", 21, "m1"), ("3m", 63, "m3")):
                prev = {"med": getattr(x, pre + "_med"), "lo": getattr(x, pre + "_lo"), "hi": getattr(x, pre + "_hi")}
                sc[h] = {"prev": {k: (None if pd.isna(v) else float(v)) for k, v in prev.items()}, "reale": None}
                if x.ticker in close and i + off < len(idx) and idx[min(i, len(idx) - 1)] >= pd.Timestamp(data) - pd.Timedelta(days=4):
                    s = close[x.ticker]
                    p0, p1 = s.iloc[i], s.iloc[i + off]
                    if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                        r = float(p1 / p0 - 1)
                        b = float(vt.iloc[i + off] / vt.iloc[i] - 1) if pd.notna(vt.iloc[i]) and pd.notna(vt.iloc[i + off]) else None
                        sc[h]["reale"], sc[h]["vt"] = r, b
                        if not ric:
                            accum[h].append((r, b, sc[h]["prev"]))
            riga["scelte"].append(sc)
        sett.append(riga)
    riep = {}
    for h, lista in accum.items():
        if not lista:
            continue
        rs = np.array([a for a, _, _ in lista])
        con_b = [(a, b) for a, b, _ in lista if b is not None]
        dentro = [p["lo"] <= a <= p["hi"] for a, _, p in lista if p["lo"] is not None and p["hi"] is not None]
        riep[h] = {"n": len(lista), "medio": float(rs.mean()), "vt": float(np.mean([b for _, b in con_b])) if con_b else None,
                   "batte_vt": float(np.mean([a > b for a, b in con_b])) if con_b else None, "dentro_fascia": float(np.mean(dentro)) if dentro else None,
                   "sopra_mediana": float(np.mean([a >= p["med"] for a, _, p in lista if p["med"] is not None])) if lista else None,
                   "mediana": float(np.median(rs))}
    return {"settimane": sett[-26:], "riepilogo": riep}


def centri_reali(riep: dict, minimo: int = 30) -> dict:
    """Mediana reale delle scelte passate, per orizzonte, solo se almeno `minimo` scelte sono maturate; altrimenti nessun centro (vale l'ipotesi dichiarata)."""
    return {h: r["mediana"] for h, r in (riep or {}).items() if r["n"] >= minimo}


# ---------------------------------------------------------------- temi
def forza_temi(ret_etf: dict, gdelt=ev.gdelt_volumi) -> list[dict]:
    """Forza di ogni tema (45.7): accelerazione delle notizie GDELT + forza relativa dell'ETF a 1 e 3 mesi contro VT. ret_etf: ticker → {"1m","3m"}."""
    vt = ret_etf.get("VT") or {}
    out = []
    for nome, (_p, etf, _q) in ev.TEMI.items():
        r = ret_etf.get(etf) or {}
        rs1 = None if r.get("1m") is None or vt.get("1m") is None else r["1m"] - vt["1m"]
        rs3 = None if r.get("3m") is None or vt.get("3m") is None else r["3m"] - vt["3m"]
        acc = ev.accelerazione(gdelt(nome))
        out.append({"tema": nome, "etf": etf, **ev.forza_tema(acc, rs1, rs3), "accel": None if acc is None else round(acc, 2)})
    return sorted(out, key=lambda x: -(x["forza"] if x["forza"] is not None else -1))


# ---------------------------------------------------------------- lavoro settimanale
def _prepara(c_all, v_all, dt=None):
    """Prezzi fino alla seduta `dt` (o all'ultima), metriche con i filtri di liquidità e la preselezione dei 600 titoli per momentum."""
    from . import titoli
    c = c_all if dt is None else c_all[c_all.index <= dt]
    v = v_all.reindex(c.index)
    ref = c["SPY"] if "SPY" in c else None
    cc = c.drop(columns=[x for x in titoli.ausiliari() if x in c])
    m = titoli.metriche(cc, v.reindex(columns=cc.columns), ref)
    m = m[(m["prezzo"] >= titoli.MIN_PREZZO) & (m["controvalore20"] >= MIN_CONTROVALORE) & ~m["anomalo"].astype(bool) & (m["n_giorni"] >= 200)]
    pre = pd.concat([m[k].rank(pct=True) for k in ("mom12_1", "dd52", "r1m", "volrel") if k in m], axis=1).mean(axis=1).sort_values(ascending=False)
    return cc, m, list(pre.index[:600])


def _selezione(cc, m, tk, ind, ev8k, nz, forza, temi, mm, vt, oggi, sab, centri, ev_=ev):
    """Candidati, punteggi e report per le date indicate con i dati fondamentali già raccolti."""
    cand, prezzi, vol = {}, {}, {}
    for t in tk:
        i = ind.get(t)
        if not i or (i.get("cap") or 0) < MIN_CAP:
            continue
        if not ((i.get("analisti") or {}).get("n") or 0) >= MIN_ANALISTI and not i.get("rpo"):
            continue
        rs = ev_.riassumi(nz.get(t, []), i.get("ricavi_ttm"))
        gravi = [e for e in ev8k.get(t, []) if e["item"] in ("1.03", "3.01", "4.02")]
        dil_cassa = any(e["item"] == "DIL" for e in ev8k.get(t, [])) and i.get("mesi_cassa") is not None and i["mesi_cassa"] < 12   # aumento di capitale in arrivo con poca cassa
        tm = [x for x in ev_.temi_di(i.get("descrizione") or "") if forza.get(x) is not None]
        nome_tema = max(tm, key=lambda x: forza[x]) if tm else None
        i = dict(i)
        i["brevetti"] = BREVETTI.get(t)
        i["rischio_binario"] = ev_.rischio_binario(i.get("industria"), i.get("ricavi_ttm"), None)
        cand[t] = {"ind": i, "voci": voci(i, m.loc[t].to_dict(), rs["eventi"], ev8k.get(t, []), forza.get(nome_tema) if nome_tema else None), "area": saldi.area_di(t, i.get("paese")),
                   "settore": i.get("settore"), "eventi": rs["eventi"], "notizie": nz.get(t, []), "nome_tema": nome_tema, "esclusa": rs["escludi"] or bool(gravi) or dil_cassa}
        s = cc[t].dropna()
        prezzi[t] = {"p": round(float(s.iloc[-1]), 2), "v": i.get("valuta") or "USD", "k": [round(float(x), 4 if x < 10 else 2) for x in s.iloc[-126::2].values]}
        prezzi[t].update(_rend(s))
        vol[t] = vol_titolo(s)
    return costruisci(cand, prezzi, vol, temi, oggi, sab, centri, mm.get("eurusd"), {}), cand


def _sabato(ts) -> str:
    return str((pd.Timestamp(ts) + pd.Timedelta(days=(5 - pd.Timestamp(ts).weekday()) % 7)).date())


def aggiorna(log=print) -> dict:
    from . import titoli
    registra_protocollo()
    arch = titoli.carica_prezzi()
    if arch is None:
        log("[opp] archivio prezzi assente: serve prima un giro riuscito di «Motore titoli Armor» (salva la cache dei prezzi). Esco senza errore.")
        raise SystemExit(0)
    c_all, v_all = arch["close"], arch["vol"]
    vt = c_all["VT"] if "VT" in c_all else (c_all["SPY"] if "SPY" in c_all else pd.Series(dtype=float))
    cc, m, tk = _prepara(c_all, v_all)
    oggi = str(cc.dropna(how="all").index[-1].date())
    prec = None
    dt_prec = c_all.index[max(c_all.index.searchsorted(pd.Timestamp(oggi) - pd.Timedelta(days=7), side="right") - 1, 0)]
    try:
        cc_p, m_p, tk_p = _prepara(c_all, v_all, dt_prec)
        prec = (cc_p, m_p, tk_p)
    except Exception as e:  # noqa: BLE001
        log("[opp] settimana scorsa non ricostruibile: " + str(e)[:100])
    union = list(dict.fromkeys(tk + (prec[2] if prec else [])))
    log(f"[opp] preselezionati {len(tk)} titoli su {len(m)} (+ settimana scorsa: {len(union) - len(tk)} in più)")
    top = json.loads((DATA / "titoli_top.json").read_text(encoding="utf-8")) if (DATA / "titoli_top.json").exists() else {"items": []}
    nomi = {i["t"]: i["n"] for i in top["items"]}
    BREVETTI.clear()
    BREVETTI.update(brevetti.carica())
    ind, ev8k, nz = saldi.arricchisci(union, nomi, log, giorni_8k=90, comunicati_max=1)
    mm = json.loads((DATA / "mercati_mondo.json").read_text(encoding="utf-8")) if (DATA / "mercati_mondo.json").exists() else {"items": []}
    ret_etf = {}
    for x in ["VT"] + [v[1] for v in ev.TEMI.values()]:
        if x in c_all:
            ss = c_all[x].dropna()
            if len(ss) > 64:
                ret_etf[x] = {"1m": float(ss.iloc[-1] / ss.iloc[-22] - 1), "3m": float(ss.iloc[-1] / ss.iloc[-64] - 1)}
    temi = forza_temi(ret_etf)
    forza = {x["tema"]: x["forza"] for x in temi}
    sab = _sabato(oggi)
    st = storico(c_all, vt)
    centri = centri_reali(st.get("riepilogo", {}))
    d, cand = _selezione(cc, m, tk, ind, ev8k, nz, forza, temi, mm, vt, oggi, sab, centri)
    log(f"[opp] candidati dopo i filtri: {len(cand)}")
    for t in d["ordine"]:   # catalizzatori biotech: studi di fase 2/3 con fine primaria nei prossimi 6 mesi (solo per i 30 scelti)
        if "biotech" in (cand[t]["ind"].get("industria") or "").lower():
            try:
                import requests
                j = requests.get(ev.clinicaltrials_url(cand[t]["ind"].get("nome") or t), timeout=30).json()
                d["dett"][t]["cataliz"] += [{"data": s_["data"], "t": f"Fine primaria studio fase {s_['fase']} ({s_['id']})"} for s_ in ev.catalizzatori_studi(j, oggi)[:2]]
            except Exception:  # noqa: BLE001
                pass
    if prec:
        try:
            dp, _ = _selezione(prec[0], prec[1], prec[2], ind, ev8k, nz, forza, temi, mm, vt, str(pd.Timestamp(dt_prec).date()), _sabato(dt_prec), centri)
            ult = cc.ffill().iloc[-1]
            for t in dp["ordine"]:
                p0 = dp["titoli"][t]["p"]
                dp["titoli"][t]["da_allora"] = None if t not in ult or pd.isna(ult[t]) or not p0 else round(float(ult[t] / p0 - 1), 4)
            dp["ric"] = True
            d["prec"] = dp
            log(f"[opp] settimana scorsa ({dp['settimana']}) ricostruita: {len(dp['ordine'])} scelte; registro +{registra(dp, dp['settimana'], file=RICOSTRUITO)}")
        except Exception as e:  # noqa: BLE001
            log("[opp] ricostruzione fallita: " + str(e)[:100])
    log(f"[opp] registro +{registra(d, sab)}")
    d["storico"] = storico(c_all, vt)
    FILE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=lambda o: None), encoding="utf-8")
    log(f"[opp] scritto {FILE.name}: {len(d['ordine'])} scelte")
    return d


def _rend(s: pd.Series) -> dict:
    s = s.dropna()
    t1 = s.index[-1]

    def r(giorni):
        x = s[s.index <= t1 - pd.Timedelta(days=giorni)]
        return None if not len(x) else round(float(s.iloc[-1] / x.iloc[-1] - 1), 5)
    return {"r7": r(7), "r1m": r(30)}


def rinfresca(log=print) -> None:
    """Aggiornamento giornaliero (nel lavoro titoli): prezzi e rendimenti delle 30 scelte e storico, senza ricalcolare il punteggio."""
    from . import titoli
    if not FILE.exists():
        return
    d = json.loads(FILE.read_text(encoding="utf-8"))
    arch = titoli.carica_prezzi()
    if not arch or not d.get("ordine"):
        return
    c_all = arch["close"]
    for t in d["ordine"]:
        if t in c_all:
            s = c_all[t].dropna()
            if len(s):
                d["titoli"][t]["p"] = round(float(s.iloc[-1]), 2)
                d["titoli"][t].update({k: v for k, v in _rend(s).items()})
    vt = c_all["VT"] if "VT" in c_all else c_all["SPY"]
    for t in (d.get("prec") or {}).get("ordine", []):
        if t in c_all:
            s_ = c_all[t].dropna()
            p0 = d["prec"]["titoli"][t]["p"]
            if len(s_) and p0:
                d["prec"]["titoli"][t]["da_allora"] = round(float(s_.iloc[-1] / p0 - 1), 4)
    d["storico"] = storico(c_all, vt)
    d["aggiornato"] = str(c_all.dropna(how="all").index[-1].date())
    FILE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=lambda o: None), encoding="utf-8")
    log("[opp] prezzi delle scelte aggiornati")


# ---------------------------------------------------------------- pagina
def carica() -> str | None:
    return FILE.read_text(encoding="utf-8") if FILE.exists() else None


CSS_EXTRA = """<style>.opt{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin:8px 0}.opt div{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:8px 10px;font-size:13px}
.opt b{display:block}.opm{margin:6px 0 0;padding-left:18px;font-size:13px}.opf{font-size:12px;color:var(--mu);margin-top:4px}.ops td.g,.ops td.r{font-variant-numeric:tabular-nums;text-align:center}
.ops td.g{background:rgba(31,143,85,.18)}.ops td.r{background:rgba(192,57,43,.18)}.ops td.n{color:var(--mu);text-align:center}.ops{font-size:12px}</style>"""

JS = r"""<script>(function(){var W=document.querySelector('[data-op]');if(!W||W.dataset.on)return;W.dataset.on=1;
var D=null,SEL='att',AREA='',DIM='',OPEN=null,INFO=JSON.parse(W.getAttribute('data-ii')||'{}'),CK=['revisioni','momentum','crescita','qualita','sorpresa','contratti','catalizzatori','valutazione'];
function S(){return SEL==='prec'&&D.prec?D.prec:D}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function pc(x,d){if(x==null)return '—';var s=(x*100).toFixed(d==null?1:d).replace('.',',').replace('-','−');return (x>0?'+':'')+s+'%'}
function nm(x,d){return x==null?'—':Number(x).toFixed(d==null?1:d).replace('.',',')}
function col(s){if(s==null)return '#64748b';return s>=70?'#16a34a':s>=40?'#d97706':'#dc2626'}
function info(k){var i=INFO[k];if(!i)return '';return '<em class="aii" data-info="'+esc(JSON.stringify({t:i[0],s:[['Cos\'è',i[1]],['Come si legge',i[2]]]}))+'">i</em>'}
function spark(k,w,h){if(!k||k.length<2)return '';var mn=Math.min.apply(null,k),mx=Math.max.apply(null,k),r=mx-mn||1;return '<svg viewBox="0 0 '+w+' '+h+'" style="width:100%;max-width:520px;height:'+h+'px"><polyline fill="none" stroke="#3b82f6" stroke-width="2" points="'+k.map(function(v,i){return (i*(w-2)/(k.length-1)+1).toFixed(1)+','+((h-4)-(v-mn)/r*(h-8)+2).toFixed(1)}).join(' ')+'"/></svg>'}
function det(t){var x=S().titoli[t],d=S().dett[t];if(!d)return '';var r=d.report,h='<div class="sdd" onclick="event.stopPropagation()"><h4>Ultimi 6 mesi</h4>'+spark(x.k,520,110);
h+='<h4>Punteggio Potenziale: '+(x.s==null?'—':x.s+'/100')+' <span class="mu" style="font-weight:400">(fattori usati: '+x.usati+' su 8)</span></h4>';
CK.forEach(function(k,i){var n=Object.keys(D.pesi)[i],v=x.comp[k];h+='<div style="font-size:12px">'+n+' ('+Math.round(D.pesi[n]*100)+'%): <b>'+(v==null?'dati insufficienti':v+'/100')+'</b></div><div class="sdb"><i style="width:'+(v||0)+'%;background:'+col(v)+'"></i></div>'});
h+='<h4>Perché è promettente</h4><p>'+esc(r.promettente)+'</p><h4>Cosa potrebbe andare storto</h4><p>'+esc(r.storto)+'</p>';
h+='<h4>Crescita stimata (fascia, non promessa)</h4><div class="sdk">'+[['1m','1 mese'],['3m','3 mesi'],['1a','1 anno'],['2a','2 anni']].map(function(o){var f=x.fasce[o[0]];return '<div style="display:block"><b>'+o[1]+'</b><br><span style="font-size:12px">'+(f?esc(f.txt):'—')+'</span></div>'}).join('')+'</div><p class="mu" style="font-size:12px">Il centro è '+(Object.keys(D.centri_reali||{}).length?'in parte ':'')+'il rendimento mediano storico del mercato ('+Math.round(D.centro_annuo*100)+'% annuo, ipotesi) finché lo storico delle scelte non basta; l\'ampiezza dipende dalla volatilità del titolo. Il punteggio per ora ordina i titoli ma non sposta il centro.</p>';
if(x.an&&x.an.target)h+='<p>Prezzo obiettivo medio degli analisti a 12 mesi: <b>'+nm(x.an.target,2)+'</b> (min '+nm(x.an.min,2)+' · max '+nm(x.an.max,2)+', '+(x.an.n||'?')+' analisti)</p>';
if(d.cataliz.length)h+='<h4>Catalizzatori in arrivo</h4><div class="sdn">'+d.cataliz.map(function(c){return '<div>'+esc(c.data)+' · '+esc(c.t)+'</div>'}).join('')+'</div>';
var I=d.ind,ks=[['ps','P/S',2],['pe','P/E',1],['ps_f','P/S previsto',2],['ev_ebitda','EV/EBITDA',1],['cap_rpo','Capitalizzazione / RPO',1],['rpo_anni','Anni di fatturato firmati',1],['piotroski','F-score',0],['margine_lordo','Margine lordo',3],['roe','ROE',3],['rev_eps_30','Stime utile 30 giorni',3],['rev_eps_90','Stime utile 90 giorni',3],['crescita_ricavi','Crescita ricavi',3]];
h+='<h4>Indicatori</h4><div class="sdk">'+ks.filter(function(k){return I[k[0]]!=null}).map(function(k){var v=I[k[0]];return '<div><span>'+k[1]+info(k[0])+'</span><b>'+nm(k[2]>=3?v*100:v,k[2]>=3?1:k[2])+(k[2]>=3?'%':'')+'</b></div>'}).join('')+'</div>';
if(d.notizie.length)h+='<h4>Notizie positive recenti</h4><div class="sdn">'+d.notizie.map(function(n){return '<div>'+esc(n.d.slice(8)+'/'+n.d.slice(5,7))+' · <span class="etq">'+esc(n.e)+'</span> <a href="'+esc(n.l||'#')+'" target="_blank" rel="noopener">'+esc(n.t)+'</a></div>'}).join('')+'</div>';
return h+'<p class="mu">'+esc(r.nota)+'</p></div>'}
function riga(t){var x=S().titoli[t],eur=x.eur!=null?' · '+nm(x.eur,2)+' €':'';
var h='<div class="sdr" data-t="'+esc(t)+'"><div class="top"><span class="nm">'+esc(x.n)+' <span class="tk">'+esc(x.t)+' · '+esc(x.sett)+' · '+esc(x.area)+'</span></span><span class="sds" style="background:'+col(x.s)+'" title="Potenziale (1-100)">'+(x.s==null?'—':x.s)+'</span></div><div class="met">';
h+=(x.da_allora!=null?'<span>Da allora <b>'+pc(x.da_allora)+'</b></span>':'')+'<span>7 giorni <b>'+pc(x.r7)+'</b></span><span>1 mese <b>'+pc(x.r1m)+'</b></span><span>Prezzo <b>'+nm(x.p,2)+' '+(x.v==='EUR'?'€':x.v)+'</b>'+eur+'</span><span>Fatturato trim. <b>'+(x.ric?x.ric.f+' '+pc(Math.abs(x.ric.v),0):'—')+'</b></span><span>P/S <b>'+nm(x.ps,1)+'</b></span><span>P/E <b>'+nm(x.pe,1)+'</b></span><span>P/S prev. <b>'+nm(x.ps_f,1)+'</b></span>'+(x.cap_rpo!=null?'<span>Cap./RPO <b>'+nm(x.cap_rpo,1)+'</b></span>':'')+'</div>';
if(x.mot&&x.mot.length)h+='<ul class="opm">'+x.mot.map(function(m){return '<li>'+esc(m)+'</li>'}).join('')+'</ul>';
h+='<div class="opf">3 mesi: '+esc(x.fasce['3m']?x.fasce['3m'].txt:'—')+'</div>';
return h+(OPEN===t?det(t):'')+'</div>'}
function cella(s,h){var c=s[h];if(!c||c.reale==null)return '<td class="n">·</td>';var p=c.prev,ok=p.med!=null?c.reale>=p.med:c.reale>=0;return '<td class="'+(ok?'g':'r')+'" title="previsto: mediana '+pc(p.med,0)+', fascia '+pc(p.lo,0)+' / '+pc(p.hi,0)+'">'+pc(c.reale,0)+'</td>'}
function storico(){var S=D.storico||{},R=S.riepilogo||{},h='<h3 style="margin-top:22px">Storico delle settimane: previsto e reale</h3>';
if(!S.settimane||!S.settimane.length)return h+'<p class="mu">Lo storico parte da questa settimana: ogni sabato si salvano le 30 scelte con le fasce previste, poi si misura il risultato reale a 1 e 3 mesi. Verde = pari o sopra la mediana prevista, rosso = sotto.</p>';
var any=Object.keys(R).length;
if(any){h+='<div class="scroll"><table class="tbl"><tr><th>Orizzonte</th><th>Scelte</th><th>Rendimento medio</th><th>MSCI World (VT)</th><th>Battono VT</th><th>Dentro la fascia 10-90</th></tr>'+Object.keys(R).map(function(k){var r=R[k];return '<tr><td>'+(k==='1m'?'1 mese':'3 mesi')+'</td><td>'+r.n+'</td><td>'+pc(r.medio,1)+'</td><td>'+pc(r.vt,1)+'</td><td>'+(r.batte_vt==null?'—':Math.round(r.batte_vt*100)+'%')+'</td><td>'+(r.dentro_fascia==null?'—':Math.round(r.dentro_fascia*100)+'%')+'</td></tr>'}).join('')+'</table></div><p class="mu">La fascia 10-90 dovrebbe contenere circa l\'80% dei risultati: se è molto diversa, le fasce vanno corrette. Lo storico si mostra anche quando è negativo.</p>'}
else h+='<p class="mu">Nessuna scelta ha ancora 1 mese di storia: le celle compaiono man mano. Verde = pari o sopra la mediana prevista, rosso = sotto.</p>';
S.settimane.slice().reverse().forEach(function(w,i){h+='<details'+(i===0?' open':'')+'><summary>Settimana del '+esc(w.data.split('-').reverse().join('/'))+(w.ric?' (ricostruita, non conta nelle statistiche)':'')+' ('+w.scelte.length+' scelte)</summary><div class="scroll"><table class="tbl ops"><tr><th>Titolo</th><th>Punt.</th><th>Previsione 1m</th><th>Reale 1m</th><th>Previsione 3m</th><th>Reale 3m</th></tr>'+w.scelte.map(function(s){return '<tr><td>'+esc(s.t)+'</td><td>'+s.s+'</td><td class="n">'+pc(s['1m'].prev.med,0)+'</td>'+cella(s,'1m')+'<td class="n">'+pc(s['3m'].prev.med,0)+'</td>'+cella(s,'3m')+'</tr>'}).join('')+'</table></div></details>'});
return h}
function render(){var ids=S().ordine.filter(function(t){var x=S().titoli[t];return (!AREA||x.area===AREA)&&(!DIM||x.dim===DIM)});
var h='<div class="sdc"><button data-sl="att" class="'+(SEL==='att'?'on':'')+'">Selezione attuale</button>'+(D.prec?'<button data-sl="prec" class="'+(SEL==='prec'?'on':'')+'">Settimana scorsa (ricostruita)</button>':'')+'</div><div class="sdc"><select id="opa"><option value="">Tutte le aree</option>'+['USA','Europa','Asia','Altri'].map(function(v){return '<option'+(AREA===v?' selected':'')+'>'+v+'</option>'}).join('')+'</select><select id="opd"><option value="">Tutte le dimensioni</option>'+[['grandi','Grandi (> 10 mld)'],['medie','Medie (2-10 mld)'],['piccole','Piccole (< 2 mld)']].map(function(v){return '<option value="'+v[0]+'"'+(DIM===v[0]?' selected':'')+'>'+v[1]+'</option>'}).join('')+'</select></div>';
if(D.temi&&D.temi.length){h+='<h3>Temi della settimana</h3><div class="opt">'+D.temi.filter(function(t){return t.forza!=null}).slice(0,6).map(function(t){return '<div><b>'+esc(t.tema)+'</b>forza <b style="display:inline;color:'+col(t.forza)+'">'+t.forza+'/100</b><span class="mu"> · notizie '+(t.notizie==null?'—':t.notizie)+' · prezzi '+(t.prezzi==null?'—':t.prezzi)+' · ETF '+esc(t.etf)+'</span></div>'}).join('')+'</div>'}
h+='<p class="mu">'+(SEL==='prec'?'<b>Ricostruita</b>: prezzi e momentum del '+S().asof.split('-').reverse().join('/')+', ma bilanci, stime e notizie di oggi, quindi può includere informazioni arrivate dopo. Serve a vedere cosa è successo da allora, non entra nelle statistiche. ':'')+'Selezione del '+S().settimana.split('-').reverse().join('/')+' (dati al '+S().asof.split('-').reverse().join('/')+'). Il punteggio dice quanto il titolo somiglia ai fattori che storicamente hanno dato rendimenti migliori: <b>non è una previsione</b>. '+ids.length+' titoli. Tocca una scheda per il dettaglio.</p><div class="sdl">'+(ids.length?ids.map(riga).join(''):'<p class="mu">Nessun risultato con questi filtri.</p>')+'</div>'+storico();
W.innerHTML=h;W.querySelectorAll('[data-sl]').forEach(function(b){b.onclick=function(){SEL=b.dataset.sl;OPEN=null;render()}});W.querySelector('#opa').onchange=function(){AREA=this.value;render()};W.querySelector('#opd').onchange=function(){DIM=this.value;render()};
W.querySelectorAll('.sdr').forEach(function(r){r.onclick=function(){var t=r.dataset.t;OPEN=OPEN===t?null:t;render()}})}
function go(j){D=j;if(!D||!D.ordine||!D.ordine.length){W.innerHTML='<p class="mu">Nessuna selezione ancora: si genera ogni sabato con il lavoro «Opportunità Armor».</p>';return}render()}
var emb=document.getElementById('armor-op-data');if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/opportunita.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(go).catch(function(){W.innerHTML='<p class="mu">Opportunità non disponibili (serve la connessione, oppure il lavoro del sabato non è ancora girato).</p>'})}
})();</script>"""


def _gf_badge() -> str:
    try:
        from . import grandi_fondi
        return grandi_fondi.badge_html()
    except Exception:  # noqa: BLE001
        return ""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-op-data'>{data_json}</script>" if data_json else ""
    ii = _h.escape(json.dumps({**saldi.IND_INFO, "cap_rpo": ("Capitalizzazione / RPO", "Capitalizzazione divisa per i contratti firmati e non ancora fatturati (RPO).", "Più basso = il mercato prezza poco il lavoro già in portafoglio."),
                               "rev_eps_30": ("Stime sull'utile a 30 giorni", "Variazione dell'utile per azione atteso a 12 mesi rispetto a 30 giorni fa (media degli analisti).", "Positivo = gli analisti stanno alzando le stime: tra i segnali più robusti in letteratura."),
                               "rev_eps_90": ("Stime sull'utile a 90 giorni", "Come sopra, rispetto a 90 giorni fa.", "Positivo e crescente = revisioni al rialzo persistenti."),
                               "crescita_ricavi": ("Crescita dei ricavi", "Variazione del fatturato dell'ultimo trimestre sullo stesso trimestre dell'anno prima.", "Sopra il 15% = crescita rapida.")}, ensure_ascii=False), quote=True)
    return (f"{saldi.CSS}{CSS_EXTRA}<h2>Opportunità: le 30 aziende della settimana</h2><div class='explain'><p>Ogni sabato Armor ordina le aziende per somiglianza ai fattori che, in letteratura, hanno storicamente accompagnato rendimenti futuri migliori: "
            "revisioni delle stime, momentum, crescita, qualità, sorprese sui conti, contratti già firmati e catalizzatori. Le crescite indicate sono <b>fasce di incertezza, non promesse</b>. "
            "Lo storico delle settimane precedenti (previsto contro reale) è in fondo e si vede anche quando è negativo. <b>Non è una consulenza finanziaria.</b></p></div>"
            f"{_gf_badge()}" f"{emb}<div class='sdw' data-op='1' data-ii='{ii}'></div>{JS}")
