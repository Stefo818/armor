"""Motore a blocchi per PROTOCOLLO_RICERCA_200000.md (scritto prima dei calcoli)."""
import sys, time, warnings, pickle, itertools
import numpy as np, pandas as pd
from scipy.stats import rankdata
warnings.filterwarnings("ignore")
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import store
from classifica_40anni import ESTERNI, MISTE_MAX
T0 = time.time()
def LOG(*a): print(f"[{time.time()-T0:5.0f}s]", *a, flush=True)

PRE90_EXT = ["1950-06-25", "1956-10-29", "1962-10-22", "1963-11-22", "1973-10-17", "1979-11-04"]
NSH = 300

class Setup:
    def __init__(s, cal, C, group, seed=7):
        s.cal = cal; s.N = len(cal); s.group = group
        s.yrs = np.asarray(cal.year); s.qtr = s.yrs * 4 + (np.asarray(cal.month) - 1) // 3
        Cn = np.asarray(C, float); N = s.N
        def fmin(k):
            m = pd.Series(Cn[::-1]).rolling(k).min().to_numpy()[::-1]
            out = np.full(N, np.nan); out[:-1] = m[1:] / Cn[:-1] - 1; return out
        fall20, fall40 = fmin(20), fmin(40)
        ext = np.zeros(N, bool)
        for d in list(ESTERNI) + list(MISTE_MAX) + PRE90_EXT:
            p = cal.searchsorted(pd.Timestamp(d)); ext[max(0, p - 5):min(N, p + 61)] = True
        ext[(cal >= "1939-09-01") & (cal <= "1945-09-02")] = True
        dd20 = Cn / pd.Series(Cn).rolling(20).max().to_numpy() - 1
        s.Y = {"T1": (fall20 <= -0.05).astype(float), "T2": (fall40 <= -0.08).astype(float), "T3": (fall20 <= -0.05).astype(float)}
        s.MASK = {"T1": (~ext) & np.isfinite(fall20), "T2": (~ext) & np.isfinite(fall40), "T3": (~ext) & np.isfinite(fall20) & (dd20 <= -0.02) & (dd20 >= -0.06)}
        s.pr = {"sel": (s.yrs >= 1992) & (s.yrs <= 2007), "ver": s.yrs >= 2008}
        if group == "P": s.pr["old"] = (s.yrs >= 1932) & (s.yrs <= 1989)
        s.pers = list(s.pr)
        s.rows = {tg: {p: np.where(s.MASK[tg] & s.pr[p])[0] for p in s.pers} for tg in s.Y}
        rng = np.random.default_rng(seed); s.YS = {}; s.null_max = {}
        for tg in s.Y:
            ys = s.Y[tg][s.rows[tg]["sel"]]; n = len(ys)
            offs = rng.integers(250, n - 250, NSH); s.YS[tg] = np.stack([np.roll(ys, int(o)) for o in offs]).astype(np.float32)
            s.null_max[tg] = np.full(NSH, -np.inf)
            LOG(f"[{group}] {tg}: sel {n} giorni (evento {ys.mean():.3f}), ver {len(s.rows[tg]['ver'])}" + (f", vecchio {len(s.rows[tg]['old'])} (evento {s.Y[tg][s.rows[tg]['old']].mean():.3f})" if "old" in s.pers else ""))
        s.stats = {tg: {k: [] for k in ("sel", "ver", "old", "lver", "lold", "nsel", "nold")} for tg in s.Y}
        s.names = []
        s.k_sel = 40
        s.top_sel = {tg: [] for tg in s.Y}  # lista di (stat, nome, vettore)
        s.top_old = {tg: [] for tg in s.Y}

def _auc(Rk, y, n1, n0): return (y.astype(np.float32) @ Rk - n1 * (n1 + 1) / 2) / (n1 * n0)

def evaluate(S, X, names, keep=True):
    """X: N x c float32. Aggiorna S.stats, S.null_max, top."""
    c = X.shape[1]; S.names += list(names); fill = {}
    for p in S.pers:
        ra = np.where(S.pr[p])[0]; Xp = X[ra]; nanf = np.isnan(Xp).mean(0); med = np.nanmedian(Xp, axis=0); med = np.where(np.isnan(med), 0, med)
        fill[p] = (ra, np.where(np.isnan(Xp), med, Xp).astype(np.float32), nanf)
    for tg in S.Y:
        y_all = S.Y[tg]; rs = S.rows[tg]
        ra, Xf, nanf_s = fill["sel"]; sub = np.searchsorted(ra, rs["sel"]); ys = y_all[rs["sel"]]; n1 = ys.sum(); n0 = len(ys) - n1
        Zs = Xf[sub]; Rk = rankdata(Zs, axis=0).astype(np.float32); a = _auc(Rk, ys, n1, n0); a[nanf_s > 0.2] = np.nan
        ori = np.where(a >= 0.5, 1.0, -1.0).astype(np.float32); stat = np.maximum(a, 1 - a)
        nl = (S.YS[tg] @ Rk - n1 * (n1 + 1) / 2) / (n1 * n0); nl = np.maximum(nl, 1 - nl); nl[:, nanf_s > 0.2] = -np.inf
        S.null_max[tg] = np.maximum(S.null_max[tg], nl.max(1))
        cut = np.percentile(Zs * ori, 90, axis=0); base_s = ys.mean()
        res = {"sel": stat.astype(np.float32), "nsel": nanf_s.astype(np.float32)}
        for per, kk in (("ver", "ver"), ("old", "old")):
            if per not in S.pers: res[kk] = np.full(c, np.nan, np.float32); res["l" + kk] = res[kk]; res["nold"] = np.full(c, np.nan, np.float32); continue
            ra2, Xf2, nanf2 = fill[per]; rr = rs[per]; sub2 = np.searchsorted(ra2, rr); yy = y_all[rr]; m1 = yy.sum(); m0 = len(yy) - m1
            Z2 = Xf2[sub2]; R2 = rankdata(Z2, axis=0).astype(np.float32); a2 = _auc(R2, yy, m1, m0); a2o = np.where(ori > 0, a2, 1 - a2)
            if per == "old": a2o[nanf2 > 0.2] = np.nan; res["nold"] = nanf2.astype(np.float32)
            al = (Z2 * ori) >= cut[None, :]; cnt = al.sum(0); hits = yy.astype(np.float32) @ al.astype(np.float32)
            lift = np.where(cnt >= 20, (hits / np.maximum(cnt, 1)) / yy.mean(), np.nan)
            res[kk] = a2o.astype(np.float32); res["l" + kk] = lift.astype(np.float32)
        if "old" not in S.pers: res["nold"] = np.full(c, np.nan, np.float32)
        for k in S.stats[tg]: S.stats[tg][k].append(res[k])
        if keep:
            valid = np.where(np.isfinite(stat))[0]
            if len(valid):
                for j in valid[np.argsort(-stat[valid])[:S.k_sel]]: S.top_sel[tg].append((float(stat[j]), names[j], X[:, j].copy(), float(ori[j])))
                S.top_sel[tg] = sorted(S.top_sel[tg], key=lambda t: -t[0])[:S.k_sel]
            if "old" in S.pers:
                so = res["old"]  # orientato dalla selezione: per l'addestramento serve il vecchio puro
                ra3, Xf3, nanf3 = fill["old"]; rr = rs["old"]; sub3 = np.searchsorted(ra3, rr); yy = y_all[rr]
                R3 = rankdata(Xf3[sub3], axis=0).astype(np.float32); a3 = _auc(R3, yy, yy.sum(), len(yy) - yy.sum()); a3[nanf3 > 0.2] = np.nan; st3 = np.abs(a3 - 0.5)
                v3 = np.where(np.isfinite(st3))[0]
                if len(v3):
                    for j in v3[np.argsort(-st3[v3])[:300]]: S.top_old[tg].append((float(st3[j]), names[j], X[:, j].copy(), float(np.sign(a3[j] - 0.5))))
                    S.top_old[tg] = sorted(S.top_old[tg], key=lambda t: -t[0])[:300]

def run_chunks(S, gen_cols, total, chunk=2500):
    """gen_cols(i0,i1) -> (X N x c float32, names)."""
    for i0 in range(0, total, chunk):
        X, nm = gen_cols(i0, min(total, i0 + chunk)); evaluate(S, X, nm); del X
        LOG(f"  valutati {min(total, i0 + chunk)}/{total}")

def finalize(S):
    out = {}
    for tg in S.Y:
        st = {k: np.concatenate(v) for k, v in S.stats[tg].items()}; sel = st["sel"]
        soglia = float(np.percentile(S.null_max[tg], 95)); n_val = int(np.isfinite(sel).sum())
        out[tg] = dict(st=st, soglia=soglia, n_val=n_val, med_null=float(np.median(S.null_max[tg])), best=float(np.nanmax(sel)))
        LOG(f"[{S.group}/{tg}] segnali validi {n_val}; soglia caso {soglia:.3f} (mediana {out[tg]['med_null']:.3f}); miglior reale {out[tg]['best']:.3f}")
    return out
