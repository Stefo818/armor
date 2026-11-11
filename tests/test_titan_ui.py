import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import titan_ui as tu  # noqa: E402


def test_titan_ui(tmp_path, monkeypatch):
    prev = {n: {"calo": c, "rialzo": r, "soglia_calo": s, "data": "x"} for n, c, r, s in
            (("1 settimana", 0.11, 0.55, 0.05), ("1 mese", 0.06, 0.73, 0.10), ("3 mesi", 0.2, 0.6, 0.1), ("6 mesi", 0.3, 0.6, 0.1), ("12 mesi", 0.44, 0.45, 0.1))}
    d = {"data": str(date.today()), "armor_index": 42.7, "super_armor": 43.8, "pilastri": {f"p{i}": 40.0 + i for i in range(1, 7)}, "previsioni": prev}
    (tmp_path / "titan.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(tu, "DATA", tmp_path)
    h = tu.html()
    assert "motore Titan" in h and h.count("class='pvc ") == 5 and "Credito" in h and "42,7" in h and "molto alto" in h
    (tmp_path / "titan.json").write_text(json.dumps({**d, "data": "2020-01-01"}), encoding="utf-8")
    assert tu.html() == ""


def test_titan_bilancio(tmp_path, monkeypatch):
    prev = {n: {"calo": c, "rialzo": r, "soglia_calo": s, "normale": b, "data": "x"} for n, c, r, s, b in
            (("1 settimana", 0.04, 0.55, 0.05, 0.06), ("1 mese", 0.03, 0.73, 0.10, 0.05), ("3 mesi", 0.07, 0.6, 0.1, 0.15), ("6 mesi", 0.14, 0.6, 0.1, 0.25), ("12 mesi", 0.2, 0.5, 0.1, 0.3))}
    d = {"data": str(date.today()), "armor_index": 42.7, "super_armor": 43.8, "pilastri": {}, "previsioni": prev}
    (tmp_path / "titan.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(tu, "DATA", tmp_path)
    h = tu.bilancio_html()
    assert "più basso del solito" in h and h.count("class='bal'") == 5 and "Titan" in h
    for x in prev.values():
        x.pop("normale")
    (tmp_path / "titan.json").write_text(json.dumps({**d, "previsioni": prev}), encoding="utf-8")
    assert "Titan" in tu.bilancio_html()   # senza il dato «normale» (vecchio file) la scheda funziona lo stesso
