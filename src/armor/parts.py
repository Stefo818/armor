"""Blocchi di pagina del cruscotto: probabilita' dettagliate, giorni simili, indicatori, valutazioni, grafici, registro, analisi."""
import html
import json

from .analysis import num, pct
from .config import HZ_LABEL
from .outlook import THRESHOLDS

e = html.escape


def _tint(ratio: float, good_up: bool) -> str:
    """Colore di sfondo leggero: rosso se la probabilita' di calo e' sopra il normale, verde se lo e' quella di risalita."""
    if ratio >= 1.5:
        a = "0.28"
    elif ratio >= 1.15:
        a = "0.14"
    else:
        return ""
    rgb = "31,143,85" if good_up else "192,57,43"
    return f"style='background:rgba({rgb},{a})'"


def matrix_html(mat: dict, sim: list[dict]) -> str:
    tabs, panes = [], []
    for k, hz in enumerate(mat):
        r = mat[hz]
        def rows(kind):
            out = []
            for thr in THRESHOLDS:
                c = r[kind][thr]
                ratio = c["p"] / c["base"] if c["base"] > 0.002 else 1.0
                star = "" if c["source"] == "modello" else "*"
                lab = ("Calo" if kind == "down" else "Risalita") + f" di almeno {thr}%"
                out.append(f"<tr><td>{lab}</td><td {_tint(ratio, kind == 'up')}><b>{pct(c['p'], 1 if c['p'] < 0.1 else 0)}</b>{star}</td>"
                           f"<td>{pct(c['base'], 1 if c['base'] < 0.1 else 0)}</td><td>{pct(c['analog'], 0)}</td></tr>")
            return "".join(out)
        head = "<thead><tr><th>Soglia</th><th>Oggi</th><th>Normale</th><th>Giorni simili</th></tr></thead>"
        ra = r["ret_analog"]
        pane = (f"<div class='mpane' id='mp-{hz}' style='{'' if k == 0 else 'display:none'}'><div class='grid2'>"
                f"<div><h4>Quanto può scendere entro {HZ_LABEL[hz]}</h4><table>{head}<tbody>{rows('down')}</tbody></table></div>"
                f"<div><h4>Quanto può salire entro {HZ_LABEL[hz]}</h4><table>{head}<tbody>{rows('up')}</tbody></table></div></div>"
                f"<p class='muted'>Nei {r['n_analog']} giorni più simili a oggi, a {HZ_LABEL[hz]} di distanza l'S&amp;P 500 ha reso in mediana {pct(ra['q50'], 1, True)} "
                f"(l'80% dei casi tra {pct(ra['q10'], 1, True)} e {pct(ra['q90'], 1, True)}); è salito nel {pct(ra['pos'], 0)} dei casi, contro il {pct(r['ret_base']['pos'], 0)} di tutti i giorni.</p></div>")
        panes.append(pane)
        tabs.append(f"<button class='tab{' on' if k == 0 else ''}' data-m='{hz}' onclick=\"showM('{hz}')\">{HZ_LABEL[hz]}</button>")
    legend = ("<div class='explain'><p><b>Come leggere la tabella.</b> «Calo di almeno 5%» = in qualche momento del periodo il prezzo è 5% sotto quello di oggi; «Risalita di almeno 5%» = in qualche momento è 5% sopra. "
              "<b>Oggi</b> è la probabilità stimata adesso; <b>Normale</b> è la frequenza storica di quell'evento (in tutti i giorni dal 1928); <b>Giorni simili</b> è la frequenza nei 150 giorni passati più simili a oggi per volatilità, distanza dai massimi e andamento. "
              "Le celle <span style='background:rgba(192,57,43,.2);padding:0 6px'>rosse</span> (cali) o <span style='background:rgba(31,143,85,.2);padding:0 6px'>verdi</span> (risalite) indicano probabilità sopra il normale. "
              "Un asterisco (*) segna le soglie con pochi casi storici: lì il numero deriva dai giorni simili invece che dal modello e va letto come un ordine di grandezza. "
              "Le due colonne non si sommano: in uno stesso periodo il prezzo può prima scendere e poi risalire.</p></div>")
    simh = ""
    if sim:
        rows = "".join(f"<tr><td>{x['date'][:7]}</td><td style='text-align:left'>{e(', '.join(x['similar']))}</td><td>{pct(x['ret_1m'], 1, True) if x['ret_1m'] is not None else '—'}</td>"
                       f"<td>{pct(x['ret_3m'], 1, True) if x['ret_3m'] is not None else '—'}</td><td>{pct(x['ret_6m'], 1, True) if x['ret_6m'] is not None else '—'}</td>"
                       f"<td>{pct(x['maxdd_3m'], 1) if x['maxdd_3m'] is not None else '—'}</td></tr>" for x in sim)
        simh = ("<h4>I momenti del passato più simili a oggi</h4><table><thead><tr><th>Quando</th><th>Cosa somigliava di più</th><th>Dopo 1 mese</th><th>Dopo 3 mesi</th>"
                "<th>Dopo 6 mesi</th><th>Calo massimo a 3 mesi</th></tr></thead><tbody>" + rows + "</tbody></table>"
                "<p class='muted'>Sono giorni diversi, distanti tra loro, scelti perché la situazione dell'S&amp;P 500 somigliava a quella di oggi (volatilità, distanza dai massimi, andamento recente). "
                "Mostrano cosa è successo dopo, ma ogni epoca è diversa: sono esempi, non previsioni.</p>")
    return f"<div class='tabs'>{''.join(tabs)}</div>{''.join(panes)}{legend}{simh}"


def signals_html(sigs: list[dict]) -> str:
    if not sigs:
        return "<p class='muted'>Dati non sufficienti.</p>"
    order = {"negativo": 0, "neutro": 1, "positivo": 2}
    rows = []
    for s in sorted(sigs, key=lambda s: (order[s["verdict"]], -s["ratio"])):
        cls = {"negativo": "bad", "positivo": "ok", "neutro": "warn"}[s["verdict"]]
        word = {"negativo": "sfavorevole", "positivo": "favorevole", "neutro": "neutro"}[s["verdict"]]
        ep = max(s["n"] / 63, 1)
        rows.append(f"<tr><td data-chart='{e(s['key'])}' class='clk'>{e(s['name'])}<div class='ihelp'>dal {s['since']} · circa {int(ep)} episodi indipendenti</div></td><td>{num(s['now'], 2)}</td>"
                    f"<td>{num(s['pct'], 0)}°</td><td>{pct(s['freq_dd10'], 0)} <span class='muted'>(normale {pct(s['base_dd10'], 0)})</span></td><td>{pct(s['ret'], 1, True)}</td>"
                    f"<td><span class='badge {cls}'>{word}</span></td></tr>")
    return ("<table><thead><tr><th>Indicatore (tocca per il grafico)</th><th>Oggi</th><th>Percentile storico</th><th>Dopo situazioni simili: calo ≥10% a 3 mesi</th>"
            "<th>Rendimento medio a 3 mesi</th><th>Lettura</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
            "<div class='explain'><p><b>Come funziona.</b> Per ogni indicatore guardo tutte le volte in cui valeva come oggi (nella stessa fascia, un quinto della storia) e conto cosa è successo all'S&amp;P 500 nei tre mesi dopo. "
            "«Sfavorevole» = calo ≥10% almeno 25% più frequente del normale (o poco più frequente e rendimento peggiore); «favorevole» = almeno 20% meno frequente. "
            "Sono statistiche del passato su episodi spesso sovrapposti: indicano il clima, non prevedono nulla da sole, e un indicatore può essere «favorevole» perché oggi è alto in un periodo di mercato forte.</p></div>")


def valuations_html(cards: list[dict]) -> str:
    out = []
    for c in cards:
        def box(label, val, pc, avg=None, since=None, dec=1, key=None):
            if val is None:
                return f"<div class='vm'><div class='lab'>{label}</div><div class='vbig muted'>n.d.</div></div>"
            ctx = ""
            if pc is not None:
                ctx = f"<div class='muted'>{num(pc, 0)}° percentile della storia</div>"
            if avg is not None:
                ctx += f"<div class='muted'>media dal {since}: {num(avg, dec)}</div>"
            clk = f" data-chart='{key}' class='vm clk'" if key else " class='vm'"
            return f"<div{clk}><div class='lab'>{label}</div><div class='vbig'>{num(val, dec)}</div>{ctx}</div>"
        k = c["key"]
        out.append(f"<div class='card vcard'><h3>{e(c['name'])}</h3><div class='vrow'>"
                   + box("Capitalizzazione / utili (P/E)", c["pe"], c.get("pe_pct"), c.get("pe_avg"), c.get("pe_since"), 1, f"val_pe_{k}")
                   + box("Capitalizzazione / fatturato (P/S)", c["ps"], c.get("ps_pct"), c.get("ps_avg"), c.get("ps_since"), 2, f"val_ps_{k}")
                   + f"</div><div class='muted'>{e(c['src'] or c['note'])}</div></div>")
    legend = ("<div class='explain'><p><b>Che cosa sono.</b> Il <b>P/E</b> dice quanti euro si pagano per ogni euro di utile annuo delle società: 20 = si paga l'utile di 20 anni. "
              "Il <b>P/S</b> fa lo stesso con il fatturato. Più sono alti, più il mercato è «caro» e più dipende da utili futuri molto buoni. "
              "I fondi pubblicano questi numeri una volta al giorno: qui sono aggiornati con il prezzo di adesso (gli utili cambiano lentamente). "
              "Per l'S&amp;P 500 il confronto con la storia parte dal 1871 (P/E) e dal 2000 (P/S); per VWCE e Nasdaq lo storico si costruisce giorno per giorno da oggi. "
              "Non misurano quando il mercato scenderà: dicono quanto margine di sicurezza c'è.</p></div>")
    return f"<div class='grid3'>{''.join(out)}</div>{legend}"


def charts_section(options: list[tuple[str, str]]) -> str:
    chips = "".join(f"<button class='chip' data-k='{k}'>{e(l)}</button>" for k, l in options)
    return ("<div class='card'><div class='chips' id='chartchips'>" + chips + "</div><div id='embedchart'></div></div>"
            "<div class='explain'><p><b>Come usare i grafici.</b> Scegli un indice con i pulsanti, poi l'intervallo (6 ore, 1 giorno, 1 settimana ... Max). "
            "Sposta il dito o il mouse sul grafico per leggere data e valore. I periodi brevi usano i prezzi ogni 5 minuti e funzionano per gli indici con prezzo in tempo reale; "
            "per gli altri indicatori (dati giornalieri o mensili) sono disattivati. Puoi aprire il grafico anche toccando qualsiasi valore sottolineato nella pagina.</p></div>")


def registry_section() -> str:
    return ("<div class='card'><div class='regbar'><select id='regsel'></select><input id='regq' placeholder='Cerca una data (es. 2026-11)' type='search'>"
            "<a class='btn' href='registro.csv' download='armor_registro.csv'>Scarica tutto (CSV)</a></div><div id='regmeta' class='muted'></div>"
            "<div class='scroll' id='regtab'></div></div>"
            "<div class='explain'><p><b>Cos'è.</b> Una riga per ogni giorno, con tutti i valori che Armor ha salvato quel giorno (prezzi, indicatori, valutazioni, probabilità, livelli). "
            "Si accumula ogni giorno e non viene mai cancellata. Scegli il gruppo di colonne, cerca una data oppure scarica tutto in CSV (si apre con Excel). "
            "Alcuni indicatori sono mensili o settimanali: nella colonna con «_data» trovi la data del dato.</p></div>")


def analysis_section(rep: dict, archive: list[dict]) -> str:
    if not rep:
        return "<p class='muted'>L'analisi giornaliera non è ancora stata generata: compare dopo il primo aggiornamento notturno.</p>"
    gen = rep.get("generated", "")[:16].replace("T", " ")
    arch = ""
    if len(archive) > 1:
        arch = "<details class='exp'><summary>Analisi dei giorni scorsi</summary>" + "".join(
            f"<details class='co'><summary><b>{a['date']}</b></summary><div class='analysis'>{a['html']}</div></details>" for a in archive[1:]) + "</details>"
    return (f"<div class='muted'>Analisi dei dati al {e(rep['date'])} · generata {e(gen)} UTC · si aggiorna ogni notte e più volte al giorno per le notizie</div>"
            f"<div class='analysis'>{rep['html']}</div>{arch}"
            "<div class='explain'><p><b>Come è fatta.</b> Ogni frase nasce da un numero: valori attuali, confronto con il passato (percentile, cosa è successo dopo le volte in cui l'indicatore era a questo livello) e lettura in parole semplici. "
            "Le notizie sono titoli e descrizioni da fonti pubbliche, ordinati per rilevanza, con un giudizio automatico positivo/negativo (modello gratuito FinBERT, addestrato su testi finanziari, quando disponibile; altrimenti un vocabolario di parole finanziarie). Si analizzano titolo e breve descrizione, non l'articolo intero: non è la lettura di un analista e può sbagliare il tono. Non è consulenza finanziaria.</p></div>")


CSS = """
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.vcard h3{margin:0 0 8px}.vrow{display:grid;grid-template-columns:1fr 1fr;gap:10px}.vm{background:var(--bg);border-radius:12px;padding:10px}.vbig{font-size:34px;font-weight:800;line-height:1.1}
.clk{cursor:pointer}.clk:hover{outline:2px solid var(--ac);outline-offset:2px}[data-chart]{cursor:pointer}
td[data-chart]>b,td[data-chart]{text-decoration:none}.lq[data-chart]::after{content:'Apri il grafico ›';display:block;margin-top:8px;font-size:12px;font-weight:700;color:var(--ac)}td.clk,td[data-chart]{color:var(--tx)}td[data-chart]:first-child{border-left:3px solid transparent}td[data-chart]:hover{border-left-color:var(--ac)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}.chip{border:1px solid var(--bd);background:var(--card);color:var(--tx);padding:6px 12px;border-radius:99px;font:inherit;font-size:13px;cursor:pointer}.chip.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.cranges{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.cranges button{border:1px solid var(--bd);background:var(--card);color:var(--tx);padding:6px 10px;border-radius:8px;font:inherit;font-size:13px;cursor:pointer}.cranges button.on{background:var(--ac);color:#fff;border-color:var(--ac)}.cranges button:disabled{opacity:.35;cursor:default}
.cstats{display:flex;flex-wrap:wrap;gap:6px 18px;margin:6px 0}.cstats div{font-size:13px;color:var(--mu)}.cstats b{display:block;font-size:17px;color:var(--tx)}
.cwrap{position:relative;width:100%;height:280px;touch-action:pan-y}.cwrap canvas{width:100%;height:100%;display:block}.ctip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:6px 10px;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.25);display:none;white-space:nowrap}
.cmodal{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:20;display:none;align-items:flex-end;justify-content:center}.cmodal.show{display:flex}
.cbox{background:var(--bg);width:100%;max-width:820px;max-height:92vh;overflow:auto;border-radius:18px 18px 0 0;padding:16px;position:relative}
@media(min-width:700px){.cmodal{align-items:center}.cbox{border-radius:18px}}
.cx{position:absolute;right:10px;top:8px;border:0;background:var(--card);color:var(--tx);width:34px;height:34px;border-radius:50%;font-size:20px;cursor:pointer}
.regbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}.regbar select,.regbar input{padding:8px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit}
.btn{display:inline-block;padding:8px 14px;border-radius:8px;background:var(--ac);color:#fff;text-decoration:none;font-weight:600}
#regtab{max-height:420px;overflow:auto}#regtab table{font-size:13px;white-space:nowrap}#regtab th{position:sticky;top:0;background:var(--card)}
.analysis{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:6px 18px;margin:10px 0}.asec{margin:14px 0;padding-bottom:6px;border-bottom:1px solid var(--bd)}.asec h3{margin:6px 0}.asec ul{padding-left:20px}.asec li{margin:8px 0}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.tag{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;font-weight:700}.tag.positivo{background:var(--okbg);color:var(--ok)}.tag.negativo{background:var(--badbg);color:var(--bad)}.tag.neutro{background:var(--bg);color:var(--mu)}
ul.news{list-style:none;padding-left:0!important}ul.news li{margin:10px 0}ul.news a{color:var(--tx)}details.co{margin:6px 0;border:1px solid var(--bd);border-radius:10px;padding:2px 12px}details.co summary{padding:8px 0}
.eps{margin-top:0}.heroin{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:12px 0}
.hchip{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px;text-align:left}.hchip .t{font-size:12px;color:var(--mu);font-weight:700}.hchip .p{font-size:26px;font-weight:800}.hchip .l{font-size:12px}
.hrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:10px}.hbox{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 14px;font-size:14px}.hbox h4{margin:0 0 6px}.hbox ul{margin:0;padding-left:18px}.hbox li{margin:5px 0}
.hbox.r{border-left:4px solid var(--bad)}.hbox.o{border-left:4px solid var(--ok)}
"""

JS = r"""
<script>
(function(){
var RANGES=[['6h','6 ore',21600],['1d','1 giorno',86400],['1w','1 settimana',604800],['1m','1 mese',2592000],['3m','3 mesi',7862400],['6m','6 mesi',15724800],['1y','1 anno',31536000],['3y','3 anni',94608000],['5y','5 anni',157680000],['max','Max',0]];
var DATA=null,cbs=[];
function load(cb){if(DATA)return cb(DATA);cbs.push(cb);if(cbs.length>1)return;
fetch('data.json?'+Date.now()).then(function(r){return r.json()}).then(function(j){DATA=j.series||{};cbs.forEach(function(f){f(DATA)})}).catch(function(){DATA={};cbs.forEach(function(f){f(DATA)})})}
function fmt(v,d){return v.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function series(s){var D=[];for(var i=0;i<s.d.length;i++)D.push([s.d[i]*86400,s.v[i]]);var I=[];if(s.i){for(var j=0;j<s.i.t.length;j++)I.push([s.i.t[j],s.i.v[j]])}return{D:D,I:I}}
function pts(s,range){var x=series(s),D=x.D,I=x.I,r=RANGES.filter(function(a){return a[0]===range})[0];
var last=Math.max(D.length?D[D.length-1][0]:0,I.length?I[I.length-1][0]:0);var from=r[2]?last-r[2]:0;
if(range==='6h'||range==='1d'||range==='1w'){var P=I.filter(function(p){return p[0]>=from});if(P.length>=5)return P;if(range==='1w'){P=D.filter(function(p){return p[0]>=from});return P.length>=3?P:[]}return[]}
var P2=D.filter(function(p){return p[0]>=from});if(I.length&&P2.length&&I[I.length-1][0]>P2[P2.length-1][0]+3600)P2.push(I[I.length-1]);return P2.length>=3?P2:[]}
function avail(s){var o={};RANGES.forEach(function(r){o[r[0]]=pts(s,r[0]).length>0});return o}
function tfmt(t,span){var d=new Date(t*1000);if(span<=2*86400)return d.toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'});
if(span<=40*86400)return d.toLocaleDateString('it-IT',{day:'2-digit',month:'2-digit'});if(span<=3*31536000)return d.toLocaleDateString('it-IT',{month:'short',year:'2-digit'});return d.getFullYear()}
function mount(root){
root.innerHTML="<div class='ctitle'></div><div class='cstats'></div><div class='cwrap'><canvas></canvas><div class='ctip'></div></div><div class='cranges'></div><div class='muted chelp'></div>";
var cv=root.querySelector('canvas'),tip=root.querySelector('.ctip'),stats=root.querySelector('.cstats'),rbox=root.querySelector('.cranges'),title=root.querySelector('.ctitle'),help=root.querySelector('.chelp');
var st={key:null,range:'3m',P:[],s:null,dec:2};
function draw(hi){var dpr=window.devicePixelRatio||1,w=cv.clientWidth,h=cv.clientHeight;cv.width=w*dpr;cv.height=h*dpr;var g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
var P=st.P;if(!P.length){g.fillStyle=css('--mu');g.font='14px system-ui';g.fillText('Nessun dato per questo intervallo',20,40);return}
var L=52,R=10,T=10,B=24,x0=P[0][0],x1=P[P.length-1][0],lo=Infinity,hi2=-Infinity;P.forEach(function(p){if(p[1]<lo)lo=p[1];if(p[1]>hi2)hi2=p[1]});var pad=(hi2-lo)*.08||Math.abs(lo)*.01||1;lo-=pad;hi2+=pad;
var X=function(t){return L+(t-x0)/Math.max(x1-x0,1)*(w-L-R)},Y=function(v){return T+(hi2-v)/(hi2-lo)*(h-T-B)};
g.font='11px system-ui';g.fillStyle=css('--mu');g.strokeStyle=css('--bd');g.lineWidth=1;
for(var k=0;k<5;k++){var v=lo+(hi2-lo)*k/4,y=Y(v);g.beginPath();g.moveTo(L,y);g.lineTo(w-R,y);g.stroke();g.textAlign='right';g.fillText(fmt(v,st.dec>2?2:st.dec),L-6,y+4)}
g.textAlign='center';for(var q=0;q<5;q++){var t=x0+(x1-x0)*q/4;g.fillText(tfmt(t,x1-x0),Math.min(Math.max(X(t),L+14),w-R-14),h-6)}
var up=P[P.length-1][1]>=P[0][1],col=up?css('--ok'):css('--bad');
var gr=g.createLinearGradient(0,T,0,h-B);gr.addColorStop(0,col+'55');gr.addColorStop(1,col+'05');
g.beginPath();P.forEach(function(p,i){i?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1]))});var ln=g.lineWidth;g.strokeStyle=col;g.lineWidth=2;g.lineJoin='round';g.stroke();
g.lineTo(X(x1),h-B);g.lineTo(X(x0),h-B);g.closePath();g.fillStyle=gr;g.fill();g.lineWidth=ln;
if(hi!=null){var p=P[hi],px=X(p[0]),py=Y(p[1]);g.strokeStyle=css('--mu');g.setLineDash([4,4]);g.beginPath();g.moveTo(px,T);g.lineTo(px,h-B);g.stroke();g.setLineDash([]);g.fillStyle=col;g.beginPath();g.arc(px,py,4.5,0,7);g.fill();
tip.style.display='block';tip.innerHTML='<b>'+fmt(p[1],st.dec)+'</b><br>'+new Date(p[0]*1000).toLocaleString('it-IT',{day:'2-digit',month:'short',year:'numeric',hour:(x1-x0<=7*86400)?'2-digit':undefined,minute:(x1-x0<=7*86400)?'2-digit':undefined});
var tw=tip.offsetWidth;tip.style.left=Math.min(Math.max(px-tw/2,0),w-tw)+'px';tip.style.top='4px'}else tip.style.display='none';
cv._m={X:X,P:P}}
function stats_(){var P=st.P;if(!P.length){stats.innerHTML='';return}var a=P[0][1],b=P[P.length-1][1],lo=Math.min.apply(null,P.map(function(p){return p[1]})),hi=Math.max.apply(null,P.map(function(p){return p[1]}));var ch=b-a,pc=a?ch/Math.abs(a)*100:0;
stats.innerHTML="<div>Ultimo<b>"+fmt(b,st.dec)+"</b></div><div>Variazione<b style='color:"+(ch>=0?css('--ok'):css('--bad'))+"'>"+(ch>=0?'+':'−')+fmt(Math.abs(ch),st.dec)+' ('+(ch>=0?'+':'−')+fmt(Math.abs(pc),1)+"%)</b></div><div>Minimo<b>"+fmt(lo,st.dec)+"</b></div><div>Massimo<b>"+fmt(hi,st.dec)+"</b></div>"}
function setRange(r){st.range=r;st.P=pts(st.s,r);stats_();rbox.querySelectorAll('button').forEach(function(b){b.classList.toggle('on',b.dataset.r===r)});draw(null)}
function show(key){load(function(D){var s=D[key];st.key=key;st.s=s;if(!s){title.textContent='Grafico non disponibile';stats.innerHTML='';st.P=[];draw(null);rbox.innerHTML='';help.textContent='Questo dato non è ancora stato scaricato.';return}
st.dec=s.dec==null?2:s.dec;title.innerHTML='<h3 style="margin:0 0 4px">'+s.l+'</h3>';help.textContent=(window.HELP&&window.HELP[key])||'';
var av=avail(s);rbox.innerHTML='';RANGES.forEach(function(r){var b=document.createElement('button');b.textContent=r[1];b.dataset.r=r[0];b.disabled=!av[r[0]];b.onclick=function(){setRange(r[0])};rbox.appendChild(b)});
var want=st.range;if(!av[want]){want=['3m','1m','1y','max'].filter(function(r){return av[r]})[0]||'max'}setRange(want)})}
function move(ev){var m=cv._m;if(!m)return;var r=cv.getBoundingClientRect(),x=(ev.touches?ev.touches[0].clientX:ev.clientX)-r.left;var P=m.P,lo=0,hi=P.length-1;while(hi-lo>1){var mid=(lo+hi)>>1;if(m.X(P[mid][0])<x)lo=mid;else hi=mid}var i=Math.abs(m.X(P[lo][0])-x)<Math.abs(m.X(P[hi][0])-x)?lo:hi;draw(i)}
cv.addEventListener('mousemove',move);cv.addEventListener('touchstart',move,{passive:true});cv.addEventListener('touchmove',move,{passive:true});cv.addEventListener('mouseleave',function(){draw(null)});cv.addEventListener('touchend',function(){setTimeout(function(){draw(null)},1500)});
window.addEventListener('resize',function(){draw(null)});
return{show:show,redraw:function(){draw(null)}}}
var modal=document.getElementById('cm'),mv=null;
function openChart(key){if(!modal)return;modal.classList.add('show');if(!mv)mv=mount(modal.querySelector('.cbody'));mv.show(key)}
if(modal){modal.addEventListener('click',function(e){if(e.target===modal||e.target.classList.contains('cx'))modal.classList.remove('show')});document.addEventListener('keydown',function(e){if(e.key==='Escape')modal.classList.remove('show')})}
document.addEventListener('click',function(e){var el=e.target.closest&&e.target.closest('[data-chart]');if(el&&el.dataset.chart)openChart(el.dataset.chart)});
var emb=document.getElementById('embedchart');if(emb){var ev=mount(emb);var chips=document.querySelectorAll('#chartchips .chip');chips.forEach(function(c){c.onclick=function(){chips.forEach(function(x){x.classList.toggle('on',x===c)});ev.show(c.dataset.k)}});if(chips.length){chips[0].classList.add('on');ev.show(chips[0].dataset.k)}}
window.showM=function(h){document.querySelectorAll('.mpane').forEach(function(e){e.style.display=e.id==='mp-'+h?'':'none'});document.querySelectorAll('.tab[data-m]').forEach(function(e){e.classList.toggle('on',e.dataset.m===h)})};
/* registro */
var rs=document.getElementById('regsel');
if(rs){var GROUPS={'Principali':['vwce_ultimo','sp500','vix','p_10g','p_1m','p_3m','p_6m','livello_1m','livello_3m'],'Prezzi e volatilità':['vwce','vt','nasdaq100','sp500','vix','vix3m','vvix','skew','move'],
'Credito, tassi e dollaro':['hy_oas','baa10y','nfci','t10y3m','t10y2y','dgs10','real10y','usd_broad','eurusd'],'Valutazioni':['cape_m','pe_m','ps_m','val_pe_vwce','val_ps_vwce','val_pe_sp500','val_ps_sp500','val_pe_ndx','val_ps_ndx','top_ps','top_pe','top_fcf_yield','ai_capex_ocf'],
'Sentiment e geopolitica':['aaii_spread','fear_greed','breadth200','breadth50','nh_nl','gpr','epu','news_sent_macro','news_neg_macro','news_pos_macro'],'Materie prime e macro':['gold','wti','unrate','icsa','cpi'],'Tutte le colonne':null};
Object.keys(GROUPS).forEach(function(k){var o=document.createElement('option');o.textContent=k;rs.appendChild(o)});
var rows=[],hdr=[];function csv(t){var L=t.trim().split(/\r?\n/).map(function(l){return l.split(',')});hdr=L[0];rows=L.slice(1)}
function lab(c){return (window.LABELS&&window.LABELS[c])||c.replace(/_/g,' ')}
function render(){var g=GROUPS[rs.value],q=document.getElementById('regq').value.trim();var cols=g?['date'].concat(g.filter(function(c){return hdr.indexOf(c)>=0})):hdr.filter(function(c){return c.slice(-5)!=='_data'||true});
var idx=cols.map(function(c){return hdr.indexOf(c)});var R=rows.filter(function(r){return !q||r[0].indexOf(q)===0||r[0].indexOf(q)>=0}).slice().reverse().slice(0,q?400:60);
var h='<table><thead><tr>'+cols.map(function(c){return '<th>'+lab(c)+'</th>'}).join('')+'</tr></thead><tbody>'+R.map(function(r){return '<tr>'+idx.map(function(i){var v=r[i]===undefined?'':r[i];if(v!==''&&!isNaN(v)&&i>0&&v.indexOf('-')<0)v=(+v).toLocaleString('it-IT',{maximumFractionDigits:4});return '<td>'+v+'</td>'}).join('')+'</tr>'}).join('')+'</tbody></table>';
document.getElementById('regtab').innerHTML=h;document.getElementById('regmeta').textContent=rows.length+' giorni registrati dal '+(rows.length?rows[0][0]:'—')+' · mostro '+R.length+' righe'}
fetch('registro.csv?'+Date.now()).then(function(r){return r.text()}).then(function(t){csv(t);render()}).catch(function(){document.getElementById('regtab').innerHTML='<p class="muted">Il registro si vede online (non dal file locale).</p>'});
rs.onchange=render;document.getElementById('regq').oninput=render}
})();
</script>
"""

MODAL = ("<div id='cm' class='cmodal'><div class='cbox'><button class='cx' aria-label='Chiudi'>×</button><div class='cbody'></div></div></div>")


def _safe(fn, label):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return f"<p class='mu'>{label} non disponibile oggi ({type(e).__name__}).</p>"


def context_section(p) -> str:
    """Regime di mercato, volatilità attesa e calendario eventi."""
    import json
    from datetime import date
    from . import calendario, regime, volatility
    from .config import DATA

    def cal():
        try:
            earn = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            earn = []
        return calendario.html(calendario.events(date.today(), 45, earn))
    return ("<h2 id='contesto'>Contesto: regime, volatilità attesa e calendario</h2>"
            "<h3>Regime di mercato</h3><div class='card'>" + _safe(lambda: regime.html(regime.compute(p)), "Regime") + "</div>"
            "<h3 style='margin-top:18px'>Volatilità attesa nel prossimo mese</h3><div class='card'>" + _safe(lambda: volatility.html(volatility.forecast(p)), "Previsione della volatilità") + "</div>"
            "<h3 style='margin-top:18px'>Prossimi eventi che muovono i mercati</h3><div class='card scroll'>" + _safe(cal, "Calendario") + "</div>")


def portfolio_section() -> str:
    from . import fx, holdings
    return ("<h2 id='portafoglio'>Il tuo VWCE: rischio di cambio e cosa contiene</h2>"
            "<h3>Cambio EUR/USD</h3><div class='card'>" + _safe(lambda: fx.html(fx.compute()), "Cambio") + "</div>"
            "<h3 style='margin-top:18px'>Composizione del fondo e concentrazione</h3><div class='card'>" + _safe(lambda: holdings.html(holdings.load()), "Composizione") + "</div>")


CSS += """
.kc{background:var(--bg);border-radius:12px;padding:12px}.kc .k{font-size:12px;color:var(--mu);text-transform:uppercase;letter-spacing:.03em}.kc .v{font-size:30px;font-weight:800;line-height:1.15}.kc .s{font-size:13px;color:var(--mu)}
.kc.ok .v{color:var(--ok)}.kc.wa .v{color:var(--warn)}.kc.ba .v{color:var(--bad)}
.bar{height:8px;background:var(--bd);border-radius:4px;min-width:60px}.bar i{display:block;height:100%;background:var(--ac);border-radius:4px}
table.cal tr.hi td{background:var(--warnbg)}
"""
