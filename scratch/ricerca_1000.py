"""Segue PROTOCOLLO_RICERCA_1000.md (scritto prima dei calcoli)."""
import json, sys, time, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import store
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX
t_start = time.time()
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]
cal = sp.index[sp.index >= "1990-01-01"]; N = len(cal)
def R(k, lag=0):
    s = store.load(k).dropna(); s = s[~s.index.duplicated()]
    s = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    return s.shift(lag) if lag else s
C = sp.reindex(cal); O, H, L, V = R("sp_open"), R("sp_high"), R("sp_low"), R("sp_vol"); r = C.pct_change(); Cn = C.to_numpy()
# ---------------- episodi
allp = [p for p in range(20, N - 120) if Cn[p] == Cn[p - 20:p + 21].max() and Cn[p + 1:p + 121].min() / Cn[p] - 1 <= -0.05]
posd = lambda d: cal.searchsorted(pd.Timestamp(d))
ext_pos = [posd(d) for d in ESTERNI]; mix_pos = [posd(d) for d in MISTE_MAX]; cls_ext = [posd(m) for m, _, nat, _ in CLASSIFICA if nat == "esterna" and pd.Timestamp(m) >= cal[0]]
esterno = lambda p: any(p - 5 <= e <= p + 60 for e in ext_pos) or any(abs(p - e) < 5 for e in cls_ext + mix_pos)
TA = np.array([p for p in allp if not esterno(p)]); DA = np.array([Cn[p + 1:p + 121].min() / Cn[p] - 1 for p in TA])
yrA = np.array([cal[i].year for i in TA])
TG = {"A": (TA, yrA <= 2007), "B": (TA[DA <= -0.10], yrA[DA <= -0.10] <= 2007)}
print("episodi A", len(TA), "B", int((DA <= -0.10).sum()), {k: (int(v[1].sum()), int((~v[1]).sum())) for k, v in TG.items()}, flush=True)
WIN = {"W": (10, 2), "W2": (3, 2), "W5": (6, 4), "W10": (10, 7)}
zona = np.zeros(N, bool)
for p in allp: zona[max(0, p - 40):min(N, p + 11)] = True
for e in ext_pos + mix_pos: zona[max(0, e - 5):min(N, e + 61)] = True
okday = (~zona) & (np.arange(N) >= 500 + 252)
yrs = np.array([d.year for d in cal]); base_sel = okday & (yrs <= 2007); base_ver = okday & (yrs >= 2008)
# ---------------- fabbrica di segnali
FEAT = {}
NS = (2, 3, 5, 10, 20, 40, 60, 120, 252)
def gen(nm, x):
    x = x.astype(float).replace([np.inf, -np.inf], np.nan)
    if x.first_valid_index() is None or x.first_valid_index() > pd.Timestamp("1999-12-31"): return
    pos = bool((x.dropna() > 0).all()); lx = np.log(x) if pos else x
    for n in NS: FEAT[f"{nm}|chg{n}"] = lx.diff(n)
    for n in (20, 60, 120, 252): FEAT[f"{nm}|z{n}"] = (x - x.rolling(n).mean()) / x.rolling(n).std()
    for n in (5, 10, 20, 60, 120, 252):
        FEAT[f"{nm}|dmax{n}"] = lx - lx.rolling(n).max(); FEAT[f"{nm}|dmin{n}"] = lx - lx.rolling(n).min()
        FEAT[f"{nm}|vol{n}"] = lx.diff().rolling(n).std(); FEAT[f"{nm}|stoc{n}"] = (x - x.rolling(n).min()) / (x.rolling(n).max() - x.rolling(n).min())
    for n in (5, 10, 20, 60): FEAT[f"{nm}|acc{n}"] = lx.diff(n) - lx.diff(n).shift(n)
rv20 = r.rolling(20).std(); vix = R("vix")
base_series = {"sp": C, "ampiezza": (H - L) / C, "volume": V, "vix": vix, "skew": R("skew"), "vix_su_rv": vix / (rv20 * np.sqrt(252) * 100), "rv20": rv20,
               "nasdaq": R("nasdaq100"), "rut": R("rut"), "mid": R("cn_mid"), "oex": R("cn_oex"), "dax": R("dax"), "nikkei": R("nikkei"),
               "baa": R("baa10y", 1), "hy": R("hy_fondo", 1), "ig": R("ig_fondo", 1), "ciss": R("ciss", 1), "curva3m": R("t10y3m", 1), "curva2a": R("t10y2y", 1),
               "t10": R("dgs10", 1), "t2": R("dgs2", 1), "dollaro": R("dxy", 1), "yen": R("jpy", 1), "fed": R("fedfunds", 1)}
for k in ("nasdaq", "rut", "mid", "oex", "dax", "nikkei"): base_series[k + "_su_sp"] = base_series[k] / C
for k in ("xlb", "xle", "xlf", "xli", "xlk", "xlp", "xlu", "xlv", "xly"):
    s = R("sec_" + k); base_series[k] = s; base_series[k + "_su_sp"] = s / C
for nm, x in base_series.items(): gen(nm, x)
n_gen = len(FEAT)
# specifiche S&P
def add(n, x): FEAT["sp_spec|" + n] = x
d = C.diff()
for n in (2, 3, 5, 14):
    up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean(); add(f"rsi{n}", 100 - 100 / (1 + up / dn))
for n in (20, 50): m_, s_ = C.rolling(n).mean(), C.rolling(n).std(); add(f"bollinger{n}", (C - m_) / (2 * s_))
for n in (5, 14): add(f"stocastico{n}", (C - L.rolling(n).min()) / (H.rolling(n).max() - L.rolling(n).min()))
e12, e26 = C.ewm(span=12).mean(), C.ewm(span=26).mean(); mac = e12 - e26; add("macd", mac / C); add("macd_diff", (mac - mac.ewm(span=9).mean()) / C)
sg = np.sign(r).fillna(0); run = sg.groupby((sg != sg.shift()).cumsum()).cumcount() + 1; add("giorni_consecutivi_con_segno", run * sg)
for n in (5, 10, 20):
    for th in (0.01, 0.02): add(f"giorni_sopra_{th}_{n}", (r > th).rolling(n).sum()); add(f"giorni_sotto_{th}_{n}", (r < -th).rolling(n).sum())
    add(f"gap_giu_{n}", (O / C.shift(1) - 1 < -0.003).rolling(n).sum()); add(f"gap_su_{n}", (O / C.shift(1) - 1 > 0.003).rolling(n).sum())
    add(f"volume_su_giu_{n}", (V * (r > 0)).rolling(n).sum() / (V * (r < 0)).rolling(n).sum()); add(f"ombra_sup_{n}", ((H - np.maximum(O, C)) / (H - L)).rolling(n).mean())
    add(f"ombra_inf_{n}", ((np.minimum(O, C) - L) / (H - L)).rolling(n).mean()); add(f"chiusura_range_{n}", ((C - L) / (H - L)).rolling(n).mean())
add("chiusura_range_3", ((C - L) / (H - L)).rolling(3).mean())
obv = (sg * V).cumsum()
for n in (20, 60): add(f"obv_{n}", (obv - obv.shift(n)) / V.rolling(n).mean())
for lag in (1, 2, 3, 4, 5):
    for n in (20, 60): add(f"autocorr{lag}_{n}", r.rolling(n).corr(r.shift(lag)))
for n in (20, 60, 120): add(f"asimmetria_{n}", r.rolling(n).skew()); add(f"curtosi_{n}", r.rolling(n).kurt())
for n in (60, 120): add(f"rapporto_varianza_{n}", C.pct_change(5).rolling(n).var() / (5 * r.rolling(n).var()))
for m in (60, 252):
    mxm = C.rolling(m).max()
    for th in (0.005, 0.01, 0.02):
        for n in (10, 20, 60): add(f"vicino_max{m}_{th}_{n}", (C >= mxm * (1 - th)).rolling(n).sum())
    for n in (10, 20): add(f"nuovi_max{m}_{n}", (C == mxm).rolling(n).sum()); add(f"nuovi_min{m}_{n}", (C == C.rolling(m).min()).rolling(n).sum())
for n in (10, 20, 50, 100, 200): add(f"dist_media{n}", C / C.rolling(n).mean() - 1)
add("media20_su_50", C.rolling(20).mean() / C.rolling(50).mean() - 1); add("media50_su_200", C.rolling(50).mean() / C.rolling(200).mean() - 1)
for n in (20, 50, 200): add(f"pendenza_media{n}", C.rolling(n).mean().pct_change(10))
add("drawdown", C / C.cummax() - 1); s_ = (C == C.rolling(252).max()).astype(int); gg = s_.cumsum(); add("sedute_dal_max252", gg.groupby(gg).cumcount().astype(float))
add("livello_tondo", pd.Series((Cn % 100) / 100, index=cal)); add("mese", pd.Series(cal.month.astype(float), index=cal)); add("giorno_settimana", pd.Series(cal.weekday.astype(float), index=cal))
add("giorno_del_mese", pd.Series(cal.day.astype(float), index=cal))
fr = pd.Series(np.nan, index=cal)
for y in range(1990, 2027):
    for m in range(1, 13):
        f = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D"); f = f[(f.month == m) & (f.weekday == 4)]
        if len(f) >= 3:
            d0 = f[2]; i0 = cal.searchsorted(d0)
            for j in range(max(0, i0 - 25), min(N, i0 + 1)): fr.iloc[j] = i0 - j
add("sedute_a_scadenza_opzioni", fr.ffill().fillna(25))
n_spec = len(FEAT) - n_gen
names = list(FEAT); M = len(names)
X = np.column_stack([FEAT[n].replace([np.inf, -np.inf], np.nan).to_numpy(dtype=np.float64) for n in names]).astype(np.float32)
print(f"tentativi singoli: generici {n_gen}, specifici S&P {n_spec}, totale {M}  (tempo {time.time()-t_start:.0f}s)", flush=True)
# ---------------- U = posizione nella distribuzione di base del proprio periodo
def cdf_matrix(base):
    U = np.full((N, M), np.nan, np.float32)
    for j in range(M):
        b = X[base, j]; b = np.sort(b[np.isfinite(b)])
        if len(b) < 300: continue
        v = X[:, j]; ok = np.isfinite(v)
        U[ok, j] = ((np.searchsorted(b, v[ok], "left") + np.searchsorted(b, v[ok], "right")) / 2 / len(b)).astype(np.float32)
    return U
Us, Uv = cdf_matrix(base_sel), cdf_matrix(base_ver)
def prefix(U):
    z = np.nan_to_num(U, nan=0.0).astype(np.float64); c = np.isfinite(U).astype(np.float64)
    return np.vstack([np.zeros((1, U.shape[1])), np.cumsum(z, 0)]), np.vstack([np.zeros((1, U.shape[1])), np.cumsum(c, 0)])
PSs, CSs = prefix(Us); PSv, CSv = prefix(Uv)
def ep_auc(PS, CS, T, k="W"):
    a_, b_ = WIN[k]; out = np.full((len(T), PS.shape[1]), np.nan)
    for i, t in enumerate(T):
        lo, hi = max(0, t - a_), min(N - 1, t - b_)
        if hi < lo: continue
        s = PS[hi + 1] - PS[lo]; c = CS[hi + 1] - CS[lo]; ok = c > 0; out[i, ok] = s[ok] / c[ok]
    return out
def mean_ep(E, need=0.7):
    cnt = np.isfinite(E).sum(0); m = np.nanmean(np.where(np.isfinite(E), E, np.nan), axis=0); m[cnt < need * E.shape[0]] = np.nan; return m
rng = np.random.default_rng(2511); RESULT = {"n_generici": n_gen, "n_specifici": n_spec, "M": M}
NSH = 500
def run_target(tg):
    T, sel = TG[tg]; Tsel, Tver = T[sel], T[~sel]
    Es = ep_auc(PSs, CSs, Tsel); a_sel = mean_ep(Es); stat = np.where(np.isfinite(a_sel), np.maximum(a_sel, 1 - a_sel), np.nan); ori = np.where(a_sel >= 0.5, 1, -1)
    # interazioni dai primi 20 della selezione
    top20 = list(np.argsort(-np.nan_to_num(stat, nan=0))[:20]); pairs = [(i, j) for ii, i in enumerate(top20) for j in top20[ii + 1:]]
    def orient(U, j, o): return U[:, j] if o > 0 else 1 - U[:, j]
    def pair_stats(Ush, ori_, pr, Tsh, base_idx):
        res = []
        for (i, j) in pr:
            si, sj = orient(Ush, i, ori_[i]), orient(Ush, j, ori_[j])
            for kind in ("min", "prod"):
                s = np.minimum(si, sj) if kind == "min" else si * sj
                b = np.sort(s[base_idx][np.isfinite(s[base_idx])])
                if len(b) < 300: res.append(np.nan); continue
                e = []
                for t in Tsh:
                    w = s[max(0, t - 10):t - 1]; w = w[np.isfinite(w)]
                    if len(w): e.append(float(((np.searchsorted(b, w, "left") + np.searchsorted(b, w, "right")) / 2 / len(b)).mean()))
                res.append(float(np.mean(e)) if len(e) >= 0.7 * len(Tsh) else np.nan)
        return np.array(res)
    base_idx_s = np.where(base_sel)[0]
    pa = pair_stats(Us, ori, pairs, Tsel, base_idx_s); pstat = np.maximum(pa, 1 - pa)
    # soglia migliore-fra-N
    mxs = []
    for _ in range(NSH):
        off = int(rng.integers(250, N - 250)); Ts = (T + off) % N; Tss = Ts[sel]
        E = ep_auc(PSs, CSs, Tss); a_ = mean_ep(E); st = np.where(np.isfinite(a_), np.maximum(a_, 1 - a_), np.nan)
        o_ = np.where(a_ >= 0.5, 1, -1); t20 = list(np.argsort(-np.nan_to_num(st, nan=0))[:20]); pr = [(i, j) for ii, i in enumerate(t20) for j in t20[ii + 1:]]
        ps = pair_stats(Us, o_, pr[:60], Tss, base_idx_s)   # sottoinsieme (60 coppie) per tempo: conservativo? vedi nota
        mxs.append(max(np.nanmax(st), np.nanmax(np.maximum(ps, 1 - ps)) if np.isfinite(ps).any() else 0))
    soglia = float(np.percentile(mxs, 95)); print(f"[{tg}] soglia caso (95°): {soglia:.3f}  mediana massimi {np.median(mxs):.3f}  episodi sel {len(Tsel)} ver {len(Tver)}", flush=True)
    # verifica
    Ev = ep_auc(PSv, CSv, Tver); Evi = np.where(ori[None, :] > 0, Ev, 1 - Ev); a_ver = mean_ep(Evi, 0.5)
    E2 = ep_auc(PSv, CSv, Tver, "W2"); a_w2 = np.where(ori > 0, mean_ep(E2, 0.5), 1 - mean_ep(E2, 0.5))
    bs = np.array([np.nanmean(Evi[rng.integers(0, len(Tver), len(Tver))], axis=0) for _ in range(1000)]); ic_lo = np.nanpercentile(bs, 5, axis=0)
    rows = []
    for j in range(M):
        if np.isfinite(stat[j]):
            rows.append(dict(nome=names[j], sel=float(stat[j]), verso=int(ori[j]), ver=float(a_ver[j]), ver_W2=float(a_w2[j]), ic90=float(ic_lo[j]),
                             passa_sel=bool(stat[j] > soglia and stat[j] >= 0.60), passa_ver=bool(stat[j] > soglia and stat[j] >= 0.60 and a_ver[j] >= 0.56 and ic_lo[j] > 0.5 and a_w2[j] > 0.5)))
    df = pd.DataFrame(rows).sort_values("sel", ascending=False)
    print(f"[{tg}] tentativi valutati {len(df)} + interazioni {len(pstat)}; max interazione {np.nanmax(pstat):.3f}")
    print(df.head(20).round(3).to_string(index=False)); print(f"[{tg}] passano selezione:", int(df.passa_sel.sum()), " passano verifica:", int(df.passa_ver.sum()))
    # per ridurre la selezione-bias: migliori in verifica fra i 100 migliori in selezione
    print(f"[{tg}] fra i primi 100 della selezione, AUC verifica media {df.head(100).ver.mean():.3f} (mediana {df.head(100).ver.median():.3f}); quota con ver>=0.56: {(df.head(100).ver>=0.56).mean():.2f}")
    # combinazioni top-K (valutate in verifica)
    comp = {}
    order = list(np.argsort(-np.nan_to_num(stat, nan=0)))
    bidx_v = np.where(base_ver)[0]
    def comp_score(Uv_, idx): return np.nanmean(np.column_stack([orient(Uv_, j, ori[j]) for j in idx]), axis=1)
    for K in (3, 5, 10, 20, 50):
        idx = order[:K]; s = comp_score(Uv, idx); b = np.sort(s[bidx_v][np.isfinite(s[bidx_v])])
        def ea(Tx, win_=(10, 2)):
            e = []
            for t in Tx:
                w = s[max(0, t - win_[0]):t - win_[1] + 1]; w = w[np.isfinite(w)]
                if len(w): e.append(float(((np.searchsorted(b, w, "left") + np.searchsorted(b, w, "right")) / 2 / len(b)).mean()))
            return e
        e = ea(Tver); obs = float(np.mean(e)); w2 = float(np.mean(ea(Tver, (3, 2))))
        nulls = [float(np.mean(ea((Tver + int(rng.integers(250, N - 250))) % N))) for _ in range(NSH)]
        p = (1 + sum(x >= obs for x in nulls)) / (NSH + 1); bsc = np.percentile([np.mean(rng.choice(e, len(e))) for _ in range(1000)], 5)
        comp[f"top{K}"] = dict(ver=obs, W2=w2, ic90=float(bsc), p=float(p), p_corr=float(min(1, p * 10)), passa=bool(obs >= 0.60 and bsc > 0.5 and min(1, p * 10) < 0.05))
        print(f"[{tg}] combinazione top{K}: ver {obs:.3f} W2 {w2:.3f} ic90 {bsc:.3f} p {p:.3f} p_corr {min(1,p*10):.3f} -> {'PASSA' if comp[f'top{K}']['passa'] else 'no'}", flush=True)
    RESULT[tg] = dict(soglia=soglia, tabella=df.head(60).to_dict("records"), comp=comp, n_pass_sel=int(df.passa_sel.sum()), n_pass_ver=int(df.passa_ver.sum()), n_int=len(pstat), max_int=float(np.nanmax(pstat)))
    return df, ori, stat, order
out_dfs = {}
for tg in ("A", "B"):
    out_dfs[tg] = run_target(tg)
json.dump(RESULT, open("scratch/ricerca_1000_esito.json", "w"), indent=1, default=float)
print("finito singoli+combinazioni, tempo", round(time.time() - t_start), "s", flush=True)

# ================= STADIO 2: modelli in avanti e allarmi (protocollo)
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
df, ori, stat, order = out_dfs["A"]; T, sel = TG["A"]; Tver = T[~sel]; Tall = T
bidx_v = np.where(base_ver)[0]; first_v = int(np.where(yrs >= 2008)[0][0])
def eval_score(s, label, valid_from=first_v):
    b = np.sort(s[bidx_v][np.isfinite(s[bidx_v])])
    def ea(Tx, w_=(10, 2)):
        e = []
        for t_ in Tx:
            w = s[max(0, t_ - w_[0]):t_ - w_[1] + 1]; w = w[np.isfinite(w)]
            if len(w): e.append(float(((np.searchsorted(b, w, "left") + np.searchsorted(b, w, "right")) / 2 / len(b)).mean()))
        return e
    e = ea(Tver); obs = float(np.mean(e)); w2 = float(np.mean(ea(Tver, (3, 2)))); span = N - valid_from
    nulls = [float(np.mean(ea(((Tver - valid_from + int(rng.integers(250, span - 250))) % span) + valid_from))) for _ in range(500)]
    p = (1 + sum(x >= obs for x in nulls)) / 501; ic = float(np.percentile([np.mean(rng.choice(e, len(e))) for _ in range(1000)], 5))
    pc = min(1, p * 10); ok = bool(obs >= 0.60 and ic > 0.5 and pc < 0.05)
    print(f"[A] {label}: ver {obs:.3f} W2 {w2:.3f} ic90 {ic:.3f} p {p:.3f} p_corr {pc:.3f} -> {'PASSA' if ok else 'no'}", flush=True)
    return dict(ver=obs, W2=w2, ic90=ic, p=float(p), p_corr=float(pc), passa=ok)
# --- modelli walk-forward
Xc = np.nan_to_num(X, nan=0.0)
posmask = np.zeros(N, bool)
for t_ in T:
    posmask[max(0, t_ - 10):t_ - 1] = True
pred = {k: np.full(N, np.nan) for k in ("ML1_logistica500", "ML2_logistica50", "ML3_alberi50", "ML4_media20")}
print("addestramento in avanti...", flush=True)
for Y in range(2008, 2027):
    i0 = int(np.where(yrs >= Y)[0][0]); cut = i0 - 130; i1 = int(np.where(yrs >= Y + 1)[0][0]) if (yrs >= Y + 1).any() else N
    trn = np.arange(N) < cut; neg = trn & okday & (np.arange(N) % 2 == 0); posi = trn & posmask & (np.arange(N) >= 500 + 252)
    # episodi i cui picchi sono ben prima del cutoff
    idx = np.where(neg | posi)[0]; y = posmask[idx].astype(int)
    if y.sum() < 20: continue
    Xt = np.where(np.isfinite(X[idx]), X[idx], np.nan); med = np.nanmedian(Xt, axis=0); Xt = np.where(np.isnan(Xt), med, Xt)
    rk = rankdata(Xt, axis=0); n1 = y.sum(); n0 = len(y) - n1; auc = (rk[y == 1].sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0); sc = np.abs(auc - 0.5)
    mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
    def prep(rows, cols): z = (np.where(np.isfinite(X[rows][:, cols]), X[rows][:, cols], med[cols]) - mu[cols]) / sd[cols]; return np.clip(z, -5, 5)
    te = np.arange(i0, i1); o500 = np.argsort(-sc)[:500]; o50 = np.argsort(-sc)[:50]; o20 = np.argsort(-sc)[:20]
    Z5 = np.clip((Xt[:, o500] - mu[o500]) / sd[o500], -5, 5); m1 = LogisticRegression(C=0.01, max_iter=300, class_weight="balanced").fit(Z5, y)
    pred["ML1_logistica500"][te] = m1.decision_function(prep(te, o500))
    Z50 = np.clip((Xt[:, o50] - mu[o50]) / sd[o50], -5, 5); m2 = LogisticRegression(C=0.1, max_iter=300, class_weight="balanced").fit(Z50, y)
    pred["ML2_logistica50"][te] = m2.decision_function(prep(te, o50))
    m3 = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, random_state=0).fit(Z50, y)
    pred["ML3_alberi50"][te] = m3.predict_proba(prep(te, o50))[:, 1]
    sgn = np.sign(auc[o20] - 0.5); pred["ML4_media20"][te] = (prep(te, o20) * sgn).mean(1)
print("addestramento finito", flush=True)
RES2 = {}
for k, s in pred.items(): RES2[k] = eval_score(s, k)
# --- allarmi per le combinazioni migliori
def pctexp(v): return pd.Series(v).expanding(500).rank(pct=True).to_numpy()
fall20 = np.array([Cn[i + 1:i + 21].min() / Cn[i] - 1 if i + 20 < N else np.nan for i in range(N)])
for K in (10, 20, 50):
    idx = order[:K]; comp = np.nanmean(np.column_stack([pctexp(X[:, j] * ori[j]) for j in idx]), axis=1); cp = pctexp(comp)
    pad = np.isfinite(cp); verd = (yrs >= 2008)
    for q in (0.8, 0.9, 0.95):
        al = (cp >= q) & pad
        hit = np.mean([al[max(0, t_ - 10):t_ - 1].any() for t_ in Tver]); hit5 = np.mean([al[max(0, t_ - 6):t_ - 3].any() for t_ in Tver])
        fa = al[base_ver].mean(); sel_ = al & verd & np.isfinite(fall20); prec = float((fall20[sel_] <= -0.05).mean()); basec = float((fall20[verd & np.isfinite(fall20) & pad] <= -0.05).mean())
        lead = []
        for t_ in Tver:
            seg = np.arange(max(0, t_ - 20), t_ - 1); f_ = np.where(al[seg])[0]
            if len(f_): lead.append(int(t_ - seg[f_[0]]))
        RES2[f"allarme_top{K}_q{q}"] = dict(episodi_con_allarme_W=float(hit), episodi_allarme_p6_p4=float(hit5), giorni_base_in_allarme=float(fa), precisione=prec, frequenza_base=basec, anticipo_mediano=(float(np.median(lead)) if lead else None), giorni_allarme_quota=float(al[verd].mean()))
        print(f"allarme top{K} q{q}: episodi con allarme in W {hit:.2f} (W5 {hit5:.2f}), giorni di base in allarme {fa:.2f}, precisione {prec:.2f} (base {basec:.2f}), anticipo mediano {np.median(lead) if lead else None}", flush=True)
RESULT["stadio2"] = RES2; RESULT["top10_nomi"] = [names[j] for j in order[:10]]; RESULT["top20_nomi"] = [names[j] for j in order[:20]]
json.dump(RESULT, open("scratch/ricerca_1000_esito.json", "w"), indent=1, default=float)
print("top10 A:", RESULT["top10_nomi"]); print("fine totale", round(time.time() - t_start), "s", flush=True)
