# -*- coding: utf-8 -*-
"""Collegamento dei valori Titan (data/titan_storia.csv) a Indice Armor e Super Armor mostrati nell'app.
Se il file Titan manca, è vuoto o è più vecchio di MAX_GIORNI rispetto al dato di mercato, restituisce None e l'app usa i valori di prima."""
import pandas as pd

from .config import DATA

FILE = DATA / "titan_storia.csv"
MAX_GIORNI = 6
ATTIVO = True   # False = ignora Titan e mostra i vecchi valori


def serie(colonna: str, rif: pd.Timestamp) -> pd.Series | None:
    if not ATTIVO:
        return None
    try:
        s = pd.read_csv(FILE, index_col=0, parse_dates=True)[colonna].dropna()
    except Exception:  # noqa: BLE001
        return None
    if len(s) < 500 or (pd.Timestamp(rif) - s.index[-1]).days > MAX_GIORNI:
        return None
    return s.clip(1, 100)
