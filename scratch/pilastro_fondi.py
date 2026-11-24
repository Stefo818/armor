import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from sklearn.metrics import roc_auc_score
from armor import store, difensivita as D
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
import concentrazione as RC
RC.ORIZ = [("B1 63g -8%", 63, 0.08), ("B2 63g -12%", 63, 0.12), ("B3 21g -5%", 21, 0.05)]
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
t = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
six = t[[f"p{i}_stress" for i in range(1, 7)]]
sai6 = six.mean(axis=1)
print("super_armor_index vs media dei sei: scarto massimo", round(float((sai6 - t["super_armor_index"]).abs().max()), 3))
dl = D.calcola(sp, None)["DIF_L"]
p7 = (dl.reindex(t.index, method="ffill") * 100).clip(1, 100)
sai7 = pd.concat([six, p7.rename("p7")], axis=1).mean(axis=1, skipna=False)   # solo dove p7 esiste
idx = t.index[p7.notna()]
y = RC.bersagli(sp).reindex(idx)
fuori = finestra(idx, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = idx.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(idx), pos + 180)] = True
ok = (~fuori).to_numpy()
A6, A7 = sai6.reindex(idx).shift(1), sai7.reindex(idx).shift(1)   # indice di IERI
res = {"dal": str(idx[0].date())}
def auc(s, yy, m):
    mm = m & ~np.isnan(yy) & ~s.isna().to_numpy()
    return roc_auc_score(yy[mm], s.to_numpy()[mm]) if mm.sum() > 100 and 0 < yy[mm].sum() < mm.sum() else np.nan
migl = 0; peggio = False
for bn, bm in {"1990-2014": idx.year <= 2014, "2015-2026": idx.year >= 2015}.items():
    for yn in y.columns:
        a6, a7 = auc(A6, y[yn].to_numpy(), ok & bm), auc(A7, y[yn].to_numpy(), ok & bm)
        res[f"{bn} {yn}"] = {"SAI6": round(float(a6), 4), "SAI7": round(float(a7), 4), "delta": round(float(a7 - a6), 4)}
for yn in y.columns:
    d = [res[f"{b} {yn}"]["delta"] for b in ("1990-2014", "2015-2026")]
    if min(d) >= 0.01: migl += 1
    if min(d) < -0.01: peggio = True
res["bersagli_migliorati_in_entrambi_i_blocchi"] = migl; res["qualcuno_peggiora_oltre_0,01"] = peggio
res["ADOTTATO"] = bool(migl >= 2 and not peggio)
res["p7_oggi"] = round(float(p7.dropna().iloc[-1]), 1)
json.dump(res, open("scratch/pilastro_fondi_esito.json", "w"), indent=1)
print(json.dumps(res, indent=1))
