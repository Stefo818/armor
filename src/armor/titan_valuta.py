# -*- coding: utf-8 -*-
"""Previsioni storiche di Titan nel formato della valutazione dei modelli (date, orizzonte, soglia, probabilità di calo), sulle stesse date degli altri modelli.
Usato da modeleval.evaluate: così Titan è confrontato con A1, FHS, FHS+VIX ecc. con la stessa regola. Solo cali: il «rialzo» di Titan è un punteggio, non una probabilità."""
import pandas as pd

from . import titan, titan_job

HZ = {"10g": (7, 0.05), "1m": (21, 0.10), "3m": (63, 0.10), "6m": (126, 0.10)}


def preds(dates, df: pd.DataFrame | None = None, log=print) -> pd.DataFrame:
    df = titan_job.costruisci() if df is None else df
    righe = []
    for hz, (h, th) in HZ.items():
        r = titan.walk_forward(df, h, th, dates=dates)
        log(f"[valuta] Titan {hz}: {len(r)} previsioni")
        for t, v in r["p_dd_v40"].items():
            righe.append({"date": t, "hz": hz, "kind": "down", "thr": int(round(th * 100)), "p": float(v)})
    return pd.DataFrame(righe)
