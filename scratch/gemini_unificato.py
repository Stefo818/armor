"""Esegue PROTOCOLLO_GEMINI_UNIFICATO.md (commit 410948c)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import store, indice_crollo as ic, grafico_indici as gi

X = ic.famiglie(); cal = X.index; sp = X["sp500"]
g = lambda sid, lag=1: ic._lag(store.load(sid).dropna(), lag).reindex(cal).ffill()
w = pd.Series(ic.PESI); w = w / w.sum()
base = sum(X[c].fillna(50.0) * w[c] for c in w.index)

def pr(s, window=1260, minp=252):   # percentile mobile senza guardare avanti (vettoriale)
    v = s.to_numpy(float); out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if np.isnan(v[i]): continue
        a = v[max(0, i - window + 1):i + 1]; a = a[~np.isnan(a)]
        if len(a) >= minp: out[i] = (a <= v[i]).mean() * 100
    return pd.Series(out, index=s.index).fillna(50.0)

cape = g("cape_m", 31); d10 = g("dgs10"); hy = g("baa10y")
vix, vix3, skew = g("vix"), g("vix3m"), g("skew")
terreno = (pr(cape) + pr(d10) + pr(hy)) / 3
s20 = sp / sp.rolling(20).mean() - 1; s50 = sp / sp.rolling(50).mean() - 1
anticipo = (pr((s20 + s50) / 2) + pr(vix / vix.rolling(60).mean()) + pr(skew)) / 3
ret = sp.pct_change(); vol20 = ret.rolling(20).std() * np.sqrt(252)
innesco = (pr(vix / vix3) + pr(vol20) + pr(vix.pct_change(5))) / 3
G1 = (0.30 * terreno + 0.35 * anticipo + 0.35 * innesco)
G2 = 0.5 * anticipo + 0.5 * innesco

def scala(punt):
    pq = punt[punt.index >= "1990-01-02"]
    q = pq.expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(punt.index)
    idx = pd.Series(np.nan, index=punt.index)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b); idx[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return idx.clip(1, 100)

C = {"0_attuale": base, "G1_gemini": G1, "G2_senza_terreno": G2}
calmo, _ = gi._maschere(); calmo = calmo.reindex(cal).fillna(False).astype(bool)
picchi = [cal.searchsorted(pd.Timestamp(p)) for p in gi.PICCHI_ENDOGENI]
SEL, VER = list(range(7)), list(range(7, 12)); S = sp.to_numpy()
ep = pd.Series(-1, index=cal)
for k, i in enumerate(picchi): ep.iloc[max(0, i - 9):i + 1] = k

def auc(v, pos, neg):
    a, b = v[pos].dropna(), v[neg].dropna()
    if not len(a) or not len(b): return np.nan
    r = pd.concat([a, b]).rank(); return float((r.iloc[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b)))

res = {}
for nome, punt in C.items():
    v = scala(punt); v = v[v.index >= "1990-01-02"]; cm = calmo.reindex(v.index)
    pre = {k: float(v[ep == k].mean()) for k in range(12)}
    calm_mean = float(v[cm].mean())
    sc = punt[punt.index >= "1990-01-02"]
    thr = float(sc[cm & (sc.index <= "2007-12-31")].dropna().quantile(0.95))
    al = (sc >= thr).reindex(cal).fillna(False).to_numpy()
    falsi = float((sc >= thr)[cm & (sc.index >= "2008-01-01")].mean() * 100)
    prot, rit = [], []
    for p in picchi:
        lo, hi = max(0, p - 10), min(len(cal) - 1, p + 40); fin = al[lo:hi + 1]
        if fin.any():
            t = lo + int(np.argmax(fin)); mn = S[p:p + 61].min()
            prot.append(float(np.clip((S[t] - mn) / (S[p] - mn), 0, 1)) if S[p] > mn else 0.0); rit.append(t - p)
        else:
            prot.append(0.0); rit.append(40)
    res[nome] = {"media_calmi": round(calm_mean, 1),
                 "prima10_sel": round(np.nanmean([pre[k] for k in SEL]), 1), "prima10_ver": round(np.nanmean([pre[k] for k in VER]), 1),
                 "stacco_sel": round(np.nanmean([pre[k] for k in SEL]) - calm_mean, 1), "stacco_ver": round(np.nanmean([pre[k] for k in VER]) - calm_mean, 1),
                 "auc_calmi_sel": round(np.nanmean([auc(v, ep == k, cm) for k in SEL]), 3), "auc_calmi_ver": round(np.nanmean([auc(v, ep == k, cm) for k in VER]), 3),
                 "protezione_sel": round(np.mean([prot[k] for k in SEL]), 2), "protezione_ver": round(np.mean([prot[k] for k in VER]), 2),
                 "ritardo_mediano_ver": float(np.median([rit[k] for k in VER])), "falsi_allarmi_calmi_dal_2008_%": round(falsi, 1),
                 "soglia_grezza": round(thr, 2), "oggi_scala_indice": round(float(v.iloc[-1]), 1), "oggi_grezzo": round(float(punt.iloc[-1]), 1),
                 "per_picco_prima10": {gi.PICCHI_ENDOGENI[k]: round(pre[k], 1) for k in range(12)}}
b = res["0_attuale"]
for n, o in res.items():
    o["passa"] = bool(n != "0_attuale" and o["stacco_ver"] - b["stacco_ver"] >= 5 and o["auc_calmi_ver"] - b["auc_calmi_ver"] >= 0.03
                      and o["protezione_ver"] - b["protezione_ver"] >= 0.10 and o["falsi_allarmi_calmi_dal_2008_%"] - b["falsi_allarmi_calmi_dal_2008_%"] <= 1
                      and o["stacco_sel"] >= b["stacco_sel"])
json.dump(res, open("scratch/gemini_unificato_esito.json", "w"), indent=1, ensure_ascii=False)
for n, o in res.items(): print(n, {k: v for k, v in o.items() if k != "per_picco_prima10"})
print(res["G1_gemini"]["per_picco_prima10"])
