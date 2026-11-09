"""Grafico di confronto giornaliero: in alto S&P 500 (giallo tratteggiato) e VWCE (blu tratteggiato), sotto Indice Armor, probabilità di calo e di rialzo,
VIX, spread e famiglie, attivabili a piacere. Dati in series/confronto.json (caricati a richiesta)."""
import json

import numpy as np
import pandas as pd

from . import armor_index, semafori, store
from .config import DATA

SERIES = [  # chiave, etichetta, colore, unità, gruppo iniziale attivo
    ("armor", "Indice Armor", "tx", "", 1),
    ("p_calo_1m", "Prob. calo ≥10% a 1 mese", "#ef4444", "%", 1),
    ("p_up_1m", "Prob. rialzo ≥5% a 1 mese", "#22c55e", "%", 1),
    ("p_calo_10g", "Prob. calo ≥5% a 10 giorni", "#f97316", "%", 0),
    ("p_calo_3m", "Prob. calo ≥10% a 3 mesi", "#dc2626", "%", 0),
    ("vix", "VIX", "#f59e0b", "", 0),
    ("hy_oas", "Spread High Yield", "#a16207", " %", 0),
    ("g_paura", "Famiglia Paura e stress", "#06b6d4", "", 0),
    ("g_credito", "Famiglia Credito", "#14b8a6", "", 0),
    ("g_valutazioni", "Famiglia Valutazioni", "#ec4899", "", 0),
    ("dd252", "Distanza dai massimi (S&P)", "#64748b", " %", 0),
]


def build(sp: pd.Series, vw: pd.Series, aix: dict | None) -> dict | None:
    if not aix:
        return None
    sp = sp.dropna()
    sp = sp[sp.index >= "2000-01-03"]
    idx = sp.index

    def al(s: pd.Series, limit: int = 7) -> pd.Series:
        s = s.dropna()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        return s.reindex(s.index.union(idx)).ffill(limit=limit).reindex(idx)

    out = {"sp500": al(sp), "vwce": al(vw, 5) if len(vw) else pd.Series(np.nan, index=idx)}
    out["armor"] = al(aix["hist"], 3)
    rh = DATA / "risk_history.csv"
    if rh.exists():
        h = pd.read_csv(rh, parse_dates=["date"]).set_index("date")
        for k, c in (("p_calo_10g", "p_10g"), ("p_calo_1m", "p_1m"), ("p_calo_3m", "p_3m")):
            if c in h:
                out[k] = al(h[c] * 100, 5)
    fe = DATA / "fhs_eval.csv"
    if fe.exists():
        f = pd.read_csv(fe, parse_dates=["date"])
        u = f[(f.hz == "1m") & (f.kind == "up") & (f.thr == 5)].set_index("date")["p"] * 100
        out["p_up_1m"] = al(u, 10)
    for k, key in (("vix", "vix"), ("hy_oas", "hy_oas")):
        try:
            out[k] = al(store.load(key), 5)
        except Exception:  # noqa: BLE001
            pass
    G = aix["G"]
    for k, g in (("g_paura", "Paura e stress dei mercati"), ("g_credito", "Credito e liquidità"), ("g_valutazioni", "Valutazioni")):
        if g in G:
            out[k] = al(1 + 99 * ((G[g] - 0.10) / 0.75).clip(0, 1), 3)
    try:
        f = armor_index.price_features if hasattr(armor_index, "price_features") else None
        from .features import price_features
        out["dd252"] = al(-price_features(sp)["dd252"] * 100, 3)
    except Exception:  # noqa: BLE001
        pass
    ser = {}
    for k, s in out.items():
        ser[k] = [None if pd.isna(x) else round(float(x), 2 if k in ("sp500", "vwce") else 1) for x in s.values]
    return {"d": [int(t.value // 86_400_000_000_000) for t in idx], "s": ser,
            "meta": [{"k": k, "n": n, "c": c, "u": u, "on": on} for k, n, c, u, on in SERIES if k in ser], "asof": str(idx[-1].date())}


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


CSS = """
.cfw{margin:8px 0}.cfbar{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}.cfbar button,.cfchips label{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
.cfbar button.on{background:var(--ac);color:#fff;border-color:var(--ac);font-weight:700}.cfchips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.cfchips label{display:flex;align-items:center;gap:6px}.cfchips label.on{border-width:2px;font-weight:700}
.cfchips i{display:inline-block;width:14px;height:4px;border-radius:2px}.cfwrap{position:relative;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:6px 4px}
.cfwrap canvas{width:100%;display:block;touch-action:pan-y;user-select:none;-webkit-user-select:none}.cftip{position:absolute;pointer-events:none;background:var(--card);color:var(--tx);border:1px solid var(--ac);border-radius:10px;padding:8px 10px;font-size:12px;line-height:1.45;box-shadow:0 6px 20px rgba(0,0,0,.4);display:none;z-index:5;min-width:170px}
.cfst{font-size:13px;margin:8px 0}.cfl{font-size:12px;color:var(--mu);display:flex;gap:14px;flex-wrap:wrap;margin:4px 6px}.cfl i{display:inline-block;width:18px;border-top:3px solid;margin-right:5px;vertical-align:middle;box-shadow:0 0 6px currentColor}.cfl span{display:inline-flex;align-items:center}
.cfchips label{transition:box-shadow .15s,opacity .15s}.cfchips label:not(.on){opacity:.55}.cfchips label.on i{box-shadow:0 0 8px 1px currentColor}
.cfzoom{font-size:13px;margin:4px 0;min-height:30px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.cfzoom button{border:1px solid var(--ac);background:var(--ac);color:#fff;border-radius:99px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer}
.cfwrap canvas{cursor:crosshair}
"""

JS = r"""
<script>
(function(){
function nf(x,d){return x==null?'n.d.':x.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function init(root){
if(root.dataset.on)return;root.dataset.on='1';root.innerHTML='<p class="mu">Caricamento del grafico…</p>';
var D=null,per=1095,act={},zoom=null,dragA=null,dragB=null,tstart=null;
var emb=document.getElementById('armor-cf-data');
function go(j){D=j;D.meta.forEach(function(m){act[m.k]=!!m.on});build()}
if(window.__ARMOR_CF){go(window.__ARMOR_CF)}else if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/confronto.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){window.__ARMOR_CF=j;go(j)}).catch(function(){root.innerHTML='<p class="mu">Grafico non disponibile (serve la connessione).</p>'})}
var TX=getComputedStyle(document.body).color;
function colr(m){return m.c==='tx'?TX:m.c}
function build(){
 var P=[[63,'3 mesi'],[126,'6 mesi'],[252,'1 anno'],[756,'3 anni'],[1260,'5 anni'],[2520,'10 anni'],[99999,'Tutto (dal 2000)']];
 root.innerHTML='<div class="cfbar"><b>Periodo:</b>'+P.map(function(p){return '<button data-p="'+p[0]+'"'+(per===p[0]?' class="on"':'')+'>'+p[1]+'</button>'}).join('')+'</div>'+
 '<div class="cfzoom"></div><div class="cfl"><span><i style="border-color:#e6a700;color:#e6a700"></i>S&amp;P 500 (base 100 al primo giorno con entrambi)</span><span><i style="border-color:#3b82f6;color:#3b82f6"></i>VWCE (base 100)</span></div>'+
 '<div class="cfwrap"><canvas id="cfc"></canvas><div class="cftip"></div></div>'+
 '<div class="cfchips">'+D.meta.map(function(m){var c=colr(m);return '<label data-k="'+m.k+'" class="'+(act[m.k]?'on':'')+'" style="'+(act[m.k]?'border-color:'+c+';box-shadow:0 0 10px '+c+'66,inset 0 0 6px '+c+'33':'')+'"><i style="background:'+c+';color:'+c+'"></i>'+m.n+'</label>'}).join('')+'</div>'+
 '<div class="cfst"></div><div class="mu">Passa il mouse o tocca il grafico: vedi data e valori. <b>Trascina</b> (mouse o dito in orizzontale) per selezionare un periodo e ingrandirlo. In basso puoi accendere o spegnere più linee insieme: con una sola linea la scala è quella reale, con più linee ognuna è riportata a 0–100% del suo minimo e massimo nel periodo (i valori reali sono nel riquadro).</div>';
 draw()}
var BASE=[null,null],cv,ctx,W,H1=190,H2=190,GAP=22,L=40,R=8,T=8,i0,i1,hov=null;
function rng(arr,a,b){var mn=1e18,mx=-1e18;for(var i=a;i<=b;i++){var v=arr[i];if(v==null)continue;if(v<mn)mn=v;if(v>mx)mx=v}return mn>mx?null:[mn,mx]}
function draw(){cv=root.querySelector('#cfc');var n=D.d.length;i1=n-1;i0=Math.max(0,n-per);if(zoom){i0=zoom[0];i1=zoom[1]}var w=cv.parentNode.clientWidth-8;W=w;var dpr=window.devicePixelRatio||1;var Ht=T+H1+GAP+H2+22;cv.width=w*dpr;cv.height=Ht*dpr;cv.style.height=Ht+'px';ctx=cv.getContext('2d');ctx.scale(dpr,dpr);
 var tx=TX,bd=getComputedStyle(document.body).getPropertyValue('--bd')||'#8884',mu=getComputedStyle(document.body).getPropertyValue('--mu')||'#888';
 function X(i){return L+(i-i0)/Math.max(1,i1-i0)*(W-L-R)}
 // pannello alto: S&P e VWCE rebased
 function base(arr){for(var i=i0;i<=i1;i++)if(arr[i]!=null)return arr[i];return null}
 var sp=D.s.sp500,vw=D.s.vwce,ib=null;for(var q=i0;q<=i1;q++){if(sp[q]!=null&&vw[q]!=null){ib=q;break}}
 var bs=ib!=null?sp[ib]:base(sp),bv=ib!=null?vw[ib]:null,A=[],B=[];BASE=[bs,bv];
 for(var i=i0;i<=i1;i++){A[i]=(sp[i]!=null&&bs)?sp[i]/bs*100:null;B[i]=(vw[i]!=null&&bv)?vw[i]/bv*100:null}
 var r1=rng(A.concat(B).length?A:A,i0,i1),r2=rng(B,i0,i1),lo=Math.min(r1?r1[0]:1e9,r2?r2[0]:1e9),hi=Math.max(r1?r1[1]:-1e9,r2?r2[1]:-1e9);var pad=(hi-lo)*0.06;lo-=pad;hi+=pad;
 function Y1(v){return T+(1-(v-lo)/(hi-lo))*H1}
 ctx.font='10px system-ui';ctx.fillStyle=mu;ctx.strokeStyle=bd;ctx.lineWidth=1;
 for(var g=0;g<=4;g++){var v=lo+(hi-lo)*g/4,y=Y1(v);ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillText(nf(v,0),2,y+3)}
 function line(arr,Y,color,dash,lw){ctx.beginPath();var st=false;ctx.strokeStyle=color;ctx.lineWidth=lw||1.6;ctx.setLineDash(dash||[]);ctx.shadowColor=color;ctx.shadowBlur=7;for(var i=i0;i<=i1;i++){var v=arr[i];if(v==null){st=false;continue}var x=X(i),y=Y(v);if(!st){ctx.moveTo(x,y);st=true}else ctx.lineTo(x,y)}ctx.stroke();ctx.setLineDash([]);ctx.shadowBlur=0}
 line(A,Y1,'#e6a700',null,2);line(B,Y1,'#3b82f6',null,2);
 // pannello basso
 var ks=D.meta.filter(function(m){return act[m.k]}),y0=T+H1+GAP;
 function Y2(v,r){return y0+(1-(v-r[0])/Math.max(1e-9,(r[1]-r[0])))*H2}
 var single=ks.length===1,rs={};ks.forEach(function(m){var r=rng(D.s[m.k],i0,i1);if(r){var p=(r[1]-r[0])*0.06||1;rs[m.k]=[r[0]-p,r[1]+p]}});
 ctx.strokeStyle=bd;ctx.fillStyle=mu;
 for(var g=0;g<=4;g++){var y=y0+H2*g/4;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();var lab=single&&rs[ks[0].k]?nf(rs[ks[0].k][1]-(rs[ks[0].k][1]-rs[ks[0].k][0])*g/4,ks[0].u?1:0):nf(100-25*g,0)+'%';ctx.fillText(lab,2,y+3)}
 ks.forEach(function(m){var r=rs[m.k];if(!r)return;line(D.s[m.k],function(v){return Y2(v,r)},colr(m),null,m.k==='armor'?2.6:1.6)});
 // asse x
 ctx.fillStyle=mu;var nt=5;for(var t=0;t<=nt;t++){var i=Math.round(i0+(i1-i0)*t/nt),dt=new Date(D.d[i]*86400000);ctx.textAlign=t===0?'left':(t===nt?'right':'center');ctx.fillText(('0'+(dt.getUTCMonth()+1)).slice(-2)+'/'+dt.getUTCFullYear(),X(i),T+H1+GAP+H2+14)}ctx.textAlign='left';
 ctx.fillStyle=tx;ctx.fillText('Mercato (base 100)',L+4,T+10);ctx.fillText(single?ks[0].n:'Indicatori (scala relativa 0–100%)',L+4,y0+10);
 if(dragA!=null&&dragB!=null){var xa=X(Math.min(dragA,dragB)),xb=X(Math.max(dragA,dragB));ctx.fillStyle='rgba(120,160,255,.22)';ctx.fillRect(xa,T,xb-xa,T+H1+GAP+H2-T);ctx.strokeStyle='rgba(120,160,255,.9)';ctx.lineWidth=1;ctx.strokeRect(xa,T,xb-xa,T+H1+GAP+H2-T)}
 if(hov!=null&&hov>=i0&&hov<=i1&&dragA==null){var x=X(hov);ctx.strokeStyle=tx;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,T+H1+GAP+H2);ctx.stroke()}
 stats(ks);zbar()}
function fd(i){var d=new Date(D.d[i]*86400000);return d.getUTCDate()+'/'+(d.getUTCMonth()+1)+'/'+d.getUTCFullYear()}
function zbar(){var z=root.querySelector('.cfzoom');if(!z)return;z.innerHTML=zoom?'<span>Zoom: <b>'+fd(i0)+' – '+fd(i1)+'</b> ('+(i1-i0+1)+' sedute)</span><button data-z="0">Azzera zoom</button>':'<span class="mu">Trascina sul grafico per ingrandire un periodo.</span>'}
function stats(ks){var el=root.querySelector('.cfst');var arm=D.s.armor,sp=D.s.sp500,hi=[],lo=[];
 for(var i=i0;i<=i1-21;i++){if(arm[i]==null||sp[i]==null||sp[i+21]==null)continue;var f=(sp[i+21]/sp[i]-1)*100;if(arm[i]>=60)hi.push(f);else if(arm[i]<=40)lo.push(f)}
 function av(a){return a.length?a.reduce(function(x,y){return x+y},0)/a.length:null}
 el.innerHTML='<b>Nel periodo scelto</b> (descrittivo, non una previsione): dopo i giorni con Indice Armor ≥60 l\'S&amp;P 500 ha reso in media <b>'+nf(av(hi),1)+'%</b> nel mese successivo ('+hi.length+' giorni); dopo quelli ≤40, <b>'+nf(av(lo),1)+'%</b> ('+lo.length+' giorni).'}
function tip(clientX){var rc=cv.getBoundingClientRect(),x=clientX-rc.left,i=Math.round(i0+(x-L)/(W-L-R)*(i1-i0));i=Math.max(i0,Math.min(i1,i));hov=i;draw();
 var t=root.querySelector('.cftip'),dt=new Date(D.d[i]*86400000),sp=D.s.sp500[i],vw=D.s.vwce[i],b1=BASE[0],b2=BASE[1];
 var h='<b>'+dt.getUTCDate()+'/'+(dt.getUTCMonth()+1)+'/'+dt.getUTCFullYear()+'</b><br><span style="color:#e6a700">■</span> S&amp;P 500: '+nf(sp,0)+(sp&&b1?' ('+nf((sp/b1-1)*100,1)+'% dalla base)':'')+'<br><span style="color:#3b82f6">■</span> VWCE: '+nf(vw,2)+(vw&&b2?' ('+nf((vw/b2-1)*100,1)+'%)':'');
 D.meta.filter(function(m){return act[m.k]}).forEach(function(m){var v=D.s[m.k][i];h+='<br><span style="color:'+colr(m)+'">■</span> '+m.n+': '+nf(v,1)+(m.u||'')});
 t.innerHTML=h;t.style.display='block';var tw=t.offsetWidth;var lx=x+14;if(lx+tw>rc.width)lx=x-tw-14;t.style.left=Math.max(0,lx)+'px';t.style.top='10px'}
root.addEventListener('click',function(e){var b=e.target.closest('button[data-p]');var zb=e.target.closest('button[data-z]');if(zb){zoom=null;hov=null;build();return}if(b){per=+b.dataset.p;zoom=null;hov=null;build();return}var l=e.target.closest('label[data-k]');if(l){var k=l.dataset.k;act[k]=!act[k];build()}});
function idx(cx){var rc=cv.getBoundingClientRect(),i=Math.round(i0+(cx-rc.left-L)/(W-L-R)*(i1-i0));return Math.max(i0,Math.min(i1,i))}
function endSel(){if(dragA==null)return;var a=Math.min(dragA,dragB==null?dragA:dragB),b=Math.max(dragA,dragB==null?dragA:dragB);dragA=dragB=null;if(b-a>=5){zoom=[a,b];hov=null;var t=root.querySelector('.cftip');if(t)t.style.display='none'}draw()}
root.addEventListener('mousedown',function(e){if(e.target===cv&&e.button===0){dragA=idx(e.clientX);dragB=dragA;e.preventDefault()}});
root.addEventListener('mousemove',function(e){if(e.target===cv||dragA!=null){if(dragA!=null){dragB=idx(e.clientX);draw()}else tip(e.clientX)}});
window.addEventListener('mouseup',function(){if(D&&dragA!=null)endSel()});
root.addEventListener('touchstart',function(e){if(e.target===cv&&e.touches[0]){tstart={x:e.touches[0].clientX,y:e.touches[0].clientY,i:idx(e.touches[0].clientX),sel:false}}},{passive:true});
root.addEventListener('touchmove',function(e){if(!tstart||!e.touches[0])return;var t=e.touches[0];if(!tstart.sel&&Math.abs(t.clientX-tstart.x)>12&&Math.abs(t.clientX-tstart.x)>Math.abs(t.clientY-tstart.y)){tstart.sel=true;dragA=tstart.i}if(tstart.sel){dragB=idx(t.clientX);draw()}},{passive:true});
root.addEventListener('touchend',function(e){if(!tstart)return;var sel=tstart.sel,x=tstart.x;tstart=null;if(sel)endSel();else tip(x)});
root.addEventListener('mouseleave',function(){hov=null;var t=root.querySelector('.cftip');if(t)t.style.display='none';if(D)draw()});
window.addEventListener('resize',function(){if(D&&root.querySelector('#cfc'))draw()});
}
window.armorConfronto=function(scope){(scope||document).querySelectorAll('.cfw[data-cf]').forEach(init)};
window.armorConfronto();
})();
</script>
"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-cf-data'>{data_json}</script>" if data_json else ""
    return f"{emb}<div class='cfw' data-cf='1'></div>{JS}"
