import sys, requests, pandas as pd
T = ["^VXN","^RVX","^VXD","^OVX","^GVZ","^VIX9D","^VXEEM","^TNX","^FVX","^IRX","^TYX","LQD","JNK","TLT","SHY","EMB","MUB","KBE","IYR","^RUT","^SOX","^NYA","JPY=X","CHF=X","AUDUSD=X","^HSI","^KS11","^FTSE","^FCHI","XLY","XLP","SPLV","USMV","MTUM","QQQ","IWD","IWF","^VIX3M","^VIX6M","GLD"]
ok = {}
for t in T:
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=315532800&period2=1795000000&interval=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        j = r.json()["chart"]["result"][0]
        c = j["indicators"]["quote"][0]["close"]
        s = pd.Series(c, index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
        s = s[~s.index.duplicated(keep="last")]
        ok[t] = s
        print(f"{t:10s} {s.index[0].date()} {s.index[-1].date()} n={len(s)}")
    except Exception as e:
        print(f"{t:10s} NO {str(e)[:50]}")
pd.to_pickle(ok, "/tmp/nuovi_yahoo.pkl")
