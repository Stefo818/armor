# -*- coding: utf-8 -*-
"""Super Armor (versione 2, 25/11/2026): come sara' l'economia nei prossimi mesi, mescolando dati finanziari (veloci) ed economici (lenti).
Scelta fatta con 26 alternative e regole scritte prima: PROTOCOLLO_SUPER_ARMOR_ECONOMIA.md / ESITO_SUPER_ARMOR_ECONOMIA.md.

Due pilastri, ognuno la media di percentili storici (solo passato, alto = peggio):
 - finanza (6 misure, peso uguale): curva dei tassi (10 anni - 3 mesi) invertita, spread del credito, spread del credito in 6 mesi,
   condizioni finanziarie, S&P 500 a 12 mesi (invertito), curva 10 anni - 2 anni invertita;
 - economia (7 misure, peso uguale): richieste di sussidio, posti di lavoro, produzione, indice di Chicago, permessi di costruzione, indicatore di Sahm, fiducia dei consumatori.
Il valore e' il PEGGIORE dei due pilastri (il piu' alto), portato su 1-100 come percentile storico. Ritardi di pubblicazione reali."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import store

FIN = {"sf_curva": ("t10y3m", "Curva dei tassi 10 anni - 3 mesi, invertita"), "sf_cred": ("baa10y", "Spread del credito (costo del debito delle aziende)"),
       "sf_cred6": ("baa10y_d6", "Spread del credito: aumento negli ultimi 6 mesi"), "sf_nfci": ("nfci", "Condizioni finanziarie strette"),
       "sf_mom": ("sp_12m", "S&P 500: andamento a 12 mesi, invertito"), "sf_curva2": ("t10y2y", "Curva dei tassi 10 anni - 2 anni, invertita")}
ECO = {"se_sussidi": ("icsa", "Richieste di sussidio di disoccupazione in aumento"), "se_lavoro": ("payems", "Posti di lavoro: crescita debole"),
       "se_prod": ("indpro", "Produzione industriale: crescita debole"), "se_chicago": ("cfnai", "Attività economica nazionale (indice di Chicago) bassa"),
       "se_permessi": ("permit", "Permessi di costruzione in calo"), "se_sahm": ("sahm", "Disoccupazione in aumento (indicatore di Sahm)"),
       "se_fiducia": ("umcsent", "Fiducia dei consumatori in calo")}
NOMI = {"super": "Super Armor", "sa_fin": "Pilastro finanza (veloce)", "sa_eco": "Pilastro economia (lenta)",
        **{k: v[1] for k, v in {**FIN, **ECO}.items()}}
MIN = 1300   # circa 5 anni di giorni di Borsa di storia prima di dare un percentile


def _L(k):
    return store.load(k).dropna()


def calcola() -> dict[str, pd.Series]:
    cal = _L("sp500").index; cal = cal[cal >= "1980-01-01"]

    def asof(s, lag):
        s = s.copy(); s.index = s.index + pd.Timedelta(days=lag); s = s[~s.index.duplicated(keep="last")]
        return s.reindex(s.index.union(cal)).ffill().reindex(cal).where(cal >= s.index[0])
    pe = lambda s: s.expanding(MIN).rank(pct=True) * 100
    ic = _L("icsa"); ic4 = ic.rolling(4).mean(); e1 = ic4 / ic4.rolling(52).min() - 1
    baa = asof(_L("baa10y"), 1); sp = asof(_L("sp500"), 1)
    C = pd.DataFrame(index=cal)
    C["sf_curva"] = pe(-asof(_L("t10y3m"), 1)); C["sf_cred"] = pe(baa); C["sf_cred6"] = pe(baa - baa.shift(126)); C["sf_nfci"] = pe(asof(_L("nfci"), 7))
    C["sf_mom"] = pe(-(sp / sp.shift(252) - 1)); C["sf_curva2"] = pe(-asof(_L("t10y2y"), 1))
    C["se_sussidi"] = pe(asof(e1, 5)); C["se_lavoro"] = pe(-asof(_L("payems").pct_change(3), 37)); C["se_prod"] = pe(-asof(_L("indpro").pct_change(3), 45))
    C["se_chicago"] = pe(-asof(_L("cfnai"), 45)); C["se_permessi"] = pe(-asof(_L("permit").pct_change(6), 45)); C["se_sahm"] = pe(asof(_L("sahm"), 40))
    C["se_fiducia"] = pe(-asof(_L("umcsent").pct_change(6), 20))
    mean = lambda cols: C[cols].mean(axis=1, skipna=True).where(C[cols].notna().sum(axis=1) >= max(2, len(cols) // 2))
    fin, eco = mean(list(FIN)), mean(list(ECO))
    peggiore = pd.concat([fin, eco], axis=1).max(axis=1, skipna=False)
    ser = {"super": 1 + 99 * peggiore.expanding(MIN).rank(pct=True), "sa_fin": fin, "sa_eco": eco}
    for c in C.columns:
        ser[c] = C[c]
    return {k: v.dropna() for k, v in ser.items() if v.dropna().size}
