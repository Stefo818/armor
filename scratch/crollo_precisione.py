"""La differenza fra due numeri che vengono spesso confusi, e che cambia tutto.

Sensibilita': quando c'e' stato un crollo, quante volte l'indice era in allarme? (fa sembrare bravo il modello)
Precisione: quando l'indice era in allarme, quante volte e' poi arrivato il crollo? (quello che serve per decidere)
Solo crisi finanziarie, secondo l'emendamento 1 del protocollo.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from crollo_ricerca import PESI_M2, bersagli, carica, mappa_indice  # noqa: E402


def main():
    X = carica()
    d = X.join(bersagli(X["sp500"]))
    d = d[d.index >= "1990-01-02"]
    cal, sp = d.index, d["sp500"]
    w = pd.Series(PESI_M2) / pd.Series(PESI_M2).sum()
    idx = mappa_indice(sum(d[c].fillna(50.0) * w[c] for c in w.index))

    fuori = finestra(cal, ESTERNI)
    for dd in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(dd))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True

    picco = sp.rolling(252, min_periods=60).max()
    dd_ora = sp / picco - 1
    # il calo arriva almeno al 10% dal massimo entro 60 sedute?
    fwd_min = pd.concat([sp.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
    arriva10 = ((fwd_min / picco - 1) <= -0.10).astype(float)
    arriva10[fwd_min.isna()] = np.nan

    ok = (~fuori) & arriva10.notna() & idx.notna()
    out = {"nota": "Solo crisi finanziarie. 'arriva al -10%' = il minimo delle 60 sedute successive sta almeno il 10% sotto il massimo a 12 mesi."}

    print("=== PRECISIONE: dopo un allarme, quante volte e' arrivato il calo del 10%? ===")
    print(f"{'situazione':46s} {'giorni':>7s} {'poi -10%':>9s} {'precisione':>11s}")
    righe = {}
    for nome, m in (
        ("mercato entro -2% dal massimo, indice verde/grigio", ok & (dd_ora > -0.02) & (idx < 41)),
        ("mercato entro -2% dal massimo, indice giallo o peggio", ok & (dd_ora > -0.02) & (idx >= 41)),
        ("mercato fra -2% e -7%, indice verde/grigio", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx < 41)),
        ("mercato fra -2% e -7%, indice giallo (41-60)", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx >= 41) & (idx <= 60)),
        ("mercato fra -2% e -7%, indice rosso o viola (61+)", ok & (dd_ora <= -0.02) & (dd_ora > -0.07) & (idx > 60)),
        ("tutti i giorni, indice giallo o peggio", ok & (idx >= 41)),
        ("tutti i giorni, indice verde", ok & (idx <= 35)),
        ("tutti i giorni (riferimento)", ok),
    ):
        y = arriva10[m]
        if len(y) < 20:
            continue
        p = float(y.mean())
        # intervallo al 90%: bootstrap a blocchi di 21 sedute
        a = y.to_numpy()
        rng = np.random.default_rng(5)
        bs = [a[np.concatenate([np.arange(x, min(x + 21, len(a))) for x in rng.integers(0, max(1, len(a) - 21), max(2, len(a) // 21))])].mean() for _ in range(800)]
        righe[nome] = {"giorni": int(len(y)), "poi_meno10": int(y.sum()), "precisione": round(p * 100, 1),
                       "ic90": [round(float(np.percentile(bs, 5)) * 100, 1), round(float(np.percentile(bs, 95)) * 100, 1)]}
        print(f"{nome:46s} {len(y):7d} {int(y.sum()):9d} {p*100:9.1f}%  IC90 {righe[nome]['ic90']}")
    out["precisione"] = righe

    print("\n=== SENSIBILITA' (il numero che inganna) ===")
    # fra i giorni che poi hanno visto il -10%, quanti erano gia' in allarme?
    cro = ok & (arriva10 == 1)
    s_gi = float((idx[cro] >= 41).mean())
    out["sensibilita_giallo"] = round(s_gi * 100, 1)
    print(f"fra i giorni seguiti dal calo al 10%, l'indice era giallo o peggio nel {s_gi*100:.1f}% dei casi")
    print(f"ma dopo un giallo il calo e' arrivato solo nel {righe['tutti i giorni, indice giallo o peggio']['precisione']}% dei casi")

    # quanti giorni di allarme per ogni crollo vero
    na = int((ok & (idx >= 41)).sum())
    nc = int((ok & (idx >= 41) & (arriva10 == 1)).sum())
    out["giorni_allarme_per_crollo"] = round(na / max(1, nc), 1)
    print(f"\nin media {na/max(1,nc):.1f} giorni di allarme per ogni giorno di allarme seguito davvero dal calo")

    # falsi allarmi raggruppati in episodi
    al = (ok & (idx >= 41)).astype(int)
    grp = (al.diff() != 0).cumsum()[al == 1]
    epis = []
    for g, blocco in al[al == 1].groupby(grp):
        t0, t1 = blocco.index[0], blocco.index[-1]
        vero = bool(arriva10[t0:t1].max() == 1)
        epis.append({"da": str(t0.date()), "a": str(t1.date()), "sedute": int(len(blocco)), "poi_meno10": vero})
    out["episodi_di_allarme"] = {"totale": len(epis), "veri": sum(1 for e in epis if e["poi_meno10"]),
                                 "falsi": sum(1 for e in epis if not e["poi_meno10"])}
    print(f"episodi di allarme distinti dal 1990 (solo finanziarie): {len(epis)}, "
          f"seguiti dal calo {out['episodi_di_allarme']['veri']}, falsi {out['episodi_di_allarme']['falsi']}")
    out["elenco_allarmi"] = epis[-12:]
    for e in epis[-8:]:
        print(f"   {e['da']} -> {e['a']} ({e['sedute']} sedute)  {'CALO' if e['poi_meno10'] else 'falso allarme'}")

    json.dump(out, open("scratch/crollo_precisione.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato scratch/crollo_precisione.json")


if __name__ == "__main__":
    main()
