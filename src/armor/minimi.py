# -*- coding: utf-8 -*-
"""Radar dei minimi (PROTOCOLLO_MINIMI.md, parte A): il mercato è vicino a un minimo a 1 settimana, 1 mese, 3 mesi, 1 anno?
Usa FHS+VIX (già in produzione) per stimare la probabilità q che nelle H sedute successive il prezzo NON scenda più di t sotto quello di oggi,
e il calo residuo (50%, 80%, 95%). Si misura sul passato se q è affidabile: l'etichetta (verificata / parziale / non verificata) viene da lì.
File: data/minimi_storia.csv (previsioni giorno per giorno), data/minimi_valutazione.json (prove), data/minimi_oggi.json (oggi)."""
import json

import numpy as np
import pandas as pd

from . import fhs, store
from .config import DATA

SCALE = {"1s": (5, 0.01), "1m": (21, 0.02), "3m": (63, 0.04), "1a": (252, 0.08)}
NOMI = {"1s": "1 settimana", "1m": "1 mese", "3m": "3 mesi", "1a": "1 anno"}
HMAX = 252
SOGLIA_ALTA, SOGLIA_MEDIA = 0.75, 0.55
STORIA = DATA / "minimi_storia.csv"
VALUT = DATA / "minimi_valutazione.json"
OGGI = DATA / "minimi_oggi.json"
TARATURA_FINE = "2012-12-31"
# serie «usd» = S&P 500 (dal 1990); serie «eur» = VWCE in euro (dal 2011): stessi metodi, file e periodi di taratura propri (PROTOCOLLO_MINIMI.md, parte C)
FILE_EUR = {"storia": DATA / "minimi_eur_storia.csv", "valut": DATA / "minimi_eur_valutazione.json", "oggi": DATA / "minimi_eur_oggi.json"}
FILE_USD = {"storia": STORIA, "valut": VALUT, "oggi": OGGI}
CFG = {"usd": {"file": FILE_USD, "fine": TARATURA_FINE, "da": "1990-01-01"}, "eur": {"file": FILE_EUR, "fine": "2018-12-31", "da": "2011-01-01"}}


def prezzi(serie: str = "usd") -> pd.Series:
    if serie == "eur":
        from . import serie_eur
        return serie_eur.costruisci()["vwce_eur"].dropna()
    from .features import closed_sp500
    return closed_sp500()
MIN_CASI = 150


# ---------------------------------------------------------------- previsione
def statistiche(paths: np.ndarray) -> dict:
    """Da percorsi simulati (HMAX × sims, base 1): per scala q (minimo tenuto) e calo residuo al 50/80/95%."""
    out = {}
    for k, (h, t) in SCALE.items():
        mn = np.minimum(paths[:h].min(axis=0), 1.0)
        dd = 1.0 - mn                                   # calo massimo ulteriore (>= 0)
        out[k] = {"q": float((dd <= t).mean()), "r50": float(np.quantile(dd, .5)), "r80": float(np.quantile(dd, .8)), "r95": float(np.quantile(dd, .95))}
    return out


def _vix_a(vix: pd.Series | None, t) -> float | None:
    if vix is None:
        return None
    v = vix[vix.index <= t]
    return float(v.iloc[-1]) if len(v) and (pd.Timestamp(t) - v.index[-1]).days < 7 else None


def storia_walk_forward(p: pd.Series, vix: pd.Series | None, dates, refit_every: int = 252, sims: int = 1500, embargo: int = 5, w: float = 0.5, log=print) -> pd.DataFrame:
    """Previsioni walk-forward (solo dati noti alla data), una riga per data."""
    p = p.dropna()
    r_all = fhs.log_returns(p[p.index >= fhs.FIT_START])
    idx = r_all.index
    rows, params, last_fit, x0 = [], None, -10 ** 9, None
    for t in dates:
        if t not in idx:
            continue
        i = idx.get_loc(t)
        if i < 750:
            continue
        if params is None or i - last_fit >= refit_every:
            params = fhs.fit(r_all.values[:max(i - embargo, 500)], x0)
            x0 = params["theta"]
            last_fit = i
        s2 = fhs.adjust_with_vix(fhs.next_variance(params, r_all.values[: i + 1]), _vix_a(vix, t), w)
        st = statistiche(fhs.simulate(params, s2, sims, HMAX, seed=int(t.strftime("%Y%m%d")) % (2 ** 31)))
        row = {"date": t}
        for k, v in st.items():
            for c, x in v.items():
                row[f"{c}_{k}"] = round(x, 4)
        rows.append(row)
        if len(rows) % 200 == 0:
            log(f"[minimi] {len(rows)} date, ultima {t.date()}")
    return pd.DataFrame(rows)


def osservati(p: pd.Series) -> pd.DataFrame:
    """Per ogni seduta e scala: distanza dal minimo delle ultime H sedute (d), esito E (minimo tenuto, NaN se non ancora noto)."""
    out = {}
    for k, (h, t) in SCALE.items():
        past = p.rolling(h, min_periods=h).min()
        out[f"d_{k}"] = p / past - 1
        fut = p[::-1].rolling(h, min_periods=h).min()[::-1].shift(-1)
        e = (fut >= p * (1 - t)).astype(float)
        out[f"E_{k}"] = e.where(fut.notna())
        out[f"fut_{k}"] = (1 - np.minimum(fut / p, 1.0)).where(fut.notna())      # calo massimo ulteriore realizzato
    return pd.DataFrame(out, index=p.index)


# ---------------------------------------------------------------- valutazione
def _lg(q):
    q = np.clip(np.asarray(q, float), 1e-3, 1 - 1e-3)
    return np.log(q / (1 - q))


def _sg(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def _platt(x, y, pen=2.0):
    """Termine fisso e pendenza sul logit, ridge verso (0, 1)."""
    th = np.array([0.0, 1.0])
    X = np.column_stack([np.ones(len(x)), x])
    P = np.diag([pen, pen])
    for _ in range(25):
        mu = _sg(X @ th)
        W = mu * (1 - mu) + 1e-9
        gr = X.T @ (y - mu) - P @ (th - np.array([0.0, 1.0]))
        H = (X * W[:, None]).T @ X + P
        st = np.linalg.solve(H, gr)
        th += st
        if np.abs(st).max() < 1e-7:
            break
    return th


def tabella(storia: pd.DataFrame, p: pd.Series) -> dict:
    """{scala: DataFrame(date indice; q, d, E, fut, cand, base, qc)} sui soli giorni con esito noto; qc = q calibrata in avanti (solo candidati)."""
    st = storia.set_index("date")
    ob = osservati(p)
    pos = pd.Series(np.arange(len(p)), index=p.index)
    res = {}
    for k, (h, t) in SCALE.items():
        d = ob[[f"d_{k}", f"E_{k}", f"fut_{k}"]].reindex(st.index)
        d.columns = ["d", "E", "fut"]
        d["q"] = st[f"q_{k}"]
        d["r80"] = st[f"r80_{k}"]
        d["pos"] = pos.reindex(st.index).values
        d["cand"] = (d["d"] <= t + 1e-12)
        d = d.dropna(subset=["d", "q"])
        d["base"] = np.nan
        d["qc"] = np.nan
        c = d[d["cand"]].copy()
        e = c["E"].values
        pc = c["pos"].values
        base = np.full(len(c), np.nan)
        qc = np.full(len(c), np.nan)
        th = None
        for i in range(len(c)):
            mat = np.flatnonzero((pc[:i] + h <= pc[i]) & ~np.isnan(e[:i]))
            base[i] = float(e[mat].mean()) if len(mat) >= 30 else 0.5
            if len(mat) >= MIN_CASI:
                if th is None or i % 5 == 0:
                    th = _platt(_lg(c["q"].values[mat]), e[mat])
                qc[i] = float(_sg(th[0] + th[1] * _lg(c["q"].values[i])))
        c["base"], c["qc"] = base, qc
        res[k] = (d, c)
    return res


def _fasce(c: pd.DataFrame, col: str = "q") -> list[dict]:
    out = []
    for nome, lo, hi in (("bassa", 0.0, SOGLIA_MEDIA), ("media", SOGLIA_MEDIA, SOGLIA_ALTA), ("alta", SOGLIA_ALTA, 1.01)):
        s = c[(c[col] >= lo) & (c[col] < hi) & c["E"].notna()]
        out.append({"fascia": nome, "n": int(len(s)), "q_media": None if not len(s) else round(float(s[col].mean()), 3), "reale": None if not len(s) else round(float(s["E"].mean()), 3)})
    return out


def valuta(storia: pd.DataFrame, p: pd.Series, fine: str = TARATURA_FINE) -> dict:
    """Prove 1-5 del protocollo, per scala e per periodo."""
    from .modeleval import auc, block_ci
    T = tabella(storia, p)
    res = {"protocollo": "PROTOCOLLO_MINIMI.md", "asof": str(storia["date"].max().date()), "scale": {}}
    for k, (d, c) in T.items():
        h, t = SCALE[k]
        c = c[c["E"].notna()]
        r = {"nome": NOMI[k], "tolleranza": t, "n_giorni": int(len(d[d["E"].notna()])), "n_candidati": int(len(c))}
        if len(c) < 60:
            r["etichetta"] = "non verificata"
            res["scale"][k] = r
            continue

        def blocco(s: pd.DataFrame, col: str = "q") -> dict:
            if len(s) < 40:
                return {"n": int(len(s))}
            eb, em = (s["base"] - s["E"]) ** 2, (s[col] - s["E"]) ** 2
            lo, hi = block_ci(em.values, eb.values, 5)
            return {"n": int(len(s)), "risparmio": round(float(1 - em.sum() / eb.sum()) * 100, 1), "ic90": [round(lo * 100, 1), round(hi * 100, 1)],
                    "auc": round(auc(s[col], s["E"]), 3), "freq": round(float(s["E"].mean()), 3), "q_media": round(float(s[col].mean()), 3)}
        tar, con = c[c.index <= fine], c[c.index > fine]
        r["tutto"], r["taratura"], r["conferma"] = blocco(c), blocco(tar), blocco(con)
        r["fasce"] = _fasce(c)
        alta = [f for f in r["fasce"] if f["fascia"] == "alta"][0]
        r["copertura80"] = {"tutto": round(float((c["fut"] <= c["r80"]).mean()), 3), "taratura": round(float((tar["fut"] <= tar["r80"]).mean()), 3) if len(tar) else None,
                            "conferma": round(float((con["fut"] <= con["r80"]).mean()), 3) if len(con) else None}
        # calibrazione facoltativa (adottata solo con la regola del protocollo)
        cc = c.dropna(subset=["qc"])
        tc, cc2 = cc[cc.index <= fine], cc[cc.index > fine]
        adot = False
        if len(tc) >= 40 and len(cc2) >= 40:
            b_t = ((tc["qc"] - tc["E"]) ** 2).mean() < ((tc["q"] - tc["E"]) ** 2).mean()
            b_c = ((cc2["qc"] - cc2["E"]) ** 2).mean() <= ((cc2["q"] - cc2["E"]) ** 2).mean() * 1.005
            adot = bool(b_t and b_c)
        r["calibrazione_adottata"] = adot
        # prove
        p1 = lambda b: b.get("ic90") is not None and b["ic90"][0] > 0
        mono = [f["reale"] for f in r["fasce"] if f["reale"] is not None and f["n"] >= 15]
        p2 = (all(mono[i] <= mono[i + 1] + 1e-9 for i in range(len(mono) - 1)) if len(mono) >= 2 else False) and (alta["n"] < 15 or abs(alta["reale"] - alta["q_media"]) <= 0.10)
        p3 = all(x is not None and 0.74 <= x <= 0.86 for x in (r["copertura80"]["taratura"], r["copertura80"]["conferma"]))
        sup = {"p1_taratura": bool(p1(r["taratura"])), "p1_conferma": bool(p1(r["conferma"])), "p2_taratura_fasce": bool(p2), "p3_copertura": bool(p3)}
        r["prove"] = sup
        n_ok = sum(sup.values())
        r["etichetta"] = "verificata" if (sup["p1_taratura"] and sup["p1_conferma"] and sup["p2_taratura_fasce"] and sup["p3_copertura"]) else ("parziale" if n_ok >= 2 else "non verificata")
        # utilità: rendimenti dopo i giorni «minimo probabile»
        rp = {}
        for lab, n in (("1m", 21), ("3m", 63), ("12m", 252)):
            fr = (p.shift(-n) / p - 1).reindex(d.index)
            cand_alta = c[(c["q"] >= SOGLIA_ALTA)].index
            rp[lab] = {"minimo_probabile": {"n": int(fr.reindex(cand_alta).notna().sum()), "mediana": _r(fr.reindex(cand_alta).median()), "positivi": _r((fr.reindex(cand_alta) > 0).mean())},
                       "tutti": {"n": int(fr.notna().sum()), "mediana": _r(fr.median()), "positivi": _r((fr > 0).mean())}}
        r["utilita"] = rp
        res["scale"][k] = r
    return res


def _r(x) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), 4)


def calibrazione_finale(storia: pd.DataFrame, p: pd.Series, valut: dict) -> dict:
    """Parametri della calibrazione, solo per le scale in cui è stata adottata (fit su tutti i candidati con esito noto)."""
    T = tabella(storia, p)
    out = {}
    for k, (d, c) in T.items():
        if valut["scale"].get(k, {}).get("calibrazione_adottata"):
            s = c[c["E"].notna()]
            if len(s) >= MIN_CASI:
                out[k] = [float(x) for x in _platt(_lg(s["q"].values), s["E"].values)]
    return out


# ---------------------------------------------------------------- oggi
def verdetto(cand: bool, q: float) -> str:
    if not cand:
        return "non_ancora"
    return "probabile" if q >= SOGLIA_ALTA else ("possibile" if q >= SOGLIA_MEDIA else "non_ancora")


def oggi(p: pd.Series | None = None, vix: pd.Series | None = None, valut: dict | None = None, cal: dict | None = None, sims: int = 3000, serie: str = "usd") -> dict:
    p = prezzi(serie) if p is None else p
    vix = store.load("vix") if vix is None else vix
    t = p.index[-1]
    r = fhs.log_returns(p[p.index >= fhs.FIT_START])
    params = fhs.fit(r.values)
    s2 = fhs.adjust_with_vix(fhs.next_variance(params, r.values), _vix_a(vix, t), 0.5)
    st = statistiche(fhs.simulate(params, s2, sims, HMAX, seed=int(t.strftime("%Y%m%d")) % (2 ** 31)))
    if valut is None:
        try:
            valut = json.loads(CFG[serie]["file"]["valut"].read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            valut = {"scale": {}}
    cal = cal if cal is not None else (valut.get("calibrazione") or {})
    out = {"data": str(t.date()), "prezzo": float(p.iloc[-1]), "scale": {}}
    for k, (h, tol) in SCALE.items():
        past = p.iloc[-h:]
        d = float(p.iloc[-1] / past.min() - 1)
        q = st[k]["q"]
        if k in cal:
            q = float(_sg(cal[k][0] + cal[k][1] * _lg(q)))
        cand = d <= tol + 1e-12
        v = valut.get("scale", {}).get(k, {})
        out["scale"][k] = {"nome": NOMI[k], "sedute": h, "tolleranza": tol, "dal_minimo": d, "minimo_livello": float(past.min()), "minimo_data": str(past.idxmin().date()),
                           "candidato": bool(cand), "q": float(q), "q_grezza": float(st[k]["q"]), "r50": st[k]["r50"], "r80": st[k]["r80"], "r95": st[k]["r95"],
                           "verdetto": verdetto(cand, q), "etichetta": v.get("etichetta", "non verificata"),
                           "fasce": v.get("fasce"), "copertura80": v.get("copertura80")}
    return out


# ---------------------------------------------------------------- lavoro giornaliero
def carica_oggi(serie: str = "usd") -> dict | None:
    try:
        return json.loads(CFG[serie]["file"]["oggi"].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def carica_storia(serie: str = "usd") -> pd.DataFrame | None:
    try:
        d = pd.read_csv(CFG[serie]["file"]["storia"], parse_dates=["date"])
        return d if len(d) else None
    except Exception:  # noqa: BLE001
        return None


def costruisci_storia(log=print, serie: str = "usd") -> pd.DataFrame:
    """Calcola la storia settimanale (una volta, 3-5 minuti) e la salva."""
    p = prezzi(serie)
    vix = store.load("vix")
    dates = p.index[p.index >= CFG[serie]["da"]][::5]
    d = storia_walk_forward(p, vix, dates, log=log)
    d.to_csv(CFG[serie]["file"]["storia"], index=False, date_format="%Y-%m-%d")
    return d


def valuta_e_salva(log=print, serie: str = "usd") -> dict:
    p = prezzi(serie)
    st = carica_storia(serie)
    v = valuta(st, p, CFG[serie]["fine"])
    v["calibrazione"] = calibrazione_finale(st, p, v)
    CFG[serie]["file"]["valut"].write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[minimi {serie}] valutazione: " + ", ".join(f"{k} {x.get('etichetta')}" for k, x in v["scale"].items()))
    return v


def aggiorna(log=print, serie: str = "usd") -> dict:
    """Ogni giorno: stima di oggi (salvata in minimi_oggi.json e aggiunta alla storia). La storia e la valutazione si rifanno con la convalida mensile."""
    o = oggi(serie=serie)
    f = CFG[serie]["file"]
    f["oggi"].write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        st = carica_storia(serie)
        if st is not None and pd.Timestamp(o["data"]) not in set(st["date"]):
            row = {"date": pd.Timestamp(o["data"])}
            for k, v in o["scale"].items():
                row.update({f"q_{k}": round(v["q_grezza"], 4), f"r50_{k}": round(v["r50"], 4), f"r80_{k}": round(v["r80"], 4), f"r95_{k}": round(v["r95"], 4)})
            pd.concat([st, pd.DataFrame([row])]).to_csv(f["storia"], index=False, date_format="%Y-%m-%d")
    except Exception as e:  # noqa: BLE001
        log("[minimi] storia non aggiornata: " + str(e)[:80])
    log(f"[minimi {serie}] " + ", ".join(f"{k} q={x['q']:.2f} {x['verdetto']}" for k, x in o["scale"].items()))
    return o


def marcatori(p: pd.Series, storia: pd.DataFrame | None = None, anni: float = 3.0, serie: str = "usd") -> dict:
    """Per il grafico: per ogni scala i giorni degli ultimi anni con verdetto «probabile» o «possibile» e, se già noto, se il minimo ha tenuto."""
    storia = carica_storia(serie) if storia is None else storia
    if storia is None:
        return {}
    ob = osservati(p)
    st = storia.set_index("date")
    st = st[st.index >= p.index[-1] - pd.Timedelta(days=int(365 * anni))]
    out = {}
    for k, (h, t) in SCALE.items():
        d = ob[f"d_{k}"].reindex(st.index)
        e = ob[f"E_{k}"].reindex(st.index)
        q = st[f"q_{k}"]
        lst = []
        for dt in st.index:
            if pd.isna(d[dt]) or d[dt] > t + 1e-12:
                continue
            v = verdetto(True, float(q[dt]))
            if v == "non_ancora":
                continue
            lst.append([str(dt.date()), v, None if pd.isna(e[dt]) else int(e[dt])])
        out[k] = lst
    return out
