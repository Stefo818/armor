# -*- coding: utf-8 -*-
"""Scheda compatta «Allerta vendite» in cima alla pagina Oggi (regole in PROTOCOLLO_FRAGILITA.md).
Si aggiorna ogni 15 secondi leggendo il servizio Cloudflare (data/live_worker.json, «url»): stessi segnali della sentinella che manda le notifiche."""
import json
from pathlib import Path

from .config import DATA

CSS = ("<style>.alr{border:1px solid var(--bd);border-left-width:5px;border-radius:12px;padding:8px 12px;background:var(--card);margin:8px 0}"
       ".alr.b{border-left-color:var(--bad)}.alr.w{border-left-color:var(--warn,#f59e0b)}.alr.ok{border-left-color:var(--ok)}"
       ".alr b.t{font-size:15px}.alr .d{font-size:13px;color:var(--mu);margin-top:3px;line-height:1.4}.alr .d b{color:var(--tx)}.alr .s{font-size:11px;color:var(--mu);margin-top:4px}</style>")


def html() -> str:
    try:
        cfg = json.loads((DATA / "live_worker.json").read_text(encoding="utf-8"))
        if not cfg.get("url"):
            return ""
        js = (Path(__file__).parent / "allerta_live.js").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    return (CSS + "<div id='allerta' class='alr'><b class='t' id='allerta-t'>Allerta vendite</b><div class='d' id='allerta-d'>Controllo dei segnali in corso…</div><div class='s' id='allerta-s'></div></div>"
            "<script>window.ALLERTA_LIVE=" + json.dumps({"url": cfg["url"]}) + ";" + js + "</script>")
