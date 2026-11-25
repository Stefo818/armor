"""Segue PROTOCOLLO_ANTICIPO_CROLLI.md (scritto prima dei calcoli)."""
import json, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from armor import store, grafico_indici as g
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]
cal = sp.index[sp.index >= "1990-01-01"]; N = len(cal)
def R(k, lag=0):
    s = store.load(k).dropna(); s = s[~s.index.duplicated()]
    s = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    return s.shift(lag) if lag else s
C = sp.reindex(cal); O, H, L, V = R("sp_open"), R("sp_high"), R("sp_low"), R("sp_vol")
r = C.pct_change(); a = sp.to_numpy()
# ---- episodi: correzioni endogene (PROTOCOLLO_ANTICIPO_CORREZIONI.md)
sys.path.insert(0, "scratch")
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX
Cn = C.to_numpy(); allp = []
for p in range(20, N - 120):
    if Cn[p] == Cn[p - 20:p + 21].max() and Cn[p + 1:p + 121].min() / Cn[p] - 1 <= -0.05: allp.append(p)
posd = lambda d: cal.searchsorted(pd.Timestamp(d))
ext_pos = [posd(d) for d in ESTERNI]; mix_pos = [posd(d) for d in MISTE_MAX]; cls_ext = [posd(m) for m, _, nat, _ in CLASSIFICA if nat == "esterna" and pd.Timestamp(m) >= cal[0]]
def esterno(p):
    return any(p - 5 <= e <= p + 60 for e in ext_pos) or any(abs(p - e) < 5 for e in cls_ext + mix_pos)
T0 = np.array([p for p in allp if not esterno(p)]); D = np.array([Cn[p + 1:p + 121].min() / Cn[p] - 1 for p in T0])
fascia = np.where(D > -0.10, "moderata", np.where(D > -0.20, "forte", "grave"))
print("correzioni totali", len(allp), "endogene", len(T0), {f: int((fascia == f).sum()) for f in ("moderata", "forte", "grave")})
yr = np.array([cal[i].year for i in T0]); SEL = yr <= 2007; VER = ~SEL; print("selezione", int(SEL.sum()), "verifica", int(VER.sum()))
W = {"W": (10, 2), "W2": (3, 2), "W5": (6, 4), "W10": (10, 7)}
def win(t, k):
    a_, b_ = W[k]; return np.arange(max(0, t - a_), min(N - 1, t - b_) + 1)
W["E"] = (-1, -5)
zona = np.zeros(N, bool)
for p in allp: zona[max(0, p - 40):min(N, p + 11)] = True
for e in ext_pos + mix_pos: zona[max(0, e - 5):min(N, e + 61)] = True
base = (~zona) & (np.arange(N) >= 500 + 252); print("giorni di base", int(base.sum()))
# ---- ipotesi
F = {}
def add(n, x, d): F[n] = (x, d)
mx = lambda s, n: s.rolling(n).max(); mn = lambda s, n: s.rolling(n).min()
dd252 = C / mx(C, 252) - 1; dd60 = C / mx(C, 60) - 1
for th in (0.01, 0.005):
    for n in (10, 20): add(f"vicino_max252_{th}_{n}", (dd252 >= -th).rolling(n).sum(), 1)
for n in (10, 20): add(f"vicino_max60_0.005_{n}", (dd60 >= -0.005).rolling(n).sum(), 1)
prev60 = H.shift(1).rolling(60).max(); add("rotture_fallite_20", ((H > prev60) & (C < prev60)).rolling(20).sum(), 1)
s_ = (C == mx(C, 252)).astype(int); gg = s_.cumsum(); add("sedute_dal_max252", gg.groupby(gg).cumcount().astype(float), 1)
add("distanza_max252_vicino", dd252, 1)
rng = (H - L) / C; add("ampiezza_5_60", rng.rolling(5).mean() / rng.rolling(60).mean(), 1); add("ampiezza_20_60_bassa", rng.rolling(20).mean() / rng.rolling(60).mean(), -1)
rv = lambda n: r.rolling(n).std()
for n in (5, 10, 20): add(f"vol_{n}_alta", rv(n), 1); add(f"vol_{n}_bassa", rv(n), -1)
add("vol_10_60", rv(10) / rv(60), 1)
dv = (r.where(r < 0, 0) ** 2).rolling(20).mean() ** .5; uv = (r.where(r > 0, 0) ** 2).rolling(20).mean() ** .5; add("vol_discesa_salita", dv / uv, 1)
up20 = (r > 0).rolling(20).mean(); add("giorni_rialzo_alta", up20, 1); add("giorni_rialzo_bassa", up20, -1)
for n in (3, 5, 10, 20, 60): add(f"rend_{n}_alto", C.pct_change(n), 1); add(f"rend_{n}_basso", C.pct_change(n), -1)
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean(); add("dist_media50", C / ma50 - 1, 1); add("dist_media200", C / ma200 - 1, 1); add("pendenza_media50_bassa", ma50 / ma50.shift(10) - 1, -1)
add("peggior_giorno_5", r.rolling(5).min(), -1); add("peggior_giorno_10", r.rolling(10).min(), -1)
for n in (5, 10): add(f"giorni_sotto_1pct_{n}", (r < -0.01).rolling(n).sum(), 1)
add("gap_ribasso_10", (O / C.shift(1) - 1 < -0.003).rolling(10).sum(), 1)
add("chiusura_nel_range_bassa", ((C - L) / (H - L)).rolling(5).mean(), -1)
add("ombra_superiore_10", ((H - np.maximum(O, C)) / (H - L)).rolling(10).mean(), 1)
vr = V.rolling(5).mean() / V.rolling(60).mean(); add("volume_5_60_alto", vr, 1); add("volume_5_60_basso", vr, -1)
add("volume_giorni_calo_rialzo", (V * (r < 0)).rolling(20).sum() / (V * (r > 0)).rolling(20).sum(), 1)
add("asimmetria_20_bassa", r.rolling(20).skew(), -1); add("curtosi_60", r.rolling(60).kurt(), 1)
ac = r.rolling(20).corr(r.shift(1)); add("autocorr_alta", ac, 1); add("autocorr_bassa", ac, -1)
add("nuovi_minimi_20_in_10", (C == mn(C, 20)).rolling(10).sum(), 1)
add("massimi_decrescenti", H.rolling(10).max() / H.shift(10).rolling(20).max(), -1)
add("rend60_su_vol60", C.pct_change(60) / rv(60), 1)
# paura
vix = R("vix"); sk = R("skew"); drv = vix.pct_change()
add("vix_alto", vix, 1); add("vix_basso", vix, -1); add("vix_var5", vix - vix.shift(5), 1); add("vix_su_media60", vix / vix.rolling(60).mean(), 1)
add("vix_su_vol_realizzata_alto", vix / (rv(20) * np.sqrt(252) * 100), 1); add("vix_su_vol_realizzata_basso", vix / (rv(20) * np.sqrt(252) * 100), -1)
add("corr_vix_borsa_positiva", drv.rolling(20).corr(r), 1); add("giorni_vix_su_borsa_su", ((drv > 0) & (r > 0)).rolling(10).sum(), 1)
add("skew_alto", sk, 1); add("skew_var10", sk - sk.shift(10), 1); add("vix_max10_su_media60", vix.rolling(10).max() / vix.rolling(60).mean(), 1)
add("borsa_vicino_max_x_vix_var5", (vix - vix.shift(5)).where(dd252 >= -0.02, 0), 1)
# credito e tassi
b = R("baa10y", 1); add("baa_liv", b, 1); add("baa_var5", b - b.shift(5), 1); add("baa_var20", b - b.shift(20), 1)
for k in ("hy_fondo", "ig_fondo"):
    x = R(k, 1); add(f"{k}_var5", x - x.shift(5), 1); add(f"{k}_var20", x - x.shift(20), 1)
ci = R("ciss", 1); add("ciss_liv", ci, 1); add("ciss_var5", ci - ci.shift(5), 1)
cv = R("t10y3m", 1); add("curva_bassa", cv, -1); add("curva_var20_bassa", cv - cv.shift(20), -1)
d10 = R("dgs10", 1); add("tasso10_scossa5", (d10 - d10.shift(5)).abs(), 1); add("tasso10_var20", d10 - d10.shift(20), 1)
d2 = R("dgs2", 1); add("tasso2_var20", d2 - d2.shift(20), 1)
dx = R("dxy", 1); add("dollaro_var5", dx.pct_change(5), 1); add("dollaro_var20", dx.pct_change(20), 1)
jp = R("jpy", 1); add("yen_scossa5", jp.pct_change(5).abs(), 1)
# altri mercati
nd = R("nasdaq100"); ru = R("rut"); mi = R("cn_mid"); oe = R("cn_oex"); dax = R("dax"); nk = R("nikkei")
for nm, x, d in (("nasdaq_su_sp", nd, 1), ("nasdaq_su_sp_basso", nd, -1), ("piccole_su_sp_alto", ru, 1), ("piccole_su_sp_basso", ru, -1)):
    add(nm + "_var20", (x / C).pct_change(20), d)
add("medie_su_sp_basso_var20", (mi / C).pct_change(20), -1); add("sp100_su_sp_var20", (oe / C).pct_change(20), 1)
add("dax_meno_sp_5", dax.pct_change(5) - C.pct_change(5), -1); add("nikkei_meno_sp_5", nk.pct_change(5) - C.pct_change(5), -1)
add("dax_20_basso", dax.pct_change(20), -1); add("nikkei_20_basso", nk.pct_change(20), -1)
sec = {k: R("sec_" + k) for k in ("xlb", "xle", "xlf", "xli", "xlk", "xlp", "xlu", "xlv", "xly")}
lg = {k: np.log(v) for k, v in sec.items()}
d_ = (lg["xlp"] + lg["xlu"] + lg["xlv"]) / 3 - (lg["xly"] + lg["xlk"] + lg["xli"]) / 3; add("difensivi_su_ciclici_var20", d_ - d_.shift(20), 1)
add("finanza_su_sp_var20_bassa", (lg["xlf"] - np.log(C)).diff(20), -1)
add("tecnologia_su_sp_alto", (lg["xlk"] - np.log(C)).diff(20), 1); add("tecnologia_su_sp_basso", (lg["xlk"] - np.log(C)).diff(20), -1)
add("voluttuari_su_base_basso", (lg["xly"] - lg["xlp"]).diff(20), -1); add("utility_su_sp_alto", (lg["xlu"] - np.log(C)).diff(20), 1)
Sd = pd.DataFrame(sec); rs = Sd.pct_change()
add("settori_sotto_media50", (Sd < Sd.rolling(50).mean()).mean(axis=1).where(Sd.notna().all(axis=1)), 1)
add("dispersione_settori_5", Sd.pct_change(5).std(axis=1), 1)
ew = rs.mean(axis=1); mv = (rs ** 2).rolling(20).mean().mean(axis=1)
add("correlazione_settori_20", (ew.rolling(20).var() - mv / 9) / (mv * (1 - 1 / 9)), 1)
add("settori_ai_massimi60_pochi", (Sd == Sd.rolling(60).max()).sum(axis=1).where(Sd.notna().all(axis=1)), -1)
# calendario
add("mesi_ago_ott", pd.Series(cal.month.isin([8, 9, 10]).astype(float), index=cal), 1)
tw = pd.Series(0.0, index=cal)
for y in range(1990, 2027):
    for m in (3, 6, 9, 12):
        f = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D"); f = f[(f.month == m) & (f.weekday == 4)]
        if len(f) >= 3:
            d0 = f[2]; tw[(cal >= d0 - pd.Timedelta(days=4)) & (cal <= d0)] = 1.0
add("settimana_scadenza_trimestrale", tw, 1)
# ---- nuove ipotesi N01-N18 (correzioni lente)
add("N01_stallo_max40", (C >= mx(C, 40) * 0.995).rolling(40).sum(), 1)
add("N02_ampiezza40_bassa", (mx(C, 40) - mn(C, 40)) / C, -1)
add("N03_vicino_max20", C / mx(C, 20) - 1, 1)
add("N04_rend120", C.pct_change(120), 1)
add("N05_settori_sotto_media200", (Sd < Sd.rolling(200).mean()).mean(axis=1).where(Sd.notna().all(axis=1) & Sd.rolling(200).mean().notna().all(axis=1)), 1)
add("N06_divergenza_settori", (Sd < Sd.rolling(50).mean()).mean(axis=1).where(dd252 >= -0.02, 0).where(Sd.notna().all(axis=1)), 1)
add("N07_volume_rialzi_20_60_basso", (V * (r > 0)).rolling(20).mean() / (V * (r > 0)).rolling(60).mean(), -1)
add("N08_vix_su_min20", vix / vix.rolling(20).min(), 1); add("N09_vix_var20", vix - vix.shift(20), 1)
add("N10_baa_var60", b - b.shift(60), 1); add("N11_curva_var60_bassa", cv - cv.shift(60), -1)
add("N12_tasso10_var60", d10 - d10.shift(60), 1); add("N13_dollaro_var60", dx.pct_change(60), 1)
add("N14_vol60_su_252", rv(60) / rv(252), 1); add("N15_giorni_sopra_1pct_20", (r > 0.01).rolling(20).sum(), 1)
add("N16_dist_media20", C / C.rolling(20).mean() - 1, 1)
add("N17_nasdaq_meno_sp_20_basso", nd.pct_change(20) - C.pct_change(20), -1)
add("N18_grandi_meno_piccole_60", C.pct_change(60) - ru.pct_change(60), 1)
names = list(F); print("N ipotesi:", len(names))
# ---- percentili espansi (direzione applicata)
P = pd.DataFrame({n: (x * d).replace([np.inf, -np.inf], np.nan).expanding(500).rank(pct=True) for n, (x, d) in F.items()})
PV = P.to_numpy(); ok0 = np.isfinite(PV)
def auc_ep(col, t):
    w = win(t, "W"); v = PV[w, col]; v = v[np.isfinite(v)]
    if len(v) == 0: return np.nan
    B = np.sort(PV[:, col][base & ok0[:, col]]);
    if len(B) < 200: return np.nan
    return float(((np.searchsorted(B, v, "left") + np.searchsorted(B, v, "right")) / 2 / len(B)).mean())
BS = [np.sort(PV[:, j][base & ok0[:, j]]) for j in range(len(names))]
def auc_win(j, t, k):
    w = win(t, k); v = PV[w, j]; v = v[np.isfinite(v)]; B = BS[j]
    if len(v) == 0 or len(B) < 200: return np.nan
    return float(((np.searchsorted(B, v, "left") + np.searchsorted(B, v, "right")) / 2 / len(B)).mean())
def auc_set(j, T, k="W"):
    x = [auc_win(j, t, k) for t in T]; x = [e for e in x if np.isfinite(e)]; return (float(np.mean(x)) if x else np.nan, len(x))
res = {}
for j, n in enumerate(names):
    s, ns = auc_set(j, T0[SEL]); v, nv = auc_set(j, T0[VER]); al, _ = auc_set(j, T0)
    esc = ~np.isin(yr, [2001, 2020]); ax, _ = auc_set(j, T0[esc])
    w2, _ = auc_set(j, T0[VER], "W2")
    fa = {f: auc_set(j, T0[fascia == f])[0] for f in ('moderata', 'forte', 'grave')}; ae, _ = auc_set(j, T0, 'E')
    # anticipo
    lead, hit = [], 0
    for t in T0:
        seg = np.arange(max(0, t - 20), t - 1); v_ = PV[seg, j]; f_ = np.where(v_ >= 0.9)[0]
        if len(f_): hit += 1; lead.append(int(t - seg[f_[0]]))
    # intervallo al 90% (episodi di verifica)
    eps = [auc_win(j, t, "W") for t in T0[VER]]; eps = np.array([e for e in eps if np.isfinite(e)])
    rng_ = np.random.default_rng(7); bs = [rng_.choice(eps, len(eps)).mean() for _ in range(2000)] if len(eps) else [np.nan]
    res[n] = dict(fasce=fa, E=ae, sel=s, n_sel=ns, ver=v, n_ver=nv, tutti=al, senza_2001_2020=ax, ver_W2=w2, ic90_basso=float(np.percentile(bs, 5)), episodi_con_segnale=hit, anticipo_mediano=(float(np.median(lead)) if lead else None), dir=F[n][1])
# ---- soglia migliore fra N
rng = np.random.default_rng(2611); mx_ = []
for _ in range(300):
    off = int(rng.integers(250, N - 250)); Ts = (T0 + off) % N; Ts = Ts[SEL]
    best = -1
    for j in range(len(names)):
        x = [auc_win(j, t, "W") for t in Ts if t >= 10]; x = [e for e in x if np.isfinite(e)]
        if x: best = max(best, float(np.mean(x)))
    mx_.append(best)
soglia = float(np.percentile(mx_, 95)); print("soglia caso (95° pct dei massimi):", round(soglia, 3), " mediana", round(float(np.median(mx_)), 3))
for n, q in res.items():
    q["passa_selezione"] = bool(q["sel"] >= 0.60 and q["sel"] > soglia) if np.isfinite(q["sel"]) else False
    q["passa_verifica"] = bool(q["passa_selezione"] and q["ver"] >= 0.56 and q["ic90_basso"] > 0.5 and q["ver_W2"] > 0.5)
tab = pd.DataFrame(res).T.sort_values("sel", ascending=False)
pd.set_option("display.width", 250)
print(tab.head(25)[["dir", "sel", "ver", "tutti", "senza_2001_2020", "ver_W2", "ic90_basso", "episodi_con_segnale", "anticipo_mediano", "E", "passa_selezione", "passa_verifica"]].round(3).to_string())
print("passano selezione:", [n for n, q in res.items() if q["passa_selezione"]]); print("passano verifica:", [n for n, q in res.items() if q["passa_verifica"]])
print("migliori per verifica (info):", tab.sort_values("ver", ascending=False).head(8)[["sel", "ver"]].round(3).to_dict("index"))
# ---- Parte 1: indici
d = g.dati()
def serie(k):
    r_ = d[k]; t_ = pd.to_datetime(pd.Series(r_["dt"]).cumsum() + r_["t0"], unit="D"); s = pd.Series([x / 10 for x in r_["v"]], index=t_.values); return s[~s.index.duplicated()].reindex(cal, method="ffill", tolerance=pd.Timedelta(days=5))
p1 = {}
for k in ("crollo", "armor", "minimi", "super", "stato"):
    s = serie(k); sv = s.to_numpy(); pe = pd.Series(sv).expanding(500).rank(pct=True).to_numpy(); Bk = np.sort(pe[base & np.isfinite(pe)])
    au = {}
    for fa in ("moderata", "forte", "grave", "tutte"):
        T_ = T0 if fa == "tutte" else T0[fascia == fa]; x = []
        for t_ in T_:
            v = pe[win(t_, "W")]; v = v[np.isfinite(v)]
            if len(v): x.append(float(((np.searchsorted(Bk, v, "left") + np.searchsorted(Bk, v, "right")) / 2 / len(Bk)).mean()))
        au[fa] = (round(float(np.mean(x)), 3), len(x)) if x else None
    vals = {}
    for fa in ("moderata", "forte", "grave"):
        T_ = T0[fascia == fa]; vals[fa] = {f"p-{q}": round(float(np.nanmean([sv[t_ - q] for t_ in T_])), 1) for q in (2, 5, 10)}
    sop = {}
    for th in (50, 60):
        l_ = []
        for t_ in T0:
            seg = sv[max(0, t_ - 60):t_ - 1]; idx = np.where(seg >= th)[0]; l_.append(int(t_ - (max(0, t_ - 60) + idx[0])) if len(idx) else None)
        ok_ = [x for x in l_ if x is not None]; sop[th] = (len(ok_), float(np.median(ok_)) if ok_ else None)
    p1[k] = dict(base=float(np.nanmean(sv[base])), auc=au, valori=vals, sopra=sop)
    print(k, "base", round(p1[k]["base"], 1), "AUC", au, "valori", vals, "sopra(n,mediana sedute)", sop)
json.dump(dict(n_endogene=int(len(T0)), fasce={f: int((fascia == f).sum()) for f in ("moderata", "forte", "grave")}, soglia=soglia, n=len(names), ipotesi=res, parte1=p1), open("scratch/anticipo_correzioni_esito.json", "w"), indent=1, default=float)
print("--- ipotesi dell'utente / struttura ---")
for n in names:
    if any(x in n for x in ("vicino_max","rotture","sedute_dal","N01","N02","N06","N07","N17","N18","massimi_decr")):
        q=res[n]; print(f"{n:32s} sel {q['sel']:.2f} ver {q['ver']:.2f} tutti {q['tutti']:.2f} segnali {q['episodi_con_segnale']}/{len(T0)} anticipo {q['anticipo_mediano']} E {q['E']:.2f}")
both=[n for n,q in res.items() if np.isfinite(q['sel']) and q['sel']>=0.55 and q['ver']>=0.55]
print("AUC>=0.55 in entrambe le meta:",len(both),both)
for n in both[:8]:
    q=res[n]; print(n, "fasce", {k:round(v,2) for k,v in q["fasce"].items()}, "W2 ver", round(q["ver_W2"],2), "ic90", round(q["ic90_basso"],2))
