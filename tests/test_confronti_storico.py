import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pandas as pd

from armor import parts, semafori, titan_registro


def test_confronti_semafori_conteggi_e_html():
    c = [{"id": "ieri", "testo": "rispetto a ieri", "data": "10/11", "cambiati": 4, "peggio": 3, "meglio": 1, "tot": 59, "prima": {"ok": 40, "wa": 12, "ba": 7}, "ora": {"ok": 38, "wa": 13, "ba": 8},
          "nomi_peggio": ["VIX"], "nomi_meglio": ["MOVE"]}]
    h = semafori.confronti_html(c)
    for t in ("rispetto a ieri", ">4<", "3 peggio", "1 meglio", "più tesi", "Allora: 40 verdi", "VIX", "MOVE"):
        assert t in h, t
    assert semafori.confronti_html([]) == "" and semafori.confronti_html(None) == ""
    it = [{"key": "a", "name": "A", "group": "G", "light": "ok", "value": 1, "dec": 1, "unit": "", "read": "x"}]
    assert "Quanti semafori sono cambiati" in semafori.oggi_html(it, "2026-11-11", c)


def test_colori_a_non_guarda_il_futuro(monkeypatch):
    ix = pd.date_range("2020-01-01", periods=300)
    s = pd.Series(range(300), index=ix, dtype=float)
    monkeypatch.setattr(semafori, "series_of", lambda key, sp=None: s)
    spec = semafori.SPEC[0]
    a = semafori.colori_a(s, "2020-06-01")
    b = semafori.colori_a(s, "2020-06-01", {})
    assert a == b and spec[0] in a


def test_grafico_orario_ha_sempre_un_ripiego():
    js = parts.JS
    assert "Mercato chiuso: mostro gli ultimi scambi disponibili" in js and "Dati orari non disponibili" in js
    assert "cand=range==='1h'?[x.I1,x.I10,I]" in js and "s.i&&s.i.t" in js


def test_titan_registro_serie_e_dizionario(tmp_path, monkeypatch):
    monkeypatch.setattr(titan_registro, "FILE", tmp_path / "r.csv")
    monkeypatch.setattr(titan_registro, "DATA", tmp_path)
    pd.DataFrame({"date": ["1994-01-05", "2026-11-09"], "model": ["Titan", "Titan"], "hz": ["1m", "1m"], "thr": [10, 10], "p": [0.05, 0.06]}).to_csv(tmp_path / "modelli_preds.csv", index=False)
    pd.DataFrame({"date": ["2026-11-10"], "hz": ["1m"], "calo": [0.0604], "rialzo": [0.7]}).to_csv(tmp_path / "r.csv", index=False)
    s = titan_registro.serie_hz("1m")
    assert abs(s.iloc[-1] - 6.04) < 1e-6 and abs(s.iloc[0] - 6.0) < 1e-6 and len(s) == 2
    assert titan_registro.per_data()[(pd.Timestamp("2026-11-10"), "1m")] == (0.0604, 0.7)
