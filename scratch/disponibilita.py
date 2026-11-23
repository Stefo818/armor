import sys
sys.path.insert(0, '/home/claude/armor/src')
import pandas as pd
from armor import store
for k in ("t10y2y", "t10y3m", "fedfunds", "sahm", "icsa", "neworder", "philly", "empire", "permit_yoy", "breadth200", "breadth50", "nh_nl",
          "rel_eqw", "baa10y", "baa_d", "dgs10", "margin_debt", "margin_yoy", "margin_sp", "skew", "gold", "dxy", "usd_broad", "eurusd", "umcsent",
          "fear_greed", "nikkei", "kre", "cape", "hy_oas"):
    try:
        s = store.load(k).dropna()
        print(f"{k:12s} n={len(s):6d}  {s.index[0].date()} -> {s.index[-1].date()}  freq~{(s.index[-1]-s.index[0]).days/max(1,len(s)):.1f}g  ultimo={s.iloc[-1]:.3g}")
    except Exception as e:  # noqa: BLE001
        print(k, "ERRORE", str(e)[:60])
