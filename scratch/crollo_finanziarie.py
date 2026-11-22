"""Indice crollo sulle sole crisi di natura finanziaria.

Segue PROTOCOLLO_INDICE_CROLLO.md, emendamento 1 (parti B, C, D).
Le finestre di shock esterno sono quelle fissate nell'emendamento, pubblicato prima di questo calcolo.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from crollo_ricerca import (COLORI, PESI_M2, auc, auc_ic, bersagli, carica, fascia,  # noqa: E402
                            mappa_indice, per_fascia, placebo, walk_forward)

FAM = [f"f{i}_" for i in range(1, 13)]
ESTERNI = ["1990-08-02", "2001-09-11", "2003-03-20", "2020-02-21", "2022-02-24",
           "2018-03-01", "2018-06-15", "2018-09-17", "2019-05-05", "2019-08-01",
           "2025-02-01", "2025-03-04", "2025-04-02"]
MISTE_MAX = ["2015-05-21", "2018-09-20"]     # massimi delle due crisi miste
PRIMA, DOPO = 5, 60                          # finestra in sedute


def finestra(cal: pd.DatetimeIndex, date: list[str]) -> pd.Series:
    """Vero nei giorni dentro una finestra di shock, da 5 sedute prima a 60 dopo."""
    m = pd.Series(False, index=cal)
    for d in date:
        t = pd.Timestamp(d)
        pos = cal.searchsorted(t)
        a, b = max(0, pos - PRIMA), min(len(cal), pos + DOPO + 1)
        m.iloc[a:b] = True
    return m


def main():
    X = carica()
    Y = bersagli(X["sp500"])
    d = X.join(Y)
    d = d[d.index >= "1990-01-02"]
    cal = d.index
    fam = [c for c in d.columns if any(c.startswith(f) for f in FAM)]
    F = d[fam]

    fuori_est = finestra(cal, ESTERNI)
    fuori_mix = finestra(cal, MISTE_MAX)
    # per le miste la finestra va fino al minimo, piu' lunga: dal massimo a 180 sedute dopo
    for dd in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(dd))
        fuori_mix.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True

    buono = (~fuori_est) & (~fuori_mix) & d["Y10"].notna()          # principale
    buono_mix = (~fuori_est) & d["Y10"].notna()                      # robustezza R5
    out = {"giorni_totali": int(d["Y10"].notna().sum()),
           "esclusi_esterni": int((fuori_est & d["Y10"].notna()).sum()),
           "esclusi_misti": int((fuori_mix & ~fuori_est & d["Y10"].notna()).sum()),
           "giorni_finanziari": int(buono.sum())}
    print(f"giorni con bersaglio: {out['giorni_totali']}  esclusi esterni: {out['esclusi_esterni']}  "
          f"esclusi misti: {out['esclusi_misti']}  restano: {out['giorni_finanziari']}")
    print(f"frequenza del bersaglio: tutto {d['Y10'][d['Y10'].notna()].mean()*100:.1f}%  "
          f"solo finanziarie {d['Y10'][buono].mean()*100:.1f}%")
    out["frequenza_base_tutto"] = round(float(d["Y10"][d["Y10"].notna()].mean()) * 100, 1)
    out["frequenza_base_finanziarie"] = round(float(d["Y10"][buono].mean()) * 100, 1)

    punteggi = {}
    punteggi["M1 media"] = F.mean(axis=1, skipna=True)
    w = pd.Series(PESI_M2) / pd.Series(PESI_M2).sum()
    punteggi["M2 pesi"] = sum(F[c].fillna(50.0) * w[c] for c in w.index)
    punteggi["M3 logistica"] = walk_forward(F, d["Y10"].where(buono), lambda: LogisticRegression(max_iter=2000, C=1.0), 21)
    punteggi["M4 alberi"] = walk_forward(F, d["Y10"].where(buono),
                                         lambda: GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0), 63)
    ch = ["f1_paura", "f3_curva", "f5_credito", "f7_tendenza"]
    punteggi["M5 due chiavi"] = sum((F[c] > 85).astype(float) for c in ch) * 25 + F[ch].mean(axis=1, skipna=True) / 100
    punteggi["Indice Armor"] = d["armor_grezzo"]

    sel = buono & (cal <= "2014-12-31")
    ver = buono & (cal >= "2015-01-01")
    print(f"\nscelta su {int(sel.sum())} giorni ({int(d['Y10'][sel].sum())} crolli), "
          f"verifica su {int(ver.sum())} giorni ({int(d['Y10'][ver].sum())} crolli)")
    print("\n=== scelta (1990-2014, solo finanziarie) ===")
    out["scelta"] = {}
    for nome, s in punteggi.items():
        a = float(auc(d["Y10"][sel], s[sel]))
        pf = per_fascia(mappa_indice(s)[sel], d["Y10"][sel])
        out["scelta"][nome] = {"auc": round(a, 4), "viola_freq": pf["viola"].get("frequenza"), "viola_giorni": pf["viola"].get("giorni")}
        print(f"{nome:16s} AUC {a:.4f}  viola {pf['viola'].get('frequenza')}% su {pf['viola'].get('giorni')} gg")
    cand = {k: v for k, v in out["scelta"].items() if k != "Indice Armor"}
    best = max(cand, key=lambda k: (cand[k]["auc"], cand[k]["viola_freq"] or 0))
    out["vincente"] = best
    print("vincente fra i nuovi:", best)

    print("\n=== verifica (2015-2026, solo finanziarie) ===")
    out["verifica"] = {}
    for nome in (best, "Indice Armor"):
        s = punteggi[nome]
        a = float(auc(d["Y10"][ver], s[ver]))
        ic = auc_ic(d["Y10"][ver], s[ver])
        pl95, _ = placebo(d["Y10"][ver], s[ver])
        base = float(d["Y10"][ver].mean())
        pf = per_fascia(mappa_indice(s)[ver], d["Y10"][ver])
        a_mix = float(auc(d["Y10"][buono_mix & (cal >= "2015-01-01")], s[buono_mix & (cal >= "2015-01-01")]))
        o = {"auc": round(a, 4), "ic90": [round(ic[0], 4), round(ic[1], 4)], "placebo_p95": round(pl95, 4),
             "frequenza_base": round(base * 100, 1), "fasce": pf, "auc_con_miste": round(a_mix, 4),
             "R1": bool(a >= 0.65 and ic[0] > 0.55), "R2": bool((pf["viola"].get("frequenza") or 0) >= 2.5 * base * 100),
             "R3": bool(pl95 < a), "R5": bool(abs(a - a_mix) <= 0.03)}
        out["verifica"][nome] = o
        print(f"{nome}: AUC {a:.4f} IC90 [{ic[0]:.4f}, {ic[1]:.4f}] placebo {pl95:.4f} base {base*100:.1f}% "
              f"| con miste {a_mix:.4f} | R1 {o['R1']} R2 {o['R2']} R3 {o['R3']} R5 {o['R5']}")
        for c in COLORI:
            f = pf[c]
            if f.get("giorni"):
                print(f"   {c:7s} {f['giorni']:5d} gg ({f['quota_giorni']:4.1f}%)  crollo nel {f['frequenza']:5.1f}%  IC90 {f['ic90']}")
    ab, aa = out["verifica"][best]["auc"], out["verifica"]["Indice Armor"]["auc"]
    out["verifica"][best]["R4"] = bool((ab - aa) >= 0.02)
    reg = {k: out["verifica"][best][k] for k in ("R1", "R2", "R3", "R4", "R5")}
    out["etichetta_nuovo"] = "Coerente con i casi osservati" if all(reg.values()) else "Non coerente"
    print(f"\nregole del modello nuovo: {reg} -> {out['etichetta_nuovo']}")
    reg_a = {k: out["verifica"]["Indice Armor"][k] for k in ("R1", "R2", "R3", "R5")}
    out["etichetta_armor"] = "Coerente con i casi osservati (R1-R3, R5)" if all(reg_a.values()) else "Non coerente"
    print(f"regole dell'Indice Armor (R4 non si applica a se stesso): {reg_a} -> {out['etichetta_armor']}")

    # scelta finale per l'app: il migliore dei due sulla verifica
    finale = best if ab > aa else "Indice Armor"
    out["indice_scelto"] = finale
    s = punteggi[finale]
    idx = mappa_indice(s)
    print(f"\nindice scelto per l'app: {finale}")

    # rendimento successivo per fascia, solo finanziarie
    sp = d["sp500"]
    print("\n=== rendimento successivo dell'S&P 500 per fascia (solo finanziarie, dal 2015) ===")
    rend = {}
    for c in COLORI:
        m = (fascia(idx) == c) & ver
        riga = {"giorni": int(m.sum())}
        txt = f"{c:8s} {int(m.sum()):5d}"
        for n in (5, 10, 21, 63):
            f = sp.shift(-n) / sp - 1
            v = (f[m].dropna()) * 100
            if len(v):
                riga[f"{n}sed"] = {"media": round(float(v.mean()), 2), "mediana": round(float(v.median()), 2),
                                   "quota_positivi": round(float((v > 0).mean() * 100), 1), "peggiore": round(float(v.min()), 1)}
                txt += f"  {v.mean():+5.2f}/{v.median():+5.2f} ({(v>0).mean()*100:3.0f}%)"
        rend[c] = riga
        print(txt)
    out["rendimento_per_fascia"] = rend

    # strategia: uscire sulle soglie, solo finanziarie (fuori dalle finestre esterne resta investito)
    print("\n=== uscire sulle soglie, dal 2015 (nelle finestre esterne resta investito) ===")
    r = np.log(sp).diff().fillna(0.0)
    per = cal >= "2015-01-01"
    for soglia, nome in ((61, "esco su rosso e viola"), (41, "esco su giallo o peggio"), (81, "esco solo su viola")):
        dentro = ((idx.shift(1) < soglia) | fuori_est.shift(1).fillna(False)).astype(float)
        rr = (r * dentro)[per]
        def mdd(x):
            cc = np.exp(x.cumsum())
            return float((cc / np.maximum.accumulate(cc) - 1).min() * 100)
        o = {"strategia": round(float(np.exp(rr.sum()) - 1) * 100, 1), "investito": round(float(np.exp(r[per].sum()) - 1) * 100, 1),
             "giorni_fuori": round(float((1 - dentro)[per].mean() * 100), 1), "peggior_perdita_strategia": round(mdd(rr), 1),
             "peggior_perdita_investito": round(mdd(r[per]), 1)}
        out.setdefault("strategia", {})[nome] = o
        print(f"  {nome:26s} {o['strategia']:+8.1f}%  vs investito {o['investito']:+8.1f}%  "
              f"fuori {o['giorni_fuori']:4.1f}% dei giorni  peggior perdita {o['peggior_perdita_strategia']:6.1f}% vs {o['peggior_perdita_investito']:6.1f}%")

    # gli 11 episodi finanziari: preavviso
    EP_FIN = [("1990-01-02", "1990-01-30"), ("1997-10-07", "1997-10-27"), ("1998-07-17", "1998-08-14"),
              ("1999-07-16", "1999-09-29"), ("2000-03-24", "2000-04-14"), ("2000-03-24", "2000-10-11"),
              ("2007-10-09", "2007-11-26"), ("2015-05-21", "2015-08-24"), ("2018-01-26", "2018-02-08"),
              ("2022-01-03", "2022-02-22"), ("2026-10-06", "2026-11-20")]
    print("\n=== gli 11 episodi finanziari: dove stava l'indice? ===")
    ep = []
    for mx, dn in EP_FIN:
        tmx, tdn = pd.Timestamp(mx), pd.Timestamp(dn)
        seg = sp[tmx:tdn]
        d2 = seg[(seg / sp[tmx] - 1) <= -0.02]
        d5 = seg[(seg / sp[tmx] - 1) <= -0.05]
        e = {"massimo": mx, "meno10": dn,
             "al_massimo": None if pd.isna(idx.get(tmx, np.nan)) else round(float(idx[tmx]), 1),
             "a_meno2": None if not len(d2) or pd.isna(idx.get(d2.index[0], np.nan)) else round(float(idx[d2.index[0]]), 1),
             "a_meno5": None if not len(d5) or pd.isna(idx.get(d5.index[0], np.nan)) else round(float(idx[d5.index[0]]), 1),
             "giorni_max_a_meno2": int(len(sp[tmx:d2.index[0]])) if len(d2) else None}
        ep.append(e)
        print(f"  {mx} -> {dn}: al massimo {e['al_massimo']}, a -2% {e['a_meno2']} (dopo {e['giorni_max_a_meno2']} sedute), a -5% {e['a_meno5']}")
    out["episodi_finanziari"] = ep
    v2 = [e["a_meno2"] for e in ep if e["a_meno2"] is not None]
    v5 = [e["a_meno5"] for e in ep if e["a_meno5"] is not None]
    if v2:
        out["mediana_a_meno2"] = round(float(np.median(v2)), 1)
        out["quanti_gialli_a_meno2"] = int(sum(1 for x in v2 if x >= 41))
        print(f"  a -2% dal massimo: mediana {np.median(v2):.1f}; giallo o peggio in {out['quanti_gialli_a_meno2']} casi su {len(v2)}")
    if v5:
        out["mediana_a_meno5"] = round(float(np.median(v5)), 1)
        out["quanti_gialli_a_meno5"] = int(sum(1 for x in v5 if x >= 41))
        print(f"  a -5% dal massimo: mediana {np.median(v5):.1f}; giallo o peggio in {out['quanti_gialli_a_meno5']} casi su {len(v5)}")

    # le due date opposte e oggi
    print("\n=== date chiave ===")
    for g in ("2026-10-06", "2026-10-30", "2026-11-05", "2026-11-13", "2026-11-18", "2026-11-19", "2026-11-20"):
        t = pd.Timestamp(g)
        if t in idx.index and pd.notna(idx[t]):
            yy = d["Y10"][t]
            out.setdefault("date_chiave", {})[g] = {"indice": round(float(idx[t]), 1), "fascia": str(fascia(idx)[t]),
                                                    "crollo_poi": None if pd.isna(yy) else int(yy)}
            print(f"  {g}: {idx[t]:5.1f} ({fascia(idx)[t]:6s})  crollo nei 10 gg dopo: {'si' if yy == 1 else ('no' if yy == 0 else '?')}")

    json.dump(out, open("scratch/crollo_finanziarie.json", "w"), ensure_ascii=False, indent=1)
    pd.DataFrame({"score": s, "indice": idx}).to_csv("scratch/crollo_indice_serie.csv", index_label="date")
    print("\nsalvato scratch/crollo_finanziarie.json")


if __name__ == "__main__":
    main()
