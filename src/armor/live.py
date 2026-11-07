"""Prezzi quasi in tempo reale (ritardo di circa 15 minuti, come Yahoo Finance) -> data/live.json."""
import json
from datetime import datetime, timezone

import requests

from .config import DATA

LIVE_FILE = DATA / "live.json"
QUOTES = {  # chiave: (simbolo Yahoo, nome, valuta)
    "vwce": ("VWCE.DE", "VWCE", "€"),
    "sp500": ("^GSPC", "S&P 500", ""),
    "sp_fut": ("ES=F", "Futures S&P 500", ""),
    "vix": ("^VIX", "VIX (paura)", ""),
    "eurusd": ("EURUSD=X", "Cambio EUR/USD", ""),
}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=5d"
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
    return {"price": float(price), "prev": float(prev) if prev else None,
            "chg": (float(price) / float(prev) - 1) if prev else None,
            "time": datetime.fromtimestamp(t_last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "open": is_open}


def fetch_all(get=None) -> dict:
    get = get or (lambda sym: requests.get(URL.format(sym=requests.utils.quote(sym)), headers=UA, timeout=20).json())
    old = {}
    try:
        old = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    quotes, errors = dict(old.get("quotes", {})), []
    for key, (sym, name, ccy) in QUOTES.items():
        try:
            q = parse_chart(get(sym))
            q.update(name=name, ccy=ccy, symbol=sym)
            quotes[key] = q
        except Exception as e:  # noqa: BLE001
            errors.append(f"{key}: {str(e)[:80]}")
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "quotes": quotes, "errors": errors}
    return out


def run() -> dict:
    out = fetch_all()
    LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, q in out["quotes"].items():
        c = "" if q.get("chg") is None else f"{q['chg'] * 100:+.2f}%"
        print(f"{k:8s} {q['price']:>10.2f} {c:>8s}  {q['time']}  {'aperto' if q['open'] else 'chiuso'}")
    for e in out["errors"]:
        print("ERR", e)
    return out


def load() -> dict:
    try:
        return json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
