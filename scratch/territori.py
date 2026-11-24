"""Ricerca territori di rischio endogeno. Regole: PROTOCOLLO_TERRITORI.md (+ addendum). Un'unica esecuzione."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from armor import store, territori as T, concentrazione as C
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
import concentrazione as RC  # scratch: bersagli, dr, ic_dr, episodi_indip
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

rng = np.random.default_rng(11)
RC.rng = rng
ORIZ = [("B1 63g -8%", 63, 0.08), ("B2 63g -12%", 63, 0.12), ("B3 126g -15%", 126, 0.15)]
RC.ORIZ = ORIZ
P = {k: store.load("cn_" + k.lower()).dropna() for k in C.SIMBOLI}
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
R = T.calcola(P, sp)
cal, I, caldo, K, stati = R["cal"], R["I"], R["caldo"], R["K"], R["stati"]
Y = RC.bersagli(sp).reindex(cal)
fuori = finestra(cal, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
ok = (~fuori).to_numpy(); ok_s = ok & ~((cal >= "1973-01-01") & (cal <= "1975-06-30"))
anni = cal.year.to_numpy()
BL = {"1971-1989": cal.year <= 1989, "1990-2014": (cal.year >= 1990) & (cal.year <= 2014), "2015-2026": cal.year >= 2015, "tutto": np.ones(len(cal), bool)}
# modello A: media indici -> percentile espandente
A = T.pe(I.mean(axis=1, skipna=True).dropna(), minimo=252).reindex(cal)
stati["MODELLO A: punteggio alto (>=0,90)"] = (A >= 0.90)
# modello B: logistica 1990-2014 su B1
X = I.copy()
tr = (BL["1990-2014"]) & ok & Y["B1 63g -8%"].notna().to_numpy()
med = X[tr].median()
Xs = X.fillna(med)
mu, sd = Xs[tr].mean(), Xs[tr].std().replace(0, 1)
res = {"ingressi": list(X.columns)}
modB = {}
for yn, _, _ in ORIZ:
    trn = BL["1990-2014"] & ok & Y[yn].notna().to_numpy()
    lr = LogisticRegression(C=0.1, max_iter=500).fit(((Xs - mu) / sd)[trn], Y[yn][trn])
    modB[yn] = pd.Series(lr.predict_proba((Xs - mu) / sd)[:, 1], index=cal)
    res.setdefault("coef_modB", {})[yn] = dict(zip(X.columns, [round(float(c), 3) for c in lr.coef_[0]]))
# stato B: probabilita' del bersaglio B1 nel decile alto del passato (percentile espandente >=0,90)
statoB = T.pe(modB["B1 63g -8%"].dropna(), minimo=252).reindex(cal) >= 0.90
stati["MODELLO B: probabilita' alta (decile alto, B1)"] = statoB
anni_t = anni
ris = {}
for sn, s in stati.items():
    sa = s.fillna(False).to_numpy().astype(bool)
    ris[sn] = {"frazione_giorni": round(float(sa[ok].mean()), 4), "episodi_indipendenti": RC.episodi_indip(pd.Series(sa))}
    for yn in Y.columns:
        y = Y[yn].to_numpy(); rr = {}
        for bn, bm in BL.items():
            okb = ok & bm; d, n, pa, pb = RC.dr(y, sa, okb)
            rr[bn] = {"DR": None if np.isnan(d) else round(float(d), 4), "n": n, "P_dentro": None if pa is None or np.isnan(pa) else round(pa, 4), "P_fuori": None if pb is None or np.isnan(pb) else round(pb, 4),
                      "IC90": RC.ic_dr(y[bm], sa[bm], ok[bm], anni[bm]) if bn != "tutto" and not np.isnan(d) else None}
        d_s, *_ = RC.dr(y, sa, ok_s); rr["senza_1973-75"] = None if np.isnan(d_s) else round(float(d_s), 4)
        ris[sn][yn] = rr
# soglia migliore-fra-N sul 2015-2026 (stati x bersagli; modelli A e B inclusi tra gli stati)
n = len(cal); nulli = []
sa_all = {k: v.fillna(False).to_numpy().astype(bool) for k, v in stati.items()}
for _ in range(500):
    k = int(rng.integers(756, n - 756)); mx = -9
    for sn, s in sa_all.items():
        sh = np.roll(s, k)
        for yn in Y.columns:
            d, *_ = RC.dr(Y[yn].to_numpy(), sh, ok & BL["2015-2026"])
            if not np.isnan(d): mx = max(mx, d)
    nulli.append(mx)
soglia = round(float(np.percentile(nulli, 95)), 4)
# AUC dei modelli sul 2015-2026 (+ IC per anno, + nullo circolare)
def auc(sc, y, m):
    mm = m & ~np.isnan(y) & ~np.isnan(sc)
    return roc_auc_score(y[mm], sc[mm]) if mm.sum() > 100 and 0 < y[mm].sum() < mm.sum() else np.nan
auc_res = {}
for nome, sc in {"A": A, "B": modB}.items():
    for yn in Y.columns:
        s_ = (sc if nome == "A" else sc[yn]).to_numpy(); y = Y[yn].to_numpy(); m = ok & BL["2015-2026"]
        a = auc(s_, y, m); ua = np.unique(anni[m]); v = []
        for _ in range(300):
            sel = np.isin(anni, rng.choice(ua, len(ua), replace=True)) & m
            idx = np.concatenate([np.flatnonzero((anni == q) & m) for q in rng.choice(ua, len(ua), replace=True)])
            mm = ~np.isnan(y[idx]) & ~np.isnan(s_[idx])
            if mm.sum() > 100 and 0 < y[idx][mm].sum() < mm.sum(): v.append(roc_auc_score(y[idx][mm], s_[idx][mm]))
        nn = [auc(np.roll(s_, int(rng.integers(756, n - 756))), y, m) for _ in range(200)]
        auc_res[f"{nome} {yn}"] = {"AUC_2015-2026": None if np.isnan(a) else round(float(a), 3), "IC90": [round(float(np.percentile(v, 5)), 3), round(float(np.percentile(v, 95)), 3)], "soglia_caso_95": round(float(np.nanpercentile(nn, 95)), 3),
                                  "AUC_1990-2014": round(float(auc(s_, y, ok & BL["1990-2014"])), 3)}
# cattura dei picchi endogeni
EV = ["1987-08-25", "1989-10-09", "1990-07-16", "1997-10-07", "1998-07-17", "2000-03-24", "2007-10-09", "2010-04-23", "2011-04-29", "2018-01-26", "2022-01-03", "2023-02-02", "2024-07-16"]
cat = {}
for sn, s in stati.items():
    sa = s.fillna(False)
    el = {}
    for d in EV:
        pos = cal.searchsorted(pd.Timestamp(d))
        if pos < 130: continue
        el[d] = bool(sa.iloc[pos - 126:pos + 1].any())
    cat[sn] = {"segnalati": sum(el.values()), "su": len(el), "mancati": [d for d, v in el.items() if not v]}
# situazione di oggi
oggi = {"data": str(cal[-1].date()), "indici": {k: (None if pd.isna(I[k].iloc[-1]) else round(float(I[k].iloc[-1]), 2)) for k in T.ORDINE}, "caldi": [k for k in T.ORDINE if caldo[k].iloc[-1]], "K": int(K.iloc[-1]),
        "A": round(float(A.dropna().iloc[-1]), 3), "B_prob": round(float(modB["B1 63g -8%"].iloc[-1]), 3),
        "ind_oggi": {k: {i: round(float(v.dropna().iloc[-1]), 2) for i, v in d.items() if v.notna().any()} for k, d in R["ind"].items()}}
# storia dei meccanismi caldi ai picchi
picchi = {d: [k for k in T.ORDINE if caldo[k].iloc[max(0, cal.searchsorted(pd.Timestamp(d)) - 20):cal.searchsorted(pd.Timestamp(d)) + 1].any()] for d in EV}
json.dump({"soglia_migliore_fra_N": soglia, "n_prove": len(stati) * 3, "risultati": ris, "auc": auc_res, "cattura": cat, "oggi": oggi, "meccanismi_caldi_ai_picchi": picchi, "coef": res, "disponibilita": {k: str(I[k].first_valid_index().date()) for k in T.ORDINE if I[k].notna().any()}},
          open("scratch/territori_esito.json", "w"), indent=1, ensure_ascii=False)
print("fatto; soglia", soglia, "stati", len(stati))
