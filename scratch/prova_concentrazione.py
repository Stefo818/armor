import sys, time
sys.path.insert(0, "src")
from armor import concentrazione as c
t = time.time()
out = c.costruisci()
r = out.pop("_riga_registro")
print(time.time() - t)
print({k: v for k, v in out.items() if k not in ("serie",)})
print(r)
print({k: (len(v["v"]) if v else None) for k, v in out["serie"].items()})
