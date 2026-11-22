"""Esplorativo (deciso dopo aver visto i risultati: nessuna etichetta possibile).

Domanda dell'utente: era prevedibile in anticipo? Qui si misura la capacita' di distinguere
SOLO nei giorni in cui il mercato e' ancora vicino ai massimi, cioe' prima che la discesa sia partita.
Un indice che funziona solo a discesa iniziata descrive il presente, non anticipa.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import store  # noqa: E402
from crollo_ricerca import PESI_M2, auc, bersagli, carica  # noqa: E402

FAM = [f"f{i}_" for i in range(1, 13)]


def main():
    X = carica()
    Y = bersagli(X["sp500"])
    d = X.join(Y)
    d = d[d.index >= "1990-01-02"]
    fam = [c for c in d.columns if any(c.startswith(f) for f in FAM)]
    sp = d["sp500"]
    dd = sp / sp.rolling(252, min_periods=60).max() - 1
    w = pd.Series(PESI_M2) / pd.Series(PESI_M2).sum()
    m2 = sum(d[c].fillna(50.0) * w[c] for c in w.index)
    arm = d["armor_grezzo"]
    out = {"nota": "Esplorativo, scelto dopo i risultati. Nessuna etichetta."}

    print("=== capacita' di distinguere secondo quanto il mercato e' GIA' scivolato ===")
    print(f"{'stato del mercato':34s} {'giorni':>7s} {'crolli':>7s} {'base':>6s} {'Armor':>7s} {'M2':>7s}")
    for nome, m in (("entro 1% dal massimo (tutto calmo)", dd >= -0.01),
                    ("fra -1% e -3% dal massimo", (dd < -0.01) & (dd >= -0.03)),
                    ("fra -3% e -7% dal massimo", (dd < -0.03) & (dd >= -0.07)),
                    ("oltre -7% dal massimo", dd < -0.07)):
        mm = m & d["Y10"].notna()
        y = d["Y10"][mm]
        a1 = auc(y, arm[mm])
        a2 = auc(y, m2[mm])
        out.setdefault("per_stato", {})[nome] = {"giorni": int(mm.sum()), "crolli": int(y.sum()), "base": round(float(y.mean()) * 100, 1),
                                                 "auc_armor": None if np.isnan(a1) else round(float(a1), 4), "auc_m2": None if np.isnan(a2) else round(float(a2), 4)}
        print(f"{nome:34s} {int(mm.sum()):7d} {int(y.sum()):7d} {y.mean()*100:5.1f}% {a1:7.4f} {a2:7.4f}")

    # quale famiglia distingue quando tutto e' ancora calmo?
    calmo = (dd >= -0.02) & d["Y10"].notna()
    print(f"\n=== quale segnale distingue quando il mercato e' entro il 2% dal massimo ({int(calmo.sum())} giorni, {int(d['Y10'][calmo].sum())} crolli) ===")
    righe = {}
    for c in fam:
        a = auc(d["Y10"][calmo], d[c][calmo])
        if not np.isnan(a):
            righe[c] = round(float(a), 4)
    for c, a in sorted(righe.items(), key=lambda x: -abs(x[1] - 0.5)):
        print(f"  {c:14s} {a:.4f}")
    out["famiglie_a_mercato_calmo"] = righe

    # segnali lenti di valutazione e leva, disponibili con anticipo
    print("\n=== segnali lenti (valutazione, leva, credito): distinguono a mercato calmo? ===")
    lenti = {}
    for k, segno in (("val_pe_sp500", 1), ("val_pe_ndx", 1), ("erp", -1), ("margin_yoy", 1), ("margin_sp", 1),
                     ("top_pe", 1), ("baa10y", 1), ("t10y2y", -1), ("real10y", 1), ("nfci", 1), ("anfci", 1),
                     ("net_liq_13w", -1), ("ai_capex_ocf", 1), ("m2_yoy", -1), ("sahm", 1), ("recprob", 1)):
        s = store.load(k).dropna()
        if s.empty:
            continue
        sv = s.copy()
        sv.index = sv.index + pd.Timedelta(days=30)   # ritardo prudente di pubblicazione
        sv = sv.reindex(sp.index).ffill()
        m = calmo & sv.notna()
        if m.sum() < 500 or d["Y10"][m].sum() < 20:
            continue
        a = auc(d["Y10"][m], segno * sv[m])
        lenti[k] = {"giorni": int(m.sum()), "crolli": int(d["Y10"][m].sum()), "auc": round(float(a), 4)}
        print(f"  {k:16s} {int(m.sum()):6d} gg  {int(d['Y10'][m].sum()):4d} crolli  AUC {a:.4f}")
    out["segnali_lenti_a_mercato_calmo"] = lenti

    # i 16 episodi: quanto preavviso davano i segnali prima che il calo arrivasse al 5%
    print("\n=== i grandi cali: dove stava l'indice Armor quando il calo era ancora piccolo? ===")
    picco = sp.cummax()
    ddp = sp / picco - 1
    ep, dentro, start = [], False, None
    for t in sp.index:
        if not dentro and ddp[t] <= -0.10:
            dentro, start = True, t
            # risali al massimo precedente
            prima = sp[:t]
            tmax = prima.idxmax()
            # primo giorno in cui il calo dal massimo superava il 2% e il 5%
            seg = sp[tmax:t]
            d2 = seg[(seg / sp[tmax] - 1) <= -0.02]
            d5 = seg[(seg / sp[tmax] - 1) <= -0.05]
            e = {"massimo": str(tmax.date()), "meno10pc": str(t.date()),
                 "armor_al_massimo": round(float(arm[tmax]), 1) if pd.notna(arm[tmax]) else None,
                 "armor_a_meno2pc": round(float(arm[d2.index[0]]), 1) if len(d2) and pd.notna(arm[d2.index[0]]) else None,
                 "armor_a_meno5pc": round(float(arm[d5.index[0]]), 1) if len(d5) and pd.notna(arm[d5.index[0]]) else None,
                 "giorni_dal_massimo_a_meno10": int(len(seg))}
            ep.append(e)
        elif dentro and ddp[t] >= -0.02:
            dentro = False
    for e in ep:
        print(f"  massimo {e['massimo']} -> -10% il {e['meno10pc']} ({e['giorni_dal_massimo_a_meno10']} sedute): "
              f"Armor al massimo {e['armor_al_massimo']}, a -2% {e['armor_a_meno2pc']}, a -5% {e['armor_a_meno5pc']}")
    out["episodi_anticipo"] = ep
    vals = [e["armor_al_massimo"] for e in ep if e["armor_al_massimo"] is not None]
    if vals:
        print(f"  mediana dell'Indice Armor al massimo precedente: {np.median(vals):.1f} (su 100)")
        out["armor_al_massimo_mediana"] = round(float(np.median(vals)), 1)

    json.dump(out, open("scratch/crollo_anticipo.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato scratch/crollo_anticipo.json")


if __name__ == "__main__":
    main()
