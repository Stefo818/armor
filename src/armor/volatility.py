"""Previsione della volatilità dell'S&P 500 a 1 mese (modello HAR + VIX).
La volatilità si prevede molto meglio della direzione dei prezzi: tende a persistere e a tornare verso la media.
Modello: regressione sui logaritmi della volatilità di ieri, dell'ultima settimana e dell'ultimo mese (e del VIX quando c'e').
Il test è fuori campione: a ogni data si usano solo dati precedenti."""
import numpy as np
import pandas as pd

from . import store

H = 21


def _frame(p: pd.Series, vix: pd.Series) -> pd.DataFrame:
    r = np.log(p).diff()
    d = pd.DataFrame(index=p.index)
    d["d"] = np.log((r.abs().rolling(3).mean() * np.sqrt(252)).clip(lower=0.02))
    d["w"] = np.log((r.rolling(5).std() * np.sqrt(252)).clip(lower=0.02))
    d["m"] = np.log((r.rolling(22).std() * np.sqrt(252)).clip(lower=0.02))
    d["q"] = np.log((r.rolling(66).std() * np.sqrt(252)).clip(lower=0.02))
    d["vix"] = np.log(vix.reindex(p.index).ffill(limit=5) / 100)
    d["y"] = np.log((r.rolling(H).std().shift(-H) * np.sqrt(252)).clip(lower=0.02))
    return d


def _ols(X, y, lam=1e-3):
    X1 = np.column_stack([np.ones(len(X)), X])
    A = X1.T @ X1 + lam * np.eye(X1.shape[1])
    return np.linalg.solve(A, X1.T @ y)


def forecast(p: pd.Series, vix: pd.Series | None = None) -> dict:
    vix = store.load("vix") if vix is None else vix
    d = _frame(p, vix)
    use_vix = vix is not None and not vix.empty
    cols = ["d", "w", "m", "q"] + (["vix"] if use_vix else [])
    train = d.dropna(subset=cols + ["y"]) if use_vix else d.dropna(subset=cols + ["y"])
    last = d.dropna(subset=cols).iloc[-1]
    # test fuori campione dal 2005, ogni 21 sedute, rifacendo il modello con i soli dati disponibili allora
    idx = train.index
    test_dates = [t for t in idx[idx >= "2005-01-01"][::H]]
    pred, real, naive, vixp = [], [], [], []
    for t in test_dates:
        tr = train[train.index <= idx[max(idx.get_loc(t) - H, 0)]]
        if len(tr) < 1500:
            continue
        b = _ols(tr[cols].values, tr["y"].values)
        x = np.r_[1, train.loc[t, cols].values]
        pred.append(float(x @ b)); real.append(train.loc[t, "y"]); naive.append(train.loc[t, "m"])
        vixp.append(train.loc[t, "vix"] if use_vix else np.nan)
    pred, real, naive, vixp = map(np.array, (pred, real, naive, vixp))
    mae = lambda a: float(np.nanmean(np.abs(np.exp(a) - np.exp(real))) * 100)
    rmse_log = lambda a: float(np.sqrt(np.nanmean((a - real) ** 2)))
    ev = {"n": int(len(real)), "mae_har": mae(pred), "mae_persist": mae(naive),
          "mae_vix": mae(vixp) if use_vix and not np.isnan(vixp).all() else None,
          "skill_vs_persist": 1 - rmse_log(pred) ** 2 / rmse_log(naive) ** 2}
    b = _ols(train[cols].values, train["y"].values)
    res = train["y"].values - np.column_stack([np.ones(len(train)), train[cols].values]) @ b
    mu = float(np.r_[1, last[cols].values] @ b)
    q = np.quantile(res[-2500:], [0.1, 0.9])
    cur = float(np.exp(last["m"]))
    hist = np.exp(train["m"])
    return {"date": last.name.strftime("%Y-%m-%d"), "attesa": float(np.exp(mu)), "bassa": float(np.exp(mu + q[0])), "alta": float(np.exp(mu + q[1])),
            "attuale_1m": cur, "attuale_1w": float(np.exp(last["w"])),
            "vix": float(np.exp(last["vix"]) * 100) if use_vix else None,
            "mediana_storica": float(hist.median()), "pct_attuale": float((hist < cur).mean()),
            "eval": ev}


def html(v: dict) -> str:
    f = lambda x: f"{x * 100:.1f}%".replace(".", ",")
    dir_ = "salire" if v["attesa"] > v["attuale_1m"] * 1.08 else ("scendere" if v["attesa"] < v["attuale_1m"] * 0.92 else "restare simile")
    e = v["eval"]
    daily = v["attesa"] / np.sqrt(252)
    vixtxt = ("Il VIX, la volatilità che gli operatori si aspettano, è " + f"{v['vix']:.1f}".replace('.', ',') + ".") if v.get("vix") else ""
    t = (f"<div class='grid2'><div class='kc'><div class='k'>Volatilità attesa (prossimo mese)</div><div class='v'>{f(v['attesa'])}</div>"
         f"<div class='s'>intervallo probabile {f(v['bassa'])} – {f(v['alta'])}</div></div>"
         f"<div class='kc'><div class='k'>Volatilità degli ultimi 21 giorni</div><div class='v'>{f(v['attuale_1m'])}</div>"
         f"<div class='s'>media storica {f(v['mediana_storica'])}</div></div></div>"
         f"<p>Il modello si aspetta che la volatilità dell'S&amp;P 500 possa <b>{dir_}</b>. In pratica: un movimento giornaliero tipico di circa "
         f"<b>±{f'{daily * 100:.1f}'.replace('.', ',')}%</b> (un giorno su tre un po' più grande). {vixtxt}</p>"
         f"<p class='mu'>Affidabilità: in {e['n']} test fuori campione dal 2005 l'errore medio è stato {e['mae_har']:.1f} punti contro {e['mae_persist']:.1f} "
         f"di chi si limita a ripetere la volatilità recente" + (f" e {e['mae_vix']:.1f} del solo VIX" if e.get('mae_vix') else "") +
         ". La volatilità si stima meglio della direzione dei prezzi, ma resta una stima: nelle crisi improvvise sale più del previsto.</p>")
    return t
