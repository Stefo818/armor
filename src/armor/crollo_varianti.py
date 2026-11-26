"""Varianti in prova dell'Indice crollo (26/11/2026): stesse fasce e stessi colori, ma costruite in modo diverso. NON sostituiscono l'indice mostrato
(nessuna ha superato tutti i criteri: ESITO_CROLLO_V2MOLT.md, ESITO_CROLLO_V2RAPIDO.md, ESITO_GEMINI_UNIFICATO.md). Qui si calcolano solo per il grafico e il registro.
Percentile espanso dal 2001 (come nei test), poi la stessa scala a tratti del Crollo."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indice_crollo as ic
from . import store

VARIANTI = {   # chiave: (nome, colore, spiegazione)
    "crollo_v2b": ("Formula di Gemini", "#0ea5e9",
                   "Prende l'indice attuale (60%) e lo unisce a tre segnali di anticipo (40%): prezzo allungato rispetto alle sue medie, paura in crescita, protezione contro i cali. Poi lo gonfia quando il mercato è caro, il debito costa di più e il credito è teso. "
                   "Nei crolli recenti (2018-2024) si alza davvero prima del picco (+6,8 punti contro −2,3 dell'attuale) e dà molti meno falsi allarmi (4,9% contro 16,2%). In compenso riconosce un po' peggio i giorni davvero rischiosi (0,77 contro 0,82) e protegge meno dopo l'allarme (0,47 contro 0,60)."),
    "crollo_k3": ("Gemini + indice attuale", "#a855f7",
                  "Media fra la formula di Gemini e l'indice attuale. Nella prova dal 2015 è meglio dell'attuale quasi ovunque (meno falsi allarmi 10,8% contro 16,2%, più protezione 0,65 contro 0,60, distacco prima dei picchi +2,0 contro −2,3), ma non è la variante scelta dalle regole fissate prima: per questo resta solo in prova."),
    "crollo_k4": ("Gemini + attuale + allarme veloce", "#f97316",
                  "Media fra la formula di Gemini, l'indice attuale e l'allarme veloce (paura a breve e instabilità della paura). È la variante vincente fra le quattro mescolanze, ma manca di poco i traguardi (protezione 0,69 contro 0,60 dell'attuale: ne serviva 0,70; distacco prima dei picchi +0,8 contro −2,3: ne servivano +5)."),
    "crollo_rapido": ("Allarme veloce", "#ef4444",
                      "Misura quanto in fretta cresce la paura: salto del VIX, differenza fra paura a 9 giorni e a 1 mese, instabilità della paura, ribassi recenti. Reagisce in pochi giorni dall'inizio di un calo, ma non anticipa. Dal 2011 per alcune parti."),
    "crollo_g1": ("Indice unificato di Gemini", "#14b8a6",
                  "Somma tre parti: terreno (mercato caro, tassi, credito), anticipo e innesco. Si alza bene prima dei crolli recenti e reagisce in circa 3 sedute, ma i suoi colori non separano i giorni rischiosi da quelli tranquilli (anzi, al contrario). Resta in prova."),
}


def _scala(q: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=q.index)
    for a, b, lo, hi in ic.TRATTI:
        m = (q >= a) & (q < b)
        out[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return out.clip(1, 100)


def _pc(s: pd.Series, cal: pd.Index) -> pd.Series:
    s = s.reindex(cal)
    return s[s.index >= "2001-01-01"].expanding(min_periods=252).rank(pct=True).reindex(cal)


def calcola(X: pd.DataFrame | None = None) -> dict[str, pd.Series]:
    X = ic.calcola_serie() if X is None else X
    cal = X.index
    base = X["punteggio"]
    spf = store.load("sp500").dropna()
    spf = spf[~spf.index.duplicated()]
    g = lambda sid, lag=1: ic._lag(store.load(sid).dropna(), lag).reindex(spf.index).ffill()   # noqa: E731
    vix, skew = g("vix"), g("skew")
    s20, s50 = spf / spf.rolling(20).mean() - 1, spf / spf.rolling(50).mean() - 1
    ant = ((ic._pr_mobile((s20 + s50) / 2) + ic._pr_mobile(vix / vix.rolling(60).mean()) + ic._pr_mobile(skew)) / 3).reindex(cal).fillna(50)
    ter = ((ic._pr_mobile(g("cape_m", 31)) + ic._pr_mobile(g("dgs10")) + ic._pr_mobile(g("baa10y"))) / 3).reindex(cal).fillna(50)
    v2b = (0.60 * base + 0.40 * ant) * (0.65 + 0.70 * ter / 100.0)
    pV, pO, pR = _pc(v2b, cal), _pc(base, cal), _pc(ic.punteggio_rapido(), cal)
    out = {"crollo_v2b": pV, "crollo_k3": (pV + pO) / 2, "crollo_k4": (pV + pO + pR) / 3, "crollo_rapido": pR}
    try:
        out["crollo_g1"] = _pc(ic.punteggio_unificato(30000), cal)
    except Exception:  # noqa: BLE001
        pass
    return {k: _scala(q).dropna() for k, q in out.items()}
