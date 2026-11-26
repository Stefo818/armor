import io
import zipfile

from armor import accumulo_extra3 as ex3

FF = """This file was created by CMPT_ME_BEME_RETS using the 202509 CRSP database.

,Mkt-RF,SMB,HML,RF
19260701,    0.10,   -0.25,   -0.27,    0.009
19260702,    0.45,   -0.33,   -0.06,    0.009
19260706,  -99.99,   -0.20,    0.15,    0.009

Copyright 2025 Kenneth R. French
"""


def test_parse_french():
    df = ex3.parse_french(FF)
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert len(df) == 3 and df["Mkt-RF"].isna().sum() == 1 and df.loc["1926-07-02", "SMB"] == -0.33


def test_parse_cboe_storia():
    df = ex3.parse_cboe_storia("DATE,OPEN,HIGH,LOW,CLOSE\n01/02/1990,17.24,17.24,17.24,17.24\n01/03/1990,18.19,18.19,18.19,18.19\n")
    assert len(df) == 2 and df["close"].iloc[1] == 18.19
    df2 = ex3.parse_cboe_storia("Date,VVIX\n2006-03-06,70.1\n")
    assert df2["vvix"].iloc[0] == 70.1


def test_parse_dtcc_cds():
    csv = ("Dissemination Identifier,Product Name,Rounded Notional Amount 1,Price Notation Type,Price,Underlier ID-Leg 1\n"
           "1,Credit:Index:CDX,\"25,000,000+\",Spread,60.5,CDX.NA.IG.45\n"
           "2,Credit:Index:iTraxx,10000000,Spread,70.0,ITRAXX-EUROPE\n"
           "3,Credit:SingleName,5000000,Spread,200,ACME CORP\n")
    r = ex3.parse_dtcc_cds(csv, "2026-11-25")
    assert r["n_operazioni"] == 3 and r["n_indici"] == 2 and r["importo_indici"] == 35_000_000
    assert abs(r["prezzo_medio_pesato_indici"] - (60.5 * 25 + 70 * 10) / 35) < 1e-9


def test_csv_da_zip():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("a.CSV", "x,y\n1,2\n")
    assert ex3._csv_da_zip(b.getvalue()).startswith("x,y")


def test_parse_dtcc_generico():
    r = ex3.parse_dtcc_generico("Product Name,Rounded Notional Amount 1\nA,\"1,000+\"\nB,500\n")
    assert r["n_operazioni"] == 2 and r["importo_totale"] == 1500


def test_dtcc_nomi_e_giorno_vuoto(tmp_path, monkeypatch):
    import datetime as dt
    import io, zipfile
    assert ex3._nome_dtcc("sec_credits", dt.date(2026, 11, 25)) == "SEC_CUMULATIVE_CREDITS_2026_11_25.zip"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("vuoto.csv", "")
    class R: content = b.getvalue()
    monkeypatch.setattr(ex3, "_get", lambda *a, **k: R)
    r = ex3._dtcc_giorno("cftc_rates", dt.date(2026, 11, 22), str(tmp_path))
    assert r["n_operazioni"] == 0 and (tmp_path / "CFTC_CUMULATIVE_RATES_2026_11_22.zip").exists()


def test_date_gia_serie_inesistente():
    assert ex3._date_gia("dtcc_serie_che_non_esiste_n_operazioni") == set()
