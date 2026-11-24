"""Territori di rischio endogeno: sette meccanismi che nel passato hanno innescato crolli nati dentro il sistema finanziario.

Regole fissate prima dei dati in PROTOCOLLO_TERRITORI.md; esito in ESITO_TERRITORI.md. Ogni meccanismo e' la media di percentili
(sempre solo del passato) di alcuni indicatori, riletti poi come percentile: «caldo» se >= 0,80. Una convergenza di meccanismi caldi
e' un «territorio». Peso zero nell'Indice crollo.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import concentrazione, store
from .config import DATA

SOGLIA = 0.80
MECC = {
    "M0": ("Troppa concentrazione su pochi titoli", "pochi titoli e la tecnologia pesano troppo (come nella bolla dot-com)"),
    "M1": ("Prezzi da bolla", "le azioni costano molto rispetto agli utili e sono salite tanto in tre anni"),
    "M2": ("Leva e affollamento", "troppi investitori indebitati o schierati dalla stessa parte, con mercato troppo tranquillo"),
    "M3": ("Credito e banche", "il credito si restringe: spread che si allargano, banche che irrigidiscono, curva dei tassi rovesciata"),
    "M4": ("Le obbligazioni drenano soldi dalle azioni", "rendimenti in salita, premio per il rischio azionario basso, meno moneta in circolazione"),
    "M5": ("Stress del debito e delle banche europee", "tensione sistemica in Europa in aumento"),
    "M6": ("Dollaro forte e debiti in valuta", "il dollaro sale in fretta e mette sotto pressione chi ha debiti in dollari"),
}
ORDINE = list(MECC)
ARCH = DATA / "territori.json"
REG = DATA / "territori_registro.csv"


def pe(s: pd.Series, minimo: int | None = None) -> pd.Series:
    """Percentile espandente (solo passato). Minimo: 252 osservazioni giornaliere/settimanali, 60 mensili."""
    s = s.dropna()
    if minimo is None:
        minimo = 60 if len(s) > 10 and (s.index[-1] - s.index[0]).days / len(s) > 10 else 252
    return s.expanding(min_periods=minimo).rank(pct=True)


def L(nome: str) -> pd.Series:
    return store.load(nome).dropna()


def _al(s: pd.Series, cal: pd.DatetimeIndex) -> pd.Series:
    return s.reindex(s.index.union(cal)).ffill().reindex(cal)


def indicatori(cal: pd.DatetimeIndex, sp: pd.Series, liv_conc: pd.Series | None = None) -> dict[str, dict[str, pd.Series]]:
    """Percentile di rischio (0-1, piu' alto = piu' rischio) di ogni indicatore, allineati al calendario di Borsa."""
    lag = concentrazione.lag
    out: dict[str, dict[str, pd.Series]] = {k: {} for k in ORDINE}
    if liv_conc is not None:
        out["M0"]["concentrazione"] = liv_conc.reindex(cal)
    cape = lag(L("cape_m"), 30)
    out["M1"]["cape"] = _al(pe(cape), cal)
    out["M1"]["salita_3_anni"] = _al(pe(np.log(sp / sp.shift(756)).dropna()), cal)
    out["M2"]["nfci_leva"] = _al(pe(lag(L("f_nfcileverage"), 5)), cal)
    md = lag(L("margin_debt"), 50)
    out["M2"]["margine_annuo"] = _al(pe(md.pct_change(12).dropna()), cal)
    out["M2"]["vix_basso"] = _al(1 - pe(L("vix").rolling(21).mean()), cal)
    out["M2"]["skew"] = _al(pe(L("skew").rolling(21).mean()), cal)
    jp = lag(L("jpy"), 1)
    out["M2"]["yen_si_rafforza"] = _al(1 - pe(np.log(jp / jp.shift(63)).dropna()), cal)
    # credito: spread che si allarga (stessa costruzione di PROTOCOLLO_CONCENTRAZIONE: C1)
    spread_m = (L("baa_lungo") - L("gs10_m").reindex(L("baa_lungo").index)).dropna()
    c_m = pe(lag(spread_m, 35).diff(3).dropna())
    c_d = pe(lag(L("baa10y"), 1).diff(63).dropna())
    c1 = pd.concat([c_m[c_m.index < "1986-06-01"], c_d[c_d.index >= "1986-06-01"]])
    out["M3"]["spread_in_allargamento"] = _al(c1, cal)
    pend = (lag(L("dgs10"), 1) - L("fedfunds").reindex(lag(L("dgs10"), 1).index, method="ffill")).dropna()
    out["M3"]["curva_rovesciata"] = _al(1 - pe(pend), cal)
    out["M3"]["banche_stringono"] = _al(pe(lag(L("sloos"), 45), minimo=20), cal)
    out["M3"]["nfci_credito"] = _al(pe(lag(L("f_nfcicredit"), 5)), cal)
    d10 = lag(L("dgs10"), 1)
    out["M4"]["rendimento_10a_in_salita"] = _al(pe(d10.diff(252).dropna()), cal)
    erp = (100 / cape - d10.reindex(cape.index, method="ffill")).dropna()
    out["M4"]["premio_rischio_basso"] = _al(1 - pe(erp), cal)
    m2 = lag(L("m2"), 30)
    out["M4"]["moneta_in_calo"] = _al(1 - pe(m2.pct_change(12).dropna()), cal)
    out["M4"]["stretta_banca_centrale"] = _al(pe(lag(L("fedfunds"), 1).diff(252).dropna()), cal)
    ci = lag(L("bce_ciss_area_euro"), 1)
    out["M5"]["stress_euro"] = _al(pe(ci), cal)
    out["M5"]["stress_euro_in_salita"] = _al(pe(ci.diff(63).dropna()), cal)
    dx = L("dxy")
    out["M6"]["dollaro_12m"] = _al(pe(np.log(dx / dx.shift(252)).dropna()), cal)
    out["M6"]["dollaro_3m"] = _al(pe(np.log(dx / dx.shift(63)).dropna()), cal)
    return out


def meccanismi(ind: dict[str, dict[str, pd.Series]], cal: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Indice di ogni meccanismo (media dei suoi indicatori poi percentile) e se e' caldo."""
    idx = {}
    for k in ORDINE:
        if not ind[k]:
            continue
        m = pd.DataFrame(ind[k]).reindex(cal).mean(axis=1, skipna=True)
        idx[k] = pe(m.dropna()).reindex(cal)
    I = pd.DataFrame(idx).reindex(columns=ORDINE)
    caldo = (I >= SOGLIA) & I.notna()
    return I, caldo


def stati(caldo: pd.DataFrame, I: pd.DataFrame) -> dict[str, pd.Series]:
    K = caldo.sum(axis=1)
    s = {"K2 almeno 2 meccanismi caldi": K >= 2, "K3 almeno 3 meccanismi caldi": K >= 3, "K4 almeno 4 meccanismi caldi": K >= 4}
    for k in ORDINE:
        s[f"{k} {MECC[k][0]}"] = caldo[k]
    s["BOLLA: prezzi da bolla e concentrazione"] = caldo["M1"] & caldo["M0"]
    s["LEVA: leva e credito"] = caldo["M2"] & caldo["M3"]
    s["DRENAGGIO: obbligazioni + leva o credito"] = caldo["M4"] & (caldo["M2"] | caldo["M3"])
    return s


def calcola(P: dict[str, pd.Series], sp: pd.Series) -> dict:
    """Tutto in un colpo: concentrazione, indicatori, meccanismi, convergenza, stati."""
    sp = sp[sp.index >= "1971-01-01"]
    cal = sp.index[sp.index >= "1971-06-01"]
    conc = concentrazione.calcola(P, sp)
    ind = indicatori(cal, sp, conc["livello"])
    I, caldo = meccanismi(ind, cal)
    K = caldo.sum(axis=1)
    return {"cal": cal, "ind": ind, "I": I, "caldo": caldo, "K": K, "stati": stati(caldo, I), "conc": conc}


FRASE = ("Non è dimostrato che questi segnali prevedano i crolli: provati su 1971-2026, nessuno ha retto la verifica sugli ultimi anni "
         "(il credito funzionava fino al 2014 e poi no). Servono a capire in che clima siamo, non a dire «sta per crollare». Peso zero sugli altri indici.")


def costruisci() -> dict:
    P = {k: store.load("cn_" + k.lower()).dropna() for k in concentrazione.SIMBOLI}
    sp = store.load("sp500").dropna()
    R = calcola(P, sp)
    I, caldo, K, cal = R["I"], R["caldo"], R["K"], R["cal"]
    A = pe(I.mean(axis=1, skipna=True).dropna(), minimo=252)
    i = len(cal) - 1
    ind = {k: {n: round(float(v.dropna().iloc[-1]), 3) for n, v in d.items() if v.notna().any()} for k, d in R["ind"].items()}
    mecc = {k: {"nome": MECC[k][0], "spiega": MECC[k][1], "indice": None if pd.isna(I[k].iloc[i]) else round(float(I[k].iloc[i]), 3), "caldo": bool(caldo[k].iloc[i]),
                "giorni_caldo_ultimi_63": int(caldo[k].iloc[-63:].sum()), "indicatori": ind[k]} for k in ORDINE}
    riga = {"data": str(cal[i].date()), "K": int(K.iloc[i]), "punteggio": round(float(A.iloc[-1]), 3)}
    for k in ORDINE:
        riga[k] = mecc[k]["indice"]
    for k, d in ind.items():
        for n, v in d.items():
            riga[f"{k}_{n}"] = v
    storia = {"t": [str(d.date()) for d in cal[-1260::5]], **{k: [None if pd.isna(x) else round(float(x), 2) for x in I[k].iloc[-1260::5]] for k in ORDINE},
              "K": [int(x) for x in K.iloc[-1260::5]]}
    return {"data": riga["data"], "K": riga["K"], "punteggio": riga["punteggio"], "meccanismi": mecc, "soglia": SOGLIA, "frase": FRASE, "storia": storia, "_riga_registro": riga}


def registra(riga: dict) -> None:
    new = pd.DataFrame([riga])
    old = pd.read_csv(REG) if REG.exists() else pd.DataFrame()
    m = pd.concat([old, new], ignore_index=True).drop_duplicates(subset=["data"], keep="last").sort_values("data")
    m.to_csv(REG, index=False)


def run() -> dict:
    out = costruisci()
    registra(out.pop("_riga_registro"))
    ARCH.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    caldi = [k for k in ORDINE if out["meccanismi"][k]["caldo"]]
    print(f"[territori] {out['data']}: {out['K']} meccanismi caldi {caldi}, punteggio {out['punteggio']:.2f}", flush=True)
    return out


def leggi() -> dict | None:
    try:
        return json.loads(ARCH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def striscia_html() -> str:
    """Striscia informativa del Quadro di oggi: quali cause dei crolli di pancia sono accese. Mai un avviso di crollo."""
    import html as _h
    d = leggi()
    if not d:
        return ""
    chips = []
    for k in ORDINE:
        m = d["meccanismi"][k]
        if m["indice"] is None:
            continue
        col = "var(--bad)" if m["caldo"] else "var(--mu)"
        tip = f"{m['spiega']}. Indice {m['indice'] * 100:.0f} su 100 (acceso da 80). " + ("Acceso oggi." if m["caldo"] else "Spento oggi.")
        chips.append(f"<span class='tr-c' style='border-color:{col};color:{col}' title='{_h.escape(tip, quote=True)}'>{_h.escape(m['nome'])} <b>{m['indice'] * 100:.0f}</b></span>")
    n = d["K"]
    tit = f"Cause dei crolli «di pancia»: {n} su 7 accese" if n else "Cause dei crolli «di pancia»: nessuna accesa"
    return ("<style>.tr{margin-top:8px}.tr-t{font-size:12px;font-weight:700}.tr-g{display:flex;flex-wrap:wrap;gap:5px;margin-top:4px}"
            ".tr-c{font-size:10.5px;border:1px solid;border-radius:999px;padding:1px 7px;white-space:nowrap}.tr-c b{margin-left:2px}</style>"
            f"<div class='tr'><div class='tr-t' title='{_h.escape(d['frase'], quote=True)}'>{_h.escape(tit)} <span style='font-weight:400;color:var(--mu)'>· informativo, non è un avviso</span></div>"
            f"<div class='tr-g'>{''.join(chips)}</div></div>")
