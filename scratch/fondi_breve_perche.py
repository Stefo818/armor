"""Perche' i fondi a breve sembrano forti da soli ma non aggiungono nulla all'Indice Armor."""
import sys

import pandas as pd

sys.path.insert(0, "src")
from armor import semafori, store  # noqa: E402

sp = store.load("sp500").dropna()
h = pd.read_csv("data/titan_storia.csv", parse_dates=["date"]).set_index("date")
f = semafori.series_of("fondi_breve", sp).reindex(h.index).ffill()
fp = f.expanding(min_periods=250).rank(pct=True) * 100
for c in ("armor_index", "super_armor_index", "p1_stress", "p3_stress", "p4_stress"):
    if c in h:
        print(f"correlazione fondi a breve con {c:18s}: {fp.corr(h[c]):+.3f}")
alto = fp >= fp.quantile(0.8)
print("\nnei giorni in cui i fondi a breve sono nel quinto piu' alto:")
print(f"  Indice Armor medio {h['armor_index'][alto].mean():.1f}  contro {h['armor_index'][~alto].mean():.1f} negli altri giorni")
print(f"  Super Armor medio  {h['super_armor_index'][alto].mean():.1f}  contro {h['super_armor_index'][~alto].mean():.1f}")
