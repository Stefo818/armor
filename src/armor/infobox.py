"""Scheda informativa comune (window.armorInfo): si apre al passaggio del mouse (250 ms), con pressione lunga (450 ms) o toccando ⓘ.
Uso: elemento con data-info='{"t":"Titolo","s":[["Cos'e","testo"],...]}' (JSON, attributo con apici gestiti dal chiamante)
oppure window.armorInfo.attach(el, fn) con fn() che restituisce {t, s}."""

CSS = """
#ainfo{position:fixed;z-index:60;max-width:360px;width:calc(100vw - 20px);background:var(--card);color:var(--tx);border:1px solid var(--ac);border-radius:12px;padding:12px 14px 12px;box-shadow:0 10px 30px rgba(0,0,0,.5);font-size:13px;line-height:1.45;display:none}
#ainfo h4{margin:0 22px 6px 0;font-size:14px}#ainfo .ai-s{margin:6px 0}#ainfo .ai-s b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--mu)}
#ainfo .x{position:absolute;right:6px;top:2px;border:0;background:transparent;color:var(--mu);font-size:22px;cursor:pointer}
.aii{display:inline-block;width:15px;height:15px;line-height:15px;border-radius:50%;border:1px solid var(--mu);color:var(--mu);font-size:10px;text-align:center;font-style:normal;cursor:help;margin-left:4px;vertical-align:middle;position:relative}
.aii::after{content:'';position:absolute;left:-10px;right:-10px;top:-10px;bottom:-10px}
#ainfo.sheet{left:8px!important;right:8px;top:auto!important;bottom:8px;width:auto;max-width:none;max-height:62vh;overflow:auto}
"""

JS = r"""
<script>
(function(){
if(window.armorInfo)return;
var box=null,tmr=null,pinned=false,fns=new WeakMap();
function esc(s){return String(s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
function mk(){if(box)return box;box=document.createElement('div');box.id='ainfo';box.innerHTML='<button class="x" aria-label="Chiudi">×</button><div class="ai-b"></div>';document.body.appendChild(box);
 box.querySelector('.x').addEventListener('click',function(){hide(true)});
 document.addEventListener('click',function(e){if(box.style.display==='block'&&!e.target.closest('#ainfo')&&!e.target.closest('[data-armorinfo]')&&!e.target.closest('[data-info]'))hide(true)},true);return box}
function data(el){var f=fns.get(el);if(f)return f(el);var j=el.getAttribute('data-info');if(!j)return null;try{return JSON.parse(j)}catch(e){return null}}
function show(el,x,y){var d=data(el);if(!d)return;var b=mk();b.querySelector('.ai-b').innerHTML='<h4>'+esc(d.t)+'</h4>'+d.s.map(function(r){return '<div class="ai-s"><b>'+esc(r[0])+'</b>'+esc(r[1])+'</div>'}).join('');
 b.style.display='block';if(window.innerWidth<640){b.classList.add('sheet');return}b.classList.remove('sheet');var w=b.offsetWidth,h=b.offsetHeight,vw=window.innerWidth,vh=window.innerHeight,rc=el.getBoundingClientRect();
 var left=Math.min(Math.max(8,(x!=null?x:rc.left)-20),vw-w-8),top=rc.bottom+8;if(top+h>vh-8)top=Math.max(8,rc.top-h-8);b.style.left=left+'px';b.style.top=top+'px'}
function hide(force){clearTimeout(tmr);if(box&&(force||!pinned)){box.style.display='none';pinned=false}}
function attach(el,fn){el.setAttribute('data-armorinfo','1');if(fn)fns.set(el,fn)}
document.addEventListener('mouseover',function(e){var el=e.target.closest&&e.target.closest('[data-armorinfo],[data-info]');if(!el||'ontouchstart' in window&&window.matchMedia('(hover:none)').matches)return;
 clearTimeout(tmr);var x=e.clientX;tmr=setTimeout(function(){show(el,x)},250)});
document.addEventListener('mouseout',function(e){var el=e.target.closest&&e.target.closest('[data-armorinfo],[data-info]');if(el){clearTimeout(tmr);if(!pinned)setTimeout(function(){if(!pinned&&box&&!box.matches(':hover'))hide()},350)}});
var lp=null,sx=0,sy=0;
document.addEventListener('touchstart',function(e){var el=e.target.closest&&e.target.closest('[data-armorinfo],[data-info]');if(!el||e.touches.length>1)return;sx=e.touches[0].clientX;sy=e.touches[0].clientY;
 lp=setTimeout(function(){pinned=true;show(el,sx);lp=null;el.dataset.lp='1';setTimeout(function(){delete el.dataset.lp},400)},450)},{passive:true});
document.addEventListener('touchmove',function(e){if(lp&&e.touches[0]&&(Math.abs(e.touches[0].clientX-sx)>10||Math.abs(e.touches[0].clientY-sy)>10)){clearTimeout(lp);lp=null}},{passive:true});
document.addEventListener('touchend',function(){if(lp){clearTimeout(lp);lp=null}},{passive:true});
document.addEventListener('click',function(e){var i=e.target.closest&&e.target.closest('.aii[data-info],.aii[data-armorinfo]');if(i){e.preventDefault();e.stopPropagation();pinned=true;show(i)}
 var l=e.target.closest&&e.target.closest('[data-lp]');if(l){e.preventDefault();e.stopPropagation()}},true);
window.armorInfo={attach:attach,show:show,hide:function(){hide(true)}};
})();
</script>
"""
