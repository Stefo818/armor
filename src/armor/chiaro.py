"""Versioni semplici e visive di previsioni, segnali, stress e volatilità, con probabilità di calo E di rialzo."""
import html as _h

import numpy as np

from .config import HZ_LABEL, PRIMARY
from .outlook import SCEN_NAMES

e = _h.escape
SCEN_COL = ["#c0392b", "#e08a7e", "#9aa5b4", "#7fcf9f", "#1f8f55"]


def P(x, d=0):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%".replace(".", ",")


def S(x, d=1):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%".replace(".", ",")


def bar(p, base, color):
    """Barra orizzontale: la probabilità di oggi, con un segno dove sta la frequenza normale."""
    w = min(max(p * 100, 0), 100)
    b = min(max(base * 100, 0), 100)
    return (f"<div class='pb'><i style='width:{w:.1f}%;background:{color}'></i><u style='left:{b:.1f}%' title='normale {P(base)}'></u></div>")


def stacked(pr, base=None):
    segs = "".join(f"<i style='width:{max(x, 0) * 100:.1f}%;background:{SCEN_COL[k]}' title='{e(SCEN_NAMES[k])}: {P(x)}'></i>" for k, x in enumerate(pr) if x == x)
    return f"<div class='stk'>{segs}</div>"


def verdict_words(pd_, pu):
    if pu is None:
        return ("neutro", "")
    if max(pd_, pu) < 0.12:
        return ("ok", "Nessun movimento forte è probabile: scenario <b>tranquillo</b>.")
    if pd_ > pu * 1.25:
        return ("bad", "Oggi è più probabile un <b>calo</b> che un rialzo.")
    if pu > pd_ * 1.25:
        return ("ok", "Oggi è più probabile un <b>rialzo</b> che un calo.")
    return ("warn", "Calo e rialzo sono <b>quasi ugualmente probabili</b>.")


def horizon_simple(hz, r, mat_hz, spot, rel, old_card_html):
    prim = PRIMARY[hz]
    pdn, bdn = r["p"][prim], r["base"][prim]
    try:
        up = mat_hz["up"][prim]
        pup, bup = up["p"], up["base"]
    except Exception:  # noqa: BLE001
        pup = bup = None
    cls, words = verdict_words(pdn, pup)
    lev = {"Basso": ("ok", "Rischio basso"), "Normale": ("ok", "Rischio nella norma"), "Elevato": ("warn", "Rischio elevato"), "Alto": ("bad", "Rischio alto")}[r["level"]]
    rows = (f"<div class='pr'><div class='pl'>Scendere di almeno {prim}%</div><div class='pn'>{P(pdn)}</div>{bar(pdn, bdn, 'var(--bad)')}"
            f"<div class='pt'>Su 100 situazioni come questa, circa <b>{round(pdn * 100)}</b> vedono un calo così (di solito {round(bdn * 100)}).</div></div>")
    if pup is not None:
        rows += (f"<div class='pr'><div class='pl'>Salire di almeno {prim}%</div><div class='pn'>{P(pup)}</div>{bar(pup, bup, 'var(--ok)')}"
                 f"<div class='pt'>Su 100 situazioni come questa, circa <b>{round(pup * 100)}</b> vedono un rialzo così (di solito {round(bup * 100)}).</div></div>")
    ret = r.get("ret")
    typ = ""
    if ret:
        typ = (f"<div class='sc3'><div><span>Caso brutto</span><b class='dn'>{S(ret['q10'])}</b></div><div><span>Caso tipico</span><b>{S(ret['q50'])}</b></div>"
               f"<div><span>Caso buono</span><b class='up'>{S(ret['q90'])}</b></div></div><div class='mu'>Cosa è successo dopo in passato in situazioni simili (8 volte su 10 il risultato è stato tra il caso brutto e il buono).</div>")
    relw = ""
    if rel:
        relw = {"Utile": "<span class='badge ok'>Stima affidabile nei test</span>", "Debole": "<span class='badge warn'>Stima debole: usala solo come indizio</span>",
                "Non affidabile": "<span class='badge bad'>Stima poco affidabile</span>"}[rel[0]]
    return (f"<div class='card hz2'><div class='hzh'><h3>{HZ_LABEL[hz]}</h3><span class='badge {lev[0]}'>{lev[1]}</span></div>"
            f"<div class='vd {cls}'>{words}</div>{rows}{typ}<div style='margin-top:8px'>{relw}</div>"
            f"<details><summary>Più dettagli (altre soglie, perché, affidabilità)</summary><div class='old'>{old_card_html}</div></details></div>")


PREV_INTRO = ("<div class='explain'><p><b>Come leggere.</b> Ogni scheda guarda un periodo (10 giorni, 1 mese…) e risponde: <i>«quanto è probabile che il mercato scenda, e quanto che salga?»</i></p>"
              "<p>La <b>barra</b> mostra la probabilità di oggi; il piccolo segno verticale sulla barra è la probabilità <b>normale</b> (la media storica). "
              "Se la barra del calo supera il segno, oggi il rischio è sopra il normale. «Su 100 situazioni come questa» significa: se oggi si ripetesse 100 volte, circa quel numero andrebbe così. "
              "Non è una promessa: è una frequenza basata sul passato.</p></div>")


# ---------------------------------------------------------------- indicatori
def signals_simple(sigs):
    if not sigs:
        return "<p class='mu'>Dati non sufficienti.</p>"
    order = {"negativo": 0, "neutro": 1, "positivo": 2}
    nn = sum(1 for s in sigs if s["verdict"] == "negativo")
    npz = sum(1 for s in sigs if s["verdict"] == "positivo")
    head = (f"<div class='sumline'><span class='badge bad'>{nn} di prudenza</span> <span class='badge warn'>{len(sigs) - nn - npz} senza segnale chiaro</span> "
            f"<span class='badge ok'>{npz} favorevoli</span></div>")
    out = []
    for s in sorted(sigs, key=lambda s: (order[s["verdict"]], -s["ratio"])):
        cls = {"negativo": "bad", "positivo": "ok", "neutro": "warn"}[s["verdict"]]
        word = {"negativo": "Prudenza", "positivo": "Favorevole", "neutro": "Nessun segnale chiaro"}[s["verdict"]]
        out.append(f"<div class='sg {cls}' data-chart='{e(s['key'])}'><div class='sgh'><b>{e(s['name'])}</b><span class='badge {cls}'>{word}</span></div>"
                   f"<div class='mu'>Oggi vale {_num(s['now'])} (più alto del {s['pct']:.0f}% dei giorni passati)</div>"
                   f"<div class='sgb'><div><span>Calo oltre 10%</span>{bar(s['freq_dd10'], s['base_dd10'], 'var(--bad)')}<b>{P(s['freq_dd10'])}</b> <i>normale {P(s['base_dd10'])}</i></div>"
                   f"<div><span>Rialzo oltre 10%</span>{bar(s['up10'], s['base_up10'], 'var(--ok)')}<b>{P(s['up10'])}</b> <i>normale {P(s['base_up10'])}</i></div></div></div>")
    intro = ("<div class='explain'><p><b>Come leggere.</b> Per ogni indicatore ho cercato tutte le volte in cui valeva come oggi e ho contato cosa ha fatto l'S&amp;P 500 nei <b>3 mesi dopo</b>. "
             "Le barre dicono in quanti casi su 100 c'è stato un calo (rosso) o un rialzo (verde) di almeno 10%; il segno verticale è la frequenza normale. "
             "«Prudenza» = i cali sono stati molto più frequenti del normale. «Favorevole» = molto meno. Tocca una scheda per vedere il grafico.</p></div>")
    return intro + head + "<div class='sggrid'>" + "".join(out) + "</div>"


def _num(x):
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s[:-3] if s.endswith(",00") else s


def scenarios_html(sigs):
    """Sezione finale: tutti gli indicatori della tabella, casi simili del passato e scenari con probabilità."""
    sg = [s for s in sigs if s.get("scen") and s["scen"][0] == s["scen"][0]]
    if not sg:
        return ""

    def pool(sel):
        if not sel:
            return None
        return [float(np.mean([s["scen"][k] for s in sel])) for k in range(5)]
    allp = pool(sg)
    neg = pool([s for s in sg if s["verdict"] == "negativo"])
    pos = pool([s for s in sg if s["verdict"] == "positivo"])
    base = sg[0]["base_scen"]

    def table(title, pr):
        if pr is None:
            return ""
        rows = "".join(f"<tr><td><i class='sw' style='background:{SCEN_COL[k]}'></i>{e(SCEN_NAMES[k])}</td><td><b>{P(pr[k])}</b></td><td class='mu'>{P(base[k])}</td></tr>" for k in range(5))
        return f"<div class='scn'><h4>{title}</h4>{stacked(pr)}<table><tr><th>Scenario a 3 mesi</th><th>Probabilità</th><th>Normale</th></tr>{rows}</table></div>"
    best = max(range(5), key=lambda k: allp[k])
    bad = allp[0] + allp[1]
    good = allp[3] + allp[4]
    txt = (f"<p><b>In sintesi:</b> mettendo insieme tutti gli indicatori, lo scenario più frequente è <b>{e(SCEN_NAMES[best].split(' (')[0].lower())}</b> ({P(allp[best])}). "
           f"Un calo (moderato o forte) ha avuto il {P(bad)} dei casi, un rialzo (moderato o forte) il {P(good)}. "
           f"Il forte calo oltre −10% è stato raro ({P(allp[0])}, normalmente {P(base[0])}).</p>")
    rows = "".join(f"<tr data-chart='{e(s['key'])}'><td>{e(s['name'])}<div class='mu'>{s['n']} giorni simili</div></td><td>{stacked(s['scen'])}</td>"
                   f"<td><b class='dn'>{P(s['scen'][0] + s['scen'][1])}</b></td><td><b class='up'>{P(s['scen'][3] + s['scen'][4])}</b></td></tr>" for s in sg)
    leg = "".join(f"<span><i class='sw' style='background:{SCEN_COL[k]}'></i>{e(SCEN_NAMES[k])}</span>" for k in range(5))
    return ("<h3 style='margin-top:26px'>Cosa è successo dopo, in tutti i casi simili a oggi: gli scenari</h3>"
            "<div class='explain'><p>Qui metto insieme <b>tutti gli indicatori della tabella sopra</b>. Per ognuno ho preso i giorni del passato in cui valeva come oggi e ho guardato come si è mosso "
            "l'S&amp;P 500 nei 3 mesi successivi, dividendo i casi in 5 scenari. Le percentuali sono la quota di casi finiti in ogni scenario. È un quadro del passato, non una previsione.</p></div>"
            f"<div class='card'>{txt}<div class='scgrid'>{table('Tutti gli indicatori insieme', allp)}"
            + (table(f'Solo gli indicatori di prudenza ({sum(1 for s in sg if s["verdict"] == "negativo")})', neg) if neg else "")
            + (table(f'Solo gli indicatori favorevoli ({sum(1 for s in sg if s["verdict"] == "positivo")})', pos) if pos else "")
            + f"</div><div class='leg'>{leg}</div></div>"
            f"<details class='exp'><summary>Scenari indicatore per indicatore</summary><div class='card scroll'><table><tr><th>Indicatore</th><th style='width:40%'>Come è andata dopo (3 mesi)</th><th>Calo</th><th>Rialzo</th></tr>{rows}</table>"
            f"<div class='leg'>{leg}</div></div></details>")


# ---------------------------------------------------------------- segnali di stress
def flags_simple(fl):
    act = [f for f in fl if f["today"] and not f["nodata"]]
    head = (f"<div class='sumline'><span class='badge {'bad' if len(act) >= 4 else ('warn' if act else 'ok')}'>{len(act)} condizioni di stress attive su {len(fl)}</span></div>")
    out = []
    for f in sorted(fl, key=lambda x: (not (x["today"] and not x["nodata"]), x["nodata"], x["name"])):
        if f["nodata"]:
            state, cls = "dato non disponibile", "na"
        elif f["today"]:
            state, cls = "ATTIVA oggi", "ba"
        else:
            state, cls = "non attiva", "ok"
        if f["freq"] is None:
            body = "<div class='mu'>Storico insufficiente per dire cosa succede dopo.</div>"
        else:
            body = (f"<div class='sgb'><div><span>Calo oltre 10% nei 3 mesi dopo</span>{bar(f['freq'], f['base'], 'var(--bad)')}<b>{P(f['freq'])}</b> <i>normale {P(f['base'])}</i></div>"
                    f"<div><span>Rialzo oltre 10% nei 3 mesi dopo</span>{bar(f['up'], f['base_up'], 'var(--ok)')}<b>{P(f['up'])}</b> <i>normale {P(f['base_up'])}</i></div></div>"
                    f"<div class='mu'>Rendimento medio dopo 3 mesi: {S(f['ret'])} · visto in {f['n']} giorni del passato</div>")
        out.append(f"<div class='fl {cls}'><div class='sgh'><b>{e(f['name'])}</b><span class='st'>{state}</span></div>{body}</div>")
    intro = ("<div class='explain'><p><b>Come leggere.</b> Sono 12 «condizioni di stress» (VIX alto, credito che si irrigidisce, curva dei tassi invertita…). Le schede <b>rosse</b> sono quelle attive oggi. "
             "Sotto ognuna: quante volte, in passato, dopo quella condizione c'è stato un calo oltre 10% (rosso) o un rialzo oltre 10% (verde) nei 3 mesi successivi, confrontate con il normale (segno verticale). "
             "Attenzione: un VIX alto spesso precede anche i rimbalzi più forti.</p></div>")
    return intro + head + "<div class='sggrid'>" + "".join(out) + "</div>"


# ---------------------------------------------------------------- volatilità
def volatility_simple(v):
    f = lambda x: f"{x * 100:.1f}%".replace(".", ",")
    att, cur, med = v["attesa"], v["attuale_1m"], v["mediana_storica"]
    if att < med * 0.8:
        lvl, cls = "più calmo del normale", "ok"
    elif att < med * 1.25:
        lvl, cls = "nella norma", "ok"
    elif att < med * 1.8:
        lvl, cls = "più agitato del normale", "warn"
    else:
        lvl, cls = "molto agitato", "bad"
    daily = att / np.sqrt(252)
    top = max(att, cur, med, v["alta"]) * 1.15
    pos = lambda x: min(x / top * 100, 100)
    scale = (f"<div class='vscale'><div class='vtrack'><b style='left:{pos(med):.0f}%'><em>media storica {f(med)}</em></b>"
             f"<b class='c2' style='left:{pos(cur):.0f}%'><em>ultimi 21 giorni {f(cur)}</em></b><b class='c3' style='left:{pos(att):.0f}%'><em>attesa {f(att)}</em></b></div></div>")
    ev = v["eval"]
    return (f"<div class='vd {cls}'>Nel prossimo mese il mercato dovrebbe essere <b>{lvl}</b>.</div>{scale}"
            f"<p>In un giorno normale l'S&amp;P 500 si muove di circa <b>±{f'{daily * 100:.1f}'.replace('.', ',')}%</b>: su 1.000 euro investiti sono circa {daily * 1000:.0f} euro in più o in meno.</p>"
            f"<p class='mu'>Intervallo probabile della volatilità annua: {f(v['bassa'])} – {f(v['alta'])}. Il VIX (la paura che gli operatori prezzano) è "
            f"{('%.1f' % v['vix']).replace('.', ',') if v.get('vix') else 'n.d.'}.</p>"
            f"<details><summary>Quanto è affidabile?</summary><p class='mu'>In {ev['n']} prove fuori campione dal 2005 l'errore medio è stato {ev['mae_har']:.1f} punti, contro {ev['mae_persist']:.1f} di chi ripete la volatilità recente. "
            "Nelle crisi improvvise la volatilità sale più del previsto.</p></details>")


CSS = """
.pb{position:relative;height:12px;background:var(--bd);border-radius:6px;margin:4px 0}.pb i{display:block;height:100%;border-radius:6px}
.pb u{position:absolute;top:-3px;width:3px;height:18px;background:var(--tx);border-radius:2px;opacity:.85}
.pr{margin:12px 0}.pl{font-size:14px;color:var(--mu)}.pn{font-size:34px;font-weight:800;line-height:1.1}.pt{font-size:13px;color:var(--mu)}
.vd{padding:8px 12px;border-radius:10px;font-size:15px;margin:8px 0}.vd.ok{background:var(--okbg)}.vd.warn{background:var(--warnbg)}.vd.bad{background:var(--badbg)}.vd.neutro{background:var(--bg)}
.sc3{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}.sc3 div{background:var(--bg);border-radius:10px;padding:6px 8px;text-align:center}.sc3 span{display:block;font-size:11px;color:var(--mu)}.sc3 b{font-size:18px}
.hz2 details{margin-top:8px}.old .card{border:0;padding:0}.old .grid4{display:block}
.sggrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px}
.sg,.fl{background:var(--card);border:1px solid var(--bd);border-left-width:6px;border-radius:12px;padding:10px 12px;cursor:pointer}
.sg.bad,.fl.ba{border-left-color:var(--bad)}.sg.ok,.fl.ok{border-left-color:var(--ok)}.sg.warn{border-left-color:var(--warn)}.fl.na{border-left-color:var(--bd)}
.sgh{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.fl .st{font-size:11px;font-weight:800;text-transform:uppercase;color:var(--mu)}.fl.ba .st{color:var(--bad)}.fl.ok .st{color:var(--ok)}
.sgb{margin-top:6px}.sgb span{font-size:12px;color:var(--mu)}.sgb i{font-style:normal;font-size:12px;color:var(--mu)}.sgb b{font-size:16px}
.sumline{margin:6px 0 10px}
.stk{display:flex;height:16px;border-radius:8px;overflow:hidden;background:var(--bd)}.stk i{display:block;height:100%}
.sw{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px}
.scgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.scn h4{margin:6px 0}.leg{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--mu);margin-top:10px}
.vscale{margin:34px 8px 22px}.vtrack{position:relative;height:10px;background:linear-gradient(90deg,var(--ok),var(--warn),var(--bad));border-radius:5px}
.vtrack b{position:absolute;top:-6px;width:4px;height:22px;background:var(--tx);border-radius:2px}.vtrack b em{position:absolute;bottom:26px;left:-40px;width:84px;text-align:center;font-style:normal;font-size:11px;font-weight:600;color:var(--mu)}
.vtrack b.c2{opacity:.55;top:-2px;height:14px}.vtrack b.c2 em{bottom:auto;top:18px}.vtrack b.c3{background:var(--ac)}
"""


# ---------------------------------------------------------------- riquadro principale: calo o rialzo?
HZ_WORD = {"10g": "nei prossimi 10 giorni", "1m": "nel prossimo mese", "3m": "nei prossimi 3 mesi", "6m": "nei prossimi 6 mesi"}


def _rel(p, b):
    if not b:
        return "nella norma"
    r = p / b
    return "più alta del normale" if r > 1.25 else ("più bassa del normale" if r < 0.8 else "nella norma")


def balance_html(pred, mat, feat_it, n_neg=0, n_tot=0):
    from .config import HORIZONS
    rows, votes = "", {"calo": 0, "rialzo": 0, "pari": 0}
    for hz in HORIZONS:
        if hz not in pred or hz not in mat:
            continue
        thr = PRIMARY[hz]
        try:
            pdn, bdn = pred[hz]["p"][thr], pred[hz]["base"][thr]
            up = mat[hz]["up"][thr]
        except Exception:  # noqa: BLE001
            continue
        pup, bup = up["p"], up["base"]
        cls, words = verdict_words(pdn, pup)
        tot = max(pdn + pup, 1e-9)
        wd = max(pdn / tot * 100, 12)
        wu = max(pup / tot * 100, 12)
        k = "calo" if pdn > pup * 1.25 else ("rialzo" if pup > pdn * 1.25 else "pari")
        if hz in ("1m", "3m", "6m"):
            votes[k] += 1
        chip = {"calo": ("bad", "più probabile il calo"), "rialzo": ("ok", "più probabile il rialzo"), "pari": ("warn", "equilibrio")}[k]
        if max(pdn, pup) < 0.12:
            chip = ("ok", "tutto tranquillo")
        rows += (f"<div class='bal'><div class='balh'><b>{HZ_LABEL[hz]}</b><span class='badge {chip[0]}'>{chip[1]}</span></div>"
                 f"<div class='tugn'><span class='dn'>Calo ≥{thr}%: <b>{P(pdn)}</b></span><span class='up'>Rialzo ≥{thr}%: <b>{P(pup)}</b></span></div>"
                 f"<div class='tug'><div class='td' style='width:{wd:.0f}%'></div><div class='tu' style='width:{wu:.0f}%'></div></div>"
                 f"<div class='mu'>Rispetto al normale: probabilità di calo {_rel(pdn, bdn)} (normale {P(bdn)}), di rialzo {_rel(pup, bup)} (normale {P(bup)}).</div></div>")
    if not rows:
        return ""
    if votes["rialzo"] > votes["calo"]:
        head, hc = "Oggi è più probabile un <b>rialzo</b> che un calo.", "ok"
    elif votes["calo"] > votes["rialzo"]:
        head, hc = "Oggi è più probabile un <b>calo</b> che un rialzo.", "bad"
    else:
        head, hc = "Calo e rialzo oggi sono <b>in equilibrio</b>.", "warn"
    why = []
    try:
        m3 = mat["3m"]
        why.append(f"Nei {m3['n_analog']} giorni passati più simili a oggi (per volatilità, distanza dai massimi e andamento recente), a 3 mesi l'S&amp;P 500 è salito nel "
                   f"<b>{P(m3['ret_analog']['pos'])}</b> dei casi (su tutti i giorni: {P(m3['ret_base']['pos'])}).")
    except Exception:  # noqa: BLE001
        pass
    for hz in ("1m", "3m"):
        d = (pred.get(hz) or {}).get("drivers") or []
        if d:
            txt = "; ".join(f"{e(feat_it.get(f, f))} ({'spinge verso più rischio' if c > 0 else 'spinge verso meno rischio'})" for f, c in d[:2])
            why.append(f"Per {HZ_LABEL[hz]} pesa soprattutto: {txt}.")
    if n_tot:
        why.append(f"{n_neg} indicatori su {n_tot} sono in zona di prudenza (vedi sotto i rischi e gli elementi favorevoli).")
    why.append("I mercati salgono più spesso di quanto scendano: per questo conta il confronto con il «normale», non solo il numero.")
    return (f"<div class='balbox'><div class='vd {hc} big'>{head}</div>{rows}"
            "<details open><summary><b>Perché?</b></summary><ul class='simple'>" + "".join(f"<li>{w}</li>" for w in why) + "</ul></details></div>")


CSS += """
.balbox{margin:12px 0}.vd.big{font-size:20px;font-weight:700;padding:12px 14px}.bal{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;margin:8px 0}
.balh{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:15px}
.tugn{display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px}.tugn b{font-size:18px}.tug{display:flex;height:12px;border-radius:9px;overflow:hidden;font-size:13px;color:#fff}.tug div{display:flex;align-items:center;padding:0 10px;white-space:nowrap;overflow:hidden}
.tug .td{background:var(--bad)}.tug .tu{background:var(--ok);justify-content:flex-end}.tug b{margin-left:4px;font-size:16px}
"""
