"""Archivio delle serie storiche: un CSV per serie (data,value) in data/series/."""
import json
from datetime import datetime, timezone

import pandas as pd

from .config import SERIES, STATUS_FILE


def path(sid: str):
    return SERIES / f"{sid}.csv"


def load(sid: str) -> pd.Series:
    """Legge una serie; se manca restituisce una serie vuota."""
    p = path(sid)
    if not p.exists():
        return pd.Series(dtype=float, name=sid)
    df = pd.read_csv(p, parse_dates=["date"])
    s = df.set_index("date")["value"].astype(float).sort_index()
    s.name = sid
    return s[~s.index.duplicated(keep="last")]


def upsert(sid: str, new: pd.Series) -> int:
    """Unisce i nuovi valori (i piu' recenti vincono). Idempotente. Restituisce le righe nuove."""
    new = pd.to_numeric(new, errors="coerce").dropna()
    if new.empty:
        return 0
    new.index = pd.to_datetime(new.index).tz_localize(None).normalize()
    old = load(sid)
    merged = pd.concat([old, new])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    added = len(merged.index.difference(old.index))
    SERIES.mkdir(parents=True, exist_ok=True)
    out = merged.rename("value").rename_axis("date").reset_index()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path(sid), index=False, float_format="%.6g")
    return added


def read_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def write_status(st: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")


def set_status(st: dict, sid: str, ok: bool, msg: str = "", new: int = 0) -> None:
    s = load(sid)
    st[sid] = {
        "ok": ok,
        "stato": "ok" if ok else ("mai scaricata" if s.empty else "ritardo"),   # se il download fallisce il file esistente resta com'è
        "msg": msg[:200],
        "new_rows": new,
        "last_date": None if s.empty else s.index[-1].strftime("%Y-%m-%d"),
        "rows": int(len(s)),
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
