import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import soglie as sg  # noqa: E402


def test_soglie_zone_e_html():
    # scala unica per i due indici: da 40 difficolta', da 60 pericolo, da 80 rischio di crollo
    for k in ("armor", "super"):
        assert [sg.zona(k, x) for x in (10, 39.9, 40, 59.9, 60, 79.9, 80, 99)] == [0, 0, 1, 1, 2, 2, 3, 3]
    h = sg.html(42.7, 61.8)
    assert "In difficoltà" in h and "In pericolo" in h and "Indice Armor" in h and "Super Armor" in h and h.count("sg-r' data-gi") == 2
    assert "Indice Armor" in sg.html(42.7, None) and sg.html(None, None) == ""
