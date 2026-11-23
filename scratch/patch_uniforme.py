import re
def rw(p, fn):
    s = open(p, 'rb').read().decode('utf-8'); n = fn(s); assert n != s, p; open(p, 'wb').write(n.encode('utf-8'))
def sub(a, b, cnt=1):
    def f(s):
        assert a in s, a[:50]; return s.replace(a, b, cnt)
    return f
def chain(*fs):
    def f(s):
        for g in fs: s = g(s)
        return s
    return f
A = 'src/armor/'
# soglie: scala unica 40/60/80, stesse tinte ovunque
rw(A+'soglie.py', chain(
 sub('LO, HI = 20, 70', 'LO, HI = 20, 90'),
 sub('COL = ["#16a34a", "#64748b", "#d97706", "#dc2626"]', 'COL = ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"]'),
 sub('NOMI = ["Tranquillo", "Neutro", "Allarme", "Pericolo"]', 'NOMI = ["Tranquillo", "In difficoltà", "In pericolo", "Rischio di crollo"]'),
 sub('FRASI = ["pochi segnali di tensione", "situazione nella norma", "tensione che cresce: prudenza", "stress diffuso: massima prudenza"]',
     'FRASI = ["pochi segnali di tensione", "mercato in difficoltà: tensione che cresce", "stress diffuso: massima prudenza", "stress estremo, tipico dei crolli"]'),
 sub('"lim": [35, 40, 45, 100], "stat": [(28, 2, -3.0), (30, 11, -4.2), (22, 20, -5.5), (20, 34, -8.2)]',
     '"lim": [40, 60, 80, 100], "stat": [(55, 6, -3.6), (35, 24, -6.1), (8, 34, -8.8), (1, 41, -12.1)]'),
 sub('"lim": [35, 45, 55, 100], "stat": [(30, 5, -3.8), (41, 10, -4.1), (15, 30, -6.3), (13, 38, -9.1)]',
     '"lim": [40, 60, 80, 100], "stat": [(55, 6, -3.8), (36, 23, -5.5), (8, 34, -9.0), (1, 68, -15.6)]'),
))
# armor_index: valore ufficiale sulla scala tarata
rw(A+'armor_index.py', chain(
 sub('tv = titan_vista.serie("armor_index", t)   # valore ufficiale: motore Titan, se i suoi dati sono freschi',
     'tv = titan_vista.serie("armor_tarato", t)   # valore ufficiale: motore Titan sulla scala tarata (40 difficolta\', 60 pericolo, 80 crollo)\n        raw_tv = titan_vista.serie("armor_index", t)\n        if tv is None:\n            tv = raw_tv'),
 sub('chiave = str(t.date()) + ("+titan" if tv is not None else "")', 'chiave = str(t.date()) + ("+titan-tarato" if tv is not None else "")'),
 sub('"change5": val - prev, "G": G,', '"change5": val - prev, "raw": float(raw_tv.iloc[-1]) if raw_tv is not None else val, "G": G,'),
))
rw(A+'jobs.py', sub('extra["armor_index"] = round(aix["value"], 2)', 'extra["armor_index"] = round(aix.get("raw", aix["value"]), 2)   # il registro resta sulla scala originale'))
rw(A+'titan_job.py', sub('"armor_index": round(float(ult["armor_index"]), 1),', '"armor_index": round(float(ult["armor_index"]), 1), "armor_tarato": round(float(ult["armor_tarato"]), 1) if "armor_tarato" in ult else round(float(ult["armor_index"]), 1),'))
rw(A+'occasione.py', sub('fasi.salute(t.get("armor_index"), t.get("super_armor"))', 'fasi.salute(t.get("armor_tarato", t.get("armor_index")), t.get("super_armor"))'))
rw(A+'fasi.py', chain(sub('(("mercato", armor, "armor_index"), ("economia", super_, "super_armor_index"))', '(("mercato", armor, "armor_tarato"), ("economia", super_, "super_armor_index"))'),
 sub('SALUTE = ["In salute", "Neutro", "Rischio", "Pericolo"]', 'SALUTE = ["In salute", "In difficoltà", "In pericolo", "Rischio di crollo"]')))
rw(A+'occasione_verifica.py', sub('(("mercato", "armor_index"), ("economia", "super_armor_index"))', '(("mercato", "armor_tarato"), ("economia", "super_armor_index"))'))
# titan_schede: stessa scala per tessere pilastri e linea tratteggiata
rw(A+'titan_schede.py', chain(
 sub('''    return "#16a34a" if v < 35 else ("#64748b" if v < 40 else ("#d97706" if v < 45 else "#dc2626"))''',
     '''    return soglie.COL[0] if v < 40 else (soglie.COL[1] if v < 60 else (soglie.COL[2] if v < 80 else soglie.COL[3]))'''),
 sub("40 if k == 'armor' else 45, 150, 38", "40, 150, 38"),
 sub("sopra 40 è zona di attenzione.", "da 40 è zona di attenzione, da 60 di pericolo, da 80 di rischio di crollo."),
 sub("<button type='button' class='ts-t' data-ts='{i}'>", "<button type='button' class='ts-t' data-ts='{i}' data-gi='{k}'>"),
))
# quadro: stesse tinte e stessa regola (<40 verde, <60 giallo, <80 rosso)
rw(A+'quadro.py', sub('''    return "#8b5cf6" if v > 80 else ("#ef4444" if v > 60 else ("#f59e0b" if v > 40 else "var(--ok)"))''',
                      '''    return "#8b5cf6" if v >= 80 else ("#ef4444" if v >= 60 else ("#f59e0b" if v >= 40 else "#22c55e"))'''))
# hero e schede: toccabili per il grafico
rw(A+'armor_index.py', sub("<div class='aix' data-amod='1'>", "<div class='aix' data-amod='1' data-gi='armor'>"))
rw(A+'soglie.py', sub('''return (f"<div class='sg-r'><div class='sg-t'>''', '''return (f"<div class='sg-r' data-gi='{'armor' if k == 'armor' else 'super'}'><div class='sg-t'>'''))
