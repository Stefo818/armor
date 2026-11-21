(function(){
var C=window.ALLERTA_LIVE; if(!C||!C.url) return;
function pct(x,d,sg){var v=(x*100).toFixed(d); if(sg&&x>=0) v='+'+v; return v.replace('.',',')+'%'}
function $(i){return document.getElementById(i)}
function paint(W){
  var A=W.allerta, box=$('allerta'); if(!A||!box) return;
  var cls='ok', tit='Nessun segnale di vendite forti', det='Futures S&amp;P 500 <b>'+(A.es15==null?'-':pct(A.es15,2,true))+'</b> in 15 minuti · paura (VIX) <b>'+(A.vix==null?'-':A.vix.toFixed(1).replace('.',','))+'</b>';
  if(A.rapido&&A.rapido.length){
    cls='b'; tit='Vendite forti in corso'; var d=[];
    A.rapido.forEach(function(r){ var q=(r.tipo==='calo60'||r.tipo==='paura60')?'60 minuti':'15 minuti'; d.push((r.tipo==='calo'||r.tipo==='calo60')?'futures S&amp;P 500 <b>'+pct(r.valore,2,true)+'</b> in '+q:'paura salita del <b>'+pct(r.valore,0,false)+'</b> in '+q+' (VIX '+r.vix.toFixed(1).replace('.',',')+')')});
    det=d.join(' · ')+'. Dopo giorni così, nei 20 giorni seguenti il mercato è salito in media del 2%: decidi con calma.';
  } else if(A.fragile){
    cls='w'; tit='Attenzione: vendite forti più probabili del solito';
    var f=A.fragile, w=[]; if(f.B) w.push('paura a '+f.vix.toFixed(1).replace('.',',')+', salita del '+(f.salita5g*100).toFixed(0)+'% in 5 giorni'); if(f.A) w.push("l'indice è appena sceso sotto la media dei 200 giorni");
    det=w.join('; ')+". In passato, in giorni così, il giorno dopo si è perso oltre l'1,2% una volta su 5 (di norma una su 11). Non è una previsione: quattro volte su cinque non succede nulla."}
  box.className='alr '+cls; $('allerta-t').textContent=tit; $('allerta-d').innerHTML=det;
  var rit=A.tes?Math.max(0,Math.round((Date.now()/1000-A.tes)/60)):null;
  $('allerta-s').textContent='Aggiornato '+new Date().toLocaleTimeString('it-IT',{timeZone:'Europe/Rome'})+' · ogni 15 secondi'+(rit!=null?' · futures con circa '+rit+' min di ritardo':'')}
var busy=false;
function tick(){ if(busy||document.hidden) return; busy=true;
  fetch(C.url+'?_='+Date.now(),{cache:'no-store'}).then(function(r){return r.json()}).then(function(W){busy=false; if(!W.ok) throw new Error(W.errore); paint(W)})
   .catch(function(){busy=false; var b=$('allerta'); if(b){b.className='alr'; $('allerta-t').textContent='Controllo vendite non raggiungibile'; $('allerta-d').textContent='Riprovo tra 15 secondi. Le notifiche sul telefono continuano a funzionare.'}})}
tick(); setInterval(tick,15000); document.addEventListener('visibilitychange',function(){if(!document.hidden) tick()});
})();
