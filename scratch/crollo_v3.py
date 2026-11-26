"""Esegue PROTOCOLLO_CROLLO_V3.md (commit 00df00f)."""
import json, sys, warnings
import numpy as np, pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra
from armor import store, indice_crollo as ic, grafico_indici as gi

X0 = ic.calcola_serie(); cal = X0.index; sp = X0["sp500"]
FAM = [c for c in X0.columns if c.startswith("f") and c[1].isdigit() and "_" in c]
F0 = X0[FAM].copy()
# --- parti della formula di Gemini
spf = store.load("sp500").dropna(); spf = spf[~spf.index.duplicated()]
g = lambda sid, lag=1: ic._lag(store.load(sid).dropna(), lag).reindex(spf.index).ffill()
vix, vix3, skew = g("vix"), g("vix3m"), g("skew")
ter = (ic._pr_mobile(g("cape_m", 31)) + ic._pr_mobile(g("dgs10")) + ic._pr_mobile(g("baa10y"))) / 3
s20, s50 = spf / spf.rolling(20).mean() - 1, spf / spf.rolling(50).mean() - 1
ant = (ic._pr_mobile((s20 + s50) / 2) + ic._pr_mobile(vix / vix.rolling(60).mean()) + ic._pr_mobile(skew)) / 3
vol20 = spf.pct_change().rolling(20).std() * np.sqrt(252)
inn = (ic._pr_mobile(vix / vix3) + ic._pr_mobile(vol20) + ic._pr_mobile(vix.pct_change(5))) / 3
F1 = F0.copy(); F1["g_terreno"], F1["g_anticipo"], F1["g_innesco"] = ter.reindex(cal), ant.reindex(cal), inn.reindex(cal)
# --- dati nuovi
def pctx(s): return ic._pct(s.dropna())
def lagcal(s, lag=1): return ic._lag(s.dropna(), lag).reindex(cal).ffill()
N = pd.DataFrame(index=cal)
N["n_vix9d"] = lagcal(pctx(store.load("cboe_vix9d_close") / store.load("cboe_vix").reindex(store.load("cboe_vix9d_close").index).ffill() if False else store.load("cboe_vix9d_close")))
v9 = store.load("cboe_vix9d_close").dropna(); vx = store.load("vix").dropna().reindex(v9.index).ffill()
N["n_vix9d"] = lagcal(pctx(v9 / vx))
N["n_vvix"] = lagcal(pctx(store.load("cboe_vvix_vvix")))
N["n_ciss"] = pd.concat([lagcal(pctx(store.load(f"bce_ciss_contr_{k}"))) for k in ("banche", "monetario", "azioni", "obbligazioni", "cambi")], axis=1).mean(axis=1)
sov = store.load("bce_sov_area_euro_pesata").dropna()
N["n_sov"] = (lagcal(pctx(sov)) + lagcal(pctx(sov - sov.shift(20)))) / 2
for nome, sid in (("n_mom", "ff_momentum_mom"), ("n_smb", "ff_fattori3_smb"), ("n_hml", "ff_fattori3_hml")):
    s = store.load(sid).dropna() / 100; N[nome] = lagcal(pctx(s.rolling(20).sum()))
ind = pd.concat([store.load(f).dropna() for f in [p.stem for p in (ic.DATA / "series").glob("ff_settori49_*.csv")]], axis=1)
N["n_disp49"] = lagcal(pctx(ind.rolling(20).sum().std(axis=1)))
F2 = F1.join(N)

# --- etichette
c = sp.to_numpy()
fm10 = pd.concat([sp.shift(-i) for i in range(1, 11)], axis=1).min(axis=1)
Ya = ((fm10 / sp - 1) <= -0.04).astype(float); Ya[fm10.isna()] = np.nan
fm60 = pd.concat([sp.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
picco = sp.rolling(252, min_periods=60).max()
Yb = ((fm60 / picco - 1) <= -0.10).astype(float); Yb[fm60.isna()] = np.nan

def prepara(F, logit):
    M = F.copy()
    return (M.fillna(50.0) / 100.0) if logit else (M / 100.0)

def walk(F, target, kind):
    logit = kind == "L"; M = prepara(F, logit); y = target
    out = pd.Series(np.nan, index=cal)
    for anno in range(2001, cal[-1].year + 1):
        ini = pd.Timestamp(f"{anno}-01-01"); i0 = cal.searchsorted(ini)
        if i0 >= len(cal): break
        fin = pd.Timestamp(f"{anno + 1}-01-01"); i1 = cal.searchsorted(fin)
        tr = np.arange(0, max(0, i0 - 70))
        tr = tr[(~np.isnan(y.to_numpy()[tr])) & (cal[tr] >= "1990-01-02")]
        if logit: tr = tr[~M.iloc[tr].isna().any(axis=1).to_numpy()]
        if len(tr) < 1500: continue
        if logit: mod = LogisticRegression(C=0.5, max_iter=500)
        else: mod = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=200, l2_regularization=1.0, random_state=0)
        cols = M.columns[M.iloc[tr].notna().sum() > 200]   # colonne senza dati nell'addestramento: nessuna informazione (come NaN)
        mod.fit(M.iloc[tr][cols].to_numpy(), y.to_numpy()[tr].astype(int))
        te = np.arange(i0, min(i1, len(cal)))
        out.iloc[te] = mod.predict_proba(M.iloc[te][cols].to_numpy())[:, 1]
    return out

def pexp(s):   # percentile espanso da 2001
    return s.dropna().expanding(min_periods=252).rank(pct=True).reindex(cal)

def scala(p):
    q = pexp(p) if p.name != "pct" else p
    idx = pd.Series(np.nan, index=cal)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b); idx[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return idx.clip(1, 100)

CAND = [("C1_L_F1_a", "L", F1, "a"), ("C2_L_F1_ab", "L", F1, "ab"), ("C3_G_F1_a", "G", F1, "a"), ("C4_G_F1_ab", "G", F1, "ab"),
        ("C5_L_F2_a", "L", F2, "a"), ("C6_L_F2_ab", "L", F2, "ab"), ("C7_G_F2_a", "G", F2, "a"), ("C8_G_F2_ab", "G", F2, "ab"),
        ("C9_L_F0_ab", "L", F0, "ab"), ("C10_G_F0_ab", "G", F0, "ab")]
SC = {}
cache = {}
for nome, kind, F, tg in CAND:
    pa = walk(F, Ya, kind); sa = pexp(pa)
    if tg == "ab":
        pb = walk(F, Yb, kind); sb = pexp(pb); sc = (sa + sb) / 2
    else: sc = sa
    sc.name = "pct"; SC[nome] = sc; print(nome, "fatto", flush=True)
# riferimenti sullo stesso periodo
ref_old = X0["punteggio"]; ref_g1 = ic.punteggio_unificato(30000).reindex(cal)
for nome, s in (("RIF_vecchio", ref_old), ("RIF_gemini", ref_g1)):
    q = s[s.index >= "2001-01-01"].expanding(min_periods=252).rank(pct=True).reindex(cal); q.name = "pct"; SC[nome] = q
IDX = {n: scala(s) for n, s in SC.items()}

calmo, _ = gi._maschere(); calmo = calmo.reindex(cal).fillna(False).astype(bool)
fuori = finestra(cal, ESTERNI)
for dd in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(dd)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
dd_ora = sp / picco - 1
PK = [cal.searchsorted(pd.Timestamp(p)) for p in ("2018-01-26", "2018-09-20", "2022-01-03", "2023-02-02", "2024-07-16")]
S = sp.to_numpy()
def auc_y(v, y, mask):
    m = mask & v.notna() & y.notna()
    a = v[m].to_numpy(); yy = y[m].to_numpy().astype(int)
    if yy.sum() < 5 or (1 - yy).sum() < 5: return np.nan
    r = rankdata(a); n1 = yy.sum(); n0 = len(yy) - n1
    return float((r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
sel = (cal >= "2001-01-01") & (cal <= "2014-12-31"); ver = cal >= "2015-01-01"
selm, verm = pd.Series(sel, index=cal), pd.Series(ver, index=cal)
res = {}
for n, v in IDX.items():
    r = {"auc_a_sel": auc_y(v, Ya, selm), "auc_b_sel": auc_y(v, Yb, selm), "auc_a_ver": auc_y(v, Ya, verm), "auc_b_ver": auc_y(v, Yb, verm)}
    r["punteggio_scelta"] = np.nanmean([r["auc_a_sel"], r["auc_b_sel"]])
    pre = pd.Series(False, index=cal)
    for p in PK: pre.iloc[max(0, p - 9):p + 1] = True
    cm_ver = calmo & verm
    r["stacco_ver"] = float(v[pre].mean() - v[cm_ver].mean()); r["media_calmi_ver"] = float(v[cm_ver].mean())
    raw = SC[n]; thr = float(raw[calmo & selm].dropna().quantile(0.95))
    al = (raw >= thr).to_numpy()
    r["falsi_ver_%"] = float((raw >= thr)[cm_ver].mean() * 100)
    prot = []
    for p in PK:
        lo, hi = max(0, p - 10), min(len(cal) - 1, p + 40); fin = al[lo:hi + 1]
        if fin.any():
            t = lo + int(np.argmax(fin)); mn = S[p:p + 61].min()
            prot.append(float(np.clip((S[t] - mn) / (S[p] - mn), 0, 1)) if S[p] > mn else 0.0)
        else: prot.append(0.0)
    r["protezione_ver"] = float(np.mean(prot))
    ok = (~fuori) & Yb.notna() & v.notna() & verm
    def rate(m):
        y = Yb[m]; return float(y.mean() * 100) if len(y) > 20 else np.nan
    t = {"vicino_verde": rate(ok & (dd_ora > -0.02) & (v < 41)), "vicino_giallo": rate(ok & (dd_ora > -0.02) & (v >= 41)),
         "mid_verde": rate(ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (v < 41)), "mid_giallo": rate(ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (v >= 41)),
         "tutti_verde": rate(ok & (v < 41)), "tutti_giallo": rate(ok & (v >= 41))}
    r["tabella_ver"] = t
    r["rapporti_ver"] = {"tutti": t["tutti_giallo"] / t["tutti_verde"], "mid": t["mid_giallo"] / t["mid_verde"], "vicino": t["vicino_giallo"] / t["vicino_verde"]}
    res[n] = r
# soglia del caso (Ya, 2015+): massimo dei dieci candidati con etichette spostate
mv = ver & ~np.isnan(Ya.to_numpy())
names = [c[0] for c in CAND]
V = np.array([rankdata(IDX[n].to_numpy()[mv]) for n in names]); yv = Ya.to_numpy()[mv].astype(int)
rng = np.random.default_rng(11); mx = []
for _ in range(300):
    k = int(rng.integers(250, len(yv) - 250)); ys = np.roll(yv, k); n1 = ys.sum(); n0 = len(ys) - n1
    mx.append(max((V[i][ys == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) for i in range(len(names))))
barra = float(np.percentile(mx, 95))
vinc = max(names, key=lambda n: res[n]["punteggio_scelta"])
o = res["RIF_vecchio"]; w = res[vinc]
crit = {"i_auc": bool(w["auc_a_ver"] - o["auc_a_ver"] >= 0.03 and w["auc_a_ver"] > barra),
        "ii_tabella": bool(w["rapporti_ver"]["tutti"] >= 2 and w["rapporti_ver"]["mid"] >= 1.5 and w["rapporti_ver"]["vicino"] >= 1.3),
        "iii_stacco": bool(w["stacco_ver"] - o["stacco_ver"] >= 5), "iv_falsi": bool(w["falsi_ver_%"] - o["falsi_ver_%"] <= 1),
        "v_protezione": bool(w["protezione_ver"] - o["protezione_ver"] >= 0.10)}
oggi = {n: round(float(IDX[n].dropna().iloc[-1]), 1) for n in IDX}
out = {"vincitore": vinc, "barra_caso_ver": round(barra, 3), "criteri": crit, "passa": all(crit.values()), "oggi": oggi, "risultati": res}
json.dump(out, open("scratch/crollo_v3_esito.json", "w"), indent=1, default=float)
print("vincitore", vinc, "barra", round(barra, 3), crit, "oggi", oggi)
for n in names + ["RIF_vecchio", "RIF_gemini"]:
    r = res[n]; print(f"{n:14s} scelta {r['punteggio_scelta']:.3f} | ver AUC a {r['auc_a_ver']:.3f} b {r['auc_b_ver']:.3f} | stacco {r['stacco_ver']:+.1f} | falsi {r['falsi_ver_%']:.1f}% | prot {r['protezione_ver']:.2f} | rapp {', '.join(f'{k} {v:.2f}' for k, v in r['rapporti_ver'].items())}")
