"""Esperimento VRP e HAR (PIANO_ARMOR3 Fasi 6a-6b), sempre in ombra. Regole in PROTOCOLLO_VRP.md (scritte prima dei risultati)."""
import json

import numpy as np
import pandas as pd

from . import fhs, store
from . import percorsi as P
from . import verifica as V
from .config import DATA, HORIZONS
from .features import fwd_maxdd, fwd_ret

FILE = DATA / "vrp_ombra.json"
INIZIO_DATI = "2008-01-01"
MODELLI = ["VIX", "FHS", "FHS+VIX", "HAR", "HAR-X", "FHS+VIX+VRP"]
RIF = "FHS+VIX"
FLOOR_VAR = 25.0          # %² annui (5% di volatilità)
MIN_OSS, FIN_VRP = 750, 1260


# ------------------------------------------------------------------ Yang-Zhang
def componenti(o: pd.Series, h: pd.Series, l: pd.Series, c: pd.Series) -> pd.DataFrame:
    """Per ogni seduta: parte notturna (o), di seduta (c), Rogers-Satchell (rs) e proxy giornaliero v = o² + rs, in %² (log-rendimenti ×100)."""
    d = pd.concat([o, h, l, c], axis=1, keys=list("ohlc"), sort=True).dropna()
    d = d[d.index >= INIZIO_DATI]
    pc = d["c"].shift(1)
    x = pd.DataFrame(index=d.index)
    x["on"] = np.log(d["o"] / pc) * 100
    x["id"] = np.log(d["c"] / d["o"]) * 100
    hh, ll, cc = np.log(d["h"] / d["o"]) * 100, np.log(d["l"] / d["o"]) * 100, np.log(d["c"] / d["o"]) * 100
    x["rs"] = hh * (hh - cc) + ll * (ll - cc)
    x["v"] = x["on"] ** 2 + x["rs"]
    return x.dropna()


def yang_zhang(x: pd.DataFrame, n: int = 21) -> pd.Series:
    """Stimatore Yang-Zhang su n sedute, annualizzato (%²). k = 0,34 / (1,34 + (n+1)/(n−1))."""
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    s_on = x["on"].rolling(n).var()
    s_id = x["id"].rolling(n).var()
    s_rs = x["rs"].rolling(n).mean()
    return (s_on + k * s_id + (1 - k) * s_rs) * 252


def tabella(x: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    """Variabili per le regressioni, alla data d: proxy giornaliero, media a 5 sedute, YZ a 21; esito y = YZ delle 21 sedute successive."""
    yz = yang_zhang(x)
    t = pd.DataFrame(index=x.index)
    t["rv_d"] = x["v"] * 252
    t["rv_w"] = x["v"].rolling(5).mean() * 252
    t["rv_m"] = yz
    t["vix2"] = vix.reindex(x.index).ffill(limit=5) ** 2
    t["y"] = yz.shift(-21)
    return t


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def previsioni_varianza(t: pd.DataFrame) -> pd.DataFrame:
    """Walk-forward: previsione a 21 sedute alla data d dei modelli di varianza, con soli esiti noti (d' ≤ d − 21)."""
    n = len(t)
    out = pd.DataFrame(index=t.index, columns=["VIX", "HAR", "HAR-X", "VRP"], dtype=float)
    A = t[["rv_d", "rv_w", "rv_m", "vix2", "y"]].values
    ok_all = np.isfinite(A).all(axis=1)
    for i in range(n):
        j = i - 21
        if j < MIN_OSS or not np.isfinite(A[i, :4]).all():
            continue
        m = ok_all[: j + 1]
        if m.sum() < MIN_OSS:
            continue
        tr = A[: j + 1][m]
        X1 = np.column_stack([np.ones(len(tr)), tr[:, 0], tr[:, 1], tr[:, 2]])
        X2 = np.column_stack([X1, tr[:, 3]])
        b1, b2 = _ols(X1, tr[:, 4]), _ols(X2, tr[:, 4])
        xi = A[i]
        out.iloc[i, out.columns.get_loc("VIX")] = xi[3]
        out.iloc[i, out.columns.get_loc("HAR")] = max(float(np.r_[1, xi[:3]] @ b1), FLOOR_VAR)
        out.iloc[i, out.columns.get_loc("HAR-X")] = max(float(np.r_[1, xi[:4]] @ b2), FLOOR_VAR)
        rec = tr[-FIN_VRP:]
        vrp = float((rec[:, 3] - rec[:, 4]).mean())
        out.iloc[i, out.columns.get_loc("VRP")] = max(xi[3] - vrp, 0.25 * xi[3])
    return out


def s0_da_bersaglio(st: dict, var_annua: float) -> float:
    """Varianza iniziale del GARCH tale che la media attesa dei primi 21 giorni coincida con la previsione (annua, %²)."""
    rho, lr = st["rho"], st["s2_lr"]
    k = np.arange(21)
    return float(max(lr + (var_annua / 252.0 - lr) / np.mean(rho ** k), 0.05 * lr))


# ------------------------------------------------------------------ walk-forward delle probabilità
def walk_forward(p: pd.Series, dates, prev: pd.DataFrame, vix: pd.Series, sims: int = 3000, refit_every: int = 252, embargo: int = 5, log=print) -> dict[str, pd.DataFrame]:
    r_all = fhs.log_returns(p[p.index >= fhs.FIT_START])
    idx = r_all.index
    rows = {m: [] for m in MODELLI}
    st, last_fit, x0 = None, -10 ** 9, None
    for t in dates:
        if t not in idx:
            continue
        i = idx.get_loc(t)
        if i < 750:
            continue
        if st is None or i - last_fit >= refit_every:
            j = max(i - embargo, 500)
            par = fhs.fit(r_all.values[:j], x0)
            x0 = par["theta"]
            st = P.stato(r_all.values[:j], par)
            last_fit = i
        stt = dict(st)
        stt["s2_next"] = fhs.next_variance(st["par"], r_all.values[: i + 1])
        vv = vix[vix.index <= t]
        v1 = float(vv.iloc[-1]) if len(vv) and (t - vv.index[-1]).days < 7 else None
        pr = prev.loc[t] if t in prev.index else None
        seed = int(t.strftime("%Y%m%d")) % (2 ** 31)
        s0s = {"FHS": stt["s2_next"], "FHS+VIX": fhs.adjust_with_vix(stt["s2_next"], v1, 0.5) if v1 else None}
        if pr is not None:
            for m, col in (("VIX", "VIX"), ("HAR", "HAR"), ("HAR-X", "HAR-X"), ("FHS+VIX+VRP", "VRP")):
                if np.isfinite(pr[col]):
                    s0s[m] = s0_da_bersaglio(stt, float(pr[col]))
        for m, s0 in s0s.items():
            if s0 is None:
                continue
            res = P.riassumi(P.simula(stt, s0, "T1", sims, seed, None, h=126), {k: n for k, n in P.ORIZZONTI.items() if n <= 126})
            for hz, o in res.items():
                for thr, pv in o["down"].items():
                    rows[m].append({"date": t, "hz": hz, "kind": "down", "thr": thr, "p": pv})
                for thr, pv in o["mdd"].items():
                    rows[m].append({"date": t, "hz": hz, "kind": "mdd", "thr": thr, "p": pv})
                rows[m].append({"date": t, "hz": hz, "kind": "neg", "thr": 0, "p": o["p_neg"]})
                for q in P.QLEV:
                    rows[m].append({"date": t, "hz": hz, "kind": "q", "thr": q, "p": o["ret"][f"q{q}"]})
    return {m: pd.DataFrame(x) for m, x in rows.items()}


def _esito(p: pd.Series, hz: str, kind: str, thr: int) -> pd.Series:
    n = P.ORIZZONTI[hz]
    if kind == "down":
        e = fwd_maxdd(p, n)
        return (e <= -thr / 100).astype(float).where(e.notna())
    if kind == "mdd":
        e = P.mdd_futuro(p, n)
        return (e <= -thr / 100).astype(float).where(e.notna())
    e = fwd_ret(p, n)
    return (e < 0).astype(float).where(e.notna())


def _base(y_all: pd.Series, p: pd.Series, dates, n: int) -> pd.Series:
    cs, cn = y_all.fillna(0).cumsum(), y_all.notna().astype(int).cumsum()
    pos = p.index.get_indexer(dates)
    j = np.maximum(pos - n, 0)
    return pd.Series(cs.values[j] / np.maximum(cn.values[j], 1), index=dates)


BERSAGLI = [("1m", "down", 5), ("1m", "mdd", 5), ("3m", "down", 10), ("1m", "neg", 0), ("3m", "neg", 0)]


def valuta(p: pd.Series, dates, wf: dict, prev: pd.DataFrame, t: pd.DataFrame, step: int = 5, reps: int = 1000) -> dict:
    pos = pd.Series(np.arange(len(p)), index=p.index).reindex(dates)
    out = {"bersagli": [], "varianza": {}}
    # QLIKE della previsione di varianza a 21 sedute (stesse date, esito noto)
    y = t["y"].reindex(dates)
    cols = {"VIX": prev["VIX"], "HAR": prev["HAR"], "HAR-X": prev["HAR-X"], "FHS+VIX+VRP": prev["VRP"]}
    D = pd.DataFrame({k: v.reindex(dates) for k, v in cols.items()})
    D["y"] = y
    D = D.dropna()
    if len(D) > 100:
        L = V.blocco_medio(21, step)
        ql = {m: np.maximum(D["y"].values, 1e-9) / np.maximum(D[m].values, 1e-9) - np.log(np.maximum(D["y"].values, 1e-9) / np.maximum(D[m].values, 1e-9)) - 1 for m in cols}
        pv = {}
        for m in cols:
            if m == "VIX":
                continue
            pv[m] = V.dm_test(ql[m], ql["VIX"], L - 1)["p"]
        adj = V.holm(pv)
        for m in cols:
            d = V.boot_diff(ql[m], ql["VIX"], L, reps) if m != "VIX" else {"diff": 0.0, "lo": 0.0, "hi": 0.0}
            out["varianza"][m] = {"qlike": float(ql[m].mean()), "diff_vs_vix": d, "p_holm": adj.get(m), "rapporto_medio_previsto_realizzato": float((D[m] / D["y"]).mean())}
        out["varianza"]["_n"] = int(len(D))
        out["varianza"]["_da"], out["varianza"]["_a"] = str(D.index[0].date()), str(D.index[-1].date())
    for hz, kind, thr in BERSAGLI:
        n = P.ORIZZONTI[hz]
        y_all = _esito(p, hz, kind, thr)
        yy = y_all.reindex(dates)
        base = _base(y_all, p, dates, n)
        rt = fwd_ret(p, n).reindex(dates)
        sel = {}
        for m, df in wf.items():
            if df is None or df.empty:
                continue
            g = df[(df.hz == hz) & (df.kind == kind) & (df.thr == thr)].set_index("date")["p"].dropna()
            if len(g):
                sel[m] = g
        modelli = [m for m in MODELLI if m in sel]
        if RIF not in modelli:
            continue
        comuni = None
        for m in modelli:
            comuni = sel[m].index if comuni is None else comuni.intersection(sel[m].index)
        d = V.prepara(dates, pos, yy, base, {m: sel[m].reindex(comuni) for m in modelli})
        if len(d) < 100:
            continue
        righe, pv = {}, {}
        for m in modelli:
            r = V.valuta_modello(d, m, n, step, RIF, reps)
            if hz in ("1m", "3m"):
                ix = d.index
                qs = {q: wf[m][(wf[m].hz == hz) & (wf[m].kind == "q") & (wf[m].thr == q)].set_index("date")["p"].reindex(ix) for q in P.QLEV}
                r["copertura_10_90"] = V.copertura(qs[10].values, qs[90].values, rt.reindex(ix).values)
                r["crps"] = V.crps_quantili([q / 100 for q in P.QLEV], np.column_stack([qs[q].values for q in P.QLEV]), rt.reindex(ix).values)
            righe[m] = r
            if m != RIF:
                pv[m] = r["vs_ref"]["dm"]["p"]
        adj = V.holm(pv)
        for m in righe:
            if m != RIF:
                righe[m]["vs_ref"]["dm"]["p_holm"] = adj.get(m)
        out["bersagli"].append({"hz": hz, "tipo": kind, "soglia": thr, "n": int(len(d)), "da": str(d.index[0].date()), "a": str(d.index[-1].date()), "modelli": righe})
    # decisione pre-registrata (PROTOCOLLO_VRP.md): «promettente» se Brier tutto a favore su ≥3 dei 5 esiti con Holm < 0,10
    prom = {}
    for m in MODELLI:
        if m == RIF:
            continue
        k = 0
        for b in out["bersagli"]:
            r = b["modelli"].get(m)
            if r and r["vs_ref"]["intero"]["hi"] < 0 and (r["vs_ref"]["dm"].get("p_holm") or 1) < 0.10:
                k += 1
        prom[m] = {"esiti_a_favore": k, "promettente": k >= 3}
    out["promettenti"] = prom
    return out


def protocollo_hash() -> str:
    import hashlib
    from .config import ROOT
    f = ROOT / "PROTOCOLLO_VRP.md"
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:24] if f.exists() else ""


def registra_protocollo() -> str:
    """Impronta del protocollo VRP in data/protocollo_vrp_log.csv (una riga per versione del file)."""
    from datetime import datetime, timezone
    h = protocollo_hash()
    if not h:
        return ""
    f = DATA / "protocollo_vrp_log.csv"
    righe = f.read_text(encoding="utf-8").splitlines() if f.exists() else ["data_utc,impronta"]
    if not any(r.endswith("," + h) for r in righe[1:]):
        righe.append(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},{h}")
        f.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return h


def html() -> str:
    try:
        r = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "<p class='muted'>Esperimento sul premio di volatilità non ancora eseguito (serve apertura, massimo e minimo dell'indice dal 2008).</p>"
    v = r.get("varianza", {})
    nomi = {"VIX": "VIX", "HAR": "HAR (solo prezzi)", "HAR-X": "HAR + VIX", "FHS+VIX+VRP": "VIX meno premio medio"}
    h = ("<p>Esperimento <b>in ombra</b> (non cambia i numeri dell'app): si prova a prevedere meglio la volatilità dei 21 giorni successivi. "
         f"Dati dal {r.get('inizio','')[:4]}, {v.get('_n','?')} date. Più basso l'errore (QLIKE), meglio.</p><table class='tbl'><tr><th>Previsione di volatilità</th><th>Errore</th><th>Rispetto al VIX</th><th>Prev./reale</th></tr>")
    for m in ("VIX", "HAR", "HAR-X", "FHS+VIX+VRP"):
        x = v.get(m)
        if not x:
            continue
        d = x["diff_vs_vix"]
        conf = "—" if m == "VIX" else f"{d['diff']:+.2f} [{d['lo']:+.2f}; {d['hi']:+.2f}], Holm p={(x['p_holm'] if x['p_holm'] is not None else float('nan')):.3f}"
        h += f"<tr><td>{nomi[m]}</td><td>{x['qlike']:.3f}</td><td>{conf}</td><td>{x['rapporto_medio_previsto_realizzato']:.2f}</td></tr>"
    h += "</table><p class='muted'>Prev./reale sopra 1 = il modello sovrastima la volatilità futura (il VIX di solito la sovrastima).</p>"
    pr = [m for m, x in r.get("promettenti", {}).items() if x.get("promettente")]
    h += ("<p><b>Sulle probabilità di calo:</b> " + ("promettenti: " + ", ".join(pr) + "." if pr else "nessun vantaggio dimostrato rispetto a FHS+VIX (regola del protocollo: intervallo tutto a favore su almeno 3 esiti su 5). Resta in ombra.") + "</p>")
    return h


def run(start: str = "2011-01-03", step: int = 5, reps: int = 1000, cache: str | None = None, log=print) -> dict:
    import os
    import pickle
    from .features import closed_sp500
    registra_protocollo()
    p = closed_sp500()
    o, h, l = store.load("sp_open"), store.load("sp_high"), store.load("sp_low")
    if min(len(o), len(h), len(l)) < 1000:
        raise RuntimeError("apertura/massimo/minimo di ^GSPC non disponibili: l'esperimento si rifà quando i dati arrivano")
    x = componenti(o, h, l, p)
    vix = store.load("vix")
    t = tabella(x, vix)
    prev = previsioni_varianza(t)
    dates = p.index[p.index >= start][::step]
    wf = pickle.load(open(cache, "rb")) if cache and os.path.exists(cache) else None
    if wf is None:
        log(f"[vrp] walk-forward su {len(dates)} date, {len(MODELLI)} modelli")
        wf = walk_forward(p, dates, prev, vix)
        if cache:
            pickle.dump(wf, open(cache, "wb"))
    res = valuta(p, dates, wf, prev, t, step, reps)
    res.update({"data": pd.Timestamp.now().strftime("%Y-%m-%d"), "inizio": start, "dati_ohlc_da": INIZIO_DATI,
                "nota": "Esperimento in ombra (PROTOCOLLO_VRP.md). Apertura di ^GSPC inaffidabile prima del 2008 (coincide con la chiusura precedente)."})
    FILE.write_text(json.dumps(res, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    try:
        from . import ricerca
        righe = []
        for b in res["bersagli"]:
            for m, r in b["modelli"].items():
                righe.append({"data": res["data"], "modello": "VRP " + m, "tipo": "vrp1", "obiettivo": f"{b['tipo']}{b['soglia']}_{b['hz']}", "periodo": f"{b['da']}..{b['a']}",
                              "variabili": "ohlc+vix", "n": r["n"], "eventi": r["episodi"]["episodi"], "auc": round(r["auc"], 4) if r["auc"] == r["auc"] else "", "bss": round(r["bss"], 4),
                              "riferimento": RIF, "promosso": bool(res["promettenti"].get(m, {}).get("promettente", False))})
        ricerca._registra(righe)
    except Exception as e:  # noqa: BLE001
        log("[vrp] registro non aggiornato: " + str(e)[:80])
    return res
