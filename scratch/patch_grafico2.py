def rw(p, fn):
    s = open(p, 'rb').read().decode('utf-8'); n = fn(s); assert n != s, p; open(p, 'wb').write(n.encode('utf-8'))
def sub(a, b):
    def f(s):
        assert a in s, a[:60]; return s.replace(a, b, 1)
    return f
def chain(*fs):
    def f(s):
        for g in fs: s = g(s)
        return s
    return f
A = 'src/armor/'
rw(A+'titan_schede.py', chain(
  sub('    dett = "".join(_dett(i, k, x) for i, (k, x) in enumerate(rig))', '    dett = ""   # le spiegazioni dei pilastri sono nel grafico a comparsa'),
  sub("(tocca un pilastro per i dettagli)", "(tocca un pilastro per il grafico)"),
))
rw(A+'titan_schede.py', lambda s: s[:s.index('JS = """<script>')] + 'JS = ""\n\n' + s[s.index('CSS = ("<style>'):])
rw(A+'grafico_indici.py', chain(
  sub('NOMI = {"armor": "Indice Armor", "super": "Super Armor", "crollo": "Indice crollo"}',
      '''NOMI = {"armor": "Indice Armor", "super": "Super Armor", "crollo": "Indice crollo"}
try:   # i sei pilastri del Super Armor: stessa scala, con la spiegazione di cosa guardano
    from .titan_schede import PIL as _PIL
    for _k, (_n, _c, _s) in _PIL.items():
        NOMI[_k] = _n
        DESC[_k] = f"{_c} {_s}"
except Exception:  # noqa: BLE001
    pass'''),
  sub('NOMI = {"armor"', 'DESC = {\n    "armor": "Salute del mercato: da 40 mercato in difficoltà, da 60 in pericolo, da 80 rischio di crollo.",\n    "super": "Salute di economia e mercato: media dei sei pilastri con lo stesso peso. Stesse soglie: 40, 60, 80.",\n    "crollo": "Rischio di crollo nella prossima settimana: fino a 35 tranquillo, da 40 teso, da 60 molto teso, da 80 panico.",\n}\nNOMI = {"armor"'),
  sub('ZONE["super"] = ZONE["armor"]', 'ZONE["super"] = ZONE["armor"]\nfor _i in range(1, 7):\n    ZONE[f"p{_i}"] = ZONE["armor"]'),
  sub('''        for k, c in (("armor", col), ("super", "super_armor_index")):''', '''        for k, c in (("armor", col), ("super", "super_armor_index")) + tuple((f"p{i}", f"p{i}_stress") for i in range(1, 7)):'''),
  sub("function zi(k,v){var l=Z[k].lim;for(var i=0;i<l.length;i++){if(v<=l[i]&&!(k==='crollo'&&false))return i}return l.length}",
      "function zi(k,v){var l=Z[k].lim;for(var i=0;i<l.length;i++){if(k==='crollo'?v<=l[i]:v<l[i])return i}return l.length}"),
  sub("if(t.closest('details,summary,a,button,input,select'))return;", "var bl=t.closest('details,summary,a,button,input,select');if(bl&&!bl.hasAttribute('data-gi'))return;"),
  sub('''+ f"<script type='application/json' id='gi-nomi'>{json.dumps(NOMI, ensure_ascii=False)}</script>"''',
      '''+ f"<script type='application/json' id='gi-nomi'>{json.dumps(NOMI, ensure_ascii=False)}</script>"
        + f"<script type='application/json' id='gi-desc'>{json.dumps(DESC, ensure_ascii=False)}</script>"'''),
  sub("NM=JSON.parse(document.getElementById('gi-nomi').textContent);", "NM=JSON.parse(document.getElementById('gi-nomi').textContent),DS=JSON.parse(document.getElementById('gi-desc').textContent);"),
  sub("document.getElementById('gi-nm').firstChild.nodeValue=NM[k];", "document.getElementById('gi-nm').firstChild.nodeValue=NM[k];document.getElementById('gi-ds').textContent=DS[k]||'';"),
  sub("<canvas id='gi-cv'>", "<div class='gi-ds' id='gi-ds'></div><canvas id='gi-cv'>"),
  sub(".gi-rg{display:flex", ".gi-ds{font-size:11.5px;color:var(--mu);line-height:1.4;margin:6px 0 0}\n.gi-rg{display:flex"),
))
