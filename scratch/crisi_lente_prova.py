# -*- coding: utf-8 -*-
"""Prove del PROTOCOLLO_CRISI_LENTE.md (regole scritte prima). Eseguire dal repository: PYTHONPATH=src python scratch/crisi_lente_prova.py
Scrive scratch/crisi_lente_risultati.json e stampa le tabelle."""
import sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, "src")
from armor import store
from armor.features import closed_sp500, fwd_maxdd
from armor.terreno import pannello_var, zscore

def S(k): return store.load(k).dropna()
# nome: (serie, segno, ritardo, trasformazione, gruppo)
def gs10():
    a, b = S("gs10_shiller"), S("gs10_m"); a = a[a.index < b.index[0]]; return pd.concat([a, b]).sort_index()
def spread_baa(): b, a = S("baa_m"), S("aaa_m"); return (b - a).dropna()
def curva(): g, t = gs10(), S("tb3ms"); return (g.groupby(g.index.to_period("M")).last().rename(lambda p: p.to_timestamp("M")) - t.groupby(t.index.to_period("M")).last().rename(lambda p: p.to_timestamp("M"))).dropna()
VARS = {
 "cape": (lambda: np.log(S("cape_m")), +1, 0, "lvl", "V"),
 "spread_baa_aaa": (spread_baa, +1, 1, "lvl", "K"), "prestiti_imprese_g6": (lambda: S("busloans_g6"), -1, 1, "lvl", "K"), "debito_privato_5a": (lambda: S("credit_ratio"), +1, 5, "d60", "K"),
 "tasso3m_var12": (lambda: S("tb3ms"), +1, 1, "d12", "L"), "curva_10a_3m": (curva, -1, 1, "lvl", "L"), "m2_yoy": (lambda: S("m2_yoy"), -1, 2, "lvl", "L"), "tasso_reale": (lambda: S("real_ff"), +1, 1, "lvl", "L"),
 "produzione_g12": (lambda: S("indpro_g12"), -1, 1, "lvl", "M"), "disoccupazione_var12": (lambda: S("unrate"), +1, 1, "d12", "M"), "inflazione": (lambda: S("cpi_yoy_lungo"), +1, 1, "lvl", "M"),
}
GR = ["V", "K", "L", "M"]
GRID = pd.date_range("1914-01-31", "2026-12-31", freq="ME")

def pv(s, lag, tr):
    if tr == "d60":
        s = s.dropna(); m = pannello_var(s, lag, "lvl", GRID); return m - m.shift(60)
    return pannello_var(s, lag, tr, GRID)

def costruisci(panels):
    Z = pd.DataFrame({k: zscore(v) * VARS[k][1] for k, v in panels.items()})
    G = pd.DataFrame({g: Z[[k for k in Z.columns if VARS[k][4] == g]].mean(axis=1, skipna=True) for g in GR})
    T = G.mean(axis=1, skipna=True).where(G.notna().sum(axis=1) >= 3)
    return Z, G, T

P = closed_sp500().dropna()
ME = P.groupby([P.index.year, P.index.month]).tail(1).index; ME = ME[(ME >= "1928-01-01")]
pos = P.index.get_indexer(ME)
dd = fwd_maxdd(P, 504); f4 = P.shift(-1008); f3 = P.shift(-756)
valid4 = f4.notna() & dd.notna()
L = ((dd <= -0.20) & (f4 < P)).astype(float).where(valid4)
Q = ((dd <= -0.20) & (f4 >= P)).astype(float).where(valid4)
Sg = (f3 < P).astype(float).where(f3.notna())
Y = {"L": L.reindex(ME).values, "S": Sg.reindex(ME).values, "Q": Q.reindex(ME).values}

def a_data(m, dates): return pd.Series(m.values[m.index.get_indexer(dates.to_period("M").to_timestamp("M"))], index=dates)
panels = {k: pv(f(), lag, tr) for k, (f, sg, lag, tr, g) in VARS.items()}
Z, G, T = costruisci(panels)
TT = a_data(T, ME); ZZ = pd.DataFrame({k: a_data(Z[k], ME) for k in Z}); GG = pd.DataFrame({k: a_data(G[k], ME) for k in G})
cape_sc = ZZ["cape"].values
ma = P.rolling(210).mean(); trend_sc = (-(P / ma - 1)).reindex(ME).values

PER = {"retro 1928-1952": ("1928-01-01", "1952-12-31"), "taratura 1953-1989": ("1953-01-01", "1989-12-31"), "conferma 1990-2022": ("1990-01-01", "2022-12-31")}
def sel(p): return (ME >= PER[p][0]) & (ME <= PER[p][1])
def auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, float); ok = np.isfinite(s) & np.isfinite(y); s, y = s[ok], y[ok]; n1 = y.sum(); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    return float((rankdata(s)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def boot(s, y, block=36, reps=1000, seed=3):
    s, y = np.asarray(s, float), np.asarray(y, float); ok = np.isfinite(s) & np.isfinite(y); s, y = s[ok], y[ok]; n = len(y); rng = np.random.default_rng(seed); out = []
    for _ in range(reps):
        st = rng.integers(0, max(n - block, 1), int(np.ceil(n / block))); ix = np.concatenate([np.arange(a, min(a + block, n)) for a in st])[:n]; v = auc(s[ix], y[ix])
        if np.isfinite(v): out.append(v)
    return (float(np.percentile(out, 5)), float(np.percentile(out, 95))) if out else (np.nan, np.nan)

R = {"n_date": len(ME), "eventi": {k: int(np.nansum(v)) for k, v in Y.items()}, "validi": {k: int(np.isfinite(v).sum()) for k, v in Y.items()}, "auc": {}, "alarme": {}, "episodi": [], "var": {}, "placebo": {}}
# ---- AUC ----
for nome, sc in (("Terreno lento", TT.values), ("CAPE da solo", cape_sc), ("Tendenza (sotto media 10 mesi)", trend_sc)) + tuple((f"gruppo {g}", GG[g].values) for g in GR):
    R["auc"][nome] = {}
    for tg in ("L", "S", "Q"):
        R["auc"][nome][tg] = {p: auc(sc[sel(p)], Y[tg][sel(p)]) for p in PER}
for k in ZZ.columns: R["var"][k] = {p: auc(ZZ[k].values[sel(p)], Y["L"][sel(p)]) for p in PER}
R["ci_L"] = {p: boot(TT.values[sel(p)], Y["L"][sel(p)]) for p in PER}
R["eventi_per_periodo"] = {p: (int(np.nansum(Y["L"][sel(p)])), int(np.isfinite(Y["L"][sel(p)]).sum())) for p in PER}

# ---- allarme: sopra l'80° percentile della propria storia (minimo 120 mesi) ----
def perc_espandibile(x, minn=120):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        h = x[:i + 1]; h = h[np.isfinite(h)]
        if len(h) >= minn and np.isfinite(x[i]): out[i] = (h <= x[i]).mean()
    return out
PT = perc_espandibile(TT.values); AL = PT >= 0.80
PC = perc_espandibile(cape_sc); ALC = PC >= 0.80
for nome, al in (("Terreno lento", AL), ("CAPE da solo", ALC)):
    R["alarme"][nome] = {}
    for p in PER:
        m = sel(p) & np.isfinite(PT) & np.isfinite(Y["L"]); y = Y["L"][m]; a = al[m]
        if y.sum() < 1: R["alarme"][nome][p] = None; continue
        R["alarme"][nome][p] = {"sensibilita": float(a[y == 1].mean()), "falsi_allarmi": float(a[y == 0].mean()), "freq_L_con_allarme": float(y[a].mean()) if a.any() else None, "freq_L_senza": float(y[~a].mean()) if (~a).any() else None, "quota_mesi_allarme": float(a.mean()), "n": int(m.sum())}
# ---- episodi ----
yl = pd.Series(Y["L"], index=ME); ev = yl[yl == 1].index
eps = [];
for d in ev:
    if not eps or (d - eps[-1][-1]).days > 366: eps.append([d])
    else: eps[-1].append(d)
al_s = pd.Series(AL & np.isfinite(PT), index=ME)
for e in eps:
    a0 = e[0]; fin = a0 - pd.DateOffset(months=24); w = al_s[(al_s.index >= fin) & (al_s.index <= a0)]
    on = w[w]; lead = int(round((a0 - on.index[0]).days / 30.4)) if len(on) else None
    ts = TT[(TT.index >= fin) & (TT.index <= a0)]
    R["episodi"].append({"inizio": str(a0.date()), "fine": str(e[-1].date()), "mesi_L": len(e), "allarme_nei_24_mesi_prima": bool(len(on)), "anticipo_mesi": lead, "mesi_allarme_su_25": int(len(on)), "terreno_medio_prima": float(ts.mean()) if len(ts.dropna()) else None, "perc_medio_prima": float(np.nanmean(PT[(ME >= fin) & (ME <= a0)])) if np.isfinite(PT[(ME >= fin) & (ME <= a0)]).any() else None})
# ---- sosia ----
def placebo(nrep=200, seed=11):
    rng = np.random.default_rng(seed); out = {p: [] for p in PER}; gsizes = [VARS[k][4] for k in VARS]
    for _ in range(nrep):
        sp = {}
        for k in VARS:
            rho = rng.choice([0.9, 0.97, 0.99]); e = rng.standard_normal(len(GRID)); x = np.zeros(len(GRID))
            for i in range(1, len(GRID)): x[i] = rho * x[i - 1] + e[i]
            s = pd.Series(x, index=GRID); s[s.index < "1919-01-01"] = np.nan; sp[k] = s
        Zp = pd.DataFrame({k: zscore(v) * VARS[k][1] for k, v in sp.items()}); Gp = pd.DataFrame({g: Zp[[k for k in Zp.columns if VARS[k][4] == g]].mean(axis=1, skipna=True) for g in GR})
        Tp = Gp.mean(axis=1, skipna=True).where(Gp.notna().sum(axis=1) >= 3); Tm = a_data(Tp, ME).values
        for p in PER: out[p].append(auc(Tm[sel(p)], Y["L"][sel(p)]))
    return {p: {"p50": float(np.nanpercentile(v, 50)), "p95": float(np.nanpercentile(v, 95)), "max": float(np.nanmax(v))} for p, v in out.items()}
R["placebo"] = placebo()
# ---- oggi ----
oggi = pd.Timestamp.today().normalize(); chiuso = (oggi.to_period("M") - 1).to_timestamp("M")
ti = float(T.loc[:chiuso].dropna().iloc[-1]); d_ult = T.loc[:chiuso].dropna().index[-1]
storia = T[T.index >= "1953-01-01"].dropna(); hist = T.loc[:d_ult].dropna()
R["oggi"] = {"data": str(d_ult.date()), "terreno_lento": ti, "percentile": float((hist <= ti).mean() * 100), "allarme": bool((hist <= ti).mean() >= 0.80),
             "gruppi": {g: (float(G.loc[d_ult, g]) if np.isfinite(G.loc[d_ult, g]) else None) for g in GR}, "variabili": {k: (float(Z.loc[d_ult, k]) if np.isfinite(Z.loc[d_ult, k]) else None) for k in Z.columns}}
pd.to_pickle({"ME": ME, "TT": TT, "PT": PT, "AL": AL, "Y": Y, "ZZ": ZZ, "GG": GG}, "/tmp/terreno/cl.pkl")
json.dump(R, open("scratch/crisi_lente_risultati.json", "w"), indent=1, default=lambda o: None if o != o else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else str(o))
f = lambda x: "  -  " if x is None or x != x else f"{x:.2f}"
print("date", len(ME), "eventi", R["eventi"], "validi", R["validi"]); print("eventi L per periodo (eventi, mesi validi):", R["eventi_per_periodo"])
print("\nAUC (retro / taratura / conferma)")
for n, d in R["auc"].items():
    print(f"{n:34s}", *[f"{tg}: " + "/".join(f(d[tg][p]) for p in PER) for tg in ("L", "S", "Q")])
print("IC90 Terreno lento L:", {p: tuple(round(x, 2) for x in v) for p, v in R["ci_L"].items()})
print("Sosia p50/p95/max L:", {p: tuple(round(v[k], 2) for k in ("p50", "p95", "max")) for p, v in R["placebo"].items()})
print("\nVariabili singole L (retro/taratura/conferma)")
for k, d in R["var"].items(): print(f"{k:24s}", "/".join(f(d[p]) for p in PER))
print("\nALLARME 80°")
for n, d in R["alarme"].items():
    for p, v in d.items(): print(f"{n:16s} {p:20s}", None if v is None else {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()})
print("\nEPISODI di crisi lenta (L=1)")
for e in R["episodi"]: print(e)
print("\nOGGI", json.dumps(R["oggi"], default=float)[:700])
