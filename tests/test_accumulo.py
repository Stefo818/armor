import pandas as pd

from armor import accumulo


def test_slug_e_simboli_senza_doppioni():
    assert accumulo.slug("^VIX9D") == "vix9d" and accumulo.slug("EURUSD=X") == "eurusd_x"
    sim = accumulo.yahoo_simboli()
    assert len(sim) > 250 and len(set(sim)) == len(sim)
    assert "^VIX" not in sim.values()   # gia' archiviato dall'app


def test_riepilogo_catena_aggrega_per_scadenza():
    j = {"data": {"current_price": 100.0, "options": [
        {"option": "SPY261218C00100000", "iv": 0.2, "delta": 0.5, "gamma": 0.02, "volume": 10, "open_interest": 100},
        {"option": "SPY261218P00100000", "iv": 0.22, "delta": -0.5, "gamma": 0.02, "volume": 30, "open_interest": 200},
        {"option": "SPY261218P00090000", "iv": 0.3, "delta": -0.25, "gamma": 0.01, "volume": 5, "open_interest": 50},
        {"option": "SPY261218C00110000", "iv": 0.18, "delta": 0.25, "gamma": 0.01, "volume": 7, "open_interest": 70},
    ]}}
    r = accumulo.riepilogo_catena(j, "2026-11-23", "SPY")
    tot = [x for x in r if x["scadenza"] == "TOTALE"][0]
    assert tot["call_vol"] == 17 and tot["put_vol"] == 35 and tot["put_oi"] == 250
    sc = [x for x in r if x["scadenza"] == "2026-12-18"][0]
    assert sc["giorni"] == 25 and abs(sc["skew25"] - 0.12) < 1e-9 and sc["iv_atm"] > 0
    assert accumulo.riepilogo_catena({"data": {}}, "2026-11-23", "SPY") == []


def test_salva_mensile_idempotente(tmp_path):
    idx = pd.to_datetime(["2026-11-20 14:30", "2026-11-20 14:35", "2026-12-01 14:30"])
    df = pd.DataFrame({"o": [1, 2, 3], "h": [1, 2, 3], "l": [1, 2, 3], "c": [1, 2, 3], "v": [1, 1, 1]}, index=idx)
    assert accumulo.salva_mensile(tmp_path, "spy", df) == 3
    assert accumulo.salva_mensile(tmp_path, "spy", df) == 0
    assert (tmp_path / "2026-11" / "spy.csv.gz").exists() and (tmp_path / "2026-12" / "spy.csv.gz").exists()
