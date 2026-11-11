# -*- coding: utf-8 -*-
"""Motore Titan v47 per Armor (porting da armor_cronos_lab.py + armor_titan_v40.py).

Tre blocchi, sempre nello stesso ordine:
  1. market_stage(S)      serie grezze (dict) -> colonne di mercato/macro (come load_all_market_data)
  2. build_features(df)   colonne di mercato -> orologi P/S/D/Top, z-score (come build_features)
  3. build_titan(df)      + dati dei grandi fondi -> 6 pilastri, Super Armor, Indice Armor, Radar Decennio
Poi walk_forward(df, horizon, ...) per le probabilita' di calo e di rialzo a 5 orizzonti.

Differenza voluta rispetto alla ricerca: niente bfill (riempire all'indietro usava dati del futuro
sulle serie che iniziano tardi, es. VIX9D dal 2011). Scala 1-100, stress da 40.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

ORIZZONTI = [(7, 0.05, "1 settimana"), (21, 0.10, "1 mese"), (63, 0.10, "3 mesi"), (126, 0.10, "6 mesi"), (252, 0.10, "12 mesi")]

SEC_USER_AGENT = "Stefano Orlando orl.infomail@gmail.com"


# ---------------------------------------------------------------- utilita'
def clean_series(s, default: float = 0.0) -> pd.Series:
    """Come nella ricerca ma SOLO in avanti: nessun valore del futuro riempie il passato."""
    return pd.Series(s, copy=True).replace([np.inf, -np.inf], np.nan).ffill().fillna(default)


def safe_mat(arr) -> np.ndarray:
    return np.nan_to_num(np.asarray(arr, dtype=float), copy=True, nan=0.0, posinf=0.0, neginf=0.0)


def causal_z(s, window: int = 1260, min_periods: int = 126) -> pd.Series:
    s_cl = clean_series(s, 0.0)
    m = s_cl.rolling(window, min_periods=min_periods).mean()
    sd = s_cl.rolling(window, min_periods=min_periods).std() + 1e-8
    return clean_series(((s_cl - m) / sd).clip(-3.5, 3.5), 0.0)


def _cz(s: pd.Series, window: int = 1260) -> pd.Series:
    """causal_z di build_features (min 252 osservazioni)."""
    m = s.rolling(window, min_periods=252).mean()
    sd = s.rolling(window, min_periods=252).std() + 1e-8
    return ((s - m) / sd).clip(-3.5, 3.5).fillna(0.0)


def _lag(s: pd.Series | None, days: int) -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series(dtype=float)
    s = pd.Series(s).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.index = s.index + pd.Timedelta(days=days)
    return s


# ---------------------------------------------------------------- 1. mercato
def market_stage(S: dict) -> pd.DataFrame:
    """S: dict nome -> pd.Series (date -> valore) con i dati grezzi, SENZA ritardi di pubblicazione.
    Chiavi: sp500 vix vix3m vvix skew y3m y5y y10y rsp iwm dxy oil gold dax n225 eem copper hyg ief
    xlk xlf xlv xly xli xlp xle xlu xlb kre iyt smh | hy_oas baa ebp nfci icsa ccsa permit indpro cpi
    oil_fred cp walcl tga rrp cape pe ps. Le mancanti usano gli stessi riserve della ricerca."""
    g = lambda k: (pd.Series(S[k]).sort_index() if k in S and S[k] is not None and len(S[k]) else pd.Series(dtype=float))
    sp = g("sp500").dropna()
    df = pd.DataFrame(index=sp.index)
    ri = lambda s: s.reindex(df.index)
    df["sp500"] = sp
    df["vix"] = ri(g("vix")).ffill()
    df["vix3m"] = ri(g("vix3m")).ffill()
    df["vvix"] = ri(g("vvix")).ffill().fillna(90.0)
    df["skew"] = ri(g("skew")).ffill().fillna(120.0)
    df["y3m"] = ri(g("y3m")).ffill()
    df["y5y"] = ri(g("y5y")).ffill()
    df["y10y"] = ri(g("y10y")).ffill()
    df["rsp"] = ri(g("rsp")).ffill()
    df["iwm"] = ri(g("iwm")).ffill()
    df["dxy"] = ri(g("dxy")).ffill()
    df["oil_yf"] = ri(g("oil")).ffill()
    df["gold"] = ri(g("gold")).ffill()

    dax, n225, eem = ri(g("dax")).ffill(), ri(g("n225")).ffill(), ri(g("eem")).ffill()
    g_us = (sp > sp.rolling(126).mean()).astype(float)
    g_eu = (dax > dax.rolling(126).mean()).where(dax.notna(), g_us)
    g_jp = (n225 > n225.rolling(126).mean()).where(n225.notna(), g_us)
    g_em = (eem > eem.rolling(126).mean()).where(eem.notna(), g_us)
    df["global_sync_bull"] = 0.35 * g_us + 0.25 * g_eu.astype(float) + 0.20 * g_jp.astype(float) + 0.20 * g_em.astype(float)

    fin = ri(g("kre")).combine_first(ri(g("xlf"))).ffill()
    trn = ri(g("iyt")).combine_first(ri(g("xli"))).ffill()
    sem = ri(g("smh")).combine_first(ri(g("xlk"))).ffill()
    df["lead_fin_63"] = (fin / sp).pct_change(63, fill_method=None).fillna(0.0)
    df["lead_trn_63"] = (trn / sp).pct_change(63, fill_method=None).fillna(0.0)
    df["lead_sem_21"] = (sem / sp).pct_change(21, fill_method=None).fillna(0.0)
    df["lead_iwm_21"] = (df["iwm"] / sp).pct_change(21, fill_method=None).fillna(0.0)

    copper = ri(g("copper")).ffill()
    df["cu_au_ret63"] = (copper / df["gold"]).pct_change(63, fill_method=None).fillna(0.0)
    df["dxy_ret63"] = df["dxy"].pct_change(63, fill_method=None).fillna(0.0)
    df["ntfs"] = (df["y5y"] - df["y3m"]).fillna(0.5)

    ratio = (ri(g("hyg")) / ri(g("ief")))
    df["hyg_ief_ret5"] = ratio.pct_change(5, fill_method=None)
    df["hyg_ief_ret21"] = ratio.pct_change(21, fill_method=None)
    df["hyg_ief_ret63"] = ratio.pct_change(63, fill_method=None)

    # spettroscopia dei settori (finestra 252, ogni 5 sedute)
    sec_cols = ["xlk", "xlf", "xlv", "xly", "xli", "xlp", "xle", "xlu", "xlb", "iwm", "hyg", "ief"]
    sec = pd.DataFrame({c: (ri(g(c)) if c != "iwm" else df["iwm"]) for c in sec_cols}).pct_change(fill_method=None)
    ar_arr = np.full(len(df), np.nan)
    mahal_arr = np.full(len(df), np.nan)
    vals = sec.values
    for i in range(252, len(df), 5):
        window = vals[i - 252:i]
        ok = np.isnan(window).sum(axis=0) < 20
        if ok.sum() >= 5:
            w = np.nan_to_num(window[:, ok], nan=0.0)
            cov = np.cov(w, rowvar=False)
            ev = np.sort(np.maximum(np.linalg.eigvalsh(cov), 1e-12))[::-1]
            k = max(1, int(np.ceil(len(ev) / 5)))
            ar_arr[i] = ev[:k].sum() / ev.sum()
            diff = w[-1] - w.mean(axis=0)
            mahal_arr[i] = float(diff @ np.linalg.pinv(cov) @ diff.T) / len(ev)
    ar_s = pd.Series(ar_arr, index=df.index).ffill()
    mh_s = pd.Series(mahal_arr, index=df.index).ffill()
    df["delta_ar"] = ((ar_s.rolling(15).mean() - ar_s.rolling(252).mean()) / (ar_s.rolling(252).std() + 1e-8)).fillna(0.0)
    df["mahal_z"] = ((mh_s.rolling(15).mean() - mh_s.rolling(252).mean()) / (mh_s.rolling(252).std() + 1e-8)).fillna(0.0)

    # macro con ritardi di pubblicazione (giorni in cui il dato era davvero noto)
    hy_oas = _lag(g("hy_oas"), 0)
    baa = g("baa").dropna()
    baa_sp = (baa - df["y10y"].reindex(baa.index).ffill()).dropna() if len(baa) else pd.Series(dtype=float)
    baa_sp = _lag(baa_sp, 5)
    ebp = _lag(g("ebp"), 28)
    nfci = _lag(g("nfci"), 6)
    icsa = _lag(g("icsa"), 6)
    ccsa = _lag(g("ccsa"), 10)
    permit, indpro, cpi = _lag(g("permit"), 45), _lag(g("indpro"), 45), _lag(g("cpi"), 45)
    oil_fred = _lag(g("oil_fred"), 0)
    cp = _lag(g("cp"), 150)
    walcl, tga, rrp = _lag(g("walcl"), 3), _lag(g("tga"), 3), _lag(g("rrp"), 2)

    df["hy_oas"] = ri(hy_oas).ffill()
    df["baa_spread"] = ri(baa_sp).ffill()
    df["credit_level"] = df["hy_oas"].combine_first(df["baa_spread"] * 2.2).ffill()
    df["ebp"] = ri(ebp).ffill().fillna(0.0)
    df["nfci"] = ri(nfci).ffill().fillna(0.0)

    icsa_d = ri(icsa).ffill()
    ma20 = icsa_d.rolling(20).mean()
    df["icsa_surge"] = ((ma20 / (ma20.rolling(252).min() + 1.0)) - 1.0).fillna(0.0)
    df["ccsa_yoy"] = ri(ccsa).ffill().pct_change(252, fill_method=None).fillna(0.0)
    df["permit_yoy"] = ri(permit).ffill().pct_change(252, fill_method=None).fillna(0.0)
    df["indpro_6m"] = ri(indpro).ffill().pct_change(126, fill_method=None).fillna(0.0)
    cpi_yoy = (ri(cpi).ffill().pct_change(252, fill_method=None) * 100.0).fillna(2.5)
    df["cpi_yoy"] = cpi_yoy
    df["cpi_accel_6m"] = (cpi_yoy - cpi_yoy.shift(126)).fillna(0.0)
    oil_comb = df["oil_yf"].combine_first(ri(oil_fred).ffill()).ffill()
    df["oil_surge_6m"] = oil_comb.pct_change(126, fill_method=None).fillna(0.0)
    df["profits_yoy"] = ri(cp).ffill().pct_change(252, fill_method=None).fillna(0.0)

    df["cape"] = ri(_lag(g("cape"), 25)).ffill().fillna(22.0)
    df["pe"] = ri(_lag(g("pe"), 45)).ffill().fillna(df["cape"] * 0.85)
    df["ps"] = ri(_lag(g("ps"), 45)).ffill().fillna(df["pe"] * 0.09)

    w_s = ri(walcl).ffill()
    tga_d = ri(tga).ffill().fillna(0.0)
    t_s = tga_d * 1000.0 if (len(tga) and tga.max() < 5000) else tga_d
    r_s = ri(rrp).ffill().fillna(0.0) * 1000.0
    net_liq = w_s - t_s - r_s
    df["net_liq_ret63"] = net_liq.pct_change(63, fill_method=None).fillna(-df["nfci"].diff(63)).fillna(0.0)

    for k, n in (("hyg_ief_ret5", 5), ("hyg_ief_ret21", 21), ("hyg_ief_ret63", 63)):
        df[k] = df[k].fillna(-df["credit_level"].diff(n) / 100.0).fillna(0.0)
    return df


# ---------------------------------------------------------------- 2. orologi
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    p = df["sp500"]
    ret = p.pct_change(fill_method=None)
    df["ret"] = ret
    df["rv5"] = ret.rolling(5).std() * np.sqrt(252)
    df["rv21"] = ret.rolling(21).std() * np.sqrt(252)
    df["rv63"] = ret.rolling(63).std() * np.sqrt(252)
    df["rv252"] = ret.rolling(252).std() * np.sqrt(252)
    df["rv_ratio"] = df["rv21"] / (df["rv252"] + 1e-8)
    df["dd252"] = 1.0 - (p / p.rolling(252).max())
    df["dd21"] = 1.0 - (p / p.rolling(21).max())
    sma5, sma50, sma200 = p.rolling(5).mean(), p.rolling(50).mean(), p.rolling(200).mean()
    df["dist_sma5"] = (p / sma5) - 1.0
    df["dist_sma200"] = (p / sma200) - 1.0
    df["sma50_200"] = (sma50 / sma200) - 1.0
    df["mom5"] = p.pct_change(5, fill_method=None).fillna(0.0)
    df["mom21"] = p.pct_change(21, fill_method=None).fillna(0.0)
    df["mom63"] = p.pct_change(63, fill_method=None).fillna(0.0)
    df["worst21"] = ret.rolling(21).min()

    net_move42 = p.diff(42)
    sum_abs42 = p.diff(1).abs().rolling(42).sum() + 1e-8
    df["er_down42"] = (np.maximum(0.0, -net_move42) / sum_abs42).fillna(0.0)
    df["er_up21"] = (np.maximum(0.0, p.diff(21)) / (p.diff(1).abs().rolling(21).sum() + 1e-8)).fillna(0.0)

    neg2 = pd.Series(np.where(ret < 0, ret ** 2, 0.0), index=df.index)
    pos2 = pd.Series(np.where(ret > 0, ret ** 2, 0.0), index=df.index)
    rm = {n: neg2.rolling(n).sum() * (252 / n) for n in (5, 21, 63)}
    rp = {n: pos2.rolling(n).sum() * (252 / n) for n in (5, 21, 63)}
    for n in (5, 21, 63):
        df[f"sjv{n}"] = (rm[n] - rp[n]) / (rm[n] + rp[n] + 1e-12)

    vix_proxy = df["vix"].fillna(df["rv21"] * 100.0)
    df["vix_clean"] = vix_proxy
    vix_dec = (vix_proxy / 100.0) * np.sqrt(0.8)
    df["har_vix_vol"] = 0.45 * vix_dec + 0.25 * np.sqrt(rm[5] * 1.8) + 0.20 * np.sqrt(rm[21] * 1.8) + 0.10 * df["rv63"]
    df["vix_term_structure"] = (vix_proxy / (df["vix3m"].fillna(vix_proxy * 1.04) + 1e-4)).fillna(0.95)

    df["z_har_vol"] = _cz(df["har_vix_vol"])
    df["z_term_inv"] = _cz(df["vix_term_structure"])
    df["z_sjv5"] = _cz(df["sjv5"])
    df["z_hyg5_weak"] = _cz(-df["hyg_ief_ret5"])
    df["z_vvix_jump"] = _cz(df["vvix"].diff(5).fillna(0.0))

    in_up = (df["dist_sma200"] > -0.02).astype(float) * (df["vix_term_structure"] < 1.02).astype(float)
    pull = np.clip(-df["mom5"] / 0.025, -1.0, 2.0) * in_up
    df["short_term_carry_7d"] = expit(-0.45 * _cz(df["vix_clean"]) - 0.35 * df["z_term_inv"] - 0.25 * df["z_hyg5_weak"] + 0.45 * pull)

    df["erp_cape"] = 100.0 / np.maximum(df["cape"], 5.0) - df["y10y"]
    df["implied_margin"] = (df["ps"] / np.maximum(df["pe"], 1.0)).clip(0.02, 0.35)
    df["z_pe_secular"] = _cz(df["pe"], 1260)
    df["z_erp_improve"] = _cz(df["erp_cape"].diff(126).fillna(0.0), 756)

    z_comp = 0.40 * _cz(df["dd252"]) + 0.35 * _cz(-df["dist_sma200"]) + 0.25 * _cz(df["har_vix_vol"])
    df["P_clock"] = expit(1.2 * z_comp)
    df["z_oil_shock"] = _cz(df["oil_surge_6m"])
    df["z_cpi_accel"] = _cz(df["cpi_accel_6m"])
    df["inflation_bite"] = 0.55 * df["z_cpi_accel"] + 0.45 * df["z_oil_shock"]

    doy = df.index.dayofyear.values
    wave = np.cos(2.0 * np.pi * (doy - 285.0) / 365.25)
    midterm = ((df.index.year % 4 == 2) & (df.index.month >= 8)).astype(float)
    df["cycle_harmonic_bull"] = (0.65 * wave + 0.35 * midterm) * df["P_clock"]

    credit_imp = df["credit_level"].diff(42).fillna(0.0) + 0.8 * df["ebp"].diff(63).fillna(0.0)
    hyg_imp = -df["hyg_ief_ret63"].fillna(0.0)
    ntfs_stress = -df["ntfs"].diff(63).fillna(0.0) - 0.4 * df["ntfs"]
    spec_imp = df["delta_ar"] + 0.4 * df["mahal_z"]
    holo_fracture = -0.45 * df["lead_fin_63"] - 0.35 * df["lead_trn_63"] + 0.20 * (df["skew"] - 125.0) / 15.0
    holo_rebound = (0.35 * _cz(df["lead_sem_21"]) + 0.25 * _cz(df["lead_iwm_21"]) + 0.25 * _cz(df["er_up21"])
                    + 0.15 * (df["global_sync_bull"] - 0.5) * 2.0)
    df["holo_fracture_z"] = _cz(holo_fracture)
    df["holo_rebound_z"] = holo_rebound
    macro_real_drag = (0.35 * _cz(-df["permit_yoy"]) + 0.35 * df["inflation_bite"]
                       + 0.15 * _cz(df["ccsa_yoy"]) + 0.15 * _cz(-df["profits_yoy"]))
    df["macro_real_drag_z"] = macro_real_drag

    z_struct_v6 = (0.26 * _cz(credit_imp) + 0.22 * _cz(hyg_imp) + 0.14 * _cz(ntfs_stress) + 0.14 * _cz(spec_imp)
                   + 0.11 * _cz(df["sjv63"]) + 0.06 * df["holo_fracture_z"] + 0.07 * macro_real_drag)
    df["S_clock_v6"] = expit(1.3 * z_struct_v6)
    sma200_falling = _cz(-sma200.pct_change(63, fill_method=None).fillna(0.0))
    z_ebp_lvl = _cz(df["ebp"])
    df["G_sys_v6"] = expit(2.0 * (0.60 * z_ebp_lvl + 0.40 * sma200_falling - 0.85))
    z_cred_fast = _cz(df["credit_level"].diff(21).fillna(0.0))
    z_sjv21 = _cz(df["sjv21"])
    deep6 = np.maximum(0.0, df["dd252"] - 0.08) / 0.10
    stab6 = expit(-0.8 * z_cred_fast - 0.5 * z_sjv21)
    df["D_ex_v6"] = np.clip(deep6 * stab6 * (1.0 - df["G_sys_v6"]), 0.0, 1.5)
    z_rate = _cz(df["y10y"].diff(63).fillna(0.0))
    near_highs = np.maximum(0.0, 0.05 - df["dd252"]) / 0.05
    df["Top_cat_v6"] = near_highs * expit(1.2 * (0.45 * z_rate + 0.30 * _cz(df["delta_ar"]) + 0.15 * df["holo_fracture_z"] + 0.15 * df["z_pe_secular"] - 0.5))

    liq_drain = -df["net_liq_ret63"] + 0.5 * df["nfci"].diff(42).fillna(0.0)
    macro_cross = -df["cu_au_ret63"] + 0.5 * df["dxy_ret63"] + 0.3 * (1.0 - df["global_sync_bull"])
    z_struct_v8 = (0.21 * _cz(credit_imp) + 0.17 * _cz(hyg_imp) + 0.19 * _cz(liq_drain) + 0.13 * _cz(macro_cross)
                   + 0.09 * _cz(spec_imp) + 0.07 * _cz(df["sjv63"]) + 0.07 * df["holo_fracture_z"] + 0.07 * df["inflation_bite"])
    df["S_clock_v8"] = expit(1.3 * z_struct_v8)
    icsa_alarm = np.clip((df["icsa_surge"] - 0.12) / 0.10, 0.0, 1.5)
    worsening = expit(1.5 * z_cred_fast)
    ebp_crisis = expit(1.5 * (z_ebp_lvl - 0.5))
    laminar = expit(1.5 * (_cz(df["er_down42"]) - 0.8))
    df["G_rec_v8"] = np.clip(icsa_alarm * worsening * ebp_crisis * (0.7 + 0.3 * laminar), 0.0, 1.0)
    z_liq = _cz(df["net_liq_ret63"])
    deep8 = np.maximum(0.0, df["dd252"] - 0.065) / 0.085
    relief = -0.35 * df["inflation_bite"] + 0.35 * df["cycle_harmonic_bull"] + 0.30 * df["z_erp_improve"]
    stab8 = expit(-0.65 * z_cred_fast - 0.35 * z_sjv21 + 0.35 * z_liq + 0.25 * holo_rebound + 0.25 * relief)
    df["D_ex_v8"] = np.clip(deep8 * stab8 * (1.0 - df["G_rec_v8"]), 0.0, 1.75)
    df["Top_cat_v8"] = near_highs * expit(1.2 * (0.35 * z_rate + 0.30 * _cz(liq_drain) + 0.20 * _cz(df["delta_ar"])
                                                 + 0.15 * df["z_pe_secular"] + 0.15 * df["inflation_bite"] - 0.45))
    df["static_stress"] = expit(0.35 * _cz(df["vix_clean"]) + 0.30 * _cz(df["credit_level"]) + 0.35 * _cz(df["dd252"]))
    return df.dropna(subset=["rv252", "sma50_200"]).copy()


# ---------------------------------------------------------------- 3. Titan
def _opt(df, col, default):
    return clean_series(df[col], default) if col in df else pd.Series(default, index=df.index)


def build_titan(df: pd.DataFrame) -> pd.DataFrame:
    """df = build_features(...) + colonne facoltative dei grandi fondi:
    dix_raw gex_raw finra_margin aaii_bull_bear cftc_sp_inst (gia' con ritardo di pubblicazione)
    e della struttura opzioni: vol_vix9d vol_vix6m vol_move cred_baa cred_cur."""
    df = df.copy()
    vix_cl = clean_series(df["vix_clean"], 18.0)
    vix3m = clean_series(df["vix3m"], vix_cl * 1.04)
    vix9d = _opt(df, "vol_vix9d", np.nan).fillna(vix_cl * 0.98)
    vix6m = _opt(df, "vol_vix6m", np.nan).fillna(vix3m * 1.03)
    move_idx = _opt(df, "vol_move", 92.0)
    cred_baa = _opt(df, "cred_baa", np.nan).fillna(clean_series(df["credit_level"], 2.0))
    cred_cur = _opt(df, "cred_cur", np.nan).fillna(clean_series(df["y10y"] - df["y3m"], 1.0))

    df["vix9d_vix3m"] = clean_series(vix9d / (vix3m + 1e-4), 0.95)
    df["vix_vix6m"] = clean_series(vix_cl / (vix6m + 1e-4), 0.95)
    df["z_vix_curve_4pt"] = clean_series(0.40 * causal_z(df["vix9d_vix3m"]) + 0.35 * clean_series(df["z_term_inv"]) + 0.25 * causal_z(df["vix_vix6m"]))
    df["z_move"] = causal_z(move_idx)
    df["z_baa_impulse"] = causal_z(cred_baa + 0.8 * cred_baa.diff(42).fillna(0.0))
    df["credit_lead_10d"] = causal_z(clean_series(df["hyg_ief_ret21"]).diff(10).fillna(0.0), window=504)

    zero = pd.Series(0.0, index=df.index)
    has = lambda c, n: (c in df) and df[c].notna().sum() > n
    if has("cftc_sp_inst", 100):
        df["z_cot_inst_exit"] = causal_z(-clean_series(df["cftc_sp_inst"], 0.0), 504) * df["cftc_sp_inst"].notna().astype(float)
    else:
        df["z_cot_inst_exit"] = zero
    if has("dix_raw", 100):
        h = df["dix_raw"].notna().astype(float)
        df["z_short_gamma"] = causal_z(-clean_series(df["gex_raw"], 1e9), 504) * h
        df["z_dark_pool_buy"] = causal_z(clean_series(df["dix_raw"], 0.43).rolling(5, min_periods=1).mean(), 504) * h
    else:
        df["z_short_gamma"] = zero
        df["z_dark_pool_buy"] = zero
    if has("finra_margin", 50):
        m = clean_series(df["finra_margin"], 100000.0)
        dd = (m.rolling(252, min_periods=21).max() - m) / (m.rolling(252, min_periods=21).max() + 1e-4)
        df["z_margin_deleverage"] = causal_z(dd, 1260) * df["finra_margin"].notna().astype(float)
    else:
        df["z_margin_deleverage"] = zero
    if has("aaii_bull_bear", 50):
        ma = clean_series(df["aaii_bull_bear"], 0.0).rolling(15, min_periods=1).mean()
        df["z_aaii_euphoria"] = causal_z(ma, 1260) * df["aaii_bull_bear"].notna().astype(float)
    else:
        df["z_aaii_euphoria"] = zero

    # Radar del Decennio Perduto (Triade assoluta: ERP_CAPE, CAPE, inversione curva, freno di Piketty)
    erp = clean_series(df["erp_cape"], 1.5)
    cape = clean_series(df["cape"], 20.0)
    y10 = clean_series(df["y10y"], 4.0)
    cpi = clean_series(df["cpi_yoy"], 2.5)
    ind6 = clean_series(df["indpro_6m"], 0.01)
    min_yc = clean_series(cred_cur.rolling(504, min_periods=21).min(), 0.5)
    raw = clean_series(0.40 * np.clip((1.2 - erp) / 2.5, -1.5, 2.5) + 0.25 * np.clip((cape - 22.0) / 10.0, -1.5, 2.5)
                       + 0.20 * np.clip(-min_yc / 0.75, -0.5, 2.0)
                       + 0.15 * np.clip(((y10 - cpi) - (ind6 * 200.0)) / 3.5, -1.5, 2.0), 0.0)
    df["lost_decade_radar"] = clean_series(np.clip(expit(1.4 * raw - 0.20) * 100.0, 1.0, 100.0), 50.0)

    OFF = -0.32
    d8 = clean_series(df["D_ex_v8"], 0.0)
    g8 = clean_series(df["G_rec_v8"], 0.0)
    pct = lambda x: clean_series(np.clip(expit(x) * 100.0, 1.0, 100.0), 38.0)
    df["p1_stress"] = pct(OFF + 0.35 * causal_z(df["dd252"]) + 0.30 * causal_z(-df["dist_sma200"]) + 0.20 * causal_z(-df["sma50_200"])
                          + 0.15 * clean_series(df["z_pe_secular"]) - 0.65 * d8)
    df["p2_stress"] = pct(OFF + 0.30 * df["z_baa_impulse"]
                          + 0.40 * (0.5 * (clean_series(df["S_clock_v6"], 0.5) - 0.5) * 3.0 + 0.5 * (clean_series(df["S_clock_v8"], 0.5) - 0.5) * 3.0)
                          - 0.90 * d8 + 0.40 * clean_series(df["Top_cat_v8"]))
    df["p3_stress"] = pct(OFF + 0.22 * causal_z(vix_cl) + 0.23 * df["z_vix_curve_4pt"] + 0.20 * df["z_move"] + 0.12 * df["z_short_gamma"]
                          + 0.12 * clean_series(df["z_vvix_jump"]) + 0.11 * causal_z(df["skew"]))
    df["p4_stress"] = pct(OFF + 0.25 * causal_z(-df["hyg_ief_ret21"]) + 0.20 * causal_z(df["delta_ar"] + 0.4 * df["mahal_z"])
                          + 0.15 * clean_series(df["holo_fracture_z"]) + 0.12 * causal_z(df["er_down42"]) + 0.12 * df["z_cot_inst_exit"]
                          + 0.10 * df["z_margin_deleverage"] + 0.08 * df["z_aaii_euphoria"] - 0.12 * df["z_dark_pool_buy"])
    df["p5_stress"] = pct(OFF + 0.35 * causal_z(df["icsa_surge"])
                          + 0.30 * causal_z(clean_series(df["credit_level"]).diff(42).fillna(0.0) + 0.8 * clean_series(df["ebp"]).diff(63).fillna(0.0))
                          + 0.20 * causal_z(-df["permit_yoy"]) + 0.15 * g8 * 3.0)
    df["p6_stress"] = pct(OFF + 0.35 * causal_z(-df["net_liq_ret63"] + 0.5 * clean_series(df["nfci"]).diff(42).fillna(0.0))
                          + 0.35 * causal_z(-df["cu_au_ret63"] + 0.5 * df["dxy_ret63"])
                          + 0.30 * (0.5 - clean_series(df["global_sync_bull"], 0.5)) * 3.0)
    eq = (df["p1_stress"] + df["p2_stress"] + df["p3_stress"] + df["p4_stress"] + df["p5_stress"] + df["p6_stress"]) / 6.0
    df["super_armor_index"] = clean_series(np.clip(eq - 9.0 * d8 * (1.0 - g8), 1.0, 100.0), 40.0)

    S6, S8 = clean_series(df["S_clock_v6"], 0.5), clean_series(df["S_clock_v8"], 0.5)
    P_now = clean_series(df["P_clock"], 0.5)
    st = clean_series(df["static_stress"], 0.5)
    D6 = clean_series(df["D_ex_v6"], 0.0)
    T8 = clean_series(df["Top_cat_v8"], 0.0)
    cyc = clean_series(df["cycle_harmonic_bull"], 0.0)
    infr = -clean_series(df["inflation_bite"], 0.0)
    erp_i = clean_series(df["z_erp_improve"], 0.0)
    pe_ch = -clean_series(df["z_pe_secular"], 0.0)
    gs = clean_series(df["global_sync_bull"], 0.5)
    v6 = 0.45 * (1.0 - S6) + 0.55 * P_now * (1.0 - S6) - 0.50 * S6
    v8 = 0.45 * (1.0 - S8) + 0.55 * P_now * (1.0 - S8) - 0.50 * S8
    fast = ((1.0 - df["p3_stress"] / 100.0) + (1.0 - df["p6_stress"] / 100.0)
            + expit(clean_series(df["holo_rebound_z"]) + 0.35 * df["credit_lead_10d"] + 0.25 * df["z_dark_pool_buy"] - 0.20 * df["z_cot_inst_exit"])) / 3.0
    dir_sec = 0.40 * (1.0 - st) + 0.30 * expit(2.0 * v6) + 0.20 * expit(1.5 * D6 + 0.3 * cyc) + 0.10 * expit(pe_ch)
    dir_mod = (0.25 * (1.0 - st) + 0.25 * expit(2.0 * v8)
               + 0.40 * expit(1.90 * d8 - 1.1 * T8 + 0.35 * cyc + 0.35 * infr + 0.25 * erp_i - 0.15 * df["z_margin_deleverage"] - 0.12 * df["z_cot_inst_exit"])
               + 0.10 * gs)
    is_mod = (df.index >= pd.Timestamp("2004-06-01")).astype(float)
    w_mod = np.clip(0.20 + 0.55 * is_mod + 0.20 * np.clip(d8, 0.0, 1.0), 0.20, 0.90)
    slow = (1.0 - w_mod) * dir_sec + w_mod * dir_mod
    bull = 0.30 * fast + 0.70 * slow
    df["armor_index"] = clean_series(np.clip(40.5 + (100.0 * (1.0 - bull) - 48.0) * 0.65, 1.0, 100.0), 40.0)
    for n, tag in ((5, "1w"), (21, "1m"), (63, "3m"), (126, "6m")):
        df[f"armor_ma_{tag}"] = df["armor_index"].rolling(n, min_periods=1).mean()
        df[f"super_ma_{tag}"] = df["super_armor_index"].rolling(n, min_periods=1).mean()
    return df


REQUIRED_COLS = [
    "sp500", "vix_clean", "vix3m", "credit_level", "y10y", "y3m", "z_term_inv", "hyg_ief_ret21", "dd252", "dist_sma200", "sma50_200",
    "z_pe_secular", "D_ex_v8", "G_rec_v8", "S_clock_v6", "S_clock_v8", "Top_cat_v8", "z_vvix_jump", "skew", "delta_ar", "mahal_z",
    "holo_fracture_z", "er_down42", "icsa_surge", "ebp", "permit_yoy", "net_liq_ret63", "nfci", "cu_au_ret63", "dxy_ret63",
    "global_sync_bull", "P_clock", "static_stress", "D_ex_v6", "cycle_harmonic_bull", "inflation_bite", "z_erp_improve",
    "holo_rebound_z", "erp_cape", "cape", "cpi_yoy", "indpro_6m"]


# ---------------------------------------------------------------- probabilita'
def walk_forward(df: pd.DataFrame, horizon: int = 126, dd_thresh: float = 0.10, include_today: bool = False, step: int = 10) -> pd.DataFrame:
    """Walk-forward di v40 (calo >= dd_thresh nei prossimi `horizon` giorni, e rialzo). Con include_today=True
    aggiunge l'ultima riga di df (previsione per OGGI: addestramento solo su esiti gia' noti)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    prices = clean_series(df["sp500"], 100.0).values
    n = len(df)
    fwd_ret = np.full(n, np.nan)
    fwd_dd = np.full(n, np.nan)
    for i in range(n - horizon):
        path = prices[i + 1:i + 1 + horizon]
        fwd_ret[i] = path[-1] / prices[i] - 1.0
        fwd_dd[i] = (prices[i] - path.min()) / prices[i]
    df = df.copy()
    df["fwd_ret"] = fwd_ret
    df["y_dd"] = (fwd_dd >= dd_thresh).astype(float)
    df["y_up"] = (fwd_ret > 0.0).astype(float)

    fast_cols = ["rv21", "rv63", "rv_ratio", "dd252", "dist_sma200", "sma50_200", "mom63", "worst21", "z_vix_curve_4pt", "z_sjv5"]
    start = int(np.searchsorted(df.index, pd.Timestamp("1994-01-03")))
    idxs = list(range(start, n - horizon, step))
    if include_today:
        idxs.append(n - 1)
    embargo = 5 if horizon <= 21 else 21
    w6 = 0.35 if horizon <= 63 else (0.75 if horizon <= 126 else 1.10)
    w8 = 0.45 if horizon <= 63 else (0.95 if horizon <= 126 else 1.40)
    wt = 0.40 if horizon <= 63 else (0.55 if horizon <= 126 else 0.70)
    k = np.arange(1, horizon + 1)
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    out, log = [], []

    def basis(sub, sc):
        P, S = sub["P_clock"].values, sub[sc].values
        sj = np.maximum(0.0, sub["sjv21"].values)
        return safe_mat(np.column_stack([1.0 - S, S * (1.0 + 0.5 * sj), P * (1.0 - S), P * S]))

    for idx in idxs:
        te = idx - horizon - embargo
        if te < 1000:
            continue
        tr = df.iloc[:te]
        y = tr["y_dd"].values
        if y.sum() < 15 or len(np.unique(y)) < 2:
            continue
        row = df.iloc[idx]
        base = float(y.mean())
        lb = np.log(base / (1.0 - base + 1e-8))
        s_init = float(row["har_vix_vol"])
        s_bar = float(tr["rv252"].median())
        vp = (s_bar ** 2 + (0.975 ** k) * (s_init ** 2 - s_bar ** 2)) / 252.0
        p_fhs = float(np.clip(base * (np.sqrt(vp.sum()) / (s_bar * np.sqrt(horizon / 252.0))) ** 1.30, 0.01, 0.95))

        sc = StandardScaler()
        clf = LogisticRegression(C=0.08, max_iter=200)
        clf.fit(sc.fit_transform(safe_mat(tr[fast_cols].values)), y)
        p_a1 = float(clf.predict_proba(sc.transform(safe_mat(row[fast_cols].values.reshape(1, -1))))[0, 1])
        fb = 0.45 * p_a1 + 0.55 * p_fhs
        sk = 0.64 if horizon == 21 else 0.78
        p_fast = float(expit(lb + sk * (lg(fb) - lb)))

        def core(sc_name, w_ex, d_col, t_col, t_sign_w):
            c = LogisticRegression(C=0.05, max_iter=200)
            c.fit(basis(tr, sc_name), y)
            pr = float(c.predict_proba(basis(df.iloc[idx:idx + 1], sc_name))[0, 1])
            return float(expit(lb + 0.65 * (lg(pr) - lb) - w_ex * float(row[d_col]) + t_sign_w * float(row[t_col])))

        p6 = core("S_clock_v6", w6, "D_ex_v6", "Top_cat_v6", 0.45)
        p8 = core("S_clock_v8", w8, "D_ex_v8", "Top_cat_v8", wt)

        mat = [m for m in log if m["idx"] <= idx - horizon]
        if len(mat) >= 20 and df.index[idx] >= pd.Timestamp("2004-06-01"):
            rec = mat[-35:]
            la = np.mean([(m["y"] - m["a"]) ** 2 for m in rec])
            lb2 = np.mean([(m["y"] - m["b"]) ** 2 for m in rec])
            wb = float(np.clip(0.35 + 0.55 * expit(38.0 * (la - lb2) + 1.4 * float(row["D_ex_v8"])), 0.25, 0.92))
        else:
            wb = 0.15
        p_macro = (1.0 - wb) * p6 + wb * p8
        p_fc = float(expit(lb + 0.72 * (lg(p_fhs) - lb)))
        if horizon <= 7:
            p_dd = 0.65 * p_fhs + 0.35 * p_fast
        elif horizon <= 21:
            p_dd = p_fast
        elif horizon <= 63:
            p_dd = 0.45 * p_fc + 0.55 * p_macro
        else:
            p_dd = p_macro

        st = float(row["static_stress"])
        b3, b6, b0 = 1.0 - float(row["armor_ma_3m"]) / 100.0, 1.0 - float(row["armor_ma_6m"]) / 100.0, 1.0 - float(row["armor_index"]) / 100.0
        if horizon <= 7:
            up = 0.40 * (1.0 - st) + 0.35 * float(row["short_term_carry_7d"]) + 0.25 * b0
        elif horizon <= 21:
            up = 0.35 * (1.0 - p_macro) + 0.35 * b6 + 0.30 * b3
        elif horizon <= 63:
            up = 0.45 * b0 + 0.35 * b3 + 0.20 * b6
        elif horizon <= 126:
            up = 0.45 * b0 + 0.30 * b3 + 0.25 * b6
        else:
            up = 0.40 * b0 + 0.30 * b3 + 0.30 * b6
        log.append({"idx": idx, "y": float(df["y_dd"].iloc[idx]), "a": p6, "b": p8})
        out.append({"date": df.index[idx], "real_ret": float(df["fwd_ret"].iloc[idx]), "y_dd": float(df["y_dd"].iloc[idx]),
                    "y_up": float(df["y_up"].iloc[idx]), "hist_base_dd": base, "p_dd_fhs": p_fhs, "p_dd_v40": float(p_dd),
                    "p_up_fhs": 1.0 - p_fhs, "p_up_v40": float(up)})
    return pd.DataFrame(out).set_index("date")


def previsioni_oggi(df: pd.DataFrame) -> dict:
    """Probabilita' di calo e di rialzo per OGGI sui 5 orizzonti (ultima riga di df)."""
    res = {}
    for h, th, nome in ORIZZONTI:
        r = walk_forward(df, h, th, include_today=True)
        last = r.iloc[-1]
        res[nome] = {"calo": round(float(last["p_dd_v40"]), 4), "rialzo": round(float(last["p_up_v40"]), 4),
                     "soglia_calo": th, "data": str(r.index[-1].date())}
    return res
