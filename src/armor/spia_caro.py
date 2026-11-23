"""Spia «mercato caro che sta già scendendo» (ricerca libera, PROTOCOLLO_RICERCA_LIBERA.md).

Punteggio = posizione storica del CAPE x posizione storica di quanto il prezzo e' sotto la media a 200 giorni.
Soglie fisse dal periodo fino al 2014 (80 e 90 per cento). Solo informativa: non cambia l'Indice crollo.
"""
from __future__ import annotations

import pandas as pd

from . import store


def _pct(s: pd.Series) -> pd.Series:
    s = s.dropna()
    mensile = len(s) > 10 and (s.index[-1] - s.index[0]).days / len(s) > 10
    return s.expanding(min_periods=60 if mensile else 252).rank(pct=True)


def punteggio() -> pd.Series | None:
    try:
        sp = store.load("sp500").dropna()
        cape = _pct(store.load("cape_m").dropna())
        cape = cape.reindex(cape.index.union(sp.index)).ffill().reindex(sp.index)
        sotto = (-(sp / sp.rolling(200, min_periods=150).mean() - 1)).clip(lower=0)
        return (cape * _pct(sotto)).dropna()
    except Exception:  # noqa: BLE001
        return None


def stato() -> dict | None:
    s = punteggio()
    if s is None or len(s) < 2000:
        return None
    ref = s[(s.index >= "1991-01-01") & (s.index <= "2014-12-31")]
    q80, q90 = float(ref.quantile(0.80)), float(ref.quantile(0.90))
    v = float(s.iloc[-1])
    liv = 2 if v >= q90 else 1 if v >= q80 else 0
    return {"v": v, "q80": q80, "q90": q90, "livello": liv, "data": s.index[-1],
            "nome": ("Spenta", "Attenzione", "Forte")[liv], "col": ("#22c55e", "#f59e0b", "#ef4444")[liv]}


def html() -> str:
    x = stato()
    if x is None:
        return ""
    if x["livello"] == 0:
        riga = "Oggi non c'è: il mercato non è insieme caro e in discesa."
    else:
        riga = ("Oggi c'è: il mercato è caro e il prezzo è già sotto la sua media dell'ultimo anno circa. "
                "Dal 2015, quando succedeva, nel 39% dei casi il mercato è sceso di almeno 8% entro 3 mesi; senza segnale in meno dell'8% dei casi.")
    return (f"<div class='kc vl' style='grid-column:1/-1'><div class='kt'>Spia: mercato caro che sta già scendendo "
            f"<small style='display:block;color:{x['col']};font-weight:700'>{x['nome']}</small></div>"
            f"<div class='vl-s' style='margin-top:6px'>{riga}</div>"
            "<div class='mu'>Trovata con una ricerca su 32 idee (solo crisi finanziarie). Funziona solo se il mercato è già in calo e i casi sono pochi: "
            "è un campanello, non una previsione sicura. Non cambia l'Indice crollo.</div></div>")
