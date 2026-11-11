import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import perche as pc  # noqa: E402


def test_perche_live_dati_e_script():
    v = {"XLK": -0.018, "XLF": -0.004, "NVDA": -0.032, "XLB": 0.001, "^GDAXI": -0.004, "EURUSD=X": 0.002}
    q = {"sp500": {"chg": -0.009, "open": True}, "vwce": {"chg": -0.0037}}
    ora = datetime(2026, 11, 10, 18, 8, tzinfo=timezone.utc)
    d = pc.costruisci(v, {"sp": [], "vw": []}, q, [], ora)
    assert d["live"]["base"]["XLB"] == 0.001 and "XLB" not in d["live"]["isin"] and "XOM" not in d["live"]["isin"]
    assert len(d["live"]["sp"]["sett"]) == 11 and d["live"]["usa_w"] == 62.0
    h = pc.html(d, ora)
    m = re.search(r"id='pcd'>(.*?)</script>", h, re.S)
    assert m and json.loads(m.group(1).replace("<\\/", "</"))["isin"]["XLK"][1] == "FUND"
    assert "id='pcs'" in h and "pcLive" in pc.JS and "api.onvista.de" in pc.JS
    assert "id='pcd'" not in pc.html({**d, "live": None}, ora)  # vecchio file senza dati live: scheda normale
