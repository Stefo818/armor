"""Archivio giornaliero delle opzioni SPY (non ricostruibile dopo): catena grezza + riepilogo."""
import gzip
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import ARCHIVE


def riepilogo(df: pd.DataFrame, spot: float, day: str) -> dict:
    """Una riga al giorno dalla catena: put/call (volumi e open interest), IV at-the-money a 30 giorni, skew put (95%, 90%, 80%) e call (105%),
    IV a scadenza breve (~7 giorni) e lunga (la più lontana archiviata) per la struttura a termine, numero di contratti e volume totale."""
    P, C = df[df.type == "P"], df[df.type == "C"]
    exp = pd.to_datetime(df.expiry)
    days = (exp - pd.Timestamp(day)).dt.days

    def scad(giorni):
        return df.loc[(days - giorni).abs().idxmin(), "expiry"]

    def iv_at(d, kind, k):
        x = d[d.type == kind]
        return float(x.iloc[(x.strike - k * spot).abs().argsort()[:1]]["impliedVolatility"].iloc[0])

    def atm(d):
        return float(np.mean([iv_at(d, "C", 1.0), iv_at(d, "P", 1.0)]))
    d30 = df[df.expiry == scad(30)]
    a30 = atm(d30)
    breve, lunga = df[df.expiry == scad(7)], df[df.expiry == df.loc[days.idxmax(), "expiry"]]
    return {"date": day, "spot": spot, "pc_volume": P.volume.sum() / max(C.volume.sum(), 1),
            "pc_open_interest": P.openInterest.sum() / max(C.openInterest.sum(), 1),
            "iv_atm_30d": a30, "put_skew_95": iv_at(d30, "P", 0.95) - a30, "put_skew_90": iv_at(d30, "P", 0.90) - a30,
            "put_skew_80": iv_at(d30, "P", 0.80) - a30, "call_skew_105": iv_at(d30, "C", 1.05) - a30,
            "iv_atm_breve": atm(breve), "giorni_breve": int(days[breve.index[0]]), "iv_atm_lunga": atm(lunga), "giorni_lunga": int(days[lunga.index[0]]),
            "n_contratti": int(len(df)), "volume_totale": float(df.volume.sum())}


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
    tutte = list(t.options)
    lontane = [min(tutte, key=lambda e, g=g: abs((pd.Timestamp(e) - pd.Timestamp(day)).days - g)) for g in (60, 90, 180)] if tutte else []
    for e in sorted(set(tutte[:6]) | set(lontane)):   # le prime 6 scadenze più tre lontane (~60, 90, 180 giorni) per la struttura a termine
        ch = t.option_chain(e)
        frames.append(ch.calls.assign(type="C", expiry=e))
        frames.append(ch.puts.assign(type="P", expiry=e))
    df = pd.concat(frames, ignore_index=True)
    df["spot"] = spot
    df["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with gzip.open(f, "wt", encoding="utf-8") as fh:
        df.to_csv(fh, index=False)
    row = riepilogo(df, spot, day)
    s = ARCHIVE / "spy_options_summary.csv"
    old = pd.read_csv(s) if s.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame([row])]).drop_duplicates("date", keep="last").to_csv(s, index=False, float_format="%.5g")
    return "ok"
