# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from armor import segnali_ui, terreno


def test_ritardo_di_pubblicazione():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2020-01-01", "2020-04-01", "2020-07-01"]))
    g = pd.date_range("2020-01-31", "2020-12-31", freq="ME")
    m = terreno.pannello_var(s, 2, "lvl", g)
    assert np.isnan(m["2020-02-29"])          # il dato del 1/1 con ritardo 2 mesi esiste solo dal 1/3
    assert m["2020-03-31"] == 1.0 and m["2020-05-31"] == 1.0 and m["2020-06-30"] == 2.0   # 2.0 (1/4) visibile da 1/6


def test_zscore_senza_futuro():
    rng = np.random.default_rng(0)
    m = pd.Series(rng.normal(size=200), index=pd.date_range("2000-01-31", periods=200, freq="ME"))
    z1 = terreno.zscore(m)
    m2 = m.copy(); m2.iloc[150:] += 50          # cambio il futuro
    z2 = terreno.zscore(m2)
    assert np.allclose(z1.iloc[:150].dropna(), z2.iloc[:150].dropna())
    assert z1.iloc[:47].isna().all()            # servono 48 mesi di storia


def test_parola_e_segno():
    assert terreno.parola(1.4)[1] == "b" and terreno.parola(0.0)[0] == "nella norma" and terreno.parola(-1)[1] == "ok"
    assert terreno.parola(None)[0] == "dato non disponibile"
    assert terreno.VARS["risparmio" if "risparmio" in terreno.VARS else "psavert"][1] == -1   # meno risparmio = più fragile


def test_calcola_e_pagina():
    idx = pd.date_range("1985-01-01", "2026-10-01", freq="MS")
    rng = np.random.default_rng(1)
    serie = {k: pd.Series(np.cumsum(rng.normal(size=len(idx))), index=idx) for k in terreno.VARS}
    r = terreno.calcola(serie, oggi="2026-11-18")
    assert r["data"] == "2026-10-31" and len(r["gruppi"]) == 5 and 0 <= r["percentile"] <= 100
    html = segnali_ui.terreno_html(dict(r, prova={"auc": {"6 mesi": {"taratura": 0.83, "conferma": 0.49}, "12 mesi": {"taratura": 0.85, "conferma": 0.47}}}))
    assert "non utile per prevedere" in html and "Credito" in html
    assert isinstance(segnali_ui.terreno_html(None), str)
    assert isinstance(segnali_ui.segnali_pagina(None, None, None, None, ter=r), str)


def test_registro_una_riga_per_mese(tmp_path):
    r = {"data": "2026-10-31", "terreno": 0.1, "gruppi": [{"g": g, "z": 0.2} for g in terreno.GRUPPI]}
    f = tmp_path / "reg.csv"
    assert terreno.registra(r, f) is True and terreno.registra(r, f) is False
    assert len(pd.read_csv(f)) == 1
    assert terreno.registra(dict(r, data="2026-11-30"), f) is True and len(pd.read_csv(f)) == 2


# ---- Crisi lente ----
import json
from pathlib import Path

from armor import crisi_lente


def test_crisi_lente_riferimenti_storici_non_cambiano():
    """Il punteggio calcolato oggi sulle serie dell'archivio, a date passate, coincide con quello delle prove (scratch/crisi_lente_risultati.json)."""
    R = json.loads((Path(__file__).resolve().parents[1] / "scratch" / "crisi_lente_risultati.json").read_text(encoding="utf-8"))
    Z, G, T = crisi_lente.punteggio(crisi_lente.serie_base(), "2026-12-31")
    for d, v in R["riferimenti"].items():
        assert abs(float(T.loc[pd.Timestamp(d).to_period("M").to_timestamp("M")]) - v) < 0.02, d


def test_crisi_lente_senza_futuro_e_registro(tmp_path):
    base = crisi_lente.serie_base()
    Z, G, T1 = crisi_lente.punteggio(base, "2010-12-31")
    base2 = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in base.items()}
    for k, v in base2.items():
        if len(v):
            v.loc[v.index >= "2011-01-01"] = v.loc[v.index >= "2011-01-01"] * 3 + 5   # cambio solo il futuro
    Z, G, T2 = crisi_lente.punteggio(base2, "2010-12-31")
    assert np.allclose(T1.loc[:"2010-12-31"].dropna(), T2.loc[:"2010-12-31"].dropna())
    r = {"data": "2026-10-31", "terreno": 0.5, "percentile": 70.0, "allarme": False, "gruppi": [{"g": g, "z": 0.1} for g in crisi_lente.GRUPPI]}
    f = tmp_path / "r.csv"
    assert crisi_lente.registra(r, f) and not crisi_lente.registra(r, f)


def test_crisi_lente_pagina():
    r = crisi_lente.calcola(oggi="2026-11-18")
    assert r["data"] == "2026-10-31" and len(r["gruppi"]) == 4 and 0 <= r["percentile"] <= 100
    r["prova"] = json.loads((Path(__file__).resolve().parents[1] / "data" / "crisi_lente_prova.json").read_text(encoding="utf-8"))
    h = segnali_ui.crisi_lente_html(r)
    assert "prova non superata" in h and "Valutazioni" in h and "Bolla internet" in h
    assert isinstance(segnali_ui.crisi_lente_html(None), str) and isinstance(segnali_ui.segnali_pagina(None, None, None, None, cl=r), str)
