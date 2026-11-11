import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import soglie as sg  # noqa: E402


def test_soglie_zone_e_html():
    assert [sg.zona("armor", x) for x in (10, 34.9, 35, 39.9, 40, 44.9, 45, 90)] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert [sg.zona("super", x) for x in (10, 35, 44.9, 45, 54.9, 55, 99)] == [0, 1, 1, 2, 2, 3, 3]
    h = sg.html(42.7, 43.8)
    assert "Allarme" in h and "Neutro" in h and "Indice Armor" in h and "Super Armor" in h and h.count("class='sg-r'") == 2
    assert "Indice Armor" in sg.html(42.7, None) and sg.html(None, None) == ""
