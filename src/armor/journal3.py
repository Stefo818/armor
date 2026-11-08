"""Diario v3 (PIANO ARMOR 3, Fase 7): data/journal_v3.csv, solo aggiunte, con catena di hash. Il diario attuale (journal.csv) resta intatto.
Una riga per data e modello (kind='previsione') con versione del codice, parametri, ingressi (valori delle variabili e data dell'ultimo dato di ogni serie),
tutte le probabilità e i quantili con l'errore Monte Carlo; gli esiti (kind='esito') si aggiungono in righe separate solo quando maturano."""
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import DATA

FILE = DATA / "journal_v3.csv"
COLS = ["ts_utc", "asof", "kind", "model", "variante", "horizon", "codice", "parametri", "ingressi", "risultati", "prev_hash", "hash"]


def _h(prev: str, row: dict) -> str:
    return hashlib.sha256((prev + "|" + "|".join(str(row.get(c, "")) for c in COLS[:-2])).encode()).hexdigest()[:20]


def read(path=None) -> pd.DataFrame:
    path = path or FILE
    if not path.exists():
        return pd.DataFrame(columns=COLS)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _js(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o), separators=(",", ":"))


def _append(rows: list[dict], path=None) -> int:
    path = path or FILE
    df = read(path)
    prev = df["hash"].iloc[-1] if len(df) else "GENESIS"
    out = []
    for r in rows:
        r = {c: r.get(c, "") for c in COLS}
        r["prev_hash"] = prev
        r["hash"] = _h(prev, r)
        prev = r["hash"]
        out.append(r)
    if out:
        pd.concat([df, pd.DataFrame(out)], ignore_index=True)[COLS].to_csv(path, index=False)
    return len(out)


def ultimi_dati() -> dict:
    """Data dell'ultimo dato di ogni serie chiave (per sapere con quali dati è stata fatta la previsione)."""
    from . import store
    from .salute import KEY_SERIES
    d = {}
    for key, _name, _lag in KEY_SERIES:
        try:
            s = store.load(key).dropna()
            d[key] = str(s.index[-1].date()) if len(s) else ""
        except Exception:  # noqa: BLE001
            d[key] = ""
    return d


def append_previsione(asof: str, model: str, variante: str, parametri: dict, ingressi: dict, risultati: dict, path=None, ts: str | None = None) -> int:
    """Una riga per (data, modello, variante). Idempotente."""
    df = read(path)
    if len(df) and ((df["asof"] == asof) & (df["kind"] == "previsione") & (df["model"] == model) & (df["variante"] == variante)).any():
        return 0
    row = {"ts_utc": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "asof": asof, "kind": "previsione", "model": model, "variante": variante,
           "horizon": "tutti", "codice": os.environ.get("GITHUB_SHA", "locale")[:12], "parametri": _js(parametri), "ingressi": _js(ingressi), "risultati": _js(risultati)}
    return _append([row], path)


def update_outcomes(p: pd.Series, path=None, ts: str | None = None) -> int:
    """Aggiunge le righe di esito per gli orizzonti scaduti (rendimento finale, minimo e massimo drawdown realizzati, con le soglie colpite)."""
    from .percorsi import ORIZZONTI
    df = read(path)
    if df.empty:
        return 0
    ee = df[df["kind"] == "esito"]
    fatti = set(zip(ee["asof"], ee["model"], ee["variante"], ee["horizon"]))
    now = ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for r in df[df["kind"] == "previsione"].itertuples():
        a = pd.Timestamp(r.asof)
        if a not in p.index:
            continue
        i = p.index.get_loc(a)
        for hz, n in ORIZZONTI.items():
            if (r.asof, r.model, r.variante, hz) in fatti or i + n >= len(p):
                continue
            w = p.values[i:i + n + 1]
            ret = float(w[-1] / w[0] - 1)
            mn = float(w[1:].min() / w[0] - 1)
            mdd = float((w / np.maximum.accumulate(w) - 1).min())
            rows.append({"ts_utc": now, "asof": r.asof, "kind": "esito", "model": r.model, "variante": r.variante, "horizon": hz, "codice": "",
                         "parametri": "", "ingressi": "", "risultati": _js({"scadenza": str(p.index[i + n].date()), "rendimento": ret, "minimo": mn, "mdd": mdd})})
    return _append(rows, path)


def verify(path=None) -> tuple[bool, str]:
    df = read(path)
    prev = "GENESIS"
    for i, r in df.iterrows():
        row = r.to_dict()
        if row["prev_hash"] != prev or _h(prev, row) != row["hash"]:
            return False, f"diario v3: riga {i + 2} modificata o catena spezzata"
        prev = row["hash"]
    return True, f"diario v3 integro ({len(df)} righe)"
