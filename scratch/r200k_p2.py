"""Fase 2: valorizzare i più promettenti (>=100000 tentativi per gruppo e bersaglio), scelti solo in selezione."""
import sys, pickle, json
from r200k_lib import *
G = sys.argv[1]; NENS = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
D = pickle.load(open(f"/tmp/r200k_{G}.pkl", "rb")); cal = D["cal"]; Y = D["Y"]; rows = D["rows"]; N = len(cal)
yrs = np.asarray(cal.year); qtr = yrs * 4 + (np.asarray(cal.month) - 1) // 3
rg = np.random.default_rng(99 if G == "P" else 100); OUT = {"gruppo": G}; TOT = 0
def auc_cols(Rk, y):
    n1 = y.sum(); return (y.astype(np.float32) @ Rk - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))
def shifts_p(score, y, nsh=20000):
    rk = rankdata(score).astype(np.float32); n = len(y); n1 = y.sum(); obs = (rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (n - n1)); ge = 0; ar = np.arange(n)
    for c0 in range(0, nsh, 1000):
        offs = rg.integers(max(20, n // 10), n - max(20, n // 10), 1000); idx = (ar[None, :] + offs[:, None]) % n; ys = y[idx].astype(np.float32)
        ge += int(((ys @ rk - n1 * (n1 + 1) / 2) / (n1 * (n - n1)) >= obs).sum())
    return float(obs), (1 + ge) / (nsh + 1)
def boot_ic(score, y, qt, nb=300):
    bl = np.unique(qt); idxb = {b: np.where(qt == b)[0] for b in bl}; aus = []
    for _ in range(nb):
        pick = np.concatenate([idxb[b] for b in rg.choice(bl, len(bl))]); yy = y[pick]
        if yy.sum() < 5 or yy.sum() == len(yy): continue
        rk = rankdata(score[pick]); aus.append((rk[yy == 1].sum() - yy.sum() * (yy.sum() + 1) / 2) / (yy.sum() * (len(yy) - yy.sum())))
    return float(np.percentile(aus, 5)) if aus else float("nan")
for tg in ("T1", "T2", "T3"):
    cand = D["top_sel"][tg][:40]; K = len(cand); y_all = Y[tg]
    U = np.zeros((N, K), np.float32)
    for i, (stt, nm, vec, ori) in enumerate(cand):
        ok = np.isfinite(vec); p = np.zeros(N, np.float32); p[ok] = (rankdata(vec[ok]) / ok.sum() - 0.5) * ori; U[:, i] = p
    rs, rv = rows[tg]["sel"], rows[tg]["ver"]; ro = rows[tg].get("old"); ys = y_all[rs]
    # pesi casuali (sottoinsiemi 2-12, Dirichlet) + regole a soglia (40 x 50)
    W = np.zeros((K, NENS), np.float32)
    for m in range(NENS):
        k = int(rg.integers(2, 13)); sel = rg.choice(K, k, replace=False); W[sel, m] = rg.dirichlet(np.ones(k))
    thr = [(i, q) for i in range(K) for q in range(50, 100)]
    nthr = len(thr); ntot = NENS + nthr; TOT += ntot
    def score_cols(c0, c1):
        cols = []
        for m in range(c0, c1):
            cols.append(U @ W[:, m] if m < NENS else (U[:, thr[m - NENS][0]] >= (thr[m - NENS][1] / 100 - 0.5)).astype(np.float32))
        return np.column_stack(cols)
    a_sel = np.empty(ntot, np.float32); null = np.full(NSH, -np.inf); YS = S_ys = None
    offs = rg.integers(250, len(ys) - 250, NSH); YS = np.stack([np.roll(ys, int(o)) for o in offs]).astype(np.float32); n1 = ys.sum(); n0 = len(ys) - n1
    for c0 in range(0, ntot, 5000):
        c1 = min(ntot, c0 + 5000); Sc = score_cols(c0, c1); Rk = rankdata(Sc[rs], axis=0).astype(np.float32)
        a_sel[c0:c1] = auc_cols(Rk, ys); nl = (YS @ Rk - n1 * (n1 + 1) / 2) / (n1 * n0); null = np.maximum(null, nl.max(1))
    soglia2 = float(np.percentile(null, 95)); order = np.argsort(-a_sel)[:10]
    LOG(f"[{G}/{tg}] fase 2: {ntot} tentativi; miglior AUC selezione {a_sel[order[0]]:.3f}; soglia caso {soglia2:.3f}; mediana top10 {np.median(a_sel[order]):.3f}")
    res = []
    for j in order:
        sc = score_cols(j, j + 1)[:, 0]; cut = np.percentile(sc[rs], 90); r_ = dict(idx=int(j), tipo="pesi" if j < NENS else "soglia", sel=float(a_sel[j]))
        if j < NENS: r_["membri"] = {cand[i][1]: float(W[i, j]) for i in range(K) if W[i, j] > 0}
        else: r_["membri"] = {cand[thr[j - NENS][0]][1]: thr[j - NENS][1]}
        for per, rr in (("ver", rv), ("old", ro)):
            if rr is None or len(rr) == 0: continue
            y = y_all[rr]; s_ = sc[rr]; obs, p = shifts_p(s_, y); al = s_ >= cut
            r_[per] = dict(auc=obs, p=p, p_corr=min(1.0, p * 10), ic90=boot_ic(s_, y, qtr[rr]), lift=float(y[al].mean() / y.mean()) if al.sum() > 20 else None, frac_allarme=float(al.mean()))
        res.append(r_)
        LOG("   ", r_["tipo"], f"sel {r_['sel']:.3f}", {k: (round(v['auc'], 3), round(v['p_corr'], 3), None if v['lift'] is None else round(v['lift'], 2)) for k, v in r_.items() if k in ("ver", "old")})
    for r_ in res:
        ps = [r_[k] for k in ("ver", "old") if k in r_]
        r_["confermato"] = bool(all(p["auc"] >= 0.60 and (p["lift"] or 0) >= 1.25 and p["p_corr"] < 0.05 for p in ps))
    OUT[tg] = dict(n_tentativi=ntot, soglia=soglia2, top=res)
OUT["n_tentativi_fase2"] = TOT; LOG("TOTALE tentativi fase 2:", TOT)
json.dump(OUT, open(f"scratch/r200k_p2_{G}.json", "w"), indent=1, default=float)
