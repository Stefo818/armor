import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from armor import store, territori as T, concentrazione as C
from classifica_40anni import ESTERNI
rng = np.random.default_rng(5)
P = {k: store.load("cn_" + k.lower()).dropna() for k in C.SIMBOLI}
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
R = T.calcola(P, sp); cal, caldo = R["cal"], R["caldo"]
TIPI = {"CREDITO": (["1990-07-16", "2007-10-09", "2011-04-29", "2023-02-02"], ["M3", "M5"]), "BOLLA": (["2000-03-24", "2022-01-03"], ["M1", "M0"]),
        "LEVA": (["1998-07-17", "2018-01-26", "2024-07-16"], ["M2", "M0"]), "VALUTE": (["1997-10-07"], ["M6"])}
ALTRI = ["1987-08-25", "1989-10-09"]
def punt(mecc):   # punteggio di un tipo: media dei suoi meccanismi caldi (0-1), disponibili
    c = caldo[mecc].astype(float); return c.mean(axis=1)
def fr(sc, d):    # frazione di sedute accese nelle 126 prima del picco
    pos = cal.searchsorted(pd.Timestamp(d)); return float(sc.iloc[pos - 126:pos + 1].mean())
def cat(sc, d):
    pos = cal.searchsorted(pd.Timestamp(d)); return bool((sc.iloc[pos - 126:pos + 1] > 0).any())
tutti = sum([v[0] for v in TIPI.values()], []) + ALTRI
vietati = pd.Series(False, index=cal)
for d in tutti + ESTERNI + ["1973-10-17"]:
    pos = cal.searchsorted(pd.Timestamp(d)); vietati.iloc[max(0, pos - 126):pos + 250] = True
casuali = np.flatnonzero((~vietati).to_numpy() & (np.arange(len(cal)) > 140))
out = {}
for t, (dd, mm) in TIPI.items():
    sc = punt(mm); propri = [fr(sc, d) for d in dd]
    altri = [fr(sc, d) for t2, (d2, _) in TIPI.items() if t2 != t for d in d2]
    nulli = [np.mean([float(sc.iloc[p - 126:p + 1].mean()) for p in rng.choice(casuali, len(dd), replace=False)]) for _ in range(500)]
    out[t] = {"meccanismi": mm, "picchi": dd, "frazione_propri": [round(x, 2) for x in propri], "media_propri": round(float(np.mean(propri)), 3), "media_altri_tipi": round(float(np.mean(altri)), 3),
              "media_casuali": round(float(np.mean(nulli)), 3), "p95_caso": round(float(np.percentile(nulli, 95)), 3), "catturati": sum(cat(sc, d) for d in dd), "su": len(dd),
              "oltre_caso": bool(np.mean(propri) > np.percentile(nulli, 95)), "piu_che_altri": bool(np.mean(propri) > np.mean(altri))}
    out[t]["esito"] = "riconosce" if (out[t]["catturati"] >= 3 and out[t]["oltre_caso"] and out[t]["piu_che_altri"]) else ("indizio" if (out[t]["oltre_caso"] and out[t]["piu_che_altri"]) else "non supportato")
    if len(dd) < 3 and out[t]["esito"] == "riconosce": out[t]["esito"] = "indizio"
# oggi
oggi = {}
for t, (dd, mm) in TIPI.items():
    sc = punt(mm); oggi[t] = {"acceso_oggi": round(float(sc.iloc[-1]), 2), "frazione_ultimi_126": round(float(sc.iloc[-126:].mean()), 2), "media_casuale_storica": out[t]["media_casuali"]}
json.dump({"tipi": out, "oggi": oggi}, open("scratch/tipi_esito.json", "w"), indent=1, ensure_ascii=False)
for t, r in out.items(): print(t, {k: v for k, v in r.items() if k not in ("picchi", "meccanismi")})
print(oggi)
