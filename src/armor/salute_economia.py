"""«Salute dell'economia» calibrata sulle recessioni (PROTOCOLLO_SALUTE_ECONOMIA.md, scelta E3).

Indice 0-100: 100 = gravità delle forti recessioni del passato (2008-09, 2020), 0 = economia in espansione.
Misure grezze (alto = peggio) di lavoro e produzione, PIL di USA ed Europa, famiglie e mutui, standardizzate sul periodo
1990-oggi (valori mancanti = neutri); media con peso uguale; una retta (a + b·media) stimata sulla gravità delle recessioni.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import store

LAV = ["l_sussidi", "l_lavoro", "l_prod", "l_chicago", "l_permessi", "l_sahm", "l_fiducia"]
PIL = ["g_usa", "g_europa"]
FAM = ["m_mutuo_var", "m_mutuo", "m_insol_mutui", "m_insol_carte", "m_stretta", "m_consumo", "m_debito"]
FORTI = [("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30")]
LIEVI = [("1990-07-01", "1991-03-31"), ("2001-03-01", "2001-11-30")]
INIZIO = "1990-01-01"


def _L(k):
    return store.load(k).dropna()


def _gravita(cal: pd.DatetimeIndex) -> pd.Series:
    mesi = pd.date_range("1989-12-31", "2030-12-31", freq="ME"); T = pd.Series(0.0, index=mesi)
    for lv, per in ((100.0, FORTI), (60.0, LIEVI)):
        for a, b in per:
            T[(mesi >= pd.Timestamp(a) + pd.offsets.MonthEnd(0)) & (mesi <= pd.Timestamp(b) + pd.offsets.MonthEnd(0))] = lv
            dopo = np.where(mesi > pd.Timestamp(b) + pd.offsets.MonthEnd(0))[0][:12]
            for j, i in enumerate(dopo, 1):
                T.iloc[i] = max(T.iloc[i], lv * (1 - j / 12))
    return T.reindex(T.index.union(cal)).bfill().reindex(cal)   # ogni giorno prende la gravità del suo mese


def misure(cal: pd.DatetimeIndex) -> pd.DataFrame:
    def asof(s, lag):
        s = s.copy(); s.index = s.index + pd.Timedelta(days=lag); s = s[~s.index.duplicated(keep="last")]
        return s.reindex(s.index.union(cal)).ffill().reindex(cal).where(cal >= s.index[0])

    def f(k):
        x = store.load(k).dropna()
        return x if len(x) > 20 else None
    X = pd.DataFrame(index=cal)
    ic = _L("icsa"); ic4 = ic.rolling(4).mean(); X["l_sussidi"] = asof(ic4 / ic4.rolling(52).min() - 1, 5)
    X["l_lavoro"] = -asof(_L("payems").pct_change(3), 37); X["l_prod"] = -asof(_L("indpro").pct_change(3), 45)
    X["l_chicago"] = -asof(_L("cfnai"), 45); X["l_permessi"] = -asof(_L("permit").pct_change(6), 45)
    X["l_sahm"] = asof(_L("sahm"), 40); X["l_fiducia"] = -asof(_L("umcsent").pct_change(6), 20)
    for k, sid in (("g_usa", "f_gdpc1"), ("g_europa", "f_clvmnacscab1gqea19")):
        s = f(sid)
        if s is not None:
            X[k] = -asof(s.pct_change(4) * 100, 120)
    mg, dm, dc, st, tc, td = (f(k) for k in ("f_mortgage30us", "f_drsfrmacbs", "f_drcclacbs", "f_drtsclcc", "f_totalsl", "f_tdsp"))
    if mg is not None:
        m = asof(mg, 3); X["m_mutuo_var"] = m - m.shift(252); X["m_mutuo"] = m
    for k, x, lag in (("m_insol_mutui", dm, 75), ("m_insol_carte", dc, 75), ("m_stretta", st, 45), ("m_debito", td, 90)):
        if x is not None:
            X[k] = asof(x, lag)
    if tc is not None:
        X["m_consumo"] = -asof(tc.pct_change(12), 45)
    return X


def calcola(cal: pd.DatetimeIndex) -> dict:
    """Restituisce {'sea': indice 0-100, 'sea_pil': pilastro PIL (percentile), 'pesi': {...}}. Giorni dal 1990."""
    cal = cal[cal >= INIZIO]; X = misure(cal)
    cols = [c for c in LAV + PIL + FAM if c in X]
    mu, sd = X[cols].mean(), X[cols].std().replace(0, np.nan)
    Z = ((X[cols] - mu) / sd).fillna(0.0)
    s = Z.mean(axis=1); T = _gravita(cal)
    b = max(float(np.cov(s, T)[0, 1] / s.var(ddof=1)), 0.0); a = float(T.mean() - b * s.mean())
    sea = (a + b * s).clip(0, 100)
    pe = lambda x: x.expanding(1300).rank(pct=True) * 100
    pil_c = [c for c in PIL if c in X]
    sea_pil = pe(X[pil_c].fillna(X[pil_c].mean()).mean(axis=1)) if pil_c else None
    contr = {c: float(b * Z[c].iloc[-1] / len(cols)) for c in cols}
    out = {"sea": sea, "pesi": {"a": a, "b": b, "n_misure": len(cols), "contributi_oggi": contr, "misure": cols}}
    if sea_pil is not None:
        out["sea_pil"] = sea_pil.dropna()
    return out
