"""Dati per i grafici interattivi (data.json): ogni indicatore con storico compatto + prezzi intraday."""
import json

import numpy as np
import pandas as pd

from . import live as livemod
from . import store
from .config import DATA

EXTRA_LABELS = {
    "vwce": ("VWCE (€)", 2), "sp500": ("S&P 500", 0), "sp_fut": ("Futures S&P 500", 0), "vix": ("VIX", 2),
    "eurusd": ("Cambio EUR/USD", 4), "vt": ("VT (azioni mondiali, $)", 2), "ndx": ("Nasdaq 100", 0), "nasdaq100": ("Nasdaq 100", 0),
    "val_pe_vwce": ("P/E VWCE (mercato mondiale)", 1), "val_ps_vwce": ("Prezzo/fatturato VWCE", 2),
    "val_pe_sp500": ("P/E S&P 500 (fondo)", 1), "val_ps_sp500": ("Prezzo/fatturato S&P 500 (fondo)", 2),
    "val_pe_ndx": ("P/E Nasdaq 100", 1), "val_ps_ndx": ("Prezzo/fatturato Nasdaq 100", 2),
    "risk_10g": ("Probabilità di calo ≥5% a 10 giorni (%)", 1), "risk_1m": ("Probabilità di calo ≥10% a 1 mese (%)", 1),
    "risk_3m": ("Probabilità di calo ≥10% a 3 mesi (%)", 1), "risk_6m": ("Probabilità di calo ≥10% a 6 mesi (%)", 1),
}


def compact(s: pd.Series, daily_years: int = 6) -> pd.Series:
    """Ultimi anni giornalieri, prima settimanali: resta leggero ma il 'max' arriva fino all'inizio."""
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if s.empty:
        return s
    cut = s.index[-1] - pd.DateOffset(years=daily_years)
    old = s[s.index < cut]
    if len(old) > 400:
        old = old.resample("W").last().dropna()
    return pd.concat([old, s[s.index >= cut]])


def ser_payload(s: pd.Series, dec: int) -> dict:
    s = compact(s)
    return {"d": [int(t.value // 86_400_000_000_000) for t in s.index], "v": [round(float(v), dec + 2) for v in s.values]}


def build(indicators: list, vwce: pd.Series, sp: pd.Series, indicator_series) -> dict:
    """indicators = lista INDICATORS di report; indicator_series = funzione che restituisce la serie."""
    out = {}
    for _group, items in indicators:
        for label, key, _bad, dec in items:
            try:
                s = indicator_series(key, sp, sp)
            except Exception:  # noqa: BLE001
                continue
            if s is None or len(s) < 5:
                continue
            d = 1 if dec == "pct" else int(dec)
            out[key] = {"l": label, "dec": d, **ser_payload(s, d)}
    for key, (lab, dec) in EXTRA_LABELS.items():
        if key in out:
            continue
        s = {"vwce": vwce}.get(key)
        if s is None and key.startswith("risk_"):
            h = pd.read_csv(DATA / "risk_history.csv") if (DATA / "risk_history.csv").exists() else pd.DataFrame()
            col = "p_" + key[5:]
            if col in h:
                s = pd.Series((h[col] * 100).values, index=pd.to_datetime(h["date"]))
        if s is None:
            s = store.load(key)
        if s is not None and len(s) >= 2:
            out[key] = {"l": lab, "dec": dec, **ser_payload(s, dec)}
    intra = livemod.load_intraday()
    for key, v in intra.items():
        if key in out:
            out[key]["i"] = v
        elif key in EXTRA_LABELS:
            lab, dec = EXTRA_LABELS[key]
            out[key] = {"l": lab, "dec": dec, "d": [], "v": [], "i": v}
    return out


def write(path, data: dict) -> None:
    """Scrive un file per ogni serie (series/<chiave>.json, caricato solo quando si apre il grafico) e un data.json minuscolo con l'indice.
    Cosi' la pagina iniziale non scarica piu' 1,4 MB di storici."""
    import re
    from datetime import datetime, timezone
    d = path.parent / "series"
    d.mkdir(parents=True, exist_ok=True)
    keep = set()
    for k, v in data.items():
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", k)
        (d / f"{name}.json").write_text(json.dumps(v, separators=(",", ":")), encoding="utf-8")
        keep.add(f"{name}.json")
    for f in d.glob("*.json"):   # serie non piu' prodotte
        if f.name not in keep:
            f.unlink()
    path.write_text(json.dumps({"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "series": {k: {"l": v.get("l"), "n": len(v.get("d", []))} for k, v in data.items()}}, separators=(",", ":")), encoding="utf-8")
