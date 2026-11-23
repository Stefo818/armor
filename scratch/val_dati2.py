import sys
sys.path.insert(0, '/home/claude/armor/src')
from armor import store
for k in ("cape_m", "pe_m"):
    print(k, store.load(k).dropna().tail(6).round(2).to_dict())
