# -*- coding: utf-8 -*-
"""Pagella in tempo reale (PROTOCOLLO_MINIMI.md, parte G): ogni giorno si salva il verdetto di ogni scala; quando passa il tempo si scrive se il minimo ha tenuto.
Il registro parte dal giorno in cui è stato attivato: non contiene nulla di ricostruito col senno di poi."""
import json

import numpy as np
import pandas as pd

from . import minimi
from .config import DATA

REG = DATA / "pagella_minimi.csv"
FILE = DATA / "pagella_minimi.json"
COLS = ["date", "serie", "scala", "verdetto", "q", "candidato"]
MIN_CASI = 30


def registra(o: dict | None, serie: str = "usd") -> int:
    """Aggiunge le 4 righe di oggi (una sola volta per giorno e serie). Restituisce quante righe nuove."""
    if not o:
        return 0
    try:
        reg = pd.read_csv(REG)
    except Exception:  # noqa: BLE001
        reg = pd.DataFrame(columns=COLS)
    gia = set(zip(reg["date"].astype(str), reg["serie"], reg["scala"]))
    new = [{"date": o["data"], "serie": serie, "scala": k, "verdetto": s["verdetto"], "q": round(float(s["q"]), 4), "candidato": int(bool(s["candidato"]))}
           for k, s in o["scale"].items() if (o["data"], serie, k) not in gia]
    if new:
        pd.concat([reg, pd.DataFrame(new)])[COLS].to_csv(REG, index=False)
    return len(new)


def esiti(reg: pd.DataFrame, prezzi: dict[str, pd.Series]) -> pd.DataFrame:
    """Per ogni riga con abbastanza sedute successive: il minimo ha tenuto (1) o no (0). Righe non ancora mature: NaN."""
    ris = []
    for _, r in reg.iterrows():
        p = prezzi.get(r["serie"])
        h, tol = minimi.SCALE[r["scala"]]
        e = np.nan
        if p is not None:
            pos = p.index.searchsorted(pd.Timestamp(r["date"]))
            if pos < len(p) and pos + h < len(p):
                e = float(p.iloc[pos + 1: pos + h + 1].min() / p.iloc[pos] >= 1 - tol)
        ris.append(e)
    out = reg.copy()
    out["E"] = ris
    return out


def riepilogo(reg: pd.DataFrame, prezzi: dict[str, pd.Series]) -> dict:
    if reg is None or not len(reg):
        return {"inizio": None, "giorni": 0, "serie": {}}
    d = esiti(reg, prezzi)
    res = {"inizio": str(pd.Timestamp(reg["date"].min()).date()), "giorni": int(reg["date"].nunique()), "serie": {}}
    for serie, g in d.groupby("serie"):
        sc = {}
        for k, (h, _) in minimi.SCALE.items():
            x = g[g["scala"] == k]
            ver = {}
            for v in ("probabile", "possibile", "non_ancora"):
                y = x[x["verdetto"] == v]
                m = y.dropna(subset=["E"])
                ver[v] = {"n": int(len(y)), "maturi": int(len(m)), "tenuto": _r(float(m["E"].mean())) if len(m) else None, "q_media": _r(float(m["q"].mean())) if len(m) else None}
            sc[k] = {"nome": minimi.NOMI[k], "sedute": h, "verdetti": ver, "ultimo": x["verdetto"].iloc[-1] if len(x) else None}
        res["serie"][serie] = sc
    return res


def _r(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 3)


def aggiorna(o_usd: dict | None = None, o_eur: dict | None = None, log=print) -> dict:
    o_usd = o_usd or minimi.carica_oggi("usd")
    o_eur = o_eur or minimi.carica_oggi("eur")
    n = registra(o_usd, "usd") + registra(o_eur, "eur")
    try:
        reg = pd.read_csv(REG)
    except Exception:  # noqa: BLE001
        reg = pd.DataFrame(columns=COLS)
    prezzi = {}
    for s in ("usd", "eur"):
        try:
            prezzi[s] = minimi.prezzi(s)
        except Exception:  # noqa: BLE001
            pass
    r = riepilogo(reg, prezzi)
    FILE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[pagella] {n} righe nuove; registro dal {r['inizio']}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
