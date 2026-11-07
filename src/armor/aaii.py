"""Sondaggio AAII sul sentiment degli investitori (settimanale, dal 1987).
Il file sentiment.xls si scarica da https://www.aaii.com/sentimentsurvey/sent_results ("Download Complete Historical Data").
Metti il file in D:\\Armor (stesso nome) oppure in D:\\Armor\\dati_manuali: viene importato a ogni aggiornamento."""
import io
from pathlib import Path

import pandas as pd
import requests

from . import store
from .config import ROOT

URL = "https://www.aaii.com/files/surveys/sentiment.xls"
LOCATIONS = [ROOT / "sentiment.xls", ROOT / "dati_manuali" / "sentiment.xls"]


def parse(src) -> pd.DataFrame:
    d = pd.read_excel(src, sheet_name="SENTIMENT", header=None, skiprows=5).iloc[:, :7]
    d.columns = ["date", "bull", "neutral", "bear", "total", "ma8", "spread"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date", "bull", "bear"]).drop_duplicates("date", keep="last").set_index("date").sort_index()
    return d.astype(float)


def to_series(d: pd.DataFrame) -> dict[str, pd.Series]:
    return {"aaii_bull": d["bull"] * 100, "aaii_bear": d["bear"] * 100, "aaii_spread": (d["bull"] - d["bear"]) * 100}


def fetch_aaii() -> dict[str, pd.Series]:
    """Prima un file messo a mano, poi il download diretto (AAII puo' richiedere il login: in quel caso resta l'ultimo file)."""
    for f in LOCATIONS:
        if Path(f).exists():
            return to_series(parse(f))
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (Armor personal dashboard)"}, timeout=30)
    if r.status_code != 200 or not r.content.startswith(b"\xd0\xcf\x11\xe0"):
        raise RuntimeError("AAII richiede il login: scarica sentiment.xls a mano e mettilo in D:\\Armor")
    return to_series(parse(io.BytesIO(r.content)))
