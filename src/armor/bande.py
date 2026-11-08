"""Fascia di rendimento attesa (calibrata) per giorno, settimana, mese, 3 mesi.

Al posto del vecchio «± VIX/√periodo» (simmetrico e troppo largo: nei test copriva il 90-93% dei casi invece dell'80%), la fascia usa la
distribuzione REALE dei rendimenti divisi per l'oscillazione implicita (VIX): rendimento / (VIX/√(252/h)). Dai quantili storici (solo dati
noti prima di ogni anno: nessuno sguardo al futuro) si ricavano 10°, 50° e 90° percentile, che sono asimmetrici (i cali sono più ampi dei rialzi).
Verifica 2000-2026 (data/bande_eval.json): copertura dell'80% nel 77-79% dei casi con fasce più strette del 28-35%.

Onestà: nessun indicatore provato (Indice Armor, VIX, momentum, medie mobili, famiglie) ha previsto la DIREZIONE (su/giù) meglio della
frequenza storica, a 1 giorno, 1 settimana, 1 mese e 3 mesi (BSS ≤ 0, AUC ≤ 0,5 fuori campione). Per questo la direzione non è «prevista»: si mostra
la frequenza storica di rialzo e, dove Armor ha un'abilità dimostrata, il rischio di cali ampi."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA
from .features import closed_sp500

H = {"g": 1, "s": 5, "m": 21, "t": 63}
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
EVAL = DATA / "bande_eval.json"
_cache: dict = {}


def _z(h: int):
    if h in _cache:
        return _cache[h]
    sp = closed_sp500()
    sp = sp[sp.index >= "1990-01-03"]
    vix = store.load("vix").reindex(sp.index).ffill()
    sig = vix / np.sqrt(252 / h)
    ret = (sp.shift(-h) / sp - 1) * 100
    z = (ret / sig).dropna()
    _cache[h] = (z, sig, ret)
    return _cache[h]


_gc: dict = {}


def zgrid(h: int, date: pd.Timestamp) -> np.ndarray:
    """Quantili 1..99 di z con soli esiti noti prima dell'inizio dell'anno di `date` (nessuno sguardo al futuro)."""
    key = (h, pd.Timestamp(date).year)
    if key not in _gc:
        z, _s, _r = _z(h)
        tr = z[z.index <= pd.Timestamp(f"{key[1]}-01-01") - pd.Timedelta(days=int(h * 1.5) + 3)]
        if len(tr) < 500:
            tr = z[z.index < pd.Timestamp(f"{key[1]}-01-01")] if len(z[z.index < pd.Timestamp(f"{key[1]}-01-01")]) >= 200 else z
        _gc[key] = np.quantile(tr.values, np.linspace(0.01, 0.99, 99))
    return _gc[key]


def band(vix: float, h: int, date: pd.Timestamp) -> dict:
    """{'lo','med','hi'} in % (10°, 50°, 90° percentile) e frequenza storica di rialzo."""
    g = zgrid(h, date)
    s = float(vix) / np.sqrt(252 / h)
    return {"lo": float(g[9] * s), "med": float(g[49] * s), "hi": float(g[89] * s), "pup": float((g > 0).mean())}


def pct_of(real: float, vix: float, h: int, date: pd.Timestamp) -> float:
    """Posizione (0-100) del rendimento reale dentro la distribuzione prevista."""
    g = zgrid(h, date)
    s = float(vix) / np.sqrt(252 / h)
    return float(np.searchsorted(g, real / s) / 99 * 100)


def evaluate(save: bool = True) -> dict:
    out = {}
    for k, h in H.items():
        z, sig, ret = _z(h)
        rows = []
        for yr in range(2000, 2027):
            te = z[z.index.year == yr]
            if te.empty:
                continue
            g = zgrid(h, pd.Timestamp(f"{yr}-01-01"))
            s = sig.reindex(te.index)
            r = ret.reindex(te.index)
            lo, hi = g[9] * s, g[89] * s
            rows.append(pd.DataFrame({"cov_e": (r >= lo) & (r <= hi), "cov_s": (r.abs() <= 1.2816 * s), "w_e": hi - lo, "w_s": 2 * 1.2816 * s}))
        d = pd.concat(rows)
        out[k] = {"h": h, "n": int(len(d)), "copertura_nuova": round(float(d.cov_e.mean()), 3), "copertura_vecchia": round(float(d.cov_s.mean()), 3),
                  "larghezza_nuova": round(float(d.w_e.mean()), 2), "larghezza_vecchia": round(float(d.w_s.mean()), 2)}
    out["direzione"] = {"nota": "Nessun indicatore ha previsto su/giù meglio della frequenza storica (regressione logistica walk-forward 2000-2026: BSS ≤ 0, AUC ≤ 0,5).",
                        "pup_storico": {k: round(float(np.mean(zgrid(h, pd.Timestamp.now()) > 0)), 3) for k, h in H.items()}}
    if save:
        EVAL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_eval() -> dict:
    try:
        return json.loads(EVAL.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
