# -*- coding: utf-8 -*-
from datetime import datetime, timezone

import numpy as np

from armor import ore, ore_ui


def _t(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M", ).replace(tzinfo=timezone.utc)


def test_gap_equo_segno_e_misura():
    assert abs(ore.gap_equo(100, 99.0, 100.0, 1.10, 1.10) - ore.BETA_ES * -0.01) < 1e-9       # futures -1% -> VWCE circa -0,83%
    assert ore.gap_equo(100, 100.0, 100.0, 1.12, 1.10) < 0                                      # euro più forte -> VWCE in euro più basso
    assert ore.gap_equo(100, 100.0, 100.0, 1.10, 1.10) == 0


def test_quota_varianza_notte_e_fine_settimana():
    assert 0.05 < ore.quota_varianza(_t("2026-11-17 18:00"), 3) < 0.35
    assert ore.quota_varianza(_t("2026-11-14 10:00"), 6) == 0.0       # sabato: futures fermi
    tot = ore.quota_varianza(_t("2026-11-17 00:00"), 24)
    assert 0.9 < tot < 1.05                                          # un giorno intero ≈ 100% della varianza


def _prev(gap_es=0.0, aperto=False, vix=22.0, ev=None):
    t0 = _t("2026-11-16 21:15")
    v = {"prezzo": 100.0, "ora": _t("2026-11-16 16:30"), "aperto": aperto}
    m = {"es_ora": 100.0 * (1 + gap_es), "es_ancora": 100.0, "fx_ora": 1.10, "fx_ancora": 1.10, "vix": vix}
    return t0, ore.previsione(t0, v, m, ev or [], sims=6000, seed=3)


def test_previsione_sposta_gli_intervalli_col_salto():
    _, a = _prev(0.0)
    _, b = _prev(-0.012)
    assert abs(a["gap"]) < 1e-9 and b["gap"] < -0.009
    for k in ore.ORIZZONTI:
        assert b["orizzonti"][k]["mediana"] < a["orizzonti"][k]["mediana"] - 0.006
        assert b["orizzonti"][k]["p_meno1"] > a["orizzonti"][k]["p_meno1"]
        o = a["orizzonti"][k]
        assert o["p10"] < o["mediana"] < o["p90"]
    # più paura = intervalli più larghi
    _, c = _prev(0.0, vix=40.0)
    assert c["orizzonti"]["6 ore"]["p90"] - c["orizzonti"]["6 ore"]["p10"] > a["orizzonti"]["6 ore"]["p90"] - a["orizzonti"]["6 ore"]["p10"]


def test_mercato_aperto_nessun_salto():
    _, r = _prev(-0.02, aperto=True)
    assert r["gap"] == 0.0


def test_evento_allarga_solo_se_dentro_la_finestra():
    t0 = _t("2026-11-17 18:00")
    ev = ore.eventi_vicini(t0, [{"date": "2026-11-17", "nome": "Trimestrale Nvidia"}, {"date": "2026-12-09", "nome": "Trimestrale Broadcom"}, {"date": "2026-11-17", "nome": "Trimestrale Pippo"}])
    assert [e["ticker"] for e in ev] == ["NVDA"] and ev[0]["quando"] == "2026-11-17T21:20Z" and 0.04 < ev[0]["k"] < 0.08
    v = {"prezzo": 100.0, "ora": t0, "aperto": True}
    m = {"es_ora": 100.0, "es_ancora": 100.0, "fx_ora": 1.1, "fx_ancora": 1.1, "vix": 22.0}
    con = ore.previsione(t0, v, m, ev, sims=8000, seed=5)["orizzonti"]
    senza = ore.previsione(t0, v, m, [], sims=8000, seed=5)["orizzonti"]
    assert con["1 ora"]["eventi"] == [] and con["3 ore"]["eventi"] == [] and con["6 ore"]["eventi"] == ["Nvidia"]
    assert (con["6 ore"]["p90"] - con["6 ore"]["p10"]) > (senza["6 ore"]["p90"] - senza["6 ore"]["p10"])
    sc = ore.scenari(ev)
    assert sc[0]["righe"][0]["vwce"] < 0 < sc[0]["righe"][-1]["vwce"]


def _res(gap, es1=None):
    t0, p = _prev(gap)
    p.update({"ora": t0.strftime("%Y-%m-%dT%H:%MZ"), "vwce": {"prezzo": 100.0, "ora": "2026-11-16T16:30Z", "sede": "Xetra"}, "mercato": {"vix": 22.0}, "eventi": [], "scenari": [], "es_1h": es1, "vix_1h": 0.05})
    p["giudizio"] = ore.giudizio(p)
    return p


def test_giudizio_e_avvisi():
    assert _res(0.0)["giudizio"]["livello"] in ("norm", "ampie")
    assert _res(-0.008)["giudizio"]["livello"] == "calo"
    assert _res(-0.015)["giudizio"]["livello"] == "forte"
    r = _res(-0.008)
    msgs, st = ore.avvisi(r, {})
    assert len(msgs) == 1 and "calo atteso" in msgs[0]["title"] and msgs[0]["priority"] == 4
    # lo stesso avviso non si ripete entro 4 ore, ma si ripete se peggiora di 0,5 punti
    r2 = dict(r, ora="2026-11-16T22:15Z")
    assert ore.avvisi(r2, st)[0] == []
    r3 = _res(-0.015)
    r3["ora"] = "2026-11-16T22:15Z"
    m3, _ = ore.avvisi(r3, st)
    assert len(m3) == 1 and m3[0]["priority"] == 5 and "forte" in m3[0]["title"]
    # nessun avviso se non c'è nulla
    assert ore.avvisi(_res(0.001), {})[0] == []
    # movimento brusco dei futures
    assert any("brusco" in m["title"] for m in ore.avvisi(_res(0.0, es1=-0.013), {})[0])
    # al massimo 4 al giorno
    assert ore.avvisi(r, {"giorno": "2026-11-16", "inviati": 4})[0] == []


def test_avviso_evento_una_volta():
    t0 = _t("2026-11-17 15:00")
    ev = ore.eventi_vicini(t0, [{"date": "2026-11-17", "nome": "Trimestrale Nvidia"}])
    r = {"ora": "2026-11-17T15:00Z", "gap": 0.0, "aperto": True, "vwce": {"prezzo": 100.0}, "eventi": ev}
    m, st = ore.avvisi(r, {})
    assert len(m) == 1 and "Nvidia" in m[0]["title"] and "22:20" in m[0]["title"]
    assert ore.avvisi(r, st)[0] == []


def test_html_sezione():
    from html.parser import HTMLParser

    class P(HTMLParser):
        n = 0
        neg = 0

        def handle_starttag(self, t, a):
            self.n += t == "div"

        def handle_endtag(self, t):
            if t == "div":
                self.n -= 1
                self.neg += self.n < 0
    r = _res(-0.02)
    h = ore_ui.html(r)
    p = P()
    p.feed(h)
    assert p.n == 0 and p.neg == 0 and "Calo forte probabile" in h and "Tra 3 ore" in h and "Come funziona" in h
    assert isinstance(ore_ui.html(None), str) and ore_ui.sub(None) == ""
