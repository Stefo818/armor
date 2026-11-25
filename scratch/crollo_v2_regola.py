"""Ricalcola la riga «Settimana a rischio sopra la norma» con l'Indice crollo senza distanza dal massimo (V2).
Stesso perimetro di PROTOCOLLO_SFASATO: solo crisi finanziarie; bersaglio: minimo dei 5 giorni successivi <= -3%."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import indice_crollo as ic, store
from classifica_40anni import ESTERNI, MISTE_MAX
def serie(pesi):
    old = dict(ic.PESI); ic.PESI.clear(); ic.PESI.update(pesi)
    try: return ic.calcola_serie()["indice"]
    finally: ic.PESI.clear(); ic.PESI.update(old)
V1 = serie({"f1_paura": .30, "f3_curva": .30, "f5_credito": .15, "f7_tendenza": .25, "f8_perdita": .25, "f10_rotaz": .15, "f6_tassi": .15})
V2 = serie({"f1_paura": .30, "f3_curva": .30, "f5_credito": .15, "f7_tendenza": .25, "f10_rotaz": .15, "f6_tassi": .15})
cal = V1.index; sp = store.load("sp500").dropna().reindex(cal).ffill()
fuori = pd.Series(False, index=cal)
for d in ESTERNI:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 63):min(len(cal), p + 61)] = True
for d in MISTE_MAX:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 5):min(len(cal), p + 181)] = True
m5 = pd.concat([sp.shift(-i) for i in range(1, 6)], axis=1).min(axis=1) / sp - 1
ev = (m5 <= -0.03).astype(float).where(m5.notna()); ok = (~fuori) & ev.notna()
for nome, V in (("V1 attuale", V1), ("V2 senza distanza", V2)):
    M = V.rolling(5).mean()
    base = ev[ok].mean()
    for soglia in (60,):
        s = ok & (M > soglia)
        print(f"{nome}: media 5 sedute > {soglia}: giorni {int(s.sum())} ({s.sum()/ok.sum()*100:.1f}% dei giorni), calo>=3% in 5 sedute {ev[s].mean()*100:.1f}% contro base {base*100:.1f}%")
    q = M[ok].quantile(0.80); s = ok & (M >= q)
    print(f"   quinto piu' alto (soglia {q:.1f}): {ev[s].mean()*100:.1f}%")
    print(f"   oggi: media 5 sedute {M.iloc[-1]:.1f}, indice {V.iloc[-1]:.1f}")
print("\n--- solo verifica (dal 2015) e scelta (fino al 2014)")
for nome, V in (("V1 attuale", V1), ("V2 senza distanza", V2)):
    M = V.rolling(5).mean()
    for lab, per in (("scelta", cal <= "2014-12-31"), ("verifica", cal >= "2015-01-01")):
        o = ok & per; s = o & (M > 60)
        print(f"{nome} {lab}: giorni>60 {int(s.sum())}, evento {ev[s].mean()*100:.1f}% contro base {ev[o].mean()*100:.1f}%")
