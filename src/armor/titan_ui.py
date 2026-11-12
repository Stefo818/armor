# -*- coding: utf-8 -*-
"""Scheda «Motore Titan»: previsioni a 5 orizzonti e sei pilastri, da data/titan.json (scritto dal lavoro giornaliero).
Il numero di rischio è una probabilità stimata; il «punteggio di tendenza» NON è una probabilità: misura quanto la direzione è favorevole (0-100)."""
import html as _h
import json
from datetime import date

from .config import DATA

E = _h.escape
PILASTRI = {"p1": ("Andamento dei prezzi", "quanto il mercato è sceso dai massimi e quanto è lontano dalle sue medie"),
            "p2": ("Credito", "quanto costa prestare alle imprese: se sale, le banche sono più prudenti"),
            "p3": ("Paura sui mercati", "volatilità e tensione sulle opzioni: sale quando gli investitori si proteggono"),
            "p4": ("Rischio tra i mercati", "come si muovono insieme obbligazioni, azioni e altri mercati"),
            "p5": ("Lavoro ed economia", "richieste di sussidi e segnali di rallentamento"),
            "p6": ("Liquidità", "quanta moneta c'è nel sistema e quanto sono facili le condizioni finanziarie")}
SOGLIA_TXT = {0.05: "5%", 0.10: "10%"}
MAX_GIORNI = 6


def carica() -> dict | None:
    try:
        d = json.loads((DATA / "titan.json").read_text(encoding="utf-8"))
        if (date.today() - date.fromisoformat(d["data"])).days > MAX_GIORNI * 2:
            return None
        return d
    except Exception:  # noqa: BLE001
        return None


def _it(x: float, d: int = 0) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def livello_calo(p: float) -> tuple[str, str]:
    if p < 0.10:
        return "ok", "basso"
    if p < 0.25:
        return "wa", "nella norma"
    if p < 0.40:
        return "or", "alto"
    return "ba", "molto alto"


def tendenza(r: float) -> str:
    return "favorevole" if r >= 0.65 else ("moderata" if r >= 0.5 else "debole")


def _scheda(nome: str, x: dict) -> str:
    cl, lv = livello_calo(x["calo"])
    sg = SOGLIA_TXT.get(round(x["soglia_calo"], 2), f"{x['soglia_calo'] * 100:.0f}%")
    return (f"<div class='pvc {cl}'><div class='pvh'>{E(nome)}</div><div class='pvbig'>{_it(x['calo'] * 100)}%<small> di un calo di almeno {sg}</small></div>"
            f"<div class='pvd'>Rischio {lv}</div>"
            f"<div class='pvm'>Punteggio di tendenza: <b>{_it(x['rialzo'] * 100)}/100</b> ({tendenza(x['rialzo'])}). Non è una probabilità: dice quanto la direzione è favorevole.</div></div>")


def _pilastro(k: str, v: float) -> str:
    n, d = PILASTRI[k]
    c = "#16a34a" if v < 35 else ("#d97706" if v < 50 else "#dc2626")
    return (f"<div class='sai-cr'><div class='sai-cn'><b>{E(n)}</b><span class='sai-cv' style='color:{c}'>{_it(v)}/100</span></div>"
            f"<div style='height:7px;border-radius:99px;background:var(--bd);overflow:hidden;margin:3px 0'><i style='display:block;height:100%;width:{max(2, min(100, v)):.0f}%;background:{c}'></i></div>"
            f"<div class='mu' style='font-size:11.5px'>{E(d)}</div></div>")


def html() -> str:
    d = carica()
    if not d or not d.get("previsioni"):
        return ""
    sch = "".join(_scheda(n.capitalize() if n[0].isdigit() is False else n, x) for n, x in d["previsioni"].items())
    pil = "".join(_pilastro(k, float(v)) for k, v in d.get("pilastri", {}).items() if k in PILASTRI)
    return ("<div class='explain'><p><b>Stato di salute del mercato: motore Titan</b> · dati del " + E(d["data"]) + f". Indice Armor <b>{_it(d['armor_index'], 1)}</b>, Super Armor <b>{_it(d['super_armor'], 1)}</b>. "
            "Per ogni periodo trovi la probabilità stimata di un calo importante (5% in una settimana, 10% negli altri periodi) e un punteggio di tendenza. "
            "Sono stime ottenute provando il modello sul passato, non promesse.</p></div>"
            f"<div class='pvg'>{sch}</div>"
            "<h3>I sei pilastri dietro l'Indice Armor</h3><p class='mu'>Ogni pilastro va da 1 (nessuna tensione) a 100 (tensione massima). Sopra 40 è zona di attenzione.</p>"
            f"<div>{pil}</div>")


def bilancio_html() -> str:
    """Riquadro «cosa dice il modello nei prossimi mesi»: per ogni periodo il rischio di calo di Titan contro il rischio abituale e la tendenza."""
    d = carica()
    if not d or not d.get("previsioni"):
        return ""
    righe, voti = "", {"alto": 0, "basso": 0, "norma": 0}
    for nome, x in d["previsioni"].items():
        n = x.get("normale")
        sg = SOGLIA_TXT.get(round(x["soglia_calo"], 2), f"{x['soglia_calo'] * 100:.0f}%")
        if n:
            r = x["calo"] / n
            k = "alto" if r > 1.25 else ("basso" if r < 0.8 else "norma")
            conf = {"alto": ("bad", "rischio più alto del solito"), "basso": ("ok", "rischio più basso del solito"), "norma": ("warn", "rischio nella norma")}[k]
            if nome in ("1 mese", "3 mesi", "6 mesi"):
                voti[k] += 1
            frase = f"Di solito, in passato, un calo di almeno {sg} è arrivato in <b>{_it(n * 100)}</b> casi su 100; oggi il modello ne stima <b>{_it(x['calo'] * 100)}</b>."
            marker = f"<u style='left:{min(n * 100, 100):.0f}%'></u>"
        else:
            conf = ("warn", "rischio " + livello_calo(x["calo"])[1])
            frase = f"Il modello stima {_it(x['calo'] * 100)} casi su 100 di un calo di almeno {sg}."
            marker = ""
        w = max(2, min(100, x["calo"] * 100))
        righe += (f"<div class='bal'><div class='balh'><b>{E(nome.capitalize())}</b><span class='badge {conf[0]}'>{conf[1]}</span></div>"
                  f"<div class='tugn'><span class='dn'>Calo ≥{sg}: <b>{_it(x['calo'] * 100)}%</b></span><span class='up'>Tendenza: <b>{tendenza(x['rialzo'])}</b> ({_it(x['rialzo'] * 100)}/100)</span></div>"
                  f"<div class='tbar'><i style='width:{w:.0f}%;background:{ {'bad': '#dc2626', 'ok': '#16a34a', 'warn': '#d97706'}[conf[0]] }'></i>{marker}</div>"
                  f"<div class='mu'>{frase}</div></div>")
    nv = sum(voti.values())
    if nv:
        if voti["alto"] > voti["basso"]:
            head, hc = f"Nei prossimi 1-6 mesi il rischio di un calo importante è <b>più alto del solito</b> ({voti['alto']} periodi su {nv}).", "bad"
        elif voti["basso"] > voti["alto"]:
            head, hc = f"Nei prossimi 1-6 mesi il rischio di un calo importante è <b>più basso del solito</b> ({voti['basso']} periodi su {nv}).", "ok"
        else:
            head, hc = f"Nei prossimi 1-6 mesi il rischio di un calo importante è <b>in linea con il solito</b> ({voti['norma']} periodi su {nv}).", "warn"
    else:
        head, hc = "Stato di salute del mercato secondo Titan.", "warn"
    return (CSS_B + f"<div class='balbox'><div class='vd {hc} big'>{head}</div>{righe}</div><div class='explain'><p><b>Come leggere.</b> La barra è la probabilità stimata di un calo importante (5% in una settimana, 10% negli altri periodi); il trattino è la frequenza abituale. "
            "La tendenza è un punteggio da 0 a 100 della direzione (non una probabilità). Modello: Titan, che misura lo stato di salute del mercato (la previsione principale dei cali è di FHS+VIX).</p></div>")


CSS_B = ("<style>.tbar{position:relative;height:9px;border-radius:99px;background:var(--bd);margin:6px 0 6px;overflow:visible}.tbar i{display:block;height:100%;border-radius:99px}"
         ".tbar u{position:absolute;top:-4px;width:2px;height:17px;background:var(--tx);opacity:.7}</style>")
