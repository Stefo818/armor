import pandas as pd

from armor import accumulo_extra as ex


def test_parse_bce():
    txt = "KEY,TIME_PERIOD,OBS_VALUE,X\na,2026-11-10,0.5,1\na,2026-11-11,0.7,1\na,2026-11-12,,1\n"
    s = ex.parse_bce(txt)
    assert list(s.round(2)) == [0.5, 0.7] and s.index[-1] == pd.Timestamp("2026-11-11")


def test_parse_ofr_e_ust():
    d = ex.parse_ofr("Date,OFR FSI,Credit\n2026-11-10,-1.2,0.3\n2026-11-11,-1.0,0.2\n")
    assert list(d.columns) == ["OFR FSI", "Credit"] and len(d) == 2
    u = ex.parse_ust("Date,1 Mo,10 Yr\n11/10/2026,4.1,4.4\n11/11/2026,4.2,4.5\n")
    assert u.index[0] == pd.Timestamp("2026-11-10") and u["10 Yr"].iloc[-1] == 4.5


def test_parse_tga_e_cot():
    j = {"data": [{"record_date": "2026-11-10", "account_type": "Treasury General Account (TGA) Closing Balance", "close_today_bal": "850000", "open_today_bal": "1"},
                  {"record_date": "2026-11-10", "account_type": "Treasury General Account (TGA) Opening Balance", "open_today_bal": "9"}]}
    assert ex.parse_tga(j).iloc[0] == 850000
    c = ex.filtra_cot([{"report_date_as_yyyy_mm_dd": "2026-11-10T00:00:00.000", "market_and_exchange_names": "E-MINI S&P 500 - CME", "open_interest_all": "5", "altro": "x"},
                       {"report_date_as_yyyy_mm_dd": "2026-11-10T00:00:00.000", "market_and_exchange_names": "COCOA - ICE", "open_interest_all": "5"}])
    assert len(c) == 1 and c["report_date_as_yyyy_mm_dd"].iloc[0] == "2026-11-10" and "altro" not in c.columns


def test_parse_wiki_gdelt_nyfed_finra():
    w = ex.parse_wiki({"items": [{"timestamp": "2026111000", "views": 120}, {"timestamp": "2026111100", "views": 150}]})
    assert w.iloc[-1] == 150 and w.index[0] == pd.Timestamp("2026-11-10")
    g = ex.parse_gdelt("Date,Series,Value\n2026-11-10T00:00:00Z,x,-2.0\n2026-11-11T00:00:00Z,x,-3.0\n")
    assert list(g) == [-2.0, -3.0]
    n = ex.parse_nyfed({"refRates": [{"effectiveDate": "2026-11-10", "percentRate": 4.3, "volumeInBillions": 2000}]}, {"tasso": "percentRate", "volume": "volumeInBillions"})
    assert n["tasso"].iloc[0] == 4.3 and n["volume"].iloc[0] == 2000
    f = ex.parse_finra("Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n20261110|SPY|60|1|100|B\n20261110|ZZZ|5|0|10|B\n", {"SPY"})
    assert list(f["Symbol"]) == ["_TOTALE", "SPY"] and f["TotalVolume"].iloc[0] == 110


def test_vix_future_scadenze_e_parser():
    sc = ex.scadenze_vix(pd.Timestamp("2026-11-23"), avanti=2)
    assert [d.strftime("%Y-%m-%d") for d in sc[:2]] == ["2026-11-18", "2026-12-16"] and all(d.weekday() == 2 for d in sc)
    v = ex.parse_vx("Trade Date,Futures,Open,High,Low,Close,Settle,Change,Total Volume,EFP,Open Interest\n2026-11-20,VX,18,19,17,18.5,18.4,0.1,100,0,500\n", "2026-12-16")
    assert v["settle"].iloc[0] == 18.4 and v["scadenza"].iloc[0] == "2026-12-16" and v["data"].iloc[0] == "2026-11-20"


def test_parse_aaii():
    df = pd.DataFrame([["titolo", None, None, None], ["Date", "Bullish", "Neutral", "Bearish"], ["2026-11-19", 35.0, 30.0, 35.0], ["2026-11-12", 40.0, 30.0, 30.0]])
    t = ex.parse_aaii(df)
    assert list(t.columns) == ["bullish", "neutral", "bearish"] and t["bullish"].iloc[0] == 35.0


def test_posizioni_complete_pacchetto_finto(tmp_path, monkeypatch):
    import io
    import zipfile

    from armor import sec_dati as sd
    monkeypatch.setattr(sd, "DIR", tmp_path)
    sub = "ACCESSION_NUMBER\tFILING_DATE\tSUBMISSIONTYPE\tCIK\tPERIODOFREPORT\na1\t2026-05-10\t13F-HR\t1\t2026-03-31\na2\t2026-05-11\t13F-HR\t2\t2026-03-31\n"
    cov = "ACCESSION_NUMBER\tFILINGMANAGER_NAME\na1\tBRIDGEWATER ASSOCIATES, LP\na2\tPiccolo Fondo\n"
    righe = ["ACCESSION_NUMBER\tNAMEOFISSUER\tCUSIP\tVALUE\tSSHPRNAMT\tPUTCALL"] + [f"a1\tAZ{i}\tC{i}\t{100 - i}\t{i + 1}\t" for i in range(5)] + ["a2\tAZ0\tC0\t5\t1\t"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("SUBMISSION.tsv", sub); z.writestr("COVERPAGE.tsv", cov); z.writestr("INFOTABLE.tsv", "\n".join(righe))
    z = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    df = sd.posizioni_complete(z)
    assert set(df["cik"]) == {"1", "2"} and len(df) == 6      # a2 e' fra i primi 150: sono pochi depositanti
    assert sd.salva_posizioni_complete(df) == 6 and sd.salva_posizioni_complete(df) == 6
    assert len(pd.read_csv(tmp_path / "posizioni" / "2026.csv.gz")) == 6   # riscrittura = sostituzione, non doppioni


def test_parse_dealer_ftd_short_interest():
    j = {"pd": {"timeseries": {"keyid": "PDPOSGST-TOT", "asofdate": "2026-11-18", "value": "12.5"}}}
    d = ex.parse_dealer({"a": [j, {"keyid": "PDPOSGST-TOT", "asofdate": "2026-11-11", "value": "*"}]})
    assert len(d) == 1 and d["valore"].iloc[0] == 12.5
    f = ex.parse_ftd("SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n20261110|x|SPY|1000|S&P|500\n20261110|y|ZZZ|50|z|2\n", {"SPY"})
    assert list(f["symbol"]) == ["_TOTALE", "SPY"] and f["fails"].iloc[0] == 1050 and f["data"].iloc[0] == "2026-11-10"
    s = ex.parse_short_interest("symbolCode|currentShortPositionQuantity|previousShortPositionQuantity|averageDailyVolumeQuantity|daysToCoverQuantity|settlementDate\nSPY|10|8|5|2|2026-11-13\nZZZ|1|1|1|1|2026-11-13\n", {"SPY"})
    assert list(s["symbol"]) == ["SPY"] and s["short"].iloc[0] == "10"
    dt = ex.date_short_interest(pd.Timestamp("2026-11-23"), mesi=1)
    assert "20261113" in dt and "20261030" in dt and all(x < "20261123" for x in dt)


def test_seconda_ondata_parser():
    from armor import accumulo_extra2 as e2
    idx = ["8-K                  ACME CORP                     123456      2026-11-10  edgar/data/1/a.txt",
           "NT 10-K              LATE INC                      777         2026-11-10  edgar/data/2/b.txt",
           "ZZZ                  X                             1           2026-11-10  edgar/data/3/c.txt",
           "8-K                  BETA CORP                     5           2026-11-11  edgar/data/4/d.txt"]
    c = e2.conta_moduli(idx)
    assert set(c["modulo"]) == {"8-K", "NT 10-K"} and int(c[(c.data == "2026-11-10") & (c.modulo == "8-K")]["n"].iloc[0]) == 1
    assert e2.totale_efts({"hits": {"total": {"value": 42}}}) == 42
    assert e2.parse_dvol({"result": {"data": [[1763856000000, 1, 2, 0.5, 55.5]]}}).iloc[0] == 55.5
    assert e2.put_call_deribit({"result": [{"instrument_name": "BTC-27DEC26-60000-P", "open_interest": 30}, {"instrument_name": "BTC-27DEC26-60000-C", "open_interest": 60}]})["put_call"] == 0.5
    j = e2.parse_jgb("Interest Rate (%)\nDate,1Y,10Y\n2026/11/20,0.8,1.9\n2026/11/19,0.8,-\n")
    assert j.index[0] == pd.Timestamp("2026-11-20") and j["10Y"].iloc[0] == 1.9
    rss = "<rss><channel><item><title>Titolo uno</title><link>http://x</link><pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>"
    r = e2.parse_rss(rss)
    assert r[0]["data"] == "2026-11-23" and r[0]["titolo"] == "Titolo uno"
    a = e2.parse_apewisdom({"results": [{"ticker": "NVDA", "rank": 1, "mentions": 50, "upvotes": 9}]}, "2026-11-23")
    assert a["menzioni"].iloc[0] == 50


def test_indicatori_componenti_e_intraday():
    import numpy as np

    from armor import accumulo_derivati as dv
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2025-01-01", periods=320)
    P = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (320, 60)), axis=0)), index=idx, columns=[f"S{i}" for i in range(60)])
    V = pd.DataFrame(1e6, index=idx, columns=P.columns)
    d = dv.indicatori_componenti(P, V, {c: ("A" if i < 30 else "B") for i, c in enumerate(P.columns)})
    assert 0 <= d["d_pct_sopra_200"].dropna().min() and d["d_pct_sopra_200"].max() <= 100
    assert 10 / 60 * 100 <= d["d_quota_volume_top10"].dropna().iloc[-1] < 40
    assert "d_pct_sopra_50_a" in d.columns and d["d_correlazione_media_21"].dropna().abs().max() < 1
    ts = pd.date_range("2026-11-20 14:30", periods=40, freq="5min")
    g = pd.DataFrame({"ts": ts, "o": 100.0, "h": 101.0, "l": 99.0, "c": np.linspace(100, 102, 40), "v": 10.0})
    m = dv.misure_giornata(g)
    assert m["ampiezza"] == 2.0 and m["ritorno_giornata"] > 1.9 and "quota_volume_ultima_ora" in m


def test_wiki_lingue_e_cucitura_trends():
    from armor import accumulo_extra2 as e2
    j = {"query": {"pages": {"1": {"title": "Bank run", "langlinks": [{"lang": "it", "*": "Corsa agli sportelli"}]}, "2": {"title": "Recession", "langlinks": []}}}}
    assert e2.parse_langlinks(j, "it") == {"Bank_run": "Corsa_agli_sportelli"}
    idx1 = pd.date_range("2026-10-01", periods=10)
    idx2 = pd.date_range("2026-10-06", periods=10)
    a = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100.0], index=idx1)
    b = pd.Series([30, 35, 40, 45, 50, 55, 60, 65, 70, 75.0], index=idx2)    # stessa realta' vista con un'altra scala (meta')
    s = e2.cuci_finestre([("2026-10-10", a), ("2026-10-15", b)])
    assert len(s) == 15 and abs(s.iloc[-1] - 150.0) < 1e-9 and abs(s[pd.Timestamp("2026-10-06")] - 60.0) < 1e-9


# ----------------------------------------------------------------------------- correzioni dopo il primo giro su GitHub (24/11/2026)
def test_parse_tga_con_null_come_testo():
    from armor.accumulo_extra import parse_tga
    j = {"data": [{"record_date": "2026-11-20", "account_type": "Treasury General Account (TGA) Closing Balance", "close_today_bal": "null", "open_today_bal": "812345"}]}
    assert parse_tga(j).iloc[0] == 812345.0


def test_parse_rss_tollera_bom_e_rifiuta_html():
    import pytest
    from armor.accumulo_extra2 import parse_rss
    xml = '﻿<?xml version="1.0" encoding="UTF-8"?><rss><channel><item><title>A</title><pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate><link>x</link></item></channel></rss>'
    assert parse_rss(xml)[0]["titolo"] == "A"
    with pytest.raises(RuntimeError):
        parse_rss("<!DOCTYPE html><html>blocked</html>")


def test_cboe_pc_largo_ricava_rapporto_da_put_e_call():
    from armor.accumulo import parse_cboe_pc_largo
    txt = "Cboe nota\nTrade Date,Call Volume,Put Volume\n2026-11-20,100,80\n2026-11-23,200,300\n"
    s = parse_cboe_pc_largo(txt)
    assert round(float(s.iloc[1]), 2) == 1.5


def test_fred_inesistente_e_ritmo(monkeypatch):
    import pytest
    from armor import accumulo

    class R:
        status_code = 400
        text = ""
        def json(self):
            return {"error_message": "Bad Request.  The series does not exist."}
    monkeypatch.setattr(accumulo.requests, "get", lambda *a, **k: R())
    monkeypatch.setattr(accumulo, "_fred_pausa", lambda *a, **k: None)
    with pytest.raises(accumulo.FredInesistente):
        accumulo.fetch_fred_acc("XXXX", chiave="k")


def test_parse_ofr_mmf_e_prolungamento(monkeypatch):
    s = ex.parse_ofr_mmf([["2026-08-31", 7000.0], ["2026-09-30", 7100.0], ["2026-10-31", 7200.0]])
    assert len(s) == 3 and s.iloc[-1] == 7200.0
    s2 = ex.parse_ofr_mmf({"timeseries": [["2026-08-31", 1.0], ["2026-09-30", 2.0]]})
    assert len(s2) == 2
    import pandas as pd
    from armor import difensivita
    base = pd.Series(100.0, index=pd.date_range("2026-08-03", periods=10, freq="W-MON"))
    monkeypatch.setattr("armor.store.load", lambda n: base if n == "mmf_assets" else pd.Series([7000.0, 7100.0, 7200.0, 7300.0], index=pd.to_datetime(["2026-08-31", "2026-09-30", "2026-10-31", "2026-11-30"])))
    out = difensivita.mmf_serie()
    assert out.index[-1] > base.index[-1] and out.iloc[-1] > 100.0
