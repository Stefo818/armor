# -*- coding: utf-8 -*-
"""Pagina «Segnali di fondo» (crescita in tempo reale, trend e momentum, flussi e posizionamento) e pagina «Stress test». Solo HTML/SVG (e un piccolo script per gli importi in euro dello stress test)."""
import html as _h
import math

from . import minimi_ui
from .minimi_ui import CSS as BASE_CSS, _badge, _pc, _sp

CSS = BASE_CSS + """<style>
.mn .g3{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:10px 0}
.mn .kpi{border:1px solid var(--bd);border-radius:14px;padding:12px 14px;background:var(--card)}
.mn .kpi .k{font-size:12px;color:var(--mu)}.mn .kpi .v2{font-size:22px;font-weight:700;margin-top:2px}.mn .kpi .s{font-size:12px;color:var(--mu);margin-top:2px;line-height:1.35}
.mn .pills{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 2px}
.mn .pill{border-radius:999px;padding:5px 12px;font-size:13px;border:1px solid var(--bd);background:var(--card)}
.mn .pill.on{background:var(--okbg);border-color:var(--ok);color:var(--ok);font-weight:600}.mn .pill.off{background:var(--badbg);border-color:var(--bad);color:var(--bad)}
.mn .mrow{display:grid;grid-template-columns:minmax(120px,210px) 1fr 54px;gap:10px;align-items:center;padding:7px 0;border-bottom:1px solid var(--bd);font-size:13.5px}
.mn .mtr{position:relative;height:10px;border-radius:6px;background:linear-gradient(90deg,var(--okbg),var(--warnbg) 60%,var(--badbg))}
.mn .mtr i{position:absolute;top:-4px;width:4px;height:18px;border-radius:2px;background:var(--tx)}
.mn .stinput{display:flex;flex-wrap:wrap;gap:10px;align-items:end}
.mn .stinput label{display:flex;flex-direction:column;font-size:12.5px;color:var(--mu);gap:4px}
.mn .stinput input{font:inherit;font-size:16px;padding:9px 12px;border-radius:10px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);width:180px}
.mn .eur{font-weight:700;white-space:nowrap}
.mn .crisis{border:1px solid var(--bd);border-radius:16px;padding:14px;background:var(--card)}
.mn .crisis h4{margin:0 0 4px;font-size:15px}.mn .crisis .big{font-size:26px;font-weight:800;color:var(--bad)}
.mn .legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12.5px;color:var(--mu);margin:6px 0}
.mn .legend i{display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:5px;vertical-align:3px}
</style>"""

PAL = ["#3b82f6", "#ef4444", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6"]


def _fmt(x, d=1):
    return "n/d" if x is None else f"{x:.{d}f}".replace(".", ",")


def _sg(x, d=1):
    return f"{x:+.{d}f}".replace(".", ",")


def _shell(inner: str) -> str:
    return CSS + "<div class='mn'>" + inner + "</div>"


# ------------------------------------------------------------------ crescita
def _gauge(v: float) -> str:
    lo, hi = -3.0, 6.0
    cx, cy, r = 160, 140, 105

    def pt(x, rr=r):
        a = math.pi * (1 - (min(max(x, lo), hi) - lo) / (hi - lo))
        return cx + rr * math.cos(a), cy - rr * math.sin(a)

    def arc(a, b, col):
        x1, y1 = pt(a)
        x2, y2 = pt(b)
        return f"<path d='M{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f}' fill='none' stroke='{col}' stroke-width='20' opacity='.75'/>"
    g = arc(-3, 0, "var(--bad)") + arc(0, 1.5, "var(--warn)") + arc(1.5, 3, "#84cc16") + arc(3, 6, "var(--ok)")
    nx, ny = pt(v, r - 8)
    lab = "".join(f"<text x='{pt(t, r + 20)[0]:.0f}' y='{pt(t, r + 20)[1] + 4:.0f}' text-anchor='middle'>{t:+d}%</text>" for t in (-3, 0, 3, 6))
    return (f"<svg viewBox='0 0 320 170' role='img' aria-label='Stima di crescita {_sg(v)}%' style='max-width:380px;margin:auto'>{g}{lab}"
            f"<line x1='{cx}' y1='{cy}' x2='{nx:.1f}' y2='{ny:.1f}' stroke='var(--tx)' stroke-width='4' stroke-linecap='round'/><circle cx='{cx}' cy='{cy}' r='8' fill='var(--tx)'/>"
            f"<text x='{cx}' y='{cy + 26}' text-anchor='middle' style='fill:var(--tx);font-size:20px;font-weight:700'>{_sg(v)}%</text></svg>")


def _barre_pil(st: list) -> str:
    w, h, ml, mb = 760, 230, 36, 26
    vals = [x[1] for x in st] + [x[2] for x in st if x[2] is not None]
    lo, hi = min(min(vals), -1.0), max(vals) + 0.5
    n = len(st)
    bw = (w - ml - 8) / n
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / (hi - lo))
    g = [f"<line x1='{ml}' x2='{w - 8}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--tx)' opacity='.5'/><text x='{ml - 4}' y='{y(0) + 4:.1f}' text-anchor='end'>0%</text>"]
    for t in (2, 4, 6):
        if t < hi:
            g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(t):.1f}' y2='{y(t):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(t) + 4:.1f}' text-anchor='end'>{t}%</text>")
    for i, (q, now, act) in enumerate(st):
        x0 = ml + i * bw + bw * 0.12
        ultimo = i == n - 1
        top, bot = (y(now), y(0)) if now >= 0 else (y(0), y(now))
        col = "var(--warn)" if ultimo else ("var(--ac)" if now >= 0 else "var(--bad)")
        g.append(f"<rect x='{x0:.1f}' y='{top:.1f}' width='{bw * 0.76:.1f}' height='{max(bot - top, 1):.1f}' rx='3' fill='{col}' opacity='{.95 if ultimo else .55}'><title>{q}: stima {_sg(now)}%{'' if act is None else ', ufficiale ' + _sg(act) + '%'}</title></rect>")
        if act is not None:
            g.append(f"<circle cx='{x0 + bw * 0.38:.1f}' cy='{y(act):.1f}' r='3.6' fill='var(--tx)' stroke='var(--card)' stroke-width='1'/>")
        if i % 4 == 0 or ultimo:
            g.append(f"<text x='{x0 + bw * 0.38:.1f}' y='{h - 8}' text-anchor='middle' style='font-size:10px'>{q.replace(' ', chr(8201))}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Stima GDPNow e crescita ufficiale per trimestre'>{''.join(g)}</svg>"


def crescita_html(c: dict | None) -> str:
    if not c:
        return "<p class='mu'>La stima di crescita sarà disponibile dopo il prossimo aggiornamento giornaliero.</p>"
    sem = c["semaforo"]
    cls = {"verde": "", "giallo": "w", "rosso": "b"}[sem["colore"]]
    nome = {"verde": "Crescita solida", "giallo": "Crescita da osservare", "rosso": "Rischio di recessione"}[sem["colore"]]
    prec = c.get("precedente")
    h = [f"<div class='hero {cls}'><span class='small'>Stima della crescita dell'economia USA, {c['trimestre']} (Fed di Atlanta, aggiornata ogni pochi giorni)</span><b class='big'>{nome}: {_fmt(c['stima'])}% annualizzato</b>"
         f"{_h.escape('; '.join(sem['motivi']).capitalize())}." + (f" Trimestre precedente (dato ufficiale): {_fmt(prec['valore'])}%." if prec else "") + "</div>",
         "<p class='sub'>Chiave di lettura: la crescita è espressa «su base annua» (se il ritmo di questo trimestre durasse un anno). Sopra 2% l'economia cresce bene, sotto 0% si restringe. Una stima è un'indicazione, non una certezza: quella ufficiale arriva settimane dopo.</p>",
         "<div class='card' style='text-align:center'>" + _gauge(c["stima"]) + "</div>"]
    sah, rec, cur = c.get("sahm"), c.get("recessione"), c.get("curva")
    kp = []
    kp.append(f"<div class='kpi'><div class='k'>Indicatore di Sahm</div><div class='v2'>{_fmt(sah, 2)}</div><div class='s'>Sale quando la disoccupazione cresce in fretta. Da 0,50 in su è segnale di recessione in corso.</div></div>")
    kp.append(f"<div class='kpi'><div class='k'>Probabilità di recessione (12 mesi)</div><div class='v2'>{_fmt(rec, 1)}%</div><div class='s'>Stima del mercato dei titoli di Stato. Sopra 40% è una soglia di allarme.</div></div>")
    kp.append(f"<div class='kpi'><div class='k'>Curva dei tassi (10 anni meno 3 mesi)</div><div class='v2'>{_fmt(cur, 2)} punti</div><div class='s'>Sotto zero (curva invertita) ha anticipato quasi tutte le recessioni.</div></div>")
    h.append("<div class='g3'>" + "".join(kp) + "</div>")
    h.append("<h3>Le stime contro la realtà, trimestre per trimestre</h3><div class='card'>" + _barre_pil(c["storico"]) +
             "<div class='legend'><span><i style='background:var(--ac)'></i>stima finale della Fed di Atlanta</span><span><i style='background:var(--warn)'></i>trimestre in corso</span><span><i style='background:var(--tx)'></i>dato ufficiale (pallino)</span></div></div>")
    pr = c.get("prova", {})
    t, s = pr.get("tutto"), pr.get("senza_2020")
    if t:
        ok = t["utile"] and (s or {}).get("utile", True)
        h.append("<div class='card' style='margin-top:10px'><b>Quanto ci si può fidare?</b> " + _badge("ok" if ok else "warn", "utile" if ok else "da prendere con cautela") +
                 f"<p class='small' style='margin:8px 0 0'>Su {t['n']} trimestri già pubblicati, la stima finale ha sbagliato in media di <b>{_fmt(t['mae_now'])} punti</b>, contro {_fmt(t['mae_ingenuo'])} se si ripetesse semplicemente il trimestre precedente "
                 f"({_fmt(s['mae_now']) if s else 'n/d'} contro {_fmt(s['mae_ingenuo']) if s else 'n/d'} escludendo il 2020). Ha indovinato il segno (crescita o contrazione) nel {_pc(t['segno'])} dei casi. "
                 "Il confronto usa il dato ufficiale più recente, che può essere stato rivisto.</p></div>")
    mk = c.get("mercato") or []
    if mk:
        rows = "".join(f"<tr><td>{_h.escape(m['banda'].capitalize())}</td><td>{m['n']}</td><td>{_sp(m['mediana'])}</td><td>{_pc(m['positivi'])}</td></tr>" for m in mk)
        h.append("<h3>E il mercato azionario?</h3><div class='card scroll'><table class='tb'><tr><th>Stima di crescita</th><th>Trimestri</th><th>Rendimento mediano S&amp;P 500 nei 3 mesi dopo</th><th>Volte positivo</th></tr>" + rows +
                 "</table><p class='small'>Dal 2011. Il mercato sale in media a prescindere dalla fascia: la crescita dice <i>come sta l'economia</i>, non quando comprare. Contrazione e crescita debole hanno pochissimi casi.</p></div>")
    return "".join(h)


# ------------------------------------------------------------------ trend
def _grafico_trend(t: dict) -> str:
    rc = t["recente"]
    pr, s200, s50 = rc["prezzo"], dict(map(tuple, rc["sma200"])), dict(map(tuple, rc["sma50"]))
    w, h, ml, mb = 760, 230, 44, 22
    vals = [v for _, v in pr] + [v for v in s200.values() if v == v] + [v for v in s50.values() if v == v]
    lo, hi = min(vals) * 0.98, max(vals) * 1.02
    n = len(pr)
    x = lambda i: ml + (w - ml - 8) * i / max(n - 1, 1)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / (hi - lo))
    g = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(v) + 4:.1f}' text-anchor='end'>{v:.0f}</text>")
    # zone sotto la media a 200 giorni
    inizio = None
    for i, (d, v) in enumerate(pr):
        sotto = d in s200 and v < s200[d]
        if sotto and inizio is None:
            inizio = i
        if (not sotto or i == n - 1) and inizio is not None:
            g.append(f"<rect x='{x(inizio):.1f}' y='8' width='{max(x(i) - x(inizio), 2):.1f}' height='{h - 8 - mb}' fill='var(--bad)' opacity='.10'/>")
            inizio = None
    line = lambda pts, col, sw, da="": ("<polyline fill='none' stroke='" + col + f"' stroke-width='{sw}' {da} points='" + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in pts) + "'/>")
    g.append(line([(i, s200[d]) for i, (d, _) in enumerate(pr) if d in s200], "var(--warn)", 2))
    g.append(line([(i, s50[d]) for i, (d, _) in enumerate(pr) if d in s50], "var(--mu)", 1.4, "stroke-dasharray='5 3'"))
    g.append(line([(i, v) for i, (_, v) in enumerate(pr)], "var(--ac)", 2))
    for yr in sorted({d[:4] for d, _ in pr}):
        i = next((j for j, (d, _) in enumerate(pr) if d >= f"{yr}-01-01"), None)
        if i:
            g.append(f"<text x='{x(i):.1f}' y='{h - 6}' text-anchor='middle'>{yr}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Prezzo con medie a 50 e 200 giorni'>{''.join(g)}</svg>"


def _curve(t: dict) -> str:
    a, b = t["curve"]["compra_e_tieni"], t["curve"]["trend"]
    w, h, ml, mb = 760, 250, 44, 22
    la, lb = [math.log(v) for _, v in a], [math.log(v) for _, v in b]
    lo, hi = min(la + lb), max(la + lb)
    n = len(a)
    x = lambda i: ml + (w - ml - 8) * i / max(n - 1, 1)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / (hi - lo))
    g = []
    for p in (1, 10, 100, 1000):
        if lo <= math.log(p) <= hi:
            g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(math.log(p)):.1f}' y2='{y(math.log(p)):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(math.log(p)) + 4:.1f}' text-anchor='end'>×{p}</text>")
    for yr in range(1930, 2030, 20):
        i = next((j for j, (d, _) in enumerate(a) if d >= f"{yr}-01-01"), None)
        if i:
            g.append(f"<text x='{x(i):.1f}' y='{h - 6}' text-anchor='middle'>{yr}</text>")
    g.append("<polyline fill='none' stroke='var(--mu)' stroke-width='1.8' points='" + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(la)) + "'/>")
    g.append("<polyline fill='none' stroke='var(--ok)' stroke-width='2.2' points='" + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(lb)) + "'/>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Crescita di 1 euro: trend contro comprare e tenere'>{''.join(g)}</svg>"


def trend_html(t: dict | None) -> str:
    if not t:
        return "<p class='mu'>Disponibile dopo il prossimo aggiornamento giornaliero.</p>"
    sc = t["punteggio"]
    cls = {3: "", 2: "", 1: "w", 0: "b"}[sc]
    msg = {3: "Trend rialzista pieno: tutti e tre i segnali sono positivi.", 2: "Trend rialzista: due segnali su tre sono positivi.", 1: "Trend incerto: un solo segnale su tre è positivo.", 0: "Trend ribassista: nessun segnale è positivo."}[sc]
    d = t["distanza_sma200"] * 100
    inc = t["ultimo_incrocio_media200"]
    verso = "verso l'alto" if inc["sopra"] else "verso il basso"
    dd = f"{abs(d):.1f}".replace(".", ",")
    h = [f"<div class='hero {cls}'><span class='small'>Trend dello S&amp;P 500 al {t['data'][8:]}/{t['data'][5:7]}/{t['data'][:4]}</span><b class='big'>{sc} segnali su 3 positivi</b>{msg} "
         f"Il prezzo è {dd}% {'sopra' if d >= 0 else 'sotto'} la media dei 200 giorni; l'ultimo incrocio è del {inc['data'][8:]}/{inc['data'][5:7]}/{inc['data'][:4]} ({verso}).</div>",
         "<p class='sub'>Chiave di lettura: i fondi che «seguono il trend» comprano quando il mercato è sopra la sua media e vendono quando scende sotto. Non prevedono: reagiscono. Qui si misura se questa regola avrebbe davvero aiutato.</p>",
         "<div class='pills'>" + "".join(f"<span class='pill {'on' if t[k] else 'off'}'>{'✓' if t[k] else '✕'} {_h.escape(minimi_ui_nome(k))}</span>" for k in ("T1", "T2", "T3")) + "</div>",
         "<div class='card' style='margin-top:10px'>" + _grafico_trend(t) +
         "<div class='legend'><span><i style='background:var(--ac)'></i>prezzo</span><span><i style='background:var(--warn)'></i>media 200 giorni</span><span><i style='background:var(--mu)'></i>media 50 giorni</span><span>zona rossa = prezzo sotto la media a 200 giorni</span></div></div>"]
    pr = t["prova"]
    st, bh = pr["strategie"], pr["compra_e_tieni"]
    p2 = st["P2"]
    h.append("<h3>Avrebbe aiutato? La regola «almeno 2 segnali su 3» contro comprare e tenere (dal 1928)</h3><div class='card'>" + _curve(t) +
             "<div class='legend'><span><i style='background:var(--ok)'></i>seguire il trend (in liquidità quando il trend è debole)</span><span><i style='background:var(--mu)'></i>comprare e tenere</span></div>"
             "<p class='small' style='margin:2px 0 0'>Scala logaritmica: ogni linea di griglia è dieci volte la precedente. Indice di prezzo senza dividendi, senza costi né tasse.</p></div>")
    rows = ["<div class='card scroll' style='margin-top:10px'><table class='tb'><tr><th>Regola</th><th>Rendimento annuo (1928-77 / 1978-2026)</th><th>Calo massimo (1928-77 / 1978-2026)</th><th>Tempo investito</th><th>Cambi all'anno</th><th>Giudizio</th></tr>"]
    b1, b2 = bh["prima"], bh["dopo"]
    rows.append(f"<tr><td><b>Comprare e tenere</b></td><td>{_pc(b1['rend_annuo'], 1)} / {_pc(b2['rend_annuo'], 1)}</td><td>{_pc(b1['calo_max'])} / {_pc(b2['calo_max'])}</td><td>100%</td><td>0</td><td>—</td></tr>")
    for k in ("T1", "T2", "T3", "P2"):
        s = st[k]
        m1, m2, mt = s["misure"]["prima"], s["misure"]["dopo"], s["misure"]["tutto"]
        giud = (_badge("ok", "protegge dai cali") if s["protegge"] else _badge("warn", "non protegge")) + " " + (_badge("ok", "rende di più") if s["rende_di_piu"] else _badge("warn", "non rende di più"))
        rows.append(f"<tr><td>{_h.escape(s['nome'])}</td><td>{_pc(m1['rend_annuo'], 1)} / {_pc(m2['rend_annuo'], 1)}</td><td>{_pc(m1['calo_max'])} / {_pc(m2['calo_max'])}</td><td>{_pc(mt['tempo_investito'])}</td><td>{_fmt(mt['cambi_anno'])}</td><td>{giud}</td></tr>")
    rows.append("<p></p></table><p class='small'>«Protegge» = il calo massimo si riduce di almeno un quarto sia nella prima sia nella seconda metà della storia. «Rende di più» = il rendimento annuo supera comprare e tenere in entrambe. "
                "Fuori dal mercato si prende il tasso a 3 mesi dei titoli di Stato. Lo scopo è ridurre le perdite grandi, non guadagnare di più: infatti di solito il rendimento è simile o minore.</p></div>")
    h.append("".join(rows).replace("<p></p>", ""))
    cd = t.get("condizionato") or []
    if cd:
        tr = "".join(f"<tr><td><b>{x['punteggio']} su 3</b></td><td>{x['giorni']}</td><td>{_sp(x['r63_med'], 1)}</td><td>{_sp(x['r252_med'], 1)}</td><td>{_pc(x['p_calo10'])}</td></tr>" for x in cd)
        h.append("<h3>Che cosa è successo dopo ogni punteggio</h3><div class='card scroll'><table class='tb'><tr><th>Segnali positivi</th><th>Giorni nella storia</th><th>Rendimento mediano a 3 mesi</th><th>A 1 anno</th><th>Casi con un altro calo oltre 10% nell'anno dopo</th></tr>" + tr +
                 "</table><p class='small'>Il punteggio 0 (trend ribassista) ha spesso preceduto rimbalzi forti, ma anche un altro calo oltre il 10% in più di metà dei casi: è un mercato già in difficoltà. Il trend ha senso come contesto, non come ordine di vendita o di acquisto.</p></div>")
    return "".join(h)


def minimi_ui_nome(k: str) -> str:
    from .trend import NOMI
    return NOMI[k]


# ------------------------------------------------------------------ flussi e opzioni
def _storia_term(f: dict) -> str:
    s = f["storia"]
    if not s:
        return ""
    w, h, ml, mb = 760, 170, 48, 22
    n = len(s)
    x = lambda i: ml + (w - ml - 8) * i / max(n - 1, 1)
    y = lambda v: 8 + (h - 8 - mb) * (1 - v)
    g = [f"<rect x='{ml}' y='{y(1):.1f}' width='{w - ml - 8}' height='{y(.8) - y(1):.1f}' fill='var(--bad)' opacity='.10'/><rect x='{ml}' y='{y(.2):.1f}' width='{w - ml - 8}' height='{y(0) - y(.2):.1f}' fill='var(--ok)' opacity='.10'/>"]
    for v in (0, .2, .5, .8, 1):
        g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(v) + 4:.1f}' text-anchor='end'>{int(v * 100)}%</text>")
    g.append("<polyline fill='none' stroke='var(--ac)' stroke-width='2' points='" + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(s)) + "'/>")
    g.append(f"<circle cx='{x(n - 1):.1f}' cy='{y(s[-1][1]):.1f}' r='5' fill='var(--warn)' stroke='var(--card)' stroke-width='2'/>")
    for yr in range(2012, 2027, 2):
        i = next((j for j, (d, _) in enumerate(s) if d >= f"{yr}-01-01"), None)
        if i:
            g.append(f"<text x='{x(i):.1f}' y='{h - 6}' text-anchor='middle'>{yr}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Termometro di affollamento dal 2011'>{''.join(g)}</svg>"


def _ladder(o: dict) -> str:
    L = o["ladder"]
    if not L:
        return ""
    w, h, ml, mb = 760, 280, 12, 24
    xs = [a for a, _, _ in L]
    lo, hi = min(xs), max(xs)
    mx = max(max(c, p) for _, c, p in L) or 1
    mid = (h - mb) / 2 + 4
    x = lambda v: ml + (w - 2 * ml) * (v - lo) / max(hi - lo, 1)
    bw = max((w - 2 * ml) / max(len(L), 1) * 0.7, 2)
    ys = lambda v: v / mx * ((h - mb) / 2 - 40)
    g = [f"<line x1='{ml}' x2='{w - ml}' y1='{mid}' y2='{mid}' stroke='var(--tx)' opacity='.4'/>"]
    for a, c, p in L:
        g.append(f"<rect x='{x(a) - bw / 2:.1f}' y='{mid - ys(c):.1f}' width='{bw:.1f}' height='{ys(c):.1f}' fill='var(--ok)' opacity='.7'><title>{a:.0f}: call {c}, put {p}</title></rect>"
                 f"<rect x='{x(a) - bw / 2:.1f}' y='{mid:.1f}' width='{bw:.1f}' height='{ys(p):.1f}' fill='var(--bad)' opacity='.7'/>")

    def lin(v, col, txt, da="", dy=0):
        if v is None or not (lo <= v <= hi):
            return ""
        return (f"<line x1='{x(v):.1f}' x2='{x(v):.1f}' y1='6' y2='{h - mb}' stroke='{col}' stroke-width='2' {da}/>"
                f"<text x='{x(v):.1f}' y='{18 + dy}' text-anchor='middle' style='fill:{col};font-weight:700'>{txt}</text>")
    g.append(lin(o["sp500"], "var(--warn)", f"oggi {o['sp500']:.0f}"))
    g.append(lin(o["flip_indice"], "var(--ac)", f"cambio gamma {o['flip_indice']:.0f}" if o["flip_indice"] else "", "stroke-dasharray='5 3'", 16))
    g.append(lin(o["muro_call"], "var(--ok)", f"muro call {o['muro_call']:.0f}" if o["muro_call"] else "", "stroke-dasharray='2 3'", 0))
    g.append(lin(o["muro_put"], "var(--bad)", f"muro put {o['muro_put']:.0f}" if o["muro_put"] else "", "stroke-dasharray='2 3'", 0))
    for v in range(int(math.ceil(lo / 100) * 100), int(hi), 100):
        g.append(f"<text x='{x(v):.1f}' y='{h - 6}' text-anchor='middle'>{v}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Interessi aperti sulle opzioni per livello'>{''.join(g)}</svg>"


def _curva_gex(o: dict) -> str:
    c = o["curva_gex"]
    w, h, ml, mb = 760, 170, 44, 22
    xs, vs = [a for a, _ in c], [float(v) for _, v in c]
    lo, hi = min(vs + [0]), max(vs + [0])
    x = lambda v: ml + (w - ml - 8) * (v - xs[0]) / max(xs[-1] - xs[0], 1)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / max(hi - lo, 1e-9))
    g = [f"<line x1='{ml}' x2='{w - 8}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--tx)' opacity='.5'/><text x='{ml - 4}' y='{y(0) + 4:.1f}' text-anchor='end'>0</text>"]
    pts = " ".join(f"{x(a):.1f},{y(float(v)):.1f}" for a, v in c)
    g.append(f"<polyline fill='none' stroke='var(--ac)' stroke-width='2.4' points='{pts}'/>")
    g.append(f"<line x1='{x(o['sp500']):.1f}' x2='{x(o['sp500']):.1f}' y1='8' y2='{h - mb}' stroke='var(--warn)' stroke-width='2'/>")
    for v in range(int(math.ceil(xs[0] / 100) * 100), int(xs[-1]), 100):
        g.append(f"<text x='{x(v):.1f}' y='{h - 6}' text-anchor='middle'>{v}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Gamma netta stimata al variare del prezzo'>{''.join(g)}</svg>"


def flussi_html(f: dict | None, o: dict | None) -> str:
    h = []
    if f:
        stato = {"affollato": ("b", "Mercato affollato"), "neutro": ("w", "Posizionamento neutro"), "prudente": ("", "Mercato prudente")}[f["stato"]]
        v = f["termometro"] * 100
        h.append(f"<div class='hero {stato[0]}'><span class='small'>Termometro di affollamento al {f['data'][8:]}/{f['data'][5:7]}/{f['data'][:4]} · {f['n_indicatori']} indicatori</span><b class='big'>{stato[1]}: {v:.0f}° percentile</b>"
                 "Misura quanto il mercato è «tutto dalla stessa parte»: sopra l'80° percentile gli investitori sono molto esposti e poco prudenti, sotto il 20° sono timorosi.</div>")
        h.append("<p class='sub'>Chiave di lettura: ogni indicatore è confrontato con la propria storia (solo il passato noto a quella data). 50° = situazione tipica. «Affollato» non significa che il mercato scenderà: significa che ci sarebbe meno gente pronta a comprare se arrivasse una brutta notizia.</p>")
        rows = "".join(f"<div class='mrow'><div>{_h.escape(i['nome'])}<div class='small'>{_h.escape(i['lettura'])} · dato al {i['data'][8:]}/{i['data'][5:7]}</div></div>"
                       f"<div class='mtr'><i style='left:calc({(i['percentile'] if i['segno'] > 0 else 1 - i['percentile']) * 100:.0f}% - 2px)'></i></div><b>{(i['percentile'] if i['segno'] > 0 else 1 - i['percentile']) * 100:.0f}°</b></div>" for i in f["indicatori"])
        h.append("<div class='card'>" + rows + "<p class='small' style='margin:8px 0 0'>A sinistra = prudente, a destra = affollato.</p></div>")
        h.append("<h3>Il termometro dal 2011</h3><div class='card'>" + _storia_term(f) + "<p class='small' style='margin:2px 0 0'>Fascia rossa = affollato (sopra 80%), verde = prudente (sotto 20%). Il pallino arancione è oggi.</p></div>")
        pr = f["prova"]
        fa = pr["fasce"]
        tab = "".join(f"<tr><td>{_h.escape(x['fascia'])}</td><td>{x['n']}</td><td>{_sp(x['r63_med'], 1)}</td><td>{_pc(x['p_calo7'])}</td></tr>" for x in fa)
        if pr.get("utile"):
            ver = _badge("ok", "utile") + f" Quando era sopra l'80° i cali oltre il 7% in 3 mesi sono stati {_pc(pr['differenza'])} più frequenti che sotto il 20° (intervallo {_pc(pr['ic90'][0])} … {_pc(pr['ic90'][1])})."
        else:
            ver = _badge("warn", "non verificato") + " Dal 2011 il termometro è stato sotto il 20° così di rado che il confronto non è possibile: oggi non si può dire che anticipi i cali."
        h.append("<div class='card scroll' style='margin-top:10px'><b>Ha funzionato?</b> " + ver + "<table class='tb' style='margin-top:8px'><tr><th>Termometro</th><th>Settimane</th><th>Rendimento mediano a 3 mesi</th><th>Calo oltre 7% in 3 mesi</th></tr>" + tab +
                 "</table><p class='small'>Settimane sovrapposte: i casi indipendenti sono molto meno. Usalo come contesto, non come segnale di acquisto o vendita.</p></div>")
    else:
        h.append("<p class='mu'>Termometro disponibile dopo il prossimo aggiornamento giornaliero.</p>")
    h.append("<h2 style='margin-top:30px'>Opzioni su SPY: dove sono i «muri»</h2>")
    if o:
        gx = o["gex_mld"]
        fd = o.get("flip_distanza")
        fdt = "" if fd is None else " (" + _sg(fd * 100) + "% da oggi)"
        gmsg = "Positiva: chi gestisce le opzioni tende a calmare i movimenti." if gx >= 0 else "Negativa: chi gestisce le opzioni tende ad amplificare i movimenti."
        gcol = "ok" if gx >= 0 else "bad"
        kp = [f"<div class='kpi'><div class='k'>Gamma netta stimata</div><div class='v2' style='color:var(--{gcol})'>{_sg(gx)} mld $</div><div class='s'>{gmsg}</div></div>",
              f"<div class='kpi'><div class='k'>Livello di cambio gamma</div><div class='v2'>{_fmt(o['flip_indice'], 0)}</div><div class='s'>Sopra questo livello la gamma è positiva, sotto negativa{fdt}.</div></div>",
              f"<div class='kpi'><div class='k'>Rapporto put/call</div><div class='v2'>{_fmt(o['pc_oi'], 2)}</div><div class='s'>Contratti put aperti per ogni call. Su SPY è alto perché molti la usano per proteggersi.</div></div>"]
        h.append("<div class='g3'>" + "".join(kp) + "</div>")
        h.append("<div class='card'>" + _ladder(o) + "<div class='legend'><span><i style='background:var(--ok)'></i>call aperte (sopra la linea)</span><span><i style='background:var(--bad)'></i>put aperte (sotto)</span><span>livelli convertiti in punti dell'S&amp;P 500</span></div></div>")
        h.append("<h3>Come cambia la gamma al muoversi del prezzo</h3><div class='card'>" + _curva_gex(o) + "<p class='small' style='margin:2px 0 0'>Miliardi di dollari per ogni 1% di movimento. Dove la curva passa sotto zero il mercato diventa più nervoso.</p></div>")
        v = o.get("verifica") or {}
        if v.get("pronto"):
            vt = (f"Dopo {v['giorni']} giorni di registro: con gamma positiva il movimento medio del giorno dopo è stato {_pc(v['mov_gamma_positiva'], 2)} ({v['n_pos']} giorni), con gamma negativa {_pc(v['mov_gamma_negativa'], 2)} ({v['n_neg']} giorni).")
        else:
            vt = f"Registro iniziato da {v.get('giorni', 1)} {'giorno' if v.get('giorni', 1) == 1 else 'giorni'}: tra {v.get('mancano', 59)} giorni l'app confronterà i movimenti del giorno dopo con gamma positiva e negativa."
        h.append("<div class='card' style='margin-top:10px'><b>Stima sperimentale</b> " + _badge("warn", "non ancora verificata") +
                 f"<p class='small' style='margin:8px 0 0'>Si ipotizza che gli operatori abbiano venduto le call e comprato le put: è una stima, non un dato certo. Dati di Yahoo (scadenze entro {45} giorni), {o['scadenze']} scadenze, ore {o.get('ora', '')}. {_h.escape(vt)}</p></div>")
    else:
        h.append("<p class='mu'>I dati sulle opzioni saranno disponibili dopo il prossimo aggiornamento giornaliero (Yahoo non sempre risponde: in quel caso resta l'ultimo dato).</p>")
    return "".join(h)


def segnali_pagina(c, t, f, o, cosa: str = "") -> str:
    return _shell("<h2>Segnali di fondo</h2>" + cosa + "<p class='sub'>Tre strumenti usati dai grandi gestori, adattati a un piano di accumulo: <b>la crescita dell'economia in tempo reale</b>, <b>il trend del mercato</b> e <b>quanto il mercato è affollato</b>. Ognuno ha la sua prova storica e dichiara i propri limiti.</p>"
                  "<h2 style='margin-top:18px'>1 · Crescita in tempo reale</h2>" + crescita_html(c) +
                  "<h2 style='margin-top:34px'>2 · Trend e momentum</h2>" + trend_html(t) +
                  "<h2 style='margin-top:34px'>3 · Flussi e posizionamento</h2>" + flussi_html(f, o) +
                  "<h3>Limiti, detti chiaramente</h3><div class='card'><ul class='small' style='margin:0;padding-left:18px;line-height:1.6'><li>Nessuno di questi segnali prevede il prossimo mese: descrivono lo stato del mercato e dell'economia.</li>"
                  "<li>La stima di crescita riguarda gli Stati Uniti; VWCE è un fondo mondiale.</li><li>Il trend è provato sull'S&amp;P 500 senza dividendi, costi e tasse: i cambi di posizione costerebbero nella realtà.</li>"
                  "<li>Il termometro ha pochi casi estremi dal 2011; le opzioni non hanno ancora storia, solo un registro che parte da oggi.</li><li>Non è un consiglio finanziario. Le regole sono scritte in PROTOCOLLO_MINIMI.md (parti H-K).</li></ul></div>")


# ------------------------------------------------------------------ stress test
STRESS_JS = r"""<script>
(function(){var I=document.getElementById('stval');if(!I)return;var K='armor_stress_v1',O=document.getElementById('stmsg');
function fm(v){return Math.round(v).toLocaleString('it-IT')}
function get(){try{return JSON.parse(localStorage.getItem(K)||'null')}catch(e){return null}}
function put(v){try{localStorage.setItem(K,JSON.stringify({v:v}))}catch(e){}}
function apply(v){var els=document.querySelectorAll('.eur[data-p]');for(var i=0;i<els.length;i++){var p=parseFloat(els[i].getAttribute('data-p'));els[i].textContent=v>0?fm(v*Math.abs(p))+' €':'—'}
 var tot=document.querySelectorAll('.eurtot[data-p]');for(var j=0;j<tot.length;j++){var q=parseFloat(tot[j].getAttribute('data-p'));tot[j].textContent=v>0?fm(v*q)+' €':'—'}}
var s=get();if(s&&s.v>0){I.value=s.v;apply(s.v)}
document.getElementById('stsave').onclick=function(){var v=parseFloat(I.value);if(!(v>0)){O.textContent='Scrivi il valore del tuo portafoglio in euro.';return}put(v);O.textContent='Importi aggiornati. Il valore resta solo in questo telefono.';apply(v)};
document.getElementById('stclear').onclick=function(){try{localStorage.removeItem(K)}catch(e){}I.value='';O.textContent='Dato cancellato da questo telefono.';apply(0)};
})();
</script>"""


def _ventaglio(att: dict) -> str:
    w, rh, ml, mr = 760, 54, 74, 20
    ks = [("1m", "1 mese"), ("3m", "3 mesi"), ("1a", "1 anno")]
    ex = [(a["istogramma"][0], a["istogramma"][-1]) for a in att.values()]
    lo, hi = min(min(e[0] for e in ex), -0.05) - 0.02, max(e[1] for e in ex) + 0.02
    H = rh * len(ks) + 30
    x = lambda v: ml + (w - ml - mr) * (v - lo) / (hi - lo)
    g = [f"<line x1='{x(0):.1f}' y1='6' x2='{x(0):.1f}' y2='{H - 22}' stroke='var(--bad)' stroke-dasharray='4 3' stroke-width='1.5'/><text x='{x(0):.1f}' y='{H - 8}' text-anchor='middle'>0%</text>"]
    step = 0.1 if hi - lo > 0.5 else 0.05
    v = math.ceil(lo / step) * step
    while v < hi:
        if abs(v) > 1e-9:
            g.append(f"<line x1='{x(v):.1f}' y1='6' x2='{x(v):.1f}' y2='{H - 22}' stroke='var(--bd)'/><text x='{x(v):.1f}' y='{H - 8}' text-anchor='middle'>{v * 100:+.0f}%</text>")
        v += step
    for i, (k, nome) in enumerate(ks):
        a = att.get(k)
        if not a:
            continue
        q = a["istogramma"]
        cy = 12 + rh * i + rh / 2 - 4
        g.append(f"<text x='4' y='{cy + 4:.1f}' style='fill:var(--tx);font-weight:600;font-size:12.5px'>{nome}</text>"
                 f"<rect x='{x(q[0]):.1f}' y='{cy - 5:.1f}' width='{x(q[-1]) - x(q[0]):.1f}' height='10' rx='5' fill='var(--ac)' opacity='.20'/>"
                 f"<rect x='{x(q[6]):.1f}' y='{cy - 10:.1f}' width='{x(q[18]) - x(q[6]):.1f}' height='20' rx='9' fill='var(--ac)' opacity='.45'/>"
                 f"<line x1='{x(q[12]):.1f}' y1='{cy - 14:.1f}' x2='{x(q[12]):.1f}' y2='{cy + 14:.1f}' stroke='var(--tx)' stroke-width='3' stroke-linecap='round'/>"
                 f"<circle cx='{x(a['fine_q5']):.1f}' cy='{cy:.1f}' r='4.5' fill='var(--bad)' stroke='var(--card)' stroke-width='1.5'/>")
    return f"<svg viewBox='0 0 {w} {H}' role='img' aria-label='Ventaglio dei risultati a 1, 3 e 12 mesi'>{''.join(g)}</svg>"


def _traiettorie(crisi: list) -> str:
    w, h, ml, mb = 760, 300, 44, 26
    allv = [v for c in crisi for _, v in c["traiettoria"]]
    lo, hi = min(allv + [-0.1]) - 0.03, max(allv + [0.1]) + 0.03
    xmax = max(g for c in crisi for g, _ in c["traiettoria"])
    x = lambda d: ml + (w - ml - 8) * d / max(xmax, 1)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / (hi - lo))
    g = [f"<line x1='{ml}' x2='{w - 8}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--tx)' opacity='.5'/><text x='{ml - 4}' y='{y(0) + 4:.1f}' text-anchor='end'>0%</text>"]
    for v in (-0.2, -0.4, -0.6, -0.8):
        if lo < v:
            g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(v) + 4:.1f}' text-anchor='end'>{v * 100:.0f}%</text>")
    for gg in range(0, int(xmax) + 1, 250):
        g.append(f"<text x='{x(gg):.1f}' y='{h - 6}' text-anchor='middle'>{gg / 250:.0f} {'anno' if gg == 250 else 'anni'}</text>" if gg else f"<text x='{x(0):.1f}' y='{h - 6}' text-anchor='middle'>massimo</text>")
    for i, c in enumerate(crisi):
        pts = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in c["traiettoria"])
        g.append(f"<polyline fill='none' stroke='{PAL[i % len(PAL)]}' stroke-width='2.2' stroke-linejoin='round' points='{pts}'><title>{_h.escape(c['nome'])}</title></polyline>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Come si sono mossi i mercati dopo il massimo, per crisi'>{''.join(g)}</svg>"


def stress_pagina(s: dict | None) -> str:
    if not s:
        return _shell("<h2>Stress test</h2><p class='mu'>Disponibile dopo il prossimo aggiornamento giornaliero.</p>")
    att = s["attese"]
    a3 = att.get("3m", {})
    h = ["<h2>Stress test: quanto potresti perdere</h2>",
         "<div class='card'><h3 style='margin:0 0 6px'>Il tuo portafoglio</h3><p class='small' style='margin:0 0 8px'>Scrivi quanto vale oggi il tuo VWCE: gli importi qui sotto si calcolano <b>sul tuo telefono</b> e non vengono inviati a nessuno.</p>"
         "<div class='stinput'><label>Valore del portafoglio (€)<input id='stval' type='number' min='1' step='100' inputmode='decimal' placeholder='es. 10000'></label>"
         "<button class='btn pri' id='stsave'>Calcola</button><button class='btn' id='stclear'>Cancella</button></div><p class='small' id='stmsg' style='margin:8px 0 0'></p></div>",
         f"<div class='hero w'><span class='small'>Simulazione sul VWCE in euro, al {s['attese_data'][8:]}/{s['attese_data'][5:7]}/{s['attese_data'][:4]}</span><b class='big'>In 3 mesi, in 4 casi su 5 il calo massimo non supera <span class='eurtot' data-p='{a3.get('calo_r80', 0):.4f}'>—</span> ({_pc(a3.get('calo_r80'), 1)})</b>"
         f"Nel caso peggiore (1 su 20) può arrivare a {_pc(a3.get('calo_r95'), 1)}. Il «calo massimo» è il punto più basso toccato lungo il percorso, non il risultato finale.</div>",
         "<p class='sub'>Chiave di lettura: la simulazione (la stessa delle previsioni di Armor, con la paura del mercato misurata dal VIX) prova 3.000 percorsi possibili. Non dice cosa succederà: dice quanto sarebbe grave un andamento sfavorevole, per sapere in anticipo se riusciresti a stare fermo.</p>",
         "<h3>I risultati possibili</h3><div class='card'>" + _ventaglio(att) +
         "<div class='legend'><span><i style='background:var(--ac);opacity:.3'></i>quasi tutti i casi (da 2 su 100 a 98 su 100)</span><span><i style='background:var(--ac);opacity:.6'></i>i casi tipici (da 1 su 4 a 3 su 4)</span><span><b>|</b> caso centrale</span><span><span style='color:var(--bad)'>●</span> perdita superata solo in 1 caso su 20</span></div></div>"]
    rows = ["<div class='card scroll' style='margin-top:10px'><table class='tb'><tr><th>Periodo</th><th>Calo massimo, metà dei casi</th><th>4 casi su 5</th><th>1 caso su 20</th><th>Perdita a fine periodo, 1 caso su 20</th><th>Perdita media nei 5 casi peggiori su 100</th><th>Probabilità di essere in perdita</th></tr>"]
    for k, nome in (("1m", "1 mese"), ("3m", "3 mesi"), ("1a", "1 anno")):
        a = att.get(k)
        if not a:
            continue
        cell = lambda p: f"{_pc(abs(p), 1)}<div class='small'><span class='eur' data-p='{abs(p):.4f}'>—</span></div>"
        rows.append(f"<tr><td><b>{nome}</b></td><td>{cell(a['calo_r50'])}</td><td>{cell(a['calo_r80'])}</td><td>{cell(a['calo_r95'])}</td><td>{cell(a['fine_q5'])}</td><td>{cell(a['es5'])}</td><td>{_pc(a['p_perdita'])}</td></tr>")
    rows.append("</table>")
    cov = s.get("copertura") or {}
    if cov:
        ok = all(v.get("ok95") for v in cov.values())
        det = "; ".join(f"a {n}: {_pc(cov[k]['oltre_r95'], 1)} dei casi (previsto 5%)" for k, n in (("1m", "1 mese"), ("3m", "3 mesi"), ("1a", "1 anno")) if k in cov)
        rows.append(f"<p class='small'><b>Prova sulla storia del VWCE in euro dal 2011:</b> {_badge('ok' if ok else 'warn', 'soglie rispettate' if ok else 'soglie non sempre rispettate')} Il calo massimo reale ha superato la soglia «1 caso su 20» {det}. "
                    "La soglia «4 casi su 5» è stata superata meno spesso del previsto: la simulazione tende a essere un po' prudente.</p>")
    rows.append("</div>")
    h.append("".join(rows))
    crisi = s["crisi"]
    h.append("<h3 style='margin-top:26px'>Le grandi crisi del passato</h3><p class='sub'>Che cosa sarebbe successo con il tuo portafoglio se una di queste crisi ricominciasse oggi dal massimo.</p>"
             "<div class='card'>" + _traiettorie(crisi) + "<div class='legend'>" + "".join(f"<span><i style='background:{PAL[i % len(PAL)]}'></i>{_h.escape(c['nome'])}</span>" for i, c in enumerate(crisi)) + "</div>"
             "<p class='small' style='margin:2px 0 0'>Ogni linea parte dal massimo prima della crisi e mostra il percorso nei 4 anni successivi.</p></div>")
    cards = []
    for c in crisi:
        anni = lambda g: "—" if g is None else (f"{g / 365.25:.1f} anni".replace(".", ",") if g > 400 else f"{g} giorni")
        rec = "non ancora recuperato" if c["recupero"] is None else f"recuperato dopo {anni(c['giorni_recupero'])}"
        pac1 = _sp(c["pac_al_minimo"], 0) if c["pac_al_minimo"] is not None else "n/d"
        pac2 = _sp(c["pac_3anni_dopo"], 0) if c["pac_3anni_dopo"] is not None else "n/d"
        cards.append(f"<div class='crisis'><h4>{_h.escape(c['nome'])}</h4><div class='big'>−{c['calo'] * 100:.0f}%</div><div class='small'>da {c['massimo'][:7]} a {c['minimo'][:7]}, {anni(c['giorni_al_minimo'])} per arrivare al minimo; {rec}.</div>"
                     f"<p style='margin:8px 0 4px;font-size:14px'>Sul tuo portafoglio: <span class='eur' data-p='{c['calo']:.4f}'>—</span> di perdita.</p>"
                     f"<p class='small' style='margin:0'>Con un piano di accumulo mensile partito dal massimo: {pac1} al minimo, {pac2} tre anni dopo il minimo (rispetto al versato).</p>"
                     f"<p class='small' style='margin:4px 0 0'>Serie: {_h.escape(c['serie_nome'])}.</p></div>")
    h.append("<div class='g4' style='margin-top:12px'>" + "".join(cards) + "</div>")
    h.append("<h3>Limiti, detti chiaramente</h3><div class='card'><ul class='small' style='margin:0;padding-left:18px;line-height:1.6'>"
             "<li>Per le crisi prima del 2008 si usa l'S&amp;P 500 (in dollari o convertito in euro): il VWCE non esisteva e il fondo mondiale ha un andamento simile ma non identico.</li>"
             "<li>Le crisi del passato non si ripetono uguali: la prossima può essere più lunga, più breve o diversa.</li>"
             "<li>Il piano di accumulo mensile è semplificato: nessun costo né tassa, rata alla stessa data ogni mese.</li>"
             "<li>Gli importi sono calcolati sul valore che scrivi tu e non sono salvati altrove. Non è un consiglio finanziario.</li></ul></div>")
    return _shell("".join(h) + STRESS_JS)
