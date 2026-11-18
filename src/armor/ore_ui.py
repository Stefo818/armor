# -*- coding: utf-8 -*-
"""Sezione «Prossime ore» della pagina Oggi: previsione del VWCE a 1, 3, 6 e 12 ore, radar degli eventi (Fed, inflazione, lavoro, trimestrali) con le attese degli analisti, notizie e prova.
Dati: ore.py (data/ore.json) e radar.py. Impaginazione: per ogni orizzonte UNA barra divisa in rosso (scende) e verde (sale) con le percentuali scritte dentro; tutto il resto in tendine."""
import html as _h
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import pieghe
from .segnali_ui import CSS as SG_CSS

ROMA = ZoneInfo("Europe/Rome")
CSS = SG_CSS + """<style>
.ore .ohd{border:1px solid var(--bd);border-left-width:4px;border-radius:12px;padding:8px 12px;background:var(--card);margin:0 0 8px}
.ore .ohd.b{border-left-color:var(--bad)}.ore .ohd.w{border-left-color:var(--warn,#f59e0b)}.ore .ohd.ok{border-left-color:var(--ok)}
.ore .ohd b.v{font-size:16px}.ore .ohd .t{font-size:12px;color:var(--mu);margin-left:6px}.ore .ohd .os{font-size:13px;color:var(--mu);margin-top:3px;line-height:1.35}.ore .ohd .os b{color:var(--tx)}
.ore .ctx{font-size:12px;color:var(--mu);margin:0 2px 8px;line-height:1.5}.ore .ctx b{color:var(--tx);font-weight:600}.ore .ctx .r{color:var(--bad);font-weight:600}
.ore .hz{border:1px solid var(--bd);border-radius:14px;background:var(--card);padding:2px 12px 4px}
.ore .hk{display:flex;justify-content:space-between;font-size:11.5px;color:var(--mu);padding:7px 0 0 54px}
.ore .hr{display:grid;grid-template-columns:46px 1fr;gap:8px;padding:6px 0;border-bottom:1px solid var(--bd)}.ore .hr:last-of-type{border-bottom:0}
.ore .lb{font-size:14px;font-weight:700;line-height:1.1;padding-top:5px}.ore .lb small{display:block;font-weight:400;color:var(--mu);font-size:11px;margin-top:2px}
.ore .pb{display:flex;height:28px;border-radius:8px;overflow:hidden;font-size:14px;font-weight:800;color:#fff}
.ore .pb span{display:flex;align-items:center;min-width:58px;padding:0 10px;white-space:nowrap}
.ore .pb .dn{background:#b4373f}.ore .pb .up{background:#1d9a68;justify-content:flex-end}
.ore .hs{font-size:12px;color:var(--mu);margin-top:3px;line-height:1.4}.ore .hs b{color:var(--tx);font-weight:600}
.ore .hs .tg{display:inline-block;border-radius:999px;padding:0 7px;font-size:11px;border:1px solid var(--bd);margin-left:4px;color:var(--tx)}
.ore .esec{font-size:12px;color:var(--mu);margin:12px 2px 4px;text-transform:uppercase;letter-spacing:.04em}
.ore details.ev{border:1px solid var(--bd);border-radius:12px;background:var(--card);margin:0 0 6px}
.ore details.ev>summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:78px 1fr auto;gap:8px;align-items:center;padding:8px 10px;font-size:13px}
.ore details.ev>summary::-webkit-details-marker{display:none}
.ore .et{font-size:12px;color:var(--mu);line-height:1.2}.ore .en small{display:block;color:var(--mu);font-size:11px}
.ore .ei{font-size:12px;font-weight:700;border-radius:8px;padding:2px 8px;border:1px solid var(--bd);white-space:nowrap}
.ore .ei.hi{color:var(--bad);background:var(--badbg);border-color:var(--bad)}.ore .ei.me{color:var(--warn,#f59e0b);border-color:var(--warn,#f59e0b)}
.ore .eb{padding:2px 12px 10px;font-size:13px;line-height:1.45}.ore .eb p{margin:6px 0}.ore .eb ul{margin:6px 0 0 16px;padding:0}.ore .eb li{margin:3px 0}
.ore .cp{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0;border:0;padding:0;background:none}.ore .cp span{border:1px solid var(--bd);border-radius:8px;padding:2px 8px;font-size:12px}
.ore .nt a{color:var(--tx);text-decoration:none}.ore .nt li{margin:5px 0;font-size:13px}.ore .nt small{color:var(--mu)}
.ore table.tb{width:100%;border-collapse:collapse;font-size:12.5px}.ore .tb th,.ore .tb td{padding:5px 4px;border-bottom:1px solid var(--bd);text-align:right}.ore .tb th:first-child,.ore .tb td:first-child{text-align:left;color:var(--mu)}
</style>"""


def _n(x, d=1, segno=False):
    return (f"{x:+.{d}f}" if segno else f"{x:.{d}f}").replace(".", ",")


def _p(x, d=1, segno=True):
    return _n(x * 100, d, segno) + "%"


def _sd(e: dict) -> float:
    """Scossa tipica sul VWCE (frazione): dato macro misurato, oppure peso × contagio × 1,25 × mossa tipica del titolo."""
    if e.get("tipo") == "macro":
        return float(e["sd"])
    return e["k"] * 1.25 * e["mossa_tipica"] / 100.0


def _ora(s: str, giorno: bool = False) -> str:
    t = datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(ROMA)
    return t.strftime("%d/%m %H:%M") if giorno else t.strftime("%H:%M")


def _quando(s: str, t0: datetime) -> str:
    q = datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(ROMA)
    d = (q.date() - t0.astimezone(ROMA).date()).days
    g = "oggi" if d == 0 else ("domani" if d == 1 else q.strftime("%d/%m"))
    return f"{g} {q.strftime('%H:%M')}"


def _direzione(a: dict) -> tuple[str, str]:
    """Etichetta di direzione dalla probabilità di stare sopra o sotto il prezzo attuale."""
    su = a["p_su"]
    if su >= 0.58:
        return "Più probabile un rialzo", "pos"
    if su >= 0.53:
        return "Lieve tendenza al rialzo", "pos"
    if su <= 0.42:
        return "Più probabile un calo", "neg"
    if su <= 0.47:
        return "Lieve tendenza al calo", "neg"
    return "Direzione indecisa", ""


def _riga(nome: str, a: dict, t0: datetime) -> str:
    fine = (t0 + timedelta(hours=a["ore"])).astimezone(ROMA).strftime("%H:%M")
    su = max(1, min(99, round(a["p_su"] * 100)))
    giu = 100 - su
    ev = "".join(f"<span class='tg'>{_h.escape(x)}</span>" for x in a["eventi"])
    return (f"<div class='hr'><div class='lb'>{nome}<small>{fine}</small></div><div>"
            f"<div class='pb'><span class='dn' style='flex:{giu}'>▼ {giu}%</span><span class='up' style='flex:{su}'>{su}% ▲</span></div>"
            f"<div class='hs'>Scende ≈ <b>{_p(a['giu_medio'], 2)}</b> · sale ≈ <b>{_p(a['su_medio'], 2)}</b>{ev}</div>"
            f"<div class='hs'>Normale <b>{_p(a['p10'], 2)}</b> … <b>{_p(a['p90'], 2)}</b> · brutto <b>{_p(a['p05'], 2)}</b></div></div></div>")


def _sintesi(r: dict) -> str:
    """Una frase: quanto è netta la direzione sulle quattro fasce."""
    o = r["orizzonti"]
    ps = [a["p_su"] for a in o.values()]
    lo, hi = min(ps), max(ps)
    a12 = o["12 ore"]
    if hi < 0.53 and lo > 0.47:
        return f"<b>Nessuna direzione chiara</b>: su {_n(lo * 100, 0)}-{_n(hi * 100, 0)} casi su 100 il prezzo sarà più alto di ora, negli altri più basso."
    testo, _ = _direzione(a12)
    return f"<b>{_h.escape(testo)}</b> a 12 ore: {_n(a12['p_su'] * 100, 0)} casi su 100 più alto di ora, {_n((1 - a12['p_su']) * 100, 0)} più basso."


def _tabella(r: dict) -> str:
    o = r["orizzonti"]
    ks = list(o)
    righe = [("Valore centrale", lambda a: _p(a["mediana"], 2)), ("Se scende, in media", lambda a: _p(a["giu_medio"], 2)), ("Se sale, in media", lambda a: _p(a["su_medio"], 2)),
             ("Caso normale (8 su 10)", lambda a: f"{_n(a['p10'] * 100, 2, True)} / {_n(a['p90'] * 100, 2, True)}"), ("Peggio 1 volta su 20", lambda a: _p(a["p05"], 2)), ("Meglio 1 volta su 20", lambda a: _p(a["p95"], 2)),
             ("Probabilità −1% o peggio", lambda a: _n(a["p_meno1"] * 100, 0) + "%"), ("Probabilità +1% o meglio", lambda a: _n(a["p_piu1"] * 100, 0) + "%"), ("Probabilità −2% o peggio", lambda a: _n(a["p_meno2"] * 100, 1) + "%")]
    corpo = "<table class='tb'><tr><th></th>" + "".join(f"<th>{k}</th>" for k in ks) + "</tr>" + "".join(f"<tr><td>{t}</td>" + "".join(f"<td>{f(o[k])}</td>" for k in ks) + "</tr>" for t, f in righe) + "</table>"
    return corpo + "<p class='small mu'>Tutte le variazioni sono rispetto al prezzo di ora. «Se scende / se sale» è la media dei casi in cui il prezzo finisce sotto o sopra quello di ora.</p>"


def _impatto(sd: float) -> tuple[str, str]:
    if sd >= 0.004:
        return "alto", "hi"
    if sd >= 0.0015:
        return "medio", "me"
    return "basso", ""


def _evento(e: dict, t0: datetime) -> str:
    sd = _sd(e)
    liv, cl = _impatto(sd)
    macro = e.get("tipo") == "macro"
    sottotitolo = "dato economico" if macro else "conti trimestrali"
    stato = "uscito" if e.get("gia_uscita") else f"±{_n(sd * 100, 2)}%"
    q = _ora(e["quando"]) if e.get("gia_uscita") else _quando(e["quando"], t0)
    testa = (f"<summary><span class='et'>{q}</span><span class='en'><b>{_h.escape(e['nome'])}</b><small>{sottotitolo} · impatto {liv}</small></span>"
             f"<span class='ei {cl}'>{stato}</span></summary>")
    if macro:
        corpo = f"<p>{_h.escape(e.get('cosa') or '')}</p>"
        if e.get("misurato"):
            corpo += (f"<p>Misurato su {e['n_misura']} uscite passate (2024-2026): nelle tre ore dopo, i futures si muovono in più del normale di circa ±{_n(e['es_eccesso'], 2)}%, che sul VWCE vale circa ±{_n(sd * 100, 2)}%. "
                      "La direzione dipende dalla sorpresa rispetto alle previsioni: non è prevedibile prima, ma l'app aggiorna la stima entro 15 minuti dall'uscita.</p>")
        else:
            corpo += f"<p>Ampiezza stimata in modo prudente (circa ±{_n(sd * 100, 2)}% sul VWCE), non misurata su uscite passate.</p>"
        if e.get("attese"):
            corpo += "<p><b>Previsioni degli economisti</b></p><ul>" + "".join(f"<li>{_h.escape(x)}</li>" for x in e["attese"]) + "</ul>"
    else:
        fonte = "prezzi delle opzioni" if e.get("mossa_implicita") else ("media delle ultime trimestrali" if (e.get("storico") or {}).get("n", 0) >= 8 else "stima")
        corpo = (f"<p>Pesa circa <b>{_n(e['peso'])}%</b> nel VWCE. Mossa tipica del titolo dopo i conti: <b>±{_n(e['mossa_tipica'])}%</b> ({fonte}). "
                 f"Sul VWCE vale circa <b>±{_n(sd / 1.25 * 100, 2)}%</b> in media, compreso l'effetto sugli altri titoli simili.</p>")
        if e.get("righe"):
            corpo += "<div class='cp'>" + "".join(f"<span>titolo {_n(x['titolo'], 0, True)}% → VWCE <b>{_n(x['vwce'], 2, True)}%</b></span>" for x in e["righe"]) + "</div>"
        if e.get("lettura"):
            corpo += "<p><b>Cosa dicono gli analisti</b></p><ul>" + "".join(f"<li>{_h.escape(x['t'])}</li>" for x in e["lettura"]) + "</ul>"
        corpo += "<p class='small mu'>La direzione non si può prevedere: nei dati degli ultimi anni né la sorpresa passata né la rincorsa del titolo spiegano la reazione. Conta quanto si discosta dalle attese.</p>"
    return f"<details class='ev'>{testa}<div class='eb'>{corpo}</div></details>"


def _eventi(r: dict, t0: datetime) -> str:
    scen = {s["ticker"]: s["righe"] for s in r.get("scenari", [])}
    evs = [{**e, "righe": scen.get(e["ticker"], [])} for e in r.get("eventi", [])]
    evs = [e for e in evs if (_sd(e) >= 0.0005 or e.get("tipo") == "macro")]
    if not evs:
        return ""
    ordine = sorted(evs, key=lambda e: (e.get("gia_uscita", False), e["quando"]))
    return "<div class='esec'>Cosa può scuotere il mercato nelle prossime ore</div>" + "".join(_evento(e, t0) for e in ordine[:7])


def _notizie(r: dict) -> str:
    n = r.get("notizie") or {}
    if not n.get("n"):
        return ""
    righe = ""
    if n.get("tono") is not None:
        base = n.get("tono_base")
        if base is None:
            t = f"Tono delle notizie macro di oggi: {_n(n['tono'], 2, True)} (scala da −1 a +1)."
        else:
            d = n["tono"] - base
            conf = "più negativo del solito" if d <= -0.08 else ("più positivo del solito" if d >= 0.08 else "in linea con gli ultimi giorni")
            t = f"Tono delle notizie macro: <b>{conf}</b> ({_n(n['tono'], 2, True)} contro {_n(base, 2, True)} della media recente)."
        righe += f"<p>{t}</p>"
    if n.get("temi"):
        righe += "<div class='cp'>" + "".join(f"<span>{_h.escape(k)} · {v}</span>" for k, v in list(n["temi"].items())[:5]) + "</div>"
    if n.get("elenco"):
        li = ""
        for x in n["elenco"]:
            fr = "▲" if x["sent"] >= 0.15 else ("▼" if x["sent"] <= -0.15 else "◆")
            tit = _h.escape(x["titolo"] or "")
            tit = f"<a href='{_h.escape(x['link'])}' target='_blank' rel='noopener'>{tit}</a>" if x.get("link") else tit
            li += f"<li>{fr} {tit}<br><small>{_h.escape(x.get('fonte') or '')} · {' · '.join(x['temi']) if x['temi'] else 'notizia in evidenza'}</small></li>"
        righe += f"<ul class='nt'>{li}</ul>"
    righe += ("<p class='small mu'>Le notizie non entrano nei numeri della previsione: nessuna prova che aggiungano precisione. Se una notizia muove davvero il mercato, futures e cambio reagiscono subito e la previsione si aggiorna da sola. "
              "Qui servono a capire il perché di un movimento.</p>")
    sub = ", ".join(list(n.get("temi", {}))[:3]) or f"{n['n']} titoli in 24 ore"
    return pieghe.fold("Notizie che possono scuotere il mercato", righe, sub)


def _prova(r: dict) -> str:
    v = r.get("verifica") or {}
    if v.get("pronto"):
        parti = [f"{k}: {_n(x['dentro'] * 100, 0)}% dentro l'intervallo su {x['n']} previsioni" for k, x in v.items() if isinstance(x, dict) and x.get("dentro") is not None]
        fw = "Verifica in avanti (dal diario di Armor): " + "; ".join(parti) + ". L'intervallo dichiarato è l'80%."
    else:
        fw = f"Verifica in avanti: il diario delle previsioni a ore è appena partito ({v.get('n', 0)} righe); dopo 30 righe confronta ogni previsione con il prezzo reale 3 e 12 ore dopo."
    return ("<p class='small'><b>Come si legge.</b> Ogni barra dice quante possibilità su 100 ci sono che, a quell'ora, il VWCE valga di più (verde) o di meno (rosso) di adesso. "
            "Se le due metà sono quasi uguali, il mercato non ha una direzione: conta solo quanto può muoversi, scritto sotto («in media» se scende o se sale, e il caso brutto che capita 1 volta su 20).</p>"
            "<p class='small'><b>Come funziona.</b> Il VWCE chiude alle 17:30 (o alle 22-23 sulle sedi serali), ma Wall Street e i futures sull'S&amp;P 500 continuano a muoversi. "
            "Armor misura quanto i futures e il cambio euro/dollaro si sono mossi dall'ultimo scambio del VWCE: quella è la parte del movimento che il prezzo non ha ancora seguito (il «salto in arrivo»). "
            "L'ampiezza delle oscillazioni viene dalla paura del mercato (VIX) e dalla forma reale dei movimenti degli ultimi due anni. Agli eventi in calendario si aggiunge la loro scossa tipica, "
            "misurata sui futures per Fed, inflazione e lavoro, e dalle reazioni passate dei titoli per le trimestrali, pesata per quanto il titolo conta nel VWCE.</p>"
            "<p class='small'><b>Analisti e notizie.</b> Le attese degli analisti (stime di utile e ricavi, revisioni, obiettivi di prezzo) mostrano quanto è alta l'asticella. Provato su 288 trimestrali: i conti battono le stime l'82% delle volte, "
            "ma il titolo sale solo il 48%, e né la sorpresa passata né la rincorsa prima dei conti predicono la reazione. Per questo la direzione di una sorpresa resta imprevedibile: si misura l'ampiezza e si aggiorna subito dopo l'uscita.</p>"
            "<p class='small'><b>Prova.</b> Su 570 notti (2024-2026) la variazione tra chiusura e apertura del VWCE è stata stimata per l'86% da futures e cambio (86% anche sulla seconda metà dei dati, non usata per tarare). "
            "Quando il salto stimato era −0,5% o peggio (64 notti su 570), il VWCE ha aperto davvero almeno a −0,5% nel 91% dei casi; con −1% o peggio (22 notti) sempre, in media −1,8%.</p>"
            f"<p class='small'>{fw}</p>"
            "<p class='small'><b>Limiti.</b> La direzione dei prossimi movimenti non è prevedibile dalla sola storia dei prezzi: su 5.500 ore provate, né l'andamento delle ore precedenti né la paura del mercato indicano con costanza se si sale o si scende. "
            "Fa eccezione il «salto in arrivo» (misurabile) e un piccolo rimbalzo dopo i cali forti, incluso ma debole. Le misure su Fed, inflazione e lavoro vengono da 15-27 uscite: ordine di grandezza, non precisione. "
            "Notizie improvvise non programmate non sono nei numeri finché il mercato non reagisce. Dopo l'apertura il salto tende in parte a rientrare (in media del 19%). "
            "La soglia di −0,5% è stata scelta dopo il calo del 17 novembre, che con −0,7% non sarebbe scattato: va riguardata fra qualche mese. Non è un consiglio finanziario.</p>")


def html(r: dict | None) -> str:
    if not r:
        return "<p class='mu'>La previsione a ore sarà disponibile dopo il prossimo aggiornamento.</p>"
    if not all("p_su" in x for x in r["orizzonti"].values()):
        return "<p class='mu'>La previsione a ore si sta aggiornando al nuovo formato: tra pochi minuti sarà qui.</p>"
    t0 = datetime.strptime(r["ora"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    g, v = r["giudizio"], r["vwce"]
    cls = {"bad": "b", "warn": "w", "ok": "ok"}[g["classe"]]
    gap = r["gap"]
    equo = v["prezzo"] * (1 + gap)
    if r.get("aperto"):
        riga = f"VWCE <b>{_n(v['prezzo'], 2)} €</b> · sta già seguendo i futures americani."
    else:
        riga = f"Ultimo scambio <b>{_n(v['prezzo'], 2)} €</b> alle {_ora(v['ora'])} · valore equo all'apertura circa <b>{_n(equo, 2)} €</b> (<b>{_p(gap, 2)}</b>)."
    m = r.get("mercato") or {}
    ctx = []
    if m.get("vix"):
        ctx.append(f"Paura (VIX) <b>{_n(m['vix'])}</b>")
    if r.get("es_1h") is not None:
        ctx.append(f"futures S&amp;P 500 <span class='{'r' if r['es_1h'] <= -0.01 else ''}'><b>{_p(r['es_1h'], 2)}</b></span> in 1 ora")
    if m.get("es_24h") is not None:
        ctx.append(f"<span class='{'r' if m['es_24h'] <= -0.01 else ''}'><b>{_p(m['es_24h'], 1)}</b></span> in 24 ore")
    rimb = " Incluso un piccolo rimbalzo atteso dopo i cali forti (segnale debole)." if any(a.get("rimbalzo") for a in r["orizzonti"].values()) else ""
    righe = "".join(_riga(k, a, t0) for k, a in r["orizzonti"].items())
    return (CSS + "<div class='mn ore'>"
            f"<div class='ohd {cls}'><b class='v'>{_h.escape(g['testo'])}</b><span class='t'>ore {_ora(r['ora'])}</span><div class='os'>{riga}</div><div class='os'>{_sintesi(r)}</div></div>"
            f"<div class='ctx'>{' · '.join(ctx)}</div>"
            "<div class='hz'><div class='hk'><span>▼ prezzo più basso di ora</span><span>più alto ▲</span></div>"
            f"{righe}</div>"
            f"<div class='ctx' style='margin-top:6px'><b>Come leggere:</b> le percentuali sono i casi su 100 in cui, a quell'ora, il prezzo è sotto (rosso) o sopra (verde) quello di adesso. "
            f"«Scende / sale» = variazione media nei due casi. «Normale» = 8 casi su 10. «Brutto» = peggio che capita 1 volta su 20.{rimb}</div>"
            + pieghe.fold("Tutti i numeri", _tabella(r))
            + _eventi(r, t0) + _notizie(r)
            + pieghe.fold("Come funziona e quanto è affidabile", _prova(r)) + "</div>")


def sub(r: dict | None) -> str:
    """Riga breve per la tendina chiusa."""
    if not r or "p_su" not in r["orizzonti"]["6 ore"]:
        return ""
    a = r["orizzonti"]["6 ore"]
    return f"{r['giudizio']['testo']} · 6 ore: {_n(a['p_su'] * 100, 0)}% su, {_n((1 - a['p_su']) * 100, 0)}% giù · peggio 1 su 20 {_p(a['p05'], 1)}"
