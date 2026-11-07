"""Motore FHS (Filtered Historical Simulation): volatilità GJR-GARCH(1,1) con errori t + simulazione dei percorsi futuri.

Idea: la volatilità dell'S&P 500 è prevedibile, la direzione no. Si stima la volatilità di oggi, poi si simulano migliaia di percorsi
dei prossimi 126 giorni pescando a caso gli shock standardizzati della storia (bootstrap). Da quei percorsi escono, in modo coerente,
tutte le probabilità di calo e di rialzo (a ogni soglia e orizzonte), gli scenari e i quantili dei rendimenti.
Nessuna libreria esterna: solo numpy e scipy. Nessuno sguardo al futuro: ogni previsione usa solo prezzi fino alla data."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln

from .config import HORIZONS
from .features import fwd_maxdd, fwd_maxup, fwd_ret
from .outlook import SCEN_EDGES, THRESHOLDS

FIT_START = "1950-01-01"
H_MAX = max(HORIZONS.values())
VRP = 0.8          # la varianza realizzata è in media ~80% di quella implicita nel VIX (premio per il rischio di volatilità)


def log_returns(p: pd.Series) -> pd.Series:
    """Rendimenti logaritmici giornalieri in percentuale."""
    p = p.dropna().astype(float)
    return (np.log(p).diff().dropna() * 100.0)


def _filter(e: np.ndarray, omega: float, alpha: float, gamma: float, beta: float) -> np.ndarray:
    """Varianza condizionata sig2[t] (usa solo e[:t]) del GJR-GARCH; sig2[n] è la varianza del giorno dopo l'ultimo."""
    n = len(e)
    neg = (e < 0).astype(float)
    u = np.empty(n + 1)
    s0 = float(np.var(e)) if n > 1 else 1.0
    u[0] = s0
    u[1:] = omega + (alpha + gamma * neg) * e ** 2
    return lfilter([1.0], [1.0, -beta], u)


def _nll(theta: np.ndarray, e: np.ndarray) -> float:
    omega, alpha, gamma, beta, nu = theta
    if alpha + gamma / 2 + beta >= 0.9995:
        return 1e10 + 1e6 * (alpha + gamma / 2 + beta)
    s2 = _filter(e, omega, alpha, gamma, beta)[:-1]
    s2 = np.maximum(s2, 1e-8)
    z2 = e ** 2 / s2
    ll = (gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(np.pi * (nu - 2)) - 0.5 * np.log(s2)
          - (nu + 1) / 2 * np.log1p(z2 / (nu - 2)))
    return -float(ll.sum())


def fit(r: pd.Series | np.ndarray, x0: np.ndarray | None = None) -> dict:
    """Stima dei parametri sui rendimenti (in %). Restituisce parametri, drift e shock standardizzati."""
    r = np.asarray(r, float)
    mu = float(r.mean())
    e = r - mu
    v = float(np.var(e))
    if x0 is None:
        x0 = np.array([v * 0.02, 0.03, 0.10, 0.88, 8.0])
    bounds = [(1e-6, 2.0), (0.0, 0.4), (0.0, 0.6), (0.5, 0.999), (2.5, 40.0)]
    res = minimize(_nll, x0, args=(e,), method="L-BFGS-B", bounds=bounds)
    th = res.x
    if not np.isfinite(res.fun) or th[1] + th[2] / 2 + th[3] >= 0.9995:
        th = x0
    omega, alpha, gamma, beta, nu = th
    s2 = _filter(e, omega, alpha, gamma, beta)
    z = e / np.sqrt(np.maximum(s2[:-1], 1e-8))
    z = (z - z.mean()) / z.std()
    return {"omega": omega, "alpha": alpha, "gamma": gamma, "beta": beta, "nu": nu, "mu": mu, "z": z, "theta": th,
            "persistence": float(alpha + gamma / 2 + beta), "n": len(r)}


def next_variance(params: dict, r: np.ndarray) -> float:
    """Varianza (in %^2) del giorno successivo all'ultimo rendimento, con parametri fissi."""
    e = np.asarray(r, float) - params["mu"]
    return float(_filter(e, params["omega"], params["alpha"], params["gamma"], params["beta"])[-1])


def simulate(params: dict, s2_next: float, sims: int = 5000, horizon: int = H_MAX, seed: int = 0) -> np.ndarray:
    """Percorsi simulati dei prezzi (base 1.0), forma (horizon, sims)."""
    rng = np.random.default_rng(seed)
    z = params["z"]
    om, al, ga, be, mu = params["omega"], params["alpha"], params["gamma"], params["beta"], params["mu"]
    s2 = np.full(sims, s2_next)
    cum = np.empty((horizon, sims))
    for h in range(horizon):
        e = np.sqrt(s2) * z[rng.integers(0, len(z), sims)]
        cum[h] = e + mu
        s2 = om + (al + ga * (e < 0)) * e ** 2 + be * s2
    return np.exp(np.cumsum(cum, axis=0) / 100.0)


def summarize(paths: np.ndarray, thresholds=THRESHOLDS) -> dict:
    """Probabilità di calo/rialzo per soglia e orizzonte, quantili e scenari dai percorsi simulati."""
    out = {}
    for hz, n in HORIZONS.items():
        sub = paths[:n]
        dd = sub.min(axis=0) - 1.0
        up = sub.max(axis=0) - 1.0
        rt = sub[-1] - 1.0
        b = np.searchsorted(SCEN_EDGES, rt, side="right")
        out[hz] = {
            "down": {t: {"p": float((dd <= -t / 100).mean())} for t in thresholds},
            "up": {t: {"p": float((up >= t / 100).mean())} for t in thresholds},
            "ret_analog": {"q10": float(np.quantile(rt, .10)), "q50": float(np.quantile(rt, .50)), "q90": float(np.quantile(rt, .90)), "pos": float((rt > 0).mean())},
            "scen": [float((b == i).mean()) for i in range(5)],
        }
    return out


def adjust_with_vix(s2_next: float, vix: float | None, w: float) -> float:
    """Sposta la varianza del primo giorno verso quella implicita dal VIX (corretta per il premio al rischio)."""
    if not vix or w <= 0 or vix <= 0:
        return s2_next
    target = VRP * (vix ** 2) / 252.0
    return float(np.exp((1 - w) * np.log(s2_next) + w * np.log(target)))


def forecast(p: pd.Series, date: pd.Timestamp | None = None, sims: int = 5000, seed: int = 0, vix: float | None = None,
             w: float = 0.0, params: dict | None = None, fit_start: str = FIT_START) -> dict:
    """Stima alla data indicata (default: ultima). Stessa struttura di outlook.probability_matrix (+ 'scen'). Usa solo prezzi fino a 'date'."""
    p = p.dropna()
    if date is not None:
        p = p[p.index <= date]
    r = log_returns(p[p.index >= fit_start])
    if params is None:
        params = fit(r.values)
    s2 = adjust_with_vix(next_variance(params, r.values), vix, w)
    res = summarize(simulate(params, s2, sims, H_MAX, seed))
    full = p
    for hz, n in HORIZONS.items():
        dd, up, rt = fwd_maxdd(full, n).dropna(), fwd_maxup(full, n).dropna(), fwd_ret(full, n).dropna()
        for t, c in res[hz]["down"].items():
            c["base"] = float((dd <= -t / 100).mean())
        for t, c in res[hz]["up"].items():
            c["base"] = float((up >= t / 100).mean())
        res[hz]["ret_base"] = {"q50": float(rt.median()), "pos": float((rt > 0).mean())}
        res[hz]["n_train"] = int(len(dd))
    res["_params"] = {k: float(params[k]) for k in ("omega", "alpha", "gamma", "beta", "nu", "mu", "persistence")}
    res["_sigma_annual"] = float(np.sqrt(s2 * 252))
    return res


def backtest_preds(p: pd.Series, dates, refit_every: int = 252, sims: int = 2000, vix: pd.Series | None = None, w: float = 0.0,
                   embargo: int = 5, fit_start: str = FIT_START) -> list[dict]:
    """Previsioni walk-forward: parametri rifatti ogni 'refit_every' sedute con dati fino a (data - embargo); a ogni data
    la varianza si aggiorna con i prezzi noti fino a quel giorno. Restituisce una lista di righe (data, orizzonte, tipo, soglia, p)."""
    p = p.dropna()
    r_all = log_returns(p[p.index >= fit_start])
    idx = r_all.index
    rows, params, last_fit = [], None, -10 ** 9
    x0 = None
    for t in dates:
        if t not in idx:
            continue
        i = idx.get_loc(t)
        if i < 750:
            continue
        if params is None or i - last_fit >= refit_every:
            j = max(i - embargo, 500)
            params = fit(r_all.values[:j], x0)
            x0 = params["theta"]
            last_fit = i
        s2 = next_variance(params, r_all.values[: i + 1])
        v = None
        if vix is not None:
            vv = vix[vix.index <= t]
            v = float(vv.iloc[-1]) if len(vv) and (t - vv.index[-1]).days < 7 else None
        s2 = adjust_with_vix(s2, v, w)
        res = summarize(simulate(params, s2, sims, H_MAX, seed=int(t.strftime("%Y%m%d")) % (2 ** 31)))
        for hz in HORIZONS:
            for kind in ("down", "up"):
                for thr, c in res[hz][kind].items():
                    rows.append({"date": t, "hz": hz, "kind": kind, "thr": thr, "p": c["p"]})
            ra = res[hz]["ret_analog"]   # quantili del rendimento finale (per gli intervalli): kind="q", thr=10/50/90
            for q in (10, 50, 90):
                rows.append({"date": t, "hz": hz, "kind": "q", "thr": q, "p": ra["q%d" % q]})
    return rows
