"""Diario delle previsioni: solo aggiunte, con catena di hash. Verifica a scadenza."""
import hashlib

import pandas as pd

from .config import HORIZONS, JOURNAL, MODEL_VERSION, OUTCOMES

COLS = ["asof", "horizon", "sessions", "model", "spot", "thr1", "p1", "thr2", "p2", "base1", "ratio",
        "level", "q10", "q50", "q90", "prev_hash", "hash"]
OUT_COLS = ["asof", "horizon", "target_date", "spot0", "spot1", "realized", "realized_maxdd", "q50",
            "discrepancy", "in_range", "hit1", "hit2", "sp_realized", "sp_maxdd"]


def _h(prev: str, row: dict) -> str:
    payload = prev + "|" + "|".join(str(row.get(c, "")) for c in COLS[:-2])
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def read(path=None) -> pd.DataFrame:
    path = path or JOURNAL
    if not path.exists():
        return pd.DataFrame(columns=COLS)
    return pd.read_csv(path, dtype={"prev_hash": str, "hash": str})


def append(asof: str, spot: float, pred: dict, model: str = MODEL_VERSION, path=None) -> int:
    """Registra la previsione di oggi (una riga per orizzonte). Idempotente: non duplica. path: diario alternativo (modalita' ombra)."""
    df = read(path)
    prev = df["hash"].iloc[-1] if len(df) else "GENESIS"
    added = 0
    rows = []
    for hz, r in pred.items():
        if ((df["asof"] == asof) & (df["horizon"] == hz) & (df["model"] == model)).any():
            continue
        thrs = sorted(r["p"])
        row = {"asof": asof, "horizon": hz, "sessions": HORIZONS[hz], "model": model, "spot": round(spot, 4),
               "thr1": thrs[0], "p1": round(r["p"][thrs[0]], 5),
               "thr2": thrs[1] if len(thrs) > 1 else "", "p2": round(r["p"][thrs[1]], 5) if len(thrs) > 1 else "",
               "base1": round(r["base"][thrs[0]], 5), "ratio": round(r["ratio"], 4), "level": r["level"],
               **{q: (round(float(r["ret"][q]), 5) if r.get("ret") and r["ret"].get(q) == r["ret"].get(q) else "") for q in ("q10", "q50", "q90")}}
        row["prev_hash"] = prev
        row["hash"] = _h(prev, row)
        prev = row["hash"]
        rows.append(row)
        added += 1
    if rows:
        out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)[COLS]
        out.to_csv(path or JOURNAL, index=False)
    return added


def verify(path=None) -> tuple[bool, str]:
    """Controlla che nessuna riga del diario sia stata modificata."""
    df = read(path)
    prev = "GENESIS"
    for i, r in df.iterrows():
        row = {c: ("" if pd.isna(r[c]) else r[c]) for c in COLS}
        for c in ("thr1", "thr2"):
            if row[c] != "":
                row[c] = int(row[c])
        # riformatta come in scrittura
        row["spot"] = round(float(r["spot"]), 4)
        for c in ("p1", "p2", "base1", "q10", "q50", "q90"):
            if row[c] != "":
                row[c] = round(float(row[c]), 5)
        row["ratio"] = round(float(r["ratio"]), 4)
        if r["prev_hash"] != prev or _h(prev, row) != r["hash"]:
            return False, f"riga {i + 2} del diario non coerente"
        prev = r["hash"]
    return True, f"{len(df)} righe, catena di hash valida"


def update_outcomes(vwce: pd.Series, sp: pd.Series) -> int:
    """Per ogni previsione scaduta calcola esito reale e scostamento. Aggiunge solo righe nuove."""
    j = read()
    if j.empty:
        return 0
    done = pd.read_csv(OUTCOMES) if OUTCOMES.exists() else pd.DataFrame(columns=OUT_COLS)
    have = set(zip(done["asof"].astype(str), done["horizon"]))
    new = []
    spi = sp.index
    for _, r in j.iterrows():
        if (str(r["asof"]), r["horizon"]) in have:
            continue
        a = pd.Timestamp(r["asof"])
        if a not in spi:
            continue
        i = spi.get_loc(a)
        n = int(r["sessions"])
        if i + n >= len(spi):
            continue
        tgt = spi[i + n]
        seg_dates = spi[i: i + n + 1]
        v = vwce.reindex(seg_dates, method="ffill").dropna()
        if len(v) < 2:
            continue
        spot0, spot1 = float(v.iloc[0]), float(v.iloc[-1])
        real = spot1 / spot0 - 1
        mdd = float((v.iloc[1:] / spot0 - 1).min())
        q50 = r["q50"]
        sp_seg = sp.iloc[i: i + n + 1]
        new.append({
            "asof": r["asof"], "horizon": r["horizon"], "target_date": tgt.strftime("%Y-%m-%d"),
            "spot0": round(spot0, 4), "spot1": round(spot1, 4), "realized": round(real, 5),
            "realized_maxdd": round(min(mdd, 0.0), 5), "q50": q50,
            "discrepancy": round(real - q50, 5) if pd.notna(q50) else "",
            "in_range": int(r["q10"] <= real <= r["q90"]) if pd.notna(r["q10"]) else "",
            "hit1": int(mdd <= -float(r["thr1"]) / 100),
            "hit2": int(mdd <= -float(r["thr2"]) / 100) if str(r["thr2"]) not in ("", "nan") else "",
            "sp_realized": round(float(sp_seg.iloc[-1] / sp_seg.iloc[0] - 1), 5),
            "sp_maxdd": round(float(min((sp_seg.iloc[1:] / sp_seg.iloc[0] - 1).min(), 0.0)), 5),
        })
    if new:
        pd.concat([done, pd.DataFrame(new)], ignore_index=True)[OUT_COLS].to_csv(OUTCOMES, index=False)
    return len(new)
