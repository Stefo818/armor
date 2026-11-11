import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import pandas as pd

from armor import fasi, occasione, occasione_ui, occasione_verifica


def _serie(n=900, crollo=True):
    ix = pd.bdate_range("2015-01-01", periods=n)
    r = np.full(n, 0.0005)
    if crollo:
        r[600:640] = -0.012          # panico: circa -38% in 40 sedute
        r[640:700] = 0.006           # ripresa
    sp = pd.Series(100 * np.cumprod(1 + r), index=ix)
    vix = pd.Series(15.0, index=ix)
    if crollo:
        vix.iloc[600:640] = np.linspace(20, 60, 40)
        vix.iloc[640:700] = np.linspace(55, 18, 60)
    return {"sp": sp, "vix": vix, "vix3m": vix * 0 + 20, "baa10y": pd.Series(2.0, index=ix), "settori": {}}


def test_occasione_panico_poi_svolta():
    d = occasione.calcola(_serie())
    assert d["occasione"].iloc[:590].max() < 30                      # prima del crollo: nessuna occasione
    assert (d["stato"].iloc[615:640] == "coltello").any()            # durante la discesa: coltello che cade
    assert d["occasione"].iloc[645:700].max() >= 50                  # dopo la svolta: occasione
    primo = np.flatnonzero((d["occasione"] >= 50).values)[0]
    assert primo > 639                                                # mai prima del minimo
    assert d["stato"].iloc[-1] in ("nessun_panico", "osservazione")


def test_occasione_non_guarda_il_futuro():
    S = _serie()
    tutto = occasione.calcola(S)
    k = 650
    tagliato = occasione.calcola({"sp": S["sp"].iloc[:k], "vix": S["vix"].iloc[:k], "vix3m": S["vix3m"].iloc[:k], "baa10y": S["baa10y"].iloc[:k], "settori": {}})
    a, b = tutto["occasione"].iloc[:k].fillna(-1), tagliato["occasione"].fillna(-1)
    assert np.allclose(a.values, b.values)


def test_fasi_tendenza_e_fasce():
    S = _serie(1500, crollo=False)
    f = fasi.tendenza(S["sp"])
    assert f.iloc[-1] == "rialzo" and f.iloc[0] == "nd"
    rng = np.random.default_rng(0)
    ix = pd.bdate_range("1990-01-01", periods=3000)
    sp = pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 3000)), index=ix)
    fs = fasi.fasce(sp, pd.Series(rng.uniform(12, 30, 3000), index=ix))
    assert len(fs) == 5 and all(r["q10"] < r["q50"] < r["q90"] for r in fs)
    assert fs[0]["q90"] - fs[0]["q10"] < fs[4]["q90"] - fs[4]["q10"]    # la fascia si allarga con l'orizzonte


def test_gruppi_e_discese():
    m = np.zeros(400, bool); m[[10, 11, 12, 300]] = True
    assert occasione_verifica.gruppi(m, 126) == [10, 300]
    sp = _serie()["sp"]
    ep = occasione_verifica.discese(sp)
    assert len(ep) == 1 and ep[0][1] == 639


def test_bussola_html(monkeypatch):
    o = {"data": "2026-11-10", "occasione": 62.0, "stato": "occasione", "panico": 20.0, "panico_rec": 70.0, "svolta": 62.0, "sconto": -18.5, "sp": 6000.0, "massimo": 7360.0,
         "voci_panico": {"caduta": 60.0, "paura": 80.0, "breve": None, "credito": 40.0, "sotto": 55.0}, "voci_svolta": {"rientra": 70.0, "curva": 100.0, "cred_stop": 20.0, "risale": 60.0, "ampiezza": 60.0},
         "scaglioni": [{"calo": 10, "livello": 6624.0, "manca": 10.4}, {"calo": 20, "livello": 5888.0, "manca": -1.9}],
         "fasi": {"tendenza": "ribasso", "umore": "agitato", "agitato": True, "fasce": [{"nome": "1 mese", "sedute": 21, "soglia": 0.05, "q10": -0.09, "q50": 0.02, "q90": 0.11, "su": 0.6, "perdita": 0.2,
                  "guadagno": 0.35, "sto10": -0.045, "sto90": 0.054, "sto_su": 0.64, "n": 200, "finora": -0.07}]},
         "salute": {"mercato": {"valore": 51.0, "zona": 3, "stato": "Pericolo", "posizione": 0.9}}, "titan_calo": {"1 mese": 0.3}}
    v = {"epoche": [{"periodo": "2008-2026", "tutti": {"m12": 13.8, "pos12": 84}, "occ50": {"gruppi": 7, "m12": 19.4, "pos12": 86}}],
         "episodi": [{"massimo": "2007-10-09", "minimo": "2009-03-09", "calo": -56.8, "segnali": 5, "primo": "2008-02-26", "sedute_dal_minimo": -260, "sopra_minimo": 104.2, "discesa_dopo": -51.0}],
         "soldi": {"1990-2021": {"arrivi": 370, "rate": {"media": -2.7, "vince": 25}, "attesa": {"media": -4.3, "vince": 31}}}, "fasce": {"1 mese": {"regge": True}}}
    monkeypatch.setattr(occasione_ui, "carica", lambda: (o, v))
    h = occasione_ui.html()
    for t in ("La bussola di oggi", "Occasione", "Pericolo", "Ribasso", "da −9% a +11%", "PRIMA del minimo", "In media no", "già toccato", "10/11/2026"):
        assert t in h, t
    assert "VIX" not in h and "nan" not in h
    assert "Fase del mercato e fasce" in occasione_ui.previsioni_html()
    monkeypatch.setattr(occasione_ui, "carica", lambda: ({}, {}))
    assert occasione_ui.html() == "" and occasione_ui.previsioni_html() == ""
