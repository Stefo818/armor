# -*- coding: utf-8 -*-
"""Tipo di ribasso (PROTOCOLLO_MINIMI.md, parte D) e altri mercati (parte F). Descrittivo: nessuna capacità previsiva dichiarata. File: data/ribasso.json."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "ribasso.json"
FASCE = [("vicino ai massimi", 0.0, 0.05), ("calo normale", 0.05, 0.10), ("correzione", 0.10, 0.20), ("mercato orso", 0.20, 0.30), ("crisi", 0.30, 1.01)]
INDICI = {"sp500": "S&P 500 (USA)", "nikkei": "Nikkei 225 (Giappone)", "dax": "DAX (Germania)", "ftsemib": "FTSE MIB (Italia)"}


def fascia_di(dd: float) -> str:
    for nome, lo, hi in FASCE:
        if lo <= dd < hi:
            return nome
    return FASCE[-1][0]


def _calo_ulteriore(p: pd.Series, h: int) -> pd.Series:
    """Quanto scende ancora il prezzo (come quota del prezzo di oggi) al punto più basso delle h sedute successive; 0 se non scende."""
    fm = p[::-1].rolling(h, min_periods=h).min()[::-1].shift(-1)
    return (1 - fm / p).clip(lower=0)


def _episodi(mask: pd.Series) -> int:
    m = mask.astype(int)
    return int(((m.diff() == 1).sum()) + int(m.iloc[0] == 1))


def per_fascia(p: pd.Series) -> list[dict]:
    p = p.dropna()
    dd = 1 - p / p.cummax()
    c63, c252 = _calo_ulteriore(p, 63), _calo_ulteriore(p, 252)
    r252 = p.shift(-252) / p - 1
    out = []
    for nome, lo, hi in FASCE:
        m = (dd >= lo) & (dd < hi)
        a, b, r = c63[m].dropna(), c252[m].dropna(), r252[m].dropna()
        out.append({"fascia": nome, "da": lo, "a": min(hi, 1.0), "giorni": int(m.sum()), "episodi": _episodi(m),
                    "calo63_med": _r(a.median()) if len(a) else None, "calo63_80": _r(a.quantile(.8)) if len(a) else None,
                    "calo252_med": _r(b.median()) if len(b) else None, "calo252_80": _r(b.quantile(.8)) if len(b) else None,
                    "p_oltre10": _r(float((b > 0.10).mean())) if len(b) else None, "rend12_med": _r(r.median()) if len(r) else None,
                    "rend12_pos": _r(float((r > 0).mean())) if len(r) else None})
    return out


def _r(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 4)


def storia_dd(p: pd.Series) -> list:
    """Distanza dal massimo, un punto a settimana dal 1928 (per il grafico)."""
    dd = (1 - p / p.cummax()).dropna()
    s = dd.resample("W-FRI").last().dropna()
    return [[str(d.date()), round(float(v), 4)] for d, v in s.items()]


def sott_acqua(p: pd.Series) -> dict:
    """Calo massimo dal picco e periodo più lungo passato sotto il massimo precedente; durata attuale."""
    p = p.dropna()
    pk = p.cummax()
    sotto = p < pk
    lun, best, cur_start, best_span = 0, None, None, None
    spans = []
    start = None
    for d, s in sotto.items():
        if s and start is None:
            start = d
        if (not s) and start is not None:
            spans.append((start, d))
            start = None
    in_corso = start
    for a, b in spans:
        g = (b - a).days / 365.25
        if g > lun:
            lun, best_span = g, (a, b)
    att = (p.index[-1] - in_corso).days / 365.25 if in_corso is not None else 0.0
    # un periodo sotto il massimo comincia l'ultimo giorno del massimo precedente
    if att > lun:
        lun, best_span = att, (in_corso, None)
    mdd = float((1 - p / pk).max())
    return {"calo_max": _r(mdd), "anni_piu_lungo": _r(lun), "da": str(best_span[0].date())[:7] if best_span else None,
            "a": (str(best_span[1].date())[:7] if best_span and best_span[1] is not None else "oggi"), "anni_attuale": _r(att),
            "dal_massimo_oggi": _r(float(1 - p.iloc[-1] / pk.iloc[-1])), "inizio_dati": str(p.index[0].date())[:4]}


def calcola(p: pd.Series | None = None) -> dict:
    if p is None:
        from .features import closed_sp500
        p = closed_sp500()
    p = p.dropna()
    dd = float(1 - p.iloc[-1] / p.cummax().iloc[-1])
    pk = p.idxmax()
    out = {"data": str(p.index[-1].date()), "dal_massimo": dd, "fascia": fascia_di(dd), "data_massimo": str(pk.date()), "giorni_dal_massimo": int((p.index[-1] - pk).days),
           "livello_massimo": float(p.max()), "prezzo": float(p.iloc[-1]), "fasce": per_fascia(p), "storia": storia_dd(p), "altri_mercati": []}
    for k, nome in INDICI.items():
        try:
            s = store.load(k).dropna()
            if len(s) > 500:
                out["altri_mercati"].append({"id": k, "nome": nome, **sott_acqua(s)})
        except Exception:  # noqa: BLE001
            continue
    return out


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    log(f"[ribasso] {r['fascia']} ({r['dal_massimo'] * 100:.1f}% sotto il massimo del {r['data_massimo']})")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
