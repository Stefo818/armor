# -*- coding: utf-8 -*-
"""Trend e momentum (PROTOCOLLO_MINIMI.md, parte J): tre segnali sull'S&P 500, la loro prova contro «comprare e tenere» e lo stato di oggi. File: data/trend.json."""
import json

import numpy as np
import pandas as pd

from . import ribasso, store
from .config import DATA

FILE = DATA / "trend.json"
META = "1977-12-31"
NOMI = {"T1": "Prezzo sopra la media a 200 giorni", "T2": "Momentum positivo (12 mesi meno l'ultimo)", "T3": "Media a 50 giorni sopra quella a 200", "P2": "Almeno 2 segnali su 3"}


def segnali(p: pd.Series) -> pd.DataFrame:
    sma200, sma50 = p.rolling(200).mean(), p.rolling(50).mean()
    mom = p.shift(21) / p.shift(252) - 1
    d = pd.DataFrame({"T1": p > sma200, "T2": mom > 0, "T3": sma50 > sma200})
    ok = sma200.notna() & mom.notna()
    d = d.where(ok, False).astype(bool)
    d["punteggio"] = d[["T1", "T2", "T3"]].sum(axis=1)
    d["P2"] = d["punteggio"] >= 2
    d.loc[~ok, ["P2"]] = False
    d["ok"] = ok
    return d


def cash_giornaliero(idx: pd.DatetimeIndex) -> pd.Series:
    t = store.load("tb3ms").dropna().reindex(idx, method="ffill").fillna(0.0) / 100.0
    return t / 252.0


def strategia(p: pd.Series, sig: pd.Series, cash: pd.Series) -> pd.Series:
    """Rendimenti giornalieri: segnale di ieri applicato a oggi; fuori mercato si prende il tasso a 3 mesi."""
    r = p.pct_change().fillna(0.0)
    pos = sig.shift(1).fillna(False).astype(float)
    return pos * r + (1 - pos) * cash


def misure(r: pd.Series, pos: pd.Series | None = None) -> dict:
    if len(r) < 252:
        return {}
    cum = (1 + r).cumprod()
    anni = len(r) / 252.0
    dd = float((1 - cum / cum.cummax()).max())
    out = {"rend_annuo": round(float(cum.iloc[-1] ** (1 / anni) - 1), 4), "calo_max": round(dd, 4), "volatilita": round(float(r.std() * np.sqrt(252)), 4)}
    if pos is not None:
        out["tempo_investito"] = round(float(pos.mean()), 3)
        out["cambi_anno"] = round(float((pos.astype(int).diff().abs() > 0).sum() / anni), 1)
    return out


def prova(p: pd.Series, sg: pd.DataFrame, cash: pd.Series) -> dict:
    ok = sg["ok"]
    p, sg, cash = p[ok], sg[ok], cash[ok]
    bh = p.pct_change().fillna(0.0)
    res = {"periodi": {"tutto": [str(p.index[0].date()), str(p.index[-1].date())], "prima": [str(p.index[0].date()), META], "dopo": ["1978-01-01", str(p.index[-1].date())]}, "strategie": {}, "compra_e_tieni": {}}
    fin = {"tutto": lambda x: x, "prima": lambda x: x[x.index <= META], "dopo": lambda x: x[x.index > META]}
    for per, f in fin.items():
        res["compra_e_tieni"][per] = misure(f(bh))
    for k in ("T1", "T2", "T3", "P2"):
        r = strategia(p, sg[k], cash)
        pos = sg[k].shift(1).fillna(False)
        m = {per: misure(f(r), f(pos)) for per, f in fin.items()}
        prot = all(m[x]["calo_max"] <= 0.75 * res["compra_e_tieni"][x]["calo_max"] for x in ("prima", "dopo"))
        rende = all(m[x]["rend_annuo"] > res["compra_e_tieni"][x]["rend_annuo"] for x in ("prima", "dopo"))
        res["strategie"][k] = {"nome": NOMI[k], "misure": m, "protegge": bool(prot), "rende_di_piu": bool(rende)}
    return res


def condizionato(p: pd.Series, sg: pd.DataFrame) -> list[dict]:
    ok = sg["ok"]
    f63, f252 = p.shift(-63) / p - 1, p.shift(-252) / p - 1
    c252 = ribasso._calo_ulteriore(p, 252)
    out = []
    for s in range(4):
        m = ok & (sg["punteggio"] == s)
        a, b, c = f63[m].dropna(), f252[m].dropna(), c252[m].dropna()
        out.append({"punteggio": s, "giorni": int(m.sum()), "r63_med": None if not len(a) else round(float(a.median()), 4), "r252_med": None if not len(b) else round(float(b.median()), 4),
                    "p_calo10": None if not len(c) else round(float((c > 0.10).mean()), 3)})
    return out


def curve(p: pd.Series, sg: pd.DataFrame, cash: pd.Series) -> dict:
    ok = sg["ok"]
    pp, ss, cc = p[ok], sg[ok], cash[ok]
    bh = (1 + pp.pct_change().fillna(0.0)).cumprod()
    st = (1 + strategia(pp, ss["P2"], cc)).cumprod()
    m = lambda s: [[str(d.date()), round(float(v), 3)] for d, v in s.resample("ME").last().dropna().items()]
    return {"compra_e_tieni": m(bh), "trend": m(st)}


def calcola(p: pd.Series | None = None) -> dict:
    if p is None:
        from .features import closed_sp500
        p = closed_sp500()
    p = p.dropna()
    sg = segnali(p)
    cash = cash_giornaliero(p.index)
    sma200, sma50 = p.rolling(200).mean(), p.rolling(50).mean()
    ult = sg.iloc[-1]
    cambi = sg["punteggio"].ne(sg["punteggio"].shift(1))
    ultimo_cambio = sg.index[cambi & sg["ok"]][-1]
    t1_cambi = sg["T1"].ne(sg["T1"].shift(1)) & sg["ok"]
    ult_t1 = sg.index[t1_cambi][-1]
    rec = p[p.index >= p.index[-1] - pd.Timedelta(days=3 * 365)]
    w = lambda s: [[str(d.date()), round(float(v), 1)] for d, v in s[s.index >= rec.index[0]].iloc[::3].items()]
    return {"data": str(p.index[-1].date()), "prezzo": float(p.iloc[-1]), "sma200": float(sma200.iloc[-1]), "sma50": float(sma50.iloc[-1]),
            "distanza_sma200": float(p.iloc[-1] / sma200.iloc[-1] - 1), "punteggio": int(ult["punteggio"]), "T1": bool(ult["T1"]), "T2": bool(ult["T2"]), "T3": bool(ult["T3"]),
            "momentum": float(p.iloc[-22] / p.iloc[-253] - 1) if len(p) > 253 else None,
            "da_giorni_punteggio": int((p.index[-1] - ultimo_cambio).days), "ultimo_incrocio_media200": {"data": str(ult_t1.date()), "sopra": bool(sg.loc[ult_t1, "T1"])},
            "prova": prova(p, sg, cash), "condizionato": condizionato(p, sg), "curve": curve(p, sg, cash),
            "recente": {"prezzo": w(p), "sma200": w(sma200), "sma50": w(sma50)}}


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    log(f"[trend] punteggio {r['punteggio']}/3, {r['distanza_sma200'] * 100:+.1f}% dalla media a 200 giorni")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
