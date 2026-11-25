"""Gruppo A: dati dal 1990 (10856 segnali precedenti + turbolenza/assorbimento + coppie casuali)."""
import sys, pickle
from r200k_lib import *
BUDGET_PAIRS = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
src = open("scratch/ricerca_10000.py").read().split("\n")[:105]
ns = {"__name__": "ricerca"}; exec("\n".join(src), ns)
FEAT, cal, C, N, bs = ns["FEAT"], ns["cal"], ns["C"], ns["N"], ns["bs"]; r = ns["r"]; R = ns["R"]
LOG("segnali singoli ereditati:", len(FEAT))
S = Setup(cal, C, "A"); S.k_sel = 300
sets = {"6": pd.DataFrame({"sp": C, "nd": bs["nasdaq"], "ru": bs["rut"], "mi": bs["mid"], "dx": bs["dax"], "nk": bs["nikkei"]}).pct_change()}
sets["15"] = pd.concat([sets["6"], pd.DataFrame({k: R("sec_" + k) for k in ns["SECS"]}).pct_change()], axis=1)
def ar_series(ret, win, ks=(1, 2, 3)):
    A = ret.to_numpy(); n = A.shape[1]; out = {k: np.full(N, np.nan) for k in ks}
    for t in range(win, N):
        w = A[t - win + 1:t + 1]
        if np.isnan(w).any(): continue
        ev = np.linalg.eigvalsh(np.corrcoef(w.T))[::-1]
        for k in ks: out[k][t] = ev[:k].sum() / n
    return {k: pd.Series(v, index=cal) for k, v in out.items()}
def turb(ret, win):
    A = ret.to_numpy(); out = np.full(N, np.nan)
    for t in range(win, N):
        w = A[t - win:t]
        if np.isnan(w).any() or np.isnan(A[t]).any(): continue
        mu = w.mean(0); cv = np.cov(w.T); d = A[t] - mu; out[t] = d @ np.linalg.pinv(cv) @ d
    return pd.Series(out, index=cal)
EXTRA = {}
for sn, ret in sets.items():
    for win in (60, 120, 250):
        for k, v in ar_series(ret, win).items(): EXTRA[f"ass{sn}_w{win}_k{k}"] = v
    for win in (250, 500):
        tb = turb(ret, win); EXTRA[f"turb{sn}_w{win}"] = tb; EXTRA[f"turb{sn}_w{win}_m5"] = tb.rolling(5).mean(); EXTRA[f"turb{sn}_w{win}_m20"] = tb.rolling(20).mean()
n0 = len(FEAT)
for k, v in EXTRA.items(): ns["gen"]("kritz|" + k, v)
LOG("segnali di turbolenza e assorbimento aggiunti:", len(FEAT) - n0, "da", len(EXTRA), "serie")
names = list(FEAT); m_s = len(names); Xs = np.column_stack([FEAT[n] for n in names]).astype(np.float32); del FEAT; ns["FEAT"] = None
def gen_s(i0, i1): return Xs[:, i0:i1], names[i0:i1]
run_chunks(S, gen_s, m_s)
good = [j for j in range(m_s) if np.isfinite(Xs[:, j][S.yrs >= 1992]).mean() > 0.7]; LOG("singoli per le coppie:", len(good))
PR = np.empty((N, len(good)), np.float32)
for jj, j in enumerate(good):
    v = Xs[:, j]; ok = np.isfinite(v); p = np.full(N, np.nan, np.float32); p[ok] = rankdata(v[ok]) / ok.sum() - 0.5; PR[:, jj] = p
del Xs
rg = np.random.default_rng(2025); pi = rg.integers(0, len(good), BUDGET_PAIRS); pj = rg.integers(0, len(good), BUDGET_PAIRS); k_ = pi != pj; pi, pj = pi[k_], pj[k_]; total = len(pi) * 3
def gen_p(i0, i1):
    cols = []; nms = []
    for t in range(i0, i1):
        q, op = divmod(t, 3); a, b = PR[:, pi[q]], PR[:, pj[q]]
        cols.append(a + b if op == 0 else (a - b if op == 1 else a * b)); nms.append(f"A|coppia|{names[good[pi[q]]]}|{names[good[pj[q]]]}|{('somma', 'diff', 'prod')[op]}")
    return np.column_stack(cols).astype(np.float32), nms
run_chunks(S, gen_p, total)
LOG("TOTALE tentativi gruppo A:", len(S.names), "(singoli", m_s, "+ coppie", total, ")")
fin = finalize(S)
pickle.dump(dict(fin=fin, names=S.names, top_sel=S.top_sel, n_single=m_s, n_pairs=total, cal=cal, Y=S.Y, rows=S.rows), open("/tmp/r200k_A.pkl", "wb"))
LOG("salvato /tmp/r200k_A.pkl")
