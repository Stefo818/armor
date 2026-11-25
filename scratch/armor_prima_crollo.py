"""Medie degli indici nelle settimane prima dei crolli NATI DENTRO la finanza (lista di PROTOCOLLO_TERRITORI.md).
Regola per scegliere la finestra, fissata PRIMA di guardare i numeri: tra 10, 20 e 40 sedute si prende quella in cui,
sui 4 indici principali (armor, crollo, super, stato), la quota di episodi con media sopra la media dei mercati calmi e' piu' alta;
a parita' la piu' lunga (meno rumore). Ogni episodio pesa uno."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src")
from armor import grafico_indici as g, store
PICCHI = ["1990-07-16", "1997-10-07", "1998-07-17", "2000-03-24", "2007-10-09", "2010-04-23", "2011-04-29", "2018-01-26", "2018-09-20", "2022-01-03", "2023-02-02", "2024-07-16"]
d = g.dati()
def serie(k):
    r = d[k]; t = pd.to_datetime(pd.Series(r["dt"]).cumsum() + r["t0"], unit="D")
    s = pd.Series([x / 10 for x in r["v"]], index=t.values); return s[~s.index.duplicated()]
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()].loc["1989-01-01":]
calmo, _ = g._maschere()
def medie_episodi(s, n):
    out = []
    for p in PICCHI:
        p = pd.Timestamp(p)
        if p not in sp.index: p = sp.index[sp.index.searchsorted(p)]
        i = sp.index.get_loc(p); a = sp.index[max(0, i - n + 1)]
        w = s[(s.index >= a) & (s.index <= p + pd.Timedelta(days=1))]
        out.append(float(w.mean()) if len(w) else np.nan)
    return out
def calmi(s):
    z = calmo.reindex(s.index, method="ffill", tolerance=pd.Timedelta(days=7)); z = z.fillna(False).astype(bool).to_numpy()
    return float(s[z].mean())
princ = ["armor", "crollo", "super", "stato"]
print("Episodi sopra la media dei mercati calmi (su 12), per finestra:")
res = {}
for n in (10, 20, 40):
    q = []
    for k in princ:
        s = serie(k); m = np.array(medie_episodi(s, n)); c = calmi(s)
        q.append(int((m > c).sum()))
    res[n] = sum(q); print(n, "sedute:", q, "totale", sum(q))
scelta = max((10, 20, 40), key=lambda n: (res[n], n)); print("FINESTRA SCELTA:", scelta)
print("\nTabella per episodio, finestra", scelta)
tab = pd.DataFrame({k: medie_episodi(serie(k), scelta) for k in princ}, index=PICCHI).round(1)
print(tab.to_string())
print("\nMedia degli episodi / calmi / storica")
for k in princ:
    s = serie(k); print(f"{k:7s} prima={np.nanmean(medie_episodi(s, scelta)):5.1f}  calmi={calmi(s):5.1f}  storica={s.mean():5.1f}")
