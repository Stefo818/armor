"""«Regime di tensione»: l'Indice Armor resta a lungo alto → cali graduali e nuovi minimi? (PIANO_ESPANSIONE Patch 43).
Regole, varianti ed esiti sono fissati in PROTOCOLLO_REGIME.md PRIMA di guardare i risultati 2013-oggi. Tutto in questo file è walk-forward:
a ogni data si usano solo dati noti. Non è consulenza finanziaria: sono frequenze storiche, con pochi episodi indipendenti."""
import hashlib
import html as _h
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import store
from .config import DATA, ROOT
from .features import closed_sp500, fwd_maxdd, fwd_ret

H = 126
LAM = 0.97
SOGLIA = 40.0
T_ATT = 45.0
PN_ATT = 0.80
STEP = 5
SEME = 20261109
VARIANTI = ("V1", "V2", "V3", "V4")
ESITI = {"a": "Nuovo minimo a 6 mesi", "b": "Calo di almeno 10% entro 6 mesi", "c": "Chiusura negativa a 6 mesi", "d": "Calo graduale (−5% o più, volatilità sotto la mediana)"}
FILE = DATA / "regime_esperimento.json"
OMBRA = DATA / "regime_ombra.csv"
A1_CACHE = DATA / "regime_a1.csv"
LOG = DATA / "protocollo_regime_log.csv"


# ---------------------------------------------------------------- protocollo
def protocollo_hash() -> str:
    f = ROOT / "PROTOCOLLO_REGIME.md"
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:24] if f.exists() else ""


def registra_protocollo() -> str:
    h = protocollo_hash()
    if not h:
        return ""
    righe = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else ["data_utc,impronta"]
    if not any(r.endswith("," + h) for r in righe[1:]):
        righe.append(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},{h}")
        LOG.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return h


# ---------------------------------------------------------------- variabili
def pressione(a: pd.Series, lam: float = LAM, soglia: float = SOGLIA) -> pd.Series:
    """P_t = Σ λ^k · max(0, A_{t−k} − soglia): ricorsione P_t = λ P_{t−1} + max(0, A_t − soglia)."""
    x = np.maximum(a.values.astype(float) - soglia, 0.0)
    out = np.empty(len(x))
    acc = 0.0
    for i, v in enumerate(x):
        acc = lam * acc + (0.0 if np.isnan(v) else v)
        out[i] = acc
    return pd.Series(out, index=a.index)


def pct_espanso(s: pd.Series, minimo: int = 250) -> pd.Series:
    """Percentile di s_t nella storia fino a t compreso."""
    v = s.values
    out = np.full(len(v), np.nan)
    srt: list[float] = []
    import bisect
    for i, x in enumerate(v):
        bisect.insort(srt, x)
        if i + 1 >= minimo:
            out[i] = bisect.bisect_right(srt, x) / len(srt)
    return pd.Series(out, index=s.index)


def variabili(a: pd.Series, p: pd.Series) -> pd.DataFrame:
    """Variabili e condizioni delle 4 varianti, allineate alle date dell'indice Armor."""
    a = a.dropna()
    a = a[~a.index.duplicated(keep="last")].sort_index()
    pp = p.reindex(a.index).ffill()
    f = pd.DataFrame(index=a.index)
    f["A"] = a
    f["min20"] = a.rolling(20).min()
    f["ma60"] = a.rolling(60).mean()
    f["P"] = pressione(a)
    f["Pn"] = pct_espanso(f["P"])
    dd = pp / pp.rolling(252, min_periods=120).max() - 1
    f["dd"] = dd
    f["d"] = (-dd).clip(0, 0.30) / 0.30
    f["Pnd"] = f["Pn"] * f["d"]
    f["V1"] = (f["min20"] >= T_ATT)
    f["V2"] = (f["ma60"] >= T_ATT)
    f["V3"] = (f["Pn"] >= PN_ATT)
    f["V4"] = f["V3"] & (dd <= -0.05)
    for k in VARIANTI:
        f[k] = f[k].where(f["min20"].notna() & f["ma60"].notna() & (f["Pn"].notna() if k in ("V3", "V4") else True), False).astype(bool)
    return f


FEAT = {"V1": ["m20"], "V2": ["m60"], "V3": ["Pn"], "V4": ["Pn", "d", "Pnd"]}


def matrice(f: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=f.index)
    X["m20"] = f["min20"] / 100
    X["m60"] = f["ma60"] / 100
    for c in ("Pn", "d", "Pnd"):
        X[c] = f[c]
    return X


# ---------------------------------------------------------------- esiti
def esiti(p: pd.Series, h: int = H) -> pd.DataFrame:
    p = p.dropna()
    lr = np.log(p).diff()
    prev_min = p.rolling(h, min_periods=h).min()
    fut_min = p[::-1].rolling(h, min_periods=h).min()[::-1].shift(-1)
    ret = fwd_ret(p, h)
    dd = fwd_maxdd(p, h)
    rvf = (lr[::-1].rolling(h, min_periods=h).std()[::-1].shift(-1)) * np.sqrt(252)
    med = rvf.shift(h).expanding(min_periods=250).median()
    ok = ret.notna()
    o = pd.DataFrame(index=p.index)
    o["a"] = (fut_min < prev_min).astype(float).where(ok & prev_min.notna())
    o["b"] = (dd <= -0.10).astype(float).where(ok)
    o["c"] = (ret < 0).astype(float).where(ok)
    o["d"] = ((ret <= -0.05) & (rvf < med)).astype(float).where(ok & med.notna())
    o["ret"] = ret
    o["dd"] = dd
    return o


def freq_nota(y: pd.Series, h: int = H) -> pd.Series:
    """Frequenza storica dell'esito nota alla data t: media degli esiti con data ≤ t − h."""
    cs = y.fillna(0).cumsum()
    cn = y.notna().astype(int).cumsum()
    j = np.maximum(np.arange(len(y)) - h, 0)
    return pd.Series(cs.values[j] / np.maximum(cn.values[j], 1), index=y.index)


# ---------------------------------------------------------------- metriche
def _brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def _auc(s, y) -> float:
    from .armor_index import _auc_np
    return float(_auc_np(np.asarray(s, float), np.asarray(y, float)))


def _boot_idx(n: int, blocco: float, reps: int, seed: int):
    from .verifica import indici_stazionari
    return indici_stazionari(n, blocco, reps, np.random.default_rng(seed))


def _ic(v: np.ndarray, level: float = 0.90) -> tuple[float, float]:
    return float(np.quantile(v, (1 - level) / 2)), float(np.quantile(v, 1 - (1 - level) / 2))


def walk_forward(X: pd.DataFrame, y: pd.Series, dates, y_known_lag: int = H, primo: int = 2006) -> pd.Series:
    """Logistica riaddestrata ogni 1° gennaio con soli esiti noti (data ≤ ultimo giorno disponibile all'addestramento − h)."""
    from sklearn.linear_model import LogisticRegression
    idx = X.index
    out = pd.Series(np.nan, index=pd.DatetimeIndex(dates))
    for anno in sorted({d.year for d in out.index}):
        if anno < primo:
            continue
        inizio = idx.searchsorted(pd.Timestamp(f"{anno}-01-01"))
        fine_tr = inizio - y_known_lag
        if fine_tr < 200:
            continue
        tr = X.iloc[:fine_tr]
        yt = y.reindex(tr.index)
        ok = tr.notna().all(axis=1) & yt.notna()
        if ok.sum() < 150 or yt[ok].nunique() < 2 or yt[ok].sum() < 10:
            continue
        m = LogisticRegression(C=1000.0, max_iter=500).fit(tr[ok].values, yt[ok].values.astype(int))
        sel = [d for d in out.index if d.year == anno]
        Xs = X.reindex(sel)
        good = Xs.notna().all(axis=1)
        if good.any():
            out.loc[Xs.index[good]] = m.predict_proba(Xs[good].values)[:, 1]
    return out


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def punteggio(pr: pd.Series, y: pd.Series, base: pd.Series, blocco: float, reps: int = 2000) -> dict:
    d = pd.concat([pr, y, base], axis=1, keys=["p", "y", "b"]).dropna()
    if len(d) < 40 or d.y.nunique() < 2:
        return {"n": int(len(d)), "bss": None}
    em, eb = (d.p - d.y).values ** 2, (d.b - d.y).values ** 2
    idx = _boot_idx(len(d), blocco, reps, SEME)
    v = 1 - em[idx].sum(axis=1) / np.maximum(eb[idx].sum(axis=1), 1e-12)
    lo, hi = _ic(v)
    return {"n": int(len(d)), "bss": float(1 - em.sum() / eb.sum()), "lo": lo, "hi": hi, "auc": _auc(d.p, d.y), "freq": float(d.y.mean())}


# ---------------------------------------------------------------- A1
def a1_p(p: pd.Series, dates, log=print) -> pd.Series:
    """p di A1 (6 mesi, −10%) walk-forward sulle date richieste, con cache incrementale."""
    c = pd.read_csv(A1_CACHE, parse_dates=["date"]).set_index("date")["p"] if A1_CACHE.exists() else pd.Series(dtype=float)
    mancano = [d for d in dates if d not in c.index]
    if mancano:
        from .modeleval import a1_preds
        log(f"[regime] A1 su {len(mancano)} date nuove")
        r = pd.DataFrame(a1_preds(p, mancano))
        r = r[(r.hz == "6m") & (r.kind == "down") & (r.thr == 10)].set_index("date")["p"]
        c = pd.concat([c, r]).sort_index()
        c = c[~c.index.duplicated(keep="last")]
        c.rename("p").to_frame().to_csv(A1_CACHE, index_label="date")
    return c.reindex(pd.DatetimeIndex(dates))


# ---------------------------------------------------------------- episodi
def episodi_di(cond: pd.Series, p: pd.Series, pausa: int = 60) -> list[dict]:
    c = cond.reindex(p.index).fillna(False).values
    pv = p.values
    idx = p.index
    res, i, n = [], 0, len(c)
    last_on = -10 ** 9
    while i < n:
        if c[i]:
            if i - last_on > pausa:
                j = i
                while j + 1 < n and c[j + 1]:
                    j += 1
                fut = pv[i + 1:i + H + 1]
                prev_min = pv[max(0, i - H + 1):i + 1].min()
                r126 = pv[i + H] / pv[i] - 1 if i + H < n else None
                r252 = pv[i + 252] / pv[i] - 1 if i + 252 < n else None
                nuovo = None
                tmin = None
                if len(fut):
                    sotto = np.where(pv[i + 1:] < prev_min)[0]
                    tmin = int(sotto[0]) + 1 if len(sotto) else None
                    if i + H < n:
                        nuovo = bool(fut.min() < prev_min)
                res.append({"inizio": str(idx[i].date()), "fine": str(idx[j].date()), "durata": int(j - i + 1),
                            "calo_max": float(fut.min() / pv[i] - 1) if len(fut) >= H else (float(fut.min() / pv[i] - 1) if len(fut) else None),
                            "completo": bool(i + H < n), "nuovo_minimo": nuovo, "t_minimo": tmin, "r126": r126, "r252": r252})
                last_on = j
                i = j + 1
                continue
            last_on = i
        i += 1
    return res


def kaplan_meier(ep: list[dict], p: pd.Series, orizzonte: int = 252) -> list[float]:
    """Probabilità di aver toccato un nuovo minimo entro t sedute (t = 21, 42, …), con censura a fine dati."""
    n = len(p)
    righe = []
    for e in ep:
        i = p.index.get_loc(pd.Timestamp(e["inizio"]))
        disp = n - 1 - i
        if e["t_minimo"] is not None and e["t_minimo"] <= orizzonte:
            righe.append((e["t_minimo"], 1))
        else:
            righe.append((min(orizzonte, disp), 0))
    return _km(righe, orizzonte)


def _km(righe: list[tuple[int, int]], orizzonte: int) -> list[float]:
    if not righe:
        return []
    righe = sorted(righe)
    s, out, k = 1.0, [], 0
    tempi = sorted({t for t, e in righe if e == 1})
    surv = {}
    for t in tempi:
        rischio = sum(1 for tt, _ in righe if tt >= t)
        ev = sum(1 for tt, e in righe if tt == t and e == 1)
        s *= 1 - ev / rischio
        surv[t] = s
    for t in range(21, orizzonte + 1, 21):
        vals = [v for tt, v in surv.items() if tt <= t]
        out.append(round(1 - (vals[-1] if vals else 1.0), 4))
        k += 1
    return out


def km_base(p: pd.Series, orizzonte: int = 252, passo: int = 21) -> list[float]:
    righe = []
    pv = p.values
    n = len(pv)
    for i in range(H, n - 1, passo):
        pm = pv[i - H + 1:i + 1].min()
        sotto = np.where(pv[i + 1:i + orizzonte + 1] < pm)[0]
        if len(sotto):
            righe.append((int(sotto[0]) + 1, 1))
        else:
            righe.append((min(orizzonte, n - 1 - i), 0))
    return _km(righe, orizzonte)


# ---------------------------------------------------------------- stato
def stato_di(f: pd.DataFrame) -> pd.Series:
    """calma / normale / formazione / persistente / persistente_calo."""
    a = f["A"]
    s = pd.Series("normale", index=f.index, dtype=object)
    s[a < 35] = "calma"
    s[(a >= T_ATT) & ~f["V1"]] = "formazione"
    s[f["V1"]] = "persistente"
    s[f["V1"] & (f["dd"] <= -0.05)] = "persistente_calo"
    return s


def sedute_sopra(a: pd.Series, soglia: float = T_ATT) -> int:
    v = a.dropna().values
    n = 0
    for x in v[::-1]:
        if x >= soglia:
            n += 1
        else:
            break
    return n


def tabella_stati(f: pd.DataFrame, o: pd.DataFrame, dal: str = "2000-01-01", al: str = "2100-01-01") -> dict:
    st = stato_di(f)
    d = pd.concat([st.rename("st"), o[["a", "b", "c", "d"]]], axis=1).dropna(subset=["a"])
    d = d[(d.index >= dal) & (d.index < al)]
    out = {}
    for nome, g in list(d.groupby("st")) + [("tutti", d)]:
        inizi = (st == nome) & (st.shift(1) != nome)
        runs = int(inizi[(inizi.index >= dal) & (inizi.index < al)].sum()) if nome != "tutti" else None
        out[nome] = {"n": int(len(g)), "episodi": runs, **{k: (float(g[k].mean()) if g[k].notna().sum() else None) for k in "abcd"}}
    return out


# ---------------------------------------------------------------- esperimento completo
def run(log=print, reps: int = 2000) -> dict:
    registra_protocollo()
    p = closed_sp500()
    a = store.load("armor_index")
    f = variabili(a, p)
    pp = p.reindex(f.index).ffill()
    o = esiti(pp)
    X = matrice(f)
    ev = f.index[::STEP]
    ev = ev[ev >= "2006-01-01"]
    blocco = max(H / STEP, 1)
    base = {k: freq_nota(o[k]).reindex(ev) for k in "abcd"}
    res = {"asof": str(f.index[-1].date()), "protocollo": protocollo_hash(), "varianti": {}, "periodi": {"scelta": "2006-2012", "verifica": "2013-oggi"}}
    prev = {}
    for v in VARIANTI:
        prev[v] = {k: walk_forward(X[FEAT[v]], o[k], ev) for k in "abcd"}
    for v in VARIANTI:
        r = {}
        for per, (da, al) in {"scelta": ("2006-01-01", "2013-01-01"), "verifica": ("2013-01-01", "2100-01-01")}.items():
            m = (ev >= da) & (ev < al)
            r[per] = {k: punteggio(prev[v][k][m], o[k].reindex(ev)[m], base[k][m], blocco, reps) for k in "abcd"}
        res["varianti"][v] = r
    # scelta pre-registrata
    medie = {}
    for v in VARIANTI:
        b = [res["varianti"][v]["scelta"][k].get("bss") for k in "abcd"]
        medie[v] = float(np.nanmean([x for x in b if x is not None])) if any(x is not None for x in b) else float("-inf")
    best = VARIANTI[0]
    for v in VARIANTI[1:]:
        if medie[v] > medie[best] + 0.005:
            best = v
    res["scelta_bss_medio"] = medie
    res["scelta"] = best
    # aggiunge informazione rispetto ad A1? (esito b)
    try:
        a1 = a1_p(p, list(ev), log)
        la1 = pd.Series(_logit(a1.values), index=ev)
        Xa = pd.DataFrame({"a1": la1})
        Xc = pd.concat([Xa, X[FEAT[best]].reindex(ev)], axis=1)
        yb = o["b"].reindex(ev)
        p_solo = walk_forward(Xa, yb, ev, y_known_lag=max(H // STEP, 1), primo=2006)
        p_comb = walk_forward(Xc, yb, ev, y_known_lag=max(H // STEP, 1), primo=2006)
        d = pd.concat([p_solo, p_comb, yb], axis=1, keys=["s", "c", "y"]).dropna()
        d = d[d.index >= "2013-01-01"]
        if len(d) > 40:
            diff = (d.c - d.y) ** 2 - (d.s - d.y) ** 2
            idx = _boot_idx(len(d), blocco, reps, SEME + 1)
            lo, hi = _ic(diff.values[idx].mean(axis=1))
            res["vs_a1"] = {"n": int(len(d)), "diff_brier": float(diff.mean()), "lo": lo, "hi": hi, "aggiunge": bool(hi < 0)}
        else:
            res["vs_a1"] = None
    except Exception as e:  # noqa: BLE001
        log("[regime] confronto con A1 non riuscito: " + str(e)[:120])
        res["vs_a1"] = None
    # episodi e sopravvivenza
    ep = {v: episodi_di(f[v], pp) for v in VARIANTI}
    res["episodi"] = ep
    res["episodi_2013"] = {v: sum(1 for e in ep[v] if e["inizio"] >= "2013-01-01") for v in VARIANTI}
    res["km"] = {"v1": kaplan_meier(ep["V1"], pp), "base": km_base(pp), "n": len(ep["V1"])}
    res["stati"] = {"2000_2012": tabella_stati(f, o, "2000-01-01", "2013-01-01"), "2013_oggi": tabella_stati(f, o, "2013-01-01"), "tutto": tabella_stati(f, o)}
    # regola di adozione
    vb = res["varianti"][best]["verifica"]["b"]
    cond = {"bss_sopra_zero": bool(vb.get("lo") is not None and vb["lo"] > 0),
            "aggiunge_a1": bool(res.get("vs_a1") and res["vs_a1"].get("aggiunge")),
            "episodi_4": res["episodi_2013"][best] >= 4}
    res["adozione"] = {"condizioni": cond, "adottata": all(cond.values())}
    # robustezza su altri mercati (V1)
    rob = {}
    for nome, getter in (("STOXX 50", lambda: store.load("stoxx50")), ("Nikkei 225", lambda: store.load("nikkei")), ("VWCE", _vwce)):
        try:
            s = getter().dropna()
            s = s[s > 0]
            oo = esiti(s)
            c = f["V1"].reindex(s.index, method="ffill").fillna(False)
            dd = pd.concat([c.rename("c"), oo[["a", "b", "c"]].rename(columns={"c": "cn"})], axis=1).dropna(subset=["a"])
            dd = dd[dd.index >= "2000-01-01"]
            on, off = dd[dd.c.astype(bool)], dd[~dd.c.astype(bool)]
            rob[nome] = {"giorni_on": int(len(on)), "da": str(dd.index[0].date()),
                         **{k: [float(on[k].mean()) if len(on) else None, float(off[k].mean()) if len(off) else None] for k in ("a", "b", "cn")}}
        except Exception as e:  # noqa: BLE001
            log(f"[regime] robustezza {nome}: {str(e)[:80]}")
    res["robustezza"] = rob
    FILE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def _vwce() -> pd.Series:
    from .features import vwce_series
    return vwce_series()


# ---------------------------------------------------------------- oggi, registro in ombra
def oggi(a: pd.Series | None = None, p: pd.Series | None = None) -> dict | None:
    try:
        a = store.load("armor_index") if a is None else a
        p = closed_sp500() if p is None else p
        f = variabili(a, p)
        if f.empty:
            return None
        st = stato_di(f)
        r = f.iloc[-1]
        return {"data": str(f.index[-1].date()), "A": float(r["A"]), "min20": float(r["min20"]), "ma60": float(r["ma60"]), "Pn": None if pd.isna(r["Pn"]) else float(r["Pn"]),
                "dd": None if pd.isna(r["dd"]) else float(r["dd"]), "stato": str(st.iloc[-1]), "sopra45": sedute_sopra(f["A"]),
                "sopra40": sedute_sopra(f["A"], 40.0), "v": {k: bool(r[k]) for k in VARIANTI}}
    except Exception as e:  # noqa: BLE001
        print("Regime di tensione non calcolato:", str(e)[:100], flush=True)
        return None


def registra_ombra(o: dict | None) -> None:
    if not o:
        return
    righe = OMBRA.read_text(encoding="utf-8").splitlines() if OMBRA.exists() else ["data,indice,min20,pn,stato,v1,v2,v3,v4"]
    if any(r.startswith(o["data"] + ",") for r in righe[1:]):
        return
    righe.append(",".join([o["data"], f"{o['A']:.2f}", f"{o['min20']:.2f}", "" if o["Pn"] is None else f"{o['Pn']:.3f}", o["stato"]] + [str(int(o["v"][k])) for k in VARIANTI]))
    OMBRA.write_text("\n".join(righe) + "\n", encoding="utf-8")


def ombra_verifica(p: pd.Series | None = None) -> dict:
    """Confronta le righe del registro ombra maturate (≥126 sedute) con gli esiti reali."""
    if not OMBRA.exists():
        return {"righe": 0, "mature": 0}
    p = closed_sp500() if p is None else p
    d = pd.read_csv(OMBRA, parse_dates=["data"]).set_index("data")
    o = esiti(p)
    j = d.join(o[["a", "b", "c"]], how="left").dropna(subset=["a"])
    out = {"righe": int(len(d)), "mature": int(len(j)), "da": str(d.index[0].date())}
    if len(j):
        on = j[j.v1 == 1]
        out["v1_on"] = int(len(on))
        out["b_on"] = float(on.b.mean()) if len(on) else None
        out["b_tutti"] = float(j.b.mean())
    return out


# ---------------------------------------------------------------- testo e pagina
NOMI_STATO = {"calma": "Calma", "normale": "Normale", "formazione": "Tensione in formazione", "persistente": "Tensione persistente", "persistente_calo": "Tensione persistente con mercato già in calo"}
COL_STATO = {"calma": "#16a34a", "normale": "#64748b", "formazione": "#d97706", "persistente": "#dc2626", "persistente_calo": "#991b1b"}
STATO_DESC = {
    "calma": "L'indice è sotto 35: storicamente il rischio di cali ampi è stato più basso del normale.",
    "normale": "L'indice è in una zona intermedia: nessun segnale particolare di tensione prolungata.",
    "formazione": "L'indice è sopra 45 ma da poche sedute: la tensione potrebbe formarsi oppure rientrare. La condizione «stabile» non è ancora scattata.",
    "persistente": "L'indice è sopra 45 da almeno 20 sedute senza scendere: è lo «stabilmente alto» che hai osservato.",
    "persistente_calo": "Come sopra, ma l'S&P 500 è già almeno 5% sotto il massimo: nei dati storici questa è la combinazione con più nuovi minimi.",
}


def _pc(x, d=0) -> str:
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%".replace(".", ",")


def frase(stato: str, r: dict | None) -> str:
    """Frase prudente con le frequenze storiche dello stato attuale."""
    if not r:
        return "Frequenze storiche non ancora calcolate (esperimento da eseguire)."
    t, t13 = r["stati"]["tutto"], r["stati"]["2013_oggi"]
    g, g13, base = t.get(stato), t13.get(stato), t["tutti"]
    if not g or not g["n"]:
        return "Troppi pochi casi storici in questo stato per dare una frequenza."
    s = (f"Storicamente, in questo stato, nuovo minimo nei 6 mesi successivi nel {_pc(g['a'])} dei casi contro il {_pc(base['a'])} normale; "
         f"calo di almeno 10% nel {_pc(g['b'])} contro {_pc(base['b'])}.")
    if g13 and g13["n"] >= 40:
        s += f" Dal 2013: nuovo minimo nel {_pc(g13['a'])} ({g13['n']} giorni)."
    ad = r.get("adozione", {})
    s += " Verificato fuori campione." if ad.get("adottata") else " Non verificato fuori campione."
    return s


def _barre_storiche(stato: str, r: dict | None) -> str:
    """Due confronti a barre: nei 6 mesi dopo giorni di questo stato vs dopo un giorno qualsiasi."""
    if not r:
        return "<p class='rg-t'>Frequenze storiche non ancora calcolate (esperimento da eseguire).</p>"
    t, t13 = r["stati"]["tutto"], r["stati"]["2013_oggi"]
    g, g13, base = t.get(stato), t13.get(stato), t["tutti"]
    if not g or not g["n"]:
        return "<p class='rg-t'>Troppi pochi casi storici in questo stato per dare una frequenza.</p>"
    mx = max(g["a"] or 0, base["a"] or 0, g["b"] or 0, base["b"] or 0, 0.01)

    def coppia(titolo, k):
        a, b = g[k], base[k]
        return (f"<div class='rg-c'><div class='rg-ct'>{titolo}</div>"
                f"<div class='rg-bl'><span>Dopo giorni come oggi</span><b>{_pc(a)}</b></div><div class='rg-bar'><i style='width:{a / mx * 100:.0f}%;background:var(--rgc)'></i></div>"
                f"<div class='rg-bl'><span>Dopo un giorno qualsiasi</span><b>{_pc(b)}</b></div><div class='rg-bar'><i style='width:{b / mx * 100:.0f}%;background:var(--mu)'></i></div></div>")
    out = (coppia("Su 100 volte, in quante l'S&amp;P 500 ha toccato un <b>nuovo minimo</b> entro 6 mesi?", "a")
           + coppia("Su 100 volte, in quante ha perso <b>almeno il 10%</b> entro 6 mesi?", "b"))
    if g13 and g13["n"] >= 40:
        out += f"<p class='rg-t'>Guardando solo dal 2013 (periodo più recente, {g13['n']} giorni): nuovo minimo nel <b>{_pc(g13['a'])}</b> dei casi.</p>"
    ad = r.get("adozione", {})
    out += ("<p class='rg-t'><b>Affidabilità:</b> verificato su dati che il modello non aveva visto.</p>" if ad.get("adottata") else
            "<p class='rg-t'><b>Affidabilità:</b> è una regolarità osservata nel passato, <b>non ancora confermata su dati nuovi</b>. Usala come indizio, non come previsione.</p>")
    return out


def box_oggi(o: dict | None, r: dict | None = None) -> str:
    if r is None and FILE.exists():
        try:
            r = json.loads(FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            r = None
    if not o:
        return ""
    st = o["stato"]
    col = COL_STATO[st]
    a, m20, pn = o["A"], o["min20"], o["Pn"]
    # scala 0-100 dell'Indice Armor con tre zone e due segnaposto
    scala = ("<div class='rg-sc'><i style='left:0;width:35%;background:#16a34a'></i><i style='left:35%;width:10%;background:#64748b'></i><i style='left:45%;width:55%;background:#d97706'></i>"
             f"<b class='rg-m' style='left:{min(max(a, 1), 99):.1f}%;background:var(--tx)' title='Oggi'>{a:.0f}</b>"
             f"<em class='rg-m2' style='left:{min(max(m20, 1), 99):.1f}%' title='Minimo a 20 sedute'></em></div>"
             "<div class='rg-zl'><span style='width:35%'>calma</span><span style='width:10%'></span><span style='width:55%'>tensione (da 45)</span></div>")
    if o["sopra45"]:
        cont = (f"L'indice è sopra 45 da <b>{o['sopra45']}</b> sedute di fila. L'allerta «persistente» scatta quando <b>anche il giorno più tranquillo delle ultime 20 sedute</b> è sopra 45 "
                f"(oggi quel minimo è <b>{m20:.0f}</b>).")
    else:
        cont = (f"L'indice oggi vale <b>{a:.0f}</b>. L'allerta «persistente» scatta solo se <b>anche il giorno più tranquillo delle ultime 20 sedute</b> resta sopra 45: "
                f"oggi quel minimo è <b>{m20:.0f}</b> (il trattino sulla scala).")
    barra = ""
    if pn is not None:
        barra = ("<div class='rg-p'><div class='rg-pt'>Da quanto tempo la tensione dura <span>(pressione accumulata)</span></div>"
                 f"<div class='rtb'><i style='width:{pn * 100:.0f}%;background:{col}'></i><span style='left:80%'></span></div>"
                 f"<div class='rg-pl'><span>0 = mai alta di recente</span><b>{pn * 100:.0f}/100</b><span>100 = massimo storico</span></div>"
                 "<div class='rg-t'>La linea verticale a 80 è la soglia di allerta. Conta quanto l'indice è stato alto di recente: i giorni vecchi pesano sempre meno.</div></div>")
    info = ("<details class='rg-info'><summary><i>i</i> Come si legge questo riquadro</summary><div>"
            "<p><b>Indice Armor.</b> Il numero da 0 a 100 con cui Armor misura la tensione del mercato oggi: più è alto, più il mercato è sotto stress.</p>"
            "<p><b>I cinque stati.</b> Calma: indice sotto 35. Normale: tra 35 e 45, senza segnali. Tensione in formazione: indice sopra 45 da poco. "
            "Tensione persistente: sopra 45 senza mai scendere per almeno 20 sedute. Persistente con mercato in calo: come prima, ma l'S&amp;P 500 è già almeno il 5% sotto il suo massimo.</p>"
            "<p><b>Pressione accumulata.</b> Somma di quanto l'indice è stato sopra 40 nei giorni passati, con peso che si dimezza ogni ~23 sedute, trasformata in una scala 0–100 rispetto a tutta la storia.</p>"
            "<p><b>Le barre.</b> Guardano ogni giorno passato in cui il mercato era nello stesso stato di oggi e contano cosa è successo nei 6 mesi dopo, confrontandolo con un giorno qualsiasi.</p></div></details>")
    titolo = {"calma": "Il mercato è tranquillo", "normale": "Nessun segnale di tensione prolungata", "formazione": "Una tensione potrebbe formarsi",
              "persistente": "La tensione dura da settimane", "persistente_calo": "Tensione che dura e mercato già in calo"}[st]
    return (f"<section class='card rt rg' style='--rgc:{col};border-left:5px solid {col}'><div class='rg-q'>Regime di tensione · <a href='#regime' data-go='regime'>Dettagli ›</a></div>"
            f"<div class='rg-hl'><i style='background:{col}'></i><span>{NOMI_STATO[st]}</span></div><div class='rg-sub'>{titolo}.</div>"
            f"<div class='rg-pt'>Indice Armor oggi (0–100)</div>{scala}<div class='rg-t'>{cont}</div>{barra}"
            f"<h4 class='rg-h'>E in passato, dopo giorni come oggi?</h4>{_barre_storiche(st, r)}{info}</section>")


CSS = ("<style>"
       ".rg-q{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mu);font-weight:700}.rg-hl{display:flex;align-items:center;gap:10px;font-size:22px;font-weight:800;margin:6px 0 2px}.rg-hl i{width:18px;height:18px;border-radius:50%}"
       ".rg-sub{font-size:14px;color:var(--mu);margin-bottom:10px}.rg-pt{font-size:13px;font-weight:700;margin:10px 0 4px}.rg-pt span{font-weight:400;color:var(--mu)}.rg-t{font-size:12.5px;line-height:1.5;color:var(--mu);margin:6px 0}.rg-t b{color:var(--tx)}"
       ".rg-sc{position:relative;height:14px;border-radius:99px;background:var(--bd);margin:14px 0 4px}.rg-sc i{position:absolute;top:0;height:100%;opacity:.5}.rg-sc i:first-child{border-radius:99px 0 0 99px}.rg-sc i:nth-of-type(3){border-radius:0 99px 99px 0}"
       ".rg-m{position:absolute;top:-4px;min-width:22px;height:22px;margin-left:-11px;border-radius:50%;color:var(--bg);font-size:11px;line-height:22px;text-align:center;border:2px solid var(--card);box-sizing:content-box;z-index:2;padding:0 1px}"
       ".rg-m2{position:absolute;top:-6px;width:3px;height:26px;margin-left:-1px;background:var(--tx);opacity:.6;z-index:1}.rg-zl{display:flex;font-size:10.5px;color:var(--mu)}"
       ".rg-pl{display:flex;justify-content:space-between;font-size:11px;color:var(--mu);margin-top:3px}.rg-pl b{color:var(--tx);font-size:13px}.rg-h{margin:16px 0 6px;font-size:15px}"
       ".rg-c{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:8px 0}.rg-ct{font-size:13px;margin-bottom:6px}.rg-bl{display:flex;justify-content:space-between;font-size:12.5px;margin-top:4px}.rg-bl b{font-size:14px}"
       ".rg-bar{height:9px;border-radius:99px;background:var(--bd);margin-top:3px;overflow:hidden}.rg-bar i{display:block;height:100%;border-radius:99px}"
       ".rg-info{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:10px 0 0;font-size:13px;line-height:1.5}.rg-info summary{cursor:pointer;font-weight:700}.rg-info summary i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:50%;background:var(--tx);color:var(--bg);font-style:normal;font-size:12px;margin-right:6px}.rg-info p{margin:8px 0}"
       ".rtb{height:10px;border-radius:6px;background:var(--bd);position:relative;margin:8px 0 2px;overflow:hidden}.rtb i{display:block;height:100%}"
       ".rtb span{position:absolute;top:0;bottom:0;width:2px;background:var(--tx);opacity:.55}.rt .rth{margin-bottom:4px}"
       ".rtg{width:100%;height:300px;display:block}.rtl{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;margin:4px 0}.rtl i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px}"
       ".rtt td.g,.rtt th.g{text-align:center}.rtneg{color:#dc2626}.rtpos{color:#16a34a}</style>")


def grafico_dati(a: pd.Series | None = None, p: pd.Series | None = None) -> dict | None:
    """S&P 500 (log, dal 2000) e fasce di regime per il grafico: [[inizio,fine,stato],…] con indici sulla serie."""
    a = store.load("armor_index") if a is None else a
    p = closed_sp500() if p is None else p
    f = variabili(a, p)
    pp = p[p.index >= f.index[0]]
    st = stato_di(f).reindex(pp.index, method="ffill")
    fasce, cur, ini = [], None, 0
    for i, s in enumerate(st.values):
        k = s if s in ("persistente", "persistente_calo", "formazione", "calma") else None
        if k != cur:
            if cur:
                fasce.append([ini, i - 1, cur])
            cur, ini = k, i
    if cur:
        fasce.append([ini, len(st) - 1, cur])
    step = 2
    return {"d": [str(t.date()) for t in pp.index[::step]], "p": [round(float(x), 1) for x in pp.values[::step]], "step": step,
            "n": len(pp), "fasce": [[x // step, y // step, z] for x, y, z in fasce]}


GRAF_JS = r"""<script>(function(){var el=document.getElementById('rtgraf');if(!el)return;var D=JSON.parse(el.getAttribute('data-g')||'null');if(!D)return;
var C={persistente:'rgba(220,38,38,.28)',persistente_calo:'rgba(153,27,27,.42)',formazione:'rgba(217,119,6,.18)',calma:'rgba(22,163,74,.12)'};
function draw(){var W=el.clientWidth||600,Hh=300,dpr=window.devicePixelRatio||1;el.width=W*dpr;el.height=Hh*dpr;var c=el.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
var cs=getComputedStyle(document.body),tx=cs.color,n=D.p.length,mn=Math.min.apply(null,D.p),mx=Math.max.apply(null,D.p),l0=Math.log(mn),l1=Math.log(mx),L=44,R=8,T=8,B=22;
function X(i){return L+(W-L-R)*i/(n-1)}function Y(v){return T+(Hh-T-B)*(1-(Math.log(v)-l0)/(l1-l0))}
c.clearRect(0,0,W,Hh);D.fasce.forEach(function(f){c.fillStyle=C[f[2]]||'transparent';c.fillRect(X(f[0]),T,Math.max(1,X(f[1])-X(f[0])),Hh-T-B)});
c.strokeStyle=tx;c.globalAlpha=.15;c.fillStyle=tx;c.font='11px sans-serif';[1,2,4,8].forEach(function(k){var v=Math.pow(2,Math.round(Math.log(mn)/Math.LN2))*k;if(v>=mn&&v<=mx){c.beginPath();c.moveTo(L,Y(v));c.lineTo(W-R,Y(v));c.stroke()}});
[500,1000,2000,4000,8000].forEach(function(v){if(v>=mn&&v<=mx){c.globalAlpha=.15;c.beginPath();c.moveTo(L,Y(v));c.lineTo(W-R,Y(v));c.stroke();c.globalAlpha=.7;c.fillText(v,4,Y(v)+4)}});
c.globalAlpha=.7;for(var y=2000;y<=2026;y+=4){var i=D.d.findIndex(function(s){return s.slice(0,4)==String(y)});if(i>=0)c.fillText(y,X(i)-10,Hh-6)}
c.globalAlpha=1;c.strokeStyle='#3b82f6';c.lineWidth=1.6;c.beginPath();D.p.forEach(function(v,i){i?c.lineTo(X(i),Y(v)):c.moveTo(X(i),Y(v))});c.stroke()}
draw();window.addEventListener('resize',draw);new MutationObserver(draw).observe(document.body,{attributes:true})})();</script>"""


def _tab_stati(r: dict) -> str:
    h = "<div class='scroll'><table class='tbl rtt'><tr><th>Stato dell'indice</th><th class='g'>Giorni</th><th class='g'>Ingressi</th>"
    h += "".join(f"<th class='g'>{t}</th>" for t in ("Nuovo minimo", "Calo ≥10%", "Chiusura negativa", "Calo graduale"))
    h += "</tr>"
    for per, lab in (("tutto", "2000–oggi"), ("2000_2012", "2000–2012"), ("2013_oggi", "2013–oggi")):
        h += f"<tr><td colspan='7'><b>{lab}</b></td></tr>"
        for k in ("calma", "normale", "formazione", "persistente", "persistente_calo", "tutti"):
            g = r["stati"][per].get(k)
            if not g or not g["n"]:
                continue
            nome = NOMI_STATO.get(k, "Tutti i giorni")
            h += f"<tr><td>{nome}</td><td class='g'>{g['n']}</td><td class='g'>{'' if g['episodi'] is None else g['episodi']}</td>" + "".join(f"<td class='g'>{_pc(g[x])}</td>" for x in "abcd") + "</tr>"
    return h + "</table></div><p class='mu'>Giorni consecutivi si sovrappongono: guarda soprattutto il numero di episodi. Con pochi episodi la percentuale è solo un indizio.</p>"


def _tab_episodi(r: dict) -> str:
    ep = r["episodi"]["V1"]
    h = ("<div class='scroll'><table class='tbl rtt'><tr><th>Inizio</th><th class='g'>Durata (sedute)</th><th class='g'>Calo max entro 6 mesi</th><th class='g'>Nuovo minimo</th><th class='g'>Rend. 6 mesi</th><th class='g'>Rend. 12 mesi</th></tr>")
    for e in ep:
        nm = "—" if e["nuovo_minimo"] is None else ("sì" if e["nuovo_minimo"] else "no")
        h += (f"<tr><td>{e['inizio'][8:]}/{e['inizio'][5:7]}/{e['inizio'][:4]}</td><td class='g'>{e['durata']}</td><td class='g {'rtneg' if (e['calo_max'] or 0) <= -0.1 else ''}'>{_pc(e['calo_max'], 1)}</td>"
              f"<td class='g'>{nm}</td><td class='g'>{_pc(e['r126'], 1)}</td><td class='g'>{_pc(e['r252'], 1)}</td></tr>")
    return h + "</table></div><p class='mu'>Un episodio inizia la prima volta che l'indice resta sopra 45 per 20 sedute dopo almeno 60 sedute senza la condizione. «—» = non ancora maturato.</p>"


def _tab_varianti(r: dict) -> str:
    nom = {"V1": "V1 · minimo a 20 sedute ≥ 45", "V2": "V2 · media a 60 sedute ≥ 45", "V3": "V3 · Pressione accumulata", "V4": "V4 · Pressione × mercato in calo"}
    h = ("<div class='scroll'><table class='tbl rtt'><tr><th>Variante</th><th class='g'>2006–2012 (scelta)<br>BSS medio</th><th class='g'>2013–oggi: calo ≥10%<br>BSS [90%]</th><th class='g'>AUC</th><th class='g'>Episodi dal 2013</th></tr>")
    for v in VARIANTI:
        vb = r["varianti"][v]["verifica"]["b"]
        bs = "—" if vb.get("bss") is None else f"{vb['bss']:+.3f} [{vb['lo']:+.3f}; {vb['hi']:+.3f}]"
        au = "—" if vb.get("auc") is None else f"{vb['auc']:.2f}"
        sc = " ◀ scelta" if v == r["scelta"] else ""
        h += f"<tr><td>{nom[v]}{sc}</td><td class='g'>{r['scelta_bss_medio'].get(v, 0):+.3f}</td><td class='g'>{bs}</td><td class='g'>{au}</td><td class='g'>{r['episodi_2013'][v]}</td></tr>"
    return h + "</table></div><p class='mu'>BSS (Brier skill score) sopra 0 = meglio della frequenza storica; sotto 0 = peggio. L'intervallo è un bootstrap a blocchi: se include 0, la differenza dal caso non è dimostrata.</p>"


def _km_svg(km: dict) -> str:
    v1, b = km.get("v1") or [], km.get("base") or []
    if not v1 or not b:
        return ""
    W, Hh, L, Bt = 520, 190, 36, 22
    n = len(v1)
    mx = max(max(v1), max(b), 0.2) * 1.1

    def pts(s):
        return " ".join(f"{L + (W - L - 8) * i / (n - 1):.1f},{8 + (Hh - 8 - Bt) * (1 - x / mx):.1f}" for i, x in enumerate(s))
    ax = "".join(f"<text x='{L + (W - L - 8) * i / (n - 1):.0f}' y='{Hh - 6}' font-size='10' fill='currentColor' text-anchor='middle'>{(i + 1)}m</text>" for i in range(0, n, 2))
    gy = "".join(f"<line x1='{L}' x2='{W - 8}' y1='{8 + (Hh - 8 - Bt) * (1 - t / mx):.0f}' y2='{8 + (Hh - 8 - Bt) * (1 - t / mx):.0f}' stroke='currentColor' opacity='.12'/>"
                 f"<text x='2' y='{12 + (Hh - 8 - Bt) * (1 - t / mx):.0f}' font-size='10' fill='currentColor'>{int(t * 100)}%</text>" for t in (0.2, 0.4, 0.6, 0.8) if t <= mx)
    return (f"<svg viewBox='0 0 {W} {Hh}' style='width:100%;max-width:560px;color:var(--tx)'>{gy}{ax}<polyline fill='none' stroke='#dc2626' stroke-width='2.2' points='{pts(v1)}'/>"
            f"<polyline fill='none' stroke='#64748b' stroke-width='2' stroke-dasharray='5 4' points='{pts(b)}'/></svg>"
            f"<div class='rtl'><span><i style='background:#dc2626'></i>Dopo l'inizio di un episodio ({km['n']} episodi)</span><span><i style='background:#64748b'></i>Un giorno qualsiasi</span></div>")


PAC_TXT = ("<p><b>Cosa può significare per chi fa il PAC</b> (non è consulenza finanziaria). Quando la tensione è persistente e il mercato è già in calo, nei dati storici i ribassi sono stati più spesso graduali e i prezzi più bassi sono arrivati mesi dopo. "
           "Per chi accumula, questo suggerisce di <b>non anticipare</b> acquisti straordinari e di distribuirli nel tempo, tenendo invariato il PAC regolare. "
           "Quando l'indice è in zona di calma, il rischio di cali ampi è stato più basso del normale. "
           "Se il segnale non è stato confermato fuori campione, resta un'informazione descrittiva e non una regola da seguire alla lettera.</p>")


def esempio_pac(p: pd.Series | None = None, f: pd.DataFrame | None = None) -> dict | None:
    """PAC costante contro PAC che durante il regime «persistente con mercato in calo» rinvia l'acquisto straordinario (pari al PAC mensile) di 3 mesi.
    Misurato sugli episodi passati dal 2000: mostra solo cosa sarebbe successo, non cosa succederà."""
    try:
        p = closed_sp500() if p is None else p
        f = variabili(store.load("armor_index"), p) if f is None else f
        pp = p.reindex(f.index).ffill()
        cond = (stato_di(f) == "persistente_calo")
        mesi = list(pd.DatetimeIndex(pp.groupby([pp.index.year, pp.index.month]).apply(lambda x: x.index[-1]).values))
        quote_a = quote_b = spesa_a = spesa_b = 0.0
        coda: list[int] = []
        for k, d in enumerate(mesi):
            px = float(pp.loc[d])
            quote_a += 200 / px   # PAC 100 + extra 100 subito
            spesa_a += 200
            quote_b += 100 / px
            spesa_b += 100
            if bool(cond.get(d, False)):
                coda.append(k + 3)
            else:
                quote_b += 100 / px
                spesa_b += 100
            scaduti = [c for c in coda if c <= k]
            for c in scaduti:
                quote_b += 100 / px
                spesa_b += 100
                coda.remove(c)
        pxf = float(pp.iloc[-1])
        va, vb = quote_a * pxf, quote_b * pxf
        return {"extra_subito": {"spesa": spesa_a, "valore": va, "rend": va / spesa_a - 1},
                "extra_rinviato": {"spesa": spesa_b, "valore": vb, "rend": vb / max(spesa_b, 1) - 1},
                "mesi_regime": int(cond.groupby([cond.index.year, cond.index.month]).last().sum()), "ultimo": str(pp.index[-1].date())}
    except Exception:  # noqa: BLE001
        return None


def pagina(o: dict | None, r: dict | None = None, g: dict | None = None) -> str:
    if r is None and FILE.exists():
        try:
            r = json.loads(FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            r = None
    head = ("<h2>Regime di tensione</h2><div class='explain'><p>Hai osservato che quando l'Indice Armor resta <b>a lungo sopra 40–50</b>, il mercato tende a calare gradualmente fino a nuovi minimi. "
            "Qui l'idea è stata trasformata in un indicatore misurato, con regole scritte <b>prima</b> di guardare i risultati recenti (file PROTOCOLLO_REGIME.md). "
            "Sono frequenze storiche, non previsioni, e gli episodi indipendenti sono pochi.</p></div>")
    top = box_oggi(o, r) if o else ""
    from . import grafico
    graf = grafico.block(g)
    if not r:
        return CSS + head + top + graf + "<p class='mu'>L'esperimento sul periodo 2013–oggi non è ancora stato eseguito: lo esegue il lavoro mensile (comando <code>esperimento-regime</code>).</p>"
    ad = r["adozione"]
    cond = ad["condizioni"]
    ok = lambda b: "✔" if b else "✘"  # noqa: E731
    va = r.get("vs_a1")
    va_txt = ("non calcolato" if not va else f"differenza di Brier {va['diff_brier']:+.4f} [{va['lo']:+.4f}; {va['hi']:+.4f}] su {va['n']} date")
    esito = ("<b>Adottato come indicatore ufficiale</b>: ha superato la verifica 2013–oggi." if ad["adottata"] else
             "<b>Indicatore descrittivo, non verificato fuori campione.</b> Non ha superato tutte le condizioni stabilite in anticipo, quindi non viene usato come regola.")
    reg = (f"<div class='card'><h3 style='margin-top:0'>Risultato del protocollo</h3><p>Variante scelta su 2006–2012: <b>{r['scelta']}</b>. Verifica unica su 2013–oggi (dati al {r['asof'][8:]}/{r['asof'][5:7]}/{r['asof'][:4]}).</p>"
           f"<p>{ok(cond['bss_sopra_zero'])} Meglio della frequenza storica, con intervallo al 90% sopra zero<br>{ok(cond['aggiunge_a1'])} Aggiunge informazione rispetto al modello A1 ({va_txt})<br>"
           f"{ok(cond['episodi_4'])} Almeno 4 episodi dal 2013 ({r['episodi_2013'][r['scelta']]})</p><p>{esito}</p></div>")
    om = ombra_verifica()
    om_txt = (f"<p class='mu'>Registro in ombra: {om['righe']} giorni registrati dal {om.get('da', '—')[8:]}/{om.get('da', '—')[5:7]}/{om.get('da', '—')[:4]}, {om['mature']} già verificabili a 6 mesi."
              + ("" if not om.get("v1_on") else f" Con condizione attiva: {om['v1_on']} giorni, calo ≥10% nel {_pc(om['b_on'])} contro {_pc(om['b_tutti'])} di tutti i giorni.") + "</p>") if om.get("righe") else "<p class='mu'>Registro in ombra appena avviato.</p>"
    pac = esempio_pac()
    pac_txt = ""
    if pac:
        a_, b_ = pac["extra_subito"], pac["extra_rinviato"]
        pac_txt = (f"<p class='mu'>Esempio storico dal 2000 (S&amp;P 500, 100 € al mese più 100 € straordinari): comprare subito l'extra ha dato {_pc(a_['rend'], 1)} sul totale versato, "
                   f"rinviare l'extra di 3 mesi durante i {pac['mesi_regime']} mesi di «tensione persistente con mercato in calo» ha dato {_pc(b_['rend'], 1)}. "
                   "È solo cosa sarebbe successo in questa storia, con pochi episodi: non dice cosa succederà.</p>")
    return (CSS + head + top + graf + "<h3 style='margin-top:18px'>Cosa è successo dopo, per stato dell'indice</h3>" + _tab_stati(r)
            + "<h3 style='margin-top:18px'>Gli episodi passati</h3>" + _tab_episodi(r)
            + "<h3 style='margin-top:18px'>Probabilità di toccare un nuovo minimo, mese per mese</h3>" + _km_svg(r["km"])
            + "<h3 style='margin-top:18px'>Le quattro varianti provate</h3>" + _tab_varianti(r) + reg + om_txt
            + "<div class='card'><h3 style='margin-top:0'>Anche negli altri mercati?</h3>" + _rob(r) + "</div>"
            + "<div class='card'>" + PAC_TXT + pac_txt + "</div>")


def _rob(r: dict) -> str:
    rb = r.get("robustezza") or {}
    if not rb:
        return "<p class='mu'>Non calcolato.</p>"
    h = "<div class='scroll'><table class='tbl rtt'><tr><th>Mercato</th><th class='g'>Giorni con regime</th><th class='g'>Nuovo minimo<br>con regime · senza</th><th class='g'>Calo ≥10%<br>con · senza</th><th class='g'>Chiusura negativa<br>con · senza</th></tr>"
    for n, x in rb.items():
        h += f"<tr><td>{n} (dal {x['da'][:4]})</td><td class='g'>{x['giorni_on']}</td>" + "".join(f"<td class='g'>{_pc(x[k][0])} · {_pc(x[k][1])}</td>" for k in ("a", "b", "cn")) + "</tr>"
    return h + "</table></div><p class='mu'>Stessa regola (indice Armor americano ≥45 per 20 sedute) applicata ad altri mercati: è un test semi-indipendente, ma anche questi mercati si muovono con l'S&amp;P 500.</p>"
