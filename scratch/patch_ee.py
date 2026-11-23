p='scratch/elementi_esterni.py'
s=open(p,encoding='utf-8').read()
a='''        pi = cal.searchsorted(pd.Timestamp(picco))
        if pi >= len(cal):
            continue
        liv = spx.iloc[pi]
        dopo = spx.iloc[pi:]
        cross = dopo[dopo <= liv * 0.90]
        d10 = cross.index[0] if len(cross) else dopo.idxmin()'''
b='''        if picco < "1991-01-01":      # picchi prima dell'inizio dei dati (1990): non valutabili
            continue
        pi = cal.searchsorted(pd.Timestamp(picco))
        if pi >= len(cal):
            continue
        liv = spx.iloc[pi]
        dopo = spx.iloc[pi:pi + 150]       # il calo di QUELL'episodio: entro 150 sedute dal picco
        cross = dopo[dopo <= liv * 0.90]
        d10 = cross.index[0] if len(cross) else dopo.idxmin()'''
assert a in s; s=s.replace(a,b)
a='''    # richiamo sulle crisi finanziarie'''
b='''    for nome, f in (("almeno due, SOLO scelta (fino al 2014)", due & sel), ("almeno due, SOLO verifica (dal 2015)", due & ver)):
        m = f & y63.notna()
        pos = np.where(m.to_numpy())[0]
        ind = 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 60).sum())
        bp = float(y63[(sel if "scelta" in nome else ver) & y63.notna()].mean()) * 100
        res[nome] = {"giorni": int(m.sum()), "episodi_indipendenti": ind, "calo8_entro_63_%": None if m.sum() == 0 else round(float(y63[m].mean()) * 100, 1), "base_periodo_%": round(bp, 1)}
        print(f"P3 {nome:42s} giorni {int(m.sum()):5d} episodi {ind:3d} calo>=8%: {res[nome]['calo8_entro_63_%']}%  (base del periodo {bp:.1f}%)")
    # richiamo sulle crisi finanziarie'''
assert a in s; s=s.replace(a,b,1)
open(p,'w',encoding='utf-8').write(s)
