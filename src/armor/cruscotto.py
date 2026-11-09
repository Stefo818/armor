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


def _dv(v, prev, d=0):
    """Valore passato con la differenza da oggi: rosso se oggi è più alto (più rischio), verde se più basso."""
    if prev is None or (isinstance(prev, float) and np.isnan(prev)):
        return "<span class='mu'>n/d</span>"
    dd = v - prev
    if abs(dd) < 0.5:
        return f"<b>{prev:.{d}f}</b> <span class='mu'>invariato</span>"
    cl, fr = ("amu", "▲ oggi è più alto di") if dd > 0 else ("amd", "▼ oggi è più basso di")
    return f"<b>{prev:.{d}f}</b> <span class='{cl}'>{fr} {abs(dd):.0f}</span>"


def _spark(vals: list, soglia: float = 40.0) -> str:
    if not vals or len(vals) < 3:
        return ""
    n = len(vals)
    X = lambda i: i * 100 / (n - 1)
    Y = lambda v: 38 - min(max(v, 0), 100) / 100 * 34
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    return ("<svg viewBox='0 0 100 42' preserveAspectRatio='none' class='amsp' role='img' aria-label='Andamento degli ultimi 3 mesi'>"
            f"<rect x='0' y='{Y(100):.1f}' width='100' height='{Y(60) - Y(100):.1f}' fill='hsl(0,70%,45%)' opacity='.10'/><rect x='0' y='{Y(60):.1f}' width='100' height='{Y(40) - Y(60):.1f}' fill='hsl(45,80%,50%)' opacity='.10'/>"
            f"<line x1='0' x2='100' y1='{Y(soglia):.1f}' y2='{Y(soglia):.1f}' stroke='var(--mu)' stroke-width='.7' stroke-dasharray='2 2' vector-effect='non-scaling-stroke'/>"
            f"<polyline fill='none' stroke='var(--ac)' stroke-width='2' vector-effect='non-scaling-stroke' points='{pts}'/><circle cx='100' cy='{Y(vals[-1]):.1f}' r='2.4' fill='var(--ac)'/></svg>"
            "<div class='amsl'><span>3 mesi fa</span><span>linea tratteggiata = 40</span><span>oggi</span></div>")


def _frase(v, x, name):
    sett = v - (x.get("media_sett") if x.get("media_sett") is not None else v)
    p7 = x.get("sett")
    if p7 is None:
        tr = ""
    else:
        d = v - p7
        tr = "è salito" if d >= 3 else "è sceso" if d <= -3 else "è rimasto più o meno uguale"
        tr = f"Rispetto a una settimana fa {tr}"
    gg = x.get("giorni_soglia")
    gu = "giorno" if gg == 1 else "giorni"
    sopra = x.get("sopra")
    stato = ""
    if gg is not None:
        stato = (f" ed è sopra 40 da {gg} {gu}" if sopra else f" ed è sotto 40 da {gg} {gu}") if not x.get("da_inizio") else (" ed è sempre stato sopra 40" if sopra else " ed è sempre stato sotto 40")
    return f"Il rischio è <b>{name}</b>. {tr}{stato}." if tr else f"Il rischio è <b>{name}</b>{stato}."


def armor_window(h: dict | None, d: dict | None) -> str:
    """Finestra dei tre indici Armor (si apre toccando l'Indice Armor): per ogni scadenza numero, parola, grafico di 3 mesi e confronto con ieri, settimana, mese, medie e da quanto è sopra 40."""
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
        zone = "<div class='amb'><i style='background:hsl(125,60%,42%);flex:40'></i><i style='background:hsl(60,70%,48%);flex:20'></i><i style='background:hsl(30,80%,50%);flex:20'></i><i style='background:hsl(0,70%,45%);flex:20'></i>" \
               f"<b style='left:{min(max(v, 1), 99):.0f}%'></b></div><div class='amt'><span>basso</span><span>40</span><span>moderato</span><span>elevato</span><span>molto alto</span></div>"
        pesi = sorted(h["pesi"].get(k, {}).items(), key=lambda t: -t[1])[:3]
        mx = max([p_ for _g, p_ in pesi] or [1])
        peso_html = "".join(f"<div class='amw'><span>{e(g)}</span><i style='width:{p_ / mx * 100:.0f}%'></i><b>{int(p_)}%</b></div>" for g, p_ in pesi)
        ver = ""
        if a.get("nuovo") is not None and not np.isnan(a["nuovo"]):
            diff, diff13 = a["nuovo"] - a["standard"], a["nuovo_2013"] - a["standard_2013"]
            chip, ct = ("ok", "meglio dell'indice standard") if diff > 0.005 and diff13 >= -0.005 else (("wa", "non meglio dell'indice standard") if diff13 < -0.005 or diff < -0.005 else ("wa", "alla pari con l'indice standard"))
            ver = (f"<div class='amh'>Quanto ha funzionato in passato</div><div class='amv2'>{a['nuovo'] * 100:.0f} <span class='mu'>su 100</span></div>"
                   f"<div class='mu'>Capacità di dare un numero più alto ai giorni che poi sono stati pericolosi. 50 = come tirare a indovinare, 100 = perfetta.</div>"
                   f"<span class='pvch {chip}'>{ct}</span><div class='mu' style='margin-top:4px'>Dal 2013 a oggi: {a['nuovo_2013'] * 100:.0f} su 100 (indice standard: {a['standard_2013'] * 100:.0f}).</div>")
        da = x.get("da_soglia", "")
        da_txt = f"{da[8:10]}/{da[5:7]}/{da[:4]}" if da else ""
        riga_soglia = ""
        if x.get("giorni_soglia") is not None:
            if x.get("da_inizio"):
                riga_soglia = f"<tr><td>{'Sopra' if x['sopra'] else 'Sotto'} 40</td><td><b>da sempre</b> <span class='mu'>(in tutto il periodo calcolato)</span></td></tr>"
            else:
                riga_soglia = f"<tr><td>{'Sopra' if x['sopra'] else 'Sotto'} 40 da</td><td><b>{x['giorni_soglia']} {'giorno' if x['giorni_soglia'] == 1 else 'giorni'}</b> <span class='mu'>(dal {da_txt})</span></td></tr>"
        tab = ("<table class='amtab'>"
               f"<tr><td>Ieri</td><td>{_dv(v, x['ieri'])}</td></tr><tr><td>Una settimana fa</td><td>{_dv(v, x['sett'])}</td></tr><tr><td>Un mese fa</td><td>{_dv(v, x.get('mese_fa'))}</td></tr>"
               f"<tr><td>Media dell'ultima settimana</td><td>{_dv(v, x.get('media_sett'))}</td></tr><tr><td>Media dell'ultimo mese</td><td>{_dv(v, x.get('media_mese'))}</td></tr>{riga_soglia}</table>")
        cards += (f"<div class='am3'><div class='amk'>{lab[k][0]}</div><div class='mu'>{lab[k][1]}</div><div class='amv' style='color:{col(v)}'>{v:.0f}<span>/100</span></div>"
                  f"<div class='aml' style='color:{col(v)}'>Rischio {name}</div><div class='amf'>{_frase(v, x, name)}</div>{zone}{_spark(x.get('spark'))}"
                  f"<div class='amh'>Confronto con il passato</div>{tab}"
                  f"<details class='amd2'><summary>Cosa pesa nel numero e quanto è affidabile</summary><div class='mu' style='margin:6px 0'>{lab[k][2]}</div>{peso_html}{ver}</details></div>")
    std = d["value"]
    ov = h["orizzonti"]
    tutte_mod = all(armor_index.band(x["v"])[0] == armor_index.band(list(ov.values())[0]["v"])[0] for x in ov.values())
    riep = (f"Oggi il rischio è <b>{armor_index.band(list(ov.values())[0]['v'])[0]}</b> su tutte e tre le scadenze." if tutte_mod
            else "Le tre scadenze <b>non coincidono</b>: " + ", ".join(f"{lab[k][0].lower()} {armor_index.band(x['v'])[0]}" for k, x in ov.items()) + ".")
    return ("<div id='amod' class='cmodal'><div class='cbox'><button class='cx' aria-label='Chiudi'>×</button><div class='cbody'>"
            "<h3 style='margin-top:0'>Indice Armor: il rischio a tre scadenze</h3>"
            f"<div class='explain'><p><b>Come si legge, in 10 secondi.</b> Ogni scheda è un numero da 1 a 100: <b>più è alto, più il mercato è a rischio</b>. Sotto 40 il rischio è basso, tra 40 e 60 è moderato, oltre 60 è elevato. "
            f"{riep} Le tre schede usano gli stessi dati, contati in modo diverso: a una settimana pesa di più la paura sui mercati, a tre mesi pesano di più credito e prezzi delle azioni.</p></div>"
            f"<div class='am3w'>{cards}</div>"
            f"<div class='amsum'><b>Media delle tre scadenze: {h['media']:.0f}</b> · Numero mostrato nella pagina «Oggi»: <b>{std:.0f}</b>. "
            "Nella pagina «Oggi» resta quello di sempre, perché la media delle tre non si è dimostrata migliore.</div>"
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
.am3{border:1px solid var(--bd);border-radius:18px;padding:14px 15px;background:var(--bg);box-shadow:0 2px 10px rgba(0,0,0,.12)}.amk{font-weight:800;font-size:16px}.amh{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--mu);margin:12px 0 4px;border-top:1px dashed var(--bd);padding-top:8px}.amb{display:flex;height:10px;border-radius:99px;overflow:hidden;position:relative;margin:10px 0 3px}.amb i{display:block}.amb b{position:absolute;top:-3px;width:5px;height:16px;border-radius:3px;background:var(--tx);box-shadow:0 0 0 2px var(--bg);transform:translateX(-50%)}.amt{display:flex;justify-content:space-between;font-size:9.5px;color:var(--mu)}.amc{font-size:13px;margin:2px 0}.amu{color:var(--bad);font-weight:700}.amd{color:var(--ok);font-weight:700}.amw{display:grid;grid-template-columns:1fr 54px 34px;gap:6px;align-items:center;font-size:12px;margin:3px 0}.amw i{display:block;height:7px;border-radius:99px;background:var(--ac)}.amw b{text-align:right}.amv2{font-size:20px;font-weight:800}.amf{font-size:14px;line-height:1.45;margin:8px 0 4px}.amsp{width:100%;height:60px;display:block;margin-top:10px;border-radius:10px;background:var(--card)}.amsl{display:flex;justify-content:space-between;font-size:10px;color:var(--mu)}.amtab{width:100%;border-collapse:collapse;font-size:13px}.amtab td{padding:6px 0;border-bottom:1px solid var(--bd);vertical-align:top}.amtab td:first-child{color:var(--mu);width:46%;padding-right:8px}.amtab tr:last-child td{border-bottom:0}.amd2{margin-top:10px;border:1px solid var(--bd);border-radius:12px;padding:0 12px;background:var(--card)}.amd2 summary{padding:10px 0;font-weight:700;font-size:13px;cursor:pointer}.amsum{border:1px solid var(--bd);border-radius:14px;padding:10px 14px;background:var(--card);margin:6px 0 10px;font-size:14px}.amv{font-size:40px;font-weight:800;line-height:1.05}.amv span{font-size:15px;color:var(--mu)}.aml{font-weight:800}
#amod{z-index:26}#dkt{transition:opacity .4s}
"""
