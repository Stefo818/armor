"""Prova dell'anticipo. Segue PROTOCOLLO_ANTICIPO.md."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import indice_crollo as ic, store, semafori  # noqa: E402
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from elementi_esterni import lag, pct_esp  # noqa: E402
from gara_indici import auc, ic90  # noqa: E402

X = ic.famiglie()
cal0 = X.index
crollo = ic.calcola_serie()
cal = crollo.index
sp = store.load("sp500").dropna().reindex(cal).ffill()
base = crollo["indice"]
X = X.reindex(cal)
L = lambda k: store.load(k).dropna()


def daily(s):
    p = pct_esp(s.dropna())
    return p.reindex(cal.union(p.index)).ffill().reindex(cal) * 100


REATT = ["f1_paura", "f2_salto", "f3_curva", "f7_tendenza", "f8_perdita", "f9_volat"]
R = X[REATT].mean(axis=1)
comp = {
    "cape": daily(L("cape_m")),
    "buffett": daily(lag(semafori.series_of("buffett").dropna(), 90)),
    "margin": daily(lag(L("margin_yoy"), 50)),
    "f5": X["f5_credito"], "f4": X["f4_protez"], "f6": X["f6_tassi"], "f10": X["f10_rotaz"], "f11": X["f11_bond"],
    "nfci": daily(L("nfci")), "liq": daily(-L("net_liq_13w")),
}
P = pd.concat(comp.values(), axis=1).mean(axis=1, skipna=True)
P[pd.concat(comp.values(), axis=1).notna().sum(axis=1) < 5] = np.nan
rk = lambda s: s.rank(pct=True)
cands = {"BASE": base, "R reattive": R, "P predisposizione": P}
cands["M5 massimo 5 giorni"] = base.rolling(5, min_periods=1).max()
cands["E3 media esponenziale 3"] = base.ewm(span=3, adjust=False).mean()
B1 = 0.5 * rk(base) + 0.5 * rk(P)
cands["B1 mista 50/50"] = B1
cands["B2 massimo 5 giorni di B1"] = B1.rolling(5, min_periods=1).max()

# perimetro e bersagli
fuori = finestra(cal, ESTERNI)
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
def minfut(n):
    return pd.concat([sp.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / sp - 1
vicino = (sp / sp.rolling(252, min_periods=120).max()) >= 0.97
Y = {}
for nome, n, s_ in (("B5", 5, 0.04), ("B10", 10, 0.06)):
    mn = minfut(n); y = (mn <= -s_).astype(float); y[mn.isna()] = np.nan; Y[nome] = y
CTRL = {"5g-3%": (5, 0.03), "21g-5%": (21, 0.05), "63g-8%": (63, 0.08)}
YC = {}
for nome, (n, s_) in CTRL.items():
    mn = minfut(n); y = (mn <= -s_).astype(float); y[mn.isna()] = np.nan; YC[nome] = y
sel = (~fuori) & (cal <= "2014-12-31"); ver = (~fuori) & (cal >= "2015-01-01")
out = {}

# ---------------- diagnosi 1: reattivita'
ret5_pass = sp.pct_change(5)
fut5 = minfut(5)
m = ~fuori
c_pass = base[m].corr(ret5_pass[m], method="spearman"); c_fut = base[m].corr(fut5[m], method="spearman")
print(f"DIAGNOSI 1: correlazione di Spearman dell'indice con i 5 giorni PRECEDENTI {c_pass:+.3f}; con il calo massimo dei 5 giorni SUCCESSIVI {c_fut:+.3f}")
for k in ("R reattive", "P predisposizione"):
    print(f"            {k}: precedenti {cands[k][m].corr(ret5_pass[m], method='spearman'):+.3f}  successivi {cands[k][m].corr(fut5[m], method='spearman'):+.3f}")
out["diag1"] = {"base_prec": round(c_pass, 3), "base_succ": round(c_fut, 3)}
# diagnosi 2: composizione
w = pd.Series(ic.PESI); w = w / w.sum()
print("DIAGNOSI 2: peso famiglie reattive nel punteggio:", round(float(w[[c for c in w.index if c in REATT]].sum()), 2), "su", round(float(w.sum()), 2))
out["diag2_peso_reattive"] = round(float(w[[c for c in w.index if c in REATT]].sum()), 2)

# ---------------- diagnosi 3: giorno prima delle crisi finanziarie
print("DIAGNOSI 3: indice il giorno prima del primo calo di almeno -3% in 5 sedute (da vicino ai massimi):")
pct_base = base.rank(pct=True)
d3 = []
for picco, calo, nat, causa in CLASSIFICA:
    if nat != "finanziaria" or picco < "1991-01-01":
        continue
    p0 = cal.searchsorted(pd.Timestamp(picco))
    fin = slice(max(0, p0 - 3), p0 + 150)
    sub = sp.iloc[fin]
    mn5 = (pd.concat([sub.shift(-i) for i in range(1, 6)], axis=1).min(axis=1) / sub - 1)
    hit = mn5[(mn5 <= -0.03) & vicino.iloc[fin]]
    if not len(hit):
        continue
    t = hit.index[0]; j = cal.get_loc(t)
    row = {"episodio": picco, "primo_calo": str(t.date()), "indice_giorno_prima": round(float(base.iloc[j - 1]), 0) if j > 0 else None,
           "P_giorno_prima": None if pd.isna(P.iloc[j - 1]) else round(float(P.iloc[j - 1]), 0), "indice_5_prima": round(float(base.iloc[j - 5]), 0),
           "indice_giorno_del_calo": round(float(base.iloc[j]), 0)}
    d3.append(row); print("  ", row)
out["diag3"] = d3

# ---------------- test principale
def episodi(y, m):
    pos = np.where((y[m] == 1).to_numpy())[0]
    return 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 20).sum())
for nome in Y:
    for per, mk in (("scelta", sel), ("verifica", ver)):
        mm = mk & vicino & Y[nome].notna()
        print(f"episodi indipendenti {nome} {per}: {episodi(Y[nome], mm)} su {int(mm.sum())} giorni, eventi {int(Y[nome][mm].sum())}")
        out[f"episodi_{nome}_{per}"] = episodi(Y[nome], mm)

# soglia del caso non necessaria per la regola di adozione (differenze contro BASE); IC per blocchi d'anno sulla differenza
res = {}
print(f"\n{'candidato':30s} " + " ".join(f"{b}-{p[:3]}" for b in Y for p in ("sce", "ver")) + " | controlli (sce/ver) delta vs BASE")
tab = {}
for k, s in cands.items():
    tab[k] = {}
    for nome in Y:
        for per, mk in (("scelta", sel), ("verifica", ver)):
            mm = mk & vicino & Y[nome].notna() & s.notna() & base.notna()
            tab[k][f"{nome}_{per}"] = float(auc(Y[nome][mm], s[mm])) if mm.sum() > 200 else np.nan
    for cn, yc in YC.items():
        for per, mk in (("scelta", sel), ("verifica", ver)):
            mm = mk & yc.notna() & s.notna() & base.notna()
            tab[k][f"{cn}_{per}"] = float(auc(yc[mm], s[mm])) if mm.sum() > 300 else np.nan
for k in cands:
    r = tab[k]
    print(f"{k:30s} " + " ".join(f"{r[f'{b}_{p}']:.3f}" for b in Y for p in ("scelta", "verifica")) + " | " +
          " ".join(f"{cn}:{r[f'{cn}_scelta']:.3f}/{r[f'{cn}_verifica']:.3f}" for cn in YC))
adot = []
for k in cands:
    if k == "BASE":
        continue
    b, r = tab["BASE"], tab[k]
    ok = all(r[f"{n}_{p}"] - b[f"{n}_{p}"] >= 0.03 for n in Y for p in ("scelta", "verifica"))
    ok &= all(r[f"{cn}_{p}"] - b[f"{cn}_{p}"] >= -0.01 for cn in YC for p in ("scelta", "verifica"))
    res[k] = {"delta": {kk: round(r[kk] - b[kk], 3) for kk in r}, "adottabile": bool(ok)}
    if ok:
        adot.append(k)
print("\nADOTTABILI:", adot)
out["tabella"] = {k: {kk: (None if np.isnan(v) else round(v, 4)) for kk, v in r.items()} for k, r in tab.items()}
out["adottabili"] = adot; out["delta"] = res
out["oggi"] = {k: (None if pd.isna(s.iloc[-1]) else round(float(s.iloc[-1]), 2)) for k, s in cands.items()}
print("OGGI:", out["oggi"])
json.dump(out, open("scratch/anticipo.json", "w"), ensure_ascii=False, indent=1, default=str)
