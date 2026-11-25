"""Copertura degli episodi e confronto con la sola volatilità (vol60) per i candidati confermati e per il migliore di ogni bersaglio."""
import sys, pickle, json
from r200k_lib import *
G = sys.argv[1]; D = pickle.load(open(f"/tmp/r200k_{G}.pkl", "rb")); P2 = json.load(open(f"scratch/r200k_p2_{G}.json")); cal = D["cal"]; Y = D["Y"]; rows = D["rows"]; N = len(cal)
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]; C = sp.reindex(cal); Cn = C.to_numpy(float); yrs = np.asarray(cal.year)
# episodi endogeni: massimo entro +-20 sedute con calo >=5% entro 120 sedute, fuori dalle finestre esterne
S0 = Setup(cal, C, G, seed=1); ext = ~S0.MASK["T1"]
peaks = []
for i in range(20, N - 120):
    if ext[i] or Cn[i] < Cn[i - 20:i + 21].max(): continue
    if Cn[i + 1:i + 121].min() / Cn[i] - 1 <= -0.05 and (not peaks or i - peaks[-1] > 20): peaks.append(i)
peaks = np.array(peaks); per = {"1932-1989": (yrs[peaks] >= 1932) & (yrs[peaks] <= 1989), "1992-2007": (yrs[peaks] >= 1992) & (yrs[peaks] <= 2007), "2008-oggi": yrs[peaks] >= 2008}
LOG("episodi endogeni:", {k: int(v.sum()) for k, v in per.items()})
lx = np.log(C); vol60 = lx.diff().rolling(60).std().to_numpy()
def build(tg, r_):
    cand = {c[1]: c for c in D["top_sel"][tg]}; s = np.zeros(N)
    for nm, w in r_["membri"].items():
        stt, _, vec, ori = cand[nm]; ok = np.isfinite(vec); p = np.zeros(N); p[ok] = (rankdata(vec[ok]) / ok.sum() - 0.5) * ori
        s += (w * p) if r_["tipo"] == "pesi" else (p >= (w / 100 - 0.5)).astype(float)
    return s
def cover(score, tg):
    rs = rows[tg]["sel"]; cut = np.percentile(score[rs], 90); al = (score >= cut) & np.isfinite(score); out = {}
    for k, msk in per.items():
        pk = peaks[msk]
        if len(pk) == 0: continue
        cov = np.mean([al[max(0, i - 10):i + 6].any() for i in pk]); lead = [int(i - np.where(al[max(0, i - 20):i + 1])[0].min() - max(0, i - 20) * 0 - 0) if False else None for i in pk]
        leads = []
        for i in pk:
            w = al[max(0, i - 20):i + 1]
            if w.any(): leads.append(int(len(w) - 1 - np.where(w)[0].min()))
        ra = rows[tg]["old"] if k == "1932-1989" and "old" in rows[tg] else (rows[tg]["sel"] if k == "1992-2007" else rows[tg]["ver"])
        rate = float(al[ra].mean()); y = Y[tg][ra]; prec = float(y[al[ra]].mean()) if al[ra].sum() else float("nan")
        med = np.nanmedian(vol60[rows[tg]['sel']]); calm = [i for i in pk if np.isfinite(vol60[i - 10]) and vol60[i - 10] <= med]; cc = float(np.mean([al[max(0, i - 10):i + 6].any() for i in calm])) if calm else None
        out[k] = dict(n_calmi=len(calm), copertura_calmi=cc, n_episodi=int(len(pk)), copertura=float(cov), casuale=float(1 - (1 - rate) ** 16), giorni_in_allarme=rate, precisione=prec, base=float(y.mean()), anticipo_mediano=float(np.median(leads)) if leads else None, n_con_anticipo=len(leads))
    return out
RES = {}
for tg in ("T1", "T2", "T3"):
    RES[tg] = {}
    # riferimento: sola volatilita a 60 sedute (verso: alta = rischio)
    RES[tg]["vol60"] = cover(np.nan_to_num(vol60, nan=-1), tg)
    sel_list = [r for r in P2[tg]["top"] if r["confermato"]][:3] or P2[tg]["top"][:1]
    for j, r_ in enumerate(sel_list): RES[tg][f"candidato{j+1}{'_confermato' if r_['confermato'] else '_non_confermato'}"] = cover(build(tg, r_), tg)
    for k, v in RES[tg].items(): LOG(f"[{G}/{tg}] {k}:", {p: (round(x['copertura'], 2), round(x['casuale'], 2), round(x['giorni_in_allarme'], 3), round(x['precisione'], 2), x['anticipo_mediano']) for p, x in v.items()})
json.dump(RES, open(f"scratch/r200k_cop_{G}.json", "w"), indent=1, default=float)
