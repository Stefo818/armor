"""Descrittivo (non una selezione): cosa misura bene l'Indice Armor? Spearman giornaliero 1990-2026 con grandezze di 'salute del mercato'."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import store
T = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
A = T["armor_tarato"].dropna(); SA = T["super_armor_index"].dropna()
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]
vx = store.load("vix").dropna()
r = np.log(sp).diff()
idx = A.index.intersection(sp.index)
sp = sp.reindex(idx); r = r.reindex(idx)
dd = sp / sp.rolling(252, min_periods=60).max() - 1           # distanza dal massimo (<=0)
vr = r.rolling(21).std() * np.sqrt(252)                       # nervosismo realizzato ora
def fwd_min(s, n): return pd.Series([s.iloc[i + 1:i + 1 + n].min() / s.iloc[i] - 1 if i + n < len(s) else np.nan for i in range(len(s))], index=s.index)
f_dd21, f_dd63 = fwd_min(sp, 21), fwd_min(sp, 63)
f_vol21 = (r[::-1].rolling(21).std()[::-1].shift(-1)) * np.sqrt(252)
f_ret63 = sp.shift(-63) / sp - 1
D = pd.DataFrame({"Armor": A.reindex(idx), "Super vecchio": SA.reindex(idx), "VIX": vx.reindex(idx).ffill(),
                  "dd_ora": -dd, "vol_ora": vr, "dd_21": -f_dd21, "dd_63": -f_dd63, "vol_21": f_vol21, "ret_63": -f_ret63}).dropna()
print(len(D), D.index[0].date(), D.index[-1].date())
print("Spearman con...  (alto = peggio per tutti)")
rows = {"Distanza dal massimo oggi": "dd_ora", "Nervosismo oggi": "vol_ora", "Calo massimo nei 21 giorni dopo": "dd_21",
        "Calo massimo nei 63 giorni dopo": "dd_63", "Nervosismo nei 21 giorni dopo": "vol_21", "Rendimento 63 giorni dopo (invertito)": "ret_63"}
for n, c in rows.items():
    print(f"{n:42s} Armor {D['Armor'].corr(D[c], method='spearman'):+.2f}  Super vecchio {D['Super vecchio'].corr(D[c], method='spearman'):+.2f}  VIX {D['VIX'].corr(D[c], method='spearman'):+.2f}")
print("\nPer fascia di Armor: giorni, distanza media dal massimo, calo medio 21g dopo, rendimento mediano 63g dopo, quota con calo>=5% nei 21g")
for lo, hi in ((0, 40), (40, 60), (60, 80), (80, 101)):
    m = D[(D.Armor >= lo) & (D.Armor < hi)]
    print(f"{lo:3d}-{hi:3d}: n={len(m):5d} dd_ora={m.dd_ora.mean()*100:5.1f}%  dd21={m.dd_21.mean()*100:5.1f}%  ret63_med={-m.ret_63.median()*100:+5.1f}%  P(dd21>=5%)={(m.dd_21>=.05).mean()*100:4.0f}%")
