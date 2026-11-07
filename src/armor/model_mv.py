"""Modello multi-variabile (compito 1.2): le 8 variabili sui prezzi + variabili di mercato e credito, dal 1990.
Ogni variabile esterna e' spostata del suo ritardo di pubblicazione (nessuno sguardo al futuro).
Non incluse perche' la storia e' troppo corta per un modello dal 1990: VIX3M/VIX (dal 2006), spread HY (dal 2023),
ampiezza, punteggi dell'Indice Armor (esistono solo dal vivo): restano come contesto."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import store
from .challenger import E2, _al
from .config import FEATURES, HORIZONS, LOGIT_C, TARGETS
from .features import price_features

EXTRA = ["log_vix", "vix_chg21", "vrp", "baa10y", "baa_chg21", "t10y3m", "nfci"]
FEATS_MV = FEATURES + EXTRA
# segno noto del legame con il rischio di calo (+1 sale, -1 scende, 0 libero): solo dove e' ovvio
MONOTONE = {"rv21": 1, "rv63": 1, "worst_day": -1, "log_vix": 1, "baa10y": 1, "nfci": 1}
FEAT_IT = {"log_vix": "VIX (paura implicita)", "vix_chg21": "variazione del VIX in un mese", "vrp": "VIX meno volatilità reale",
           "baa10y": "spread delle obbligazioni aziendali", "baa_chg21": "variazione dello spread in un mese",
           "t10y3m": "curva dei tassi 10 anni - 3 mesi", "nfci": "condizioni finanziarie (NFCI)"}
MIN_ROWS = 1000   # circa 4 anni di storia prima della prima previsione


def mv_extra(idx: pd.DatetimeIndex, rv21: pd.Series | None = None) -> pd.DataFrame:
    """Variabili esterne allineate alle date idx. Ritardi: VIX 0 giorni; BAA, curva 1 giorno; NFCI 5 giorni (settimanale)."""
    L = store.load
    vix = _al(L("vix"), idx, 0, 5)
    baa = _al(L("baa10y"), idx, 1, 5)
    f = pd.DataFrame(index=idx)
    f["log_vix"] = np.log(vix)
    f["vix_chg21"] = vix / vix.shift(21) - 1
    f["vrp"] = vix / 100 - (rv21 if rv21 is not None else np.nan)
    f["baa10y"] = baa
    f["baa_chg21"] = baa - baa.shift(21)
    f["t10y3m"] = _al(L("t10y3m"), idx, 1, 5)
    f["nfci"] = _al(L("nfci"), idx, 5, 10)
    return f


class MVEngine(E2):
    def __init__(self, close: pd.Series, algo: str = "logit"):
        p = close.dropna().astype(float)
        rv21 = price_features(p)["rv21"]
        extra = mv_extra(p.index, rv21)[EXTRA]
        super().__init__(p, extra=extra, algo=algo)

    def _new_model(self):
        if self.algo == "gbm":
            cst = [MONOTONE.get(f, 0) for f in self.feats]
            return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=120, min_samples_leaf=250,
                                                  l2_regularization=5.0, monotonic_cst=cst, random_state=0)
        return make_pipeline(StandardScaler(), LogisticRegression(C=LOGIT_C, max_iter=1000))


def mv_preds(p: pd.Series, dates, algo: str = "logit", refit_every: int = 63) -> list[dict]:
    """Previsioni walk-forward dei cali: a ogni data il modello usa solo esiti gia' maturati (purge incorporato)."""
    eng = MVEngine(p, algo)
    first = eng.F.index[0]
    rows, fitted, last = [], None, -10 ** 9
    for t in dates:
        if t not in eng.F.index:
            continue
        k = eng.F.index.get_loc(t)
        if k < MIN_ROWS + 126:
            continue
        i = eng.p.index.get_loc(t)
        if fitted is None or i - last >= refit_every:
            fitted = eng.fit(t)
            last = i
        pr = eng.predict(fitted, t)
        for hz in HORIZONS:
            if hz in pr:
                for thr in TARGETS[hz]:
                    rows.append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": pr[hz]["p"][thr]})
    return rows
