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
        raise RuntimeError(f"rapporti non disponibili per {sym}")
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
