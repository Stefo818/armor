import sys
sys.path.insert(0, "src")
from armor import cruscotto, store, semafori
import armor.parts as parts
sp, vw, vx = store.load("sp500"), store.load("vwce"), store.load("vix")
try:
    sem = semafori.calcola() if hasattr(semafori, "calcola") else []
except Exception:
    sem = []
h = cruscotto.kpi_html(sem, sp, vw, vx)
css = cruscotto.CSS + parts.CSS if hasattr(parts, "CSS") else cruscotto.CSS
open("/tmp/kpi.html", "w", encoding="utf-8").write(f"<html><head><meta name=viewport content='width=device-width,initial-scale=1'><style>:root{{--bg:#0b1220;--card:#131b2b;--bd:#26324a;--tx:#e6ebf5;--mu:#8b97ad;--ok:#22c55e;--bad:#ef4444;--warn:#f59e0b;--ac:#60a5fa}}body{{background:var(--bg);color:var(--tx);font-family:system-ui;margin:12px}}{css}</style></head><body>{h}</body></html>")
