# -*- coding: utf-8 -*-
"""«Ribassi lenti: due chiavi» (PROTOCOLLO_CRISI_LENTE_2.md). Nessun parametro stimato: percentili sulla storia dal 1990, minimo e massimo.
Chiave 1 = credito facile E tassi che salgono (minimo tra Boom e Shock). Chiave 2 = stretta del credito. Allarme = massimo tra le due ≥ 80°.
Il primo tentativo (punteggio su storia lunga, PROTOCOLLO_CRISI_LENTE.md) è documentato in ESITO_CRISI_LENTE.md.
File: data/crisi_lente.json (stato), data/crisi_lente_registro.csv (una riga al mese: giudizio in avanti), data/crisi_lente_prova.json (esito delle prove)."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA
from .terreno import pannello_var

FILE = DATA / "crisi_lente.json"
REGISTRO = DATA / "crisi_lente_registro.csv"
PROVA = DATA / "crisi_lente_prova.json"
INIZIO = "1990-01-31"      # il mercato moderno
MIN_MESI = 60
SOGLIA, MODERATA = 0.80, 0.65
# serie: nome -> (id archivio o funzione, ritardo, trasformazione)
SERIE = {
    "prestiti": ("busloans_g6", 1, "lvl"), "debito5a": ("credit_ratio", 5, "d60"), "spread": ("*spread", 1, "lvl"), "sloos": ("sloos", 2, "lvl"), "margin": ("margin_yoy", 2, "lvl"), "m2": ("m2_yoy", 2, "lvl"),
    "t3m": ("tb3ms", 1, "d12"), "t10": ("dgs10", 0, "d12"), "mutui": ("mortgage30", 0, "d12"), "reale": ("real_ff", 1, "lvl"), "infl": ("cpi_yoy_lungo", 1, "lvl"), "curva": ("*curva", 1, "lvl"),
    "sloos_p": ("sloos_piccole", 2, "lvl"), "sloos_c": ("sloos_carte", 2, "lvl"), "nfci": ("nfci_credit", 0, "lvl"), "ins_carte": ("delinq_cc", 5, "lvl"), "ins_mutui": ("delinq_mut", 5, "lvl"),
    "cape": ("cape_m", 0, "lvl"),
}
# gruppo -> [(nome serie, descrizione semplice, inv)]   inv = True: valore basso = più rischio
GRUPPI = {
    "boom": ("Credito facile e abbondante", [("prestiti", "Crescita dei prestiti alle imprese", False), ("debito5a", "Crescita del debito privato in 5 anni", False), ("spread", "Extra-rendimento chiesto alle imprese (basso = tutti tranquilli)", True),
                                              ("sloos", "Banche che stringono i prestiti (poche = credito facile)", True), ("margin", "Debito per comprare titoli", False), ("m2", "Moneta in circolazione", False)]),
    "shock": ("Tassi e inflazione che salgono", [("t3m", "Salita del tasso a 3 mesi in un anno", False), ("t10", "Salita del rendimento a 10 anni in un anno", False), ("mutui", "Salita dei tassi dei mutui in un anno", False),
                                                  ("reale", "Tasso della banca centrale al netto dell'inflazione", False), ("infl", "Inflazione", False), ("curva", "Curva dei rendimenti (invertita = rischio)", True)]),
    "stretta": ("Credito che si restringe", [("sloos", "Banche che stringono i prestiti alle grandi imprese", False), ("sloos_p", "Banche che stringono alle piccole imprese", False), ("sloos_c", "Banche che stringono sulle carte di credito", False),
                                              ("spread", "Extra-rendimento chiesto alle imprese", False), ("nfci", "Condizioni del credito (indice della Fed di Chicago)", False), ("ins_carte", "Carte di credito non pagate", False),
                                              ("ins_mutui", "Mutui non pagati", False), ("prestiti", "Prestiti alle imprese che rallentano", True)]),
}
SPIEGA = {"boom": "Prestiti, debiti e moneta in forte crescita, rischio ignorato: il terreno su cui poi basta una scintilla.",
          "shock": "Tassi, mutui e inflazione che salgono in fretta: è ciò che toglie il credito facile dal mercato.",
          "stretta": "Banche che chiudono i rubinetti e famiglie e imprese che non riescono a pagare."}


def _mensile(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return s.groupby(s.index.to_period("M")).last().rename(lambda p: p.to_timestamp("M"))


def serie_base(serie: dict | None = None) -> dict:
    L = (lambda k: store.load(k).dropna()) if serie is None else (lambda k: serie.get(k, pd.Series(dtype=float)).dropna())
    out = {}
    for n, (sid, lag, tr) in SERIE.items():
        if not sid.startswith("*"):
            out[n] = L(sid)
    out["spread"] = (L("baa_m") - L("aaa_m")).dropna()
    a, b = L("gs10_shiller"), L("gs10_m")
    g10 = pd.concat([a[a.index < b.index[0]], b]).sort_index() if len(b) else a
    out["curva"] = (_mensile(g10) - _mensile(L("tb3ms"))).dropna()
    return out


def pannelli(base: dict, fine) -> pd.DataFrame:
    gr = pd.date_range("1975-01-31", pd.Timestamp(fine) + pd.offsets.MonthEnd(0), freq="ME")
    cols = {}
    for n, (sid, lag, tr) in SERIE.items():
        s = base.get(n, pd.Series(dtype=float))
        if tr == "d60":
            m = pannello_var(s, lag, "lvl", gr); cols[n] = m - m.shift(60)
        else:
            cols[n] = pannello_var(s, lag, tr, gr)
    return pd.DataFrame(cols)


def percentili(P: pd.DataFrame) -> pd.DataFrame:
    """Percentile di ogni mese nella storia dal 1990 fino a quel mese (solo passato, minimo 60 mesi)."""
    P = P.loc[INIZIO:]
    out = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    for c in P.columns:
        v = P[c].values.astype(float); o = np.full(len(v), np.nan)
        for i in range(len(v)):
            h = v[:i + 1]; h = h[np.isfinite(h)]
            if len(h) >= MIN_MESI and np.isfinite(v[i]):
                o[i] = (h <= v[i]).mean()
        out[c] = o
    return out


def punteggi(PC: pd.DataFrame) -> pd.DataFrame:
    """Boom, Shock, Chiave 1, Chiave 2, punteggio: tutti da 0 a 1."""
    res = {}
    for g, (nome, vs) in GRUPPI.items():
        cols = []
        for n, d, inv in vs:
            cols.append(1 - PC[n] if inv else PC[n])
        M = pd.concat(cols, axis=1)
        res[g] = M.mean(axis=1, skipna=True).where(M.notna().sum(axis=1) >= len(vs) / 2)
    R = pd.DataFrame(res)
    R["k1"] = np.minimum(R["boom"], R["shock"])
    R["k2"] = R["stretta"]
    R["score"] = np.fmax(R["k1"], R["k2"]).where(R["k1"].notna() | R["k2"].notna())
    R.loc[R["k1"].isna() & R["k2"].isna(), "score"] = np.nan
    return R


def parola(p) -> tuple[str, str]:
    """Percentile in senso di rischio (0-1)."""
    if p is None or p != p:
        return "dato non disponibile", ""
    if p >= SOGLIA:
        return "in zona di rischio", "b"
    if p >= MODERATA:
        return "sopra la norma", "w"
    if p >= 0.35:
        return "nella norma", ""
    return "tranquillo", "ok"


def calcola(serie: dict | None = None, oggi=None) -> dict:
    oggi = pd.Timestamp(oggi) if oggi is not None else pd.Timestamp.today().normalize()
    chiuso = oggi if oggi == oggi + pd.offsets.MonthEnd(0) else (oggi.to_period("M") - 1).to_timestamp("M")
    P = pannelli(serie_base(serie), chiuso).loc[:chiuso]
    PC = percentili(P); S = punteggi(PC)
    d = S["score"].dropna().index[-1]; r = S.loc[d]
    f = lambda x: None if x != x else float(x)
    gruppi = []
    for g, (nome, vs) in GRUPPI.items():
        pv = []
        for n, desc, inv in vs:
            p = PC.loc[d, n]; rs = None if p != p else float(1 - p if inv else p)
            pv.append({"chiave": n, "nome": desc, "rischio": rs, "testo": parola(rs)[0]})
        v = f(r[g]); t, cl = parola(v)
        gruppi.append({"g": g, "nome": nome, "spiega": SPIEGA[g], "valore": v, "testo": t, "classe": cl, "variabili": pv})
    sc = f(r["score"])
    cape = f(PC.loc[d, "cape"])
    storia = [{"d": str(i.date()), "k1": None if x1 != x1 else round(float(x1), 3), "k2": None if x2 != x2 else round(float(x2), 3)} for i, x1, x2 in zip(S.index, S["k1"], S["k2"]) if i >= pd.Timestamp("1997-01-01")]
    quale = "Credito facile + tassi" if (f(r["k1"]) or 0) >= (f(r["k2"]) or 0) else "Stretta del credito"
    return {"data": str(d.date()), "score": sc, "k1": f(r["k1"]), "k2": f(r["k2"]), "boom": f(r["boom"]), "shock": f(r["shock"]), "stretta": f(r["stretta"]),
            "allarme": bool(sc is not None and sc >= SOGLIA), "moderata": bool(sc is not None and MODERATA <= sc < SOGLIA), "chiave_attiva": quale,
            "soglia": SOGLIA, "gruppi": gruppi, "valutazioni": cape, "storia": storia}


def registra(r: dict, path=None) -> bool:
    path = path or REGISTRO
    cols = ["data", "score", "chiave1", "chiave2", "boom", "shock", "stretta", "allarme"]
    nz = lambda x: "" if x is None else round(x, 4)
    riga = {"data": r["data"], "score": nz(r["score"]), "chiave1": nz(r["k1"]), "chiave2": nz(r["k2"]), "boom": nz(r["boom"]), "shock": nz(r["shock"]), "stretta": nz(r["stretta"]), "allarme": int(r["allarme"])}
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
    log(f"[crisi lente] {r['data']}: punteggio {r['score'] * 100:.0f}° percentile, chiave 1 {r['k1'] * 100:.0f}°, chiave 2 {r['k2'] * 100:.0f}°, allarme {'ACCESO' if r['allarme'] else 'spento'}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
