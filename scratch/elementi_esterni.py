"""Prova degli elementi spia suggeriti da due testi esterni. Segue PROTOCOLLO_ELEMENTI_ESTERNI.md (nessuna regola cambiata dopo la pubblicazione)."""
import json
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import indice_crollo as ic  # noqa: E402
from armor import store  # noqa: E402
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from gara_indici import auc, ic90  # noqa: E402

ORIZZONTI = {"una settimana": (5, 0.03), "un mese": (21, 0.05), "tre mesi": (63, 0.08)}


def jpy() -> pd.Series | None:
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/JPY=X?period1=820454400&period2=1795000000&interval=1d",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        j = r.json()["chart"]["result"][0]
        s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
        s = s[~s.index.duplicated()]
        return s if len(s) > 3000 else None
    except Exception as e:  # noqa: BLE001
        print("JPY non scaricabile:", str(e)[:80])
        return None


def lag(s: pd.Series, giorni: int) -> pd.Series:
    s = s.dropna().copy()
    s.index = s.index + pd.Timedelta(days=giorni)
    return s[~s.index.duplicated(keep="last")]


def pct_esp(s: pd.Series) -> pd.Series:
    s = s.dropna()
    nativo_mensile = len(s) > 10 and (s.index[-1] - s.index[0]).days / len(s) > 10
    return s.expanding(min_periods=60 if nativo_mensile else 252).rank(pct=True)


def main():
    h = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
    crollo = ic.calcola_serie()
    sp = store.load("sp500").dropna()
    cal = h.index.intersection(sp.index).intersection(crollo.index)
    spx = sp.loc[cal]
    L = lambda k: store.load(k).dropna()

    # --- serie grezze dei candidati (orientate: piu' alto = piu' rischio), con i ritardi di pubblicazione
    raw = {}
    t2, t3 = L("t10y2y"), L("t10y3m")
    raw["C01 curva 10a-2a invertita"] = -t2
    raw["C02 curva 10a-3m invertita"] = -t3

    def disinv(t):
        inv = (t < 0).rolling(252, min_periods=1).max() > 0
        return (t.diff(63).clip(lower=0)).where(inv, 0.0)
    raw["C03 disinversione 2a-10a"] = disinv(t2)
    raw["C04 disinversione 3m-10a"] = disinv(t3)
    raw["C05 ciclo di rialzi dei tassi"] = L("fedfunds").diff(252)
    raw["C06 regola di Sahm"] = lag(L("sahm"), 35)
    raw["C07 indagine manifatturiera"] = -lag(L("philly"), 20)
    no = L("neworder")
    raw["C08 ordini beni durevoli"] = -lag(no.pct_change(12) * 100, 35)
    raw["C09 permessi di costruzione"] = -lag(L("permit_yoy"), 45)
    b = L("baa10y")
    raw["C10 impulso del credito"] = b.diff(10)
    raw["C11 livello spread credito"] = b
    secs = [L(f"sec_{k}") for k in ("xlb", "xlc", "xle", "xlf", "xli", "xlk", "xlp", "xlre", "xlu", "xlv", "xly")]
    sec = pd.concat(secs, axis=1).sort_index()
    sotto = (sec < sec.rolling(200, min_periods=150).mean()).where(sec.rolling(200, min_periods=150).mean().notna())
    n_sotto = (sotto.sum(axis=1) / sotto.notna().sum(axis=1).replace(0, np.nan)) * 9.0
    n_sotto = n_sotto[sotto.notna().sum(axis=1) >= 8]
    vicino = (sp / sp.rolling(252, min_periods=120).max()) >= 0.95
    raw["C12 ampiezza settori con indice vicino ai massimi"] = n_sotto.where(vicino.reindex(n_sotto.index).fillna(False), 0.0)
    raw["C13 ampiezza settori semplice"] = n_sotto
    rs = (L("rsp") / L("spy").reindex(L("rsp").index)).dropna()
    raw["C14 ampiezza a pesi uguali"] = -rs.pct_change(63)
    my = lag(L("margin_yoy"), 50)
    raw["C15 debito a margine"] = my
    r252 = (sp.pct_change(252) * 100)
    raw["C16 debito a margine contro prezzi"] = (my - r252.reindex(my.index, method="ffill")).dropna()
    raw["C17 SKEW"] = L("skew")
    raw["C18 oro"] = L("gold").pct_change(63)
    raw["C19 dollaro"] = L("dxy").pct_change(21)
    y = jpy()
    if y is not None:
        raw["C20 yen forte"] = -y.diff(21) / y
    else:
        print("C20 escluso: serie del cambio con yen non disponibile")
    raw["C21 euforia dei consumatori"] = lag(L("umcsent"), 40)

    # --- punteggio = percentuale espansa, portata sul calendario giornaliero
    cand = {}
    for k, s in raw.items():
        p = pct_esp(s.dropna())
        cand[k] = p.reindex(cal.union(p.index)).ffill().reindex(cal)
    base = (crollo["indice"].reindex(cal))
    base_p = pct_esp(base).reindex(cal)

    # --- bersagli e perimetro
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

    out = {"candidati": {}, "soglia_caso_95": None}
    # --- soglia del caso: migliore su N prove con bersagli mescolati a blocchi d'anno
    rng = np.random.default_rng(23)
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
    out["soglia_caso_95"] = round(soglia, 4)
    print(f"soglia del caso (migliore su ~63 prove, 95° percentile): {soglia:.4f}")

    # --- P1 e P2
    rk = lambda s: s.rank(pct=True)
    print(f"{'candidato':52s} {'orizzonte':14s} {'scelta':>7s} {'verif.':>7s} {'IC90 verifica':>16s} {'P1':>4s} | {'dBase sel':>9s} {'dBase ver':>9s}")
    for k, s in cand.items():
        out["candidati"][k] = {}
        for ori in ORIZZONTI:
            a_s, a_v = auc(Y[ori][sel], s[sel]), auc(Y[ori][ver], s[ver])
            if np.isnan(a_v):
                continue
            ic_ = ic90(Y[ori][ver], s[ver])
            p1 = bool(a_v >= 0.60 and ic_ and ic_[0] > 0.50 and a_v > soglia)
            # valore aggiunto: base contro misto 0,8/0,2 sugli stessi giorni
            d = {}
            for nome, m in (("sel", sel), ("ver", ver)):
                mm = m & s.notna() & base_p.notna()
                if mm.sum() < 300:
                    d[nome] = None
                    continue
                b_auc = auc(Y[ori][mm], base_p[mm])
                mis = 0.8 * rk(base_p[mm]) + 0.2 * rk(s[mm])
                d[nome] = round(float(auc(Y[ori][mm], mis) - b_auc), 4)
            out["candidati"][k][ori] = {"auc_scelta": None if np.isnan(a_s) else round(float(a_s), 4), "auc_verifica": round(float(a_v), 4),
                                        "ic90": ic_, "P1": p1, "dBase_scelta": d["sel"], "dBase_verifica": d["ver"]}
            print(f"{k:52s} {ori:14s} {a_s if not np.isnan(a_s) else float('nan'):7.3f} {a_v:7.3f} {str(ic_):>16s} {'SI' if p1 else '-':>4s} | {d['sel'] if d['sel'] is not None else float('nan'):9.4f} {d['ver'] if d['ver'] is not None else float('nan'):9.4f}")

    # regola di adozione P2
    ado = []
    for k, per in out["candidati"].items():
        buoni, cattivi = 0, 0
        for ori, r in per.items():
            ds, dv = r["dBase_scelta"], r["dBase_verifica"]
            if ds is None or dv is None:
                continue
            if ds >= 0.01 and dv >= 0.01:
                buoni += 1
            if ds < -0.01 or dv < -0.01:
                cattivi += 1
        if buoni >= 2 and cattivi == 0:
            ado.append(k)
    out["P2_adottabili"] = ado
    out["P1_promossi"] = sorted({k for k, per in out["candidati"].items() for r in per.values() if r["P1"]})
    print("\nP1 promossi:", out["P1_promossi"])
    print("P2 adottabili:", ado)

    # --- P3: il triangolo
    def p80(k):
        return cand[k] >= 0.80
    A = p80("C10 impulso del credito")
    Bc = p80("C03 disinversione 2a-10a") & (raw["C03 disinversione 2a-10a"].reindex(cal, method="ffill") > 0)
    Cc = (cand["C12 ampiezza settori con indice vicino ai massimi"].notna() &
          (raw["C12 ampiezza settori con indice vicino ai massimi"].reindex(cal, method="ffill") >= 3)) & p80("C15 debito a margine")
    tri = (A & Bc & Cc).fillna(False)
    due = ((A.astype(int) + Bc.astype(int) + Cc.astype(int)) >= 2).fillna(False)
    y63 = Y["tre mesi"]
    base63 = float(y63[ver | sel].mean())
    res = {"base_calo8_63": round(base63 * 100, 1)}
    for nome, f in (("A (impulso del credito)", A), ("B (disinversione)", Bc), ("C (ampiezza + debito)", Cc), ("tutte e tre", tri), ("almeno due", due)):
        m = f & (~fuori) & y63.notna()
        epi = int((m.astype(int).diff().fillna(0) == 1).sum())
        # episodi indipendenti: separati da 60 sedute
        pos = np.where(m.to_numpy())[0]
        ind = 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 60).sum())
        res[nome] = {"giorni": int(m.sum()), "episodi_indipendenti": ind,
                     "calo8_entro_63_%": None if m.sum() == 0 else round(float(y63[m].mean()) * 100, 1)}
        print(f"P3 {nome:26s} giorni {int(m.sum()):5d}  episodi {ind:3d}  calo>=8% entro 63 sedute: {res[nome]['calo8_entro_63_%']}%  (base {base63*100:.1f}%)")
    for nome, f in (("almeno due, SOLO scelta (fino al 2014)", due & sel), ("almeno due, SOLO verifica (dal 2015)", due & ver)):
        m = f & y63.notna()
        pos = np.where(m.to_numpy())[0]
        ind = 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 60).sum())
        bp = float(y63[(sel if "scelta" in nome else ver) & y63.notna()].mean()) * 100
        res[nome] = {"giorni": int(m.sum()), "episodi_indipendenti": ind, "calo8_entro_63_%": None if m.sum() == 0 else round(float(y63[m].mean()) * 100, 1), "base_periodo_%": round(bp, 1)}
        print(f"P3 {nome:42s} giorni {int(m.sum()):5d} episodi {ind:3d} calo>=8%: {res[nome]['calo8_entro_63_%']}%  (base del periodo {bp:.1f}%)")
    # richiamo sulle crisi finanziarie
    rich = []
    for picco, calo, nat, causa in CLASSIFICA:
        if nat != "finanziaria":
            continue
        if picco < "1991-01-01":      # picchi prima dell'inizio dei dati (1990): non valutabili
            continue
        pi = cal.searchsorted(pd.Timestamp(picco))
        if pi >= len(cal):
            continue
        liv = spx.iloc[pi]
        dopo = spx.iloc[pi:pi + 150]       # il calo di QUELL'episodio: entro 150 sedute dal picco
        cross = dopo[dopo <= liv * 0.90]
        d10 = cross.index[0] if len(cross) else dopo.idxmin()
        j = cal.searchsorted(d10)
        w = slice(max(0, j - 63), j + 1)
        rich.append({"picco": picco, "d10": str(d10.date()), "calo": calo,
                     "triangolo": bool(tri.iloc[w].any()), "almeno_due": bool(due.iloc[w].any()),
                     "A": bool(A.iloc[w].any()), "B": bool(Bc.iloc[w].any()), "C": bool(Cc.iloc[w].any())})
    res["richiamo"] = rich
    n = len(rich)
    print(f"\nRichiamo su {n} crisi finanziarie (63 sedute prima del -10%): triangolo {sum(r['triangolo'] for r in rich)}/{n}, "
          f"almeno due {sum(r['almeno_due'] for r in rich)}/{n}, A {sum(r['A'] for r in rich)}, B {sum(r['B'] for r in rich)}, C {sum(r['C'] for r in rich)}")
    for r in rich:
        print("  ", r["picco"], r["d10"], f"{r['calo']}%", "tri" if r["triangolo"] else "---", "due" if r["almeno_due"] else "---",
              "A" if r["A"] else "-", "B" if r["B"] else "-", "C" if r["C"] else "-")
    out["P3"] = res
    # oggi
    out["oggi"] = {k: (None if pd.isna(s.iloc[-1]) else round(float(s.iloc[-1]), 3)) for k, s in cand.items()}
    out["oggi"]["triangolo_acceso"] = bool(tri.iloc[-1]); out["oggi"]["almeno_due"] = bool(due.iloc[-1])
    out["oggi"]["A"] = bool(A.iloc[-1]); out["oggi"]["B"] = bool(Bc.iloc[-1]); out["oggi"]["C"] = bool(Cc.iloc[-1])
    print("\noggi:", {k: v for k, v in out["oggi"].items() if k in ("triangolo_acceso", "almeno_due", "A", "B", "C")})
    json.dump(out, open("scratch/elementi_esterni.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
