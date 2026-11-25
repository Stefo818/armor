"""Segue PROTOCOLLO_MINIMI_2.md (scritto prima dei calcoli)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import occasione as oc, indice_crollo as ic
S = oc.serie_archivio(); d = oc.calcola(S); ix = d.index; sp = d["sp"]
cr = ic.calcola_serie()["indice"].reindex(ix).ffill()
M0 = 100 - d["occasione"]
M1 = pd.concat([d["panico_rec"], 100 - d["svolta"]], axis=1).min(axis=1, skipna=False)
dd = sp / sp.rolling(252, min_periods=60).max() - 1
stress = dd <= -0.08
M2 = M1.where(stress, 1.0)
C = pd.DataFrame({"M0 100-Minimi": M0, "M1 continua a scendere": M1, "M2 M1 solo sotto stress": M2, "M3 Indice crollo": cr})
mn = lambda h: pd.concat([sp.shift(-i) for i in range(1, h + 1)], axis=1).min(axis=1) / sp - 1
m21, m63 = mn(21), mn(63)
Y = {"F1 -5% in 21": (m21 <= -0.05).astype(float).where(m21.notna()), "F2 -8% in 63": (m63 <= -0.08).astype(float).where(m63.notna())}
def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float); n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    r = pd.Series(s).rank().to_numpy(); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
rng = np.random.default_rng(2512); out = {}
for per, pm in (("tutti i giorni", pd.Series(True, index=ix)), ("sotto stress", stress)):
    for ev, y in Y.items():
        ms = pm & y.notna() & (ix <= "2012-12-31"); mv = pm & y.notna() & (ix >= "2013-01-01")
        Cs, Cv, yv, ys = C[ms].fillna(0), C[mv].fillna(0), y[mv], y[ms]
        anni = np.array(sorted(set(Cv.index.year))); gr = {a: np.where(Cv.index.year == a)[0] for a in anni}
        boot = {k: [] for k in C}
        for _ in range(500):
            sc = rng.choice(anni, len(anni)); idx = np.concatenate([gr[a] for a in sc]); yy = yv.to_numpy()[idx]
            for k in C: boot[k].append(auc(Cv[k].to_numpy()[idx], yy))
        best = []
        for _ in range(200):
            mp = dict(zip(anni, rng.permutation(anni))); fin = np.zeros(len(yv))
            for a in anni: fin[gr[a]] = np.resize(yv.to_numpy()[gr[mp[a]]], len(gr[a]))
            best.append(np.nanmax([auc(Cv[k], fin) for k in C]))
        sog = float(np.percentile(best, 95))
        r = {"soglia_caso": sog, "giorni_scelta": int(len(ys)), "giorni_verifica": int(len(yv)), "base_verifica_%": float(yv.mean() * 100), "punteggi": {}}
        for k in C:
            r["punteggi"][k] = {"scelta": auc(Cs[k], ys), "verifica": auc(Cv[k], yv), "IC90": [float(np.nanpercentile(boot[k], 5)), float(np.nanpercentile(boot[k], 95))]}
        out[f"{per} | {ev}"] = r
        print(f"\n{per} | {ev}: giorni {len(ys)}/{len(yv)} base {r['base_verifica_%']:.1f}% soglia {sog:.3f}")
        for k, v in r["punteggi"].items(): print(f"  {k:28s} scelta {v['scelta']:.3f} verifica {v['verifica']:.3f} IC90 [{v['IC90'][0]:.3f},{v['IC90'][1]:.3f}]")
# rendimento medio a 21 sedute: M1 alto contro basso, sotto stress, verifica
fwd = sp.shift(-21) / sp - 1; v = stress & (ix >= "2013-01-01") & fwd.notna()
al, ba = v & (M1 >= 80), v & (M1 <= 20)
out["rend21"] = {"M1>=80": {"giorni": int(al.sum()), "media_%": float(fwd[al].mean() * 100) if al.sum() else None},
                 "M1<=20": {"giorni": int(ba.sum()), "media_%": float(fwd[ba].mean() * 100) if ba.sum() else None}}
out["oggi"] = {k: float(C[k].iloc[-1]) for k in C}
print("\nrend 21 sedute sotto stress (verifica):", out["rend21"]); print("oggi:", out["oggi"])
json.dump(out, open("scratch/minimi_2_esito.json", "w"), indent=1, default=float)
