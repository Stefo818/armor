"""Gara fra Indice Armor, Super Armor e Indice crollo. Segue PROTOCOLLO_GARA_INDICI.md.

81 candidati (3 indici x 9 misure x 3 orizzonti). Scelta sul 1990-2014, verifica sul 2015-2026,
e soglia del caso: quanto vale «la migliore su 81» quando i bersagli sono rumore.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from armor import store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402

INDICI = {"Indice Armor": "armor_tarato", "Super Armor": "super_armor_index", "Indice crollo": "indice_crollo"}
FINESTRE = (5, 21, 63, 126)
ORIZZONTI = {"una settimana": (5, 0.03), "un mese": (21, 0.05), "tre mesi": (63, 0.08)}


def auc(y, s):
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2 or len(y) < 200:
        return np.nan
    r = pd.Series(s).rank().to_numpy()
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def ic90(y, s, giri=600, seed=4):
    d = pd.DataFrame({"y": y, "s": s}).dropna()
    d["anno"] = d.index.year
    anni = sorted(d["anno"].unique())
    per = {a: g for a, g in d.groupby("anno")}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(giri):
        c = pd.concat([per[a] for a in rng.choice(anni, len(anni), replace=True)])
        a = auc(c["y"], c["s"])
        if not np.isnan(a):
            out.append(a)
    return [round(float(np.percentile(out, 5)), 4), round(float(np.percentile(out, 95)), 4)] if len(out) > 50 else None


def main():
    h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
    crollo = ic.calcola_serie()
    sp = store.load("sp500").dropna()
    cal = h.index.intersection(sp.index).intersection(crollo.index)
    h, spx = h.loc[cal], sp.loc[cal]
    base = pd.DataFrame({"armor_tarato": h["armor_tarato"], "super_armor_index": h["super_armor_index"],
                         "indice_crollo": crollo["indice"].reindex(cal)}, index=cal)

    # i 27 candidati
    cand = {}
    for nome, col in INDICI.items():
        s = base[col]
        cand[f"{nome} · livello di oggi"] = s
        for n in FINESTRE:
            cand[f"{nome} · media {n} sedute"] = s.rolling(n, min_periods=max(3, n // 2)).mean()
            cand[f"{nome} · sedute sopra 60 su {n}"] = (s > 60).rolling(n, min_periods=max(3, n // 2)).sum()

    fuori = finestra(cal, ESTERNI)
    for d in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(d))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True

    Y = {}
    for ori, (n, soglia) in ORIZZONTI.items():
        mn = pd.concat([spx.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / spx - 1
        y = (mn <= -soglia).astype(float)
        y[mn.isna()] = np.nan
        Y[ori] = y

    sel = (~fuori) & (cal <= "2014-12-31")
    ver = (~fuori) & (cal >= "2015-01-01")
    out = {"orizzonti": {}}
    print(f"scelta: {int(sel.sum())} giorni · verifica: {int(ver.sum())} giorni (sole crisi finanziarie)")
    for ori in ORIZZONTI:
        print(f"   base «{ori}»: scelta {Y[ori][sel].mean()*100:.1f}%  verifica {Y[ori][ver].mean()*100:.1f}%")

    # --- soglia del caso: la migliore su 81 quando i bersagli sono mescolati a blocchi di un anno
    print("\n=== quanto vale «la migliore su 81» per puro caso ===")
    rng = np.random.default_rng(17)
    anni = sorted(set(cal[ver].year))
    migliori = []
    for _ in range(120):
        ordine = rng.permutation(anni)
        mappa = dict(zip(anni, ordine))
        best = 0.0
        for ori in ORIZZONTI:
            yy = Y[ori][ver]
            # bersaglio di un anno attaccato a un altro anno: rompe il legame senza rompere la struttura
            finto = pd.Series(index=yy.index, dtype=float)
            for a in anni:
                src = yy[yy.index.year == mappa[a]].to_numpy()
                dst = yy.index[yy.index.year == a]
                finto.loc[dst] = np.resize(src, len(dst)) if len(src) else np.nan
            for nome, s in cand.items():
                a_ = auc(finto, s[ver])
                if not np.isnan(a_):
                    best = max(best, max(a_, 1 - a_))
        migliori.append(best)
    soglia_caso = float(np.percentile(migliori, 95))
    out["soglia_caso_95"] = round(soglia_caso, 4)
    print(f"   95° percentile della migliore su 81 sotto rumore: {soglia_caso:.4f}")
    print(f"   (mediana {np.median(migliori):.4f}) — un candidato deve battere {soglia_caso:.4f} per contare")

    # --- la gara
    for ori, (n, soglia) in ORIZZONTI.items():
        righe = []
        for nome, s in cand.items():
            a_sel = auc(Y[ori][sel], s[sel])
            a_ver = auc(Y[ori][ver], s[ver])
            if np.isnan(a_sel) or np.isnan(a_ver):
                continue
            righe.append({"candidato": nome, "auc_scelta": round(float(a_sel), 4), "auc_verifica": round(float(a_ver), 4)})
        righe.sort(key=lambda x: -x["auc_scelta"])
        vinc = righe[0]
        m = ver & cand[vinc["candidato"]].notna()
        sv = cand[vinc["candidato"]][m]
        q = sv.quantile(0.8)
        prec = float(Y[ori][m & (cand[vinc["candidato"]] >= q)].mean()) * 100
        b = float(Y[ori][ver].mean()) * 100
        vinc["ic90_verifica"] = ic90(Y[ori][ver], cand[vinc["candidato"]][ver])
        vinc["precisione_quinto"] = round(prec, 1)
        vinc["base"] = round(b, 1)
        vinc["G1"] = bool(vinc["auc_verifica"] >= 0.60 and (vinc["ic90_verifica"] or [0])[0] > 0.50)
        vinc["G2"] = bool(vinc["auc_verifica"] > soglia_caso)
        vinc["G3"] = bool(prec >= 2 * b)
        vinc["promosso"] = bool(vinc["G1"] and vinc["G2"] and vinc["G3"])
        out["orizzonti"][ori] = {"vincitore": vinc, "classifica_scelta": righe[:8]}
        print(f"\n=== {ori} (base nella verifica {b:.1f}%) ===")
        print(f"{'candidato':44s} {'scelta':>8s} {'verifica':>9s}")
        for r in righe[:8]:
            print(f"{r['candidato']:44s} {r['auc_scelta']:8.4f} {r['auc_verifica']:9.4f}")
        print(f"  vincitore: {vinc['candidato']}  verifica {vinc['auc_verifica']:.4f} IC90 {vinc['ic90_verifica']}")
        print(f"  quinto più alto {prec:.1f}% contro base {b:.1f}%  |  G1 {vinc['G1']} G2 {vinc['G2']} G3 {vinc['G3']} -> {'PROMOSSO' if vinc['promosso'] else 'non promosso'}")

    json.dump(out, open("scratch/gara_indici.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato scratch/gara_indici.json")


if __name__ == "__main__":
    main()
