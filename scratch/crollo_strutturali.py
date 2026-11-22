"""Emendamento 2: le dodici famiglie strutturali, provate SOLO entro il 5% dai massimi.

Ipotesi: il settore guida cede mentre l'indice tiene. Costruzione fissata nel protocollo, parte D.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import store  # noqa: E402
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402

SETTORI = ["sec_xlk", "sec_xlf", "sec_xle", "sec_xli", "sec_xlv", "sec_xlp", "sec_xly", "sec_xlb", "sec_xlu"]
NOMI_SET = {"sec_xlk": "tecnologia", "sec_xlf": "finanza", "sec_xle": "energia", "sec_xli": "industria",
            "sec_xlv": "salute", "sec_xlp": "beni di base", "sec_xly": "consumi discrezionali",
            "sec_xlb": "materiali", "sec_xlu": "servizi pubblici"}
MIN_STORIA = 500
NOMI = {
    "g1_divergenza": "il settore guida cede mentre l'indice tiene",
    "g2_ampiezza": "pochi settori sopra la loro media a 200 giorni",
    "g3_tecnologia": "tecnologia tirata rispetto al resto del mercato",
    "g4_valutazione": "valutazioni storicamente alte",
    "g5_premio": "premio per il rischio azionario basso",
    "g6_leva": "debito a margine degli investitori in crescita",
    "g7_credito": "credito alle imprese in espansione o standard allentati",
    "g8_liquidita": "liquidità del sistema in calo",
    "g9_tassi": "tassi reali e curva in movimento",
    "g10_oro": "oro in fuga rispetto alle azioni",
    "g11_insolvenze": "insolvenze delle imprese in peggioramento",
    "g12_guida": "il settore guida smette di guidare",
}


def _pct(s, inv=False):
    r = (-s if inv else s).expanding(min_periods=MIN_STORIA).rank(pct=True) * 100.0
    return r


def _lag(s, giorni):
    out = s.copy()
    out.index = out.index + pd.Timedelta(days=giorni)
    return out


def costruisci():
    sp = store.load("sp500").dropna()
    cal = sp.index

    def g(sid, lag=0):
        s = store.load(sid).dropna()
        if lag:
            s = _lag(s, lag)
        return s.reindex(cal).ffill()

    S = {k: g(k) for k in SETTORI}
    SP = pd.DataFrame(S)
    # settore guida: rendimento relativo a 24 mesi piu' alto (solo passato)
    rel24 = pd.DataFrame({k: (v / v.shift(504)) / (sp / sp.shift(504)) for k, v in S.items()})
    ok = rel24.notna().any(axis=1)
    guida = pd.Series(pd.NA, index=cal, dtype=object)
    guida[ok] = rel24[ok].idxmax(axis=1)

    X = pd.DataFrame(index=cal)
    # 1 divergenza: quanto il settore guida e' sotto il suo massimo a 6 mesi
    mx126 = SP.rolling(126, min_periods=60).max()
    giu = (SP / mx126 - 1)
    X["g1_divergenza"] = _pct(pd.Series([giu.loc[t, guida[t]] if isinstance(guida[t], str) else np.nan for t in cal], index=cal), inv=True)
    # 2 ampiezza: quanti settori sopra la media a 200 giorni
    sopra = sum((SP[k] > SP[k].rolling(200, min_periods=100).mean()).astype(float) for k in SETTORI)
    X["g2_ampiezza"] = _pct(sopra, inv=True)
    # 3 tecnologia contro il resto (dal 1985)
    ndx = g("nasdaq100")
    rap = ndx / sp
    X["g3_tecnologia"] = _pct(rap / rap.rolling(200, min_periods=100).mean() - 1)
    # 4 valutazione: CAPE e prezzo su utili mensili
    X["g4_valutazione"] = (_pct(g("cape_m", 30)) + _pct(g("pe_m", 30))) / 2
    # 5 premio per il rischio (basso = caro)
    X["g5_premio"] = _pct(g("erp", 30), inv=True)
    # 6 leva degli investitori
    X["g6_leva"] = (_pct(g("margin_yoy", 30)) + _pct(g("margin_sp", 30))) / 2
    # 7 credito alle imprese
    X["g7_credito"] = (_pct(g("busloans_g6", 60)) + _pct(g("sloos", 60), inv=True)) / 2
    # 8 liquidita'
    X["g8_liquidita"] = _pct(g("net_liq_13w", 7), inv=True)
    # 9 tassi reali e curva
    r10 = g("real10y", 1)
    cur = g("t10y2y", 1)
    X["g9_tassi"] = (_pct(r10) + _pct(r10 - r10.shift(60)) + _pct(cur, inv=True) + _pct(cur - cur.shift(60), inv=True)) / 4
    # 10 oro contro azioni
    au = g("gold") / sp
    X["g10_oro"] = _pct(au / au.shift(60) - 1)
    # 11 insolvenze delle imprese
    X["g11_insolvenze"] = (_pct(g("delinq_biz", 90).diff(252)) + _pct(g("chargeoff_biz", 90).diff(252))) / 2
    # 12 la guida smette di guidare
    r3 = pd.Series([S[guida[t]][t] / S[guida[t]].shift(63)[t] if isinstance(guida[t], str) else np.nan for t in cal], index=cal)
    X["g12_guida"] = _pct(r3 - sp / sp.shift(63), inv=True)

    X["sp500"] = sp
    X["guida"] = guida
    return X


# episodi finanziari nell'era dei settori (protocollo emendamento 1, tabella B)
EPISODI = {"2000": ("2000-03-24", "2001-04-04"), "2007": ("2007-10-09", "2008-10-27"),
           "2015": ("2015-05-21", "2015-08-24"), "2018": ("2018-01-26", "2018-02-08"),
           "2022": ("2022-01-03", "2022-02-22"), "2026": ("2026-10-06", "2026-11-20")}


def main():
    X = costruisci()
    sp, cal = X["sp500"], X.index
    fam = [c for c in X.columns if c.startswith("g") and c != "guida"]
    picco = sp.rolling(252, min_periods=60).max()
    dd = sp / picco - 1
    fwd = pd.concat([sp.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
    Y = ((fwd / picco - 1) <= -0.10).astype(float)
    Y[fwd.isna()] = np.nan

    fuori = finestra(cal, ESTERNI)
    for d in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(d))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True

    zona = (~fuori) & (dd > -0.05) & Y.notna() & (cal >= "1999-01-01")
    out = {"zona_giorni": int(zona.sum()), "zona_positivi": int(Y[zona].sum()),
           "frequenza_base": round(float(Y[zona].mean()) * 100, 1)}
    print(f"zona entro il 5% dai massimi, sole finanziarie, dal 1999: {int(zona.sum())} giorni, "
          f"{int(Y[zona].sum())} seguiti dal calo al 10% = base {Y[zona].mean()*100:.1f}%")

    # settore guida nel tempo
    print("\nsettore guida negli episodi:")
    for k, (a, b) in EPISODI.items():
        t = pd.Timestamp(a)
        if t in X.index and isinstance(X["guida"][t], str):
            print(f"  {k}: {NOMI_SET[X['guida'][t]]}")
            out.setdefault("guida_episodi", {})[k] = NOMI_SET[X["guida"][t]]

    # --- quale famiglia distingue nella zona (AUC)
    def auc(y, s):
        m = (~pd.isna(y)) & (~pd.isna(s))
        y, s = np.asarray(y)[m], np.asarray(s)[m]
        if len(np.unique(y)) < 2:
            return np.nan
        r = pd.Series(s).rank().to_numpy()
        n1, n0 = y.sum(), (1 - y).sum()
        return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    print("\n=== quale famiglia parla entro il 5% dai massimi ===")
    print(f"{'famiglia':18s} {'giorni':>7s} {'AUC':>7s}   descrizione")
    tab = {}
    for c in fam:
        m = zona & X[c].notna()
        a = auc(Y[m], X[c][m])
        if np.isnan(a):
            continue
        tab[c] = {"giorni": int(m.sum()), "auc": round(float(a), 4)}
        print(f"{c:18s} {int(m.sum()):7d} {a:7.4f}   {NOMI[c]}")
    out["famiglie"] = tab
    print("\nordine per forza del segnale:")
    for c, v in sorted(tab.items(), key=lambda x: -x[1]["auc"]):
        print(f"  {v['auc']:.4f}  {NOMI[c]}")

    X[fam + ["sp500", "guida"]].to_csv("scratch/crollo_strutturali_serie.csv", index_label="date")
    pd.DataFrame({"Y60": Y, "dd": dd, "zona": zona}).to_csv("scratch/crollo_strutturali_y.csv", index_label="date")
    json.dump(out, open("scratch/crollo_strutturali.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato")


if __name__ == "__main__":
    main()
