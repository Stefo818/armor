"""Costruzione delle variabili dell'Indice crollo secondo PROTOCOLLO_INDICE_CROLLO.md, parti 2 e 3.

Nessuna variabile usa dati non pubblici quel giorno. I ritardi sono quelli della parte 2.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from armor import store  # noqa: E402

MIN_STORIA = 500   # protocollo parte 3: almeno 500 osservazioni precedenti


def _lag(s: pd.Series, giorni: int) -> pd.Series:
    """Ritardo di pubblicazione in giorni di calendario (parte 2)."""
    if giorni <= 0:
        return s
    out = s.copy()
    out.index = out.index + pd.Timedelta(days=giorni)
    return out


def _pct(s: pd.Series) -> pd.Series:
    """Percentile su storia crescente, mai guardando il futuro (parte 3)."""
    r = s.expanding(min_periods=MIN_STORIA).rank(pct=True)
    return r * 100.0


def carica(sp_override: pd.Series | None = None) -> pd.DataFrame:
    sp = store.load("sp500").dropna() if sp_override is None else sp_override.dropna()
    cal = sp.index  # il calendario di borsa comanda

    def g(sid, lag=0):
        return _lag(store.load(sid).dropna(), lag).reindex(cal).ffill()

    vix, vix3m = g("vix"), g("vix3m")
    skew, pput = g("skew"), g("pput")
    baa = g("baa10y", 1)
    d10, d2 = g("dgs10", 1), g("dgs2", 1)
    move = g("move")
    semi, small = g("rel_semi"), g("rel_small")
    banche, rameoro = g("rel_banche"), g("rel_rame_oro")
    armor = g("armor_index")

    r = np.log(sp).diff()
    ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean()
    sotto200 = (sp < ma200).astype(float)
    # da quante sedute la media a 200 giorni e' rotta (0 se non e' rotta)
    grp = (sotto200 != sotto200.shift()).cumsum()
    rotta_da = sotto200.groupby(grp).cumsum() * sotto200

    X = pd.DataFrame(index=cal)
    # 1 livello della paura
    X["f1_paura"] = _pct(vix)
    # 2 salto della paura
    X["f2_salto"] = (_pct(vix / vix.shift(5) - 1) + _pct(vix / vix.shift(10) - 1)) / 2
    # 3 curva della paura (sopra 1 = allarme); prima del 2006 non esiste: resta mancante
    X["f3_curva"] = _pct(vix / vix3m)
    # 4 costo delle protezioni
    X["f4_protez"] = (_pct(skew) + _pct(pput)) / 2
    # 5 credito: livello e variazione a 20 sedute
    X["f5_credito"] = (_pct(baa) + _pct(baa - baa.shift(20))) / 2
    # 6 tassi
    X["f6_tassi"] = (_pct((d10 - d10.shift(5)).abs()) + _pct((d10 - d10.shift(20)).abs()) + _pct(-(d10 - d2))) / 3
    # 7 tendenza (piu' alto = peggio)
    X["f7_tendenza"] = (_pct(-(sp / ma50 - 1)) + _pct(-(sp / ma200 - 1)) + _pct(rotta_da)) / 3
    # 8 perdita in corso dal massimo a 12 mesi
    X["f8_perdita"] = _pct(-(sp / sp.rolling(252, min_periods=60).max() - 1))
    # 9 volatilita' realizzata, totale e solo parte negativa
    X["f9_volat"] = (_pct(r.rolling(20).std()) + _pct(r.clip(upper=0).rolling(20).std())) / 2
    # 10 rotazione difensiva (forza relativa in calo = allarme)
    rot = []
    for s in (semi, small, banche, rameoro):
        rot.append(_pct(-(s / s.rolling(60).mean() - 1)))
    X["f10_rotaz"] = pd.concat(rot, axis=1).mean(axis=1)
    # 11 volatilita' dei titoli di Stato
    X["f11_bond"] = _pct(move)
    # 12 Indice Armor
    X["f12_armor"] = _pct(armor)

    X["sp500"] = sp
    X["armor_grezzo"] = armor
    return X


def bersagli(sp: pd.Series) -> pd.DataFrame:
    def y(n, soglia):
        fwd = pd.concat([sp.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / sp - 1
        out = (fwd <= -soglia).astype(float)
        out[fwd.isna()] = np.nan
        return out
    return pd.DataFrame({"Y10": y(10, 0.05), "Y5": y(5, 0.04)}, index=sp.index)


if __name__ == "__main__":
    X = carica()
    Y = bersagli(X["sp500"])
    d = X.join(Y)
    d = d[d.index >= "1990-01-02"]
    print(d.notna().mean().round(3).to_string())
    print("\nrighe:", len(d), "prima:", d.index[0].date(), "ultima:", d.index[-1].date())
    fam = [c for c in d.columns if c.startswith("f")]
    print("\ncorrelazione con Y10:")
    print(d[fam].corrwith(d["Y10"]).sort_values(ascending=False).round(3).to_string())
