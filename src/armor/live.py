"""Prezzi quasi in tempo reale (ritardo di circa 15 minuti, come Yahoo Finance) -> data/live.json."""
import json
from datetime import datetime, timezone

import pandas as pd
import requests

from .config import DATA

LIVE_FILE = DATA / "live.json"
VWCE_VENUES = [  # sedi su cui il VWCE e' quotato in euro: vince l'ultimo scambio (alcune restano aperte fino alle 22-23)
    ("VWCE.DE", "Xetra"), ("VWCE.MI", "Borsa Italiana"), ("VWCE.F", "Francoforte"), ("VWCE.SG", "Stoccarda"),
    ("VWCE.MU", "Monaco/gettex"), ("VWCE.BE", "Berlino"), ("VWCE.DU", "Düsseldorf")]
QUOTES = {  # chiave: (simbolo Yahoo, nome, valuta)
    "vwce": ("VWCE.DE", "VWCE", "€"),
    "sp500": ("^GSPC", "S&P 500", ""),
    "sp_fut": ("ES=F", "Futures S&P 500", ""),
    "vix": ("^VIX", "VIX (paura)", ""),
    "eurusd": ("EURUSD=X", "Cambio EUR/USD", ""),
    "vt": ("VT", "VT (azioni mondiali in dollari)", "$"),
    "ndx": ("^NDX", "Nasdaq 100", ""),
}
HIDDEN_IN_BAR = {"vt", "ndx"}   # servono per le valutazioni e i grafici, non per la barra in alto
INTRADAY_FILE = DATA / "intraday.json"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=5d"
URL1 = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d"
UA = {"User-Agent": "Mozilla/5.0 (Armor personal dashboard)"}


def parse_chart(js: dict, now_ts: float | None = None) -> dict:
    """Estrae prezzo, chiusura precedente e stato mercato da una risposta chart di Yahoo."""
    r = js["chart"]["result"][0]
    meta, ts = r["meta"], r.get("timestamp") or []
    closes = r["indicators"]["quote"][0]["close"]
    off = int(meta.get("gmtoffset", 0))
    pts = [(t, c) for t, c in zip(ts, closes) if c is not None]
    if not pts:
        raise ValueError("nessun prezzo")
    day = lambda t: (t + off) // 86400
    t_last, price = pts[-1]
    prev = next((c for t, c in reversed(pts) if day(t) < day(t_last)), None)
    if prev is None:
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    if meta.get("regularMarketPrice") and meta.get("regularMarketTime", 0) >= t_last:
        price, t_last = float(meta["regularMarketPrice"]), int(meta["regularMarketTime"])
    now_ts = now_ts or datetime.now(timezone.utc).timestamp()
    reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    is_open = bool(reg and reg.get("start", 0) <= now_ts <= reg.get("end", 0)) and now_ts - t_last < 3600
    return {"_pts": [(int(t), float(c)) for t, c in pts], "price": float(price), "prev": float(prev) if prev else None,
            "chg": (float(price) / float(prev) - 1) if prev else None,
            "time": datetime.fromtimestamp(t_last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "open": is_open}


VWCE_ISIN = "IE00BK5BQT80"
# fonti con le sedi serali (Lang & Schwarz fino alle 23, Tradegate e gettex fino alle 22): se rispondono, vince l'ultimo scambio
EXTRA_URLS = [
    ("onvista", "https://api.onvista.de/api/v1/instruments/FUND/ISIN:{isin}/snapshot"),
    ("onvista", "https://api.onvista.de/api/v1/etfs/ISIN:{isin}/snapshot"),
    ("tradegate", "https://www.tradegate.de/refresh.php?isin={isin}"),
]


def _num(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(".", "").replace(",", ".")) if "," in str(x) else float(x)
    except Exception:  # noqa: BLE001
        return None


def parse_venues(js, fonte: str) -> list:
    """Cerca nella risposta (qualsiasi struttura) le quotazioni in euro con prezzo, ora e sede. Restituisce [{price, time, venue, prev}]."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            price = _num(o.get("last")) if o.get("last") is not None else None
            t = o.get("datetimeLast") or o.get("datetime") or o.get("lastTradeTime")
            cur = o.get("isoCurrency") or o.get("currency")
            mk = o.get("market")
            venue = (mk.get("name") if isinstance(mk, dict) else None) or o.get("marketName") or (mk if isinstance(mk, str) else None)
            if price and t and (cur in (None, "EUR")):
                try:
                    ts = pd.Timestamp(t)
                    ts = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("Europe/Berlin").tz_convert("UTC")
                    prev = _num(o.get("previousLast") or o.get("previousClose") or o.get("close") or 0) or None
                    out.append({"price": price, "time": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "venue": str(venue or fonte), "prev": prev})
                except Exception:  # noqa: BLE001
                    pass
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(js)
    return out


def parse_tradegate(js: dict, now=None) -> list:
    """Tradegate (refresh.php) dà l'ultimo prezzo senza l'ora: si usa solo se oggi ci sono stati scambi, con ora = adesso (o le 22:00 a mercato chiuso)."""
    last = _num(js.get("last"))
    if not last or not _num(js.get("executions") or 0):
        return []
    now = pd.Timestamp(now or pd.Timestamp.now(tz="Europe/Berlin"))
    now = now.tz_convert("Europe/Berlin") if now.tzinfo else now.tz_localize("Europe/Berlin")
    t = min(now, now.normalize() + pd.Timedelta(hours=22))
    prev = _num(js.get("close")) or None
    return [{"price": last, "time": t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "venue": "Tradegate", "prev": prev}]


def extra_venues(errors: list, get_json=None) -> list:
    get_json = get_json or (lambda u: requests.get(u, headers=UA, timeout=15).json())
    out, seen = [], set()
    for fonte, url in EXTRA_URLS:
        if fonte in seen:
            continue
        try:
            js = get_json(url.format(isin=VWCE_ISIN))
            v = parse_tradegate(js) if fonte == "tradegate" else parse_venues(js, fonte)
            if v:
                out += v
                seen.add(fonte)
        except Exception as e:  # noqa: BLE001
            errors.append(f"vwce {fonte}: {str(e)[:60]}")
    return out


def best_vwce(get, errors: list, extra: list | None = None) -> dict:
    """Legge tutte le sedi (Yahoo + fonti serali) e sceglie l'ultimo scambio (a parità, la prima della lista: Xetra)."""
    found = []
    for sym, venue in VWCE_VENUES:
        try:
            q = parse_chart(get(sym))
            q.update(name="VWCE", ccy="€", symbol=sym, venue=venue)
            found.append(q)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{sym}: {str(e)[:60]}")
    if not found:
        raise RuntimeError("nessuna sede raggiungibile")
    prev_ref = found[0].get("prev")
    for v in (extra or []):   # sedi serali: stessa struttura delle quotazioni Yahoo
        q = {"price": v["price"], "prev": v.get("prev") or prev_ref, "time": v["time"], "open": False, "name": "VWCE", "ccy": "€",
             "symbol": found[0]["symbol"], "venue": v["venue"]}
        q["chg"] = (q["price"] / q["prev"] - 1) if q["prev"] else None
        found.append(q)
    ref = found[0]["price"]
    ok = [q for q in found if abs(q["price"] / ref - 1) < 0.03] or found   # scarta prezzi anomali
    t_max = max(q["time"] for q in ok)
    from datetime import datetime as _d
    recent = [q for q in ok if (_d.fromisoformat(t_max[:-1]) - _d.fromisoformat(q["time"][:-1])).total_seconds() <= 300]
    best = recent[0]
    best["alts"] = {q["venue"]: [round(q["price"], 2), q["time"]] for q in ok}
    return best


def fine_series(pts: list) -> dict:
    """Da punti al minuto: ultimi 90 minuti ai minuti (grafico 1 ora) e ultime 12 ore ogni 10 minuti (grafico 6 ore)."""
    if not pts:
        return {}
    t_end = pts[-1][0]
    one = [(t, c) for t, c in pts if t >= t_end - 5400]
    ten = {}
    for t, c in pts:
        if t >= t_end - 43200:
            ten[t // 600 * 600] = c
    return {"t1": [t for t, _ in one], "v1": [round(c, 4) for _, c in one],
            "t10": list(ten.keys()), "v10": [round(c, 4) for c in ten.values()]}


def fetch_all(get=None, get1=None) -> dict:
    get = get or (lambda sym: requests.get(URL.format(sym=requests.utils.quote(sym)), headers=UA, timeout=20).json())
    old = {}
    try:
        old = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    quotes, errors = dict(old.get("quotes", {})), []
    for key, (sym, name, ccy) in QUOTES.items():
        try:
            if key == "vwce":
                q = best_vwce(get, errors, extra_venues(errors))
            else:
                q = parse_chart(get(sym))
                q.update(name=name, ccy=ccy, symbol=sym)
            quotes[key] = q
        except Exception as e:  # noqa: BLE001
            errors.append(f"{key}: {str(e)[:80]}")
    intraday = {}
    for k, q in quotes.items():
        pts = q.pop("_pts", None)
        if pts:
            intraday[k] = {"t": [t for t, _ in pts], "v": [round(c, 4) for _, c in pts], "sym": q.get("symbol")}
    get1 = get1 or (lambda sym: requests.get(URL1.format(sym=requests.utils.quote(sym)), headers=UA, timeout=20).json())
    for k, q in quotes.items():
        if k not in intraday or k in ("sp_fut",):
            continue
        try:
            fine = fine_series(parse_chart(get1(q["symbol"]))["_pts"])
            intraday[k].update(fine)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{k} 1m: {str(e)[:60]}")
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "quotes": quotes, "errors": errors,
           "_intraday": intraday}
    return out


def run() -> dict:
    out = fetch_all()
    LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    intraday = out.pop("_intraday", {})
    LIVE_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if intraday:
        INTRADAY_FILE.write_text(json.dumps(intraday), encoding="utf-8")
    v = out["quotes"].get("vwce") or {}
    if v:
        print(f"[live] VWCE: {v.get('price')} da {v.get('venue')} alle {v.get('time')} · sedi lette: "
              + ", ".join(f"{k} {p[0]} ({p[1][11:16]} UTC)" for k, p in (v.get("alts") or {}).items()))
    for k, q in out["quotes"].items():
        c = "" if q.get("chg") is None else f"{q['chg'] * 100:+.2f}%"
        print(f"{k:8s} {q['price']:>10.2f} {c:>8s}  {q['time']}  {'aperto' if q['open'] else 'chiuso'}  {q.get('venue', '')}")
    for e in out["errors"]:
        print("ERR", e)
    return out


def load_intraday() -> dict:
    try:
        return json.loads(INTRADAY_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def load() -> dict:
    try:
        return json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
