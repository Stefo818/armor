"""Difensivita' dei grandi fondi. Regole: PROTOCOLLO_DIFENSIVITA.md. Un'unica esecuzione."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from armor import store, territori as T, concentrazione as C
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
import concentrazione as RC
rng = np.random.default_rng(23); RC.rng = rng
RC.ORIZ = [("B1 63g -8%", 63, 0.08), ("B2 63g -12%", 63, 0.12)]
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
cal = sp.index[sp.index >= "1981-06-01"]
lag = C.lag
def pe(s, minimo): return s.dropna().expanding(min_periods=minimo).rank(pct=True)
def al(s): return s.reindex(s.index.union(cal)).ffill().reindex(cal)
spw = np.log(sp)
mmf = lag(store.load("mmf_assets").dropna(), 2)
ymm = np.log(mmf).diff(52).dropna(); ysp = np.log(sp).resample("W-MON").last().diff(52)
rel = (ymm - ysp.reindex(ymm.index, method="ffill")).dropna()
D1 = al(pe(rel, 104)); D1b = al(pe(np.log(mmf).diff(13).dropna(), 104))
g = store.load("gold").dropna(); D2 = al(pe(np.log(g / sp.reindex(g.index, method="ffill")).diff(63).dropna(), 504))
t = store.load("tlt").dropna(); D3 = al(pe(np.log(t / sp.reindex(t.index, method="ffill")).diff(63).dropna(), 504))
D4 = al(1 - pe(lag(store.load("cot_lev_net").dropna(), 4), 104)); D5 = al(1 - pe(lag(store.load("cot_am_net").dropna(), 4), 104))
gf = json.load(open("data/grandi_fondi.json"))["segnali"]["f13_protezione"]["storia"]
f13 = pd.Series(gf["v"], index=pd.to_datetime(gf["d"])); f13.index = f13.index + pd.Timedelta(days=46)
D6 = al(pe(f13, 8))
DL = pe(pd.concat([D1, D1b, D2], axis=1).mean(axis=1, skipna=True).where(pd.concat([D1, D1b, D2], axis=1).notna().any(axis=1)), 504).reindex(cal)
comp = pd.concat([D1, D1b, D2, D3, D4, D5, D6], axis=1)
DC = pe(comp.mean(axis=1, skipna=True).where(comp.notna().sum(axis=1) >= 4), 504).reindex(cal)
# bersagli ed esclusioni
Y = RC.bersagli(sp).reindex(cal)
fuori = finestra(cal, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
ok = (~fuori).to_numpy(); anni = cal.year.to_numpy()
BL = {"1981-2014": cal.year <= 2014, "2015-2026": cal.year >= 2015}
res = {"T1": {}, "T2": {}, "T3": {}}
stati = {}
for nome, ind in (("DIF-L", DL), ("DIF-C", DC)):
    stati[f"{nome} alto>=0,80"] = (ind >= 0.80); stati[f"{nome} basso<=0,20"] = (ind <= 0.20)
for sn, s in stati.items():
    sa = s.fillna(False).to_numpy().astype(bool); valido = (~(DL if sn.startswith("DIF-L") else DC).isna()).to_numpy()
    res["T1"][sn] = {"frazione": round(float(sa[ok].mean()), 3), "episodi": RC.episodi_indip(pd.Series(sa))}
    for yn in Y.columns:
        y = Y[yn].to_numpy(); rr = {}
        for bn, bm in BL.items():
            okb = ok & bm & valido; d, n, pa, pb = RC.dr(y, sa, okb)
            rr[bn] = {"DR": None if np.isnan(d) else round(float(d), 4), "n": n, "P_dentro": None if pa is None or np.isnan(pa) else round(pa, 4), "P_fuori": None if pb is None or np.isnan(pb) else round(pb, 4),
                      "IC90": RC.ic_dr(y[bm], sa[bm], (ok & valido)[bm], anni[bm]) if not np.isnan(d) else None}
        res["T1"][sn][yn] = rr
# soglia migliore fra N (8 prove) sul 2015-2026
nul = []; n = len(cal)
for _ in range(500):
    k = int(rng.integers(504, n - 504)); mx = -9
    for sn, s in stati.items():
        sh = np.roll(s.fillna(False).to_numpy().astype(bool), k); v = (~(DL if sn.startswith("DIF-L") else DC).isna()).to_numpy()
        for yn in Y.columns:
            d, *_ = RC.dr(Y[yn].to_numpy(), sh, ok & BL["2015-2026"] & v)
            if not np.isnan(d): mx = max(mx, d)
    nul.append(mx)
res["soglia_migliore_fra_8"] = round(float(np.percentile(nul, 95)), 4)
# T2 rimbalzo
dd = (sp / sp.rolling(252, min_periods=126).max() - 1).reindex(cal)
fw = (sp.shift(-63) / sp - 1).reindex(cal)
sott = ((dd <= -0.10) & fw.notna() & DL.notna()).to_numpy() & ok
def diff_med(m, ind):
    a, b = m & (ind >= 0.67).to_numpy(), m & (ind <= 0.33).to_numpy()
    return (np.median(fw.to_numpy()[a]) - np.median(fw.to_numpy()[b])) if a.sum() > 30 and b.sum() > 30 else np.nan, int(a.sum()), int(b.sum())
for bn, bm in BL.items():
    m = sott & bm; d, na, nb = diff_med(m, DL); ua = np.unique(anni[m]); v = []
    for _ in range(400):
        q = rng.choice(ua, len(ua), replace=True); sel = np.zeros(len(cal), bool)
        for a_ in q: sel |= (anni == a_) & m
        x, *_ = diff_med(sel, DL)
        if not np.isnan(x): v.append(x)
    res["T2"][bn] = {"diff_mediana_alto_meno_basso": None if np.isnan(d) else round(float(d), 4), "n_alto": na, "n_basso": nb, "IC90": [round(float(np.percentile(v, 5)), 4), round(float(np.percentile(v, 95)), 4)] if len(v) > 50 else None,
                     "episodi_sotto_-10%": RC.episodi_indip(pd.Series(m))}
# T3 conferma: Bolla o Credito >= 70
P = {k: store.load("cn_" + k.lower()).dropna() for k in C.SIMBOLI}
Rr = T.calcola(P, sp); I = Rr["I"]
bol = T.pe(I[["M1", "M0"]].mean(axis=1, skipna=True).dropna(), 252).reindex(cal); cre = T.pe(I[["M3", "M5"]].mean(axis=1, skipna=True).dropna(), 252).reindex(cal)
acc = ((bol >= 0.70) | (cre >= 0.70)).fillna(False).to_numpy()
low, high = (DL <= 0.33).to_numpy(), (DL >= 0.67).to_numpy()
y = Y["B1 63g -8%"].to_numpy(); okc = ok & acc & (low | high) & DL.notna().to_numpy()
res["T3"]["giorni_stato"] = int((ok & acc).sum())
for bn, bm in [("tutto", np.ones(len(cal), bool))] + list(BL.items()):
    d, n_, pa, pb = RC.dr(y, low, okc & bm)
    res["T3"][bn] = {"DR_bassa_meno_alta": None if np.isnan(d) else round(float(d), 4), "n_bassa": n_, "P_bassa": None if pa is None or np.isnan(pa) else round(pa, 4), "P_alta": None if pb is None or np.isnan(pb) else round(pb, 4),
                     "IC90": RC.ic_dr(y[bm], low[bm], okc[bm], anni[bm]) if not np.isnan(d) else None}
oggi = {"data": str(cal[-1].date()), "DIF-L": round(float(DL.dropna().iloc[-1]), 3), "DIF-C": None if DC.dropna().empty else round(float(DC.dropna().iloc[-1]), 3), "componenti": {k: round(float(v.dropna().iloc[-1]), 2) for k, v in zip(["D1", "D1b", "D2", "D3", "D4", "D5", "D6"], [D1, D1b, D2, D3, D4, D5, D6]) if v.notna().any()},
        "Bolla": round(float(bol.iloc[-1]), 2), "Credito": round(float(cre.iloc[-1]), 2), "disponibili": {"DIF-L dal": str(DL.first_valid_index().date()), "DIF-C dal": str(DC.first_valid_index().date())}}
res["oggi"] = oggi
json.dump(res, open("scratch/difensivita_esito.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])
