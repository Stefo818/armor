"""Difensivita' dei grandi fondi (PROTOCOLLO_DIFENSIVITA.md, esito in ESITO_DIFENSIVITA.md). Solo registro giornaliero, peso zero, NON mostrata nell'app:
nessun test l'ha promossa. Piu' alto = piu' difensivi (liquidita' che cresce piu' del mercato, oro e obbligazioni che battono le azioni, fondi netti corti, protezioni 13F)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import concentrazione, store
from .config import DATA

REG = DATA / "difensivita_registro.csv"


def _pe(s: pd.Series, minimo: int) -> pd.Series:
    return s.dropna().expanding(min_periods=minimo).rank(pct=True)


def calcola(sp: pd.Series, f13: pd.Series | None = None) -> pd.DataFrame:
    """Componenti D1-D6 e indici DIF-L e DIF-C, giorno per giorno dal 1981 (solo passato, con i ritardi di pubblicazione)."""
    lag = concentrazione.lag
    sp = sp.dropna()
    cal = sp.index[sp.index >= "1981-06-01"]

    def al(s):
        return s.reindex(s.index.union(cal)).ffill().reindex(cal)
    mmf = lag(store.load("mmf_assets").dropna(), 2)
    spw = np.log(sp).resample("W-MON").last().diff(52)
    ymm = np.log(mmf).diff(52).dropna()
    d1 = al(_pe((ymm - spw.reindex(ymm.index, method="ffill")).dropna(), 104))
    d1b = al(_pe(np.log(mmf).diff(13).dropna(), 104))
    g = store.load("gold").dropna()
    d2 = al(_pe(np.log(g / sp.reindex(g.index, method="ffill")).diff(63).dropna(), 504))
    t = store.load("tlt").dropna()
    d3 = al(_pe(np.log(t / sp.reindex(t.index, method="ffill")).diff(63).dropna(), 504))
    d4 = al(1 - _pe(lag(store.load("cot_lev_net").dropna(), 4), 104))
    d5 = al(1 - _pe(lag(store.load("cot_am_net").dropna(), 4), 104))
    d6 = pd.Series(np.nan, index=cal)
    if f13 is not None and len(f13) > 8:
        f = f13.copy()
        f.index = pd.to_datetime(f.index) + pd.Timedelta(days=46)
        d6 = al(_pe(f, 8))
    comp = pd.concat({"D1": d1, "D1b": d1b, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6}, axis=1)
    dl = comp[["D1", "D1b", "D2"]]
    out = comp.copy()
    out["DIF_L"] = _pe(dl.mean(axis=1, skipna=True).where(dl.notna().any(axis=1)), 504).reindex(cal)
    out["DIF_C"] = _pe(comp.mean(axis=1, skipna=True).where(comp.notna().sum(axis=1) >= 4), 504).reindex(cal)
    return out


def run() -> dict | None:
    sp = store.load("sp500").dropna()
    try:
        d = json.loads((DATA / "grandi_fondi.json").read_text(encoding="utf-8"))["segnali"]["f13_protezione"]["storia"]
        f13 = pd.Series(d["v"], index=pd.to_datetime(d["d"]))
    except Exception:  # noqa: BLE001
        f13 = None
    m = calcola(sp, f13)
    u = m.dropna(subset=["DIF_L"]).iloc[-1]
    riga = {"data": str(u.name.date()), **{k: (None if pd.isna(v) else round(float(v), 3)) for k, v in u.items()}}
    old = pd.read_csv(REG) if REG.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame([riga])], ignore_index=True).drop_duplicates(subset=["data"], keep="last").sort_values("data").to_csv(REG, index=False)
    print(f"[difensivita] {riga['data']}: DIF-L {riga['DIF_L']}, DIF-C {riga['DIF_C']}", flush=True)
    return riga
