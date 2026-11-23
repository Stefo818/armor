def rw(p, fn):
    s = open(p, 'rb').read().decode('utf-8'); n = fn(s); assert n != s, p; open(p, 'wb').write(n.encode('utf-8'))
def sub(a, b):
    def f(s):
        assert a in s, a[:70]; return s.replace(a, b, 1)
    return f
def chain(*fs):
    def f(s):
        for g in fs: s = g(s)
        return s
    return f

P = 'src/armor/grafico_indici.py'
rw(P, chain(
 # --- dati: parti dell'Indice Armor, pilastri 7 e 8 informativi
 sub('''ZONE["super"] = ZONE["armor"]
for _i in range(1, 7):
    ZONE[f"p{_i}"] = ZONE["armor"]''',
 '''ZONE["super"] = ZONE["armor"]
# pilastri mostrati dentro ogni indice (chiave -> figli, nell'ordine in cui compaiono)
KIDS = {
    "armor": ["a_paura", "a_liquidita", "a_rimbalzo", "a_stress", "a_ciclo"],
    "super": ["p1", "p2", "p3", "p4", "p5", "p6", "i7", "i8"],
}
PAR = {k: p for p, ks in KIDS.items() for k in ks}
TAG = {"a_paura": "parte veloce", "a_liquidita": "parte veloce", "a_rimbalzo": "parte veloce",
       "a_stress": "parte lenta", "a_ciclo": "parte lenta", "i7": "solo informativo", "i8": "solo informativo"}
for _k in PAR:
    ZONE[_k] = ZONE["armor"]
NOMI.update({"a_paura": "Paura sui mercati", "a_liquidita": "Liquidità", "a_rimbalzo": "Segnali di rimbalzo",
             "a_stress": "Stress di mercato e credito", "a_ciclo": "Ciclo, prezzi e valutazioni",
             "i7": "7° Fondi a breve termine", "i8": "8° Indice Buffett"})
DESC.update({
    "a_paura": "Parte veloce dell'Indice Armor (peso 30% insieme alle altre due). È lo stesso pilastro «Paura sui mercati» del Super Armor: indice della paura, sua curva, volatilità delle obbligazioni.",
    "a_liquidita": "Parte veloce dell'Indice Armor. È lo stesso pilastro «Liquidità» del Super Armor: quanta moneta circola e quanto è facile ottenerla.",
    "a_rimbalzo": "Parte veloce dell'Indice Armor. Misura se ci sono segnali di rimbalzo (credito che migliora, acquisti istituzionali). Qui il numero è il rischio: più è alto, meno segnali di rimbalzo.",
    "a_stress": "Parte lenta dell'Indice Armor (peso 70% insieme al ciclo). Unisce paura, costo del credito e distanza dai massimi dell'ultimo anno: è il termometro di fondo dello stress.",
    "a_ciclo": "Parte lenta dell'Indice Armor. Riassume ciclo economico, prezzi, valutazioni, inflazione e movimenti dei grandi fondi. Si muove piano: oscilla di meno degli altri.",
    "i7": "Fondi a leva che riducono il rischio (percentuale rispetto alla storia disponibile, dal 2010). Solo informativo: provato come 7° pilastro, non è entrato nel Super Armor perché non lo migliorava.",
    "i8": "Valore di tutte le azioni USA diviso il PIL (indice Buffett), come percentuale rispetto alla storia. Solo informativo: provato come 8° pilastro, non è entrato nel Super Armor perché non lo migliorava.",
})'''),
 sub('''    try:
        c = pd.read_csv(DATA / "indice_crollo_storia.csv"''', '''    try:   # pilastri 7 e 8: informativi, in percentile rispetto alla propria storia, sull'asse dei giorni Titan
        from . import semafori
        d = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
        for k, key in (("i7", "fondi_breve"), ("i8", "buffett")):
            s = semafori.series_of(key).dropna()
            if len(s) > 60:
                pct = s.expanding(min_periods=40).apply(lambda w: float((w.iloc[:-1] < w.iloc[-1]).mean()), raw=False) * 100 if len(s) < 2500 else (s.expanding(min_periods=40).rank(pct=True) * 100)
                x = _serie(pct.dropna().reindex(d.index, method="ffill").dropna().clip(1, 100))
                if x:
                    out[k] = x
    except Exception:  # noqa: BLE001
        pass
    try:
        c = pd.read_csv(DATA / "indice_crollo_storia.csv"'''),
 sub('for k, c in (("armor", col), ("super", "super_armor_index")) + tuple((f"p{i}", f"p{i}_stress") for i in range(1, 7)):',
     'for k, c in (("armor", col), ("super", "super_armor_index")) + tuple((f"p{i}", f"p{i}_stress") for i in range(1, 7)) + tuple((a, a) for a in KIDS["armor"]):'),
 # --- html: contenitori, JSON dei figli
 sub('''        + f"<script type='application/json' id='gi-desc'>''', '''        + f"<script type='application/json' id='gi-kids'>{json.dumps({'kids': KIDS, 'par': PAR, 'tag': TAG}, ensure_ascii=False)}</script>"
        + f"<script type='application/json' id='gi-desc'>'''),
 sub("<button type='button' class='gi-x' id='gi-xb'", "<button type='button' class='gi-bk' id='gi-bk' hidden></button><button type='button' class='gi-x' id='gi-xb'"),
 sub('''"<div id='gi-st'></div></div></div>"''', '''"<div id='gi-kd'></div><div id='gi-st'></div></div></div>"'''),
 # --- css
 sub(".gi-ds{", ".gi-bk{flex:none;align-self:center;border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;padding:6px 11px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}\n.gi-bk[hidden]{display:none}\n.gi-kt{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin:12px 0 5px}\n.gi-kt small{text-transform:none;font-weight:400;letter-spacing:0}\n.gi-kg{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}\n.gi-k{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:12px;padding:6px 8px 7px;text-align:left;font:inherit;cursor:pointer;position:relative;overflow:hidden;transition:.15s}\n.gi-k:active{transform:scale(.97)}\n.gi-k.inf{border-style:dashed}\n.gi-kn{font-size:10.5px;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.gi-kv{display:flex;align-items:baseline;justify-content:space-between;gap:4px}\n.gi-kv b{font-size:21px;font-weight:800;line-height:1.15;color:var(--c);font-variant-numeric:tabular-nums}\n.gi-kv em{font-style:normal;font-size:10.5px;font-weight:700}\n.gi-kb{height:4px;border-radius:99px;background:var(--bd);overflow:hidden;margin-top:3px}\n.gi-kb i{display:block;height:100%;background:var(--c)}\n.gi-kg2{font-size:9.5px;color:var(--mu);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.gi-ds{"),
 # --- js: caricamento figli e apertura con ritorno al genitore
 sub("DS=JSON.parse(document.getElementById('gi-desc').textContent);", "DS=JSON.parse(document.getElementById('gi-desc').textContent),KD=JSON.parse(document.getElementById('gi-kids').textContent);"),
 sub("function open(k){if(!S[k])return;", '''function kids(k){var box=document.getElementById('gi-kd'),ks=(KD.kids[k]||[]).filter(function(x){return S[x]});if(!ks.length){box.innerHTML='';return}
var h='<div class="gi-kt">'+(k==='armor'?'I pilastri dell\\u2019Indice Armor':'I pilastri del Super Armor')+' <small>(tocca per il grafico)</small></div><div class="gi-kg">';
ks.forEach(function(x){var t=S[x].t,v=S[x].v,n=v.length-1,val=v[n],dv=n>=5?val-v[n-5]:0,c=Z[x].col[zi(x,val)],ar=Math.abs(dv)<.5?'':'<em style="color:'+(dv>0?'var(--bad)':'var(--ok)')+'">'+(dv>0?'\\u25b2':'\\u25bc')+it(Math.abs(dv),1)+'</em>',tg=KD.tag[x]||'';
h+='<button type="button" class="gi-k'+(x==='i7'||x==='i8'?' inf':'')+'" data-k="'+x+'" style="--c:'+c+'"><div class="gi-kn">'+NM[x]+'</div><div class="gi-kv"><b>'+it(val)+'</b>'+ar+'</div><div class="gi-kb"><i style="width:'+Math.max(3,Math.min(100,val))+'%"></i></div>'+(tg?'<div class="gi-kg2">'+tg+'</div>':'')+'</button>'});
box.innerHTML=h+'</div>';box.querySelectorAll('.gi-k').forEach(function(b){b.addEventListener('click',function(){open(b.dataset.k)})})}
function open(k){if(!S[k])return;'''),
 sub("stats();head();draw();sh.scrollTop=0}", "stats();kids(k);var pr=KD.par[k],bk=document.getElementById('gi-bk');if(pr){bk.hidden=false;bk.textContent='\\u2039 '+NM[pr];bk.onclick=function(){open(pr)}}else{bk.hidden=true}head();draw();sh.scrollTop=0}"),
))
