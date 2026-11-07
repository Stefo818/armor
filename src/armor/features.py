"""Variabili calcolate dai prezzi. Ogni valore alla data t usa solo dati fino a t."""
import numpy as np
import pandas as pd

from . import store


def price_features(p: pd.Series) -> pd.DataFrame:
    lr = np.log(p).diff()
    f = pd.DataFrame(index=p.index)
    f["rv21"] = lr.rolling(21).std() * np.sqrt(252)
    f["rv63"] = lr.rolling(63).std() * np.sqrt(252)
    f["rv_ratio"] = f["rv21"] / (lr.rolling(252, min_periods=120).std() * np.sqrt(252))
    f["dd252"] = p / p.rolling(252, min_periods=120).max() - 1
    f["ma200"] = p / p.rolling(200).mean() - 1
    f["ma50_200"] = p.rolling(50).mean() / p.rolling(200).mean() - 1
    f["mom63"] = p / p.shift(63) - 1
    f["worst_day"] = lr.rolling(21).min()
    return f


def fwd_maxdd(p: pd.Series, h: int) -> pd.Series:
    """Calo massimo rispetto al prezzo di oggi nelle h sedute successive (valore <= 0)."""
    m = p[::-1].rolling(h, min_periods=h).min()[::-1].shift(-1)
    return np.minimum(m / p - 1, 0.0)


def fwd_maxup(p: pd.Series, h: int) -> pd.Series:
    """Rialzo massimo rispetto al prezzo di oggi nelle h sedute successive (valore >= 0)."""
    m = p[::-1].rolling(h, min_periods=h).max()[::-1].shift(-1)
    return np.maximum(m / p - 1, 0.0)


def fwd_ret(p: pd.Series, h: int) -> pd.Series:
    return p.shift(-h) / p - 1


def vwce_series() -> pd.Series:
    """Prezzo VWCE: quotazione reale se presente, altrimenti proxy VT/EURUSD (solo per la storia)."""
    v = store.load("vwce_de")
    vt, fx = store.load("vt"), store.load("eurusd")
    if vt.empty or fx.empty:
        return v
    proxy = (vt / fx.reindex(vt.index).ffill()).dropna()
    if v.empty:
        return proxy
    scale = v.iloc[0] / proxy.reindex([v.index[0]], method="ffill").iloc[0]
    return pd.concat([proxy[proxy.index < v.index[0]] * scale, v]).sort_index()


def closed_sp500() -> pd.Series:
    s = store.load("sp500")
    return s[s > 0].dropna()
