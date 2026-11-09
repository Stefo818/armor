"""Prezzi in tempo reale nel telefono (VWCE e S&P 500), senza server: la pagina interroga ogni 15 secondi l'API pubblica di onvista.de
(quotazioni delle sedi tedesche/italiane per il VWCE, indicazione in tempo reale sull'indice S&P 500), che accetta richieste dal browser.
Yahoo (usato da GitHub ogni 15 minuti) non lo permette. Se onvista non risponde si resta sui dati di GitHub, aggiornati ogni 15 minuti.
Le quotazioni ricevute si accumulano in window.LIVETICKS e il grafico (1 ora, 6 ore, 1 giorno e ultimo punto degli altri intervalli) le aggiunge."""

JS = r"""<script>(function(){
if(location.protocol.indexOf('http')!==0)return;
var SRC={vwce:'FUND/ISIN:IE00BK5BQT80',sp500:'INDEX/ISIN:US78378X1072'},API='https://api.onvista.de/api/v1/instruments/',EVERY=15000;
window.LIVETICKS=window.LIVETICKS||{};var fails=0,busy=false,timer=null;
function best(j,key){var L=[];if(j&&j.quote)L.push(j.quote);if(j&&j.quoteList&&j.quoteList.list)L=L.concat(j.quoteList.list);
L=L.filter(function(q){return q&&q.last>0&&q.datetimeLast&&(key!=='vwce'||q.isoCurrency==='EUR')});if(!L.length)return null;
L.sort(function(a,b){return new Date(b.datetimeLast)-new Date(a.datetimeLast)});return L[0]}
function apply(key,q){var L=window.LIVE;if(!L||!L.quotes||!L.quotes[key])return false;var old=L.quotes[key],px=+q.last;
if(old.price&&Math.abs(px/old.price-1)>0.05)return false;
var t=Math.floor(new Date(q.datetimeLast).getTime()/1000),prev=+q.previousLast||old.prev;
var nq=Object.assign({},old,{price:px,prev:prev,chg:prev?px/prev-1:old.chg,time:new Date(t*1000).toISOString().replace('.000Z','Z'),venue:(q.market&&q.market.name)||old.venue,open:(Date.now()/1000-t)<1200,live:true});
if(new Date(nq.time)<new Date(old.time))return false;
L.quotes[key]=nq;var tk=window.LIVETICKS[key]=window.LIVETICKS[key]||[];if(!tk.length||t>tk[tk.length-1][0])tk.push([t,px]);else if(t===tk[tk.length-1][0])tk[tk.length-1][1]=px;
if(tk.length>3000)tk.splice(0,tk.length-3000);return true}
function one(key){return fetch(API+SRC[key]+'/snapshot',{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var q=best(j,key);return q?apply(key,q):false})}
function poll(){if(busy||document.hidden)return;busy=true;
Promise.all(Object.keys(SRC).map(function(k){return one(k).catch(function(){return null})})).then(function(r){
var ok=r.some(function(x){return x===true||x===false});if(ok){fails=0;if(window.LIVE)window.LIVE.liveAt=Date.now();if(window.armorPaint)window.armorPaint();(window.ARMOR_TICKS||[]).forEach(function(f){try{f()}catch(e){}})}else{fails++}
busy=false}).catch(function(){busy=false;fails++})}
function loop(){poll();timer=setTimeout(loop,fails>=3?60000:EVERY)}
document.addEventListener('visibilitychange',function(){if(!document.hidden){clearTimeout(timer);loop()}});
setTimeout(loop,1200)})();</script>"""
