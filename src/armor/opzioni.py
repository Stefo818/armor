# -*- coding: utf-8 -*-
"""Posizionamento nelle opzioni su SPY (PROTOCOLLO_MINIMI.md, parte K): rapporto put/call, «muri» di call e put, gamma netta stimata e livello di cambio di segno.
Dati correnti di Yahoo (nessuna storia): ogni giorno si salva una riga nel diario; dopo 60 giorni si confronta il movimento del giorno dopo con gamma positiva e negativa.
Ipotesi dichiarata: gli operatori hanno venduto call e comprato put (come nei modelli pubblici di «gamma exposure»): è una stima, non un dato osservato."""
import json
from datetime import date, datetime

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "opzioni_spy.json"
DIARIO = DATA / "opzioni_diario.csv"
MAX_SCADENZE = 8
MAX_GIORNI = 45
COLS = ["date", "spot_spy", "sp500", "gex_mld", "flip_indice", "pc_oi", "muro_call", "muro_put"]


def _phi(x):
    return np.exp(-0.5 * x * x) / np.sqrt(2 * np.pi)


def gamma_bs(S, K, T, iv):
    """Gamma di Black-Scholes (tassi e dividendi trascurati)."""
    iv = np.maximum(iv, 1e-3)
    T = np.maximum(T, 1.0 / 365.0)
    d1 = (np.log(S / K) + 0.5 * iv ** 2 * T) / (iv * np.sqrt(T))
    return _phi(d1) / (S * iv * np.sqrt(T))


def gex(chain: pd.DataFrame, S: float) -> float:
    """Gamma netta in dollari per un movimento dell'1% (call +, put -)."""
    g = gamma_bs(S, chain["strike"].values, chain["T"].values, chain["iv"].values)
    segno = np.where(chain["tipo"].values == "C", 1.0, -1.0)
    return float((segno * g * chain["oi"].values * 100 * S * S * 0.01).sum())


def flip(chain: pd.DataFrame, S: float) -> float | None:
    """Prezzo (di SPY) in cui la gamma netta cambia segno, cercato tra -10% e +10% dal prezzo di oggi."""
    grid = np.linspace(0.90 * S, 1.10 * S, 81)
    v = np.array([gex(chain, x) for x in grid])
    cross = np.where(np.sign(v[:-1]) * np.sign(v[1:]) < 0)[0]
    if not len(cross):
        return None
    i = cross[np.argmin(np.abs(grid[cross] - S))]
    return float(grid[i] - v[i] * (grid[i + 1] - grid[i]) / (v[i + 1] - v[i]))


def analizza(chain: pd.DataFrame, S: float, sp: float) -> dict:
    """Da una tabella (strike, tipo C/P, oi, iv, T) calcola le misure. `sp` = livello dell'indice S&P 500 per convertire gli strike di SPY."""
    f = sp / S
    c, p = chain[chain["tipo"] == "C"], chain[chain["tipo"] == "P"]
    vicino = chain[(chain["strike"] >= 0.9 * S) & (chain["strike"] <= 1.1 * S)]
    cs = vicino[vicino["tipo"] == "C"].groupby("strike")["oi"].sum()
    ps = vicino[vicino["tipo"] == "P"].groupby("strike")["oi"].sum()
    muro_c = float(cs[cs.index >= S].idxmax()) if len(cs[cs.index >= S]) else None
    muro_p = float(ps[ps.index <= S].idxmax()) if len(ps[ps.index <= S]) else None
    fl = flip(chain, S)
    g = gex(chain, S)
    bins = sorted(set(vicino["strike"]))
    ladder = [[round(k * f, 0), int(cs.get(k, 0)), int(ps.get(k, 0))] for k in bins if 0.93 * S <= k <= 1.07 * S]
    grid = np.linspace(0.92 * S, 1.08 * S, 33)
    curva = [[round(x * f, 0), round(gex(chain, x) / 1e9, 2)] for x in grid]
    return {"spot_spy": round(S, 2), "sp500": round(sp, 1), "gex_mld": round(g / 1e9, 2), "flip_indice": None if fl is None else round(fl * f, 0), "flip_distanza": None if fl is None else round(fl / S - 1, 4),
            "pc_oi": round(float(p["oi"].sum() / max(c["oi"].sum(), 1)), 3), "muro_call": None if muro_c is None else round(muro_c * f, 0), "muro_put": None if muro_p is None else round(muro_p * f, 0),
            "oi_call": int(c["oi"].sum()), "oi_put": int(p["oi"].sum()), "scadenze": int(chain["scad"].nunique()), "ladder": ladder, "curva_gex": curva}


def scarica(oggi: date | None = None) -> tuple[pd.DataFrame, float, pd.Series]:
    import yfinance as yf
    oggi = pd.Timestamp(oggi or date.today())
    t = yf.Ticker("SPY")
    h = t.history(period="10d")["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    S = float(h.iloc[-1])
    rows = []
    n = 0
    for ex in t.options:
        giorni = (pd.Timestamp(ex) - oggi).days
        if giorni < 0 or giorni > MAX_GIORNI:
            continue
        ch = t.option_chain(ex)
        for tipo, df in (("C", ch.calls), ("P", ch.puts)):
            d = df[["strike", "openInterest", "impliedVolatility"]].dropna()
            d = d[(d["openInterest"] > 0) & (d["impliedVolatility"] > 0.01)]
            for k, oi, iv in d.itertuples(index=False):
                rows.append((ex, float(k), tipo, float(oi), float(iv), max(giorni, 0.5) / 365.0))
        n += 1
        if n >= MAX_SCADENZE:
            break
    chain = pd.DataFrame(rows, columns=["scad", "strike", "tipo", "oi", "iv", "T"])
    if chain.empty:
        raise RuntimeError("nessuna opzione scaricata")
    return chain, S, h


def registra(r: dict, data: str) -> None:
    try:
        d = pd.read_csv(DIARIO)
    except Exception:  # noqa: BLE001
        d = pd.DataFrame(columns=COLS)
    if data in set(d["date"].astype(str)):
        return
    row = {"date": data, "spot_spy": r["spot_spy"], "sp500": r["sp500"], "gex_mld": r["gex_mld"], "flip_indice": r["flip_indice"], "pc_oi": r["pc_oi"], "muro_call": r["muro_call"], "muro_put": r["muro_put"]}
    pd.concat([d, pd.DataFrame([row])])[COLS].to_csv(DIARIO, index=False)


def verifica(diario: pd.DataFrame, sp: pd.Series) -> dict:
    """Dopo almeno 60 giorni: movimento assoluto medio del giorno dopo con gamma positiva e negativa."""
    if diario is None or len(diario) < 60:
        return {"giorni": 0 if diario is None else int(len(diario)), "pronto": False, "mancano": max(60 - (0 if diario is None else len(diario)), 0)}
    d = diario.copy()
    d["date"] = pd.to_datetime(d["date"])
    r = sp.pct_change().abs()
    nxt = []
    for dt in d["date"]:
        pos = r.index.searchsorted(dt, side="right")
        nxt.append(float(r.iloc[pos]) if pos < len(r) else np.nan)
    d["mov"] = nxt
    d = d.dropna(subset=["mov"])
    pos_, neg_ = d[d["gex_mld"] >= 0]["mov"], d[d["gex_mld"] < 0]["mov"]
    return {"giorni": int(len(d)), "pronto": True, "mov_gamma_positiva": None if not len(pos_) else round(float(pos_.mean()), 4), "n_pos": int(len(pos_)),
            "mov_gamma_negativa": None if not len(neg_) else round(float(neg_.mean()), 4), "n_neg": int(len(neg_))}


def aggiorna(log=print) -> dict | None:
    sp = store.load("sp500").dropna()
    try:
        chain, S, h = scarica()
        rif = h[h.index <= sp.index[-1]]
        # livello dell'S&P 500 equivalente al prezzo di SPY di oggi: rapporto misurato nello stesso giorno
        sp_eq = S * float(sp.iloc[-1]) / float(rif.iloc[-1]) if len(rif) else S * 10.0
        r = analizza(chain, S, sp_eq)
        r["data"] = str(pd.Timestamp.now().date())
        r["ora"] = datetime.utcnow().strftime("%H:%M UTC")
        registra(r, r["data"])
    except Exception as e:  # noqa: BLE001
        log("[opzioni] non scaricate: " + str(e)[:100])
        return carica()
    try:
        r["verifica"] = verifica(pd.read_csv(DIARIO), sp)
    except Exception:  # noqa: BLE001
        r["verifica"] = {"giorni": 0, "pronto": False, "mancano": 60}
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    log(f"[opzioni] gamma netta {r['gex_mld']:+.1f} mld, put/call {r['pc_oi']:.2f}, muro call {r['muro_call']}, muro put {r['muro_put']}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
