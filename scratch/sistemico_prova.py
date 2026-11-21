# -*- coding: utf-8 -*-
"""Prova del PROTOCOLLO_SISTEMICO.md (regole scritte prima). PYTHONPATH=src python scratch/sistemico_prova.py -> scratch/sistemico_risultati.json"""
import json, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy.stats import rankdata
from armor import modello_sistemico as ms, store
t0 = time.time()
D = ms.calcola_serie(); print("serie calcolata", round(time.time() - t0), "s", D.index[0].date(), D.index[-1].date(), flush=True)
sp = store.load("sp500").dropna().reindex(D.index)
T = pd.read_csv("data/titan_storia.csv", parse_dates=["date"]).set_index("date").reindex(D.index)
vix = store.load("vix").dropna().reindex(D.index).ffill()
P = sp.values; n = len(P)
def fmin(h):
    o = np.full(n, np.nan)
    for i in range(n - h): o[i] = P[i + 1:i + h + 1].min() / P[i] - 1
    return o
m3, m6 = fmin(63), fmin(126)
Y3 = pd.Series((m3 <= -0.08).astype(float), index=D.index).where(~np.isnan(m3)); Y6 = pd.Series((m6 <= -0.10).astype(float), index=D.index).where(~np.isnan(m6))
shock = pd.Series(False, index=D.index)
# Y3 che "inizia" nelle finestre: giorno in cui si tocca il -8% entro le 63 sedute, oppure la finestra stessa
fin = [("1998-07-15", "1998-10-31"), ("2020-02-01", "2020-04-30"), ("2025-03-01", "2025-04-30")]
for a, b in fin:
    ia = D.index.searchsorted(pd.Timestamp(a)); ib = D.index.searchsorted(pd.Timestamp(b), side="right")
    shock.iloc[max(ia - 63, 0):ib] = True        # sedute i cui 63 giorni successivi cadono (anche in parte) nella finestra di shock
univ = (D["dd252"] > -4.0) & D.index.isin(D.index[D.index >= "1997-01-01"]) & Y3.notna() & Y6.notna()
prim = univ & ~shock
def auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, float); m = np.isfinite(s) & np.isfinite(y); s, y = s[m], y[m]; n1 = y.sum(); n0 = len(y) - n1
    return np.nan if n1 < 3 or n0 < 3 else float((rankdata(s)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def boot(s, y, block=63, reps=1000, seed=7):
    s, y = np.asarray(s, float), np.asarray(y, float); m = np.isfinite(s) & np.isfinite(y); s, y = s[m], y[m]; N = len(y); rng = np.random.default_rng(seed); o = []
    for _ in range(reps):
        st = rng.integers(0, max(N - block, 1), int(np.ceil(N / block))); ix = np.concatenate([np.arange(a, min(a + block, N)) for a in st])[:N]; v = auc(s[ix], y[ix])
        if np.isfinite(v): o.append(v)
    return [float(np.percentile(o, 5)), float(np.percentile(o, 95))]
pvix = vix.expanding(504).rank(pct=True) * 100
v5 = vix.shift(5); B = ((vix >= 22) & (vix / v5 - 1 >= 0.10)).astype(float)
modelli = {"Radar 1-3 mesi (score_3m)": D["score_3m"], "Radar 6 mesi (score_6m)": D["score_6m"], "Indice Armor": T["armor_index"], "Super Armor": T["super_armor_index"], "Percentile del VIX": pvix, "Regola paura in salita (B)": B}
R = {"campione": {"sedute_primario": int(prim.sum()), "Y3_primario": int(Y3[prim].sum()), "frequenza_base_Y3": float(Y3[prim].mean()), "sedute_tutte": int(univ.sum()), "Y3_tutte": int(Y3[univ].sum()), "Y6_primario": int(Y6[prim].sum())}, "auc": {}}
halves = {"1997-2011": D.index < "2012-01-01", "2012-2026": D.index >= "2012-01-01", "2008-2026": D.index >= "2008-01-01"}
for nome, s in modelli.items():
    r = {"Y3_primario": auc(s[prim], Y3[prim]), "Y3_tutte": auc(s[univ], Y3[univ]), "Y6_primario": auc(s[prim], Y6[prim])}
    for h, mk in halves.items(): r["Y3_" + h] = auc(s[prim & mk], Y3[prim & mk])
    R["auc"][nome] = r
R["ic90_Y3_radar3m"] = boot(D["score_3m"][prim], Y3[prim]); R["ic90_Y3_armor"] = boot(T["armor_index"][prim], Y3[prim])
# riferimento di caso: spostamenti circolari
rng = np.random.default_rng(11); sc = D["score_3m"].values; ok = prim.values; yv = Y3.values; ref = []
for _ in range(500):
    k = int(rng.integers(252, n - 252)); ref.append(auc(np.where(ok, np.roll(sc, k), np.nan), yv))
R["riferimento_caso_p95"] = float(np.nanpercentile(ref, 95)); R["riferimento_caso_p50"] = float(np.nanpercentile(ref, 50))
# precisione e quota
hi = (D["score_3m"] >= 60) & prim
R["allerta"] = {"quota_sedute": float(hi.sum() / prim.sum()), "precisione": float(Y3[hi].mean()) if hi.any() else None, "frequenza_base": float(Y3[prim].mean()), "sedute": int(hi.sum())}
# episodi: Y3 sulle sedute (universo "tutte", con flag shock) raggruppati
dd = (sp / sp.rolling(252).max() - 1) * 100
ep = []; idxs = np.where((Y3 == 1) & univ)[0]
for i in idxs:
    if not ep or i - ep[-1][-1] > 126: ep.append([i])
    else: ep[-1].append(i)
righe = []
for e in ep:
    i0 = e[0]; j = next((k for k in range(i0, min(i0 + 63 + 1, n)) if sp.iloc[k] / sp.iloc[max(0, i0 - 0):k + 1].max() - 1 <= -0.05 or dd.iloc[k] <= -5), None)
    # giorno in cui il calo dal massimo a 252 sedute raggiunge -5% (a partire dalla prima seduta dell'episodio)
    jj = next((k for k in range(i0, min(i0 + 200, n)) if dd.iloc[k] <= -5), None)
    if jj is None: continue
    w = D["score_3m"].iloc[max(jj - 126, 0):jj + 1]; sopra = w[w >= 60]
    righe.append({"inizio": str(D.index[i0].date()), "giorno_meno5": str(D.index[jj].date()), "shock_esterno": bool(shock.iloc[i0]), "intercettato": bool(len(sopra)), "anticipo_sedute": None if not len(sopra) else int(jj - D.index.get_loc(sopra.index[0])), "massimo_prima": float(w.max()), "regime": str(D["regime"].iloc[max(jj - 5, 0)])})
R["episodi"] = righe
# sensori mancanti: quota di sedute con almeno 1 sensore costante per anno (informativo)
dis = {"vix3m": "2006-07", "vvix": "2007-01", "move": "2002-11", "hyg": "2007-04", "kre": "2006-06", "rsp": "2003-05", "real10y": "2003-01", "iyt": "2004-01", "net_liq_13w": "2003-03"}
R["sensori_inizio"] = dis
# ultimi valori
u = D.iloc[-1]; R["oggi"] = {"data": str(D.index[-1].date()), "regime": u["regime"], "score_3m": float(u["score_3m"]), "score_6m": float(u["score_6m"]), "dd252": float(u["dd252"]), "ultimi": D[["regime", "score_3m", "score_6m"]].tail(8).reset_index().astype(str).values.tolist()}
# regola
a3 = R["auc"]["Radar 1-3 mesi (score_3m)"]; ar = R["auc"]["Indice Armor"]
c = {"auc>=0.65": a3["Y3_primario"] >= 0.65, "ic_basso>=0.55": R["ic90_Y3_radar3m"][0] >= 0.55, "meta_e_2008>=0.60": all(a3["Y3_" + h] >= 0.60 for h in halves), "sopra_caso_p95": a3["Y3_primario"] > R["riferimento_caso_p95"],
     "sopra_armor+0.02": a3["Y3_primario"] >= ar["Y3_primario"] + 0.02, "precisione>=2xbase": (R["allerta"]["precisione"] or 0) >= 2 * R["allerta"]["frequenza_base"]}
R["regola"] = {k: bool(v) for k, v in c.items()}; R["etichetta"] = "Coerente con i casi osservati" if all(c.values()) else "Non coerente"
json.dump(R, open("scratch/sistemico_risultati.json", "w"), indent=1, default=lambda o: None if o != o else float(o) if isinstance(o, (np.floating,)) else bool(o) if isinstance(o, np.bool_) else str(o))
f = lambda x: "  -  " if x is None or x != x else f"{x:.3f}"
print("campione", R["campione"]); print("AUC"); [print(f"  {k:32s} Y3 princ {f(v['Y3_primario'])} tutte {f(v['Y3_tutte'])} Y6 {f(v['Y6_primario'])} | 97-11 {f(v['Y3_1997-2011'])} 12-26 {f(v['Y3_2012-2026'])} 08-26 {f(v['Y3_2008-2026'])}") for k, v in R["auc"].items()]
print("IC90 radar3m", [round(x, 3) for x in R["ic90_Y3_radar3m"]], "armor", [round(x, 3) for x in R["ic90_Y3_armor"]], "caso p50/p95", round(R["riferimento_caso_p50"], 3), round(R["riferimento_caso_p95"], 3))
print("allerta", R["allerta"]); [print(" ", e) for e in R["episodi"]]; print("oggi", R["oggi"]["regime"], R["oggi"]["score_3m"], R["oggi"]["score_6m"], R["oggi"]["dd252"])
print("regola", R["regola"], "->", R["etichetta"]); print("tempo", round(time.time() - t0), "s")
