# -*- coding: utf-8 -*-
"""«Crisi lente» (PROTOCOLLO_CRISI_LENTE.md): quanto il terreno somiglia a quello che ha preceduto i crolli senza recupero in 4 anni (1929, 1937, 1973, 2000, 2007).
Punteggio da 4 gruppi (valutazioni, credito, liquidità e tassi, economia), allarme sopra l'80° percentile della propria storia. Esito delle prove: vedi ESITO_CRISI_LENTE.md.
File: data/crisi_lente.json (stato) e data/crisi_lente_registro.csv (una riga al mese, per il giudizio in avanti)."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA
from .terreno import pannello_var, zscore

FILE = DATA / "crisi_lente.json"
REGISTRO = DATA / "crisi_lente_registro.csv"
PROVA = DATA / "crisi_lente_prova.json"
GRUPPI = {"V": "Valutazioni", "K": "Credito", "L": "Liquidità e tassi", "M": "Economia"}
SPIEGA = {"V": "Quanto costano le azioni rispetto agli utili medi degli ultimi 10 anni. Prezzi molto alti rendono più lunghi i recuperi.",
          "K": "Quanto è caro il rischio di credito e quanto sta crescendo il debito di famiglie e imprese.",
          "L": "Tassi, curva dei rendimenti e moneta in circolazione: quanto è tirata la liquidità.",
          "M": "Produzione, lavoro e inflazione: se l'economia reale è in sofferenza."}
SOGLIA = 0.80
# nome: (descrizione semplice, segno (+1: valore alto = più rischio), ritardo in mesi, trasformazione, gruppo)
VARS = {
    "cape": ("Prezzo delle azioni rispetto agli utili di 10 anni", +1, 0, "lvl", "V"),
    "spread_baa_aaa": ("Extra-rendimento chiesto alle imprese meno solide", +1, 1, "lvl", "K"),
    "prestiti_imprese_g6": ("Crescita dei prestiti alle imprese (6 mesi)", -1, 1, "lvl", "K"),
    "debito_privato_5a": ("Crescita del debito privato in 5 anni", +1, 5, "d60", "K"),
    "tasso3m_var12": ("Variazione del tasso a 3 mesi in un anno", +1, 1, "d12", "L"),
    "curva_10a_3m": ("Curva dei rendimenti 10 anni meno 3 mesi", -1, 1, "lvl", "L"),
    "m2_yoy": ("Moneta in circolazione (variazione annua)", -1, 2, "lvl", "L"),
    "tasso_reale": ("Tasso della banca centrale al netto dell'inflazione", +1, 1, "lvl", "L"),
    "produzione_g12": ("Produzione industriale (variazione annua)", -1, 1, "lvl", "M"),
    "disoccupazione_var12": ("Variazione della disoccupazione in un anno", +1, 1, "d12", "M"),
    "inflazione": ("Inflazione annua", +1, 1, "lvl", "M"),
}
CHIAVI = {"cape": "cape_m", "spread_baa_aaa": None, "prestiti_imprese_g6": "busloans_g6", "debito_privato_5a": "credit_ratio", "tasso3m_var12": "tb3ms", "curva_10a_3m": None,
          "m2_yoy": "m2_yoy", "tasso_reale": "real_ff", "produzione_g12": "indpro_g12", "disoccupazione_var12": "unrate", "inflazione": "cpi_yoy_lungo"}


def _mensile(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return s.groupby(s.index.to_period("M")).last().rename(lambda p: p.to_timestamp("M"))


def serie_base(serie: dict | None = None) -> dict:
    """Le 11 serie grezze (dall'archivio, o passate dal test)."""
    L = (lambda k: store.load(k).dropna()) if serie is None else (lambda k: serie.get(k, pd.Series(dtype=float)).dropna())
    out = {}
    for k, c in CHIAVI.items():
        if c:
            out[k] = np.log(L(c)) if k == "cape" else L(c)
    out["spread_baa_aaa"] = (L("baa_m") - L("aaa_m")).dropna()
    a, b = L("gs10_shiller"), L("gs10_m")
    g10 = pd.concat([a[a.index < b.index[0]], b]).sort_index() if len(b) else a
    out["curva_10a_3m"] = (_mensile(g10) - _mensile(L("tb3ms"))).dropna()
    return out


def punteggio(base: dict, fine) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    gr = pd.date_range("1914-01-31", pd.Timestamp(fine) + pd.offsets.MonthEnd(0), freq="ME")
    panels = {}
    for k, (_, sg, lag, tr, g) in VARS.items():
        s = base.get(k, pd.Series(dtype=float))
        if tr == "d60":
            m = pannello_var(s, lag, "lvl", gr)
            panels[k] = m - m.shift(60)
        else:
            panels[k] = pannello_var(s, lag, tr, gr)
    Z = pd.DataFrame({k: zscore(v) * VARS[k][1] for k, v in panels.items()})
    G = pd.DataFrame({g: Z[[k for k in Z.columns if VARS[k][4] == g]].mean(axis=1, skipna=True) for g in GRUPPI})
    T = G.mean(axis=1, skipna=True).where(G.notna().sum(axis=1) >= 3)
    return Z, G, T


def percentile_espandibile(T: pd.Series, minn: int = 120) -> pd.Series:
    """Posizione di ogni mese nella storia nota fino a quel mese (0-1). Solo passato."""
    v = T.values.astype(float); out = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[:i + 1]; h = h[np.isfinite(h)]
        if len(h) >= minn and np.isfinite(v[i]):
            out[i] = (h <= v[i]).mean()
    return pd.Series(out, index=T.index)


def parola(g: str, z) -> tuple[str, str]:
    if z is None or z != z:
        return "dato non disponibile", ""
    if g == "V":
        return (("molto care", "b") if z >= 1.0 else ("care", "w") if z >= 0.4 else ("nella norma", "") if z > -0.4 else ("a prezzi bassi", "ok"))
    return (("sotto forte pressione", "b") if z >= 1.0 else ("un po' sopra la norma", "w") if z >= 0.4 else ("nella norma", "") if z > -0.4 else ("più tranquillo del solito", "ok"))


def calcola(serie: dict | None = None, oggi=None) -> dict:
    oggi = pd.Timestamp(oggi) if oggi is not None else pd.Timestamp.today().normalize()
    chiuso = oggi if oggi == oggi + pd.offsets.MonthEnd(0) else (oggi.to_period("M") - 1).to_timestamp("M")
    Z, G, T = punteggio(serie_base(serie), chiuso)
    T = T.loc[:chiuso]
    d = T.dropna().index[-1]
    P = percentile_espandibile(T.loc["1950-01-01":] if False else T)
    pc = float(P.loc[d]) if np.isfinite(P.loc[d]) else None
    gruppi = []
    for g, nome in GRUPPI.items():
        z = float(G.loc[d, g]) if np.isfinite(G.loc[d, g]) else None
        txt, cl = parola(g, z)
        vs = []
        for k, (n, sg, lag, tr, gg) in VARS.items():
            if gg == g:
                zk = float(Z.loc[d, k]) if np.isfinite(Z.loc[d, k]) else None
                vs.append({"chiave": k, "nome": n, "z": zk, "testo": parola(g, zk)[0]})
        gruppi.append({"g": g, "nome": nome, "spiega": SPIEGA[g], "z": z, "testo": txt, "classe": cl, "variabili": vs})
    st = P[P.index >= "1953-01-01"].dropna()
    storia = [{"d": str(i.date()), "v": round(float(v), 3)} for i, v in st.items()][::3]
    return {"data": str(d.date()), "terreno": float(T.loc[d]), "percentile": None if pc is None else pc * 100, "allarme": bool(pc is not None and pc >= SOGLIA),
            "soglia": SOGLIA * 100, "gruppi": gruppi, "storia": storia}


def registra(r: dict, path=None) -> bool:
    path = path or REGISTRO
    cols = ["data", "terreno", "percentile", "allarme"] + list(GRUPPI)
    riga = {"data": r["data"], "terreno": round(r["terreno"], 4), "percentile": "" if r["percentile"] is None else round(r["percentile"], 1), "allarme": int(r["allarme"]),
            **{g["g"]: ("" if g["z"] is None else round(g["z"], 4)) for g in r["gruppi"]}}
    try:
        df = pd.read_csv(path)
    except Exception:  # noqa: BLE001
        df = pd.DataFrame(columns=cols)
    if (df["data"].astype(str) == riga["data"]).any():
        return False
    pd.concat([df, pd.DataFrame([riga])], ignore_index=True)[cols].to_csv(path, index=False)
    return True


def aggiorna(log=print) -> dict:
    r = calcola()
    try:
        r["prova"] = json.loads(PROVA.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        r["prova"] = {}
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    registra(r)
    log(f"[crisi lente] {r['data']}: {r['percentile']:.0f}° percentile, allarme {'ACCESO' if r['allarme'] else 'spento'}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
