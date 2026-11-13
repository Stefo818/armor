"""Ogni dato salvato in data/series deve avere una spiegazione semplice; il glossario li mostra tutti."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import confronto, extra13, glossario_dati, glossario_serie  # noqa: E402

SERIES = Path(__file__).resolve().parents[1] / "data" / "series"


def test_nessun_dato_senza_spiegazione():
    chiavi_semplici = {v: k for k, v in confronto.SIMPLE.items()}
    mancanti = [f.stem for f in SERIES.glob("*.csv")
                if glossario_serie.scheda(f.stem) is None and glossario_serie.scheda(chiavi_semplici.get(f.stem, "")) is None]
    assert not mancanti, mancanti


def test_schede_complete_e_pagina_glossario():
    for k, d in glossario_dati.DATI.items():
        assert all(len(d[c]) > 10 for c in ("nome", "cosa", "perche", "lettura", "fonte")) or d["lettura"], k
        assert d["cosa"].endswith((".", ")")) and "  " not in d["cosa"], k
    h = extra13.glossario_html()
    assert "Tutti i dati dell'app, spiegati" in h and "Prezzi al consumo" in h and "Liquidità netta della Fed" in h
    assert h.count("class='gl gd'") >= len(glossario_dati.DATI) + 40 and "Indice Armor" in h
