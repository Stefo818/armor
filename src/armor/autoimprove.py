"""Miglioramento automatico del modello, con regole fissate in anticipo.

Ogni mese: (1) si provano tutte le variabili candidate contro il modello in uso (sfide);
(2) se una variabile migliora il modello in modo netto e stabile, diventa parte del nuovo modello (versione A2, A3...);
(3) si misura quanto il modello in uso e' migliore della versione iniziale A1 e del mese scorso (indice mensile).
Tutto e' registrato in data/models.json e data/improvement.csv: nessun cambiamento avviene senza lasciare traccia."""
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import challenger
from .config import DATA, MODEL_VERSION, PRIMARY
from .features import closed_sp500
from .model import Engine

MODELS = DATA / "models.json"
IMPROVEMENT = DATA / "improvement.csv"
MIN_PASSING_TARGETS = 2     # una variabile deve superare la regola su almeno 2 orizzonti
MIN_DAYS_BETWEEN = 90       # al massimo un cambio di modello ogni 90 giorni
SCORE_FROM = pd.Timestamp("2013-01-01")


def registry() -> dict:
    try:
        return json.loads(MODELS.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"champion": MODEL_VERSION,
                "versions": [{"id": MODEL_VERSION, "extra": [], "date": "2026-11-07",
                              "note": "Versione iniziale: otto variabili sui prezzi dell'S&P 500."}]}


def save_registry(reg: dict) -> None:
    MODELS.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")


def champion_info(reg: dict | None = None) -> dict:
    reg = reg or registry()
    return next(v for v in reg["versions"] if v["id"] == reg["champion"])


def _extra_frame(names: list[str], idx) -> pd.DataFrame | None:
    if not names:
        return None
    cands = challenger.candidates(idx)
    return pd.concat([cands[n] for n in names], axis=1)


def champion_engine(p: pd.Series):
    """Motore del modello in uso. Se le variabili extra non sono aggiornate, ripiega su A1 (e lo dice)."""
    info = champion_info()
    algo = info.get("algo", "logit")
    if not info["extra"]:
        return Engine(p, algo=algo), info["id"]
    try:
        ex = _extra_frame(info["extra"], p.index)
        eng = challenger.E2(p, ex, ex.dropna().index, algo=algo)
        if eng.F.index[-1] != p.dropna().index[-1] and Engine(p).F.index[-1] == p.dropna().index[-1]:
            raise ValueError("variabili extra non aggiornate")
        return eng, info["id"]
    except Exception as e:  # noqa: BLE001
        print("Modello", info["id"], "non utilizzabile oggi, uso A1:", str(e)[:100])
        return Engine(p), MODEL_VERSION


def _rule(d: pd.DataFrame, hz: str) -> tuple[bool, float, float]:
    g = d[(d.hz == hz) & (d.thr == PRIMARY[hz])]
    me, ml = challenger._metrics(g[g.t.dt.year < 2013]), challenger._metrics(g[g.t.dt.year >= 2013])
    if np.isnan(me[0]) or np.isnan(ml[0]):
        return False, np.nan, np.nan
    dbe, dbl = me[1] - me[0], ml[1] - ml[0]
    ok = dbe > 0.01 and dbl > 0.01 and me[3] - me[2] > 0 and ml[3] - ml[2] > 0
    return bool(ok), dbe, dbl


def consider_promotion(ch: pd.DataFrame, p: pd.Series, reg: dict) -> str | None:
    cur = champion_info(reg)
    last = pd.Timestamp(cur["date"])
    if cur["id"] != MODEL_VERSION and (pd.Timestamp.now() - last).days < MIN_DAYS_BETWEEN:
        return None
    c = ch[(ch.get("principale", 0) == 1) & (ch["esito"] == "CANDIDATA")]
    counts = c.groupby("variabile").size()
    algo_n = int(counts.get(challenger.ALGO_NAME, 0))
    best = [v for v, n in counts.sort_values(ascending=False).items()
            if n >= MIN_PASSING_TARGETS and v not in cur["extra"] and v != challenger.ALGO_NAME]
    if not best and algo_n >= MIN_PASSING_TARGETS and cur.get("algo", "logit") == "logit":
        ex = _extra_frame(cur["extra"], p.index)
        ok_idx = ex.dropna().index if ex is not None else None
        A, B = challenger.E2(p, ex, ok_idx), challenger.E2(p, ex, ok_idx, algo="gbm")
        start = max(pd.Timestamp("2000-01-01"), p.index[0] + pd.DateOffset(years=25))
        d = challenger._evaluate(A, B, p.index, start, step=21, refit=252)
        passed = [hz for hz in ("10g", "1m", "3m", "6m") if _rule(d, hz)[0]]
        if len(passed) < MIN_PASSING_TARGETS:
            return None
        new_id = f"A{len(reg['versions']) + 1}"
        reg["versions"].append({"id": new_id, "extra": list(cur["extra"]), "algo": "gbm", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                "note": f"Nuovo tipo di modello (gradient boosting): migliora su {', '.join(passed)} sia nel 2000-12 sia dal 2013."})
        reg["champion"] = new_id
        save_registry(reg)
        return new_id
    if not best:
        return None
    name = best[0]
    names = cur["extra"] + [name]
    ex = _extra_frame(names, p.index)
    ok_idx = ex.dropna().index
    A = challenger.E2(p, _extra_frame(cur["extra"], p.index), ok_idx, algo=cur.get("algo", "logit"))
    B = challenger.E2(p, ex, ok_idx, algo=cur.get("algo", "logit"))
    start = max(pd.Timestamp("2000-01-01"), ok_idx[0] + pd.DateOffset(years=12))
    d = challenger._evaluate(A, B, p.index, start)
    passed = [hz for hz in ("10g", "1m", "3m", "6m") if _rule(d, hz)[0]]
    if len(passed) < MIN_PASSING_TARGETS:
        return None
    new_id = f"A{len(reg['versions']) + 1}"
    reg["versions"].append({"id": new_id, "extra": names, "algo": cur.get("algo", "logit"), "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            "note": f"Aggiunta la variabile «{name}»: migliora il modello su {', '.join(passed)} sia nel 2000-12 sia dal 2013."})
    reg["champion"] = new_id
    save_registry(reg)
    return new_id


def score(p: pd.Series) -> dict:
    """Indice Armor = media dell'indice di Brier (BSS) dei 4 orizzonti principali dal 2013, x100. Piu' alto = meglio."""
    info = champion_info()
    ex = _extra_frame(info["extra"], p.index)
    ok_idx = ex.dropna().index if ex is not None else None
    A = challenger.E2(p, None, ok_idx)
    algo = info.get("algo", "logit")
    B = challenger.E2(p, ex, ok_idx, algo=algo) if (ex is not None or algo != "logit") else A
    d = challenger._evaluate(A, B, p.index, SCORE_FROM, step=10)
    a, b, per = [], [], {}
    for hz in ("10g", "1m", "3m", "6m"):
        g = d[(d.hz == hz) & (d.thr == PRIMARY[hz])]
        m = challenger._metrics(g)
        if not np.isnan(m[0]):
            a.append(m[0]); b.append(m[1]); per[hz] = round(m[1] * 100, 2)
    return {"score_champion": round(float(np.mean(b)) * 100, 2), "score_a1": round(float(np.mean(a)) * 100, 2), "per_hz": per}


def run() -> pd.DataFrame:
    p = closed_sp500()
    ch = challenger.run()
    reg = registry()
    promoted = consider_promotion(ch, p, reg)
    save_registry(reg)
    s = score(p)
    old = pd.read_csv(IMPROVEMENT) if IMPROVEMENT.exists() else pd.DataFrame(columns=["month", "model", "score", "score_a1", "vs_a1", "vs_prev", "promoted", "tested", "per_hz"])
    month = pd.Timestamp.now().strftime("%Y-%m")
    prev = old[old.month != month].iloc[-1] if len(old[old.month != month]) else None
    row = {"month": month, "model": reg["champion"], "score": s["score_champion"], "score_a1": s["score_a1"],
           "vs_a1": round(s["score_champion"] - s["score_a1"], 2),
           "vs_prev": round(s["score_champion"] - float(prev["score"]), 2) if prev is not None else np.nan,
           "promoted": promoted or "", "tested": int(ch["variabile"].nunique()),
           "per_hz": json.dumps(s["per_hz"])}
    out = pd.concat([old[old.month != month], pd.DataFrame([row])], ignore_index=True)
    out.to_csv(IMPROVEMENT, index=False)
    print(f"Modello in uso: {reg['champion']}  indice Armor: {row['score']}  vs A1: {row['vs_a1']}  vs mese scorso: {row['vs_prev']}"
          + (f"  NUOVO MODELLO {promoted}" if promoted else ""))
    return out
