"""Ricerca del modello (PIANO_MODELLO §2, §4, §5). Comando: python -m armor ricerca (workflow «Ricerca modello Armor»).

Regole che il codice fa rispettare:
- walk-forward: ogni anno di prova usa solo mesi il cui esito era già noto (purge = orizzonte) e dati già pubblicati (ritardi in fondamentali.LAG);
- hold-out: gli esiti devono chiudersi entro il 31/12/2018. Gli anni 2019+ si usano UNA sola volta nella prova finale (patch 23, holdout=True);
- soglie dei segnali singoli fissate prima (SEGNALI), mai ottimizzate;
- ogni prova finisce in data/ricerca/registro_prove.csv (anche quelle andate male).

Questa è la forma iniziale (Fase A): segnali singoli, logistica per famiglia, storia lunga, conteggio dei segnali, prima analisi per episodio
e mesi più simili a oggi. I modelli a due stadi, il gradient boosting monotono e la taratura si aggiungono nella Fase B."""
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import fondamentali, store
from .config import DATA

OUT = DATA / "ricerca"
REGISTRO = OUT / "registro_prove.csv"
FINE_RICERCA = pd.Timestamp("2018-12-31")
HOLDOUT = pd.Timestamp("2019-01-01")
SOTTOPERIODI = [("1960-1989", 1960, 1989), ("1990-2009", 1990, 2009), ("2010-2018", 2010, 2018)]

FAMIGLIE = {
    "Salute delle aziende": ["eps_g12", "eps_g3", "sales_g12", "margin_sp", "cp_g4", "delinq_biz", "chargeoff_biz", "busloans_g6"],
    "Credito": ["credito", "baa_d6", "nfci", "anfci", "sloos", "nfci_credit", "nfci_leverage", "kcfsi"],
    "Valutazioni": ["cape_m", "erp"],
    "Inflazione e tassi": ["infl", "infl_acc", "real_ff", "curva", "curva_min12", "dgs10"],
    "Economia reale": ["claims_up", "ccsa_yoy", "sahm", "cfnai", "permit_yoy", "indpro_g12", "isratio"],
    "Liquidità e leva": ["net_liq_13w", "m2_yoy", "margin_yoy"],
    "Mercato interno": ["rel_small", "rel_eqw", "rel_cicl", "rel_semi", "rel_trasp", "rel_banche", "rel_rame_oro", "rel_credito"],
    "Prezzi e paura": ["mom12", "sma10", "dd252", "vix"],
    "Europa": ["ciss"],
}
LUNGO = ["eps_g12", "eps_g3", "cape_m", "erp", "credito", "baa_d6", "curva", "curva_min12", "infl", "indpro_g12", "sahm", "mom12", "sma10", "dd252"]
# soglie pre-registrate (§2.3): nome -> (colonna, confronto, soglia)
SEGNALI = {
    "Utili in calo (12 mesi)": ("eps_g12", "<", 0),
    "Utili in calo forte (oltre -10%)": ("eps_g12", "<", -10),
    "CAPE sopra 30": ("cape_m", ">", 30),
    "Premio utili-bond sotto 1%": ("erp", "<", 1),
    "Spread del credito +0,5 punti in 6 mesi": ("baa_d6", ">", 0.5),
    "Sussidi +20% dal minimo dell'anno": ("claims_up", ">", 20),
    "Curva dei tassi invertita (ultimi 12 mesi)": ("curva_min12", "<", 0),
    "Prezzo sotto la media a 10 mesi": ("sma10", "<", 0),
    "VIX sopra 30": ("vix", ">", 30),
    "Inflazione sopra 4%": ("infl", ">", 4),
    "Disoccupazione in salita (regola di Sahm)": ("sahm", ">=", 0.5),
    "Prestiti alle imprese in ritardo sopra 2,5%": ("delinq_biz", ">", 2.5),
    "Credito alle imprese in calo (6 mesi)": ("busloans_g6", "<", 0),
}
OBIETTIVI = [("calo10", 3), ("calo10", 6), ("calo10", 12), ("calo20", 12), ("rialzo", 1), ("rialzo", 3), ("rialzo", 6), ("rialzo", 12)]
NOMI_OB = {"calo10": "calo ≥10%", "calo20": "calo ≥20%", "rialzo": "rialzo"}


def _base_ids() -> list:
    ids = set(sum(FAMIGLIE.values(), [])) | set(LUNGO) | {c for c, _o, _t in SEGNALI.values()}
    ids -= {"credito", "baa_d6", "curva", "curva_min12", "infl", "mom12", "sma10", "dd252"}
    return sorted(ids | {"baa10y", "baa_lungo", "t10y3m", "curve_lunga", "cpi_yoy", "cpi_yoy_lungo"})


def dataset(load=store.load, end=None, con_oggi: bool = False) -> pd.DataFrame:
    """Variabili a fine mese, ciascuna con il suo ritardo di pubblicazione."""
    X = fondamentali.mensile(_base_ids(), load=load, end=end, con_oggi=con_oggi)
    sp = load("sp500").dropna()
    pos = sp.index.searchsorted(X.index - pd.Timedelta(days=1), side="right") - 1   # chiusura nota al giorno prima
    m = pd.Series(np.where(pos >= 0, sp.values[np.clip(pos, 0, None)], np.nan), index=X.index)
    hi = sp.rolling(252, min_periods=120).max()
    hm = pd.Series(np.where(pos >= 0, hi.values[np.clip(pos, 0, None)], np.nan), index=X.index)
    X["mom12"] = (m / m.shift(12) - 1) * 100
    X["sma10"] = (m / m.rolling(10).mean() - 1) * 100
    X["dd252"] = (m / hm - 1) * 100
    X["credito"] = X["baa10y"].combine_first(X["baa_lungo"])
    X["baa_d6"] = X["credito"] - X["credito"].shift(6)
    X["curva"] = X["t10y3m"].combine_first(X["curve_lunga"])
    X["curva_min12"] = X["curva"].rolling(12, min_periods=6).min()
    X["infl"] = X["cpi_yoy"].combine_first(X["cpi_yoy_lungo"])
    return X


def obiettivi(sp: pd.Series, idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Per ogni fine mese: calo massimo entro h mesi (calo10_h, calo20_h), rialzo a h mesi (rialzo_h), rendimento (ret_h)."""
    sp = sp.dropna()
    d, v = sp.index.values, sp.values
    last = sp.index[-1]
    out = {}
    for h in sorted({h for _k, h in OBIETTIVI}):
        dd, rt = np.full(len(idx), np.nan), np.full(len(idx), np.nan)
        for i, t in enumerate(idx):
            e = t + pd.DateOffset(months=h)
            if e > last:
                continue
            a = np.searchsorted(d, np.datetime64(t), side="right")
            b = np.searchsorted(d, np.datetime64(e), side="right")
            if a == 0 or b - a < 5:
                continue
            p0 = v[a - 1]
            dd[i] = (v[a:b].min() / p0 - 1) * 100
            rt[i] = (v[b - 1] / p0 - 1) * 100
        out[f"dd_{h}"], out[f"ret_{h}"] = dd, rt
    Y = pd.DataFrame(out, index=idx)
    for k, h in OBIETTIVI:
        src = Y[f"dd_{h}"] if k.startswith("calo") else Y[f"ret_{h}"]
        y = (src <= -10) if k == "calo10" else ((src <= -20) if k == "calo20" else (src > 0))
        Y[f"{k}_{h}"] = y.astype(float).where(src.notna())
    return Y


def _fit_predict(Xtr, ytr, Xte, modello: str):
    if modello == "gbm":
        from sklearn.ensemble import HistGradientBoostingClassifier
        m = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=150, min_samples_leaf=40).fit(Xtr, ytr)
        return m.predict_proba(Xte)[:, 1]
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(C=0.3, max_iter=1000).fit(sc.transform(Xtr), ytr)
    return m.predict_proba(sc.transform(Xte))[:, 1]


def walk_forward(X: pd.DataFrame, y: pd.Series, h: int, cols: list, anni=(1960, 2018), modello: str = "logit",
                 train_da=None, min_train: int = 120, holdout: bool = False):
    """Previsioni fuori campione anno per anno. Senza holdout=True nessun esito può chiudersi dopo il 31/12/2018."""
    fine = pd.Timestamp.now() if holdout else FINE_RICERCA
    if not holdout and anni[1] >= HOLDOUT.year:
        anni = (anni[0], HOLDOUT.year - 1)
    D = X[cols]
    ok = D.notna().all(axis=1) & y.notna()
    if train_da is not None:
        ok &= X.index >= pd.Timestamp(train_da)
    p, c = pd.Series(np.nan, index=X.index), pd.Series(np.nan, index=X.index)
    chiusura = X.index + pd.DateOffset(months=h)
    for yr in range(anni[0], anni[1] + 1):
        te = ok & (X.index.year == yr) & (chiusura <= fine)
        if not te.any():
            continue
        tr = ok & (chiusura < pd.Timestamp(f"{yr}-01-01"))   # purge: esito noto prima dell'anno di prova
        if tr.sum() < min_train or y[tr].nunique() < 2:
            continue
        p[te] = _fit_predict(D[tr].values, y[tr].values, D[te].values, modello)
        c[te] = float(y[tr].mean())
    return p, c


def metriche(p: pd.Series, c: pd.Series, y: pd.Series, mask=None) -> dict:
    from sklearn.metrics import roc_auc_score
    k = p.notna() & c.notna() & y.notna()
    if mask is not None:
        k &= mask
    if k.sum() < 24 or y[k].nunique() < 2:
        return {"n": int(k.sum()), "eventi": int(y[k].sum()) if k.any() else 0, "auc": None, "bss": None}
    bs, bc = float(np.mean((p[k] - y[k]) ** 2)), float(np.mean((c[k] - y[k]) ** 2))
    return {"n": int(k.sum()), "eventi": int(y[k].sum()), "base": round(float(y[k].mean()), 3),
            "auc": round(float(roc_auc_score(y[k], p[k])), 3), "bss": round(1 - bs / bc, 3) if bc > 0 else None}


def segnali_singoli(X: pd.DataFrame, Y: pd.DataFrame, da: int = 1960) -> list:
    """Frequenze storiche con segnale acceso/spento (solo esiti chiusi entro il 2018)."""
    ops = {"<": np.less, ">": np.greater, ">=": np.greater_equal}
    k = (X.index.year >= da) & (X.index + pd.DateOffset(months=12) <= FINE_RICERCA) & Y["dd_6"].notna() & Y["ret_12"].notna()
    out = []
    for nome, (col, op, thr) in SEGNALI.items():
        v = X[col]
        on = k & v.notna() & ops[op](v.fillna(0), thr)
        off = k & v.notna() & ~ops[op](v.fillna(0), thr)
        if on.sum() < 6 or off.sum() < 24:
            out.append({"segnale": nome, "mesi_acceso": int(on.sum()), "nota": "dati insufficienti"})
            continue
        out.append({"segnale": nome, "mesi_acceso": int(on.sum()), "mesi_spento": int(off.sum()), "dal": int(X.index[k & v.notna()][0].year),
                    "p_calo10_6m_acceso": round(float((Y["dd_6"][on] <= -10).mean() * 100), 1),
                    "p_calo10_6m_spento": round(float((Y["dd_6"][off] <= -10).mean() * 100), 1),
                    "ret12_acceso": round(float(Y["ret_12"][on].mean()), 1), "ret12_spento": round(float(Y["ret_12"][off].mean()), 1),
                    "p_rialzo12_acceso": round(float((Y["ret_12"][on] > 0).mean() * 100), 1)})
    return out


def conteggio_segnali(X: pd.DataFrame) -> pd.Series:
    ops = {"<": np.less, ">": np.greater, ">=": np.greater_equal}
    tot = pd.Series(0.0, index=X.index)
    for col, op, thr in SEGNALI.values():
        v = X[col]
        tot += (v.notna() & ops[op](v.fillna(0), thr)).astype(float)
    return tot


def episodi(sp: pd.Series, p: pd.Series, c: pd.Series, y: pd.Series, da="1960-01-01", soglia_calo: float = 20) -> list:
    """Per ogni calo ≥20% (dal massimo al minimo) chiuso entro il 2018: mesi in allarme nei 12 mesi prima del massimo.
    Allarme = previsione superiore a 1,5 volte la frequenza storica."""
    s = sp[(sp.index >= da) & (sp.index <= FINE_RICERCA)].dropna()
    out, peak_v, peak_d, low_v, low_d, in_dd = [], s.iloc[0], s.index[0], s.iloc[0], s.index[0], False
    for d, v in s.items():
        if v > peak_v and not in_dd:
            peak_v, peak_d = v, d
        dd = (v / peak_v - 1) * 100
        if dd <= -soglia_calo and not in_dd:
            in_dd, low_v, low_d = True, v, d
        if in_dd:
            if v < low_v:
                low_v, low_d = v, d
            if v >= peak_v:
                out.append((peak_d, low_d, (low_v / peak_v - 1) * 100))
                in_dd, peak_v, peak_d = False, v, d
    if in_dd:
        out.append((peak_d, low_d, (low_v / peak_v - 1) * 100))
    allarme = (p > 1.5 * c) & p.notna()
    res = []
    for pk, lo, depth in out:
        w = allarme[(allarme.index > pk - pd.DateOffset(months=12)) & (allarme.index <= pk)]
        res.append({"massimo": pk.strftime("%Y-%m"), "minimo": lo.strftime("%Y-%m"), "calo": round(depth, 1),
                    "mesi_valutati": int(p[w.index].notna().sum()), "mesi_in_allarme_prima": int(w.sum())})
    k = allarme & y.notna()
    falsi = int((k & (y == 0)).sum())
    return [{"episodi": res, "mesi_in_allarme": int(k.sum()), "falsi_allarmi": falsi}]


def analoghi(X: pd.DataFrame, Y: pd.DataFrame, cols: list, k: int = 25, distanza_min: int = 3) -> dict:
    """I k mesi del passato più simili all'ultima riga (oggi), distanziati di almeno `distanza_min` mesi, con esito a 12 mesi già noto.
    DA VALIDARE nella Fase B prima di mostrarlo come indicazione."""
    D = X[cols].dropna()
    if len(D) < 200 or X.index[-1] not in D.index:
        return {"nota": "dati insufficienti per gli analoghi", "colonne": cols}
    oggi = D.iloc[-1]
    passato = D.iloc[:-1]
    passato = passato[(passato.index <= X.index[-1] - pd.DateOffset(months=12)) & Y["ret_12"].reindex(passato.index).notna()]
    sd = passato.std().replace(0, 1)
    dist = np.sqrt(((passato - oggi) / sd).pow(2).mean(axis=1)).sort_values()
    scelti = []
    for d in dist.index:
        if all(abs((d.year - s.year) * 12 + d.month - s.month) >= distanza_min for s in scelti):
            scelti.append(d)
        if len(scelti) >= k:
            break
    r12, r6, dd12 = Y["ret_12"].reindex(scelti), Y["ret_6"].reindex(scelti), Y["dd_12"].reindex(scelti)
    return {"data": X.index[-1].strftime("%Y-%m-%d"), "colonne": cols, "k": len(scelti),
            "oggi": {c: round(float(oggi[c]), 2) for c in cols},
            "mesi": [{"mese": s.strftime("%Y-%m"), "distanza": round(float(dist[s]), 2), "ret_6": round(float(r6[s]), 1) if pd.notna(r6[s]) else None,
                      "ret_12": round(float(r12[s]), 1), "calo_max_12": round(float(dd12[s]), 1)} for s in scelti],
            "rialzo_12_su_k": int((r12 > 0).sum()), "mediana_12": round(float(r12.median()), 1),
            "p10_12": round(float(r12.quantile(0.1)), 1), "p90_12": round(float(r12.quantile(0.9)), 1),
            "calo10_12_su_k": int((dd12 <= -10).sum()), "rialzo_6_su_k": int((r6 > 0).sum()),
            "nota": "Non ancora validato: si mostra nell'app solo se supera la verifica della Fase B."}


def _registra(righe: list) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(righe)
    df.to_csv(REGISTRO, mode="a", header=not REGISTRO.exists(), index=False)


def colonne_disponibili(X: pd.DataFrame, cols: list, entro: str) -> list:
    """Colonne con dati dal più tardi `entro` (servono abbastanza anni di addestramento)."""
    keep = []
    for c in cols:
        s = X[c].dropna()
        if len(s) and s.index[0] <= pd.Timestamp(entro):
            keep.append(c)
    return keep


def run(load=store.load, save: bool = True) -> dict:
    import time as _t
    t0 = _t.time()
    X = dataset(load=load, con_oggi=True)
    sp = load("sp500").dropna()
    Y = obiettivi(sp, X.index)
    X["n_segnali"] = conteggio_segnali(X)
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mancanti = [c for c in _base_ids() if X[c].dropna().empty]
    prove = [("Solo prezzi", ["mom12", "sma10", "dd252"], (1960, 2018)),
             ("Conteggio dei segnali", ["n_segnali"], (1960, 2018)),
             ("Storia lunga (tutte le variabili dal 1928)", colonne_disponibili(X, LUNGO, "1955-12-31"), (1960, 2018))]
    for fam, cols in FAMIGLIE.items():
        cc = colonne_disponibili(X, cols, "1992-12-31")
        if cc:
            prove.append((f"Famiglia: {fam}", cc, (2000, 2018)))
    tutte = colonne_disponibili(X, sorted(set(sum(FAMIGLIE.values(), []))), "1992-12-31")
    if tutte:
        prove.append(("Tutte le famiglie (dati dal 1992)", tutte, (2000, 2018)))
    risultati, righe, ep = [], [], None
    for nome, cols, anni in prove:
        for ob, h in OBIETTIVI:
            y = Y[f"{ob}_{h}"]
            p, c = walk_forward(X, y, h, cols, anni=anni)
            m = metriche(p, c, y)
            sub = {lab: metriche(p, c, y, (X.index.year >= a) & (X.index.year <= b)).get("auc") for lab, a, b in SOTTOPERIODI}
            r = {"modello": nome, "obiettivo": f"{NOMI_OB[ob]} entro {h} mesi" if ob != "rialzo" else f"rialzo a {h} mesi", "ob": ob, "h": h,
                 "periodo": f"{anni[0]}-{anni[1]}", "variabili": cols, **m, "auc_sotto": sub}
            risultati.append(r)
            righe.append({"data": oggi, "modello": nome, "tipo": "logit", "obiettivo": f"{ob}_{h}", "periodo": r["periodo"], "variabili": "+".join(cols),
                          "n": m["n"], "eventi": m["eventi"], "auc": m["auc"], "bss": m["bss"], **{f"auc_{k}": v for k, v in sub.items()}})
            if nome.startswith("Storia lunga") and ob == "calo10" and h == 12:
                ep = episodi(sp, p, c, y)
    seg = segnali_singoli(X, Y, 1960)
    seg90 = segnali_singoli(X, Y, 1990)
    an = analoghi(X, Y, colonne_disponibili(X, LUNGO, "1955-12-31"))
    res = {"data": oggi, "versione": "Fase A (forma iniziale)", "fine_ricerca": FINE_RICERCA.strftime("%Y-%m-%d"),
           "nota": "Gli anni 2019-oggi non sono stati usati: sono riservati alla prova finale (patch 23).",
           "prove_totali_registro": None, "mancanti": mancanti, "risultati": risultati, "segnali_dal_1960": seg, "segnali_dal_1990": seg90,
           "episodi_storia_lunga_calo10_12m": ep, "analoghi_oggi": an, "secondi": round(_t.time() - t0, 1)}
    if save:
        _registra(righe)
        try:
            reg = pd.read_csv(REGISTRO)
            res["prove_totali_registro"] = int(reg.drop_duplicates(["modello", "tipo", "obiettivo", "periodo", "variabili"]).shape[0])
        except Exception:  # noqa: BLE001
            pass
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "risultati.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "analoghi_oggi.json").write_text(json.dumps(an, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "episodi.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"[ricerca] {len(risultati)} prove in {res['secondi']}s; serie mancanti: {', '.join(mancanti) or 'nessuna'}", flush=True)
    for r in risultati:
        if r["auc"] is not None:
            print(f"[ricerca] {r['modello'][:38]:38s} {r['obiettivo']:24s} {r['periodo']} AUC {r['auc']:.3f} BSS {r['bss']:+.3f} n {r['n']} eventi {r['eventi']}", flush=True)
    return res


def load_results() -> dict:
    try:
        return json.loads((OUT / "risultati.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
