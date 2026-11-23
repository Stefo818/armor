"""Predisposizione al crollo: quanto il terreno e' fragile, indipendentemente dal fatto che il mercato stia gia' scendendo.

Regole e risultati: PROTOCOLLO_ANTICIPO.md / ESITO_ANTICIPO.md. Non ha superato la regola di adozione,
quindi NON cambia l'Indice crollo: e' un'informazione separata, registrata ogni giorno per la prova in avanti.
Media dei percentili storici (solo passato) di dieci fattori di fragilita'.
"""
from __future__ import annotations

import csv

import numpy as np
import pandas as pd

from . import store
from .config import DATA

REGISTRO = DATA / "predisposizione_registro.csv"
NOMI = {
    "cape": "mercato caro rispetto agli utili", "buffett": "Borsa molto grande rispetto all'economia",
    "margin": "debiti fatti per comprare azioni", "f5": "costo del debito delle aziende",
    "f4": "costo delle assicurazioni sul ribasso", "f6": "scosse sui tassi americani",
    "f10": "fuga dai settori che rischiano di più", "f11": "nervosismo sui titoli di Stato",
    "nfci": "condizioni finanziarie strette", "liq": "liquidità che si prosciuga",
}


def _lag(s: pd.Series, g: int) -> pd.Series:
    s = s.dropna().copy()
    s.index = s.index + pd.Timedelta(days=g)
    return s[~s.index.duplicated(keep="last")]


def _pct(s: pd.Series, cal) -> pd.Series:
    s = s.dropna()
    mensile = len(s) > 10 and (s.index[-1] - s.index[0]).days / len(s) > 10
    p = s.expanding(min_periods=60 if mensile else 252).rank(pct=True)
    return p.reindex(cal.union(p.index)).ffill().reindex(cal) * 100


def componenti(df: pd.DataFrame) -> pd.DataFrame:
    """df = indice_crollo.calcola_serie(): contiene le famiglie f1..f12."""
    from . import semafori
    cal = df.index
    L = lambda k: store.load(k).dropna()
    c = pd.DataFrame(index=cal)
    c["cape"] = _pct(L("cape_m"), cal)
    c["buffett"] = _pct(_lag(semafori.series_of("buffett"), 90), cal)
    c["margin"] = _pct(_lag(L("margin_yoy"), 50), cal)
    for k in ("f5", "f4", "f6", "f10", "f11"):
        c[k] = df[{"f5": "f5_credito", "f4": "f4_protez", "f6": "f6_tassi", "f10": "f10_rotaz", "f11": "f11_bond"}[k]]
    c["nfci"] = _pct(L("nfci"), cal)
    c["liq"] = _pct(-L("net_liq_13w"), cal)
    return c


def calcola(df: pd.DataFrame) -> dict | None:
    try:
        c = componenti(df)
        ok = c.notna().sum(axis=1) >= 5
        p = c.mean(axis=1, skipna=True).where(ok)
        ult = c.iloc[-1].dropna().sort_values(ascending=False)
        v = float(p.dropna().iloc[-1])
        return {"valore": round(v, 0), "data": str(p.dropna().index[-1].date()),
                "spinte": [{"nome": NOMI[k], "valore": round(float(x), 0)} for k, x in ult.head(3).items()],
                "calme": [{"nome": NOMI[k], "valore": round(float(x), 0)} for k, x in ult.tail(2).items()],
                "liv": "alta" if v >= 70 else "media" if v >= 50 else "bassa"}
    except Exception:  # noqa: BLE001
        return None


def registra(res: dict | None) -> None:
    if not res:
        return
    riga = {"data": res["data"], "predisposizione": res["valore"]}
    try:
        viste = set()
        if REGISTRO.exists():
            with REGISTRO.open(encoding="utf-8") as f:
                viste = {r["data"] for r in csv.DictReader(f)}
        if riga["data"] in viste:
            return
        nuovo = not REGISTRO.exists()
        with REGISTRO.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(riga))
            if nuovo:
                w.writeheader()
            w.writerow(riga)
    except Exception:  # noqa: BLE001
        pass
