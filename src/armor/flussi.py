# -*- coding: utf-8 -*-
"""Flussi e posizionamento (PROTOCOLLO_MINIMI.md, parte K): termometro di affollamento del mercato e sua prova. File: data/flussi.json."""
import json
from datetime import date

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "flussi.json"
MIN_ANNI = 3
# id serie, nome semplice, segno (+1: valore alto = mercato più affollato/compiacente), come leggerlo
INDICATORI = [("cot_lev_net", "Fondi speculativi: posizione netta sui futures", +1, "più comprati = più affollato"),
              ("margin_yoy", "Debito per comprare titoli (variazione annua)", +1, "più debito = più affollato"),
              ("mmf_yoy", "Liquidità nei fondi monetari (variazione annua)", -1, "più liquidità che cresce = più prudenza"),
              ("skew", "Domanda di protezione dai crolli (SKEW)", +1, "indice alto = più copertura contro i crolli rari"),
              ("vix_term", "VIX contro VIX a 3 mesi", -1, "rapporto basso = poca paura immediata"),
              ("aaii_spread", "Rialzisti meno ribassisti (sondaggio AAII)", +1, "più rialzisti = più affollato")]


def _settimana(s: pd.Series) -> pd.Series:
    if s is None or not isinstance(s.index, pd.DatetimeIndex) or not len(s.dropna()):
        return pd.Series(dtype=float)
    return s.dropna().resample("W-FRI").last().ffill()


def serie_base() -> dict[str, pd.Series]:
    out = {}
    out["cot_lev_net"] = _settimana(store.load("cot_lev_net"))
    mg = store.load("margin_yoy").dropna()
    out["margin_yoy"] = _settimana(mg.shift(1, freq="MS") if len(mg) else mg)   # dato mensile pubblicato con circa un mese di ritardo
    mm = store.load("mmf_assets").dropna()
    out["mmf_yoy"] = _settimana(mm.resample("W-FRI").last().ffill().pct_change(52) * 100)
    out["skew"] = _settimana(store.load("skew"))
    v, v3 = store.load("vix").dropna(), store.load("vix3m").dropna()
    out["vix_term"] = _settimana((v / v3.reindex(v.index, method="ffill")).dropna())
    out["aaii_spread"] = _settimana(store.load("aaii_spread"))
    return {k: s for k, s in out.items() if len(s)}


def percentile(s: pd.Series, anni: int = MIN_ANNI) -> pd.Series:
    """Percentile della storia nota fino a quella data (finestra espandibile, minimo `anni` anni di settimane)."""
    v = s.values
    out = np.full(len(v), np.nan)
    n0 = 52 * anni
    for i in range(n0, len(v)):
        w = v[: i + 1]
        out[i] = float((w[:-1] < w[-1]).mean() + 0.5 * (w[:-1] == w[-1]).mean())
    return pd.Series(out, index=s.index)


def termometro(base: dict[str, pd.Series] | None = None, oggi: date | None = None) -> pd.DataFrame:
    base = serie_base() if base is None else base
    oggi = pd.Timestamp(oggi or date.today())
    cols = {}
    fine = max((x.index[-1] for x in base.values() if len(x)), default=oggi)
    idx = pd.date_range(min(x.index[0] for x in base.values()), fine, freq="W-FRI")
    for k, nome, sg, _ in INDICATORI:
        s = base.get(k)
        if s is None or not len(s):
            continue
        if k == "aaii_spread" and (oggi - s.index[-1]).days > 28:      # file manuale: si usa solo se aggiornato
            continue
        p = percentile(s).reindex(idx).ffill(limit=10)    # un dato più vecchio resta valido per al massimo 10 settimane
        cols[k] = p if sg > 0 else 1 - p
    d = pd.DataFrame(cols)
    d["n"] = d.notna().sum(axis=1)
    d["termometro"] = d.drop(columns="n").mean(axis=1).where(d["n"] >= 3)
    return d


def _ic_differenza(ev_a: np.ndarray, ev_b: np.ndarray, blocco: int = 13, n: int = 2000, seed: int = 7) -> list[float]:
    """Intervallo al 90% della differenza di frequenza (A meno B) con blocchi di 13 settimane."""
    rng = np.random.default_rng(seed)
    out = []

    def bs(x: np.ndarray) -> float:
        m = len(x)
        k = max(m // blocco, 1)
        idx = (rng.integers(0, max(m - blocco, 1), k)[:, None] + np.arange(blocco)[None, :]).ravel()
        return float(x[np.clip(idx, 0, m - 1)].mean())
    for _ in range(n):
        out.append(bs(ev_a) - bs(ev_b))
    return [round(float(np.quantile(out, .05)), 3), round(float(np.quantile(out, .95)), 3)]


def prova(t: pd.DataFrame, p: pd.Series) -> dict:
    """Dal 2011: per fasce del termometro, rendimento a 3 mesi e frequenza di un calo ulteriore oltre 7% in 63 sedute."""
    from . import ribasso
    x = t["termometro"].dropna()
    x = x[x.index >= "2011-01-01"]
    pos = p.index.searchsorted(x.index, side="right") - 1
    ok = (pos >= 0) & (pos + 63 < len(p))
    x, pos = x[ok], pos[ok]
    px = p.values
    fut = (px[pos + 63] / px[pos] - 1)
    calo = ribasso._calo_ulteriore(p, 63).values[pos]
    d = pd.DataFrame({"t": x.values, "r": fut, "calo7": (calo > 0.07).astype(float)}, index=x.index)
    out = {"n": int(len(d)), "da": str(d.index[0].date()) if len(d) else None, "fasce": []}
    for nome, lo, hi in (("sotto il 20%", 0, .2), ("tra 20% e 80%", .2, .8), ("sopra l'80%", .8, 1.01)):
        z = d[(d["t"] >= lo) & (d["t"] < hi)]
        out["fasce"].append({"fascia": nome, "n": int(len(z)), "r63_med": None if not len(z) else round(float(z["r"].median()), 4), "p_calo7": None if not len(z) else round(float(z["calo7"].mean()), 3)})
    lo_, hi_ = d[d["t"] < .2]["calo7"].values, d[d["t"] >= .8]["calo7"].values
    if len(lo_) >= 20 and len(hi_) >= 20:
        ic = _ic_differenza(hi_, lo_)
        out["differenza"] = round(float(hi_.mean() - lo_.mean()), 3)
        out["ic90"] = ic
        out["utile"] = bool(ic[0] > 0)
    else:
        out["utile"] = False
    return out


def storia_termometro(t: pd.DataFrame) -> list:
    s = t["termometro"].dropna()
    s = s[s.index >= "2011-01-01"]
    return [[str(d.date()), round(float(v), 3)] for d, v in s.iloc[::2].items()]


def calcola() -> dict:
    from .features import closed_sp500
    p = closed_sp500()
    base = serie_base()
    t = termometro(base)
    ult = t.dropna(subset=["termometro"]).iloc[-1]
    ind = []
    for k, nome, sg, lettura in INDICATORI:
        if k in t.columns and not np.isnan(t[k].iloc[-1]):
            val = base[k].iloc[-1]
            ind.append({"id": k, "nome": nome, "valore": round(float(val), 2), "percentile": round(float(t[k].iloc[-1]), 3), "lettura": lettura, "segno": sg, "data": str(base[k].index[-1].date())})
    v = float(ult["termometro"])
    return {"data": str(t.dropna(subset=["termometro"]).index[-1].date()), "termometro": v, "n_indicatori": int(ult["n"]),
            "stato": "affollato" if v >= .8 else ("prudente" if v <= .2 else "neutro"), "indicatori": ind, "prova": prova(t, p), "storia": storia_termometro(t)}


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    log(f"[flussi] termometro {r['termometro'] * 100:.0f}% ({r['stato']}), {r['n_indicatori']} indicatori")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
