# -*- coding: utf-8 -*-
"""Crescita in tempo reale (PROTOCOLLO_MINIMI.md, parte H): GDPNow della Fed di Atlanta, la sua accuratezza e un semaforo di crescita. File: data/crescita.json."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "crescita.json"


def trimestre(d: pd.Timestamp) -> str:
    return f"{d.year} T{(d.month - 1) // 3 + 1}"


def prova(now: pd.Series, act: pd.Series) -> dict:
    """Errore di GDPNow contro il metodo ingenuo (crescita del trimestre prima), trimestri già pubblicati."""
    d = pd.concat([now.rename("now"), act.rename("act"), act.shift(1).rename("prev")], axis=1).dropna()
    if len(d) < 8:
        return {"n": int(len(d))}

    def blocco(x: pd.DataFrame) -> dict:
        e1, e2 = (x["now"] - x["act"]).abs(), (x["prev"] - x["act"]).abs()
        return {"n": int(len(x)), "mae_now": round(float(e1.mean()), 2), "mae_ingenuo": round(float(e2.mean()), 2), "segno": round(float((np.sign(x["now"]) == np.sign(x["act"])).mean()), 3),
                "utile": bool(e1.mean() < e2.mean())}
    ex = d[~((d.index >= "2020-01-01") & (d.index < "2021-01-01"))]
    return {"tutto": blocco(d), "senza_2020": blocco(ex)}


def semaforo(stima: float | None, sahm: float | None, rec: float | None) -> dict:
    """Regole fisse del protocollo."""
    motivi = []
    if stima is None:
        return {"colore": "giallo", "motivi": ["stima non disponibile"]}
    rosso = stima < 0 or (sahm is not None and sahm >= 0.5) or (rec is not None and rec >= 40)
    verde = stima >= 1.5 and (sahm is None or sahm < 0.3) and (rec is None or rec < 20)
    if stima < 0:
        motivi.append("la stima di crescita è negativa")
    if sahm is not None and sahm >= 0.5:
        motivi.append("l'indicatore di Sahm segnala recessione")
    if rec is not None and rec >= 40:
        motivi.append(f"probabilità di recessione {rec:.0f}%")
    if rosso:
        return {"colore": "rosso", "motivi": motivi}
    if verde:
        return {"colore": "verde", "motivi": ["crescita stimata solida, nessun segnale di recessione"]}
    if stima < 1.5:
        motivi.append("crescita stimata sotto l'1,5%")
    if sahm is not None and sahm >= 0.3:
        motivi.append("l'indicatore di Sahm sale")
    if rec is not None and rec >= 20:
        motivi.append(f"probabilità di recessione {rec:.0f}%")
    return {"colore": "giallo", "motivi": motivi or ["segnali misti"]}


def banda(x: float) -> str:
    return "contrazione" if x < 0 else ("debole" if x < 1.5 else ("moderata" if x < 3 else "forte"))


def mercato(now: pd.Series, sp: pd.Series) -> list[dict]:
    """Descrittivo: rendimento dell'S&P 500 nei 63 giorni dopo ogni trimestre, per fascia della stima finale."""
    rows = []
    for d, v in now.items():
        t = d + pd.offsets.QuarterEnd(0) + pd.Timedelta(days=30)
        pos = sp.index.searchsorted(t)
        if pos + 63 < len(sp):
            rows.append((banda(float(v)), float(sp.iloc[pos + 63] / sp.iloc[pos] - 1)))
    df = pd.DataFrame(rows, columns=["b", "r"])
    out = []
    for b in ("contrazione", "debole", "moderata", "forte"):
        x = df[df["b"] == b]["r"]
        out.append({"banda": b, "n": int(len(x)), "mediana": None if not len(x) else round(float(x.median()), 4), "positivi": None if not len(x) else round(float((x > 0).mean()), 3)})
    return out


def calcola() -> dict:
    now, act = store.load("gdpnow").dropna(), store.load("gdp_real_g").dropna()
    sp = store.load("sp500").dropna()
    sahm, rec, curva = store.load("sahm").dropna(), store.load("recprob").dropna(), store.load("t10y3m").dropna()
    ult = now.index[-1]
    stima = float(now.iloc[-1])
    prec = act[act.index < ult]
    sah = float(sahm.iloc[-1]) if len(sahm) else None
    rc = float(rec.iloc[-1]) if len(rec) else None
    sem = semaforo(stima, sah, rc)
    q = act.index.intersection(now.index)[-24:]
    storico = [[trimestre(d), round(float(now[d]), 2), round(float(act[d]), 2) if d in act.index else None] for d in now.index[-24:]]
    return {"data": str(pd.Timestamp.now().date()), "trimestre": trimestre(ult), "stima": stima, "banda": banda(stima),
            "precedente": {"trimestre": trimestre(prec.index[-1]), "valore": float(prec.iloc[-1])} if len(prec) else None,
            "semaforo": sem, "sahm": sah, "recessione": rc, "curva": float(curva.iloc[-1]) if len(curva) else None, "prova": prova(now, act), "storico": storico,
            "mercato": mercato(now, sp), "ultimo_dato": str(ult.date())}


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[crescita] {r['trimestre']}: stima {r['stima']:.1f}% ({r['banda']}), semaforo {r['semaforo']['colore']}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
