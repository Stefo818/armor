"""Esegue PROTOCOLLO_REAZIONE_RAPIDA.md (commit 502dc30)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import store, indice_crollo as ic, grafico_indici as gi

X = ic.famiglie(); cal = X.index; sp = X["sp500"]
g = lambda sid, lag=0: ic._lag(store.load(sid).dropna(), lag).reindex(cal).ffill()
w = pd.Series(ic.PESI); w = w / w.sum()
base = sum(X[c].fillna(50.0) * w[c] for c in w.index)
vix, vix3 = g("vix"), g("vix3m")
r = np.log(sp).diff()
f_salto = (ic._pct(vix / vix.shift(5) - 1) + ic._pct(vix / vix.shift(10) - 1)) / 2
f_curva = ic._pct(vix / vix3)
f_liv = ic._pct(vix)
f_dn5 = ic._pct(r.clip(upper=0).rolling(5).std())
veloce = 0.30 * f_salto.fillna(50) + 0.25 * f_curva.fillna(50) + 0.20 * f_liv.fillna(50) + 0.25 * f_dn5.fillna(50)
v9, vv = g("cboe_vix9d_close", 1), g("cboe_vvix_vvix", 1)
f9 = ic._pct(v9 / vix).fillna(50); fvv = ic._pct(vv).fillna(50)
f9[f9.index < "2011-06-01"] = 50.0; fvv[fvv.index < "2007-01-01"] = 50.0
veloce2 = 0.30 * f_salto.fillna(50) + 0.10 * f_curva.fillna(50) + 0.20 * f_liv.fillna(50) + 0.15 * f9 + 0.15 * fvv + 0.10 * f_dn5.fillna(50)
C = {"0_attuale": base, "1_veloce": veloce, "2_veloce_dati_nuovi": veloce2,
     "3_massimo": pd.concat([ic._pct(base), ic._pct(veloce)], axis=1).max(axis=1)}

calmo, _ = gi._maschere(); calmo = calmo.reindex(cal).fillna(False).astype(bool)
picchi = [cal.searchsorted(pd.Timestamp(p)) for p in gi.PICCHI_ENDOGENI]
SEL, VER = list(range(7)), list(range(7, 12))
S = sp.to_numpy()
out = {}
for nome, sc in C.items():
    sc = sc[sc.index >= "1990-01-02"]
    cm_sel = sc[calmo.reindex(sc.index) & (sc.index <= "2007-12-31")].dropna()
    thr = float(cm_sel.quantile(0.95))
    al = (sc >= thr)
    falsi_post08 = float(al[calmo.reindex(sc.index) & (sc.index >= "2008-01-01")].mean() * 100)
    ep = []
    for k, p in enumerate(picchi):
        lo, hi = max(0, p - 10), min(len(cal) - 1, p + 40)
        fin = al.reindex(cal).fillna(False).to_numpy()[lo:hi + 1]
        if fin.any():
            t = lo + int(np.argmax(fin))
            minimo = S[p:p + 61].min()
            res = float(np.clip((S[t] - minimo) / (S[p] - minimo), 0, 1)) if S[p] > minimo else 0.0
            ep.append((t - p, res))
        else:
            ep.append((40, 0.0))   # nessun allarme: nessuna protezione (come scritto nel protocollo)
    ep_sel, ep_ver = [ep[i] for i in SEL], [ep[i] for i in VER]
    out[nome] = {"soglia": round(thr, 1), "falsi_calmi_dal_2008_%": round(falsi_post08, 1),
                 "residua_sel": round(np.mean([e[1] for e in ep_sel]), 2), "residua_ver": round(np.mean([e[1] for e in ep_ver]), 2),
                 "ritardo_mediano_sel": float(np.median([e[0] for e in ep_sel])), "ritardo_mediano_ver": float(np.median([e[0] for e in ep_ver])),
                 "per_picco": {gi.PICCHI_ENDOGENI[k]: [int(ep[k][0]), round(ep[k][1], 2)] for k in range(12)}}
b = out["0_attuale"]
for n, o in out.items():
    ok_b = o["falsi_calmi_dal_2008_%"] - b["falsi_calmi_dal_2008_%"] <= 1
    # lettura LETTERALE della regola (a) come scritta (residua piu' bassa di 0,10): contraria allo scopo, vedi esito
    o["passa_lettera"] = bool(n != "0_attuale" and b["residua_ver"] - o["residua_ver"] >= 0.10 and ok_b and o["residua_sel"] <= b["residua_sel"])
    # lettura secondo lo SCOPO (piu' discesa ancora davanti all'allarme: +0,10), con (b) e (c) uguali
    o["passa_scopo"] = bool(n != "0_attuale" and o["residua_ver"] - b["residua_ver"] >= 0.10 and ok_b and o["residua_sel"] >= b["residua_sel"])
json.dump(out, open("scratch/reazione_rapida_esito.json", "w"), indent=1, ensure_ascii=False)
for n, o in out.items():
    print(n, {k: v for k, v in o.items() if k != "per_picco"})
print(out["0_attuale"]["per_picco"]); print(out["2_veloce_dati_nuovi"]["per_picco"])
