"""Archivio giornaliero delle opzioni SPY (non ricostruibile dopo): catena grezza + riepilogo."""
import gzip
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import ARCHIVE


def archive_spy_options() -> str:
    import yfinance as yf

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    chains = ARCHIVE / "chains"
    chains.mkdir(parents=True, exist_ok=True)
    f = chains / f"spy_{day}.csv.gz"
    if f.exists():
        return "gia' archiviato oggi"
    t = yf.Ticker("SPY")
    spot = float(t.history(period="1d")["Close"].iloc[-1])
    frames = []
    for e in t.options[:6]:
        ch = t.option_chain(e)
        frames.append(ch.calls.assign(type="C", expiry=e))
        frames.append(ch.puts.assign(type="P", expiry=e))
    df = pd.concat(frames, ignore_index=True)
    df["spot"] = spot
    df["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with gzip.open(f, "wt", encoding="utf-8") as fh:
        df.to_csv(fh, index=False)
    # riepilogo: put/call su volumi e open interest, IV at-the-money e skew a ~30 giorni
    P, C = df[df.type == "P"], df[df.type == "C"]
    exp = pd.to_datetime(df.expiry)
    days = (exp - pd.Timestamp(day)).dt.days
    target = df.loc[(days - 30).abs().idxmin(), "expiry"]
    d = df[df.expiry == target]
    def iv_at(kind, k):
        x = d[d.type == kind]
        return float(x.iloc[(x.strike - k * spot).abs().argsort()[:1]]["impliedVolatility"].iloc[0])
    atm = np.mean([iv_at("C", 1.0), iv_at("P", 1.0)])
    row = {"date": day, "spot": spot, "pc_volume": P.volume.sum() / max(C.volume.sum(), 1),
           "pc_open_interest": P.openInterest.sum() / max(C.openInterest.sum(), 1),
           "iv_atm_30d": atm, "put_skew_95": iv_at("P", 0.95) - atm, "put_skew_90": iv_at("P", 0.90) - atm}
    s = ARCHIVE / "spy_options_summary.csv"
    old = pd.read_csv(s) if s.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame([row])]).drop_duplicates("date", keep="last").to_csv(s, index=False, float_format="%.5g")
    return "ok"
