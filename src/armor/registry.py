"""Registro giornaliero: una riga per ogni giorno con tutti i valori salvati (si accumula, si consulta e si scarica)."""
import pandas as pd

from . import journal, store
from .config import DATA, HORIZONS, PRIMARY

REGISTRY = DATA / "registry" / "daily.csv"
EXTRA_KEYS = ["vwce", "vt", "nasdaq100", "val_pe_vwce", "val_ps_vwce", "val_pe_sp500", "val_ps_sp500", "val_pe_ndx", "val_ps_ndx",
              "aaii_spread", "aaii_bull", "aaii_bear", "fear_greed", "breadth200", "breadth50", "nh_nl", "gpr", "top_ps", "top_pe",
              "top_fcf_yield", "ai_capex_ocf"]


def keys(indicators: list) -> list[str]:
    ks = []
    for _g, items in indicators:
        for _l, k, _b, _d in items:
            if k not in ks and not k.startswith("spy_") and k not in ("dd252", "vterm", "eq_gdp", "rsp_spy"):
                ks.append(k)
    return ks + [k for k in EXTRA_KEYS if k not in ks]


def row_for(date: pd.Timestamp, pred: dict, indicators: list, spot: float, news_summary: dict | None = None, extra: dict | None = None) -> dict:
    row = {"date": date.strftime("%Y-%m-%d")}
    for k in keys(indicators):
        s = store.load(k)
        s = s[s.index <= date] if len(s) else s
        if len(s):
            row[k] = round(float(s.iloc[-1]), 5)
            row[k + "_data"] = s.index[-1].strftime("%Y-%m-%d")   # data del dato (alcuni sono mensili/settimanali)
    if spot == spot:
        row["vwce_ultimo"] = round(float(spot), 4)
    for hz in HORIZONS:
        if hz in pred:
            r = pred[hz]
            row[f"p_{hz}"] = round(r["p"][PRIMARY[hz]], 5)
            row[f"livello_{hz}"] = r["level"]
    if news_summary:
        for k, v in news_summary.items():
            row[k] = v
    for k, v in (extra or {}).items():
        row[k] = v
    return row


def append(row: dict) -> int:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame([row])
    if REGISTRY.exists():
        old = pd.read_csv(REGISTRY, dtype=str)
        old = old[old["date"] != row["date"]]
        df = pd.concat([old, new.astype(str)], ignore_index=True, sort=False)
    else:
        df = new
    cols = ["date"] + sorted(c for c in df.columns if c != "date")
    df.sort_values("date")[cols].to_csv(REGISTRY, index=False)
    return len(df)


def read() -> pd.DataFrame:
    try:
        return pd.read_csv(REGISTRY)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
