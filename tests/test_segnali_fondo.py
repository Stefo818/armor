# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from armor import alerts, crescita, flussi, opzioni, segnali_ui, stress, trend


def _serie(n=1500, drift=0.0004, seed=1):
    r = np.random.default_rng(seed).normal(drift, 0.01, n)
    return pd.Series(100 * np.cumprod(1 + r), index=pd.bdate_range("2015-01-01", periods=n))


def test_semaforo_regole():
    assert crescita.semaforo(-0.5, 0.1, 5)["colore"] == "rosso"
    assert crescita.semaforo(2.5, 0.1, 5)["colore"] == "verde"
    assert crescita.semaforo(0.8, 0.1, 5)["colore"] == "giallo"
    assert crescita.semaforo(2.5, 0.6, 5)["colore"] == "rosso"


def test_trend_segnali_e_strategia():
    p = _serie()
    sg = trend.segnali(p)
    assert set(["T1", "T2", "T3", "P2", "punteggio", "ok"]) <= set(sg.columns)
    assert not sg["ok"].iloc[:200].any() and sg["ok"].iloc[-1]
    cash = pd.Series(0.0, index=p.index)
    r = trend.strategia(p, sg["P2"], cash)
    assert len(r) == len(p) and r.iloc[0] == 0
    # fuori mercato con tasso zero: nessun rendimento
    r2 = trend.strategia(p, pd.Series(False, index=p.index), cash)
    assert float(r2.abs().sum()) == 0.0


def test_stress_crisi_singola():
    idx = pd.date_range("2000-01-01", "2006-12-31", freq="B")
    v = np.concatenate([np.linspace(100, 200, 300), np.linspace(200, 100, 300), np.linspace(100, 300, len(idx) - 600)])
    p = pd.Series(v, index=idx)
    c = stress.crisi_singola(p, "x", str(idx[100].date()), str(idx[700].date()), "usd")
    assert abs(c["calo"] - 0.5) < 0.02 and c["recupero"] is not None and c["traiettoria"][0][1] == 0


def test_flussi_percentile_e_termometro():
    s = pd.Series(np.arange(300, dtype=float), index=pd.date_range("2015-01-01", periods=300, freq="W-FRI"))
    pc = flussi.percentile(s)
    assert pc.iloc[:156].isna().all() and pc.iloc[-1] > 0.99
    t = flussi.termometro({"cot_lev_net": s, "skew": s, "vix_term": s}, oggi=s.index[-1].date())
    assert t["n"].iloc[-1] == 3 and 0.0 <= t["termometro"].iloc[-1] <= 1.0


def _catena():
    rows = []
    for k in range(90, 111):
        for tipo in "CP":
            rows.append(("2026-12-18", float(k), tipo, 1000.0 + 50 * abs(k - 100), 0.2, 30 / 365))
    return pd.DataFrame(rows, columns=["scad", "strike", "tipo", "oi", "iv", "T"])


def test_opzioni_analizza_e_diario(tmp_path, monkeypatch):
    ch = _catena()
    assert opzioni.gamma_bs(100.0, 100.0, 0.1, 0.2) > 0
    r = opzioni.analizza(ch, 100.0, 5000.0)
    assert abs(r["pc_oi"] - 1.0) < 1e-6 and r["muro_call"] >= 5000 >= r["muro_put"]
    monkeypatch.setattr(opzioni, "DIARIO", tmp_path / "d.csv")
    opzioni.registra(r, "2026-11-12")
    opzioni.registra(r, "2026-11-12")
    assert len(pd.read_csv(tmp_path / "d.csv")) == 1
    assert opzioni.verifica(pd.read_csv(tmp_path / "d.csv"), _serie())["pronto"] is False


def test_pagine_html_bilanciate():
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.n = 0
            self.neg = 0

        def handle_starttag(self, t, a):
            self.n += t == "div"

        def handle_endtag(self, t):
            if t == "div":
                self.n -= 1
                self.neg += self.n < 0
    for d in (segnali_ui.segnali_pagina(crescita.carica(), trend.carica(), flussi.carica(), opzioni.carica()), segnali_ui.stress_pagina(stress.carica())):
        p = P()
        p.feed(d)
        assert p.n == 0 and p.neg == 0
    assert "Stress test" in segnali_ui.stress_pagina(stress.carica()) or "stress" in segnali_ui.stress_pagina(stress.carica()).lower()


def test_pagine_senza_dati_non_crollano():
    assert isinstance(segnali_ui.segnali_pagina(None, None, None, None), str)
    assert isinstance(segnali_ui.stress_pagina(None), str)


def test_avvisi_trend_e_crescita():
    pred = {"1m": {"level": "basso"}}
    base = dict(pred=pred, regime=None, vix=None, event=None, move=None, today="2026-11-14")
    _, st = alerts.detect({}, **base, segnali={"t1": True, "crescita": "verde"})
    m, _ = alerts.detect(st, **base, segnali={"t1": False, "crescita": "rosso"})
    titoli = " ".join(x["title"] for x in m)
    assert "sotto la media a 200" in titoli and "semaforo rosso" in titoli
    m2, _ = alerts.detect(st, **base, segnali={"t1": True, "crescita": "verde"})
    assert not m2
