"""Indice di affidabilità (PIANO ARMOR 3, Fase 4): nessun punteggio con pesi inventati, ma cinque segnali con soglie fissate prima e mostrati uno per uno.

| Segnale | Quando si accende |
| Disaccordo | |sfidante − A1| ≥ 5 punti e rapporto ≥ 2 su una soglia principale |
| Dati vecchi | qualche serie chiave rossa in salute.py |
| Situazione mai vista | distanza di Mahalanobis dello stato di oggi (variabili di A1 + VIX + spread BAA + curva 10Y-3M) oltre il 99° percentile della storia di addestramento |
| Errori recenti | Brier delle ultime previsioni scadute nel diario peggiore della frequenza storica (solo con almeno 12 finestre scadute non sovrapposte) |
| Instabilità | la probabilità cambia di oltre 3 punti stimando il GARCH su finestre diverse (dal 1950, dal 1990, ultimi 15 anni) |
Livello: 0 segnali accesi = alta; 1 = media; 2 o più = bassa, con l'avviso «stima poco affidabile: …». Un segnale non valutabile (None) non conta."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import fhs, store
from .config import DATA, FEATURES, HORIZONS, PRIMARY
from .features import fwd_maxdd, price_features

FILE = DATA / "affidabilita.json"
SOGLIA_INSTABILITA = 0.03
PERCENTILE_NUOVO = 0.99
MIN_FINESTRE = 12
LIVELLI = {0: "alta", 1: "media"}
NOMI = {"disaccordo": "Disaccordo tra i modelli", "dati": "Dati non aggiornati", "mai_visto": "Situazione mai vista", "errori": "Errori recenti", "instabilita": "Stima instabile"}


def segnale_disaccordo(pred: dict) -> dict:
    acceso = [hz for hz, r in pred.items() if (r.get("sfidante") or {}).get("div")]
    if not any("sfidante" in r for r in pred.values()):
        return {"id": "disaccordo", "acceso": None, "dettaglio": "sfidante non calcolato oggi"}
    det = "; ".join(f"{hz}: A1 {pred[hz]['p'][PRIMARY[hz]]:.0%} contro {pred[hz]['sfidante']['p'][PRIMARY[hz]]:.0%}" for hz in acceso) if acceso else "i due modelli sono d'accordo"
    return {"id": "disaccordo", "acceso": bool(acceso), "dettaglio": det}


def segnale_dati(rows: list[dict]) -> dict:
    rosse = [r["name"] for r in rows if r["light"] == "ba"]
    return {"id": "dati", "acceso": bool(rosse), "dettaglio": (", ".join(rosse[:5]) + ("…" if len(rosse) > 5 else "")) if rosse else "tutte le serie chiave sono regolari"}


def stato_variabili(p: pd.Series) -> pd.DataFrame:
    f = price_features(p)[FEATURES]
    ex = pd.DataFrame({"vix": store.load("vix"), "baa10y": store.load("baa10y"), "t10y3m": store.load("t10y3m")})
    ex = ex.reindex(f.index).ffill(limit=7)
    return pd.concat([f, ex], axis=1).dropna()


def mahalanobis(X: pd.DataFrame, x: np.ndarray) -> tuple[float, float, int]:
    """(distanza di oggi, soglia al 99° percentile delle distanze storiche, numero di date). Covarianza con piccola regolarizzazione."""
    A = X.values
    mu = A.mean(axis=0)
    C = np.cov(A, rowvar=False) + 1e-9 * np.eye(A.shape[1])
    Ci = np.linalg.inv(C)
    d = np.sqrt(np.einsum("ij,jk,ik->i", A - mu, Ci, A - mu))
    d0 = float(np.sqrt((x - mu) @ Ci @ (x - mu)))
    return d0, float(np.quantile(d, PERCENTILE_NUOVO)), len(A)


def segnale_mai_visto(p: pd.Series, t) -> dict:
    try:
        S = stato_variabili(p[p.index <= t])
        if len(S) < 1000 or S.index[-1] != pd.Timestamp(t):
            return {"id": "mai_visto", "acceso": None, "dettaglio": "variabili di oggi non tutte disponibili"}
        d0, soglia, n = mahalanobis(S.iloc[:-1], S.iloc[-1].values)
        return {"id": "mai_visto", "acceso": bool(d0 > soglia), "dettaglio": f"distanza {d0:.1f} contro soglia {soglia:.1f} (99° percentile di {n} giorni)", "valore": d0, "soglia": soglia}
    except Exception as e:  # noqa: BLE001
        return {"id": "mai_visto", "acceso": None, "dettaglio": "non calcolabile: " + str(e)[:60]}


def segnale_errori(diario: pd.DataFrame, p: pd.Series, orizzonte: str = "1m", modello: str | None = None) -> dict:
    """Brier delle previsioni scadute del diario (una per finestra non sovrapposta) contro quello della frequenza storica. Serve un minimo di finestre."""
    n = HORIZONS[orizzonte]
    d = diario[diario["horizon"] == orizzonte].copy()
    if modello:
        d = d[d["model"].str.startswith(modello)]
    d = d.drop_duplicates("asof").sort_values("asof")
    dd = fwd_maxdd(p, n)
    pos = pd.Series(np.arange(len(p)), index=p.index)
    sel, last = [], -10 ** 9
    for r in d.itertuples():
        a = pd.Timestamp(r.asof)
        if a not in p.index or pd.isna(dd.get(a, np.nan)):
            continue
        if pos[a] - last >= n:
            sel.append((float(r.p1), float(r.base1), float(dd[a] <= -float(r.thr1) / 100)))
            last = pos[a]
    if len(sel) < MIN_FINESTRE:
        return {"id": "errori", "acceso": None, "dettaglio": f"non ancora valutabile: {len(sel)} finestre scadute su {MIN_FINESTRE} richieste", "finestre": len(sel)}
    a = np.array(sel)
    bp, bb = float(np.mean((a[:, 0] - a[:, 2]) ** 2)), float(np.mean((a[:, 1] - a[:, 2]) ** 2))
    return {"id": "errori", "acceso": bool(bp > bb), "dettaglio": f"Brier {bp:.4f} contro {bb:.4f} della frequenza storica su {len(sel)} finestre", "finestre": len(sel)}


def segnale_instabilita(p: pd.Series, t, vix: float | None = None) -> dict:
    """Probabilità principale a 1 e 3 mesi (simulazione GARCH) stimando i parametri su tre finestre di storia diverse."""
    try:
        pp = p[p.index <= t]
        seed = int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31)
        inizi = {"dal 1950": "1950-01-01", "dal 1990": "1990-01-01", "ultimi 15 anni": str((pd.Timestamp(t) - pd.DateOffset(years=15)).date())}
        ris = {}
        for nome, da in inizi.items():
            f = fhs.forecast(pp, sims=3000, seed=seed, fit_start=da)
            ris[nome] = {hz: float(f[hz]["down"][PRIMARY[hz]]["p"]) for hz in ("1m", "3m")}
        spread = {hz: max(v[hz] for v in ris.values()) - min(v[hz] for v in ris.values()) for hz in ("1m", "3m")}
        peggio = max(spread, key=spread.get)
        return {"id": "instabilita", "acceso": bool(spread[peggio] > SOGLIA_INSTABILITA),
                "dettaglio": f"a {peggio.replace('1m', '1 mese').replace('3m', '3 mesi')} la stima va da {min(v[peggio] for v in ris.values()):.0%} a {max(v[peggio] for v in ris.values()):.0%} secondo la storia usata",
                "per_finestra": ris}
    except Exception as e:  # noqa: BLE001
        return {"id": "instabilita", "acceso": None, "dettaglio": "non calcolabile: " + str(e)[:60]}


def livello(segnali: list[dict]) -> dict:
    accesi = [s for s in segnali if s["acceso"]]
    n = len(accesi)
    lv = LIVELLI.get(n, "bassa")
    avviso = ("Stima poco affidabile: " + "; ".join(f"{NOMI[s['id']].lower()} ({s['dettaglio']})" for s in accesi) + ".") if n >= 2 else ""
    return {"livello": lv, "n_accesi": n, "avviso": avviso}


def calcola(pred: dict, p: pd.Series, t, diario: pd.DataFrame | None = None, salute_rows: list[dict] | None = None, scrivi: bool = True) -> dict:
    from . import journal, salute
    segnali = [segnale_disaccordo(pred), segnale_dati(salute_rows if salute_rows is not None else salute.compute()), segnale_mai_visto(p, t),
               segnale_errori(diario if diario is not None else journal.read(), p), segnale_instabilita(p, t)]
    out = {"asof": str(pd.Timestamp(t).date()), "segnali": segnali, **livello(segnali)}
    if scrivi:
        FILE.write_text(json.dumps(out, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    return out


def html() -> str:
    try:
        a = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    cls = {"alta": "ok", "media": "warn", "bassa": "bad"}[a["livello"]]
    righe = ""
    for s in a["segnali"]:
        st = {True: ("bad", "acceso"), False: ("ok", "spento"), None: ("warn", "non valutabile")}[s["acceso"]]
        righe += f"<div class='mu' style='margin:3px 0'><span class='badge {st[0]}'>{st[1]}</span> <b>{_h.escape(NOMI[s['id']])}</b>: {_h.escape(s['dettaglio'])}</div>"
    av = f"<div class='vd bad' style='margin:6px 0'>{_h.escape(a['avviso'])}</div>" if a.get("avviso") else ""
    return (f"<div class='card'><div class='hzh'><h3 style='margin:0'>Quanto è affidabile la stima di oggi</h3><span class='badge {cls}'>Affidabilità {a['livello']}</span></div>{av}{righe}"
            "<p class='mu'>Cinque segnali con soglie fissate prima, nessun punteggio inventato: 0 accesi = alta, 1 = media, 2 o più = bassa. "
            "Un segnale non valutabile non conta.</p></div>")
