"""Tutti i cali forti dell'S&P 500 negli ultimi 40 anni, rilevati dai dati (non dalla memoria).

Un episodio inizia al massimo precedente e finisce al minimo, prima che il recupero torni entro il 3%
dal massimo. Soglia: almeno 8% di calo, cosi' si prendono anche quelli medi che la soglia del 10% perde.
"""
import json
import sys

import pandas as pd

sys.path.insert(0, "src")
from armor import store  # noqa: E402

SOGLIA = 0.08
sp = store.load("sp500").dropna()
sp = sp[sp.index >= "1986-01-01"]
picco = sp.cummax()
dd = sp / picco - 1

ep, dentro, t_max = [], False, sp.index[0]
for t in sp.index:
    if sp[t] >= picco[t] - 1e-9 and not dentro:
        t_max = t
    if not dentro and dd[t] <= -SOGLIA:
        dentro = True
        inizio_max = sp[:t].idxmax()
    elif dentro and dd[t] >= -0.03:
        seg = sp[inizio_max:t]
        tmin = seg.idxmin()
        ep.append({"massimo": str(inizio_max.date()), "minimo": str(tmin.date()),
                   "calo": round(float(seg.min() / sp[inizio_max] - 1) * 100, 1),
                   "sedute": int(len(sp[inizio_max:tmin]))})
        dentro = False
if dentro:
    seg = sp[inizio_max:]
    tmin = seg.idxmin()
    ep.append({"massimo": str(inizio_max.date()), "minimo": str(tmin.date()),
               "calo": round(float(seg.min() / sp[inizio_max] - 1) * 100, 1),
               "sedute": int(len(sp[inizio_max:tmin])), "in_corso": True})

print(f"cali di almeno l'{SOGLIA*100:.0f}% dal 1986: {len(ep)}\n")
print(f"{'massimo':12s} {'minimo':12s} {'calo':>7s} {'sedute':>7s}")
for e in ep:
    print(f"{e['massimo']:12s} {e['minimo']:12s} {e['calo']:6.1f}% {e['sedute']:7d}{'  (in corso)' if e.get('in_corso') else ''}")
json.dump(ep, open("scratch/episodi_40anni.json", "w"), ensure_ascii=False, indent=1)
