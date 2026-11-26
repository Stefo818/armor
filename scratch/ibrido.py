"""Esegue PROTOCOLLO_IBRIDO.md (commit sopra)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra
from armor import store, indice_crollo as ic, grafico_indici as gi

X = ic.calcola_serie(); cal = X.index; sp = X["sp500"]
base = X["punteggio"]
G1 = ic.punteggio_unificato(30000)
G1 = G1.reindex(cal)
def scala(punt):
    pq = punt[punt.index >= "1990-01-02"]
    q = pq.expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(punt.index)
    idx = pd.Series(np.nan, index=punt.index)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b); idx[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return idx.clip(1, 100)
pb = base[base.index >= "1990-01-02"].expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(cal)
pg = G1[G1.index >= "1990-01-02"].expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(cal)
H = (pb + pg) / 2
C = {"0_attuale": base, "G1": G1, "H_ibrido": H}

calmo, _ = gi._maschere(); calmo = calmo.reindex(cal).fillna(False).astype(bool)
picchi = [cal.searchsorted(pd.Timestamp(p)) for p in gi.PICCHI_ENDOGENI]
SEL, VER = list(range(7)), list(range(7, 12)); S = sp.to_numpy()
ep = pd.Series(-1, index=cal)
for k, i in enumerate(picchi): ep.iloc[max(0, i - 9):i + 1] = k
def auc(v, pos, neg):
    a, b = v[pos].dropna(), v[neg].dropna()
    if not len(a) or not len(b): return np.nan
    r = pd.concat([a, b]).rank(); return float((r.iloc[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b)))

fuori = finestra(cal, ESTERNI)
for dd in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(dd)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
picco = sp.rolling(252, min_periods=60).max(); dd_ora = sp / picco - 1
fwd_min = pd.concat([sp.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
arriva10 = ((fwd_min / picco - 1) <= -0.10).astype(float); arriva10[fwd_min.isna()] = np.nan

res = {}
for nome, punt in C.items():
    v = scala(punt); v = v[v.index >= "1990-01-02"]; cm = calmo.reindex(v.index)
    pre = {k: float(v[ep == k].mean()) for k in range(12)}; cmn = float(v[cm].mean())
    sc = punt[punt.index >= "1990-01-02"]
    thr = float(sc[cm & (sc.index <= "2007-12-31")].dropna().quantile(0.95))
    al = (sc >= thr).reindex(cal).fillna(False).to_numpy()
    falsi = float((sc >= thr)[cm & (sc.index >= "2008-01-01")].mean() * 100)
    prot = []
    for p in picchi:
        lo, hi = max(0, p - 10), min(len(cal) - 1, p + 40); fin = al[lo:hi + 1]
        if fin.any():
            t = lo + int(np.argmax(fin)); mn = S[p:p + 61].min()
            prot.append(float(np.clip((S[t] - mn) / (S[p] - mn), 0, 1)) if S[p] > mn else 0.0)
        else: prot.append(0.0)
    idx = scala(punt); ok = (~fuori) & arriva10.notna() & idx.notna()
    def rate(m):
        y = arriva10[m]; return round(100 * float(y.mean()), 1) if len(y) > 20 else None
    tab = {"vicino_verde": rate(ok & (dd_ora > -0.02) & (idx < 41)), "vicino_giallo+": rate(ok & (dd_ora > -0.02) & (idx >= 41)),
           "2-7_verde": rate(ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx < 41)), "2-7_giallo+": rate(ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx >= 41)),
           "tutti_verde": rate(ok & (idx < 41)), "tutti_giallo+": rate(ok & (idx >= 41))}
    res[nome] = {"media_calmi": round(cmn, 1), "stacco_sel": round(np.nanmean([pre[k] for k in SEL]) - cmn, 1), "stacco_ver": round(np.nanmean([pre[k] for k in VER]) - cmn, 1),
                 "auc_calmi_ver": round(np.nanmean([auc(v, ep == k, cm) for k in VER]), 3), "protezione_ver": round(np.mean([prot[k] for k in VER]), 2),
                 "falsi_%": round(falsi, 1), "tabella": tab,
                 "rapporti": {"tutti": round(tab["tutti_giallo+"] / tab["tutti_verde"], 2), "2-7": round(tab["2-7_giallo+"] / tab["2-7_verde"], 2), "vicino": round(tab["vicino_giallo+"] / tab["vicino_verde"], 2)}}
b = res["0_attuale"]
for n, o in res.items():
    A = n != "0_attuale" and (o["stacco_ver"] - b["stacco_ver"] >= 5 and o["auc_calmi_ver"] - b["auc_calmi_ver"] >= 0.03 and o["protezione_ver"] - b["protezione_ver"] >= 0.10
                              and o["falsi_%"] - b["falsi_%"] <= 1 and o["stacco_sel"] >= b["stacco_sel"])
    B = o["rapporti"]["tutti"] >= 2 and o["rapporti"]["2-7"] >= 1.5 and o["rapporti"]["vicino"] >= 1.3
    o["batteria_A"], o["batteria_B"], o["passa"] = bool(A), bool(B), bool(A and B)
json.dump(res, open("scratch/ibrido_esito.json", "w"), indent=1)
for n, o in res.items(): print(n, o)
