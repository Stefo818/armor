# -*- coding: utf-8 -*-
"""Fase rispetto al minimo (indice «Minimi»): 100 = il mercato sta andando verso un minimo (discesa in corso, fondo ancora davanti),
1 = si sta allontanando dai minimi verso nuovi massimi. Regole e misure: PROTOCOLLO_MINIMI_5.md / ESITO_MINIMI_5.md.

Due parti con lo stesso peso:
- «modello»: regressione logistica addestrata ogni anno su 14 mercati (solo giorni in discesa, bersaglio «il fondo e' ancora davanti»);
- «cinque segnali semplici»: media di percentili storici (nessun addestramento).
Tutto usa solo dati noti quel giorno; ogni anno e' previsto da un modello addestrato fino all'anno prima (95 giorni di salto)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import store

MERCATI = {"S&P 500": "sp500", "FTSE": "x_ftse", "CAC": "x_fchi", "SMI": "x_ssmi", "IBEX": "x_ibex", "AEX": "x_aex", "BEL20": "x_bfx", "HangSeng": "x_hsi",
           "Toronto": "x_gsptse", "Sydney": "x_axjo", "SanPaolo": "x_bvsp", "Seul": "x_ks11", "Taiwan": "x_twii", "Messico": "x_mxx"}
VAR = ["dd252", "dd63", "rimb", "dal_min", "r5", "r21", "r63", "m50", "m200", "pend50", "vol21", "vol_rap", "giorni_neri", "dsh", "volpk"]
SEGNALI = {"mf_rimb": ("a", "Poco rimbalzo dal minimo"), "mf_dur": ("b", "Pochi giorni dal massimo"), "mf_pend": ("c", "Media a 50 giorni in discesa"),
           "mf_neri": ("d", "Molti giorni neri di recente"), "mf_vol": ("e", "Volatilità ancora vicina al picco")}


def _feats(sp: pd.Series) -> pd.DataFrame:
    ix = sp.index; r = sp.pct_change(); pos = pd.Series(np.arange(len(sp)), index=ix)
    mx252, mx63, mn63 = sp.rolling(252).max(), sp.rolling(63).max(), sp.rolling(63).min()
    ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean(); v21, v63 = r.rolling(21).std(), r.rolling(63).std()
    P = pd.DataFrame({"dd252": sp / mx252 - 1, "dd63": sp / mx63 - 1, "rimb": sp / mn63 - 1, "dal_min": (pos - pos.where(sp == mn63).ffill()).clip(upper=63),
                      "r5": sp.pct_change(5), "r21": sp.pct_change(21), "r63": sp.pct_change(63), "m50": sp / ma50 - 1, "m200": sp / ma200 - 1,
                      "pend50": ma50 / ma50.shift(21) - 1, "vol21": v21, "vol_rap": v21 / v63, "giorni_neri": (r < -0.01).astype(float).rolling(21).sum(),
                      "dsh": (pos - pos.where(sp == mx252).ffill()).clip(upper=252), "volpk": v21 / v21.rolling(63).max()})
    P["px"] = sp
    return P.replace([np.inf, -np.inf], np.nan)


def tabella() -> pd.DataFrame:
    frames = []
    for nome, k in MERCATI.items():
        try:
            s = store.load(k).dropna(); s = s[(s.index >= "1989-01-01") & ~s.index.duplicated()]
            if len(s) < 2000:
                continue
            F = _feats(s).dropna(subset=VAR); F["mercato"] = nome
            st = (F["dd252"] <= -0.08).to_numpy(); ep = np.zeros(len(F), int); cur = 0; last = -99
            for i, v in enumerate(st):
                if v:
                    if i - last > 21 or cur == 0:
                        cur += 1
                    ep[i] = cur; last = i
            F["ep"] = ep; F.index.name = "data"; frames.append(F.reset_index())
        except Exception:  # noqa: BLE001
            continue
    D = pd.concat(frames, ignore_index=True); D["epid"] = D["mercato"] + "_" + D["ep"].astype(str); D["T"] = np.nan
    for _, g in D[D["ep"] > 0].groupby("epid"):
        tr = g["px"].idxmin(); D.loc[g.index, "T"] = (g.index < tr).astype(float); D.loc[tr, "T"] = np.nan
    D["anno"] = D["data"].dt.year
    return D


def calcola() -> pd.DataFrame:
    """Serie giornaliere dell'S&P 500: minimi (1-100), modello, cinque segnali e ciascun segnale. Dal 2001."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    D = tabella(); D["L1"] = np.nan
    for Y in range(2000, int(D["anno"].max()) + 1):
        lim = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=95); trn = D[(D["data"] < lim) & D["T"].notna()]; te = D["anno"] == Y
        if len(trn) < 300 or te.sum() == 0:
            continue
        sc = StandardScaler().fit(trn[VAR]); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(trn[VAR]), trn["T"])
        D.loc[te, "L1"] = m.predict_proba(sc.transform(D.loc[te, VAR]))[:, 1]
    g = D.groupby("mercato")
    pe = lambda s: s.expanding(252).rank(pct=True)
    comp = pd.DataFrame({"a": 1 - g["rimb"].transform(pe), "b": 1 - g["dsh"].transform(pe), "c": 1 - g["pend50"].transform(pe),
                         "d": g["giorni_neri"].transform(pe), "e": g["volpk"].transform(pe)})
    D["L3"] = comp.mean(axis=1, skipna=False); D["L1p"] = g["L1"].transform(pe)
    for k, (c, _) in SEGNALI.items():
        D[k] = comp[c]
    D["E1"] = (D["L1p"] + D["L3"]) / 2
    s = D[D["mercato"] == "S&P 500"].set_index("data")
    out = pd.DataFrame({"minimi": (1 + 99 * s["E1"].expanding(252).rank(pct=True)), "mi_modello": s["L1p"] * 100, "mi_semplice": s["L3"] * 100})
    for k in SEGNALI:
        out[k] = s[k] * 100
    return out.dropna(subset=["minimi"])
