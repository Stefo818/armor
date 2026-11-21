import json

from armor import modello_sistemico as ms


def test_serie_senza_futuro_e_intervalli():
    df = ms.calcola_serie()
    assert not df.empty and set(df["regime"].unique()) <= set(ms.REGIME_META)
    assert df["score_3m"].dropna().between(0, 100).all() and df["score_6m"].dropna().between(0, 100).all()
    sp = ms.store.load("sp500").dropna()
    tagliata = ms.calcola_serie(sp.iloc[:-30])
    d = tagliata.index[-1]
    assert tagliata.loc[d, "regime"] == df.loc[d, "regime"]
    assert abs(tagliata.loc[d, "score_3m"] - df.loc[d, "score_3m"]) < 0.5


def test_riferimenti_storici_e_scheda(tmp_path, monkeypatch):
    df = ms.calcola_serie()
    # valori del 13 novembre 2026 riportati nel documento tecnico e riprodotti dalla prova (scratch/sistemico_prova.py)
    assert 64.0 <= df.loc["2026-11-13", "score_3m"] <= 67.0
    monkeypatch.setattr(ms, "FILE", tmp_path / "ms.json")
    monkeypatch.setattr(ms, "STORIA", tmp_path / "ms.csv")
    r = ms.aggiorna(log=lambda *_: None)
    assert r["regime"] in ms.REGIME_META and len(r["sensori"]) == 3
    h = ms.oggi_html()
    assert "Radar di fondo" in h and "non una previsione" in h and "Indice Armor" in h
    assert r["prova"].get("etichetta") == "Non coerente"
