"""Ricerca del modello (PIANO_MODELLO §2, §4, §5). Comando: python -m armor ricerca (workflow «Ricerca modello Armor»).

Regole che il codice fa rispettare:
- walk-forward: ogni anno di prova usa solo mesi il cui esito era già noto (purge = orizzonte) e dati già pubblicati (ritardi in fondamentali.LAG);
- hold-out: gli esiti devono chiudersi entro il 31/12/2018. Gli anni 2019+ si usano UNA sola volta nella prova finale (patch 23, holdout=True);
- soglie dei segnali singoli fissate prima (SEGNALI), mai ottimizzate;
- ogni prova finisce in data/ricerca/registro_prove.csv (anche quelle andate male).

Fase A: segnali singoli, logistica per famiglia, storia lunga, conteggio dei segnali, episodi, mesi più simili a oggi (`run`).
Fase B (`fase_b`): logistica, alberi monotoni con taratura di Platt, mesi simili (k vicini), famiglie combinate, due stadi (recessione → calo),
«caro + deterioramento», conteggio; confronto con Solo prezzi / Indice Armor / A1 sugli stessi mesi; promozione in ombra con le regole pre-registrate.
Prova finale (`prova_finale`): una sola volta sugli anni 2019-oggi per i modelli promossi."""
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


def _wf(fp, X: pd.DataFrame, y: pd.Series, h: int, anni=(1960, 2018), min_train: int = 120, holdout: bool = False,
        ok=None, purge_extra: int = 0):
    """Motore walk-forward: fp(maschera_addestramento, maschera_prova, inizio_anno) -> probabilità per le righe di prova.
    Senza holdout=True nessun esito può chiudersi dopo il 31/12/2018 (anni 2019+ riservati alla prova finale)."""
    fine = pd.Timestamp.now().normalize() if holdout else FINE_RICERCA
    if not holdout and anni[1] >= HOLDOUT.year:
        anni = (anni[0], HOLDOUT.year - 1)
    ok = (pd.Series(True, index=X.index) if ok is None else ok) & y.notna()
    p, c = pd.Series(np.nan, index=X.index), pd.Series(np.nan, index=X.index)
    chiusura = X.index + pd.DateOffset(months=h)
    for yr in range(anni[0], anni[1] + 1):
        start = pd.Timestamp(f"{yr}-01-01")
        te = ok & (X.index.year == yr) & (chiusura <= fine)
        if not te.any():
            continue
        tr = ok & (chiusura + pd.DateOffset(months=purge_extra) < start)   # purge: esito noto prima dell'anno di prova
        if tr.sum() < min_train or y[tr].nunique() < 2:
            continue
        try:
            p[te] = fp(tr.values, te.values, start)
        except Exception as e:  # noqa: BLE001
            print(f"[ricerca] anno {yr} saltato: {str(e)[:80]}", flush=True)
            continue
        c[te] = float(y[tr].mean())
    return p, c


def walk_forward(X: pd.DataFrame, y: pd.Series, h: int, cols: list, anni=(1960, 2018), modello: str = "logit",
                 train_da=None, min_train: int = 120, holdout: bool = False):
    """Previsioni fuori campione anno per anno con logistica (o alberi). Senza holdout=True nessun esito dopo il 31/12/2018."""
    D = X[cols]
    ok = D.notna().all(axis=1)
    if train_da is not None:
        ok &= X.index >= pd.Timestamp(train_da)
    yv = y.values
    return _wf(lambda tr, te, _s: _fit_predict(D.values[tr], yv[tr], D.values[te], modello), X, y, h, anni, min_train, holdout, ok)


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


COLONNE_REG = ["data", "modello", "tipo", "obiettivo", "periodo", "variabili", "n", "eventi", "auc", "bss", "riferimento", "meglio_sotto",
               "peggio_sotto", "promosso", "auc_1960-1989", "auc_1990-2009", "auc_2010-2018"]


def _registra(righe: list) -> None:
    """Aggiunge le prove al registro con colonne fisse (anche le prove andate male restano)."""
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(righe).reindex(columns=COLONNE_REG)
    df.to_csv(REGISTRO, mode="a", header=not REGISTRO.exists(), index=False)


def prove_totali() -> int:
    try:
        reg = pd.read_csv(REGISTRO)
        return int(reg.drop_duplicates(["modello", "tipo", "obiettivo", "periodo", "variabili"]).shape[0])
    except Exception:  # noqa: BLE001
        return 0


def colonne_disponibili(X: pd.DataFrame, cols: list, entro: str) -> list:
    """Colonne con dati dal più tardi `entro` (servono abbastanza anni di addestramento)."""
    keep = []
    for c in cols:
        s = X[c].dropna()
        if len(s) and s.index[0] <= pd.Timestamp(entro):
            keep.append(c)
    return keep


# ================================================================ Fase B (PIANO_MODELLO §5-§6): modelli, regole, prova finale
# Regole fissate PRIMA di vedere i risultati (pre-registrazione, novembre 2026):
# - obiettivi per l'adozione: calo ≥10% entro 3/6/12 mesi e calo ≥20% entro 12 mesi; la direzione (rialzo) si mostra solo se BSS > 0,01;
# - storia lunga: prova 1960-2018, riferimento «Solo prezzi», sottoperiodi 1960-1989 / 1990-2009 / 2010-2018;
# - dati recenti: prova 2000-2018, riferimento = il migliore tra «Solo prezzi», Indice Armor e A1, sottoperiodi 2000-2006 / 2007-2012 / 2013-2018;
# - ombra: BSS > 0 e AUC ≥ riferimento + 0,02 in almeno 2 sottoperiodi su 3, nessuno sotto riferimento - 0,02 (confronto sugli stessi mesi);
# - prova finale 2019-oggi (una sola volta): BSS > 0 e AUC ≥ Indice Armor sugli stessi mesi → adottato nei numeri dell'app.
SOTTO_2000 = [("2000-2006", 2000, 2006), ("2007-2012", 2007, 2012), ("2013-2018", 2013, 2018)]
PRIMARI = [("calo10", 3), ("calo10", 6), ("calo10", 12), ("calo20", 12)]
# segno del legame con il RISCHIO DI CALO (+1: valori più alti = più rischio). Per il rialzo i segni si invertono.
SEGNI = {"eps_g12": -1, "eps_g3": -1, "sales_g12": -1, "margin_sp": 0, "cp_g4": -1, "delinq_biz": 1, "chargeoff_biz": 1, "busloans_g6": -1,
         "cape_m": 1, "erp": -1, "credito": 1, "baa_d6": 1, "nfci": 1, "anfci": 1, "sloos": 1, "nfci_credit": 1, "nfci_leverage": 1, "kcfsi": 1,
         "infl": 1, "infl_acc": 1, "real_ff": 1, "curva": -1, "curva_min12": -1, "dgs10": 1, "claims_up": 1, "ccsa_yoy": 1, "sahm": 1, "cfnai": -1,
         "permit_yoy": -1, "indpro_g12": -1, "isratio": 1, "net_liq_13w": -1, "m2_yoy": -1, "margin_yoy": 1, "rel_small": -1, "rel_eqw": -1,
         "rel_cicl": -1, "rel_semi": -1, "rel_trasp": -1, "rel_banche": -1, "rel_rame_oro": -1, "rel_credito": -1, "mom12": -1, "sma10": -1,
         "dd252": -1, "vix": 1, "ciss": 1, "n_segnali": 1}
REC_COLS = ["curva", "curva_min12", "credito", "baa_d6", "claims_up", "sahm", "indpro_g12", "cfnai", "permit_yoy", "delinq_biz", "busloans_g6"]
# recessioni USA (NBER, date ufficiali; si usano se la serie USREC non è ancora scaricata)
NBER = [("1929-08", "1933-03"), ("1937-05", "1938-06"), ("1945-02", "1945-10"), ("1948-11", "1949-10"), ("1953-07", "1954-05"), ("1957-08", "1958-04"),
        ("1960-04", "1961-02"), ("1969-12", "1970-11"), ("1973-11", "1975-03"), ("1980-01", "1980-07"), ("1981-07", "1982-11"),
        ("1990-07", "1991-03"), ("2001-03", "2001-11"), ("2007-12", "2009-06"), ("2020-02", "2020-04")]


def recessione_entro(idx: pd.DatetimeIndex, mesi: int = 12, load=store.load) -> pd.Series:
    """1 se nei `mesi` successivi c'è almeno un mese di recessione USA (USREC se disponibile, altrimenti date NBER)."""
    u = load("usrec").dropna()
    if len(u) > 500:
        rec = (u.resample("ME").max() > 0.5)
    else:
        m = pd.date_range("1925-01-31", pd.Timestamp.now(), freq="ME")
        rec = pd.Series(False, index=m)
        for a, b in NBER:
            rec[(rec.index >= pd.Timestamp(a)) & (rec.index <= pd.Timestamp(b) + pd.offsets.MonthEnd(0))] = True
    out = []
    for t in idx:
        w = rec[(rec.index > t) & (rec.index <= t + pd.DateOffset(months=mesi))]
        out.append(np.nan if len(w) < mesi - 1 else float(w.any()))
    return pd.Series(out, index=idx)


def _platt(p_tr, y_tr):
    from sklearn.linear_model import LogisticRegression
    z = np.log(np.clip(p_tr, 1e-4, 1 - 1e-4) / (1 - np.clip(p_tr, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    m = LogisticRegression(C=10, max_iter=500).fit(z, y_tr)
    if m.coef_[0][0] <= 0:   # una taratura con pendenza negativa invertirebbe l'ordine: in quel caso non si tara
        return lambda p: p
    return lambda p: m.predict_proba(np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1))[:, 1]


def _gbm(Xtr, ytr, Xte, segni):
    from sklearn.ensemble import HistGradientBoostingClassifier
    mk = lambda: HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=150, min_samples_leaf=40, monotonic_cst=list(segni))
    n = len(ytr)
    k = int(n * 0.7)
    cal = None
    if k > 60 and len(set(ytr[k:])) == 2 and len(set(ytr[:k])) == 2:   # taratura di Platt su un pezzo finale dell'addestramento
        m0 = mk().fit(Xtr[:k], ytr[:k])
        cal = _platt(m0.predict_proba(Xtr[k:])[:, 1], ytr[k:])
    p = mk().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    return cal(p) if cal else p


def _knn(Xtr, ytr, Xte, k: int = 25, shrink: float = 5):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    base = ytr.mean()
    out = []
    for b in B:
        d = np.sqrt(((A - b) ** 2).mean(1))
        nb = np.argsort(d)[:k]
        out.append((ytr[nb].sum() + shrink * base) / (len(nb) + shrink))
    return np.array(out)


def _logit_cols(Xtr, ytr, Xte):
    return _fit_predict(Xtr, ytr, Xte, "logit")


def _esegui(fp, X, y, h, anni, holdout, ok=None, oggi: bool = False):
    """Walk-forward normale, oppure (oggi=True) una sola previsione per l'ultima riga addestrata su tutti gli esiti già chiusi."""
    if not oggi:
        return _wf(fp, X, y, h, anni, holdout=holdout, ok=ok)
    ok = pd.Series(True, index=X.index) if ok is None else ok
    if not bool(ok.iloc[-1]):
        return None
    chiusura = X.index + pd.DateOffset(months=h)
    tr = (ok & y.notna() & (chiusura < X.index[-1])).values
    te = np.zeros(len(X), bool)
    te[-1] = True
    if tr.sum() < 120 or y[tr].nunique() < 2:
        return None
    return float(fp(tr, te, X.index[-1])[0])


def modello(nome: str, X: pd.DataFrame, y: pd.Series, h: int, ob: str, anni, cols: list, holdout: bool = False, load=store.load, extra=None,
            oggi: bool = False):
    """Previsioni walk-forward di un modello della sezione 5: (p, c), o None se mancano i dati. Con oggi=True: la probabilità di oggi."""
    sgn = 1 if ob.startswith("calo") else -1
    yv = y.values
    if nome in ("logit", "gbm", "knn"):
        if not cols:
            return None
        D = X[cols].values
        ok = X[cols].notna().all(axis=1)
        if nome == "logit":
            fp = lambda tr, te, s: _logit_cols(D[tr], yv[tr], D[te])
        elif nome == "gbm":
            segni = [int(SEGNI.get(c, 0) * sgn) for c in cols]
            fp = lambda tr, te, s: _gbm(D[tr], yv[tr], D[te], segni)
        else:
            fp = lambda tr, te, s: _knn(D[tr], yv[tr], D[te])
        return _esegui(fp, X, y, h, anni, holdout, ok, oggi)
    if nome == "famiglie":   # una logistica per famiglia, poi combinazione con pesi non negativi
        fams = [c for c in (extra or []) if c]
        if len(fams) < 2:
            return None
        allc = sorted(set(sum(fams, [])))
        ok = X[allc].notna().all(axis=1)

        def fp(tr, te, s):
            from sklearn.linear_model import LogisticRegression
            Ztr, Zte = [], []
            for fc in fams:
                D = X[fc].values
                ptr = _logit_cols(D[tr], yv[tr], D[tr])
                pte = _logit_cols(D[tr], yv[tr], D[te])
                lg = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4)))
                Ztr.append(lg(ptr))
                Zte.append(lg(pte))
            Ztr, Zte = np.array(Ztr).T, np.array(Zte).T
            keep = list(range(Ztr.shape[1]))
            for _i in range(len(keep)):
                m = LogisticRegression(C=1.0, max_iter=500).fit(Ztr[:, keep], yv[tr])
                neg = [keep[j] for j, w in enumerate(m.coef_[0]) if w < 0]
                if not neg:
                    break
                keep = [j for j in keep if j not in neg]
                if not keep:
                    return np.full(te.sum(), yv[tr].mean())
            return m.predict_proba(Zte[:, keep])[:, 1]
        return _esegui(fp, X, y, h, anni, holdout, ok, oggi)
    if nome == "due_stadi":   # 1) probabilità di recessione entro 12 mesi; 2) rischio di calo dato P(recessione), valutazioni e tendenza
        rc = [c for c in (extra or []) if c in X]
        st2 = [c for c in ("cape_m", "erp", "mom12", "sma10", "dd252") if c in cols]
        if len(rc) < 2:
            return None
        rec = recessione_entro(X.index, 12, load).values
        allc = sorted(set(rc + st2))
        ok = X[allc].notna().all(axis=1)
        R, S2 = X[rc].values, X[st2].values if st2 else np.zeros((len(X), 0))
        chius_rec = X.index + pd.DateOffset(months=24)   # le recessioni si annunciano fino a ~12 mesi dopo: purge di 24 mesi

        def fp(tr, te, s):
            trr = tr & (chius_rec < s) & ~np.isnan(rec)
            if trr.sum() < 120 or len(set(rec[trr])) < 2:
                raise ValueError("pochi dati per lo stadio 1")
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            sc = StandardScaler().fit(R[trr])
            m1 = LogisticRegression(C=0.3, max_iter=1000).fit(sc.transform(R[trr]), rec[trr])
            pr = m1.predict_proba(sc.transform(np.nan_to_num(R)))[:, 1]   # le righe con dati mancanti non sono mai usate (maschere tr/te)
            z = np.log(np.clip(pr, 1e-4, 1 - 1e-4) / (1 - np.clip(pr, 1e-4, 1 - 1e-4))).reshape(-1, 1)
            F = np.hstack([z, S2])
            return _logit_cols(F[tr], yv[tr], F[te])
        return _esegui(fp, X, y, h, anni, holdout, ok, oggi)
    if nome == "interazione":   # «caro + deterioramento», regola fissa
        if "cape_m" not in X or X["cape_m"].dropna().empty:
            return None
        q80 = X["cape_m"].expanding(min_periods=120).quantile(0.8)
        det = (X["eps_g12"] < 0) | (X["baa_d6"] > 0.5) | (X["sma10"] < 0)
        sig = ((X["cape_m"] > q80) & det).astype(float).where(q80.notna() & X["cape_m"].notna())
        D = sig.values.reshape(-1, 1)
        return _esegui(lambda tr, te, s: _logit_cols(D[tr], yv[tr], D[te]), X, y, h, anni, holdout, sig.notna(), oggi)
    if nome == "conteggio":
        D = X[["n_segnali"]].values
        return _esegui(lambda tr, te, s: _logit_cols(D[tr], yv[tr], D[te]), X, y, h, anni, holdout, None, oggi)
    raise ValueError(nome)


def riferimenti(X: pd.DataFrame, y: pd.Series, h: int, ob: str, anni, holdout: bool = False) -> dict:
    """Riferimenti: «Solo prezzi» (logistica), Indice Armor (valore grezzo per l'AUC; logistica per il BSS) e A1 (diario storico, solo 3 e 6 mesi)."""
    out = {"Solo prezzi": walk_forward(X, y, h, ["mom12", "sma10", "dd252"], anni=anni, holdout=holdout)}
    if "armor" in X and X["armor"].notna().sum() > 60:
        D = X[["armor"]].values
        pa, ca = _wf(lambda tr, te, s: _logit_cols(D[tr], y.values[tr], D[te]), X, y, h, anni, min_train=48, holdout=holdout, ok=X["armor"].notna())
        out["Indice Armor"] = (pa, ca, X["armor"])
    a1 = X.get(f"a1_{h}")
    if ob == "calo10" and a1 is not None and a1.notna().sum() > 60:
        k = a1.notna() & y.notna()
        fine = pd.Timestamp.now() if holdout else FINE_RICERCA
        k &= (X.index.year >= anni[0]) & (X.index.year <= (anni[1] if holdout else min(anni[1], 2018))) & (X.index + pd.DateOffset(months=h) <= fine)
        c = pd.Series(np.nan, index=X.index)
        for yr in sorted(set(X.index[k].year)):   # frequenza di confronto: solo esiti noti prima dell'anno
            prev = y[(X.index + pd.DateOffset(months=h) < pd.Timestamp(f"{yr}-01-01")) & y.notna()]
            c[k & (X.index.year == yr)] = prev.mean() if len(prev) else np.nan
        out["A1"] = (a1.where(k), c)
    return out


def confronta(p, c, y, rp, sub, ref_raw=None) -> dict:
    """Confronto con un riferimento sugli STESSI mesi, per sottoperiodo."""
    from sklearn.metrics import roc_auc_score
    rr = ref_raw if ref_raw is not None else rp
    k0 = p.notna() & c.notna() & y.notna() & rr.notna()
    det, meglio, peggio = {}, 0, 0
    for lab, a, b in sub:
        k = k0 & (p.index.year >= a) & (p.index.year <= b)
        if k.sum() < 24 or y[k].nunique() < 2:
            det[lab] = None
            continue
        am, ar = float(roc_auc_score(y[k], p[k])), float(roc_auc_score(y[k], rr[k]))
        det[lab] = {"modello": round(am, 3), "riferimento": round(ar, 3)}
        meglio += am - ar >= 0.02
        peggio += am - ar < -0.02
    return {"sotto": det, "meglio": int(meglio), "peggio": int(peggio)}


def dataset_completo(load=store.load, con_oggi: bool = True) -> tuple:
    X = dataset(load=load, con_oggi=con_oggi)
    sp = load("sp500").dropna()
    Y = obiettivi(sp, X.index)
    X["n_segnali"] = conteggio_segnali(X)
    a = load("armor_index").dropna()
    if len(a):
        pos = a.index.searchsorted(X.index, side="right") - 1
        X["armor"] = np.where(pos >= 0, a.values[np.clip(pos, 0, None)], np.nan)
        X.loc[X.index < a.index[0], "armor"] = np.nan
    try:
        rh = pd.read_csv(DATA / "risk_history.csv", parse_dates=["date"]).set_index("date").sort_index()
        for h, col in ((3, "p_3m"), (6, "p_6m")):
            s = rh[col].dropna()
            pos = s.index.searchsorted(X.index, side="right") - 1
            v = np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)
            age = np.where(pos >= 0, (X.index - s.index[np.clip(pos, 0, None)]).days, 9999)
            X[f"a1_{h}"] = np.where(age <= 10, v, np.nan)
    except Exception:  # noqa: BLE001
        pass
    return X, Y, sp


def candidati(X: pd.DataFrame) -> dict:
    """Modelli della sezione 5 per i due periodi, con le colonne disponibili."""
    L = colonne_disponibili(X, LUNGO + ["claims_up"], "1955-12-31")
    T = colonne_disponibili(X, sorted(set(sum(FAMIGLIE.values(), []))), "1992-12-31")
    famL = [colonne_disponibili(X, cols, "1955-12-31") for cols in FAMIGLIE.values()]
    famT = [colonne_disponibili(X, cols, "1992-12-31") for cols in FAMIGLIE.values()]
    recL = colonne_disponibili(X, REC_COLS, "1955-12-31")
    recT = colonne_disponibili(X, REC_COLS, "1992-12-31")
    return {
        "lungo": {"anni": (1960, 2018), "sub": SOTTOPERIODI, "modelli": [
            ("Logistica (storia lunga)", "logit", L, None), ("Alberi monotoni (storia lunga)", "gbm", L, None),
            ("Mesi simili (storia lunga)", "knn", L, None), ("Famiglie combinate (storia lunga)", "famiglie", L, [f for f in famL if f]),
            ("Due stadi: recessione poi calo (storia lunga)", "due_stadi", L, recL), ("Caro + deterioramento", "interazione", L, None),
            ("Conteggio dei segnali", "conteggio", L, None)]},
        "recente": {"anni": (2000, 2018), "sub": SOTTO_2000, "modelli": [
            ("Logistica (tutti i dati dal 1992)", "logit", T, None), ("Alberi monotoni (tutti i dati)", "gbm", T, None),
            ("Mesi simili (tutti i dati)", "knn", T, None), ("Famiglie combinate (tutti i dati)", "famiglie", T, [f for f in famT if f]),
            ("Due stadi: recessione poi calo (tutti i dati)", "due_stadi", T, recT), ("Caro + deterioramento", "interazione", T, None),
            ("Conteggio dei segnali", "conteggio", T, None)]},
    }


def fase_b(load=store.load, save: bool = True) -> dict:
    import time as _t
    t0 = _t.time()
    X, Y, sp = dataset_completo(load)
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    C = candidati(X)
    righe, risultati, promossi, direzione = [], [], [], []
    for per, spec in C.items():
        for ob, h in OBIETTIVI:
            y = Y[f"{ob}_{h}"]
            refs = riferimenti(X, y, h, ob, spec["anni"])
            ref_met = {}
            for rn, rv in refs.items():
                pr, cr = rv[0], rv[1]
                raw = rv[2] if len(rv) > 2 else None
                m = metriche(pr, cr, y)
                if raw is not None:   # AUC dell'indice grezzo (più fedele dell'adattamento logistico)
                    k = raw.notna() & pr.notna() & y.notna()
                    if k.sum() > 24 and y[k].nunique() == 2:
                        from sklearn.metrics import roc_auc_score
                        m["auc"] = round(float(roc_auc_score(y[k], raw[k])), 3)
                ref_met[rn] = m
                righe.append({"data": oggi, "modello": f"[rif] {rn}", "tipo": "riferimento", "obiettivo": f"{ob}_{h}", "periodo": f"{spec['anni'][0]}-{spec['anni'][1]}",
                              "variabili": rn, "n": m["n"], "eventi": m["eventi"], "auc": m["auc"], "bss": m["bss"]})
            cand_ref = [(m["auc"], rn) for rn, m in ref_met.items() if m.get("auc") is not None and (per == "recente" or rn == "Solo prezzi")]
            best_ref = max(cand_ref)[1] if cand_ref else None
            for nome, tipo, cols, extra in spec["modelli"]:
                try:
                    res = modello(tipo, X, y, h, ob, spec["anni"], cols, load=load, extra=extra)
                except Exception as e:  # noqa: BLE001
                    print(f"[ricerca] {nome} {ob}_{h}: errore {str(e)[:80]}", flush=True)
                    res = None
                if res is None:
                    continue
                p, c = res
                m = metriche(p, c, y)
                cf = None
                if best_ref:
                    rv = refs[best_ref]
                    cf = confronta(p, c, y, rv[0], spec["sub"], rv[2] if len(rv) > 2 else None)
                passa = bool(m["bss"] is not None and m["bss"] > 0 and cf and cf["meglio"] >= 2 and cf["peggio"] == 0)
                r = {"periodo_tipo": per, "periodo": f"{spec['anni'][0]}-{spec['anni'][1]}", "modello": nome, "tipo": tipo, "variabili": cols,
                     "ob": ob, "h": h, **m, "riferimento": best_ref, "rif_auc": ref_met.get(best_ref, {}).get("auc") if best_ref else None,
                     "confronto": cf, "promosso": passa and (ob, h) in PRIMARI}
                risultati.append(r)
                if r["promosso"]:
                    promossi.append({k: r[k] for k in ("periodo_tipo", "periodo", "modello", "tipo", "variabili", "ob", "h", "auc", "bss", "riferimento", "rif_auc")})
                if ob == "rialzo" and m["bss"] is not None and m["bss"] > 0.01 and cf and cf["peggio"] == 0:
                    direzione.append({"modello": nome, "h": h, "bss": m["bss"], "auc": m["auc"]})
                righe.append({"data": oggi, "modello": nome, "tipo": tipo, "obiettivo": f"{ob}_{h}", "periodo": r["periodo"], "variabili": "+".join(cols),
                              "n": m["n"], "eventi": m["eventi"], "auc": m["auc"], "bss": m["bss"], "riferimento": best_ref,
                              "meglio_sotto": cf["meglio"] if cf else None, "peggio_sotto": cf["peggio"] if cf else None, "promosso": r["promosso"]})
            risultati.append({"periodo_tipo": per, "periodo": f"{spec['anni'][0]}-{spec['anni'][1]}", "modello": "_riferimenti", "ob": ob, "h": h, "rif": ref_met})
    # mesi simili: validi solo se il modello «Mesi simili» supera le regole su almeno un obiettivo primario
    knn_ok = any(p["tipo"] == "knn" for p in promossi)
    res = {"data": oggi, "versione": "Fase B", "fine_ricerca": FINE_RICERCA.strftime("%Y-%m-%d"), "regole": "PIANO_MODELLO §6 (pre-registrate in ricerca.py)",
           "risultati": risultati, "promossi": promossi, "direzione_prevedibile": direzione, "analoghi_validati": knn_ok,
           "segnali_dal_1960": segnali_singoli(X, Y, 1960), "segnali_dal_1990": segnali_singoli(X, Y, 1990),
           "mancanti": [c for c in _base_ids() if X[c].dropna().empty], "secondi": None}
    an_cols = colonne_disponibili(X, LUNGO, "1955-12-31")
    res["analoghi_oggi"] = analoghi(X, Y, an_cols)
    best_long = next((p for p in promossi if p["periodo_tipo"] == "lungo"), None)
    try:
        nm, tp = ("Logistica (storia lunga)", "logit") if not best_long else (best_long["modello"], best_long["tipo"])
        spec = next(m for m in C["lungo"]["modelli"] if m[0] == nm)
        pr, cr = modello(spec[1], X, Y["calo10_12"], 12, "calo10", (1960, 2018), spec[2], load=load, extra=spec[3])
        res["episodi"] = {"modello": nm, **episodi(sp, pr, cr, Y["calo10_12"])[0]}
    except Exception as e:  # noqa: BLE001
        res["episodi"] = {"errore": str(e)[:100]}
    res["secondi"] = round(_t.time() - t0, 1)
    if save:
        _registra(righe)
        res["prove_totali_registro"] = prove_totali()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "fase_b.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "promossi.json").write_text(json.dumps({"data": oggi, "promossi": promossi}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"[ricerca] Fase B: {len(righe)} prove in {res['secondi']}s; promossi in ombra: {len(promossi)}; direzione prevedibile: {len(direzione)}", flush=True)
    return res


def prova_finale(load=store.load, save: bool = True, force: bool = False) -> dict:
    """Prova UNICA sugli anni 2019-oggi per i modelli promossi (PIANO_MODELLO §6). Si esegue una sola volta: se esiste già, restituisce il risultato salvato."""
    f = OUT / "prova_finale.json"
    if f.exists() and not force:
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        prom = json.loads((OUT / "promossi.json").read_text(encoding="utf-8")).get("promossi", [])
    except Exception:  # noqa: BLE001
        prom = []
    X, Y, sp = dataset_completo(load)
    C = candidati(X)
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    anni = (2019, pd.Timestamp.now().year)
    out, righe, adottati = [], [], []
    for ob, h in PRIMARI:
        y = Y[f"{ob}_{h}"]
        refs = riferimenti(X, y, h, ob, anni, holdout=True)
        mods = [p for p in prom if p["ob"] == ob and p["h"] == h]
        entry = {"ob": ob, "h": h, "riferimenti": {}, "modelli": []}
        from sklearn.metrics import roc_auc_score
        for rn, rv in refs.items():
            m = metriche(rv[0], rv[1], y)
            if len(rv) > 2:
                k = rv[2].notna() & rv[0].notna() & y.notna()
                if k.sum() > 12 and y[k].nunique() == 2:
                    m["auc"] = round(float(roc_auc_score(y[k], rv[2][k])), 3)
            entry["riferimenti"][rn] = m
        for pm in mods:
            spec = next((m for m in C[pm["periodo_tipo"]]["modelli"] if m[0] == pm["modello"]), None)
            if not spec:
                continue
            p, c = modello(spec[1], X, y, h, ob, anni, spec[2], holdout=True, load=load, extra=spec[3])
            m = metriche(p, c, y)
            ra = None
            if "Indice Armor" in refs:   # AUC dell'Indice sugli stessi mesi
                raw = refs["Indice Armor"][2]
                k = p.notna() & raw.notna() & y.notna()
                if k.sum() > 12 and y[k].nunique() == 2:
                    ra = round(float(roc_auc_score(y[k], raw[k])), 3)
            ok = bool(m["bss"] is not None and m["bss"] > 0 and m["auc"] is not None and ra is not None and m["auc"] >= ra)
            e = {"modello": pm["modello"], "periodo_tipo": pm["periodo_tipo"], **m, "auc_indice_stessi_mesi": ra, "adottato": ok}
            entry["modelli"].append(e)
            righe.append({"data": oggi, "modello": pm["modello"], "tipo": "prova_finale", "obiettivo": f"{ob}_{h}", "periodo": f"{anni[0]}-{anni[1]}",
                          "variabili": "+".join(spec[2]), "n": m["n"], "eventi": m["eventi"], "auc": m["auc"], "bss": m["bss"], "promosso": ok})
            if ok:
                adottati.append({"modello": pm["modello"], "periodo_tipo": pm["periodo_tipo"], "tipo": spec[1], "variabili": spec[2], "ob": ob, "h": h,
                                 "auc": m["auc"], "bss": m["bss"], "auc_indice": ra})
        out.append(entry)
    res = {"data": oggi, "anni": f"{anni[0]}-{anni[1]}", "nota": "Prova unica: gli anni 2019-oggi non erano mai stati usati nella ricerca.",
           "promossi_provati": len(prom), "esiti": out, "adottati": adottati}
    if save:
        _registra(righe)
        OUT.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "adottati.json").write_text(json.dumps({"data": oggi, "adottati": adottati}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"[ricerca] prova finale 2019-oggi: {len(prom)} modelli provati, {len(adottati)} adottati", flush=True)
    return res


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
        res["prove_totali_registro"] = prove_totali()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "risultati.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "analoghi_oggi.json").write_text(json.dumps(an, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (OUT / "episodi.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"[ricerca] {len(risultati)} prove in {res['secondi']}s; serie mancanti: {', '.join(mancanti) or 'nessuna'}", flush=True)
    try:   # Fase B: tutti i modelli della sezione 5 con le regole della sezione 6
        res["fase_b"] = {k: v for k, v in fase_b(load=load, save=save).items() if k in ("promossi", "direzione_prevedibile", "analoghi_validati", "secondi")}
    except Exception as e:  # noqa: BLE001
        print("[ricerca] Fase B non riuscita:", str(e)[:150], flush=True)
    for r in risultati:
        if r["auc"] is not None:
            print(f"[ricerca] {r['modello'][:38]:38s} {r['obiettivo']:24s} {r['periodo']} AUC {r['auc']:.3f} BSS {r['bss']:+.3f} n {r['n']} eventi {r['eventi']}", flush=True)
    return res


def load_results() -> dict:
    try:
        return json.loads((OUT / "risultati.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
