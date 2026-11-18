# -*- coding: utf-8 -*-
"""Prove del PROTOCOLLO_CRISI_LENTE_2.md (regole scritte prima). Eseguire dal repository: PYTHONPATH=src python scratch/crisi_lente2_prova.py
Scrive scratch/crisi_lente2_risultati.json e data/crisi_lente_prova.json."""
import sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, "src")
from armor import crisi_lente as cl
from armor.features import closed_sp500, fwd_maxdd

P = closed_sp500().dropna()
ME = P.groupby([P.index.year, P.index.month]).tail(1).index; ME = ME[ME >= "1995-01-01"]
mese = lambda idx: idx.to_period("M").to_timestamp("M")

# bersaglio (definizione per episodi: Emendamento 1 del protocollo)
cm = P.cummax(); ddp = P / cm - 1; seg = (P >= cm).cumsum()
episodi_lenti = []
for k, g in P.groupby(seg):
    if len(g) < 2: continue
    mn = ddp.loc[g.index].min(); peak = g.index[0]
    if peak >= pd.Timestamp("1989-01-01") and mn <= -0.15 and len(g) >= 378: episodi_lenti.append((peak, g.index))
RLs = pd.Series(0.0, index=P.index)
for peak, gi in episodi_lenti:
    i0 = P.index.get_loc(peak); fine10 = gi[(ddp.loc[gi] <= -0.10).values][0]
    RLs.iloc[max(i0 - 504, 0):P.index.get_loc(fine10) + 1] = 1.0
RL = RLs.reindex(ME)
vicino = (P / P.rolling(252, 1).max() - 1 >= -0.05).reindex(ME)          # non ancora in crisi
ok = vicino.values & RL.notna().values
base = cl.serie_base()
Pn = cl.pannelli(base, "2026-12-31"); PC = cl.percentili(Pn); S = cl.punteggi(PC)
Sm = S.reindex(mese(ME)); Sm.index = ME
y = RL.values

def auc(s, yy):
    s, yy = np.asarray(s, float), np.asarray(yy, float); m = np.isfinite(s) & np.isfinite(yy); s, yy = s[m], yy[m]; n1 = yy.sum(); n0 = len(yy) - n1
    return np.nan if n1 < 3 or n0 < 3 else float((rankdata(s)[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def boot(s, yy, block=24, reps=1000, seed=3):
    s, yy = np.asarray(s, float), np.asarray(yy, float); m = np.isfinite(s) & np.isfinite(yy); s, yy = s[m], yy[m]; n = len(yy); rng = np.random.default_rng(seed); o = []
    for _ in range(reps):
        st = rng.integers(0, max(n - block, 1), int(np.ceil(n / block))); ix = np.concatenate([np.arange(a, min(a + block, n)) for a in st])[:n]; v = auc(s[ix], yy[ix])
        if np.isfinite(v): o.append(v)
    return (float(np.percentile(o, 5)), float(np.percentile(o, 95))) if o else (np.nan, np.nan)

R = {"n_mesi_validi": int(ok.sum()), "mesi_RL": int(np.nansum(y[ok])), "auc": {}, "episodi": [], "allarme": {}}
cape_p = PC["cape"].reindex(mese(ME)).values
trend = (-(P / P.rolling(210).mean() - 1)).reindex(ME).values
conf = {"Punteggio (max delle due chiavi)": Sm["score"].values, "Chiave 1 (credito facile + tassi)": Sm["k1"].values, "Chiave 2 (stretta)": Sm["k2"].values, "Boom da solo": Sm["boom"].values, "Shock da solo": Sm["shock"].values,
        "Valutazioni (CAPE) da sole": cape_p, "Tendenza (sotto media 10 mesi)": trend}
for n, sc in conf.items(): R["auc"][n] = auc(np.where(ok, sc, np.nan), y)
R["ci_score"] = boot(np.where(ok, Sm["score"].values, np.nan), y)
# punteggio "Terreno lento" della prima prova sullo stesso insieme (se disponibile)
try:
    from armor import crisi_lente_v1 as v1  # noqa
except Exception:
    pass

# allarme e episodi
sc = pd.Series(Sm["score"].values, index=ME); al = (sc >= cl.SOGLIA); mod = (sc >= cl.MODERATA)
k1 = pd.Series(Sm["k1"].values, index=ME); k2 = pd.Series(Sm["k2"].values, index=ME)
rl = pd.Series(np.where(ok, y, np.nan), index=ME)
m_all = np.isfinite(rl.values)
yy = rl.values[m_all]; a = al.values[m_all]
R["allarme"] = {"falsi_allarmi": float(a[yy == 0].mean()), "sensibilita": float(a[yy == 1].mean()), "quota_tempo_allarme": float(a.mean()), "P_RL_con_allarme": float(yy[a].mean()) if a.any() else None, "P_RL_senza": float(yy[~a].mean()),
                "moderata_o_piu_falsi": float(mod.values[m_all][yy == 0].mean()), "n": int(m_all.sum())}
ev = rl[rl == 1].index; eps = []
for d in ev:
    if not eps or (d - eps[-1][-1]).days > 366: eps.append([d])
    else: eps[-1].append(d)
nomi = {1: "Bolla internet (2000-02)", 2: "Crisi finanziaria (2007-09)", 3: "Tassi e inflazione (2022)"}
for i, e in enumerate(eps, 1):
    a0 = e[0]; fin = a0 - pd.DateOffset(months=24); w = al[(al.index >= fin) & (al.index <= a0)]; on = w[w]
    chi = None
    if len(on):
        d1 = on.index[0]; chi = "chiave 1" if (k1.loc[d1] >= k2.loc[d1]) else "chiave 2"
    R["episodi"].append({"nome": nomi.get(i, str(a0.date())), "primo_mese": str(a0.date()), "ultimo_mese": str(e[-1].date()), "mesi": len(e), "allarme_prima": bool(len(on)), "anticipo_mesi": None if not len(on) else int(round((a0 - on.index[0]).days / 30.4)),
                         "mesi_allarme_su_25": int(len(on)), "chiave_prima": chi, "punteggio_massimo_prima": float(sc[(sc.index >= fin) & (sc.index <= a0)].max()),
                         "k1_max": float(k1[(k1.index >= fin) & (k1.index <= a0)].max()), "k2_max": float(k2[(k2.index >= fin) & (k2.index <= a0)].max())})
# sosia
def placebo(nrep=200, seed=11):
    rng = np.random.default_rng(seed); GR = pd.date_range("1975-01-31", "2026-12-31", freq="ME"); out = []
    for _ in range(nrep):
        Pn_ = pd.DataFrame(index=GR)
        for c in Pn.columns:
            rho = rng.choice([0.9, 0.97, 0.99]); e = rng.standard_normal(len(GR)); x = np.zeros(len(GR))
            for i in range(1, len(GR)): x[i] = rho * x[i - 1] + e[i]
            Pn_[c] = x
        Sp = cl.punteggi(cl.percentili(Pn_)).reindex(mese(ME)); out.append(auc(np.where(ok, Sp["score"].values, np.nan), y))
    return {"p50": float(np.nanpercentile(out, 50)), "p95": float(np.nanpercentile(out, 95)), "max": float(np.nanmax(out))}
R["sosia"] = placebo()
# regola
c1 = all(e["allarme_prima"] for e in R["episodi"]) and len(R["episodi"]) >= 3
c2 = R["allarme"]["falsi_allarmi"] <= 0.25; c3 = R["auc"]["Punteggio (max delle due chiavi)"] >= 0.70; c4 = R["auc"]["Punteggio (max delle due chiavi)"] > R["sosia"]["p95"]
R["regola"] = {"allarme_prima_di_tutti": bool(c1), "falsi_allarmi_ok": bool(c2), "auc_ok": bool(c3), "sopra_sosia": bool(c4)}; R["etichetta"] = "coerente con i casi osservati" if (c1 and c2 and c3 and c4) else "non coerente"
json.dump(R, open("scratch/crisi_lente2_risultati.json", "w"), indent=1, default=lambda o: None if o != o else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o))
pd.to_pickle({"ME": ME, "S": Sm, "ok": ok, "y": y}, "/tmp/terreno/cl2.pkl")
f = lambda x: "  -  " if x is None or x != x else f"{x:.2f}"
print("mesi validi (non ancora in crisi)", R["n_mesi_validi"], "mesi RL", R["mesi_RL"])
print("AUC:", {k: f(v) for k, v in R["auc"].items()}); print("IC90 punteggio", tuple(round(x, 2) for x in R["ci_score"]), "sosia", {k: round(v, 2) for k, v in R["sosia"].items()})
print("Allarme:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in R["allarme"].items()})
for e in R["episodi"]: print(e)
print("Regola:", R["regola"], "->", R["etichetta"])
