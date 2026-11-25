"""Minimi e correlazione. Segue PROTOCOLLO_MINIMI_CORRELAZIONE.md (commit f7b9de8, scritto prima dei calcoli)."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from armor import occasione as oc, store  # noqa: E402

S = oc.serie_archivio(); d = oc.calcola(S); ix = d.index
sp = d["sp"]

# correlazione media a coppie dei nove settori, 21 sedute
R = pd.DataFrame({k: v.dropna().reindex(ix).ffill().pct_change() for k, v in S["settori"].items()}).dropna()
vals = np.full(len(R), np.nan); A = R.to_numpy()
for i in range(21, len(R)):
    c = np.corrcoef(A[i - 20:i + 1].T); n = c.shape[0]
    vals[i] = (c.sum() - n) / (n * (n - 1))
C21 = pd.Series(vals, index=R.index).reindex(ix)
pe = lambda s, m=252: s.expanding(min_periods=m).rank(pct=True)
p90 = C21.rolling(63, min_periods=21).max()
rank_max = pe(C21).rolling(63, min_periods=21).max()
rientra = (100 * (-(C21 / p90 - 1) / 0.25).clip(0, 1)).where(rank_max >= 0.90, 0.0).where(C21.notna())
alta = pe(C21) * 100

VP, VS = list(oc.VOCI_P), list(oc.VOCI_S)
def comb(extra_p=None, extra_s=None):
    P = d[VP].copy(); Sv = d[VS].copy()
    if extra_p is not None: P["k"] = extra_p
    if extra_s is not None: Sv["k"] = extra_s
    pan = P.mean(axis=1).where(P.notna().sum(axis=1) >= 3); sv = Sv.mean(axis=1).where(Sv.notna().sum(axis=1) >= 3)
    prec = pan.rolling(63, min_periods=1).max()
    return pd.concat([prec, sv], axis=1).min(axis=1, skipna=False), sv
occ3, sv6 = comb(extra_s=rientra); occ4, _ = comb(extra_p=alta); occ5, _ = comb(extra_p=alta, extra_s=rientra)
cand = {"R0 Occasione": d["occasione"], "R1 Svolta": d["svolta"], "K1 correlazione che rientra": rientra, "K2 correlazione alta": alta,
        "K3 Occasione + rientra": occ3, "K4 Occasione + alta": occ4, "K5 Occasione + entrambe": occ5, "K6 Svolta a 6 voci": sv6}
Cd = pd.DataFrame(cand)

dd = sp / sp.rolling(252, min_periods=60).max() - 1
stress = (dd <= -0.08) & C21.notna()
mn = lambda h: pd.concat([sp.shift(-i) for i in range(1, h + 1)], axis=1).min(axis=1) / sp - 1
m21, m63 = mn(21), mn(63)
Y = {"T1 tiene a 1 mese": (m21 >= -0.03).astype(float).where(m21.notna()), "T2 tiene a 3 mesi": (m63 >= -0.05).astype(float).where(m63.notna())}
sel = stress & (ix <= "2012-12-31"); ver = stress & (ix >= "2013-01-01")

def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float); n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    r = pd.Series(s).rank().to_numpy(); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def episodi(m):
    pos = np.where(np.asarray(m))[0]; return 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 63).sum())

rng = np.random.default_rng(2511); out = {"eventi": {}}
print("giorni sotto stress: scelta", int(sel.sum()), "verifica", int(ver.sum()), flush=True)
for ev, y in Y.items():
    ms, mv = sel & y.notna(), ver & y.notna()
    ys, yv = y[ms], y[mv]; Cs, Cv = Cd[ms].fillna(0), Cd[mv].fillna(0)
    ep = (int(1 + (np.diff(np.where(ms)[0]) > 63).sum()), int(1 + (np.diff(np.where(mv)[0]) > 63).sum()))
    a_s = {k: auc(Cs[k], ys) for k in Cd}; a_v = {k: auc(Cv[k], yv) for k in Cd}
    anni = np.array(sorted(set(Cv.index.year))); gr = {a: np.where(Cv.index.year == a)[0] for a in anni}
    boot = {k: [] for k in Cd}
    for _ in range(500):
        sc = rng.choice(anni, len(anni)); idx = np.concatenate([gr[a] for a in sc]); yy = yv.to_numpy()[idx]
        for k in Cd: boot[k].append(auc(Cv[k].to_numpy()[idx], yy))
    ic = {k: (float(np.nanpercentile(boot[k], 5)), float(np.nanpercentile(boot[k], 95))) for k in Cd}
    best = []
    for _ in range(200):
        mp = dict(zip(anni, rng.permutation(anni))); fin = np.zeros(len(yv))
        for a in anni: fin[gr[a]] = np.resize(yv.to_numpy()[gr[mp[a]]], len(gr[a]))
        best.append(np.nanmax([auc(Cv[k], fin) for k in Cd]))
    sog = float(np.percentile(best, 95))
    print(f"\n=== {ev}: giorni scelta {len(ys)} verifica {len(yv)} | giorni positivi {int(ys.sum())}/{int(yv.sum())} | blocchi di stress {ep} | soglia del caso {sog:.3f}")
    for k in Cd: print(f"  {k:30s} scelta {a_s[k]:.3f}  verifica {a_v[k]:.3f}  IC90 [{ic[k][0]:.3f}, {ic[k][1]:.3f}]")
    out["eventi"][ev] = {"soglia": sog, "scelta": a_s, "verifica": a_v, "ic90": ic, "blocchi": ep}

print("\n=== REGOLE (K contro R0)")
pas = []
for k in Cd:
    if k.startswith("R"): continue
    b1 = all(out["eventi"][e]["scelta"][k] >= out["eventi"][e]["scelta"]["R0 Occasione"] + 0.03 and out["eventi"][e]["verifica"][k] >= out["eventi"][e]["verifica"]["R0 Occasione"] + 0.03 for e in Y)
    b2 = any(out["eventi"][e]["verifica"][k] > out["eventi"][e]["soglia"] for e in Y)
    b3 = any(out["eventi"][e]["ic90"][k][0] > 0.55 for e in Y)
    print(f"  {k:30s} B1 {int(b1)} B2 {int(b2)} B3 {int(b3)}")
    if b1 and b2 and b3: pas.append(k)
print("PASSANO:", pas or "nessuno")

# descrittivo: picco di correlazione e minimo di prezzo nelle discese >= 12%
print("\n=== Discese >= 12%: minimo di prezzo e picco di C21")
mx = sp.rolling(252, min_periods=60).max(); calo = sp / mx - 1
ep_list = []; i = 0; n = len(sp)
inn = (calo <= -0.12).to_numpy()
while i < n:
    if inn[i]:
        j = i
        while j + 1 < n and (inn[j + 1] or (j + 1 - i) < 5 or calo.iloc[j + 1] < -0.04) and not (calo.iloc[j + 1] >= -0.02): j += 1
        seg = sp.iloc[i:j + 1]; lo = seg.idxmin()
        pk = (calo.loc[:lo][calo.loc[:lo] == 0]).index
        ep_list.append((i, j, lo)); i = j + 126
    else: i += 1
dentro = 0; righe = []
for (i, j, lo) in ep_list:
    a = max(0, ix.get_loc(lo) - 126)   # finestra: 126 sedute prima del minimo fino a 21 dopo
    w = C21.iloc[a: ix.get_loc(lo) + 22].dropna()
    if len(w) < 30: continue
    pico = w.idxmax(); lag = int(ix.get_loc(pico) - ix.get_loc(lo)); v_min = float(C21.loc[lo]) if not np.isnan(C21.loc[lo]) else np.nan
    righe.append({"minimo": str(lo.date()), "calo": round(float(calo.loc[lo]) * 100, 1), "picco_C21": str(pico.date()), "sedute": lag, "C21_al_minimo": round(v_min, 2), "mediana_C21": round(float(C21.dropna().loc[:lo].median()), 2)})
    dentro += abs(lag) <= 10
    print(f"  minimo {lo.date()} ({calo.loc[lo]*100:.1f}%)  picco C21 {pico.date()}  scarto {lag:+d} sedute  C21 al minimo {v_min:.2f} (mediana storica {C21.dropna().loc[:lo].median():.2f})")
print(f"picco di correlazione entro ±10 sedute dal minimo: {dentro}/{len(righe)}")
out["descrittivo"] = {"episodi": righe, "dentro_10": int(dentro), "n": len(righe), "passano": pas}
json.dump(out, open("scratch/minimi_correlazione_esito.json", "w"), indent=1, default=float)
