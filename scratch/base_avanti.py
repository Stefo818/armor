import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import concentrazione as c, store
P = {k: store.load("cn_" + k.lower()) for k in c.SIMBOLI}
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
m = c.calcola(P, sp); m = m[m.livello.notna()]
p = sp.reindex(m.index)
res = {}
for h in (84, 126):
    fwd = pd.concat([p.shift(-i) for i in range(1, h + 1)], axis=1).min(axis=1) / p - 1
    ok = p.shift(-h).notna() & (m.index >= "1990-01-01")
    for th in (0.05, 0.08, 0.12):
        y = (fwd <= -th)
        res[f"h{h}_{int(th*100)}"] = {"base": round(float(y[ok].mean()), 3), "S1": round(float(y[ok & m.S1].mean()), 3), "n_S1": int((ok & m.S1).sum()),
                                     "rip": round(float(y[ok & m.riprezzamento].mean()), 3), "n_rip": int((ok & m.riprezzamento).sum()),
                                     "livello>=0.8": round(float(y[ok & (m.livello >= .8)].mean()), 3)}
res["ep_S1_dal1990"] = len([i for i in c.inizi_episodi(m.S1) if m.index[i] >= pd.Timestamp("1990-01-01")])
res["ep_rip_dal1990"] = len([i for i in c.inizi_episodi(m.riprezzamento) if m.index[i] >= pd.Timestamp("1990-01-01")])
res["giorni_S1_dal1990"] = int((m.S1 & (m.index >= "1990-01-01")).sum())
res["ultima_S1"] = str(m.index[np.flatnonzero(m.S1.to_numpy())[-1]].date())
print(json.dumps(res, indent=1))
