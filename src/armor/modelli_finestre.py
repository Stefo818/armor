"""Vincitori per periodo (Patch 81): chi ha sbagliato meno ogni settimana, mese, trimestre e semestre, per ognuno dei quattro orizzonti.
Si usano le previsioni storiche di ogni modello (stessa regola per tutti): per ogni periodo vince il modello con l'errore medio (Brier) più basso
tra quelli confrontati. «Normale» (la frequenza storica) partecipa: se vince, vuol dire che nessun modello ha aggiunto informazione in quel periodo.
Se primo e secondo sono entro l'1% di errore, il periodo è «Pari» (nessun vincitore netto). Si contano solo previsioni con esito già noto (nessun futuro). Risultato salvato in data/modelli_finestre.json."""
import json

import numpy as np
import pandas as pd

from .config import DATA, PRIMARY

FILE = DATA / "modelli_finestre.json"
HZ = ("10g", "1m", "3m", "6m")
MODELLI = ("A1", "FHS", "FHS+VIX")
PERIODI = {"settimana": "W", "mese": "M", "trimestre": "Q", "semestre": "H"}


def _chiave(idx: pd.DatetimeIndex, per: str) -> pd.Series:
    if per == "settimana":
        iso = idx.isocalendar()
        return pd.Series([f"{a}-S{b:02d}" for a, b in zip(iso.year, iso.week)], index=idx)
    if per == "mese":
        return pd.Series(idx.strftime("%Y-%m"), index=idx)
    if per == "trimestre":
        return pd.Series([f"{d.year}-T{(d.month - 1) // 3 + 1}" for d in idx], index=idx)
    return pd.Series([f"{d.year}-{'1' if d.month <= 6 else '2'}S" for d in idx], index=idx)


def errori(p: pd.Series, preds: dict, modelli=MODELLI) -> dict:
    """{orizzonte: DataFrame(date × modello) di errori al quadrato; solo date con esito noto e con tutti i modelli}."""
    from .modeleval import outcome, purged_base
    out = {}
    for hz in HZ:
        thr = PRIMARY[hz]
        cols = {}
        for m in modelli:
            df = preds.get(m)
            if df is None:
                continue
            g = df[(df.hz == hz) & (df.kind == "down") & (df.thr == thr)].drop_duplicates("date").set_index("date")["p"].dropna()
            if len(g):
                cols[m] = g
        if not cols:
            continue
        dates = pd.DatetimeIndex(sorted(set.intersection(*[set(c.index) for c in cols.values()])))
        y = outcome(p, dates, hz, "down", thr).dropna()
        dates = y.index
        base = purged_base(p, dates, hz, "down", thr)
        e = pd.DataFrame({"Normale": (base - y) ** 2})
        for m, c in cols.items():
            e[m] = (c.loc[dates] - y) ** 2
        out[hz] = e
    return out


def vincitori(e: pd.DataFrame, per: str) -> pd.DataFrame:
    """Per ogni periodo: errore medio di ogni modello e vincitore."""
    k = _chiave(e.index, per)
    g = e.groupby(k.values).mean()
    n = e.groupby(k.values).size()
    ordine = np.sort(g.values, axis=1)
    pari = (ordine[:, 1] - ordine[:, 0]) <= 0.01 * np.maximum(ordine[:, 0], 1e-9)   # primo e secondo entro l'1%: nessun vincitore netto
    g["vince"] = np.where(pari, "Pari", g.idxmin(axis=1))
    g["n"] = n
    return g


def _quote(g: pd.DataFrame, modelli: list[str]) -> dict:
    if not len(g):
        return {m: 0.0 for m in modelli + ["Pari"]}
    return {m: round(float((g["vince"] == m).mean() * 100), 1) for m in modelli + ["Pari"]}


def calcola(p: pd.Series, preds: dict) -> dict:
    E = errori(p, preds)
    modelli = ["Normale"] + [m for m in MODELLI if any(m in e.columns for e in E.values())]
    res = {"modelli": modelli, "orizzonti": {}, "ultima_data": ""}
    for hz, e in E.items():
        res["ultima_data"] = max(res["ultima_data"], str(e.index[-1].date()))
        res["orizzonti"][hz] = {"soglia": PRIMARY[hz], "n_date": int(len(e)), "da": str(e.index[0].date()), "periodi": {}}
        for per in PERIODI:
            g = vincitori(e, per)
            rec = g[g.index >= str(e.index[-1].year - 12)]   # ultimi ~12 anni
            res["orizzonti"][hz]["periodi"][per] = {
                "n": int(len(g)), "quote": _quote(g, modelli), "quote_12a": _quote(rec, modelli),
                "ultimi": [{"p": str(i), "v": r["vince"], "n": int(r["n"]), "err": {m: round(float(r[m]), 4) for m in modelli}} for i, r in g.tail(8).iterrows()]}
        # errore medio cumulativo per anno (per il grafico a barre)
        y = e.groupby(e.index.year).mean()
        res["orizzonti"][hz]["anni"] = {str(a): {m: round(float(r[m]), 4) for m in modelli} for a, r in y.iterrows()}
        res["orizzonti"][hz]["anni_n"] = {str(a): int(c) for a, c in e.groupby(e.index.year).size().items()}
        res["orizzonti"][hz]["tot"] = {m: round(float(e[m].mean()), 4) for m in modelli}
        res["orizzonti"][hz]["tot_12m"] = {m: round(float(e.tail(max(int(len(e) / 36), 20))[m].mean()), 4) for m in modelli}
    return res


def salva(res: dict) -> None:
    FILE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
