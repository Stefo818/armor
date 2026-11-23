"""Ricerca libera. Segue PROTOCOLLO_RICERCA_LIBERA.md (nessuna regola cambiata dopo la pubblicazione)."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from armor import store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from elementi_esterni import ORIZZONTI, lag, pct_esp  # noqa: E402
from gara_indici import auc, ic90  # noqa: E402


def main():
    h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
    crollo = ic.calcola_serie()
    sp = store.load("sp500").dropna()
    cal = h.index.intersection(sp.index).intersection(crollo.index)
    spx = sp.loc[cal]
    L = lambda k: store.load(k).dropna()
    ma200 = sp.rolling(200, min_periods=150).mean()
    est = sp / ma200 - 1

    raw = {}
    raw["D01 CAPE"] = L("cape_m")
    raw["D02 P/E"] = L("pe_m")
    raw["D03 Indice Buffett"] = lag(L("buffett") if False else __import__("armor.semafori", fromlist=["x"]).series_of("buffett").dropna(), 90)
    raw["D04 premio al rischio basso"] = -lag(L("erp"), 30)
    raw["D08 nfci livello"] = L("nfci")
    raw["D09 nfci variazione 13 sett"] = L("nfci").diff(13)
    raw["D10 nfci leva"] = L("nfci_leverage")
    raw["D11 stlfsi"] = L("stlfsi")
    raw["D12 kcfsi"] = lag(L("kcfsi"), 35)
    raw["D13 ciss"] = L("ciss")
    raw["D14 salita rendimento 10 anni"] = L("dgs10").diff(63)
    raw["D15 salita rendimento 2 anni"] = L("dgs2").diff(63)
    raw["D16 prosciugamento liquidita"] = -L("net_liq_13w")
    raw["D17 M2 annuo basso"] = -lag(L("m2_yoy"), 45)
    raw["D18 crescita fondi monetari"] = lag(L("mmf_assets").pct_change(13), 7)
    raw["D19 MOVE"] = L("move")
    v3 = L("vix3m")
    raw["D20 VIX su VIX3M"] = (L("vix") / v3.reindex(L("vix").index)).dropna()
    raw["D21 VVIX"] = L("vvix")
    raw["D22 variazione VIX 21 sedute"] = L("vix").diff(21)
    raw["D23 sotto la media 200"] = -est
    raw["D24 momento 10 mesi negativo"] = -(sp / sp.shift(210) - 1)
    raw["D25 rendimento 252 sedute"] = sp.pct_change(252)
    raw["D26 sopra la media 200"] = est
    r = (L("hyg") / L("ief").reindex(L("hyg").index)).dropna()
    raw["D27 HYG/IEF in calo"] = -r.pct_change(63)
    raw["D28 prestiti imprese in calo"] = -lag(L("busloans").pct_change(12), 45)
    raw["D29 stretta SLOOS"] = lag(L("sloos"), 30)
    raw["D30 insoluti imprese"] = lag(L("chargeoff_biz"), 60)

    cand = {}
    for k, s in raw.items():
        s = s.dropna()
        p = pct_esp(s)
        cand[k] = p.reindex(cal.union(p.index)).ffill().reindex(cal)
    below = (-est).clip(lower=0).reindex(cal)
    cand["D05 CAPE x salita rendimento"] = cand["D01 CAPE"] * cand["D14 salita rendimento 10 anni"]
    cand["D06 CAPE x stretta finanziaria"] = cand["D01 CAPE"] * cand["D09 nfci variazione 13 sett"]
    cand["D07 CAPE x sotto media 200"] = cand["D01 CAPE"] * pct_esp(below.dropna()).reindex(cal)
    cand["D31 misto valutazione-condizioni-tassi"] = (cand["D01 CAPE"] + cand["D08 nfci livello"] + cand["D14 salita rendimento 10 anni"]) / 3
    cand["D32 misto volatilita-prezzo-credito"] = (cand["D19 MOVE"] + cand["D23 sotto la media 200"] + cand["D27 HYG/IEF in calo"]) / 3
    cand = dict(sorted(cand.items()))

    base = crollo["indice"].reindex(cal)
    base_p = pct_esp(base).reindex(cal)

    fuori = finestra(cal, ESTERNI)
    for d in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(d))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
    Y = {}
    for ori, (n, soglia) in ORIZZONTI.items():
        mn = pd.concat([spx.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / spx - 1
        yy = (mn <= -soglia).astype(float)
        yy[mn.isna()] = np.nan
        Y[ori] = yy
    sel = (~fuori) & (cal <= "2014-12-31")
    ver = (~fuori) & (cal >= "2015-01-01")

    # copertura: almeno 5 anni validi nel periodo di scelta
    valutabili = {}
    for k, s in cand.items():
        n_ok = int((s[sel].notna()).sum())
        valutabili[k] = n_ok >= 5 * 252 and s[ver].notna().sum() > 300
    nonval = [k for k, v in valutabili.items() if not v]
    cand = {k: s for k, s in cand.items() if valutabili[k]}
    print("non valutabili:", nonval)

    rng = np.random.default_rng(29)
    anni = sorted(set(cal[ver].year))
    migliori = []
    for _ in range(120):
        mappa = dict(zip(anni, rng.permutation(anni)))
        best = 0.0
        for ori in ORIZZONTI:
            yy = Y[ori][ver]
            finto = pd.Series(index=yy.index, dtype=float)
            for a in anni:
                src = yy[yy.index.year == mappa[a]].to_numpy()
                dst = yy.index[yy.index.year == a]
                finto.loc[dst] = np.resize(src, len(dst)) if len(src) else np.nan
            for k, s in cand.items():
                a_ = auc(finto, s[ver])
                if not np.isnan(a_):
                    best = max(best, max(a_, 1 - a_))
        migliori.append(best)
    soglia = float(np.percentile(migliori, 95))
    print(f"soglia del caso ({len(cand)} candidati, 95 pct): {soglia:.4f}")

    out = {"soglia_caso_95": round(soglia, 4), "non_valutabili": nonval, "candidati": {}}
    rk = lambda s: s.rank(pct=True)
    for k, s in cand.items():
        out["candidati"][k] = {}
        for ori in ORIZZONTI:
            a_s, a_v = auc(Y[ori][sel], s[sel]), auc(Y[ori][ver], s[ver])
            if np.isnan(a_v):
                continue
            ic_ = ic90(Y[ori][ver], s[ver])
            p1 = bool(a_v >= 0.60 and ic_ and ic_[0] > 0.50 and a_v > soglia)
            d = {}
            for nome, m in (("sel", sel), ("ver", ver)):
                mm = m & s.notna() & base_p.notna()
                if mm.sum() < 300:
                    d[nome] = None
                    continue
                b_auc = auc(Y[ori][mm], base_p[mm])
                d[nome] = round(float(auc(Y[ori][mm], 0.8 * rk(base_p[mm]) + 0.2 * rk(s[mm])) - b_auc), 4)
            out["candidati"][k][ori] = {"auc_scelta": None if np.isnan(a_s) else round(float(a_s), 4), "auc_verifica": round(float(a_v), 4),
                                        "ic90": ic_, "P1": p1, "dBase_scelta": d["sel"], "dBase_verifica": d["ver"]}
            print(f"{k:40s} {ori:14s} sc {a_s:6.3f} ve {a_v:6.3f} IC {str(ic_):>16s} P1 {'SI' if p1 else '-'} | dB sel {d['sel']} ver {d['ver']}")
    ado = []
    for k, per in out["candidati"].items():
        buoni = cattivi = 0
        for r_ in per.values():
            ds, dv = r_["dBase_scelta"], r_["dBase_verifica"]
            if ds is None or dv is None:
                continue
            buoni += ds >= 0.01 and dv >= 0.01
            cattivi += ds < -0.01 or dv < -0.01
        if buoni >= 2 and cattivi == 0:
            ado.append(k)
    out["P2_adottabili"] = ado
    out["P1_promossi"] = sorted({k for k, per in out["candidati"].items() for r_ in per.values() if r_["P1"]})
    print("\nP1 promossi:", out["P1_promossi"])
    print("P2 adottabili:", ado)

    # secondo controllo per gli adottabili: escludere uno alla volta i 3 anni con piu' episodi (63 sedute)
    y63 = Y["tre mesi"]
    top = [int(a) for a in y63[ver | sel].groupby(y63[ver | sel].index.year).sum().sort_values(ascending=False).index[:3]]
    out["anni_esclusi"] = top
    out["P2_secondo_controllo"] = {}
    for k in ado:
        s = cand[k]
        esiti = {}
        for a in top:
            ok = 0
            for ori in ORIZZONTI:
                dd = []
                for m in (sel, ver):
                    mm = m & s.notna() & base_p.notna() & (cal.year != a)
                    if mm.sum() < 300:
                        dd.append(None); continue
                    b_ = auc(Y[ori][mm], base_p[mm])
                    dd.append(float(auc(Y[ori][mm], 0.8 * rk(base_p[mm]) + 0.2 * rk(s[mm])) - b_))
                if None not in dd and dd[0] >= 0.01 and dd[1] >= 0.01:
                    ok += 1
            esiti[a] = ok
        out["P2_secondo_controllo"][k] = esiti
        print("secondo controllo", k, esiti)
    out["oggi"] = {k: (None if pd.isna(s.iloc[-1]) else round(float(s.iloc[-1]), 3)) for k, s in cand.items()}
    json.dump(out, open("scratch/ricerca_libera.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
