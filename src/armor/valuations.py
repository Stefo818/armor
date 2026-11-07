"""Rapporti capitalizzazione/utili (P/E) e capitalizzazione/fatturato (P/S) di VWCE, S&P 500 e Nasdaq 100.
I fondi pubblicano questi rapporti una volta al giorno: li salviamo e li aggiorniamo "in tempo reale"
moltiplicandoli per la variazione del prezzo dell'indice da quel momento (gli utili cambiano lentamente)."""
from datetime import datetime, timezone

import pandas as pd

from . import live as livemod
from . import store

# chiave: (ETF di riferimento su Yahoo, nome, serie prezzi per il ricalcolo, quotazione live)
FUNDS = {
    "vwce": ("VT", "VWCE (mercato mondiale)", "vt", "vt"),
    "sp500": ("SPY", "S&P 500", "sp500", "sp500"),
    "ndx": ("QQQ", "Nasdaq 100", "nasdaq100", "ndx"),
}


def parse_equity_holdings(df: pd.DataFrame) -> dict[str, float]:
    """Estrae P/E e P/S dalla tabella dei fondi di Yahoo (righe 'Price/Earnings', 'Price/Sales')."""
    out = {}
    for idx in df.index:
        low = str(idx).lower().replace(" ", "")
        row = pd.to_numeric(df.loc[idx], errors="coerce").dropna()
        if row.empty:
            continue
        v = float(row.iloc[0])
        if "price/earnings" in low and v > 0:
            out["pe"] = v
        elif "price/sales" in low and v > 0:
            out["ps"] = v
    return out


def fetch_fund(sym: str) -> dict[str, float]:
    import yfinance as yf
    t = yf.Ticker(sym)
    out = {}
    try:
        out = parse_equity_holdings(t.funds_data.equity_holdings)
    except Exception:  # noqa: BLE001
        pass
    if "pe" not in out:
        try:
            info = t.info
            if info.get("trailingPE"):
                out["pe"] = float(info["trailingPE"])
        except Exception:  # noqa: BLE001
            pass
    if "pe" not in out and "ps" not in out:
        out = from_constituents(t)
        if out:
            print(f"[valuations] {sym}: rapporti stimati dai principali titoli", flush=True)
    if "pe" not in out and "ps" not in out:
        raise RuntimeError(f"rapporti non disponibili per {sym}")
    return out


def harmonic(vals: list[tuple[float, float]]) -> float | None:
    """Media armonica pesata (il modo corretto di mediare un P/E: si media l'inverso, cioe' gli utili per euro investito)."""
    vals = [(w, v) for w, v in vals if v and v > 0 and w and w > 0]
    if len(vals) < 5:
        return None
    tw = sum(w for w, _ in vals)
    return tw / sum(w / v for w, v in vals)


def from_constituents(t, n: int = 25) -> dict[str, float]:
    """Ripiego: P/E e P/S calcolati sui primi n titoli del fondo, pesati."""
    import yfinance as yf
    top = t.funds_data.top_holdings
    pe, ps = [], []
    for sym, r in list(top.iterrows())[:n]:
        w = float(r["Holding Percent"])
        try:
            info = yf.Ticker(str(sym)).info
        except Exception:  # noqa: BLE001
            continue
        pe.append((w, info.get("trailingPE")))
        ps.append((w, info.get("priceToSalesTrailing12Months")))
    out = {}
    a, b = harmonic([(w, float(v)) for w, v in pe if v]), harmonic([(w, float(v)) for w, v in ps if v])
    if a:
        out["pe"] = a
    if b:
        out["ps"] = b
    return out


def snapshot() -> dict[str, float]:
    """Salva i rapporti di oggi: serie val_pe_<chiave> e val_ps_<chiave>."""
    today = pd.Timestamp(datetime.now(timezone.utc).date())
    res, errs = {}, []
    for key, (sym, *_rest) in FUNDS.items():
        try:
            m = fetch_fund(sym)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{sym}: {str(e)[:60]}")
            continue
        for k, v in m.items():
            res[f"val_{k}_{key}"] = pd.Series({today: v})
    if not res:
        raise RuntimeError("; ".join(errs) or "nessun dato")
    return res


def _price_at(series_key: str, d: pd.Timestamp):
    s = store.load(series_key)
    s = s[s.index <= d]
    return float(s.iloc[-1]) if len(s) else None


def current() -> list[dict]:
    """Rapporti attuali per le tre schede: valore ricalcolato col prezzo di adesso + contesto storico."""
    q = livemod.load().get("quotes", {})
    cards = []
    for key, (sym, name, pkey, lkey) in FUNDS.items():
        card = {"key": key, "name": name, "pe": None, "ps": None, "note": "", "pe_pct": None, "ps_pct": None, "src": ""}
        live_p = (q.get(lkey) or {}).get("price")
        for m in ("pe", "ps"):
            s = store.load(f"val_{m}_{key}")
            if len(s):
                d, v0 = s.index[-1], float(s.iloc[-1])
                p0 = _price_at(pkey, d)
                p1 = live_p if live_p else _price_at(pkey, pd.Timestamp.now().normalize())
                scale = (p1 / p0) if (p0 and p1) else 1.0
                card[m] = v0 * scale
                card["src"] = f"Rapporti dei fondi del {d.strftime('%d/%m/%Y')}, aggiornati con il prezzo di adesso"
                if len(s) >= 30:
                    card[m + "_pct"] = float((s < card[m]).mean() * 100)
        if key == "sp500" and (card["pe"] is None or card["ps"] is None):   # ripiego: dati storici di multpl
            for m, ser in (("pe", "pe_m"), ("ps", "ps_m")):
                s = store.load(ser)
                if len(s) and card[m] is None:
                    p0 = _price_at("sp500", s.index[-1])
                    p1 = live_p or _price_at("sp500", pd.Timestamp.now().normalize())
                    card[m] = float(s.iloc[-1]) * ((p1 / p0) if (p0 and p1) else 1.0)
                    card["src"] = "Dati mensili di multpl.com, aggiornati con il prezzo di adesso"
        if key == "sp500":
            for m, ser in (("pe", "pe_m"), ("ps", "ps_m")):
                s = store.load(ser)
                if len(s) > 200 and card[m] is not None:
                    card[m + "_pct"] = float((s < card[m]).mean() * 100)
                    card[m + "_avg"] = float(s.mean())
                    card[m + "_since"] = s.index[0].year
        if card["pe"] is None and card["ps"] is None:
            card["note"] = "Dato non ancora disponibile: compare dopo il primo aggiornamento che riesce a leggerlo."
        cards.append(card)
    return cards


ZONES = {  # (soglia gialla, soglia rossa) indicative; per l'S&P 500 sono quelle storiche usate nell'analisi
    ("sp500", "pe"): (17, 24), ("sp500", "ps"): (2, 3), ("vwce", "pe"): (17, 21), ("vwce", "ps"): (2, 2.8),
    ("ndx", "pe"): (24, 30), ("ndx", "ps"): (4, 6),
}


def zone(key: str, m: str, v: float | None) -> str | None:
    if v is None or (key, m) not in ZONES:
        return None
    y, r = ZONES[(key, m)]
    return "ok" if v < y else ("wa" if v < r else "ba")


def history_context(ser_key: str, value: float, tol: float = 0.10) -> dict | None:
    """Cosa e' successo all'S&P 500 dopo i giorni in cui il rapporto valeva come oggi (entro +-10%), a 3, 6 e 12 mesi."""
    import numpy as np
    from .features import closed_sp500, fwd_maxdd, fwd_ret
    s = store.load(ser_key)
    p = closed_sp500()
    if len(s) < 200 or value is None:
        return None
    d = s.reindex(pd.date_range(s.index[0], p.index[-1])).ffill(limit=45).shift(1).reindex(p.index).dropna()
    vals = s.dropna()
    res = {"avg": float(vals.mean()), "median": float(vals.median()), "p75": float(vals.quantile(.75)), "p90": float(vals.quantile(.90)),
           "since": int(s.index[0].year), "pct": float((vals < value).mean() * 100), "rows": []}
    near = d[(d >= value * (1 - tol)) & (d <= value * (1 + tol))]
    res["n_days"], res["n_years"] = int(len(near)), int(near.index.year.nunique()) if len(near) else 0
    for lab, h in (("3 mesi", 63), ("6 mesi", 126), ("1 anno", 252)):
        r = fwd_ret(p, h)
        a, b = r.reindex(near.index).dropna(), r.reindex(d.index).dropna()
        row = {"orizzonte": lab, "n": int(len(a))}
        if len(a) >= 30:
            row.update(mean=float(a.mean()), median=float(a.median()), pos=float((a > 0).mean()), p10=float(a.quantile(.10)),
                       all_mean=float(b.mean()), all_pos=float((b > 0).mean()))
            if h == 63:
                dd = fwd_maxdd(p, 63)
                row["dd10"] = float((dd.reindex(near.index).dropna() <= -0.10).mean())
                row["all_dd10"] = float((dd.reindex(d.index).dropna() <= -0.10).mean())
        res["rows"].append(row)
    return res
