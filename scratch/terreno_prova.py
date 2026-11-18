# -*- coding: utf-8 -*-
"""Prove del PROTOCOLLO_TERRENO.md (regole scritte prima). Eseguire dal repository: PYTHONPATH=src python scratch/terreno_prova.py [cartella_fred]
Scrive scratch/terreno_risultati.json e stampa le tabelle."""
import sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, "src")
from armor import store
from armor.features import closed_sp500, fwd_maxdd

FRED = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/terreno")
C_LOGIT = 0.2          # vincolo della logistica (fissato prima di calcolare)
MIN_TRAIN = 60         # mesi con esito maturato
HZ = {"E6": (126, 0.10), "E12": (252, 0.15)}
TARATURA = ("1994-01-01", "2009-12-31"); CONFERMA = ("2010-01-01", "2026-12-31")
META = (("2010-01-01", "2017-12-31"), ("2018-01-01", "2026-12-31"))

def fred(k):
    d = pd.read_csv(FRED / f"{k}.csv"); d.columns = ["date", "v"]
    s = pd.to_numeric(d["v"], errors="coerce"); s.index = pd.to_datetime(d["date"]); return s.dropna()
def rep(k): return store.load(k).dropna()

# nome: (serie, segno, ritardo_mesi, trasformazione, gruppo)
VARS = {
 "sloos": (lambda: rep("sloos"), +1, 2, "lvl", "A"), "stretta_piccole": (lambda: fred("DRTSCIS"), +1, 2, "lvl", "A"),
 "stretta_carte": (lambda: fred("DRTSCLCC"), +1, 2, "lvl", "A"), "baa10y": (lambda: rep("baa10y"), +1, 0, "lvl", "A"),
 "nfci_credit": (lambda: rep("nfci_credit"), +1, 0, "lvl", "A"), "prestiti_imprese_g6": (lambda: rep("busloans_g6"), -1, 1, "lvl", "A"),
 "insoluti_carte": (lambda: rep("delinq_cc"), +1, 5, "lvl", "B"), "insoluti_mutui": (lambda: fred("DRSFRMACBS"), +1, 5, "lvl", "B"),
 "debito_su_reddito": (lambda: fred("TDSP"), +1, 6, "lvl", "B"), "risparmio": (lambda: fred("PSAVERT"), -1, 2, "lvl", "B"),
 "tasso_mutui_var12": (lambda: fred("MORTGAGE30US"), +1, 0, "d12", "B"),
 "tasso_reale_banca": (lambda: rep("real_ff"), +1, 1, "lvl", "C"), "premio_azioni": (lambda: rep("erp"), -1, 1, "lvl", "C"),
 "rend10_var12": (lambda: rep("dgs10"), +1, 0, "d12", "C"), "curva_10a_3m": (lambda: rep("t10y3m"), -1, 0, "lvl", "C"),
 "debito_titoli_yoy": (lambda: rep("margin_yoy"), +1, 2, "lvl", "D"), "m2_yoy": (lambda: rep("m2_yoy"), -1, 2, "lvl", "D"),
 "monetari_g12": (lambda: rep("mmf_assets"), +1, 1, "g12", "D"), "liquidita_netta_13s": (lambda: rep("net_liq_13w"), -1, 0, "lvl", "D"),
 "insoluti_imprese": (lambda: rep("delinq_biz"), +1, 5, "lvl", "E"), "perdite_imprese": (lambda: rep("chargeoff_biz"), +1, 5, "lvl", "E"),
}
GRUPPI = {"A": "Credito", "B": "Famiglie", "C": "Alternative sicure", "D": "Flussi e liquidità", "E": "Imprese"}

P = closed_sp500().dropna()
ME = P.groupby([P.index.year, P.index.month]).tail(1).index          # ultima seduta di ogni mese
ME = ME[(ME >= "1994-01-01")]
GRID = pd.date_range("1975-01-31", "2026-12-31", freq="ME")           # griglia mensile per le variabili

def panel_var(s, lag, tr):
    s = s[~s.index.duplicated(keep="last")].sort_index()
    av = s.copy(); av.index = (s.index + pd.DateOffset(months=lag)) if lag else s.index
    av = av[~av.index.duplicated(keep="last")].sort_index()
    m = av.reindex(av.index.union(GRID)).ffill().reindex(GRID)
    m[m.index < av.index[0]] = np.nan
    if tr == "d12": m = m - m.shift(12)
    elif tr == "g12": m = m / m.shift(12) - 1
    return m

def zscore(m, minp=48):
    mu, sd = m.expanding(minp).mean(), m.expanding(minp).std()
    return ((m - mu) / sd.replace(0, np.nan)).clip(-4, 4)

def costruisci(panels):
    """panels: dict nome -> serie mensile grezza (già con trasformazione). Restituisce z firmati, gruppi, Terreno."""
    Z = pd.DataFrame({k: zscore(v) * VARS[k][1] for k, v in panels.items()})
    G = pd.DataFrame({g: Z[[k for k in Z.columns if VARS[k][4] == g]].mean(axis=1, skipna=True) for g in GRUPPI})
    T = G.mean(axis=1, skipna=True).where(G.notna().sum(axis=1) >= 3)
    return Z, G, T

panels = {k: panel_var(f(), lag, tr) for k, (f, sg, lag, tr, g) in VARS.items()}
Z, G, T = costruisci(panels)

def a_data(m, dates):  # valore del pannello mensile alla data (mese di appartenenza)
    idx = m.index.get_indexer(dates.to_period("M").to_timestamp("M"))
    return pd.Series(m.values[idx], index=dates)
TT = a_data(T, ME); ZZ = pd.DataFrame({k: a_data(Z[k], ME) for k in Z}); GG = pd.DataFrame({k: a_data(G[k], ME) for k in G})
pos = P.index.get_indexer(ME)

Y = {}
for nome, (h, thr) in HZ.items():
    dd = fwd_maxdd(P, h); y = (dd <= -thr).astype(float).where(dd.notna())
    Y[nome] = y.reindex(ME)

# benchmark: FHS+VIX a 6 mesi (previsione già nell'app), logistica su VIX e distanza dai massimi a 12 mesi
mp = pd.read_csv("data/modelli_preds.csv", parse_dates=["date"])
fh = mp[(mp.model == "FHS+VIX") & (mp.hz == "6m")].drop_duplicates("date").set_index("date")["p"].sort_index()
p_fhs = pd.Series(fh.reindex(fh.index.union(ME)).ffill(limit=6).reindex(ME).values, index=ME)
vix = store.load("vix").dropna(); lvix = np.log(vix.reindex(vix.index.union(ME)).ffill().reindex(ME))
dd252 = (P / P.rolling(252, 1).max() - 1).reindex(ME)

lg = lambda p: np.log(np.clip(p, 1e-3, 1 - 1e-3) / (1 - np.clip(p, 1e-3, 1 - 1e-3)))

def walk(X, y, h, c=C_LOGIT, minn=MIN_TRAIN):
    """Logistica in avanti: a ogni data solo esiti maturati (pos_j + h <= pos_i). X: array (n, k)."""
    n = len(y); out = np.full(n, np.nan); X = np.asarray(X, float); ok_x = np.isfinite(X).all(1)
    for i in range(n):
        if not ok_x[i]: continue
        mat = np.flatnonzero((pos[:i] + h <= pos[i]) & np.isfinite(y[:i]) & ok_x[:i])
        if len(mat) < minn or y[mat].sum() < 3 or y[mat].sum() > len(mat) - 3: continue
        mu, sd = X[mat].mean(0), X[mat].std(0) + 1e-9
        m = LogisticRegression(C=c, max_iter=200).fit((X[mat] - mu) / sd, y[mat])
        out[i] = m.predict_proba(((X[i] - mu) / sd)[None, :])[0, 1]
    return out

def freq(y, h):
    out = np.full(len(y), np.nan)
    for i in range(len(y)):
        mat = np.flatnonzero((pos[:i] + h <= pos[i]) & np.isfinite(y[:i]))
        if len(mat) >= 36: out[i] = y[mat].mean()
    return out

def auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, float); ok = np.isfinite(s) & np.isfinite(y); s, y = s[ok], y[ok]
    n1 = y.sum(); n0 = len(y) - n1
    if n1 < 2 or n0 < 2: return np.nan
    r = rankdata(s); return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

def boot_auc(s, y, block=12, reps=1000, seed=3):
    s, y = np.asarray(s, float), np.asarray(y, float); ok = np.isfinite(s) & np.isfinite(y); s, y = s[ok], y[ok]; n = len(y)
    rng = np.random.default_rng(seed); out = []
    for _ in range(reps):
        st = rng.integers(0, max(n - block, 1), int(np.ceil(n / block))); ix = np.concatenate([np.arange(a, min(a + block, n)) for a in st])[:n]
        v = auc(s[ix], y[ix]);
        if np.isfinite(v): out.append(v)
    return (float(np.percentile(out, 5)), float(np.percentile(out, 95))) if out else (np.nan, np.nan)

def skill(p1, p0, y, block=12, reps=1000, seed=5):
    p1, p0, y = np.asarray(p1, float), np.asarray(p0, float), np.asarray(y, float); ok = np.isfinite(p1) & np.isfinite(p0) & np.isfinite(y)
    e1, e0 = ((p1 - y) ** 2)[ok], ((p0 - y) ** 2)[ok]; n = len(e1)
    if n < 12: return np.nan, (np.nan, np.nan), n
    rng = np.random.default_rng(seed); out = []
    for _ in range(reps):
        st = rng.integers(0, max(n - block, 1), int(np.ceil(n / block))); ix = np.concatenate([np.arange(a, min(a + block, n)) for a in st])[:n]
        out.append(1 - e1[ix].sum() / e0[ix].sum())
    return float((1 - e1.sum() / e0.sum()) * 100), (float(np.percentile(out, 5) * 100), float(np.percentile(out, 95) * 100)), n

def sel(period): return (ME >= period[0]) & (ME <= period[1])
R = {"config": {"C": C_LOGIT, "min_train": MIN_TRAIN, "n_date": int(len(ME))}, "var_singole": {}, "gruppi": {}, "terreno": {}, "design": {}, "placebo": {}}

# ---- 1. AUC delle variabili singole, dei gruppi e del Terreno (tutte riportate) ----
def auc_tab(score, y, per):
    m = sel(per); return auc(np.asarray(score)[m], np.asarray(y)[m])
for nome, (h, thr) in HZ.items():
    y = Y[nome].values
    for k in ZZ.columns:
        R["var_singole"].setdefault(k, {})[nome] = {"taratura": auc_tab(ZZ[k].values, y, TARATURA), "conferma": auc_tab(ZZ[k].values, y, CONFERMA)}
    for g in GG.columns:
        R["gruppi"].setdefault(g, {})[nome] = {"taratura": auc_tab(GG[g].values, y, TARATURA), "conferma": auc_tab(GG[g].values, y, CONFERMA)}
    m = sel(CONFERMA); s_ = TT.values
    R["terreno"][nome] = {"taratura": auc_tab(s_, y, TARATURA), "conferma": auc_tab(s_, y, CONFERMA), "tutto": auc(s_, y),
                          "ci_conferma": boot_auc(s_[m], y[m]), "ci_taratura": boot_auc(s_[sel(TARATURA)], y[sel(TARATURA)]),
                          "meta1": auc_tab(s_, y, META[0]), "meta2": auc_tab(s_, y, META[1]),
                          "eventi_conferma": int(np.nansum(y[m])), "n_conferma": int(np.isfinite(y[m]).sum() & True) if False else int(np.isfinite(y[m]).sum()),
                          "eventi_taratura": int(np.nansum(y[sel(TARATURA)])), "n_taratura": int(np.isfinite(y[sel(TARATURA)]).sum())}

# ---- 2. Prova del sosia ----
def placebo(nrep=200, seed=11):
    rng = np.random.default_rng(seed); out = {n: {"taratura": [], "conferma": []} for n in HZ}
    gr = [VARS[k][4] for k in VARS]
    for _ in range(nrep):
        sp = {}
        for j, k in enumerate(VARS):
            rho = rng.choice([0.9, 0.97, 0.99]); e = rng.standard_normal(len(GRID)); x = np.zeros(len(GRID))
            for i in range(1, len(GRID)): x[i] = rho * x[i - 1] + e[i]
            s = pd.Series(x, index=GRID); s[s.index < "1990-01-01"] = np.nan; sp[k] = s
        _, _, Tp = costruisci(sp); Tm = a_data(Tp, ME).values
        for n in HZ:
            y = Y[n].values; out[n]["taratura"].append(auc_tab(Tm, y, TARATURA)); out[n]["conferma"].append(auc_tab(Tm, y, CONFERMA))
    return {n: {p: {"p50": float(np.nanpercentile(v, 50)), "p95": float(np.nanpercentile(v, 95)), "p05": float(np.nanpercentile(v, 5)), "max": float(np.nanmax(v))} for p, v in d.items()} for n, d in out.items()}
R["placebo"] = placebo()

# ---- 3. Probabilità: D1 (Terreno) e D2 (cinque gruppi), contro frequenza storica e contro il mercato ----
PRED = {}
for nome, (h, thr) in HZ.items():
    y = Y[nome].values
    f0 = freq(y, h)
    d1 = walk(TT.values[:, None], y, h); d2 = walk(GG.values, y, h)
    if nome == "E6":
        mk_x = np.column_stack([lg(p_fhs.values)]); mk_name = "FHS+VIX"
        mk_raw = p_fhs.values
    else:
        mk_x = np.column_stack([lvix.values, dd252.values]); mk_name = "VIX+distanza dai massimi"; mk_raw = None
    mk = walk(mk_x, y, h)
    mk_t = walk(np.column_stack([mk_x, TT.values]), y, h)
    mk_g = walk(np.column_stack([mk_x, GG.values]), y, h)
    PRED[nome] = dict(f0=f0, d1=d1, d2=d2, mk=mk, mk_t=mk_t, mk_g=mk_g, y=y)
    r = {"mercato": mk_name}
    for per_n, per in (("taratura", TARATURA), ("conferma", CONFERMA)):
        m = sel(per)
        r[per_n] = {"D1_vs_freq": skill(d1[m], f0[m], y[m]), "D2_vs_freq": skill(d2[m], f0[m], y[m]), "mercato_vs_freq": skill(mk[m], f0[m], y[m]),
                    "mercato+Terreno_vs_mercato": skill(mk_t[m], mk[m], y[m]), "mercato+gruppi_vs_mercato": skill(mk_g[m], mk[m], y[m])}
        if mk_raw is not None: r[per_n]["mercato+Terreno_vs_FHS_grezzo"] = skill(mk_t[m], mk_raw[m], y[m])
    R["design"][nome] = r

# scelta del disegno in taratura: miglior guadagno medio sui due orizzonti
sc = {d: np.nanmean([R["design"][n]["taratura"][f"{d}_vs_freq"][0] for n in HZ]) for d in ("D1", "D2")}
R["design_scelto"] = max(sc, key=sc.get); R["design_punteggio_taratura"] = sc

# ---- 4. Oggi ----
oggi = pd.Timestamp(pd.Timestamp.today().normalize()).to_period("M").to_timestamp("M")
zi = Z.loc[:oggi].iloc[-1]; gi = G.loc[:oggi].iloc[-1]; ti = float(T.loc[:oggi].iloc[-1])
perc = lambda x, ser: float((ser.dropna() <= x).mean() * 100)
R["oggi"] = {"data_pannello": str(T.loc[:oggi].index[-1].date()), "terreno": ti, "percentile_storico": perc(ti, T[T.index >= "1994-01-01"]),
             "gruppi": {g: {"nome": GRUPPI[g], "z": float(gi[g]) if np.isfinite(gi[g]) else None} for g in GRUPPI},
             "variabili": {k: (float(zi[k]) if np.isfinite(zi[k]) else None) for k in Z.columns}}
for n in HZ:
    d = PRED[n]; ix = np.flatnonzero(np.isfinite(d["d1"]))[-1] if np.isfinite(d["d1"]).any() else None
    R["oggi"][n] = {"D1": float(d["d1"][ix]) if ix is not None else None, "freq": float(d["f0"][ix]) if ix is not None else None, "data": str(ME[ix].date()) if ix is not None else None}
json.dump(R, open("scratch/terreno_risultati.json", "w"), indent=1, default=lambda o: None if o != o else float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else str(o))
pd.to_pickle({"ME": ME, "TT": TT, "ZZ": ZZ, "GG": GG, "Y": Y, "PRED": PRED}, "/tmp/terreno/pred.pkl")

# ---- stampa ----
f = lambda x: "  -  " if x is None or x != x else f"{x:.3f}"
print("N date", len(ME), {n: (int(np.nansum(Y[n])), int(Y[n].notna().sum())) for n in HZ})
print("\nTERRENO (punteggio unico) AUC")
for n in HZ:
    t = R["terreno"][n]; p = R["placebo"][n]
    print(n, "taratura", f(t["taratura"]), "conferma", f(t["conferma"]), "CI90 conf", tuple(round(x, 3) for x in t["ci_conferma"]), "metà", f(t["meta1"]), f(t["meta2"]),
          "| sosia conferma p50/p95/max", round(p["conferma"]["p50"], 3), round(p["conferma"]["p95"], 3), round(p["conferma"]["max"], 3),
          "| eventi/n conferma", t["eventi_conferma"], t["n_conferma"])
print("\nGRUPPI AUC (taratura / conferma)")
for g in GRUPPI:
    print(g, GRUPPI[g], *[f"{n}: {f(R['gruppi'][g][n]['taratura'])}/{f(R['gruppi'][g][n]['conferma'])}" for n in HZ])
print("\nVARIABILI SINGOLE AUC (taratura / conferma)")
for k in ZZ.columns:
    print(f"{k:22s}", *[f"{n}: {f(R['var_singole'][k][n]['taratura'])}/{f(R['var_singole'][k][n]['conferma'])}" for n in HZ])
print("\nPROBABILITA' (guadagno % di errore, intervallo 90%, n)")
for n in HZ:
    for per in ("taratura", "conferma"):
        print(n, per, {k: (round(v[0], 1), tuple(round(x, 1) for x in v[1]), v[2]) for k, v in R["design"][n][per].items() if k != "mercato"})
print("Disegno scelto:", R["design_scelto"], {k: round(v, 2) for k, v in sc.items()})
print("\nOGGI", json.dumps(R["oggi"], default=float)[:900])
