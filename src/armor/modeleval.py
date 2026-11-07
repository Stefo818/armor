"""Valutazione dei modelli con la stessa regola per tutti (comando: python -m armor valuta-modelli).

- walk-forward con date di prova ogni `step` sedute dal 1990;
- A1 (logistica): usa solo esiti già maturati alla data (purge incorporato: righe di addestramento <= data - orizzonte);
- FHS: parametri rifatti ogni anno con dati fino a 5 sedute prima (embargo); nessun esito futuro entra mai;
- frequenza «normale» (base): media degli esiti già maturati alla data (purged), uguale per tutti i modelli;
- metriche: Brier, BSS contro il normale, log loss, AUC, taratura a 10 gruppi; intervalli al 90% con bootstrap a blocchi (63 sedute).
Per i rialzi il modello A1 non esiste (calcola solo i cali): per i rialzi si confrontano FHS e normale."""
import json

import numpy as np
import pandas as pd

from . import fhs
from .config import DATA, HORIZONS, PRIMARY, TARGETS
from .features import closed_sp500, fwd_maxdd, fwd_maxup
from .model import Engine

EVAL_JSON = DATA / "model_eval.json"
FHS_CSV = DATA / "fhs_eval.csv"
BLOCK = 63


def auc(score, y) -> float:
    score, y = np.asarray(score, float), np.asarray(y, float)
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    if n1 < 10 or n0 < 10:
        return float("nan")
    r = pd.Series(score).rank().values
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def block_ci(err_m: np.ndarray, err_b: np.ndarray, step: int, reps: int = 400, seed: int = 1) -> tuple[float, float]:
    """Intervallo al 90% del BSS con bootstrap a blocchi (blocchi di ~63 sedute)."""
    n = len(err_m)
    if n < 30:
        return (float("nan"), float("nan"))
    L = max(int(np.ceil(BLOCK / step)), 1)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / L))
    vals = []
    for _ in range(reps):
        starts = rng.integers(0, max(n - L, 1), nb)
        ix = np.concatenate([np.arange(s, min(s + L, n)) for s in starts])[:n]
        vals.append(1 - err_m[ix].sum() / max(err_b[ix].sum(), 1e-12))
    return float(np.quantile(vals, .05)), float(np.quantile(vals, .95))


def purged_base(p: pd.Series, dates, hz: str, kind: str, thr: int) -> pd.Series:
    """Frequenza storica dell'evento nota alla data t: media degli esiti delle date <= t - orizzonte (nessun esito futuro)."""
    n = HORIZONS[hz]
    y = ((fwd_maxdd(p, n) <= -thr / 100) if kind == "down" else (fwd_maxup(p, n) >= thr / 100)).astype(float)
    y = y.where(fwd_maxdd(p, n).notna())
    cs = y.fillna(0).cumsum()
    cn = y.notna().astype(int).cumsum()
    pos = p.index.get_indexer(dates)
    j = np.maximum(pos - n, 0)
    return pd.Series(cs.values[j] / np.maximum(cn.values[j], 1), index=dates)


def outcome(p: pd.Series, dates, hz: str, kind: str, thr: int) -> pd.Series:
    n = HORIZONS[hz]
    if kind == "down":
        e = fwd_maxdd(p, n)
        y = (e <= -thr / 100).astype(float)
    else:
        e = fwd_maxup(p, n)
        y = (e >= thr / 100).astype(float)
    return y.where(e.notna()).reindex(dates)


def a1_preds(p: pd.Series, dates, refit_every: int = 63) -> list[dict]:
    eng = Engine(p)
    rows, fitted, last = [], None, -10 ** 9
    for t in dates:
        if t not in eng.F.index:
            continue
        i = p.index.get_loc(t)
        if fitted is None or i - last >= refit_every:
            fitted = eng.fit(t)
            last = i
        pr = eng.predict(fitted, t)
        for hz in HORIZONS:
            if hz in pr:
                for thr in TARGETS[hz]:
                    rows.append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": pr[hz]["p"][thr]})
    return rows


def evaluate(start: str = "1990-01-01", step: int = 5, sims: int = 2000, log=print) -> dict:
    p = closed_sp500()
    vix = None
    try:
        from . import store
        v = store.load("vix")
        vix = v if len(v) > 1000 else None
    except Exception:  # noqa: BLE001
        pass
    dates = p.index[p.index >= start][::step]
    preds = {}
    log(f"[valuta] A1 su {len(dates)} date ...")
    preds["A1"] = pd.DataFrame(a1_preds(p, dates))
    log("[valuta] FHS ...")
    preds["FHS"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims))
    if vix is not None:
        log("[valuta] FHS + VIX ...")
        preds["FHS+VIX"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims, vix=vix, w=0.5))
    # il rendimento del primo anno dopo l'inizio non ha storia sufficiente: si valuta dove tutti i modelli hanno previsioni
    out_rows, calib = [], []
    targets = sorted({(r.hz, r.kind, int(r.thr)) for r in preds["FHS"].itertuples() if (r.kind == "down" and r.thr in TARGETS[r.hz]) or (r.kind == "up" and r.thr in TARGETS[r.hz])},
                     key=lambda x: (x[1] != "down", list(HORIZONS).index(x[0]), x[2]))
    for hz, kind, thr in targets:
        y = outcome(p, dates, hz, kind, thr)
        base = purged_base(p, dates, hz, kind, thr)
        common = y.dropna().index
        sel = {}
        for m, df in preds.items():
            g = df[(df.hz == hz) & (df.kind == kind) & (df.thr == thr)].set_index("date")["p"]
            if len(g):
                sel[m] = g
        if not sel:
            continue
        for m in sel:
            common = common.intersection(sel[m].index)
        common = common[(common >= pd.Timestamp(start) + pd.DateOffset(years=5))] if False else common
        yy, bb = y.loc[common].values, base.loc[common].values
        err_b = (bb - yy) ** 2
        for m in ["Normale"] + list(sel):
            pp = bb if m == "Normale" else sel[m].loc[common].values
            err = (pp - yy) ** 2
            brier, brier_b = float(err.mean()), float(err_b.mean())
            bss = 1 - brier / brier_b if brier_b > 0 else float("nan")
            lo, hi = block_ci(err, err_b, step) if m != "Normale" else (float("nan"), float("nan"))
            pc = np.clip(pp, 1e-4, 1 - 1e-4)
            ll = float(-(yy * np.log(pc) + (1 - yy) * np.log(1 - pc)).mean())
            yrs = common.year
            def bss_sub(mask):
                if mask.sum() < 20:
                    return float("nan")
                bb_ = ((bb[mask] - yy[mask]) ** 2).mean()
                return float(1 - ((pp[mask] - yy[mask]) ** 2).mean() / bb_) if bb_ > 0 else float("nan")
            out_rows.append({"kind": kind, "hz": hz, "thr": thr, "model": m, "n": int(len(common)), "freq": float(yy.mean()), "brier": brier,
                             "bss": bss, "bss_lo": lo, "bss_hi": hi, "logloss": ll, "auc": auc(pp, yy) if m != "Normale" else 0.5,
                             "bss_1990_2012": bss_sub(yrs < 2013), "bss_2013_26": bss_sub(yrs >= 2013)})
            if m != "Normale":
                try:
                    q = pd.qcut(pd.Series(pp), 10, duplicates="drop")
                    for b, x in pd.DataFrame({"p": pp, "y": yy}).groupby(q, observed=True):
                        calib.append({"kind": kind, "hz": hz, "thr": thr, "model": m, "prev": float(x.p.mean()), "real": float(x.y.mean()), "n": int(len(x))})
                except Exception:  # noqa: BLE001
                    pass
    res = {"date": pd.Timestamp.now().strftime("%Y-%m-%d"), "start": start, "step": step, "sims": sims, "metrics": out_rows, "calibration": calib,
           "note": "Stessa regola per tutti i modelli; frequenza normale con soli esiti già maturati; A1 non modella i rialzi."}
    try:
        EVAL_JSON.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        f = preds["FHS"]
        f = f[f.thr.isin([PRIMARY[h] for h in HORIZONS]) | f.thr.isin([5, 10])]
        f.assign(date=f["date"].dt.strftime("%Y-%m-%d")).to_csv(FHS_CSV, index=False, float_format="%.4f")
    except Exception as e:  # noqa: BLE001
        log("[valuta] salvataggio non riuscito: " + str(e)[:80])
    return res


def table(res: dict) -> str:
    """Tabella di testo per il log: una riga per bersaglio, colonne per modello (Brier / BSS / AUC)."""
    df = pd.DataFrame(res["metrics"])
    lines = [f"{'bersaglio':<16}{'modello':<10}{'n':>5}{'freq':>7}{'Brier':>9}{'BSS':>8}{'[90%]':>16}{'AUC':>7}{'BSS90-12':>10}{'BSS13-26':>10}"]
    for (kind, hz, thr), g in df.groupby(["kind", "hz", "thr"], sort=False):
        for _, r in g.iterrows():
            ci = "" if np.isnan(r.bss_lo) else f"[{r.bss_lo:+.2f},{r.bss_hi:+.2f}]"
            lines.append(f"{('calo' if kind == 'down' else 'rialzo') + ' ' + hz + ' ' + str(thr) + '%':<16}{r.model:<10}{int(r.n):>5}{r.freq:>7.3f}{r.brier:>9.4f}{r.bss:>+8.3f}{ci:>16}{r.auc:>7.3f}{r.bss_1990_2012:>+10.3f}{r.bss_2013_26:>+10.3f}")
    return "\n".join(lines)
