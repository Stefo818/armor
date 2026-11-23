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
