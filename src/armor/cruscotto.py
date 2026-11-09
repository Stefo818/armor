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


def armor_window(h: dict | None, d: dict | None) -> str:
    """Finestra dei tre indici Armor (si apre toccando l'Indice Armor)."""
    if not h or not d:
        return ""
    col = armor_index.color
    cards = ""
    lab = {"settimana": ("A breve termine", "prossima settimana"), "mese": ("A medio termine", "prossimo mese"), "3 mesi": ("A lungo termine", "prossimi 3 mesi")}
    for k, x in h["orizzonti"].items():
        v = x["v"]
        name, _ = armor_index.band(v)
        a = x.get("auc") or {}
        ver = ""
        if a.get("nuovo") is not None and not np.isnan(a["nuovo"]):
            ver = (f"<div class='mu'>Verifica ({e(a['evento'])}, dal 2000): AUC {_fmt(a['nuovo'], 2)} contro {_fmt(a['standard'], 2)} dell'indice standard; "
                   f"dal 2013 {_fmt(a['nuovo_2013'], 2)} contro {_fmt(a['standard_2013'], 2)}.</div>")
        cards += (f"<div class='am3'><div class='mu'>{lab[k][0]} · {lab[k][1]}</div><div class='amv' style='color:{col(v)}'>{v:.0f}<span>/100</span></div>"
                  f"<div class='aml' style='color:{col(v)}'>Rischio {name}</div><div class='trow'>{trend_cells(v, x['ieri'], x['sett'], 0, 1.0, True)}</div>{ver}</div>")
    std = d["value"]
    w = h["pesi"]
    wtxt = "; ".join(f"<b>{k}</b>: " + ", ".join(f"{g.split()[0]} {int(v)}" for g, v in ww.items()) for k, ww in w.items())
    return ("<div id='amod' class='cmodal'><div class='cbox'><button class='cx' aria-label='Chiudi'>×</button><div class='cbody'>"
            "<h3 style='margin-top:0'>Indice Armor: breve, medio e lungo termine</h3>"
            "<div class='explain'><p>Stessi indicatori, ma con pesi diversi: a una settimana contano di più paura (VIX) e tendenza dei prezzi, a 3 mesi contano di più credito e valutazioni. "
            "Quando i tre indici divergono ti dice che tipo di rischio sta crescendo.</p></div>"
            f"<div class='am3w'>{cards}</div>"
            f"<p><b>Media dei tre: {h['media']:.0f}</b> · Indice standard (quello mostrato in «Oggi», validato dal 2000): <b>{std:.0f}</b>. "
            "L'indice mostrato resta lo standard: la media dei tre non è stata verificata meglio, quindi non lo sostituisce.</p>"
            "<p class='mu'>Verifica onesta: i pesi sono stati fissati in anticipo, non stimati sui dati. L'indice a 1 settimana batte di poco quello standard; a 3 mesi no (dal 2013 è alla pari o peggio). "
            f"Pesi usati — {wtxt}.</p>"
            "<p><button class='btn pri' data-chart='armor_index' id='amodchart'>Apri il grafico dell'Indice Armor</button> <button class='btn' data-go='indici'>Come è calcolato</button></p>"
            "</div></div></div>")


def ticker_items(news: dict, evs: list[dict], aix: dict | None) -> list[str]:
    out = []
    if aix:
        out.append(f"Indice Armor {aix['value']:.0f}/100 · rischio {armor_index.band(aix['value'])[0]}")
    for x in evs[:2]:
        out.append(f"📅 {x['date'][8:10]}/{x['date'][5:7]}: {x['nome']}")
    its = [i for i in (news or {}).get("items", []) if i.get("kind") in ("macro", "sector")]
    for i in its[:7]:
        tag = {"negativo": "▼", "positivo": "▲"}.get(i.get("label"), "•")
        t = i["title"].rsplit(" - ", 1)[0]
        out.append(f"{tag} {t[:110]}")
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
(function(){var el=document.getElementById('dkt');if(!el)return;var items=window.TICKER||[],i=0;
function vw(){var q=window.LIVE&&window.LIVE.quotes&&window.LIVE.quotes.vwce;if(!q||!q.price)return null;var c=q.chg!=null?(' '+(q.chg>=0?'▲':'▼')+Math.abs(q.chg*100).toFixed(2).replace('.',',')+'%'):'';
return 'VWCE '+q.price.toFixed(2).replace('.',',')+' €'+c}
function next(){var all=[];var v=vw();if(v)all.push(v);items.forEach(function(x){all.push(x)});if(!all.length)return;var t=all[i%all.length];i++;el.style.opacity=0;setTimeout(function(){el.textContent=t;el.style.opacity=1},250)}
next();setInterval(next,5000)})();
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
.aix{cursor:pointer}.am3w{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:10px 0}
.am3{border:1px solid var(--bd);border-radius:12px;padding:10px 12px;background:var(--bg)}.amv{font-size:40px;font-weight:800;line-height:1.05}.amv span{font-size:15px;color:var(--mu)}.aml{font-weight:800}
#amod{z-index:26}#dkt{transition:opacity .25s}
"""
