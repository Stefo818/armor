import pandas as pd

from armor import indice_crollo as ic


def test_scala_e_fasce():
    df = ic.calcola_serie()
    v = df["indice"].dropna()
    assert v.between(1, 100).all()
    # le fasce devono restare rare come nel protocollo parte 6: viola intorno al 4% dei giorni
    quota = (v > 80).mean()
    assert 0.01 <= quota <= 0.09, quota
    assert ic._fascia(20)[0] == "verde" and ic._fascia(38)[0] == "grigio"
    assert ic._fascia(50)[0] == "giallo" and ic._fascia(70)[0] == "rosso" and ic._fascia(95)[0] == "viola"


def test_nessuno_sguardo_al_futuro():
    df = ic.calcola_serie()
    sp = ic.store.load("sp500").dropna()
    tagliata = ic.calcola_serie(sp.iloc[:-30])
    d = tagliata.index[-1]
    assert abs(tagliata.loc[d, "indice"] - df.loc[d, "indice"]) < 0.5


def test_date_della_verifica():
    """Valori verificati in ESITO_INDICE_CROLLO.md: al massimo era basso, poi sale."""
    df = ic.calcola_serie()
    assert df.loc[pd.Timestamp("2026-10-06"), "indice"] < 35      # al massimo: verde
    assert 60 < df.loc[pd.Timestamp("2026-11-18"), "indice"] <= 80  # vigilia del crollo: rosso
    assert df.loc[pd.Timestamp("2026-11-05"), "indice"] > 60        # falso allarme: anche lui rosso


def test_situazione_cambia_con_la_discesa():
    a = ic.situazione(70, -1.0)
    b = ic.situazione(70, -4.0)
    c = ic.situazione(70, -12.0)
    assert a["zona"] == "vicino ai massimi" and b["zona"] == "già scivolato" and c["zona"] == "in correzione"
    assert b["prob"] == 28.0 and c["prob"] == 33.0
    assert "rimbalzo" in c["usare"]


def test_scheda(tmp_path, monkeypatch):
    monkeypatch.setattr(ic, "FILE", tmp_path / "ic.json")
    monkeypatch.setattr(ic, "STORIA", tmp_path / "ic.csv")
    r = ic.aggiorna(log=lambda *_: None)
    assert r["etichetta"] == "Non coerente" and r["fascia"] in {f[1] for f in ic.FASCE}
    h = ic.oggi_html()
    assert "Indice crollo" in h and "non che devi vendere" in h or "rimbalzo" in h
    assert "229 periodi" in h and "termometro" in h
    # la regola di onesta' della parte 8: mai «molto probabile»
    assert "molto probabile" not in h


def test_settore_piu_rotto():
    """Emendamento 3: il settore piu' rotto e' descrizione, non previsione."""
    df = ic.calcola_serie()
    u = df.dropna(subset=["settore_giu"]).iloc[-1]
    assert -100 < float(u["settore_giu"]) <= 0
    assert u["settore_quale"] in ic.SETTORI
    # oggi la tecnologia e' il settore piu' rotto, verificato in ESITO_INDICE_CROLLO.md
    assert ic.SETTORI[u["settore_quale"]] == "tecnologia"


def test_riga_settore_dichiara_i_limiti():
    d = {"settore": {"nome": "tecnologia", "giu": -26.0, "rotto": True}, "sotto_massimo": -2.0, "indice": 50}
    h = ic._settore_html(d)
    assert "42%" in h and "2015" in h and "quarto tentativo" in h
    d2 = dict(d, sotto_massimo=-12.0)
    assert "correzione iniziata" in ic._settore_html(d2)
    d3 = {"settore": {"nome": "energia", "giu": -8.0, "rotto": False}, "sotto_massimo": -1.0, "indice": 20}
    assert "Nessun settore è rotto" in ic._settore_html(d3)
