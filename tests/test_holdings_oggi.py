"""Pesi del fondo riportati a oggi con i prezzi (dati finti, nessuna rete)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import holdings  # noqa: E402


def _base():
    return {"data": "2026-11-07", "top": [["Alfa", 10.0, "AAA"], ["Beta", 5.0, "BBB"]], "sectors": [["Tecnologia", 60.0], ["Finanza", 40.0]],
            "prezzi": {"VT": 100.0, "AAA": 100.0, "BBB": 100.0, "IXN": 100.0, "IXG": 100.0}}


def test_un_titolo_che_crolla_pesa_meno():
    t, s, nota = holdings.riporta_a_oggi(_base(), {"VT": 100.0, "AAA": 40.0, "BBB": 100.0, "IXN": 50.0, "IXG": 100.0})
    assert not nota and t[0][2] == "BBB" and abs(t[1][1] - 4.0) < 1e-9 and abs(t[0][1] - 5.0) < 1e-9
    assert abs(sum(w for _, w in s) - 100) < 1e-9 and s[0][0] == "Finanza"   # tecnologia sotto, finanza davanti


def test_se_il_fondo_sale_tutti_scalano_e_senza_prezzi_restano_i_pesi_di_yahoo():
    t, _, _ = holdings.riporta_a_oggi(_base(), {"VT": 110.0, "AAA": 110.0, "BBB": 110.0, "IXN": 110.0, "IXG": 110.0})
    assert abs(t[0][1] - 10.0) < 1e-9
    t2, _, nota = holdings.riporta_a_oggi(_base(), {})
    assert nota and t2[0][1] == 10.0
