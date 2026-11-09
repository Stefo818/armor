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


def test_indice_probabilita_isotonica_e_pesi():
    from armor import armor_index as A
    rng = np.random.default_rng(0)
    idx = pd.Series(rng.uniform(1, 100, 3000), index=pd.bdate_range("2000-01-03", periods=3000))
    y = pd.Series((rng.random(3000) < 0.05 + 0.4 * idx.values / 100).astype(float), index=idx.index)
    y.iloc[-30:] = np.nan                                  # esiti non ancora noti
    r = A.iso_probs(idx, {"dd10_63": y}, 80.0)["events"]["dd10_63"]
    lo = A.iso_probs(idx, {"dd10_63": y}, 10.0)["events"]["dd10_63"]
    assert r["p"] > lo["p"] + 0.15 and 0 <= lo["p"] <= r["p"] <= 1 and r["n"] == 2970
    # pesi: coefficienti >= 0, la famiglia informativa pesa di piu'
    G = rng.random((2000, 3))
    yy = (rng.random(2000) < 0.1 + 0.6 * G[:, 0]).astype(float)
    c = A.fit_weights_logit(G, [(np.arange(2000), yy)])
    assert (c >= 0).all() and c[0] > 3 * max(c[1], c[2])


def test_famiglie_senza_sguardo_al_futuro(monkeypatch):
    from armor import armor_index as A
    idx = pd.bdate_range("2000-01-03", periods=200)
    G = pd.DataFrame({g: np.arange(200, dtype=float) for g in A.GROUPS}, index=idx)
    monkeypatch.setattr(A, "build_scores", lambda sp: (pd.DataFrame(index=idx), {}))
    monkeypatch.setattr(A, "combine", lambda S: (None, G))
    f = A.family_features(pd.Series(1.0, index=idx))
    assert f["fam_valut"].iloc[100] == 70.0 and f["fam_paura"].iloc[100] == 99.0 and f["fam_credito"].iloc[100] == 95.0
    assert f["fam_paura"].iloc[:1].isna().all() and "fam_sent" not in f


def test_auc_indice_dal_vivo_soglia_40_esiti():
    from armor import learning
    rng = np.random.default_rng(1)
    idx = pd.Series(rng.uniform(1, 100, 400), index=pd.bdate_range("2026-01-01", periods=400))
    ev_pochi = pd.Series((np.arange(400) < 10).astype(float), index=idx.index)
    ev_molti = pd.Series((rng.random(400) < 0.1 + 0.5 * idx.values / 100).astype(float), index=idx.index)
    d = learning.index_live_auc(idx, {"a": ev_pochi, "b": ev_molti})
    assert d["events"]["a"]["auc"] is None and d["events"]["b"]["auc"] > 0.6 and d["events"]["b"]["n_events"] >= 40


def test_notifiche_massimo_una_al_giorno_e_solo_cambiamenti():
    from armor import alerts
    pred = {"1m": {"level": "Elevato"}, "3m": {"level": "Normale"}}
    st = {"levels": {"1m": "Normale"}, "aix_band": "moderato", "divergence": False}
    m, new = alerts.detect(st, pred, "Calma", 18.0, None, None, "2026-11-09", aix_band="elevato", divergence=True)
    assert len(m) == 3 and {x["title"].split(":")[0] for x in m} >= {"Rischio in aumento a 1 mese", "Indice Armor", "Allarme divergenza attivato"}
    m2, _ = alerts.detect(new, pred, "Calma", 18.0, None, None, "2026-11-09", aix_band="elevato", divergence=True)
    assert m2 == []                                                     # nessuna ripetizione
    out, st2 = alerts.pick_daily(m, [], new, "2026-11-09")
    assert len(out) == 1 and "Altri cambiamenti" in out[0]["message"] and out[0]["priority"] == 4
    out2, _ = alerts.pick_daily(m, [], st2, "2026-11-09")
    assert out2 == []                                                   # gia' partita una notifica oggi
    pend = [{"title": "Rapporto settimanale pronto", "message": "x", "priority": 2}]
    assert alerts.pick_daily([], pend, {}, "2026-11-10")[0][0]["title"] == "Rapporto settimanale pronto"
    # nessun avviso per un livello che cambia in modi non richiesti (es. 3m, o 1m da elevato a normale)
    assert alerts.detect({"levels": {"1m": "Elevato", "3m": "Basso"}}, {"1m": {"level": "Normale"}, "3m": {"level": "Alto"}}, None, None, None, None, "d")[0] == []


def test_ombra_diario_catena_e_punteggi(tmp_path):
    from armor import journal, shadow
    pred = {"1m": {"p": {5: 0.3, 10: 0.1}, "base": {5: 0.2, 10: 0.05}, "ratio": 2.0, "level": "Alto"}}   # senza quantili (come i modelli ombra)
    path = tmp_path / "ombra.csv"
    assert journal.append("2020-01-02", 100.0, pred, model="FHS", path=path) == 1
    assert journal.append("2020-01-02", 100.0, pred, model="FHS", path=path) == 0
    assert journal.append("2020-01-02", 100.0, pred, model="MV-GBM", path=path) == 1
    assert journal.verify(path)[0]
    sp = _prezzi_finti(3000)
    sp.index = pd.bdate_range("2019-06-03", periods=3000)
    main = pd.DataFrame([{"asof": "2020-01-02", "horizon": "1m", "model": "A1", "p1": 0.25, "base1": 0.2, "thr1": 5}])
    sc = shadow.scores_from(journal.read(path), main, sp)
    assert set(sc.model) == {"FHS", "MV-GBM", "A1"} and (sc.n == 1).all()


def test_rapporto_mensile_e_notizie_spente():
    from armor import news_signal, rapporto
    sp = _prezzi_finti(1500)
    first = pd.Timestamp(sp.index[600]).replace(day=1)
    reg = {"champion": "A1", "versions": [], "tentativi": [{"id": "E1", "data": first.strftime("%Y-%m-15"), "adottato": False, "campione": "A1"}]}
    d = rapporto.build(first, sp, pd.DataFrame(), pd.DataFrame(), reg, pd.DataFrame(), None)
    assert "mercato" in d and "non adottata" in d["modello"]["cambiamenti"][0]
    assert "non adottata" in rapporto.html(d) and "Rapporto mensile Armor" in rapporto.message(d)["title"]
    idx = pd.bdate_range("2024-01-01", periods=900)
    regd = pd.DataFrame({"date": idx.strftime("%Y-%m-%d"), "news_sent_macro": np.linspace(-1, 1, 900)})
    assert news_signal.feature(idx, regd) is None                      # spento
    news_signal.ATTIVO = True
    try:
        assert news_signal.feature(idx[:200], regd.iloc[:200]) is None   # storia corta
        f = news_signal.feature(idx, regd)
        s = news_signal.storia(regd)
        assert abs(f["news_tone21"].loc[idx[700]] - s.rolling(21, min_periods=10).mean().loc[idx[699]]) < 1e-9   # spostato di un giorno
    finally:
        news_signal.ATTIVO = False


def test_pagina_fiducia_e_prossimo_evento():
    from datetime import date
    from armor import ui
    assert ui.verdict(0.05, 0.01, 0.1, -0.03)[0] == "ok" and "peggio" in ui.verdict(0.05, 0.01, 0.1, -0.03)[1]
    assert ui.verdict(0.03, -0.02, 0.1, 0.0)[0] == "warn" and ui.verdict(-0.01, -0.1, 0.0, None)[0] == "bad"
    assert "<svg" in ui.calib_svg([(0.05, 0.04), (0.2, 0.25)]) and ui.calib_svg([]) == ""
    rows, cal = [], []
    for hz, thr in (("10g", 5), ("1m", 10), ("3m", 10), ("6m", 10)):
        rows.append({"set": "modelli", "model": "A1", "hz": hz, "thr": thr, "kind": "down", "bss": 0.05, "bss_lo": 0.01, "bss_hi": 0.1, "auc": 0.7,
                     "bss_2013_26": -0.05, "n": 100, "da": "1995-01-01"})
        cal.append({"set": "modelli", "model": "A1", "hz": hz, "thr": thr, "kind": "down", "prev": 0.1, "real": 0.12, "n": 10})
    h = ui.fiducia_html(ev={"metrics": rows, "calibration": cal, "intervalli": {}})
    assert "batte la media storica" in h and "peggio" in h and h.count("<svg") == 4
    assert "non è ancora disponibile" in ui.fiducia_html(ev={})
    assert "Prossimo evento" in ui.next_event_html(date(2026, 11, 7))


def test_dati_per_serie_e_js_a_caricamento_tardivo(tmp_path):
    import json
    from armor import parts, sitedata
    data = {"vwce": {"l": "VWCE", "dec": 2, "d": [1, 2], "v": [1.0, 2.0]}, "a/b": {"l": "X", "dec": 0, "d": [1], "v": [3.0]}}
    (tmp_path / "series").mkdir()
    (tmp_path / "series" / "vecchia.json").write_text("{}")
    sitedata.write(tmp_path / "data.json", data)
    assert json.loads((tmp_path / "series" / "vwce.json").read_text())["v"] == [1.0, 2.0] and (tmp_path / "series" / "a_b.json").exists()
    assert not (tmp_path / "series" / "vecchia.json").exists() and (tmp_path / "data.json").stat().st_size < 500
    assert "series/" in parts.JS and "var emb=" not in parts.JS and "var emb=" in parts.LATE_JS["embedchart"] and "var emb=" in parts.JS_FULL
    assert "armorEnsure(id)" in parts.TABS_JS_LAZY


def test_mappa_e_calendario():
    import json as _j
    import pandas as _pd
    from armor import armor_index as _ai, extra13 as _e13, mappa as _mp, store as _st
    from armor.features import closed_sp500, vwce_series
    sp = closed_sp500()
    aix = _ai.compute(sp)
    if aix is None:
        return
    m = _mp.build_mappa(sp, aix, vwce_series())
    assert m["rows"][0]["k"] == "vwce" and m["rows"][1]["k"] == "sp500" and m["rows"][2]["k"] == "armor"
    n = len(m["w"])
    assert n > 400 and all(len(r["sc"]) == n and len(r["v"]) == n for r in m["rows"])
    assert any(r["k"] == "vix" and r.get("sv") for r in m["rows"])
    _j.loads(_mp.dumps(m))   # niente NaN: JSON valido
    assert "NaN" not in _mp.dumps(m)
    today = _pd.Timestamp(sp.index[-1]) + _pd.Timedelta(days=1)
    evs = _e13.all_events((today - _pd.Timedelta(days=1200)).date(), (today + _pd.Timedelta(days=75)).date())
    c = _mp.build_cal(sp, vwce_series(), _st.load("vix"), aix, today, evs)
    assert len(c["d"]) > 500 and len(c["w"]) > 100 and len(c["m"]) > 30 and "NaN" not in _mp.dumps(c)
    # il rendimento reale di un giorno coincide con la variazione dell'S&P 500
    d = [x for x in c["d"] if x[1] is not None][-1]
    r = sp.pct_change() * 100
    assert abs(r.loc[_pd.Timestamp(d[0])] - d[1]) < 0.01
    # blocchi HTML
    assert "data-mappa" in _mp.mappa_block() and "data-cal2" in _mp.cal_block()


def test_bande_ordinate():
    import pandas as pd
    from armor import bande
    b = bande.band(18.0, 21, pd.Timestamp("2024-06-03"))
    assert b["lo"] < b["med"] < b["hi"] and 0 < b["pup"] < 1
    assert 0 <= bande.pct_of(1.0, 18.0, 21, pd.Timestamp("2024-06-03")) <= 100


def test_holdings_html_con_cap():
    from armor import holdings
    d = {"date": "2026-11-07", "source": "x", "top": [["Apple", 4.5, "AAPL", 4100.0], ["Old", 1.0]],
         "sectors": [["Tecnologia", 38.0]]}
    h = holdings.html(d)
    assert "4.100" in h and "n.d." in h


# ---------------------------------------------------------------- patch 21: dati nuovi, ritardi, ricerca (nessuna rete)
def _ms_series(vals, start="2000-01-01"):
    return pd.Series(vals, index=pd.date_range(start, periods=len(vals), freq="MS"), dtype=float)


def test_mensile_rispetta_ritardo():
    from armor import fondamentali
    s = _ms_series(np.arange(1, 25))          # dato di gennaio 2000 = 1, febbraio = 2, ...
    fondamentali.LAG["_prova"] = 45
    X = fondamentali.mensile(["_prova"], load=lambda k: s, start="2000-01-31", end="2001-12-31")
    assert np.isnan(X.loc["2000-01-31", "_prova"])            # gennaio è noto solo a metà febbraio
    assert X.loc["2000-02-29", "_prova"] == 1
    assert X.loc["2000-03-31", "_prova"] == 2
    X2 = fondamentali.mensile(["_prova"], load=lambda k: s, start="2000-01-31", end="2001-12-15", con_oggi=True)
    assert X2.index[-1] == pd.Timestamp("2001-12-15")


def test_calcola_derivate_senza_date_future():
    from armor import fondamentali
    d = pd.bdate_range("2000-01-03", "2006-12-29")
    sp = pd.Series(np.linspace(1000, 1500, len(d)), index=d)
    pe = _ms_series([20.0] * 84)                                 # P/E costante: utili crescono come il prezzo
    walcl = pd.Series(4_000_000.0, index=pd.date_range("2003-01-01", "2006-12-27", freq="W-WED"))
    data = {"sp500": sp, "pe_m": pe, "walcl": walcl, "tga": walcl * 0 + 500_000.0, "rrp": pd.Series(100.0, index=d),
            "cpi": _ms_series(100 * 1.03 ** (np.arange(84) / 12)), "iwm": sp * 0.1, "spy": sp * 0.5}
    out = fondamentali.calcola(load=lambda k: data.get(k, pd.Series(dtype=float)))
    eps = out["eps_sp"]
    assert abs(out["eps_g12"].iloc[-1] - (eps.iloc[-1] / eps.iloc[-13] - 1) * 100) < 1e-9
    assert abs(out["net_liq"].iloc[-1] - (4000 - 500 - 100)) < 1e-6      # miliardi
    assert abs(out["cpi_yoy"].iloc[-1] - 3.0) < 0.01
    assert abs(out["rel_small"].iloc[-1]) < 1e-9                          # stesso andamento: forza relativa nulla
    for k, s in out.items():
        assert s.index.max() <= d[-1], k


def test_parse_finra_e_ciss():
    from armor import fondamentali
    raw = pd.DataFrame([["FINRA margin statistics", None, None], ["Year-Month", "Debit Balances in Customers' Securities Margin Accounts", "Free Credit"],
                        ["2026-08", 1_200_000, 200_000], ["2026-09", 1_250_000, 210_000]])
    s = fondamentali.parse_finra(raw)
    assert s.loc["2026-09-01"] == 1_250_000 and len(s) == 2
    c = fondamentali.parse_ciss("KEY,FREQ,TIME_PERIOD,OBS_VALUE\nx,D,2026-11-05,0.081\nx,D,2026-11-06,0.09\n")
    assert c.iloc[-1] == 0.09 and c.index[-1] == pd.Timestamp("2026-11-06")


def test_calcola_revisioni_pesate():
    from armor import fondamentali
    rows = [{"up": 3, "dn": 1, "g": 10.0, "cap": 3e12}] * 5 + [{"up": 0, "dn": 4, "g": 0.0, "cap": 1e12}] * 5
    r = fondamentali.calcola_revisioni(rows)
    assert abs(r["rev_breadth"] - (50 * 3 + (-100) * 1) / 4) < 1e-9
    assert abs(r["fwd_growth"] - 7.5) < 1e-9
    assert fondamentali.calcola_revisioni(rows[:9])["rev_breadth"] is None    # meno di 10 titoli: nessun valore


def test_ricerca_obiettivi_e_holdout():
    from armor import ricerca
    p = _prices(6000, seed=3)
    p.index = pd.bdate_range("1995-01-02", periods=6000)
    idx = pd.date_range("1996-01-31", "2017-12-31", freq="ME")
    Y = ricerca.obiettivi(p, idx)
    t = idx[10]
    w = p[(p.index > t) & (p.index <= t + pd.DateOffset(months=6))]
    p0 = p[p.index <= t].iloc[-1]
    assert abs(Y.loc[t, "dd_6"] - (w.min() / p0 - 1) * 100) < 1e-9
    assert Y.loc[t, "rialzo_6"] == float(w.iloc[-1] > p0)
    X = pd.DataFrame({"a": np.random.default_rng(0).normal(size=len(idx))}, index=idx)
    pr, cl = ricerca.walk_forward(X, Y["calo10_6"], 6, ["a"], anni=(2005, 2030), min_train=60)
    chiuse = pr.dropna().index + pd.DateOffset(months=6)
    assert len(pr.dropna()) > 0 and chiuse.max() <= ricerca.FINE_RICERCA          # mai esiti dopo il 2018 senza holdout


def test_semafori_e_candidati_coerenti():
    from armor import armor_index, fondamentali, semafori, sources
    keys = [s[0] for s in semafori.SPEC]
    assert all(len(s) == 10 for s in semafori.SPEC) and len(keys) == len(set(keys))
    assert semafori.MONITORATI <= set(keys)
    assert not set(fondamentali.FRED_NUOVE) & set(sources.FRED) and not set(fondamentali.FRED_NUOVE.values()) & set(sources.FRED.values())
    for k, fam, kind, y, r in armor_index._new_items():
        assert fam in armor_index.GROUPS and kind in ("hi", "lo")


# ---------------------------------------------------------------- patch 22-23: aziende VWCE, ricerca Fase B, prova finale
def _yf_frame(rows: dict, dates):
    return pd.DataFrame(rows, index=pd.to_datetime(dates)).T


def test_aziende_analizza_trimestre_e_etichetta():
    from armor import aziende
    dq = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"]
    inc = _yf_frame({"Total Revenue": [120, 110, 105, 100, 100], "Net Income": [30, 25, 22, 20, 20], "Operating Income": [40, 35, 30, 28, 25]}, dq)
    bal = _yf_frame({"Total Debt": [50, 55, 60, 60, 60], "Cash And Cash Equivalents": [40, 35, 30, 30, 30]}, dq)
    r = aziende.analizza(inc_q=inc, bal_q=bal)
    assert r["base"] == "trimestre" and r["periodo"] == "lug-set 2026" and r["periodo_prec"] == "lug-set 2025"
    assert r["rev_12m"] == 120 + 110 + 105 + 100 and "fatturato" in r["aumentati"] and "debito" in r["diminuiti"]
    assert abs(r["rev_g"] - 20) < 1e-9 and abs(r["ni_g"] - 50) < 1e-9 and abs(r["opm_d"] - (40 / 120 - 25 / 100) * 100) < 1e-9
    assert r["etichetta"] == "In miglioramento" and r["punteggio"] >= 2
    peg = aziende.analizza(inc_q=_yf_frame({"Total Revenue": [90, 100, 100, 100, 100], "Net Income": [5, 20, 20, 20, 20],
                                            "Operating Income": [9, 20, 20, 20, 20]}, dq))
    assert peg["etichetta"] == "In peggioramento"
    assert "errore" in aziende.analizza()                     # nessun bilancio: errore, nessuna eccezione


def test_aziende_pesi_e_riepilogo():
    from armor import aziende
    w = aziende.pesi_stimati({"NVDA": 5e12, "AAPL": 4e12, "X": None}, ("NVDA", 5.0))
    assert abs(w["AAPL"] - 4.0) < 1e-9 and "X" not in w
    rows = [{"stato": 1, "peso": 5.0}, {"stato": 0, "peso": 3.0}, {"stato": -1, "peso": 2.0}, {"sym": "Y", "errore": "x"}]
    r = aziende.riepilogo(rows)
    assert (r["migliora"], r["stabile"], r["peggiora"], r["n"]) == (1, 1, 1, 3) and r["peso_migliora"] == 5.0
    assert "Non ci sono ancora dati" in aziende.html({})


def test_platt_non_inverte_e_recessioni_nber():
    from armor import ricerca
    cal = ricerca._platt(np.array([0.9, 0.8, 0.2, 0.1] * 10), np.array([0, 0, 1, 1] * 10))   # relazione invertita: niente taratura
    assert np.allclose(cal(np.array([0.3, 0.7])), [0.3, 0.7])
    idx = pd.date_range("2007-01-31", "2007-12-31", freq="ME")
    r = ricerca.recessione_entro(idx, 12, load=lambda k: pd.Series(dtype=float))
    assert r.iloc[0] == 1.0   # recessione NBER da dicembre 2007


def test_prova_finale_una_sola_volta(tmp_path, monkeypatch):
    from armor import ricerca
    monkeypatch.setattr(ricerca, "OUT", tmp_path)
    (tmp_path / "prova_finale.json").write_text('{"adottati": [], "anni": "2019-2026"}', encoding="utf-8")
    assert ricerca.prova_finale(save=False)["anni"] == "2019-2026"      # già fatta: si rilegge, non si rifà


def test_esegui_oggi_usa_solo_esiti_chiusi():
    from armor import ricerca
    idx = pd.date_range("1990-01-31", "2020-12-31", freq="ME")
    X = pd.DataFrame({"a": np.arange(len(idx), dtype=float)}, index=idx)
    y = pd.Series((np.arange(len(idx)) % 3 == 0).astype(float), index=idx)
    visti = {}

    def fp(tr, te, s):
        visti["max_tr"] = X.index[tr].max()
        return np.array([0.5])
    assert ricerca._esegui(fp, X, y, 12, (2020, 2020), True, None, oggi=True) == 0.5
    assert visti["max_tr"] + pd.DateOffset(months=12) < idx[-1]


def test_box_ciclico_rende_html():
    from armor import ciclico
    d = {"date": "2026-11-08", "accesi": 1, "totale": 2, "percentile_accesi": 40,
         "segnali": [{"segnale": "CAPE sopra 30", "valore": 40.0, "acceso": True}, {"segnale": "VIX sopra 30", "valore": 20.0, "acceso": False}],
         "analoghi": {"k": 2, "mesi": [{"mese": "2000-01", "ret_12": -5.0}, {"mese": "2018-01", "ret_12": 3.0}], "rialzo_12_su_k": 1,
                      "mediana_12": -1.0, "p10_12": -5.0, "p90_12": 3.0, "calo10_12_su_k": 1}}
    assert "1 segnali accesi su 2" in ciclico.box_rischio(d) and "2000-01" in ciclico.box_simili(d)


def test_aziende_semestrale_e_confronto_precedente():
    from armor import aziende
    semi = _yf_frame({"Total Revenue": [50, 45, 48], "Net Income": [5, 4, 5]}, ["2026-06-30", "2025-12-31", "2025-06-30"])
    r = aziende.analizza(inc_q=semi)
    assert r["q"]["mesi"] == 6 and r["q"]["tipo"] == "semestre" and r["q"]["periodo"] == "gen-giu 2026" and r["q"]["conf"] == "anno"
    assert r["rev_12m"] == 95                                       # ultimi due semestri
    q4 = _yf_frame({"Total Revenue": [30, 25, 24, 23]}, ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"])
    ann = _yf_frame({"Total Revenue": [100, 90]}, ["2025-12-31", "2024-12-31"])
    r2 = aziende.analizza(inc_q=q4, inc_a=ann)
    assert r2["q"]["conf"] == "precedente" and r2["q"]["periodo_conf"] == "apr-giu 2026"
    assert r2["base"] == "anno" and abs(r2["rev_g"] - 100 / 9) < 1e-9       # etichetta sull'anno fiscale se manca lo stesso trimestre
    assert aziende.etichetta_periodo("2026-11-02", 3) == "ago-ott 2026"     # trimestre fiscale che finisce all'inizio di novembre


def test_valutazione_e_rpo_sec():
    from armor import aziende
    js = {"units": {"USD": [{"end": "2025-09-30", "val": 300e9, "form": "10-Q"}, {"end": "2024-09-30", "val": 200e9, "form": "10-Q"},
                            {"end": "2025-06-30", "val": 280e9, "form": "10-Q"}]}}
    rp = aziende.parse_rpo(js)
    assert rp["valore"] == 300e9 and rp["data"] == "2025-09-30" and abs(rp["crescita"] - 50) < 1e-9
    rp["usd"] = rp["valore"]
    v = aziende.valutazione(3000e9, 300e9, 1.0, rp)
    assert abs(v["ps"] - 10) < 1e-9 and abs(v["ps_rpo"] - 5) < 1e-9 and abs(v["rpo_anni"] - 1) < 1e-9
    assert aziende.parse_rpo({}) is None


def test_vwce_sedi_serali_vince_ultimo_scambio():
    from armor import live
    js = {"quoteList": {"list": [
        {"market": {"name": "Lang & Schwarz"}, "last": 165.62, "datetimeLast": "2023-11-14T22:59:30.000+01:00", "isoCurrency": "EUR", "previousLast": 164.9},
        {"market": {"name": "Tradegate"}, "last": 165.55, "datetimeLast": "2023-11-14T21:58:00.000+01:00", "isoCurrency": "EUR"},
        {"market": {"name": "NYSE"}, "last": 180.0, "datetimeLast": "2023-11-14T21:58:00.000+01:00", "isoCurrency": "USD"}]}}
    v = live.parse_venues(js, "onvista")
    assert {x["venue"] for x in v} == {"Lang & Schwarz", "Tradegate"}                     # quotazioni in dollari scartate
    assert v[0]["time"] == "2023-11-14T21:59:30Z"
    day = 86400
    base = 1_700_000_000 // day * day
    yah = {"chart": {"result": [{"meta": {"gmtoffset": 0, "currentTradingPeriod": {"regular": {"start": 0, "end": 1}}},
                                 "timestamp": [base - day + 100, base + 16 * 3600], "indicators": {"quote": [{"close": [164.5, 165.1]}]}}]}}
    q = live.best_vwce(lambda s: yah if s == "VWCE.DE" else (_ for _ in ()).throw(RuntimeError("404")), [], v)
    assert q["venue"] == "Lang & Schwarz" and abs(q["price"] - 165.62) < 1e-9 and abs(q["chg"] - (165.62 / 164.9 - 1)) < 1e-12
    # ha vinto una sede serale: lo storico per i grafici 1 ora / 6 ore / 1 giorno viene da Yahoo e finisce con il prezzo serale
    assert q["_pts"][-1][1] == 165.62 and q["_pts"][0][1] == 164.5 and len(q["_pts"]) == 3
    tg = live.parse_tradegate({"last": "165,40", "executions": 12, "close": "164,80"}, now=pd.Timestamp("2023-11-14 23:30", tz="Europe/Berlin"))
    assert tg[0]["price"] == 165.4 and tg[0]["time"] == "2023-11-14T21:00:00Z"            # mercato chiuso: ora delle 22:00
    assert live.parse_tradegate({"last": "165,40", "executions": 0}) == []


def test_campioni_regola_e_coerenza():
    from armor import campioni
    def row(model, hz, thr, b1, b2, auc=0.7, bss=None):
        return {"set": "modelli", "kind": "down", "model": model, "hz": hz, "thr": thr, "bss_2000_12": b1, "bss_2013_26": b2, "auc": auc,
                "bss": bss if bss is not None else (b1 + b2) / 2}
    m = [row("A1", "1m", 10, 0.06, 0.04), row("FHS", "1m", 10, 0.11, 0.046), row("FHS+VIX", "1m", 10, 0.11, 0.052),
         row("A1", "1m", 5, 0.04, 0.03), row("FHS", "1m", 5, 0.05, 0.04), row("FHS+VIX", "1m", 5, 0.05, 0.04),
         row("A1", "6m", 10, 0.077, -0.077), row("FHS", "6m", 10, 0.05, -0.01)]
    s = campioni.scegli(m)
    assert s["1m"]["motore"] == "FHS+VIX" and s["6m"]["motore"] == "A1" and s["10g"]["motore"] == "A1"
    pred = {"3m": {"p": {10: 0.24, 15: 0.13}, "base": {10: 0.15, 15: 0.07}, "ratio": 1.6, "level": "Elevato"},
            "6m": {"p": {10: 0.15, 20: 0.04}, "base": {10: 0.25, 20: 0.06}, "ratio": 0.6, "level": "Basso"}}
    campioni.coerenza(pred)
    assert pred["6m"]["p"][10] == 0.24 and pred["6m"]["coerenza"]
    fake = lambda p, date=None, sims=0, seed=0, vix=None, w=0: {"1m": {"down": {5: {"p": 0.3}, 10: {"p": 0.1}}}}
    pr = {"1m": {"p": {5: 0.17, 10: 0.03}, "base": {5: 0.19, 10: 0.05}, "ratio": 0.6, "level": "Normale"}}
    out, mid = campioni.applica(pr, None, "2026-11-06", "A1", {"orizzonti": {"1m": {"motore": "FHS"}}}, fhs_fn=fake)
    assert out["1m"]["p"][10] == 0.1 and out["1m"]["p_a1"][10] == 0.03 and mid == "A1+FHS(1m)"


def test_lista_semafori_e_link():
    from armor import semafori
    t = semafori.cliccabile("<b>Semafori:</b> 8 rossi, 16 gialli, 35 verdi.")
    assert "data-semlist='ba'" in t and "data-semlist='all'" in t and ">8 rossi<" in t
    items = [{"key": "vix", "name": "VIX", "group": "Paura", "value": 31.0, "dec": 1, "unit": "", "light": "ba", "date": "06/11/2026", "pct": 95.0, "zones": "z"},
             {"key": "t10y3m", "name": "Curva", "group": "Tassi", "value": 0.6, "dec": 2, "unit": "", "light": "ok", "date": "06/11/2026", "pct": None, "zones": "z"}]
    h = semafori.lista_html(items)
    assert "id='semmod'" in h and "data-sml='ba'" in h and "data-sml='ok'" in h and "data-sml='wa'" not in h and "data-chart='vix'" in h


def test_patch26_a1_resta_principale_sfidante_affiancato():
    from armor import campioni, chiaro
    fake = lambda p, date=None, sims=0, seed=0, vix=None, w=0: {"1m": {"down": {5: {"p": 0.30}, 10: {"p": 0.11}}}, "3m": {"down": {10: {"p": 0.24}}}}
    pr = {"1m": {"p": {5: 0.17, 10: 0.03}, "base": {5: 0.19, 10: 0.05}, "ratio": 0.6, "level": "Normale"},
          "3m": {"p": {10: 0.08}, "base": {10: 0.15}, "ratio": 0.5, "level": "Basso"}}
    out = campioni.sfidante(pr, None, "2026-11-06", fhs_fn=fake, vix=25.0)
    assert out["1m"]["p"][10] == 0.03 and out["3m"]["p"][10] == 0.08            # A1 non cambia
    assert out["1m"]["sfidante"]["p"][10] == 0.11 and out["1m"]["sfidante"]["div"] is True
    assert out["3m"]["sfidante"]["div"] is True
    assert campioni.divergenza(0.20, 0.24) is False and campioni.divergenza(0.02, 0.06) is False and campioni.divergenza(0.10, 0.17) is False
    assert campioni.divergenza(0.30, 0.10) is True
    # controllo di coerenza: avvisa, non modifica
    pc = {"3m": {"p": {10: 0.24}}, "6m": {"p": {10: 0.15}}}
    av = campioni.avvisi_coerenza(pc)
    assert av and pc["6m"]["p"][10] == 0.15
    assert campioni.avvisi_coerenza({"3m": {"p": {10: 0.1}}, "6m": {"p": {10: 0.2}}}) == []
    h = chiaro.horizon_simple("1m", {**out["1m"], "ratio": 0.6}, {"up": {10: {"p": 0.1, "base": 0.1}}}, 100.0, None, "")
    assert "Sperimentale" in h and "Divergenza" in h


def test_verifica_strumenti_su_dati_sintetici():
    import numpy as np
    from armor import verifica as V
    rng = np.random.default_rng(1)
    n = 600
    # bootstrap: un modello davvero migliore ha intervallo tutto negativo; due modelli uguali includono lo zero
    base = rng.random(n)
    a = (base - 0.5) ** 2 + 0.10 + rng.normal(0, 0.05, n)
    r1 = V.boot_diff(a - 0.05, a, 4.0, reps=500)
    assert r1["hi"] < 0 and abs(r1["diff"] + 0.05) < 1e-9
    r2 = V.boot_diff(a, a + rng.normal(0, 0.05, n), 4.0, reps=500)
    assert r2["lo"] < 0 < r2["hi"]
    # finestre non sovrapposte: distanza minima h tra le date scelte, più sfasamenti
    pos = np.arange(0, 1000, 5)
    subs = V.sottocampioni(pos, 21)
    assert len(subs) >= 4 and all((np.diff(pos[s]) >= 21).all() for s in subs)
    # episodi: giorni con evento vicini = uno stesso episodio
    y = np.zeros(400); ev = [10, 11, 12, 100, 101, 300]
    y[ev] = 1
    assert V.episodi(np.arange(400), y, 21) == {"giorni": 6, "episodi": 3}
    # Diebold-Mariano: perdite identiche = nessun risultato; differenza netta = p piccolo
    assert V.dm_test(a, a, 3)["p"] != V.dm_test(a, a, 3)["p"]
    assert V.dm_test(a - 0.05 + rng.normal(0, 0.02, n), a, 3)["p"] < 0.01
    # Holm: esempio noto
    h = V.holm({"x": 0.01, "y": 0.04, "z": 0.03})
    assert abs(h["x"] - 0.03) < 1e-12 and abs(h["z"] - 0.06) < 1e-12 and abs(h["y"] - 0.06) < 1e-12
    # PBO: configurazioni casuali = circa 0,5; una configurazione sempre migliore = quasi 0
    rnd = rng.normal(0, 1, (160, 20))
    assert 0.3 < V.pbo_cscv(rnd)["pbo"] < 0.7
    dom = rnd.copy(); dom[:, 3] += 3.0
    assert V.pbo_cscv(dom)["pbo"] < 0.05
    # pendenza di calibrazione: probabilità vere ≈ 1, probabilità troppo estreme < 1
    p = rng.uniform(0.02, 0.6, 20000); yy = (rng.random(20000) < p).astype(float)
    assert 0.85 < V.calib_slope(p, yy) < 1.15
    pe = 1 / (1 + np.exp(-2.5 * np.log(p / (1 - p))))
    assert V.calib_slope(pe, yy) < 0.6
    # copertura, CRPS e QLIKE su casi calcolabili a mano
    assert V.copertura([0, 0, 0, 0], [1, 1, 1, 1], [0.5, 0.5, 2, -1]) == 0.5
    assert abs(V.crps_quantili([0.5], [[0.0]], [2.0]) - 2.0) < 1e-12      # pinball(0,5)=1·... 2·0,5·2 = 2
    assert V.qlike([1.0, 4.0], [1.0, 4.0]) == 0.0 and V.qlike([1.0], [2.0]) > 0
    # BSS: modello uguale alla frequenza = 0
    yy2 = (rng.random(500) < 0.2).astype(float)
    assert abs(V.bss(np.full(500, 0.2), yy2, np.full(500, 0.2))) < 1e-12


def test_verifica_regola_adozione_e_confronto():
    import numpy as np
    import pandas as pd
    from armor import verifica as V
    rng = np.random.default_rng(3)
    n = 1700   # 1994-2026 con una data ogni 5 sedute
    idx = pd.bdate_range("1994-01-03", periods=n * 5)[::5]
    pos = np.arange(n) * 5
    pv = rng.uniform(0.03, 0.4, n)
    y = (rng.random(n) < pv).astype(float)              # il modello «vero» conosce pv
    d = V.prepara(idx, pos, y, np.full(n, y.mean()), {"A1": np.clip(pv + rng.normal(0, 0.12, n), 0.01, 0.99), "VAR": pv})
    r = V.valuta_modello(d, "VAR", 21, 5, reps=300)
    assert r["vs_ref"]["intero"]["hi"] < 0 and r["bss"] > 0 and r["non_sovrapposti"]["sfasamenti"] >= 4
    ok = V.regola_adozione(r, 0.80, 0.2, 0.01)
    assert ok["passa"] is True, ok
    assert V.regola_adozione(r, 0.90, 0.2, 0.01)["passa"] is False         # copertura fuori 77-83%
    assert V.regola_adozione(r, 0.80, 0.7, 0.01)["passa"] is False         # PBO troppo alto
    assert V.regola_adozione(r, 0.80, 0.2, 0.30)["passa"] is False         # Holm non superato
    assert V.regola_adozione(r, None, 0.2, 0.01)["passa"] is False         # non valutabile = non superata


def test_revisione_codice_definizioni_e_purge(monkeypatch):
    import numpy as np
    import pandas as pd
    from armor import features, store
    from armor.model import Engine
    # calo massimo = minimo delle h sedute SUCCESSIVE rispetto al prezzo di oggi (non il massimo drawdown): 100, 110, 99, 120, 100
    p = pd.Series([100.0, 110.0, 99.0, 120.0, 100.0, 100.0], index=pd.bdate_range("2024-01-01", periods=6))
    d = features.fwd_maxdd(p, 3)
    assert abs(d.iloc[0] - (-0.01)) < 1e-12 and abs(d.iloc[1] - (99 / 110 - 1)) < 1e-12 and d.iloc[2] == (100 / 99 - 1 if False else min(100 / 99 - 1, 0.0))
    assert d.iloc[-3:].isna().all()                       # senza esito noto non c'è etichetta
    # purge: l'addestramento a data `cut` non usa nessuna riga la cui finestra futura finisce dopo `cut`
    rng = np.random.default_rng(0)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 1500))), index=pd.bdate_range("2015-01-01", periods=1500))
    e = Engine(px)
    cut = px.index[1000]
    fit = e.fit(cut)
    for hz, n in {"1m": 21, "3m": 63}.items():
        ultima = px.index[1000 - n]
        atteso = int(((e.F.index <= ultima) & e.dd[hz].reindex(e.F.index).notna() & e.ret[hz].reindex(e.F.index).notna()).sum())
        assert fit["hz"][hz]["n"] == atteso
    # VWCE in euro: livello in dollari / F (dollari per euro). VT 120 USD con F = 1,20 → 100 EUR; con F = 1,25 → 96 EUR
    idx = pd.bdate_range("2019-01-01", periods=3)
    serie = {"vwce_de": pd.Series(dtype=float), "vt": pd.Series([120.0, 120.0, 120.0], index=idx), "eurusd": pd.Series([1.20, 1.25, 1.20], index=idx)}
    monkeypatch.setattr(store, "load", lambda sid: serie[sid])
    v = features.vwce_series()
    assert abs(v.iloc[0] - 100.0) < 1e-9 and abs(v.iloc[1] - 96.0) < 1e-9


def _stato_finto(z=None, omega=0.02, alpha=0.03, gamma=0.10, beta=0.88, mu=0.03):
    import numpy as np
    from armor import percorsi as P
    rho = alpha + gamma / 2 + beta
    par = {"omega": omega, "alpha": alpha, "gamma": gamma, "beta": beta, "nu": 7.0, "mu": mu, "persistence": rho,
           "z": z if z is not None else np.random.default_rng(5).standard_t(6, 5000) / np.sqrt(6 / 4), "theta": None}
    lr = omega / (1 - rho)
    return {"par": par, "s2_next": lr, "cap": lr * 6.0, "rho": rho, "s2_lr": lr, "emivita": float(np.log(0.5) / np.log(rho))}


def test_percorsi_coerenza_e_caso_deterministico():
    import numpy as np
    from armor import percorsi as P
    # caso deterministico: residui nulli → rendimento costante mu% al giorno → quantili tutti uguali, nessuna perdita
    st = _stato_finto(z=np.zeros(100), mu=0.04)
    res = P.riassumi(P.simula(st, 1.0, "T0", 500, 1))
    for hz, n in P.ORIZZONTI.items():
        atteso = np.exp(0.04 * n / 100) - 1
        assert all(abs(v - atteso) < 1e-9 for v in res[hz]["ret"].values())
        assert res[hz]["p_neg"] == 0 and all(p == 0 for p in res[hz]["down"].values()) and all(p == 0 for p in res[hz]["mdd"].values())
    # coerenza per costruzione: più lungo = non meno probabile; soglia più alta = non più probabile; drawdown ≥ perdita da oggi
    st = _stato_finto()
    for tail in ("T0", "T1", "T2", "T3"):
        res = P.riassumi(P.simula(st, st["s2_lr"] * 3, tail, 4000, 7))
        hz = sorted(P.ORIZZONTI, key=lambda k: P.ORIZZONTI[k])
        for kind in ("down", "mdd"):
            for t in P.SOGLIE:
                v = [res[h][kind][t] for h in hz]
                assert all(a <= b + 1e-12 for a, b in zip(v, v[1:])), (tail, kind, t, v)
            for h in hz:
                v = [res[h][kind][t] for t in P.SOGLIE]
                assert all(a >= b - 1e-12 for a, b in zip(v, v[1:]))
        for h in hz:
            for t in P.SOGLIE:
                assert res[h]["mdd"][t] >= res[h]["down"][t] - 1e-12
            q = list(res[h]["ret"].values())
            assert q == sorted(q)
            assert abs(res[h]["se"]["down"][10] - np.sqrt(res[h]["down"][10] * (1 - res[h]["down"][10]) / 4000)) < 1e-12


def test_percorsi_controllo_code_e_varianti():
    import numpy as np
    from armor import percorsi as P
    st = _stato_finto()
    s0 = st["cap"] * 8                                  # partenza estrema: il tetto T1 e l'ancoraggio T2 devono ridurre le code
    a = P.riassumi(P.simula(st, s0, "T0", 4000, 3), extra=True)["12m"]
    b = P.riassumi(P.simula(st, s0, "T1", 4000, 3), extra=True)["12m"]
    c = P.riassumi(P.simula(st, s0, "T2", 4000, 3), extra=True)["12m"]
    assert b["estremi"]["min"] > a["estremi"]["min"] and b["curtosi"] < a["curtosi"]
    assert c["ret"]["q95"] - c["ret"]["q5"] < a["ret"]["q95"] - a["ret"]["q5"]
    # stessi numeri casuali: con lo stesso seme e la stessa varianza il risultato è identico
    assert P.riassumi(P.simula(st, 1.0, "T1", 500, 9))["3m"] == P.riassumi(P.simula(st, 1.0, "T1", 500, 9))["3m"]
    # V0 / V1 / V2: V2 non esiste senza VIX3M; V1 sposta la varianza verso il VIX
    assert P.varianza_iniziale(st, "V2T0", 20.0, None) == (None, None)
    s_v0 = P.varianza_iniziale(st, "V0T0", 40.0, 30.0)[0]
    s_v1 = P.varianza_iniziale(st, "V1T0", 40.0, 30.0)[0]
    assert s_v1 != s_v0 and abs(s_v0 - st["s2_next"]) < 1e-12
    # V2: la media attesa dei giorni 1-21 coincide col bersaglio r21·VIX²/252, e quella dei giorni 22-63 con il bersaglio forward
    s0, m2 = P.varianza_iniziale(st, "V2T0", 20.0, 22.0, (0.8, 0.7))
    k = np.arange(63)
    ev = st["s2_lr"] + st["rho"] ** k * (s0 - st["s2_lr"])
    assert abs(ev[:21].mean() - 0.8 * 400 / 252) < 1e-9
    fwd = (63 * 22.0 ** 2 - 21 * 20.0 ** 2) / 42
    assert abs(ev[21:63].mean() * m2 - 0.7 * fwd / 252) < 1e-6 or m2 in (0.25, 4.0)
    # volatilità attesa a 252 sedute e persistenza registrate
    cv = P.curva_vol(st, st["s2_lr"] * 4)
    assert len(cv) == 252 and cv[0] > cv[-1] > np.sqrt(st["s2_lr"] * 252) * 0.99 and st["emivita"] > 10


def test_percorsi_rapporti_walk_forward_senza_futuro():
    import numpy as np
    import pandas as pd
    from armor import percorsi as P
    idx = pd.bdate_range("2000-01-03", periods=1800)
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0, 1.0, 1800), index=idx)
    vix = pd.Series(np.full(1800, 16.0), index=idx)
    d = P.rapporti_realizzata_implicita(r, vix, vix * 1.05)
    i = 1500
    # ritardo di 21 sedute: il rapporto «noto» alla posizione i usa solo date ≤ i−21, e cambiare i rendimenti futuri non lo modifica
    r2 = r.copy(); r2.iloc[i + 1:] = 10.0
    d2 = P.rapporti_realizzata_implicita(r2, vix, vix * 1.05)
    assert P._rapporto(d, i, "r21", 21) == P._rapporto(d2, i, "r21", 21)
    assert 0.5 <= P._rapporto(d, i, "r21", 21) <= 1.2
    assert P._rapporto(d, 100, "r21", 21) == 0.8                 # poche date: valore predefinito


def test_diario_v3_catena_esiti_e_manomissione(tmp_path):
    import numpy as np
    import pandas as pd
    from armor import journal3
    f = tmp_path / "j3.csv"
    p = pd.Series(100 * np.exp(np.cumsum(np.full(300, 0.001))), index=pd.bdate_range("2024-01-01", periods=300))
    a = str(p.index[10].date())
    assert journal3.append_previsione(a, "Percorsi", "V1T1", {"rho": 0.98}, {"vix": 20.0}, {"1m": {"p": 0.1}}, path=f, ts="2026-11-08T00:00:00Z") == 1
    assert journal3.append_previsione(a, "Percorsi", "V1T1", {}, {}, {}, path=f) == 0                      # idempotente
    assert journal3.append_previsione(a, "A1", "A1", {}, {}, {"1m": {"p": 0.05}}, path=f, ts="2026-11-08T00:00:01Z") == 1
    ok, _ = journal3.verify(f)
    assert ok
    n = journal3.update_outcomes(p, path=f, ts="2026-11-08T01:00:00Z")
    assert n == 12 and journal3.update_outcomes(p, path=f) == 0                                            # 6 orizzonti × 2 modelli, una volta sola
    e = journal3.read(f)
    r = e[(e["kind"] == "esito") & (e["model"] == "Percorsi") & (e["horizon"] == "1m")].iloc[0]
    import json
    x = json.loads(r.risultati)
    assert abs(x["rendimento"] - (np.exp(0.001 * 21) - 1)) < 1e-9 and x["mdd"] == 0.0
    assert journal3.verify(f)[0]
    # manomissione di una riga = catena spezzata
    t = f.read_text(encoding="utf-8").replace('""vix"":20.0', '""vix"":99.0')
    f.write_text(t, encoding="utf-8")
    assert journal3.verify(f)[0] is False


def test_adozione_applica_solo_dove_promossa():
    from armor import percorsi as P
    pred = {"1m": {"p": {5: 0.2, 10: 0.04}, "base": {5: 0.19, 10: 0.05}, "ratio": 0.8, "level": "Normale"},
            "3m": {"p": {10: 0.10, 15: 0.05}, "base": {10: 0.15, 15: 0.07}, "ratio": 0.7, "level": "Normale"}}
    res = {"1m": {"down": {5: 0.30, 10: 0.12}}, "3m": {"down": {10: 0.30, 15: 0.18}}}
    o = {"adottate": {"1m": "V1T1"}, "varianti": {"V1T1": res}}
    out, mid = P.applica_adozione(pred, o, "A1")
    assert out["1m"]["p"][10] == 0.12 and out["1m"]["p_a1"][10] == 0.04 and out["1m"]["adottato"] and out["1m"]["motore"] == "Percorsi V1T1"
    assert out["3m"]["p"][10] == 0.10 and "adottato" not in out["3m"] and mid == "A1+PERC(1m)"
    assert P.applica_adozione({"1m": {"p": {10: 0.1}}}, {"adottate": {}}, "A1")[1] == "A1"


def test_percorsi_html_legge_json_con_chiavi_testo(tmp_path, monkeypatch):
    import json
    import numpy as np
    from armor import percorsi as P
    st = _stato_finto()
    res = P.riassumi(P.simula(st, st["s2_lr"], "T1", 300, 1), extra=True)
    res["_diag"] = {"persistenza": 0.98, "emivita": 33.0, "vol_lungo": 0.16, "n_percorsi": 300}
    res["_vol"] = [0.2, 0.18, 0.17]
    basi = {hz: {"p_neg": 0.3, "down10": 0.1, "mdd10": 0.2} for hz in P.ORIZZONTI}
    f = tmp_path / "oggi.json"
    f.write_text(json.dumps({"mostrata": "V1T1", "adottate": {}, "varianti": {"V1T1": res}, "basi": basi}, default=float), encoding="utf-8")   # le chiavi numeriche diventano testo
    monkeypatch.setattr(P, "OGGI", f)
    h = P.html()
    assert "Sperimentale" in h and "1 anno" in h and "Chiudere in negativo" in h


def test_serie_euro_conversione_collegamento_e_segmenti(monkeypatch):
    import numpy as np
    import pandas as pd
    from armor import serie_eur as S, store
    idx = pd.bdate_range("2019-01-01", periods=6)
    F = pd.Series([1.20, 1.25, 1.25, 1.10, 1.10, 1.10], index=idx)
    usd = pd.Series([120.0, 125.0, 125.0, 121.0, 121.0, 121.0], index=idx)
    eur = S.converti(usd, F)
    assert np.allclose(eur.values, [100.0, 100.0, 100.0, 110.0, 110.0, 110.0])        # livello / F, caso numerico con F noto
    # rendimento in euro: 1 + r€ = (1 + r$)·F(t−1)/F(t): VT +4,2% in dollari mentre l'euro sale da 1,25 a 1,10 → +10%
    assert abs((eur.iloc[3] / eur.iloc[2]) - (usd.iloc[3] / usd.iloc[2]) * F.iloc[2] / F.iloc[3]) < 1e-12
    # collegamento: un solo fattore di scala, il reale resta com'è
    reale = pd.Series([200.0, 202.0], index=idx[4:])
    c = S.collega(eur, reale)
    assert c.iloc[-1] == 202.0 and abs(c.loc[idx[3]] - 110.0 * (200.0 / 110.0)) < 1e-9 and len(c) == 6
    # segmenti dichiarati e S&P in euro etichettato solo come robustezza
    ser = {"dexuseu": pd.Series(dtype=float), "eurusd": pd.Series(np.full(300, 1.1), index=pd.bdate_range("2008-01-01", periods=300)),
           "vt": pd.Series(np.linspace(30, 40, 200), index=pd.bdate_range("2008-06-01", periods=200)),
           "sp500": pd.Series(np.linspace(1000, 1500, 300), index=pd.bdate_range("2008-01-01", periods=300)),
           "vwce_de": pd.Series(np.linspace(60, 66, 50), index=pd.bdate_range("2009-01-01", periods=50))}
    monkeypatch.setattr(store, "load", lambda sid: ser[sid])
    s = S.costruisci()
    ids = [x["id"] for x in s["segmenti"]]
    assert ids == ["b", "a", "c"] and "solo robustezza" in s["segmenti"][2]["nome"] and s["fonte_cambio"] == "Yahoo EURUSD=X"
    assert s["vwce_eur"].index[0] == s["vt_eur"].index[0] and s["vwce_eur"].loc[ser["vwce_de"].index[0]] == 60.0


def test_affidabilita_segnali_e_livello(monkeypatch):
    import numpy as np
    import pandas as pd
    from armor import affidabilita as A
    # disaccordo: si accende solo con la divergenza (≥5 punti e rapporto ≥2), non valutabile senza sfidante
    pred = {"1m": {"p": {10: 0.03}, "sfidante": {"p": {10: 0.11}, "div": True}}, "3m": {"p": {10: 0.2}, "sfidante": {"p": {10: 0.22}, "div": False}}}
    assert A.segnale_disaccordo(pred)["acceso"] is True
    assert A.segnale_disaccordo({"1m": {"p": {10: 0.03}, "sfidante": {"p": {10: 0.04}, "div": False}}})["acceso"] is False
    assert A.segnale_disaccordo({"1m": {"p": {10: 0.03}}})["acceso"] is None
    # dati vecchi: una serie rossa accende il segnale
    assert A.segnale_dati([{"light": "ok", "name": "a"}, {"light": "ba", "name": "VIX"}])["acceso"] is True
    assert A.segnale_dati([{"light": "ok", "name": "a"}, {"light": "wa", "name": "b"}])["acceso"] is False
    # situazione mai vista: un punto lontano dalla storia supera il 99° percentile, uno tipico no
    rng = np.random.default_rng(4)
    X = pd.DataFrame(rng.normal(0, 1, (3000, 4)))
    d_tip, soglia, n = A.mahalanobis(X, np.zeros(4))
    d_str, _, _ = A.mahalanobis(X, np.full(4, 6.0))
    assert d_tip < soglia < d_str and n == 3000 and 2.5 < soglia < 4.5
    # errori recenti: con meno di 12 finestre non è valutabile; con 12 finestre cattive si accende, con 12 buone no
    idx = pd.bdate_range("2020-01-01", periods=1500)
    p = pd.Series(100 * np.exp(np.cumsum(np.full(1500, 0.0005))), index=idx)          # sempre in salita: nessun calo
    def diario(prob, k):
        return pd.DataFrame({"horizon": "1m", "model": "A1", "asof": [str(idx[i * 21].date()) for i in range(k)], "thr1": 10, "p1": prob, "base1": 0.10})
    assert A.segnale_errori(diario(0.5, 5), p)["acceso"] is None
    assert A.segnale_errori(diario(0.5, 14), p)["acceso"] is True        # probabilità alta, nessun calo: peggio della frequenza
    assert A.segnale_errori(diario(0.01, 14), p)["acceso"] is False
    # livello: 0 = alta, 1 = media, ≥2 = bassa con avviso; un segnale non valutabile non conta
    s = lambda a: {"id": "dati", "acceso": a, "dettaglio": "x"}
    assert A.livello([s(False), s(None)])["livello"] == "alta"
    assert A.livello([s(True), s(False)])["livello"] == "media"
    l = A.livello([s(True), s(True), s(False)])
    assert l["livello"] == "bassa" and l["avviso"].startswith("Stima poco affidabile")


def test_affidabilita_instabilita_su_finestre_diverse(monkeypatch):
    import numpy as np
    import pandas as pd
    from armor import affidabilita as A, fhs
    idx = pd.bdate_range("1995-01-02", periods=5000)
    p = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(8).normal(0.0003, 0.01, 5000))), index=idx)
    def fake(pp, sims=0, seed=0, fit_start="1950-01-01", **k):
        v = {"1950-01-01": 0.10, "1990-01-01": 0.10}.get(fit_start, 0.20)
        return {hz: {"down": {10: {"p": v}, 5: {"p": v}}} for hz in ("1m", "3m")}
    monkeypatch.setattr(fhs, "forecast", fake)
    r = A.segnale_instabilita(p, p.index[-1])
    assert r["acceso"] is True and "10%" in r["dettaglio"] and "20%" in r["dettaglio"]
    monkeypatch.setattr(fhs, "forecast", lambda pp, sims=0, seed=0, fit_start="", **k: {hz: {"down": {10: {"p": 0.1}, 5: {"p": 0.1}}} for hz in ("1m", "3m")})
    assert A.segnale_instabilita(p, p.index[-1])["acceso"] is False


def test_pac_simulatore_caso_deterministico_e_prudente():
    import numpy as np
    from armor import pacsim
    r = 50                                              # +0,5% al mese, costante
    g = 1.005
    C, M, n = 1000.0, 100.0, 60
    atteso = C * g ** n + M * sum(g ** k for k in range(1, n + 1))
    s = pacsim.patrimonio([r] * n, C, M)["serie"]
    assert abs(s[-1]["valore"] - atteso) < 1e-6 and s[-1]["versato"] == C + M * n and s[-1]["mdd"] == 0
    # TER: il patrimonio scende del costo annuo; costo per acquisto: ogni rata netta; scenario prudente: 3 punti all'anno in meno
    f = 0.9986 ** (1 / 12)
    s2 = pacsim.patrimonio([r] * 12, 0.0, 100.0, ter=0.14)["serie"][-1]["valore"]
    assert abs(s2 - 100 * sum((g * f) ** k for k in range(1, 13))) < 1e-6
    assert abs(pacsim.patrimonio([r] * 1, 0.0, 100.0, costo=2.0)["serie"][0]["valore"] - 98 * g) < 1e-9
    p = pacsim.patrimonio([r] * 12, 1000.0, 0.0, prudente=True)["serie"][-1]["valore"]
    assert abs(p - 1000 * (g * 0.97 ** (1 / 12)) ** 12) < 1e-6
    # giorno di acquisto: più tardi nel mese = meno rendimento nel primo mese
    assert pacsim.patrimonio([100], 0, 100, giorno=28)["serie"][0]["valore"] < pacsim.patrimonio([100], 0, 100, giorno=1)["serie"][0]["valore"]
    # sospensione: liquidità ferma = soldi non investiti (senza rendimento); investita alla ripresa = lump sum con un solo costo
    fer = pacsim.patrimonio([r] * 6, 0.0, 100.0, sospendi=3, modo="ferma")["serie"][-1]["valore"]
    inv = pacsim.patrimonio([r] * 6, 0.0, 100.0, sospendi=3, modo="inv")["serie"][-1]["valore"]
    assert abs(fer - (300.0 + 100 * sum(g ** k for k in range(1, 4)))) < 1e-9 and inv > fer
    # drawdown del patrimonio: un calo del 10% dopo un mese di salita
    m = pacsim.patrimonio([0, -1000], 1000.0, 0.0)["serie"]
    assert abs(m[-1]["mdd"] + 0.10) < 1e-12


def test_pac_percorsi_e_bootstrap_mensile():
    import numpy as np
    import pandas as pd
    from armor import pacsim
    idx = pd.bdate_range("2008-06-02", periods=4500)
    p = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0.0004, 0.01, 4500))), index=idx)
    d = pacsim.costruisci(p, n_paths=300, mesi=60, seme=5)
    a = np.array(d["paths"])
    assert a.shape == (300, 60) and d["ter"] == 0.14 and d["mesi_storici"] > 150
    assert a.min() > -9000 and a.max() < 20000                                  # nessun rendimento mensile oltre i limiti (−90% / +200%)
    d2 = pacsim.costruisci(p, n_paths=300, mesi=60, seme=5)
    assert d2["paths"] == d["paths"]                                            # seme fisso = stesso risultato


def test_pac_javascript_uguale_al_python():
    import numpy as np
    from armor import pacsim
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        br = pw.chromium.launch()
    except Exception:  # noqa: BLE001
        import pytest
        pytest.skip("browser non disponibile")
    try:
        pg = br.new_page()
        pg.set_content("<html><body>" + pacsim.HTML + pacsim.JS + "</body></html>")
        rng = np.random.default_rng(3)
        paths = np.rint(rng.normal(60, 450, (40, 60))).astype(int).tolist()
        o = {"C": 3000, "M": 150, "d": 15, "cost": 1.5, "ter": 0.14, "sosp": 3, "modo": "inv", "prud": True}
        pg.evaluate("d=>window.__pacsim.setData(d)", {"paths": paths, "prudente": 0.03, "n": 40, "mesi": 60, "mesi_storici": 200, "rendimento_storico_annuo": 0.1})
        js = pg.evaluate("o=>{const r=window.__pacsim.stat(o);return {w60:r[60].raw,w12:r[12].raw,d60:r[60].mddMed,below:r[60].below}}", o)
        py = [pacsim.patrimonio(x, 3000, 150, 15, 1.5, 0.14, True, 3, "inv")["serie"] for x in paths]
        assert np.allclose(js["w60"], [s[59]["valore"] for s in py], rtol=1e-9) and np.allclose(js["w12"], [s[11]["valore"] for s in py], rtol=1e-9)
        assert abs(js["d60"] - float(np.median([s[59]["mdd"] for s in py]))) < 1e-9
    finally:
        br.close(); pw.stop()


def test_pacsim_costo_storico():
    from armor import pacsim
    a = pacsim.patrimonio([0] * 3, 1000.0, 100.0)["serie"][-1]
    b = pacsim.patrimonio([0] * 3, 1000.0, 100.0, K=700.0)["serie"][-1]
    assert a["versato"] == 1300.0 and b["versato"] == 1000.0 and a["valore"] == b["valore"]
    assert "pskc" in pacsim.HTML and "o.K>0" in pacsim.JS


def test_vrp_componenti_e_regressioni():
    import numpy as np, pandas as pd
    from armor import vrp
    rng = np.random.default_rng(3)
    n = 1500
    idx = pd.bdate_range("2008-01-01", periods=n)
    c = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)
    o = c.shift(1).fillna(c.iloc[0]) * np.exp(rng.normal(0, 0.003, n))
    h = np.maximum(o, c) * 1.004
    l = np.minimum(o, c) * 0.996
    x = vrp.componenti(o, h, l, c)
    yz = vrp.yang_zhang(x).dropna()
    assert 100 < yz.mean() < 5000 and (yz > 0).all()           # %² annui (vol ~16%: ≈ 250-ish)
    vix = pd.Series(16.0, index=idx)
    t = vrp.tabella(x, vix)
    prev = vrp.previsioni_varianza(t)
    # nessun anticipo: la previsione alla data d non usa esiti oltre d-21 (cambiare il futuro non la cambia)
    t2 = t.copy(); t2.iloc[1300:, t2.columns.get_loc("y")] = 1e6
    prev2 = vrp.previsioni_varianza(t2)
    a, b = prev["HAR"].iloc[1200], prev2["HAR"].iloc[1200]
    assert np.isfinite(a) and abs(a - b) < 1e-9
    assert (prev["HAR"].dropna() >= vrp.FLOOR_VAR).all()
    st = {"rho": 0.989, "s2_lr": 1.0}
    s0 = vrp.s0_da_bersaglio(st, 400.0)
    ev = st["s2_lr"] + st["rho"] ** np.arange(21) * (s0 - st["s2_lr"])
    assert abs(ev.mean() * 252 - 400.0) < 1e-6
    assert "VIX" in vrp.html() or "non ancora" in vrp.html()


# ------------------------------------------------------------------ Patch 34: integrità, diagnostica, backup
def _diario_finto(tmp_path, n=4):
    from armor import journal3 as J
    f = tmp_path / "journal_v3.csv"
    for k in range(n):
        J.append_previsione(f"2026-11-{k + 2:02d}", "A1", "A1", {"m": 1}, {"i": k}, {"1m": {"p": {"10": 0.1 * k}}}, path=f, ts="2026-11-08T00:00:00Z")
    return f


def test_verifica_ok(tmp_path):
    from armor import journal3 as J
    f = _diario_finto(tmp_path)
    assert J.verifica_estrema(f) == (True, 4, None)
    assert J.verifica(f) == (True, 4, None)
    assert J.verifica_estrema(tmp_path / "non_esiste.csv") == (True, 0, None)


def test_verifica_rotta_prev_hash(tmp_path):
    from armor import journal3 as J
    f = _diario_finto(tmp_path)
    df = J.read(f)
    df.loc[2, "prev_hash"] = "0" * 20
    df.to_csv(f, index=False)
    ok, riga, err = J.verifica_estrema(f)
    assert (ok, riga, err) == (False, 4, "prev_hash non corrisponde")      # riga 4 del file = terza riga di dati


def test_verifica_rotta_hash(tmp_path):
    from armor import journal3 as J
    f = _diario_finto(tmp_path)
    df = J.read(f)
    df.loc[1, "risultati"] = df.loc[1, "risultati"].replace("0.1", "0.9")
    df.to_csv(f, index=False)
    ok, riga, err = J.verifica_estrema(f)
    assert (ok, riga, err) == (False, 3, "hash non corrisponde")


def test_jobs_esce_con_errore_se_diario_rotto(tmp_path, monkeypatch):
    import pytest
    from armor import jobs, journal3 as J
    f = _diario_finto(tmp_path)
    monkeypatch.setattr(J, "FILE", f)
    jobs.controllo_diario()                         # integro: nessuna eccezione
    df = J.read(f)
    df.loc[1, "model"] = "X"
    df.to_csv(f, index=False)
    with pytest.raises(SystemExit) as e:
        jobs.controllo_diario()
    assert e.value.code == 1


def test_diagnostica_heartbeat(tmp_path):
    from datetime import date
    from armor import diagnostica as D
    (tmp_path / "series").mkdir()
    (tmp_path / "series" / "sp500.csv").write_text("date,value\n2026-11-05,100\n2026-11-06,101\n")
    (tmp_path / "series" / "altra.csv").write_text("date,value\n2020-01-01,1\n")
    oggi = date(2026, 11, 11)      # mercoledì
    d = D.diagnostica_heartbeat(tmp_path, oggi)                      # diario assente/vuoto
    assert d["giorni_da_ultima"] is None and d["ultima_previsione"] is None
    _diario_finto(tmp_path, 1)                                       # asof 2026-11-02
    assert D.diagnostica_heartbeat(tmp_path, date(2026, 11, 2))["giorni_da_ultima"] == 0
    assert D.diagnostica_heartbeat(tmp_path, date(2026, 11, 9))["giorni_da_ultima"] == 5       # lun 2 → lun 9 = 5 giorni lavorativi
    assert D.diagnostica_heartbeat(tmp_path, date(2026, 11, 3))["giorni_da_ultima"] == 1
    # il weekend non conta: da venerdì a lunedì = 1
    assert D._lavorativi("2026-11-06", date(2026, 11, 9)) == 1
    st = {x["nome"]: x for x in d["fonti"]}
    assert st["sp500"]["stato"] == "warning" and st["sp500"]["giorni_ritardo"] == 5     # soglia 4 giorni
    assert st["altra"]["stato"] == "warning" and st["vix"]["stato"] == "errore"         # vix assente
    assert (tmp_path / "diagnostica.json").exists()
    assert "Diario fermo da 5 giorni" in D.badge({"giorni_da_ultima": 5, "fonti": []}) and "bad" in D.badge({"giorni_da_ultima": 5, "fonti": []})
    assert "warn" in D.badge({"giorni_da_ultima": 2, "fonti": []}) and "aggiornato oggi" in D.badge({"giorni_da_ultima": 0, "fonti": []})


def test_avvisi_ntfy_banner_issue(tmp_path, monkeypatch):
    from armor import diagnostica as D, store
    monkeypatch.setattr(store, "STATUS_FILE", tmp_path / "status.json")
    inviati, issues = [], []
    diag = {"giorni_da_ultima": 3, "oggi": "2026-11-11", "fonti": []}
    # senza ntfy: banner nello stato, nessuna issue sotto i 4 giorni
    r = D.avvisi(diag, env={}, send=lambda m, t: inviati.append(m) or 1, issue=lambda *a: issues.append(a) or "aperta")
    assert r["banner"] and not r["ntfy"] and r["issue"] is None
    assert store.read_status()["alert_diario"]["testo"].startswith("[Armor] Diario fermo da 3 giorni")
    # con ntfy: un solo invio al giorno
    r = D.avvisi(diag, env={"NTFY_TOPIC": "x"}, send=lambda m, t: inviati.append(m) or 1)
    r2 = D.avvisi(diag, env={"NTFY_TOPIC": "x"}, send=lambda m, t: inviati.append(m) or 1)
    assert r["ntfy"] and not r2["ntfy"] and len(inviati) == 1 and inviati[0][0]["priority"] == 4
    # 4 giorni con token: issue
    d4 = {**diag, "giorni_da_ultima": 4}
    r = D.avvisi(d4, env={"GITHUB_TOKEN": "t"}, issue=lambda *a: issues.append(a) or "aperta")
    assert r["issue"] == "aperta" and issues[0][2] == "[Armor] Diario fermo da 4 giorni"
    # rientro: l'avviso sparisce
    D.avvisi({"giorni_da_ultima": 0, "oggi": "2026-11-12", "fonti": []}, env={})
    assert "alert_diario" not in store.read_status()


def test_issue_non_duplicata():
    from datetime import date
    from armor import diagnostica as D

    class R:
        def __init__(self, j): self.j = j
        def json(self): return self.j
        def raise_for_status(self): pass
    chiamate = []
    esistente = [{"number": 7, "title": "[Armor] Diario fermo da 4 giorni", "updated_at": "2026-11-10T08:00:00Z"}]
    post = lambda url, **k: chiamate.append(url) or R({})
    assert D._http_issue("t", "a/b", "[Armor] Diario fermo da 5 giorni", "{}", date(2026, 11, 11), get=lambda *a, **k: R(esistente), post=post) == "commentata"
    assert chiamate[-1].endswith("/issues/7/comments")
    esistente[0]["updated_at"] = "2026-11-11T01:00:00Z"
    assert D._http_issue("t", "a/b", "x", "{}", date(2026, 11, 11), get=lambda *a, **k: R(esistente), post=post) == "esistente"
    assert D._http_issue("t", "a/b", "[Armor] Diario fermo da 4 giorni", "{}", date(2026, 11, 11), get=lambda *a, **k: R([]), post=post) == "aperta"


def test_backup_settimanale(tmp_path):
    from datetime import date, timedelta
    from armor import journal3 as J
    _diario_finto(tmp_path)
    cart = tmp_path / "journal_backups"
    lun = date(2026, 1, 5)
    assert J.backup_settimanale(lun, tmp_path) == "journal_v3_2026-02.csv"
    assert J.backup_settimanale(lun + timedelta(days=3), tmp_path) is None                   # stessa settimana ISO
    assert len(list(cart.glob("journal_v3_*.csv"))) == 1
    assert J.backup_settimanale(lun + timedelta(days=7), tmp_path) == "journal_v3_2026-03.csv"
    for k in range(2, 20):
        J.backup_settimanale(lun + timedelta(days=7 * k), tmp_path)
    files = sorted(cart.glob("journal_v3_*.csv"))
    assert len(files) == 12 and files[-1].name == "journal_v3_2026-21.csv" and files[0].name == "journal_v3_2026-10.csv"
    import json
    idx = json.loads((cart / "indice.json").read_text())
    assert len(idx) == 12 and idx[0]["n_righe"] == 4 and len(idx[0]["hash_ultima_riga"]) == 20


def test_status_stato_fonte_e_backoff(tmp_path, monkeypatch):
    import pandas as pd
    from armor import store, sources
    assert [sources.pausa(i) for i in range(3)] == [2, 4, 8]
    monkeypatch.setattr(store, "load", lambda sid: pd.Series(dtype=float))
    st = {}
    store.set_status(st, "x", False, "errore")
    assert st["x"]["stato"] == "mai scaricata"
    monkeypatch.setattr(store, "load", lambda sid: pd.Series([1.0], index=pd.to_datetime(["2026-11-05"])))
    store.set_status(st, "x", False, "errore")
    assert st["x"]["stato"] == "ritardo"
    store.set_status(st, "x", True)
    assert st["x"]["stato"] == "ok"


def test_affidabilita_html_chiaro(tmp_path, monkeypatch):
    import json
    from armor import affidabilita as A
    seg = [{"id": "disaccordo", "acceso": True, "dettaglio": "1 mese: calo ≥10% → A1 3%, sfidante 11%"}, {"id": "dati", "acceso": False, "dettaglio": "tutte le serie chiave sono regolari"},
           {"id": "mai_visto", "acceso": False, "dettaglio": "distanza dalla norma 4.1, limite 8.9"}, {"id": "errori", "acceso": None, "dettaglio": "non ancora valutabile"},
           {"id": "instabilita", "acceso": True, "dettaglio": "a 1 mese la probabilità va da 12% a 20%"}]
    ori = [{"hz": "1m", "soglia": 10, "a1": 0.03, "sfidante": 0.11, "normale": 0.05}]
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"asof": "2026-11-06", "segnali": seg, "livello": "bassa", "n_accesi": 2, "avviso": "x", "orizzonti": ori}))
    monkeypatch.setattr(A, "FILE", f)
    h = A.html()
    assert "Stima poco affidabile" in h and "Come muoverti" in h and "Cosa aspettarti" in h
    assert "da 3% a 11%" in h and "0,6× a 2,2× il normale" in h and "in attesa" in h
    f.write_text(json.dumps({"asof": "x", "segnali": seg[1:3], "livello": "alta", "n_accesi": 0, "avviso": ""}))
    assert "Stima affidabile" in A.html()


def test_traduzione_cache_e_fallback(tmp_path):
    import json
    from armor import traduzione as T
    chiamate = []

    def cattivo(t):
        chiamate.append(("cattivo", t))
        raise RuntimeError("giù")

    def buono(t):
        chiamate.append(("buono", t))
        return "IT: " + t
    c = tmp_path / "tr.json"
    r = T.traduci(["Stocks fall", "Stocks fall", "Fed warns"], c, servizi=(cattivo, buono), workers=1)
    assert r == {"Stocks fall": "IT: Stocks fall", "Fed warns": "IT: Fed warns"}      # il primo servizio fallisce, ripiega sul secondo
    assert len(json.loads(c.read_text(encoding="utf-8"))) == 2
    n = len(chiamate)
    T.traduci(["Stocks fall"], c, servizi=(cattivo, buono))
    assert len(chiamate) == n                                                          # già in cache: nessuna chiamata
    # nessun servizio risponde: il titolo resta com'è e non si solleva nulla
    news = {"items": [{"title": "Oil jumps"}, {"title": "Stocks fall"}]}
    assert T.applica(news, c, servizi=(cattivo,), tempo_max=5) == 1
    assert news["items"][0]["title"] == "Oil jumps" and news["items"][1]["title"] == "IT: Stocks fall" and news["items"][1]["title_en"] == "Stocks fall"
    assert news["traduzione"] == {"titoli_in_italiano": 1, "totale": 2}
    assert T.applica(news, c, servizi=(cattivo,)) == 1                                  # idempotente: l'originale è in title_en


def test_dock_colore_distinto():
    from armor import extra13
    assert "#dockbar{" in extra13.CSS and "background:#3b4fc4" in extra13.CSS.split("#dockbar{")[1].split("}")[0]


def test_archivio_dati_tabella_catalogo_e_live(tmp_path, monkeypatch):
    import pandas as pd
    from armor import archivio_dati as A, store
    idx = pd.bdate_range("2026-10-01", periods=10)
    serie = {"sp500": pd.Series(range(10), index=idx, dtype=float), "vix": pd.Series(20.0, index=idx), "vix6m": pd.Series(22.0, index=idx[3:])}
    monkeypatch.setattr(store, "load", lambda k: serie.get(k, pd.Series(dtype=float)))
    live = tmp_path / "live_daily.csv"
    monkeypatch.setattr(A, "LIVE_DAILY", live)
    monkeypatch.setattr(A, "OPZIONI", tmp_path / "no.csv")
    monkeypatch.setattr(A, "REGISTRO", tmp_path / "no2.csv")
    lv = {"quotes": {"vwce": {"price": 165.0, "time": "2026-10-09T20:00:00Z", "venue": "LS Exchange", "alts": {"Xetra": [165.2, "x"], "LS": [164.9, "y"]}},
                     "sp500": {"price": 7300.0}, "sp_fut": {"price": 7310.0}, "vix": {"price": 21.0}, "eurusd": {"price": 1.08}}}
    assert A.registra_live(lv, live) and A.registra_live(lv, live)                      # seconda scrittura nello stesso giorno: una sola riga
    d = pd.read_csv(live)
    assert len(d) == 1 and d.loc[0, "n_sedi"] == 2 and abs(d.loc[0, "spread_sedi_pct"] - (165.2 / 164.9 - 1) * 100) < 1e-3
    t = A.tabella(giorni=5)
    assert len(t) == 5 and t[("vol", "vix")].notna().all() and t[("sedi", "vw")].notna().sum() == 1
    cat = {r["nome"]: r for r in A.catalogo_righe()}
    r6 = cat["VIX e curva a termine (9 giorni, 3 e 6 mesi)"]
    assert r6["n"] == 7 and r6["da"] == "2026-10-06" and r6["tipo"] == "storico"
    h = A.html(giorni=5)
    assert "solo da oggi" in h and "a pagamento altrove" in h and "data-arcg='opz'" in h and "Scarica tutto" in h
    assert "date,vol_vix" in A.csv_text()


def test_riepilogo_opzioni_sintetico():
    import numpy as np
    import pandas as pd
    from armor import archive
    rows = []
    for e, g in (("2026-11-13", 7), ("2026-12-04", 28), ("2027-02-05", 90)):
        for k in range(60, 111, 5):
            for kind in ("C", "P"):
                rows.append({"type": kind, "expiry": e, "strike": float(k), "impliedVolatility": 0.2 + 0.001 * abs(100 - k) + 0.001 * g / 30, "volume": 10, "openInterest": 100})
    df = pd.DataFrame(rows)
    r = archive.riepilogo(df, 100.0, "2026-11-06")
    assert abs(r["iv_atm_30d"] - 0.2 - 0.001 * 28 / 30) < 1e-9 and r["put_skew_80"] > r["put_skew_90"] > 0
    assert r["giorni_breve"] == 7 and r["giorni_lunga"] == 91 and r["iv_atm_lunga"] > r["iv_atm_breve"] and r["n_contratti"] == len(df)
    assert not np.isnan(r["pc_volume"])


def test_pagina_live_e_archivio_nel_sito():
    from armor import livefeed, parts
    assert "api.onvista.de" in livefeed.JS and "LIVETICKS" in livefeed.JS and "15000" in livefeed.JS
    import inspect
    src = inspect.getsource(parts)
    assert "window.LIVETICKS" in src and "ARMOR_TICKS" in src and "api.onvista.de" not in src


# ---- patch 38: coerenza dei dati
def test_parse_ls_solo_feriali_e_senza_oggi():
    import json
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from armor import sources
    ms = lambda d: int(pd.Timestamp(d).value // 1_000_000)  # noqa: E731
    pts = [[ms("2026-11-05"), 163.53], [ms("2026-11-06"), 165.01], [ms("2026-11-07"), 165.01], [ms("2026-11-08"), 165.01], [ms("2026-11-09"), 165.47]]
    txt = json.dumps({"series": {"history": {"data": pts}}})
    s = sources.parse_ls(txt, datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    assert list(s.index.strftime("%Y-%m-%d")) == ["2026-11-05", "2026-11-06"] and s.iloc[-1] == 165.01
    s2 = sources.parse_ls(txt, datetime(2026, 11, 9, 23, 30, tzinfo=ZoneInfo("Europe/Berlin")))
    assert s2.index[-1] == pd.Timestamp("2026-11-09")


def test_trend_dated_usa_date_vere():
    from armor import cruscotto
    s = pd.Series([17.2, 19.42, 21.15, 20.83, 16.61, 28.18, 25.64], index=pd.to_datetime(
        ["2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]))
    h = cruscotto.trend_dated(s, 1, True)
    assert "Il 05/11" in h and "28,2" in h and "Il 30/10" in h and "Ieri" not in h and "data-h=" in h


def test_putcall_degenere_non_e_un_dato(tmp_path, monkeypatch):
    from armor import archive
    df = pd.DataFrame({"type": ["C", "P"], "expiry": ["2026-12-18"] * 2, "strike": [700, 700], "volume": [0, 0], "openInterest": [0, 0],
                       "impliedVolatility": [0.2, 0.2]})
    r = archive.riepilogo(df, 700.0, "2026-11-07")
    assert pd.isna(r["pc_open_interest"]) and pd.isna(r["pc_volume"])


def test_audit_confronta_con_riferimento():
    from armor import audit_dati
    ix = pd.to_datetime(["2026-11-05", "2026-11-06"])
    v = pd.Series([28.18, 25.64], index=ix)
    rif = pd.DataFrame({"close": [28.18, 28.0]}, index=ix)
    res = audit_dati.controlla(vix=v, sp=pd.Series([1.0, 2.0], index=ix), ls=pd.Series([1.0, 2.0], index=ix), xe=pd.Series(dtype=float), rif=rif)
    ok = {x["controllo"]: x["ok"] for x in res}
    assert ok["VIX 05/11"] and not ok["VIX 06/11"]


# ---- patch 40: grafico di confronto esteso
def test_parse_cboe_putcall():
    from armor import sources
    t = "Cboe Equity Put/Call Ratio\nx\nDATE,CALL,PUT,TOTAL,P/C Ratio\n11/1/2006,976510,623929,1600439,0.64\n11/2/2006,1100,900,2000,0.82\n"
    s = sources.parse_cboe_pc(t)
    assert len(s) == 2 and abs(s.iloc[0] - 0.64) < 1e-9


def test_previsti_aggrega():
    from armor import previsti
    righe = [{"cap": 100.0, "utile": 5.0, "ricavi": 50.0} for _ in range(120)]
    a = previsti.aggrega(righe)
    assert abs(a["pe_fwd"] - 20) < 1e-9 and abs(a["ps_fwd"] - 2) < 1e-9
    assert previsti.aggrega(righe[:10]) is None


def test_glossario_copre_tutte_le_serie():
    from armor import confronto, glossario_serie
    mancanti = [k for k, *_ in confronto.SERIES if glossario_serie.scheda(k) is None]
    assert not mancanti, mancanti


# ---- patch 41: semafori di oggi, cambi, schede mappa
def test_semafori_cambiati_e_storia(tmp_path, monkeypatch):
    from armor import semafori
    monkeypatch.setattr(semafori, "_storia_path", lambda: tmp_path / "s.csv")
    it = [{"key": "a", "name": "A", "group": "G1", "light": "ok", "value": 1.0, "dec": 1, "unit": "", "read": "r"},
          {"key": "b", "name": "B", "group": "G1", "light": "wa", "value": 2.0, "dec": 1, "unit": "", "read": "r"}]
    semafori.registra_colori(it, "2026-11-06")
    it[0] = dict(it[0], light="ba")
    semafori.registra_colori(it, "2026-11-09")
    semafori.registra_colori(it, "2026-11-09")   # idempotente
    ch, dt = semafori.cambiati(it, "2026-11-09")
    assert dt == "2026-11-06" and len(ch) == 1 and ch[0]["key"] == "a" and (ch[0]["da"], ch[0]["a"]) == ("ok", "ba")
    h = semafori.oggi_html(it, "2026-11-09")
    assert "Cambiati dal 06/11" in h and "data-sg='0'" in h


def test_weekend_options_date():
    from armor import archive
    assert archive.venerdi_se_weekend("2026-11-07") == "2026-11-06" and archive.venerdi_se_weekend("2026-11-09") == "2026-11-09"


def test_hero_trend_con_date():
    from armor import cruscotto
    h = pd.Series(range(40, 50), index=pd.bdate_range("2026-10-26", periods=10), dtype=float)
    out = cruscotto.hero_trend({"hist": h})
    assert "Il 05/11" in out and "Il 30/10" in out and "Ieri" not in out


# ---- patch 42: notizie
def test_novita_archivio_dedup_e_ordine(tmp_path):
    import json
    from datetime import datetime, timezone

    from armor import novita
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    mk = lambda t, ti, lb="neutro": {"title": ti, "title_en": "EN " + ti, "source": "S", "link": "http://x", "time": t, "kind": "macro", "group": "g", "themes": [], "label": lb}  # noqa: E731
    (tmp_path / "2026-11-07.json").write_text(json.dumps({"items": [mk("2026-11-07T10:00:00Z", "A", "negativo"), mk("2026-11-06T10:00:00Z", "B")]}))
    (tmp_path / "2026-11-08.json").write_text(json.dumps({"items": [mk("2026-11-07T10:00:00Z", "A", "positivo"), mk("2026-11-08T09:00:00Z", "C")]}))
    (tmp_path / "2026-09-01.json").write_text(json.dumps({"items": [mk("2026-09-01T10:00:00Z", "VECCHIA")]}))
    a = novita.archivio(30, now, tmp_path)
    assert [i["ti"] for i in a["items"]] == ["C", "A", "B"] and a["items"][1]["lb"] == "positivo"
    assert novita.etichetta_giorno("2026-11-09T09:20:00Z", now) == "oggi 10:20" and novita.etichetta_giorno("2026-11-08T09:20:00Z", now).startswith("ieri")


def test_ticker_items_notizie_recenti_prima():
    from datetime import datetime, timedelta, timezone

    from armor import cruscotto
    n = datetime.now(timezone.utc)
    it = lambda h, s: {"title": f"T{h}", "kind": "macro", "label": "neutro", "score": s, "time": (n - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")}  # noqa: E731
    out = cruscotto.ticker_items({"items": [it(30, 5), it(2, 1), it(10, 3)]}, [], None)
    assert [x["t"].split(" ", 2)[2] for x in out] == ["• T2", "• T10", "• T30"] and all(x["n"] == 1 for x in out)


def test_regime_pressione_e_percentile():
    from armor import tensione as t
    a = pd.Series([50.0, 50.0, 30.0, 45.0], index=pd.bdate_range("2020-01-01", periods=4))
    P = t.pressione(a)
    assert abs(P.iloc[0] - 10) < 1e-9 and abs(P.iloc[1] - (0.97 * 10 + 10)) < 1e-9
    assert abs(P.iloc[2] - 0.97 * P.iloc[1]) < 1e-9 and abs(P.iloc[3] - (0.97 * P.iloc[2] + 5)) < 1e-9
    s = pd.Series(np.arange(300, dtype=float), index=pd.bdate_range("2020-01-01", periods=300))
    pe = t.pct_espanso(s)
    assert pe.iloc[:249].isna().all() and abs(pe.iloc[-1] - 1.0) < 1e-9


def test_regime_no_lookahead_e_stato():
    from armor import tensione as t
    p = _prices(1500, seed=3)
    a = pd.Series(np.clip(40 + 15 * np.sin(np.arange(1500) / 80) + np.random.default_rng(2).normal(0, 3, 1500), 1, 99), index=p.index)
    full = t.variabili(a, p)
    cut = t.variabili(a.iloc[:900], p.iloc[:900])
    for c in ("min20", "ma60", "P", "Pn", "dd"):
        x, y = full[c].iloc[:900].values, cut[c].values
        assert np.allclose(x, y, equal_nan=True)
    st = t.stato_di(full)
    assert set(st.unique()) <= set(t.NOMI_STATO)
    assert (st[full["A"] < 35] == "calma").all()
    assert (full["V1"] <= (full["min20"] >= 45)).all()


def test_regime_esiti_e_episodi():
    from armor import tensione as t
    p = _prices(900, seed=5)
    o = t.esiti(p)
    i = 300
    fut = p.iloc[i + 1:i + 127]
    assert o["b"].iloc[i] == float(fut.min() / p.iloc[i] - 1 <= -0.10)
    assert o["a"].iloc[i] == float(fut.min() < p.iloc[i - 125:i + 1].min())
    assert o[["a", "b", "c"]].iloc[-5:].isna().all().all()
    cond = pd.Series(False, index=p.index)
    cond.iloc[100:110] = True
    cond.iloc[130:140] = True      # meno di 60 sedute dopo: stesso episodio
    cond.iloc[400:420] = True
    ep = t.episodi_di(cond, p)
    assert [e["inizio"] for e in ep] == [str(p.index[100].date()), str(p.index[400].date())]
    assert ep[1]["durata"] == 20
    km = t.kaplan_meier(ep, p)
    assert len(km) == 12 and all(km[i] <= km[i + 1] + 1e-9 for i in range(11))


def test_regime_frase_e_box():
    from armor import tensione as t
    o = {"data": "2026-11-06", "A": 50.3, "min20": 39.0, "ma60": 44.0, "Pn": 0.7, "dd": -0.02, "stato": "formazione", "sopra45": 12, "sopra40": 20, "v": {k: False for k in t.VARIANTI}}
    r = {"stati": {"tutto": {"formazione": {"n": 500, "a": 0.55, "b": 0.3}, "tutti": {"a": 0.32, "b": 0.28}}, "2013_oggi": {}}, "adozione": {"adottata": False}}
    h = t.box_oggi(o, r)
    assert "Tensione in formazione" in h and "Non verificato fuori campione" in h and "12" in h and "55%" in h


def test_mondo_rendimenti_eur_e_filtri():
    from armor import mondo
    idx = pd.bdate_range("2025-01-01", periods=300)
    s = pd.Series(100 * 1.001 ** np.arange(300), index=idx)
    fx = pd.Series(np.linspace(1.0, 1.2, 300), index=idx)    # euro che si rafforza: i dollari valgono meno
    loc, eur = mondo.rendimenti(s, fx, "USD")
    r1m = s.iloc[-1] / s[s.index <= idx[-1] - pd.Timedelta(days=30)].iloc[-1] - 1
    f0 = fx[fx.index <= idx[-1] - pd.Timedelta(days=30)].iloc[-1]
    assert abs(loc[2] - r1m) < 1e-4 and abs(eur[2] - ((1 + r1m) * f0 / fx.iloc[-1] - 1)) < 1e-4 and eur[2] < loc[2]
    assert abs(loc[0] - (s.iloc[-1] / s.iloc[-2] - 1)) < 1e-4 and loc[5] is not None
    l2, e2 = mondo.rendimenti(s, fx, "EUR")
    assert e2 == l2
    assert mondo.rendimenti(s.iloc[:10], fx, "USD") is None
    bad = s.copy()
    bad.iloc[100] = bad.iloc[99] * 5
    assert mondo.rendimenti(bad, fx, "USD") is None   # +400% in un giorno: scartato


def test_mondo_costruisci_e_pagina():
    from armor import mondo
    idx = pd.bdate_range("2025-01-01", periods=300)
    cl = pd.DataFrame({"SPY": 100 * 1.001 ** np.arange(300), "EWJ": 50 * 1.0005 ** np.arange(300), "GC=F": np.linspace(2000, 2500, 300)}, index=idx)
    fx = pd.Series(1.1, index=idx)
    d = mondo.costruisci(cl, mondo.universo(), fx)
    assert {x["t"] for x in d["items"]} >= {"SPY", "EWJ", "GC=F"} and "VWCE.DE" in d["mancanti"]
    x = [i for i in d["items"] if i["t"] == "EWJ"][0]
    assert x["iso"] == "JPN" and len(x["k"]) == 30 and len(x["r"]) == 6 == len(x["e"])
    assert len({u["t"] + u["c"] for u in mondo.universo()}) == len(mondo.universo())
    h = mondo.block(mondo.dumps(d))
    assert "armor-md-data" in h and "Cresciuti di più" in h


NASDAQ_TXT = """Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
ZZZZ|Test Corp|Q|Y|N|100|N|N
QQQ|Invesco QQQ Trust|G|N|N|100|Y|N
XYZW|Foo Acquisition Corp. - Class A|S|N|N|100|N|N
WARR|Bar Inc. - Warrants|S|N|N|100|N|N
TQQQ|ProShares UltraPro QQQ|G|N|N|100|N|N
File Creation Time: 1109202622:00|||||||
"""
OTHER_TXT = """ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
JPM|JPMorgan Chase & Co. Common Stock|N|JPM|N|100|N|JPM
BRK.B|Berkshire Hathaway Inc. Class B|N|BRK.B|N|100|N|BRK-B
File Creation Time: 1109202622:00|||||||
"""


def test_titoli_universo_e_filtri():
    from armor import titoli
    df = titoli.filtra_elenco(pd.concat([titoli.parse_nasdaq_listed(NASDAQ_TXT), titoli.parse_other_listed(OTHER_TXT)], ignore_index=True))
    assert sorted(df.t) == ["AAPL", "BRK-B", "JPM"]


def test_titoli_metriche_e_liquidi():
    from armor import titoli
    idx = pd.bdate_range("2025-06-01", periods=300)
    r = np.random.default_rng(0)
    c = pd.DataFrame({"A": 50 * np.exp(np.cumsum(r.normal(0, .01, 300))), "B": 0.5 * np.exp(np.cumsum(r.normal(0, .01, 300))), "C": 20 * np.exp(np.cumsum(r.normal(0, .01, 300)))}, index=idx)
    v = pd.DataFrame({"A": 1e6, "B": 1e6, "C": 100.0}, index=idx)
    c.iloc[-3, 2] = c.iloc[-4, 2] * 6   # dato anomalo
    ref = pd.Series(100 * np.exp(np.cumsum(r.normal(0, .008, 300))), index=idx)
    m = titoli.metriche(c, v, ref)
    assert abs(m.at["A", "r1m"] - (c.A.iloc[-1] / c.A.iloc[-22] - 1)) < 1e-9 and m.at["C", "anomalo"] and not m.at["A", "anomalo"]
    assert set(titoli.liquidi(m).index) == {"A"}     # B costa meno di 1, C anomalo e illiquido


def test_titoli_archivio_incrementale(tmp_path, monkeypatch):
    from armor import titoli
    monkeypatch.setattr(titoli, "CACHE", tmp_path)
    monkeypatch.setattr(titoli, "PREZZI", tmp_path / "p.pkl.gz")
    chiamate = []

    def finto(tk, per, log):
        chiamate.append((tuple(tk), per))
        n = 300 if per == "14mo" else 10
        idx = pd.bdate_range(end="2026-11-06", periods=n)
        return pd.DataFrame({t: np.linspace(10, 20, n) for t in tk}, index=idx), pd.DataFrame({t: 1000.0 for t in tk}, index=idx)
    a = titoli.aggiorna_prezzi(["X", "Y"], scarica=finto)
    assert a["close"].shape == (280, 2) and chiamate[0][1] == "14mo"
    chiamate.clear()
    a = titoli.aggiorna_prezzi(["X", "Y", "Z"], scarica=finto)
    assert [c[1] for c in chiamate] == ["10d", "14mo"] and set(a["close"].columns) == {"X", "Y", "Z"}


def test_titoli_formule():
    from armor import titoli_fond as f
    cur = {"ni": 10, "cfo": 15, "assets": 100, "ltd": 20, "ca": 60, "cl": 30, "shares": 100, "revenue": 120, "gross": 60}
    prev = {"ni": 5, "cfo": 8, "assets": 100, "ltd": 25, "ca": 50, "cl": 30, "shares": 100, "revenue": 100, "gross": 45}
    assert f.piotroski(cur, prev)["score"] == 9
    assert f.piotroski({"ni": 1}, {"ni": 1}) is None
    x = {"ca": 60, "cl": 30, "assets": 100, "retained": 20, "ebit": 10, "cap": 200, "liab": 50, "revenue": 120, "equity_book": 50}
    assert abs(f.altman(x)["z"] - (1.2 * .3 + 1.4 * .2 + 3.3 * .1 + .6 * 4 + 1.2)) < 0.006
    assert abs(f.altman(x, False)["z"] - (6.56 * .3 + 3.26 * .2 + 6.72 * .1 + 1.05 * 1.0)) < 0.006
    assert f.mesi_cassa(100, -50) == 6.0 and f.mesi_cassa(100, 5) is None
    assert abs(f.diluizione(110, 100) - 0.1) < 1e-9 and f.freccia(110, 100)["f"] == "▲"
    assert f.sue(1.1, 1.0, [0.1, -0.1, 0.05, 0.0, 0.1])["tipo"] == "sue" and f.sue(1.1, 1.0)["sue"] == 0.1
    r = f.rapporti(1000, 500, 50, 600, 80, rpo=2000)
    assert r["ps"] == 2 and r["pe"] == 20 and r["rpo_anni"] == 4 and r["cap_rpo"] == 0.5
    facts = {"facts": {"us-gaap": {"RevenueRemainingPerformanceObligation": {"units": {"USD": [
        {"end": "2025-09-30", "val": 1000, "form": "10-Q", "filed": "2025-11-05"}, {"end": "2026-09-30", "val": 3000, "form": "10-Q", "filed": "2026-11-05"}]}}}}}
    assert f.rpo_da_facts(facts)["rpo"] == 3000 and f.rpo_da_facts(facts, "2026-01-01")["rpo"] == 1000   # nessuno sguardo al futuro
    sub = {"filings": {"recent": {"form": ["8-K", "10-Q", "8-K"], "filingDate": ["2026-11-05", "2026-11-01", "2025-01-01"], "items": ["1.01,9.01", "", "2.02"], "accessionNumber": ["a", "b", "c"]}}}
    e = f.eventi_8k(sub, 30, "2026-11-09")
    assert len(e) == 1 and e[0]["item"] == "1.01" and e[0]["tono"] == "pos"


def test_titoli_eventi_e_temi():
    from armor import titoli_eventi as ev
    c = ev.classifica("Acme wins contract worth $1.2 billion from Navy")
    assert c["evento"] == "contratto" and c["importo"] == 1.2e9 and ev.pct_fatturato(c["importo"], 4e9) == 0.3
    assert ev.classifica("Rosen Law Firm encourages investors who lost money to inquire")["spam"]
    assert ev.classifica("Foo cuts guidance after weak demand")["saldi"] == -2
    assert ev.classifica("Foo to be acquired by Bar")["saldi"] == "escludi"
    assert ev.classifica("Weather is nice") is None
    r = ev.riassumi([{"title": "Rosen Law Firm reminds investors", "time": "2026-11-05T10:00:00Z"}, {"title": "Foo misses estimates", "time": "2026-11-06T10:00:00Z"}])
    assert len(r["eventi"]) == 1 and r["n_spam"] == 1
    assert ev.causa_calo(-0.10, -0.09, 1.0, [])["tipo"] == "settore"
    assert ev.causa_calo(-0.20, -0.02, 1.0, r["eventi"])["tipo"] == "azienda"
    assert ev.causa_calo(-0.20, -0.02, 1.0, [])["tipo"] == "ignota"
    assert "Robotica" in ev.temi_di("A new humanoid robot factory") and ev.accelerazione([1] * 84) == 1.0
    assert ev.accelerazione([1] * 70 + [3] * 14) == 3.0 and ev.forza_tema(3.0, .2, .2)["forza"] == 100 and ev.forza_tema(None, None, None)["forza"] is None
    j = {"studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT1", "briefTitle": "t"}, "designModule": {"phases": ["PHASE3"]},
                      "statusModule": {"primaryCompletionDateStruct": {"date": "2027-02"}}}}]}
    assert ev.catalizzatori_studi(j, "2026-11-09")[0]["id"] == "NCT1"
    assert ev.rischio_binario("Biotechnology", 1e6, 1) and not ev.rischio_binario("Software", 1e6, 1)


def _finti_saldi():
    from armor import saldi
    r = np.random.default_rng(4)
    items, fond, nz = [], {}, {}
    for i in range(40):
        t = f"T{i}"
        rr = [-0.02 - 0.01 * (i % 7)] * 5 + [0.1]
        items.append({"t": t, "n": f"Azienda {i}", "c": "titoli", "s": "Technology" if i % 2 else "Energy", "v": "USD", "p": 10.0 + i, "r": rr, "e": rr, "k": [1, 2, 3], "k6": [1, 2, 3, 2],
                      "x3": -0.03 - 0.001 * i, "beta": 1.1, "cap": 1e9 * (i + 1), "paese": "United States", "ind": "Software"})
        fond[t] = {"nome": f"Azienda {i}", "settore": "Technology" if i % 2 else "Energy", "industria": "Software", "paese": "United States", "cap": 1e9 * (i + 1),
                   "ricavi_q_1a": {"var": 0.1 - i * 0.01, "f": "▲" if i < 10 else "▼"}, "ricavi_ttm": 1e9, "ps": 1 + i * 0.3, "pe": 10 + i, "ps_f": 1 + i * 0.2, "pe_f": None, "ev_ebitda": 8 + i * 0.5,
                   "piotroski": {"score": 9 - i % 10, "su": 9}, "altman": {"z": 4 - i * 0.1, "zona": "sicura"}, "copertura_interessi": 10 - i * 0.2, "debito_netto_ebitda": i * 0.1,
                   "current_ratio": 2 - i * 0.02, "margine_lordo": 0.6 - i * 0.01, "margine_fcf": 0.2 - i * 0.005, "roe": 0.2, "mesi_cassa": 3.0 if i == 5 else None, "diluizione": 0.01 * i,
                   "analisti": {"raccomandazione": 2.0, "target": 20.0 + i, "n": 8}, "insider_acq_90g": 2 if i == 3 else None, "short_float": 0.05, "rpo": None, "rpo_anni": None}
        nz[t] = []
    nz["T1"] = [{"title": "Azienda 1 cuts guidance for 2027", "time": "2026-11-06T10:00:00Z", "source": "Reuters", "link": "http://x"}]
    nz["T2"] = [{"title": "Azienda 2 to be acquired by BigCo", "time": "2026-11-06T10:00:00Z"}]
    return saldi, {"asof": "2026-11-06", "items": items}, fond, nz


def test_saldi_punteggio_report_e_registro(tmp_path, monkeypatch):
    saldi, top, fond, nz = _finti_saldi()
    monkeypatch.setattr(saldi, "REGISTRO", tmp_path / "reg.csv")
    d = saldi.costruisci(top, fond, nz, [{"n": "ETF X", "t": "XX", "c": "etf", "s": "Azionario USA", "v": "USD", "p": 50, "r": [-0.01, -0.02, -0.03, -0.04, -0.05, 0.1], "k": [1, 2]}],
                         {"XLK": {"1g": -0.01, "1s": -0.02, "1m": -0.03, "3m": 0.0, "6m": 0.0}}, 1.1)
    assert len(d["classifiche"]["1g"]) <= 100 and "T2" not in d["titoli"] and d["escluse_acquisizioni"] == ["T2"]
    assert d["classifiche"]["1g"] == sorted(d["classifiche"]["1g"], key=lambda t: d["titoli"][t]["r"]["1g"])
    sc = {t: x["s"] for t, x in d["titoli"].items()}
    assert all(1 <= v <= 100 for v in sc.values() if v is not None)
    assert sc["T0"] > sc["T39"]                          # azienda più solida e più a buon prezzo: punteggio più alto
    assert sc["T5"] <= 15 and "cassa" in " ".join(d["titoli"]["T5"]["tetti"])   # meno di 6 mesi di cassa: tetto
    assert d["titoli"]["T1"]["causa"] == "azienda" and "Previsioni tagliate" in d["titoli"]["T1"]["causa_t"]
    rep = d["dett"]["T1"]["report"]
    assert set(rep) == {"perche", "salute", "favorevole", "rischi", "nota"} and rep["rischi"] and "consulenza" in rep["nota"]
    assert d["etf_classifiche"]["1g"] == ["XX"] and d["etf"]["XX"]["r"]["3g"] is None
    n1 = saldi.registra(d, "2026-11-06")
    assert n1 > 0 and saldi.registra(d, "2026-11-06") == 0       # nessun doppione
    h = saldi.block(saldi.json.dumps(d))
    assert "armor-sd-data" in h and "non è una consulenza finanziaria" in h.lower()


def test_saldi_verifica_per_fascia():
    saldi = __import__("armor.saldi", fromlist=["x"])
    idx = pd.bdate_range("2026-01-01", periods=120)
    close = pd.DataFrame({"A": np.linspace(10, 20, 120), "B": np.linspace(10, 5, 120)}, index=idx)
    spy = pd.Series(np.linspace(100, 110, 120), index=idx)
    reg = pd.DataFrame({"data": [idx[0], idx[0]], "ticker": ["A", "B"], "periodo": ["1g", "1g"], "punteggio": [90, 10], "prezzo": [10, 10]})
    v = saldi.verifica(close, spy, reg)
    f = {x["fascia"]: x for x in v["orizzonti"]["1m"]["fasce"]}
    assert f["81-100"]["medio"] > 0 > f["1-20"]["medio"] and f["81-100"]["su"] == 1.0 and f["1-20"]["su"] == 0.0
