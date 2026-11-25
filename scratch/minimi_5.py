"""Segue PROTOCOLLO_MINIMI_5.md (commit 85c0f55, scritto prima dei calcoli)."""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import store, occasione as oc
from classifica_40anni import ESTERNI, MISTE_MAX
MERC = {"S&P 500": "sp500", "FTSE": "x_ftse", "CAC": "x_fchi", "SMI": "x_ssmi", "IBEX": "x_ibex", "AEX": "x_aex", "BEL20": "x_bfx", "HangSeng": "x_hsi",
        "Toronto": "x_gsptse", "Sydney": "x_axjo", "SanPaolo": "x_bvsp", "Seul": "x_ks11", "Taiwan": "x_twii", "Messico": "x_mxx"}
XP = ["dd252", "dd63", "rimb", "dal_min", "r5", "r21", "r63", "m50", "m200", "pend50", "vol21", "vol_rap", "giorni_neri", "dsh", "volpk"]
fuori_date = [pd.Timestamp(d) for d in ESTERNI]; mix = [pd.Timestamp(d) for d in MISTE_MAX]
def feats(sp):
    ix = sp.index; r = sp.pct_change(); pos = pd.Series(np.arange(len(sp)), index=ix)
    mx252, mx63, mn63 = sp.rolling(252).max(), sp.rolling(63).max(), sp.rolling(63).min()
    ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean(); vol21, vol63 = r.rolling(21).std(), r.rolling(63).std()
    dsl = (pos - pos.where(sp == mn63).ffill()).clip(upper=63); dsh = (pos - pos.where(sp == mx252).ffill()).clip(upper=252)
    P = pd.DataFrame({"dd252": sp / mx252 - 1, "dd63": sp / mx63 - 1, "rimb": sp / mn63 - 1, "dal_min": dsl, "r5": sp.pct_change(5), "r21": sp.pct_change(21),
                      "r63": sp.pct_change(63), "m50": sp / ma50 - 1, "m200": sp / ma200 - 1, "pend50": ma50 / ma50.shift(21) - 1, "vol21": vol21, "vol_rap": vol21 / vol63,
                      "giorni_neri": (r < -0.01).astype(float).rolling(21).sum(), "dsh": dsh, "volpk": vol21 / vol21.rolling(63).max()})
    P["px"] = sp; return P.replace([np.inf, -np.inf], np.nan)
frames = []
for nome, k in MERC.items():
    try:
        s = store.load(k).dropna(); s = s[(s.index >= "1989-01-01") & ~s.index.duplicated()]
        if len(s) < 2000: continue
        F = feats(s).dropna(subset=XP[:11] + XP[11:]); F["mercato"] = nome
        st = (F["dd252"] <= -0.08).to_numpy(); ep = np.zeros(len(F), int); cur = 0; last = -99
        for i, v in enumerate(st):
            if v:
                if i - last > 21 or cur == 0: cur += 1
                ep[i] = cur; last = i
        # unisce periodi separati da meno di 21 sedute
        F["ep"] = ep; F = F.reset_index().rename(columns={F.index.name or "index": "data"}); frames.append(F)
    except Exception as e: print(nome, "NO", str(e)[:50])
D = pd.concat(frames, ignore_index=True)
D["epid"] = D["mercato"] + "_" + D["ep"].astype(str)
D = D.assign(T=np.nan)
for eid, g in D[D["ep"] > 0].groupby("epid"):
    tr = g["px"].idxmin(); D.loc[g.index, "T"] = (g.index < tr).astype(float); D.loc[tr, "T"] = np.nan
exo = pd.Series(False, index=D.index)
for d0 in fuori_date: exo |= (D["data"] >= d0 - pd.Timedelta(days=90)) & (D["data"] <= d0 + pd.Timedelta(days=88))
for d0 in mix: exo |= (D["data"] >= d0 - pd.Timedelta(days=7)) & (D["data"] <= d0 + pd.Timedelta(days=260))
D["exo"] = exo; D["anno"] = D["data"].dt.year
print("mercati", D["mercato"].nunique(), "discese", D.loc[D["ep"] > 0, "epid"].nunique(), "giorni con bersaglio", int(D["T"].notna().sum()), "esclusi shock esterni", int((D["T"].notna() & D["exo"]).sum()), flush=True)
# L1 pooled
D["L1"] = np.nan
for Y in range(2000, 2027):
    lim = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=95); trn = D[(D["data"] < lim) & D["T"].notna()]; te = D["anno"] == Y
    if len(trn) < 300 or te.sum() == 0: continue
    sc = StandardScaler().fit(trn[XP]); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(trn[XP]), trn["T"])
    D.loc[te, "L1"] = m.predict_proba(sc.transform(D.loc[te, XP]))[:, 1]
# punteggi senza addestramento: percentili espansi per mercato
pe = lambda s: s.expanding(252).rank(pct=True)
comp = pd.DataFrame({"a": -D.groupby("mercato")["rimb"].transform(pe), "b": -D.groupby("mercato")["dsh"].transform(pe), "c": -D.groupby("mercato")["pend50"].transform(pe),
                     "d": D.groupby("mercato")["giorni_neri"].transform(pe), "e": D.groupby("mercato")["volpk"].transform(pe)})
D["L3"] = comp.mean(axis=1, skipna=False)
D["N1"] = -D["dsh"]; D["N2"] = -D["rimb"]
D["L1p"] = D.groupby("mercato")["L1"].transform(lambda s: s.expanding(252).rank(pct=True)); D["E1"] = (D["L1p"] + D["L3"]) / 2
# S&P 500: B0 e L2
sp = D[D["mercato"] == "S&P 500"].set_index("data"); S = oc.serie_archivio(); d = oc.calcola(S)
B0 = (100 - d["svolta"]); D["B0"] = np.nan; msk = D["mercato"] == "S&P 500"; D.loc[msk, "B0"] = D.loc[msk, "data"].map(B0).to_numpy()
al = lambda s: s.dropna().reindex(sp.index, method="ffill")
vix, baa = al(store.load("vix")), al(store.load("baa10y")); sett = pd.DataFrame({k: al(v) for k, v in S["settori"].items() if len(v)})
V = pd.DataFrame({"vix_pct": vix.expanding(252).rank(pct=True), "vix_su_max": vix / vix.rolling(63).max(), "baa_su_max": baa / baa.rolling(63).max(),
                  "settori_50": (sett > sett.rolling(50).mean()).mean(axis=1).where(sett.notna().all(axis=1))}); V.loc[V.index < "1999-01-01"] = np.nan
SP = sp[XP].join(V); SP["T"] = sp["T"]; SP["anno"] = sp["anno"]; XV = XP + list(V.columns); D["L2"] = np.nan
for Y in range(2000, 2027):
    lim = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=95); trn = SP[(SP.index < lim) & SP["T"].notna() & SP[XV].notna().all(axis=1)]; te = (SP["anno"] == Y) & SP[XV].notna().all(axis=1)
    if len(trn) < 300 or te.sum() == 0: continue
    sc = StandardScaler().fit(trn[XV]); m = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(trn[XV]), trn["T"])
    D.loc[msk & D["data"].isin(SP.index[te]), "L2"] = m.predict_proba(sc.transform(SP.loc[te, XV]))[:, 1]
def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float); n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    rk = pd.Series(s).rank().to_numpy(); return float((rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
rng = np.random.default_rng(2515)
POOL = ["N1", "N2", "L1", "L3", "E1"]
E = D[D["T"].notna() & ~D["exo"] & (D["anno"] >= 2000) & D[POOL].notna().all(axis=1)].reset_index(drop=True)
eps = E["epid"].unique(); gi = {e: np.where(E["epid"] == e)[0] for e in eps}
print("valutazione: giorni", len(E), "discese", len(eps), "mercati", E["mercato"].nunique(), "base fondo davanti %.1f%%" % (E["T"].mean() * 100), flush=True)
res = {"giorni": len(E), "discese": len(eps), "pool": {}}
for h in POOL:
    a = auc(E[h], E["T"]); b = []
    for _ in range(500):
        ii = np.concatenate([gi[e] for e in rng.choice(eps, len(eps))]); b.append(auc(E[h].to_numpy()[ii], E["T"].to_numpy()[ii]))
    pe_auc = {e: auc(E[h].to_numpy()[gi[e]], E["T"].to_numpy()[gi[e]]) for e in eps}
    ok = [v for v in pe_auc.values() if v == v]
    res["pool"][h] = {"AUC": a, "IC90": [float(np.nanpercentile(b, 5)), float(np.nanpercentile(b, 95))], "discese_sopra_0.5": int(sum(v > 0.5 for v in ok)), "discese_valutabili": len(ok)}
best = []
for _ in range(200):
    y = E["T"].to_numpy().copy()
    for e in eps:
        ii = gi[e]; y[ii] = np.roll(E["T"].to_numpy()[ii], int(rng.integers(1, max(2, len(ii)))))
    best.append(max(auc(E[h], y) for h in POOL))
res["soglia_caso"] = float(np.percentile(best, 95)); print("soglia del caso: %.3f" % res["soglia_caso"])
for h, v in res["pool"].items(): print(f"  {h}: AUC {v['AUC']:.3f} [{v['IC90'][0]:.3f},{v['IC90'][1]:.3f}] discese>0.5: {v['discese_sopra_0.5']}/{v['discese_valutabili']}")
SPE = D[(D["mercato"] == "S&P 500") & D["T"].notna() & ~D["exo"] & (D["anno"] >= 2000)]; res["sp500"] = {}
for h in ["B0", "N1", "N2", "L1", "L2", "L3", "E1"]:
    z = SPE[SPE[h].notna()]; res["sp500"][h] = {"giorni": len(z), "AUC": auc(z[h], z["T"]), "discese": int(z["epid"].nunique())}
print("S&P 500:", {k: (v["giorni"], round(v["AUC"], 3), v["discese"]) for k, v in res["sp500"].items()})
oggi = D[D["mercato"] == "S&P 500"].iloc[-1]; res["oggi_sp500"] = {h: float(oggi[h]) if oggi[h] == oggi[h] else None for h in ["L1", "L3", "E1", "B0"]}
res["per_mercato"] = {m: {h: auc(g[h], g["T"]) for h in ("L1", "L3", "N1")} for m, g in E.groupby("mercato")}
print("per mercato:", {m: {h: round(v, 2) for h, v in x.items()} for m, x in res["per_mercato"].items()})
json.dump(res, open("scratch/minimi_5_esito.json", "w"), indent=1, default=float)
