# -*- coding: utf-8 -*-
"""Laboratorio esplorativo per i precursori endogeni dei drawdown.

Eseguire dalla root del repository:
    PYTHONPATH=src python scratch/armor_endogenous_lab.py

Non modifica score o previsioni in produzione. Campionamento mensile vicino ai massimi,
walk-forward, embargo legato all'orizzonte, benchmark a frequenza base, report JSON.
Le serie breadth da componenti correnti sono separate per survivorship bias.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from armor import store
from armor.features import vwce_series
from armor.semafori import credit_gap

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch" / "armor_endogenous_lab_result.json"


def load(k: str) -> pd.Series:
    return store.load(k).dropna().astype(float)


def align(s: pd.Series, idx: pd.DatetimeIndex, max_ffill: int = 5) -> pd.Series:
    if s.empty:
        return pd.Series(np.nan, index=idx, dtype=float)
    return s.reindex(s.index.union(idx)).sort_index().ffill(limit=max_ffill).reindex(idx)


def lag_available(s: pd.Series, idx: pd.DatetimeIndex, days: int, max_ffill: int = 160) -> pd.Series:
    """Shift from observation date to conservative assumed publication/availability date."""
    if s.empty:
        return pd.Series(np.nan, index=idx, dtype=float)
    x = s.copy()
    x.index = pd.to_datetime(x.index) + pd.Timedelta(days=days)
    x = x[~x.index.duplicated(keep="last")].sort_index()
    return x.reindex(x.index.union(idx)).sort_index().ffill(limit=max_ffill).reindex(idx)


def add_ratio(F: pd.DataFrame, name: str, a: str, b: str, windows=(21, 63)) -> None:
    aa, bb = align(load(a), F.index), align(load(b), F.index)
    lr = np.log(aa.where(aa > 0)) - np.log(bb.where(bb > 0))
    for w in windows:
        F[f"{name}_{w}"] = lr - lr.shift(w)
    F[f"{name}_dd126"] = lr - lr.rolling(126, min_periods=80).max()


def add_dsr(F: pd.DataFrame) -> list[str]:
    """BIS DSR features. Lag of 120 days is conservative; transforms use only past quarters."""
    added = []
    for sid in [
        "bis_dsr_us_private", "bis_dsr_us_households", "bis_dsr_us_corporate",
        "bis_dsr_xm_private", "bis_dsr_jp_private", "bis_dsr_gb_private", "bis_dsr_ca_private",
    ]:
        q = load(sid)
        if q.empty:
            continue
        q = q.sort_index()
        z = (q - q.rolling(20, min_periods=12).mean()) / q.rolling(20, min_periods=12).std()
        feats = {
            f"{sid}_level": q,
            f"{sid}_yoy": q - q.shift(4),
            f"{sid}_z20q": z,
        }
        for col, series in feats.items():
            F[col] = lag_available(series, F.index, days=120, max_ffill=180)
            added.append(col)
    return added


def build_features(p: pd.Series, target: str) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    idx = p.index
    F = pd.DataFrame(index=idx)
    lr = np.log(p.where(p > 0)).diff()
    F["rv21"] = lr.rolling(21).std() * np.sqrt(252)
    F["rv63"] = lr.rolling(63).std() * np.sqrt(252)
    F["rv_ratio"] = F["rv21"] / (lr.rolling(252, min_periods=120).std() * np.sqrt(252))
    F["dd252"] = p / p.rolling(252, min_periods=120).max() - 1
    F["ma200"] = p / p.rolling(200).mean() - 1
    F["ma50_200"] = p.rolling(50).mean() / p.rolling(200).mean() - 1
    F["mom63"] = p / p.shift(63) - 1
    F["worst_day"] = lr.rolling(21).min()

    # S&P/global cross-market returns to identify contagion and geographic divergence.
    for sid in ["sp500", "vt", "vwce_de", "stoxx50", "nikkei", "eem", "dax"]:
        s = align(load(sid), idx)
        if s.notna().sum() > 252:
            F[f"{sid}_mom63"] = s / s.shift(63) - 1
            F[f"{sid}_dd252"] = s / s.rolling(252, min_periods=120).max() - 1
    if target == "vwce_eur_proxy":
        fx = align(load("eurusd"), idx)
        F["eurusd_mom21"] = fx / fx.shift(21) - 1
        F["eurusd_mom63"] = fx / fx.shift(63) - 1

    # Volatility / options: current fear and term-structure inversion.
    vix, vix3m = align(load("vix"), idx), align(load("vix3m"), idx)
    vvix, skew, move = align(load("vvix"), idx), align(load("skew"), idx), align(load("move"), idx)
    F["vix_lvl"] = vix
    F["vix_d21"] = np.log(vix.where(vix > 0) / vix.shift(21))
    F["vix_term"] = vix / (vix3m + 1e-6)
    F["vix_term_d21"] = F["vix_term"] - F["vix_term"].shift(21)
    F["vvix"] = vvix
    F["vvix_d21"] = np.log(vvix.where(vvix > 0) / vvix.shift(21))
    F["skew"] = skew
    F["move"] = move

    # Credit risk and relative funding prices.
    for a, b, nm in [
        ("baa_d", "aaa_d", "baa_aaa"), ("hyg", "ief", "hyg_ief"), ("jnk", "ief", "jnk_ief"),
        ("lqd", "ief", "lqd_ief"), ("kre", "spy", "kre_spy"), ("sec_xlf", "spy", "xlf_spy"),
    ]:
        add_ratio(F, nm, a, b)
    for nm in ["baa10y"]:
        s = align(load(nm), idx)
        F[nm] = s
        F[f"{nm}_d63"] = s - s.shift(63)

    # Market internals using broad, long-lived ETF/index proxies; not constituent survivorship data.
    for a, b, nm in [
        ("rsp", "spy", "rsp_spy"), ("smh", "spy", "smh_spy"), ("qqq", "spy", "qqq_spy"),
        ("sec_xly", "sec_xlp", "xly_xlp"), ("sec_xlu", "spy", "xlu_spy"),
        ("iwm", "spy", "iwm_spy"), ("iyt", "spy", "iyt_spy"),
    ]:
        add_ratio(F, nm, a, b)

    # Cross-asset correlations can expose loss of diversification / flight-to-quality.
    spy = align(load("spy"), idx)
    for sym in ["ief", "hyg", "gld", "dxy", "rsp"]:
        b = align(load(sym), idx)
        F[f"corr_spy_{sym}_63"] = spy.pct_change(fill_method=None).rolling(63, min_periods=48).corr(b.pct_change(fill_method=None))

    # Macro series are shifted to assumed publication dates before being forward-filled.
    macro_lags = {
        "nfci_credit": 7, "nfci_leverage": 7, "nfci_risk": 7, "nfci": 7, "anfci": 7,
        "stlfsi": 7, "icsa": 7, "sloos": 45, "sloos_piccole": 45, "sloos_carte": 45,
        "net_liq_13w": 7, "cape_m": 45, "m2_yoy": 45, "margin_yoy": 45,
        "sahm": 45, "real10y": 2, "dgs10": 2, "fedfunds": 2, "unrate": 45,
    }
    for nm, lag in macro_lags.items():
        s = lag_available(load(nm), idx, lag, max_ffill=160)
        F[nm] = s
        if nm in {"nfci_credit", "nfci_leverage", "nfci_risk", "nfci", "anfci", "stlfsi", "icsa", "sloos", "net_liq_13w", "cape_m", "m2_yoy", "margin_yoy", "sahm", "unrate"}:
            F[f"{nm}_d63"] = s - s.shift(63)

    # BIS credit-to-GDP gap: one-sided HP approximation already used by Armor's semaphore.
    cr = load("credit_ratio")
    if not cr.empty:
        gap = credit_gap(cr)
        F["credit_gap_bis_hp"] = lag_available(gap, idx, 120, max_ffill=180)
        F["credit_ratio_yoy"] = lag_available(cr - cr.shift(4), idx, 120, max_ffill=180)
    dsr_cols = add_dsr(F)

    # CUSUM-like persistence: exponentially weighted stress history, without fitted thresholds.
    for nm in ["nfci_credit", "nfci_leverage", "stlfsi", "baa10y", "credit_gap_bis_hp"]:
        if nm in F:
            F[f"{nm}_ewm6"] = F[nm].ewm(span=6, min_periods=4, adjust=False).mean()
            F[f"{nm}_trend3"] = F[nm] - F[nm].shift(63)

    # Current constituent breadth is isolated (not eligible for promotion: survivorship bias).
    breadth_cols = []
    for nm in ["d_pct_sopra_20", "d_pct_sopra_50", "d_pct_sopra_200", "d_pct_nuovi_massimi_252", "d_pct_nuovi_minimi_252", "d_dispersione", "d_correlazione_media_21", "d_correlazione_media_63", "d_quota_volume_top10"]:
        s = align(load(nm), idx)
        if s.notna().sum() > 50:
            col = f"breadth_{nm}"
            F[col] = s
            F[f"{col}_d21"] = s - s.shift(21)
            breadth_cols.extend([col, f"{col}_d21"])

    price_cols = [c for c in ["rv21", "rv63", "rv_ratio", "dd252", "ma200", "ma50_200", "mom63", "worst_day"] if c in F]
    credit_cols = [c for c in F.columns if any(c.startswith(x) for x in [
        "baa_aaa", "baa10y", "hyg_ief", "jnk_ief", "lqd_ief", "nfci", "anfci", "stlfsi", "sloos", "icsa",
        "credit_gap", "credit_ratio", "bis_dsr", "margin_yoy", "net_liq", "m2_yoy", "real10y", "dgs10", "unrate", "sahm",
    ])]
    cross_cols = [c for c in F.columns if any(c.startswith(x) for x in [
        "vix", "vvix", "skew", "move", "rsp_spy", "smh_spy", "qqq_spy", "xly_xlp", "xlu_spy", "iwm_spy", "iyt_spy",
        "kre_spy", "xlf_spy", "corr_spy", "sp500_", "vt_", "vwce_de_", "stoxx50_", "nikkei_", "eem_", "dax_", "eurusd_",
    ])]
    groups = {
        "price_baseline": price_cols,
        "credit_funding": list(dict.fromkeys(credit_cols)),
        "cross_asset_internal": list(dict.fromkeys(cross_cols)),
        "all_core": list(dict.fromkeys(price_cols + credit_cols + cross_cols)),
        "breadth_sensitivity_only": list(dict.fromkeys(price_cols + credit_cols + cross_cols + breadth_cols)),
    }
    if dsr_cols:
        groups["BIS_DSR_only"] = dsr_cols
    return F, groups


def forward_min_dd(p: pd.Series, h: int) -> pd.Series:
    future_min = p[::-1].rolling(h, min_periods=h).min()[::-1].shift(-1)
    return future_min / p - 1


def cluster_count(dates: list[pd.Timestamp], gap_days: int = 370) -> int:
    clusters: list[list[pd.Timestamp]] = []
    for d in dates:
        if not clusters or (d - clusters[-1][-1]).days > gap_days:
            clusters.append([d])
        else:
            clusters[-1].append(d)
    return len(clusters)


def walk_forward(X: pd.DataFrame, y: pd.Series, model_name: str, start: str, embargo_days: int,
                 min_train: int = 48, refit_every: int = 12) -> dict:
    dates = X.index
    preds, actual, priors, test_dates = [], [], [], []
    model, last_fit, goodcols, prior = None, -10_000, [], np.nan
    for pos, dt in enumerate(dates):
        if dt < pd.Timestamp(start) or pd.isna(y.loc[dt]):
            continue
        if model is None or pos - last_fit >= refit_every:
            train_mask = (dates < dt - pd.Timedelta(days=embargo_days)) & y.notna()
            tr = np.where(train_mask)[0]
            if len(tr) < min_train:
                continue
            Xt, yt = X.iloc[tr].copy(), y.iloc[tr]
            goodcols = list(Xt.columns[Xt.notna().mean() >= 0.60])
            if not goodcols or yt.sum() < 8 or (1 - yt).sum() < 8:
                continue
            imputer = SimpleImputer(strategy="median")
            if model_name == "LOGIT_L2":
                model = make_pipeline(imputer, StandardScaler(),
                                      LogisticRegression(C=0.03, max_iter=600, class_weight=None))
            elif model_name == "HIST_GRADIENT_BOOSTING":
                model = make_pipeline(imputer,
                                      HistGradientBoostingClassifier(max_iter=60, learning_rate=0.04,
                                                                     max_leaf_nodes=5, min_samples_leaf=12,
                                                                     l2_regularization=10, random_state=42))
            else:
                raise ValueError(model_name)
            model.fit(Xt[goodcols], yt.astype(int))
            prior = float((yt.sum() + 1) / (len(yt) + 2))  # smoothed train-only base rate
            last_fit = pos
        probability = float(model.predict_proba(X.loc[[dt], goodcols])[0, 1])
        preds.append(probability); actual.append(int(y.loc[dt])); priors.append(prior); test_dates.append(dt)
    if len(actual) < 20 or len(set(actual)) < 2:
        return {"n": len(actual), "positivi": int(sum(actual)), "esito": "campione insufficiente"}
    yy, pp, p0 = np.asarray(actual), np.asarray(preds), np.asarray(priors)
    brier = brier_score_loss(yy, pp)
    brier0 = brier_score_loss(yy, p0)
    top_cut = np.quantile(pp, 0.90)
    top = pp >= top_cut
    pos_dates = [pd.Timestamp(d) for d, a in zip(test_dates, yy) if a]
    return {
        "n": int(len(yy)), "positivi": int(yy.sum()), "frequenza_test": round(float(yy.mean()), 4),
        "episodi_positivi_approssimati": cluster_count(pos_dates),
        "inizio_test": str(pd.Timestamp(test_dates[0]).date()), "fine_test": str(pd.Timestamp(test_dates[-1]).date()),
        "auc": round(float(roc_auc_score(yy, pp)), 4), "pr_auc": round(float(average_precision_score(yy, pp)), 4),
        "brier": round(float(brier), 5), "brier_skill_vs_base_train": round(float(1 - brier / brier0), 4) if brier0 > 0 else None,
        "tasso_eventi_top10pct": round(float(yy[top].mean()), 4),
        "recall_top10pct": round(float(yy[top].sum() / max(yy.sum(), 1)), 4),
        "prob_media": round(float(pp.mean()), 4), "prob_max": round(float(pp.max()), 4),
    }


def run() -> dict:
    prices = {"sp500": load("sp500"), "vwce_eur_proxy": vwce_series().dropna()}
    results = {
        "protocollo": "endogenous-lab-v1",
        "data": str(pd.Timestamp.today().date()),
        "note": [
            "Ricerca sperimentale: nessun punteggio entra negli indici di produzione.",
            "Le probabilità sono stimate walk-forward; embargo 100/200/380 giorni per 63/126/252 sedute.",
            "I dati macro FRED sono storici rivisti, non veri vintages point-in-time.",
            "La breadth da componenti correnti è solo sensibilità per survivorship bias.",
            "La proxy VWCE usa VT/EURUSD prima della storia reale VWCE; il campione è più corto.",
        ],
        "targets": {},
    }
    for target, p in prices.items():
        if p.empty:
            continue
        F, groups = build_features(p, target)
        month_dates = p.groupby([p.index.year, p.index.month]).tail(1).index
        near_high = (p / p.rolling(252, min_periods=120).max() - 1).reindex(month_dates) >= -0.05
        result_target = {
            "target": target, "prezzo_da": str(p.index.min().date()), "prezzo_a": str(p.index.max().date()),
            "mesi_totali": int(len(month_dates)), "mesi_vicino_massimo": int(near_high.sum()),
            "features_dsr_presenti": [c for c in F.columns if c.startswith("bis_dsr_")],
            "targets": {},
        }
        for label, h, threshold, embargo in [
            ("dd63_8", 63, -0.08, 100), ("dd126_10", 126, -0.10, 200), ("dd252_15", 252, -0.15, 380),
        ]:
            y_daily = (forward_min_dd(p, h) <= threshold).astype(float)
            # incomplete future windows are missing, never silently relabelled as no-crash.
            valid = forward_min_dd(p, h).notna()
            y_daily = y_daily.where(valid)
            y = y_daily.reindex(month_dates)
            Fm = F.reindex(month_dates)
            mask = near_high & y.notna()
            target_res = {"orizzonte_sedute": h, "soglia_drawdown": threshold,
                          "mesi_vicino_massimo_valutabili": int(mask.sum()),
                          "mesi_positivi": int(y.loc[mask].sum()), "embargo_giorni": embargo, "modelli": {}}
            for group, cols in groups.items():
                if not cols:
                    continue
                # Breadth group is deliberately later and is not eligible for promotion.
                start = "2010-01-31" if target == "sp500" and group in ("price_baseline", "credit_funding") else "2015-01-31"
                if target == "vwce_eur_proxy":
                    start = "2015-01-31"
                X = Fm.loc[mask, cols]
                yy = y.loc[mask]
                for model_name in ["LOGIT_L2", "HIST_GRADIENT_BOOSTING"]:
                    target_res["modelli"].setdefault(group, {})[model_name] = walk_forward(
                        X, yy, model_name, start=start, embargo_days=embargo,
                    )
            result_target["targets"][label] = target_res
        results["targets"][target] = result_target
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


if __name__ == "__main__":
    report = run()
    for target, body in report["targets"].items():
        print(f"\n=== {target} | {body['prezzo_da']} - {body['prezzo_a']} ===")
        for name, res in body["targets"].items():
            print(f"\n{name}: n vicino ai massimi={res['mesi_vicino_massimo_valutabili']}, positivi={res['mesi_positivi']}, embargo={res['embargo_giorni']}g")
            for group, models in res["modelli"].items():
                for mdl, metrics in models.items():
                    print(group, mdl, metrics)
    print(f"\nRisultati scritti in {OUT}")
