"""Regime di mercato: calma, tensione o crisi. Tre gruppi trovati automaticamente (modello a miscela gaussiana)
guardando volatilità recente, distanza dai massimi e andamento a 3 mesi dell'S&P 500 dal 1928.
Il gruppo è una descrizione dello stato attuale, non una previsione. I gruppi sono stabiliti sull'intera storia."""
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from .features import fwd_maxdd, fwd_ret, price_features

NAMES = ["Calma", "Tensione", "Crisi"]
EXPL = {
    "Calma": "Prezzi vicini ai massimi e oscillazioni contenute. È la condizione normale: i cali profondi qui sono più rari, ma anche le crisi partono quasi sempre da una fase calma.",
    "Tensione": "Oscillazioni sopra la norma e/o prezzi lontani dai massimi. Il mercato è nervoso: sono frequenti sia rimbalzi forti sia nuovi cali.",
    "Crisi": "Forte volatilità e cali profondi. Storicamente è qui che si perde di più, ma anche dove si sono costruiti i rendimenti dei 12 mesi successivi.",
}


def compute(p: pd.Series) -> dict:
    F = price_features(p)[["rv21", "dd252", "mom63"]].dropna()
    X = pd.DataFrame({"lv": np.log(F.rv21), "dd": F.dd252, "mom": F.mom63})
    sc = StandardScaler().fit(X.values)
    Z = sc.transform(X.values)
    g = GaussianMixture(3, covariance_type="full", n_init=4, random_state=7).fit(Z)
    lab = g.predict(Z)
    order = np.argsort([X.lv.values[lab == k].mean() for k in range(3)])
    remap = {int(old): new for new, old in enumerate(order)}
    reg = pd.Series([remap[int(k)] for k in lab], index=X.index)
    post = g.predict_proba(Z)[:, order]
    cur = int(reg.iloc[-1])
    run = int((reg[::-1] != cur).values.argmax()) if (reg != cur).any() else len(reg)
    f63, d63, f21 = fwd_ret(p, 63), fwd_maxdd(p, 63), fwd_ret(p, 21)
    stats = []
    for k in range(3):
        m = reg == k
        a = pd.DataFrame({"r1": f21.reindex(reg.index)[m], "r3": f63.reindex(reg.index)[m], "dd": d63.reindex(reg.index)[m]}).dropna()
        stats.append({"nome": NAMES[k], "quota": float(m.mean()), "r1": float(a.r1.mean()), "r3": float(a.r3.mean()),
                      "p_dd10": float((a.dd <= -0.10).mean()), "vol": float(np.exp(X.lv[m]).mean()),
                      "n": int(m.sum())})
    return {"date": reg.index[-1].strftime("%Y-%m-%d"), "corrente": cur, "nome": NAMES[cur],
            "prob": [float(x) for x in post[-1]], "giorni": run, "stats": stats, "series": reg}


def html(r: dict) -> str:
    pc = lambda x, d=0: f"{x * 100:.{d}f}%".replace(".", ",")
    cls = ["ok", "wa", "ba"][r["corrente"]]
    rows = "".join(f"<tr><td>{s['nome']}</td><td>{pc(s['quota'])}</td><td>{pc(s['vol'], 0)}</td><td>{pc(s['r1'], 1)}</td><td>{pc(s['r3'], 1)}</td><td>{pc(s['p_dd10'])}</td></tr>" for s in r["stats"])
    return (f"<div class='kc {cls}'><div class='k'>Regime attuale</div><div class='v'>{r['nome']}</div>"
            f"<div class='s'>da {r['giorni']} sedute · probabilità {pc(r['prob'][r['corrente']])}</div></div>"
            f"<p>{EXPL[r['nome']]}</p>"
            f"<table><tr><th>Regime</th><th>% del tempo</th><th>Volatilità</th><th>Rend. medio 1 mese dopo</th><th>Rend. medio 3 mesi dopo</th><th>Calo ≥10% nei 3 mesi dopo</th></tr>{rows}</table>"
            "<p class='mu'>Lettura: la tabella mostra cosa è successo in media dopo ogni giorno classificato in quel regime dal 1928. "
            "Serve a dare contesto agli altri indicatori: lo stesso valore del VIX pesa diversamente in calma o in crisi.</p>")
