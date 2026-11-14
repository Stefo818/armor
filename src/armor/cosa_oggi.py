# -*- coding: utf-8 -*-
"""«Cosa fare oggi»: tre righe che riassumono minimi, fase di lungo periodo, regime di tensione e distanza dal massimo.
Regole fisse scritte in PROTOCOLLO_MINIMI.md (parte G). Non contiene importi: la decisione su quanto versare in più resta dell'utente."""
import html as _h

LIV = {0: ("ok", "bassa"), 1: ("warn", "media"), 2: ("bad", "alta")}
STATO_REG = {"calma": 0, "normale": 0, "formazione": 1, "persistente": 2, "persistente_calo": 2}
STATO_NOME = {"calma": "calma", "normale": "normale", "formazione": "tensione in formazione", "persistente": "tensione persistente", "persistente_calo": "tensione persistente con mercato in calo"}
FASE_LIV = {"sana": 0, "cara": 1, "contrazione": 2}
VER = {"probabile": 2, "possibile": 1, "non_ancora": 0}


def extra(o: dict | None, fase: str | None) -> dict:
    """Forza dell'occasione per un versamento extra."""
    if not o:
        return {"livello": "n/d", "testo": "Il radar dei minimi non è ancora disponibile.", "scale": []}
    sc = o["scale"]
    prob = [k for k, s in sc.items() if s["verdetto"] == "probabile"]
    poss = [k for k, s in sc.items() if s["verdetto"] == "possibile"]
    forte = any(k in prob for k in ("1m", "3m", "1a"))
    if fase == "contrazione":
        forte = any(k in prob for k in ("3m", "1a"))
    nomi = lambda ks: ", ".join(sc[k]["nome"] for k in ks)
    if forte:
        return {"livello": "forte", "testo": f"Minimo probabile a {nomi(prob)}: è il tipo di momento in cui un versamento extra ha più senso.", "scale": prob}
    if prob or poss:
        det = (f"minimo probabile a {nomi(prob)}" if prob else "") + (" e " if prob and poss else "") + (f"minimo possibile a {nomi(poss)}" if poss else "")
        nota = " In questa fase di lungo periodo servono segnali sulle scale più lunghe (3 mesi o 1 anno) per considerarla forte." if (fase == "contrazione" and prob) else ""
        return {"livello": "debole", "testo": f"Segnale debole: {det}.{nota}", "scale": prob + poss}
    return {"livello": "nessuna", "testo": "Nessun minimo in vista: nessuna delle quattro scale è in una zona di minimo con probabilità sufficiente.", "scale": []}


def cautela(regime: str | None, fase: str | None, dal_massimo: float | None, occasione_forte: bool) -> dict:
    liv, motivi = 0, []
    if regime in STATO_REG:
        v = STATO_REG[regime]
        liv = max(liv, v)
        if v:
            motivi.append(f"regime di tensione: {STATO_NOME[regime]}")
    if fase in FASE_LIV:
        v = 0 if (fase == "contrazione" and occasione_forte) else FASE_LIV[fase]
        liv = max(liv, v)
        if v and fase != "sana":
            motivi.append("valutazioni di lungo periodo " + ("molto alte" if fase == "contrazione" else "alte"))
    if dal_massimo is not None and dal_massimo > 0.10:
        liv = max(liv, 2)
        motivi.append(f"mercato {dal_massimo * 100:.0f}% sotto il massimo")
    k, nome = LIV[liv]
    return {"livello": nome, "classe": k, "motivi": motivi}


def calcola(minimi_usd: dict | None, minimi_eur: dict | None, fase: dict | None, regime: str | None, dal_massimo: float | None) -> dict:
    cod = (fase or {}).get("codice")
    e = extra(minimi_usd, cod)
    c = cautela(regime, cod, dal_massimo, e["livello"] == "forte")
    eur = None
    if minimi_eur:
        pe = [s["nome"] for s in minimi_eur["scale"].values() if s["verdetto"] == "probabile"]
        eur = ("In euro (VWCE): minimo probabile a " + ", ".join(pe) + ".") if pe else "In euro (VWCE): nessun minimo probabile."
    return {"extra": e, "cautela": c, "euro": eur}


CSS = """<style>
.co{border:1px solid var(--bd);border-radius:18px;background:var(--card);padding:16px 18px;margin:0 0 14px}
.co h3{margin:0 0 10px;font-size:17px}
.co .rw{display:grid;grid-template-columns:130px 1fr;gap:6px 12px;align-items:start;padding:9px 0;border-top:1px solid var(--bd)}
.co .rw:first-of-type{border-top:0}
.co .rw b{font-size:13.5px}.co .rw span.t{font-size:14.5px;line-height:1.45}
.co .chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 4px}
.co .chip{border:1px solid var(--bd);border-radius:12px;padding:6px 10px;font-size:12.5px;background:var(--bg);cursor:pointer;color:var(--tx);font:inherit;font-size:12.5px}
.co .chip.ok{border-color:var(--ok);background:var(--okbg)}.co .chip.pw{border-color:var(--warn);background:var(--warnbg)}
.co .small{font-size:12.5px;color:var(--mu);line-height:1.45}
@media(max-width:520px){.co .rw{grid-template-columns:1fr}}
</style>"""


def contesto_chips() -> str:
    """Quattro etichette di contesto (trend, crescita, affollamento, opzioni): non cambiano le regole di «extra» e «cautela»."""
    out = ""
    try:
        from . import crescita, flussi, opzioni, trend
        t, c, f, o = trend.carica(), crescita.carica(), flussi.carica(), opzioni.carica()
        if t:
            out += f"<button class='chip {'ok' if t['punteggio'] >= 2 else 'pw'}' data-go='segnali' title='Segnali di fondo'><b>Trend</b> · {t['punteggio']} segnali su 3</button>"
        if c:
            cl = {"verde": "ok", "giallo": "pw", "rosso": ""}.get(c["semaforo"]["colore"], "")
            out += f"<button class='chip {cl}' data-go='segnali' title='Segnali di fondo'><b>Crescita</b> · {c['stima']:+.1f}% stimata</button>".replace(".", ",")
        if f:
            out += f"<button class='chip' data-go='segnali' title='Segnali di fondo'><b>Affollamento</b> · {f['stato']} ({f['termometro'] * 100:.0f}°)</button>"
        if o and o.get("gex_mld") is not None:
            out += f"<button class='chip' data-go='segnali' title='Segnali di fondo'><b>Opzioni</b> · gamma {'positiva' if o['gex_mld'] >= 0 else 'negativa'}</button>"
    except Exception:  # noqa: BLE001
        return ""
    return out


def html(minimi_usd: dict | None, minimi_eur: dict | None, fase: dict | None, regime: str | None, dal_massimo: float | None) -> str:
    c = calcola(minimi_usd, minimi_eur, fase, regime, dal_massimo)
    e, ca = c["extra"], c["cautela"]
    ek = {"forte": "ok", "debole": "warn", "nessuna": "bad", "n/d": "warn"}[e["livello"]]
    en = {"forte": "Occasione forte", "debole": "Occasione debole", "nessuna": "Nessuna occasione", "n/d": "Non disponibile"}[e["livello"]]
    chips = ""
    if minimi_usd:
        for k, s in minimi_usd["scale"].items():
            cl = {"probabile": "ok", "possibile": "pw", "non_ancora": ""}[s["verdetto"]]
            lab = {"probabile": "minimo probabile", "possibile": "minimo possibile", "non_ancora": "non ancora"}[s["verdetto"]]
            chips += f"<button class='chip {cl}' data-go='minimi' title='Apri il radar dei minimi'><b>{_h.escape(s['nome'])}</b> · {lab} · {s['q'] * 100:.0f}%</button>"
    fase_txt = f"Fase di lungo periodo: <b>{_h.escape(fase['nome'])}</b>. " if fase else ""
    mot = ("Motivi: " + "; ".join(ca["motivi"]) + ".") if ca["motivi"] else "Nessun segnale di allarme tra regime di tensione, valutazioni e distanza dal massimo."
    return (CSS + "<div class='co'><h3>Cosa fare oggi</h3>"
            "<div class='rw'><b>Versamento programmato</b><span class='t'>Continua come sempre: il piano di accumulo compra a prezzi diversi e non richiede di indovinare il momento.</span></div>"
            f"<div class='rw'><b>Versamento extra</b><span class='t'><span class='badge {ek}'>{en}</span> {_h.escape(e['testo'])}</span></div>"
            f"<div class='rw'><b>Livello di cautela</b><span class='t'><span class='badge {ca['classe']}'>{ca['livello']}</span> {_h.escape(mot)}</span></div>"
            f"<div class='chips'>{chips}</div>"
            f"<div class='chips'>{contesto_chips()}</div>"
            f"<p class='small' style='margin:6px 0 0'>{fase_txt}{_h.escape(c['euro'] or '')} Chiave di lettura: «minimo probabile» = il prezzo è vicino al più basso di quella scala e la stima dice che da qui non scende molto di più. "
            "Quanto versare in più resta una tua decisione; non è un consiglio finanziario.</p></div>")
