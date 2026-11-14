# -*- coding: utf-8 -*-
"""Sezione «Minimi e lungo periodo»: radar dei minimi a 4 scale + fase di lungo periodo a 2-15 anni. Solo HTML/SVG (nessuno script), colori dalle variabili dell'app."""
import html as _h

import numpy as np
import pandas as pd

from . import minimi

CSS = """<style>
.mn h3{margin:26px 0 8px}.mn .sub{color:var(--mu);font-size:13px;margin:0 0 10px}
.mn .hero{border-radius:18px;padding:18px 20px;border:1px solid var(--bd);background:linear-gradient(135deg,var(--card),var(--okbg));margin-bottom:6px}
.mn .hero.w{background:linear-gradient(135deg,var(--card),var(--warnbg))}.mn .hero.b{background:linear-gradient(135deg,var(--card),var(--badbg))}
.mn .hero b.big{font-size:22px;display:block;margin:2px 0 4px}
.mn .g4{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:12px}
.mn .sc{border:1px solid var(--bd);border-radius:16px;padding:14px;background:var(--card)}
.mn .sc.ok{border-color:var(--ok);box-shadow:0 0 0 1px var(--ok) inset}.mn .sc.pw{border-color:var(--warn)}
.mn .sc h4{margin:0 0 2px;font-size:15px;display:flex;justify-content:space-between;gap:6px;align-items:center}
.mn .v{font-weight:700;font-size:17px;margin:6px 0 2px}.mn .v.ok{color:var(--ok)}.mn .v.pw{color:var(--warn)}.mn .v.no{color:var(--mu)}
.mn .small{font-size:12.5px;color:var(--mu);line-height:1.45}
.mn .bar{position:relative;height:12px;border-radius:7px;background:var(--bd);margin:10px 0 4px;overflow:visible}
.mn .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:7px;background:var(--ac)}
.mn .bar u{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--tx);opacity:.55}
.mn .tb{width:100%;border-collapse:collapse;font-size:13.5px}.mn .tb th,.mn .tb td{padding:7px 8px;border-bottom:1px solid var(--bd);text-align:left;vertical-align:middle}
.mn .tb th{font-size:12px;color:var(--mu);font-weight:600}
.mn svg{width:100%;height:auto;display:block}.mn svg text{fill:var(--mu);font-size:11px;font-family:inherit}
.mn .key{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:var(--mu);margin:6px 0}
.mn .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.mn .zones{display:flex;height:16px;border-radius:8px;overflow:hidden;margin:12px 0 4px}
.mn .zones span{display:block}
.mn .scroll{overflow-x:auto}
</style>"""

ETICH = {"verificata": ("ok", "verificata"), "parziale": ("warn", "parzialmente verificata"), "non verificata": ("bad", "non verificata")}
ETICH_LP = {"buona": ("ok", "buona"), "media": ("warn", "media"), "debole": ("bad", "debole")}
VER = {"probabile": ("ok", "Minimo probabile"), "possibile": ("pw", "Minimo possibile"), "non_ancora": ("no", "Non ancora")}
ANNI = {"2": "2 anni", "3": "3 anni", "5": "5 anni", "8": "8 anni", "10": "10 anni", "15": "15 anni"}


def _pc(x, d=0):
    return "n/d" if x is None else f"{x * 100:.{d}f}%".replace(".", ",")


def _sp(x, d=1):
    return "n/d" if x is None else f"{x * 100:+.{d}f}%".replace(".", ",")


def _badge(kind, txt):
    return f"<span class='badge {kind}'>{_h.escape(txt)}</span>"


# ------------------------------------------------------------------ minimi
def _fasce_txt(f):
    if not f:
        return ""
    a = next((x for x in f if x["fascia"] == "alta"), None)
    m = next((x for x in f if x["fascia"] == "media"), None)
    s = []
    if a and a["n"] >= 5:
        s.append(f"Quando la stima era alta (≥75%), il minimo ha tenuto davvero il {_pc(a['reale'])} delle volte ({a['n']} casi).")
    if m:
        s.append(f"Con stima media (55-75%): {_pc(m['reale'])} ({m['n']} casi).")
    return " ".join(s)


def _scheda(k, s):
    cls, vt = VER[s["verdetto"]]
    ek, et = ETICH.get(s["etichetta"], ETICH["non verificata"])
    q = s["q"]
    pos = "ok" if cls == "ok" else ("pw" if cls == "pw" else "")
    cand = (f"Il prezzo è a <b>{_pc(s['dal_minimo'], 1)}</b> sopra il minimo degli ultimi {s['nome']} ({s['minimo_data'][8:]}/{s['minimo_data'][5:7]}/{s['minimo_data'][:4]}).")
    cand += (" Rientra nella zona del minimo" + ("." if s["verdetto"] != "non_ancora" else ", ma la probabilità che tenga è ancora sotto il 55%.")) if s["candidato"] else f" Per essere «vicino al minimo» dovrebbe stare entro {_pc(s['tolleranza'])}."
    return (f"<div class='sc {pos}'><h4>{_h.escape(s['nome'])} {_badge(ek, et)}</h4>"
            f"<div class='v {cls}'>{vt}</div>"
            f"<div class='small'>Probabilità che da oggi il prezzo non scenda più del {_pc(s['tolleranza'])} sotto il livello attuale per {s['nome']}: <b>{_pc(q)}</b></div>"
            f"<div class='bar'><i style='width:{max(2, min(100, q * 100)):.0f}%'></i><u style='left:55%'></u><u style='left:75%'></u></div>"
            f"<div class='small' style='display:flex;justify-content:space-between'><span>0%</span><span>55% possibile</span><span>75% probabile</span></div>"
            f"<p class='small' style='margin:8px 0 4px'>{cand}</p>"
            f"<p class='small' style='margin:4px 0'>Se il minimo non tiene, il calo ulteriore in 1 caso su 2 è di circa <b>{_pc(s['r50'], 1)}</b>, in 4 su 5 fino a <b>{_pc(s['r80'], 1)}</b>, in 19 su 20 fino a <b>{_pc(s['r95'], 1)}</b>.</p>"
            f"<p class='small' style='margin:4px 0'>{_fasce_txt(s.get('fasce'))}</p></div>")


def _grafico_scala(p, marc, k, nome, anni=3.0):
    w, h, ml, mr, mt, mb = 760, 170, 8, 8, 10, 22
    s = p[p.index >= p.index[-1] - pd.Timedelta(days=int(365 * anni))]
    s = s.iloc[::2] if len(s) > 400 else s
    lo, hi = float(s.min()), float(s.max())
    x = lambda i: ml + (w - ml - mr) * i / max(len(s) - 1, 1)
    y = lambda v: mt + (h - mt - mb) * (1 - (v - lo) / max(hi - lo, 1e-9))
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s.values))
    area = f"{ml},{h - mb} {pts} {x(len(s) - 1):.1f},{h - mb}"
    idx = {d: i for i, d in enumerate(s.index)}
    mk = []
    for d, ver, e in marc.get(k, []):
        t = pd.Timestamp(d)
        pos = s.index.searchsorted(t)
        if pos >= len(s):
            continue
        cx, cy = x(pos), y(float(s.iloc[pos]))
        col = "var(--ok)" if ver == "probabile" else "var(--warn)"
        if e is None:
            mk.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='4.5' fill='none' stroke='{col}' stroke-width='2'/>")
        elif e == 1:
            mk.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='4.5' fill='{col}' stroke='var(--card)' stroke-width='1'/>")
        else:
            mk.append(f"<path d='M{cx - 4:.1f} {cy - 4:.1f}l8 8m0 -8l-8 8' stroke='var(--bad)' stroke-width='2' fill='none'/>")
    ticks = []
    for yr in sorted({d.year for d in s.index}):
        pos = s.index.searchsorted(pd.Timestamp(f"{yr}-01-01"))
        if 0 < pos < len(s):
            ticks.append(f"<text x='{x(pos):.1f}' y='{h - 6}' text-anchor='middle'>{yr}</text>")
    n = len(marc.get(k, []))
    return (
        f"<div class='card' style='margin-bottom:10px'><b>{_h.escape(nome)}</b> <span class='small'>· {n} segnali negli ultimi {int(anni)} anni</span>"
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Prezzo S&P 500 con i segnali di minimo a {nome}'>"
        f"<polygon points='{area}' fill='var(--ac)' opacity='.10'/><polyline points='{pts}' fill='none' stroke='var(--ac)' stroke-width='1.8' stroke-linejoin='round'/>"
        f"{''.join(mk)}{''.join(ticks)}<text x='{ml}' y='{mt + 9}'>{hi:.0f}</text><text x='{ml}' y='{h - mb - 3}'>{lo:.0f}</text></svg></div>")


def _riepilogo(o):
    prob = [s["nome"] for s in o["scale"].values() if s["verdetto"] == "probabile"]
    poss = [s["nome"] for s in o["scale"].values() if s["verdetto"] == "possibile"]
    if prob:
        return "", "Minimo probabile", f"Il mercato è vicino a un minimo a: {', '.join(prob)}." + (f" Possibile anche a: {', '.join(poss)}." if poss else "")
    if poss:
        return "w", "Minimo possibile", f"Segnale debole a: {', '.join(poss)}. Nessuna scala supera la soglia «probabile»."
    return "w", "Nessun minimo in vista", "Oggi nessuna delle 4 scale è in una zona di minimo con probabilità sufficiente: non c'è ancora un punto d'ingresso statistico per un versamento extra."


def _minimi_html(o, marc, p):
    k, t, d = _riepilogo(o)
    h = [f"<div class='hero {k}'><span class='small'>Dati al {o['data'][8:]}/{o['data'][5:7]}/{o['data'][:4]} · S&P 500 {o['prezzo']:.0f}</span><b class='big'>{t}</b>{d}</div>",
         "<p class='sub'>Chiave di lettura: «minimo» a una scala = il prezzo di oggi è vicino al più basso degli ultimi giorni di quella scala <i>e</i> nel periodo seguente non scende più di una piccola soglia. "
         "La probabilità viene dal modello FHS+VIX (lo stesso delle previsioni). L'etichetta dice se, guardando 36 anni di storia, quelle probabilità si sono rivelate vere.</p>",
         "<div class='g4'>" + "".join(_scheda(k2, s) for k2, s in o["scale"].items()) + "</div>"]
    if p is not None and marc:
        h.append("<h3>Dove il modello avrebbe segnalato un minimo (ultimi 3 anni)</h3>"
                 "<div class='key'><span><span class='dot' style='background:var(--ok)'></span>minimo probabile, ha tenuto</span><span><span class='dot' style='background:var(--warn)'></span>minimo possibile, ha tenuto</span>"
                 "<span><span style='color:var(--bad);font-weight:700'>✕</span> non ha tenuto</span><span><span class='dot' style='border:2px solid var(--ok);background:none'></span>esito non ancora noto</span></div>")
        for k2, s in o["scale"].items():
            h.append(_grafico_scala(p, marc, k2, s["nome"]))
    return "".join(h)


# ------------------------------------------------------------------ lungo periodo
def _range_chart(lp):
    rows = [(a, lp["orizzonti"][a]) for a in ANNI if a in lp["orizzonti"]]
    vals = [v for _, o in rows for v in (o["p10"], o["p90"], o["media_storica"]) if v is not None]
    lo, hi = min(min(vals), -0.03) - 0.01, max(vals) + 0.01
    w, rh, ml, mr = 760, 38, 70, 20
    H = rh * len(rows) + 30
    x = lambda v: ml + (w - ml - mr) * (v - lo) / (hi - lo)
    g = [f"<line x1='{x(0):.1f}' y1='6' x2='{x(0):.1f}' y2='{H - 22}' stroke='var(--bad)' stroke-width='1.5' stroke-dasharray='4 3'/><text x='{x(0):.1f}' y='{H - 8}' text-anchor='middle'>0% reale</text>"]
    step = 0.02 if hi - lo < 0.2 else 0.05
    v = np.ceil(lo / step) * step
    while v < hi:
        if abs(v) > 1e-9:
            g.append(f"<line x1='{x(v):.1f}' y1='6' x2='{x(v):.1f}' y2='{H - 22}' stroke='var(--bd)'/><text x='{x(v):.1f}' y='{H - 8}' text-anchor='middle'>{v * 100:+.0f}%</text>")
        v += step
    for i, (a, o) in enumerate(rows):
        cy = 10 + rh * i + rh / 2 - 4
        ek = ETICH_LP.get(o["etichetta"], ETICH_LP["debole"])[0]
        col = {"ok": "var(--ok)", "warn": "var(--warn)", "bad": "var(--mu)"}[ek]
        g.append(f"<text x='4' y='{cy + 4:.1f}' style='fill:var(--tx);font-weight:600;font-size:12.5px'>{ANNI[a]}</text>"
                 f"<rect x='{x(o['p10']):.1f}' y='{cy - 8:.1f}' width='{x(o['p90']) - x(o['p10']):.1f}' height='16' rx='8' fill='{col}' opacity='.28'/>"
                 f"<rect x='{x(o['p10']):.1f}' y='{cy - 8:.1f}' width='{x(o['p90']) - x(o['p10']):.1f}' height='16' rx='8' fill='none' stroke='{col}' stroke-width='1.2'/>"
                 f"<line x1='{x(o['p50']):.1f}' y1='{cy - 11:.1f}' x2='{x(o['p50']):.1f}' y2='{cy + 11:.1f}' stroke='var(--tx)' stroke-width='3' stroke-linecap='round'/>"
                 f"<circle cx='{x(o['media_storica']):.1f}' cy='{cy:.1f}' r='3.5' fill='var(--card)' stroke='var(--mu)' stroke-width='1.6'/>")
    return f"<svg viewBox='0 0 {w} {H}' role='img' aria-label='Fascia del rendimento reale annuo per orizzonte'>{''.join(g)}</svg>"


def _scatter(lp):
    d = lp.get("dispersione10")
    if not d:
        return ""
    pts = d["punti"]
    w, h, ml, mb = 760, 300, 40, 26
    xs = [p[0] for p in pts] + [lp["cape_oggi"]]
    ys = [p[1] for p in pts]
    xlo, xhi = 4, max(xs) + 2
    ylo, yhi = min(ys) - 0.01, max(ys) + 0.01
    x = lambda v: ml + (w - ml - 10) * (v - xlo) / (xhi - xlo)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - ylo) / (yhi - ylo))
    g = [f"<line x1='{ml}' x2='{w - 10}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--bad)' stroke-dasharray='4 3'/><text x='{ml - 4}' y='{y(0) + 4:.1f}' text-anchor='end'>0%</text>"]
    for v in range(10, int(xhi), 10):
        g.append(f"<line x1='{x(v):.1f}' x2='{x(v):.1f}' y1='8' y2='{h - mb}' stroke='var(--bd)'/><text x='{x(v):.1f}' y='{h - 8}' text-anchor='middle'>CAPE {v}</text>")
    for v in (0.05, 0.10, 0.15):
        if ylo < v < yhi:
            g.append(f"<line x1='{ml}' x2='{w - 10}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(v) + 4:.1f}' text-anchor='end'>{v * 100:.0f}%</text>")
    for c, r, yr in pts:
        col = "var(--bad)" if r < 0 else "var(--ac)"
        g.append(f"<circle cx='{x(c):.1f}' cy='{y(r):.1f}' r='3' fill='{col}' opacity='.55'><title>Partenza {yr}: {r * 100:+.1f}% reale annuo</title></circle>")
    a, b = d["a"], d["b"]
    x1, x2 = xlo + 1, xhi - 1
    g.append(f"<line x1='{x(x1):.1f}' y1='{y(a + b * np.log(x1)):.1f}' x2='{x(x2):.1f}' y2='{y(a + b * np.log(x2)):.1f}' stroke='var(--tx)' stroke-width='2' opacity='.8'/>")
    yo = lp["orizzonti"]["10"]["atteso"]
    g.append(f"<line x1='{x(lp['cape_oggi']):.1f}' x2='{x(lp['cape_oggi']):.1f}' y1='8' y2='{h - mb}' stroke='var(--warn)' stroke-width='1.5'/>"
             f"<circle cx='{x(lp['cape_oggi']):.1f}' cy='{y(yo):.1f}' r='7' fill='var(--warn)' stroke='var(--card)' stroke-width='2'/>"
             f"<text x='{x(lp['cape_oggi']) - 10:.1f}' y='{y(yo) - 12:.1f}' text-anchor='end' style='fill:var(--tx);font-weight:700'>Oggi: CAPE {lp['cape_oggi']:.0f}</text>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Valutazioni di partenza e rendimento reale a 10 anni'>{''.join(g)}</svg>"


def _barre10(lp):
    rows = lp.get("rendimento10_per_anno") or []
    if not rows:
        return ""
    w, h, ml, mb = 760, 220, 40, 24
    vals = [r[1] for r in rows]
    lo, hi = min(vals + [-0.02]), max(vals)
    y = lambda v: 8 + (h - 8 - mb) * (1 - (v - lo) / (hi - lo))
    n = len(rows)
    bw = (w - ml - 10) / n
    g = [f"<line x1='{ml}' x2='{w - 10}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--tx)' opacity='.5'/><text x='{ml - 4}' y='{y(0) + 4:.1f}' text-anchor='end'>0%</text>"]
    for v in (0.05, 0.10):
        if v < hi:
            g.append(f"<line x1='{ml}' x2='{w - 10}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(v) + 4:.1f}' text-anchor='end'>{v * 100:.0f}%</text>")
    for i, (d, v) in enumerate(rows):
        x0 = ml + i * bw
        top, bot = (y(v), y(0)) if v >= 0 else (y(0), y(v))
        g.append(f"<rect x='{x0:.1f}' y='{top:.1f}' width='{max(bw - 0.4, 0.6):.2f}' height='{max(bot - top, .6):.1f}' fill='{'var(--ac)' if v >= 0 else 'var(--bad)'}'><title>Partenza {d}: {v * 100:+.1f}% reale annuo nei 10 anni dopo</title></rect>")
    last = None
    for i, (d, v) in enumerate(rows):
        dec = int(d[:4]) // 20 * 20
        if dec != last and int(d[:4]) % 20 < 6:
            g.append(f"<text x='{ml + i * bw:.1f}' y='{h - 6}'>{dec}</text>")
            last = dec
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Rendimento reale a 10 anni per anno di partenza'>{''.join(g)}</svg>"


def _lungo_html(lp):
    if not lp:
        return "<p class='mu'>Il modello di lungo periodo sarà disponibile dopo il prossimo aggiornamento giornaliero.</p>"
    f = lp["fase"]
    cls = {"sana": "", "cara": "w", "contrazione": "b"}[f["codice"]]
    o10 = lp["orizzonti"]["10"]
    desc = {"sana": "Le valutazioni sono nella norma o basse: storicamente i rendimenti dei 10 anni successivi sono stati buoni.",
            "cara": "Le valutazioni sono alte: storicamente i rendimenti dei 10 anni successivi sono stati più bassi della media.",
            "contrazione": "Le valutazioni sono tra le più alte mai viste: storicamente i 10-15 anni successivi hanno reso molto meno della media e a volte hanno perso contro l'inflazione."}[f["codice"]]
    pr = lp.get("prova_fasi") or {}
    h = [f"<div class='hero {cls}'><span class='small'>Fase del mercato a lungo termine · CAPE {lp['cape_oggi']:.1f} · dati storici fino a {lp['dati_fino_a']}</span>"
         f"<b class='big'>{_h.escape(f['nome'])}</b>{desc}"
         f"<div class='small' style='margin-top:8px'>Atteso a 10 anni: <b>{_sp(o10['atteso'])}</b> reale all'anno (fascia 10%-90%: {_sp(o10['p10'])} … {_sp(o10['p90'])}) · probabilità di perdere contro l'inflazione: <b>{_pc(o10['p_perdita'])}</b></div></div>",
         "<p class='sub'>Chiave di lettura: «CAPE» = prezzo dell'indice diviso gli utili medi degli ultimi 10 anni (corretti per l'inflazione): misura quanto il mercato è «caro». «Reale» = al netto dell'inflazione, con dividendi reinvestiti. Si usa lo S&P 500 perché ha la storia più lunga (dal 1871).</p>"]
    # termometro CAPE
    cp = lp["cape_percentili"]
    pcent = f["percentile"] * 100
    h.append("<h3>Quanto è «caro» il mercato rispetto alla sua storia</h3><div class='card'>"
             "<div class='zones'><span style='width:60%;background:var(--ok);opacity:.55'></span><span style='width:25%;background:var(--warn);opacity:.65'></span><span style='width:15%;background:var(--bad);opacity:.65'></span></div>"
             f"<div style='position:relative;height:22px'><span style='position:absolute;left:{min(pcent, 99):.1f}%;transform:translateX(-50%);font-size:18px;line-height:1'>▲</span></div>"
             f"<div class='small' style='display:flex;justify-content:space-between'><span>Sana (sotto il 60° percentile)</span><span>Cara (60°-85°)</span><span>Rischio (sopra l'85°)</span></div>"
             f"<p style='margin:10px 0 0'>Oggi il CAPE è <b>{lp['cape_oggi']:.1f}</b>: più alto del <b>{pcent:.1f}%</b> di tutti i mesi dal 1881. Mediana storica {cp['0.5']:.1f}, soglia «cara» {cp['0.75']:.1f}, soglia «rischio» {cp['0.85']:.1f}.</p></div>")
    # fasce per orizzonte
    h.append("<h3>Quanto ci si può aspettare a 2, 3, 5, 8, 10, 15 anni</h3><div class='card'>"
             "<div class='key'><span><span class='dot' style='background:var(--ac);opacity:.5'></span>fascia 10%-90% del rendimento reale annuo</span><span><b>|</b> valore centrale</span><span><span class='dot' style='border:2px solid var(--mu);background:none'></span>media storica di sempre</span></div>"
             + _range_chart(lp) + "</div>")
    tb = ["<div class='card scroll' style='margin-top:10px'><table class='tb'><tr><th>Orizzonte</th><th>Atteso (reale/anno)</th><th>Fascia 10%-90%</th><th>Perdere contro l'inflazione</th><th>Media storica</th><th>Quanto è affidabile</th></tr>"]
    for a in ANNI:
        o = lp["orizzonti"].get(a)
        if not o:
            continue
        ek, et = ETICH_LP.get(o["etichetta"], ETICH_LP["debole"])
        tb.append(f"<tr><td><b>{ANNI[a]}</b></td><td>{_sp(o['atteso'])}</td><td>{_sp(o['p10'])} … {_sp(o['p90'])}</td><td>{_pc(o['p_perdita'])}</td><td>{_sp(o['media_storica'])}</td>"
                  f"<td>{_badge(ek, et)}<div class='small'>R² {o['r2'] if o['r2'] is not None else 'n/d'}</div></td></tr>")
    tb.append("</table><p class='small'>Affidabilità: «buona» = il CAPE ha aiutato a prevedere sia prima sia dopo il 1970; «media» = ha aiutato in entrambe le metà; «debole» = non ha aiutato in modo stabile. "
              "R² = quanto la previsione batte la semplice media storica (0 = per niente, 1 = perfetta; negativo = peggio della media).</p></div>")
    h.append("".join(tb))
    h.append("<h3>Valutazioni di partenza e che cosa è successo dopo (10 anni)</h3><div class='card'><p class='sub'>Ogni punto è un mese di partenza: a sinistra mercato «economico», a destra «caro»; in alto rendimento reale annuo nei 10 anni dopo. I punti rossi sono decenni persi contro l'inflazione.</p>"
             + _scatter(lp) + "</div>")
    h.append("<h3>I «decenni perduti» della storia</h3><div class='card'>" + _barre10(lp) +
             "<p class='small'>Ogni barra = chi ha investito in quel periodo: rendimento reale annuo dei 10 anni successivi. Rosso = ha perso potere d'acquisto.</p>")
    dp = lp.get("decenni_perduti") or []
    if dp:
        h.append("<p style='margin:6px 0 0'>Periodi di partenza con 10 anni negativi: " + ", ".join(f"<b>{x['da']} – {x['a']}</b> (peggiore {_sp(x['peggiore'])})" for x in dp) + ".</p>")
    h.append("</div>")
    sim = lp.get("anni_simili") or []
    if sim:
        h.append("<h3>Quando le valutazioni erano simili a oggi</h3><div class='card scroll'><table class='tb'><tr><th>Periodo</th><th>CAPE massimo</th><th>Picco</th><th>Dopo 5 anni</th><th>Dopo 10 anni</th><th>Dopo 15 anni</th></tr>"
                 + "".join(f"<tr><td>{x['da']} → {x['a']}</td><td>{x['cape_max']:.1f}</td><td>{x['picco']}</td><td>{_sp(x['r5'])}</td><td>{_sp(x['r10'])}</td><td>{_sp(x['r15'])}</td></tr>" for x in sim)
                 + "</table><p class='small'>Mediana del rendimento reale annuo partendo da mesi con CAPE entro ±25% da quello di oggi. Pochi episodi indipendenti: è un confronto storico, non una previsione.</p></div>")
    h.append(_cosa_cambia(lp, f))
    return "".join(h)


def _cosa_cambia(lp, f):
    pf = lp.get("prova_fasi") or {}
    sup = pf.get("superata")
    txt = {"sana": "Fase favorevole: il piano di accumulo costante funziona bene; i minimi sono un di più.",
           "cara": "Fase da osservare: i versamenti costanti restano utili, ma conviene dare più peso alle occasioni di calo vere (minimi verificati) rispetto ai versamenti extra «a caso».",
           "contrazione": "Fase di cautela: i rendimenti attesi a 10-15 anni sono bassi. Il versamento costante resta il pilastro (compra anche quando i prezzi scendono), ma i versamenti extra hanno più senso solo su minimi probabili e dopo cali profondi, non sui piccoli ribassi."}[f["codice"]]
    prova = ("La prova fatta sulla storia lo conferma: nelle fasi di rischio il rendimento a 10 anni è stato più basso che nelle fasi sane, in entrambe le metà del periodo." if sup
             else "Attenzione: la prova sulle fasi non è superata in modo netto in tutte e due le metà della storia; la fase è un'indicazione, non una regola.")
    return f"<h3>Che cosa cambia per il tuo piano</h3><div class='card'><p style='margin:0 0 6px'>{txt}</p><p class='small' style='margin:0'>{prova} La decisione su quanto versare in più resta tua.</p></div>"


def _limiti(lp, o):
    return ("<h3>Limiti, detti chiaramente</h3><div class='card'><ul class='small' style='margin:0;padding-left:18px;line-height:1.6'>"
            "<li>Tutto si basa sullo S&amp;P 500, non sull'indice mondiale di VWCE: la storia lunga esiste solo per quello americano.</li>"
            "<li>I minimi sono stimati, non previsti: anche una stima «alta» sbaglia circa una volta su cinque. La probabilità reale per fascia è scritta in ogni scheda.</li>"
            "<li>A lungo periodo i casi davvero indipendenti sono pochi (circa 15 decenni di storia): le fasce sono più strette di quanto la realtà abbia fatto vedere, quindi vanno lette come un ordine di grandezza.</li>"
            "<li>Dopo il 1970 il CAPE spiega poco i rendimenti a 8 anni o meno; a 10-15 anni aiuta di più ma non in modo netto. Oggi il CAPE è fuori dalla maggior parte dei dati storici.</li>"
            "<li>Non è un consiglio finanziario. I numeri non cambiano dopo aver visto i risultati (regole scritte in PROTOCOLLO_MINIMI.md).</li></ul></div>")


# ------------------------------------------------------------------ radar in euro, ribasso, altri mercati, pagella
def _euro_html(o, v):
    if not o:
        return "<p class='mu'>Il radar in euro sarà disponibile dopo il prossimo aggiornamento giornaliero.</p>"
    k, t, d = _riepilogo(o)
    return (f"<div class='hero {k}'><span class='small'>Dati al {o['data'][8:]}/{o['data'][5:7]}/{o['data'][:4]} · VWCE in euro (storia: VT convertito in euro fino a luglio 2019, poi VWCE reale)</span><b class='big'>{t}</b>{d}</div>"
            "<p class='sub'>Stessi metodi e stesse soglie del radar principale, ma sul prezzo che conta per te: quello in euro, con il cambio. La storia è più corta (circa 18 anni): meno casi, quindi più prudenza nell'etichetta.</p>"
            "<div class='g4'>" + "".join(_scheda(k2, s) for k2, s in o["scale"].items()) + "</div>")


def _ribasso_chart(r):
    pts = r["storia"]
    w, h, ml, mt, mb = 760, 230, 40, 8, 22
    ymax = max(0.6, max(x[1] for x in pts))
    n = len(pts)
    x = lambda i: ml + (w - ml - 8) * i / max(n - 1, 1)
    y = lambda v: mt + (h - mt - mb) * v / ymax
    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(pts))
    g = []
    for lim, nome in ((0.10, "10%"), (0.20, "20%"), (0.30, "30%"), (0.50, "50%")):
        if lim < ymax:
            g.append(f"<line x1='{ml}' x2='{w - 8}' y1='{y(lim):.1f}' y2='{y(lim):.1f}' stroke='var(--bd)'/><text x='{ml - 4}' y='{y(lim) + 4:.1f}' text-anchor='end'>-{nome}</text>")
    for yr in range(1930, 2030, 10):
        i = next((j for j, (d, _) in enumerate(pts) if d >= f"{yr}-01-01"), None)
        if i is not None:
            g.append(f"<text x='{x(i):.1f}' y='{h - 6}' text-anchor='middle'>{yr}</text>")
    oggi = r["dal_massimo"]
    g.append(f"<polygon points='{ml},{mt} {line} {x(n - 1):.1f},{mt}' fill='var(--bad)' opacity='.22'/><polyline points='{line}' fill='none' stroke='var(--bad)' stroke-width='1.2'/>"
             f"<circle cx='{x(n - 1):.1f}' cy='{y(oggi):.1f}' r='5' fill='var(--warn)' stroke='var(--card)' stroke-width='2'/>")
    return f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Distanza dal massimo storico dello S&P 500 dal 1928'>{''.join(g)}</svg>"


def _ribasso_html(r):
    if not r:
        return "<p class='mu'>Disponibile dopo il prossimo aggiornamento giornaliero.</p>"
    cur = r["fascia"]
    cls = {"vicino ai massimi": "", "calo normale": "w", "correzione": "w", "mercato orso": "b", "crisi": "b"}[cur]
    h = [f"<div class='hero {cls}'><span class='small'>Distanza dal massimo storico dello S&amp;P 500 (massimo del {r['data_massimo'][8:]}/{r['data_massimo'][5:7]}/{r['data_massimo'][:4]}, {r['giorni_dal_massimo']} giorni fa)</span>"
         f"<b class='big'>{_h.escape(cur.capitalize())}: {r['dal_massimo'] * 100:.1f}% sotto il massimo</b>"
         "Il tipo di ribasso conta: dopo un calo normale il mercato di solito riparte; dopo un mercato orso i minimi si costruiscono con più calma. La tabella mostra che cosa è successo davvero dal 1928, partendo da ogni livello.</div>"]
    h.append("<div class='card'>" + _ribasso_chart(r) + "<p class='small' style='margin:4px 0 0'>Ogni punto è una settimana: quanto il mercato era sotto il suo massimo di sempre. Il pallino arancione è oggi.</p></div>")
    rows = ["<div class='card scroll' style='margin-top:10px'><table class='tb'><tr><th>Dove siamo</th><th>Giorni nella storia</th><th>Calo ulteriore in 3 mesi (metà dei casi / 4 su 5)</th><th>Calo ulteriore in 1 anno (metà / 4 su 5)</th><th>Casi con altro calo oltre 10%</th><th>Rendimento mediano a 1 anno</th></tr>"]
    for f in r["fasce"]:
        on = f["fascia"] == cur
        st = " style='background:var(--warnbg);font-weight:600'" if on else ""
        rows.append(f"<tr{st}><td>{'▶ ' if on else ''}{_h.escape(f['fascia'])} <span class='small'>({f['da'] * 100:.0f}-{min(f['a'], 1) * 100:.0f}%)</span></td><td>{f['giorni']} <span class='small'>({f['episodi']} episodi)</span></td>"
                    f"<td>{_pc(f['calo63_med'], 1)} / {_pc(f['calo63_80'], 1)}</td><td>{_pc(f['calo252_med'], 1)} / {_pc(f['calo252_80'], 1)}</td><td>{_pc(f['p_oltre10'])}</td><td>{_sp(f['rend12_med'])}</td></tr>")
    rows.append("</table><p class='small'>Chiave di lettura: «calo ulteriore» = di quanto scende ancora il prezzo, al punto più basso, dopo quel giorno. Giorni vicini si assomigliano: gli episodi indipendenti sono molto meno dei giorni. È un contesto storico, non una previsione.</p></div>")
    h.append("".join(rows))
    return "".join(h)


def _altri_html(r):
    am = (r or {}).get("altri_mercati") or []
    if not am:
        return ""
    rows = ["<div class='card scroll'><table class='tb'><tr><th>Mercato</th><th>Calo massimo dal picco</th><th>Periodo più lungo sotto il massimo precedente</th><th>Oggi</th></tr>"]
    for m in am:
        lung = f"{m['anni_piu_lungo']:.1f} anni ({m['da']} → {m['a']})".replace(".", ",") if m["anni_piu_lungo"] is not None else "n/d"
        oggi = "ai massimi" if (m["dal_massimo_oggi"] or 0) < 0.005 else f"{m['dal_massimo_oggi'] * 100:.1f}% sotto il massimo".replace(".", ",")
        rows.append(f"<tr><td><b>{_h.escape(m['nome'])}</b><div class='small'>dati dal {m['inizio_dati']}</div></td><td>{_pc(m['calo_max'])}</td><td>{lung}</td><td>{oggi}</td></tr>")
    rows.append("</table><p class='small'>Indici di prezzo (senza dividendi), in valuta locale. Serve a ricordare che un «decennio perduto» non è solo americano: il Giappone ha impiegato decenni a tornare sui massimi del 1989.</p></div>")
    return "".join(rows)


def _pagella_html(pg):
    if not pg or not pg.get("inizio"):
        return ("<p class='mu'>Il registro parte dal prossimo aggiornamento giornaliero: da quel giorno l'app salva ogni verdetto e, quando passa il tempo, scrive se il minimo ha tenuto davvero.</p>")
    ini = pg["inizio"]
    ser = pg["serie"].get("usd", {})
    rows = ["<div class='card scroll'><table class='tb'><tr><th>Scala</th><th>Oggi</th><th>«Minimo probabile» dati</th><th>Esiti già noti</th><th>Il minimo ha tenuto</th><th>«Minimo possibile» dati</th><th>Esiti noti / tenuto</th></tr>"]
    for k, s in ser.items():
        pr, po = s["verdetti"]["probabile"], s["verdetti"]["possibile"]
        ult = VER.get(s["ultimo"], ("no", "n/d"))[1] if s["ultimo"] else "n/d"
        ten = lambda x: ("in attesa" if not x["maturi"] else (f"{_pc(x['tenuto'])} su {x['maturi']}" if x["maturi"] >= 30 else f"{_pc(x['tenuto'])} su {x['maturi']} (pochi casi)"))
        rows.append(f"<tr><td><b>{_h.escape(s['nome'])}</b></td><td>{ult}</td><td>{pr['n']}</td><td>{pr['maturi']}</td><td>{ten(pr)}</td><td>{po['n']}</td><td>{po['maturi']} · {ten(po)}</td></tr>")
    rows.append(f"</table><p class='small'>Registro attivo dal {ini[8:]}/{ini[5:7]}/{ini[:4]} ({pg['giorni']} {'giorno' if pg['giorni'] == 1 else 'giorni'}). Nulla è ricostruito col senno di poi: sono i verdetti dati il giorno stesso. "
                "Un esito è noto quando sono passate tutte le sedute della scala (5, 21, 63, 252). Con meno di 30 casi il risultato non dice ancora niente di affidabile.</p></div>")
    return "".join(rows)


def _nota_tassi(lp):
    if not lp:
        return ""
    bs = [(h, o["variante_b"]) for h, o in lp["orizzonti"].items() if isinstance(o.get("variante_b"), dict) and "delta_prima" in o["variante_b"]]
    if not bs:
        return ""
    ad = [h for h, b in bs if b["adottata"]]
    tr = lp.get("tasso_reale_oggi")
    tr_t = (" Oggi il tasso a 10 anni supera l'inflazione di circa " + f"{tr * 100:.1f}".replace(".", ",") + "%.") if tr is not None else ""
    if ad:
        txt = "Aggiungere il tasso reale (tasso a 10 anni meno inflazione) ha migliorato la previsione a " + ", ".join(f"{h} anni" for h in ad) + ": per quegli orizzonti si usa il modello con i tassi."
    else:
        txt = "Abbiamo provato ad aggiungere il tasso reale (tasso a 10 anni meno inflazione) al CAPE: a 5, 8, 10 e 15 anni non ha migliorato la previsione in modo stabile nelle due metà della storia, quindi resta il solo CAPE."
    return f"<div class='card' style='margin-top:10px'><p class='small' style='margin:0'><b>Prova con i tassi.</b> {txt}{tr_t}</p></div>"


def html(o: dict | None, p: pd.Series | None = None, lp: dict | None = None, marc: dict | None = None, extra: dict | None = None) -> str:
    extra = extra or {}
    if o is None:
        mi = "<p class='mu'>I minimi saranno disponibili dopo il prossimo aggiornamento giornaliero.</p>"
    else:
        if marc is None and p is not None:
            try:
                marc = minimi.marcatori(p)
            except Exception:  # noqa: BLE001
                marc = {}
        mi = _minimi_html(o, marc or {}, p)
    top = extra.get("cosa_oggi", "")
    return (CSS + "<div class='mn'><h2>Minimi e lungo periodo</h2>" + top +
            "<p class='sub'>Due domande per chi versa ogni mese: <b>il mercato è vicino a un minimo?</b> (1 settimana, 1 mese, 3 mesi, 1 anno) e <b>in che fase di lungo periodo siamo?</b> (2-15 anni).</p>"
            "<h2 style='margin-top:18px'>1 · Radar dei minimi (S&amp;P 500)</h2>" + mi +
            "<h2 style='margin-top:34px'>2 · Radar in euro (VWCE)</h2>" + _euro_html(extra.get("eur"), None) +
            "<h2 style='margin-top:34px'>3 · Che tipo di ribasso è?</h2>" + _ribasso_html(extra.get("ribasso")) +
            "<h2 style='margin-top:34px'>4 · Mercato a lungo termine</h2>" + _lungo_html(lp) + _nota_tassi(lp) +
            "<h3>Non solo l'America: quanto tempo sotto i massimi</h3>" + (_altri_html(extra.get("ribasso")) or "<p class='mu'>Disponibile dopo il prossimo aggiornamento.</p>") +
            "<h2 style='margin-top:34px'>5 · Pagella in tempo reale</h2><p class='sub'>I segnali dati davvero giorno per giorno e se si sono rivelati giusti: la prova più onesta, perché non può essere ritoccata dopo.</p>" + _pagella_html(extra.get("pagella")) +
            _limiti(lp, o) + "</div>")
