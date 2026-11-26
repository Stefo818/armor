# -*- coding: utf-8 -*-
"""Registro giornaliero dei valori da misurare in avanti (peso zero, nessuna decisione):
Status index e componenti, correlazione dei settori a 21 sedute e suo calo, stretta di liquidita' e tassi,
fragilita' x innesco, credito che si rovina. Una riga al giorno in data/indizi_registro.csv."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import store
from .config import DATA

REG = DATA / "indizi_registro.csv"


def _ultimo(s: pd.Series | None):
    try:
        s = s.dropna()
        return float(s.iloc[-1]), s
    except Exception:  # noqa: BLE001
        return np.nan, None


def correlazione_settori() -> tuple[float, float]:
    """Correlazione media a coppie dei settori (21 sedute) e «rientra» (calo dal massimo a 63 sedute, scala 0-100)."""
    from . import occasione
    S = occasione.serie_archivio()
    R = pd.DataFrame({k: v.dropna().pct_change() for k, v in S["settori"].items() if len(v)})
    R = R.dropna().iloc[-400:]
    A = R.to_numpy(); vals = []
    for i in range(20, len(R)):
        c = np.corrcoef(A[i - 20:i + 1].T); n = c.shape[0]
        vals.append((c.sum() - n) / (n * (n - 1)))
    C = pd.Series(vals, index=R.index[20:])
    p90 = C.iloc[-63:].max()
    rientra = float(100 * min(max(-(C.iloc[-1] / p90 - 1) / 0.25, 0), 1))
    return float(C.iloc[-1]), rientra


def riga() -> dict:
    from . import status_index
    S = status_index.calcola()
    r: dict = {"data": str(S["crollo"].index[-1].date())}
    for k, v in S.items():
        r[k] = round(float(v.iloc[-1]), 2) if len(v) else np.nan
    c5 = S["crollo"].rolling(5).mean().iloc[-1]
    r["crollo_m5"] = round(float(c5), 2)
    r["stato_x_crollo"] = round(float(c5) / 100 * float(S["stato"].iloc[-1]), 2)
    try:
        r["c21"], r["c21_rientra"] = (round(x, 4) for x in correlazione_settori())
    except Exception:  # noqa: BLE001
        r["c21"] = r["c21_rientra"] = np.nan
    try:   # segnali candidati per il test in avanti (ESITO_RICERCA_10000.md): volatilita' dell'S&P 500 e distanza dal massimo a 20 sedute
        sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()].loc["1990-01-01":]; rr = sp.pct_change()
        for n in (20, 60):
            v = rr.rolling(n).std().dropna(); r[f"vol{n}_sp"] = round(float(v.iloc[-1]) * 100, 3); r[f"vol{n}_sp_pct"] = round(float((v <= v.iloc[-1]).mean()) * 100, 1)
        r["vol_coppia_pct"] = round(r["vol20_sp_pct"] * r["vol60_sp_pct"] / 100, 1); r["dist_max20_sp"] = round(float(sp.iloc[-1] / sp.iloc[-20:].max() - 1) * 100, 2)
        r["segnale_vol_allarme"] = int(r["vol60_sp_pct"] >= 90)
    except Exception:  # noqa: BLE001
        pass
    try:   # candidato «reazione rapida» (ESITO_REAZIONE_RAPIDA.md): solo da misurare in avanti
        from . import indice_crollo as _ic
        pr = _ic.punteggio_rapido().dropna()
        r["crollo_rapido"] = round(float(pr.iloc[-1]), 1)
        r["crollo_rapido_allarme"] = int(float(pr.iloc[-1]) >= _ic.SOGLIA_RAPIDO)
    except Exception:  # noqa: BLE001
        pass
    for nome, chiave in (("nfci", "nfci"), ("liquidita_netta_13s", "net_liq_13w"), ("rend_2anni", "dgs2"), ("rend_10anni", "dgs10"),
                         ("spread_baa", "baa10y"), ("curva_10_2", "t10y2y"),
                         ("mutuo_30_anni", "f_mortgage30us"), ("petrolio_wti", "wti"), ("inflazione_cpi", "cpi"), ("tasso_fed", "fedfunds"), ("debito_famiglie_reddito", "f_tdsp"),
                         ("stretta_credito_famiglie", "f_drtsclcc"), ("carte_insolventi", "f_drcclacbs"), ("mutui_insolventi", "f_drsfrmacbs"), ("credito_consumo", "f_totalsl")):
        try:
            r[nome] = round(_ultimo(store.load(chiave))[0], 4)
        except Exception:  # noqa: BLE001
            r[nome] = np.nan
    # credito che si rovina: spread nel terzo piu' basso della sua storia ma in risalita da un mese
    try:
        v, s = _ultimo(store.load("baa10y"))
        pct = float((s.rank(pct=True)).iloc[-1])
        sal = float(s.iloc[-1] - s.iloc[-22])
        r["credito_pct"] = round(pct * 100, 1); r["credito_var_1m"] = round(sal, 3)
        r["credito_si_rovina"] = int(pct <= 0.40 and sal > 0)
    except Exception:  # noqa: BLE001
        r["credito_pct"] = r["credito_var_1m"] = r["credito_si_rovina"] = np.nan
    return r


def aggiorna(log=print) -> dict:
    r = riga()
    old = pd.read_csv(REG) if REG.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame([r])], ignore_index=True).drop_duplicates(subset=["data"], keep="last").sort_values("data").to_csv(REG, index=False)
    log(f"[indizi_registro] {r['data']}: {len(r) - 1} valori registrati")
    return r
