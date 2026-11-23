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
def indice_da(fam):
    w_ = pd.Series({k: v for k, v in ic.PESI.items() if k in fam}); w_ = w_ / w_.sum()
    pun = sum(X[c].fillna(50.0) * w_[c] for c in w_.index)
    pq = pun[pun.index >= "1990-01-02"]
    q = pq.expanding(min_periods=ic.MIN_STORIA).rank(pct=True).reindex(pun.index)
    idx = pd.Series(np.nan, index=X.index)
    for a, b, lo, hi in ic.TRATTI:
        m_ = (q >= a) & (q < b); idx[m_] = lo + (q[m_] - a) / (b - a) * (hi - lo)
    return idx.clip(1, 100)
NP = indice_da([k for k in ic.PESI if k not in ("f1_paura", "f2_salto", "f3_curva")])
NP2 = indice_da([k for k in ic.PESI if k not in ("f1_paura", "f2_salto", "f3_curva", "f7_tendenza", "f8_perdita")])
RP = X[["f7_tendenza", "f8_perdita", "f9_volat"]].mean(axis=1)
cands = {"BASE": base, "NP senza paura": NP, "RP solo prezzo": RP, "NP2 senza paura e prezzo": NP2, "P predisposizione": P,
         "C1 0.5NP+0.5P": 0.5 * rk(NP) + 0.5 * rk(P), "C2 0.5NP2+0.5P": 0.5 * rk(NP2) + 0.5 * rk(P)}
print("pesi: paura nel punteggio attuale =", round(sum(ic.PESI[k] for k in ("f1_paura", "f3_curva")) / sum(ic.PESI.values()), 2), "(f1+f3; f2 non pesa)")

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
vixs = store.load("vix").dropna().reindex(cal).ffill()
vmx = pd.concat([vixs.shift(-i) for i in range(1, 6)], axis=1).max(axis=1)
yp = ((vmx / vixs - 1) >= 0.35).astype(float); yp[vmx.isna()] = np.nan; yp[vixs >= 22] = np.nan
YC["paura in arrivo"] = yp
sel = (~fuori) & (cal <= "2014-12-31"); ver = (~fuori) & (cal >= "2015-01-01")
out = {}

out = {}
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
    ok &= all(r[f"{cn}_{p}"] - b[f"{cn}_{p}"] >= -0.01 for cn in YC if cn != "paura in arrivo" for p in ("scelta", "verifica"))
    ok &= all(r[f"paura in arrivo_{p}"] - b[f"paura in arrivo_{p}"] >= -0.02 for p in ("scelta", "verifica"))
    res[k] = {"delta": {kk: round(r[kk] - b[kk], 3) for kk in r}, "adottabile": bool(ok)}
    if ok:
        adot.append(k)
print("\nADOTTABILI:", adot)
out["tabella"] = {k: {kk: (None if np.isnan(v) else round(v, 4)) for kk, v in r.items()} for k, r in tab.items()}
out["adottabili"] = adot; out["delta"] = res
out["oggi"] = {k: (None if pd.isna(s.iloc[-1]) else round(float(s.iloc[-1]), 2)) for k, s in cands.items()}
print("OGGI:", out["oggi"])
json.dump(out, open("scratch/anticipo2.json", "w"), ensure_ascii=False, indent=1, default=str)
