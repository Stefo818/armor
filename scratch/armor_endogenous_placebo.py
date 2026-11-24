# -*- coding: utf-8 -*-
"""Placebo per armor_endogenous_lab.py: quanto vale «il migliore su N prove» per puro caso?
Le etichette (calo si/no) vengono spostate in modo circolare di un numero casuale di mesi rispetto alle variabili:
resta l'autocorrelazione, sparisce il legame con le variabili. Si ripete tutto il laboratorio e si tiene il miglior
punto di abilita' (Brier Skill) fra tutte le combinazioni: e' la soglia che un risultato vero deve superare."""
import json
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "scratch")
import armor_endogenous_lab as L  # noqa: E402

N_PROVE = int(sys.argv[1]) if len(sys.argv) > 1 else 8
rng = np.random.default_rng(2026)
p = L.load("sp500")
F, groups = L.build_features(p, "sp500")
months = p.groupby([p.index.year, p.index.month]).tail(1).index
near = (p / p.rolling(252, min_periods=120).max() - 1).reindex(months) >= -0.05
Fm = F.reindex(months)
HOR = [("dd63_8", 63, -0.08, 100), ("dd126_10", 126, -0.10, 200), ("dd252_15", 252, -0.15, 380)]
t0 = time.time(); best_real, null_best = {}, {h[0]: [] for h in HOR}
for lab, h, thr, emb in HOR:
    yd = (L.forward_min_dd(p, h) <= thr).astype(float).where(L.forward_min_dd(p, h).notna())
    y = yd.reindex(months); mask = near & y.notna()
    pos = np.flatnonzero(mask.to_numpy())
    best_real[lab] = None
    for it in range(N_PROVE + 1):
        yy = y.loc[mask].copy()
        if it > 0:   # placebo: etichette spostate in modo circolare
            k = int(rng.integers(12, len(yy) - 12)); yy = pd.Series(np.roll(yy.to_numpy(), k), index=yy.index)
        bs = []
        for g, cols in groups.items():
            if g in ("breadth_sensitivity_only", "BIS_DSR_only") or not cols:
                continue
            start = "2010-01-31" if g in ("price_baseline", "credit_funding") else "2015-01-31"
            for mn in ("LOGIT_L2", "HIST_GRADIENT_BOOSTING"):
                r = L.walk_forward(Fm.loc[mask, cols], yy, mn, start=start, embargo_days=emb)
                v = r.get("brier_skill_vs_base_train")
                if v is not None: bs.append(v)
        mx = max(bs) if bs else np.nan
        if it == 0: best_real[lab] = mx
        else: null_best[lab].append(mx)
    print(lab, "migliore reale", round(best_real[lab], 4), "| migliore per caso (media, 95°):", round(float(np.nanmean(null_best[lab])), 4), round(float(np.nanpercentile(null_best[lab], 95)), 4), f"({time.time() - t0:.0f}s)", flush=True)
json.dump({"prove": N_PROVE, "migliore_reale": best_real, "migliore_caso": null_best}, open("scratch/armor_endogenous_placebo_esito.json", "w"), indent=1)
