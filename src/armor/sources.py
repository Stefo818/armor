"""Scaricamento dati da fonti gratuite. Ogni fonte e' indipendente: se una fallisce le altre proseguono."""
import io
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from . import store

UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}

# id -> (simbolo yfinance, fuso del mercato, ora chiusura HH:MM)
YF = {
    "sp500": ("^GSPC", "America/New_York", "16:30"),
    "vix": ("^VIX", "America/New_York", "16:30"),
    "vix3m": ("^VIX3M", "America/New_York", "16:30"),
    "vix9d": ("^VIX9D", "America/New_York", "16:30"),
    "vvix": ("^VVIX", "America/New_York", "16:30"),
    "skew": ("^SKEW", "America/New_York", "16:30"),
    "move": ("^MOVE", "America/New_York", "16:30"),
    "nasdaq100": ("^NDX", "America/New_York", "16:30"),
    "vt": ("VT", "America/New_York", "16:30"),
    "hyg": ("HYG", "America/New_York", "16:30"),
    "ief": ("IEF", "America/New_York", "16:30"),
    "rsp": ("RSP", "America/New_York", "16:30"),
    "spy": ("SPY", "America/New_York", "16:30"),
    "gold": ("GC=F", "America/New_York", "18:30"),
    "wti": ("CL=F", "America/New_York", "18:30"),
    "dxy": ("DX-Y.NYB", "America/New_York", "18:30"),
    "eurusd": ("EURUSD=X", "UTC", "23:59"),
    "vwce_de": ("VWCE.DE", "Europe/Berlin", "17:50"),
}

# id -> codice FRED (CSV pubblico, nessuna chiave necessaria)
FRED = {
    "baa10y": "BAA10Y", "t10y2y": "T10Y2Y", "t10y3m": "T10Y3M",
    "hy_oas": "BAMLH0A0HYM2", "ig_oas": "BAMLC0A0CM",
    "nfci": "NFCI", "stlfsi": "STLFSI4",
    "real10y": "DFII10", "be10y": "T10YIE", "dgs10": "DGS10", "dgs2": "DGS2", "fedfunds": "DFF",
    "usd_broad": "DTWEXBGS", "epu": "USEPUINDXD",
    "icsa": "ICSA", "unrate": "UNRATE", "cpi": "CPIAUCSL",
    "equity_value": "NCBEILQ027S", "gdp": "GDP",
}

CBOE = {"pput": "https://cdn.cboe.com/api/global/us_indices/daily_prices/PPUT_History.csv"}

MULTPL = {
    "ps_m": "https://www.multpl.com/s-p-500-price-to-sales/table/by-quarter",
    "cape_m": "https://www.multpl.com/shiller-pe/table/by-month",
    "pe_m": "https://www.multpl.com/s-p-500-pe-ratio/table/by-month",
}

SHILLER_URLS = [
    "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
    "https://img1.wsimg.com/blobby/go/e5e77e9f-e23f-40a5-9bb8-8d1bc3c4a7e3/downloads/ie_data.xls",
]


def _get(url: str, tries: int = 3, timeout: int = 40) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(str(last))


def drop_open_session(s: pd.Series, tz: str, close_hhmm: str) -> pd.Series:
    """Toglie l'ultima riga se la seduta di oggi non e' ancora chiusa (dato provvisorio)."""
    if s.empty:
        return s
    now = datetime.now(ZoneInfo(tz))
    hh, mm = map(int, close_hhmm.split(":"))
    closed = now.hour * 60 + now.minute >= hh * 60 + mm
    if s.index[-1].date() == now.date() and not closed:
        return s.iloc[:-1]
    return s


def fetch_yf(sid: str, start: str | None) -> pd.Series:
    import yfinance as yf

    sym, tz, close = YF[sid]
    last = None
    for i in range(3):
        try:
            tk = yf.Ticker(sym)
            h = tk.history(period="max", auto_adjust=True, actions=False) if start is None else tk.history(start=start, auto_adjust=True, actions=False)
            if h is not None and not h.empty:
                s = h["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                s = s[s > 0]
                return drop_open_session(s, tz, close)
            last = "nessun dato"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(3 * (i + 1))
    raise RuntimeError(last or "errore")


def fetch_fred(code: str) -> pd.Series:
    r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}", tries=2, timeout=25)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"]


def fetch_cboe(url: str) -> pd.Series:
    r = _get(url)
    txt = r.text
    lines = txt.splitlines()
    k = next(i for i, ln in enumerate(lines[:20]) if ln.lower().startswith("date"))
    df = pd.read_csv(io.StringIO("\n".join(lines[k:])))
    df.columns = [c.strip().lower() for c in df.columns]
    col = next(c for c in df.columns if c != "date")
    df["date"] = pd.to_datetime(df["date"])
    return pd.to_numeric(df[col], errors="coerce").set_axis(df["date"]).dropna()


def parse_multpl(text: str) -> pd.Series:
    """Estrae coppie data/valore dalla tabella di multpl.com (accetta HTML o testo copiato)."""
    import re
    dates = list(re.finditer(r"([A-Z][a-z]{2} \d{1,2}, \d{4})", text))
    out = {}
    for i, m in enumerate(dates):
        end = dates[i + 1].start() if i + 1 < len(dates) else len(text)
        seg = text[m.end():min(end, m.end() + 400)]
        v = re.search(r"(-?\d+(?:[.,]\d+)?)", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", seg)).replace("†", " "))
        if v:
            out[pd.to_datetime(m.group(1))] = float(v.group(1).replace(",", ""))
    if not out:
        raise RuntimeError("tabella multpl non riconosciuta")
    return pd.Series(out).sort_index()


def fetch_multpl(url: str) -> pd.Series:
    return parse_multpl(_get(url).text)


def fetch_shiller() -> dict[str, pd.Series]:
    """CAPE e P/E (Shiller). Dati mensili, pubblicati con ritardo: usati solo come contesto."""
    last = None
    for url in SHILLER_URLS:
        try:
            raw = _get(url, timeout=90).content
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Data", header=None)
            hdr = next(i for i in range(0, 15) if any(str(c).strip().upper() == "CAPE" for c in df.iloc[i]))
            col_cape = next(j for j, c in enumerate(df.iloc[hdr]) if str(c).strip().upper() == "CAPE")
            body = df.iloc[hdr + 1:].copy()
            body = body[pd.to_numeric(body[0], errors="coerce").notna()]
            dt = pd.to_numeric(body[0])
            year = dt.astype(int)
            month = ((dt - year) * 100).round().astype(int).clip(1, 12)
            idx = pd.to_datetime(dict(year=year, month=month, day=1)) + pd.offsets.MonthEnd(0)
            price = pd.to_numeric(body[1], errors="coerce").set_axis(idx)
            earn = pd.to_numeric(body[3], errors="coerce").set_axis(idx)
            cape = pd.to_numeric(body[col_cape], errors="coerce").set_axis(idx)
            pe = (price / earn).replace([float("inf")], float("nan"))
            return {"cape": cape.dropna(), "pe_trailing": pe.dropna()}
        except Exception as e:  # noqa: BLE001
            last = str(e)
    raise RuntimeError(last or "errore")


def update_all(full: bool = False, only: list[str] | None = None) -> dict:
    """Aggiorna tutte le serie. Restituisce lo stato per serie (salvato in data/status.json)."""
    st = store.read_status()
    for sid in YF:
        if only and sid not in only:
            continue
        try:
            old = store.load(sid)
            start = None if (full or old.empty) else (old.index[-1] - timedelta(days=12)).strftime("%Y-%m-%d")
            n = store.upsert(sid, fetch_yf(sid, start))
            store.set_status(st, sid, True, "", n)
        except Exception as e:  # noqa: BLE001
            store.set_status(st, sid, False, str(e))
    fred_fails = 0
    for sid, code in FRED.items():
        if only and sid not in only:
            continue
        if fred_fails >= 2:  # FRED non risponde: si salta il resto invece di aspettare per ogni serie
            store.set_status(st, sid, False, "FRED non raggiungibile: saltata (si aggiorna dal PC)")
            continue
        try:
            store.set_status(st, sid, True, "", store.upsert(sid, fetch_fred(code)))
            fred_fails = 0
        except Exception as e:  # noqa: BLE001
            fred_fails += 1
            store.set_status(st, sid, False, str(e))
    for sid, url in CBOE.items():
        if only and sid not in only:
            continue
        try:
            store.set_status(st, sid, True, "", store.upsert(sid, fetch_cboe(url)))
        except Exception as e:  # noqa: BLE001
            store.set_status(st, sid, False, str(e))
    for sid, url in MULTPL.items():
        if only and sid not in only:
            continue
        try:
            store.set_status(st, sid, True, "", store.upsert(sid, fetch_multpl(url)))
        except Exception as e:  # noqa: BLE001
            store.set_status(st, sid, False, str(e))
    try:
        from . import extras
        extras.update_extras(st, only)
    except Exception as e:  # noqa: BLE001
        store.set_status(st, 'extras', False, str(e))
    store.write_status(st)
    return st
