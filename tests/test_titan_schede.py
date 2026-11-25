import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import titan_schede as ts  # noqa: E402
from armor import titan_vista as tv  # noqa: E402


def _csv(tmp_path, ultimo):
    idx = pd.bdate_range(end=ultimo, periods=700)
    r = np.random.default_rng(1)
    d = pd.DataFrame({"armor_index": 40 + r.normal(0, 3, 700), "super_armor_index": 42 + r.normal(0, 3, 700)}, index=idx)
    for i in range(1, 7):
        d[f"p{i}_stress"] = 38 + r.normal(0, 6, 700)
    d.rename_axis("date").to_csv(tmp_path / "t.csv")


def test_schede_titan_fresche_e_vecchie(tmp_path, monkeypatch):
    _csv(tmp_path, pd.Timestamp.today().normalize())
    monkeypatch.setattr(ts, "FILE", tmp_path / "t.csv")
    monkeypatch.setattr(tv, "FILE", tmp_path / "t.csv")
    monkeypatch.setattr("armor.difensivita.leggi", lambda: None)
    h = ts.super_html()
    assert "Super Armor" in h and "Indice Armor" in h and h.count("class='ts-t'") >= 15 and "Finanza" in h and "Economia" in h
    assert "rischio di crollo" in h and ts.indici_html() == h   # scala tarata: 40 difficolta, 60 pericolo, 80 crollo
    assert "Super Armor" in ts.guida_html()
    _csv(tmp_path, pd.Timestamp("2020-01-10"))
    assert ts.super_html() == "" and ts.indici_html() == "" and ts.guida_html() == ""   # file vecchio: schede di prima


def test_settimo_pilastro_fondi_senza_peso(tmp_path, monkeypatch):
    _csv(tmp_path, pd.Timestamp.today().normalize())
    monkeypatch.setattr(ts, "FILE", tmp_path / "t.csv")
    monkeypatch.setattr(tv, "FILE", tmp_path / "t.csv")
    monkeypatch.setattr("armor.difensivita.leggi", lambda: {"ultimi": [20.0 + i * 0.1 for i in range(30)]})
    h = ts.super_html()
    assert h.count("class='ts-t'") >= 16 and "Fondi (difensività)" in h


def test_flash_super_armor_frasi_semplici():
    import pandas as pd
    from armor import super_armor_flash as f
    ix = pd.date_range("2025-01-01", periods=300)
    mk = lambda v: pd.Series([v] * 280 + [v + 12] * 20, index=ix)
    S = {"super": mk(50), "sa_fin": mk(50), "sa_eco": mk(50), "se_lavoro": mk(70), "se_permessi": mk(80), "sc_infl": mk(80), "sc_tassi2": mk(80)}
    r = f.flash(S, pd.Series(range(300), index=ix, dtype=float))
    assert r["frase"] and r["flash"] and len(r["flash"]) <= 10
    titoli = " ".join(a for _, a, _ in r["flash"])
    assert "L'economia si sta indebolendo" in titoli and "Inflazione e tassi alti pesano" in titoli
