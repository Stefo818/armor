"""Il semaforo funziona anche fuori dall'S&P 500? (Patch 60b, validazione su più mercati)
Su ogni mercato si usa solo FHS (la simulazione sui rendimenti del mercato stesso, senza VIX americano né modello A1, che esistono solo per l'S&P 500):
rapporto = probabilità FHS / frequenza storica normale del mercato, stessi colori e soglie del semaforo (senza Grigio, che richiede due modelli).
Domanda: più il colore è alto, più spesso segue un calo? Se sì su quasi tutti i mercati, la lettura «rapporto col normale» non è un caso dell'S&P 500."""
import json

import numpy as np
import pandas as pd

from . import modeleval
from .config import DATA
from .semaforo_rischio import BERSAGLI, COLORI, colore

FILE = DATA / "semaforo_mercati.json"
MERCATI = [("nasdaq100", "Nasdaq 100"), ("dax", "Germania (DAX)"), ("nikkei", "Giappone (Nikkei)"), ("ftsemib", "Italia (FTSE MIB)"), ("eem", "Paesi emergenti"), ("rsp", "S&P 500 a pesi uguali")]


def tabella(p: pd.Series, preds: pd.DataFrame) -> dict:
    ser = {}
    for hz, thr in BERSAGLI:
        f = preds[(preds.hz == hz) & (preds.thr == thr) & (preds.kind == "down")].set_index("date")["p"]
        ser[(hz, thr)] = (f, modeleval.purged_base(p, f.index, hz, "down", thr).reindex(f.index), modeleval.outcome(p, f.index, hz, "down", thr).reindex(f.index))
    idx = None
    for f, b, y in ser.values():
        ok = y.dropna().index.intersection(b.dropna().index)
        idx = ok if idx is None else idx.intersection(ok)
    if idx is None or len(idx) < 150:
        return {"n": 0 if idx is None else int(len(idx)), "righe": [], "monotona": None}
    r = np.mean([(f.loc[idx] / b.loc[idx]).values for f, b, y in ser.values()], axis=0)
    col = np.array([colore(a, a) for a in r])
    righe = []
    for c in COLORI[:4]:
        m = col == c
        if m.sum() < 10:
            righe.append({"colore": c, "n": int(m.sum())})
            continue
        d = {"colore": c, "n": int(m.sum())}
        for (hz, thr), (f, b, y) in ser.items():
            d[f"{hz}_{thr}"] = {"freq": float(y.loc[idx].values[m].mean()), "freq_tutte": float(y.loc[idx].values.mean())}
        righe.append(d)
    ok = [d for d in righe if "1m_5" in d]
    mono = bool(len(ok) >= 3 and all(all(ok[i][k]["freq"] <= ok[i + 1][k]["freq"] + 1e-9 for i in range(len(ok) - 1)) for k in ("1m_5", "3m_10")))
    return {"n": int(len(idx)), "da": str(idx.min().date()), "a": str(idx.max().date()), "righe": righe, "monotona": mono,
            "alto_vs_basso": {k: (ok[-1][k]["freq"] - ok[0][k]["freq"]) if len(ok) >= 2 else None for k in ("1m_5", "3m_10")}}


def run(step: int = 10, sims: int = 1000, log=print) -> dict:
    from . import fhs, store
    out = {"data": str(pd.Timestamp.now().date()), "mercati": {}}
    for sid, nome in MERCATI:
        try:
            x = store.load(sid)
            p = x[x > 0].dropna()
            p = p[p.index >= "1990-01-01"] if sid != "rsp" else p
            dates = p.index[p.index >= p.index[0] + pd.Timedelta(days=365 * 6)][::step]
            log(f"[mercati] {nome}: {len(dates)} date")
            df = pd.DataFrame(fhs.backtest_preds(p, dates, sims=sims, vix=None, w=0.0, fit_start=str(p.index[0].date())))
            df = df[[t in {5, 10} for t in df.thr]]
            out["mercati"][sid] = {"nome": nome, **tabella(p, df)}
        except Exception as e:  # noqa: BLE001
            log(f"[mercati] {nome}: errore {str(e)[:120]}")
            out["mercati"][sid] = {"nome": nome, "errore": str(e)[:120], "righe": [], "monotona": None}
    FILE.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def html() -> str:
    from html import escape as e
    d = carica()
    if not d:
        return ""
    ok = [(k, v) for k, v in d["mercati"].items() if v.get("monotona") is not None]
    if not ok:
        return ""
    n_ok = sum(1 for _k, v in ok if v["monotona"])
    righe = "".join(f"<tr><td>{e(v['nome'])}</td><td>{'Sì' if v['monotona'] else 'No'}</td><td>{'' if not v.get('alto_vs_basso') else '+%.0f punti' % (100 * v['alto_vs_basso']['1m_5'])}</td></tr>".replace(".", ",") for _k, v in ok)
    return (f"<h4>Funziona anche su altri mercati?</h4><p class='mu'>Stessa regola (rapporto col normale), solo con la simulazione FHS. In {n_ok} mercati su {len(ok)} più il colore è alto, più spesso segue un calo.</p>"
            "<div style='overflow-x:auto'><table class='tb'><tr><th>Mercato</th><th>Colori in ordine</th><th>Cali ≥5% in un mese: colore più alto contro più basso</th></tr>" + righe + "</table></div>")
