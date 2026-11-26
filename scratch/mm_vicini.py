import pickle, json, numpy as np, pandas as pd, sys
from r200k_lib import *
ck = pickle.load(open("/tmp/mm_ck.pkl", "rb")); TOP, TG, SELR, mkt = ck["TOP"], ck["TG"], ck["SELR"], ck["mkt"]
KEYS = ["sp500", "f_nikkei225", "dax", "x_ftse", "x_fchi", "x_hsi", "x_gsptse", "x_ibex", "x_ssmi", "x_aex", "x_bfx", "x_atx", "x_axjo", "x_bvsp", "x_mxx", "x_ks11", "x_twii", "x_sti", "x_jkse", "x_bsesn", "x_000001_ss", "x_ta125_ta", "ftsemib"]
dm = []
for mi, k in enumerate(KEYS):
    s = store.load(k).dropna(); s = s[~s.index.duplicated()]; s = s[s > 0]
    if k == "sp500": s = s[s.index >= "1928-01-01"]
    C = s; lx = np.log(C); dl = lx.diff(); vol60 = dl.rolling(60).std(); calm = vol60 <= vol60.expanding(500).median(); Cn = C.to_numpy(float); n = len(Cn)
    def fm(kk):
        m = pd.Series(Cn[::-1]).rolling(kk).min().to_numpy()[::-1]; o = np.full(n, np.nan); o[:-1] = m[1:] / Cn[:-1] - 1; return o
    f20 = fm(20); ok_ = calm.to_numpy() & np.isfinite(vol60.to_numpy()) & (np.arange(n) >= 1008)
    if k == "sp500":
        from classifica_40anni import ESTERNI, MISTE_MAX
        ext = np.zeros(n, bool)
        for d in list(ESTERNI) + list(MISTE_MAX) + PRE90_EXT: p = C.index.searchsorted(pd.Timestamp(d)); ext[max(0, p - 5):min(n, p + 61)] = True
        ext[(C.index >= "1939-09-01") & (C.index <= "1945-09-02")] = True; ok_ &= ~ext
    idx = np.where(ok_ & np.isfinite(f20))[0]; dm.append((lx - lx.rolling(252).max()).to_numpy()[idx])
dm = np.concatenate(dm); assert len(dm) == len(mkt), (len(dm), len(mkt))
rg = np.random.default_rng(8)
def blocks(rows): return [np.where(mkt[rows] == m)[0] for m in np.unique(mkt[rows])]
def auc(s, y):
    ok = np.isfinite(s); rk = rankdata(s[ok]); yy = y[ok]; n1 = yy.sum(); return float((rk[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(yy) - n1)))
def pval(s, y, rows, nsh=3000):
    ok = np.isfinite(s); s = s[ok]; y = y[ok]; rw = rows[ok]; obs = auc(s, y); bl = blocks(rw); ge = 0
    for _ in range(nsh):
        ys = np.empty(len(y))
        for b in bl: n = len(b); ys[b] = y[b][np.roll(np.arange(n), int(rg.integers(max(20, n // 10), n - max(20, n // 10))))] if n > 60 else y[b]
        n1 = ys.sum(); rk = rankdata(s); ge += ((rk[ys == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(ys) - n1)) >= obs)
    return obs, (1 + ge) / (nsh + 1)
OUT = {}
for tg in ("T1", "T2"):
    y = TG[tg]; rs = SELR[tg]; res = []
    for st, nm, vec, ori in TOP[tg][:8]:
        r_ = dict(nome=nm[:90], sel=st)
        for p in ("v1", "v2"):
            rr = rs[p]; sc = vec[rr] * ori; a, pv = pval(sc, y[rr], rr, 1500); r_[p] = dict(auc=a, p_corr=min(1, pv * 8))
            near = dm[rr] >= -0.03; r_[p + "_vicino_max"] = dict(auc=auc(sc[near], y[rr][near]), n=int(near.sum()), eventi=float(y[rr][near].mean()), eventi_tutti=float(y[rr].mean()))
        res.append(r_); LOG(tg, nm[:60], {k: (round(v["auc"], 3), round(v["p_corr"], 3)) if "p_corr" in v else (round(v["auc"], 3), v["n"]) for k, v in r_.items() if isinstance(v, dict)})
    OUT[tg] = res
json.dump(OUT, open("scratch/mm_vicini.json", "w"), indent=1, default=float)
