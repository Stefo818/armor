import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import config, journal, store  # noqa: E402
from armor.features import fwd_maxdd, price_features  # noqa: E402
from armor.model import Engine, level_of  # noqa: E402


def _prices(n=3000, seed=1):
    r = np.random.default_rng(seed).normal(0.0003, 0.01, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2000-01-03", periods=n))


def test_fwd_maxdd_matches_bruteforce():
    p = _prices(300)
    got = fwd_maxdd(p, 10)
    for i in (5, 50, 200):
        exp = min(p.iloc[i + 1:i + 11].min() / p.iloc[i] - 1, 0)
        assert abs(got.iloc[i] - exp) < 1e-12
    assert got.iloc[-3:].isna().all()


def test_features_no_lookahead():
    p = _prices(800)
    full = price_features(p)
    cut = price_features(p.iloc[:500])
    pd.testing.assert_frame_equal(full.iloc[:500], cut, check_exact=False)


def test_fit_uses_only_matured_outcomes_and_probs_valid():
    p = _prices(2500)
    eng = Engine(p)
    t = p.index[2000]
    f1 = eng.fit(t)
    # cambiare i prezzi FUTURI non deve cambiare il modello
    p2 = p.copy()
    p2.iloc[2001:] = p2.iloc[2001:] * 0.5
    eng2 = Engine(p2)
    f2 = eng2.fit(t)
    a, b = eng.predict(f1, t), eng2.predict(f2, t)
    for hz in a:
        for thr in a[hz]["p"]:
            assert 0 <= a[hz]["p"][thr] <= 1
            assert abs(a[hz]["p"][thr] - b[hz]["p"][thr]) < 1e-9


def test_levels():
    assert level_of(0.3) == "Basso" and level_of(1.0) == "Normale" and level_of(1.5) == "Elevato" and level_of(3) == "Alto"


def test_journal_idempotent_and_tamper_detected(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "j.csv")
    pred = {"1m": {"p": {5: .2, 10: .05}, "base": {5: .18, 10: .04}, "ratio": 1.2, "level": "Normale",
                   "ret": {"q10": -.05, "q50": .01, "q90": .05}}}
    assert journal.append("2026-01-02", 100.0, pred) == 1
    assert journal.append("2026-01-02", 100.0, pred) == 0
    assert journal.append("2026-01-05", 101.0, pred) == 1
    ok, _ = journal.verify()
    assert ok
    txt = (tmp_path / "j.csv").read_text().replace("0.2,", "0.1,", 1)
    (tmp_path / "j.csv").write_text(txt)
    assert not journal.verify()[0]


def test_store_upsert_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "SERIES", tmp_path)
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    assert store.upsert("x", s) == 2
    assert store.upsert("x", s) == 0
    assert len(store.load("x")) == 2


def test_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "j.csv")
    monkeypatch.setattr(journal, "OUTCOMES", tmp_path / "o.csv")
    idx = pd.bdate_range("2026-01-01", periods=40)
    sp = pd.Series(np.linspace(100, 110, 40), index=idx)
    vw = pd.Series(np.linspace(50, 52, 40), index=idx)
    pred = {"1m": {"p": {5: .2, 10: .05}, "base": {5: .18, 10: .04}, "ratio": 1.2, "level": "Normale",
                   "ret": {"q10": -.05, "q50": .01, "q90": .05}}}
    journal.append(idx[0].strftime("%Y-%m-%d"), 50.0, pred)
    assert journal.update_outcomes(vw, sp) == 1
    assert journal.update_outcomes(vw, sp) == 0
    o = pd.read_csv(tmp_path / "o.csv")
    assert abs(o.realized[0] - (vw.iloc[21] / vw.iloc[0] - 1)) < 1e-4


def test_parse_multpl_html_e_testo():
    from armor.sources import parse_multpl
    html = "<tr><td>Nov 6, 2026</td><td><abbr>&#x2020;</abbr> 3.64</td></tr><tr><td>Dec 31, 2025</td><td>&#x2020; 3.35</td></tr>"
    s = parse_multpl(html)
    assert list(s.values) == [3.35, 3.64]
    s2 = parse_multpl("Nov 6, 2026\t† 3.64\nSep 30, 2025\t  3.28")
    assert list(s2.values) == [3.28, 3.64]


def test_extras_pure_functions():
    import numpy as np
    import pandas as pd
    from armor import extras
    idx = pd.bdate_range("2024-01-01", periods=300)
    rng = np.random.default_rng(0)
    px = pd.DataFrame(np.cumprod(1 + rng.normal(0.0005, 0.01, (300, 5)), axis=0), index=idx, columns=list("ABCDE"))
    out = extras.compute_breadth(px)
    assert {"breadth50", "breadth200", "nh_nl"} <= set(out.columns)
    assert out["breadth200"].dropna().between(0, 100).all()


def test_live_parse_chart():
    from armor import live
    day = 86400
    base = 1_700_000_000 // day * day
    ts = [base + 3600, base + 7200, base + day + 3600, base + day + 7200]
    js = {"chart": {"result": [{"meta": {"gmtoffset": 0, "regularMarketPrice": 103.0, "regularMarketTime": ts[-1],
                                         "currentTradingPeriod": {"regular": {"start": ts[-1] - 1000, "end": ts[-1] + 1000}}},
                                "timestamp": ts, "indicators": {"quote": [{"close": [100.0, 101.0, None, 102.0]}]}}]}}
    q = live.parse_chart(js, now_ts=ts[-1] + 60)
    assert q["price"] == 103.0 and q["prev"] == 101.0 and q["open"] is True
    assert abs(q["chg"] - (103 / 101 - 1)) < 1e-9


def test_aaii_to_series():
    import pandas as pd
    from armor import aaii
    d = pd.DataFrame({"bull": [0.4, 0.3], "neutral": [0.3, 0.3], "bear": [0.3, 0.4], "total": [1, 1], "ma8": [0, 0], "spread": [0.1, -0.1]},
                     index=pd.to_datetime(["2026-10-29", "2026-11-05"]))
    s = aaii.to_series(d)
    assert abs(s["aaii_spread"].iloc[-1] + 10) < 1e-9 and abs(s["aaii_bull"].iloc[0] - 40) < 1e-9


def test_best_vwce_picks_latest_venue():
    from armor import live
    day = 86400
    base = 1_700_000_000 // day * day
    def js(price, t, cp=None):
        ts = [base - day + 100, base - day + 200, t]
        return {"chart": {"result": [{"meta": {"gmtoffset": 0, "currentTradingPeriod": {"regular": {"start": 0, "end": 1}}},
                                      "timestamp": ts, "indicators": {"quote": [{"close": [cp or price, cp or price, price]}]}}]}}
    data = {"VWCE.DE": js(165.84, base + 17 * 3600), "VWCE.MU": js(165.08, base + 23 * 3600), "VWCE.F": js(250.0, base + 23 * 3600 + 60)}
    def get(sym):
        if sym in data:
            return data[sym]
        raise RuntimeError("404")
    errs = []
    q = live.best_vwce(get, errs)
    assert q["venue"] == "Monaco/gettex" and abs(q["price"] - 165.08) < 1e-9   # 250 scartato come anomalo


def test_valuations_parse_and_scale(tmp_path, monkeypatch):
    import pandas as pd
    from armor import valuations
    df = pd.DataFrame({"VT": [19.5, 2.4, 3.1], "Category Average": [18.0, 2.0, 2.9]},
                      index=["Price/Earnings", "Price/Sales", "Price/Book"])
    m = valuations.parse_equity_holdings(df)
    assert m == {"pe": 19.5, "ps": 2.4}


def test_news_parse_and_sentiment():
    from datetime import datetime, timezone
    from armor import news
    xml = """<rss><channel>
      <item><title>Stocks plunge as war fears grow - Reuters</title><link>http://x/1</link><pubDate>Fri, 06 Nov 2026 14:00:00 GMT</pubDate><description>&lt;p&gt;Markets tumble&lt;/p&gt;</description></item>
      <item><title>Nvidia beats estimates, shares surge on AI chip demand</title><link>http://x/2</link><pubDate>Fri, 06 Nov 2026 15:00:00 GMT</pubDate><description>Record revenue</description></item>
    </channel></rss>"""
    items = news.parse_rss(xml)
    assert items[0]["source"] == "Reuters" and items[0]["title"].startswith("Stocks plunge")
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    en = news.enrich(items, now, "macro", "Mercati")
    assert en[0]["label"] == "negativo" and "Guerre e geopolitica" in en[0]["themes"]
    assert en[1]["label"] == "positivo" and "Intelligenza artificiale e chip" in en[1]["themes"]
    data = news.collect(get=lambda url: xml, now=now)
    assert len(data["items"]) == 2          # i duplicati tra feed diversi vengono eliminati


def test_calendario_e_avvisi():
    from datetime import date
    from armor import alerts, calendario
    ev = calendario.events(date(2026, 11, 7), 45)
    assert any(e["tipo"] == "FOMC" and e["date"] == "2026-12-09" for e in ev)
    assert calendario.next_big(ev, date(2026, 11, 7))["giorni"] == 3
    pred = {"1m": {"level": "Elevato"}}
    m, new = alerts.detect({"levels": {"1m": "Normale"}}, pred, None, 31.0, None, None, "2026-11-09")
    assert len(m) == 1 and new["levels"]["1m"] == "Elevato"
    m2, _ = alerts.detect(new, pred, None, 31.0, None, None, "2026-11-09")
    assert m2 == []   # nessuna ripetizione
    sent = []
    class R:  # finto server
        ok = True
    assert alerts.send(m, "t", post=lambda *a, **k: sent.append(k["json"]) or R()) == 1 and sent[0]["topic"] == "t"


def test_volatilita_regime_fx():
    import numpy as np, pandas as pd
    from armor import regime, volatility
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("1990-01-01", periods=6000)
    vol = np.where((np.arange(6000) // 500) % 3 == 2, 0.025, 0.007)
    p = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, vol))), index=idx)
    v = volatility.forecast(p, pd.Series(dtype=float))
    assert v["attesa"] > 0 and v["bassa"] < v["attesa"] < v["alta"]
    r = regime.compute(p)
    assert r["nome"] in regime.NAMES and abs(sum(r["prob"]) - 1) < 1e-6


def test_news_scorer_iniettato():
    from armor import news
    out = news.collect(get=lambda u: "<rss><channel></channel></rss>", scorer=lambda t: [])
    assert out["model"] == "vocabolario"


def test_allarmi_semafori_coerenza():
    from armor import allarmi, insight, semafori
    msgs, st = allarmi.evaluate([{"id": "a", "key": "vix", "op": ">", "value": 30}], {"vix": {"label": "VIX", "value": 35.0}}, {})
    assert len(msgs) == 1 and st["a"] is True
    msgs2, st2 = allarmi.evaluate([{"id": "a", "key": "vix", "op": ">", "value": 30}], {"vix": {"label": "VIX", "value": 35.0}}, st)
    assert msgs2 == [] and st2["a"]
    msgs3, st3 = allarmi.evaluate([{"id": "a", "key": "vix", "op": ">", "value": 30}], {"vix": {"label": "VIX", "value": 20.0}}, st)
    assert st3["a"] is False
    spec = semafori.SPEC_BY["vix"]
    assert semafori.light_of(spec, 15, None) == "ok" and semafori.light_of(spec, 25, None) == "wa" and semafori.light_of(spec, 35, None) == "ba"
    items = [{"key": "vix", "light": "ba", "name": "VIX"}, {"key": "hy_oas", "light": "ok", "name": "HY"}]
    c = insight.coherence(items)
    assert c["discordanti"] and "Paura e opzioni" in c["tesi"]


def test_fine_series_cot_e_valutazioni():
    from armor import live, posizionamento, valuations
    pts = [(1000 + 60 * i, 100.0 + i) for i in range(800)]
    f = live.fine_series(pts)
    assert len(f["t1"]) <= 91 and f["t10"][1] - f["t10"][0] == 600
    assert valuations.harmonic([(1, 20.0)] * 5) == 20.0 and valuations.harmonic([(1, 20.0)]) is None
    assert valuations.zone("sp500", "pe", 30) == "ba" and valuations.zone("sp500", "pe", 15) == "ok"
    line = '"E-MINI S&P 500 - CME",261103,2026-11-03,13874A,CME ,00,138 ,2000000,100000,300000,50000,800000,100000,200000,300000,900000,100000,1,2\n'
    assert round(posizionamento.parse_cot(line).iloc[0]["lev"], 1) == -30.0


def test_indice_armor_punteggi_e_termometro():
    import pandas as pd
    from armor import armor_index as A
    x = pd.Series([10.0, 20.0, 30.0, 40.0])
    s = A._thresh_score(x, "hi", 20, 30)
    assert s.iloc[0] == 0 and abs(s.iloc[1] - .35) < 1e-9 and abs(s.iloc[2] - .7) < 1e-9 and s.iloc[3] == 1
    lo = A._thresh_score(pd.Series([2.0, 1.05, 0.95, 0.5]), "lo", 1.05, 0.95)
    assert lo.iloc[0] == 0 and lo.iloc[3] == 1 and lo.is_monotonic_increasing
    idx = pd.date_range("2020-01-01", periods=5)
    z = [0, .2, .5, .8, 1.0]
    S = pd.DataFrame({k: z for k in ["vix", "vterm", "vvix", "hy_oas", "baa10y", "cape_m", "pe_m", "dd252", "ma200"]}, index=idx)
    v, _g = A.combine(S)
    assert v.dropna().is_monotonic_increasing and 1 <= v.dropna().min() and v.dropna().max() <= 100
    assert "svg" in A.thermometer(50) and A.band(10)[0] == "molto basso" and A.band(95)[0] == "molto alto"


def test_run_parallel_non_blocca():
    import time
    from armor.guard import run_parallel
    r = run_parallel({"a": lambda: 1, "b": lambda: time.sleep(5)}, workers=2, deadline=0.5)
    assert r["a"] == ("ok", 1) and r["b"][0] == "err"


def test_chiaro_e_extra13():
    import pandas as pd
    from armor import chiaro, extra13
    pr = [0.05, 0.15, 0.4, 0.3, 0.1]
    assert "stk" in chiaro.stacked(pr) and chiaro.P(0.123, 0) == "12%"
    h = chiaro.horizon_simple("1m", {"p": {10: 0.03}, "base": {10: 0.05}, "level": "Normale", "ret": {"q10": -.05, "q50": .01, "q90": .06}},
                              {"up": {10: {"p": 0.02, "base": 0.03}}}, 100.0, ("Utile", ""), "<i>old</i>")
    assert "Nessun movimento forte" in h and "Salire di almeno" in h
    out = extra13.glossario_html()
    assert "VIX" in out and "Esempio" in out
    sp = pd.Series(100 + pd.Series(range(120)).values * 0.1, index=pd.bdate_range("2026-06-01", periods=120))
    vix = pd.Series(18.0, index=sp.index)
    c = extra13.calendar_html(sp.index[-1].date(), sp, vix)
    assert "Calendario degli eventi" in c and "Previsti" not in c
    assert "Oggi cosa faccio" in extra13.oggi_html(None, None, [], 0)


def test_rapporti_capovolti_e_apprendimento(tmp_path, monkeypatch):
    import pandas as pd
    from armor import store, valuations, learning
    monkeypatch.setattr(store, "SERIES", tmp_path)
    monkeypatch.setattr("armor.config.SERIES", tmp_path)
    assert abs(valuations.norm(0.04) - 25) < 1e-9 and valuations.norm(24.5) == 24.5
    df = pd.DataFrame({"Price/Earnings": [0.0397], "Price/Sales": [0.29]}, index=["x"]).T
    out = valuations.parse_equity_holdings(df.rename(columns={"x": 0}))
    assert 24 < out["pe"] < 26 and 3 < out["ps"] < 4
    store.upsert("val_pe_sp500", pd.Series({pd.Timestamp("2026-11-01"): 0.04, pd.Timestamp("2026-11-02"): 25.0}))
    valuations.repair()
    assert (store.load("val_pe_sp500") > 1).all()
    t = learning.live_table(pd.Series(dtype=float))
    assert t.empty or "bss" in t


def test_fase0_fred_stooq_salute_registro():
    import json
    import pandas as pd
    from armor import registry, salute, sources
    js = json.dumps({"observations": [{"date": "2026-11-03", "value": "4.1"}, {"date": "2026-11-04", "value": "."}, {"date": "2026-11-05", "value": "4.3"}]})
    s = sources.parse_fred_json(js)
    assert list(s.values) == [4.1, 4.3]
    assert list(sources.parse_fred_csv("DATE,X\n2026-11-03,1.5\n2026-11-04,.\n").values) == [1.5]
    st = sources.parse_stooq_csv("Date,Open,High,Low,Close,Volume\n2026-11-05,1,2,0.5,6000.5,10\n2026-11-06,1,2,0.5,6100.25,10\n")
    assert st.iloc[-1] == 6100.25 and len(st) == 2
    rows = salute.compute({"sp500": {"last_date": "2026-11-06"}, "vix": {"last_date": "2026-10-01", "msg": "x"}, "cape_m": {"last_date": "2026-10-31"}},
                          today=pd.Timestamp("2026-11-07"))
    d = {r["key"]: r["light"] for r in rows}
    assert d["sp500"] == "ok" and d["vix"] == "ba" and d["cape_m"] == "ok"
    assert "VIX" in salute.red_names(rows) and "Fermo" in salute.html(rows)
    row = {"date": "2026-11-06", "armor_index": 50}
    assert "pup_1m" in registry.check(row) and "date" not in registry.check(row)


def _garch_series(n=4000, seed=3):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    om, al, be = 0.02, 0.08, 0.90
    s2, r = 1.0, []
    for _ in range(n):
        e = np.sqrt(s2) * rng.standard_t(7) / np.sqrt(7 / 5)
        r.append(e + 0.03)
        s2 = om + al * e * e + be * s2
    p = 100 * np.exp(np.cumsum(np.array(r) / 100))
    return pd.Series(p, index=pd.bdate_range("2005-01-03", periods=n))


def test_fhs_stima_simulazione_e_nessun_futuro():
    import numpy as np
    from armor import fhs
    p = _garch_series()
    r = fhs.log_returns(p)
    pr = fhs.fit(r.values)
    assert 0.9 < pr["persistence"] < 1.0 and pr["nu"] > 2.5 and abs(pr["z"].std() - 1) < 1e-6
    f = fhs.forecast(p, sims=1500, seed=1)
    for hz in ("10g", "1m", "3m", "6m"):
        d = [f[hz]["down"][t]["p"] for t in sorted(f[hz]["down"])]
        u = [f[hz]["up"][t]["p"] for t in sorted(f[hz]["up"])]
        assert all(a >= b - 1e-12 for a, b in zip(d, d[1:])) and all(a >= b - 1e-12 for a, b in zip(u, u[1:]))   # soglie più alte = meno probabili
        assert abs(sum(f[hz]["scen"]) - 1) < 1e-9
    # più alta la varianza iniziale, più probabili i cali grandi
    lo = fhs.summarize(fhs.simulate(pr, 0.3, 1500, seed=2))["1m"]["down"][5]["p"]
    hi = fhs.summarize(fhs.simulate(pr, 6.0, 1500, seed=2))["1m"]["down"][5]["p"]
    assert hi > lo + 0.2
    # nessuno sguardo al futuro: stessa data, dati futuri diversi -> stessa previsione
    t = p.index[2500]
    a = fhs.forecast(p, date=t, sims=800, seed=5)["1m"]["down"][5]["p"]
    p2 = p.copy()
    p2[p2.index > t] = p2[p2.index > t] * 3
    b = fhs.forecast(p2, date=t, sims=800, seed=5)["1m"]["down"][5]["p"]
    assert a == b


def test_valutazione_modelli_purged_e_auc():
    import numpy as np
    import pandas as pd
    from armor import modeleval
    p = _garch_series(1500)
    dates = p.index[800::50]
    b1 = modeleval.purged_base(p, dates, "1m", "down", 5)
    p2 = p.copy()
    p2[p2.index > dates[3]] *= 0.5     # il futuro cambia drasticamente
    b2 = modeleval.purged_base(p2, dates, "1m", "down", 5)
    assert np.allclose(b1.iloc[:3].values, b2.iloc[:3].values)   # la frequenza «normale» a t non dipende dal futuro
    assert abs(modeleval.auc([0.1, 0.2, 0.8, 0.9] * 10, [0, 0, 1, 1] * 10) - 1.0) < 1e-9
    lo, hi = modeleval.block_ci(np.full(200, 0.9), np.full(200, 1.0), 5)
    assert abs(lo - 0.1) < 1e-6 and abs(hi - 0.1) < 1e-6


def _prezzi_finti(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    vol = np.where((np.arange(n) // 250) % 3 == 2, 0.02, 0.008)
    r = rng.standard_normal(n) * vol + 0.0003
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2000-01-03", periods=n))


def test_mv_nessuno_sguardo_al_futuro(monkeypatch):
    """Le variabili esterne alla data t non cambiano se si cambiano i dati futuri; il ritardo e' rispettato."""
    from armor import model_mv
    idx = pd.bdate_range("2000-01-03", periods=600)
    rng = np.random.default_rng(0)
    base = {k: pd.Series(rng.random(600) + 1, index=idx) for k in ("vix", "baa10y", "t10y3m", "nfci")}
    base["vix"] = base["vix"] * 20

    def mk(d):
        return lambda k: d[k]
    monkeypatch.setattr(model_mv.store, "load", mk(base))
    rv = pd.Series(0.1, index=idx)
    a = model_mv.mv_extra(idx, rv)
    mod = {k: v.copy() for k, v in base.items()}
    for k in mod:
        mod[k].iloc[400:] = 999.0
    monkeypatch.setattr(model_mv.store, "load", mk(mod))
    b = model_mv.mv_extra(idx, rv)
    pd.testing.assert_frame_equal(a.iloc[:400], b.iloc[:400])
    # NFCI ritardato di 5 giorni: il valore al giorno 399 non usa il dato del giorno 399 ma di prima
    t = idx[300]   # i ritardi sono in giorni di calendario
    assert a["nfci"].loc[t] == base["nfci"].asof(t - pd.Timedelta(days=5))
    assert a["baa10y"].loc[t] == base["baa10y"].asof(t - pd.Timedelta(days=1))


def test_ensemble_pesi_monotonia_e_ritorno_al_normale():
    from armor import ensemble
    rng = np.random.default_rng(1)
    y = (rng.random(2000) < 0.2).astype(float)
    buono = np.clip(0.1 + 0.2 * y + rng.normal(0, 0.05, 2000), 0.01, 0.99)   # informativo
    rumore = np.clip(rng.random(2000), 0.01, 0.99)
    w = ensemble.fit_weights(np.column_stack([buono, rumore]), y)
    assert abs(w.sum() - 1) < 1e-9 and (w >= 0).all() and w[0] > 0.8
    m = ensemble.monotonize({5: 0.3, 10: 0.4, 15: 0.1})
    assert m[5] >= m[10] >= m[15]


def test_ensemble_walk_forward_senza_abilita_torna_al_normale():
    """Se i modelli sono rumore puro, dopo il periodo di prova l'abilita' misurata e' <= 0 e p = normale."""
    from armor import ensemble, modeleval
    p = _prezzi_finti(3000)
    dates = p.index[300::5]
    rng = np.random.default_rng(5)
    rows = []
    for t in dates:
        for hz in ensemble.HORIZONS:
            for thr in ensemble.TARGETS[hz]:
                for k in ("down", "up"):
                    rows.append({"date": t, "hz": hz, "kind": k, "thr": thr, "p": float(rng.random())})
    pr = pd.DataFrame(rows)
    preds = {m: pr.copy() for m in ("A1", "FHS", "MV-logit", "MV-GBM")}
    bf = lambda hz, k, t: modeleval.purged_base(p, dates, hz, k, t)
    of = lambda hz, k, t: modeleval.outcome(p, dates, hz, k, t)
    df, st = ensemble.combine(p, dates, preds, bf, of, step=5)
    tail = df[df.date > dates[-300]]
    assert len(tail) > 0 and tail.w.mean() < 0.35   # rumore: poca fiducia
    ok = df.groupby(["date", "hz", "kind"]).apply(lambda g: (g.sort_values("thr").p.diff().dropna() <= 1e-12).all())
    assert ok.all()


def test_intervalli_conformali_e_spiegazioni():
    from armor import ensemble, spiega
    p = _prezzi_finti(2500)
    dates = p.index[300::5]
    rng = np.random.default_rng(2)
    rows = []
    for t in dates:   # intervalli troppo stretti di proposito: il conformale deve allargarli
        for hz in ensemble.HORIZONS:
            rows += [{"date": t, "hz": hz, "kind": "q", "thr": 10, "p": -0.01}, {"date": t, "hz": hz, "kind": "q", "thr": 50, "p": 0.0},
                     {"date": t, "hz": hz, "kind": "q", "thr": 90, "p": 0.01}]
    q = pd.DataFrame(rows)
    c = ensemble.coverage(ensemble.interval_scale(q, p, dates, "1m"))
    assert c["copertura_conformale"] > c["copertura_grezza"] + 0.2 and abs(c["copertura_conformale"] - 0.8) < 0.08
    assert len(spiega.cause_logit([("rv21", 0.9), ("dd252", -0.4), ("mom63", 0.01)])) == 2
    assert "sopra" in spiega.cause_fhs(0.30, 0.15)


def test_intervallo_verificato_dal_vivo(monkeypatch):
    from armor import spiega
    ev = {"intervalli": {"3m": {"A1": {"copertura_grezza": 0.89, "copertura_conformale": 0.80, "k_ultimo": 0.8, "n": 100}},
                         "1m": {"A1": {"copertura_grezza": 0.81, "copertura_conformale": 0.79, "k_ultimo": 0.95, "n": 100}}}}
    monkeypatch.setattr(spiega, "_eval", lambda: ev)
    ret = {"q10": -0.10, "q50": 0.02, "q90": 0.14}
    r3, t3 = spiega.ret_display("3m", ret)          # fuori da 80% +- 3: si stringe attorno a q50
    assert abs((r3["q90"] - r3["q10"]) - 0.8 * 0.24) < 1e-9 and "80%" in t3
    r1, _ = spiega.ret_display("1m", ret)           # gia' a posto: invariato
    assert r1 == ret
    assert spiega.ret_display("6m", ret) == (ret, "")
