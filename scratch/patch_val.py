def rw(p, fn):
    s = open(p, 'rb').read().decode('utf-8'); n = fn(s); assert n != s, p; open(p, 'wb').write(n.encode('utf-8'))
def sub(a, b, cnt=1):
    def f(s):
        assert a in s, a[:70]; return s.replace(a, b, cnt)
    return f
def chain(*fs):
    def f(s):
        for g in fs: s = g(s)
        return s
    return f

P = 'src/armor/grafico_indici.py'
rw(P, chain(
 # ---------- Python: serie delle valutazioni, configurazione, schede
 sub('def dati() -> dict:\n    out: dict = {}',
 '''VAL = {   # valutazioni del mercato: piu' alto = piu' caro = peggio
    "cape": ("CAPE S&P 500", "prezzo su utili medi di 10 anni", 1, ""),
    "pe": ("P/E S&P 500", "prezzo su utili di un anno", 1, ""),
    "buffett": ("Indice Buffett", "valore della Borsa su prodotto interno lordo", 0, "%"),
}
VAL_NOM = ["Nella norma", "Sopra la norma", "Caro", "Estremo"]
VAL_COL = ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"]
VAL_DESC = {
    "cape": "Prezzo delle 500 maggiori aziende americane diviso la media dei loro utili degli ultimi 10 anni, corretta per l'inflazione. Più è alto, più il mercato è caro rispetto a quanto guadagna: in passato valori alti hanno preceduto rendimenti più bassi e cali più profondi. Non dice quando.",
    "pe": "Prezzo delle 500 maggiori aziende americane diviso gli utili dell'ultimo anno. Più è alto, più si paga caro ogni euro di utile. Verde nella norma storica, giallo sopra la norma, rosso caro, viola estremo.",
    "buffett": "Valore di tutte le azioni americane diviso il prodotto interno lordo (la ricchezza prodotta in un anno). Sopra 100% si paga la Borsa più di quanto produce il Paese. Il dato arriva ogni trimestre, con ritardo.",
}


def val_serie(k: str):
    try:
        if k == "cape":
            return store.load("cape_m").dropna()
        if k == "pe":
            return store.load("pe_m").dropna()
        from . import semafori
        return semafori.series_of("buffett").dropna()
    except Exception:  # noqa: BLE001
        return None


def val_info() -> dict:
    """Per ogni valutazione: valore di oggi, posizione nella storia, soglie (50/80/95 per cento della storia) e colori."""
    out = {}
    for k, (nome, sub_, dec, u) in VAL.items():
        s = val_serie(k)
        if s is None or len(s) < 100:
            continue
        v = float(s.iloc[-1])
        lim = [round(float(s.quantile(q)), 2) for q in (0.50, 0.80, 0.95)]
        i = sum(v >= x for x in lim)
        out[k] = {"nome": nome, "sub": sub_, "dec": dec, "u": u, "v": v, "pos": float((s < v).mean()), "lim": lim, "i": i,
                  "col": VAL_COL[i], "nom": VAL_NOM[i], "mediana": float(s.median()), "dal": int(s.index[0].year),
                  "data": s.index[-1], "ieri": float(s.iloc[-2]) if len(s) > 1 else None,
                  "sett": float(s[s.index <= s.index[-1] - pd.Timedelta(days=7)].iloc[-1]) if (s.index <= s.index[-1] - pd.Timedelta(days=7)).any() else None}
    return out


def _it(x: float, d: int = 0) -> str:
    return f"{x:.{d}f}".replace(".", ",").replace("-", "\\u2212")


def val_cards() -> str:
    """Tre schede per «Paura, protezioni e prezzi»: CAPE, P/E, Buffett con colore e grafico toccando."""
    info = val_info()
    if not info:
        return ""
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    out = ""
    for k, x in info.items():
        zone = ["verde", "gialla", "rossa", "viola"]
        seg = "".join(f"<i style='flex:{w};background:{c};opacity:{1 if j == x['i'] else .3}'></i>" for j, (w, c) in enumerate(zip((50, 30, 15, 5), VAL_COL)))
        pos = min(max(x["pos"] * 100, 1), 99)
        freschezza = ""
        if (pd.Timestamp.now() - x["data"]).days > 20:
            freschezza = f"<div class='mu'>Dato al {x['data'].day} {mesi[x['data'].month - 1]} {x['data'].year}: arriva ogni trimestre.</div>"
        prev = ""
        if x["ieri"] is not None and not freschezza:
            d = x["v"] - x["ieri"]
            prev = (f"<div class='vl-p'>ieri <b>{_it(x['ieri'], x['dec'])}{x['u']}</b> "
                    f"<span style='color:{'var(--bad)' if d > 0 else 'var(--ok)'}'>{'\\u25b2' if d > 0 else '\\u25bc'} {_it(abs(d), x['dec'])}</span>"
                    + (f" · 1 sett. fa <b>{_it(x['sett'], x['dec'])}{x['u']}</b>" if x["sett"] is not None else "") + "</div>")
        out += (f"<div class='kc vl' data-gi='{k}'><div class='kt'>{x['nome']} <span class='sdot' style='background:{x['col']}'></span>"
                f"<small style='color:{x['col']};font-weight:700'>{x['nom']}</small></div>"
                f"<div class='kv' style='color:{x['col']}'>{_it(x['v'], x['dec'])}{x['u']}</div>"
                f"<div class='vl-s'>{x['sub']}</div>"
                f"<div class='vl-g'>{seg}<u style='left:{pos:.0f}%'></u></div>"
                f"<div class='vl-p'>Più alto del <b>{x['pos'] * 100:.0f}%</b> dei dati dal {x['dal']} · tipico {_it(x['mediana'], x['dec'])}{x['u']}</div>"
                f"{prev}{freschezza}<div class='mu'>Tocca per il grafico ›</div></div>")
    return out


def val_cfg() -> tuple[dict, dict, dict]:
    """Configurazione del grafico per le valutazioni: serie, opzioni, zone (soglie in unita' reali)."""
    ser, cfg, zone = {}, {}, {}
    info = val_info()
    for k, x in info.items():
        s = val_serie(k)
        r = _serie(s)
        if not r:
            continue
        ser[k] = r
        zone[k] = {"lim": x["lim"], "col": VAL_COL, "nom": VAL_NOM}
        trim = k == "buffett"
        cfg[k] = {"val": 1, "dec": x["dec"], "u": x["u"], "pp": "sul dato precedente",
                  "rng": [["1A", 365], ["3A", 1096], ["5A", 1826], ["10A", 3652], ["20A", 7305], ["Max", 0]] if trim else [["1M", 30], ["3M", 91], ["1A", 365], ["5A", 1826], ["20A", 7305], ["Max", 0]],
                  "prev": [["3 mesi fa", 91], ["6 mesi fa", 182], ["1 anno fa", 365]] if trim else [["Ieri", 1], ["Una settimana fa", 7], ["Un mese fa", 30]],
                  "mean": None if trim else [["Ultima settimana", 7], ["Ultimo mese", 30], ["Ultimi 3 mesi", 91]],
                  "def": 1 if trim else 1}
        NOMI[k] = x["nome"]
        DESC[k] = VAL_DESC[k]
    return ser, cfg, zone


def dati() -> dict:
    out: dict = {}'''),
 sub('import pandas as pd\n\nfrom .config import DATA', 'import pandas as pd\n\nfrom . import store\nfrom .config import DATA'),
 sub('''    try:   # pilastri 7 e 8''', '''    try:
        out.update(val_cfg()[0])
    except Exception:  # noqa: BLE001
        pass
    try:   # pilastri 7 e 8'''),
 sub('''    zone = {k: {"lim": ZONE[k]["lim"], "col": ZONE[k]["col"], "nom": ZONE[k]["nom"]} for k in d}''',
     '''    vser, vcfg, vzone = val_cfg()
    zone = {k: {"lim": ZONE[k]["lim"], "col": ZONE[k]["col"], "nom": ZONE[k]["nom"]} for k in d if k in ZONE}
    zone.update(vzone)'''),
 sub('''        + f"<script type='application/json' id='gi-desc'>''', '''        + f"<script type='application/json' id='gi-cfg'>{json.dumps(vcfg, ensure_ascii=False, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-desc'>'''),
 sub('''<div class='gi-rg'>{chips}</div>"''', '''<div class='gi-rg' id='gi-rg'></div>"'''),
 sub('''    chips = "".join(f"<button type='button' data-i='{i}'>{n}</button>" for i, n in
                    enumerate(("1S", "1M", "3M", "6M", "1A", "3A", "5A", "Max")))
''', ''),
 sub(".gi-ds{", ".kc.vl{cursor:pointer}.vl-s{font-size:11px;color:var(--mu);margin-top:-2px}\n.vl-g{display:flex;position:relative;height:8px;border-radius:99px;margin:9px 0 4px}\n.vl-g i{display:block;height:100%}.vl-g i:first-child{border-radius:99px 0 0 99px}.vl-g i:nth-child(4){border-radius:0 99px 99px 0}\n.vl-g u{position:absolute;top:-4px;width:3px;height:16px;border-radius:2px;background:var(--tx);box-shadow:0 0 0 2px var(--card);transform:translateX(-1px)}\n.vl-p{font-size:11.5px;color:var(--mu);line-height:1.4}.vl-p b{color:var(--tx)}\n.gi-ds{"),
 # ---------- JS
 sub("KD=JSON.parse(document.getElementById('gi-kids').textContent);", "KD=JSON.parse(document.getElementById('gi-kids').textContent),CF=JSON.parse(document.getElementById('gi-cfg').textContent);"),
 sub("var RG=[['1S',7],['1M',30],['3M',91],['6M',182],['1A',365],['3A',1096],['5A',1826],['Max',0]];",
     "var RGD=[['1S',7],['1M',30],['3M',91],['6M',182],['1A',365],['3A',1096],['5A',1826],['Max',0]],RG=RGD;\nfunction cfg(){return CF[cur]||{}}\nfunction fv(v,d){var c=cfg();return it(v,d==null?(c.dec||0):d)+(c.u||'')}\nfunction chips(){var box=document.getElementById('gi-rg');box.innerHTML=RG.map(function(r,i){return '<button type=\"button\" data-i=\"'+i+'\">'+r[0]+'</button>'}).join('');box.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){range(+b.dataset.i)})})}"),
 sub("if(hi-lo<16){var m=(hi+lo)/2;lo=m-8;hi=m+8}var p=(hi-lo)*.14;tya=Math.max(0,lo-p);tyb=Math.min(100,hi+p);if(tyb-tya<12){tya=Math.max(0,tyb-12)}",
     "var vl=cfg().val,ms=vl?Math.max(1,.14*Math.abs((hi+lo)/2)):16;if(hi-lo<ms){var m=(hi+lo)/2;lo=m-ms/2;hi=m+ms/2}var p=(hi-lo)*.14;if(vl){tya=Math.max(0,lo-p);tyb=hi+p}else{tya=Math.max(0,lo-p);tyb=Math.min(100,hi+p);if(tyb-tya<12){tya=Math.max(0,tyb-12)}}"),
 sub("cx.fillText(String(Math.round(g)),pr+4,yy)", "cx.fillText(st<1?g.toFixed(1):String(Math.round(g)),pr+4,yy)"),
 sub("cx.fillText(String(l[j]),pr+4,ys)", "cx.fillText(it(l[j],cfg().dec||0),pr+4,ys)"),
 sub("' · '+it(V[ci],1);", "' · '+fv(V[ci],1);"),
 sub("big.textContent=it(v);", "big.textContent=fv(v);"),
 sub("</b> sulla seduta precedente'}d.innerHTML=txt;", "</b> '+(cfg().pp||'sulla seduta precedente')}d.innerHTML=txt;"),
 sub("var d=document.getElementById('gi-dd'),txt=dlong(T[i]);", "var d=document.getElementById('gi-dd'),txt=dlong(T[i]);"),
 sub("document.getElementById('gi-ds').textContent=DS[k]||'';", "document.getElementById('gi-ds').textContent=DS[k]||'';RG=cfg().rng||RGD;chips();"),
 sub("cursor=null;range(2);v0=tv0;", "cursor=null;range(cfg().def!=null?cfg().def:2);v0=tv0;"),
 sub('''function stats(){var n=T.length-1,box=document.getElementById('gi-st'),h='';''',
     '''function atDay(days){var tt=T[T.length-1]-days,i=bs(tt);return i}
function statsVal(){var n=T.length-1,box=document.getElementById('gi-st'),c=cfg(),h='';
function tile(lbl,v,sub){var cc=zc(v);return '<div class="gi-c" style="--c:'+cc+'"><div class="gi-cn">'+fv(v)+'</div><div class="gi-cl">'+lbl+'</div><div class="gi-cs">'+sub+'</div></div>'}
if(c.mean){h+='<div class="gi-sc">Valore medio</div><div class="gi-g">'+c.mean.map(function(m){var a=atDay(m[1]),s=0,k=0;for(var i=a+1;i<=n;i++){s+=V[i];k++}if(!k){s=V[n];k=1}return tile(m[0],s/k,m[1]+' giorni')}).join('')+'</div>'}
h+='<div class="gi-sc">Com\\u2019era prima</div><div class="gi-g">'+c.prev.map(function(m){var i=atDay(m[1]),df=V[n]-V[i],cl=Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)';return tile(m[0],V[i],dshort(T[i])+' \\u00b7 <b style="color:'+cl+'">'+(Math.abs(df)<.05?'=':(df>0?'\\u25b2 ':'\\u25bc ')+it(Math.abs(df),c.dec||0))+'</b>')}).join('')+'</div>';
h+='<div class="gi-hint" style="margin-top:6px">Colori rispetto alla storia: verde nella norma, giallo sopra la norma, rosso caro, viola estremo. Freccia rossa = oggi \\u00e8 pi\\u00f9 caro di allora.</div>';
box.innerHTML=h}
function stats(){if(cfg().val)return statsVal();var n=T.length-1,box=document.getElementById('gi-st'),h='';'''),
 sub("ov.querySelectorAll('.gi-rg button').forEach(function(b){b.addEventListener('click',function(){range(+b.dataset.i)})});", ""),
 sub("cv.addEventListener('dblclick',function(){range(7)});", "cv.addEventListener('dblclick',function(){range(RG.length-1)});"),
))

# ---------- la scheda va nel blocco «Paura, protezioni e prezzi»
rw('src/armor/cruscotto.py', sub('''    return f"<div class='kpis'>{cards}</div><div class='mu liveinfo' style='margin:-4px 0 10px'></div>"''',
'''    try:
        from . import grafico_indici
        extra = grafico_indici.val_cards()
    except Exception:  # noqa: BLE001
        extra = ""
    return f"<div class='kpis'>{cards}{extra}</div><div class='mu liveinfo' style='margin:-4px 0 10px'></div>"'''))
