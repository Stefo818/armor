"""Prezzi quasi in tempo reale (ritardo di circa 15 minuti, come Yahoo Finance) -> data/live.json."""
import json
from datetime import datetime, timezone

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


def best_vwce(get, errors: list) -> dict:
    """Legge tutte le sedi e sceglie l'ultimo scambio (a parita', la prima della lista: Xetra)."""
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
    ref = found[0]["price"]
    ok = [q for q in found if abs(q["price"] / ref - 1) < 0.03] or found   # scarta prezzi anomali
    t_max = max(q["time"] for q in ok)
    from datetime import datetime as _d
    recent = [q for q in ok if (_d.fromisoformat(t_max[:-1]) - _d.fromisoformat(q["time"][:-1])).total_seconds() <= 300]
    best = recent[0]
    best["alts"] = {q["venue"]: [round(q["price"], 2), q["time"]] for q in ok}
    return best


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
            if key == "vwce":
                q = best_vwce(get, errors)
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
            intraday[k] = {"t": [t for t, _ in pts], "v": [round(c, 4) for _, c in pts]}
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
