"""Tasto «Aggiorna dati»: dal telefono avvia subito i workflow di GitHub (prezzi + pagina, oppure tutti i dati) e segue lo stato.

Il sito è statico (GitHub Pages): per avviare un workflow serve una chiave GitHub personale con il solo permesso «Actions: lettura e scrittura»
sul repository armor. La chiave si incolla una volta e resta salvata solo su quel dispositivo (memoria del browser), mai nel sito o nel repository.
Avviso «dati fermi»: se una serie chiave non si aggiorna da più del normale (salute.py) compare una riga in cima alla pagina."""
import html as _h

from . import salute

HTML = """
<button id='fzbtn' class='btn fzb' type='button' aria-haspopup='dialog'>⟳ Aggiorna dati</button>
<div id='fzpanel' class='fzp' role='dialog' aria-label='Aggiorna i dati adesso'>
<div class='fzh'><b>Aggiorna i dati adesso</b><button id='fzclose' class='btn' type='button' aria-label='Chiudi'>✕</button></div>
<p class='fzt'>Di solito i dati si aggiornano da soli: prezzi ogni 15 minuti (8-23), tutto il resto ogni sera dopo la chiusura di Wall Street e di nuovo al mattino.
Da qui puoi forzare subito l'aggiornamento.</p>
<div id='fztokbox'>
<p class='fzt'><b>Una sola volta su questo telefono serve una chiave GitHub</b> (resta salvata solo qui):</p>
<ol class='fzt'><li>Apri <a href='https://github.com/settings/personal-access-tokens/new' target='_blank' rel='noopener'>github.com → nuova chiave «fine-grained»</a> (accedi se serve).</li>
<li>Token name: <b>Armor</b> · Expiration: <b>1 anno</b> · Repository access: <b>Only select repositories → armor</b>.</li>
<li>Permissions → Repository permissions → <b>Actions: Read and write</b> (nient'altro).</li>
<li>Generate token, copia la chiave (inizia con <code>github_pat_</code>) e incollala qui sotto.</li></ol>
<input id='fztok' type='password' autocomplete='off' placeholder='github_pat_…'>
<button id='fzsave' class='btn pri' type='button'>Salva la chiave</button>
</div>
<div id='fzacts'>
<button class='btn pri' type='button' data-wf='site.yml' data-lbl='Prezzi e pagina'>Prezzi e pagina (3-5 minuti)</button>
<button class='btn' type='button' data-wf='daily.yml' data-lbl='Tutti i dati e le previsioni'>Tutti i dati e le previsioni (20-30 minuti)</button>
<button id='fzforget' class='btn' type='button'>Dimentica la chiave</button>
</div>
<button id='fzreload' class='btn' type='button'>Ricarica la pagina</button>
<p id='fzstat' class='fzt' aria-live='polite'></p>
</div>
"""

JS = r"""<script>(function(){
var K='armor_gh_token',P=document.getElementById('fzpanel'),S=document.getElementById('fzstat');if(!P)return;
function tok(){try{return localStorage.getItem(K)||''}catch(e){return ''}}
function setTok(v){try{if(v)localStorage.setItem(K,v);else localStorage.removeItem(K)}catch(e){}}
var h=location.hostname,gh=/\.github\.io$/.test(h),owner=gh?h.split('.')[0]:'Stefo818',repo=gh?(location.pathname.split('/')[1]||'armor'):'armor';
var API='https://api.github.com/repos/'+owner+'/'+repo+'/actions/';
function paint(){var t=tok();document.getElementById('fztokbox').style.display=t?'none':'';document.getElementById('fzacts').style.display=t?'':'none'}
document.getElementById('fzbtn').onclick=function(){P.classList.toggle('show');paint()};
document.getElementById('fzclose').onclick=function(){P.classList.remove('show')};
document.getElementById('fzsave').onclick=function(){var v=document.getElementById('fztok').value.trim();if(v){setTok(v);paint();S.textContent='Chiave salvata su questo dispositivo.'}};
document.getElementById('fzforget').onclick=function(){setTok('');paint();S.textContent='Chiave cancellata da questo dispositivo.'};
document.getElementById('fzreload').onclick=function(){location.reload()};
function hdr(){return {'Authorization':'Bearer '+tok(),'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}}
[].forEach.call(document.querySelectorAll('[data-wf]'),function(b){b.onclick=function(){run(b.getAttribute('data-wf'),b.getAttribute('data-lbl'))}});
function iso(ms){return new Date(ms).toISOString().slice(0,19)+'Z'}
function run(wf,lbl){var t0=iso(Date.now()-90000);S.textContent='Avvio di «'+lbl+'»…';
fetch(API+'workflows/'+wf+'/dispatches',{method:'POST',headers:hdr(),body:JSON.stringify({ref:'main'})}).then(function(r){
if(r.status===204){S.textContent='Avviato. Controllo lo stato ogni 20 secondi…';poll(wf,t0,lbl,0)}
else if(r.status===401||r.status===403||r.status===404){S.textContent='GitHub rifiuta la chiave ('+r.status+'): controlla che sia per il repository armor con il permesso «Actions: Read and write», oppure creane una nuova.'}
else r.text().then(function(x){S.textContent='GitHub ha risposto '+r.status+': '+x.slice(0,140)})
}).catch(function(e){S.textContent='Nessuna risposta da GitHub ('+e+'). Riprova tra poco.'})}
function poll(wf,t0,lbl,n){setTimeout(function(){
fetch(API+'workflows/'+wf+'/runs?per_page=1&created='+encodeURIComponent('>='+t0),{headers:hdr(),cache:'no-store'}).then(function(r){return r.json()}).then(function(j){
var x=(j.workflow_runs||[])[0];if(!x){S.textContent='In attesa che GitHub avvii «'+lbl+'»…';if(n<180)poll(wf,t0,lbl,n+1);return}
var st={queued:'in coda',in_progress:'in corso',completed:'finito',waiting:'in attesa',pending:'in attesa'}[x.status]||x.status;
S.innerHTML='«'+lbl+'»: <b>'+st+'</b>'+(x.conclusion?' ('+(x.conclusion==='success'?'riuscito':x.conclusion)+')':'')+' · <a href="'+x.html_url+'" target="_blank" rel="noopener">vedi su GitHub</a>';
if(x.status!=='completed'){if(n<180)poll(wf,t0,lbl,n+1);return}
if(x.conclusion!=='success'){S.innerHTML+='<br>Qualcosa non è andato: apri il link e copia le righe con ERR.';return}
if(wf==='site.yml'){S.innerHTML+='<br>Pagina pubblicata: ricarico tra 40 secondi.';setTimeout(function(){location.reload()},40000)}
else{S.innerHTML+='<br>Dati aggiornati: ora GitHub ricostruisce il sito…';poll('site.yml',iso(Date.now()-120000),'Sito Armor',0)}
}).catch(function(){if(n<180)poll(wf,t0,lbl,n+1)})},20000)}
})();</script>"""

CSS = """
header{align-items:flex-start;gap:10px}.fzb{white-space:nowrap;flex:0 0 auto}
.fzp{display:none;position:fixed;z-index:60;left:12px;right:12px;top:64px;max-width:560px;margin:0 auto;max-height:82vh;overflow:auto;
background:var(--card);color:var(--tx);border:1px solid var(--bd);border-radius:14px;padding:14px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
.fzp.show{display:block}.fzh{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.fzt{font-size:13.5px;color:var(--tx)}.fzp ol{padding-left:20px}.fzp li{margin:3px 0}.fzp a{color:var(--ac)}
.fzp input{width:100%;box-sizing:border-box;padding:9px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--tx);margin:6px 0}
.fzp .btn{margin:4px 6px 4px 0}.fzstale{border-left:4px solid var(--bad)}
"""


def banner_dati_fermi() -> str:
    """Riga in cima alla pagina se qualche dato chiave è fermo da più del normale."""
    try:
        rows = salute.compute()
    except Exception:  # noqa: BLE001
        return ""
    ferme = [r for r in rows if r["light"] == "ba"]
    if not ferme:
        return ""
    nomi = ", ".join(_h.escape(r["name"]) for r in ferme[:6]) + ("…" if len(ferme) > 6 else "")
    return (f"<div class='banner fzstale'><b>Dati non aggiornati:</b> {nomi}. Le stime che li usano sono meno affidabili. "
            "Tocca <b>⟳ Aggiorna dati</b> in alto oppure guarda «Storico → Salute dei dati».</div>")
