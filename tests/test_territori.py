import pandas as pd

from armor import territori as t


def test_pe_percentile_espandente_senza_futuro():
    s = pd.Series(range(1, 400), index=pd.bdate_range("2000-01-03", periods=399), dtype=float)
    p = t.pe(s, minimo=252)
    assert p.iloc[:251].isna().all() and p.iloc[-1] == 1.0
    s2 = s.copy(); s2.iloc[-1] = -5.0       # cambiare l'ultimo valore non cambia i percentili passati
    assert t.pe(s2, minimo=252).iloc[:-1].equals(p.iloc[:-1])


def test_meccanismi_caldo_e_stati():
    cal = pd.bdate_range("2000-01-03", periods=5)
    I = pd.DataFrame({k: [0.5] * 5 for k in t.ORDINE}, index=cal)
    I.loc[cal[-1], ["M1", "M0", "M4", "M2"]] = 0.9
    caldo = (I >= t.SOGLIA) & I.notna()
    st = t.stati(caldo, I)
    assert st["K4 almeno 4 meccanismi caldi"].iloc[-1] and not st["K4 almeno 4 meccanismi caldi"].iloc[0]
    assert st["BOLLA: prezzi da bolla e concentrazione"].iloc[-1] and st["DRENAGGIO: obbligazioni + leva o credito"].iloc[-1]
    assert not st["LEVA: leva e credito"].iloc[-1]


def test_striscia_html_non_e_un_avviso(monkeypatch):
    d = {"K": 1, "frase": "x", "meccanismi": {k: {"nome": t.MECC[k][0], "spiega": "s", "indice": 0.9 if k == "M1" else 0.4, "caldo": k == "M1"} for k in t.ORDINE}}
    monkeypatch.setattr(t, "leggi", lambda: d)
    h = t.striscia_html()
    assert "1 su 7 accese" in h and "non è un avviso" in h and "crollo probabile" not in h
