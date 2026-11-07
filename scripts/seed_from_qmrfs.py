"""Copia lo storico di QMRFS in data/series/ (si usa una volta sola: python scripts/seed_from_qmrfs.py <qmrfs.sqlite>)."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import store  # noqa: E402

db = sys.argv[1]
keep = ["sp500", "vix", "vix3m", "vvix", "hyg", "ief", "baa10y", "t10y2y", "t10y3m", "skew", "move", "vt", "eurusd", "vwce_de"]
c = sqlite3.connect(db)
o = pd.read_sql("select series_id,obs_date,value from observations where status in ('ok','stale')", c)
o["obs_date"] = pd.to_datetime(o["obs_date"])
for sid in keep:
    s = o[o.series_id == sid].set_index("obs_date")["value"]
    print(sid, len(s), store.upsert(sid, s))
