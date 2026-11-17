# -*- coding: utf-8 -*-
"""Sezione «Prossime ore» della pagina Oggi: previsione del VWCE a 1, 3, 6 e 12 ore, eventi in arrivo (trimestrali) e prova. Dati: ore.py (data/ore.json)."""
import html as _h
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import pieghe
from .segnali_ui import CSS as SG_CSS

ROMA = ZoneInfo("Europe/Rome")
CSS = SG_CSS + """<style>
.ore .oh{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}
.ore .rng{position:relative;height:12px;margin:10px 0 4px;border-radius:7px;background:linear-gradient(90deg,var(--badbg),var(--card) 38%,var(--card) 62%,var(--okbg));border:1px solid var(--bd)}
.ore .rng b{position:absolute;top:1px;height:8px;border-radius:5px;background:var(--ac);opacity:.45}
.ore .rng i{position:absolute;top:-3px;width:3px;height:16px;border-radius:2px;background:var(--tx)}
.ore .rng u{position:absolute;top:-4px;left:50%;width:1px;height:18px;background:var(--mu);opacity:.6}
.ore .kpi .v2{font-size:19px;white-space:nowrap}.ore .kpi .v2.neg{color:var(--bad)}.ore .kpi .v2.pos{color:var(--ok)}
.ore .ev{border:1px solid var(--bd);border-radius:14px;padding:12px 14px;background:var(--card);margin:10px 0}
.ore .ev table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13.5px}.ore .ev td,.ore .ev th{padding:5px 8px;border-bottom:1px solid var(--bd);text-align:left}
.ore .tag{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;border:1px solid var(--bd);margin-left:6px;color:var(--mu)}
</style>"""


def _n(x, d=1, segno=False):
    return (f"{x:+.{d}f}" if segno else f"{x:.{d}f}").replace(".", ",")


def _p(x, d=1, segno=True):
    return _n(x * 100, d, segno) + "%"


def _ora(s: str, giorno: bool = False) -> str:
    t = datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(ROMA)
    return t.strftime("%d/%m %H:%M") if giorno else t.strftime("%H:%M")


def _barra(a: dict, scala: float = 0.03) -> str:
    f = lambda v: max(0.0, min(100.0, 50 + 50 * v / scala))
    lo, hi, md = f(a["p10"]), f(a["p90"]), f(a["mediana"])
    return f"<div class='rng'><u></u><b style='left:{lo:.1f}%;width:{max(hi - lo, 1):.1f}%'></b><i style='left:{md:.1f}%'></i></div>"


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


def _scheda(nome: str, a: dict, t0: datetime) -> str:
    fine = (t0 + timedelta(hours=a["ore"])).astimezone(ROMA).strftime("%H:%M")
    testo, cl = _direzione(a)
    ev = f"<span class='tag'>{_h.escape(', '.join(a['eventi']))}</span>" if a["eventi"] else ""
    rimb = "<div class='s'>Dopo un calo forte il mercato tende a rimbalzare un po' più spesso che a scendere ancora: segnale debole, già incluso nei numeri.</div>" if a.get("rimbalzo") else ""
    return (f"<div class='kpi'><div class='k'>Tra {nome} (alle {fine}){ev}</div>"
            f"<div class='v2 {cl}'>{testo}</div>"
            f"<div class='s'><b>{_n(a['p_su'] * 100, 0)}%</b> di probabilità di essere sopra il prezzo di ora, <b>{_n((1 - a['p_su']) * 100, 0)}%</b> sotto. Valore centrale: <b>{_p(a['mediana'], 2)}</b>.</div>"
            f"{_barra(a)}"
            f"<div class='s'>Caso normale: da <b>{_p(a['p10'], 2)}</b> a <b>{_p(a['p90'], 2)}</b> (8 casi su 10).<br>"
            f"Se scende, in media <b>{_p(a['giu_medio'], 2)}</b>; se sale, <b>{_p(a['su_medio'], 2)}</b>.<br>"
            f"Peggio 1 volta su 20: <b>{_p(a['p05'], 2)}</b> · meglio 1 volta su 20: <b>{_p(a['p95'], 2)}</b>.<br>"
            f"Probabilità di −1% o peggio: <b>{_n(a['p_meno1'] * 100, 0)}%</b> · di +1% o meglio: <b>{_n(a['p_piu1'] * 100, 0)}%</b> · di −2% o peggio: <b>{_n(a['p_meno2'] * 100, 1)}%</b>.</div>{rimb}</div>")


def _evento(e: dict) -> str:
    sd = e["k"] * e["mossa_tipica"] / 100.0
    imp = " (ricavata dai prezzi delle opzioni)" if e.get("mossa_implicita") else " (media delle ultime trimestrali)"
    righe = "".join(f"<tr><td>{_n(x['titolo'], 0, True)}%</td><td><b>{_n(x['vwce'], 2, True)}%</b></td></tr>" for x in e["righe"]) if e.get("righe") else ""
    q = _ora(e["quando"])
    if e.get("gia_uscita"):
        return (f"<div class='ev'><b>{_h.escape(e['nome'])}: conti già usciti alle {q}</b><p class='small' style='margin:6px 0 0'>L'effetto è già nei futures e quindi nel valore atteso sopra: non serve altro.</p></div>")
    tab = (f"<table><tr><th>Se {_h.escape(e['nome'])} si muove di</th><th>Il VWCE si muove di circa</th></tr>{righe}</table>") if righe else ""
    return (f"<div class='ev'><b>Stasera alle {q}: conti di {_h.escape(e['nome'])}</b> <span class='tag'>pesa circa {_n(e['peso'])}% nel VWCE</span>"
            f"<p class='small' style='margin:6px 0 0'>Mossa tipica del titolo dopo i conti: ±{_n(e['mossa_tipica'], 1)}%{imp}. Sul VWCE vale circa ±{_n(abs(sd) * 100, 1)}%, più l'effetto sugli altri titoli tecnologici "
            f"(sulle ultime 12 trimestrali l'S&amp;P 500 si è mosso in media 0,09 volte la mossa di Nvidia). La direzione di una sorpresa non si può prevedere: l'app aggiorna il valore atteso entro 15 minuti dall'uscita.</p>{tab}</div>")


def _prova(r: dict) -> str:
    v = r.get("verifica") or {}
    if v.get("pronto"):
        parti = [f"{k}: {_n(x['dentro'] * 100, 0)}% dentro l'intervallo su {x['n']} previsioni" for k, x in v.items() if isinstance(x, dict) and x.get("dentro") is not None]
        fw = "Verifica in avanti (dal diario di Armor): " + "; ".join(parti) + ". L'intervallo dichiarato è l'80%."
    else:
        fw = f"Verifica in avanti: il diario delle previsioni a ore è appena partito ({v.get('n', 0)} righe); dopo 30 righe confronta ogni previsione con il prezzo reale 3 e 12 ore dopo."
    return ("<p class='small'><b>Come funziona.</b> Il VWCE chiude alle 17:30 (o alle 22-23 sulle sedi serali), ma Wall Street e i futures sull'S&amp;P 500 continuano a muoversi. "
            "Armor misura quanto i futures e il cambio euro/dollaro si sono mossi dall'ultimo scambio del VWCE: quella è la parte del movimento che il prezzo non ha ancora seguito (il «salto in arrivo»). "
            "L'ampiezza delle oscillazioni viene dalla paura del mercato (VIX) e dalla forma reale dei movimenti degli ultimi due anni; per le trimestrali si aggiunge l'incertezza del titolo, pesata per quanto conta nel VWCE.</p>"
            "<p class='small'><b>Prova.</b> Su 570 notti (2024-2026) la variazione tra chiusura e apertura del VWCE è stata stimata per l'86% da futures e cambio; l'86% vale anche sulla seconda metà dei dati, non usata per tarare. "
            "Quando il salto stimato era −0,5% o peggio (64 notti su 570), il VWCE ha aperto davvero almeno a −0,5% nel 91% dei casi; con −1% o peggio (22 notti) sempre, in media −1,8%. Gli intervalli a 1, 3, 6 e 12 ore coprono l'80% dei casi nella seconda metà dei dati (81%, 80%, 80%, 82%).</p>"
            f"<p class='small'>{fw}</p>"
            "<p class='small'><b>Limiti.</b> La direzione dei prossimi movimenti non è prevedibile dalla sola storia dei prezzi: su 5.500 ore provate, né l'andamento delle ore precedenti né la paura del mercato indicano con costanza se si sale o si scende. Fa eccezione il «salto in arrivo» (futures e cambio mossi dopo l'ultimo scambio), che è misurabile, e un piccolo rimbalzo dopo i cali forti, qui incluso ma debole. Per questo le probabilità «sopra/sotto» restano spesso vicine a 50 e 50: è un'informazione, non una mancanza. Non prevede la direzione di una notizia a sorpresa e non sa nulla di ciò che accade dopo l'ultimo aggiornamento (ogni 15 minuti). Dopo l'apertura il salto tende in parte a rientrare (in media del 19%): non è incluso. "
            "La soglia di −0,5% è stata scelta dopo il calo del 17 novembre, che con −0,7% non sarebbe scattato: va riguardata fra qualche mese. Non è un consiglio finanziario.</p>")


def html(r: dict | None) -> str:
    if not r:
        return "<p class='mu'>La previsione a ore sarà disponibile dopo il prossimo aggiornamento.</p>"
    if not all("p_su" in x for x in r["orizzonti"].values()):
        return "<p class='mu'>La previsione a ore si sta aggiornando al nuovo formato: tra pochi minuti sarà qui.</p>"
    t0 = datetime.strptime(r["ora"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    g, v = r["giudizio"], r["vwce"]
    cls = {"bad": "b", "warn": "w", "ok": ""}[g["classe"]]
    gap = r["gap"]
    equo = v["prezzo"] * (1 + gap)
    if r.get("aperto"):
        riga = f"Il VWCE sta scambiando adesso a <b>{_n(v['prezzo'], 2)} €</b> e segue già i futures americani."
    else:
        riga = (f"Ultimo scambio del VWCE: <b>{_n(v['prezzo'], 2)} €</b> alle {_ora(v['ora'])} ({_h.escape(v.get('sede') or '')}). Da allora futures e cambio indicano un valore equo di circa <b>{_n(equo, 2)} €</b> (<b>{_p(gap, 2)}</b>) all'apertura.")
    m = r.get("mercato") or {}
    chips = []
    if m.get("vix"):
        chips.append(f"<span class='pill'>Paura (VIX) {_n(m['vix'])}" + (f" · {_p(m['vix_1h'], 0)} in 1 ora" if m.get("vix_1h") is not None else "") + "</span>")
    if r.get("es_1h") is not None:
        chips.append(f"<span class='pill {'off' if r['es_1h'] <= -0.01 else ''}'>Futures S&amp;P 500 {_p(r['es_1h'], 2)} nell'ultima ora</span>")
    schede = "".join(_scheda(k, a, t0) for k, a in r["orizzonti"].items())
    ev = "".join(_evento({**e, "righe": next((s["righe"] for s in r.get("scenari", []) if s["ticker"] == e["ticker"]), [])}) for e in r.get("eventi", []))
    return (CSS + "<div class='mn ore'>"
            f"<div class='hero {cls}'><span class='small'>Aggiornata alle {_ora(r['ora'])} (ora italiana) · si rinnova ogni 15 minuti</span><b class='big'>{_h.escape(g['testo'])}</b>{riga}</div>"
            f"<div class='pills'>{''.join(chips)}</div>"
            "<p class='sub'>Chiave di lettura: guarda prima la direzione e le percentuali «sopra / sotto»: se sono vicine a 50 e 50, il mercato non ha una direzione e conta solo quanto può muoversi. "
            "Se sono molto sbilanciate (per esempio 70 e 30), c'è già un movimento in arrivo da una parte. «Peggio 1 volta su 20» è lo scenario cattivo realistico, non il peggiore possibile.</p>"
            f"<div class='g3'>{schede}</div>{ev}"
            + pieghe.fold("Come funziona e quanto è affidabile", _prova(r)) + "</div>")


def sub(r: dict | None) -> str:
    """Riga breve per la tendina chiusa."""
    if not r or "p_su" not in r["orizzonti"]["6 ore"]:
        return ""
    a = r["orizzonti"]["6 ore"]
    return f"{r['giudizio']['testo']} · 6 ore: {_direzione(a)[0].lower()} ({_n(a['p_su'] * 100, 0)}% su) · peggio 1 su 20 {_p(a['p05'], 1)}"
