"""Pagina «Notizie»: archivio degli ultimi 30 giorni (dai file giornalieri di data/news), deduplicato, diviso per giorno,
con filtri e ricerca. Dati in series/notizie.json (caricati a richiesta) oppure incorporati nella pagina."""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import DATA
from .news import norm

NEWS_DIR = DATA / "news"
ROMA = ZoneInfo("Europe/Rome")
MAX_ITEMS = 900


def archivio(giorni: int = 30, now: datetime | None = None, news_dir=None) -> dict:
    now = now or datetime.now(timezone.utc)
    d = news_dir or NEWS_DIR
    taglio = (now - timedelta(days=giorni)).strftime("%Y-%m-%d")
    visti: dict[str, dict] = {}
    for p in sorted(d.glob("20*.json")):          # dal piu' vecchio: il file piu' recente sovrascrive (stesso titolo, tono aggiornato)
        if p.stem < taglio:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for i in data.get("items", []):
            k = norm(i.get("title_en") or i["title"])
            if not k:
                continue
            visti[k] = {"t": i.get("time") or (p.stem + "T12:00:00Z"), "s": i.get("source", ""), "ti": i["title"],
                        "te": i.get("title_en") if i.get("title_en") and i.get("title_en") != i["title"] else None,
                        "l": i.get("link", ""), "k": i.get("kind", ""), "g": i.get("group", ""), "th": i.get("themes", []),
                        "lb": i.get("label", "neutro")}
    items = sorted(visti.values(), key=lambda x: x["t"], reverse=True)[:MAX_ITEMS]
    return {"fetched": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "n": len(items), "items": items}


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def etichetta_giorno(iso: str, now: datetime | None = None) -> str:
    """«oggi 14:20» / «ieri 09:05» / «ven 06/11 18:30» in ora italiana."""
    now = (now or datetime.now(timezone.utc)).astimezone(ROMA)
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ROMA)
    delta = (now.date() - t.date()).days
    g = "oggi" if delta == 0 else ("ieri" if delta == 1 else f"{['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'][t.weekday()]} {t:%d/%m}")
    return f"{g} {t:%H:%M}"


CSS = """
.nzw{margin:8px 0}.nzbar{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}.nzbar button{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
.nzbar button.on{background:var(--ac);color:#fff;border-color:var(--ac);font-weight:700}.nzq{width:100%;box-sizing:border-box;border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:10px;padding:9px 12px;font:inherit;margin:6px 0}
.nzd{position:sticky;top:0;background:var(--bg);z-index:2;margin:16px 0 4px;padding:6px 0;font-weight:800;font-size:15px;border-bottom:1px solid var(--bd)}
.nzi{display:block;background:var(--card);border:1px solid var(--bd);border-left-width:5px;border-radius:10px;padding:9px 12px;margin:6px 0;color:var(--tx);text-decoration:none}
.nzi.negativo{border-left-color:var(--bad)}.nzi.positivo{border-left-color:var(--ok)}.nzi.neutro{border-left-color:var(--mu)}
.nzi b{display:block;font-size:14px;line-height:1.35}.nzi .en{font-size:12px;color:var(--mu);margin-top:2px}.nzi .me{font-size:12px;color:var(--mu);margin-top:4px;display:flex;gap:8px;flex-wrap:wrap}
.nzi .tg{border:1px solid var(--bd);border-radius:99px;padding:0 7px}.nzc{font-size:12px;color:var(--mu);margin:4px 0}
"""

JS = r"""
<script>
(function(){
var MESI=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'],GS=['domenica','lunedì','martedì','mercoledì','giovedì','venerdì','sabato'];
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function init(root){
if(root.dataset.on)return;root.dataset.on='1';root.innerHTML='<p class="mu">Caricamento delle notizie…</p>';
var D=null,flt='all',q='',lim=80;
var emb=document.getElementById('armor-nz-data');
function go(j){D=j;build()}
if(window.__ARMOR_NZ){go(window.__ARMOR_NZ)}else if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/notizie.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){window.__ARMOR_NZ=j;go(j)}).catch(function(){root.innerHTML='<p class="mu">Notizie non disponibili (serve la connessione).</p>'})}
var F=[['all','Tutte'],['macro','Macro e Fed'],['mkt','Mercati'],['co','Aziende di VWCE'],['sec','Settori e temi'],['neg','Solo negative'],['pos','Solo positive']];
function day(t){return new Date(t).toLocaleDateString('sv-SE',{timeZone:'Europe/Rome'})}
function hm(t){return new Date(t).toLocaleTimeString('it-IT',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit'})}
function dl(d){var oggi=day(new Date()),ieri=day(new Date(Date.now()-864e5));if(d===oggi)return 'Oggi';if(d===ieri)return 'Ieri';var a=d.split('-'),dt=new Date(Date.UTC(+a[0],+a[1]-1,+a[2],12));return GS[dt.getUTCDay()].replace(/^./,function(c){return c.toUpperCase()})+' '+(+a[2])+' '+MESI[+a[1]-1]}
function isMacro(i){return i.k==='macro'&&((i.th||[]).some(function(t){return t==='Banche centrali e tassi'||t==='Inflazione'||t==='Lavoro e crescita'})||i.g==='Banche centrali'||i.g==='Inflazione e lavoro')}
function ok(i){if(flt==='macro'&&!isMacro(i))return false;if(flt==='mkt'&&!(i.k==='macro'&&!isMacro(i)))return false;if(flt==='co'&&i.k!=='company')return false;if(flt==='sec'&&i.k!=='sector')return false;if(flt==='neg'&&i.lb!=='negativo')return false;if(flt==='pos'&&i.lb!=='positivo')return false;
 if(q){var h=((i.ti||'')+' '+(i.te||'')+' '+(i.s||'')+' '+(i.g||'')+' '+(i.th||[]).join(' ')).toLowerCase();if(h.indexOf(q)<0)return false}return true}
function build(){root.innerHTML='<div class="nzbar">'+F.map(function(f){return '<button data-f="'+f[0]+'">'+f[1]+'</button>'}).join('')+'</div><input class="nzq" type="search" placeholder="Cerca nelle notizie (azienda, tema, fonte…)"><div class="nzc"></div><div class="nzl"></div>';
 root.querySelector('.nzq').addEventListener('input',function(e){q=e.target.value.toLowerCase().trim();lim=80;draw()});draw()}
function draw(){root.querySelectorAll('.nzbar button').forEach(function(b){b.classList.toggle('on',b.dataset.f===flt)});
 var L=D.items.filter(ok),show=L.slice(0,lim),h='',cur='';
 show.forEach(function(i){var d=day(i.t);if(d!==cur){cur=d;h+='<div class="nzd">'+dl(d)+'</div>'}
  var tg=(i.th||[]).slice(0,2).map(function(t){return '<span class="tg">'+esc(t)+'</span>'}).join('');
  h+='<a class="nzi '+esc(i.lb)+'" href="'+esc(i.l)+'" target="_blank" rel="noopener"><b>'+esc(i.ti)+'</b>'+(i.te?'<div class="en">'+esc(i.te)+'</div>':'')+'<div class="me"><span>'+hm(i.t)+'</span><span>'+esc(i.s)+'</span>'+(i.g?'<span>'+esc(i.g)+'</span>':'')+'<span>'+(i.lb==='negativo'?'▼ tono negativo':(i.lb==='positivo'?'▲ tono positivo':'• neutra'))+'</span>'+tg+'</div></a>'});
 if(L.length>lim)h+='<p><button class="btn" data-more="1">Mostra altre '+Math.min(80,L.length-lim)+' (di '+(L.length-lim)+')</button></p>';
 if(!L.length)h='<p class="mu">Nessuna notizia con questi filtri.</p>';
 root.querySelector('.nzc').textContent=L.length+' notizie · archivio degli ultimi 30 giorni · titoli tradotti in italiano (sotto, l\'originale in inglese)';root.querySelector('.nzl').innerHTML=h}
root.addEventListener('click',function(e){var b=e.target.closest('button[data-f]');if(b){flt=b.dataset.f;lim=80;draw();return}if(e.target.closest('button[data-more]')){lim+=80;draw()}});
}
window.armorNotizie=function(scope){(scope||document).querySelectorAll('.nzw[data-nz]').forEach(init)};
window.armorNotizie();
})();
</script>
"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-nz-data'>{data_json}</script>" if data_json else ""
    return (f"<h2>Notizie</h2><div class='explain'><p>Tutte le notizie raccolte da Armor (macroeconomia, banche centrali, mercati, aziende di VWCE e settori) degli ultimi 30 giorni, "
            "dalla più recente. Il colore a sinistra è il tono (rosso = negativo, verde = positivo). Tocca una notizia per aprire l'originale.</p></div>"
            f"{emb}<div class='nzw' data-nz='1'></div>{JS}")
