# -*- coding: utf-8 -*-
"""Dati per il motore Titan presi dall'archivio di Armor (data/series) + storia fissa (data/series_storia).
raw_da_archivio() -> dict di serie grezze per titan.market_stage()."""
import pandas as pd

from . import store
from .config import DATA

STORIA = DATA / "series_storia"

# nome Titan -> id nell'archivio
MAPPA = {
    "sp500": "sp500", "vix": "vix", "vix3m": "vix3m", "vvix": "vvix", "skew": "skew", "rsp": "rsp", "iwm": "iwm", "dxy": "dxy",
    "oil": "wti", "oil_fred": "wti", "gold": "gold", "copper": "copper", "dax": "dax", "n225": "nikkei", "eem": "eem",
    "hyg": "hyg", "ief": "ief", "kre": "kre", "iyt": "iyt", "smh": "smh",
    "xlk": "sec_xlk", "xlf": "sec_xlf", "xlv": "sec_xlv", "xly": "sec_xly", "xli": "sec_xli", "xlp": "sec_xlp",
    "xle": "sec_xle", "xlu": "sec_xlu", "xlb": "sec_xlb",
    "baa": "baa_m", "baa10y": "baa10y", "nfci": "nfci", "icsa": "icsa", "ccsa": "ccsa", "permit": "permit", "indpro": "indpro",
    "cpi": "cpi", "cp": "cp", "walcl": "walcl", "tga": "tga", "rrp": "rrp",
}


def _storia(nome: str) -> pd.Series:
    p = STORIA / f"{nome}.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p, parse_dates=["date"])
    return df.set_index("date")["value"].astype(float).sort_index()


def raw_da_archivio() -> dict:
    S = {k: store.load(v) for k, v in MAPPA.items()}
    dgs10 = store.load("dgs10")
    # tassi: archivio (giornaliero FRED) con precedenza, storia fissa dove l'archivio non arriva
    S["y10y"] = dgs10.combine_first(_storia("y10y"))
    t3 = (dgs10 - store.load("t10y3m")).dropna()
    S["y3m"] = t3.combine_first(_storia("y3m"))
    dgs5 = store.load("dgs5")
    S["y5y"] = dgs5.combine_first(_storia("y5y")) if len(dgs5) else _storia("y5y")
    S["ebp"] = _storia("ebp")                       # nota Fed: da collegare ad un aggiornamento automatico
    S["cape"] = store.load("cape_m").combine_first(_storia("cape"))
    S["pe"] = store.load("pe_m").combine_first(_storia("pe"))
    S["ps"] = store.load("ps_m").combine_first(_storia("ps"))
    return S
