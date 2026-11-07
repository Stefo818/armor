"""Nuovi pezzi dell'app (Fase 3): prossimo evento, pagina «Quanto mi posso fidare», sezione «Il mio PAC» (dati solo nel telefono)."""
import html as _h
import json
from datetime import date, datetime, timedelta

import pandas as pd

from .config import DATA, HORIZONS, HZ_LABEL, PRIMARY

e = _h.escape


def _pc(x, d=0, sign=False):
    return "n.d." if x is None or x != x else (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%").replace(".", ",")


# ---------------------------------------------------------------- blocco 5 di «Oggi»
def next_event_html(today: date | None = None) -> str:
    from . import extra13
    today = today or date.today()
    evs = [x for x in extra13.all_events(today, today + timedelta(days=21)) if x["peso"] >= 2 and x["date"] >= today.isoformat()]
    if not evs:
        return "<div class='card b5ev'><div class='lab'>Prossimo evento importante</div><b>Nessun evento importante nelle prossime 3 settimane.</b></div>"
    x = evs[0]
    d = datetime.fromisoformat(x["date"]).date()
    n = (d - today).days
    quando = "oggi" if n == 0 else ("domani" if n == 1 else f"tra {n} giorni")
    return (f"<div class='card b5ev'><div class='lab'>Prossimo evento importante</div><div class='evn'>{e(x['nome'])}</div>"
            f"<div class='evd'><b>{d.strftime('%d/%m/%Y')}</b> · {quando}</div>"
            "<div class='mu'>Nei giorni degli eventi i prezzi oscillano di più: non reagire d'istinto. <a href='#' data-cal='1'>Calendario completo ›</a></div></div>")


# ---------------------------------------------------------------- pagina «Quanto mi posso fidare»
def verdict(bss: float, lo: float, hi: float, recent: float | None) -> tuple[str, str]:
    """(classe, frase) onesta per un orizzonte. «Batte» solo se l'intervallo al 90% sta tutto sopra zero."""
    if bss == bss and lo == lo and lo > 0:
        cls, txt = "ok", "batte la media storica"
    elif bss == bss and bss > 0.02:
        cls, txt = "warn", "è un po' meglio della media storica, ma i test non bastano a dimostrarlo"
    else:
        cls, txt = "bad", "non batte la media storica: qui conta il confronto con il «normale», non il numero"
    if recent is not None and recent == recent and recent < -0.02:
        txt += "; dal 2013 ha fatto peggio del normale"
    return cls, txt


def calib_svg(pts: list[tuple[float, float]], w: int = 210) -> str:
    """Grafico di taratura: previsto (asse x) contro realmente avvenuto (asse y), 10 gruppi di giorni."""
    if not pts:
        return ""
    m = max(max(p for p, _ in pts), max(r for _, r in pts), 0.05) * 1.1
    pad, S = 28, w - 36
    X = lambda v: pad + v / m * S
    Y = lambda v: pad + S - v / m * S
    dots = "".join(f"<circle cx='{X(p):.1f}' cy='{Y(r):.1f}' r='4.5' fill='var(--ac)'/>" for p, r in pts)
    line = "<polyline fill='none' stroke='var(--ac)' stroke-width='1.5' points='" + " ".join(f"{X(p):.1f},{Y(r):.1f}" for p, r in sorted(pts)) + "'/>"
    t = lambda v: f"{v * 100:.0f}%"
    return (f"<svg viewBox='0 0 {w} {w + 14}' class='calsvg' role='img' aria-label='Previsto contro reale'>"
            f"<rect x='{pad}' y='{pad}' width='{S}' height='{S}' fill='none' stroke='var(--bd)'/>"
            f"<line x1='{X(0)}' y1='{Y(0)}' x2='{X(m)}' y2='{Y(m)}' stroke='var(--mu)' stroke-dasharray='4 4'/>{line}{dots}"
            f"<text x='{pad}' y='{pad + S + 12}' class='ax'>0</text><text x='{pad + S}' y='{pad + S + 12}' text-anchor='end' class='ax'>{t(m)}</text>"
            f"<text x='{pad - 4}' y='{pad + 8}' text-anchor='end' class='ax'>{t(m)}</text>"
            f"<text x='{pad + S / 2}' y='{w + 10}' text-anchor='middle' class='ax'>previsto</text>"
            f"<text x='8' y='{pad + S / 2}' class='ax' transform='rotate(-90 8 {pad + S / 2})' text-anchor='middle'>avvenuto</text></svg>")


def fiducia_html(sp: pd.Series | None = None, ev: dict | None = None, live: pd.DataFrame | None = None) -> str:
    if ev is None:
        try:
            ev = json.loads((DATA / "model_eval.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            ev = None
    if not ev:
        return "<div class='card'><p class='mu'>Il test storico dei modelli non è ancora disponibile: si crea con la «Convalida mensile» di GitHub.</p></div>"
    m = pd.DataFrame(ev["metrics"])
    cal = pd.DataFrame(ev["calibration"])
    sets = "modelli"
    cards, verdicts, recent = "", {}, []
    cov = ev.get("intervalli", {})
    for hz in HORIZONS:
        thr = PRIMARY[hz]
        a = m[(m.set == sets) & (m.model == "A1") & (m.hz == hz) & (m.thr == thr) & (m.kind == "down")]
        if a.empty:
            continue
        a = a.iloc[0]
        cls, txt = verdict(a.bss, a.bss_lo, a.bss_hi, a.bss_2013_26)
        verdicts[hz] = (cls, txt)
        if a.bss_2013_26 == a.bss_2013_26 and a.bss_2013_26 < -0.02:
            recent.append(hz)
        c = cal[(cal.set == sets) & (cal.model == "A1") & (cal.hz == hz) & (cal.thr == thr) & (cal.kind == "down")]
        svg = calib_svg(list(zip(c.prev, c.real)))
        cv = (cov.get(hz) or {}).get("A1")
        cvt = f"Intervallo all'80% dei rendimenti: copre il {cv['copertura_conformale'] * 100:.0f}% dei casi." if cv else ""
        lv = ""
        if live is not None and len(live):
            r = live[(live.kind == "calo") & (live.hz == hz)]
            if len(r):
                r = r.iloc[0]
                lv = (f"<p class='mu'>Dal vivo: {int(r.n)} previsioni scadute, BSS {r.bss:+.2f}. " if r.n >= 20 else f"<p class='mu'>Dal vivo: solo {int(r.n)} previsioni scadute, troppo poche per giudicare. ").replace(".", ",") + "</p>"
        cards += (f"<div class='card fcard'><div class='hzh'><h3>{HZ_LABEL[hz]}: calo ≥{thr}%</h3><span class='badge {cls}'>{'batte il normale' if cls == 'ok' else ('forse' if cls == 'warn' else 'non batte il normale')}</span></div>"
                  f"<div class='fgrid'><div>{svg}</div><div><p><b>A {HZ_LABEL[hz]} Armor {e(txt)}.</b></p>"
                  f"<p class='mu'>Punteggio BSS {_n(a.bss)} (intervallo al 90%: da {_n(a.bss_lo)} a {_n(a.bss_hi)}; 0 = come la media storica). AUC {_n(a.auc, plain=True)}. Dal 2013: {_n(a.bss_2013_26)}.</p>"
                  f"<p class='mu'>{e(cvt)}</p>{lv}</div></div>"
                  f"<p class='mu'>Come leggere il grafico: se i punti stanno sulla linea tratteggiata, le probabilità previste coincidono con quanto è successo davvero. "
                  f"Sopra la linea = Armor sottostima, sotto = sovrastima ({int(a.n)} giorni di prova, dal {e(str(a.da))}).</p></div>")
    if not cards:
        return "<div class='card'><p class='mu'>Dati del test non ancora completi.</p></div>"
    names = {"10g": "a 10 giorni", "1m": "a 1 mese", "3m": "a 3 mesi", "6m": "a 6 mesi"}
    j = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " e " + xs[-1]
    ok = [names[h] for h, (c, _t) in verdicts.items() if c == "ok"]
    mid = [names[h] for h, (c, _t) in verdicts.items() if c == "warn"]
    no = [names[h] for h, (c, _t) in verdicts.items() if c == "bad"]
    parts = []
    if ok:
        parts.append(f"{j(ok)} Armor <b>batte la media storica</b>")
    if mid:
        parts.append(f"{j(mid)} è <b>un po' meglio della media, ma non dimostrato</b>")
    if no:
        parts.append(f"{j(no)} <b>non la batte</b>: mostra più che altro quanto il rischio è alto o basso rispetto al normale")
    rec = (f" Attenzione: {j([names[h] for h in recent])}, dal 2013 in poi, ha fatto <b>peggio</b> del normale." if recent else "")
    lead = ("<div class='explain fid'><p><b>La risposta onesta:</b> " + "; ".join(parts) + "." + rec +
            " Armor misura il rischio, non prevede il futuro. I test sono fatti sul passato, senza usare dati futuri.</p></div>")
    return (lead + cards + "<div class='card'><p class='mu'>Il «normale» è la frequenza storica dell'evento (quanto spesso succede in generale). "
            "Il BSS dice di quanto Armor fa meglio di questa semplice media: sotto 0 fa peggio, 0,05 è un piccolo miglioramento, 0,20 sarebbe molto buono. "
            "Il test usa le previsioni di ogni data come le avrebbe fatte Armor allora (walk-forward). Le finestre a 3-6 mesi si sovrappongono: "
            "i casi davvero indipendenti sono molti meno dei giorni testati.</p></div>")


def _n(x, plain: bool = False) -> str:
    return (f"{x:.2f}" if plain else f"{x:+.2f}").replace(".", ",")


# ---------------------------------------------------------------- sezione «Il mio PAC»
PAC_HTML = """<div class='card' id='pacbox'><h3 style='margin-top:0'>Il mio PAC</h3>
<p class='mu'>I tuoi dati restano <b>solo in questo telefono</b> (non vengono inviati a nessuno). Stima semplice: una rata al mese, alla stessa data, al prezzo di quel giorno. Non è un consiglio di acquisto o di vendita.</p>
<div class='pacform'><label>Importo mensile (€)<input id='pacamt' type='number' min='1' step='1' inputmode='decimal' placeholder='es. 200'></label>
<label>Data di inizio<input id='pacstart' type='date'></label>
<button class='btn pri' id='pacsave'>Calcola</button> <button class='btn' id='pacclear'>Cancella i miei dati</button></div>
<div id='pacout' class='pacout'></div></div>"""

PAC_JS = r"""<script>
(function(){var A=document.getElementById('pacamt');if(!A)return;var S=document.getElementById('pacstart'),O=document.getElementById('pacout'),K='armor_pac_v1';
function fm(v,d){return v.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function get(){try{return JSON.parse(localStorage.getItem(K)||'null')}catch(e){return null}}
function put(o){try{localStorage.setItem(K,JSON.stringify(o))}catch(e){}}
var s0=get();if(s0){A.value=s0.amt;S.value=s0.start}
var series=null;
function loadS(cb){if(series)return cb(series);fetch('series/vwce.json?'+Date.now()).then(function(r){return r.ok?r.json():null}).then(function(j){series=j&&j.d?j:{d:[],v:[]};cb(series)}).catch(function(){series={d:[],v:[]};cb(series)})}
function calc(amt,start){loadS(function(s){if(!s.d.length){O.innerHTML='<p class="muted">Prezzi del VWCE non disponibili ora.</p>';return}
var t0=Date.parse(start)/86400000,last=s.d[s.d.length-1],px=s.v[s.v.length-1],L=window.LIVE&&LIVE.quotes&&LIVE.quotes.vwce&&LIVE.quotes.vwce.price;if(L)px=L;
function at(day){var lo=0,hi=s.d.length-1;if(day<=s.d[0])return s.v[0];while(hi-lo>1){var m=(lo+hi)>>1;if(s.d[m]<=day)lo=m;else hi=m}return s.v[lo]}
var sd=new Date(start+'T00:00:00Z'),dom=sd.getUTCDate(),y=sd.getUTCFullYear(),m=sd.getUTCMonth(),inv=0,q=0,n=0,peak=0,mdd=0,mdate=null,cur=null;
while(true){var dt=Date.UTC(y,m,Math.min(dom,28))/86400000;if(dt>last)break;var p=at(dt);inv+=amt;q+=amt/p;n++;m++;if(m>11){m=0;y++}}
if(!n){O.innerHTML='<p class="muted">La data di inizio è nel futuro o troppo vicina: nessuna rata ancora.</p>';return}
var avg=inv/q,val=q*px,pl=val/inv-1;
for(var i=0;i<s.d.length;i++){if(s.d[i]<t0)continue;if(s.v[i]>peak)peak=s.v[i];var d=s.v[i]/peak-1;if(d<mdd){mdd=d;mdate=s.d[i]}}
var diff=px/avg-1,cls=diff<0?'dn':'up';
var h='<div class="pacg"><div class="kc"><div class="k">Versato ('+n+' rate)</div><div class="v">'+fm(inv,0)+' €</div></div><div class="kc"><div class="k">Valore stimato</div><div class="v">'+fm(val,0)+' €</div></div>'+
'<div class="kc"><div class="k">Prezzo medio di carico</div><div class="v">'+fm(avg,2)+' €</div></div><div class="kc"><div class="k">Risultato</div><div class="v '+cls+'">'+(pl>=0?'+':'')+fm(pl*100,1)+'%</div></div></div>';
h+='<p>Il VWCE oggi vale <b>'+fm(px,2)+' €</b>, cioè <b class="'+cls+'">'+(diff>=0?'+':'')+fm(diff*100,1)+'%</b> rispetto al tuo prezzo medio di carico.'+(diff<0?' La prossima rata compra quote a un prezzo più basso del tuo medio: è così che i cali aiutano un PAC.':' La prossima rata compra a un prezzo sopra il tuo medio: normale nelle fasi di rialzo.')+'</p>';
h+='<table><tr><th>Se il prezzo scendesse del…</th><th>Quote della prossima rata</th><th>Nuovo prezzo medio</th></tr>';
[0,5,10,20].forEach(function(c){var pp=px*(1-c/100),nq=amt/pp,na=(inv+amt)/(q+nq);h+='<tr><td>'+(c?'−'+c+'%':'oggi')+' ('+fm(pp,2)+' €)</td><td>'+fm(nq,3)+'</td><td>'+fm(na,2)+' €</td></tr>'});
h+='</table>';
if(mdate!==null)h+='<p class="mu">Dal tuo inizio il calo massimo del VWCE dal suo massimo è stato <b>'+fm(mdd*100,1)+'%</b> (verso il '+new Date(mdate*86400000).toLocaleDateString('it-IT',{month:'long',year:'numeric'})+'). Le rate pagate in quel periodo hanno comprato quote a prezzi più bassi.</p>';
h+='<p class="mu">Prima del 2019 il prezzo del VWCE è stimato dall\'indice mondiale (VT) e dal cambio; prezzi dei mesi recenti senza costi, tasse e commissioni. È una stima, non il tuo estratto conto.</p>';O.innerHTML=h})}
document.getElementById('pacsave').onclick=function(){var a=parseFloat(A.value),st=S.value;if(!(a>0)||!st){O.innerHTML='<p class="muted">Inserisci importo e data di inizio.</p>';return}put({amt:a,start:st});calc(a,st)};
document.getElementById('pacclear').onclick=function(){try{localStorage.removeItem(K)}catch(e){}A.value='';S.value='';O.innerHTML='<p class="muted">Dati cancellati da questo telefono.</p>'};
if(s0)calc(+s0.amt,s0.start)})();
</script>"""

CSS = """
.b5{margin:0 0 12px}.b5ev .evn{font-size:20px;font-weight:800;margin:2px 0}.b5ev .evd{font-size:15px;margin-bottom:4px}.b5ev .lab{font-size:12px;color:var(--mu);text-transform:uppercase;letter-spacing:.5px}
.more{font-size:13px;color:var(--mu);margin:6px 0 16px}.more a{color:var(--ac)}
.fcard{margin:12px 0}.fgrid{display:grid;grid-template-columns:minmax(150px,230px) 1fr;gap:14px;align-items:center}.calsvg{width:100%;height:auto;max-width:230px}
.fid p{font-size:16px}@media(max-width:600px){.fgrid{grid-template-columns:1fr}.calsvg{max-width:260px;margin:auto;display:block}}
.pacform{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:10px 0}.pacform label{display:grid;gap:3px;font-size:13px;color:var(--mu)}
.pacform input{padding:9px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--tx);font:inherit;min-width:140px}
.pacg{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}.pacout table{margin:8px 0}
"""
