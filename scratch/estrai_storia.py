# -*- coding: utf-8 -*-
"""Estrae UNA VOLTA dalla cache di ricerca le serie che FRED non da' piu' per intero
(spread high yield dal 1996, EBP, CAPE/P/E/P/S di Shiller, tassi a 3/5/10 anni) e le salva in data/series_storia/.
Le date vengono riportate indietro del ritardo di pubblicazione, cosi' titan.market_stage lo riapplica una sola volta."""
import os, sys
import pandas as pd

PKL = r"E:\Onedrive\Armor test\test_armor\armor_market_cache.pkl"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "series_storia")
os.makedirs(OUT, exist_ok=True)
LAG = {"y3m": 0, "y5y": 0, "y10y": 0, "hy_oas": 0, "baa_spread": 5, "ebp": 28, "cape": 25, "pe": 45, "ps": 45}

df = pd.read_pickle(PKL)
print("cache:", df.index[0].date(), "->", df.index[-1].date(), len(df), "righe")
for col, lag in LAG.items():
    if col not in df:
        print("MANCA", col); continue
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        print(f"{col:11s} VUOTA nella cache (0 valori): la ricerca non l'ha usata"); continue
    s = s[s.ne(s.shift())]                      # solo i giorni in cui il valore cambia
    s.index = s.index - pd.Timedelta(days=lag)
    s.rename("value").rename_axis("date").to_csv(os.path.join(OUT, f"{col}.csv"))
    print(f"{col:11s} {s.index[0].date()} -> {s.index[-1].date()}  ({len(s)} valori)")
print("Salvato in", OUT)
