"""Salute dei dati: per ogni serie importante, da quanti giorni non si aggiorna e se è normale (verde / giallo / rosso)."""
import html as _h
from datetime import datetime

import pandas as pd

from . import store

# (chiave, nome, ritardo normale in giorni)
KEY_SERIES = [
    ("sp500", "S&P 500", 4), ("vix", "VIX", 4), ("vt", "Azioni mondiali (VT)", 4), ("nasdaq100", "Nasdaq 100", 4),
    ("vix3m", "VIX a 3 mesi", 4), ("hy_oas", "Spread High Yield", 6), ("nfci", "Condizioni finanziarie (NFCI)", 12),
    ("t10y3m", "Curva 10Y-3M", 6), ("baa10y", "Spread BAA-10Y", 6), ("icsa", "Richieste sussidio", 12),
    ("cape_m", "CAPE", 50), ("pe_m", "P/E S&P 500", 50), ("ps_m", "P/S S&P 500", 120),
    ("val_pe_vwce", "P/E VWCE (fondo)", 4), ("aaii_spread", "Sentiment AAII", 12), ("unrate", "Disoccupazione", 50),
    # PIANO_MODELLO §3 (dati nuovi; le date dei trimestrali e mensili FRED sono l'inizio del periodo, quindi il ritardo normale è lungo)
    ("cp", "Profitti aziendali USA", 240), ("delinq_biz", "Prestiti alle imprese in ritardo", 240), ("core_cpi", "Inflazione di fondo", 75),
    ("cfnai", "Attività economica (CFNAI)", 90), ("m2", "Massa monetaria M2", 90), ("ciss", "Stress area euro (CISS)", 7),
    ("iwm", "Piccole aziende (IWM)", 4), ("rev_breadth", "Revisioni degli utili", 5), ("gs10_m", "Tasso 10 anni (storia lunga)", 75),
]
LIGHT = {"ok": "Aggiornato", "wa": "In ritardo", "ba": "Fermo", "na": "Nessun dato"}


def compute(status: dict | None = None, today: pd.Timestamp | None = None) -> list[dict]:
    today = (today or pd.Timestamp.now()).normalize()
    st = status if status is not None else store.read_status()
    rows = []
    for key, name, lag in KEY_SERIES:
        s = st.get(key, {})
        last = s.get("last_date")
        if not last:
            sr = store.load(key)
            last = None if sr.empty else sr.index[-1].strftime("%Y-%m-%d")
        if not last:
            rows.append({"key": key, "name": name, "last": None, "age": None, "light": "na", "msg": s.get("msg", ""), "ok": s.get("ok")})
            continue
        age = (today - pd.Timestamp(last)).days
        light = "ok" if age <= lag else ("wa" if age <= 2 * lag else "ba")
        rows.append({"key": key, "name": name, "last": last, "age": age, "light": light, "msg": s.get("msg", ""), "ok": s.get("ok")})
    return rows


def red_names(rows: list[dict]) -> list[str]:
    return [r["name"] for r in rows if r["light"] == "ba" and r["key"] in ("sp500", "vix", "vt", "hy_oas", "nfci", "t10y3m")]


def html(rows: list[dict]) -> str:
    e = _h.escape
    n_bad = sum(1 for r in rows if r["light"] in ("wa", "ba"))
    head = (f"<div class='sumline'><span class='badge {'ok' if n_bad == 0 else ('warn' if n_bad <= 3 else 'bad')}'>{len(rows) - n_bad} fonti su {len(rows)} aggiornate</span></div>")
    body = ""
    for r in sorted(rows, key=lambda r: ({"ba": 0, "wa": 1, "na": 2, "ok": 3}[r["light"]], r["name"])):
        age = "n.d." if r["age"] is None else ("oggi" if r["age"] == 0 else f"{r['age']} giorni fa")
        last = "—" if r["last"] is None else datetime.fromisoformat(r["last"]).strftime("%d/%m/%Y")
        note = e(r["msg"]) if r["msg"] else ""
        body += (f"<tr><td>{e(r['name'])}</td><td>{last}</td><td>{age}</td><td><span class='badge {({'ok': 'ok', 'wa': 'warn', 'ba': 'bad', 'na': 'warn'})[r['light']]}'>{LIGHT[r['light']]}</span></td>"
                 f"<td class='mu'>{note}</td></tr>")
    return (head + "<div class='scroll'><table><tr><th>Dato</th><th>Ultimo valore</th><th>Ritardo</th><th>Stato</th><th>Nota</th></tr>" + body + "</table></div>"
            "<p class='mu'>Verde = aggiornamento regolare per quel tipo di dato (i dati mensili e settimanali hanno ritardi normali più lunghi). "
            "Se un dato chiave è fermo, le stime che lo usano sono meno affidabili.</p>")
