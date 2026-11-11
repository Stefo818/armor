# -*- coding: utf-8 -*-
"""Archivio delle probabilità di calo storiche di ogni modello (data/modelli_preds.csv: date, model, hz, thr, p), per il grafico di confronto.
Si aggiorna con la valutazione mensile (tutti i modelli) e con il comando `titan-storia` (solo Titan)."""
import pandas as pd

from .config import DATA, PRIMARY

FILE = DATA / "modelli_preds.csv"
COLS = ["date", "model", "hz", "thr", "p"]


def carica() -> pd.DataFrame | None:
    try:
        d = pd.read_csv(FILE, parse_dates=["date"])
        return d if len(d) else None
    except Exception:  # noqa: BLE001
        return None


def salva(model: str, df: pd.DataFrame) -> int:
    """Sostituisce le righe di `model` (df con colonne date, hz, kind, thr, p; solo cali alle soglie principali) lasciando gli altri modelli."""
    x = df[(df.get("kind", "down") == "down")].copy()
    x = x[[PRIMARY.get(h) == t for h, t in zip(x.hz, x.thr.astype(int))]]
    x["model"] = model
    x["date"] = pd.to_datetime(x["date"])
    x["p"] = x["p"].astype(float).round(4)
    x = x[COLS]
    old = carica()
    if old is not None:
        x = pd.concat([old[old.model != model], x])
    x.sort_values(["model", "hz", "date"]).to_csv(FILE, index=False, date_format="%Y-%m-%d")
    return len(x)
