"""Segue PROTOCOLLO_MULTIMERCATO.md."""
import sys, pickle, json, itertools
from r200k_lib import *
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
NPAIR = int(sys.argv[1]) if len(sys.argv) > 1 else 33000; NENS = int(sys.argv[2]) if len(sys.argv) > 2 else 30000
KEYS = ["sp500", "f_nikkei225", "dax", "x_ftse", "x_fchi", "x_hsi", "x_gsptse", "x_ibex", "x_ssmi", "x_aex", "x_bfx", "x_atx", "x_axjo", "x_bvsp", "x_mxx", "x_ks11", "x_twii", "x_sti", "x_jkse", "x_bsesn", "x_000001_ss", "x_ta125_ta", "ftsemib"]
MK = {}
for k in KEYS:
    try:
        s = store.load(k).dropna(); s = s[~s.index.duplicated()]; s = s[s > 0]
        if k == "sp500": s = s[s.index >= "1928-01-01"]
        if len(s) >= 5000: MK[k] = s
        else: LOG("scartato", k, len(s))
    except Exception as e: LOG("assente", k, e)
names_m = list(MK); LOG("mercati:", len(names_m), names_m)
WIN = (5, 10, 20, 40, 60, 120, 252)
def feats(C):
    lx = np.log(C); dl = lx.diff(); F = {}; neg2 = np.minimum(dl, 0) ** 2; pos2 = np.maximum(dl, 0) ** 2; ST = {}
    for w in WIN:
        R_ = dl.rolling(w); ST[("dev", w)] = R_.std(); ST[("devgiu", w)] = np.sqrt(neg2.rolling(w).mean()); ST[("devsu", w)] = np.sqrt(pos2.rolling(w).mean()); ST[("rapp", w)] = ST[("devgiu", w)] / ST[("devsu", w)]
        ST[("asim", w)] = R_.skew(); ST[("curt", w)] = R_.kurt(); ST[("max", w)] = R_.max(); ST[("min", w)] = R_.min(); ST[("sommaabs", w)] = dl.abs().rolling(w).sum(); ST[("quotasu", w)] = (dl > 0).rolling(w).mean()
        ST[("dmax", w)] = lx - lx.rolling(w).max(); ST[("dmin", w)] = lx - lx.rolling(w).min(); ST[("dmedia", w)] = lx - lx.rolling(w).mean(); ST[("rend", w)] = lx.diff(w); ST[("range", w)] = lx.rolling(w).max() - lx.rolling(w).min()
        ST[("nuovimax", w)] = (C == C.rolling(w).max()).rolling(w).sum(); ST[("ac1", w)] = dl.rolling(w).corr(dl.shift(1))
        t = np.arange(w, dtype=float); p1 = t - t.mean(); p2 = t ** 2; p2 = p2 - p2.mean(); p2 = p2 - p1 * (p2 @ p1) / (p1 @ p1); xv = lx.to_numpy()
        rd = lambda p: pd.Series(np.concatenate([np.full(w - 1, np.nan), np.convolve(xv, p[::-1], mode="valid")]), index=C.index)
        b1 = rd(p1) / (p1 @ p1); b2 = rd(p2) / (p2 @ p2); sst = (lx ** 2).rolling(w).sum() - lx.rolling(w).sum() ** 2 / w
        ST[("pend", w)] = b1; ST[("curv", w)] = b2; ST[("r2", w)] = (b1 ** 2 * (p1 @ p1)) / sst
    for lam in (0.9, 0.94, 0.97): ST[(f"ewma{lam}", 0)] = np.sqrt((dl ** 2).ewm(alpha=1 - lam).mean())
    rv1 = dl.abs(); rv5 = np.sqrt((dl ** 2).rolling(5).mean()); rv22 = np.sqrt((dl ** 2).rolling(22).mean()); ST[("har", 0)] = 0.3 * rv1 + 0.4 * rv5 + 0.3 * rv22
    bv = (np.pi / 2) * (dl.abs() * dl.abs().shift(1)); rvw = (dl ** 2).rolling(20).sum(); ST[("salto20", 0)] = ((rvw - bv.rolling(20).sum()).clip(lower=0)) / rvw
    for (a, w), x in ST.items():
        x = x.replace([np.inf, -np.inf], np.nan); n = f"{a}{w}"; F[f"{n}|raw"] = x; F[f"{n}|lag5"] = x.shift(5); F[f"{n}|z252"] = (x - x.rolling(252).mean()) / x.rolling(252).std(); F[f"{n}|diff20"] = x.diff(20)
        m = x.rolling(252).mean(); F[f"{n}|rapp252"] = x / m.where(m.abs() > 1e-12) - 1
    for a in ("dev", "devgiu", "rend", "pend", "dmax", "quotasu", "range", "sommaabs"):
        for wa, wb in itertools.combinations(WIN, 2):
            xa, xb = ST[(a, wa)], ST[(a, wb)]; F[f"rel_{a}_{wa}_su_{wb}"] = xa / xb.where(xb.abs() > 1e-12); F[f"rel_{a}_{wa}_meno_{wb}"] = xa - xb
    return F, dl
ROWS = []; XL = []; FN = None
for mi, (k, C) in enumerate(MK.items()):
    F, dl = feats(C); FN = FN or list(F); vol60 = dl.rolling(60).std(); calm = vol60 <= vol60.expanding(500).median()
    lxv = np.log(C).to_numpy(); Cn = C.to_numpy(float); n = len(Cn)
    def fm(kk):
        m = pd.Series(Cn[::-1]).rolling(kk).min().to_numpy()[::-1]; o = np.full(n, np.nan); o[:-1] = m[1:] / Cn[:-1] - 1; return o
    f20, f40 = fm(20), fm(40); ok_ = calm.to_numpy() & np.isfinite(vol60.to_numpy()) & (np.arange(n) >= 1008)
    if k == "sp500":
        from classifica_40anni import ESTERNI, MISTE_MAX
        ext = np.zeros(n, bool)
        for d in list(ESTERNI) + list(MISTE_MAX) + PRE90_EXT: p = C.index.searchsorted(pd.Timestamp(d)); ext[max(0, p - 5):min(n, p + 61)] = True
        ext[(C.index >= "1939-09-01") & (C.index <= "1945-09-02")] = True; ok_ &= ~ext
    Z = np.column_stack([((F[f] - F[f].expanding(500).mean()) / F[f].expanding(500).std()).clip(-5, 5).to_numpy(np.float32) for f in FN])
    idx = np.where(ok_ & np.isfinite(f20))[0]
    ROWS.append(pd.DataFrame(dict(m=mi, date=C.index[idx], y1=(f20[idx] <= -0.05).astype(float), y2=np.where(np.isfinite(f40[idx]), (f40[idx] <= -0.08).astype(float), np.nan))))
    XL.append(Z[idx]); LOG("  ", k, "giorni calmi usabili", len(idx))
META = pd.concat(ROWS, ignore_index=True); X = np.vstack(XL).astype(np.float32); del XL; yrs = META.date.dt.year.to_numpy(); mkt = META.m.to_numpy()
grp_sel = (mkt % 2 == 0); PER = {"sel": grp_sel & (yrs <= 2007), "v1": grp_sel & (yrs >= 2008), "v2": ~grp_sel}
LOG("righe", len(META), "segnali singoli", len(FN), {p: int(v.sum()) for p, v in PER.items()})
rg = np.random.default_rng(31); TG = {"T1": META.y1.to_numpy(), "T2": META.y2.to_numpy()}
def blocks(rows): return [np.where(mkt[rows] == m)[0] for m in np.unique(mkt[rows])]
def shifted(y, rows, nsh, rg):
    bl = blocks(rows); out = np.empty((nsh, len(rows)), np.float32)
    for s in range(nsh):
        for b in bl: n = len(b); out[s, b] = y[np.roll(np.arange(n), int(rg.integers(max(20, n // 10), n - max(20, n // 10))))] if n > 60 else y[b]
    return out
def auc_r(Rk, y): n1 = y.sum(); return (y.astype(np.float32) @ Rk - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))
SELR = {}; YSH = {}; NULL = {}
for tg in TG:
    ok = np.isfinite(TG[tg]); SELR[tg] = {p: np.where(PER[p] & ok)[0] for p in PER}; ysel = TG[tg][SELR[tg]["sel"]]
    sub = ysel; bl = blocks(SELR[tg]["sel"]); YSH[tg] = np.empty((NSH, len(sub)), np.float32)
    for s in range(NSH):
        for b in bl: n = len(b); YSH[tg][s, b] = sub[b][np.roll(np.arange(n), int(rg.integers(n // 10, n - n // 10)))]
    NULL[tg] = np.full(NSH, -np.inf)
STAT = {tg: {k: [] for k in ("sel", "v1", "v2")} for tg in TG}; NAMES = []; TOP = {tg: [] for tg in TG}
def evaluate(Xc, nms):
    NAMES.extend(nms)
    for tg in TG:
        y = TG[tg]; rs = SELR[tg]; Xs = Xc[rs["sel"]]; nanf = np.isnan(Xs).mean(0); med = np.nanmedian(Xs, axis=0); med = np.where(np.isnan(med), 0, med); Zs = np.where(np.isnan(Xs), med, Xs)
        ys = y[rs["sel"]]; Rk = rankdata(Zs, axis=0).astype(np.float32); a = auc_r(Rk, ys); a[nanf > 0.2] = np.nan; ori = np.where(a >= 0.5, 1.0, -1.0); st = np.maximum(a, 1 - a)
        nl = (YSH[tg] @ Rk - ys.sum() * (ys.sum() + 1) / 2) / (ys.sum() * (len(ys) - ys.sum())); nl = np.maximum(nl, 1 - nl); nl[:, nanf > 0.2] = -np.inf; NULL[tg] = np.maximum(NULL[tg], nl.max(1))
        STAT[tg]["sel"].append(st.astype(np.float32))
        for p in ("v1", "v2"):
            Xp = Xc[rs[p]]; mp = np.nanmedian(Xp, axis=0); mp = np.where(np.isnan(mp), 0, mp); Zp = np.where(np.isnan(Xp), mp, Xp); yy = y[rs[p]]; ap = auc_r(rankdata(Zp, axis=0).astype(np.float32), yy)
            STAT[tg][p].append(np.where(ori > 0, ap, 1 - ap).astype(np.float32))
        v = np.where(np.isfinite(st))[0]
        for j in v[np.argsort(-st[v])[:300]]: TOP[tg].append((float(st[j]), nms[j], Xc[:, j].copy(), float(ori[j])))
        TOP[tg] = sorted(TOP[tg], key=lambda t: -t[0])[:300]
def chunks(gen, total, size=2500):
    for i0 in range(0, total, size):
        Xc, nm = gen(i0, min(total, i0 + size)); evaluate(Xc, nm); LOG(f"  valutati {min(total, i0 + size)}/{total}")
chunks(lambda i, j: (X[:, i:j], FN[i:j]), len(FN))
pi = rg.integers(0, len(FN), NPAIR); pj = rg.integers(0, len(FN), NPAIR); kk = pi != pj; pi, pj = pi[kk], pj[kk]; total = len(pi) * 3
def gp(i0, i1):
    cols = []; nm = []
    for t in range(i0, i1):
        q, op = divmod(t, 3); a, b = X[:, pi[q]], X[:, pj[q]]; cols.append(a + b if op == 0 else (a - b if op == 1 else a * b)); nm.append(f"coppia|{FN[pi[q]]}|{FN[pj[q]]}|{('somma', 'diff', 'prod')[op]}")
    return np.column_stack(cols).astype(np.float32), nm
chunks(gp, total, 600)
LOG("TOTALE segnali fase 1:", len(NAMES))
RES = {"n_fase1": len(NAMES), "mercati": names_m, "righe": len(META)}
for tg in TG:
    st = {k: np.concatenate(v) for k, v in STAT[tg].items()}; sog = float(np.percentile(NULL[tg], 95)); sel = st["sel"]; ok = np.isfinite(sel); o = np.argsort(-np.where(ok, sel, -1))[:100]
    pas = ok & (sel > sog) & (sel >= 0.58); rob = ok & (sel >= 0.58) & (st["v1"] >= 0.56) & (st["v2"] >= 0.56)
    RES[tg] = dict(soglia=sog, miglior=float(np.nanmax(sel)), passano_sel=int(pas.sum()), robusti_descrittivi=int(rob.sum()), top100_v1=float(np.nanmean(st["v1"][o])), top100_v2=float(np.nanmean(st["v2"][o])), top100_v2_med=float(np.nanmedian(st["v2"][o])),
                   migliori=[dict(nome=NAMES[j][:100], sel=float(sel[j]), v1=float(st["v1"][j]), v2=float(st["v2"][j])) for j in np.argsort(-np.where(ok & np.isfinite(st["v2"]), np.minimum(st["v1"], st["v2"]), -1))[:4]])
    LOG(tg, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in RES[tg].items() if k != "migliori"}); [LOG("    ", m) for m in RES[tg]["migliori"][:3]]
pickle.dump(dict(RES=RES, TOP=TOP, TG=TG, SELR=SELR, mkt=mkt, yrs=yrs), open('/tmp/mm_ck.pkl','wb')); json.dump(RES, open('scratch/mm_esito_fase1.json','w'), indent=1, default=float); LOG('checkpoint salvato')
# fase 2 + p-value
def pshift(score, y, rows, nsh=10000):
    ok = np.isfinite(score); rk = rankdata(score).astype(np.float32); n1 = y.sum(); obs = (rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)); ge = 0
    for c0 in range(0, nsh, 1000):
        ys = shifted(y, rows, 1000, rg); ge += int(((ys @ rk - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)) >= obs).sum())
    return float(obs), (1 + ge) / (nsh + 1)
for tg in TG:
    cand = TOP[tg][:40]; K = len(cand); U = np.column_stack([np.nan_to_num(c[2], nan=0) * c[3] for c in cand]).astype(np.float32); y = TG[tg]; rs = SELR[tg]; ys = y[rs["sel"]]
    W = np.zeros((K, NENS), np.float32)
    for m in range(NENS): k_ = int(rg.integers(2, 13)); s_ = rg.choice(K, k_, replace=False); W[s_, m] = rg.dirichlet(np.ones(k_))
    a_sel = np.empty(NENS, np.float32)
    for c0 in range(0, NENS, 1000):
        Sc = U[rs["sel"]] @ W[:, c0:c0 + 1000]; a_sel[c0:c0 + 1000] = auc_r(rankdata(Sc, axis=0).astype(np.float32), ys)
    top = np.argsort(-a_sel)[:10]; res = []
    for j in top:
        sc = U @ W[:, j]; r_ = dict(sel=float(a_sel[j]))
        for p in ("v1", "v2"):
            rr = rs[p]; obs, pv = pshift(sc[rr], y[rr], rr); r_[p] = dict(auc=obs, p_corr=min(1.0, pv * 10))
        r_["confermato"] = bool(all(r_[p]["auc"] >= 0.56 and r_[p]["p_corr"] < 0.05 for p in ("v1", "v2"))); res.append(r_)
    RES[tg]["fase2"] = res; RES[tg]["n_fase2"] = NENS
    LOG(f"[{tg}] fase 2: {NENS} insiemi; confermati {sum(r['confermato'] for r in res)}/10; migliori:", [(round(r['sel'], 3), round(r['v1']['auc'], 3), round(r['v2']['auc'], 3), round(r['v2']['p_corr'], 3)) for r in res[:4]])
ALG = {"logL2_001": lambda: LogisticRegression(C=0.01, max_iter=200), "logL2_01": lambda: LogisticRegression(C=0.1, max_iter=200), "logL1": lambda: LogisticRegression(C=0.05, penalty="l1", solver="liblinear"), "lda": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
       "nb": lambda: GaussianNB(), "knn50": lambda: KNeighborsClassifier(50), "rf": lambda: RandomForestClassifier(100, max_depth=5, min_samples_leaf=20, n_jobs=2, random_state=0), "et": lambda: ExtraTreesClassifier(100, max_depth=6, min_samples_leaf=20, n_jobs=2, random_state=0),
       "hgb2": lambda: HistGradientBoostingClassifier(max_depth=2, max_iter=100, learning_rate=0.05, random_state=0), "hgb3": lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, random_state=0), "hgb4": lambda: HistGradientBoostingClassifier(max_depth=4, max_iter=100, learning_rate=0.05, random_state=0)}
NM = len(ALG) * 3 * 2
for tg in TG:
    cand = TOP[tg][:300]; Z = np.column_stack([np.nan_to_num(c[2], nan=0) * c[3] for c in cand]).astype(np.float32); y = TG[tg]; rs = SELR[tg]; trn = rs["sel"][::3]; out = {}
    for K in (30, 100, 300):
        for a, mk in ALG.items():
            try: m = mk().fit(Z[trn][:, :K], y[trn])
            except Exception: continue
            r_ = {}
            for p in ("v1", "v2"):
                rr = rs[p]; sc = m.predict_proba(Z[rr][:, :K])[:, 1]; obs, pv = pshift(sc, y[rr], rr, 3000); r_[p] = dict(auc=obs, p_corr=min(1.0, pv * NM / 2))
            r_["passa"] = bool(all(r_[p]["auc"] >= 0.56 and r_[p]["p_corr"] < 0.05 for p in ("v1", "v2"))); out[f"{a}_{K}"] = r_
    RES[tg]["modelli"] = out; b = sorted(out.items(), key=lambda kv: -min(kv[1]["v1"]["auc"], kv[1]["v2"]["auc"]))[:4]
    LOG(f"[{tg}] modelli {len(out)}; passano {sum(v['passa'] for v in out.values())}; migliori:", [(k, round(v['v1']['auc'], 3), round(v['v2']['auc'], 3), round(v['v2']['p_corr'], 2)) for k, v in b])
RES["totale"] = len(NAMES) + 2 * NENS + NM
json.dump(RES, open("scratch/mm_esito.json", "w"), indent=1, default=float); LOG("TOTALE tentativi:", RES["totale"])
