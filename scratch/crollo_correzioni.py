"""Correzioni richieste dall'audit esterno (GPT/Gemini) del 22 novembre 2026.

1. I pesi di M2: il protocollo è ambiguo. Si calcolano entrambe le letture e si pubblicano entrambe.
2. Il bootstrap di per_fascia() era rotto: con 41 giorni estraeva blocchi solo dalla prima metà, e
   restituiva un intervallo che non conteneva nemmeno la stima. Rifatto a blocchi di un anno su tutto il
   campione, ricalcolando la frequenza di fascia dentro ogni ricampionamento.
3. Numero di episodi indipendenti al posto del numero di giorni.
4. Metriche mancanti: richiamo, giorni di falso allarme, quota di giorni in allarme, anticipo per episodio.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from crollo_finanziarie import ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from crollo_ricerca import TRATTI, bersagli, carica  # noqa: E402

COLORI = ["verde", "grigio", "giallo", "rosso", "viola"]
# lettura A: come era nel codice, un peso per ogni variabile (somma grezza 1,55)
PESI_A = {"f1_paura": 0.30, "f3_curva": 0.30, "f5_credito": 0.15, "f7_tendenza": 0.25,
          "f8_perdita": 0.25, "f10_rotaz": 0.15, "f6_tassi": 0.15}
# lettura B: come la legge l'audit, il peso è del gruppo (somma esattamente 1,00)
PESI_B = {"f1_paura": 0.15, "f3_curva": 0.15, "f5_credito": 0.15, "f7_tendenza": 0.125,
          "f8_perdita": 0.125, "f10_rotaz": 0.15, "f6_tassi": 0.15}


def mappa(punteggio, dentro):
    q = punteggio[dentro].expanding(min_periods=500).rank(pct=True).reindex(punteggio.index)
    out = pd.Series(np.nan, index=punteggio.index)
    for a, b, lo, hi in TRATTI:
        m = (q >= a) & (q < b)
        out[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    return out.clip(1, 100)


def auc(y, s):
    m = (~pd.isna(y)) & (~pd.isna(s))
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2:
        return np.nan
    r = pd.Series(s).rank().to_numpy()
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def fascia(v):
    return pd.cut(v, [0, 35, 40, 60, 80, 100], labels=COLORI)


def bootstrap_anni(idx, y, zona, giri=2000, seed=4):
    """Intervalli a blocchi di un anno: i giorni vicini non sono osservazioni indipendenti.

    Si ricampionano anni interi e si ricalcola la frequenza dentro ogni fascia.
    """
    d = pd.DataFrame({"f": fascia(idx), "y": y, "anno": idx.index.year})[zona].dropna()
    anni = sorted(d["anno"].unique())
    rng = np.random.default_rng(seed)
    acc = {c: [] for c in COLORI}
    per_anno = {a: g for a, g in d.groupby("anno")}
    for _ in range(giri):
        pezzi = [per_anno[a] for a in rng.choice(anni, len(anni), replace=True)]
        camp = pd.concat(pezzi)
        for c in COLORI:
            s = camp[camp["f"] == c]["y"]
            if len(s) >= 5:
                acc[c].append(float(s.mean()))
    out = {}
    for c in COLORI:
        s = d[d["f"] == c]["y"]
        if len(s) == 0:
            continue
        v = acc[c]
        out[c] = {"giorni": int(len(s)), "quota_giorni": round(len(s) / len(d) * 100, 1),
                  "frequenza": round(float(s.mean()) * 100, 1),
                  "ic90": [round(float(np.percentile(v, 5)) * 100, 1), round(float(np.percentile(v, 95)) * 100, 1)] if len(v) > 50 else None,
                  "anni_con_dati": int(d[d["f"] == c]["anno"].nunique())}
    return out


def episodi_indipendenti(y, zona):
    """Blocchi contigui di giorni con bersaglio vero: sono gli episodi, non i giorni."""
    s = (y.where(zona) == 1).astype(int)
    grp = (s.diff() != 0).cumsum()[s == 1]
    return int(grp.nunique())


def main():
    X = carica()
    d = X.join(bersagli(X["sp500"]))
    d = d[d.index >= "1990-01-02"]
    cal = d.index
    fuori = finestra(cal, ESTERNI)
    for dd in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(dd))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
    buono = (~fuori) & d["Y10"].notna()
    ver = buono & (cal >= "2015-01-01")
    out = {}

    print("=== 1. I due modi di leggere i pesi di M2 ===")
    print("il protocollo dice: «paura e curva 0,30; credito 0,15; tendenza e perdita 0,25; rotazione 0,15; tassi 0,15 (normalizzati a 1)»")
    for nome, pesi in (("A: un peso per variabile (come nel codice)", PESI_A), ("B: il peso è del gruppo (come legge l'audit)", PESI_B)):
        w = pd.Series(pesi)
        w = w / w.sum()
        s = sum(d[c].fillna(50.0) * w[c] for c in w.index)
        a_sel = float(auc(d["Y10"][buono & (cal <= "2014-12-31")], s[buono & (cal <= "2014-12-31")]))
        a_ver = float(auc(d["Y10"][ver], s[ver]))
        idx = mappa(s, buono)
        pf = bootstrap_anni(idx, d["Y10"], ver)
        vio = pf.get("viola", {})
        out[nome] = {"auc_scelta": round(a_sel, 4), "auc_verifica": round(a_ver, 4), "fasce": pf}
        print(f"\n{nome}")
        print(f"  AUC scelta 1990-2014: {a_sel:.4f}   AUC verifica 2015-2026: {a_ver:.4f}")
        for c in COLORI:
            f = pf.get(c)
            if f:
                print(f"    {c:7s} {f['giorni']:5d} gg in {f['anni_con_dati']:2d} anni  crollo {f['frequenza']:5.1f}%  IC90 {f['ic90']}")

    base = float(d["Y10"][ver].mean()) * 100
    print(f"\nfrequenza di base nel periodo di verifica: {base:.1f}%  (soglia R2 = {base*2.5:.1f}%)")
    out["base_verifica"] = round(base, 1)
    out["soglia_R2"] = round(base * 2.5, 1)

    print("\n=== 2. Quante osservazioni indipendenti ci sono davvero ===")
    ne = episodi_indipendenti(d["Y10"], buono)
    nev = episodi_indipendenti(d["Y10"], ver)
    out["episodi_indipendenti"] = {"1990_2026": ne, "2015_2026": nev, "giorni_1990_2026": int(buono.sum()), "giorni_2015_2026": int(ver.sum())}
    print(f"  giorni nel sottoinsieme finanziario: {int(buono.sum())}, ma blocchi contigui di bersaglio vero: {ne}")
    print(f"  nel periodo di verifica: {int(ver.sum())} giorni, {nev} blocchi")
    print("  l'audit ha ragione: la dimensione vera del problema è vicina al numero di episodi, non di righe")

    # 3. metriche operative mancanti, sulla versione A (quella pubblicata)
    w = pd.Series(PESI_A)
    w = w / w.sum()
    sA = sum(d[c].fillna(50.0) * w[c] for c in w.index)
    idxA = mappa(sA, buono)
    print("\n=== 3. Metriche operative che mancavano (versione pubblicata, verifica 2015-2026) ===")
    print(f"{'soglia':24s} {'gg allarme':>10s} {'quota gg':>9s} {'precisione':>11s} {'richiamo':>9s} {'falsi gg':>9s}")
    met = {}
    for soglia, nome in ((41, "giallo o peggio"), (61, "rosso o viola"), (81, "solo viola")):
        al = ver & (idxA >= soglia)
        y = d["Y10"][ver]
        prec = float(d["Y10"][al].mean()) * 100 if al.sum() else float("nan")
        rich = float((al & (d["Y10"] == 1)).sum() / max(1, (ver & (d["Y10"] == 1)).sum())) * 100
        falsi = int((al & (d["Y10"] == 0)).sum())
        met[nome] = {"giorni_allarme": int(al.sum()), "quota_giorni": round(float(al.sum() / ver.sum()) * 100, 1),
                     "precisione": round(prec, 1), "richiamo": round(rich, 1), "giorni_falso_allarme": falsi}
        print(f"{nome:24s} {int(al.sum()):10d} {al.sum()/ver.sum()*100:8.1f}% {prec:10.1f}% {rich:8.1f}% {falsi:9d}")
    out["metriche_operative"] = met

    # 4. anticipo per episodio: quante sedute prima del -10% l'indice entra in giallo
    EP = [("1990-01-02", "1990-01-30"), ("1997-10-07", "1997-10-27"), ("1998-07-17", "1998-08-14"),
          ("1999-07-16", "1999-09-29"), ("2000-03-24", "2000-04-14"), ("2000-03-24", "2000-10-11"),
          ("2007-10-09", "2007-11-26"), ("2015-05-21", "2015-08-24"), ("2018-01-26", "2018-02-08"),
          ("2022-01-03", "2022-02-22"), ("2026-10-06", "2026-11-20")]
    print("\n=== 4. Anticipo per episodio: quante sedute di giallo prima che il calo arrivi al 10% ===")
    ant = []
    for mx, dn in EP:
        tmx, tdn = pd.Timestamp(mx), pd.Timestamp(dn)
        fin = cal[(cal >= tmx) & (cal <= tdn)]
        g = idxA.reindex(fin)
        primi = g[g >= 41]
        if len(primi):
            sedute = int(len(cal[(cal >= primi.index[0]) & (cal <= tdn)]))
            ant.append({"episodio": mx, "primo_giallo": str(primi.index[0].date()), "sedute_prima_del_meno10": sedute})
            print(f"  {mx} -> {dn}: primo giallo il {primi.index[0].date()}, {sedute} sedute prima del -10%")
        else:
            ant.append({"episodio": mx, "primo_giallo": None, "sedute_prima_del_meno10": 0})
            print(f"  {mx} -> {dn}: mai giallo prima")
    v = [a["sedute_prima_del_meno10"] for a in ant if a["sedute_prima_del_meno10"]]
    out["anticipo"] = {"per_episodio": ant, "mediana_sedute": int(np.median(v)) if v else None,
                       "episodi_con_anticipo": len(v), "episodi_totali": len(EP)}
    if v:
        print(f"  mediana: {int(np.median(v))} sedute, con anticipo in {len(v)} episodi su {len(EP)}")

    json.dump(out, open("scratch/crollo_correzioni.json", "w"), ensure_ascii=False, indent=1)
    print("\nsalvato scratch/crollo_correzioni.json")


if __name__ == "__main__":
    main()
