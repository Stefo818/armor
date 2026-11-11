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
    return ("<div class='explain'><p><b>Modello ufficiale: motore Titan</b> · dati del " + E(d["data"]) + f". Indice Armor <b>{_it(d['armor_index'], 1)}</b>, Super Armor <b>{_it(d['super_armor'], 1)}</b>. "
            "Per ogni periodo trovi la probabilità stimata di un calo importante (5% in una settimana, 10% negli altri periodi) e un punteggio di tendenza. "
            "Sono stime ottenute provando il modello sul passato, non promesse.</p></div>"
            f"<div class='pvg'>{sch}</div>"
            "<h3>I sei pilastri dietro l'Indice Armor</h3><p class='mu'>Ogni pilastro va da 1 (nessuna tensione) a 100 (tensione massima). Sopra 40 è zona di attenzione.</p>"
            f"<div>{pil}</div>")
