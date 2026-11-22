# -*- coding: utf-8 -*-
"""Grafico a comparsa per Indice Armor, Super Armor e Indice crollo.

Si apre toccando uno dei tre indici (qualunque scheda con l'attributo data-gi). Mostra l'andamento con
intervalli 1 settimana ... massimo, scorrevole con un dito e ingrandibile con due dita (o rotella del mouse),
le medie delle ultime 1/4/13 settimane e i valori di ieri, una e due settimane fa.
I dati sono incorporati nella pagina in forma compatta (date a differenze, valori x10 interi).
"""
import json

import pandas as pd

from .config import DATA

NOMI = {"armor": "Indice Armor", "super": "Super Armor", "crollo": "Indice crollo"}
# soglie e colori delle zone; stessa scala 40/60/80 per Armor e Super Armor, quella a cinque fasce per l'Indice crollo
ZONE = {
    "armor": {"lim": [40, 60, 80], "col": ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"],
              "nom": ["Tranquillo", "Mercato in difficoltà", "Mercato in pericolo", "Rischio di crollo"]},
    "crollo": {"lim": [35, 40, 60, 80], "col": ["#22c55e", "#9ca3af", "#f59e0b", "#ef4444", "#8b5cf6"],
               "nom": ["Nessuna tensione", "Zona di passaggio", "Mercato teso", "Mercato molto teso", "Mercato in panico"]},
}
ZONE["super"] = ZONE["armor"]


def _serie(s: pd.Series) -> dict | None:
    s = s.dropna()
    if len(s) < 10:
        return None
    t = (s.index.normalize() - pd.Timestamp("1970-01-01")).days.astype(int).tolist()
    dt = [0] + [t[i] - t[i - 1] for i in range(1, len(t))]
    return {"t0": t[0], "dt": dt, "v": [int(round(float(x) * 10)) for x in s.values]}


def dati() -> dict:
    out: dict = {}
    try:
        d = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
        col = "armor_tarato" if "armor_tarato" in d else "armor_index"
        for k, c in (("armor", col), ("super", "super_armor_index")):
            if c in d:
                x = _serie(d[c])
                if x:
                    out[k] = x
    except Exception:  # noqa: BLE001
        pass
    try:
        c = pd.read_csv(DATA / "indice_crollo_storia.csv", index_col=0, parse_dates=True)["indice"]
        x = _serie(c)
        if x:
            out["crollo"] = x
    except Exception:  # noqa: BLE001
        pass
    return out


CSS = """<style>
[data-gi]{cursor:pointer;-webkit-tap-highlight-color:transparent}
#gi-ov{position:fixed;inset:0;z-index:9999;display:none;align-items:flex-end;justify-content:center;background:rgba(8,12,20,.5);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);opacity:0;transition:opacity .2s}
#gi-ov.on{display:flex}#gi-ov.in{opacity:1}
#gi-sh{width:100%;max-width:580px;max-height:94vh;overflow:auto;overscroll-behavior:contain;background:var(--card);color:var(--tx);border:1px solid var(--bd);border-radius:22px 22px 0 0;padding:12px 14px calc(14px + env(safe-area-inset-bottom));transform:translateY(40px);transition:transform .25s cubic-bezier(.2,.8,.2,1);box-shadow:0 -10px 40px rgba(0,0,0,.25)}
#gi-ov.in #gi-sh{transform:none}
@media(min-width:700px){#gi-ov{align-items:center}#gi-sh{border-radius:22px}}
.gi-hd{display:flex;align-items:flex-start;gap:10px}
.gi-t{flex:1;min-width:0}
.gi-nm{font-size:12px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.gi-zn{font-size:11px;font-weight:800;padding:1px 9px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);text-transform:none;letter-spacing:0;background:color-mix(in srgb,var(--c) 14%,transparent)}
.gi-big{display:flex;align-items:baseline;gap:8px;margin-top:2px;flex-wrap:wrap}
.gi-v{font-size:42px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.gi-dd{font-size:12px;color:var(--mu)}
.gi-x{flex:none;width:36px;height:36px;border-radius:50%;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:20px;line-height:1;cursor:pointer;display:grid;place-items:center;padding:0}
.gi-x:active{transform:scale(.92)}
.gi-rg{display:flex;gap:5px;margin:10px 0 6px;overflow-x:auto;scrollbar-width:none;padding-bottom:1px}
.gi-rg::-webkit-scrollbar{display:none}
.gi-rg button{flex:1 0 auto;min-width:38px;border:1px solid var(--bd);background:var(--bg);color:var(--mu);border-radius:99px;padding:5px 9px;font:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:.15s}
.gi-rg button.on{background:var(--tx);color:var(--card);border-color:var(--tx)}
#gi-cv{display:block;width:100%;height:clamp(210px,36vh,290px);touch-action:none;border-radius:12px;background:var(--bg);cursor:crosshair;user-select:none;-webkit-user-select:none}
.gi-hint{font-size:10.5px;color:var(--mu);text-align:center;margin:4px 0 0}
.gi-sc{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin:12px 0 5px}
.gi-g{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
.gi-c{border:1px solid var(--bd);border-radius:12px;background:var(--bg);padding:7px 6px 6px;text-align:center;position:relative;overflow:hidden}
.gi-c::before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:var(--c)}
.gi-cn{font-size:23px;font-weight:800;line-height:1.1;color:var(--c);font-variant-numeric:tabular-nums}
.gi-cl{font-size:11.5px;font-weight:600;margin-top:1px}
.gi-cs{font-size:10.5px;color:var(--mu);margin-top:1px;min-height:13px}
.gi-cs b{font-weight:700}
</style>"""

JS = r"""<script>(function(){
if(window.giOn)return;window.giOn=1;
var el=document.getElementById('gi-dati');if(!el)return;
var RAW=JSON.parse(el.textContent),Z=JSON.parse(document.getElementById('gi-zone').textContent),NM=JSON.parse(document.getElementById('gi-nomi').textContent);
var S={};Object.keys(RAW).forEach(function(k){var r=RAW[k],t=[],a=r.t0;for(var i=0;i<r.dt.length;i++){a+=r.dt[i];t.push(a)}S[k]={t:t,v:r.v.map(function(x){return x/10})}});
var ov=document.getElementById('gi-ov');document.body.appendChild(ov);
var sh=document.getElementById('gi-sh'),cv=document.getElementById('gi-cv'),cx=cv.getContext('2d');
var cur=null,T,V,ZN,v0,v1,t0,t1,ya,yb,tya,tyb,cursor=null,W=0,H=0,dpr=1,raf=0,rangeDays=null,C={};
var M={l:8,r:30,t:12,b:22};
var RG=[['1S',7],['1M',30],['3M',91],['6M',182],['1A',365],['3A',1096],['5A',1826],['Max',0]];
function it(x,d){var s=x.toFixed(d==null?0:d).replace('.',',');return s.replace('-','−')}
function zi(k,v){var l=Z[k].lim;for(var i=0;i<l.length;i++){if(v<=l[i]&&!(k==='crollo'&&false))return i}return l.length}
function zc(v){return Z[cur].col[zi(cur,v)]}
function dfmt(d,o){return new Date(d*864e5).toLocaleDateString('it-IT',Object.assign({timeZone:'UTC'},o))}
function dlong(d){return dfmt(d,{weekday:'short',day:'numeric',month:'short',year:'numeric'})}
function dshort(d){return dfmt(d,{day:'numeric',month:'short'})}
function bs(x){var lo=0,hi=T.length-1;while(lo<hi){var m=(lo+hi+1)>>1;if(T[m]<=x)lo=m;else hi=m-1}return lo}
function setTheme(){var cs=getComputedStyle(document.documentElement);C.tx=cs.getPropertyValue('--tx').trim()||'#222';C.mu=cs.getPropertyValue('--mu').trim()||'#888';C.bd=cs.getPropertyValue('--bd').trim()||'#ddd';C.bg=cs.getPropertyValue('--bg').trim()||'#f4f6f9';C.card=cs.getPropertyValue('--card').trim()||'#fff'}
function size(){dpr=Math.min(3,window.devicePixelRatio||1);W=cv.clientWidth;H=cv.clientHeight;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cx.setTransform(dpr,0,0,dpr,0,0)}
function pw(){return W-M.l-M.r}
function X(d){return M.l+(d-v0)/(v1-v0)*pw()}
function Y(v){return M.t+(1-(v-ya)/(yb-ya))*(H-M.t-M.b)}
function fit(){var a=bs(v0),b=bs(v1),lo=1e9,hi=-1e9;a=Math.max(0,a-1);b=Math.min(T.length-1,b+1);for(var i=a;i<=b;i++){if(V[i]<lo)lo=V[i];if(V[i]>hi)hi=V[i]}if(hi-lo<16){var m=(hi+lo)/2;lo=m-8;hi=m+8}var p=(hi-lo)*.14;tya=Math.max(0,lo-p);tyb=Math.min(100,hi+p);if(tyb-tya<12){tya=Math.max(0,tyb-12)}}
function clampView(){var full=T[T.length-1]-T[0],sp=v1-v0;var mn=6,mx=full*1.06+3;if(sp<mn){var c=(v0+v1)/2;v0=c-mn/2;v1=c+mn/2;sp=mn}if(sp>mx){v0=v1-mx;sp=mx}var pad=sp*.04;var lo=T[0]-pad,hi=T[T.length-1]+pad;if(v0<lo){v1+=lo-v0;v0=lo}if(v1>hi){v0-=v1-hi;v1=hi}}
function nice(span,n){var r=span/n,p=Math.pow(10,Math.floor(Math.log10(r))),f=r/p;return(f<1.5?1:f<3?2:f<7?5:10)*p}
function xticks(){var sp=v1-v0,n=Math.max(2,Math.floor(pw()/78)),C0=[['d',1],['d',2],['d',7],['d',14],['m',1],['m',2],['m',3],['m',6],['y',1],['y',2],['y',5],['y',10]],u=null;
for(var i=0;i<C0.length;i++){var a=C0[i],dd=a[0]==='d'?a[1]:a[0]==='m'?30.44*a[1]:365.25*a[1];if(sp/dd<=n){u=a;break}}if(!u)u=['y',10];var out=[],k=u[1];
if(u[0]==='d'){var s=k===7?Math.ceil((v0-4)/7)*7+4:Math.ceil(v0/k)*k;for(var t=s;t<=v1;t+=k)out.push([t,dshort(t)])}
else{var d0=new Date(v0*864e5),y=d0.getUTCFullYear(),m=d0.getUTCMonth();
if(u[0]==='m'){while(true){if(m%k===0){var t2=Date.UTC(y,m,1)/864e5;if(t2>v1)break;if(t2>=v0){var lab=dfmt(t2,{month:'short'});if(sp>400||m===0)lab+=" ’"+String(y).slice(2);out.push([t2,lab])}}m++;if(m>11){m=0;y++}if(y>2200)break}}
else{while(true){if(y%k===0){var t3=Date.UTC(y,0,1)/864e5;if(t3>v1)break;if(t3>=v0)out.push([t3,String(y)])}y++;if(y>2200)break}}}
return out}
function draw(){
if(!cur)return;cx.clearRect(0,0,W,H);var l=Z[cur].lim,co=Z[cur].col,pl=M.l,pr=W-M.r,pt=M.t,pb=H-M.b;
// fasce di colore
for(var i=0;i<co.length;i++){var lo=i===0?-1e3:l[i-1],hi=i===l.length?1e3:l[i];var ya1=Math.max(pt,Math.min(pb,Y(hi))),yb1=Math.max(pt,Math.min(pb,Y(lo)));if(yb1-ya1>.5){cx.globalAlpha=.075;cx.fillStyle=co[i];cx.fillRect(pl,ya1,pr-pl,yb1-ya1)}}
cx.globalAlpha=1;cx.font='10px system-ui,sans-serif';cx.textBaseline='middle';cx.textAlign='left';
// griglia
var st=nice(yb-ya,4);cx.strokeStyle=C.bd;cx.lineWidth=1;cx.fillStyle=C.mu;
for(var g=Math.ceil(ya/st)*st;g<=yb;g+=st){var yy=Math.round(Y(g))+.5;cx.globalAlpha=.7;cx.beginPath();cx.moveTo(pl,yy);cx.lineTo(pr,yy);cx.stroke();cx.globalAlpha=1;cx.fillText(String(Math.round(g)),pr+4,yy)}
// soglie
cx.setLineDash([4,4]);for(var j=0;j<l.length;j++){var ys=Y(l[j]);if(ys>pt&&ys<pb){cx.strokeStyle=co[j+1]||co[j];cx.globalAlpha=.55;cx.beginPath();cx.moveTo(pl,ys);cx.lineTo(pr,ys);cx.stroke();cx.globalAlpha=1;cx.fillStyle=co[j+1]||co[j];cx.font='700 10px system-ui,sans-serif';cx.fillText(String(l[j]),pr+4,ys);cx.font='10px system-ui,sans-serif'}}cx.setLineDash([]);
// asse x
var tk=xticks();cx.fillStyle=C.mu;cx.textAlign='center';cx.textBaseline='top';
tk.forEach(function(q){var xx=X(q[0]);if(xx<pl+8||xx>pr-8)return;cx.strokeStyle=C.bd;cx.globalAlpha=.6;cx.beginPath();cx.moveTo(Math.round(xx)+.5,pb);cx.lineTo(Math.round(xx)+.5,pb+4);cx.stroke();cx.globalAlpha=1;cx.fillText(q[1],xx,pb+6)});
// linea (con pochi punti si disegna tutto; con molti si tiene minimo e massimo di ogni gruppo)
var a=Math.max(0,bs(v0)-1),b=Math.min(T.length-1,bs(v1)+1),n=b-a+1,pts=[],cap=Math.max(60,Math.floor(pw()*1.2));
if(n<=cap){for(var i2=a;i2<=b;i2++)pts.push(i2)}else{var bk=Math.ceil(n/(cap/2));for(var s0=a;s0<=b;s0+=bk){var e0=Math.min(b,s0+bk-1),im=s0,iM=s0;for(var q2=s0;q2<=e0;q2++){if(V[q2]<V[im])im=q2;if(V[q2]>V[iM])iM=q2}if(im<iM){pts.push(im);if(iM!==im)pts.push(iM)}else{pts.push(iM);if(iM!==im)pts.push(im)}}if(pts[pts.length-1]!==b)pts.push(b)}
cx.save();cx.beginPath();cx.rect(pl,pt-2,pr-pl+1,pb-pt+4);cx.clip();
var gr=cx.createLinearGradient(0,pt,0,pb);function stop(o,c){gr.addColorStop(Math.max(0,Math.min(1,o)),c)}
for(var r2=co.length-1;r2>=0;r2--){var hi2=r2===l.length?1e3:l[r2],lo2=r2===0?-1e3:l[r2-1];stop((Y(hi2)-pt)/(pb-pt),co[r2]);stop((Y(lo2)-pt)/(pb-pt),co[r2])}
cx.beginPath();pts.forEach(function(i3,k){var px=X(T[i3]),py=Y(V[i3]);if(k)cx.lineTo(px,py);else cx.moveTo(px,py)});
cx.lineJoin='round';cx.lineCap='round';cx.lineWidth=2.2;cx.strokeStyle=gr;cx.stroke();
var lx=X(T[pts[pts.length-1]]);cx.lineTo(lx,pb);cx.lineTo(X(T[pts[0]]),pb);cx.closePath();cx.globalAlpha=.16;cx.fillStyle=gr;cx.fill();cx.globalAlpha=1;cx.restore();
// ultimo punto
var li=T.length-1;if(T[li]>=v0&&T[li]<=v1){var ex=X(T[li]),ey=Y(V[li]),c0=zc(V[li]);cx.fillStyle=c0;cx.globalAlpha=.25;cx.beginPath();cx.arc(ex,ey,7,0,7);cx.fill();cx.globalAlpha=1;cx.beginPath();cx.arc(ex,ey,3.6,0,7);cx.fill();cx.strokeStyle=C.bg;cx.lineWidth=1.5;cx.stroke()}
// cursore
if(cursor!=null){var ci=cursor,cxp=X(T[ci]);if(cxp>=pl&&cxp<=pr){var cyp=Y(V[ci]),cc=zc(V[ci]);cx.strokeStyle=C.mu;cx.globalAlpha=.7;cx.setLineDash([3,3]);cx.lineWidth=1;cx.beginPath();cx.moveTo(cxp,pt);cx.lineTo(cxp,pb);cx.stroke();cx.setLineDash([]);cx.globalAlpha=1;
cx.fillStyle=cc;cx.beginPath();cx.arc(cxp,cyp,5,0,7);cx.fill();cx.strokeStyle=C.card;cx.lineWidth=2;cx.stroke();
var tx=dshort(T[ci])+(v1-v0>300?' '+dfmt(T[ci],{year:'2-digit'}):'')+' · '+it(V[ci],1);cx.font='700 11px system-ui,sans-serif';var tw=cx.measureText(tx).width+14,bx=Math.max(pl,Math.min(pr-tw,cxp-tw/2)),by=pt+2;
cx.fillStyle=C.tx;cx.globalAlpha=.92;rr(bx,by,tw,20,10);cx.fill();cx.globalAlpha=1;cx.fillStyle=C.card;cx.textAlign='center';cx.textBaseline='middle';cx.fillText(tx,bx+tw/2,by+10.5)}}
}
function rr(x,y,w,h,r){cx.beginPath();cx.moveTo(x+r,y);cx.arcTo(x+w,y,x+w,y+h,r);cx.arcTo(x+w,y+h,x,y+h,r);cx.arcTo(x,y+h,x,y,r);cx.arcTo(x,y,x+w,y,r);cx.closePath()}
function head(){var i=cursor!=null?cursor:T.length-1,v=V[i],c=zc(v),pv=i>0?V[i-1]:null;
var big=document.getElementById('gi-v');big.textContent=it(v);big.style.color=c;
var d=document.getElementById('gi-dd'),txt=dlong(T[i]);if(pv!=null){var df=v-pv;txt+=' · <b style="color:'+(Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)')+'">'+(Math.abs(df)<.05?'invariato':(df>0?'▲ +':'▼ −')+it(Math.abs(df),1))+'</b> sulla seduta precedente'}d.innerHTML=txt;
var zn=document.getElementById('gi-zn');zn.textContent=Z[cur].nom[zi(cur,v)];zn.style.setProperty('--c',c)}
function loop(){raf=0;var go=false,ease=.22;
if(Math.abs(tv0-v0)>.02||Math.abs(tv1-v1)>.02){v0+=(tv0-v0)*ease;v1+=(tv1-v1)*ease;go=true}else{v0=tv0;v1=tv1}
fit0();if(Math.abs(tya-ya)>.02||Math.abs(tyb-yb)>.02){ya+=(tya-ya)*ease;yb+=(tyb-yb)*ease;go=true}else{ya=tya;yb=tyb}
draw();if(go)raf=requestAnimationFrame(loop)}
var tv0,tv1;function fit0(){var s0=v0,s1=v1;fit()}
function kick(){if(!raf)raf=requestAnimationFrame(loop)}
function setView(a,b,anim){tv0=a;tv1=b;if(!anim){v0=a;v1=b}kick()}
function hit(c){var n=ov.querySelectorAll('.gi-rg button');n.forEach(function(x){x.classList.toggle('on',x.dataset.i===String(c))})}
function range(i){var n=RG[i][1],last=T[T.length-1],first=T[0],b=last+Math.max(1,(n||last-first)*.03),a=n?Math.max(first,last-n):first;tv0=a;tv1=b;rangeDays=i;hit(i);cursor=null;head();kick()}
function stats(){var n=T.length-1,box=document.getElementById('gi-st'),h='';
function tile(lbl,v,sub){var c=zc(v);return '<div class="gi-c" style="--c:'+c+'"><div class="gi-cn">'+it(v)+'</div><div class="gi-cl">'+lbl+'</div><div class="gi-cs">'+sub+'</div></div>'}
function mean(k){var a=Math.max(0,n-k+1),s=0;for(var i=a;i<=n;i++)s+=V[i];return s/(n-a+1)}
h+='<div class="gi-sc">Valore medio</div><div class="gi-g">'+tile('Ultima settimana',mean(5),'5 sedute')+tile('Ultimo mese',mean(21),'21 sedute')+tile('Ultimi 3 mesi',mean(63),'63 sedute')+'</div>';
function prev(lbl,k){if(n-k<0)return '';var v=V[n-k],df=V[n]-v,c=Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)';return tile(lbl,v,dshort(T[n-k])+' · <b style="color:'+c+'">'+(Math.abs(df)<.05?'=':(df>0?'▲ ':'▼ ')+it(Math.abs(df),1))+'</b>')}
h+='<div class="gi-sc">Com’era prima</div><div class="gi-g">'+prev('Ieri',1)+prev('Una settimana fa',5)+prev('Due settimane fa',10)+'</div>';
h+='<div class="gi-hint" style="margin-top:6px">La freccia mostra di quanto è cambiato l’indice da allora a oggi: rossa se il rischio è salito, verde se è sceso.</div>';
box.innerHTML=h}
function open(k){if(!S[k])return;cur=k;T=S[k].t;V=S[k].v;setTheme();document.getElementById('gi-nm').firstChild.nodeValue=NM[k];
document.body.style.overflow='hidden';ov.classList.add('on');requestAnimationFrame(function(){ov.classList.add('in')});size();
cursor=null;range(2);v0=tv0;v1=tv1;fit();ya=tya;yb=tyb;stats();head();draw();sh.scrollTop=0}
function close(){ov.classList.remove('in');document.body.style.overflow='';setTimeout(function(){if(!ov.classList.contains('in'))ov.classList.remove('on')},220)}
// ---- gesti
var P={},g0=null;
function pos(e){var r=cv.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
function d2x(px){return v0+(px-M.l)/pw()*(v1-v0)}
function near(px){var i=bs(d2x(px));if(i<T.length-1&&Math.abs(T[i+1]-d2x(px))<Math.abs(T[i]-d2x(px)))i++;return Math.max(0,Math.min(T.length-1,i))}
function manual(){rangeDays=null;hit(-1)}
cv.addEventListener('pointerdown',function(e){cv.setPointerCapture(e.pointerId);P[e.pointerId]=pos(e);var ks=Object.keys(P);
if(ks.length===1){g0={m:false,x:P[ks[0]].x,v0:v0,v1:v1,t:e.timeStamp,touch:e.pointerType!=='mouse'}}
else if(ks.length===2){var a=P[ks[0]],b=P[ks[1]];g0={pin:true,d:Math.max(20,Math.abs(a.x-b.x)),c:(a.x+b.x)/2,v0:v0,v1:v1,m:true}}});
cv.addEventListener('pointermove',function(e){var p=pos(e);
if(!P[e.pointerId]){if(e.pointerType==='mouse'){cursor=near(p.x);head();kick()}return}
P[e.pointerId]=p;var ks=Object.keys(P);if(!g0)return;
if(ks.length>=2&&g0.pin){var a=P[ks[0]],b=P[ks[1]],dist=Math.max(20,Math.abs(a.x-b.x)),mid=(a.x+b.x)/2,sp0=g0.v1-g0.v0,sp=sp0*g0.d/dist,anc=g0.v0+(g0.c-M.l)/pw()*sp0,n0=anc-(mid-M.l)/pw()*sp;v0=n0;v1=n0+sp;clampView();tv0=v0;tv1=v1;manual();cursor=null;head();fit();ya=tya;yb=tyb;draw();return}
if(ks.length===1&&!g0.pin){var dx=p.x-g0.x;if(Math.abs(dx)>5)g0.m=true;if(g0.m){var sp1=g0.v1-g0.v0,sh0=-dx/pw()*sp1;v0=g0.v0+sh0;v1=g0.v1+sh0;clampView();tv0=v0;tv1=v1;manual();cursor=null;fit();ya=tya;yb=tyb;draw();head()}else if(!g0.touch){cursor=near(p.x);head();draw()}}});
function up(e){var had=P[e.pointerId];delete P[e.pointerId];var ks=Object.keys(P);
if(g0&&!g0.m&&!g0.pin&&had&&ks.length===0){cursor=near(had.x);head();kick()}
if(ks.length===1&&g0&&g0.pin){var q=P[ks[0]];g0={m:true,x:q.x,v0:v0,v1:v1,touch:true}}
if(ks.length===0)g0=null}
cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
cv.addEventListener('pointerleave',function(e){if(e.pointerType==='mouse'&&!P[e.pointerId]){cursor=null;head();kick()}});
cv.addEventListener('wheel',function(e){e.preventDefault();var p=pos(e),f=Math.exp(e.deltaY*.0015),sp=v1-v0,anc=d2x(p.x),ns=sp*f;v0=anc-(p.x-M.l)/pw()*ns;v1=v0+ns;clampView();tv0=v0;tv1=v1;manual();fit();ya=tya;yb=tyb;draw()},{passive:false});
cv.addEventListener('dblclick',function(){range(7)});
// ---- apertura/chiusura
document.addEventListener('click',function(e){var t=e.target;if(t.closest('#gi-ov'))return;var c=t.closest('[data-gi]');if(!c)return;if(t.closest('details,summary,a,button,input,select'))return;open(c.getAttribute('data-gi'))});
document.getElementById('gi-xb').addEventListener('click',close);
ov.addEventListener('click',function(e){if(e.target===ov)close()});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&ov.classList.contains('on'))close()});
ov.querySelectorAll('.gi-rg button').forEach(function(b){b.addEventListener('click',function(){range(+b.dataset.i)})});
window.addEventListener('resize',function(){if(ov.classList.contains('on')){size();kick()}});
})()</script>"""


def html() -> str:
    d = dati()
    if not d:
        return ""
    chips = "".join(f"<button type='button' data-i='{i}'>{n}</button>" for i, n in
                    enumerate(("1S", "1M", "3M", "6M", "1A", "3A", "5A", "Max")))
    zone = {k: {"lim": ZONE[k]["lim"], "col": ZONE[k]["col"], "nom": ZONE[k]["nom"]} for k in d}
    return (
        CSS
        + f"<script type='application/json' id='gi-dati'>{json.dumps(d, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-zone'>{json.dumps(zone, ensure_ascii=False, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-nomi'>{json.dumps(NOMI, ensure_ascii=False)}</script>"
        + "<div id='gi-ov' role='dialog' aria-modal='true' aria-label='Grafico dell&#39;indice'><div id='gi-sh'>"
        "<div class='gi-hd'><div class='gi-t'><div class='gi-nm' id='gi-nm'>x<span class='gi-zn' id='gi-zn'></span></div>"
        "<div class='gi-big'><span class='gi-v' id='gi-v'></span><span class='gi-dd' id='gi-dd'></span></div></div>"
        "<button type='button' class='gi-x' id='gi-xb' aria-label='Chiudi'>&times;</button></div>"
        f"<div class='gi-rg'>{chips}</div>"
        "<canvas id='gi-cv'></canvas>"
        "<div class='gi-hint'>Trascina per scorrere · pizzica con due dita per ingrandire · tocca per leggere un giorno</div>"
        "<div id='gi-st'></div></div></div>"
        + JS)
