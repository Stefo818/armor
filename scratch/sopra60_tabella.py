"""Parte 7 del protocollo: la domanda esplicita dell'utente.

«Quando gli indici stanno sopra 60 per una settimana, un mese, tre mesi, quante probabilita' di crollo?»
Risposta misurata per tutti e tre gli indici e tutte e quattro le finestre, anche dove non e' promossa.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from armor import store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402

h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
crollo = ic.calcola_serie()
sp = store.load("sp500").dropna()
cal = h.index.intersection(sp.index).intersection(crollo.index)
h, spx = h.loc[cal], sp.loc[cal]
IDX = {"Indice Armor": h["armor_tarato"], "Super Armor": h["super_armor_index"], "Indice crollo": crollo["indice"].reindex(cal)}
fuori = finestra(cal, ESTERNI)
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d))
    fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
buono = ~fuori

ORI = {"una settimana (-3%)": (5, 0.03), "un mese (-5%)": (21, 0.05), "tre mesi (-8%)": (63, 0.08)}
Y = {}
for k, (n, s) in ORI.items():
    mn = pd.concat([spx.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / spx - 1
    y = (mn <= -s).astype(float)
    y[mn.isna()] = np.nan
    Y[k] = y

FIN = {"5 sedute (una settimana)": 5, "21 sedute (un mese)": 21, "63 sedute (tre mesi)": 63, "126 sedute (sei mesi)": 126}
out = {}
print("Quota di giorni sopra 60 nella finestra = almeno la meta' delle sedute della finestra.\n")
for k in ORI:
    print(f"=== bersaglio: {k} · frequenza di base {Y[k][buono].mean()*100:.1f}% ===")
    print(f"{'indice':15s} {'finestra':26s} {'giorni':>7s} {'episodi':>8s} {'crollo poi':>11s} {'rispetto alla base':>19s}")
    base = float(Y[k][buono].mean()) * 100
    for nome, s in IDX.items():
        for fn, n in FIN.items():
            q = (s > 60).rolling(n, min_periods=max(3, n // 2)).mean()
            m = buono & (q >= 0.5) & Y[k].notna()
            if m.sum() < 30:
                continue
            g = pd.Series(m.astype(int))
            ep = (g.diff() != 0).cumsum()[g == 1].nunique()
            p = float(Y[k][m].mean()) * 100
            out.setdefault(k, {}).setdefault(nome, {})[fn] = {"giorni": int(m.sum()), "episodi": int(ep),
                                                              "crollo": round(p, 1), "base": round(base, 1),
                                                              "volte_la_base": round(p / base, 1) if base else None}
            print(f"{nome:15s} {fn:26s} {int(m.sum()):7d} {ep:8d} {p:10.1f}% {p/base:18.1f}x")
    print()
json.dump(out, open("scratch/sopra60_tabella.json", "w"), ensure_ascii=False, indent=1)
print("salvato")
