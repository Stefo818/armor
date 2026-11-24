import numpy as np
import pandas as pd

from armor import concentrazione as c


def _prezzi(n=800, seed=1):
    r = np.random.default_rng(seed).normal(0.0003, 0.01, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2000-01-03", periods=n))


def test_inizi_episodi_raggruppa_per_distanza():
    s = pd.Series(False, index=pd.bdate_range("2000-01-03", periods=600))
    s.iloc[[10, 11, 12, 50, 400, 401]] = True
    assert c.inizi_episodi(s) == [10, 400]   # 50 e' a meno di 126 sedute da 12: stesso episodio


def test_episodio_carico_salita_e_calo():
    p = np.array([100.0, 105, 110, 120, 118, 100, 90, 95])
    e = c.episodio_carico(p, 0, finestra=7)
    assert e["completo"] and e["calo_arrivato"]
    assert round(e["salita"], 2) == 0.20 and e["sedute_al_picco"] == 3 and e["sedute_al_calo"] == 5
    assert c.episodio_carico(np.array([100.0, 101, 102]), 0, finestra=50) == {"completo": False}   # finestra non finita e nessun calo: non valutabile


def test_testo_stato_margine_residuo_e_confronto():
    st = {"dal": "1990", "carico": {"episodi": 8, "valutabili": 8, "con_calo": 8, "salita_mediana": 0.11, "mesi_al_picco_mediana": 7.0, "mesi_al_calo_mediana": 9.0,
                                    "mesi_al_calo_max": 16.0, "calo_mediano": -0.14},
          "riprezzamento": {"episodi": 9, "valutabili": 9, "con_calo_8": 1, "calo_mediano": -0.047, "calo_medio": -0.054, "mesi_al_minimo_mediana": 1.0},
          "base": {"salita_mediana": 0.14, "calo10_18mesi": 0.65, "calo_mediano": -0.039, "calo8_6mesi": 0.27}}
    t = c.testo_stato("carico", st, {"variazione": 0.04})
    assert t["tipo"] == "margine" and round(t["valore"], 2) == 0.07 and "65%" in t["dettaglio"]
    assert c.testo_stato("carico", st, {"variazione": 0.30})["valore"] == 0.0   # margine finito: non diventa negativo
    r = c.testo_stato("riprezzamento", st, None)
    assert r["tipo"] == "calo" and "piccola" in r["dettaglio"]
    assert c.testo_stato("calmo", st, None)["riga"] == "nessun allarme"


def test_serie_grafico_settimanale_poi_giornaliera():
    s = pd.Series(np.linspace(10, 90, 3000), index=pd.bdate_range("2012-01-02", periods=3000))
    x = c._serie_grafico(s)
    assert x["dt"][0] == 0 and len(x["dt"]) == len(x["v"]) and len(x["v"]) < len(s)


def test_tessera_nel_quadro(monkeypatch):
    from armor import quadro
    fake = {"sovraccarico": 84.0, "tendenza": 3.0, "testo": {"tipo": "margine", "riga": "margine tipico ancora +7% prima del calo", "dettaglio": "x"}}
    monkeypatch.setattr("armor.concentrazione.leggi", lambda: fake)
    h, n = quadro._tessera_sovraccarico()
    assert n == 4 and "data-gi='sovr'" in h and "84" in h and "margine tipico" in h
    monkeypatch.setattr("armor.concentrazione.leggi", lambda: None)
    assert quadro._tessera_sovraccarico() == ("", 3)


def test_analoghi_e_frasi():
    r = np.random.default_rng(3)
    idx = pd.bdate_range("1985-01-01", periods=3000)
    sp = pd.Series(100 * np.exp(np.cumsum(r.normal(0.0003, 0.01, 3000))), index=idx)
    m = pd.DataFrame({"livello": r.uniform(0, 1, 3000), "accel": r.uniform(0, 1, 3000)}, index=idx)
    a = c.analoghi(sp, m, orizzonte=60, k=100, dal="1990-01-01")
    assert a["giorni"] == 100 and a["episodi"] >= 1
    assert a["calo_max"]["med"] <= 0 <= a["salita_max"]["med"]
    assert a["calo_max"]["p25"] <= a["calo_max"]["med"] <= a["calo_max"]["p75"]
    assert "casi simili" in c.riga_analoghi(a) and "S&P 500" in c.testo_analoghi(a)
    assert c.riga_analoghi(None) == "" and c.testo_analoghi(None) == ""
