"""Rischio di cambio EUR/USD per chi compra VWCE in euro. VWCE non è coperto dal cambio: se il dollaro si indebolisce,
il valore in euro scende anche se le borse restano ferme (e viceversa)."""
import numpy as np
import pandas as pd

from . import store
from .features import vwce_series

DEFAULT_BETA = -0.60


def _ret(s: pd.Series, days: int) -> float:
    s = s.dropna()
    if len(s) < 2:
        return float("nan")
    t = s.index[-1] - pd.Timedelta(days=days)
    s0 = s[s.index <= t]
    return float(s.iloc[-1] / s0.iloc[-1] - 1) if len(s0) else float("nan")


def beta_fx() -> tuple[float, int]:
    """Sensibilità reale di VWCE (in euro) al cambio: regressione sui rendimenti settimanali, a parità di andamento di VT in dollari."""
    v, vt, fx = store.load("vwce_de"), store.load("vt"), store.load("eurusd")
    if min(len(v), len(vt), len(fx)) < 200:
        return DEFAULT_BETA, 0
    d = pd.concat([v, vt, fx], axis=1, keys=["v", "vt", "fx"]).dropna().resample("W").last().dropna()
    r = np.log(d).diff().dropna()
    if len(r) < 60:
        return DEFAULT_BETA, len(r)
    X = np.column_stack([np.ones(len(r)), r.vt.values, r.fx.values])
    b = np.linalg.lstsq(X, r.v.values, rcond=None)[0]
    beta = float(np.clip(b[2], -1.0, 0.0))
    return beta, int(len(r))


def compute() -> dict:
    fx, vt = store.load("eurusd"), store.load("vt")
    if fx.empty:
        raise ValueError("serie EUR/USD assente")
    beta, n = beta_fx()
    cur = float(fx.iloc[-1])
    pct = float((fx < cur).mean())
    rows = []
    for name, days in [("1 anno", 365), ("3 anni", 1095), ("5 anni", 1825)]:
        rf = _ret(fx, days)
        rv = _ret(vt, days) if not vt.empty else float("nan")
        rows.append({"periodo": name, "usd": rv, "cambio": -rf if not np.isnan(rf) else float("nan"),
                     "eur": (1 + rv) / (1 + rf) - 1 if not (np.isnan(rv) or np.isnan(rf)) else float("nan")})
    scen = [{"eurusd": s, "impatto": beta * s} for s in (-0.10, -0.05, 0.05, 0.10)]
    vol_fx = float(np.log(fx).diff().dropna().iloc[-252:].std() * np.sqrt(252))
    return {"eurusd": cur, "date": fx.index[-1].strftime("%Y-%m-%d"), "pct": pct, "beta": beta, "n": n, "rows": rows,
            "scen": scen, "vol_fx": vol_fx, "media10": float(fx.iloc[-2520:].mean())}


def html(r: dict) -> str:
    pc = lambda x, d=1: "n.d." if x != x else f"{x * 100:+.{d}f}%".replace(".", ",")
    rows = "".join(f"<tr><td>{x['periodo']}</td><td>{pc(x['usd'])}</td><td>{pc(x['cambio'])}</td><td><b>{pc(x['eur'])}</b></td></tr>" for x in r["rows"])
    sc = "".join(f"<tr><td>Euro {s['eurusd'] * 100:+.0f}% sul dollaro</td><td><b>{pc(s['impatto'])}</b></td></tr>".replace(".0%", "%") for s in r["scen"])
    pos = "sopra" if r["pct"] > 0.5 else "sotto"
    return (f"<div class='grid2'><div class='kc'><div class='k'>EUR/USD</div><div class='v'>{r['eurusd']:.3f}</div><div class='s'>{pos} la sua storia più di {max(r['pct'], 1 - r['pct']) * 100:.0f}% delle volte</div></div>"
            f"<div class='kc'><div class='k'>Sensibilità di VWCE al cambio</div><div class='v'>{r['beta']:.2f}</div><div class='s'>1% di euro in più = {abs(r['beta']):.1f}% in meno per VWCE</div></div></div>"
            "<p>VWCE è quotato in euro ma investe soprattutto in dollari (circa i due terzi del fondo sono titoli USA). "
            "Quando l'euro si rafforza, i tuoi titoli valgono meno in euro anche se le borse non scendono.</p>"
            f"<table><tr><th>Periodo</th><th>Mercato in dollari (VT)</th><th>Effetto cambio</th><th>Risultato in euro</th></tr>{rows}</table>"
            f"<table><tr><th>Scenario</th><th>Effetto stimato su VWCE (a parità di borse)</th></tr>{sc}</table>"
            f"<p class='mu'>Sensibilità stimata dai rendimenti settimanali reali di VWCE ({r['n']} settimane). Il cambio oscilla circa del {r['vol_fx'] * 100:.0f}% l'anno: "
            "nel lungo periodo con il PAC tende a compensarsi, ma può pesare per anni. Non è una previsione sul cambio.</p>")
