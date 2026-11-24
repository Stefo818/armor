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
