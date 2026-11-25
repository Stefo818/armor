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
# ---- episodi
f5 = pd.Series([a[i + 1:i + 6].min() / a[i] - 1 if i + 5 < len(a) else np.nan for i in range(len(a))], index=sp.index).reindex(cal)
days = np.where((f5 <= -0.08).fillna(False).to_numpy())[0]
T0 = []; last = None
for d in days:
    if last is None or d - last > 60: T0.append(int(d))
    last = d
T0 = np.array(T0); print("episodi", len(T0), [str(cal[i].date()) for i in T0])
yr = np.array([cal[i].year for i in T0]); SEL = yr <= 2011; VER = ~SEL
W = {"W": (10, 2), "W2": (3, 2), "W5": (6, 4), "W10": (10, 7)}
def win(t, k):  # posizioni t-k1 .. t-k2
    a_, b_ = W[k]; return np.arange(max(0, t - a_), t - b_ + 1)
zona = np.zeros(N, bool)
for t in T0: zona[max(0, t - 60):min(N, t + 6)] = True
base = (~zona) & (np.arange(N) >= 500 + 252)
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
    # anticipo
    lead, hit = [], 0
    for t in T0:
        seg = np.arange(max(0, t - 20), t - 1); v_ = PV[seg, j]; f_ = np.where(v_ >= 0.9)[0]
        if len(f_): hit += 1; lead.append(int(t - seg[f_[0]]))
    # intervallo al 90% (episodi di verifica)
    eps = [auc_win(j, t, "W") for t in T0[VER]]; eps = np.array([e for e in eps if np.isfinite(e)])
    rng_ = np.random.default_rng(7); bs = [rng_.choice(eps, len(eps)).mean() for _ in range(2000)] if len(eps) else [np.nan]
    res[n] = dict(sel=s, n_sel=ns, ver=v, n_ver=nv, tutti=al, senza_2001_2020=ax, ver_W2=w2, ic90_basso=float(np.percentile(bs, 5)), episodi_con_segnale=hit, anticipo_mediano=(float(np.median(lead)) if lead else None), dir=F[n][1])
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
    q["passa_selezione"] = bool(q["sel"] >= 0.65 and q["sel"] > soglia) if np.isfinite(q["sel"]) else False
    q["passa_verifica"] = bool(q["passa_selezione"] and q["ver"] >= 0.60 and q["ic90_basso"] > 0.5 and q["ver_W2"] > 0.5)
tab = pd.DataFrame(res).T.sort_values("sel", ascending=False)
pd.set_option("display.width", 250)
print(tab.head(25)[["dir", "sel", "ver", "tutti", "senza_2001_2020", "ver_W2", "ic90_basso", "episodi_con_segnale", "anticipo_mediano", "passa_selezione", "passa_verifica"]].round(3).to_string())
print("passano selezione:", [n for n, q in res.items() if q["passa_selezione"]]); print("passano verifica:", [n for n, q in res.items() if q["passa_verifica"]])
print("migliori per verifica (info):", tab.sort_values("ver", ascending=False).head(8)[["sel", "ver"]].round(3).to_dict("index"))
# ---- Parte 1: indici
d = g.dati()
def serie(k):
    r_ = d[k]; t = pd.to_datetime(pd.Series(r_["dt"]).cumsum() + r_["t0"], unit="D"); s = pd.Series([x / 10 for x in r_["v"]], index=t.values); return s[~s.index.duplicated()].reindex(cal, method="ffill", tolerance=pd.Timedelta(days=5))
p1 = {}
for k in ("crollo", "armor", "minimi"):
    s = serie(k); ep = []
    for t in T0:
        seg = s.iloc[max(0, t - 60):t - 1]
        def prima(th):
            idx = np.where(seg.to_numpy() >= th)[0]; return int(t - (max(0, t - 60) + idx[0])) if len(idx) else None
        w40 = s.iloc[max(0, t - 40):t + 1].to_numpy()
        if np.isnan(w40).all(): continue
        imin = int(np.nanargmin(w40)); ep.append(dict(data=str(cal[t].date()), sopra50=prima(50), sopra60=prima(60), da_minimo=int(len(w40) - 1 - imin), v_t2=float(s.iloc[t - 2]), v_t5=float(s.iloc[t - 5]), v_t10=float(s.iloc[t - 10])))
    bm = float(s[base].mean()); p1[k] = dict(base=bm, episodi=ep)
    A = [x for x in (np.nan if True else 0,)]
    print(k, "media giorni di base", round(bm, 1))
    print(pd.DataFrame(ep).to_string(index=False))
    col = pd.Series(s.to_numpy()); pe = col.expanding(500).rank(pct=True).to_numpy(); Bk = np.sort(pe[base & np.isfinite(pe)])
    au = []
    for t in T0:
        v = pe[win(t, "W")]; v = v[np.isfinite(v)]
        if len(v): au.append(float(((np.searchsorted(Bk, v, "left") + np.searchsorted(Bk, v, "right")) / 2 / len(Bk)).mean()))
    p1[k]["auc"] = float(np.mean(au)); print(k, "AUC episodi (W)", round(float(np.mean(au)), 3))
json.dump(dict(episodi=[str(cal[i].date()) for i in T0], soglia=soglia, n=len(names), ipotesi=res, parte1=p1), open("scratch/anticipo_crolli_esito.json", "w"), indent=1, default=float)

print("--- ipotesi dell'utente / struttura ---")
for n in names:
    if any(x in n for x in ("vicino_max","rotture","sedute_dal","ampiezza","massimi_decr","ombra","chiusura_nel")):
        q=res[n]; print(f"{n:32s} sel {q['sel']:.2f} ver {q['ver']:.2f} tutti {q['tutti']:.2f} segnali {q['episodi_con_segnale']}/13 anticipo {q['anticipo_mediano']}")
both=[n for n,q in res.items() if np.isfinite(q['sel']) and q['sel']>=0.6 and q['ver']>=0.6]
print("AUC>=0.60 in entrambe le meta:",len(both),both)
for n in ("vix_su_media60","ampiezza_5_60","vol_10_60","vix_max10_su_media60"):
    j=names.index(n); print(n,{k:round(auc_set(j,T0,k)[0],3) for k in W})
