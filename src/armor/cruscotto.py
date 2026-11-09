"""Cruscotto di «Oggi»: indici principali con semaforo, valore di ieri e di una settimana fa, freccia di tendenza (VIX con termometro);
finestra con i tre indici Armor (settimana, mese, 3 mesi); testi a rotazione nella barra dell'Assistente."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import armor_index, semafori

e = _h.escape


def _fmt(x, d=1):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def arrow(delta, thr, risk=True):
    """Freccia di tendenza. risk=True: salire = più rischio (rosso)."""
    if delta is None or np.isnan(delta):
        return "<span class='tr0'>—</span>"
    if abs(delta) < thr:
        return "<span class='tr0' title='stabile'>▬</span>"
    up = delta > 0
    bad = up if risk else (not up)
    return f"<span class='{'trb' if bad else 'trg'}' title='{'in aumento' if up else 'in calo'}'>{'▲' if up else '▼'}</span>"


def trend_cells(now, ieri, sett, d=0, thr=1.0, risk=True, rel=False) -> str:
    """Ieri e settimana fa con differenza e freccia."""
    def one(lab, ref):
        if ref is None or now is None or np.isnan(ref):
            return f"<div class='tcl'><span class='mu'>{lab}</span> <b>n.d.</b></div>"
        diff = now - ref
        pct = (diff / ref * 100) if (rel and ref) else None
        t = (f"{diff:+.{d}f}" if round(diff, d) != 0 else f"{0:.{d}f}").replace(".", ",") if not rel else f"{pct:+.1f}%".replace(".", ",")
        t = t.replace("-", "−")
        return (f"<div class='tcl'><span class='mu'>{lab}</span> <b>{_fmt(ref, d)}</b> {arrow(pct if rel else diff, thr if not rel else 1.0, risk)} "
                f"<span class='mu'>({t})</span></div>")
    return one("Ieri", ieri) + one("Sett. fa", sett)


def _closes(s: pd.Series, n: int = 12) -> list:
    s = s.dropna()
    return [[i.strftime("%Y-%m-%d"), round(float(v), 4)] for i, v in s.tail(n).items()]


def _dm(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}"


def trend_dated(s: pd.Series, d: int, risk: bool, rel: bool = True, live: bool = True, thr: float | None = None) -> str:
    """Variazioni rispetto a due chiusure con la data esplicita (niente «Ieri», che nel weekend ingannava).
    Il valore mostrato e' l'ultima chiusura; la chiusura precedente e quella di una settimana prima sono calcolate
    sulla stessa serie e, se c'e' un prezzo in diretta, il browser le ricalcola con le stesse regole (vedi report.paint)."""
    s = s.dropna()
    if s.empty:
        return ""
    now, dnow = float(s.iloc[-1]), s.index[-1]
    prev = s[s.index < dnow]
    wk = s[s.index <= dnow - pd.Timedelta(days=7)]

    def one(ref_s):
        if ref_s.empty:
            return "<div class='tcl'><span class='mu'>n.d.</span></div>"
        ref, dt = float(ref_s.iloc[-1]), ref_s.index[-1]
        diff = now - ref
        pct = diff / ref * 100 if ref else None
        t = (f"{pct:+.1f}%" if rel else f"{diff:+.{d}f}").replace(".", ",").replace("-", "\u2212")
        return (f"<div class='tcl'><span class='mu'>Il {_dm(dt.strftime('%Y-%m-%d'))}</span> <b>{_fmt(ref, d)}</b> "
                f"{arrow(pct if rel else diff, (1.0 if rel else 0.0) if thr is None else thr, risk)} <span class='mu'>({t})</span></div>")
    attrs = (f" data-h='{json.dumps(_closes(s), separators=(',', ':'))}' data-d='{d}' data-risk='{1 if risk else 0}'") if live else ""
    return f"<div class='trow'{attrs}>{one(prev)}{one(wk)}</div>"


def hero_trend(d: dict | None) -> str:
    if not d:
        return ""
    h = d["hist"].dropna()
    if len(h) < 7:
        return ""
    now, sett = float(h.iloc[-1]), float(h.iloc[-6])
    ch = now - sett
    word = "in aumento" if ch > 2 else ("in calo" if ch < -2 else "stabile")
    return (f"<div class='htr'><div class='htrb'>{arrow(ch, 2.0)} <b>Rischio {word}</b> <span class='mu'>(rispetto a una settimana fa)</span></div>"
            f"{trend_dated(h, 0, True, rel=False, live=False, thr=1.0)}</div>")


def _vix_gauge(v: float | None) -> str:
    if v is None:
        return ""
    lo, hi = 10.0, 45.0
    pos = min(max((v - lo) / (hi - lo), 0), 1) * 100
    return ("<div class='vg'><div class='vgb'><i style='left:" + f"{pos:.1f}" + "%' id='vixmark'></i></div>"
            "<div class='vgl'><span>calma<br>&lt;15</span><span>normale<br>15-20</span><span>nervoso<br>20-30</span><span>stress<br>&gt;30</span></div></div>")


def _light(sem: list, key: str) -> tuple[str, str]:
    for i in sem or []:
        if i["key"] == key:
            return i["light"], semafori.LIGHT_TXT.get(i["light"], "")
    return "na", "In raccolta"


def _tail(s: pd.Series, n: int):
    s = s.dropna()
    return (float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else None, float(s.iloc[-6]) if len(s) > 5 else None) if len(s) else (None, None, None)


def kpi_html(sem: list, sp: pd.Series, vwce: pd.Series, vix: pd.Series) -> str:
    cards = ""
    # VIX
    v, v1, v5 = _tail(vix, 6)
    lt, ltxt = _light(sem, "vix")
    cards += (f"<div class='kc lq' data-k='vix' data-chart='vix'><div class='kt'>VIX · paura <span class='sdot {lt}'></span><small>{ltxt}</small></div>"
              f"<div class='kv lqp'>{_fmt(v, 2)}</div><div class='lqc'></div>"
              f"{_vix_gauge(v)}{trend_dated(vix, 2, True)}"
              "<div class='mu'>Sopra 20 nervoso, sopra 30 stress.</div></div>")
    # Put/Call
    arch = semafori._arch_series("pc_open_interest")
    pc, p1, p5 = _tail(arch, 6)
    lt, ltxt = _light(sem, "pc_oi")
    if pc is None:
        body = "<div class='kv'>n.d.</div><div class='mu'>In raccolta: l'archivio ha iniziato da poco, servono alcuni giorni per ieri e settimana.</div>"
    else:
        body = (f"<div class='kv'>{_fmt(pc, 2)}</div>{trend_dated(arch, 2, True, live=False)}"
                + ("" if len(arch) > 5 else f"<div class='mu'>Storia ancora corta ({len(arch)} {'giorno' if len(arch) == 1 else 'giorni'}).</div>"))
    cards += (f"<div class='kc' data-chart='pc_oi'><div class='kt'>Put/Call (SPY) <span class='sdot {lt}'></span><small>{ltxt}</small></div>{body}"
              "<div class='mu'>Più alto = più protezioni comprate.</div></div>")
    # S&P 500 e VWCE
    for key, nm, ser, chart in (("sp500", "S&P 500", sp, "sp500"), ("vwce", "VWCE", vwce, "vwce")):
        s = ser.dropna()
        if s.empty:
            continue
        x = float(s.iloc[-1])
        dd = (x / float(s.rolling(252, min_periods=60).max().iloc[-1]) - 1) * 100
        cards += (f"<div class='kc lq' data-k='{key}' data-chart='{chart}'><div class='kt'>{nm}</div><div class='kv lqp'>{_fmt(x, 2)}</div><div class='lqc'></div>"
                  f"{trend_dated(s, 2, False)}<div class='mu'>Dal massimo a 1 anno: {_fmt(dd, 1)}%</div></div>")
    return f"<div class='kpis'>{cards}</div><div class='mu liveinfo' style='margin:-4px 0 10px'></div>"


def _delta(v, prev):
    if prev is None or (isinstance(prev, float) and np.isnan(prev)):
        return "<span class='mu'>n/d</span>"
    d = v - prev
    if abs(d) < 0.5:
        return f"<b>{prev:.0f}</b> <span class='mu'>(invariato)</span>"
    cl, fr = ("amu", "▲ sale") if d > 0 else ("amd", "▼ scende")
    return f"<b>{prev:.0f}</b> <span class='{cl}'>{fr} di {abs(d):.0f}</span>"


def armor_window(h: dict | None, d: dict | None) -> str:
    """Finestra dei tre indici Armor (si apre toccando l'Indice Armor): tre schede chiare, con barra del livello, cosa pesa di più e quanto è affidabile."""
    if not h or not d:
        return ""
    col = armor_index.color
    cards = ""
    lab = {"settimana": ("Prossima settimana", "per chi guarda i prossimi giorni", "Conta soprattutto la paura sui mercati e come si stanno muovendo i prezzi."),
           "mese": ("Prossimo mese", "per chi guarda le prossime settimane", "Contano paura e prezzi, ma anche lo stato del credito (quanto è facile farsi prestare soldi)."),
           "3 mesi": ("Prossimi 3 mesi", "per chi guarda un orizzonte più lungo", "Contano di più credito e prezzi delle azioni rispetto agli utili (se sono cari o no).")}
    for k, x in h["orizzonti"].items():
        v = x["v"]
        name, _ = armor_index.band(v)
        a = x.get("auc") or {}
        zone = "<div class='amb'><i style='background:hsl(125,60%,42%);flex:30'></i><i style='background:hsl(60,70%,48%);flex:25'></i><i style='background:hsl(30,80%,50%);flex:25'></i><i style='background:hsl(0,70%,45%);flex:20'></i>" \
               f"<b style='left:{min(max(v, 1), 99):.0f}%'></b></div><div class='amt'><span>basso</span><span>moderato</span><span>alto</span><span>molto alto</span></div>"
        pesi = sorted(h["pesi"].get(k, {}).items(), key=lambda t: -t[1])[:3]
        mx = max([p_ for _g, p_ in pesi] or [1])
        peso_html = "".join(f"<div class='amw'><span>{e(g)}</span><i style='width:{p_ / mx * 100:.0f}%'></i><b>{int(p_)}%</b></div>" for g, p_ in pesi)
        ver = ""
        if a.get("nuovo") is not None and not np.isnan(a["nuovo"]):
            diff = a["nuovo"] - a["standard"]
            diff13 = a["nuovo_2013"] - a["standard_2013"]
            if diff > 0.005 and diff13 >= -0.005:
                chip, ct = "ok", "meglio dell'indice standard"
            elif diff13 < -0.005 or diff < -0.005:
                chip, ct = "wa", "non meglio dell'indice standard"
            else:
                chip, ct = "wa", "alla pari con l'indice standard"
            ver = (f"<div class='amh'>Quanto ha funzionato in passato</div><div class='amv2'>{a['nuovo'] * 100:.0f} <span class='mu'>su 100</span></div>"
                   f"<div class='mu'>È la capacità di dare un numero più alto ai giorni che poi sono stati pericolosi. 50 = come tirare a indovinare, 100 = perfetta.</div>"
                   f"<span class='pvch {chip}'>{ct}</span><div class='mu' style='margin-top:4px'>Dal 2013 a oggi: {a['nuovo_2013'] * 100:.0f} su 100 (l'indice standard: {a['standard_2013'] * 100:.0f}).</div>")
        cards += (f"<div class='am3'><div class='amk'>{lab[k][0]}</div><div class='mu'>{lab[k][1]}</div><div class='amv' style='color:{col(v)}'>{v:.0f}<span>/100</span></div>"
                  f"<div class='aml' style='color:{col(v)}'>Rischio {name}</div>{zone}<div class='mu' style='margin-top:6px'>{lab[k][2]}</div>"
                  f"<div class='amh'>Com'è cambiato</div><div class='amc'>Ieri era {_delta(v, x['ieri'])}</div><div class='amc'>Una settimana fa era {_delta(v, x['sett'])}</div>"
                  f"<div class='amh'>Cosa pesa di più nel numero</div>{peso_html}{ver}</div>")
    std = d["value"]
    return ("<div id='amod' class='cmodal'><div class='cbox'><button class='cx' aria-label='Chiudi'>×</button><div class='cbody'>"
            "<h3 style='margin-top:0'>Indice Armor: il rischio a tre scadenze</h3>"
            "<div class='explain'><p><b>Come si legge, in 10 secondi.</b> Ogni scheda è un numero da 1 a 100: <b>più è alto, più il mercato è a rischio</b>. Intorno a 50 il rischio è nella media. "
            "Sono gli stessi dati, contati in modo diverso a seconda dell'orizzonte: a una settimana pesa di più la paura sui mercati, a tre mesi pesano di più credito e prezzi delle azioni. "
            "<b>Se i tre numeri sono molto diversi</b>, ti dicono che il rischio sta crescendo solo in un orizzonte (per esempio solo a breve).</p></div>"
            f"<div class='am3w'>{cards}</div>"
            f"<div class='amsum'><b>Media dei tre: {h['media']:.0f}</b> · Numero mostrato nella pagina «Oggi»: <b>{std:.0f}</b>. "
            "Nella pagina «Oggi» resta quello di sempre, perché la media dei tre non si è dimostrata migliore.</div>"
            "<details class='gl'><summary>Quanto possiamo fidarci</summary><p class='mu'>I pesi sono stati decisi in anticipo, non adattati ai dati già visti. A una settimana il nuovo numero è appena meglio di quello standard; "
            "a tre mesi, dal 2013 a oggi, è uguale o peggio. Quindi: utile per capire <i>che tipo</i> di rischio cresce, non per prevedere un crollo.</p></details>"
            "<p><button class='btn pri' data-chart='armor_index' id='amodchart'>Apri il grafico dell'Indice Armor</button> <button class='btn' data-go='indici'>Come è calcolato</button></p>"
            "</div></div></div>")


def ticker_items(news: dict, evs: list[dict], aix: dict | None) -> list[dict]:
    """Elementi della barra in basso. Le notizie vengono dopo indice ed eventi, dalla piu' recente alla meno recente, con la data breve."""
    from datetime import datetime, timedelta, timezone

    from . import novita
    out = []
    if aix:
        out.append({"t": f"Indice Armor {aix['value']:.0f}/100 · rischio {armor_index.band(aix['value'])[0]}", "n": 0})
    for x in evs[:2]:
        out.append({"t": f"📅 {x['date'][8:10]}/{x['date'][5:7]}: {x['nome']}", "n": 0})
    now = datetime.now(timezone.utc)
    its = [i for i in (news or {}).get("items", []) if i.get("kind") in ("macro", "sector") and i.get("time")]
    rec = [i for i in its if datetime.fromisoformat(i["time"].replace("Z", "+00:00")) > now - timedelta(days=3)] or its
    rec = sorted(rec, key=lambda x: -x["score"])[:10]
    for i in sorted(rec, key=lambda x: x["time"], reverse=True):
        tag = {"negativo": "▼", "positivo": "▲"}.get(i.get("label"), "•")
        t = i["title"].rsplit(" - ", 1)[0]
        out.append({"t": f"{novita.etichetta_giorno(i['time'], now)} {tag} {t[:100]}", "n": 1})
    return out


JS = r"""
<script>
(function(){
var m=document.getElementById('amod');
document.addEventListener('click',function(ev){var a=ev.target.closest&&ev.target.closest('[data-amod]');if(a&&!ev.target.closest('a')){ev.preventDefault();ev.stopPropagation();if(m)m.classList.add('show');return}
if(m&&(ev.target===m||ev.target.classList.contains('cx')))m.classList.remove('show');
if(m&&ev.target.closest&&ev.target.closest('#amod [data-chart],#amod [data-go]'))m.classList.remove('show')},true);
function mv(){var q=window.LIVE&&window.LIVE.quotes&&window.LIVE.quotes.vix;var el=document.getElementById('vixmark');if(q&&q.price&&el){el.style.left=Math.min(Math.max((q.price-10)/35,0),1)*100+'%'}}
setInterval(mv,15000);setTimeout(mv,1500);
})();
</script>
"""

TICKER_JS = r"""
<script>
(function(){var el=document.getElementById('dkt');if(!el)return;var items=(window.TICKER||[]).map(function(x){return typeof x==='string'?{t:x,n:0}:x}),i=0,cur=null,hold=false,SEC=9000;
function vw(){var q=window.LIVE&&window.LIVE.quotes&&window.LIVE.quotes.vwce;if(!q||!q.price)return null;var c=q.chg!=null?(' '+(q.chg>=0?'▲':'▼')+Math.abs(q.chg*100).toFixed(2).replace('.',',')+'%'):'';
return {t:'VWCE '+q.price.toFixed(2).replace('.',',')+' €'+c,n:0}}
function next(){if(hold)return;var all=[];var v=vw();if(v)all.push(v);items.forEach(function(x){all.push(x)});if(!all.length)return;cur=all[i%all.length];i++;el.style.opacity=0;setTimeout(function(){el.textContent=cur.t;el.style.opacity=1},400)}
next();setInterval(next,SEC);
var bar=document.getElementById('dockbar');if(bar){var rel=null;function h(){hold=true;clearTimeout(rel)}function r(){clearTimeout(rel);rel=setTimeout(function(){hold=false},3000)}
 bar.addEventListener('mouseenter',h);bar.addEventListener('mouseleave',r);bar.addEventListener('touchstart',h,{passive:true});bar.addEventListener('touchend',r,{passive:true})}
el.addEventListener('click',function(e){if(cur&&cur.n&&window.armorDock){e.stopPropagation();window.armorDock('notizie')}})})();
</script>
"""

CSS = """
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 14px}
.kc .mu{font-size:12px;color:var(--mu)}.kc .lqc{font-size:12px}.kc{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:11px 12px;cursor:pointer}
.kt{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;color:var(--mu);display:flex;align-items:center;gap:6px;flex-wrap:wrap}.kt small{font-size:11px;text-transform:none;letter-spacing:0;font-weight:700;color:var(--tx)}
.kv{font-size:30px;font-weight:800;line-height:1.1;margin:4px 0}
.sdot{display:inline-block;width:13px;height:13px;border-radius:50%;background:var(--mu)}.sdot.ok{background:var(--ok)}.sdot.wa{background:var(--warn)}.sdot.ba{background:var(--bad)}
.trow{display:grid;gap:2px;font-size:12px;margin:4px 0}.tcl b{font-size:13px}.trb{color:var(--bad);font-weight:900}.trg{color:var(--ok);font-weight:900}.tr0{color:var(--mu);font-weight:900}
.vg{margin:6px 0 4px}.vgb{position:relative;height:10px;border-radius:6px;background:linear-gradient(90deg,#2fb36b 0%,#2fb36b 14%,#e1c23a 29%,#e8962f 57%,#d8392b 100%)}
.vgb i{position:absolute;top:-4px;width:4px;height:18px;border-radius:2px;background:var(--tx);box-shadow:0 0 0 2px var(--card);transform:translateX(-2px)}
.vgl{display:flex;justify-content:space-between;font-size:9px;color:var(--mu);line-height:1.1;margin-top:3px;text-align:center}
.htr{margin-top:6px;padding-top:6px;border-top:1px solid rgba(128,128,128,.3)}.htrb{font-size:14px}.htrb .trb,.htrb .trg,.htrb .tr0{font-size:18px}
.aix{cursor:pointer}.am3w{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:12px 0}
.am3{border:1px solid var(--bd);border-radius:18px;padding:14px 15px;background:var(--bg);box-shadow:0 2px 10px rgba(0,0,0,.12)}.amk{font-weight:800;font-size:16px}.amh{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--mu);margin:12px 0 4px;border-top:1px dashed var(--bd);padding-top:8px}.amb{display:flex;height:10px;border-radius:99px;overflow:hidden;position:relative;margin:10px 0 3px}.amb i{display:block}.amb b{position:absolute;top:-3px;width:5px;height:16px;border-radius:3px;background:var(--tx);box-shadow:0 0 0 2px var(--bg);transform:translateX(-50%)}.amt{display:flex;justify-content:space-between;font-size:9.5px;color:var(--mu)}.amc{font-size:13px;margin:2px 0}.amu{color:var(--bad);font-weight:700}.amd{color:var(--ok);font-weight:700}.amw{display:grid;grid-template-columns:1fr 54px 34px;gap:6px;align-items:center;font-size:12px;margin:3px 0}.amw i{display:block;height:7px;border-radius:99px;background:var(--ac)}.amw b{text-align:right}.amv2{font-size:20px;font-weight:800}.amsum{border:1px solid var(--bd);border-radius:14px;padding:10px 14px;background:var(--card);margin:6px 0 10px;font-size:14px}.amv{font-size:40px;font-weight:800;line-height:1.05}.amv span{font-size:15px;color:var(--mu)}.aml{font-weight:800}
#amod{z-index:26}#dkt{transition:opacity .4s}
"""
