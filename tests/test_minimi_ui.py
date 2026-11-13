import json

import numpy as np
import pandas as pd

from armor import lungo_periodo, minimi, minimi_ui


def _oggi():
    sc = {}
    for k, (h, t) in minimi.SCALE.items():
        sc[k] = {"nome": minimi.NOMI[k], "sedute": h, "tolleranza": t, "dal_minimo": 0.005, "minimo_livello": 100.0, "minimo_data": "2026-11-05", "candidato": True, "q": 0.8,
                 "q_grezza": 0.8, "r50": 0.01, "r80": 0.03, "r95": 0.06, "verdetto": "probabile", "etichetta": "verificata",
                 "fasce": [{"fascia": "alta", "n": 40, "q_media": 0.8, "reale": 0.78}], "copertura80": {"tutto": 0.8}}
    return {"data": "2026-11-12", "prezzo": 7000.0, "scale": sc}


def test_verdetto_soglie():
    assert minimi.verdetto(True, 0.8) == "probabile"
    assert minimi.verdetto(True, 0.6) == "possibile"
    assert minimi.verdetto(True, 0.4) == "non_ancora"
    assert minimi.verdetto(False, 0.99) == "non_ancora"


def test_html_minimi_senza_dati_non_si_rompe():
    h = minimi_ui.html(None, None, None)
    assert "Minimi e lungo periodo" in h and "disponibili" in h


def test_html_minimi_con_dati():
    idx = pd.bdate_range("2023-01-02", periods=800)
    p = pd.Series(100 + np.cumsum(np.random.default_rng(1).normal(0, 1, len(idx))), index=idx)
    marc = {"1s": [[str(idx[300].date()), "probabile", 1], [str(idx[400].date()), "possibile", 0], [str(idx[790].date()), "probabile", None]]}
    h = minimi_ui.html(_oggi(), p, None, marc)
    assert "Minimo probabile" in h and "<svg" in h and "1 settimana" in h and "Non è un consiglio" in h


def test_lungo_periodo_fase_e_percentili():
    idx = pd.date_range("1900-01-31", periods=1200, freq="ME")
    df = pd.DataFrame({"cape": np.linspace(8, 30, len(idx))}, index=idx)
    assert lungo_periodo.fase(df, 40)["codice"] == "contrazione"
    assert lungo_periodo.fase(df, 9)["codice"] == "sana"


def test_html_lungo_con_dati_salvati():
    lp = lungo_periodo.carica()
    if lp is None:
        return
    h = minimi_ui.html(None, None, lp)
    assert "Atteso a 10 anni" in h and "decenni perduti" in h.lower()
