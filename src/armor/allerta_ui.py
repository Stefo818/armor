# -*- coding: utf-8 -*-
"""Scheda compatta «Allerta vendite» in cima alla pagina Oggi (regole in PROTOCOLLO_FRAGILITA.md).
Si aggiorna ogni 15 secondi leggendo il servizio Cloudflare (data/live_worker.json, «url»): stessi segnali della sentinella che manda le notifiche."""
import json
from pathlib import Path

from .config import DATA

CSS = """<style>
.alr{border:1px solid var(--bd);border-left-width:5px;border-radius:12px;padding:9px 12px;background:var(--card);margin:8px 0}
.alr.b{border-left-color:var(--bad)}.alr.w{border-left-color:var(--warn,#f59e0b)}.alr.ok{border-left-color:var(--ok)}
.alr b.t{font-size:15px;display:block}
.alr .d{font-size:12.5px;color:var(--mu);margin-top:3px;line-height:1.45}.alr .d b{color:var(--tx)}
details.alrd{margin-top:6px}
details.alrd>summary{list-style:none;cursor:pointer;font-size:12px;color:var(--mu);display:flex;align-items:center;gap:6px}
details.alrd>summary::-webkit-details-marker{display:none}
details.alrd>summary::after{content:"";width:6px;height:6px;border-right:2px solid var(--mu);border-bottom:2px solid var(--mu);transform:rotate(45deg);transition:transform .18s}
details.alrd[open]>summary::after{transform:rotate(225deg)}
.alr .x{font-size:12.5px;color:var(--mu);line-height:1.5;margin-top:6px}
.alr .s{font-size:10.5px;color:var(--mu);margin-top:5px}
</style>"""


def html() -> str:
    try:
        cfg = json.loads((DATA / "live_worker.json").read_text(encoding="utf-8"))
        if not cfg.get("url"):
            return ""
        js = (Path(__file__).parent / "allerta_live.js").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    return (CSS + "<div id='allerta' class='alr'><b class='t' id='allerta-t'>Allerta vendite</b>"
            "<div class='d' id='allerta-d'>Controllo dei segnali in corso…</div>"
            "<details class='alrd'><summary>Cosa vuol dire</summary><div class='x' id='allerta-x'></div>"
            "<div class='s' id='allerta-s'></div></details></div>"
            "<script>window.ALLERTA_LIVE=" + json.dumps({"url": cfg["url"]}) + ";" + js + "</script>")
