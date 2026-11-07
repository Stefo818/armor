"""Combinazione dei motori, taratura e ritorno al normale (compito 1.4) + intervalli conformali (1.5).

Tutto e' walk-forward: a ogni data i pesi, la taratura e l'abilita' usano SOLO previsioni ed esiti gia' maturati.
Regole fissate prima di guardare i risultati:
1. pesi non negativi (somma 1) per orizzonte che minimizzano il log loss fuori campione, rifatti ogni ~anno;
2. taratura isotonica per bersaglio sulle previsioni combinate fuori campione (almeno 150 date mature, altrimenti nessuna);
3. ritorno al normale: p = base + w (p_tarata - base), w = clip(BSS_ultimi_5_anni / 0,10, 0, 1); senza abilita' misurata w = 0;
4. coerenza: per ogni orizzonte la probabilita' non cresce al crescere della soglia.
Per i rialzi l'unico motore e' FHS (gli altri modellano solo i cali).
Regola di adozione: vedi adoption()."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression

from .config import HORIZONS, PRIMARY, TARGETS
from .features import fwd_ret

SKILL_SCALE = 0.10
SKILL_YEARS = 5
MIN_ISO = 150      # date mature minime per la taratura isotonica
MIN_W = 100        # date mature minime per stimare i pesi
MIN_SKILL = 40     # date mature minime per misurare l'abilita'
DOWN_MODELS = ["A1", "FHS", "MV-logit", "MV-GBM"]
UP_MODELS = ["FHS"]


def _ll(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def fit_weights(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pesi >= 0, somma 1, che minimizzano il log loss. P: (n, modelli)."""
    k = P.shape[1]
    if k == 1:
        return np.ones(1)
    r = minimize(lambda w: _ll(y, P @ w), np.ones(k) / k, method="SLSQP", bounds=[(0, 1)] * k,
                 constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"maxiter": 100})
    w = np.clip(r.x if r.success else np.ones(k) / k, 0, None)
    return w / w.sum()


def monotonize(vals: dict[int, float]) -> dict[int, float]:
    """p non cresce al crescere della soglia."""
    out, m = {}, 1.0
    for t in sorted(vals):
        m = min(m, vals[t])
        out[t] = m
    return out


def combine(p: pd.Series, dates, preds: dict, base_fn, outcome_fn, step: int = 5, refit_every: int = 50, isotonic: bool = True):
    """preds: {modello: DataFrame(date,hz,kind,thr,p)}. base_fn(hz,kind,thr)->Series 'normale' purged; outcome_fn(hz,kind,thr)->Series 0/1/NaN.
    Restituisce (DataFrame finale con colonne date,hz,kind,thr,p,raw,cal,w ; dict stato finale per l'uso dal vivo)."""
    dates = pd.DatetimeIndex(dates)
    pos = p.index.get_indexer(dates)
    tgt = [(hz, k, t) for hz in HORIZONS for k in ("down", "up") for t in TARGETS[hz]]
    A = {}   # per bersaglio: matrice previsioni dei modelli (date x modelli), y, base
    for hz, k, t in tgt:
        ms = DOWN_MODELS if k == "down" else UP_MODELS
        cols = {}
        for m in ms:
            if m in preds:
                df = preds[m]
                g = df[(df.hz == hz) & (df.kind == k) & (df.thr == t)].set_index("date")["p"]
                cols[m] = g.reindex(dates)
        A[(hz, k, t)] = {"P": pd.DataFrame(cols, index=dates), "y": outcome_fn(hz, k, t).reindex(dates).values,
                         "b": base_fn(hz, k, t).reindex(dates).values}
    W, ISO = {}, {}                        # per (hz, kind) pesi; per bersaglio isotonica
    cal = {key: np.full(len(dates), np.nan) for key in A}
    out = []
    state = {}
    for i, t in enumerate(dates):
        if i % refit_every == 0 or len(W) < 8:
            for hz in HORIZONS:
                n = HORIZONS[hz]
                for k in ("down", "up"):
                    ms = [m for m in (DOWN_MODELS if k == "down" else UP_MODELS) if m in preds]
                    Ps, ys = [], []
                    for tt in TARGETS[hz]:
                        d = A[(hz, k, tt)]
                        mat = (pos <= pos[i] - n) & ~np.isnan(d["y"])
                        mat &= d["P"][ms].notna().all(axis=1).values
                        if mat.any():
                            Ps.append(d["P"][ms].values[mat]); ys.append(d["y"][mat])
                    if Ps and sum(len(a) for a in ys) >= MIN_W:
                        W[(hz, k)] = (ms, fit_weights(np.vstack(Ps), np.concatenate(ys)))
        for hz, k, tt in tgt:
            d, n = A[(hz, k, tt)], HORIZONS[hz]
            if (hz, k) not in W:
                continue
            ms, w = W[(hz, k)]
            row = d["P"].iloc[i]
            if row[ms].isna().any():
                continue
            raw = float(np.dot(w, row[ms].values))
            if i % refit_every == 0 or (hz, k, tt) not in ISO:
                mat = (pos <= pos[i] - n) & ~np.isnan(d["y"]) & d["P"][ms].notna().all(axis=1).values
                if isotonic and mat.sum() >= MIN_ISO:
                    rr = d["P"][ms].values[mat] @ w
                    ISO[(hz, k, tt)] = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(rr, d["y"][mat])
            c = float(ISO[(hz, k, tt)].predict([raw])[0]) if (hz, k, tt) in ISO else raw
            cal[(hz, k, tt)][i] = c
            lo = pos[i] - SKILL_YEARS * 252
            m2 = (pos <= pos[i] - n) & (pos >= lo) & ~np.isnan(d["y"]) & ~np.isnan(cal[(hz, k, tt)])
            b = d["b"][i]
            if m2.sum() >= MIN_SKILL:
                num = ((cal[(hz, k, tt)][m2] - d["y"][m2]) ** 2).sum()
                den = ((d["b"][m2] - d["y"][m2]) ** 2).sum()
                bss = 1 - num / den if den > 0 else 0.0
                wt = float(np.clip(bss / SKILL_SCALE, 0, 1))
            else:
                bss, wt = float("nan"), 0.0
            out.append({"date": t, "hz": hz, "kind": k, "thr": tt, "raw": raw, "cal": c, "w": wt, "bss5": bss,
                        "p": b + wt * (c - b)})
    df = pd.DataFrame(out)
    if len(df):   # coerenza tra soglie
        df = df.sort_values(["date", "hz", "kind", "thr"])
        for (dt, hz, k), g in df.groupby(["date", "hz", "kind"], sort=False):
            m = monotonize(dict(zip(g.thr, g.p)))
            df.loc[g.index, "p"] = [m[x] for x in g.thr]
    return df, {"weights": {f"{hz}|{k}": {"modelli": ms, "pesi": [float(x) for x in w]} for (hz, k), (ms, w) in W.items()}}


def adoption(metrics: pd.DataFrame, tol: float = 0.01, model: str = "Combinato") -> dict:
    """Regola di adozione (fissata in anticipo): sul bersaglio principale di ogni orizzonte il combinato batte A1 nel BSS
    su almeno 2 orizzonti sia nel 2000-2012 sia dal 2013, e non peggiora nessun orizzonte (in nessun periodo) di oltre 0,01.
    metrics: righe del set 'finale' con model, hz, thr, kind, bss_2000_12, bss_2013_26."""
    rows = []
    for hz in HORIZONS:
        a = metrics[(metrics.model == "A1") & (metrics.hz == hz) & (metrics.thr == PRIMARY[hz]) & (metrics.kind == "down")]
        c = metrics[(metrics.model == model) & (metrics.hz == hz) & (metrics.thr == PRIMARY[hz]) & (metrics.kind == "down")]
        if a.empty or c.empty:
            continue
        a, c = a.iloc[0], c.iloc[0]
        rows.append({"hz": hz, "d_2000_12": float(c.bss_2000_12 - a.bss_2000_12), "d_2013_26": float(c.bss_2013_26 - a.bss_2013_26),
                     "bss_c": float(c.bss), "bss_a1": float(a.bss)})
    n1 = sum(r["d_2000_12"] > 0 for r in rows)
    n2 = sum(r["d_2013_26"] > 0 for r in rows)
    worse = [r["hz"] for r in rows if min(r["d_2000_12"], r["d_2013_26"]) < -tol]
    ok = n1 >= 2 and n2 >= 2 and not worse
    return {"adopt": bool(ok), "orizzonti_meglio_2000_12": n1, "orizzonti_meglio_2013_26": n2, "peggiorati_oltre_soglia": worse, "dettaglio": rows}


# ---------- intervalli conformali (1.5) ----------
def interval_scale(q: pd.DataFrame, p: pd.Series, dates, hz: str, cover: float = 0.80, min_n: int = 40) -> pd.DataFrame:
    """q: righe kind='q' di FHS (date,hz,thr in 10/50/90,p). Per ogni data: fattore k (walk-forward) tale che l'intervallo
    q50 +- k*(q90-q10)/2 copra l'80% degli esiti maturati. Restituisce date, lo, hi, lo_raw, hi_raw, r (esito), k."""
    n = HORIZONS[hz]
    g = q[q.hz == hz].pivot_table(index="date", columns="thr", values="p")
    g = g.reindex(pd.DatetimeIndex(dates)).dropna()
    r = fwd_ret(p, n).reindex(g.index)
    half = (g[90] - g[10]) / 2
    s = ((r - g[50]).abs() / half.replace(0, np.nan))
    pos = p.index.get_indexer(g.index)
    ks = []
    for i in range(len(g)):
        m = (pos <= pos[i] - n) & s.notna().values
        ks.append(float(np.quantile(s.values[m], cover)) if m.sum() >= min_n else np.nan)
    k = pd.Series(ks, index=g.index)
    return pd.DataFrame({"lo_raw": g[10], "hi_raw": g[90], "lo": g[50] - k * half, "hi": g[50] + k * half, "r": r, "k": k})


def coverage(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["r"])
    raw = float(((d.r >= d.lo_raw) & (d.r <= d.hi_raw)).mean())
    dd = d.dropna(subset=["k"])
    con = float(((dd.r >= dd.lo) & (dd.r <= dd.hi)).mean()) if len(dd) else float("nan")
    return {"copertura_grezza": raw, "copertura_conformale": con, "n": int(len(dd)), "k_ultimo": float(dd.k.iloc[-1]) if len(dd) else float("nan")}


def registra_tentativo(res: dict, path) -> None:
    """Scrive in models.json (chiave 'tentativi') l'esito della regola di adozione, senza toccare il campione in uso."""
    import json
    from datetime import datetime, timezone
    reg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"champion": "A1", "versions": []}
    a = res["adozione"]
    voce = {"id": "E1-combinato", "data": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "adottato": bool(a["adopt"]),
            "regola": "BSS meglio di A1 su >=2 orizzonti sia 2000-12 sia 2013-26, nessun peggioramento oltre 0,01",
            "orizzonti_meglio_2000_12": a["orizzonti_meglio_2000_12"], "orizzonti_meglio_2013_26": a["orizzonti_meglio_2013_26"],
            "peggiorati": a["peggiorati_oltre_soglia"], "campione": reg.get("champion", "A1")}
    b = res.get("adozione_B")
    if b:
        voce["variante_B_a_posteriori"] = {"nota": "senza taratura isotonica, scelta DOPO aver visto i risultati: non adottabile",
                                           "regola_superata": bool(b["adopt"]), "peggiorati": b["peggiorati_oltre_soglia"]}
    reg.setdefault("tentativi", [])
    reg["tentativi"] = [t for t in reg["tentativi"] if not (t.get("id") == voce["id"] and t.get("data") == voce["data"])] + [voce]
    if a["adopt"]:
        voce["nota"] = "Regola superata: la sostituzione di A1 va decisa e collegata a mano (vedi CONTINUA_DA_QUI.md)."
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
