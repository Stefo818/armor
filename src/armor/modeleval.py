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
                ra = pr[hz].get("ret")   # quantili del rendimento (intervallo 80% mostrato dall'app)
                if ra:
                    for q in (10, 50, 90):
                        rows.append({"date": t, "hz": hz, "kind": "q", "thr": q, "p": ra["q%d" % q]})
    return rows


def _score(p, dates, preds: dict, label: str, step: int, kinds_thr=None):
    """Metriche per bersaglio sulle date comuni a tutti i modelli disponibili per quel bersaglio."""
    out_rows, calib = [], []
    targets = sorted({(r.hz, r.kind, int(r.thr)) for df in preds.values() for r in df.drop_duplicates(["hz", "kind", "thr"]).itertuples()
                      if r.kind in ("down", "up") and r.thr in TARGETS[r.hz]},
                     key=lambda x: (x[1] != "down", list(HORIZONS).index(x[0]), x[2]))
    for hz, kind, thr in targets:
        y = outcome(p, dates, hz, kind, thr)
        base = purged_base(p, dates, hz, kind, thr)
        common = y.dropna().index
        sel = {}
        for m, df in preds.items():
            g = df[(df.hz == hz) & (df.kind == kind) & (df.thr == thr)].set_index("date")["p"].dropna()
            if len(g):
                sel[m] = g
        if not sel:
            continue
        for m in sel:
            common = common.intersection(sel[m].index)
        if len(common) < 30:
            continue
        yy, bb = y.loc[common].values, base.loc[common].values
        err_b = (bb - yy) ** 2
        yrs = common.year
        for m in ["Normale"] + list(sel):
            pp = bb if m == "Normale" else sel[m].loc[common].values
            err = (pp - yy) ** 2
            brier, brier_b = float(err.mean()), float(err_b.mean())
            bss = 1 - brier / brier_b if brier_b > 0 else float("nan")
            lo, hi = block_ci(err, err_b, step) if m != "Normale" else (float("nan"), float("nan"))
            pc = np.clip(pp, 1e-4, 1 - 1e-4)
            ll = float(-(yy * np.log(pc) + (1 - yy) * np.log(1 - pc)).mean())

            def bss_sub(mask):
                if mask.sum() < 20:
                    return float("nan")
                bb_ = ((bb[mask] - yy[mask]) ** 2).mean()
                return float(1 - ((pp[mask] - yy[mask]) ** 2).mean() / bb_) if bb_ > 0 else float("nan")
            out_rows.append({"set": label, "kind": kind, "hz": hz, "thr": thr, "model": m, "n": int(len(common)),
                             "da": str(common[0].date()), "freq": float(yy.mean()), "brier": brier,
                             "bss": bss, "bss_lo": lo, "bss_hi": hi, "logloss": ll, "auc": auc(pp, yy) if m != "Normale" else 0.5,
                             "bss_1990_2012": bss_sub(yrs < 2013), "bss_2000_12": bss_sub((yrs >= 2000) & (yrs < 2013)),
                             "bss_2013_26": bss_sub(yrs >= 2013)})
            if m != "Normale":
                try:
                    q = pd.qcut(pd.Series(pp), 10, duplicates="drop")
                    for _, x in pd.DataFrame({"p": pp, "y": yy}).groupby(q, observed=True):
                        calib.append({"set": label, "kind": kind, "hz": hz, "thr": thr, "model": m, "prev": float(x.p.mean()), "real": float(x.y.mean()), "n": int(len(x))})
                except Exception:  # noqa: BLE001
                    pass
    return out_rows, calib


def evaluate(start: str = "1990-01-01", step: int = 5, sims: int = 2000, log=print, cache: str | None = None) -> dict:
    """cache: file pickle facoltativo con le previsioni dei singoli modelli (solo per le prove locali)."""
    import os
    import pickle
    from . import ensemble, model_mv
    p = closed_sp500()
    vix = None
    try:
        from . import store
        v = store.load("vix")
        vix = v if len(v) > 1000 else None
    except Exception:  # noqa: BLE001
        pass
    dates = p.index[p.index >= start][::step]
    preds = pickle.load(open(cache, "rb")) if cache and os.path.exists(cache) else {}
    if not preds:
        log(f"[valuta] A1 su {len(dates)} date ...")
        preds["A1"] = pd.DataFrame(a1_preds(p, dates))
        log("[valuta] FHS ...")
        preds["FHS"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims))
        if vix is not None:
            log("[valuta] FHS + VIX ...")
            preds["FHS+VIX"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims, vix=vix, w=0.5))
        log("[valuta] multi-variabile (logistica) ...")
        preds["MV-logit"] = pd.DataFrame(model_mv.mv_preds(p, dates, "logit", 63))
        log("[valuta] multi-variabile (alberi) ...")
        preds["MV-GBM"] = pd.DataFrame(model_mv.mv_preds(p, dates, "gbm", 126))
        log("[valuta] multi-variabile + famiglie dell'Indice (logistica, alberi) ...")
        preds["MVF-logit"] = pd.DataFrame(model_mv.mv_preds(p, dates, "logit", 63, fam=True))
        preds["MVF-GBM"] = pd.DataFrame(model_mv.mv_preds(p, dates, "gbm", 126, fam=True))
        try:   # Titan: motore ufficiale di Armor (riferimento dal 11/2026), stesse date e stessa regola degli altri
            from . import titan_valuta
            log("[valuta] Titan ...")
            preds["Titan"] = titan_valuta.preds(dates, log=log)
        except Exception as e:  # noqa: BLE001
            log("[valuta] Titan non valutato: " + str(e)[:100])
        if cache:
            pickle.dump(preds, open(cache, "wb"))
    ftgt = lambda df: df[df.kind != "q"]
    try:   # archivio delle probabilità storiche di ogni modello, per il grafico di confronto
        from . import modelli_preds
        for nome, d_ in preds.items():
            if not nome.startswith("MVF"):
                modelli_preds.salva(nome, ftgt(d_))
    except Exception as e:  # noqa: BLE001
        log("[valuta] archivio previsioni non salvato: " + str(e)[:80])
    set1 = {m: ftgt(d) for m, d in preds.items() if not m.startswith("MVF")}
    rows1, cal1 = _score(p, dates, set1, "modelli", step)
    setF = {m: ftgt(d) for m, d in preds.items() if m in ("A1", "FHS", "MV-logit", "MV-GBM") or m.startswith("MVF")}
    rowsF, calF = _score(p, dates, setF, "famiglie", step)
    log("[valuta] combinazione, taratura e ritorno al normale ...")
    base_fn = lambda hz, k, t: purged_base(p, dates, hz, k, t)
    out_fn = lambda hz, k, t: outcome(p, dates, hz, k, t)
    comb, state = ensemble.combine(p, dates, set1, base_fn, out_fn, step=step)
    combB, _ = ensemble.combine(p, dates, set1, base_fn, out_fn, step=step, isotonic=False)   # variante B: scelta a posteriori, solo informativa
    cols = ["date", "hz", "kind", "thr", "p"]
    set2 = {"A1": set1["A1"], "FHS": set1["FHS"], "Combinato": comb[cols], "Combinato-B": combB[cols]}
    rows2, cal2 = _score(p, dates, set2, "finale", step)
    adopt = ensemble.adoption(pd.DataFrame(rows2))
    adoptB = ensemble.adoption(pd.DataFrame(rows2), model="Combinato-B")
    log(f"[valuta] regola di adozione: {'SUPERATA' if adopt['adopt'] else 'non superata'}")
    cov = {}
    for nome in ("A1", "FHS"):
        q = preds[nome][preds[nome].kind == "q"]
        for hz in HORIZONS:
            try:
                cov.setdefault(hz, {})[nome] = ensemble.coverage(ensemble.interval_scale(q, p, dates, hz))
            except Exception as e:  # noqa: BLE001
                log("[valuta] intervalli " + hz + ": " + str(e)[:60])
    imp = []
    try:
        from . import spiega
        eng = model_mv.MVEngine(p, "gbm")
        imp = spiega.perm_importance(eng, eng.fit(eng.p.index[-1]), "3m")
    except Exception as e:  # noqa: BLE001
        log("[valuta] importanza: " + str(e)[:60])
    wsum = comb.groupby(["hz", "kind", "thr"]).tail(1)[["hz", "kind", "thr", "w", "bss5"]].to_dict("records") if len(comb) else []
    res = {"date": pd.Timestamp.now().strftime("%Y-%m-%d"), "start": start, "step": step, "sims": sims, "metrics": rows1 + rowsF + rows2,
           "calibration": cal1 + calF + cal2, "adozione": adopt, "adozione_B": adoptB, "intervalli": cov, "ensemble": state, "abilita_ultima": wsum, "importanza_gbm_3m": imp,
           "note": "Stessa regola per tutti i modelli; frequenza normale con soli esiti gia' maturati; A1 non modella i rialzi."}
    try:
        ensemble.registra_tentativo(res, DATA / "models.json")
    except Exception as e:  # noqa: BLE001
        log("[valuta] registro tentativi non riuscito: " + str(e)[:80])
    try:
        EVAL_JSON.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
        f = ftgt(preds["FHS"])
        f = f[f.thr.isin([PRIMARY[h] for h in HORIZONS]) | f.thr.isin([5, 10])]
        f.assign(date=f["date"].dt.strftime("%Y-%m-%d")).to_csv(FHS_CSV, index=False, float_format="%.4f")
        from . import modelli_finestre   # vincitori per settimana/mese/trimestre/semestre (pagina Modelli)
        modelli_finestre.salva(modelli_finestre.calcola(p, preds))
    except Exception as e:  # noqa: BLE001
        log("[valuta] salvataggio non riuscito: " + str(e)[:80])
    return res


def table(res: dict) -> str:
    """Tabella di testo per il log: una riga per bersaglio e modello (Brier / BSS / AUC), un blocco per insieme di date."""
    df = pd.DataFrame(res["metrics"])
    if "set" not in df:
        df["set"] = "modelli"
    lines = []
    for lab, gs in df.groupby("set", sort=False):
        lines.append(f"== {lab} ==")
        lines.append(f"{'bersaglio':<16}{'modello':<10}{'n':>5}{'freq':>7}{'Brier':>9}{'BSS':>8}{'[90%]':>16}{'AUC':>7}{'BSS00-12':>10}{'BSS13-26':>10}")
        for (kind, hz, thr), g in gs.groupby(["kind", "hz", "thr"], sort=False):
            for _, r in g.iterrows():
                ci = "" if np.isnan(r.bss_lo) else f"[{r.bss_lo:+.2f},{r.bss_hi:+.2f}]"
                b2 = r.get("bss_2000_12", float("nan"))
                lines.append(f"{('calo' if kind == 'down' else 'rialzo') + ' ' + hz + ' ' + str(thr) + '%':<16}{r.model:<10}{int(r.n):>5}{r.freq:>7.3f}{r.brier:>9.4f}{r.bss:>+8.3f}{ci:>16}{r.auc:>7.3f}{b2:>+10.3f}{r.bss_2013_26:>+10.3f}")
    return "\n".join(lines)
