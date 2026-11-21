# -*- coding: utf-8 -*-
"""Radar sistemico (MSA v3, specifica del 21 novembre 2026, provata con PROTOCOLLO_SISTEMICO.md).
Regime strutturale (5 regimi, soglie fisse, ritardi di pubblicazione), 3 sensori veloci per regime, barometro rame/oro + dollaro,
doppio orizzonte (1-3 mesi e 6 mesi). Le opzioni istituzionali sono mostrate solo come informazione: l'archivio ha pochi giorni e non è provabile."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import store
from .config import ARCHIVE, DATA

FILE = DATA / "modello_sistemico.json"
STORIA = DATA / "modello_sistemico_storia.csv"

LAGS = {"dgs10": 1, "real10y": 1, "baa10y": 1, "t10y3m": 1, "icsa": 6, "nfci_credit": 6, "stlfsi": 7, "net_liq_13w": 3, "cpi_yoy": 45, "cpi_yoy_lungo": 45, "unrate": 37, "sahm": 37,
        "pe_m": 60, "cape_m": 60, "cape": 60, "sloos": 40, "baa_m": 32, "gs10_m": 32}

REGIME_META = {
    "RECES_DOMANDA": {"nome": "Domanda che si indebolisce", "corto": "Domanda debole", "ignorati": "Valutazioni e paura bassa all'inizio di una recessione: spesso ingannano.",
                      "sensori": ["Sussidi di disoccupazione e settori ciclici", "Banche e credito alle imprese", "Curva della paura"]},
    "STRETTA_CREDITO": {"nome": "Credito che si restringe", "corto": "Credito stretto", "ignorati": "Rimbalzi di breve periodo: spesso trappole finché il credito non si rilassa.",
                        "sensori": ["Banche regionali e credito alle imprese", "Curva della paura", "Rame, oro e dollaro"]},
    "SHOCK_OFFERTA": {"nome": "Inflazione e tassi in pressione", "corto": "Inflazione e tassi", "ignorati": "Il rapporto prezzo/utili sembra basso perché gli utili sono gonfiati dall'inflazione.",
                      "sensori": ["Tassi reali e legame azioni-obbligazioni", "Velocità dei tassi a 10 anni", "Curva della paura"]},
    "CARO_TASSI_LIQ": {"nome": "Mercato caro con tassi alti", "corto": "Caro con tassi alti", "ignorati": "Lavoro e crescita forti: arrivano in ritardo e non proteggono da correzioni sui prezzi.",
                       "sensori": ["Velocità dei tassi a 10 anni e volatilità dei titoli di Stato", "Tecnologia contro il resto del mercato", "Curva della paura"]},
    "CALMA_STRUTTURALE": {"nome": "Nessuno squilibrio di fondo", "corto": "Calma di fondo", "ignorati": "Indicatori lenti: nessuno squilibrio attivo, rumore smorzato.",
                          "sensori": ["Curva della paura", "Credito alle imprese", "Rame, oro e dollaro"]},
}


def _lagged(name: str, idx: pd.DatetimeIndex, ffill_lim: int = 90) -> pd.Series:
    try:
        s = store.load(name).dropna()
    except Exception:  # noqa: BLE001
        return pd.Series(np.nan, index=idx)
    if s.empty:
        return pd.Series(np.nan, index=idx)
    s = s.copy()
    s.index = s.index + pd.Timedelta(days=LAGS.get(name, 0))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(s.index.union(idx)).ffill(limit=ffill_lim).reindex(idx)


def _exp_pct(s: pd.Series, min_p: int = 504) -> pd.Series:
    return s.expanding(min_periods=min_p).rank(pct=True).fillna(0.5) * 100.0


def opzioni_info() -> dict:
    """Informazione (NON entra nel punteggio): salto della copertura contro i crolli nelle opzioni sull'indice, dall'archivio quotidiano."""
    try:
        df = pd.read_csv(ARCHIVE / "spy_options_summary.csv").dropna(subset=["spot"])
        u, p = df.iloc[-1], df.iloc[-2]
        return {"giorni_archivio": int(len(df)), "put_skew_80": float(u["put_skew_80"]), "put_skew_80_prec": float(p["put_skew_80"]), "pc_oi": float(u["pc_open_interest"]), "data": str(u["date"])}
    except Exception:  # noqa: BLE001
        return {}


def calcola_serie(sp_override: pd.Series | None = None, titan_df: pd.DataFrame | None = None) -> pd.DataFrame:
    sp = (store.load("sp500") if sp_override is None else sp_override).dropna().loc["1995-01-01":]
    idx = sp.index
    D = pd.DataFrame(index=idx)
    for k in ("vix", "vix3m", "vvix", "move", "dgs10", "real10y", "baa10y", "spy", "rsp", "smh", "kre", "iyt", "hyg", "ief", "sec_xly", "sec_xlp", "wti", "copper", "gold", "dxy"):
        D[k] = _lagged(k, idx, ffill_lim=10)
    for k in ("icsa", "nfci_credit", "stlfsi", "net_liq_13w"):
        D[k] = _lagged(k, idx, ffill_lim=20)
    for k in ("cpi_yoy", "cpi_yoy_lungo", "unrate", "sahm", "pe_m", "cape_m", "cape", "sloos", "baa_m", "gs10_m"):
        D[k] = _lagged(k, idx, ffill_lim=130)
    cape = D["cape_m"].combine_first(D["cape"])
    cpi = D["cpi_yoy"].combine_first(D["cpi_yoy_lungo"])
    baa = D["baa10y"].combine_first(D["baa_m"] - D["gs10_m"])
    vix3m = D["vix3m"].fillna(D["vix"] * 1.04)
    sahm = D["sahm"].combine_first(D["unrate"].rolling(63, min_periods=20).mean() - D["unrate"].rolling(252, min_periods=120).min()).fillna(0.0)
    icsa_ratio = D["icsa"].rolling(20, min_periods=5).mean() / (D["icsa"].rolling(252, min_periods=60).min() + 1.0)

    cond_reces = (sahm >= 0.35) | (icsa_ratio >= 1.20)
    cond_cred = (D["sloos"].fillna(0) > 20.0) | (baa.fillna(0) > 2.45) | (D["nfci_credit"].fillna(-1) > 0.15)
    cond_supp = ((cpi.fillna(0) > 3.8) & (cpi.diff(126).fillna(0) > 0.30)) | (D["wti"].pct_change(126).fillna(0) > 0.30)
    cond_val = ((cape.fillna(0) > 27.0) | (D["pe_m"].fillna(0) > 21.0)) & (
        (D["dgs10"].fillna(0) > 4.20) | (D["real10y"].fillna(0) > 1.50) | (D["dgs10"].diff(126).fillna(0) > 0.50) | (D["net_liq_13w"].fillna(0) < -3.0))
    regime = pd.Series("CALMA_STRUTTURALE", index=idx)
    regime[cond_val] = "CARO_TASSI_LIQ"
    regime[cond_supp] = "SHOCK_OFFERTA"
    regime[cond_cred] = "STRETTA_CREDITO"
    regime[cond_reces] = "RECES_DOMANDA"

    if titan_df is None:
        titan_path = DATA / "titan_storia.csv"
        titan_df = pd.read_csv(titan_path, parse_dates=["date"]).set_index("date") if titan_path.exists() else None
    if titan_df is not None:
        titan = titan_df.reindex(idx)
        t_p2, t_p4, t_p5, t_p6 = (_exp_pct(titan[c]) for c in ("p2_stress", "p4_stress", "p5_stress", "p6_stress"))
        sup_pct = _exp_pct(titan["super_armor_index"])
    else:
        t_p2 = t_p4 = t_p5 = t_p6 = sup_pct = pd.Series(50.0, index=idx)

    s_rate = 0.60 * _exp_pct(D["dgs10"].diff(10).fillna(0)) + 0.40 * _exp_pct(D["move"].fillna(85))
    rel_rsp = (D["rsp"] / D["spy"]).pct_change(10).fillna(0)
    rel_smh = (D["smh"] / D["spy"]).pct_change(10).fillna(0)
    s_lead = _exp_pct(-np.minimum(rel_rsp, rel_smh * 0.55))
    s_vol = 0.65 * _exp_pct(D["vix"] / (vix3m + 1e-4)) + 0.35 * _exp_pct(D["vvix"].fillna(90))
    sb_corr = D["spy"].pct_change().fillna(0).rolling(21, min_periods=10).corr(D["ief"].pct_change().fillna(0)).fillna(0)
    s_infl = 0.50 * _exp_pct(D["real10y"].diff(10).fillna(D["dgs10"].diff(10).fillna(0))) + 0.50 * _exp_pct(sb_corr)
    s_cred = 0.45 * _exp_pct(-(D["hyg"] / D["ief"]).pct_change(10).fillna(0)) + 0.35 * _exp_pct(-(D["kre"] / D["spy"]).pct_change(10).fillna(rel_rsp)) + 0.20 * _exp_pct(baa.diff(21).fillna(0))
    rel_cyc = 0.5 * (D["iyt"] / D["spy"]).pct_change(10).fillna(0) + 0.5 * (D["sec_xly"] / D["sec_xlp"]).pct_change(10).fillna(0)
    s_lab = 0.55 * _exp_pct(icsa_ratio) + 0.45 * _exp_pct(-rel_cyc)
    s_cross = 0.50 * _exp_pct(-(D["copper"] / D["gold"]).pct_change(21).fillna(0)) + 0.50 * _exp_pct(D["dxy"].pct_change(21).fillna(0))

    msa = pd.Series(np.nan, index=idx)
    m_v, m_s, m_c, m_r, m_k = (regime == "CARO_TASSI_LIQ"), (regime == "SHOCK_OFFERTA"), (regime == "STRETTA_CREDITO"), (regime == "RECES_DOMANDA"), (regime == "CALMA_STRUTTURALE")
    msa[m_v] = 0.30 * s_rate[m_v] + 0.25 * s_lead[m_v] + 0.15 * s_vol[m_v] + 0.30 * (0.5 * t_p2[m_v] + 0.5 * t_p6[m_v])
    msa[m_s] = 0.35 * s_infl[m_s] + 0.25 * s_rate[m_s] + 0.15 * s_vol[m_s] + 0.25 * t_p6[m_s]
    msa[m_c] = 0.40 * s_cred[m_c] + 0.20 * s_vol[m_c] + 0.40 * (0.5 * t_p2[m_c] + 0.5 * t_p4[m_c])
    msa[m_r] = 0.40 * s_lab[m_r] + 0.30 * s_cred[m_r] + 0.30 * t_p5[m_r]
    msa[m_k] = 0.45 * (0.50 * s_vol[m_k] + 0.50 * s_cred[m_k])

    out = pd.DataFrame(index=idx)
    out["regime"] = regime
    out["msa"] = msa.round(1)
    for n, s in (("s_rate", s_rate), ("s_lead", s_lead), ("s_vol", s_vol), ("s_infl", s_infl), ("s_cred", s_cred), ("s_lab", s_lab), ("s_cross", s_cross)):
        out[n] = s.round(1)
    out["score_3m"] = (0.85 * (0.70 * msa + 0.30 * sup_pct) + 0.15 * s_cross).round(1)
    out["score_6m"] = (0.85 * (0.30 * msa + 0.70 * sup_pct) + 0.15 * s_cross).round(1)
    out["dd252"] = ((sp / sp.rolling(252).max() - 1.0) * 100.0).round(2)
    return out


PROVA = DATA / "sistemico_prova.json"


def _classe(v: float) -> str:
    return "bad" if v >= 75 else ("warn" if v >= 60 else "ok")


def aggiorna(log=print) -> dict:
    df = calcola_serie()
    ult = df.iloc[-1]
    reg = str(ult["regime"])
    meta = REGIME_META[reg]
    sensori = {"CARO_TASSI_LIQ": [("s_rate", 0), ("s_lead", 1), ("s_vol", 2)], "SHOCK_OFFERTA": [("s_infl", 0), ("s_rate", 1), ("s_vol", 2)], "STRETTA_CREDITO": [("s_cred", 0), ("s_vol", 1), ("s_cross", 2)],
               "RECES_DOMANDA": [("s_lab", 0), ("s_cred", 1), ("s_vol", 2)], "CALMA_STRUTTURALE": [("s_vol", 0), ("s_cred", 1), ("s_cross", 2)]}[reg]
    res = {"data": str(df.index[-1].date()), "regime": reg, "regime_nome": meta["nome"], "regime_corto": meta["corto"], "ignorati": meta["ignorati"],
           "sensori": [{"nome": meta["sensori"][i], "valore": float(ult[c]), "classe": "bad" if ult[c] >= 70 else ("warn" if ult[c] >= 50 else "ok")} for c, i in sensori],
           "score_3m": float(ult["score_3m"]), "score_6m": float(ult["score_6m"]), "dd252": float(ult["dd252"]), "opzioni": opzioni_info(), "prova": json.loads(PROVA.read_text(encoding="utf-8")) if PROVA.exists() else {}}
    FILE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    df.tail(2520).to_csv(STORIA, index_label="date")
    log(f"[sistemico] {res['data']} · {meta['corto']} · 1-3 mesi {res['score_3m']:.0f} · 6 mesi {res['score_6m']:.0f}")
    return res


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def oggi_html() -> str:
    """Scheda compatta «Radar di fondo» (contesto, non previsione: l'etichetta della prova è «Non coerente», vedi PROTOCOLLO_SISTEMICO.md)."""
    import html as _h
    d = carica()
    if not d:
        return ""
    s3, s6 = d["score_3m"], d["score_6m"]
    cls = _classe(s3)
    tit = "Pressione di fondo alta" if s3 >= 60 else ("Pressione di fondo in crescita" if s3 >= 45 else "Pressione di fondo bassa")
    sens = "".join(f"<li>{_h.escape(s['nome'])}: <b>{'alto' if s['valore'] >= 70 else ('medio' if s['valore'] >= 50 else 'basso')}</b></li>" for s in d.get("sensori", []))
    p = d.get("prova") or {}
    odds = ""
    if p.get("precisione") and p.get("frequenza_base"):
        odds = (f"In passato, quando il punteggio a 1-3 mesi era da 60 in su, nei 3 mesi seguenti l'indice ha perso almeno l'8% circa 1 volta su {round(1 / p['precisione'])} "
                f"(normalmente 1 volta su {round(1 / p['frequenza_base'])}). ")
    o = d.get("opzioni") or {}
    opz = ""
    if o.get("put_skew_80") and o.get("put_skew_80_prec"):
        opz = (f"<div class='rs-mu'>Opzioni sull'indice: il costo delle assicurazioni contro un crollo del 20% è passato da {o['put_skew_80_prec']:.2f} a {o['put_skew_80']:.2f} nell'ultimo giorno. "
               f"Archivio di soli {o['giorni_archivio']} giorni: non provabile, non entra nel punteggio.</div>")
    return (
        "<style>.rs{border:1px solid var(--bd);border-left-width:5px;border-radius:12px;background:var(--card);padding:8px 12px;margin:8px 0}.rs.ok{border-left-color:var(--ok)}.rs.warn{border-left-color:var(--warn,#f59e0b)}.rs.bad{border-left-color:var(--bad)}"
        ".rs-tit{font-size:15px;font-weight:700}.rs-mu{font-size:12px;color:var(--mu);line-height:1.4;margin-top:4px}.rs ul{margin:4px 0 0;padding-left:18px;font-size:13px}</style>"
        f"<div class='rs {cls}'><div class='rs-tit'>Radar di fondo · {tit} ({s3:.0f} su 100 a 1-3 mesi, {s6:.0f} a 6 mesi)</div>"
        f"<div class='rs-mu' style='font-size:13px'>Regime di oggi: <b>{_h.escape(d['regime_nome'])}</b>. Cosa guarda ora:</div><ul>{sens}</ul>"
        f"<div class='rs-mu'>{odds}Non guarda: {_h.escape(d.get('ignorati', ''))}</div>{opz}"
        "<div class='rs-mu'>Prova fatta una volta sola sui dati dal 1997: non fa meglio dell'Indice Armor, quindi è un contesto in più, non una previsione e non manda notifiche sul telefono.</div></div>")
