"""Classificazione di tutti i cali forti dal 1986, con la causa documentata, e taratura della scala.

Le cause vengono dalla cronaca e dalle fonti ufficiali, non dal comportamento del modello: la regola del
progetto e' classificare prima di misurare.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from armor import store  # noqa: E402

# massimo di partenza -> (calo, natura, causa documentata)
CLASSIFICA = [
    ("1986-09-04", -9.4, "finanziaria", "timori su inflazione e tassi, vendite automatiche dei programmi"),
    ("1987-08-25", -33.5, "finanziaria", "lunedi nero: assicurazione di portafoglio e vendite automatiche, dopo mesi di rialzo dei tassi"),
    ("1989-10-09", -10.2, "finanziaria", "crollo delle obbligazioni spazzatura (salta il riacquisto di UAL) e crisi delle casse di risparmio"),
    ("1990-07-16", -19.9, "esterna", "invasione del Kuwait, shock del petrolio"),
    ("1994-02-02", -8.9, "finanziaria", "rialzo a sorpresa dei tassi: l'anno del massacro delle obbligazioni"),
    ("1997-02-18", -9.6, "finanziaria", "timori di stretta monetaria, poi confermata a marzo"),
    ("1997-10-07", -10.8, "finanziaria", "crisi finanziaria asiatica, attacco al cambio di Hong Kong"),
    ("1998-07-17", -19.3, "finanziaria", "default russo e crollo del fondo a leva LTCM"),
    ("1999-07-16", -12.1, "finanziaria", "stretta della banca centrale americana"),
    ("1999-12-31", -9.2, "finanziaria", "tassi in salita e valutazioni tirate"),
    ("2000-03-24", -49.1, "finanziaria", "scoppio della bolla tecnologica"),
    ("2007-07-19", -9.4, "finanziaria", "prime perdite sui mutui subprime e crisi dei fondi quantitativi di agosto"),
    ("2007-10-09", -56.8, "finanziaria", "crisi dei mutui e del credito, poi fallimento di Lehman"),
    ("2015-05-21", -14.2, "mista", "svalutazione cinese, crollo del petrolio con contagio sul credito energetico"),
    ("2018-01-26", -10.2, "finanziaria", "scoppio dei prodotti scommessi sulla volatilita' bassa"),
    ("2018-09-20", -19.8, "mista", "stretta della banca centrale piu' guerra dei dazi con la Cina"),
    ("2020-02-19", -33.9, "esterna", "pandemia"),
    ("2020-09-02", -9.6, "finanziaria", "rientro delle scommesse a leva sulle opzioni dei titoli tecnologici"),
    ("2022-01-03", -25.4, "finanziaria", "inflazione e stretta monetaria (il grosso del calo precede l'invasione dell'Ucraina)"),
    ("2024-07-16", -8.5, "finanziaria", "rientro del carry trade sullo yen dopo il rialzo dei tassi giapponesi"),
    ("2025-02-19", -18.9, "esterna", "dazi e guerra commerciale"),
    ("2026-01-27", -9.1, "esterna", "attacchi USA-Israele contro l'Iran e blocco dello stretto di Hormuz"),
    ("2026-10-06", -11.6, "finanziaria", "rivalutazione dei titoli dell'intelligenza artificiale, inflazione e timori di stretta, rendimenti in salita"),
]

# finestre di shock esterno, aggiornate: da 5 sedute prima a 60 dopo l'evento
ESTERNI = ["1990-08-02", "2001-09-11", "2003-03-20", "2020-02-21", "2022-02-24",
           "2018-03-01", "2018-06-15", "2018-09-17", "2019-05-05", "2019-08-01",
           "2025-02-01", "2025-03-04", "2025-04-02",
           "2026-02-25"]   # NUOVA: attacchi USA-Israele contro l'Iran (fonte: Janus Henderson, Nasdaq, Chase)
MISTE_MAX = ["2015-05-21", "2018-09-20"]
PRIMA, DOPO = 5, 60


def finestra(cal, date, dopo=DOPO):
    m = pd.Series(False, index=cal)
    for d in date:
        pos = cal.searchsorted(pd.Timestamp(d))
        m.iloc[max(0, pos - PRIMA):min(len(cal), pos + dopo + 1)] = True
    return m


def main():
    n = {}
    for _, _, nat, _ in CLASSIFICA:
        n[nat] = n.get(nat, 0) + 1
    print(f"cali di almeno l'8% dal 1986: {len(CLASSIFICA)}")
    print("  " + "  ".join(f"{k}: {v}" for k, v in sorted(n.items())))
    print(f"\n{'massimo':12s} {'calo':>7s}  {'natura':12s} causa")
    for mx, calo, nat, causa in CLASSIFICA:
        print(f"{mx:12s} {calo:6.1f}%  {nat:12s} {causa}")

    # --- taratura della scala sull'Indice Armor, solo crisi finanziarie
    h = pd.read_csv("data/titan_storia.csv", parse_dates=["date"]).set_index("date")
    sp = store.load("sp500").dropna()
    cal = h.index.intersection(sp.index)
    h, spx = h.loc[cal], sp.loc[cal]
    fuori = finestra(cal, ESTERNI)
    for d in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(d))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
    picco = spx.rolling(252, min_periods=60).max()
    fwd = pd.concat([spx.shift(-i) for i in range(1, 61)], axis=1).min(axis=1)
    Y = ((fwd / picco - 1) <= -0.10).astype(float)
    Y[fwd.isna()] = np.nan
    f10 = pd.concat([spx.shift(-i) for i in range(1, 11)], axis=1).min(axis=1) / spx - 1
    Y10 = (f10 <= -0.05).astype(float)
    Y10[f10.isna()] = np.nan
    buono = (~fuori) & Y.notna()
    print(f"\n=== taratura su {int(buono.sum())} giorni di sole crisi finanziarie (esclusa anche l'Iran) ===")

    sup, arm = h["super_armor_index"], h["armor_index"]
    # i confini del Super Armor, che i dati gia' confermano, espressi in percentile
    q40 = float((sup[buono] < 40).mean())
    q60 = float((sup[buono] < 60).mean())
    q80 = float((sup[buono] < 80).mean())
    print(f"Super Armor: 40 = {q40*100:.1f}° percentile, 60 = {q60*100:.1f}°, 80 = {q80*100:.1f}°")
    # gli stessi percentili sull'Indice Armor danno i punti di aggancio della nuova scala
    a40, a60, a80 = (round(float(arm[buono].quantile(q)), 2) for q in (q40, q60, q80))
    print(f"Indice Armor: gli stessi percentili cadono a {a40}, {a60}, {a80} della scala di oggi")
    print(f"              (oggi l'Indice Armor vale {float(arm.dropna().iloc[-1]):.1f})")

    def riscala(v, a=(a40, a60, a80)):
        return np.interp(v, [1.0, a[0], a[1], a[2], 100.0], [1.0, 40.0, 60.0, 80.0, 100.0])

    nuovo = pd.Series(riscala(arm.values), index=arm.index)
    print(f"\n{'fascia':12s} {'giorni':>7s} {'quota':>7s} {'-10% in 60 sed':>15s} {'-5% in 10 sed':>14s}")
    out = {"classifica": [{"massimo": a, "calo": b, "natura": c, "causa": d} for a, b, c, d in CLASSIFICA],
           "ancore": {"a40": a40, "a60": a60, "a80": a80}, "oggi_grezzo": round(float(arm.dropna().iloc[-1]), 1),
           "oggi_nuovo": round(float(nuovo.dropna().iloc[-1]), 1), "fasce": {}}
    for lo, hi, et in ((0, 40, "sotto 40"), (40, 60, "40-60"), (60, 80, "60-80"), (80, 101, "sopra 80")):
        m = buono & (nuovo >= lo) & (nuovo < hi)
        if m.sum() < 10:
            print(f"{et:12s} {int(m.sum()):7d}   troppo pochi")
            continue
        a_, b_ = float(Y[m].mean()) * 100, float(Y10[m].mean()) * 100
        out["fasce"][et] = {"giorni": int(m.sum()), "quota": round(float(m.sum() / buono.sum()) * 100, 1),
                            "m10": round(a_, 1), "m5": round(b_, 1)}
        print(f"{et:12s} {int(m.sum()):7d} {m.sum()/buono.sum()*100:6.1f}% {a_:14.1f}% {b_:13.1f}%")
    base, base10 = float(Y[buono].mean()) * 100, float(Y10[buono].mean()) * 100
    out["base"] = {"m10": round(base, 1), "m5": round(base10, 1)}
    print(f"\nbase: -10% entro 60 sedute {base:.1f}%   -5% entro 10 sedute {base10:.1f}%")
    print(f"oggi l'Indice Armor passerebbe da {float(arm.dropna().iloc[-1]):.1f} a {float(nuovo.dropna().iloc[-1]):.1f}")
    json.dump(out, open("scratch/classifica_40anni.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
