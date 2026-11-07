"""Fonti aggiuntive (contesto e archivio): geopolitica, sentiment, ampiezza, grandi aziende, investimenti AI.
Ogni fonte e' indipendente e prudente: se fallisce, lo stato lo dice e le altre proseguono."""
import io
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import store
from .config import ARCHIVE
from .sources import UA, _get

# ---------------------------------------------------------------- geopolitica (GPR, Caldara-Iacoviello)
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"


def parse_gpr(df: pd.DataFrame) -> dict[str, pd.Series]:
    cols = {str(c).strip().upper(): c for c in df.columns}
    if "DATE" in cols:
        d = pd.to_datetime(df[cols["DATE"]], errors="coerce")
    elif "DAY" in cols:
        d = pd.to_datetime(df[cols["DAY"]].astype(str).str[:8], format="%Y%m%d", errors="coerce")
    else:
        raise RuntimeError("colonna data non trovata nel file GPR")
    out = {}
    for sid, name in (("gpr", "GPRD"), ("gpr_threat", "GPRD_THREAT"), ("gpr_act", "GPRD_ACT")):
        if name in cols:
            s = pd.to_numeric(df[cols[name]], errors="coerce").set_axis(d).dropna()
            out[sid] = s[s.index.notna()]
    if "gpr" not in out:
        raise RuntimeError("colonna GPRD non trovata")
    return out


def fetch_gpr() -> dict[str, pd.Series]:
    raw = _get(GPR_URL, timeout=90).content
    return parse_gpr(pd.read_excel(io.BytesIO(raw)))


# ---------------------------------------------------------------- sentiment: CNN Fear & Greed
def parse_fear_greed(js: dict) -> pd.Series:
    data = js["fear_and_greed_historical"]["data"]
    s = pd.Series({pd.to_datetime(x["x"], unit="ms").normalize(): float(x["y"]) for x in data}).sort_index()
    if s.empty:
        raise RuntimeError("nessun dato Fear & Greed")
    return s


def fetch_fear_greed() -> pd.Series:
    import requests
    r = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                     headers={**UA, "Accept": "application/json", "Origin": "https://edition.cnn.com",
                              "Referer": "https://edition.cnn.com/"}, timeout=40)
    r.raise_for_status()
    return parse_fear_greed(r.json())


# ---------------------------------------------------------------- ampiezza del mercato (titoli S&P 500)
def compute_breadth(close: pd.DataFrame) -> pd.DataFrame:
    """% titoli sopra media 50 e 200 giorni, nuovi massimi meno nuovi minimi a 52 settimane (in %)."""
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    valid50, valid200 = ma50.notna() & close.notna(), ma200.notna() & close.notna()
    out = pd.DataFrame(index=close.index)
    out["breadth50"] = ((close > ma50) & valid50).sum(axis=1) / valid50.sum(axis=1).replace(0, np.nan) * 100
    out["breadth200"] = ((close > ma200) & valid200).sum(axis=1) / valid200.sum(axis=1).replace(0, np.nan) * 100
    hi, lo = close.rolling(252, min_periods=200).max(), close.rolling(252, min_periods=200).min()
    n = (hi.notna() & close.notna()).sum(axis=1).replace(0, np.nan)
    out["nh_nl"] = (((close >= hi) & hi.notna()).sum(axis=1) - ((close <= lo) & lo.notna()).sum(axis=1)) / n * 100
    return out.dropna(how="all")


def sp500_tickers() -> list[str]:
    cache = ARCHIVE / "sp500_tickers.csv"
    try:
        html = _get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies").text
        t = pd.read_html(io.StringIO(html))[0]
        col = "Symbol" if "Symbol" in t.columns else t.columns[0]
        tickers = sorted({str(x).strip().replace(".", "-") for x in t[col] if str(x).strip()})
        if len(tickers) > 400:
            ARCHIVE.mkdir(parents=True, exist_ok=True)
            pd.Series(tickers, name="ticker").to_csv(cache, index=False)
            return tickers
    except Exception:  # noqa: BLE001
        pass
    if cache.exists():
        return pd.read_csv(cache)["ticker"].tolist()
    raise RuntimeError("elenco titoli S&P 500 non raggiungibile")


def fetch_breadth() -> pd.DataFrame:
    import yfinance as yf
    tickers = sp500_tickers()
    px = yf.download(tickers, period="2y", auto_adjust=True, progress=False, threads=True)["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
    px = px.dropna(axis=1, how="all")
    if px.shape[1] < 300:
        raise RuntimeError(f"solo {px.shape[1]} titoli scaricati")
    return compute_breadth(px)


# ---------------------------------------------------------------- grandi aziende e investimenti AI
TOP = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK-B", "LLY", "JPM", "V", "WMT", "XOM",
       "ORCL", "MA", "NFLX", "COST", "JNJ", "HD", "PG", "BAC", "ABBV", "TSM", "ASML", "AMD", "KO", "CVX", "CSCO", "UNH"]
AI_CAPEX = ["MSFT", "GOOGL", "AMZN", "META", "ORCL"]
FUND_FIELDS = ["marketCap", "trailingPE", "forwardPE", "priceToSalesTrailing12Months", "totalRevenue", "profitMargins",
               "freeCashflow", "operatingCashflow", "revenueGrowth", "earningsGrowth", "totalDebt", "totalCash"]


def aggregate_fundamentals(df: pd.DataFrame) -> dict[str, float]:
    """Indicatori ponderati per capitalizzazione sulle grandi aziende (df con colonne FUND_FIELDS)."""
    d = df.dropna(subset=["marketCap"])
    d = d[d.marketCap > 0]
    out = {}
    r = d.dropna(subset=["totalRevenue"])
    if len(r) >= 10 and r.totalRevenue.sum() > 0:
        out["top_ps"] = r.marketCap.sum() / r.totalRevenue.sum()
    e = d[(d.trailingPE > 0)]
    if len(e) >= 10:
        out["top_pe"] = e.marketCap.sum() / (e.marketCap / e.trailingPE).sum()
    f = d.dropna(subset=["freeCashflow"])
    if len(f) >= 10:
        out["top_fcf_yield"] = f.freeCashflow.sum() / f.marketCap.sum() * 100
    return out


def snapshot_fundamentals() -> dict[str, float]:
    import yfinance as yf
    rows = {}
    for t in TOP:
        try:
            info = yf.Ticker(t).info
            rows[t] = {k: info.get(k) for k in FUND_FIELDS}
        except Exception:  # noqa: BLE001
            continue
    if len(rows) < 15:
        raise RuntimeError(f"solo {len(rows)} aziende lette")
    df = pd.DataFrame(rows).T.apply(pd.to_numeric, errors="coerce")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (ARCHIVE / "fundamentals").mkdir(parents=True, exist_ok=True)
    df.rename_axis("ticker").to_csv(ARCHIVE / "fundamentals" / f"{day}.csv")
    return aggregate_fundamentals(df)


def _row(df: pd.DataFrame, *keys: str):
    for idx in df.index:
        low = str(idx).lower()
        if any(k in low for k in keys):
            return df.loc[idx]
    return None


def ttm_capex_ocf(cf: pd.DataFrame) -> tuple[float, float] | None:
    """Somma degli ultimi 4 trimestri di investimenti (capex) e flusso di cassa operativo."""
    cap, ocf = _row(cf, "capital expenditure"), _row(cf, "operating cash flow", "operating activities")
    if cap is None or ocf is None:
        return None
    cols = sorted(cf.columns, reverse=True)[:4]
    if len(cols) < 4:
        return None
    c, o = cap[cols].astype(float), ocf[cols].astype(float)
    if c.isna().any() or o.isna().any():
        return None
    return abs(float(c.sum())), float(o.sum())


def snapshot_ai_capex() -> float:
    import yfinance as yf
    tot_c = tot_o = 0.0
    parts = {}
    for t in AI_CAPEX:
        try:
            r = ttm_capex_ocf(yf.Ticker(t).quarterly_cashflow)
        except Exception:  # noqa: BLE001
            r = None
        if r:
            tot_c += r[0]
            tot_o += r[1]
            parts[t] = {"capex_ttm": r[0], "ocf_ttm": r[1]}
    if len(parts) < 3 or tot_o <= 0:
        raise RuntimeError("dati insufficienti per capex/flusso di cassa")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (ARCHIVE / "fundamentals").mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "fundamentals" / f"ai_capex_{day}.json").write_text(json.dumps(parts), encoding="utf-8")
    return tot_c / tot_o


# ---------------------------------------------------------------- orchestrazione
def update_extras(st: dict, only: list[str] | None = None) -> None:
    today = pd.Timestamp(datetime.now(timezone.utc).date())

    def run(ids: list[str], fn, as_series: bool = True):
        if only and not set(ids) & set(only):
            return
        try:
            print(f"[extras] {ids[0]} ...", flush=True)
            from .guard import with_timeout
            res = with_timeout(fn, 420 if ids[0] == "breadth50" else 240, ids[0])
            if isinstance(res, dict):
                for sid, s in res.items():
                    new = store.upsert(sid, s if isinstance(s, pd.Series) else pd.Series({today: float(s)}))
                    store.set_status(st, sid, True, "", new)
            elif isinstance(res, pd.DataFrame):
                for sid in res.columns:
                    store.set_status(st, sid, True, "", store.upsert(sid, res[sid]))
            elif isinstance(res, pd.Series):
                store.set_status(st, ids[0], True, "", store.upsert(ids[0], res))
            else:
                store.set_status(st, ids[0], True, "", store.upsert(ids[0], pd.Series({today: float(res)})))
        except Exception as e:  # noqa: BLE001
            print(f"[extras] {ids[0]} ERRORE: {str(e)[:120]}", flush=True)
            for sid in ids:
                store.set_status(st, sid, False, str(e))

    from .aaii import fetch_aaii
    run(["aaii_bull", "aaii_bear", "aaii_spread"], fetch_aaii)
    from .valuations import snapshot as snapshot_valuations
    run(["val_pe_vwce", "val_ps_vwce", "val_pe_sp500", "val_ps_sp500", "val_pe_ndx", "val_ps_ndx"], snapshot_valuations)
    run(["gpr", "gpr_threat", "gpr_act"], fetch_gpr)
    run(["fear_greed"], fetch_fear_greed)
    run(["breadth50", "breadth200", "nh_nl"], fetch_breadth)
    run(["top_ps", "top_pe", "top_fcf_yield"], snapshot_fundamentals)
    run(["ai_capex_ocf"], snapshot_ai_capex)
