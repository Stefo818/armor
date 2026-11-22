"""Ricerca dell'Indice crollo. Segue PROTOCOLLO_INDICE_CROLLO.md parti 4, 5, 6, 7, 9.

Scelta del modello solo sui dati 1990-2014; prestazione riportata sul 2015-2026.
Tutti i punteggi sono a finestra crescente: ogni giorno usa solo il passato.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import store  # noqa: E402
from crollo_segnali import bersagli, carica  # noqa: E402

FAM = [f"f{i}_" for i in range(1, 13)]
NEUTRO = 50.0          # scelta di implementazione: famiglia non disponibile = neutra
SCELTA_FINE = "2014-12-31"
VER_INIZIO = "2015-01-01"
PESI_M2 = {"f1_paura": 0.30, "f3_curva": 0.30, "f5_credito": 0.15, "f7_tendenza": 0.25,
           "f8_perdita": 0.25, "f10_rotaz": 0.15, "f6_tassi": 0.15}
# protocollo parte 6
TRATTI = [(0.00, 0.55, 1, 35), (0.55, 0.65, 36, 40), (0.65, 0.85, 41, 60), (0.85, 0.96, 61, 80), (0.96, 1.01, 81, 100)]
COLORI = ["verde", "grigio", "giallo", "rosso", "viola"]


def auc(y, s):
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2:
        return np.nan
    r = pd.Series(s).rank().to_numpy()
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def auc_ic(y, s, blocco=21, giri=1000, seed=7):
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    n = len(y)
    nb = max(1, n // blocco)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(giri):
        st = rng.integers(0, max(1, n - blocco), nb)
        idx = np.concatenate([np.arange(a, min(a + blocco, n)) for a in st])
        a = auc(y[idx], s[idx])
        if not np.isnan(a):
            out.append(a)
    return float(np.percentile(out, 5)), float(np.percentile(out, 95))


def placebo(y, s, giri=200, seed=11):
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    rng = np.random.default_rng(seed)
    out = [auc(np.roll(y, int(k)), s) for k in rng.integers(100, len(y) - 100, giri)]
    out = [a for a in out if not np.isnan(a)]
    return float(np.percentile(out, 95)), float(np.median(out))


def walk_forward(X, y, modello, ogni, ritardo=11, min_tr=1000):
    """Punteggio fuori campione: al giorno t il modello e' addestrato solo su bersagli completati."""
    Xv = X.fillna(NEUTRO).to_numpy()
    yv = y.to_numpy()
    out = np.full(len(X), np.nan)
    mdl = None
    for i in range(len(X)):
        if i % ogni == 0 or mdl is None:
            fine = i - ritardo
            if fine >= min_tr:
                tr_y = yv[:fine]
                ok = ~np.isnan(tr_y)
                if ok.sum() >= min_tr and len(np.unique(tr_y[ok])) == 2:
                    mdl = modello()
                    mdl.fit(Xv[:fine][ok], tr_y[ok])
        if mdl is not None:
            out[i] = mdl.predict_proba(Xv[i:i + 1])[0, 1]
    return pd.Series(out, index=X.index)


def mappa_indice(score: pd.Series) -> pd.Series:
    """Percentile su storia crescente, poi la scala a tratti della parte 6."""
    q = score.expanding(min_periods=500).rank(pct=True)
    out = pd.Series(np.nan, index=score.index)
    for a, b, lo, hi in TRATTI:
        m = (q >= a) & (q < b)
        out[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return out.clip(1, 100)


def fascia(idx: pd.Series) -> pd.Series:
    b = pd.cut(idx, [0, 35, 40, 60, 80, 100], labels=COLORI)
    return b


def per_fascia(idx, y):
    d = pd.DataFrame({"f": fascia(idx), "y": y}).dropna()
    r = {}
    for c in COLORI:
        s = d[d["f"] == c]["y"]
        if len(s) == 0:
            r[c] = {"giorni": 0}
            continue
        p = float(s.mean())
        # intervallo al 90% con blocchi di 21 sedute
        rng = np.random.default_rng(3)
        bs = []
        a = s.to_numpy()
        for _ in range(500):
            st = rng.integers(0, max(1, len(a) - 21), max(1, len(a) // 21))
            ix = np.concatenate([np.arange(x, min(x + 21, len(a))) for x in st])
            bs.append(a[ix].mean())
        r[c] = {"giorni": int(len(s)), "quota_giorni": round(len(s) / len(d) * 100, 1),
                "frequenza": round(p * 100, 1), "ic90": [round(float(np.percentile(bs, 5)) * 100, 1), round(float(np.percentile(bs, 95)) * 100, 1)]}
    return r


def main():
    X = carica()
    Y = bersagli(X["sp500"])
    d = X.join(Y)
    d = d[d.index >= "1990-01-02"]
    fam = [c for c in d.columns if any(c.startswith(f) for f in FAM)]
    F = d[fam]

    punteggi = {}
    # M1 media semplice
    punteggi["M1 media"] = F.mean(axis=1, skipna=True)
    # M2 pesi fissati
    w = pd.Series(PESI_M2)
    w = w / w.sum()
    num = sum(F[c].fillna(NEUTRO) * w[c] for c in w.index)
    punteggi["M2 pesi"] = num
    # M3 logistica
    punteggi["M3 logistica"] = walk_forward(F, d["Y10"], lambda: LogisticRegression(max_iter=2000, C=1.0), 21)
    # M4 alberi potenziati
    punteggi["M4 alberi"] = walk_forward(
        F, d["Y10"], lambda: GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0), 63)
    # M5 due chiavi
    chiavi = ["f1_paura", "f3_curva", "f5_credito", "f7_tendenza"]
    acc = sum((F[c] > 85).astype(float) for c in chiavi)
    punteggi["M5 due chiavi"] = acc * 25 + F[chiavi].mean(axis=1, skipna=True) / 100
    # riferimento
    punteggi["Indice Armor"] = d["armor_grezzo"]

    res = {"scelta_1990_2014": {}, "verifica_2015_2026": {}}
    sel = d.index <= SCELTA_FINE
    ver = d.index >= VER_INIZIO
    for nome, s in punteggi.items():
        res["scelta_1990_2014"][nome] = {"auc_Y10": round(float(auc(d["Y10"][sel], s[sel])), 4),
                                         "auc_Y5": round(float(auc(d["Y5"][sel], s[sel])), 4)}
        idx = mappa_indice(s)
        pf = per_fascia(idx[sel], d["Y10"][sel])
        res["scelta_1990_2014"][nome]["viola_freq"] = pf["viola"].get("frequenza")
        res["scelta_1990_2014"][nome]["viola_giorni"] = pf["viola"].get("giorni")

    # scelta del vincente con il criterio della parte 5
    cand = {k: v for k, v in res["scelta_1990_2014"].items() if k != "Indice Armor"}
    best = max(cand, key=lambda k: (cand[k]["auc_Y10"], cand[k]["viola_freq"] or 0))
    res["vincente"] = best
    print("=== scelta (1990-2014) ===")
    for k, v in res["scelta_1990_2014"].items():
        print(f"{k:16s} AUC Y10 {v['auc_Y10']:.4f}  AUC Y5 {v['auc_Y5']:.4f}  viola {v['viola_freq']}% su {v['viola_giorni']} gg")
    print("vincente:", best)

    # verifica sul periodo mai usato per scegliere
    s = punteggi[best]
    idx = mappa_indice(s)
    yv = d["Y10"][ver]
    a = float(auc(yv, s[ver]))
    ic = auc_ic(yv, s[ver])
    pl95, plmed = placebo(yv, s[ver])
    arm = float(auc(yv, punteggi["Indice Armor"][ver]))
    base = float(yv.mean())
    pf = per_fascia(idx[ver], yv)
    res["verifica_2015_2026"] = {
        "modello": best, "auc": round(a, 4), "ic90": [round(ic[0], 4), round(ic[1], 4)],
        "placebo_p95": round(pl95, 4), "placebo_mediana": round(plmed, 4),
        "auc_armor": round(arm, 4), "frequenza_base": round(base * 100, 1), "fasce": pf,
        "auc_2015_2020": round(float(auc(d["Y10"][(d.index >= "2015-01-01") & (d.index < "2021-01-01")], s[(d.index >= "2015-01-01") & (d.index < "2021-01-01")])), 4),
        "auc_2021_2026": round(float(auc(d["Y10"][d.index >= "2021-01-01"], s[d.index >= "2021-01-01"])), 4),
        "auc_dal_2020": round(float(auc(d["Y10"][d.index >= "2020-01-01"], s[d.index >= "2020-01-01"])), 4),
    }
    print("\n=== verifica (2015-2026) ===")
    v = res["verifica_2015_2026"]
    print(f"AUC {v['auc']:.4f} IC90 {v['ic90']}  placebo p95 {v['placebo_p95']:.4f}  Armor {v['auc_armor']:.4f}  base {v['frequenza_base']}%")
    print(f"meta': 2015-2020 {v['auc_2015_2020']:.4f} | 2021-2026 {v['auc_2021_2026']:.4f} | dal 2020 {v['auc_dal_2020']:.4f}")
    for c in COLORI:
        f = pf[c]
        if f.get("giorni"):
            print(f"  {c:7s} {f['giorni']:5d} gg ({f['quota_giorni']:4.1f}%)  crollo nel {f['frequenza']:5.1f}%  IC90 {f['ic90']}")

    # regole di accettazione, parte 7
    viola = pf["viola"].get("frequenza", 0) or 0
    R = {"R1": a >= 0.65 and ic[0] > 0.55, "R2": viola >= 2.5 * base * 100,
         "R3": pl95 < a, "R4": (a - arm) >= 0.02 or (abs(a - arm) < 0.02 and viola > 0)}
    res["regole"] = {k: bool(x) for k, x in R.items()}
    res["etichetta"] = "Coerente con i casi osservati" if all(R.values()) else "Non coerente"
    print("\nregole:", res["regole"], "->", res["etichetta"])

    # parte 9: falsi allarmi, episodi, replay
    allarme = idx >= 41
    res["falsi_allarmi"] = {}
    for per, m in (("1990-2026", d.index >= "1990-01-02"), ("2015-2026", ver)):
        aa = allarme & m & d["Y10"].notna()
        res["falsi_allarmi"][per] = {"giorni_allarme": int(aa.sum()),
                                     "senza_crollo": int(((aa) & (d["Y10"] == 0)).sum()),
                                     "quota_senza_crollo": round(float(((aa) & (d["Y10"] == 0)).sum() / max(1, aa.sum()) * 100), 1)}
    # episodi di calo >=10% e preavviso
    sp = d["sp500"]
    picco = sp.cummax()
    dd = sp / picco - 1
    ep, dentro = [], False
    for t in sp.index:
        if not dentro and dd[t] <= -0.10:
            dentro = True
            ep.append({"inizio_calo": str(t.date())})
        elif dentro and dd[t] >= -0.02:
            dentro = False
    # per ogni episodio: il massimo dell'indice nei 10 giorni prima che il calo del 10% fosse completato
    for e in ep:
        t = pd.Timestamp(e["inizio_calo"])
        fin = idx.index[(idx.index <= t)][-10:]
        mx = float(idx.reindex(fin).max()) if len(fin) else float("nan")
        e["indice_max_10gg_prima"] = None if np.isnan(mx) else round(mx, 1)
        e["preavviso"] = bool(mx >= 41) if not np.isnan(mx) else None
    res["episodi_10pc"] = ep
    con = sum(1 for e in ep if e["preavviso"])
    res["episodi_riassunto"] = {"totale": len(ep), "con_preavviso": con}
    print(f"\nepisodi di calo >=10%: {len(ep)}, con preavviso (giallo o peggio nei 10 gg prima): {con}")

    for giorno in ("2026-11-05", "2026-11-18", "2026-11-19", "2026-11-20", "2026-10-30", "2026-11-13"):
        t = pd.Timestamp(giorno)
        if t in idx.index:
            res.setdefault("replay", {})[giorno] = {"indice": round(float(idx[t]), 1), "fascia": str(fascia(idx)[t]),
                                                    "Y10": None if pd.isna(d["Y10"][t]) else int(d["Y10"][t])}
            print(f"  {giorno}: indice {idx[t]:.1f} ({fascia(idx)[t]})  crollo poi? {d['Y10'][t]}")

    # controllo assenza di sguardo al futuro (parte 2)
    spc = store.load("sp500").dropna()
    Xc = carica(spc.iloc[:-30])
    Sc = {"M1 media": Xc[[c for c in Xc.columns if any(c.startswith(f) for f in FAM)]].mean(axis=1, skipna=True)}
    if best == "M1 media":
        dref = mappa_indice(punteggi["M1 media"])
        dcut = mappa_indice(Sc["M1 media"])
        com = dcut.dropna().index.intersection(dref.dropna().index)[-1]
        res["controllo_futuro"] = {"data": str(com.date()), "differenza": round(float(abs(dcut[com] - dref[com])), 3)}
        print("controllo futuro:", res["controllo_futuro"])

    json.dump(res, open("scratch/crollo_risultati.json", "w"), ensure_ascii=False, indent=1)
    # serie per l'integrazione
    pd.DataFrame({"score": punteggi[best], "indice": idx, "Y10": d["Y10"]}).to_csv("scratch/crollo_serie.csv", index_label="date")
    print("\nsalvato scratch/crollo_risultati.json")


if __name__ == "__main__":
    main()
