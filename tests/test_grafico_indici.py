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
        assert len(r["dt"]) == len(r["v"]) and len(r["v"]) > 200


def test_html_ha_grafico_chiusura_e_gesti():
    h = grafico_indici.html()
    assert "id='gi-ov'" in h and "gi-xb" in h and "pointerdown" in h and "touch-action:none" in h
    for k in ("1S", "1M", "3M", "6M", "1A", "3A", "5A", "Max"):
        assert f"['{k}'," in h
    for t in ("Valore medio", "Ieri", "Una settimana fa", "Due settimane fa"):
        assert t in h
    json.loads(re.search(r"id='gi-dati'>(.*?)</script>", h).group(1))


def test_schede_collegate():
    assert "data-gi='crollo'" in indice_crollo.oggi_html()
    q = quadro.html()
    assert all(f"data-gi='{k}'" in q for k in ("armor", "super", "crollo"))


def test_pilastri_dentro_ogni_indice():
    d = grafico_indici.dati()
    for k in ("a_paura", "a_liquidita", "a_rimbalzo", "a_stress", "a_ciclo", "p1", "p6"):
        assert k in d, k
    assert grafico_indici.KIDS["super"][:6] == ["p1", "p2", "p3", "p4", "p5", "p6"]
    assert len(grafico_indici.KIDS["armor"]) == 5
    h = grafico_indici.html()
    assert "gi-kd" in h and "gi-bk" in h and "solo informativo" in h


def test_valutazioni_schede_e_grafico():
    from armor import grafico_indici as g
    info = g.val_info()
    assert set(info) == {"cape", "pe", "buffett"}
    for x in info.values():
        assert x["nom"] in g.VAL_NOM and x["col"] in g.VAL_COL
    h = g.val_cards()
    for k in ("cape", "pe", "buffett"):
        assert f"data-gi='{k}'" in h
    assert "gi-cfg" in g.html()


def test_spia_caro_stato():
    from armor import spia_caro
    x = spia_caro.stato()
    assert x and x["livello"] in (0, 1, 2) and x["q80"] < x["q90"]
    assert "Spia" in spia_caro.html()
