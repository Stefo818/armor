# -*- coding: utf-8 -*-
"""Titan+ (PROTOCOLLO_TITAN_PLUS.md): parte dalla probabilità di FHS+VIX e la corregge con i sei pilastri di Titan.
I pesi della correzione si autoregolano: ogni settimana si rifà una regressione logistica con memoria che sbiadisce (mezza vita in anni),
usando solo gli esiti già maturati, con un «elastico» che tiene i pesi vicino allo zero (allora Titan+ = FHS+VIX).
Gruppi di mercato (calmo/agitato, sotto la media lunga) hanno pesi propri, ma legati ai pesi generali da un elastico più stretto.
Freno automatico: se negli ultimi 2 anni Titan+ sbaglia più di FHS+VIX, l'elastico si stringe."""
import numpy as np
import pandas as pd

from . import modelli_finestre as mf
from . import modelli_preds, store
from .config import DATA, HORIZONS, PRIMARY
from .features import closed_sp500

PIL = [f"p{i}_stress" for i in range(1, 7)]
LAM = {"a": 1e7, "w": 50.0, "s": 1e7, "g": 150.0}   # elastici (fissati prima delle prove); termine fisso e pendenza bloccati a zero (errore di metodo corretto dal protocollo n.3): si misura solo l'effetto dei pilastri
MINIMO = 150          # esiti maturati necessari prima di correggere
CRISI = [("2000-03-01", "2002-12-31"), ("2007-10-01", "2009-06-30"), ("2020-02-01", "2020-06-30"), ("2022-01-01", "2022-12-31")]


def _lg(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _sg(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def prepara(hz: str, p: pd.Series | None = None, preds: pd.DataFrame | None = None, oggi: dict | None = None) -> pd.DataFrame:
    """Tabella per orizzonte: esito, probabilità FHS+VIX (p0), Titan (pT), pilastri standardizzati col solo passato, gruppi di mercato."""
    p = closed_sp500() if p is None else p
    mp = modelli_preds.carica() if preds is None else preds
    mp = mp.assign(kind="down") if "kind" not in mp else mp
    pr = {m: g for m, g in mp.groupby("model")}
    E = mf.errori(p, {m: pr[m] for m in ("FHS+VIX", "Titan")}, modelli=("FHS+VIX", "Titan"))[hz]
    d = E.index
    from .modeleval import outcome
    y = outcome(p, d, hz, "down", PRIMARY[hz])

    def serie(m):
        g = pr[m]
        return g[(g.hz == hz) & (g.thr == PRIMARY[hz])].drop_duplicates("date").set_index("date")["p"].loc[d]
    t = pd.DataFrame({"y": y, "p0": serie("FHS+VIX"), "pT": serie("Titan")}, index=d)
    if oggi:   # riga di oggi (esito ignoto): serve solo per la previsione del giorno
        dt_ = pd.Timestamp(oggi["date"])
        t.loc[dt_] = [np.nan, float(oggi["p0"]), float(oggi.get("pT", oggi["p0"]))]
        t = t.sort_index()
        d = t.index
    st = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)[PIL]
    st = st.reindex(st.index.union(d)).ffill().reindex(d)
    mu, sd = st.expanding(250).mean(), st.expanding(250).std()
    z = ((st - mu) / sd.replace(0, np.nan)).clip(-4, 4).fillna(0.0)
    zr = ((st - st.rolling(1260, 500).mean()) / st.rolling(1260, 500).std().replace(0, np.nan)).clip(-4, 4).fillna(0.0)
    for c in PIL:
        t["z" + c[1]] = z[c]
        t["r" + c[1]] = zr[c]          # standardizzazione sugli ultimi ~5 anni (sedute giornaliere, qui ~1260 date di storia)
    vix = store.load("vix").reindex(p.index).ffill(limit=5).reindex(d)
    q = vix.expanding(750).quantile(0.7)
    from . import fasi
    tend = fasi.tendenza(p).reindex(d)
    g = np.zeros(len(d), int)
    g[(vix > q).values] = 1                        # agitato
    g[(tend == "ribasso").values] = 2             # sotto la media lunga (ha la precedenza)
    t["g"] = g
    t["pos"] = p.index.get_indexer(d)
    t["base_g"] = g
    return t


def _fit(X, off, y, w, pen, th0=None, it=10):
    th = np.zeros(X.shape[1]) if th0 is None else th0.copy()
    for _ in range(it):
        eta = off + X @ th
        mu = _sg(eta)
        W = w * mu * (1 - mu) + 1e-9
        gr = X.T @ (w * (y - mu)) - pen * th
        H = (X * W[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, gr)
        th += np.clip(step, -1.5, 1.5)
        if np.abs(step).max() < 1e-5:
            break
    return th


def esegui(hz: str, mezza_vita: float = 5.0, gruppi: bool = True, freno: bool = True, tab: pd.DataFrame | None = None, fino: str | None = None, feat: str = "z") -> pd.DataFrame:
    """Previsione giorno per giorno di Titan+: restituisce la tabella con la colonna pP (probabilità di Titan+)."""
    t = prepara(hz) if tab is None else tab.copy()
    h = HORIZONS[hz]
    n = len(t)
    # feat: "z" = pilastri standardizzati (prova 1); "zpos" = solo la parte sopra la norma, così in mercato tranquillo non si tocca nulla (prova 2); "rpos" = come zpos ma standardizzati sugli ultimi anni (prova 3)
    z = t[[f"{'r' if feat == 'rpos' else 'z'}{i}" for i in range(1, 7)]].values
    if feat in ("zpos", "rpos"):
        z = np.maximum(z, 0.0)
    lg0 = _lg(t["p0"].values)
    y = t["y"].values
    pos = t["pos"].values
    dt = t.index.values.astype("datetime64[D]").astype(int)
    grp = t["g"].values if gruppi else np.zeros(n, int)
    ng = 3 if gruppi else 1
    # colonne: 1, pendenza su logit(p0) centrata, 6 pilastri, poi per ogni gruppo 1..2: 6 pilastri
    mlg = np.nanmean(lg0)
    def design(ix):
        base = np.column_stack([np.ones(len(ix)), lg0[ix] - mlg, z[ix]])
        if not gruppi:
            return base
        ex = [z[ix] * (grp[ix] == k)[:, None] for k in (1, 2)]
        return np.column_stack([base] + ex)
    pen0 = np.array([LAM["a"], LAM["s"]] + [LAM["w"]] * 6 + ([LAM["g"]] * 12 if gruppi else []))
    pP = lg0.copy()
    out = np.full(n, np.nan)
    th = None
    lam_mult = 1.0
    ultimo_fit = -99
    for i in range(n):
        mat = np.flatnonzero((pos[:i] + h <= pos[i]) & ~np.isnan(y[:i]))
        if len(mat) >= MINIMO:
            if freno and i > 104:
                r = mat[-104:]
                pr = _sg(pP[r])
                b_new = np.mean((pr - y[r]) ** 2)
                b_old = np.mean((t["p0"].values[r] - y[r]) ** 2)
                lam_mult = 4.0 if b_new > b_old else 1.0
            if i - ultimo_fit >= 1:
                age = (dt[i] - dt[mat]) / 365.25
                w = 0.5 ** (age / mezza_vita)
                X = design(mat)
                th = _fit(X, lg0[mat], y[mat], w, pen0 * lam_mult, th)
                ultimo_fit = i
            eta = lg0[i] + design(np.array([i])) @ th
            pP[i] = float(eta[0])
        out[i] = _sg(pP[i])
        pP[i] = pP[i]
        if fino and str(t.index[i].date()) > fino:
            out[i + 1:] = np.nan
            break
    t["pP"] = out
    return t


def metriche(t: pd.DataFrame, da: str, a: str) -> dict:
    """Errore medio (Brier) di FHS+VIX, Titan e Titan+, risparmio di Titan+ su FHS+VIX, crisi, periodi calmi, intervallo al 90%."""
    from .modeleval import auc, block_ci
    s = t.loc[da:a].dropna(subset=["y", "pP"])
    e = {k: (s[c] - s["y"]) ** 2 for k, c in (("FHS+VIX", "p0"), ("Titan", "pT"), ("Titan+", "pP"))}
    r = {k: float(v.mean() * 1000) for k, v in e.items()}
    r["risparmio_%"] = float((1 - e["Titan+"].sum() / e["FHS+VIX"].sum()) * 100)
    r["risparmio_titan_%"] = float((1 - e["Titan"].sum() / e["FHS+VIX"].sum()) * 100)
    lo, hi = block_ci(e["Titan+"].values, e["FHS+VIX"].values, 5)
    r["ci90"] = (round(lo * 100, 1), round(hi * 100, 1))
    cr = pd.Series(False, index=s.index)
    for x, y_ in CRISI:
        cr[x:y_] = True
    for nome, m in (("crisi", cr), ("calmi", s["g"] == 0)):
        if m.sum() > 10:
            r[f"{nome}_%"] = float((1 - e["Titan+"][m].sum() / e["FHS+VIX"][m].sum()) * 100)
            r[f"{nome}_n"] = int(m.sum())
    r["auc_p0"], r["auc_P"] = auc(s["p0"], s["y"]), auc(s["pP"], s["y"])
    r["n"] = int(len(s))
    return r


def storia_preds(log=print) -> pd.DataFrame:
    """Previsioni storiche di Titan+ (stesse date di FHS+VIX e Titan in modelli_preds.csv), nel formato del resto della valutazione."""
    righe = []
    for hz in mf.HZ:
        t = esegui(hz)
        thr = PRIMARY[hz]
        for d, v in t["pP"].dropna().items():
            righe.append({"date": d, "hz": hz, "kind": "down", "thr": int(thr), "p": float(v)})
        log(f"[valuta] Titan+ {hz}: {int(t['pP'].notna().sum())} previsioni")
    return pd.DataFrame(righe)


def oggi(data, p0: dict, pT: dict | None = None, p: pd.Series | None = None) -> dict:
    """Probabilità di calo di Titan+ per oggi, per ogni orizzonte. p0 = {hz: FHS+VIX}, pT = {hz: Titan}. Se qualcosa manca, ritorna ciò che riesce."""
    out = {}
    p = closed_sp500() if p is None else p
    mp = modelli_preds.carica()
    for hz in mf.HZ:
        try:
            if hz not in p0:
                continue
            x = {"date": data, "p0": p0[hz], "pT": (pT or {}).get(hz, p0[hz])}
            t = esegui(hz, tab=prepara(hz, p, mp, oggi=x))
            v = t["pP"].iloc[-1]
            out[hz] = float(v) if np.isfinite(v) else float(p0[hz])
        except Exception as e:  # noqa: BLE001
            print(f"[titan+] {hz} non calcolato:", str(e)[:80], flush=True)
    return out
