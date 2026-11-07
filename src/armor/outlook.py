"""Prospettive dettagliate: probabilita' di cali e risalite a tante soglie, giorni passati simili,
e lettura indicatore per indicatore (che cosa e' successo in passato quando valeva come oggi)."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import store
from .config import FEATURES, HORIZONS, MIN_EVENTS
from .features import fwd_maxdd, fwd_maxup, fwd_ret, price_features

THRESHOLDS = [1, 3, 5, 8, 10, 15, 20]
K_NEIGHBORS = 150
FEAT_IT = {"rv21": "volatilità recente", "rv63": "volatilità a 3 mesi", "rv_ratio": "volatilità rispetto al normale",
           "dd252": "distanza dai massimi", "ma200": "prezzo vs media 200 giorni", "ma50_200": "media 50 vs 200 giorni",
           "mom63": "andamento a 3 mesi", "worst_day": "peggior giornata del mese"}


def _targets(p: pd.Series):
    dd = {h: fwd_maxdd(p, n) for h, n in HORIZONS.items()}
    up = {h: fwd_maxup(p, n) for h, n in HORIZONS.items()}
    rt = {h: fwd_ret(p, n) for h, n in HORIZONS.items()}
    return dd, up, rt


def probability_matrix(p: pd.Series, date: pd.Timestamp | None = None) -> dict:
    """Per ogni orizzonte e soglia: probabilita' del modello (se i casi storici bastano), frequenza normale,
    frequenza nei giorni piu' simili a oggi. Usa solo esiti gia' noti alla data."""
    p = p.dropna()
    F = price_features(p)[FEATURES].dropna()
    date = date or F.index[-1]
    x_now = F.loc[[date]]
    dd, up, rt = _targets(p)
    mu, sd = F.mean(), F.std().replace(0, 1)
    Z = (F - mu) / sd
    out = {}
    ipos = p.index.get_loc(date)
    for hz, n in HORIZONS.items():
        known = F.index[F.index <= p.index[max(ipos - n, 0)]] if ipos - n >= 0 else F.index[:0]
        known = known[known < date]
        X = F.loc[known]
        zr = Z.loc[known]
        dist = np.sqrt(((zr.values - Z.loc[date].values) ** 2).sum(axis=1))
        order = np.argsort(dist)
        nn_idx = known[order[:K_NEIGHBORS]]
        res = {"down": {}, "up": {}, "n_train": int(len(X)), "n_analog": int(len(nn_idx))}
        for kind, ser in (("down", dd[hz]), ("up", up[hz])):
            for thr in THRESHOLDS:
                if kind == "down":
                    y = (ser.loc[known] <= -thr / 100)
                    ya = (ser.loc[nn_idx] <= -thr / 100)
                else:
                    y = (ser.loc[known] >= thr / 100)
                    ya = (ser.loc[nn_idx] >= thr / 100)
                base, an = float(y.mean()), float(ya.mean())
                model_p, source = an, "analoghi"
                if y.sum() >= MIN_EVENTS and (~y).sum() >= MIN_EVENTS:
                    try:
                        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))
                        m.fit(X.values, y.astype(int).values)
                        model_p, source = float(m.predict_proba(x_now.values)[0, 1]), "modello"
                    except Exception:  # noqa: BLE001
                        pass
                res[kind][thr] = {"p": model_p, "base": base, "analog": an, "source": source,
                                  "events": int(y.sum())}
        r = rt[hz].loc[nn_idx]
        res["ret_analog"] = {"q10": float(r.quantile(.1)), "q50": float(r.quantile(.5)), "q90": float(r.quantile(.9)),
                             "pos": float((r > 0).mean())}
        res["ret_base"] = {"q50": float(rt[hz].loc[known].median()), "pos": float((rt[hz].loc[known] > 0).mean())}
        out[hz] = res
    return out


def similar_days(p: pd.Series, date: pd.Timestamp | None = None, n: int = 6, gap: int = 21) -> list[dict]:
    """I giorni del passato piu' simili a oggi (distinti: almeno `gap` sedute di distanza) e che cosa e' successo dopo."""
    p = p.dropna()
    F = price_features(p)[FEATURES].dropna()
    date = date or F.index[-1]
    mu, sd = F.mean(), F.std().replace(0, 1)
    Z = (F - mu) / sd
    cand = F.index[F.index < date - pd.Timedelta(days=200)]
    dist = pd.Series(np.sqrt(((Z.loc[cand].values - Z.loc[date].values) ** 2).sum(axis=1)), index=cand).sort_values()
    picked = []
    for d, v in dist.items():
        if all(abs(p.index.get_loc(d) - p.index.get_loc(q)) > gap for q, _ in picked):
            picked.append((d, v))
        if len(picked) >= n:
            break
    rows = []
    zn = Z.loc[date]
    for d, v in picked:
        i = p.index.get_loc(d)

        def after(k):
            return float(p.iloc[i + k] / p.iloc[i] - 1) if i + k < len(p) else None
        win = p.iloc[i:i + 64]
        mdd = float(win.min() / p.iloc[i] - 1) if len(win) > 10 else None
        close = sorted(FEATURES, key=lambda f: abs(Z.loc[d, f] - zn[f]))[:2]
        rows.append({"date": d.strftime("%Y-%m-%d"), "dist": round(float(v), 2), "ret_1m": after(21), "ret_3m": after(63),
                     "ret_6m": after(126), "maxdd_3m": mdd, "similar": [FEAT_IT[f] for f in close]})
    return rows


# ------------------------------------------------------------------ lettura indicatore per indicatore
# (chiave serie, nome, direzione del rischio: +1 = valore alto e' piu' rischioso, -1 = valore basso e' piu' rischioso, ritardo giorni, giorni max di ritardo)
SIGNALS = [
    ("vix", "VIX (paura)", 1, 0, 6), ("skew", "SKEW (protezione dai crolli)", 1, 0, 6),
    ("move", "MOVE (volatilità obbligazioni)", 1, 0, 8), ("baa10y", "Spread credito BAA-10Y", 1, 1, 8),
    ("hy_oas", "Spread High Yield", 1, 1, 8), ("nfci", "Condizioni finanziarie NFCI", 1, 5, 14),
    ("stlfsi", "Stress finanziario St. Louis", 1, 5, 14), ("t10y3m", "Curva tassi 10Y-3M", -1, 1, 8),
    ("t10y2y", "Curva tassi 10Y-2Y", -1, 1, 8), ("real10y", "Tasso reale a 10 anni", 1, 1, 8),
    ("dgs10", "Rendimento Treasury 10 anni", 1, 1, 8), ("usd_broad", "Dollaro (indice ampio)", 1, 5, 14),
    ("cape_m", "CAPE (valutazione)", 1, 1, 50), ("pe_m", "P/E S&P 500", 1, 1, 50), ("ps_m", "Prezzo/fatturato S&P 500", 1, 1, 110),
    ("epu", "Incertezza politica (EPU)", 1, 1, 10), ("gpr", "Rischio geopolitico (GPR)", 1, 1, 10),
    ("unrate", "Disoccupazione USA", 1, 30, 60), ("icsa", "Richieste di sussidio disoccupazione", 1, 5, 14),
    ("gold", "Oro", 1, 0, 6), ("wti", "Petrolio WTI", 1, 0, 6), ("aaii_spread", "Sentiment AAII (rialzisti-ribassisti)", -1, 1, 14),
]


def _aligned(key: str, idx: pd.DatetimeIndex, lag: int, limit: int) -> pd.Series:
    s = store.load(key)
    if s.empty:
        return pd.Series(dtype=float)
    full = s.reindex(pd.date_range(s.index[0], idx[-1])).ffill(limit=limit).shift(lag)
    return full.reindex(idx)


SCEN_EDGES = [-0.10, -0.03, 0.03, 0.10]
SCEN_NAMES = ["Forte calo (oltre −10%)", "Calo moderato (−10% … −3%)", "Laterale (−3% … +3%)", "Rialzo moderato (+3% … +10%)", "Forte rialzo (oltre +10%)"]


def scenario_probs(r: pd.Series) -> list[float]:
    """Quota di casi in ciascuno dei 5 scenari di rendimento finale a 3 mesi."""
    r = r.dropna()
    if r.empty:
        return [float("nan")] * 5
    b = np.searchsorted(SCEN_EDGES, r.values, side="right")
    return [float((b == i).mean()) for i in range(5)]


def signal_table(p: pd.Series, h: str = "3m") -> list[dict]:
    """Per ogni indicatore: valore oggi, percentile storico, e che cosa e' successo all'S&P 500 nei 3 mesi dopo
    le volte in cui l'indicatore era nella stessa fascia (quintile) di oggi."""
    p = p.dropna()
    n = HORIZONS[h]
    dd, rt = fwd_maxdd(p, n), fwd_ret(p, n)
    upm = fwd_maxup(p, n)
    ok_idx = p.index[:-n]
    base_up = float((upm.loc[ok_idx] >= 0.10).mean())
    base_sc = scenario_probs(rt.loc[ok_idx])
    base_dd = float((dd.loc[ok_idx] <= -0.10).mean())
    base_ret = float(rt.loc[ok_idx].mean())
    out = []
    for key, name, bad, lag, maxage in SIGNALS:
        s = _aligned(key, p.index, lag, 400)
        raw = store.load(key)
        if s.dropna().empty or len(s.dropna()) < 750 or raw.empty:
            continue
        if (p.index[-1] - raw.index[-1]).days > maxage + 15:
            continue
        now = float(raw.iloc[-1])
        hist = s.dropna()
        pct = float((hist < now).mean() * 100)
        edges = hist.quantile([.2, .4, .6, .8]).values
        q = np.searchsorted(edges, now)
        qs = pd.Series(np.searchsorted(edges, s.values), index=s.index).where(s.notna())
        mask = (qs == q) & dd.notna() & rt.notna()
        m = int(mask.sum())
        if m < 150:
            continue
        freq = float((dd[mask] <= -0.10).mean())
        ret = float(rt[mask].mean())
        pos = float((rt[mask] > 0).mean())
        ratio = freq / base_dd if base_dd > 0 else 1.0
        # il rendimento medio conta quanto la frequenza di cali: lettura prudente
        if ratio >= 1.25 or (ratio >= 1.1 and ret < base_ret - 0.01):
            verdict = "negativo"
        elif ratio <= 0.8 or (ratio <= 0.92 and ret > base_ret + 0.01):
            verdict = "positivo"
        else:
            verdict = "neutro"
        out.append({"up10": float((upm[mask] >= 0.10).mean()), "base_up10": base_up, "scen": scenario_probs(rt[mask]), "base_scen": base_sc,
                    "key": key, "name": name, "now": now, "pct": pct, "quintile": int(q) + 1, "n": m,
                    "freq_dd10": freq, "base_dd10": base_dd, "ratio": ratio, "ret": ret, "base_ret": base_ret,
                    "pos": pos, "verdict": verdict, "since": hist.index[0].strftime("%Y")})
    return out


def episodes_for_value(key: str, p: pd.Series, n: int = 3, gap_days: int = 120) -> list[dict]:
    """Date del passato in cui l'indicatore valeva quasi come oggi, con l'esito dell'S&P 500 a 3 mesi."""
    s = store.load(key)
    if s.empty or len(s) < 300:
        return []
    now = float(s.iloc[-1])
    hist = s[s.index < s.index[-1] - pd.Timedelta(days=90)]
    d = (hist - now).abs().sort_values()
    picked = []
    for dt in d.index:
        if all(abs((dt - q).days) > gap_days for q in picked):
            picked.append(dt)
        if len(picked) >= n:
            break
    out = []
    for dt in sorted(picked):
        pp = p[p.index >= dt]
        if len(pp) < 64:
            continue
        w = pp.iloc[:64]
        out.append({"date": dt.strftime("%Y-%m"), "value": float(hist.loc[dt]), "ret_3m": float(pp.iloc[63] / pp.iloc[0] - 1),
                    "maxdd": float(w.min() / pp.iloc[0] - 1)})
    return out
