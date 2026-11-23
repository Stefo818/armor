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
