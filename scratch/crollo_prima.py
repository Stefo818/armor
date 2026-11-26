"""Esegue PROTOCOLLO_CROLLO_PRIMA.md (commit 3d28fbb)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import store, indice_crollo as ic, grafico_indici as gi

X = ic.famiglie()
cal = X.index
sp = X["sp500"]
g = lambda sid, lag=0: ic._lag(store.load(sid).dropna(), lag).reindex(cal).ffill()
w = pd.Series(ic.PESI); w = w / w.sum()
base = sum(X[c].fillna(50.0) * w[c] for c in w.index)

vix = g("vix")
f_vol = ic._pct(vix / vix.rolling(60).mean())
H, L = g("sp_high"), g("sp_low"); rng = (H - L) / sp
f_amp = ic._pct(rng.rolling(5).mean() / rng.rolling(60).mean())
sov = g("bce_sov_area_euro_pesata", 1)
f_sov = ((ic._pct(sov) + ic._pct(sov - sov.shift(20))) / 2)
ciss = pd.concat([ic._pct(g(f"bce_ciss_contr_{k}", 1)) for k in ("banche", "monetario", "azioni", "obbligazioni", "cambi")], axis=1).mean(axis=1)
f_ciss = ciss
for f in (f_sov, f_ciss):
    f[f.index < "2000-02-01"] = 50.0

def a_indice(punt):
    pq = punt[punt.index >= "1990-01-02"]
    q = pq.expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(punt.index)
    idx = pd.Series(np.nan, index=punt.index)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b)
        idx[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return idx.clip(1, 100)

CAND = {
    "0_attuale": base,
    "1_vol60": 0.7 * base + 0.3 * f_vol.fillna(50),
    "2_ampiezza": 0.7 * base + 0.3 * f_amp.fillna(50),
    "3_titoli_stato_UE": 0.7 * base + 0.3 * f_sov.fillna(50),
    "4_CISS_contributi": 0.7 * base + 0.3 * f_ciss.fillna(50),
    "5_misto": 0.55 * base + 0.15 * f_vol.fillna(50) + 0.15 * f_amp.fillna(50) + 0.15 * f_sov.fillna(50),
}
calmo, _ = gi._maschere()
calmo = calmo.reindex(cal).fillna(False).astype(bool)
picchi = [cal.searchsorted(pd.Timestamp(p)) for p in gi.PICCHI_ENDOGENI]
sel_i, ver_i = list(range(7)), list(range(7, 12))
pre = pd.Series(False, index=cal); ep = pd.Series(-1, index=cal)
for k, i in enumerate(picchi):
    pre.iloc[max(0, i - 19):i + 1] = True; ep.iloc[max(0, i - 19):i + 1] = k

def auc(v, pos, neg):
    a, b = v[pos].dropna(), v[neg].dropna()
    if len(a) == 0 or len(b) == 0: return float("nan")
    r = pd.concat([a, b]).rank()
    return float((r.iloc[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b)))

def ep_auc(v, eps, neg):   # AUC pesata per episodio
    out = []
    for k in eps:
        pos = ep == k
        out.append(auc(v, pos, neg))
    return float(np.nanmean(out))

res = {}
for nome, punt in CAND.items():
    v = a_indice(punt)
    v = v[v.index >= "1990-01-02"]
    pr = {k: float(v[ep == k].mean()) for k in range(12)}
    cm = float(v[calmo.reindex(v.index)].mean())
    allm = float(v.mean())
    res[nome] = {
        "media_calmi": round(cm, 1), "media_tutti": round(allm, 1),
        "prima_sel": round(np.nanmean([pr[k] for k in sel_i]), 1), "prima_ver": round(np.nanmean([pr[k] for k in ver_i]), 1),
        "prima_tutti": round(np.nanmean(list(pr.values())), 1),
        "stacco_sel": round(np.nanmean([pr[k] for k in sel_i]) - cm, 1), "stacco_ver": round(np.nanmean([pr[k] for k in ver_i]) - cm, 1),
        "auc_calmi_sel": round(ep_auc(v, sel_i, calmo.reindex(v.index)), 3), "auc_calmi_ver": round(ep_auc(v, ver_i, calmo.reindex(v.index)), 3),
        "auc_tutti_sel": round(ep_auc(v, sel_i, ep == -1), 3), "auc_tutti_ver": round(ep_auc(v, ver_i, ep == -1), 3),
        "per_episodio": {gi.PICCHI_ENDOGENI[k]: round(pr[k], 1) for k in range(12)},
    }
b = res["0_attuale"]
for nome, r in res.items():
    r["passa"] = bool(r["stacco_ver"] - b["stacco_ver"] >= 5 and r["auc_calmi_ver"] - b["auc_calmi_ver"] >= 0.03
                      and r["media_calmi"] - b["media_calmi"] <= 3 and r["stacco_sel"] >= b["stacco_sel"] and nome != "0_attuale")
json.dump(res, open("scratch/crollo_prima_esito.json", "w"), indent=1, ensure_ascii=False)
for nome, r in res.items():
    print(nome, {k: v for k, v in r.items() if k != "per_episodio"})
print(res["0_attuale"]["per_episodio"])
