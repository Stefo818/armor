# -*- coding: utf-8 -*-
"""Calcolo giornaliero del motore Titan v47: scrive data/titan.json (oggi) e data/titan_storia.csv (storia).
Usa solo l'archivio dell'app (data/series) + data/series_storia: niente file del PC.
Grandi fondi: margin debt FINRA e posizioni CFTC dei gestori se presenti nell'archivio; DIX/GEX e AAII non ci sono
(AAII per licenza resta solo sul PC): in quel caso quei termini valgono zero e il resto del motore non cambia."""
import json

import pandas as pd

from . import store, titan, titan_dati
from .config import DATA

OUT_JSON = DATA / "titan.json"
OUT_CSV = DATA / "titan_storia.csv"


def _asof(s: pd.Series, idx: pd.DatetimeIndex, lag: int) -> pd.Series:
    s = s.dropna().copy()
    if s.empty:
        return pd.Series(float("nan"), index=idx)
    s.index = s.index + pd.Timedelta(days=lag)          # data in cui il dato era davvero noto
    return s.reindex(s.index.union(idx)).ffill().reindex(idx).where(lambda x: x.index >= s.index[0])


def costruisci() -> pd.DataFrame:
    S = titan_dati.raw_da_archivio()
    base = titan.build_features(titan.market_stage(S))
    ix = base.index
    for col, sid in (("vol_vix9d", "vix9d"), ("vol_vix6m", "vix6m"), ("vol_move", "move"), ("cred_cur", "t10y3m"), ("cred_baa", "baa10y")):
        base[col] = _asof(store.load(sid), ix, 0)
    base["finra_margin"] = _asof(store.load("margin_debt"), ix, 45)
    base["cftc_sp_inst"] = _asof(store.load("cot_am_net"), ix, 4)
    return titan.build_titan(base)


def calcola() -> dict:
    df = costruisci()
    ult = df.iloc[-1]
    pil = {f"p{i}": round(float(ult[f"p{i}_stress"]), 1) for i in range(1, 7)}
    return {"data": str(df.index[-1].date()), "armor_index": round(float(ult["armor_index"]), 1),
            "super_armor": round(float(ult["super_armor_index"]), 1), "radar_decennio": round(float(ult["lost_decade_radar"]), 1),
            "pilastri": pil, "previsioni": titan.previsioni_oggi(df), "versione": "titan-v47"}, df


def esegui() -> dict:
    oggi, df = calcola()
    OUT_JSON.write_text(json.dumps(oggi, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["armor_index", "super_armor_index", "lost_decade_radar"] + [f"p{i}_stress" for i in range(1, 7)]
    out = df.loc["1990-01-01":, cols].round(2)
    out.index.name = "date"
    out.to_csv(OUT_CSV)
    return oggi
