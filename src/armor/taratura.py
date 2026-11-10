"""Taratura annidata delle probabilità di calo (Patch 60a, regole in PROTOCOLLO_TARATURA.md, scritte prima dei risultati).
Modelli: A1 e FHS+VIX; correttori: Platt e isotonico; miscela calibrata; misure per fascia di VIX. Solo esiti noti alla data della previsione."""
import hashlib
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from . import modeleval
from .config import DATA, HORIZONS, PRIMARY, ROOT, TARGETS

FILE = DATA / "taratura.json"
PROTO = ROOT / "PROTOCOLLO_TARATURA.md"
MIN_N, MIN_EV, REFIT = 150, 8, 10
FASCE = [("VIX sotto 18", 0, 18), ("VIX 18-25", 18, 25), ("VIX sopra 25", 25, 1e9)]
EPS = 1e-3


def _logit(p):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _sig(z):
    return 1 / (1 + np.exp(-z))


def predizioni(p: pd.Series, vix: pd.Series | None, start: str = "1990-01-01", step: int = 5, sims: int = 2000, cache: str | None = None, log=print) -> dict:
    """Previsioni walk-forward di A1 e FHS+VIX (solo calo, soglie dell'app)."""
    from . import fhs
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    dates = p.index[p.index >= start][::step]
    log(f"[taratura] A1 su {len(dates)} date ...")
    a1 = pd.DataFrame(modeleval.a1_preds(p, dates))
    log("[taratura] FHS+VIX ...")
    fv = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims, vix=vix, w=0.5))
    out = {"dates": dates}
    for nome, df in (("A1", a1), ("FHS+VIX", fv)):
        df = df[df.kind == "down"]
        out[nome] = df[[t in TARGETS[h] for h, t in zip(df.hz, df.thr)]]
    if cache:
        pickle.dump(out, open(cache, "wb"))
    return out


def _fit_platt(z, y):
    if y.sum() < MIN_EV or (1 - y).sum() < MIN_EV:
        return None
    m = LogisticRegression(C=100.0, max_iter=200).fit(z.reshape(-1, 1), y)
    return lambda zz: _sig(m.coef_[0, 0] * zz + m.intercept_[0])


def _fit_iso(pp, y):
    if y.sum() < MIN_EV:
        return None
    m = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(pp, y)
    return lambda x: np.clip(m.predict(np.asarray(x, float)), EPS, 1 - EPS)


def tarare(pos: np.ndarray, n_sess: int, X: np.ndarray, y: np.ndarray, metodo: str) -> np.ndarray:
    """pos = posizione in sedute di ogni data; X = previsione (probabilità o logit se platt); y = esito (NaN se non noto).
    Alla data k si usano solo le righe j con pos_j + n_sess <= pos_k. Ritorna le previsioni tarate (NaN prima di avere abbastanza dati)."""
    out = np.full(len(X), np.nan)
    f, last = None, -10 ** 9
    for k in range(len(X)):
        ok = (pos + n_sess <= pos[k]) & np.isfinite(y)
        if ok.sum() < MIN_N:
            continue
        if f is None or k - last >= REFIT:
            f = (_fit_platt(X[ok], y[ok]) if metodo == "platt" else _fit_iso(X[ok], y[ok]))
            last = k
        if f is not None:
            out[k] = float(f(np.array([X[k]]))[0])
    return out


def _pendenza(pp, y):
    z = _logit(pp)
    if y.sum() < 5 or (1 - y).sum() < 5:
        return float("nan")
    return float(LogisticRegression(C=1e4, max_iter=300).fit(z.reshape(-1, 1), y).coef_[0, 0])


def _misure(pp, y, base, anni, vix):
    err, err_b = (pp - y) ** 2, (base - y) ** 2

    def bss(m):
        return float(1 - err[m].mean() / err_b[m].mean()) if m.sum() >= 20 and err_b[m].mean() > 0 else float("nan")
    allm = np.ones(len(y), bool)
    out = {"n": int(len(y)), "freq": float(y.mean()), "p_media": float(pp.mean()), "bss": bss(allm), "bss_2000_12": bss((anni >= 2000) & (anni < 2013)), "bss_2013_26": bss(anni >= 2013),
           "pendenza": _pendenza(pp, y), "distorsione": float(pp.mean() - y.mean()),
           "logloss": float(-(y * np.log(np.clip(pp, EPS, 1)) + (1 - y) * np.log(np.clip(1 - pp, EPS, 1))).mean())}
    try:
        from sklearn.metrics import roc_auc_score
        out["auc"] = float(roc_auc_score(y, pp)) if 0 < y.sum() < len(y) else float("nan")
    except Exception:  # noqa: BLE001
        out["auc"] = float("nan")
    fas = {}
    for nome, lo, hi in FASCE:
        m = np.isfinite(vix) & (vix >= lo) & (vix < hi)
        if m.sum() >= 20:
            fas[nome] = {"n": int(m.sum()), "freq": float(y[m].mean()), "p_media": float(pp[m].mean()), "distorsione": float(pp[m].mean() - y[m].mean()), "bss": bss(m)}
    out["fasce_vix"] = fas
    try:   # intervallo al 90% con blocchi (stesso metodo della valutazione mensile)
        lo, hi = modeleval.block_ci(err, err_b, 5, reps=300)
        out["bss_lo"], out["bss_hi"] = float(lo), float(hi)
    except Exception:  # noqa: BLE001
        out["bss_lo"] = out["bss_hi"] = float("nan")
    return out


def valuta(p: pd.Series, vix: pd.Series | None, pr: dict, log=print) -> dict:
    dates = pr["dates"]
    pos_all = np.array([p.index.get_loc(t) for t in dates])
    vv = (vix.reindex(dates, method="ffill").values if vix is not None else np.full(len(dates), np.nan)).astype(float)
    righe = []
    for hz, n in HORIZONS.items():
        for thr in TARGETS[hz]:
            a = pr["A1"][(pr["A1"].hz == hz) & (pr["A1"].thr == thr)].set_index("date")["p"]
            f = pr["FHS+VIX"][(pr["FHS+VIX"].hz == hz) & (pr["FHS+VIX"].thr == thr)].set_index("date")["p"]
            idx = a.index.intersection(f.index)
            if len(idx) < 400:
                continue
            ii = np.array([dates.get_loc(t) for t in idx])
            y_all = modeleval.outcome(p, idx, hz, "down", thr).reindex(idx)
            base_all = modeleval.purged_base(p, idx, hz, "down", thr).reindex(idx)
            pos = pos_all[ii]
            yv = y_all.values.astype(float)
            pa, pf = a.loc[idx].values, f.loc[idx].values
            z_a, z_f = _logit(pa), _logit(pf)
            cand = {"A1": pa, "FHS+VIX": pf, "Media A1 e FHS+VIX": _sig((z_a + z_f) / 2),
                    "A1 + Platt": tarare(pos, n, z_a, yv, "platt"), "A1 + isotonica": tarare(pos, n, pa, yv, "iso"),
                    "FHS+VIX + Platt": tarare(pos, n, z_f, yv, "platt"), "FHS+VIX + isotonica": tarare(pos, n, pf, yv, "iso"),
                    "Combinato-Tarato": tarare(pos, n, (z_a + z_f) / 2, yv, "platt")}
            comune = np.isfinite(yv) & np.isfinite(base_all.values) & np.all([np.isfinite(v) for v in cand.values()], axis=0)
            if comune.sum() < 200:
                continue
            anni = idx.year.values[comune]
            for nome, pp in cand.items():
                m = _misure(np.asarray(pp)[comune], yv[comune], base_all.values[comune], anni, vv[ii][comune])
                righe.append({"hz": hz, "thr": int(thr), "principale": int(thr) == PRIMARY[hz], "modello": nome, "da": str(idx[comune][0].date()), **m})
        log(f"[taratura] {hz} fatto")
    return {"righe": righe}


def verdetto(righe: list[dict]) -> dict:
    """Regola del protocollo: per ogni versione tarata contro il genitore, sulle soglie principali."""
    df = pd.DataFrame(righe)
    out = {}
    pr = df[df.principale]
    for nome, gen in (("A1 + Platt", "A1"), ("A1 + isotonica", "A1"), ("FHS+VIX + Platt", "FHS+VIX"), ("FHS+VIX + isotonica", "FHS+VIX"),
                      ("Combinato-Tarato", "FHS+VIX"), ("Combinato-Tarato", "A1")):
        buoni, peggio, dist_ok, det = 0, False, True, {}
        for hz in HORIZONS:
            a = pr[(pr.hz == hz) & (pr.modello == nome)]
            b = pr[(pr.hz == hz) & (pr.modello == gen)]
            if a.empty or b.empty:
                continue
            a, b = a.iloc[0], b.iloc[0]
            d0, d1 = a.bss_2000_12 - b.bss_2000_12, a.bss_2013_26 - b.bss_2013_26
            det[hz] = {"d_bss_2000_12": float(d0), "d_bss_2013_26": float(d1)}
            if d0 >= 0.005 and d1 >= 0.005:
                buoni += 1
            if d0 < -0.005 or d1 < -0.005:
                peggio = True
            fa, fb = (a.fasce_vix or {}).get("VIX sopra 25"), (b.fasce_vix or {}).get("VIX sopra 25")
            if fa and fb and abs(fa["distorsione"]) > abs(fb["distorsione"]):
                dist_ok = False
        out[f"{nome} contro {gen}"] = {"orizzonti_migliori": buoni, "nessun_peggioramento": not peggio, "distorsione_vix_alto_ok": dist_ok,
                                       "supera": bool(buoni >= 3 and not peggio and dist_ok), "dettaglio": det}
    return out


def protocollo_hash() -> str:
    return hashlib.sha256(PROTO.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run(cache: str | None = None, log=print) -> dict:
    from .features import closed_sp500
    from . import store
    p = closed_sp500()
    v = store.load("vix")
    vix = v if len(v) > 1000 else None
    pr = predizioni(p, vix, cache=cache, log=log)
    res = valuta(p, vix, pr, log)
    res["verdetto"] = verdetto(res["righe"])
    res["data"] = str(pd.Timestamp.now().date())
    res["protocollo_sha256"] = protocollo_hash()
    FILE.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
