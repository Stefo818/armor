import sys
sys.path.insert(0, '/home/claude/armor/src')
from armor import store
for k in ("cape_m", "pe_m", "pe_trailing", "pe_fwd", "val_pe_sp500", "cape", "equity_value", "gdp", "erp"):
    try:
        s = store.load(k).dropna()
        print(f"{k:14s} n={len(s):6d} {s.index[0].date()} -> {s.index[-1].date()} ultimo={s.iloc[-1]:.4g}  mediana={s.median():.4g} p25={s.quantile(.25):.4g} p75={s.quantile(.75):.4g} p90={s.quantile(.9):.4g}")
    except Exception as e:
        print(k, "ERR", str(e)[:60])
