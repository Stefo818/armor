"""Parte 9 del protocollo, piu' la domanda che conta per l'utente: conviene agire sulle fasce?

Misura, per ogni fascia, il rendimento successivo medio e mediano. Un indice che segnala crolli
ma e' seguito in media da rialzi farebbe perdere soldi a chi vende: va detto.
Include anche l'Indice Armor rimappato e una miscela, dichiarati come esplorativi dove lo sono.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import store  # noqa: E402
from crollo_ricerca import (COLORI, PESI_M2, auc, auc_ic, bersagli, carica,  # noqa: E402
                            fascia, mappa_indice, per_fascia, placebo)

FAM = [f"f{i}_" for i in range(1, 13)]
VER = "2015-01-01"


def main():
    X = carica()
    Y = bersagli(X["sp500"])
    d = X.join(Y)
    d = d[d.index >= "1990-01-02"]
    fam = [c for c in d.columns if any(c.startswith(f) for f in FAM)]
    F = d[fam]
    w = pd.Series(PESI_M2)
    w = w / w.sum()
    m2 = sum(F[c].fillna(50.0) * w[c] for c in w.index)
    arm = d["armor_grezzo"]
    mix = (m2.rank(pct=True) * 100 + arm.rank(pct=True) * 100) / 2   # esplorativa: usa i ranghi su tutto il periodo

    sp = d["sp500"]
    out = {"nota": "Rendimenti successivi dell'S&P 500 in percento. Periodo di verifica dal 2015."}
    ver = d.index >= VER
    base = float(d["Y10"][ver].mean())

    # --- Indice Armor rimappato sulle fasce richieste: regole R1-R3 (R4 non si applica a se stesso)
    ia = mappa_indice(arm)
    a = float(auc(d["Y10"][ver], arm[ver]))
    ic = auc_ic(d["Y10"][ver], arm[ver])
    pl95, _ = placebo(d["Y10"][ver], arm[ver])
    pf = per_fascia(ia[ver], d["Y10"][ver])
    out["armor_rimappato"] = {"auc": round(a, 4), "ic90": [round(ic[0], 4), round(ic[1], 4)], "placebo_p95": round(pl95, 4),
                              "frequenza_base": round(base * 100, 1), "fasce": pf,
                              "R1": bool(a >= 0.65 and ic[0] > 0.55), "R2": bool((pf["viola"].get("frequenza") or 0) >= 2.5 * base * 100), "R3": bool(pl95 < a)}
    print("=== Indice Armor rimappato sulle fasce richieste (verifica 2015-2026) ===")
    print(f"AUC {a:.4f} IC90 [{ic[0]:.4f}, {ic[1]:.4f}] placebo p95 {pl95:.4f} base {base*100:.1f}%  R1-R3 {out['armor_rimappato']['R1']},{out['armor_rimappato']['R2']},{out['armor_rimappato']['R3']}")
    for c in COLORI:
        f = pf[c]
        if f.get("giorni"):
            print(f"  {c:7s} {f['giorni']:5d} gg ({f['quota_giorni']:4.1f}%)  crollo nel {f['frequenza']:5.1f}%  IC90 {f['ic90']}")

    # --- miscela, esplorativa (scelta dopo aver visto i risultati: non puo' avere etichetta)
    am = float(auc(d["Y10"][ver], mix[ver]))
    out["miscela_esplorativa"] = {"auc": round(am, 4), "nota": "scelta dopo i risultati, non validata"}
    print(f"\nmiscela (esplorativa) AUC {am:.4f}  vs Armor {a:.4f}  vs M2 {float(auc(d['Y10'][ver], m2[ver])):.4f}")

    # --- la domanda che conta: cosa e' successo DOPO ogni fascia
    print("\n=== rendimento successivo dell'S&P 500 per fascia (Indice Armor rimappato, dal 2015) ===")
    print(f"{'fascia':8s} {'gg':>5s} {'5 sed.':>18s} {'10 sed.':>18s} {'21 sed.':>18s} {'63 sed.':>18s}")
    rend = {}
    for c in COLORI:
        m = (fascia(ia) == c) & ver
        riga = {"giorni": int(m.sum())}
        txt = f"{c:8s} {int(m.sum()):5d}"
        for n in (5, 10, 21, 63):
            f = sp.shift(-n) / sp - 1
            v = f[m].dropna() * 100
            if len(v):
                riga[f"{n}sed"] = {"media": round(float(v.mean()), 2), "mediana": round(float(v.median()), 2),
                                   "quota_positivi": round(float((v > 0).mean() * 100), 1),
                                   "peggiore": round(float(v.min()), 1)}
                txt += f"  {v.mean():+5.2f}/{v.median():+5.2f} ({(v>0).mean()*100:3.0f}%)"
            else:
                txt += " " * 19
        rend[c] = riga
        print(txt)
    out["rendimento_per_fascia"] = rend
    print("  (media/mediana in %, fra parentesi la quota di casi positivi)")

    # --- costo di vendere sul rosso: confronto fra stare investito e uscire su rosso o viola
    print("\n=== e se uscissi quando l'indice entra in rosso e rientrassi quando torna sotto? (dal 2015) ===")
    r = np.log(sp).diff().fillna(0.0)
    for soglia, nome in ((61, "esco su rosso e viola"), (81, "esco solo su viola"), (41, "esco su giallo o peggio")):
        dentro = (ia.shift(1) < soglia).astype(float)   # decisione con l'indice di ieri: nessuno sguardo al futuro
        rr = (r * dentro)[ver]
        tot_f = float(np.exp(rr.sum()) - 1) * 100
        tot_i = float(np.exp(r[ver].sum()) - 1) * 100
        gg_fuori = float((1 - dentro)[ver].mean() * 100)
        # peggior perdita dal massimo
        def mdd(x):
            c = np.exp(x.cumsum())
            return float((c / np.maximum.accumulate(c) - 1).min() * 100)
        out.setdefault("strategia", {})[nome] = {"soglia": soglia, "rendimento_strategia": round(tot_f, 1), "rendimento_restando_investito": round(tot_i, 1),
                                                 "giorni_fuori_mercato": round(gg_fuori, 1), "peggior_perdita_strategia": round(mdd(rr), 1),
                                                 "peggior_perdita_investito": round(mdd(r[ver]), 1)}
        print(f"  {nome:26s} strategia {tot_f:+8.1f}%  restando investito {tot_i:+8.1f}%  fuori mercato {gg_fuori:4.1f}% dei giorni  peggior perdita {mdd(rr):6.1f}% vs {mdd(r[ver]):6.1f}%")

    # --- replay delle due date opposte, con dettaglio delle famiglie
    print("\n=== le due date opposte ===")
    for giorno in ("2026-11-05", "2026-11-18"):
        t = pd.Timestamp(giorno)
        out.setdefault("replay", {})[giorno] = {"indice_armor_rimappato": round(float(ia[t]), 1), "fascia": str(fascia(ia)[t]),
                                                "crollo_poi": int(d["Y10"][t]), "famiglie": {c: round(float(d[c][t]), 0) if pd.notna(d[c][t]) else None for c in fam}}
        print(f"  {giorno}: indice {ia[t]:.1f} ({fascia(ia)[t]}), crollo nei 10 gg dopo: {'si' if d['Y10'][t] else 'no'}")
        print("    " + "  ".join(f"{c[3:]}={d[c][t]:.0f}" for c in fam if pd.notna(d[c][t])))

    # --- le serie corte: aiutano sugli ultimi mesi? esplorativo, non validabile
    corte = {}
    for k in ("breadth200", "nh_nl", "hy_oas", "fear_greed"):
        s = store.load(k).dropna()
        if len(s) > 120:
            sv = s.reindex(sp.index).ffill()
            m = sv.notna() & d["Y10"].notna()
            corte[k] = {"righe": int(m.sum()), "auc": round(float(auc(d["Y10"][m], -sv[m] if k in ("breadth200", "nh_nl") else sv[m])), 4)}
    out["serie_corte_esplorative"] = corte
    print("\nserie corte (esplorative, storia troppo breve per l'etichetta):", json.dumps(corte, ensure_ascii=False))

    json.dump(out, open("scratch/crollo_resa.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato scratch/crollo_resa.json")


if __name__ == "__main__":  # pragma: no cover
    main()
