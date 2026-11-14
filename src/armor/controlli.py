# -*- coding: utf-8 -*-
"""Controlli rapidi PRIMA di salvare i dati nel repository (daily.yml). Fermano il salvataggio solo per problemi gravi:
file chiave illeggibili o vuoti, diario con catena rotta. Il resto (dati vecchi) è solo segnalato."""
import json
from datetime import date

import pandas as pd

from .config import DATA

JSON_CHIAVE = ["minimi_oggi.json", "lungo_periodo.json", "ribasso.json", "status.json", "occasione.json"]
CSV_CHIAVE = ["journal_v3.csv", "ombra_modelli.csv", "pagella_minimi.csv"]
MAX_ETA = {"series/sp500.csv": 6, "series/vix.csv": 6}


def verifica(oggi: date | None = None, base=None) -> tuple[list[str], list[str]]:
    """(problemi gravi, avvisi). Funzione pura sul contenuto della cartella data."""
    base = base or DATA
    oggi = pd.Timestamp(oggi or date.today())
    gravi, avvisi = [], []
    for f in JSON_CHIAVE:
        p = base / f
        if not p.exists():
            avvisi.append(f"{f}: file assente")
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            gravi.append(f"{f}: JSON illeggibile ({type(e).__name__})")
    for f in CSV_CHIAVE:
        p = base / f
        if not p.exists():
            avvisi.append(f"{f}: file assente")
            continue
        try:
            d = pd.read_csv(p)
            if not len(d):
                gravi.append(f"{f}: file vuoto")
        except Exception as e:  # noqa: BLE001
            gravi.append(f"{f}: CSV illeggibile ({type(e).__name__})")
    for f, lim in MAX_ETA.items():
        p = base / f
        try:
            d = pd.read_csv(p, index_col=0, parse_dates=True)
            eta = (oggi - d.index[-1]).days
            if eta > lim:
                avvisi.append(f"{f}: ultimo dato di {eta} giorni fa")
        except Exception as e:  # noqa: BLE001
            gravi.append(f"{f}: illeggibile ({type(e).__name__})")
    return gravi, avvisi


def run() -> int:
    gravi, avvisi = verifica()
    for a in avvisi:
        print("[controlli] avviso:", a, flush=True)
    for g in gravi:
        print("[controlli] ERRORE:", g, flush=True)
    try:
        from . import journal3
        ok, n, err = journal3.verifica_estrema()
        print(f"[controlli] diario: {'ok' if ok else 'ROTTO'} ({n} righe)", flush=True)
        if not ok:
            gravi.append(f"diario: catena rotta alla riga {n} ({err})")
    except Exception as e:  # noqa: BLE001
        print("[controlli] diario non controllabile:", type(e).__name__, flush=True)
    print(f"[controlli] {len(gravi)} problemi gravi, {len(avvisi)} avvisi", flush=True)
    return 1 if gravi else 0
