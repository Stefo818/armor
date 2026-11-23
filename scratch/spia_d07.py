import sys
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import indice_crollo as ic, store
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
from elementi_esterni import ORIZZONTI, pct_esp
h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
crollo = ic.calcola_serie(); sp = store.load("sp500").dropna()
cal = h.index.intersection(sp.index).intersection(crollo.index); spx = sp.loc[cal]
cape = pct_esp(store.load("cape_m").dropna()); cape = cape.reindex(cape.index.union(cal)).ffill().reindex(cal)
est = (sp / sp.rolling(200, min_periods=150).mean() - 1)
below = (-est).clip(lower=0).reindex(cal)
sc = cape * pct_esp(below.dropna()).reindex(cal)
fuori = finestra(cal, ESTERNI)
for d in MISTE_MAX:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - PRIMA):min(len(cal), p + 180)] = True
print("oggi: cape pct %.3f, sotto media %.4f, punteggio %.3f, percentile storico del punteggio %.3f" % (cape.iloc[-1], below.iloc[-1], sc.iloc[-1], (sc.dropna() < sc.iloc[-1]).mean()))
for nome, m in (("scelta", cal <= "2014-12-31"), ("verifica", cal >= "2015-01-01")):
    for soglia_q in (0.80, 0.90):
        q = sc[m & ~fuori].quantile(soglia_q)
        for ori, (n, s_) in ORIZZONTI.items():
            mn = pd.concat([spx.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / spx - 1
            y = (mn <= -s_).astype(float); y[mn.isna()] = np.nan
            mm = m & ~fuori & y.notna() & sc.notna()
            a = sc >= q
            print(f"{nome:9s} top{int((1-soglia_q)*100):2d}% {ori:14s} acceso {int((a&mm).sum()):5d} gg: calo {y[a&mm].mean()*100:5.1f}% | spento {y[(~a)&mm].mean()*100:5.1f}%")
