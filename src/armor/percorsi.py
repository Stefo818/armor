"""Motore unico di percorsi (PIANO ARMOR 3, Fase 2): dagli STESSI percorsi simulati escono, in modo coerente tra orizzonti e soglie,
  1) il rendimento finale (quantili 5-95 e probabilità di chiudere in perdita),
  2) la perdita rispetto a oggi (probabilità che il minimo scenda sotto -5/-10/-15/-20%),
  3) il massimo drawdown dentro il periodo (massimo calcolato lungo il percorso).
Basato su fhs.py (GJR-GARCH-t con residui ricampionati). Orizzonti: 5, 7, 21, 63, 126, 252 sedute (7 = «10 giorni» storico).
Varianti pre-registrate in PROTOCOLLO_VERIFICA.md §3: varianza iniziale V0/V1/V2 × controllo delle code T0/T1/T2/T3. Stessi numeri casuali per tutti
gli orizzonti e tutte le varianti (seme fisso per data): le differenze dipendono solo dalla varianza.
Definizioni (fissate prima di verificare):
  V0  FHS attuale (varianza di oggi dal filtro GARCH).
  V1  FHS+VIX: varianza iniziale spostata verso VIX con peso 0,5 e premio 0,8 (fhs.adjust_with_vix).
  V2  struttura a termine: varianza media attesa dei giorni 1-21 = r21 · VIX²; dei giorni 22-63 = r_fwd · varianza forward (63·VIX3M² − 21·VIX²)/42;
      r21 e r_fwd = media (ultime 1.260 date con esito noto, limitata a 0,5-1,2; 0,8 se meno di 250) di «varianza realizzata / implicita» in walk-forward.
      Il GARCH fornisce la dinamica: la varianza iniziale è scelta perché la sua media attesa sui giorni 1-21 sia il bersaglio; sui giorni 22-63 la varianza
      usata è moltiplicata per il fattore che porta la media attesa al bersaglio; oltre il giorno 63 vale la dinamica del GARCH. Senza VIX3M la variante non esiste.
  T0  nessun controllo.   T1  tetto alla varianza condizionata (99,5° percentile delle varianze storiche filtrate).
  T2  ancoraggio di lungo periodo: dal giorno 64 la varianza usata è la media geometrica 50/50 tra quella del GARCH e quella di lungo periodo ω/(1−ρ),
      limitata a [1/4, 4] volte quella di lungo periodo.
  T3  bootstrap filtrato a blocchi: varianza attesa deterministica (che torna verso il lungo periodo con persistenza ρ) × blocchi di 21 residui storici standardizzati."""
import numpy as np
import pandas as pd
from scipy.stats import kurtosis

from . import fhs

ORIZZONTI = {"1s": 5, "10g": 7, "1m": 21, "3m": 63, "6m": 126, "12m": 252}
VECCHI = ("10g", "1m", "3m", "6m")           # quelli confrontabili con A1
H_MAX = 252
QLEV = (5, 10, 25, 50, 75, 90, 95)
SOGLIE = (5, 10, 15, 20)
VARIANTI = [f"{v}{t}" for v in ("V0", "V1", "V2") for t in ("T0", "T1", "T2", "T3")]
SEMPLICITA = {v: i for i, v in enumerate(VARIANTI)}   # ordine di semplicità: V0 < V1 < V2, poi T0 < T1 < T2 < T3
N_LIVE, N_BACKTEST = 20000, 3000
LIMITI_CODE = {"rendimento_min": -0.80, "rendimento_max": 3.00}   # a 252 sedute: percorsi fuori da questi limiti sono segnalati


# ------------------------------------------------------------------ stima dei parametri e della varianza di partenza
def stato(r: np.ndarray, params: dict | None = None) -> dict:
    """Parametri GARCH e grandezze derivate dai rendimenti (in %). Se `params` manca si stima."""
    par = params if params is not None else fhs.fit(r)
    e = np.asarray(r, float) - par["mu"]
    s2f = fhs._filter(e, par["omega"], par["alpha"], par["gamma"], par["beta"])
    rho = float(par["persistence"])
    lr = float(par["omega"] / (1 - rho)) if rho < 1 else float(np.var(e))
    return {"par": par, "s2_next": float(s2f[-1]), "cap": float(np.quantile(s2f[:-1], 0.995)), "rho": rho, "s2_lr": lr,
            "emivita": float(np.log(0.5) / np.log(rho)) if 0 < rho < 1 else float("nan")}


def curva_vol(st: dict, s2_0: float, h: int = H_MAX) -> list[float]:
    """Volatilità annua attesa giorno per giorno (radice della varianza attesa), con la dinamica del GARCH."""
    k = np.arange(h)
    ev = st["s2_lr"] + st["rho"] ** k * (s2_0 - st["s2_lr"])
    return [float(np.sqrt(max(x, 1e-12) * 252)) for x in ev]


def rapporti_realizzata_implicita(r: pd.Series, vix: pd.Series, vix3m: pd.Series) -> pd.DataFrame:
    """Per ogni data d: varianza realizzata / implicita sui giorni 1-21 e 22-63 successivi (annualizzate, in %²). Esito noto solo da d+21 e d+63."""
    r = r.dropna()
    idx = r.index
    r2 = (r.values ** 2)
    c = np.concatenate([[0.0], np.cumsum(r2)])
    n = len(r)
    rv21 = np.full(n, np.nan)
    rvf = np.full(n, np.nan)
    for i in range(n):          # r[i] è il rendimento della seduta idx[i]; dopo la data idx[i] vengono i+1...
        if i + 21 < n:
            rv21[i] = (c[i + 22] - c[i + 1]) / 21 * 252
        if i + 63 < n:
            rvf[i] = (c[i + 64] - c[i + 22]) / 42 * 252
    v1 = vix.reindex(idx).ffill(limit=5).values ** 2
    v3 = vix3m.reindex(idx).ffill(limit=5).values ** 2
    fwd = (63 * v3 - 21 * v1) / 42
    d = pd.DataFrame({"r21": rv21 / v1, "rfwd": np.where(fwd > 0, rvf / fwd, np.nan)}, index=idx)
    return d


def _rapporto(d: pd.DataFrame, i: int, col: str, ritardo: int, finestra: int = 1260, minimo: int = 250) -> float:
    """Media (limitata a 0,5-1,2) delle ultime `finestra` date con esito noto alla posizione i."""
    x = d[col].values[max(0, i - ritardo - finestra + 1): max(0, i - ritardo + 1)]
    x = x[np.isfinite(x)]
    return float(np.clip(x.mean(), 0.5, 1.2)) if len(x) >= minimo else 0.8


def varianza_iniziale(st: dict, variante: str, vix: float | None, vix3m: float | None, rap: tuple[float, float] | None = None) -> tuple[float | None, float | None]:
    """(varianza di partenza, fattore per i giorni 22-63 o None). Restituisce (None, None) se la variante non è calcolabile."""
    v = variante[:2]
    s2 = st["s2_next"]
    if v == "V0":
        return s2, None
    if v == "V1":
        return fhs.adjust_with_vix(s2, vix, 0.5), None
    if not vix or not vix3m or vix <= 0 or vix3m <= 0:
        return None, None
    r21, rf = rap if rap is not None else (0.8, 0.8)
    t1 = r21 * vix ** 2 / 252.0
    fwd = (63 * vix3m ** 2 - 21 * vix ** 2) / 42.0
    t2 = rf * max(fwd, 0.25 * vix ** 2) / 252.0
    rho, lr = st["rho"], st["s2_lr"]
    k1, k2 = np.arange(21), np.arange(21, 63)
    s0 = lr + (t1 - lr) / np.mean(rho ** k1)
    s0 = max(s0, 0.05 * lr)
    media2 = lr + (s0 - lr) * np.mean(rho ** k2)
    mult = float(np.clip(t2 / max(media2, 1e-12), 0.25, 4.0))
    return float(s0), mult


# ------------------------------------------------------------------ simulazione
def simula(st: dict, s2_0: float, tail: str, n_paths: int, seed: int, mult2: float | None = None, h: int = H_MAX) -> np.ndarray:
    """Percorsi (base 1,0), forma (h, n_paths). Stessi indici casuali per ogni variante con lo stesso seme."""
    par, z = st["par"], st["par"]["z"]
    rng = np.random.default_rng(seed)
    om, al, ga, be, mu = par["omega"], par["alpha"], par["gamma"], par["beta"], par["mu"]
    rho, lr, cap = st["rho"], st["s2_lr"], st["cap"]
    out = np.empty((h, n_paths))
    if tail == "T3":
        L = 21
        nb = int(np.ceil(h / L))
        starts = rng.integers(0, len(z) - L + 1, (nb, n_paths))
        k = np.arange(h)
        ev = lr + rho ** k * (s2_0 - lr)
        if mult2 is not None:
            ev[21:63] = ev[21:63] * mult2
        ev = np.maximum(ev, 1e-8)
        for t in range(h):
            out[t] = np.sqrt(ev[t]) * z[starts[t // L] + t % L] + mu
        return np.exp(np.cumsum(out, axis=0) / 100.0)
    idx = rng.integers(0, len(z), (h, n_paths))
    s2 = np.full(n_paths, float(s2_0))
    lo, hi = lr / 4.0, lr * 4.0
    for t in range(h):
        sv = s2
        if tail == "T2" and t >= 63:
            sv = np.clip(np.exp(0.5 * np.log(np.maximum(s2, 1e-12)) + 0.5 * np.log(lr)), lo, hi)
        if mult2 is not None and 21 <= t < 63:
            sv = s2 * mult2
        if tail == "T1":
            sv = np.minimum(sv, cap)
        e = np.sqrt(sv) * z[idx[t]]
        out[t] = e + mu
        s2 = om + (al + ga * (e < 0)) * e ** 2 + be * s2
        if tail == "T1":
            s2 = np.minimum(s2, cap)
    return np.exp(np.cumsum(out, axis=0) / 100.0)


def riassumi(paths: np.ndarray, orizzonti: dict | None = None, extra: bool = False) -> dict:
    """Dai percorsi: per ogni orizzonte rendimento finale (quantili, P<0), perdita rispetto a oggi e massimo drawdown, con errore Monte Carlo."""
    orizzonti = orizzonti or ORIZZONTI
    N = paths.shape[1]
    base = np.vstack([np.ones((1, N)), paths])
    dd_run = np.minimum.accumulate(paths / np.maximum.accumulate(base, axis=0)[1:] - 1.0, axis=0)   # drawdown massimo fino a ogni seduta
    min_run = np.minimum.accumulate(paths, axis=0) - 1.0
    out = {}
    for hz, n in orizzonti.items():
        rt = paths[n - 1] - 1.0
        q = np.quantile(rt, [x / 100 for x in QLEV])
        se = lambda p: float(np.sqrt(max(p * (1 - p), 0) / N))
        down = {t: float((min_run[n - 1] <= -t / 100).mean()) for t in SOGLIE}
        mdd = {t: float((dd_run[n - 1] <= -t / 100).mean()) for t in SOGLIE}
        pneg = float((rt < 0).mean())
        o = {"ret": {f"q{k}": float(v) for k, v in zip(QLEV, q)}, "p_neg": pneg, "down": down, "mdd": mdd,
             "se": {"down": {t: se(p) for t, p in down.items()}, "mdd": {t: se(p) for t, p in mdd.items()}, "p_neg": se(pneg)}}
        if extra and n >= 126:
            lr_ = np.log(paths[n - 1])
            o["curtosi"] = float(kurtosis(lr_))
            o["estremi"] = {"min": float(rt.min()), "max": float(rt.max()), "fuori_limiti": float(((rt < LIMITI_CODE["rendimento_min"]) | (rt > LIMITI_CODE["rendimento_max"])).mean())}
        out[hz] = o
    return out


def stima(r: np.ndarray, variante: str, seed: int, vix: float | None = None, vix3m: float | None = None, rap=None, n_paths: int = N_LIVE,
          st: dict | None = None, extra: bool = False, orizzonti: dict | None = None) -> dict | None:
    """Stima completa per una variante. None se la variante non è calcolabile (V2 senza VIX3M)."""
    st = st or stato(r)
    s0, m2 = varianza_iniziale(st, variante, vix, vix3m, rap)
    if s0 is None:
        return None
    res = riassumi(simula(st, s0, variante[2:], n_paths, seed, m2), orizzonti, extra)
    res["_diag"] = {"persistenza": st["rho"], "emivita": st["emivita"], "vol_lungo": float(np.sqrt(st["s2_lr"] * 252)), "vol_partenza": float(np.sqrt(s0 * 252)),
                    "vol_garch_oggi": float(np.sqrt(st["s2_next"] * 252)), "n_percorsi": n_paths, "variante": variante,
                    "parametri": {k: float(st["par"][k]) for k in ("omega", "alpha", "gamma", "beta", "nu", "mu")}}
    return res


# ------------------------------------------------------------------ walk-forward (verifica)
def mdd_futuro(p: pd.Series, n: int) -> pd.Series:
    """Massimo drawdown realizzato nelle n sedute successive a ogni data (massimo calcolato dal prezzo di quella data in poi)."""
    v = p.values
    out = np.full(len(v), np.nan)
    for i in range(len(v) - n):
        w = v[i:i + n + 1]
        out[i] = (w / np.maximum.accumulate(w) - 1.0).min()
    return pd.Series(out, index=p.index)


def walk_forward(p: pd.Series, dates, vix: pd.Series, vix3m: pd.Series, varianti=None, sims: int = N_BACKTEST, refit_every: int = 252, embargo: int = 5,
                 fit_start: str = fhs.FIT_START, log=print) -> dict[str, pd.DataFrame]:
    """Previsioni walk-forward di ogni variante: solo dati noti a ogni data; parametri rifatti ogni anno (con distanza di `embargo` sedute).
    Righe: date, hz (10g/1m/3m/6m), kind (down = perdita rispetto a oggi, mdd, q = quantili del rendimento finale), thr, p."""
    varianti = varianti or VARIANTI
    p = p.dropna()
    r_all = fhs.log_returns(p[p.index >= fit_start])
    idx = r_all.index
    rap = rapporti_realizzata_implicita(r_all, vix, vix3m) if vix3m is not None and len(vix3m) > 300 else None
    rows = {v: [] for v in varianti}
    st, last_fit, x0 = None, -10 ** 9, None
    for t in dates:
        if t not in idx:
            continue
        i = idx.get_loc(t)
        if i < 750:
            continue
        if st is None or i - last_fit >= refit_every:
            j = max(i - embargo, 500)
            par = fhs.fit(r_all.values[:j], x0)
            x0 = par["theta"]
            st = stato(r_all.values[:j], par)
            last_fit = i
        stt = dict(st)
        stt["s2_next"] = fhs.next_variance(st["par"], r_all.values[: i + 1])
        vv = vix[vix.index <= t]
        v1 = float(vv.iloc[-1]) if len(vv) and (t - vv.index[-1]).days < 7 else None
        v3s = vix3m[vix3m.index <= t] if vix3m is not None else pd.Series(dtype=float)
        v3 = float(v3s.iloc[-1]) if len(v3s) and (t - v3s.index[-1]).days < 7 else None
        ra = (_rapporto(rap, i, "r21", 21), _rapporto(rap, i, "rfwd", 63)) if rap is not None else None
        seed = int(t.strftime("%Y%m%d")) % (2 ** 31)
        for v in varianti:
            s0, m2 = varianza_iniziale(stt, v, v1, v3, ra)
            if s0 is None:
                continue
            res = riassumi(simula(stt, s0, v[2:], sims, seed, m2), {k: n for k, n in ORIZZONTI.items()})
            for hz, o in res.items():
                for thr, pv in o["down"].items():
                    rows[v].append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": pv})
                for thr, pv in o["mdd"].items():
                    rows[v].append({"date": t, "hz": hz, "kind": "mdd", "thr": thr, "p": pv})
                for q in QLEV:
                    rows[v].append({"date": t, "hz": hz, "kind": "q", "thr": q, "p": o["ret"][f"q{q}"]})
    return {v: pd.DataFrame(x) for v, x in rows.items()}


# ------------------------------------------------------------------ verifica delle varianti (protocollo §3-§4)
def curtosi_storica(p: pd.Series, n: int, da: str = "1950-01-01") -> float:
    """Curtosi in eccesso dei rendimenti logaritmici a n sedute, con finestre non sovrapposte (storia dal 1950)."""
    lp = np.log(p[p.index >= da].dropna().values)
    x = lp[n::n] - lp[:-n:n][: len(lp[n::n])]
    return float(kurtosis(x)) if len(x) > 20 else float("nan")


def valuta_varianti(p: pd.Series, dates, wf: dict, a1: pd.DataFrame, step: int = 5, reps: int = 1000, log=print) -> dict:
    """Confronto delle 12 varianti con A1 (stesse date), regola di adozione orizzonte per orizzonte. Non cambia nulla nell'app: scrive solo il risultato."""
    from . import verifica as V
    from .config import HORIZONS, PRIMARY
    from .features import fwd_ret
    from .modeleval import outcome, purged_base
    pos_all = pd.Series(np.arange(len(p)), index=p.index)
    pos = pos_all.reindex(dates)
    out = {"orizzonti": {}, "varianti": VARIANTI}
    for hz in VECCHI:
        n, thr = HORIZONS[hz], PRIMARY[hz]
        y = outcome(p, dates, hz, "down", thr)
        base = purged_base(p, dates, hz, "down", thr)
        rt = fwd_ret(p, n).reindex(dates)
        sa = a1[(a1.hz == hz) & (a1.kind == "down") & (a1.thr == thr)].set_index("date")["p"].dropna()
        d_a1 = V.prepara(dates, pos, y, base, {"A1": sa})
        ra = V.valuta_modello(d_a1, "A1", n, step, "A1", reps)
        serie, qs = {}, {}
        for v, df in wf.items():
            if df is None or df.empty:
                continue
            g = df[(df.hz == hz) & (df.kind == "down") & (df.thr == thr)].set_index("date")["p"].dropna()
            if len(g):
                serie[v] = g
            qs[v] = {q: df[(df.hz == hz) & (df.kind == "q") & (df.thr == q)].set_index("date")["p"] for q in QLEV}
        righe, pv = {}, {}
        for v, g in serie.items():
            d = V.prepara(dates, pos, y, base, {"A1": sa, v: g})
            if len(d) < 60:
                continue
            r = V.valuta_modello(d, v, n, step, "A1", reps)
            ix = d.index
            lo, hi = qs[v][10].reindex(ix), qs[v][90].reindex(ix)
            r["copertura_10_90"] = V.copertura(lo.values, hi.values, rt.reindex(ix).values)
            r["copertura_5_95"] = V.copertura(qs[v][5].reindex(ix).values, qs[v][95].reindex(ix).values, rt.reindex(ix).values)
            qm = np.column_stack([qs[v][q].reindex(ix).values for q in QLEV])
            r["crps"] = V.crps_quantili([q / 100 for q in QLEV], qm, rt.reindex(ix).values)
            r["date_ratio"] = float(len(d) / max(len(d_a1), 1))
            r["da"], r["a"] = str(ix[0].date()), str(ix[-1].date())
            righe[v] = r
            pv[v] = r["vs_ref"]["dm"]["p"]
        adj = V.holm(pv)
        # PBO: matrice «varianti × blocchi di tempo» del Brier sulle date comuni a tutte le varianti
        pbo = {"pbo": float("nan"), "n_comb": 0}
        pbo_pieno = dict(pbo)
        if len(serie) >= 3:
            comuni = None
            for g in serie.values():
                comuni = g.index if comuni is None else comuni.intersection(g.index)
            comuni = comuni.intersection(y.dropna().index)
            if len(comuni) > 200:
                bl = np.array_split(np.arange(len(comuni)), 32)
                yy = y.reindex(comuni).values
                M = np.array([[-V.brier(serie[v].reindex(comuni).values[b], yy[b]) for v in serie] for b in bl])
                pbo = V.pbo_cscv(M, 16)
            piene = [v for v in serie if righe.get(v, {}).get("date_ratio", 0) >= 0.95]
            if len(piene) >= 3:
                cm = serie[piene[0]].index
                for v in piene[1:]:
                    cm = cm.intersection(serie[v].index)
                cm = cm.intersection(y.dropna().index)
                bl = np.array_split(np.arange(len(cm)), 32)
                yy = y.reindex(cm).values
                M = np.array([[-V.brier(serie[v].reindex(cm).values[b], yy[b]) for v in piene] for b in bl])
                pbo_pieno = V.pbo_cscv(M, 16)
        passano = []
        for v, r in righe.items():
            r["vs_ref"]["dm"]["p_holm"] = adj.get(v)
            ok = V.regola_adozione(r, r["copertura_10_90"], pbo["pbo"], adj.get(v))
            if r["date_ratio"] < 0.95:
                ok["condizioni"]["0_stesse_date_di_A1"] = False
                ok["passa"] = False
            r["adozione"] = ok
            if ok["passa"]:
                passano.append(v)
        scelta = None
        if passano:
            mn = min(righe[v]["crps"] for v in passano)
            vicini = [v for v in passano if righe[v]["crps"] <= mn * 1.01]
            me = min(righe[v]["ece"] for v in vicini)
            vicini2 = [v for v in vicini if righe[v]["ece"] <= me * 1.01 + 1e-12]
            scelta = sorted(vicini2, key=lambda v: SEMPLICITA[v])[0] if len(vicini2) > 1 else vicini2[0]
        out["orizzonti"][hz] = {"sedute": n, "soglia": thr, "A1": ra, "varianti": righe, "pbo": pbo, "pbo_varianti_complete": pbo_pieno, "passano": passano, "scelta": scelta}
        log(f"[percorsi] {hz}: passano {passano or 'nessuna'} (PBO {pbo['pbo']:.2f})")
    # variante da mostrare come «sperimentale» dove nessuna è adottata: CRPS medio normalizzato, solo su varianti con tutte le date
    punt = {}
    for hz, o in out["orizzonti"].items():
        pieni = {v: r for v, r in o["varianti"].items() if r["date_ratio"] >= 0.95}
        if not pieni:
            continue
        mn = min(r["crps"] for r in pieni.values())
        for v, r in pieni.items():
            punt.setdefault(v, []).append(r["crps"] / mn)
    ok_v = {v: np.mean(x) for v, x in punt.items() if len(x) == len(out["orizzonti"])}
    out["mostrata"] = min(ok_v, key=lambda v: (round(ok_v[v], 3), SEMPLICITA[v])) if ok_v else "V1T1"
    out["crps_relativo"] = {v: float(x) for v, x in ok_v.items()}
    out["curtosi_storica"] = {str(n): curtosi_storica(p, n) for n in (126, 252)}
    return out


def run_verifica(start: str = "1994-01-01", step: int = 5, reps: int = 1000, cache_wf: str | None = None, cache_a1: str | None = None, log=print) -> dict:
    """Walk-forward delle 12 varianti + confronto con A1 + regola di adozione. Scrive data/percorsi_verifica.json e data/adozione.json, e le prove nel registro."""
    import json
    import os
    import pickle
    from . import store, verifica
    from .config import DATA
    from .features import closed_sp500
    from .modeleval import a1_preds
    p = closed_sp500()
    dates = p.index[p.index >= start][::step]
    wf = pickle.load(open(cache_wf, "rb")) if cache_wf and os.path.exists(cache_wf) else None
    if wf is None:
        log(f"[percorsi] walk-forward di {len(VARIANTI)} varianti su {len(dates)} date")
        wf = walk_forward(p, dates, store.load("vix"), store.load("vix3m"), log=log)
        if cache_wf:
            pickle.dump(wf, open(cache_wf, "wb"))
    a1 = pickle.load(open(cache_a1, "rb")) if cache_a1 and os.path.exists(cache_a1) else None
    if a1 is None:
        a1 = pd.DataFrame(a1_preds(p, dates))
        if cache_a1:
            pickle.dump(a1, open(cache_a1, "wb"))
    res = valuta_varianti(p, dates, wf, a1, step, reps, log)
    res.update({"data": pd.Timestamp.now().strftime("%Y-%m-%d"), "protocollo": verifica.protocollo_hash(), "inizio": start, "passo": step})
    ad = {"data": res["data"], "protocollo": res["protocollo"], "mostrata": res["mostrata"],
          "orizzonti": {hz: {"variante": o["scelta"]} for hz, o in res["orizzonti"].items()}}
    (DATA / "percorsi_verifica.json").write_text(json.dumps(res, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    (DATA / "adozione.json").write_text(json.dumps(ad, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        from . import ricerca
        righe = []
        for hz, o in res["orizzonti"].items():
            for v, r in o["varianti"].items():
                righe.append({"data": res["data"], "modello": "Percorsi " + v, "tipo": "protocollo1", "obiettivo": f"calo{o['soglia']}_{hz}", "periodo": f"{r['da']}..{r['a']}",
                              "variabili": "percorsi", "n": r["n"], "eventi": r["episodi"]["episodi"], "auc": round(r["auc"], 4) if r["auc"] == r["auc"] else "", "bss": round(r["bss"], 4),
                              "riferimento": "A1", "promosso": bool(r["adozione"]["passa"])})
        ricerca._registra(righe)
    except Exception as e:  # noqa: BLE001
        log("[percorsi] registro non aggiornato: " + str(e)[:80])
    return res


# ------------------------------------------------------------------ uso quotidiano: stima di oggi, adozione, pagina
import json as _json

from .config import DATA as _DATA

OGGI = _DATA / "percorsi_oggi.json"
ADOZIONE = _DATA / "adozione.json"
DEFAULT_MOSTRATA = "V1T1"


def adozione() -> dict:
    try:
        return _json.loads(ADOZIONE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def basi_storiche(p: pd.Series) -> dict:
    """Frequenze storiche (dal 1950) a ogni orizzonte: chiudere in negativo, perdita ≥10% da oggi, massimo drawdown ≥10%."""
    from .features import fwd_maxdd, fwd_ret
    q = p[p.index >= "1950-01-01"].dropna()
    out = {}
    for hz, n in ORIZZONTI.items():
        rt, dd = fwd_ret(q, n).dropna(), fwd_maxdd(q, n).dropna()
        m = mdd_futuro(q, n).dropna() if n <= 252 else None
        out[hz] = {"p_neg": float((rt < 0).mean()), "down10": float((dd <= -0.10).mean()), "mdd10": float((m <= -0.10).mean()) if m is not None else None,
                   "q10": float(rt.quantile(.10)), "q50": float(rt.quantile(.50)), "q90": float(rt.quantile(.90))}
    return out


def oggi(p: pd.Series, t, varianti: list[str] | None = None, n_paths: int = N_LIVE, scrivi: bool = True) -> dict:
    """Stima di oggi per le varianti richieste (default: quella da mostrare e quelle adottate). Seme fisso per data."""
    from . import store
    ad = adozione()
    mostrata = ad.get("mostrata") or DEFAULT_MOSTRATA
    adottate = {hz: o["variante"] for hz, o in (ad.get("orizzonti") or {}).items() if o.get("variante")}
    varianti = varianti or sorted({mostrata, *adottate.values()})
    t = pd.Timestamp(t)
    pp = p[p.index <= t]
    r = fhs.log_returns(pp[pp.index >= fhs.FIT_START])
    st = stato(r.values)
    vix, v3 = store.load("vix").dropna(), store.load("vix3m").dropna()
    vix, v3 = vix[vix.index <= t], v3[v3.index <= t]
    a = float(vix.iloc[-1]) if len(vix) and (t - vix.index[-1]).days < 7 else None
    b = float(v3.iloc[-1]) if len(v3) and (t - v3.index[-1]).days < 7 else None
    rap = None
    if len(v3) > 300:
        try:
            rd = rapporti_realizzata_implicita(r, store.load("vix"), store.load("vix3m"))
            rap = (_rapporto(rd, len(rd) - 1, "r21", 21), _rapporto(rd, len(rd) - 1, "rfwd", 63))
        except Exception:  # noqa: BLE001
            rap = None
    seed = int(t.strftime("%Y%m%d")) % (2 ** 31)
    out = {"asof": str(t.date()), "mostrata": mostrata, "adottate": adottate, "vix": a, "vix3m": b, "rapporti": rap, "varianti": {}, "basi": basi_storiche(pp)}
    for v in varianti:
        res = stima(r.values, v, seed, a, b, rap, n_paths=n_paths, st=st, extra=True)
        if res is None:
            continue
        res["_vol"] = curva_vol(st, varianza_iniziale(st, v, a, b, rap)[0])[::7]
        out["varianti"][v] = res
    try:   # variante in ombra V1T1_HAR (Patch 60a): varianza di partenza dal modello HAR con VIX; solo se ci sono apertura, massimo e minimo dell'indice
        from . import vrp
        va, dh = vrp.har_ultima(p, t)
        if va is not None and a is not None:
            s0 = vrp.s0_da_bersaglio(st, va)
            res = riassumi(simula(st, s0, "T1", n_paths, seed, None), None, True)
            res["_diag"] = {"persistenza": st["rho"], "emivita": st["emivita"], "vol_lungo": float(np.sqrt(st["s2_lr"] * 252)), "vol_partenza": float(np.sqrt(s0 * 252)),
                            "vol_garch_oggi": float(np.sqrt(st["s2_next"] * 252)), "n_percorsi": n_paths, "variante": "V1T1_HAR", "har_ultimo_dato": dh,
                            "var_har_annua": float(va), "vix_oggi": float(a)}
            res["_vol"] = curva_vol(st, s0)[::7]
            out["varianti"]["V1T1_HAR"] = res
    except Exception as e:  # noqa: BLE001
        print("[percorsi] V1T1_HAR non calcolata:", str(e)[:100])
    if scrivi:
        OGGI.write_text(_json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def applica_adozione(pred: dict, o: dict, mid: str) -> tuple[dict, str]:
    """Agli orizzonti dove una variante è stata ADOTTATA sulla verifica storica (data/adozione.json), le probabilità principali vengono dal motore di percorsi;
    A1 resta in p_a1. Dove nessuna variante ha superato la regola, A1 resta il numero principale."""
    from .model import VERDICT, level_of
    from .config import PRIMARY
    usati = []
    for hz, v in (o.get("adottate") or {}).items():
        res = (o.get("varianti") or {}).get(v)
        if not res or hz not in pred or hz not in res:
            continue
        r = pred[hz]
        r["p_a1"] = dict(r["p"])
        r["p"] = {thr: float(res[hz]["down"][thr]) for thr in r["p"]}
        r["motore"], r["adottato"], r["variante"] = f"Percorsi {v}", True, v
        prim = PRIMARY[hz]
        r["ratio"] = r["p"][prim] / r["base"][prim] if r["base"][prim] > 0 else 1.0
        r["level"] = level_of(r["ratio"])
        r["verdict"] = VERDICT[r["level"]]
        usati.append(hz)
    return pred, (f"{mid}+PERC({','.join(usati)})" if usati else mid)


def _pc(x: float, dec: int = 0) -> str:
    return (f"{x * 100:.{dec}f}%").replace(".", ",")


def html() -> str:
    """Sezione «Scenari a 1 settimana - 1 anno»."""
    try:
        o = _json.loads(OGGI.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    v = o.get("mostrata")
    res = (o.get("varianti") or {}).get(v)
    if not res:
        return ""
    d = res["_diag"]
    basi = o.get("basi", {})
    ad = o.get("adottate", {})
    nomi = {"1s": "1 settimana", "10g": "10 giorni", "1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi", "12m": "1 anno"}
    righe = ""
    for hz in ("1s", "1m", "3m", "6m", "12m"):
        x, b = res[hz], basi.get(hz, {})
        agg = ""
        for k, lab in (("down", "Perdita da oggi"), ("mdd", "Massimo drawdown")):
            se = x["se"][k]["10"] if "10" in x["se"][k] else x["se"][k][10]
            v10 = x[k]["10"] if "10" in x[k] else x[k][10]
            agg += f"<td>{_pc(v10)}{'<br><span class=mu>±' + _pc(se, 1) + '</span>' if se > 0.005 else ''}</td>"
        righe += (f"<tr><td><b>{nomi[hz]}</b></td><td>{_pc(x['ret']['q10'])} / {_pc(x['ret']['q50'])} / {_pc(x['ret']['q90'])}</td>"
                  f"<td>{_pc(x['p_neg'])}<br><span class=mu>storico {_pc(b.get('p_neg', 0))}</span></td>{agg}"
                  f"<td><span class=mu>{_pc(b.get('down10', 0))} / {_pc(b['mdd10']) if b.get('mdd10') is not None else 'n.d.'}</span></td></tr>")
    etich = ("<span class='badge ok'>Adottato sulla verifica storica, in conferma dal vivo: " + ", ".join(f"{nomi[h]} ({x})" for h, x in ad.items()) + "</span> "
             if ad else "<span class='badge warn'>Sperimentale: non ha superato la regola di adozione, il numero principale resta A1</span> ")
    sp = ""
    if "_vol" in res:
        vals = res["_vol"]
        mx, mn = max(vals), min(vals)
        pts = " ".join(f"{i * 100 / (len(vals) - 1):.1f},{38 - (x - mn) / max(mx - mn, 1e-9) * 34:.1f}" for i, x in enumerate(vals))
        sp = (f"<svg viewBox='0 0 100 42' width='100%' height='60' role='img' aria-label='Volatilità attesa nei prossimi 12 mesi'><polyline fill='none' stroke='var(--ac)' stroke-width='1.5' points='{pts}'/></svg>"
              f"<div class='mu'>Volatilità annua attesa: oggi {vals[0]:.0f}% → fra 12 mesi {vals[-1]:.0f}% (di lungo periodo {d['vol_lungo']:.0f}%).</div>")
    return (f"<p>Un solo motore di simulazione ({_h(v)}, {d['n_percorsi']:,} percorsi) produce tutti i numeri qui sotto: sono coerenti per costruzione tra orizzonti e soglie. ".replace(",", ".") + etich + "</p>"
            "<div class='scroll'><table><tr><th>Orizzonte</th><th>Caso brutto / tipico / buono</th><th>Chiudere in negativo</th><th>Perdita ≥10% da oggi</th><th>Drawdown ≥10%</th><th>Storico (perdita / drawdown)</th></tr>"
            + righe + "</table></div>"
            f"<p class='mu'>Persistenza della volatilità {str(round(d['persistenza'], 3)).replace('.', ',')}: uno shock dimezza in circa {d['emivita']:.0f} sedute. «Caso brutto/buono» = 10° e 90° percentile. "
            "Il drawdown è il calo dal massimo raggiunto dentro il periodo; la perdita da oggi è il calo rispetto al prezzo di oggi. Oltre qualche mese la volatilità torna verso il lungo periodo: le stime a 6-12 mesi sono le meno affidabili.</p>" + sp)


def _h(x) -> str:
    import html as h
    return h.escape(str(x))


NOMI_COND = {"0_stesse_date_di_A1": "non copre le stesse date di A1", "1_brier_intero": "Brier non meglio di A1 (intervallo include lo zero)",
             "1_brier_non_sovrapposti": "non meglio di A1 sulle finestre non sovrapposte", "1_holm": "differenza non significativa dopo Holm",
             "2_bss_1994_2012": "BSS ≤ 0 nel 1994-2012", "2_bss_2013_oggi": "BSS ≤ 0 dal 2013", "3_pendenza": "calibrazione fuori da 0,8-1,2",
             "4_copertura": "copertura 10-90 fuori da 77-83%", "5_pbo": "PBO ≥ 0,5"}


def html_verifica() -> str:
    """«Quanto fidarsi»: esito della regola di adozione storica per le 12 varianti (data/percorsi_verifica.json)."""
    try:
        res = _json.loads((_DATA / "percorsi_verifica.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    f = lambda x, d=3: "n.d." if x is None or x != x else f"{x:+.{d}f}".replace(".", ",")
    nomi = {"10g": "10 giorni", "1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi"}
    out = ("<p>Il motore di percorsi ha 12 varianti scritte prima del test (PROTOCOLLO_VERIFICA.md). Una sostituisce A1 a un orizzonte solo se supera <b>tutte</b> le condizioni: Brier meglio di A1 con intervallo tutto a favore "
           "(campione intero e finestre non sovrapposte, con Holm), BSS positivo in 1994-2012 e dal 2013, calibrazione 0,8-1,2, copertura della fascia 10-90 tra 77% e 83%, PBO sotto 0,5.</p>")
    for hz, o in res["orizzonti"].items():
        righe = ""
        for v, r in sorted(o["varianti"].items(), key=lambda kv: kv[1]["crps"]):
            ad = r["adozione"]
            manca = [NOMI_COND.get(k, k) for k, ok in ad["condizioni"].items() if not ok]
            vr = r["vs_ref"]["intero"]
            righe += (f"<tr><td>{v}</td><td>{f(vr['diff'], 4)} [{f(vr['lo'], 4)}; {f(vr['hi'], 4)}]</td><td>{f(r.get('bss_1994_2012'), 2)} / {f(r.get('bss_2013_oggi'), 2)}</td>"
                      f"<td>{str(round(r['pendenza'], 2)).replace('.', ',')}</td><td>{_pc(r['copertura_10_90'])}</td><td>{str(round(r['crps'], 4)).replace('.', ',')}</td>"
                      f"<td>{'<b>passa</b>' if ad['passa'] else _h('; '.join(manca[:2]))}</td></tr>")
        sc = o["scelta"]
        out += (f"<h4 style='margin:14px 0 4px'>{nomi[hz]}: calo ≥{o['soglia']}% — {'adottato ' + sc if sc else 'nessuna variante passa, resta A1'} (PBO {str(round(o['pbo']['pbo'], 2)).replace('.', ',')})</h4>"
                f"<div class='scroll'><table><tr><th>Variante</th><th>Differenza di Brier da A1 [90%]</th><th>BSS 94-12 / 13-oggi</th><th>Pend.</th><th>Copertura 10-90</th><th>CRPS</th><th>Esito</th></tr>{righe}</table></div>")
    return out + "<p class='mu'>Differenza di Brier negativa = meglio di A1. Le varianti V2 usano il VIX a 3 mesi, disponibile solo dal 2006: non coprono le stesse date di A1 e quindi non possono essere adottate. Le prove sono nel registro.</p>"
