# -*- coding: utf-8 -*-
"""Lungo periodo (PROTOCOLLO_MINIMI.md, parte B): in che fase di lungo periodo è il mercato e quanto ci si può aspettare a 2, 3, 5, 8, 10, 15 anni?
Dati: S&P 500 mensile dal 1871 (prezzo, dividendi, prezzi al consumo: Robert Shiller) e CAPE mensile (serie cape_m).
Modello: rendimento totale reale annualizzato = a + b · ln(CAPE), imparato in avanti (solo finestre già concluse alla data). File: data/lungo_periodo.json."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "lungo_periodo.json"
ORIZZONTI = (2, 3, 5, 8, 10, 15)
PRIMO_OOS = "1920-01-01"
META = "1969-12-31"
SOGLIA_SANA, SOGLIA_CARA = 0.60, 0.85
SOGLIA_B = 0.02                  # miglioramento minimo dell'R² perché la variante con i tassi sostituisca quella col solo CAPE
ORIZZONTI_B = (5, 8, 10, 15)


def dati_mensili() -> pd.DataFrame:
    """Mese per mese (fine mese): indice del rendimento totale reale (dividendi reinvestiti, al netto dell'inflazione) e CAPE."""
    P, D, C = (store.load(k).dropna() for k in ("price_shiller", "div_shiller", "cpi_shiller"))
    m = lambda s: s.groupby(s.index.to_period("M")).last()
    P, D, C = m(P), m(D), m(C)
    cape = store.load("cape_m").dropna()
    cape = cape.groupby(cape.index.to_period("M")).last()
    df = pd.DataFrame({"P": P, "D": D, "C": C}).dropna()
    r = (df["P"] + df["D"] / 12.0) / df["P"].shift(1) / (df["C"] / df["C"].shift(1))
    df["idx"] = r.fillna(1.0).cumprod()
    df["cape"] = cape.reindex(df.index)
    df["tr"] = tasso_reale().reindex(df.index.to_timestamp("M")).values
    df.index = df.index.to_timestamp("M")
    return df.dropna(subset=["cape"])


def _mese(x: pd.Series) -> pd.Series:
    x = x.dropna()
    x = x.groupby(x.index.to_period("M")).last()
    x.index = x.index.to_timestamp("M")
    return x


def tasso_reale() -> pd.Series:
    """Tasso a 10 anni meno inflazione sui 12 mesi (in frazione), mese per mese dal 1872: Shiller fino al 2023, poi FRED (GS10 e inflazione annua)."""
    g = _mese(store.load("gs10_shiller")) / 100
    g2 = _mese(store.load("gs10_m")) / 100
    g = pd.concat([g, g2[g2.index > g.index[-1]]])
    c = _mese(store.load("cpi_shiller"))
    inf = c.pct_change(12)
    y = _mese(store.load("cpi_yoy")) / 100
    inf = pd.concat([inf, y[y.index > inf.index[-1]]])
    return (g - inf).dropna()


def _target(df: pd.DataFrame, h: int) -> pd.Series:
    n = 12 * h
    return (df["idx"].shift(-n) / df["idx"]) ** (1.0 / h) - 1


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    b = np.cov(x, y, bias=True)[0, 1] / max(np.var(x), 1e-12)
    return float(y.mean() - b * x.mean()), float(b)


def oos(df: pd.DataFrame, h: int) -> pd.DataFrame:
    """Previsione in avanti per ogni mese dal 1920: yhat, benchmark (media storica nota), esito reale (se la finestra è conclusa), quantili dei residui noti."""
    n = 12 * h
    y = _target(df, h)
    x = np.log(df["cape"].values)
    yv = y.values
    rows = []
    for i in range(len(df)):
        if df.index[i] < pd.Timestamp(PRIMO_OOS):
            continue
        ok = np.arange(0, max(i - n + 1, 0))              # coppie con finestra conclusa alla data i (s + n <= i)
        ok = ok[~np.isnan(yv[ok])] if len(ok) else ok
        if len(ok) < 120:
            continue
        a, b = _ols(x[ok], yv[ok])
        res = yv[ok] - (a + b * x[ok])
        yh = a + b * x[i]
        rows.append({"date": df.index[i], "yhat": yh, "bench": float(yv[ok].mean()), "y": yv[i], "q10": float(np.quantile(res, .10)), "q50": float(np.quantile(res, .5)),
                     "q90": float(np.quantile(res, .90)), "p_neg": float((yh + res < 0).mean()), "b": b, "n": len(ok)})
    return pd.DataFrame(rows).set_index("date")


def r2(o: pd.DataFrame) -> float | None:
    s = o.dropna(subset=["y"])
    if len(s) < 60:
        return None
    return float(1 - ((s["y"] - s["yhat"]) ** 2).sum() / ((s["y"] - s["bench"]) ** 2).sum())


def valuta_orizzonte(df: pd.DataFrame, h: int) -> dict:
    o = oos(df, h)
    s = o.dropna(subset=["y"])
    a, b = s[s.index <= META], s[s.index > META]
    cop = lambda z: None if len(z) < 30 else round(float(((z["y"] >= z["yhat"] + z["q10"]) & (z["y"] <= z["yhat"] + z["q90"])).mean()), 3)
    ra, rb, rt = r2(a), r2(b), r2(s)
    et = "buona" if (ra is not None and rb is not None and ra > 0.10 and rb > 0.10) else ("media" if (ra is not None and rb is not None and ra > 0 and rb > 0) else "debole")
    return {"h": h, "r2": _r(rt), "r2_prima": _r(ra), "r2_dopo": _r(rb), "copertura": {"tutto": cop(s), "prima": cop(a), "dopo": cop(b)},
            "pendenza": {"prima": _r(float(a["b"].mean())) if len(a) else None, "dopo": _r(float(b["b"].mean())) if len(b) else None},
            "n_indipendenti": int(len(df) / (12 * h)), "etichetta": et, "oos": o}


def _r(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 4)


def _X(df: pd.DataFrame, idx) -> np.ndarray:
    return np.column_stack([np.ones(len(idx)), np.log(df["cape"].values[idx]), df["tr"].values[idx]])


def oos_b(df: pd.DataFrame, h: int) -> pd.DataFrame:
    """Come oos(), ma con due variabili: ln(CAPE) e tasso reale. Solo mesi con tasso disponibile."""
    n = 12 * h
    y = _target(df, h).values
    ok_tr = ~np.isnan(df["tr"].values)
    rows = []
    for i in range(len(df)):
        if df.index[i] < pd.Timestamp(PRIMO_OOS) or not ok_tr[i]:
            continue
        ok = np.arange(0, max(i - n + 1, 0))
        ok = ok[~np.isnan(y[ok]) & ok_tr[ok]] if len(ok) else ok
        if len(ok) < 120:
            continue
        beta = np.linalg.lstsq(_X(df, ok), y[ok], rcond=None)[0]
        res = y[ok] - _X(df, ok) @ beta
        yh = float((_X(df, np.array([i])) @ beta)[0])
        rows.append({"date": df.index[i], "yhat": yh, "bench": float(y[ok].mean()), "y": y[i], "q10": float(np.quantile(res, .10)), "q90": float(np.quantile(res, .90))})
    return pd.DataFrame(rows).set_index("date")


def confronta_b(df: pd.DataFrame, h: int) -> dict:
    """Prova della variante B contro A sugli stessi mesi, nelle due metà; B sostituisce A solo se migliora l'R² di almeno 0,02 in entrambe."""
    a, b = oos(df, h), oos_b(df, h)
    a = a.reindex(b.index)
    out = {"h": h}
    for nome, f in (("prima", lambda z: z[z.index <= META]), ("dopo", lambda z: z[z.index > META])):
        ra, rb = r2(f(a)), r2(f(b))
        out[f"r2_a_{nome}"], out[f"r2_b_{nome}"] = _r(ra), _r(rb)
    d1 = None if out["r2_a_prima"] is None or out["r2_b_prima"] is None else out["r2_b_prima"] - out["r2_a_prima"]
    d2 = None if out["r2_a_dopo"] is None or out["r2_b_dopo"] is None else out["r2_b_dopo"] - out["r2_a_dopo"]
    out["delta_prima"], out["delta_dopo"] = _r(d1), _r(d2)
    out["adottata"] = bool(d1 is not None and d2 is not None and d1 >= SOGLIA_B and d2 >= SOGLIA_B)
    return out


def previsione_b(df: pd.DataFrame, h: int, cape_oggi: float, tr_oggi: float) -> dict:
    y = _target(df, h)
    pairs = y.dropna()
    ok = np.array([df.index.get_loc(d) for d in pairs.index])
    m = ~np.isnan(df["tr"].values[ok])
    ok = ok[m]
    beta = np.linalg.lstsq(_X(df, ok), y.values[ok], rcond=None)[0]
    res = y.values[ok] - _X(df, ok) @ beta
    yh = float(beta @ np.array([1.0, np.log(cape_oggi), tr_oggi]))
    return {"atteso": _r(yh), "p10": _r(yh + float(np.quantile(res, .10))), "p50": _r(yh + float(np.quantile(res, .5))), "p90": _r(yh + float(np.quantile(res, .90))),
            "p_perdita": _r(float((yh + res < 0).mean())), "coef_tasso": _r(float(beta[2]))}


def fase(df: pd.DataFrame, cape_oggi: float) -> dict:
    """Percentile del CAPE di oggi rispetto a tutta la storia conosciuta e fase (soglie fissate nel protocollo)."""
    storia = df["cape"].dropna()
    pc = float((storia < cape_oggi).mean())
    f = "Espansione sana" if pc < SOGLIA_SANA else ("Maturità: valutazioni care" if pc < SOGLIA_CARA else "Rischio di contrazione lunga")
    return {"percentile": pc, "nome": f, "codice": "sana" if pc < SOGLIA_SANA else ("cara" if pc < SOGLIA_CARA else "contrazione")}


def prova_fasi(df: pd.DataFrame) -> dict:
    """Prova 3: rendimento reale mediano a 10 anni per fase (percentile in avanti), nelle due metà."""
    y = _target(df, 10)
    cape = df["cape"]
    pc = cape.expanding(240).apply(lambda w: float((w[:-1] < w[-1]).mean()) if len(w) > 1 else np.nan, raw=True)
    out = {}
    for nome, mask in (("sana", pc < SOGLIA_SANA), ("cara", (pc >= SOGLIA_SANA) & (pc < SOGLIA_CARA)), ("contrazione", pc >= SOGLIA_CARA)):
        s = y[mask].dropna()
        out[nome] = {"mediana": _r(float(s.median())) if len(s) else None, "n": int(len(s)),
                     "prima": _r(float(s[s.index <= META].median())) if (s.index <= META).sum() > 24 else None, "dopo": _r(float(s[s.index > META].median())) if (s.index > META).sum() > 24 else None,
                     "perdita": _r(float((s < 0).mean())) if len(s) else None}
    ok = all(out["contrazione"][k] is not None and out["sana"][k] is not None and out["contrazione"][k] < out["sana"][k] for k in ("prima", "dopo"))
    out["superata"] = bool(ok)
    return out


def anni_simili(df: pd.DataFrame, cape_oggi: float, tol: float = 0.25) -> list[dict]:
    """Episodi con CAPE entro ±25% da oggi (separati da almeno 12 mesi) e che cosa è successo dopo."""
    near = df[(df["cape"] >= cape_oggi * (1 - tol)) & (df["cape"] <= cape_oggi * (1 + tol))]
    out, start, prev = [], None, None
    for dt in near.index:
        if prev is None or (dt - prev).days > 365:
            if start is not None:
                out.append((start, prev))
            start = dt
        prev = dt
    if start is not None:
        out.append((start, prev))
    ys = {h: _target(df, h) for h in (5, 10, 15)}
    res = []
    for a, b in out:
        sel = near[(near.index >= a) & (near.index <= b)]
        pk = sel["cape"].idxmax()
        res.append({"da": str(a.date())[:7], "a": str(b.date())[:7], "mesi": int(len(sel)), "cape_max": _r(float(sel["cape"].max())), "picco": str(pk.date())[:7],
                    **{f"r{h}": _r(ys[h].reindex(sel.index).median()) for h in (5, 10, 15)}})
    return res


def decenni_perduti(df: pd.DataFrame) -> list[dict]:
    """Periodi in cui chi ha investito ha perso potere d'acquisto per 10 anni (rendimento totale reale a 10 anni negativo)."""
    y = _target(df, 10).dropna()
    neg = y[y < 0]
    out, start, prev = [], None, None
    for dt in neg.index:
        if prev is None or (dt - prev).days > 400:
            if start is not None:
                out.append((start, prev))
            start = dt
        prev = dt
    if start is not None:
        out.append((start, prev))
    return [{"da": str(a.date())[:7], "a": str(b.date())[:7], "peggiore": _r(float(y[a:b].min()))} for a, b in out]


def calcola() -> dict:
    df = dati_mensili()
    cape_oggi = float(store.load("cape_m").dropna().iloc[-1])
    ult = df.index[-1]
    res = {"asof": str(pd.Timestamp.now().date()), "dati_fino_a": str(ult.date())[:7], "cape_oggi": cape_oggi, "fase": fase(df, cape_oggi), "prova_fasi": prova_fasi(df),
           "tasso_reale_oggi": _r(float(tasso_reale().iloc[-1])), "orizzonti": {}, "anni_simili": anni_simili(df, cape_oggi), "decenni_perduti": decenni_perduti(df)}
    x_oggi = np.log(cape_oggi)
    for h in ORIZZONTI:
        v = valuta_orizzonte(df, h)
        n = 12 * h
        y = _target(df, h)
        pairs = y.dropna()
        ok = np.log(df["cape"].reindex(pairs.index).values)
        a, b = _ols(ok, pairs.values)
        res_ = pairs.values - (a + b * ok)
        yh = a + b * x_oggi
        o = v.pop("oos")
        v.update({"atteso": _r(yh), "p10": _r(yh + float(np.quantile(res_, .10))), "p50": _r(yh + float(np.quantile(res_, .5))), "p90": _r(yh + float(np.quantile(res_, .90))),
                  "p_perdita": _r(float((yh + res_ < 0).mean())), "media_storica": _r(float(pairs.mean())), "a": _r(a), "b": _r(b)})
        if h in ORIZZONTI_B:
            try:
                cb = confronta_b(df, h)
                tr_oggi = float(tasso_reale().iloc[-1])
                cb.update(previsione_b(df, h, cape_oggi, tr_oggi))
                cb["tasso_reale_oggi"] = _r(tr_oggi)
                v["variante_b"] = cb
                v["modello"] = "B" if cb["adottata"] else "A"
                if cb["adottata"]:
                    v["atteso_a"], v["p_perdita_a"] = v["atteso"], v["p_perdita"]
                    v.update({k2: cb[k2] for k2 in ("atteso", "p10", "p50", "p90", "p_perdita")})
            except Exception as e:  # noqa: BLE001
                v["variante_b"] = {"errore": str(e)[:80]}
        res["orizzonti"][str(h)] = v
        if h == 10:
            s = pairs.iloc[::3]
            res["dispersione10"] = {"punti": [[round(float(df["cape"][d]), 2), round(float(vv), 4), str(d.year)] for d, vv in s.items()], "a": _r(a), "b": _r(b)}
    c = df["cape"]
    res["serie_cape"] = [[str(d.date())[:7], round(float(v), 2)] for d, v in c.iloc[::6].items()] + [[str(ult.date())[:7], round(float(c.iloc[-1]), 2)]]
    res["cape_percentili"] = {q: _r(float(c.quantile(q))) for q in (0.1, 0.25, 0.5, 0.75, 0.85, 0.9)}
    y10 = _target(df, 10).dropna()
    res["rendimento10_per_anno"] = [[str(d.year) + "-" + str(d.month).zfill(2), round(float(v), 4)] for d, v in y10.iloc[::6].items()]
    return res


def aggiorna(log=print) -> dict:
    r = calcola()
    FILE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    log("[lungo periodo] fase: " + r["fase"]["nome"] + " · CAPE " + f"{r['cape_oggi']:.1f}" + " · " + ", ".join(f"{h}a {v['etichetta']}" for h, v in r["orizzonti"].items()))
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
