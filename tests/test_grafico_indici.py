import json
import re

from armor import grafico_indici, quadro, indice_crollo


def test_dati_compatti_e_ricostruibili():
    d = grafico_indici.dati()
    assert {"armor", "super", "crollo"} <= set(d)
    for k, r in d.items():
        t = r["t0"]
        for x in r["dt"][1:]:
            assert x > 0
            t += x
        assert len(r["dt"]) == len(r["v"]) and len(r["v"]) > 500


def test_html_ha_grafico_chiusura_e_gesti():
    h = grafico_indici.html()
    assert "id='gi-ov'" in h and "gi-xb" in h and "pointerdown" in h and "touch-action:none" in h
    for k in ("1S", "1M", "3M", "6M", "1A", "3A", "5A", "Max"):
        assert f">{k}<" in h
    for t in ("Valore medio", "Ieri", "Una settimana fa", "Due settimane fa"):
        assert t in h
    json.loads(re.search(r"id='gi-dati'>(.*?)</script>", h).group(1))


def test_schede_collegate():
    assert "data-gi='crollo'" in indice_crollo.oggi_html()
    q = quadro.html()
    assert all(f"data-gi='{k}'" in q for k in ("armor", "super", "crollo"))
