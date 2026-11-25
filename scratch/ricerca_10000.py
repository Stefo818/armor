"""Segue PROTOCOLLO_RICERCA_10000.md (+ aggiunta), scritto prima dei calcoli."""
import json, sys, time, warnings, itertools
import numpy as np, pandas as pd
from scipy.stats import rankdata
warnings.filterwarnings("ignore")
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import store
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX
T_START = time.time(); LOG = lambda *a: print(f"[{time.time()-T_START:5.0f}s]", *a, flush=True)
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]
cal = sp.index[sp.index >= "1990-01-01"]; N = len(cal); yrs = np.array([d.year for d in cal]); qtr = np.array([d.year * 4 + (d.month - 1) // 3 for d in cal])
def R(k, lag=0):
    s = store.load(k).dropna(); s = s[~s.index.duplicated()]
    s = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    return s.shift(lag) if lag else s
C = sp.reindex(cal); O, H, L, V = R("sp_open"), R("sp_high"), R("sp_low"), R("sp_vol"); r = C.pct_change(); Cn = C.to_numpy()
posd = lambda d: cal.searchsorted(pd.Timestamp(d))
# ---------------- bersagli
fall20 = np.array([Cn[i + 1:i + 21].min() / Cn[i] - 1 if i + 20 < N else np.nan for i in range(N)])
fall40 = np.array([Cn[i + 1:i + 41].min() / Cn[i] - 1 if i + 40 < N else np.nan for i in range(N)])
ext = np.zeros(N, bool)
for d in ESTERNI + MISTE_MAX: ext[max(0, posd(d) - 5):min(N, posd(d) + 61)] = True
valid0 = (~ext) & (np.arange(N) >= cal.searchsorted(pd.Timestamp("1992-01-01")))
dd20 = (C / C.rolling(20).max() - 1).to_numpy()
Y = {"T1": (fall20 <= -0.05).astype(float), "T2": (fall40 <= -0.08).astype(float), "T3": (fall20 <= -0.05).astype(float)}
MASK = {"T1": valid0 & np.isfinite(fall20), "T2": valid0 & np.isfinite(fall40), "T3": valid0 & np.isfinite(fall20) & (dd20 <= -0.02) & (dd20 >= -0.06)}
for k in MASK: LOG(k, "giorni validi", int(MASK[k].sum()), "frequenza evento", round(float(Y[k][MASK[k]].mean()), 3), "selezione", int((MASK[k] & (yrs <= 2007)).sum()), "verifica", int((MASK[k] & (yrs >= 2008)).sum()))
# ---------------- segnali
FEAT = {}
def put(n, x):
    a = x.to_numpy(dtype=np.float64) if hasattr(x, "to_numpy") else np.asarray(x, float)
    a = np.where(np.isfinite(a), a, np.nan); FEAT[n] = a.astype(np.float32)
NS = (2, 3, 5, 10, 20, 40, 60, 120, 252)
def gen(nm, x):
    x = x.astype(float).replace([np.inf, -np.inf], np.nan)
    if x.first_valid_index() is None or x.first_valid_index() > pd.Timestamp("1999-12-31"): return
    pos = bool((x.dropna() > 0).all()); lx = np.log(x) if pos else x; dl = lx.diff()
    for n in NS: put(f"{nm}|chg{n}", lx.diff(n))
    for n in (20, 60, 120, 252): put(f"{nm}|z{n}", (x - x.rolling(n).mean()) / x.rolling(n).std())
    for n in (5, 10, 20, 60, 120, 252):
        put(f"{nm}|dmax{n}", lx - lx.rolling(n).max()); put(f"{nm}|dmin{n}", lx - lx.rolling(n).min())
        put(f"{nm}|vol{n}", dl.rolling(n).std()); put(f"{nm}|stoc{n}", (x - x.rolling(n).min()) / (x.rolling(n).max() - x.rolling(n).min()))
    for n in (5, 10, 20, 60): put(f"{nm}|acc{n}", lx.diff(n) - lx.diff(n).shift(n))
    # estese
    for sp_ in (10, 30, 90): put(f"{nm}|ewz{sp_}", (x - x.ewm(span=sp_).mean()) / x.ewm(span=sp_).std())
    for n in (20, 60, 120): put(f"{nm}|corrsp{n}", dl.rolling(n).corr(r))
    for n in (20, 60): put(f"{nm}|skew{n}", dl.rolling(n).skew())
    for a_, b_ in ((2, 5), (5, 20), (10, 60), (20, 120), (60, 252)): put(f"{nm}|momd{a_}_{b_}", lx.diff(a_) / a_ - lx.diff(b_) / b_)
    for a_, b_ in ((5, 20), (10, 60), (20, 120), (60, 252)): put(f"{nm}|volr{a_}_{b_}", dl.rolling(a_).std() / dl.rolling(b_).std())
    for n in (5, 10, 20, 60): put(f"{nm}|upfrac{n}", (dl > 0).rolling(n).mean())
    sg = np.sign(dl).fillna(0); put(f"{nm}|serie", (sg.groupby((sg != sg.shift()).cumsum()).cumcount() + 1) * sg); put(f"{nm}|dd_storico", lx - lx.cummax())
    for n in (5, 20):
        for lag in (1, 2, 3, 5): put(f"{nm}|chg{n}_ritardo{lag}", lx.diff(n).shift(lag))
    c5 = lx.diff(5); put(f"{nm}|chg5_max20", c5.rolling(20).max()); put(f"{nm}|chg5_min20", c5.rolling(20).min())
    v20 = dl.rolling(20).std(); put(f"{nm}|vol20_chg20", v20.diff(20) / v20.shift(20)); put(f"{nm}|vol20_z252", (v20 - v20.rolling(252).mean()) / v20.rolling(252).std())
rv20 = r.rolling(20).std(); vix = R("vix")
bs = {"sp": C, "ampiezza": (H - L) / C, "volume": V, "vix": vix, "skew": R("skew"), "vix_su_rv": vix / (rv20 * np.sqrt(252) * 100), "rv20": rv20,
      "nasdaq": R("nasdaq100"), "rut": R("rut"), "mid": R("cn_mid"), "oex": R("cn_oex"), "dax": R("dax"), "nikkei": R("nikkei"),
      "baa": R("baa10y", 1), "hy": R("hy_fondo", 1), "ig": R("ig_fondo", 1), "ciss": R("ciss", 1), "curva3m": R("t10y3m", 1), "curva2a": R("t10y2y", 1),
      "t10": R("dgs10", 1), "t2": R("dgs2", 1), "dollaro": R("dxy", 1), "yen": R("jpy", 1), "fed": R("fedfunds", 1)}
for k in ("nasdaq", "rut", "mid", "oex", "dax", "nikkei"): bs[k + "_su_sp"] = bs[k] / C
SECS = ("xlb", "xle", "xlf", "xli", "xlk", "xlp", "xlu", "xlv", "xly")
for k in SECS: s = R("sec_" + k); bs[k] = s; bs[k + "_su_sp"] = s / C
for nm, x in bs.items(): gen(nm, x)
n_gen = len(FEAT); LOG("fabbrica generica+estesa:", n_gen)
def add(n, x): put("sp_spec|" + n, x)
d = C.diff()
for n in (2, 3, 4, 5, 7, 9, 14, 21, 30):
    up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean(); add(f"rsi{n}", 100 - 100 / (1 + up / dn))
for n in (20, 50): m_, s_ = C.rolling(n).mean(), C.rolling(n).std(); add(f"bollinger{n}", (C - m_) / (2 * s_))
for n in (5, 14): add(f"stocastico{n}", (C - L.rolling(n).min()) / (H.rolling(n).max() - L.rolling(n).min()))
mac = C.ewm(span=12).mean() - C.ewm(span=26).mean(); add("macd", mac / C); add("macd_diff", (mac - mac.ewm(span=9).mean()) / C)
sg = np.sign(r).fillna(0); add("giorni_consecutivi", (sg.groupby((sg != sg.shift()).cumsum()).cumcount() + 1) * sg)
for n in (5, 10, 20):
    for th in (0.01, 0.02): add(f"giorni_sopra_{th}_{n}", (r > th).rolling(n).sum()); add(f"giorni_sotto_{th}_{n}", (r < -th).rolling(n).sum())
    add(f"gap_giu_{n}", (O / C.shift(1) - 1 < -0.003).rolling(n).sum()); add(f"gap_su_{n}", (O / C.shift(1) - 1 > 0.003).rolling(n).sum())
    add(f"volume_su_giu_{n}", (V * (r > 0)).rolling(n).sum() / (V * (r < 0)).rolling(n).sum()); add(f"ombra_sup_{n}", ((H - np.maximum(O, C)) / (H - L)).rolling(n).mean())
    add(f"ombra_inf_{n}", ((np.minimum(O, C) - L) / (H - L)).rolling(n).mean()); add(f"chiusura_range_{n}", ((C - L) / (H - L)).rolling(n).mean())
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
add("livello_tondo", pd.Series((Cn % 100) / 100, index=cal)); add("mese", pd.Series(cal.month.astype(float), index=cal)); add("giorno_settimana", pd.Series(cal.weekday.astype(float), index=cal)); add("giorno_del_mese", pd.Series(cal.day.astype(float), index=cal))
# ampiezza
Sd = pd.DataFrame({k: R("sec_" + k) for k in SECS}); IDX = pd.DataFrame({"nd": bs["nasdaq"], "ru": bs["rut"], "mi": bs["mid"], "oe": bs["oex"], "dx": bs["dax"], "nk": bs["nikkei"]}); ALLP = pd.concat([Sd, IDX], axis=1)
for n in (20, 50, 100, 200):
    put(f"ampiezza|settori_sopra_media{n}", (Sd > Sd.rolling(n).mean()).mean(axis=1).where(Sd.rolling(n).mean().notna().all(axis=1)))
    put(f"ampiezza|tutti_sopra_media{n}", (ALLP > ALLP.rolling(n).mean()).mean(axis=1).where(ALLP.rolling(n).mean().notna().all(axis=1)))
for n in (5, 20): put(f"ampiezza|dispersione_{n}", Sd.pct_change(n).std(axis=1))
rs = Sd.pct_change(); ew = rs.mean(axis=1)
for n in (20, 60): mv = (rs ** 2).rolling(n).mean().mean(axis=1); put(f"ampiezza|correlazione_{n}", (ew.rolling(n).var() - mv / 9) / (mv * (1 - 1 / 9)))
for n in (20, 60, 252): put(f"ampiezza|settori_max{n}", (Sd == Sd.rolling(n).max()).sum(axis=1)); put(f"ampiezza|settori_min{n}", (Sd == Sd.rolling(n).min()).sum(axis=1))
put("ampiezza|tutti_rend20_pos", (ALLP.pct_change(20) > 0).mean(axis=1).where(ALLP.notna().all(axis=1))); put("ampiezza|tutti_dd60_5", ((ALLP / ALLP.rolling(60).max() - 1) < -0.05).mean(axis=1).where(ALLP.notna().all(axis=1)))
n_sing = len(FEAT); LOG("segnali singoli:", n_sing)
# ---------------- coppie fisse (60 mattoni, versi fissati ora)
BLOCKS = [("sp|chg5", 1), ("sp|chg10", 1), ("sp|chg20", 1), ("sp|chg60", 1), ("sp|dmax20", 1), ("sp|dmin20", 1), ("sp|dmax60", 1), ("sp|vol5", 1), ("sp|vol20", 1), ("sp|vol60", 1),
          ("sp|z20", 1), ("sp|z60", 1), ("sp|stoc20", 1), ("sp_spec|dist_media20", 1), ("sp_spec|dist_media50", 1), ("sp_spec|rsi14", 1), ("sp_spec|rsi2", 1), ("sp_spec|drawdown", -1),
          ("vix|chg5", 1), ("vix|chg20", 1), ("vix|z20", 1), ("vix|z60", 1), ("vix|stoc20", 1), ("vix|dmin20", 1), ("vix_su_rv|z60", 1), ("skew|chg10", 1), ("skew|z60", 1),
          ("baa|chg20", 1), ("baa|chg5", 1), ("hy|chg20", 1), ("ig|chg20", 1), ("ciss|chg5", 1), ("curva3m|chg20", -1), ("t10|chg20", 1), ("t2|chg20", 1), ("dollaro|chg20", 1), ("yen|vol20", 1),
          ("mid_su_sp|chg20", -1), ("rut_su_sp|chg20", -1), ("nasdaq_su_sp|chg20", 1), ("mid|dmin20", 1), ("mid|chg20", 1), ("rut|chg20", 1), ("xlk_su_sp|chg20", 1), ("xlu_su_sp|chg20", 1),
          ("xlf_su_sp|chg20", -1), ("xly_su_sp|chg20", -1), ("dax_su_sp|chg20", -1), ("nikkei|chg20", -1), ("ampiezza|settori_sopra_media50", -1), ("ampiezza|tutti_sopra_media200", -1),
          ("ampiezza|dispersione_5", 1), ("ampiezza|correlazione_20", 1), ("ampiezza|settori_max60", -1), ("sp|upfrac10", 1), ("sp|volr5_20", 1), ("sp|momd5_20", 1), ("sp|corrsp20", 1), ("vix|corrsp20", 1), ("sp|vol10", 1)]
assert len(BLOCKS) == 60 and all(b in FEAT for b, _ in BLOCKS), [b for b, _ in BLOCKS if b not in FEAT]
Pb = []
for nme, sgn in BLOCKS:
    v = FEAT[nme].astype(np.float64) * sgn; ok = np.isfinite(v); p = np.full(N, np.nan); p[ok] = rankdata(v[ok]) / ok.sum(); Pb.append(p.astype(np.float32))
for i, j in itertools.combinations(range(60), 2):
    a_, b_ = Pb[i], Pb[j]; nm = f"coppia|{BLOCKS[i][0]}&{BLOCKS[j][0]}"
    FEAT[nm + "|min"] = np.minimum(a_, b_); FEAT[nm + "|max"] = np.maximum(a_, b_); FEAT[nm + "|prod"] = a_ * b_; FEAT[nm + "|diff"] = a_ - b_
names = list(FEAT); M = len(names); X = np.column_stack([FEAT[n] for n in names]); del FEAT
LOG(f"TOTALE segnali (singoli {n_sing} + coppie {M - n_sing}) = {M}; + modelli (in seguito)")
# ---------------- selezione/verifica per bersaglio
rng = np.random.default_rng(1011); NSH = 300; RES = {"M": M, "n_singoli": n_sing, "n_coppie": M - n_sing}
def rank_auc_matrix(rows, y):
    Xr = X[rows]; nanf = np.isnan(Xr).mean(0); med = np.nanmedian(Xr, axis=0); Xr = np.where(np.isnan(Xr), med, Xr)
    Rk = np.empty(Xr.shape, np.float32)
    for c0 in range(0, M, 2000): Rk[:, c0:c0 + 2000] = rankdata(Xr[:, c0:c0 + 2000], axis=0)
    n1 = y.sum(); n0 = len(y) - n1
    return Rk, nanf, n1, n0
def auc_from(Rk, y, n1, n0): return (y.astype(np.float32) @ Rk - n1 * (n1 + 1) / 2) / (n1 * n0)
MODELLI = {}
def run_target(tg):
    mk, y_all = MASK[tg], Y[tg]
    rows_s = np.where(mk & (yrs <= 2007))[0]; rows_v = np.where(mk & (yrs >= 2008))[0]; ys, yv = y_all[rows_s], y_all[rows_v]
    Rs, nanf, n1, n0 = rank_auc_matrix(rows_s, ys); a_sel = auc_from(Rs, ys, n1, n0); a_sel[nanf > 0.2] = np.nan
    stat = np.maximum(a_sel, 1 - a_sel); ori = np.where(a_sel >= 0.5, 1, -1)
    mxs = []
    for _ in range(NSH):
        off = int(rng.integers(250, len(rows_s) - 250)); a_ = auc_from(Rs, np.roll(ys, off), n1, n0); a_[nanf > 0.2] = np.nan; mxs.append(np.nanmax(np.maximum(a_, 1 - a_)))
    soglia = float(np.percentile(mxs, 95)); LOG(f"[{tg}] soglia caso (95° pct del massimo su {int(np.isfinite(stat).sum())} segnali): {soglia:.3f}; mediana {np.median(mxs):.3f}; miglior reale {np.nanmax(stat):.3f}")
    Rv, nanv, m1, m0 = rank_auc_matrix(rows_v, yv); a_ver = auc_from(Rv, yv, m1, m0); a_ver_o = np.where(ori > 0, a_ver, 1 - a_ver)
    # lift con soglia congelata
    Xs, Xv = X[rows_s], X[rows_v]; cut = np.nanpercentile(np.where(ori > 0, Xs, -Xs), 90, axis=0); ov = np.where(ori > 0, Xv, -Xv); al = ov >= cut[None, :]
    base_v = yv.mean(); lift = np.array([(yv[al[:, j]].mean() / base_v) if al[:, j].sum() > 20 else np.nan for j in range(M)]); frac = al.mean(0)
    order = np.argsort(-np.nan_to_num(stat, nan=0))
    top = []
    for j in order[:25]:
        top.append(dict(nome=names[j], sel=float(stat[j]), verso=int(ori[j]), ver=float(a_ver_o[j]), lift=float(lift[j]), frazione_allarme=float(frac[j])))
    LOG(f"[{tg}] primi 15 per selezione:"); [LOG("   ", f"{t['nome'][:70]:70s} sel {t['sel']:.3f} ver {t['ver']:.3f} lift {t['lift']:.2f}") for t in top[:15]]
    passa_sel = [j for j in range(M) if np.isfinite(stat[j]) and stat[j] > soglia and stat[j] >= 0.58]
    LOG(f"[{tg}] passano la selezione: {len(passa_sel)}")
    top100 = order[:100]; LOG(f"[{tg}] fra i 100 migliori della selezione: AUC verifica media {np.nanmean(a_ver_o[top100]):.3f}, mediana {np.nanmedian(a_ver_o[top100]):.3f}, quota ≥0.56 {np.mean(a_ver_o[top100] >= 0.56):.2f}; lift mediano {np.nanmedian(lift[top100]):.2f}")
    passati = []
    for j in passa_sel:
        sc = ov[:, j]; bl = np.unique(qtr[rows_v]); idxb = {b: np.where(qtr[rows_v] == b)[0] for b in bl}; aus = []
        for _ in range(300):
            pick = np.concatenate([idxb[b] for b in rng.choice(bl, len(bl))]); yy = yv[pick]
            if yy.sum() < 5 or yy.sum() == len(yy): continue
            rk = rankdata(sc[pick]); aus.append((rk[yy == 1].sum() - yy.sum() * (yy.sum() + 1) / 2) / (yy.sum() * (len(yy) - yy.sum())))
        ic = float(np.percentile(aus, 5)); ok = bool(a_ver_o[j] >= 0.56 and ic > 0.5 and lift[j] >= 1.25)
        passati.append(dict(nome=names[j], sel=float(stat[j]), ver=float(a_ver_o[j]), ic90=ic, lift=float(lift[j]), passa=ok))
    LOG(f"[{tg}] passano anche la verifica: {sum(p['passa'] for p in passati)}", [p for p in passati if p["passa"]][:10])
    RES[tg] = dict(soglia=soglia, top=top, n_pass_sel=len(passa_sel), passati=passati, base_ver=float(base_v), base_sel=float(ys.mean()),
                   top100_ver_media=float(np.nanmean(a_ver_o[top100])), top100_lift_mediano=float(np.nanmedian(lift[top100])))
    return dict(order=order, ori=ori, stat=stat, rows_s=rows_s, rows_v=rows_v, ys=ys, yv=yv)
SEL = {tg: run_target(tg) for tg in ("T1", "T2", "T3")}
json.dump(RES, open("scratch/ricerca_10000_esito.json", "w"), indent=1, default=float); LOG("stadio singoli+coppie finito")
# ---------------- modelli walk-forward
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
ALG = {"logL2_001": lambda: LogisticRegression(C=0.01, max_iter=200), "logL2_01": lambda: LogisticRegression(C=0.1, max_iter=200), "logL1": lambda: LogisticRegression(C=0.05, penalty="l1", solver="liblinear"),
       "lda": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"), "nb": lambda: GaussianNB(), "knn50": lambda: KNeighborsClassifier(50),
       "rf": lambda: RandomForestClassifier(100, max_depth=5, min_samples_leaf=20, n_jobs=2, random_state=0), "et": lambda: ExtraTreesClassifier(100, max_depth=6, min_samples_leaf=20, n_jobs=2, random_state=0),
       "hgb2": lambda: HistGradientBoostingClassifier(max_depth=2, max_iter=100, learning_rate=0.05, random_state=0), "hgb3": lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, random_state=0),
       "hgb4": lambda: HistGradientBoostingClassifier(max_depth=4, max_iter=100, learning_rate=0.05, random_state=0)}
FOLDS = list(range(2008, 2027, 2)); KS = (30, 100, 300); NMOD = len(ALG) * len(KS) * 3; RES["n_modelli"] = NMOD; LOG("modelli:", NMOD)
for tg in ("T1", "T2", "T3"):
    s = SEL[tg]; mk, y_all = MASK[tg], Y[tg]; pool = s["order"][:1500]; PRED = {f"{a}_{k}": np.full(N, np.nan) for a in ALG for k in KS}
    for Y0 in FOLDS:
        i0 = int(np.where(yrs >= Y0)[0][0]); i1 = int(np.where(yrs >= Y0 + 2)[0][0]) if (yrs >= Y0 + 2).any() else N
        trn = np.where(mk & (np.arange(N) < i0 - 45))[0][::2]; te = np.arange(i0, i1); yt = y_all[trn]
        Xt = X[trn][:, pool]; med = np.nanmedian(Xt, axis=0); Xt = np.where(np.isnan(Xt), med, Xt); rk = rankdata(Xt, axis=0); n1_ = yt.sum(); n0_ = len(yt) - n1_
        auc_ = (yt @ rk - n1_ * (n1_ + 1) / 2) / (n1_ * n0_); o_ = np.argsort(-np.abs(auc_ - 0.5)); sg_ = np.sign(auc_ - 0.5)
        Xe = np.where(np.isnan(X[te][:, pool]), med, X[te][:, pool]); mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
        for K in KS:
            cols = o_[:K]; Zt = np.clip((Xt[:, cols] - mu[cols]) / sd[cols], -5, 5); Ze = np.clip((Xe[:, cols] - mu[cols]) / sd[cols], -5, 5)
            for a, mkf in ALG.items():
                try:
                    m = mkf().fit(Zt, yt); PRED[f"{a}_{K}"][te] = m.predict_proba(Ze)[:, 1]
                except Exception as e: pass
    # valutazione modelli
    rows_v = s["rows_v"]; yv = s["yv"]; out = {}; bl = np.unique(qtr[rows_v]); idxb = {b: np.where(qtr[rows_v] == b)[0] for b in bl}
    for k, p in PRED.items():
        sc = p[rows_v]; ok = np.isfinite(sc)
        if ok.sum() < 500 or yv[ok].sum() < 20: continue
        y_ = yv[ok]; sc_ = sc[ok]; rk_ = rankdata(sc_); n1_ = y_.sum(); n0_ = len(y_) - n1_; obs = (rk_[y_ == 1].sum() - n1_ * (n1_ + 1) / 2) / (n1_ * n0_)
        nulls = [(np.roll(y_, int(rng.integers(250, len(y_) - 250)))[None, :] @ rk_ - n1_ * (n1_ + 1) / 2)[0] / (n1_ * n0_) for _ in range(NSH)]
        pv = (1 + sum(x >= obs for x in nulls)) / (NSH + 1)
        aus = []
        for _ in range(200):
            pick = np.concatenate([idxb[b] for b in rng.choice(bl, len(bl))]); pk = pick[ok[pick]]; yy = yv[pk]
            if yy.sum() < 5: continue
            rr = rankdata(p[rows_v][pk]); aus.append((rr[yy == 1].sum() - yy.sum() * (yy.sum() + 1) / 2) / (yy.sum() * (len(yy) - yy.sum())))
        ic = float(np.percentile(aus, 5)); cutm = np.nanpercentile(sc_, 90); alarm = sc_ >= cutm; lift = float(y_[alarm].mean() / y_.mean())
        out[k] = dict(auc=float(obs), ic90=ic, lift=lift, p=float(pv), p_corr=float(min(1, pv * NMOD / 3)), passa=bool(obs >= 0.60 and ic > 0.5 and lift >= 1.25 and min(1, pv * NMOD / 3) < 0.05))
    best = sorted(out.items(), key=lambda kv: -kv[1]["auc"])[:6]; LOG(f"[{tg}] modelli valutati {len(out)}; passano {sum(v['passa'] for v in out.values())}; migliori:", [(k, round(v['auc'], 3), round(v['lift'], 2), round(v['p_corr'], 2)) for k, v in best])
    RES[tg]["modelli"] = out
    np.save(f"/tmp/pred_{tg}.npy", {k: v for k, v in PRED.items()} , allow_pickle=True)
json.dump(RES, open("scratch/ricerca_10000_esito.json", "w"), indent=1, default=float)
LOG("TOTALE tentativi: segnali", M, "+ modelli", NMOD, "=", M + NMOD)
