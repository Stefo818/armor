# -*- coding: utf-8 -*-
"""Stress test e perdita massima (PROTOCOLLO_MINIMI.md, parte I): crisi storiche e perdite attese in euro con FHS+VIX. Le percentuali sono calcolate qui;
gli importi in euro sono calcolati sul telefono con il valore che l'utente scrive (mai inviato altrove). File: data/stress.json."""
import json

import numpy as np
import pandas as pd

from . import fhs, minimi, store
from .config import DATA

FILE = DATA / "stress.json"
ORIZZONTI = {"1m": 21, "3m": 63, "1a": 252}
# nome, inizio finestra, fine finestra, serie: «usd» S&P 500 in dollari, «eur_sp» S&P 500 convertito in euro, «eur» VWCE in euro
CRISI = [("Crisi del 1929", "1929-09-01", "1932-07-31", "usd"), ("Crollo 1973-74", "1973-01-01", "1974-12-31", "usd"), ("Crollo del 1987", "1987-08-01", "1987-12-31", "usd"),
         ("Bolla internet 2000-02", "2000-03-01", "2002-10-31", "eur_sp"), ("Crisi finanziaria 2008", "2007-10-01", "2009-03-31", "eur_sp"),
         ("Covid 2020", "2020-02-01", "2020-03-31", "eur"), ("Tassi e inflazione 2022", "2022-01-01", "2022-10-31", "eur")]
SERIE_NOME = {"usd": "S&P 500 in dollari", "eur_sp": "S&P 500 convertito in euro", "eur": "VWCE in euro"}


def _serie(k: str) -> pd.Series:
    if k == "usd":
        from .features import closed_sp500
        return closed_sp500()
    from . import serie_eur
    s = serie_eur.costruisci()
    return (s["sp_eur"] if k == "eur_sp" else s["vwce_eur"]).dropna()


def crisi_singola(p: pd.Series, nome: str, a: str, b: str, k: str) -> dict | None:
    w = p[(p.index >= a) & (p.index <= b)]
    if len(w) < 5:
        return None
    # massimo = punto più alto prima del minimo della finestra
    tr = w.idxmin()
    pre = w[w.index <= tr]
    pk = pre.idxmax()
    w2 = p[(p.index >= pk) & (p.index <= tr)]
    calo = float(1 - p[tr] / p[pk])
    rec = p[(p.index > tr) & (p >= p[pk])]
    rec_d = rec.index[0] if len(rec) else None
    # piano di accumulo mensile costante iniziato al massimo: risultato al minimo e 3 anni dopo il minimo
    def pac(fine: pd.Timestamp) -> float | None:
        if fine > p.index[-1]:
            return None
        date = pd.date_range(pk, fine, freq="MS")
        if len(date) < 2:
            return None
        px = p.reindex(p.index.union(date)).ffill().reindex(date)
        q = (1.0 / px).sum()
        val = q * float(p[p.index <= fine].iloc[-1])
        return round(float(val / len(date) - 1), 4)
    traj = p[(p.index >= pk)].iloc[:1000]
    traj = (traj / traj.iloc[0] - 1)
    sub = traj.iloc[::5]
    return {"nome": nome, "serie": k, "serie_nome": SERIE_NOME[k], "massimo": str(pk.date()), "minimo": str(tr.date()), "calo": round(calo, 4),
            "giorni_al_minimo": int((tr - pk).days), "recupero": str(rec_d.date()) if rec_d is not None else None, "giorni_recupero": int((rec_d - pk).days) if rec_d is not None else None,
            "pac_al_minimo": pac(tr), "pac_3anni_dopo": pac(tr + pd.DateOffset(years=3)),
            "traiettoria": [[int(i * 5), round(float(v), 4)] for i, v in enumerate(sub.values)]}


def perdite_attese(p: pd.Series, vix: pd.Series | None, sims: int = 3000) -> dict:
    t = p.index[-1]
    r = fhs.log_returns(p[p.index >= fhs.FIT_START])
    params = fhs.fit(r.values)
    s2 = fhs.adjust_with_vix(fhs.next_variance(params, r.values), minimi._vix_a(vix, t), 0.5)
    paths = fhs.simulate(params, s2, sims, 252, seed=int(t.strftime("%Y%m%d")) % (2 ** 31))
    out = {}
    for k, n in ORIZZONTI.items():
        sub = paths[:n]
        fin = sub[-1] - 1.0
        dd = 1.0 - np.minimum(sub.min(axis=0), 1.0)
        q5, q20 = float(np.quantile(fin, .05)), float(np.quantile(fin, .20))
        peggio = fin[fin <= q5]
        out[k] = {"sedute": n, "fine_q5": q5, "fine_q20": q20, "fine_mediana": float(np.median(fin)), "es5": float(peggio.mean()), "p_perdita": float((fin < 0).mean()),
                  "calo_r50": float(np.quantile(dd, .5)), "calo_r80": float(np.quantile(dd, .8)), "calo_r95": float(np.quantile(dd, .95)),
                  "istogramma": [round(float(x), 4) for x in np.quantile(fin, np.linspace(0.02, 0.98, 25))]}
    return out


def prova_copertura() -> dict:
    """Quante volte il calo massimo reale ha superato la soglia che la simulazione indicava come «solo nel 5%» e «solo nel 20%» dei casi (VWCE in euro, dal 2011)."""
    st = minimi.carica_storia("eur")
    if st is None:
        return {}
    p = minimi.prezzi("eur")
    ob = minimi.osservati(p)
    s = st.set_index("date")
    out = {}
    for k in ORIZZONTI:
        fut = ob[f"fut_{minimi_chiave(k)}"].reindex(s.index)
        d = pd.DataFrame({"fut": fut, "r80": s[f"r80_{minimi_chiave(k)}"], "r95": s[f"r95_{minimi_chiave(k)}"]}).dropna()
        if len(d) < 50:
            continue
        f95, f80 = float((d["fut"] > d["r95"]).mean()), float((d["fut"] > d["r80"]).mean())
        out[k] = {"n": int(len(d)), "oltre_r95": round(f95, 3), "oltre_r80": round(f80, 3), "ok95": bool(0.03 <= f95 <= 0.08), "ok80": bool(0.14 <= f80 <= 0.26)}
    return out


def minimi_chiave(k: str) -> str:
    return {"1m": "1m", "3m": "3m", "1a": "1a"}[k]


def calcola() -> dict:
    res = {"data": str(pd.Timestamp.now().date()), "crisi": [], "attese": {}, "copertura": {}}
    cache = {}
    for nome, a, b, k in CRISI:
        try:
            cache.setdefault(k, _serie(k))
            c = crisi_singola(cache[k], nome, a, b, k)
            if c:
                res["crisi"].append(c)
        except Exception as e:  # noqa: BLE001
            print(f"[stress] {nome}: {str(e)[:80]}")
    pe = cache.get("eur")
    if pe is None:
        pe = _serie("eur")
    res["attese"] = perdite_attese(pe, store.load("vix"))
    res["attese_data"] = str(pe.index[-1].date())
    try:
        res["copertura"] = prova_copertura()
    except Exception as e:  # noqa: BLE001
        print("[stress] copertura non calcolata:", str(e)[:80])
    return res


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    a = r["attese"].get("3m", {})
    log(f"[stress] 3 mesi: perdita al 5% {a.get('fine_q5', 0) * 100:.1f}%, calo massimo 4 su 5 {a.get('calo_r80', 0) * 100:.1f}%")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
