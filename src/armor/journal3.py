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


def verifica_estrema(path=None) -> tuple[bool, int, str | None]:
    """Rilegge il file riga per riga (senza pandas) e ricostruisce la catena da GENESIS.
    Integro: (True, numero di righe, None). Rotto: (False, numero di riga nel file con l'intestazione come riga 1, 'prev_hash non corrisponde' | 'hash non corrisponde')."""
    import csv
    path = path or FILE
    if not path.exists():
        return True, 0, None
    prev, n = "GENESIS", 0
    with open(path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            if row.get("prev_hash") != prev:
                return False, i, "prev_hash non corrisponde"
            if _h(prev, row) != row.get("hash"):
                return False, i, "hash non corrisponde"
            prev = row["hash"]
            n += 1
    return True, n, None


def verifica(path=None) -> tuple[bool, int, str | None]:
    """(ok, numero di righe, errore). Come verifica_estrema; in caso di errore il testo include il numero di riga."""
    ok, n, err = verifica_estrema(path)
    return (True, n, None) if ok else (False, n, f"riga {n}: {err}")


def ripara(path=None, scarti=None, log=print) -> tuple[int, int]:
    """Ripara il caso tipico di catena rotta: due esecuzioni hanno scritto la stessa riga (stessa data, tipo, modello, variante, orizzonte), per esempio
    un giro locale con diario non aggiornato e un giro di GitHub. Si tocca solo la parte dopo la prima rottura: le righe doppie vanno in
    data/journal_v3_scartate.csv (con la nota del motivo), le altre si ricollegano alla catena. Le righe prima della rottura non cambiano mai.
    Se la rottura ha un'altra causa (riga modificata a mano) non si tocca nulla. Restituisce (righe scartate, righe ricollegate)."""
    import csv
    path = path or FILE
    if not path.exists():
        return 0, 0
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    prev, b = "GENESIS", None
    for i, r in enumerate(rows):
        if r.get("prev_hash") != prev:
            b = i
            break
        if _h(prev, r) != r.get("hash"):
            return 0, 0   # riga modificata: non è un doppione, non si ripara
        prev = r["hash"]
    if b is None:
        return 0, 0
    visti = {(r["asof"], r["kind"], r["model"], r["variante"], r["horizon"]) for r in rows[:b]}
    tieni, scarta = [], []
    for r in rows[b:]:
        k = (r["asof"], r["kind"], r["model"], r["variante"], r["horizon"])
        if k in visti:
            scarta.append(r)
        else:
            visti.add(k)
            tieni.append(r)
    if not scarta:
        return 0, 0
    out = []
    for r in tieni:
        r = {c: r.get(c, "") for c in COLS}
        r["prev_hash"] = prev
        r["hash"] = _h(prev, r)
        prev = r["hash"]
        out.append(r)
    scarti = scarti or (path.parent / "journal_v3_scartate.csv")
    nuovo = not scarti.exists()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(scarti, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS + ["scartata_il", "motivo"])
        if nuovo:
            w.writeheader()
        for r in scarta:
            w.writerow({**{c: r.get(c, "") for c in COLS}, "scartata_il": now, "motivo": "riga doppia scritta da un'altra esecuzione (diario non aggiornato)"})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        for r in rows[:b] + out:
            w.writerow({c: r.get(c, "") for c in COLS})
    log(f"[diario] riparato: {len(scarta)} righe doppie spostate in {scarti.name}, {len(out)} righe ricollegate")
    return len(scarta), len(out)


def backup_settimanale(oggi=None, base=None, mantieni: int = 12) -> str | None:
    """Una copia del diario per settimana ISO in data/journal_backups/journal_v3_AAAA-SS.csv (se non c'è già), tiene le ultime `mantieni`, aggiorna indice.json.
    Restituisce il nome del file creato, None se la settimana era già coperta o il diario non esiste."""
    import shutil
    from datetime import date
    base = base or DATA
    src = base / "journal_v3.csv"
    if not src.exists():
        return None
    oggi = oggi or date.today()
    iso = oggi.isocalendar()
    cart = base / "journal_backups"
    cart.mkdir(parents=True, exist_ok=True)
    nome = f"journal_v3_{iso[0]}-{iso[1]:02d}.csv"
    creato = None
    if not (cart / nome).exists():
        shutil.copyfile(src, cart / nome)
        creato = nome
    files = sorted(cart.glob("journal_v3_*.csv"))
    for vecchio in files[:-mantieni]:
        vecchio.unlink()
    files = files[-mantieni:]
    indice = []
    for f in files:
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        indice.append({"file": f.name, "n_righe": int(len(df)), "hash_ultima_riga": df["hash"].iloc[-1] if len(df) else ""})
    (cart / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    return creato
