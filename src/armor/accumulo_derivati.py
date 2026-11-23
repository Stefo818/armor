"""Indicatori calcolati dai dati grezzi accumulati (23/11/2026): cosi' le ricerche future partono da misure pronte e non da 500 colonne.
- dai 503 titoli dell'S&P 500: ampiezza (quanti titoli sono sopra le medie), nuovi massimi/minimi, concentrazione, dispersione, correlazione media, volume nei titoli in rialzo;
- dalle barre a 5 minuti: ampiezza della giornata, volatilita' realizzata intraday, prima e ultima ora.
Tutte le serie sono ricalcolate dall'inizio a ogni giro (costa pochi secondi) e salvate come d_<nome> (titoli) e di_<strumento>_<misura> (intraday)."""
from __future__ import annotations

import gzip
import io

import numpy as np
import pandas as pd

from . import store
from .config import DATA

BASE = DATA / "componenti"


def carica_componenti() -> tuple[pd.DataFrame, pd.DataFrame]:
    def leggi(prefisso):
        pezzi = []
        for f in sorted(BASE.glob(f"{prefisso}_*.csv.gz")):
            pezzi.append(pd.read_csv(f, index_col=0, parse_dates=True))
        if not pezzi:
            return pd.DataFrame()
        df = pd.concat(pezzi).sort_index()
        return df[~df.index.duplicated(keep="last")]
    return leggi("close"), leggi("vol")


def correlazione_media(R: pd.DataFrame, finestra: int = 21) -> pd.Series:
    """Media delle correlazioni fra tutte le coppie di titoli, su finestre scorrevoli. Alta = i titoli si muovono tutti insieme (come nelle crisi)."""
    X = R.to_numpy(dtype=float)
    out = np.full(len(R), np.nan)
    for i in range(finestra, len(R) + 1):
        w = X[i - finestra:i]
        ok = ~np.isnan(w).any(axis=0)
        if ok.sum() < 50:
            continue
        w = w[:, ok]
        sd = w.std(axis=0)
        ok2 = sd > 0
        if ok2.sum() < 50:
            continue
        c = np.corrcoef(w[:, ok2], rowvar=False)
        n = c.shape[0]
        out[i - 1] = (c.sum() - n) / (n * (n - 1))
    return pd.Series(out, index=R.index)


def indicatori_componenti(P: pd.DataFrame, V: pd.DataFrame | None = None, settori: dict[str, str] | None = None) -> pd.DataFrame:
    P = P.dropna(how="all").sort_index()
    R = P.pct_change(fill_method=None)
    ok = P.notna()
    out = pd.DataFrame(index=P.index)
    for n in (20, 50, 200):
        m = P.rolling(n, min_periods=int(n * 0.9)).mean()
        out[f"d_pct_sopra_{n}"] = ((P > m).where(ok & m.notna()).mean(axis=1) * 100)
    mx = P.rolling(252, min_periods=200).max()
    mn = P.rolling(252, min_periods=200).min()
    out["d_pct_nuovi_massimi_252"] = ((P >= mx).where(mx.notna() & ok).mean(axis=1) * 100)
    out["d_pct_nuovi_minimi_252"] = ((P <= mn).where(mn.notna() & ok).mean(axis=1) * 100)
    out["d_pct_sotto_massimo_20"] = ((P < mx * 0.8).where(mx.notna() & ok).mean(axis=1) * 100)
    out["d_pct_in_rialzo"] = ((R > 0).where(R.notna()).mean(axis=1) * 100)
    out["d_pct_su_5"] = ((R >= 0.05).where(R.notna()).mean(axis=1) * 100)
    out["d_pct_giu_5"] = ((R <= -0.05).where(R.notna()).mean(axis=1) * 100)
    out["d_ritorno_medio"] = R.mean(axis=1) * 100
    out["d_ritorno_mediano"] = R.median(axis=1) * 100
    out["d_dispersione"] = R.std(axis=1) * 100
    out["d_asimmetria_cross"] = R.skew(axis=1)
    ew = R.mean(axis=1)
    out["d_vol_realizzata_21"] = ew.rolling(21, min_periods=15).std() * np.sqrt(252) * 100
    out["d_correlazione_media_21"] = correlazione_media(R, 21)
    out["d_correlazione_media_63"] = correlazione_media(R, 63)
    if V is not None and len(V):
        V = V.reindex(P.index)
        dv = (P * V).where(ok)
        tot = dv.sum(axis=1).replace(0, np.nan)
        top10 = dv.apply(lambda r: r.nlargest(10).sum(), axis=1) if len(dv) < 6000 else None
        out["d_quota_volume_top10"] = top10 / tot * 100
        out["d_quota_volume_in_rialzo"] = dv.where(R > 0).sum(axis=1) / tot * 100
        out["d_volume_dollari_totale"] = tot / 1e9
    if settori:
        s = pd.Series(settori)
        m50 = P.rolling(50, min_periods=45).mean()
        sopra = (P > m50).where(ok & m50.notna())
        for nome, colonne in s.groupby(s).groups.items():
            cols = [c for c in colonne if c in sopra.columns]
            if len(cols) >= 5:
                out["d_pct_sopra_50_" + "".join(ch if ch.isalnum() else "_" for ch in nome.lower()).strip("_")] = sopra[cols].mean(axis=1) * 100
    return out.dropna(how="all")


def aggiorna_derivati_componenti(stato: dict) -> None:
    P, V = carica_componenti()
    if P.empty:
        raise RuntimeError("nessun dato dei componenti")
    sett = {}
    el = BASE / "elenco.csv"
    if el.exists():
        e = pd.read_csv(el)
        e["Symbol"] = e["Symbol"].astype(str).str.replace(".", "-", regex=False)
        sett = dict(zip(e["Symbol"], e["GICS Sector"]))
    ind = indicatori_componenti(P, V, sett)
    n = 0
    for c in ind.columns:
        s = ind[c].dropna()
        if len(s):
            n += store.upsert(c, s.round(4))
    stato["derivati_componenti"] = {"indicatori": len(ind.columns), "giorni": len(ind), "ultimo": str(ind.index[-1].date()), "righe_nuove": n}


# ----------------------------------------------------------------------------- dalle barre a 5 minuti
def misure_giornata(g: pd.DataFrame) -> dict | None:
    g = g.sort_values("ts")
    g = g[g["c"] > 0]
    if len(g) < 12:
        return None
    c = g["c"].to_numpy(dtype=float)
    r = np.diff(np.log(c))
    primo = g["o"].iloc[0] if g["o"].iloc[0] > 0 else c[0]
    k = min(12, len(g) // 3)
    out = {"ampiezza": (g["h"].max() - g["l"].min()) / primo * 100, "vol_realizzata": float(np.sqrt((r ** 2).sum()) * 100),
           "ritorno_giornata": (c[-1] / primo - 1) * 100, "ritorno_prima_ora": (c[k - 1] / primo - 1) * 100, "ritorno_ultima_ora": (c[-1] / c[-k - 1] - 1) * 100,
           "barre": float(len(g))}
    picco = np.maximum.accumulate(c)
    out["calo_massimo_giornata"] = float(((c / picco) - 1).min() * 100)
    v = g["v"].fillna(0).to_numpy(dtype=float)
    if v.sum() > 0:
        out["quota_volume_ultima_ora"] = float(v[-k:].sum() / v.sum() * 100)
    return out


def aggiorna_derivati_intraday(stato: dict) -> None:
    base = DATA / "intraday"
    righe = []
    for f in sorted(base.glob("*/*.csv.gz")):
        giorno = f.stem.replace(".csv", "")
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            df = pd.read_csv(io.StringIO(fh.read()), parse_dates=["ts"])
        for sym, g in df.groupby("sym"):
            m = misure_giornata(g)
            if m:
                righe.append({"data": pd.Timestamp(giorno), "sym": sym, **m})
    if not righe:
        raise RuntimeError("nessuna barra intraday")
    t = pd.DataFrame(righe)
    n = 0
    for sym, g in t.groupby("sym"):
        sl = "".join(ch if ch.isalnum() else "_" for ch in sym.lower()).strip("_")
        # i giorni con poche barre (parziali, weekend degli strumenti non 24 ore) sono gia' scartati; tengo anche la data piu' recente se completa
        for col in g.columns.difference(["data", "sym"]):
            s = g.set_index("data")[col].dropna()
            s = s[~s.index.duplicated(keep="last")]
            if len(s):
                n += store.upsert(f"di_{sl}_{col}", s.round(5))
    stato["derivati_intraday"] = {"strumenti": int(t["sym"].nunique()), "giorni": int(t["data"].nunique()), "righe_nuove": n}
