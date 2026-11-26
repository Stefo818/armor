"""Stesse tabelle di crollo_precisione.py ma per l'Indice Crollo versione 3 (formula unificata). Solo crisi finanziarie, dal 1990."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra
from armor import indice_crollo as ic

X = ic.calcola_serie()
for nome_idx in ("indice", "indice_classico"):
    idx = X[nome_idx]; sp = X["sp500"]; cal = X.index
    fuori = finestra(cal, ESTERNI)
    for dd in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(dd)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
    picco = sp.rolling(252, min_periods=60).max(); dd_ora = sp / picco - 1
    fwd_min = pd.concat([sp.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
    arriva10 = ((fwd_min / picco - 1) <= -0.10).astype(float); arriva10[fwd_min.isna()] = np.nan
    ok = (~fuori) & arriva10.notna() & idx.notna()
    print("=====", nome_idx)
    for nome, m in (("<2% max, verde/grigio", ok & (dd_ora > -0.02) & (idx < 41)), ("<2% max, giallo o peggio", ok & (dd_ora > -0.02) & (idx >= 41)),
                    ("2-7%, verde/grigio", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx < 41)), ("2-7%, giallo 41-60", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx >= 41) & (idx <= 60)),
                    ("2-7%, rosso/viola 61+", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx > 60)), ("tutti, giallo o peggio", ok & (idx >= 41)), ("tutti, verde", ok & (idx <= 35)), ("tutti", ok)):
        y = arriva10[m]
        print(f"{nome:28s} giorni {len(y):5d}  poi -10%: {100*y.mean():5.1f}%" if len(y) else f"{nome}: vuoto")
