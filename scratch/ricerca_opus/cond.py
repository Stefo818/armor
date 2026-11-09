exec(open("fund.py").read().split("# target")[0])
r12 = (M.shift(-12) / M - 1) * 100; r3 = (M.shift(-3) / M - 1) * 100
dd6 = pd.Series([ (sp[(sp.index>t)&(sp.index<=t+pd.DateOffset(months=6))].min()/M[t]-1)*100 if t < sp.index[-1]-pd.DateOffset(months=6) else np.nan for t in M.index], M.index)
base = M.index >= "1990-01-01"
sig = {
 "Utili in calo (12 mesi)": F.eps_g12 < 0,
 "Utili in calo forte (<-10%)": F.eps_g12 < -10,
 "CAPE > 30": F.cape > 30,
 "Premio utili-bond < 1%": F.erp < 1,
 "Spread credito +0,5 pt in 6 mesi": F.baa_d6 > 0.5,
 "Sussidi disoccupazione +20% dal minimo": F.claims_d6 > 20,
 "Curva invertita (ultimi 12 mesi)": F.curve_min12 < 0,
 "Prezzo sotto media 10 mesi": F.sma10 < 0,
 "VIX > 30": F.vix > 30,
}
rows = []
for k, s in sig.items():
    s = s & base & F.notna().any(axis=1)
    on = s & r12.notna(); off = (~s) & base & r12.notna()
    rows.append([k, int(on.sum()), round(r3[on].mean(), 1), round(r3[off].mean(), 1), round(r12[on].mean(), 1), round(r12[off].mean(), 1),
                 round((dd6[on] <= -10).mean() * 100), round((dd6[off & dd6.notna()] <= -10).mean() * 100)])
df = pd.DataFrame(rows, columns=["segnale", "mesi", "r3m_on", "r3m_off", "r12m_on", "r12m_off", "P_calo10_6m_on", "P_calo10_6m_off"])
print(df.to_string(index=False))
# segnali oggi
last = F.iloc[-1]; print(last.round(2).to_dict())
