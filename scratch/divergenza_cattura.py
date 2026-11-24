import sys, numpy as np, pandas as pd
sys.path.insert(0, "scratch")
exec(open("scratch/divergenza.py").read().split("res = {")[0])
EV = ["1990-07-16", "1997-10-07", "1998-07-17", "2000-03-24", "2007-10-09", "2010-04-23", "2011-04-29", "2018-01-26", "2022-01-03"]
pos = [cal.searchsorted(pd.Timestamp(d)) for d in EV]
rng2 = np.random.default_rng(3); n = len(cal)
for sn in ("D1 lenta", "D2 veloce", "D3 alto"):
    st = stati[sn].to_numpy().astype(bool)
    def cnt(x): return sum(bool(x[p - 126:p + 1].any()) for p in pos)
    obs = cnt(st); nul = [cnt(np.roll(st, int(rng2.integers(504, n - 504)))) for _ in range(1000)]
    print(sn, "catturati", obs, "su 9; caso: media", round(np.mean(nul), 2), "p(>=obs)", round(float(np.mean(np.array(nul) >= obs)), 3))
