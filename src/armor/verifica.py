"""Verifica rigorosa e unica per tutti i modelli (PIANO ARMOR 3, Fase 1b). Solo numpy/pandas: nessuna libreria esterna.

Principi: stesse date e stessi esiti per tutti i modelli; frequenza storica «normale» nota a ogni data; finestre sovrapposte trattate
con bootstrap stazionario, sottocampioni non sovrapposti ed episodi; confronti con test di Diebold-Mariano (errori HAC) e correzione di Holm;
probabilità di sovra-adattamento (PBO, metodo CSCV). Per le distribuzioni: copertura delle fasce e CRPS; per la volatilità: QLIKE.
Le regole di adozione sono in PROTOCOLLO_VERIFICA.md e in `regola_adozione()` (stesse soglie nei due posti)."""
from itertools import combinations
from math import erf, sqrt

import numpy as np
import pandas as pd

REPS = 2000
SEME = 20261108

# soglie della regola di adozione storica (PROTOCOLLO_VERIFICA.md §4): non cambiarle dopo aver visto i risultati
SOGLIE = {"ic": 0.90, "bss_periodi": ((1994, 2012), (2013, 2100)), "pend": (0.8, 1.2), "copertura": (0.77, 0.83), "pbo_max": 0.5, "holm_alpha": 0.10}


# ------------------------------------------------------------------ metriche di base
def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def bss(p, y, base) -> float:
    b = brier(base, y)
    return float(1 - brier(p, y) / b) if b > 0 else float("nan")


def logloss(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def auc(score, y) -> float:
    score, y = np.asarray(score, float), np.asarray(y, float)
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    if n1 < 5 or n0 < 5:
        return float("nan")
    r = pd.Series(score).rank().values
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def calib_curve(p, y, bins: int = 10) -> pd.DataFrame:
    """Curva di affidabilità a `bins` classi di uguale numerosità."""
    d = pd.DataFrame({"p": np.asarray(p, float), "y": np.asarray(y, float)})
    try:
        q = pd.qcut(d.p, bins, duplicates="drop")
    except ValueError:
        return pd.DataFrame(columns=["prev", "real", "n"])
    g = d.groupby(q, observed=True).agg(prev=("p", "mean"), real=("y", "mean"), n=("y", "size")).reset_index(drop=True)
    return g


def ece(p, y, bins: int = 10) -> float:
    """Errore di calibrazione medio (pesato sul numero di casi per classe)."""
    g = calib_curve(p, y, bins)
    return float((g.n * (g.prev - g.real).abs()).sum() / g.n.sum()) if len(g) else float("nan")


def calib_slope(p, y, iters: int = 50) -> float:
    """Pendenza di calibrazione: coefficiente b della regressione logistica y ~ a + b·logit(p). 1 = calibrato; <1 = probabilità troppo estreme."""
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    if y.sum() < 5 or y.sum() > len(y) - 5 or np.std(p) < 1e-9:
        return float("nan")
    x = np.log(p / (1 - p))
    X = np.column_stack([np.ones_like(x), x])
    w = np.array([0.0, 1.0])
    for _ in range(iters):
        z = np.clip(X @ w, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        W = mu * (1 - mu) + 1e-9
        H = X.T @ (X * W[:, None]) + 1e-8 * np.eye(2)
        step = np.linalg.solve(H, X.T @ (y - mu))
        w = w + step
        if np.abs(step).max() < 1e-8:
            break
    return float(w[1])


# ------------------------------------------------------------------ finestre sovrapposte
def blocco_medio(h: int, step: int) -> int:
    """Lunghezza media del blocco, in numero di osservazioni: un orizzonte h con una data ogni `step` sedute."""
    return max(int(np.ceil(h / step)), 1)


def indici_stazionari(n: int, mean_block: float, reps: int, rng) -> np.ndarray:
    """Bootstrap stazionario di Politis-Romano: matrice (reps, n) di indici."""
    pr = 1.0 / max(mean_block, 1.0)
    idx = np.empty((reps, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, reps)
    nuovo = rng.random((reps, n)) < pr
    inizio = rng.integers(0, n, (reps, n))
    for t in range(1, n):
        idx[:, t] = np.where(nuovo[:, t], inizio[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def boot_diff(loss_a, loss_b, mean_block: float, reps: int = REPS, seed: int = SEME, level: float = 0.90) -> dict:
    """Differenza media di perdita (a − b) con intervallo bootstrap stazionario. Negativa = a meglio di b."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    n = len(d)
    if n < 30:
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": n}
    idx = indici_stazionari(n, mean_block, reps, np.random.default_rng(seed))
    m = d[idx].mean(axis=1)
    lo, hi = np.quantile(m, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {"diff": float(d.mean()), "lo": float(lo), "hi": float(hi), "n": n}


def boot_bss(err_m, err_b, mean_block: float, reps: int = REPS, seed: int = SEME, level: float = 0.90) -> dict:
    err_m, err_b = np.asarray(err_m, float), np.asarray(err_b, float)
    n = len(err_m)
    if n < 30:
        return {"bss": float("nan"), "lo": float("nan"), "hi": float("nan")}
    idx = indici_stazionari(n, mean_block, reps, np.random.default_rng(seed))
    v = 1 - err_m[idx].sum(axis=1) / np.maximum(err_b[idx].sum(axis=1), 1e-12)
    lo, hi = np.quantile(v, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {"bss": float(1 - err_m.sum() / max(err_b.sum(), 1e-12)), "lo": float(lo), "hi": float(hi)}


def sottocampioni(pos, h: int, max_sfasamenti: int | None = None) -> list[np.ndarray]:
    """Sottocampioni non sovrapposti: date con almeno h sedute di distanza (scelta golosa), uno per ogni sfasamento iniziale possibile.
    `pos` = numero di seduta di ogni data (crescente). Restituisce liste di indici posizionali."""
    pos = np.asarray(pos)
    out = []
    n_start = len(pos) if max_sfasamenti is None else min(len(pos), max_sfasamenti)
    visti = set()
    for s in range(n_start):
        if pos[s] - pos[0] >= h:
            break
        sel, last = [], -10 ** 12
        for i in range(s, len(pos)):
            if pos[i] - last >= h:
                sel.append(i)
                last = pos[i]
        key = tuple(sel[:6])
        if key in visti:
            continue
        visti.add(key)
        out.append(np.array(sel))
    return out


def episodi(pos, y, h: int) -> dict:
    """Numero di episodi: giorni con evento separati da meno di h sedute appartengono allo stesso episodio."""
    pos, y = np.asarray(pos), np.asarray(y)
    ev = pos[y == 1]
    if len(ev) == 0:
        return {"giorni": 0, "episodi": 0}
    return {"giorni": int(len(ev)), "episodi": int(1 + (np.diff(ev) >= h).sum())}


def dm_test(loss_a, loss_b, lag: int) -> dict:
    """Diebold-Mariano con varianza HAC (Bartlett, ritardo `lag`). stat<0: a ha perdita minore. p a due code (normale)."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    n = len(d)
    if n < 30 or np.allclose(d, d[0]):
        return {"stat": float("nan"), "p": float("nan")}
    dm = d.mean()
    e = d - dm
    v = float(e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        v += 2 * (1 - k / (lag + 1)) * float(e[k:] @ e[:-k]) / n
    v = max(v, 1e-18)
    st = dm / sqrt(v / n)
    p = 2 * (1 - 0.5 * (1 + erf(abs(st) / sqrt(2))))
    return {"stat": float(st), "p": float(p)}


def holm(pvals: dict) -> dict:
    """Correzione di Holm-Bonferroni. Restituisce i p aggiustati."""
    items = sorted(((k, v) for k, v in pvals.items() if v == v), key=lambda kv: kv[1])
    m = len(items)
    out, run = {k: float("nan") for k in pvals}, 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


# ------------------------------------------------------------------ PBO (CSCV)
def pbo_cscv(perf: np.ndarray, S: int = 16, max_comb: int = 2000, seed: int = SEME) -> dict:
    """Probabilità di sovra-adattamento (Bailey et al.): `perf` = matrice (T blocchi di tempo × N configurazioni), più alto = meglio.
    Si divide il tempo in S blocchi, si prende ogni metà come «in campione» e l'altra come «fuori campione»: PBO = frazione di casi in cui
    la configurazione migliore in campione sta sotto la mediana fuori campione."""
    perf = np.asarray(perf, float)
    T, N = perf.shape
    if N < 2 or T < 4:
        return {"pbo": float("nan"), "n_comb": 0}
    S = min(S, T - (T % 2))
    blocchi = np.array_split(np.arange(T), S)
    comb = list(combinations(range(S), S // 2))
    if len(comb) > max_comb:
        rng = np.random.default_rng(seed)
        comb = [comb[i] for i in rng.choice(len(comb), max_comb, replace=False)]
    logit = []
    for c in comb:
        a = np.concatenate([blocchi[i] for i in c])
        b = np.concatenate([blocchi[i] for i in range(S) if i not in c])
        best = int(np.argmax(perf[a].mean(axis=0)))
        oos = perf[b].mean(axis=0)
        rank = (oos < oos[best]).sum() + 0.5 * ((oos == oos[best]).sum() - 1)
        w = (rank + 1) / (N + 1)
        logit.append(np.log(w / (1 - w)))
    logit = np.array(logit)
    return {"pbo": float((logit <= 0).mean()), "n_comb": len(comb)}


# ------------------------------------------------------------------ distribuzioni e volatilità
def copertura(lo, hi, y) -> float:
    lo, hi, y = np.asarray(lo, float), np.asarray(hi, float), np.asarray(y, float)
    return float(((y >= lo) & (y <= hi)).mean())


def crps_quantili(livelli, quantili, y) -> float:
    """CRPS approssimato dai quantili previsti: 2 × media della perdita «pinball» sui livelli dati. `quantili` ha forma (n, k)."""
    q = np.asarray(quantili, float)
    y = np.asarray(y, float)[:, None]
    t = np.asarray(livelli, float)[None, :]
    u = y - q
    return float(2 * np.mean(np.maximum(t * u, (t - 1) * u)))


def qlike(var_prevista, var_realizzata) -> float:
    """QLIKE per previsioni di varianza (più basso = meglio, robusto al rumore della varianza realizzata)."""
    f, r = np.maximum(np.asarray(var_prevista, float), 1e-12), np.maximum(np.asarray(var_realizzata, float), 1e-12)
    return float(np.mean(r / f - np.log(r / f) - 1))


# ------------------------------------------------------------------ confronto completo
def prepara(dates, pos, y, base, preds: dict) -> pd.DataFrame:
    """Tabella unica per un bersaglio: date comuni a tutti i modelli. `preds` = {nome: serie p indicizzata per data}."""
    f = lambda x: x if isinstance(x, pd.Series) else pd.Series(np.asarray(x), index=dates)
    d = pd.DataFrame({"pos": f(pos), "y": f(y), "base": f(base)})
    for m, s in preds.items():
        d[m] = s if isinstance(s, pd.Series) else pd.Series(np.asarray(s), index=dates)
    return d.dropna().sort_index()


def valuta_modello(d: pd.DataFrame, modello: str, h: int, step: int, ref: str = "A1", reps: int = REPS) -> dict:
    """Tutte le metriche di un modello su `d` (date comuni). Se modello != ref include il confronto con ref."""
    y, p, b = d["y"].values, d[modello].values, d["base"].values
    L = blocco_medio(h, step)
    e_m, e_b = (p - y) ** 2, (b - y) ** 2
    out = {"modello": modello, "n": int(len(d)), "freq": float(y.mean()), "brier": float(e_m.mean()), "bss": bss(p, y, b), "logloss": logloss(p, y),
           "auc": auc(p, y), "ece": ece(p, y), "pendenza": calib_slope(p, y), "episodi": episodi(d["pos"].values, y, h)}
    out["bss_ci"] = boot_bss(e_m, e_b, L, reps)
    anni = d.index.year
    for (a, z) in SOGLIE["bss_periodi"]:
        m = (anni >= a) & (anni <= z)
        out[f"bss_{a}_{z if z < 2100 else 'oggi'}"] = bss(p[m], y[m], b[m]) if m.sum() >= 30 else float("nan")
    subs = sottocampioni(d["pos"].values, h)
    out["non_sovrapposti"] = {"sfasamenti": len(subs),
                              "n_medio": float(np.mean([len(s) for s in subs])) if subs else 0.0,
                              "bss_medio": float(np.nanmean([bss(p[s], y[s], b[s]) for s in subs])) if subs else float("nan"),
                              "bss_dev": float(np.nanstd([bss(p[s], y[s], b[s]) for s in subs])) if subs else float("nan")}
    if modello != ref and ref in d:
        e_r = (d[ref].values - y) ** 2
        out["vs_ref"] = {"ref": ref, "intero": boot_diff(e_m, e_r, L, reps), "dm": dm_test(e_m, e_r, L - 1)}
        ups, dif = [], []
        for s in subs:
            r_ = boot_diff(e_m[s], e_r[s], 1.0, min(reps, 1000))   # non sovrapposti: bootstrap quasi indipendente
            ups.append(r_["hi"])
            dif.append(r_["diff"])
        out["vs_ref"]["non_sovrapposti"] = {"diff_medio": float(np.nanmean(dif)) if dif else float("nan"),
                                            "hi_mediano": float(np.nanmedian(ups)) if ups else float("nan")}
    return out


def regola_adozione(r: dict, copertura_10_90: float | None, pbo: float | None, p_holm: float | None) -> dict:
    """Regola di adozione storica (PROTOCOLLO_VERIFICA.md §4). `r` = valuta_modello(...) della variante contro A1.
    Tutte le condizioni devono essere vere; una condizione non valutabile (None/NaN) conta come NON superata."""
    ok = lambda x: x is not None and x == x
    v = r.get("vs_ref", {})
    c = {}
    c["1_brier_intero"] = bool(ok(v.get("intero", {}).get("hi")) and v["intero"]["hi"] < 0)
    c["1_brier_non_sovrapposti"] = bool(ok(v.get("non_sovrapposti", {}).get("hi_mediano")) and v["non_sovrapposti"]["hi_mediano"] < 0 and v["non_sovrapposti"]["diff_medio"] < 0)
    c["1_holm"] = bool(ok(p_holm) and p_holm < SOGLIE["holm_alpha"])
    c["2_bss_1994_2012"] = bool(ok(r.get("bss_1994_2012")) and r["bss_1994_2012"] > 0)
    c["2_bss_2013_oggi"] = bool(ok(r.get("bss_2013_oggi")) and r["bss_2013_oggi"] > 0)
    c["3_pendenza"] = bool(ok(r.get("pendenza")) and SOGLIE["pend"][0] <= r["pendenza"] <= SOGLIE["pend"][1])
    c["4_copertura"] = bool(ok(copertura_10_90) and SOGLIE["copertura"][0] <= copertura_10_90 <= SOGLIE["copertura"][1])
    c["5_pbo"] = bool(ok(pbo) and pbo < SOGLIE["pbo_max"])
    return {"passa": bool(all(c.values())), "condizioni": c}


# ------------------------------------------------------------------ protocollo: impronta
def protocollo_hash() -> str:
    from .config import ROOT
    import hashlib
    f = ROOT / "PROTOCOLLO_VERIFICA.md"
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:24] if f.exists() else ""


def registra_protocollo() -> str:
    """Scrive (una volta per versione del file) data e impronta del protocollo in data/protocollo_log.csv. Segnala se l'impronta cambia."""
    from datetime import datetime, timezone
    from .config import DATA
    h = protocollo_hash()
    if not h:
        return ""
    f = DATA / "protocollo_log.csv"
    righe = f.read_text(encoding="utf-8").splitlines() if f.exists() else ["data_utc,impronta"]
    if any(r.endswith("," + h) for r in righe[1:]):
        return h
    righe.append(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},{h}")
    f.write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"[protocollo] impronta registrata: {h}" + (" (ATTENZIONE: il protocollo è cambiato rispetto alla prima versione)" if len(righe) > 2 else ""), flush=True)
    return h


# ------------------------------------------------------------------ verifica storica dei modelli esistenti (Fase 1c)
def _logit_preds(p: pd.Series, dates, feats: list[str], refit_every: int = 63) -> list[dict]:
    from .model import Engine
    eng = Engine(p, feats)
    from .config import HORIZONS, TARGETS
    rows, fitted, last = [], None, -10 ** 9
    for t in dates:
        if t not in eng.F.index:
            continue
        i = p.index.get_loc(t)
        if fitted is None or i - last >= refit_every:
            fitted, last = eng.fit(t), i
        pr = eng.predict(fitted, t)
        for hz in HORIZONS:
            if hz in pr:
                for thr in TARGETS[hz]:
                    rows.append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": pr[hz]["p"][thr]})
    return rows


def _indice_preds(p: pd.Series, dates, refit_every: int = 63, min_anni: int = 5) -> list[dict]:
    """Indice Armor trasformato in probabilità: logistica a una variabile, stimata solo su esiti maturati (walk-forward)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from . import store
    from .config import HORIZONS, MIN_EVENTS, TARGETS
    from .features import fwd_maxdd
    ai = store.load("armor_index").dropna()
    ai = ai[ai.index.isin(p.index)]
    if ai.empty:
        return []
    dd = {hz: fwd_maxdd(p, n) for hz, n in HORIZONS.items()}
    rows, mods, last = [], {}, -10 ** 9
    for t in dates:
        if t not in ai.index:
            continue
        i = p.index.get_loc(t)
        if i - last >= refit_every or not mods:
            mods = {}
            for hz, n in HORIZONS.items():
                if i - n < 0:
                    continue
                cut = p.index[i - n]
                X = ai[ai.index <= cut]
                if len(X) < 252 * min_anni:
                    continue
                for thr in TARGETS[hz]:
                    y = (dd[hz].reindex(X.index) <= -thr / 100)
                    ok = dd[hz].reindex(X.index).notna()
                    if y[ok].sum() < MIN_EVENTS:
                        continue
                    m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500))
                    m.fit(X[ok].values.reshape(-1, 1), y[ok].astype(int).values)
                    mods[(hz, thr)] = m
            last = i
        for (hz, thr), m in mods.items():
            rows.append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": float(m.predict_proba([[ai.loc[t]]])[0, 1])})
    return rows


def run_storica(start: str = "1994-01-01", step: int = 5, sims: int = 2000, cache: str | None = None, log=print, reps: int = REPS) -> dict:
    """Rifà la verifica di A1, FHS, FHS+VIX, Indice Armor e «Solo prezzi» con gli strumenti di questo modulo. Salva data/verifica_storica.json."""
    import json
    import os
    import pickle
    from . import fhs, store
    from .config import BASELINE_FEATURES, DATA, HORIZONS, TARGETS
    from .features import closed_sp500
    from .modeleval import a1_preds, outcome, purged_base
    p = closed_sp500()
    dates = p.index[p.index >= start][::step]
    preds = pickle.load(open(cache, "rb")) if cache and os.path.exists(cache) else {}
    if not preds:
        vix = store.load("vix")
        log(f"[verifica] A1 su {len(dates)} date"); preds["A1"] = pd.DataFrame(a1_preds(p, dates))
        log("[verifica] Solo prezzi"); preds["Solo prezzi"] = pd.DataFrame(_logit_preds(p, dates, BASELINE_FEATURES))
        log("[verifica] FHS"); preds["FHS"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims))
        if len(vix) > 1000:
            log("[verifica] FHS+VIX"); preds["FHS+VIX"] = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims, vix=vix, w=0.5))
        log("[verifica] Indice Armor"); preds["Indice Armor"] = pd.DataFrame(_indice_preds(p, dates))
        if cache:
            pickle.dump(preds, open(cache, "wb"))
    pos_all = pd.Series(np.arange(len(p)), index=p.index)
    res = {"data": pd.Timestamp.now().strftime("%Y-%m-%d"), "inizio": start, "passo": step, "repliche": reps, "protocollo": protocollo_hash(), "bersagli": []}
    for hz, h in HORIZONS.items():
        for thr in TARGETS[hz]:
            y = outcome(p, dates, hz, "down", thr)
            base = purged_base(p, dates, hz, "down", thr)
            sel = {}
            for m, df in preds.items():
                if df.empty:
                    continue
                g = df[(df.hz == hz) & (df.kind == "down") & (df.thr == thr)].set_index("date")["p"].dropna()
                if len(g):
                    sel[m] = g
            if "A1" not in sel:
                continue
            rows, pv = [], {}
            for m in sel:
                if m == "A1":
                    continue
                d = prepara(dates, pos_all.reindex(dates), y, base, {"A1": sel["A1"], m: sel[m]})
                if len(d) < 60:
                    continue
                r = valuta_modello(d, m, h, step, "A1", reps)
                r["da"], r["a"] = str(d.index[0].date()), str(d.index[-1].date())
                rows.append(r)
                pv[m] = r["vs_ref"]["dm"]["p"]
            d1 = prepara(dates, pos_all.reindex(dates), y, base, {"A1": sel["A1"]})
            ra = valuta_modello(d1, "A1", h, step, "A1", reps)
            ra["da"], ra["a"] = str(d1.index[0].date()), str(d1.index[-1].date())
            adj = holm(pv)
            for r in rows:
                r["vs_ref"]["dm"]["p_holm"] = adj.get(r["modello"])
            conf = [m for m in ("A1", "Solo prezzi", "FHS", "FHS+VIX") if m in sel]
            pbo = {"pbo": float("nan"), "n_comb": 0}
            if len(conf) >= 3:
                dc = prepara(dates, pos_all.reindex(dates), y, base, {m: sel[m] for m in conf})
                T = len(dc)
                blocchi = np.array_split(np.arange(T), 32)
                perf = np.array([[-brier(dc[m].values[b], dc["y"].values[b]) for m in conf] for b in blocchi])
                pbo = pbo_cscv(perf, 16)
            res["bersagli"].append({"hz": hz, "orizzonte_sedute": h, "soglia": thr, "A1": ra, "sfidanti": rows, "pbo": pbo, "pbo_modelli": conf})
    (DATA / "verifica_storica.json").write_text(json.dumps(res, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    try:
        from . import ricerca
        righe = []
        for b in res["bersagli"]:
            for r in [b["A1"]] + b["sfidanti"]:
                righe.append({"data": res["data"], "modello": r["modello"], "tipo": "verifica1994", "obiettivo": f"calo{b['soglia']}_{b['hz']}", "periodo": f"{r['da']}..{r['a']}",
                              "variabili": "walk-forward", "n": r["n"], "eventi": r["episodi"]["episodi"], "auc": round(r["auc"], 4) if r["auc"] == r["auc"] else "", "bss": round(r["bss"], 4)})
        ricerca._registra(righe)
    except Exception as e:  # noqa: BLE001
        log("[verifica] registro non aggiornato: " + str(e)[:80])
    return res


def tabella_testo(res: dict) -> str:
    f = lambda x: "n.d." if x is None or x != x else f"{x:+.3f}"
    out = []
    for b in res["bersagli"]:
        out.append(f"== calo ≥{b['soglia']}% in {b['orizzonte_sedute']} sedute (PBO {f(b['pbo']['pbo'])}) ==")
        for r in [b["A1"]] + b["sfidanti"]:
            ci = r["bss_ci"]
            v = r.get("vs_ref", {})
            dm = f"ΔBrier {f(v['intero']['diff'])} [{f(v['intero']['lo'])},{f(v['intero']['hi'])}] DM p {v['dm']['p']:.3f} Holm {f(v['dm'].get('p_holm'))}" if v else "riferimento"
            out.append(f"{r['modello']:<14} n={r['n']:<5} episodi={r['episodi']['episodi']:<3} Brier {r['brier']:.4f} BSS {f(r['bss'])} [{f(ci['lo'])},{f(ci['hi'])}] AUC {r['auc']:.3f} "
                       f"pend {f(r['pendenza'])} ECE {r['ece']:.3f} | {dm}")
    return "\n".join(out)


def html() -> str:
    """Tabella di «Quanto fidarsi»: verifica storica con intervalli di confidenza (data/verifica_storica.json)."""
    import html as _h
    import json
    from .config import DATA, HZ_LABEL
    try:
        res = json.loads((DATA / "verifica_storica.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    f = lambda x, d=3: "n.d." if x is None or x != x else f"{x:+.{d}f}".replace(".", ",")
    out = ("<p>Verifica rifatta con uno strumento unico: stesse date e stessi esiti per tutti i modelli, dal " + _h.escape(res["inizio"][:4]) +
           ", sempre con i soli dati noti a ogni data. Le finestre si sovrappongono, quindi gli intervalli sono calcolati con il bootstrap a blocchi (90%) e si conta anche il numero di <b>episodi</b> "
           "(crisi distinte), che è molto più piccolo del numero di giorni. <b>Se l'intervallo include lo zero, il modello non si distingue dalla semplice frequenza storica.</b></p>")
    for b in res["bersagli"]:
        rows = ""
        for r in [b["A1"]] + b["sfidanti"]:
            ci = r["bss_ci"]
            v = r.get("vs_ref")
            diff = "riferimento" if not v else f"{f(v['intero']['diff'], 4)} [{f(v['intero']['lo'], 4)}; {f(v['intero']['hi'], 4)}] · p {f(v['dm'].get('p_holm'), 2).replace('+', '')}"
            rows += (f"<tr><td>{_h.escape(r['modello'])}</td><td>{r['episodi']['episodi']}</td><td>{f(r['bss'])} [{f(ci['lo'], 2)}; {f(ci['hi'], 2)}]</td>"
                     f"<td>{str(round(r['auc'], 2)).replace('.', ',')}</td><td>{f(r['pendenza'], 2).replace('+', '')}</td><td>{diff}</td></tr>")
        out += (f"<h4 style='margin:14px 0 4px'>Calo di almeno {b['soglia']}% in {HZ_LABEL[b['hz']]}</h4><div class='scroll'><table><tr><th>Modello</th><th>Episodi</th><th>BSS [90%]</th><th>AUC</th>"
                f"<th>Pendenza</th><th>Differenza di Brier da A1 [90%] · p (Holm)</th></tr>{rows}</table></div>")
    return out + ("<p class='mu'>BSS: quanto la probabilità è migliore della frequenza storica (0 = uguale). Pendenza: 1 = probabilità calibrate, sotto 1 = troppo estreme. "
                  "Differenza di Brier negativa = meglio di A1; conta solo se l'intervallo sta tutto sotto lo zero. «p (Holm)» tiene conto dei confronti multipli. "
                  "Le regole per cambiare il numero principale sono scritte in PROTOCOLLO_VERIFICA.md.</p>")
