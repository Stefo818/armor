from armor.bis_dsr import parse_sdmx_json, _period_end


def test_periodo_bis_trimestrale():
    assert str(_period_end("1999-Q1").date()) == "1999-03-31"
    assert str(_period_end("2026Q2").date()) == "2026-06-30"


def test_parser_sdmx_mappa_paese_e_settore():
    payload = {
        "dataSets": [{
            "series": {
                "0:0:0": {"observations": {"0": [27.1], "1": [27.4]}},
                "0:1:0": {"observations": {"0": [25.1], "1": [25.2]}},
                "0:0:1": {"observations": {"0": [41.1], "1": [41.4]}},
            }
        }],
        "structure": {"dimensions": {
            "series": [
                {"id": "FREQ", "values": [{"id": "Q"}]},
                {"id": "BORROWERS_CTY", "values": [{"id": "US"}, {"id": "XM"}]},
                {"id": "DSR_BORROWERS", "values": [{"id": "P"}, {"id": "H"}]},
            ],
            "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2024-Q1"}, {"id": "2024-Q2"}]}],
        }},
    }
    result = parse_sdmx_json(payload)
    assert set(result) == {"bis_dsr_us_private", "bis_dsr_xm_private", "bis_dsr_us_households"}
    assert result["bis_dsr_us_private"].iloc[-1] == 27.4
    assert str(result["bis_dsr_us_private"].index[-1].date()) == "2024-06-30"


def test_parser_rifiuta_risposta_sdmx_incompleta():
    try:
        parse_sdmx_json({"dataSets": [], "structure": {}})
    except ValueError:
        return
    raise AssertionError("Il parser deve rifiutare una risposta priva di dimensioni")


def test_fetch_all_completa_le_aree_mancanti_con_fallback(monkeypatch):
    import pandas as pd
    from armor import bis_dsr

    calls = []

    def fake_request(key, start):
        calls.append(key)
        # La query aggregata restituisce solo gli USA: il collector deve
        # chiedere separatamente le aree non presenti nella risposta.
        if key == "Q.US+XM+JP+GB+CA.P":
            return {"bis_dsr_us_private": pd.Series([8.0], index=[pd.Timestamp("2025-03-31")])}
        if key.endswith(".P"):
            country = key.split(".")[1]
            slug = bis_dsr.COUNTRIES[country]
            return {f"bis_dsr_{slug}_private": pd.Series([9.0], index=[pd.Timestamp("2025-03-31")])}
        if key == "Q.US.H+N":
            raise RuntimeError("query combinata non supportata")
        if key in ("Q.US.H", "Q.US.N"):
            slug = "households" if key.endswith(".H") else "corporate"
            return {f"bis_dsr_us_{slug}": pd.Series([10.0], index=[pd.Timestamp("2025-03-31")])}
        raise AssertionError(key)

    monkeypatch.setattr(bis_dsr, "_request_key", fake_request)
    monkeypatch.setattr(bis_dsr.store, "load", lambda sid: pd.Series(dtype=float))
    out = bis_dsr.fetch_all(full=True)
    assert set(out) == {
        "bis_dsr_us_private", "bis_dsr_xm_private", "bis_dsr_jp_private",
        "bis_dsr_gb_private", "bis_dsr_ca_private", "bis_dsr_us_households",
        "bis_dsr_us_corporate",
    }
    assert "Q.XM.P" in calls and "Q.JP.P" in calls and "Q.US.H" in calls and "Q.US.N" in calls


def test_parser_accetta_anche_ref_area():
    payload = {"dataSets": [{"series": {"0:0:0": {"observations": {"0": [5.0]}}}}],
               "structure": {"dimensions": {"series": [{"id": "FREQ", "values": [{"id": "Q"}]}, {"id": "REF_AREA", "values": [{"id": "JP"}]},
                                                       {"id": "DSR_BORROWERS", "values": [{"id": "P"}]}],
                             "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2024-Q4"}]}]}}}
    assert set(parse_sdmx_json(payload)) == {"bis_dsr_jp_private"}


def test_errori_non_inghiottiti(monkeypatch):
    import pandas as pd
    from armor import bis_dsr

    def fake(key, start):
        if key == "Q.XM.P":
            raise RuntimeError("404 non trovato")
        return {}
    monkeypatch.setattr(bis_dsr, "_request_key", fake)
    monkeypatch.setattr(bis_dsr.store, "load", lambda sid: pd.Series(dtype=float))
    err = {}
    bis_dsr.fetch_all(full=True, errori=err)
    assert "Q.XM.P" in err and "404" in err["Q.XM.P"]


def test_prima_vista_registrata_una_sola_volta(tmp_path):
    import pandas as pd
    from armor import bis_dsr
    f = tmp_path / "meta.json"
    s = {"bis_dsr_us_private": pd.Series([8.0, 8.1], index=pd.to_datetime(["2025-03-31", "2025-06-30"]))}
    assert bis_dsr.registra_prima_vista(s, "2026-11-24", f) == 2
    s["bis_dsr_us_private"].loc[pd.Timestamp("2025-09-30")] = 8.3
    assert bis_dsr.registra_prima_vista(s, "2026-12-30", f) == 1
    import json
    m = json.loads(f.read_text())["bis_dsr_us_private"]
    assert m["2025-03-31"] == "2026-11-24" and m["2025-09-30"] == "2026-12-30"
