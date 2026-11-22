"""Cosa vuol dire davvero «sopra 80 il calo arriva al 10% nel 100% dei casi».

Il bersaglio era misurato dal massimo a 12 mesi, non dal prezzo del giorno: se il mercato e' gia' sceso
molto, quel calo e' in buona parte gia' avvenuto. Qui si guarda cosa succede DOPO, al prezzo di quel
giorno, che e' l'unica cosa che conta per chi e' dentro.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402

h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
sp = store.load("sp500").dropna()
cal = h.index.intersection(sp.index)
h, spx = h.loc[cal], sp.loc[cal]
fuori = finestra(cal, ESTERNI)
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d))
    fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
picco = spx.rolling(252, min_periods=60).max()
dd = spx / picco - 1
buono = (~fuori) & spx.notna()
alto = buono & (h["armor_tarato"] > 80)

print(f"giorni con indice sopra 80: {int(alto.sum())}")
g = pd.Series(alto.astype(int))
blocchi = (g.diff() != 0).cumsum()[g == 1]
print(f"non sono consecutivi: sono {blocchi.nunique()} periodi distinti\n")
print(f"{'periodo':26s} {'giorni':>7s} {'gia sotto il massimo':>21s}")
for b, blk in g[g == 1].groupby(blocchi):
    t0, t1 = blk.index[0], blk.index[-1]
    print(f"{str(t0.date())} -> {str(t1.date())} {len(blk):7d} {dd[t0:t1].mean()*100:20.1f}%")

print(f"\nquanto era GIA' sceso il mercato in quei giorni: in mediana {dd[alto].median()*100:.1f}% sotto il massimo")
print(f"   (quindi dei 10 punti del bersaglio, in mediana ne erano gia' stati persi {-dd[alto].median()*100:.1f})")

print("\n=== cosa succede DOPO, partendo dal prezzo di quel giorno ===")
print(f"{'orizzonte':12s} {'mediana':>9s} {'media':>8s} {'positivi':>9s} {'peggiore':>9s} {'scende ancora >5%':>18s}")
for n in (5, 10, 21, 63, 126):
    f = (spx.shift(-n) / spx - 1)[alto].dropna() * 100
    mn = (pd.concat([spx.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / spx - 1)[alto].dropna() * 100
    if len(f):
        print(f"{n:4d} sedute  {f.median():+8.2f}% {f.mean():+7.2f}% {(f>0).mean()*100:8.0f}% {f.min():+8.1f}% {(mn<=-5).mean()*100:17.0f}%")
print("\n(«scende ancora >5%» = in qualche momento della finestra il prezzo e' sceso di almeno il 5% sotto quel giorno)")

print("\n=== lo stesso controllo su tutte le fasce ===")
print(f"{'fascia':12s} {'giorni':>7s} {'gia sotto il massimo (mediana)':>31s} {'dopo 21 sedute (mediana)':>26s} {'scende ancora >5% in 21 sed':>28s}")
for lo, hi, et in ((0, 40, "sotto 40"), (40, 60, "40-60"), (60, 80, "60-80"), (80, 101, "sopra 80")):
    m = buono & (h["armor_tarato"] >= lo) & (h["armor_tarato"] < hi)
    f21 = (spx.shift(-21) / spx - 1)[m].dropna() * 100
    mn21 = (pd.concat([spx.shift(-i) for i in range(1, 22)], axis=1).min(axis=1) / spx - 1)[m].dropna() * 100
    print(f"{et:12s} {int(m.sum()):7d} {dd[m].median()*100:30.1f}% {f21.median():25.2f}% {(mn21<=-5).mean()*100:27.0f}%")
