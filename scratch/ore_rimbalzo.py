"""Il «rimbalzo atteso dopo i cali forti» esiste davvero? Verifica su due anni di dati orari.

Nel codice (ore.py) c'e' una deriva positiva fissa applicata ogni volta che i futures sono scesi di
almeno l'1% nelle ultime 24 ore. E' l'unica cosa che inclina la previsione quando il mercato e' aperto,
perche' li' il «gap» vale zero. Era stata tarata su 2024-2026. Qui si rimisura e si guarda se tiene
anche quando il mercato e' in discesa.
"""
import json
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, "src")
from armor import store  # noqa: E402

H = {"User-Agent": "Mozilla/5.0"}


def orari(sym, giorni=730):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1h&range={giorni}d"
    j = requests.get(u, headers=H, timeout=60).json()["chart"]["result"][0]
    c = j["indicators"]["quote"][0]["close"]
    s = pd.Series(c, index=pd.to_datetime(j["timestamp"], unit="s", utc=True)).dropna()
    return s[~s.index.duplicated()]


es = orari("ES=F")
print(f"futures orari: {len(es)} ore, dal {es.index[0].date()} al {es.index[-1].date()}")
sp = store.load("sp500").dropna()
ma200 = sp.rolling(200).mean()
picco = sp.rolling(252, min_periods=60).max()
giorno = es.index.tz_convert("UTC").normalize().tz_localize(None)
sopra_ma = pd.Series(giorno, index=es.index).map((sp > ma200).reindex(sp.index).to_dict()).ffill()
dd = pd.Series(giorno, index=es.index).map((sp / picco - 1).to_dict()).ffill()

calo24 = es / es.shift(24) - 1
out = {}
print(f"\n{'situazione':40s} {'ore':>7s}  " + "  ".join(f"{h:>2d}h sale" for h in (1, 3, 6, 12)))
CASI = [
    ("tutte le ore", pd.Series(True, index=es.index)),
    ("dopo un calo dei futures >=1% in 24h", calo24 <= -0.01),
    ("   ...con l'indice sopra la media 200gg", (calo24 <= -0.01) & (sopra_ma == True)),   # noqa: E712
    ("   ...con l'indice sotto la media 200gg", (calo24 <= -0.01) & (sopra_ma == False)),  # noqa: E712
    ("   ...e il mercato oltre -7% dal massimo", (calo24 <= -0.01) & (dd <= -0.07)),
    ("dopo un calo >=2% in 24h", calo24 <= -0.02),
    ("mercato oltre -7% dal massimo (sempre)", dd <= -0.07),
]
for nome, m in CASI:
    riga = {}
    txt = f"{nome:40s} {int(m.sum()):7d}  "
    for h in (1, 3, 6, 12):
        f = es.shift(-h) / es - 1
        v = f[m].dropna()
        if len(v) < 50:
            txt += "    -   "
            continue
        riga[f"{h}h"] = {"ore": int(len(v)), "sale": round(float((v > 0).mean()) * 100, 1),
                         "mediana": round(float(v.median()) * 100, 3)}
        txt += f"  {(v>0).mean()*100:5.1f}%"
    out[nome] = riga
    print(txt)

print("\nmediana del movimento (%), stessi casi:")
for nome, m in CASI:
    txt = f"{nome:40s}         "
    for h in (1, 3, 6, 12):
        v = (es.shift(-h) / es - 1)[m].dropna()
        txt += f"  {v.median()*100:+6.3f}" if len(v) >= 50 else "       -"
    print(txt)

# cosa diceva la regola il 19 e 20 novembre
print("\n=== il 19 e 20 novembre: la regola del rimbalzo era accesa? ===")
for g in ("2026-11-19", "2026-11-20"):
    m = (es.index.tz_convert("UTC").strftime("%Y-%m-%d") == g)
    if m.sum() == 0:
        continue
    acc = (calo24[m] <= -0.01).mean() * 100
    mov = (es[m].iloc[-1] / es[m].iloc[0] - 1) * 100
    print(f"  {g}: accesa nel {acc:.0f}% delle ore; i futures quel giorno hanno fatto {mov:+.2f}%")

json.dump(out, open("scratch/ore_rimbalzo.json", "w"), ensure_ascii=False, indent=1)
print("\nsalvato")
