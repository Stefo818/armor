import sys
sys.path.insert(0, "src")
from armor import quadro, grafico_indici, titan_schede
h = titan_schede.combo_html() + grafico_indici.html()
open("/tmp/status.html", "w", encoding="utf-8").write(
    "<html><head><meta name=viewport content='width=device-width,initial-scale=1'><style>:root{--bg:#0b1220;--card:#131b2b;--bd:#26324a;--tx:#e6ebf5;--mu:#8b97ad;--ok:#22c55e;--bad:#ef4444;--warn:#f59e0b;--ac:#60a5fa}"
    "body{background:var(--bg);color:var(--tx);font-family:system-ui;margin:10px}</style></head><body>" + h + "</body></html>")
