"""Gruppo P: solo prezzi S&P 500 (dal 1928) + macro lunghi. Segue PROTOCOLLO_RICERCA_200000.md."""
import sys, pickle
from r200k_lib import *
BUDGET_PAIRS = int(sys.argv[1]) if len(sys.argv) > 1 else 45000
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]; sp = sp[sp.index >= "1928-01-01"]
cal = sp.index; C = sp; N = len(cal)
Cn = C.to_numpy(float); lx = np.log(C); dl = lx.diff()
S = Setup(cal, C, "P")
SER = {}
WIN = (2, 3, 4, 5, 7, 10, 15, 20, 30, 40, 60, 90, 120, 180, 252, 378, 504)
STAT = {}  # (stat,w) -> serie
def st(name, w, x): STAT[(name, w)] = x
neg2 = np.minimum(dl, 0) ** 2; pos2 = np.maximum(dl, 0) ** 2
for w in WIN:
    R_ = dl.rolling(w); st("media", w, R_.mean()); st("dev", w, R_.std()); st("devgiu", w, np.sqrt(neg2.rolling(w).mean())); st("devsu", w, np.sqrt(pos2.rolling(w).mean()))
    st("rapp_giu_su", w, STAT[("devgiu", w)] / STAT[("devsu", w)]); st("max", w, R_.max()); st("min", w, R_.min())
    st("q05", w, R_.quantile(0.05)) if w >= 20 else None; st("q95", w, R_.quantile(0.95)) if w >= 20 else None
    if w >= 3: st("asim", w, R_.skew())
    if w >= 4: st("curt", w, R_.kurt())
    st("sommaabs", w, dl.abs().rolling(w).sum()); st("quotasu", w, (dl > 0).rolling(w).mean()); st("quota_m1", w, (dl < -0.01).rolling(w).mean()); st("quota_p1", w, (dl > 0.01).rolling(w).mean())
    st("dmax", w, lx - lx.rolling(w).max()); st("dmin", w, lx - lx.rolling(w).min()); st("dmedia", w, lx - lx.rolling(w).mean()); st("range", w, lx.rolling(w).max() - lx.rolling(w).min())
    st("rend", w, lx.diff(w)); st("nuovimax", w, (C == C.rolling(w).max()).rolling(w).sum()) if w >= 5 else None
    st("ac1", w, dl.rolling(w).corr(dl.shift(1))) if w >= 5 else None
    if w >= 4:  # pendenza, curvatura, R2 del logaritmo del prezzo (proxy di crescita più veloce dell'esponenziale)
        t = np.arange(w, dtype=float); p1 = t - t.mean(); p2 = t ** 2; p2 = p2 - p2.mean(); p2 = p2 - p1 * (p2 @ p1) / (p1 @ p1)
        xv = lx.to_numpy()
        def roll_dot(p): return pd.Series(np.concatenate([np.full(w - 1, np.nan), np.convolve(xv, p[::-1], mode="valid")]), index=cal)
        b1 = roll_dot(p1) / (p1 @ p1); b2 = roll_dot(p2) / (p2 @ p2)
        sst = (lx ** 2).rolling(w).sum() - lx.rolling(w).sum() ** 2 / w
        st("pend", w, b1); st("curv", w, b2); st("r2", w, (b1 ** 2 * (p1 @ p1)) / sst); st("curv_su_pend", w, b2 / b1.abs())
# estensioni di letteratura: volatilità condizionata (EWMA/GJR-lite/HAR), salti, coda
EXT = {}
for lam in (0.8, 0.9, 0.94, 0.97, 0.99):
    EXT[f"ewma{lam}"] = np.sqrt((dl ** 2).ewm(alpha=1 - lam).mean()); EXT[f"ewmagiu{lam}"] = np.sqrt(neg2.ewm(alpha=1 - lam).mean())
    EXT[f"ewma_asim{lam}"] = EXT[f"ewmagiu{lam}"] / np.sqrt(pos2.ewm(alpha=1 - lam).mean())
rv1 = dl.abs(); rv5 = np.sqrt((dl ** 2).rolling(5).mean()); rv22 = np.sqrt((dl ** 2).rolling(22).mean()); rv66 = np.sqrt((dl ** 2).rolling(66).mean())
EXT["har"] = 0.3 * rv1 + 0.4 * rv5 + 0.3 * rv22; EXT["har2"] = 0.2 * rv1 + 0.3 * rv5 + 0.3 * rv22 + 0.2 * rv66; EXT["har_su_lungo"] = EXT["har"] / dl.rolling(504).std()
bv = (np.pi / 2) * (dl.abs() * dl.abs().shift(1))
for w in (10, 20, 60): rvw = (dl ** 2).rolling(w).sum(); EXT[f"salto{w}"] = ((rvw - bv.rolling(w).sum()).clip(lower=0)) / rvw
def hill(w, q=0.1):
    x = (-dl).to_numpy(); out = np.full(N, np.nan); k = max(5, int(w * q))
    for i in range(w, N):
        seg = x[i - w + 1:i + 1]; top = np.sort(seg)[-k - 1:]
        if top[0] > 0: out[i] = 1.0 / np.mean(np.log(top[1:] / top[0]))
    return pd.Series(out, index=cal)
for w in (120, 252, 504): EXT[f"hill{w}"] = hill(w)
for w in (60, 252): vl = dl.rolling(w).std(); EXT[f"quota_vol_alta{w}"] = (dl.rolling(20).std() > dl.rolling(1008).median() * 0 + dl.rolling(1008).std()).rolling(w).mean()
vv = dl.rolling(20).std()
EXT["persist_volalta"] = (vv > vv.rolling(504).median()).rolling(60).mean(); EXT["cond_vol_su_cum"] = vv / np.sqrt((dl ** 2).expanding().mean())
for k, v in EXT.items(): STAT[("ext_" + k, 0)] = v
LOG("statistiche base:", len(STAT))
FEAT = {}
def put(n, x):
    a = x.to_numpy(dtype=np.float64) if hasattr(x, "to_numpy") else np.asarray(x, float)
    a = np.where(np.isfinite(a), a, np.nan)
    if np.isfinite(a).sum() < 3000 or np.nanstd(a) == 0: return
    FEAT[n] = a.astype(np.float32)
def variants(nm, x):
    x = x.astype(float).replace([np.inf, -np.inf], np.nan); put(f"{nm}|raw", x)
    for l in (1, 2, 3, 5, 10, 20): put(f"{nm}|lag{l}", x.shift(l))
    for w in (252, 1008): put(f"{nm}|z{w}", (x - x.rolling(w).mean()) / x.rolling(w).std())
    for d_ in (5, 20): put(f"{nm}|diff{d_}", x.diff(d_))
    m252 = x.rolling(252).mean(); put(f"{nm}|rapp252", x / m252.where(m252.abs() > 1e-12) - 1)
for (a, w), x in STAT.items(): variants(f"P|{a}{w}", x)
n_var = len(FEAT); LOG("varianti statistiche:", n_var)
RELS = ("dev", "devgiu", "devsu", "range", "sommaabs", "pend", "asim", "max", "min", "q05", "q95", "quotasu", "dmax", "dmin", "rend", "r2")[:14]
RELS = ("dev", "devgiu", "devsu", "range", "sommaabs", "pend", "asim", "max", "min", "quotasu", "dmax", "dmin", "rend", "r2")
for a in RELS:
    for wa, wb in itertools.combinations(WIN, 2):
        if (a, wa) in STAT and (a, wb) in STAT:
            xa, xb = STAT[(a, wa)], STAT[(a, wb)]
            put(f"P|rel_{a}_{wa}_su_{wb}", xa / xb.where(xb.abs() > 1e-12)); put(f"P|rel_{a}_{wa}_meno_{wb}", xa - xb)
n_rel = len(FEAT) - n_var; LOG("relazioni fra finestre:", n_rel)
# macro lunghi (ritardo di pubblicazione prudente: 2 mesi; 1 mese per serie di mercato)
def mser(k, how="mean"):
    s = store.load(k).dropna(); s = s[~s.index.duplicated()]; s = s.resample("MS").mean(); return s
MK = {"aaa": ("aaa_m", 1), "baa": ("baa_m", 1), "gs10": ("gs10_m", 1), "tb3": ("tb3ms", 1), "ff": ("fedfunds", 1), "cpi_yoy": ("cpi_yoy_lungo", 2), "cpi": ("cpi_nsa", 2), "indpro": ("indpro", 2),
      "indpro_g12": ("indpro_g12", 2), "payems": ("payems", 2), "unrate": ("unrate", 2), "manemp": ("f_manemp", 2), "awh": ("f_awhman", 2), "ppi": ("f_ppiaco", 2), "circ": ("f_currcir", 2), "totalsl": ("f_totalsl", 2),
      "busloans": ("busloans", 2), "umcsent": ("umcsent", 2), "cape": ("cape_m", 1), "pe": ("pe_m", 1), "eps": ("eps_sp", 3), "m1": ("f_m1sl", 2), "m2": ("f_m2sl", 2), "dtb3": ("f_dtb3", 1), "prime": ("f_dprime", 1),
      "uscons": ("f_uscons", 2), "usgood": ("f_usgood", 2), "houst": ("f_houst", 2), "permit": ("permit", 2), "psavert": ("psavert", 2), "erp": ("erp", 1), "credit_ratio": ("credit_ratio", 4), "cp_gdp": ("cp_gdp", 4)}
M = {}
for nm, (k, lag) in MK.items(): M[nm] = (mser(k), lag)
def comb(a, b, op): return (op(M[a][0], M[b][0].reindex(M[a][0].index)), max(M[a][1], M[b][1]))
M["spread_baa_aaa"] = comb("baa", "aaa", lambda x, y: x - y); M["spread_baa_gs10"] = comb("baa", "gs10", lambda x, y: x - y); M["curva_10_3m"] = comb("gs10", "tb3", lambda x, y: x - y)
M["curva_10_ff"] = comb("gs10", "ff", lambda x, y: x - y); M["tasso_reale"] = comb("gs10", "cpi_yoy", lambda x, y: x - y); M["ff_reale"] = comb("ff", "cpi_yoy", lambda x, y: x - y)
M["prime_meno_ff"] = comb("prime", "ff", lambda x, y: x - y); M["aaa_meno_gs10"] = comb("aaa", "gs10", lambda x, y: x - y); M["eps_su_prezzo"] = (M["eps"][0] / M["cape"][0].reindex(M["eps"][0].index), 3)
def put_m(n, ms, lag):
    s = ms.copy(); s.index = s.index + pd.DateOffset(months=lag); s = s[~s.index.duplicated()]
    d = s.reindex(s.index.union(cal)).ffill().reindex(cal); put(n, d)
for nm, (ms, lag) in M.items():
    ms = ms.dropna()
    if len(ms) < 200: continue
    pos = bool((ms > 0).all()) and ms.max() / ms.min() > 3; lg = np.log(ms) if pos else ms
    put_m(f"M|{nm}|livello", ms, lag)
    for k in (1, 3, 6, 12): put_m(f"M|{nm}|var{k}", lg.diff(k), lag)
    for k in (60, 120): put_m(f"M|{nm}|z{k}", (ms - ms.rolling(k).mean()) / ms.rolling(k).std(), lag)
    put_m(f"M|{nm}|dmax12", lg - lg.rolling(12).max(), lag); put_m(f"M|{nm}|dmin12", lg - lg.rolling(12).min(), lag); put_m(f"M|{nm}|acc6", lg.diff(6) - lg.diff(6).shift(6), lag)
n_mac = len(FEAT) - n_var - n_rel; LOG("macro:", n_mac)
names = list(FEAT); m_s = len(names); LOG("segnali singoli gruppo P:", m_s)
Xs = np.column_stack([FEAT[n] for n in names]); del FEAT
def gen_s(i0, i1): return Xs[:, i0:i1], names[i0:i1]
run_chunks(S, gen_s, m_s)
# coppie casuali: percentili centrati dei singoli con storia sufficiente
good = [j for j in range(m_s) if np.isfinite(Xs[S.pr["old"] | S.pr["sel"] | S.pr["ver"], j]).mean() > 0.7]
LOG("singoli con storia sufficiente per le coppie:", len(good))
PR = np.empty((N, len(good)), np.float32)
for c0 in range(0, len(good), 1000):
    blk = Xs[:, good[c0:c0 + 1000]]
    for jj in range(blk.shape[1]):
        v = blk[:, jj]; ok = np.isfinite(v); p = np.full(N, np.nan, np.float32); p[ok] = rankdata(v[ok]) / ok.sum() - 0.5; PR[:, c0 + jj] = p
del Xs
rg = np.random.default_rng(2024); pi = rg.integers(0, len(good), BUDGET_PAIRS); pj = rg.integers(0, len(good), BUDGET_PAIRS); keep_ = pi != pj; pi, pj = pi[keep_], pj[keep_]
total = len(pi) * 3
def gen_p(i0, i1):
    cols = []; nms = []
    for t in range(i0, i1):
        q, op = divmod(t, 3); a, b = PR[:, pi[q]], PR[:, pj[q]]
        cols.append(a + b if op == 0 else (a - b if op == 1 else a * b)); nms.append(f"P|coppia|{names[good[pi[q]]]}|{names[good[pj[q]]]}|{('somma', 'diff', 'prod')[op]}")
    return np.column_stack(cols).astype(np.float32), nms
run_chunks(S, gen_p, total)
LOG("TOTALE tentativi gruppo P:", len(S.names), "(singoli", m_s, "+ coppie", total, ")")
fin = finalize(S)
pickle.dump(dict(fin=fin, names=S.names, top_sel=S.top_sel, top_old=S.top_old, n_single=m_s, n_pairs=total, cal=cal, Y=S.Y, rows=S.rows, n_rel=n_rel, n_var=n_var, n_mac=n_mac), open("/tmp/r200k_P.pkl", "wb"))
LOG("salvato /tmp/r200k_P.pkl")
