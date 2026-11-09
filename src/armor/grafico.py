"""Grafico interattivo con zoom, scorrimento e serie selezionabili (Patch 49): S&P 500 con fasce di regime, VWCE, Nasdaq, VT, i maggiori titoli del VWCE
e gli indicatori (Indice Armor, VIX, rischi, spread). Le serie si caricano da series/<chiave>.json solo quando si selezionano."""
import html as _h
import json

import pandas as pd

from .config import DATA

AZ = DATA / "azioni"

HOLD = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "TSM", "JPM", "LLY", "V"]
NOMI = {"NVDA": "NVIDIA", "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Alphabet", "META": "Meta", "AVGO": "Broadcom", "TSLA": "Tesla",
        "TSM": "TSMC", "JPM": "JPMorgan", "LLY": "Eli Lilly", "V": "Visa"}


def _p(t: str):
    return AZ / f"{t}.csv"


def _load(t: str) -> pd.Series:
    if not _p(t).exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(_p(t), parse_dates=["date"])
    return df.set_index("date")["value"].astype(float).sort_index()


def _upsert(t: str, new: pd.Series) -> int:
    new = pd.to_numeric(new, errors="coerce").dropna()
    if new.empty:
        return 0
    new.index = pd.to_datetime(new.index).tz_localize(None).normalize()
    old = _load(t)
    m = pd.concat([old, new])
    m = m[~m.index.duplicated(keep="last")].sort_index()
    AZ.mkdir(parents=True, exist_ok=True)
    o = m.rename("value").rename_axis("date").reset_index()
    o["date"] = o["date"].dt.strftime("%Y-%m-%d")
    o.to_csv(_p(t), index=False, float_format="%.6g")
    return len(m.index.difference(old.index))


def aggiorna(log=print) -> int:
    """Storico dei maggiori titoli del VWCE (yfinance, prezzi rettificati) in data/series/px_<simbolo>.csv; incrementale."""
    import yfinance as yf
    n = 0
    for t in HOLD:
        try:
            nuovo = _p(t).exists()
            d = yf.download(t, period="10d" if nuovo else "max", interval="1d", auto_adjust=True, progress=False)
            c = d["Close"]
            c = c.iloc[:, 0] if hasattr(c, "columns") else c
            n += _upsert(t, c.dropna())
        except Exception as e:  # noqa: BLE001
            log(f"[grafico] {t} non scaricato: {str(e)[:80]}")
    log(f"[grafico] nuovi punti: {n}")
    return n


def disponibili() -> list[list[str]]:
    return [[t, NOMI[t]] for t in HOLD if _p(t).exists()]


def extra_chartdata(sitedata) -> dict:
    out = {}
    for t, nome in disponibili():
        s = _load(t)
        if len(s) > 5:
            out["px_" + t] = {"l": nome, "dec": 2, **sitedata.ser_payload(s, 2)}
    return out


CSS = ("<style>.gx{position:relative}.gxc{width:100%;height:330px;display:block;touch-action:none;cursor:crosshair;border:1px solid var(--bd);border-radius:12px;background:var(--card)}"
       ".gxb,.gxk{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.gxb button,.gxk button{padding:7px 12px;border:1px solid var(--bd);border-radius:99px;background:var(--card);color:var(--tx);font-size:13px;font-weight:600;cursor:pointer}"
       ".gxb button.on,.gxk button.on{background:var(--ac,#3b82f6);color:#fff;border-color:transparent}.gxk button i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}"
       ".gxk button.off{opacity:.45}.gxh{font-size:12px;color:var(--mu);margin:8px 0 2px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}"
       ".gxt{min-height:44px;font-size:13px;padding:8px 12px;border:1px solid var(--bd);border-radius:10px;background:var(--card);margin-top:6px}.gxt b{font-variant-numeric:tabular-nums}</style>")

JS = r"""<script>(function(){var root=document.getElementById('gx');if(!root||root.dataset.on)return;root.dataset.on=1;var G=JSON.parse(root.getAttribute('data-g')||'null');if(!G)return;
var cv=root.querySelector('canvas'),tip=root.querySelector('.gxt'),COL=['#3b82f6','#f59e0b','#10b981','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16','#f97316','#14b8a6','#a855f7','#64748b','#eab308','#0ea5e9','#22c55e','#f43f5e'];
var CAT=[{k:'sp',l:'S&P 500',t:'p',g:'Prezzi e indici'},{k:'vwce',l:'VWCE (€)',t:'p',g:'Prezzi e indici'},{k:'vt',l:'Mondo (VT)',t:'p',g:'Prezzi e indici'},{k:'ndx',l:'Nasdaq 100',t:'p',g:'Prezzi e indici'}]
.concat((G.az||[]).map(function(a){return {k:'px_'+a[0],l:a[1],t:'p',g:'Maggiori titoli del VWCE'}}))
.concat([['armor_index','Indice Armor'],['vix','VIX'],['risk_1m','Rischio calo 1 mese'],['risk_3m','Rischio calo 3 mesi'],['risk_6m','Rischio calo 6 mesi'],['hy_oas','Spread High Yield'],['cape_m','CAPE'],['t10y3m','Curva 10Y-3M'],['nfci','Condizioni finanziarie']].map(function(a){return {k:a[0],l:a[1],t:'i',g:'Indicatori (scala propria, 0–100% della finestra)'}}));
CAT.forEach(function(c,i){c.c=COL[i%COL.length]});
var S={sp:{d:G.d.map(function(s){return Math.floor(Date.parse(s)/864e5)}),v:G.p}},ON={sp:1},BANDS=1,CUR=null,FAIL={};
var dmin=S.sp.d[0],dmax=S.sp.d[S.sp.d.length-1],x0=dmin,x1=dmax;
var FC={persistente:'rgba(220,38,38,.20)',persistente_calo:'rgba(153,27,27,.32)',formazione:'rgba(217,119,6,.14)',calma:'rgba(22,163,74,.09)'};
function load(k,cb){if(S[k]||FAIL[k])return cb();fetch('series/'+k+'.json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){if(!j.d||!j.d.length)throw 0;S[k]=j;cb()}).catch(function(){FAIL[k]=1;ON[k]=0;buildKeys();cb()})}
function fmtD(d){var t=new Date(d*864e5);return ('0'+t.getUTCDate()).slice(-2)+'/'+('0'+(t.getUTCMonth()+1)).slice(-2)+'/'+t.getUTCFullYear()}
function idx(a,d){var lo=0,hi=a.length-1;while(lo<hi){var m=(lo+hi+1)>>1;if(a[m]<=d)lo=m;else hi=m-1}return lo}
function nf(v,dec){return v==null?'—':Number(v).toFixed(dec==null?2:dec).replace('.',',')}
var geom={};
function draw(){var W=cv.clientWidth||600,H=330,dpr=window.devicePixelRatio||1;cv.width=W*dpr;cv.height=H*dpr;var c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,W,H);
var L=46,R=10,T=10,B=24,pw=W-L-R,ph=H-T-B,tx=getComputedStyle(document.body).color;geom={L:L,R:R,W:W,pw:pw};function X(d){return L+(d-x0)/(x1-x0)*pw}
if(BANDS&&G.fasce){G.fasce.forEach(function(f){var a=S.sp.d[f[0]],b=S.sp.d[Math.min(f[1],S.sp.d.length-1)];if(b<x0||a>x1)return;c.fillStyle=FC[f[2]]||'transparent';var xa=Math.max(L,X(a)),xb=Math.min(L+pw,X(b));c.fillRect(xa,T,Math.max(1,xb-xa),ph)})}
var act=CAT.filter(function(k){return ON[k.k]&&S[k.k]}),pr=act.filter(function(k){return k.t==='p'}),ind=act.filter(function(k){return k.t==='i'});
var ymin=Infinity,ymax=-Infinity,base={};pr.forEach(function(k){var s=S[k.k],i0=idx(s.d,x0);if(s.d[i0]<x0&&i0<s.d.length-1)i0++;base[k.k]=s.v[i0];for(var i=i0;i<s.d.length&&s.d[i]<=x1;i++){var y=Math.log(s.v[i]/base[k.k]*100);if(y<ymin)ymin=y;if(y>ymax)ymax=y}});
if(!isFinite(ymin)){ymin=Math.log(50);ymax=Math.log(200)}var pad=(ymax-ymin)*.06||.1;ymin-=pad;ymax+=pad;function Y(v){return T+ph*(1-(Math.log(v)-ymin)/(ymax-ymin))}
c.font='11px sans-serif';c.textBaseline='middle';c.lineWidth=1;
if(pr.length){[5,10,20,25,30,40,50,60,70,80,90,100,110,125,150,175,200,250,300,400,500,700,1000,1500,2000,3000,5000,10000,20000,50000,100000].forEach(function(v){var y=Y(v);if(y<T||y>T+ph)return;c.globalAlpha=.12;c.strokeStyle=tx;c.beginPath();c.moveTo(L,y);c.lineTo(L+pw,y);c.stroke();c.globalAlpha=.7;c.fillStyle=tx;c.fillText(v,4,y)})}
c.globalAlpha=.7;c.fillStyle=tx;c.textBaseline='alphabetic';var span=(x1-x0)/365.25,t0=new Date(x0*864e5).getUTCFullYear(),t1=new Date(x1*864e5).getUTCFullYear();
if(span>3){var st=span>20?4:span>9?2:1;for(var y=Math.ceil(t0/st)*st;y<=t1;y+=st){var xx=X(Date.UTC(y,0,1)/864e5);if(xx>=L&&xx<=L+pw){c.fillText(y,xx-10,H-6);c.globalAlpha=.1;c.beginPath();c.moveTo(xx,T);c.lineTo(xx,T+ph);c.stroke();c.globalAlpha=.7}}}
else{var M=['gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic'],ms=span>2?6:span>1.2?3:1,dd=new Date(x0*864e5),yy=dd.getUTCFullYear(),mo=Math.ceil(dd.getUTCMonth()/ms)*ms;for(var n=0;n<60;n++){var dt=Date.UTC(yy,mo+n*ms,1)/864e5;if(dt>x1)break;var xx2=X(dt);if(xx2>=L)c.fillText(M[new Date(dt*864e5).getUTCMonth()]+' '+String(new Date(dt*864e5).getUTCFullYear()).slice(2),xx2-12,H-6)}}
c.globalAlpha=1;c.lineWidth=1.7;c.lineJoin='round';
function line(s,f,col){c.strokeStyle=col;c.beginPath();var st=false,i0=Math.max(0,idx(s.d,x0)-1);for(var i=i0;i<s.d.length;i++){if(s.d[i]>x1){var yv=f(s.v[i]);if(isFinite(yv)&&st)c.lineTo(X(s.d[i]),yv);break}var yv2=f(s.v[i]);if(!isFinite(yv2))continue;st?c.lineTo(X(s.d[i]),yv2):(c.moveTo(X(s.d[i]),yv2),st=true)}c.stroke()}
pr.forEach(function(k){line(S[k.k],function(v){return Y(v/base[k.k]*100)},k.c)});
ind.forEach(function(k){var s=S[k.k],mn=Infinity,mx=-Infinity;for(var i=0;i<s.d.length;i++){if(s.d[i]>=x0&&s.d[i]<=x1){if(s.v[i]<mn)mn=s.v[i];if(s.v[i]>mx)mx=s.v[i]}}if(!isFinite(mn))return;var r=(mx-mn)||1;c.setLineDash([5,3]);line(s,function(v){return T+ph*(1-.04-(v-mn)/r*.92)},k.c);c.setLineDash([])});
if(CUR!=null&&CUR>=x0&&CUR<=x1){var xc=X(CUR);c.strokeStyle=tx;c.globalAlpha=.55;c.beginPath();c.moveTo(xc,T);c.lineTo(xc,T+ph);c.stroke();c.globalAlpha=1}
tipUpd(pr,base)}
function tipUpd(pr,base){if(CUR==null){tip.innerHTML='Tocca o clicca sul grafico per leggere i valori di quel giorno. Trascina per spostarti, pizzica o usa la rotella per ingrandire, doppio tocco per ripartire.';return}
var h='<b>'+fmtD(CUR)+'</b>';CAT.forEach(function(k){if(!ON[k.k]||!S[k.k])return;var s=S[k.k],i=idx(s.d,CUR);if(s.d[i]>CUR||CUR-s.d[i]>20){h+='<br><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:'+k.c+'"></i> '+k.l+': n/d';return}
var extra='';if(k.t==='p'&&base[k.k]&&CUR>=x0)extra=' <span class="mu">('+(s.v[i]/base[k.k]*100-100>=0?'+':'')+nf(s.v[i]/base[k.k]*100-100,1)+'% dall\'inizio della finestra)</span>';h+='<br><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:'+k.c+'"></i> '+k.l+': <b>'+nf(s.v[i],k.t==='p'&&s.v[i]>100?0:2)+'</b>'+extra});
if(BANDS&&G.fasce){var j=idx(S.sp.d,CUR),st='';G.fasce.forEach(function(f){if(j>=f[0]&&j<=f[1])st={persistente:'tensione persistente',persistente_calo:'tensione persistente con mercato in calo',formazione:'tensione in formazione',calma:'calma'}[f[2]]});if(st)h+='<br>Regime: <b>'+st+'</b>'}tip.innerHTML=h}
function clamp(){var min=30;if(x1-x0<min){var m=(x0+x1)/2;x0=m-min/2;x1=m+min/2}if(x0<dmin){x1+=dmin-x0;x0=dmin}if(x1>dmax){x0-=x1-dmax;x1=dmax}if(x0<dmin)x0=dmin}
function zoom(f,cx){var a=x0+(x1-x0)*cx,w=(x1-x0)*f;x0=a-w*cx;x1=a+w*(1-cx);clamp();draw()}
function range(y){x1=dmax;x0=y?dmax-y*365.25:dmin;clamp();syncR();draw()}
function syncR(){root.querySelectorAll('[data-r]').forEach(function(b){var y=+b.dataset.r,on=y?Math.abs((x1-x0)-y*365.25)<40&&x1>=dmax-2:(x0<=dmin+2&&x1>=dmax-2);b.className=on?'on':''})}
var P={},mv=false,sx=0,s0=0,s1=0,dist=0,w0=0;
function fx(e){var r=cv.getBoundingClientRect();return (e.clientX-r.left-geom.L)/geom.pw}
cv.onpointerdown=function(e){cv.setPointerCapture&&cv.setPointerCapture(e.pointerId);P[e.pointerId]=e;var k=Object.keys(P);mv=false;if(k.length===1){sx=e.clientX;s0=x0;s1=x1}else if(k.length===2){dist=Math.abs(P[k[0]].clientX-P[k[1]].clientX);w0=x1-x0;s0=x0}};
cv.onpointermove=function(e){var k=Object.keys(P);if(!P[e.pointerId]){if(e.pointerType==='mouse'){CUR=x0+(x1-x0)*Math.min(1,Math.max(0,fx(e)));draw()}return}P[e.pointerId]=e;
if(k.length===2){var d=Math.abs(P[k[0]].clientX-P[k[1]].clientX);if(dist>10){var f=dist/Math.max(d,10),cx=Math.min(1,Math.max(0,fx({clientX:(P[k[0]].clientX+P[k[1]].clientX)/2})));var a=s0+w0*cx,w=w0*f;x0=a-w*cx;x1=a+w*(1-cx);clamp();mv=true;syncR();draw()}return}
var dx=e.clientX-sx;if(Math.abs(dx)>4)mv=true;if(mv){var sh=-dx/geom.pw*(s1-s0);x0=s0+sh;x1=s1+sh;clamp();syncR();draw()}};
cv.onpointerup=cv.onpointercancel=function(e){var was=Object.keys(P).length===1&&P[e.pointerId];delete P[e.pointerId];if(was&&!mv){CUR=x0+(x1-x0)*Math.min(1,Math.max(0,fx(e)));draw()}};
cv.onwheel=function(e){e.preventDefault();zoom(e.deltaY<0?.8:1.25,Math.min(1,Math.max(0,fx(e))))};cv.ondblclick=function(){range(0)};
function buildKeys(){var h='',g='';CAT.forEach(function(k){if(FAIL[k.k])return;if(k.g!==g){g=k.g;h+='<div class="gxh">'+g+'</div><div class="gxk">'}h+='<button data-k="'+k.k+'" class="'+(ON[k.k]?'':'off')+'"><i style="background:'+k.c+'"></i>'+k.l+'</button>';var nx=CAT[CAT.indexOf(k)+1];if(!nx||nx.g!==g)h+='</div>'});
root.querySelector('.gxs').innerHTML=h+'<div class="gxh">Sfondo</div><div class="gxk"><button data-bd="1" class="'+(BANDS?'':'off')+'">Fasce di regime di tensione</button></div>';
root.querySelectorAll('[data-k]').forEach(function(b){b.onclick=function(){var k=b.dataset.k;if(ON[k]){ON[k]=0;buildKeys();draw()}else{ON[k]=1;load(k,function(){buildKeys();draw()})}}});root.querySelectorAll('[data-bd]').forEach(function(b){b.onclick=function(){BANDS=BANDS?0:1;buildKeys();draw()}})}
root.querySelectorAll('[data-r]').forEach(function(b){b.onclick=function(){range(+b.dataset.r)}});buildKeys();syncR();draw();window.addEventListener('resize',draw);new MutationObserver(draw).observe(document.body,{attributes:true})})();</script>"""


def block(g: dict | None, titolo: str = "S&P 500 e periodi di regime: grafico interattivo") -> str:
    if not g:
        return ""
    g = {**g, "az": disponibili()}
    leg = ("<div class='rtl'><span><i style='background:rgba(153,27,27,.55)'></i>Persistente con mercato in calo</span><span><i style='background:rgba(220,38,38,.4)'></i>Persistente</span>"
           "<span><i style='background:rgba(217,119,6,.35)'></i>In formazione</span><span><i style='background:rgba(22,163,74,.25)'></i>Calma</span></div>")
    rng = "".join(f"<button data-r='{v}'>{n}</button>" for v, n in ((1, "1 anno"), (3, "3 anni"), (5, "5 anni"), (10, "10 anni"), (0, "Tutto")))
    return (f"{CSS}<h3 style='margin-top:18px'>{titolo}</h3><div class='gx' id='gx' data-g='{_h.escape(json.dumps(g), quote=True)}'><div class='gxb'>{rng}</div>"
            f"<canvas class='gxc'></canvas><div class='gxt'></div>{leg}<div class='gxs'></div>"
            "<p class='mu'>Prezzi e indici sono confrontati in <b>base 100</b> all'inizio della finestra visibile (scala logaritmica). Gli indicatori (linee tratteggiate) usano una scala propria: "
            "il valore reale compare toccando il grafico.</p></div>" + JS)
