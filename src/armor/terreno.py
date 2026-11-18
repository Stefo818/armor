# -*- coding: utf-8 -*-
"""«Terreno»: pressioni lente su credito, famiglie, rendimenti alternativi, flussi e imprese (PROTOCOLLO_TERRENO.md).
Esito delle prove: NON previsivo (alla conferma 2010-2026 ha fallito). Qui è solo una scheda informativa, a peso zero. File: data/terreno.json."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "terreno.json"
REGISTRO = DATA / "terreno_registro.csv"   # una riga per mese: serve al giudizio futuro (si confronta con i cali veri dopo 6 e 12 mesi)
GRUPPI = {"A": "Credito", "B": "Famiglie", "C": "Alternative sicure", "D": "Flussi e liquidità", "E": "Imprese"}
SPIEGA = {"A": "Quanto è difficile ottenere un prestito e quanto costa il rischio di credito.",
          "B": "Quante famiglie fanno fatica con carte, mutui e debiti, e quanto riescono a risparmiare.",
          "C": "Quanto rendono i titoli di Stato rispetto alle azioni: se rendono molto, i soldi hanno alternative sicure.",
          "D": "Quanto debito serve per comprare titoli, quanta moneta circola e quanti soldi vanno nei fondi monetari.",
          "E": "Quante imprese non restituiscono i prestiti alle banche."}
# chiave archivio -> (nome semplice, segno (+1: valore alto = terreno più fragile), ritardo in mesi, trasformazione, gruppo)
VARS = {
    "sloos": ("Banche che stringono i prestiti alle grandi imprese", +1, 2, "lvl", "A"),
    "sloos_piccole": ("Banche che stringono i prestiti alle piccole imprese", +1, 2, "lvl", "A"),
    "sloos_carte": ("Banche che stringono sulle carte di credito", +1, 2, "lvl", "A"),
    "baa10y": ("Extra-rendimento chiesto alle imprese di qualità media", +1, 0, "lvl", "A"),
    "nfci_credit": ("Condizioni del credito (indice della Fed di Chicago)", +1, 0, "lvl", "A"),
    "busloans_g6": ("Crescita dei prestiti alle imprese (6 mesi)", -1, 1, "lvl", "A"),
    "delinq_cc": ("Carte di credito non pagate", +1, 5, "lvl", "B"),
    "delinq_mut": ("Mutui non pagati", +1, 5, "lvl", "B"),
    "tdsp": ("Quota del reddito che va a pagare debiti", +1, 6, "lvl", "B"),
    "psavert": ("Risparmio sul reddito", -1, 2, "lvl", "B"),
    "mortgage30": ("Tasso dei mutui (variazione in 12 mesi)", +1, 0, "d12", "B"),
    "real_ff": ("Tasso della banca centrale al netto dell'inflazione", +1, 1, "lvl", "C"),
    "erp": ("Premio delle azioni sui titoli di Stato", -1, 1, "lvl", "C"),
    "dgs10": ("Rendimento a 10 anni (variazione in 12 mesi)", +1, 0, "d12", "C"),
    "t10y3m": ("Curva dei rendimenti 10 anni meno 3 mesi", -1, 0, "lvl", "C"),
    "margin_yoy": ("Debito per comprare titoli (variazione annua)", +1, 2, "lvl", "D"),
    "m2_yoy": ("Moneta in circolazione (variazione annua)", -1, 2, "lvl", "D"),
    "mmf_assets": ("Soldi nei fondi monetari (crescita in 12 mesi)", +1, 1, "g12", "D"),
    "net_liq_13w": ("Liquidità netta del sistema (13 settimane)", -1, 0, "lvl", "D"),
    "delinq_biz": ("Prestiti alle imprese non restituiti", +1, 5, "lvl", "E"),
    "chargeoff_biz": ("Perdite sui prestiti alle imprese", +1, 5, "lvl", "E"),
}
# serie nuove prese da FRED (chiave archivio -> codice)
FRED_NUOVE = {"sloos_piccole": "DRTSCIS", "sloos_carte": "DRTSCLCC", "delinq_mut": "DRSFRMACBS", "tdsp": "TDSP", "psavert": "PSAVERT", "mortgage30": "MORTGAGE30US"}
MIN_MESI = 48


def scarica(log=print) -> int:
    """Aggiorna le serie nuove (se FRED non risponde resta l'ultimo dato salvato)."""
    from . import sources
    n = 0
    for k, code in FRED_NUOVE.items():
        try:
            n += store.upsert(k, sources.fetch_fred(code))
        except Exception as e:  # noqa: BLE001
            log(f"[terreno] {k} non aggiornata: {str(e)[:60]}")
    return n


def _griglia(fine) -> pd.DatetimeIndex:
    return pd.date_range("1975-01-31", pd.Timestamp(fine) + pd.offsets.MonthEnd(0), freq="ME")


def pannello_var(s: pd.Series, lag: int, tr: str, griglia: pd.DatetimeIndex) -> pd.Series:
    """Serie mensile «come era nota» a ogni fine mese: ritardo di pubblicazione, poi ultimo valore noto."""
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if s.empty:
        return pd.Series(np.nan, index=griglia)
    av = s.copy()
    av.index = (s.index + pd.DateOffset(months=lag)) if lag else s.index
    av = av[~av.index.duplicated(keep="last")].sort_index()
    m = av.reindex(av.index.union(griglia)).ffill().reindex(griglia)
    m[m.index < av.index[0]] = np.nan
    if tr == "d12":
        m = m - m.shift(12)
    elif tr == "g12":
        m = m / m.shift(12) - 1
    return m


def zscore(m: pd.Series, minp: int = MIN_MESI) -> pd.Series:
    """Standardizzazione sul solo passato (media e deviazione espandibili)."""
    mu, sd = m.expanding(minp).mean(), m.expanding(minp).std()
    return ((m - mu) / sd.replace(0, np.nan)).clip(-4, 4)


def costruisci(panels: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    Z = pd.DataFrame({k: zscore(v) * VARS[k][1] for k, v in panels.items()})
    G = pd.DataFrame({g: Z[[k for k in Z.columns if VARS[k][4] == g]].mean(axis=1, skipna=True) for g in GRUPPI})
    T = G.mean(axis=1, skipna=True).where(G.notna().sum(axis=1) >= 3)
    return Z, G, T


def parola(z) -> tuple[str, str]:
    """(testo semplice, classe colore) per un punteggio: 0 = situazione tipica, +1 = una deviazione sopra la norma."""
    if z is None or z != z:
        return "dato non disponibile", ""
    if z >= 1.0:
        return "sotto forte pressione", "b"
    if z >= 0.4:
        return "un po' sopra la norma", "w"
    if z > -0.4:
        return "nella norma", ""
    return "più tranquillo del solito", "ok"


def calcola(serie: dict | None = None, oggi=None) -> dict:
    oggi = pd.Timestamp(oggi) if oggi is not None else pd.Timestamp.today().normalize()
    gr = _griglia(oggi)
    serie = serie if serie is not None else {k: store.load(k) for k in VARS}
    panels = {k: pannello_var(serie.get(k, pd.Series(dtype=float)), lag, tr, gr) for k, (_, sg, lag, tr, g) in VARS.items()}
    Z, G, T = costruisci(panels)
    # mese in corso: si usa l'ultimo mese chiuso (nessun dato dal futuro)
    chiuso = oggi if oggi == oggi + pd.offsets.MonthEnd(0) else (oggi.to_period("M") - 1).to_timestamp("M")
    riga = T.loc[:chiuso].dropna()
    d = riga.index[-1]
    storia = T[T.index >= "1994-01-01"].dropna()
    perc = float((storia <= riga.iloc[-1]).mean() * 100)
    gruppi = []
    for g, nome in GRUPPI.items():
        z = float(G.loc[d, g]) if np.isfinite(G.loc[d, g]) else None
        txt, cl = parola(z)
        vs = []
        for k, (n, sg, lag, tr, gg) in VARS.items():
            if gg != g:
                continue
            zk = float(Z.loc[d, k]) if np.isfinite(Z.loc[d, k]) else None
            vs.append({"chiave": k, "nome": n, "z": zk, "testo": parola(zk)[0]})
        gruppi.append({"g": g, "nome": nome, "spiega": SPIEGA[g], "z": z, "testo": txt, "classe": cl, "variabili": vs})
    serie_t = [{"d": str(i.date()), "v": round(float(v), 3)} for i, v in storia[storia.index >= "2000-01-01"].items()]
    return {"data": str(d.date()), "terreno": float(riga.iloc[-1]), "percentile": perc, "testo": parola(float(riga.iloc[-1]))[0], "classe": parola(float(riga.iloc[-1]))[1],
            "gruppi": gruppi, "storia": serie_t[::3],
            "prova": {"stato": "non utile", "taratura_auc": {"6 mesi": None, "12 mesi": None}, "conferma_auc": {"6 mesi": None, "12 mesi": None}}}


def registra(r: dict, path=None) -> bool:
    """Aggiunge la riga del mese se manca (una sola per mese). Restituisce True se ha scritto."""
    path = path or REGISTRO
    cols = ["data", "terreno"] + list(GRUPPI)
    riga = {"data": r["data"], "terreno": round(r["terreno"], 4), **{g["g"]: ("" if g["z"] is None else round(g["z"], 4)) for g in r["gruppi"]}}
    try:
        df = pd.read_csv(path)
    except Exception:  # noqa: BLE001
        df = pd.DataFrame(columns=cols)
    if (df["data"].astype(str) == riga["data"]).any():
        return False
    pd.concat([df, pd.DataFrame([riga])], ignore_index=True)[cols].to_csv(path, index=False)
    return True


def aggiorna(log=print) -> dict:
    scarica(log)
    r = calcola()
    try:   # esito delle prove (scratch/terreno_risultati.json), se presente
        p = json.loads((DATA / "terreno_prova.json").read_text(encoding="utf-8"))
        r["prova"] = p
    except Exception:  # noqa: BLE001
        pass
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    registra(r)
    log(f"[terreno] {r['data']}: {r['terreno']:+.2f} ({r['testo']}), {r['percentile']:.0f}° percentile dal 1994")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
