"""Emendamento 3: «un settore importante è già rotto mentre l'indice tiene».

Costruzione e regole R10-R14 fissate nel protocollo, pubblicato prima di questo calcolo.
Verifica a esclusione di un episodio alla volta: il modello che giudica un episodio non lo ha mai visto.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from armor import store  # noqa: E402
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from crollo_strutturali import EPISODI, NOMI_SET, SETTORI, _pct, costruisci  # noqa: E402


def precisione(y, s, quota=0.2):
    """Precisione nel quinto piu' alto del segnale, con intervallo al 90% a blocchi di 21 sedute."""
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = y[m], s[m]
    if len(y) < 100:
        return None
    soglia = s.quantile(1 - quota)
    sel = y[s >= soglia]
    a = sel.to_numpy()
    rng = np.random.default_rng(9)
    bs = [a[np.concatenate([np.arange(x, min(x + 21, len(a))) for x in rng.integers(0, max(1, len(a) - 21), max(2, len(a) // 21))])].mean() for _ in range(800)]
    return {"giorni": int(len(sel)), "precisione": round(float(sel.mean()) * 100, 1),
            "ic90": [round(float(np.percentile(bs, 5)) * 100, 1), round(float(np.percentile(bs, 95)) * 100, 1)],
            "soglia": round(float(soglia), 2)}


def main():
    X = costruisci()
    sp, cal = X["sp500"], X.index
    S = {k: store.load(k).dropna().reindex(cal).ffill() for k in SETTORI}
    SP = pd.DataFrame(S)

    # --- nuova famiglia: settori rotti
    mx126 = SP.rolling(126, min_periods=60).max()
    giu = SP / mx126 - 1                      # quanto ogni settore e' sotto il suo massimo a 6 mesi
    X["s1_rotto"] = _pct(-giu.min(axis=1))    # il settore piu' rotto
    X["s2_quanti"] = _pct((giu <= -0.10).sum(axis=1))
    r3 = SP / SP.shift(63) - 1
    X["s3_dispers"] = _pct(r3.max(axis=1) - r3.min(axis=1))
    ndx = store.load("nasdaq100").dropna().reindex(cal).ffill()
    rap = ndx / sp
    sopra = (SP > SP.rolling(200, min_periods=100).mean()).sum(axis=1)
    X["s4_pochi"] = (_pct(rap / rap.rolling(200, min_periods=100).mean() - 1) * _pct(sopra, inv=True)) / 100

    # composito «assetto sistemico», componenti fissate nel protocollo parte C
    COMP = ["s1_rotto", "s2_quanti", "g4_valutazione", "g5_premio", "g11_insolvenze", "g10_oro"]
    X["assetto"] = X[COMP].mean(axis=1, skipna=True)

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
    base = float(Y[zona].mean()) * 100
    out = {"base_zona": round(base, 1), "giorni_zona": int(zona.sum())}
    print(f"zona: {int(zona.sum())} giorni, base {base:.1f}%")

    def auc(y, s):
        m = (~pd.isna(y)) & (~pd.isna(s))
        y, s = np.asarray(y)[m], np.asarray(s)[m]
        if len(np.unique(y)) < 2:
            return np.nan
        r = pd.Series(s).rank().to_numpy()
        n1, n0 = y.sum(), (1 - y).sum()
        return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    print("\n=== le nuove famiglie e il composito ===")
    for c in ("s1_rotto", "s2_quanti", "s3_dispers", "s4_pochi", "assetto"):
        m = zona & X[c].notna()
        p = precisione(Y[m], X[c][m])
        a = auc(Y[m], X[c][m])
        out.setdefault("nuove", {})[c] = {"auc": round(float(a), 4), **(p or {})}
        print(f"{c:12s} AUC {a:.4f}  quinto piu' alto: {p['precisione']}% su {p['giorni']} gg  IC90 {p['ic90']}")

    # --- riferimento: l'Indice crollo attuale nella STESSA zona e sullo stesso bersaglio
    att = ic.calcola_serie()["indice"].reindex(cal)
    m = zona & att.notna()
    p_att = precisione(Y[m], att[m])
    out["riferimento_indice_attuale"] = {"auc": round(float(auc(Y[m], att[m])), 4), **p_att}
    print(f"\nIndice crollo attuale, stessa zona: AUC {out['riferimento_indice_attuale']['auc']:.4f}  "
          f"quinto piu' alto {p_att['precisione']}% su {p_att['giorni']} gg  IC90 {p_att['ic90']}")

    # --- N2: logistica a esclusione di un episodio alla volta
    FAM = [c for c in X.columns if (c.startswith("g") or c.startswith("s")) and c not in ("guida",)]
    FAM = [c for c in FAM if c != "sp500"]
    fin = {k: (pd.Timestamp(a), pd.Timestamp(b)) for k, (a, b) in EPISODI.items()}

    def mask_ep(k, giorni=120):
        a, b = fin[k]
        return (cal >= a - pd.Timedelta(days=giorni)) & (cal <= b + pd.Timedelta(days=30))

    Xf = X[FAM].fillna(50.0)
    pred_loeo = pd.Series(np.nan, index=cal)
    for k in EPISODI:
        test = zona & mask_ep(k)
        tr = zona & (~mask_ep(k))
        if test.sum() < 20 or tr.sum() < 500:
            continue
        mdl = LogisticRegression(max_iter=3000, C=0.3)
        mdl.fit(Xf[tr], Y[tr])
        pred_loeo[test] = mdl.predict_proba(Xf[test])[:, 1]
    mL = pred_loeo.notna()
    p_loeo = precisione(Y[mL], pred_loeo[mL])
    out["N2_esclusione_episodio"] = {"auc": round(float(auc(Y[mL], pred_loeo[mL])), 4), **(p_loeo or {})}
    print(f"\nN2 (logistica, episodio escluso): AUC {out['N2_esclusione_episodio']['auc']:.4f}  "
          f"quinto piu' alto {p_loeo['precisione']}% su {p_loeo['giorni']} gg  IC90 {p_loeo['ic90']}")

    # composito con esclusione di un episodio: la soglia del quinto si calcola solo sul resto
    prec_fuori = []
    for k in EPISODI:
        test = zona & mask_ep(k)
        tr = zona & (~mask_ep(k))
        if test.sum() < 20:
            continue
        soglia = X["assetto"][tr].quantile(0.8)
        sel = Y[test & (X["assetto"] >= soglia)]
        if len(sel) >= 5:
            prec_fuori.append({"episodio": k, "giorni": int(len(sel)), "precisione": round(float(sel.mean()) * 100, 1)})
    out["assetto_esclusione_episodio"] = prec_fuori
    if prec_fuori:
        tot_g = sum(x["giorni"] for x in prec_fuori)
        med = sum(x["precisione"] * x["giorni"] for x in prec_fuori) / tot_g
        out["assetto_loeo_media"] = round(med, 1)
        print("\ncomposito «assetto», soglia presa senza l'episodio giudicato:")
        for x in prec_fuori:
            print(f"   {x['episodio']}: {x['precisione']:5.1f}% su {x['giorni']:4d} giorni")
        print(f"   media pesata: {med:.1f}%")

    # --- placebo
    mA = zona & X["assetto"].notna()
    ya, sa = Y[mA].to_numpy(), X["assetto"][mA].to_numpy()
    rng = np.random.default_rng(13)
    pl = []
    for kk in rng.integers(100, len(ya) - 100, 200):
        yr = np.roll(ya, int(kk))
        so = np.quantile(sa, 0.8)
        pl.append(yr[sa >= so].mean())
    out["placebo_p95"] = round(float(np.percentile(pl, 95)) * 100, 1)
    print(f"\nplacebo (200 spostamenti): 95° percentile {out['placebo_p95']}%")

    # --- R14: quanti episodi hanno un giorno nel quinto piu' alto nei 60 giorni prima del -10%
    soglia_g = X["assetto"][zona].quantile(0.8)
    print("\n=== R14: l'assetto era nel quinto piu' alto nei 60 giorni prima del calo al 10%? ===")
    ep_ok = 0
    for k, (a, b) in EPISODI.items():
        ta = pd.Timestamp(a)
        # primo giorno in cui il calo dal massimo raggiunge il 10%
        seg = sp[ta:pd.Timestamp(b)]
        d10 = seg[(seg / sp[ta] - 1) <= -0.10]
        t10 = d10.index[0] if len(d10) else pd.Timestamp(b)
        fin60 = cal[(cal <= t10) & (cal >= t10 - pd.Timedelta(days=120))]
        vals = X["assetto"].reindex(fin60).dropna()
        mx = float(vals.max()) if len(vals) else np.nan
        ok = bool(mx >= soglia_g) if not np.isnan(mx) else None
        ep_ok += 1 if ok else 0
        # anche il settore guida/rotto in quel momento
        rotto = giu.reindex(fin60).min(axis=1).min() if len(fin60) else np.nan
        quale = giu.reindex(fin60).min(axis=0).idxmin() if len(fin60) else None
        out.setdefault("R14", {})[k] = {"assetto_max": None if np.isnan(mx) else round(mx, 1),
                                        "soglia": round(float(soglia_g), 1), "nel_quinto": ok,
                                        "settore_piu_rotto": NOMI_SET.get(quale), "quanto_rotto": None if pd.isna(rotto) else round(float(rotto) * 100, 1)}
        print(f"  {k}: assetto max {mx:.1f} (soglia {soglia_g:.1f}) -> {'SI' if ok else 'no'}; "
              f"settore piu' rotto: {NOMI_SET.get(quale)} a {rotto*100 if pd.notna(rotto) else float('nan'):.1f}%")
    out["R14_episodi_ok"] = ep_ok
    print(f"  episodi con preavviso: {ep_ok} su {len(EPISODI)}")

    # --- regole
    pa = out["nuove"]["assetto"]
    R = {"R10": pa["precisione"] >= 25 and pa["ic90"][0] > base,
         "R11": (out.get("assetto_loeo_media") or 0) >= 18,
         "R12": out["placebo_p95"] < pa["precisione"],
         "R13": (pa["precisione"] - p_att["precisione"]) >= 8,
         "R14": ep_ok >= 4}
    out["regole"] = {k: bool(v) for k, v in R.items()}
    out["etichetta"] = "Coerente con i casi osservati" if all(R.values()) else "Non coerente"
    print(f"\nregole: {out['regole']}\netichetta: {out['etichetta']}")

    # oggi
    oggi = X.iloc[-1]
    out["oggi"] = {c: (None if pd.isna(oggi[c]) else round(float(oggi[c]), 0)) for c in COMP + ["assetto", "s3_dispers", "s4_pochi"]}
    out["oggi"]["settore_piu_rotto"] = NOMI_SET.get(giu.iloc[-1].idxmin())
    out["oggi"]["quanto_rotto"] = round(float(giu.iloc[-1].min()) * 100, 1)
    print(f"\noggi: assetto {out['oggi']['assetto']}, settore piu' rotto {out['oggi']['settore_piu_rotto']} "
          f"a {out['oggi']['quanto_rotto']}% dal suo massimo a 6 mesi")

    json.dump(out, open("scratch/crollo_settore_rotto.json", "w"), ensure_ascii=False, indent=1)
    X[COMP + ["assetto", "sp500"]].to_csv("scratch/crollo_assetto_serie.csv", index_label="date")
    print("\nsalvato scratch/crollo_settore_rotto.json")


if __name__ == "__main__":
    main()
