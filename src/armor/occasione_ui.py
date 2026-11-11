# -*- coding: utf-8 -*-
"""Schede «Bussola di oggi»: salute del mercato e dell'economia, fase, Indice Occasione, fasce per orizzonte e pagella storica.
Tutti i numeri vengono da data/occasione.json (lavoro giornaliero) e data/occasione_verifica.json (convalida mensile)."""
import html as _h
import json

from . import fasi, occasione, soglie
from .config import DATA

E = _h.escape
COL = soglie.COL
COL_ST = {"nessun_panico": "#64748b", "osservazione": "#d97706", "coltello": "#dc2626", "occasione": "#16a34a", "occasione_forte": "#15803d", "nd": "#64748b"}
UMORE = {"agitato": "più ampie del solito", "calmo": "più piccole del solito", "normale": "nella norma"}
COL_FASE = {"rialzo": "#16a34a", "ribasso": "#dc2626", "laterale": "#d97706", "nd": "#64748b"}


def _leggi(nome: str) -> dict:
    p = DATA / nome
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def carica() -> tuple:
    return _leggi("occasione.json"), _leggi("occasione_verifica.json")


def _n(x, dec: int = 1, segno: bool = False) -> str:
    if x is None:
        return "n.d."
    s = f"{x:+.{dec}f}" if segno else f"{x:.{dec}f}"
    return s.replace(".", ",").replace("-", "−")


def _pc(x, dec: int = 0, segno: bool = False) -> str:
    return "n.d." if x is None else _n(x * 100, dec, segno) + "%"


def consiglio(o: dict) -> str:
    """Frase guida per le entrate extra, dallo stato di oggi (osservazione sul passato, non un consiglio)."""
    st, sc = o.get("stato"), _n(o.get("sconto"), 1)
    return {
        "nessun_panico": f"Nessuna occasione particolare: il mercato è a {sc}% dal massimo dell'anno e non c'è stato panico. Vale il piano mensile. Per i soldi extra, la storia dice che aspettare un calo in media non rende di più che entrare subito.",
        "osservazione": f"C'è stata tensione (mercato a {sc}% dal massimo dell'anno), ma manca il panico vero oppure manca ancora la svolta. Niente di speciale da fare: si osserva.",
        "coltello": f"Il mercato sta scendendo con forza ({sc}% dal massimo dell'anno) e non ci sono ancora segni di svolta. In passato, in questa situazione, chi voleva fare un'entrata extra ha fatto meglio ad aspettare la svolta o a dividerla in più parti.",
        "occasione": f"C'è stato panico e ora ci sono segni di svolta (mercato a {sc}% dal massimo dell'anno). In passato questa è stata spesso una buona finestra per un'entrata extra. Attenzione: nei grandi ribassi (2001, 2008) i primi segnali sono arrivati troppo presto, quindi meglio dividere in più parti.",
        "occasione_forte": f"Panico forte seguito da una svolta chiara (mercato a {sc}% dal massimo dell'anno): è la situazione che in passato ha accompagnato i minimi importanti. Resta valido dividere l'entrata in più parti: nei grandi ribassi il primo segnale non è stato l'ultimo.",
    }.get(st, "Dati insufficienti per l'Indice Occasione di oggi.")


def _tessera(titolo: str, valore: str, chip: str, col: str, nota: str) -> str:
    return (f"<div class='oc-t' style='--c:{col}'><span class='oc-tt'>{E(titolo)}</span><span class='oc-chip'>{E(chip)}</span>"
            f"<b class='oc-v'>{valore}</b><span class='oc-tn'>{nota}</span></div>")


def _tessere(o: dict, v: dict) -> str:
    out, sal = "", o.get("salute") or {}
    for k, titolo, nome in (("mercato", "Salute del mercato", "Indice Armor"), ("economia", "Salute di economia e finanza", "Super Armor")):
        s = sal.get(k)
        if not s:
            continue
        freq = ""
        try:
            r = v["salute"][k]["1995-2026"]
            freq = f" In questo stato, in passato, un calo di almeno il 10% entro 3 mesi è arrivato nel {_n(r[s['zona']]['discesa'], 0)}% dei casi (media di sempre {_n(r[4]['base'], 0)}%)."
        except Exception:
            pass
        pos = f" Più alto del {_pc(s.get('posizione'))} dei giorni dal 1990." if s.get("posizione") is not None else ""
        out += _tessera(titolo, f"{_n(s['valore'])}<small>/100</small>", s["stato"], COL[s["zona"]], f"{nome}.{pos}{freq}")
    f = o.get("fasi") or {}
    t = f.get("tendenza")
    if t in fasi.FASI:
        nome, perche = fasi.FASI[t]
        um = f.get("umore") or ("agitato" if f.get("agitato") else "calmo")
        umore = UMORE.get(um, UMORE["normale"])
        out += _tessera("Fase del mercato", nome, um, COL_FASE[t], f"{perche[0].upper()}{perche[1:]}. Oscillazioni attese: {umore}.")
    if o.get("occasione") is not None:
        st = o.get("stato", "nd")
        out += _tessera("Indice Occasione", f"{_n(o['occasione'], 0)}<small>/100</small>", occasione.STATI[st][0], COL_ST[st],
                        f"Sale solo quando c'è stato panico <i>e</i> ci sono segni di svolta. Da 50 in su è «occasione». Sconto dal massimo dell'anno: {_n(o.get('sconto'))}%.")
    return out


def tabella_fasce(o: dict, v: dict) -> str:
    fs = (o.get("fasi") or {}).get("fasce") or []
    if not fs:
        return ""
    tc, reg = o.get("titan_calo") or {}, v.get("fasce") or {}
    righe = ""
    for r in fs:
        sg = _n(r["soglia"] * 100, 0)
        stella = "" if (reg.get(r["nome"]) or {}).get("regge", True) else "<sup>*</sup>"
        calo = tc.get(r["nome"])
        righe += (f"<tr><td><b>{E(r['nome'])}</b>{stella}</td><td>{_pc(r.get('finora'), 1, True)}</td>"
                  f"<td><b>da {_pc(r['q10'], 0, True)} a {_pc(r['q90'], 0, True)}</b></td><td>{_pc(r['q50'], 1, True)}</td>"
                  f"<td>{_pc(r['perdita'])} <small>oltre −{sg}%</small></td><td>{_pc(r['guadagno'])} <small>oltre +{sg}%</small></td><td>{_pc(calo) if calo is not None else 'n.d.'}</td></tr>")
    return ("<div class='scroll'><table class='oc-tab'><thead><tr><th>Entro</th><th>Finora<br><small>stesso periodo appena passato</small></th><th>Fascia probabile<br><small>8 casi su 10</small></th>"
            "<th>Valore centrale</th><th>Rischio di perdere</th><th>Possibilità di guadagnare</th><th>Scivolone lungo la strada<br><small>calo di almeno 10% in qualche momento (5% per 1 settimana), stima del motore Titan</small></th></tr></thead><tbody>"
            + righe + "</tbody></table></div>"
            "<p class='oc-nota'><b>Come leggere.</b> Abbiamo preso tutti i giorni dal 1990 in cui la paura sul mercato era simile a quella di oggi e abbiamo guardato cosa è successo dopo. "
            "«Fascia probabile» vuol dire: in 8 casi su 10 il risultato è stato dentro questi due numeri; in 1 caso su 10 è andata peggio, in 1 su 10 meglio. "
            "I numeri sono sulla Borsa americana (S&amp;P 500), che pesa per più di metà dentro VWCE; in euro conta anche il cambio. "
            "Non è una previsione della direzione: nelle prove nessun metodo ha saputo dire in anticipo se il mercato sale o scende. La fascia invece regge: quando la paura è alta è davvero più larga."
            + ("<br><sup>*</sup> Su questo orizzonte la fascia non è risultata più precisa della semplice storia passata." if any(not (reg.get(r["nome"]) or {}).get("regge", True) for r in fs) else "") + "</p>")


def _barra(nome: str, val, col: str) -> str:
    w = 0 if val is None else max(0, min(100, val))
    return f"<div class='oc-b'><span>{E(nome)}</span><div class='oc-bb'><i style='width:{w:.0f}%;background:{col}'></i></div><b>{_n(val, 0)}</b></div>"


def dettaglio_occasione(o: dict) -> str:
    if o.get("occasione") is None:
        return ""
    vp = "".join(_barra(occasione.VOCI_P[k], x, "#dc2626") for k, x in (o.get("voci_panico") or {}).items() if x is not None)
    vs = "".join(_barra(occasione.VOCI_S[k], x, "#16a34a") for k, x in (o.get("voci_svolta") or {}).items() if x is not None)
    sc = "".join(f"<tr><td>−{s['calo']}% dal massimo</td><td>{_n(s['livello'], 0)}</td><td>{'già toccato' if s['manca'] >= 0 else 'manca ancora ' + _n(s['manca'], 1) + '%'}</td></tr>" for s in o.get("scaglioni") or [])
    return ("<div class='oc-2'><div><h4>Panico <small>quanto è stata forte la discesa negli ultimi 3 mesi</small></h4>"
            + _barra("Panico (massimo degli ultimi 3 mesi)", o.get("panico_rec"), "#dc2626") + _barra("Panico di oggi", o.get("panico"), "#dc2626") + "<div class='oc-voci'>" + vp + "</div></div>"
            "<div><h4>Svolta <small>segni che la discesa si sta esaurendo</small></h4>" + _barra("Svolta di oggi", o.get("svolta"), "#16a34a") + "<div class='oc-voci'>" + vs + "</div></div></div>"
            "<p class='oc-nota'>L'Indice Occasione è il più basso tra «Panico degli ultimi 3 mesi» e «Svolta»: servono tutti e due. "
            "Senza panico non c'è sconto; senza svolta si rischia di comprare mentre si scende ancora («coltello che cade»).</p>"
            f"<h4>Livelli da tenere d'occhio <small>S&amp;P 500 oggi {_n(o.get('sp'), 0)}, massimo dell'anno {_n(o.get('massimo'), 0)}</small></h4>"
            "<div class='scroll'><table class='oc-tab'><thead><tr><th>Sconto</th><th>Livello dell'S&amp;P 500</th><th>Distanza da oggi</th></tr></thead><tbody>" + sc + "</tbody></table></div>")


def pagella(v: dict) -> str:
    if not v.get("epoche"):
        return ""
    righe = ""
    for e in v["epoche"]:
        t, a = e.get("tutti", {}), e.get("occ50", {})
        if "m12" not in a:
            continue
        ok = a["m12"] > t.get("m12", 0) and a["pos12"] >= t.get("pos12", 0) - 5
        righe += (f"<tr><td><b>{e['periodo']}</b></td><td>{a.get('gruppi', 0)}</td><td>{_n(a['m12'], 1, True)}% <small>contro {_n(t.get('m12'), 1, True)}% di un giorno qualsiasi</small></td>"
                  f"<td>{a['pos12']}% <small>contro {t.get('pos12')}%</small></td><td class='{'oc-ok' if ok else 'oc-ko'}'>{'ha funzionato' if ok else 'non ha funzionato'}</td></tr>")
    ep = ""
    for r in v.get("episodi") or []:
        if "primo" not in r:
            ep += f"<tr><td>{r['massimo'][:4]}</td><td>{_n(r['calo'], 0)}%</td><td colspan='3'>nessun segnale</td></tr>"
            continue
        quando = f"{abs(r['sedute_dal_minimo'])} sedute {'dopo' if r['sedute_dal_minimo'] >= 0 else 'PRIMA'} del minimo"
        cls = "oc-ko" if r["discesa_dopo"] < -10 else "oc-ok"
        ep += (f"<tr><td>{r['minimo'][:4]}</td><td>{_n(r['calo'], 0)}%</td><td>{quando}</td><td>{_n(r['sopra_minimo'], 0, True)}%</td>"
               f"<td class='{cls}'>{'nessuna' if r['discesa_dopo'] == 0 else _n(r['discesa_dopo'], 0) + '%'}</td></tr>")
    s = (v.get("soldi") or {}).get("1990-2021") or {}
    soldi = ""
    if s:
        soldi = (f"<h4>Aspettare l'occasione con i soldi fermi conviene?</h4><p class='oc-nota'><b>In media no.</b> Prova su {s['arrivi']} arrivi di denaro, uno al mese dal 1990 al 2021, con il risultato dopo 5 anni. "
                 f"Chi ha aspettato il segnale di occasione (al massimo un anno) ha chiuso in media {_n(s['attesa']['media'], 1)}% rispetto a chi ha investito subito, e ha fatto meglio solo {s['attesa']['vince']} volte su 100. "
                 f"Chi ha diviso in 12 rate mensili: {_n(s['rate']['media'], 1)}%, meglio {s['rate']['vince']} volte su 100. Il motivo: mentre si aspetta, il mercato di solito sale. "
                 "Quindi l'indice non serve a tenere soldi fermi in attesa: serve a riconoscere i momenti in cui uno sforzo in più, se puoi farlo, è stato pagato meglio.</p>")
    return ("<h4>Quanto ha funzionato in passato <small>segnale = Indice Occasione da 50 in su</small></h4>"
            "<div class='scroll'><table class='oc-tab'><thead><tr><th>Periodo</th><th>Occasioni</th><th>Rendimento tipico nei 12 mesi dopo</th><th>Volte in positivo dopo 12 mesi</th><th>Giudizio</th></tr></thead><tbody>"
            + righe + "</tbody></table></div>"
            "<p class='oc-nota'><b>Come leggere.</b> Ha funzionato bene nei cali veloci e nelle crisi brevi. Non ha funzionato nei ribassi lunghi (1929-1932, 2000-2002 e in parte 2008), "
            "dove il mercato ha fatto più rimbalzi falsi prima del minimo vero. Prima del 1990 la paura è misurata dalle oscillazioni dei prezzi, perché l'indice della paura non esisteva.</p>"
            "<h4>Dove è scattato nei grandi cali dal 1990</h4><div class='scroll'><table class='oc-tab'><thead><tr><th>Anno del minimo</th><th>Calo totale</th><th>Primo segnale</th>"
            "<th>Prezzo rispetto al minimo</th><th>Altra discesa dopo il segnale</th></tr></thead><tbody>" + ep + "</tbody></table></div>" + soldi)


def html() -> str:
    """Scheda per la pagina Oggi."""
    o, v = carica()
    if not o or o.get("occasione") is None:
        return ""
    return (CSS + "<section class='b5'><div class='oc'><h3>La bussola di oggi <small>salute, fase del mercato e occasioni per le entrate extra</small></h3>"
            f"<div class='oc-g'>{_tessere(o, v)}</div><p class='oc-msg'><b>Per le entrate extra:</b> {consiglio(o)}</p>"
            "<details class='oc-d'><summary>Cosa può succedere da qui: fasce per 1 settimana, 1, 3, 6 e 12 mesi</summary>" + tabella_fasce(o, v) + "</details>"
            "<details class='oc-d'><summary>Indice Occasione: come è fatto oggi e i livelli da tenere d'occhio</summary>" + dettaglio_occasione(o) + "</details>"
            "<details class='oc-d'><summary>Le prove: quanto ha funzionato in passato (anche dove ha sbagliato)</summary>" + pagella(v) + "</details>"
            f"<p class='oc-fine'>Dati al {E('/'.join(reversed(str(o.get('data')).split('-'))))}. Osservazioni sul passato, non previsioni e non consigli. Regole scritte prima delle prove in PROTOCOLLO_OCCASIONE.md.</p></div></section>")


def previsioni_html() -> str:
    """Scheda per la pagina Previsioni: fase e fasce per orizzonte."""
    o, v = carica()
    tab = tabella_fasce(o, v) if o else ""
    if not tab:
        return ""
    f = o.get("fasi") or {}
    nome = fasi.FASI.get(f.get("tendenza"), ("n.d.", ""))[0]
    return (CSS + f"<div class='card oc'><h3 style='margin-top:0'>Fase del mercato e fasce per orizzonte <small>fase di oggi: {E(nome)}, oscillazioni {E(UMORE.get(f.get('umore'), 'nella norma'))}</small></h3>" + tab + "</div>")


CSS = ("<style>.oc h3{margin:0 0 8px}.oc h3 small,.oc h4 small{font-size:12px;color:var(--mu);font-weight:500;margin-left:6px}.oc h4{margin:14px 0 6px;font-size:14px}"
       ".oc-g{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}@media(max-width:900px){.oc-g{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){.oc-g{grid-template-columns:1fr}}"
       ".oc-t{position:relative;border:1px solid var(--bd);border-top:4px solid var(--c);border-radius:12px;padding:8px 10px 9px;background:var(--bg);display:flex;flex-direction:column;gap:2px}"
       ".oc-tt{font-size:11.5px;color:var(--mu);font-weight:700;text-transform:uppercase;letter-spacing:.3px}.oc-v{font-size:24px;font-weight:800;line-height:1.1;color:var(--c)}.oc-v small{font-size:12px;color:var(--mu);font-weight:600}"
       ".oc-chip{align-self:flex-start;font-weight:800;font-size:12px;padding:1px 9px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);background:color-mix(in srgb,var(--c) 13%,transparent)}"
       ".oc-tn{font-size:11.5px;color:var(--mu);line-height:1.4}.oc-msg{font-size:13.5px;line-height:1.5;margin:10px 0 6px;padding:9px 11px;border-radius:10px;background:var(--bg);border-left:4px solid var(--ac)}"
       ".oc-d{border:1px solid var(--bd);border-radius:10px;margin-top:6px;padding:0 10px}.oc-d>summary{cursor:pointer;font-weight:700;font-size:13.5px;padding:9px 0}.oc-d[open]{padding-bottom:10px}"
       ".oc-tab{font-size:13px}.oc-tab small{display:block;font-size:10.5px;color:var(--mu);font-weight:500}.oc-tab th{vertical-align:bottom}.oc-nota{font-size:12px;color:var(--mu);line-height:1.5;margin:8px 0 4px}"
       ".oc-ok{color:var(--ok);font-weight:700}.oc-ko{color:var(--bad);font-weight:700}.oc-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:640px){.oc-2{grid-template-columns:1fr}}"
       ".oc-b{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) 28px;align-items:center;gap:8px;font-size:12.5px;margin:4px 0}.oc-b b{text-align:right}"
       ".oc-bb{height:8px;border-radius:99px;background:var(--bd);overflow:hidden}.oc-bb i{display:block;height:100%;border-radius:99px}.oc-voci{margin-top:6px;padding-top:4px;border-top:1px dashed var(--bd)}"
       ".oc-voci .oc-b{font-size:11.5px;color:var(--mu)}.oc-fine{font-size:11px;color:var(--mu);margin:8px 0 0}</style>")
