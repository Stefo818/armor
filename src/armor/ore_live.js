(function(){
var C=window.ORE_LIVE; if(!C||!C.url) return;
function pct(x,d,sg){var v=(x*100).toFixed(d); if(sg&&x>=0) v='+'+v; return v.replace('.',',')+'%'}
function num(x,d){return x.toFixed(d).replace('.',',')}
function cdfAt(xs,v){var n=xs.length; if(v<=xs[0]) return 0.5/ (n+1); if(v>=xs[n-1]) return 1-0.5/(n+1);
  for(var i=0;i<n-1;i++){ if(v<=xs[i+1]){ var f=(v-xs[i])/((xs[i+1]-xs[i])||1e-12); return (i+1+f)/(n+1);} } return 1-0.5/(n+1)}
function stats(qz,gap){
  var xs=qz.map(function(v){return v+gap}), n=xs.length, dn=[],up=[];
  xs.forEach(function(v){(v<0?dn:up).push(v)});
  var m=function(a,d){return a.length?a.reduce(function(s,v){return s+v},0)/a.length:d};
  return {su:1-cdfAt(xs,0), m15:cdfAt(xs,C.live.s_forte), giu:m(dn,xs[0]), sale:m(up,xs[n-1]),
          p10:xs[Math.round(0.10*(n+1))-1], p90:xs[Math.round(0.90*(n+1))-1], p05:xs[Math.round(0.05*(n+1))-1]}
}
function esChiuso(d){var w=d.getUTCDay(),h=d.getUTCHours(); return (w===5&&h>=22)||w===6||(w===0&&h<23)}
function valueAt(pts,t){var v=null; for(var i=0;i<pts.length;i++){ if(pts[i][0]<=t) v=pts[i][1]; else break } return v==null&&pts.length?pts[0][1]:v}
function giudizio(g,p6,p12,vix,ev){
  if(g<=C.live.s_calo_forte||Math.max(p6,p12)>=0.20) return ['Calo forte probabile','b'];
  if(g<=C.live.s_calo||Math.max(p6,p12)>=0.10) return ['Rischio di calo','w'];
  if(g>=0.004) return ['Più probabile un rialzo','ok'];
  if(vix>=25||ev) return ['Oscillazioni più ampie del solito','w'];
  return ['Oscillazioni nella norma','ok']}
function direzione(su){ if(su>=0.58) return 'Più probabile un rialzo'; if(su>=0.53) return 'Lieve tendenza al rialzo'; if(su<=0.42) return 'Più probabile un calo'; if(su<=0.47) return 'Lieve tendenza al calo'; return 'Direzione indecisa'}
function calcola(W,now){
  var tTrade=W.vwce.time, aperto=((now/1000-tTrade)<=1200)&&!esChiuso(new Date(now));
  var gap=0;
  if(!aperto){ var ea=valueAt(W.es.serie,tTrade), fa=valueAt(W.fx.serie,tTrade);
    if(ea&&fa) gap=C.live.beta_es*(W.es.p/ea-1)+C.live.beta_fx*(W.fx.p/fa-1) }
  var H={}, ev=false; Object.keys(C.orizzonti).forEach(function(k){var o=C.orizzonti[k]; H[k]=stats(o.qz,gap); if(o.eventi) ev=true});
  var vix=W.vix?W.vix.p:C.vix;
  var g=giudizio(gap,H['6 ore'].m15,H['12 ore'].m15,vix,ev);
  var sup=Object.keys(H).map(function(k){return H[k].su}), lo=Math.min.apply(null,sup), hi=Math.max.apply(null,sup), su12=H['12 ore'].su, sint;
  if(hi<0.53&&lo>0.47) sint='<b>Nessuna direzione chiara</b>: su '+num(lo*100,0)+'-'+num(hi*100,0)+' casi su 100 il prezzo sarà più alto di ora, negli altri più basso.';
  else sint='<b>'+direzione(su12)+'</b> a 12 ore: '+num(su12*100,0)+' casi su 100 più alto di ora, '+num((1-su12)*100,0)+' più basso.';
  return {gap:gap,aperto:aperto,H:H,g:g,sint:sint,vix:vix}
}
window.OreLive={calcola:calcola,stats:stats,giudizio:giudizio};
var root=document.getElementById('ore-h'); if(!root) return;
function $(id){return document.getElementById(id)}
function fmtOra(sec){return new Date(sec*1000).toLocaleTimeString('it-IT',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit'})}
function paint(W){
  var now=Date.now(), R=calcola(W,now), p=W.vwce.price;
  root.className='ohd '+R.g[1]; $('ore-v').textContent=R.g[0]; $('ore-t').textContent='ore '+new Date(now).toLocaleTimeString('it-IT',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit',second:'2-digit'});
  $('ore-riga').innerHTML=R.aperto?'VWCE <b>'+num(p,2)+' €</b> · sta già seguendo i futures americani.'
    :'Ultimo scambio <b>'+num(p,2)+' €</b> alle '+fmtOra(W.vwce.time)+' · valore equo all\'apertura circa <b>'+num(p*(1+R.gap),2)+' €</b> (<b>'+pct(R.gap,2,true)+'</b>).';
  $('ore-sint').innerHTML=R.sint;
  var es1=W.es.h1?W.es.p/W.es.h1-1:null, es24=W.es.h24?W.es.p/W.es.h24-1:null, c=[];
  if(R.vix) c.push('Paura (VIX) <b>'+num(R.vix,1)+'</b>');
  if(es1!=null) c.push('futures S&amp;P 500 <span class="'+(es1<=-0.01?'r':'')+'"><b>'+pct(es1,2,true)+'</b></span> in 1 ora');
  if(es24!=null) c.push('<span class="'+(es24<=-0.01?'r':'')+'"><b>'+pct(es24,1,true)+'</b></span> in 24 ore');
  $('ore-ctx').innerHTML=c.join(' · ');
  var rows=root.parentNode.querySelectorAll('.hr[data-h]');
  Array.prototype.forEach.call(rows,function(row){
    var s=R.H[row.getAttribute('data-h')]; if(!s) return;
    var su=Math.max(1,Math.min(99,Math.round(s.su*100))), gi=100-su, dn=row.querySelector('.pb .dn'), up=row.querySelector('.pb .up'), hs=row.querySelectorAll('.hs');
    dn.style.flex=gi; dn.textContent='▼ '+gi+'%'; up.style.flex=su; up.textContent=su+'% ▲';
    var b1=hs[0].querySelectorAll('b'), b2=hs[1].querySelectorAll('b');
    b1[0].textContent=pct(s.giu,2,true); b1[1].textContent=pct(s.sale,2,true); b2[0].textContent=pct(s.p10,2,true); b2[1].textContent=pct(s.p90,2,true); b2[2].textContent=pct(s.p05,2,true)});
  var a6=R.H['6 ore'], fs=root.closest('details.fold'); fs=fs&&fs.querySelector('summary .fs');
  if(fs) fs.textContent=R.g[0]+' · 6 ore: '+num(a6.su*100,0)+'% su, '+num((1-a6.su)*100,0)+'% giù · peggio 1 su 20 '+pct(a6.p05,1,true);
  var ritardoEs=Math.max(0,Math.round((now/1000-W.es.time)/60));
  $('ore-st').innerHTML='<span style="color:var(--ok)">●</span> In diretta ogni 15 secondi · prezzo VWCE: <b>'+(W.vwce.venue||'')+'</b> · i futures arrivano con circa '+ritardoEs+' min di ritardo.'}
function errore(m){var e=$('ore-st'); if(e) e.innerHTML='<span style="color:var(--warn,#f59e0b)">●</span> '+m+' Mostro l\'ultimo calcolo (aggiornato ogni 15 minuti).'}
var busy=false;
function tick(){ if(busy||document.hidden) return; busy=true;
  fetch(C.url+(C.url.indexOf('?')<0?'?':'&')+'sede='+encodeURIComponent(C.sede||'')+'&_='+Date.now(),{cache:'no-store'}).then(function(r){return r.json()}).then(function(W){busy=false; if(!W.ok) throw new Error(W.errore); paint(W)}).catch(function(e){busy=false; errore('Prezzi in diretta non raggiungibili.')})}
tick(); setInterval(tick,15000); document.addEventListener('visibilitychange',function(){if(!document.hidden) tick()});
})();
