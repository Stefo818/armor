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
