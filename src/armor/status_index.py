"""Status index: Crollo, Minimi, Stato. Tre numeri da 1 a 100, stessa scala a colori (fasce 35 / 40 / 60 / 80).

- Crollo: Indice crollo (PROTOCOLLO_INDICE_CROLLO_2.md; versione 2, senza distanza dal massimo).
- Minimi (indice di fase, dal 25/11/2026): alto = il mercato va verso un minimo (discesa in corso, fondo davanti); basso = si allontana dai minimi verso nuovi massimi.
  Modello e misure: fase_minimo.py, PROTOCOLLO_MINIMI_5.md / ESITO_MINIMI_5.md.
- Stato: ex «Terreno fragile» (predisposizione.py): media di dieci percentili di fragilita', resa sulla stessa scala a tratti
  del Crollo (percentile espanso del punteggio, dal 1990). Alto = terreno molto fragile; non dice il giorno.
Ogni indice ha le sue componenti, salvate come serie compatte per i grafici (data/status_index.json).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import indice_crollo as ic
from .config import DATA

FILE = DATA / "status_index.json"
INIZIO = "1990-01-02"
SETTIMANALE_FINO = "2022-12-31"   # componenti: fino al 2022 un punto a settimana (pagina leggera); i tre indici principali sono giornalieri da sempre
ZONE_LIM = [35, 40, 60, 80]
ZONE_COL = ["#22c55e", "#9ca3af", "#f59e0b", "#ef4444", "#8b5cf6"]
NOMI_ZONE = {
    "crollo": ["Nessuna tensione", "Zona di passaggio", "Mercato teso", "Mercato molto teso", "Mercato in panico"],
    "minimi": ["Lontano dai minimi, verso nuovi massimi", "Zona di passaggio", "Possibile discesa in corso", "Verso un minimo", "Discesa in corso, fondo lontano"],
    "stato": ["Terreno solido", "Zona di passaggio", "Terreno fragile", "Terreno molto fragile", "Terreno estremamente fragile"],
}
# componenti: chiave grafico -> (colonna, nome semplice, spiegazione corta)
CROLLO_KIDS = {"cr_paura": ("f1_paura", "paura del mercato"), "cr_curva": ("f3_curva", "paura a breve più alta che a tre mesi"),
               "cr_tend": ("f7_tendenza", "prezzo sotto le sue medie"), "cr_cred": ("f5_credito", "costo del debito delle aziende"),
               "cr_rot": ("f10_rotaz", "fuga dai settori rischiosi"), "cr_tassi": ("f6_tassi", "scosse sui tassi americani")}
MINIMI_PAN: dict = {}   # (vecchia versione: panico e svolta; dal 25/11/2026 il Minimi e' un indice di fase, vedi fase_minimo.py)
MINIMI_SVO = {"mf_rimb": ("mf_rimb", "poco rimbalzo dal minimo"), "mf_dur": ("mf_dur", "pochi giorni dal massimo"), "mf_pend": ("mf_pend", "media a 50 giorni in discesa"),
              "mf_neri": ("mf_neri", "molti giorni neri di recente"), "mf_vol": ("mf_vol", "volatilità ancora vicina al picco")}


def mappa_tratti(punteggio: pd.Series) -> pd.Series:
    """Percentile espanso del punteggio (dal 1990) -> numero da 1 a 100 con la scala a tratti dell'Indice crollo."""
    p = punteggio[punteggio.index >= INIZIO]
    q = p.expanding(min_periods=ic.MIN_STORIA).rank(pct=True)
    out = pd.Series(np.nan, index=q.index)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b)
        out[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return out.clip(1, 100)


def calcola() -> dict:
    """Serie giornaliere di tutto lo Status index e delle sue componenti (indice = DatetimeIndex dal 1990)."""
    from . import predisposizione
    X = ic.calcola_serie()
    ser: dict[str, pd.Series] = {"crollo": X["indice"]}
    for k, (c, _) in CROLLO_KIDS.items():
        ser[k] = X[c]
    try:   # varianti in prova dell'Indice crollo (non sostituiscono quello mostrato)
        from . import crollo_varianti
        ser.update(crollo_varianti.calcola(X))
    except Exception:  # noqa: BLE001
        pass
    from . import fase_minimo
    f = fase_minimo.calcola()
    for k in ("minimi", "mi_modello", "mi_semplice", *fase_minimo.SEGNALI):
        ser[k] = f[k].clip(1, 100)
    comp = predisposizione.componenti(X)
    p = comp.mean(axis=1, skipna=True).where(comp.notna().sum(axis=1) >= 5)
    ser["stato"] = mappa_tratti(p)
    for c in comp.columns:
        ser["st_" + c] = comp[c]
    try:   # Super Armor versione 2 (economia dei prossimi mesi) e le sue misure
        from . import super_armor_2
        ser.update(super_armor_2.calcola())
    except Exception:  # noqa: BLE001
        pass
    return {k: v[v.index >= INIZIO].dropna() for k, v in ser.items()}


def compatta(s: pd.Series, giornaliera: bool = False) -> dict | None:
    """Pagina leggera: un punto a settimana fino al 2022, poi giornaliero. Formato di grafico_indici._serie."""
    from .grafico_indici import _serie
    s = s.dropna()
    if len(s) < 10:
        return None
    if giornaliera:   # i tre indici principali: un punto al giorno da sempre
        return _serie(s)
    vecchio = s[s.index <= SETTIMANALE_FINO]
    vecchio = vecchio.groupby(vecchio.index.to_period("W")).tail(1)
    return _serie(pd.concat([vecchio, s[s.index > SETTIMANALE_FINO]]))


def livello(k: str, v: float) -> int:
    return sum(v > x for x in ZONE_LIM)


def aggiorna(log=print) -> dict:
    ser = calcola()
    out = {"serie": {}, "oggi": {}}
    for k, s in ser.items():
        c = compatta(s, giornaliera=k in ("crollo", "minimi", "stato", "super", "sa_fin", "sa_eco", "sa_costi", "sa_fam", "sa_pil", "sea"))
        if c:
            out["serie"][k] = c
    for k in ("crollo", "minimi", "stato"):
        s = ser[k].dropna()
        v = float(s.iloc[-1]); tr = float(s.iloc[-1] - s.iloc[-6]) if len(s) > 5 else 0.0
        out["oggi"][k] = {"valore": round(v, 1), "tendenza": round(tr, 1), "zona": NOMI_ZONE[k][livello(k, v)], "data": str(s.index[-1].date())}
    if "super" in ser:   # Super Armor v2: valore, tendenza e pilastri di oggi
        x = ser["super"].dropna(); f, e = ser["sa_fin"].dropna(), ser["sa_eco"].dropna()
        out["oggi"]["super"] = {"valore": round(float(x.iloc[-1]), 1), "tendenza": round(float(x.iloc[-1] - x.iloc[-6]), 1), "zona": "", "data": str(x.index[-1].date()),
                                "finanza": round(float(f.iloc[-1]), 1), "economia": round(float(e.iloc[-1]), 1), "sopra60": int((x.tail(5) > 60).sum())}
    if "sea" in ser:   # Salute dell'economia (oggi): valore e tendenza
        y = ser["sea"].dropna()
        out["oggi"]["sea"] = {"valore": round(float(y.iloc[-1]), 1), "tendenza": round(float(y.iloc[-1] - y.iloc[-6]), 1), "zona": "", "data": str(y.index[-1].date())}
    out["data"] = max(x["data"] for x in out["oggi"].values())
    FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log("[status_index] " + " · ".join(f"{k} {x['valore']:.0f}" for k, x in out["oggi"].items()))
    return out


def leggi() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
