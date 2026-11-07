"""Spiegazione di ogni previsione (compito 1.6): le prime 3 cause in parole semplici."""
import numpy as np
import pandas as pd

from .config import HORIZONS, PRIMARY
from .features import fwd_maxdd
from .model_mv import FEAT_IT as FEAT_MV
from .outlook import FEAT_IT

NOMI = {**FEAT_IT, **FEAT_MV}


def cause_logit(drivers: list, n: int = 3) -> list[str]:
    """drivers: [(variabile, contributo)] = coefficiente x valore standardizzato. Contributo > 0 = aumenta il rischio di calo."""
    out = []
    for f, c in sorted(drivers or [], key=lambda t: -abs(t[1]))[:n]:
        if abs(c) < 0.05:
            continue
        out.append(f"{NOMI.get(f, f)}: {'aumenta' if c > 0 else 'riduce'} il rischio")
    return out


def cause_fhs(sigma_annual: float, sigma_normale: float) -> str:
    """Frase sulla volatilita' attesa dal motore FHS contro quella normale."""
    r = sigma_annual / sigma_normale if sigma_normale > 0 else 1.0
    verso = "sopra" if r > 1.15 else ("sotto" if r < 0.87 else "in linea con")
    return f"Volatilità attesa {sigma_annual * 100:.0f}% annua contro un normale di {sigma_normale * 100:.0f}%: {verso} la media"


def sigma_normale(p: pd.Series) -> float:
    """Volatilita' annua mediana storica (rendimenti logaritmici giornalieri), solo prezzi noti."""
    r = np.log(p.dropna()).diff().dropna()
    return float(r.rolling(63).std().median() * np.sqrt(252))


def perm_importance(eng, fitted: dict, hz: str = "3m", years: int = 5, reps: int = 3, seed: int = 0, step: int = 5) -> list[tuple[str, float]]:
    """Importanza per permutazione di un modello ad alberi sugli ultimi 'years' anni (solo esiti maturati):
    quanto peggiora il log loss mescolando una variabile alla volta."""
    n = HORIZONS[hz]
    thr = PRIMARY[hz]
    m = fitted["hz"][hz]["models"].get(thr)
    if m is None:
        return []
    idx = eng.F.index
    last = eng.p.index[-1 - n]
    sel = idx[(idx <= last) & (idx >= last - pd.DateOffset(years=years))][::step]
    X = eng.F.loc[sel].values
    y = (eng.dd[hz].loc[sel] <= -thr / 100).astype(int).values

    def ll(Xm):
        pr = np.clip(m.predict_proba(Xm)[:, 1], 1e-4, 1 - 1e-4)
        return float(-(y * np.log(pr) + (1 - y) * np.log(1 - pr)).mean())
    base = ll(X)
    rng = np.random.default_rng(seed)
    out = []
    for j, f in enumerate(eng.feats):
        d = []
        for _ in range(reps):
            Xp = X.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            d.append(ll(Xp) - base)
        out.append((f, float(np.mean(d))))
    return sorted(out, key=lambda t: -t[1])


def cause_gbm(imp: list, n: int = 3) -> list[str]:
    return [f"{NOMI.get(f, f)}: pesa molto sul modello ad alberi" for f, v in imp[:n] if v > 0.0005]


# ---------- uso dal vivo: intervalli verificati e riga sulla volatilita' ----------
def _eval() -> dict:
    import json
    from .config import DATA
    try:
        return json.loads((DATA / "model_eval.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def ret_display(hz: str, ret: dict | None, modello: str = "A1") -> tuple[dict | None, str]:
    """Intervallo 80% da mostrare: se nei test passati la copertura era fuori da 80% +- 3 punti, i quantili q10/q90 vengono
    stretti o allargati attorno a q50 con il fattore k misurato (conformale). Restituisce (ret, frase sulla copertura misurata)."""
    if not ret:
        return ret, ""
    c = ((_eval().get("intervalli") or {}).get(hz) or {}).get(modello)
    if not c or not c.get("n"):
        return ret, ""
    raw, con, k = c["copertura_grezza"], c["copertura_conformale"], c["k_ultimo"]
    out, cop = ret, raw
    if abs(raw - 0.80) > 0.03 and k == k and 0.3 < k < 3:
        half = (ret["q90"] - ret["q10"]) / 2
        out = {**ret, "q10": ret["q50"] - k * half, "q90": ret["q50"] + k * half}
        cop = con
    return out, f"Verifica: in passato questo intervallo ha contenuto il risultato nel {cop * 100:.0f}% dei casi (obiettivo 80%, {c['n']} prove)."


def linea_fhs() -> str:
    """Riga «Perché?» sul motore FHS: volatilita' attesa contro normale. Vuota se qualcosa manca."""
    try:
        from . import fhs
        from .features import closed_sp500
        p = closed_sp500()
        f = fhs.forecast(p, sims=200)
        return cause_fhs(f["_sigma_annual"] / 100.0, sigma_normale(p))   # _sigma_annual e' in %
    except Exception:  # noqa: BLE001
        return ""
