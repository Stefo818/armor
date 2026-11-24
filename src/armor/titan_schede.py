# -*- coding: utf-8 -*-
"""Schede di Indice Armor e Super Armor costruite sui sei pilastri del motore Titan (data/titan_storia.csv).
Se i dati Titan non sono freschi, ogni funzione restituisce "" e l'app mostra le schede di prima."""
import html as _h

import pandas as pd

from . import soglie, titan_vista
from .config import DATA

E = _h.escape
FILE = DATA / "titan_storia.csv"
PIL = {
    "p1": ("Andamento dei prezzi", "Quanto la Borsa è scesa dai massimi dell'ultimo anno, quanto è lontana dalle sue medie di 50 e 200 giorni e se le aziende costano troppo rispetto ai loro utili.",
           "Sale quando i prezzi si indeboliscono o i valori sono molto alti."),
    "p2": ("Credito", "Quanto costa il credito alle imprese (la differenza di rendimento tra obbligazioni aziendali e titoli di Stato) e a che punto è il ciclo del credito.",
           "Sale quando le banche e i risparmiatori chiedono più interessi alle imprese: è un segnale di prudenza."),
    "p3": ("Paura sui mercati", "L'indice della paura (VIX) e la sua curva, la volatilità delle obbligazioni (MOVE), le opzioni e i salti improvvisi di nervosismo.",
           "Sale quando gli investitori pagano di più per proteggersi."),
    "p4": ("Rischio tra i mercati", "Come si muovono insieme obbligazioni, azioni e altri mercati, e cosa fanno i grandi fondi: se tutto si muove nella stessa direzione, di solito c'è stress.",
           "Sale quando i mercati perdono ordine o i grandi fondi riducono il rischio."),
    "p5": ("Lavoro ed economia", "Richieste di sussidio di disoccupazione, tensione sul credito e permessi di costruzione: i primi segnali che l'economia reale rallenta.",
           "Sale quando l'economia reale mostra segni di rallentamento."),
    "p6": ("Liquidità", "Quanta moneta circola nel sistema, quanto sono facili le condizioni finanziarie, rame contro oro, forza del dollaro e se le Borse del mondo salgono insieme.",
           "Sale quando il denaro diventa più scarso e meno facile da ottenere."),
}


def dati() -> pd.DataFrame | None:
    ok = titan_vista.serie("armor_index", pd.Timestamp.today().normalize())
    if ok is None:
        return None
    try:
        d = pd.read_csv(FILE, index_col=0, parse_dates=True).dropna(subset=["armor_index", "super_armor_index"])
        if "armor_tarato" in d:   # scala tarata: 40 difficolta', 60 pericolo, 80 rischio di crollo
            d["armor_index"] = d["armor_tarato"]
        return d
    except Exception:  # noqa: BLE001
        return None


def _it(x: float, d: int = 0) -> str:
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def _spark(v: list[float], col: str, soglia: float | None = None, w: int = 160, h: int = 34) -> str:
    lo, hi = min(v + ([soglia] if soglia else [])) - 2, max(v + ([soglia] if soglia else [])) + 2
    X = lambda i: 2 + (w - 4) * i / (len(v) - 1)
    Y = lambda x: 3 + (h - 6) * (1 - (x - lo) / (hi - lo))
    pts = " ".join(f"{X(i):.1f},{Y(x):.1f}" for i, x in enumerate(v))
    ln = f"<line x1='0' x2='{w}' y1='{Y(soglia):.1f}' y2='{Y(soglia):.1f}' stroke='currentColor' stroke-dasharray='3 3' opacity='.35'/>" if soglia else ""
    return (f"<svg viewBox='0 0 {w} {h}' preserveAspectRatio='none' class='ts-sp'>{ln}<polyline points='{pts}' fill='none' stroke='{col}' stroke-width='1.8' stroke-linejoin='round' vector-effect='non-scaling-stroke'/>"
            f"<circle cx='{X(len(v) - 1):.1f}' cy='{Y(v[-1]):.1f}' r='2.6' fill='{col}'/></svg>")


def _delta(s: pd.Series, n: int) -> float | None:
    return float(s.iloc[-1] - s.iloc[-1 - n]) if len(s) > n else None


def _freccia(d: float | None, inv: bool = True) -> str:
    if d is None or abs(d) < 0.5:
        return "<span class='ts-d'>= stabile</span>"
    sale = d > 0
    c = "#dc2626" if sale else "#16a34a"   # per questi indici salire = più rischio
    return f"<span class='ts-d' style='color:{c}'>{'▲' if sale else '▼'} {_it(abs(d), 1)} in 1 settimana</span>"


def _colp(v: float) -> str:
    return soglie.COL[0] if v < 40 else (soglie.COL[1] if v < 60 else (soglie.COL[2] if v < 80 else soglie.COL[3]))


def _mini(nome: str, k: str, s: pd.Series, nota: str) -> str:
    v = float(s.iloc[-1])
    i = soglie.zona(k, v)
    c = soglie.COL[i]
    prev = " · ".join(f"{lab} <b>{_it(float(s.iloc[-1 - n]))}</b>" for lab, n in (("ieri", 1), ("1 sett. fa", 5), ("1 mese fa", 21)) if len(s) > n)
    return (f"<div class='ts-c' data-gi='{k}'><div class='ts-ct'><span class='ts-k'>{E(nome)}</span><span class='ts-chip' style='--c:{c}'>{soglie.NOMI[i]}</span></div>"
            f"<div class='ts-cb'><div class='ts-v' style='color:{c}'>{_it(v)}<small>/100</small></div>"
            f"<div class='ts-cs'>{_spark([float(x) for x in s.iloc[-120:]], c, 40, 150, 38)}</div></div>"
            f"<div class='ts-cm'>{_freccia(_delta(s, 5))}<span class='ts-pv2'>{prev}</span></div><div class='ts-nt'>{nota}</div></div>")


APIL = {"a_paura": ("Paura sui mercati", "parte veloce"), "a_liquidita": ("Liquidità", "parte veloce"), "a_rimbalzo": ("Segnali di rimbalzo", "parte veloce"),
        "a_stress": ("Stress di mercato e credito", "parte lenta"), "a_ciclo": ("Ciclo, prezzi e valutazioni", "parte lenta")}


def _tile(i: int, k: str, s: pd.Series, nome: str | None = None, tag: str = "") -> str:
    nome = nome or PIL[k][0]
    v = float(s.iloc[-1])
    c = _colp(v)
    d = _delta(s, 5)
    fr = "" if d is None or abs(d) < 0.5 else f"<em style='color:{'#dc2626' if d > 0 else '#16a34a'}'>{'▲' if d > 0 else '▼'}{_it(abs(d), 1)}</em>"
    return (f"<button type='button' class='ts-t' data-ts='{i}' data-gi='{k}'><span class='ts-tn'>{E(nome)}</span><span class='ts-tv' style='color:{c}'>{_it(v)}</span>{fr}"
            f"<span class='ts-tb'><i style='width:{max(3, min(100, v)):.0f}%;background:{c}'></i></span>" + (f"<span class='ts-tag'>{E(tag)}</span>" if tag else "") + "</button>")


def _dett(i: int, k: str, s: pd.Series) -> str:
    nome, cosa, sale = PIL[k]
    c = _colp(float(s.iloc[-1]))
    return (f"<div class='ts-d2' data-tsd='{i}' hidden><div class='ts-d2s'>{_spark([float(x) for x in s.iloc[-120:]], c, 40, 260, 44)}<small>ultime 120 sedute</small></div>"
            f"<div><p><b>{E(nome)} · cosa guarda.</b> {E(cosa)}</p><p><b>Come leggerlo.</b> {E(sale)} Da 1 (nessuna tensione) a 100 (tensione massima); da 40 è zona di attenzione, da 60 di pericolo, da 80 di rischio di crollo.</p></div></div>")


def combo_html() -> str:
    """Scheda compatta: Indice Armor e Super Armor affiancati, sei pilastri in miniatura con dettagli a comparsa."""
    df = dati()
    if df is None:
        return ""
    a, sa = df["armor_index"], df["super_armor_index"]
    rig = sorted(((k, df[f"{k}_stress"]) for k in PIL), key=lambda kv: -float(kv[1].iloc[-1]))
    top, low = rig[0], rig[-1]
    tiles = "".join(_tile(i, k, x) for i, (k, x) in enumerate(rig))
    n_t = len(rig)
    try:   # 7° pilastro informativo: difensività dei grandi fondi (provato, non migliora il Super Armor: senza peso)
        from . import difensivita
        dj = difensivita.leggi()
        if dj and len(dj.get("ultimi", [])) > 10:
            tiles += _tile(9, "i9", pd.Series(dj["ultimi"]), "Fondi (difensività)", "senza peso")
            n_t += 1
    except Exception:  # noqa: BLE001
        pass
    arm = "".join(_tile(20 + i, k, df[k], APIL[k][0], APIL[k][1]) for i, k in enumerate(APIL) if k in df and df[k].notna().any())
    arm_html = (f"<div class='ts-ph'>I pilastri dell'Indice Armor <small>(tocca un pilastro per il grafico)</small></div><div class='ts-tg' style='--n:5'>{arm}</div>" if arm else "")
    dett = ""   # le spiegazioni dei pilastri sono nel grafico a comparsa
    return (CSS + "<section class='b5'><div class='ts'><div class='ts-g'>"
            + _mini("Indice Armor", "armor", a, "Da 40 mercato in difficoltà, da 60 in pericolo, da 80 rischio di crollo.")
            + _mini("Super Armor", "super", sa, f"Media dei sei pilastri: spinge di più <b>{E(PIL[top[0]][0])}</b> ({_it(float(top[1].iloc[-1]))}), il più tranquillo è <b>{E(PIL[low[0]][0])}</b> ({_it(float(low[1].iloc[-1]))}).")
            + "</div><div class='ts-ph'>I sei pilastri del Super Armor <small>(tocca un pilastro per il grafico)</small></div>"
            f"<div class='ts-tg' style='--n:{n_t}'>{tiles}</div>{arm_html}{dett}"
            "<details class='ts-how'><summary>Come sono fatti i due indici</summary><p><b>Indice Armor.</b> Misura quanto oggi il mercato è in pericolo di calo e di nervosità. Mescola una parte <b>veloce</b> (30%: paura sui mercati, liquidità, segnali di rimbalzo) "
            "e una <b>lenta</b> (70%: prezzi, ciclo del credito, valutazioni, inflazione, grandi fondi). <b>Super Armor.</b> È la media dei sei pilastri con lo stesso peso: mostra da dove arriva il rischio. "
            "Entrambi vanno da 1 (mercato sano) a 100 (pericolo massimo); le zone di rischio sono nella scheda «Zone di rischio».</p></details></div></section>" + JS)


def super_html() -> str:
    return combo_html()


def armor_html() -> str:
    return ""   # l'Indice Armor è nella scheda compatta insieme al Super Armor (combo_html)


def indici_html() -> str:
    return combo_html()


def guida_html() -> str:
    if dati() is None:
        return ""
    pil = "".join(f"<li>{E(n)}</li>" for n, _c, _s in PIL.values())
    return (CSS + "<details class='gi'><summary><i>?</i><span><b>Nuovo qui? Cosa sono questi due numeri</b><small>Indice Armor e Super Armor in 30 secondi</small></span></summary><div class='gi-b'>"
            "<p class='gi-lead'>Sono due <b>termometri del rischio</b> dell'S&amp;P 500 (le 500 maggiori aziende americane, il mercato che guida le Borse del mondo, VWCE compreso). "
            "Vanno da <b>1 (mercato sano)</b> a <b>100 (pericolo massimo)</b>. Dicono <b>quanto oggi i segnali sono preoccupanti</b>, non quando scenderà la Borsa e non cosa comprare o vendere.</p>"
            "<div class='gi-cols'><div class='gi-c' style='border-top:4px solid hsl(265,75%,68%)'><h4>Indice Armor</h4><p>Un giudizio <b>rapido e sensibile</b>: mescola una parte veloce (paura, liquidità, rimbalzi) e una lenta (prezzi, credito, valutazioni). "
            "<b>Le zone, tarate sulle sole crisi finanziarie dal 1986.</b> La domanda che conta è: da qui, quanto rischio di perdere ancora? "
            "Entro un mese il prezzo è sceso di almeno un altro 5% nell'<b>8%</b> dei casi sotto 40, nel <b>23%</b> fra 40 e 60, nel <b>35%</b> fra 60 e 80 e nel <b>63%</b> sopra 80. "
            "Sopra 80 però il mercato è già sceso in mediana del 20% dal massimo, e quei giorni sono tre soli episodi (1998, 2008, 2022): è la fotografia di dove sei, non la previsione di dove vai. "
            "In tutte e quattro le zone il prezzo di un mese dopo è stato in mediana più alto, non più basso: un numero alto segnala turbolenza, non discesa sicura. "
            "La scala non cambia cosa sa il modello, sposta solo dove cadono i confini.</p></div>"
            f"<div class='gi-c' style='border-top:4px solid hsl(35,90%,55%)'><h4>Super Armor</h4><p>La <b>media di sei pilastri</b> con lo stesso peso:</p><ul>{pil}</ul>"
            "<p>Zone: sotto 35 tranquillo, 35-45 neutro, 45-55 allarme, da 55 pericolo.</p></div></div>"
            "<div class='gi-diff'><b>La differenza in una riga:</b> l'Indice Armor è il termometro veloce; il Super Armor mostra <b>da quali pilastri</b> arriva il rischio.</div>"
            "<p class='gi-lim'><b>Cosa non sono:</b> non sono consigli di investimento e non prevedono il futuro. Le zone vengono dai dati storici dal 1995 (vedi «Zone di rischio»).</p></div></details>")


JS = ""

CSS = ("<style>.ts{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:10px 12px}.ts-g{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.ts-g{grid-template-columns:1fr}}"
       ".ts-c{border:1px solid var(--bd);border-radius:12px;padding:8px 10px;background:var(--bg)}.ts-ct{display:flex;justify-content:space-between;align-items:center;gap:8px}.ts-k{font-size:12px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px}"
       ".ts-chip{font-weight:800;font-size:12px;padding:1px 10px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);background:color-mix(in srgb,var(--c) 13%,transparent)}"
       ".ts-cb{display:flex;align-items:center;justify-content:space-between;gap:10px}.ts-v{font-size:38px;font-weight:800;line-height:1.1}.ts-v small{font-size:13px;color:var(--mu);font-weight:600}.ts-cs{flex:1;max-width:190px}.ts-sp{width:100%;height:38px;display:block;color:var(--tx)}"
       ".ts-cm{display:flex;flex-wrap:wrap;gap:2px 10px;font-size:11.5px;color:var(--mu)}.ts-cm b{color:var(--tx)}.ts-d{font-size:12px;font-weight:600;color:var(--mu)}.ts-nt{font-size:12px;line-height:1.4;margin-top:4px}"
       ".ts-ph{font-size:12px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin:10px 0 5px}.ts-ph small{text-transform:none;font-weight:400;letter-spacing:0}"
       ".ts-tg{display:grid;grid-template-columns:repeat(var(--n,6),1fr);gap:6px}@media(max-width:820px){.ts-tg{grid-template-columns:repeat(3,1fr)}}@media(max-width:480px){.ts-tg{grid-template-columns:repeat(2,1fr)}}"
       ".ts-t{display:grid;align-content:start;grid-template-columns:1fr auto;gap:1px 4px;text-align:left;border:1px solid var(--bd);border-radius:10px;background:var(--bg);color:var(--tx);padding:6px 8px;font:inherit;cursor:pointer;transition:.15s}"
       ".ts-tag{grid-column:1/3;font-size:10px;color:var(--mu);margin-top:2px}.ts-t:hover{border-color:var(--mu)}.ts-t.on{border-color:var(--tx);box-shadow:0 0 0 1px var(--tx)}.ts-tn{grid-column:1/3;font-size:11.5px;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
       ".ts-tv{font-size:22px;font-weight:800;line-height:1.1}.ts-t em{font-style:normal;font-size:11px;font-weight:700;align-self:end;text-align:right}.ts-tb{grid-column:1/3;height:5px;border-radius:99px;background:var(--bd);overflow:hidden;margin-top:3px}.ts-tb i{display:block;height:100%;border-radius:99px}"
       ".ts-d2{display:grid;grid-template-columns:260px 1fr;gap:12px;margin-top:8px;padding:8px 10px;border-left:3px solid var(--bd);font-size:12.5px;line-height:1.5}@media(max-width:640px){.ts-d2{grid-template-columns:1fr}}.ts-d2[hidden]{display:none}"
       ".ts-d2 p{margin:2px 0}.ts-d2s small{display:block;font-size:10px;color:var(--mu);text-align:right}.ts-d2 .ts-sp{height:44px}"
       ".ts-how{font-size:12px;color:var(--mu);margin-top:8px}.ts-how summary{cursor:pointer;font-weight:700;color:var(--tx)}.ts-how p{margin:5px 0 0;line-height:1.5}"
       '@media(max-width:560px){.ts{padding:8px 7px}.ts-g{grid-template-columns:1fr 1fr!important;gap:6px}.ts-c{padding:6px 7px}.ts-k{font-size:9.5px;letter-spacing:.2px}.ts-chip{font-size:9px;padding:0 6px;border-width:1px}.ts-cb{gap:4px}.ts-v{font-size:28px}.ts-v small{font-size:10px}.ts-cs{max-width:none}.ts-sp{height:24px}.ts-cm{font-size:9px;gap:0 6px}.ts-d{font-size:9.5px}.ts-nt{font-size:9.5px;line-height:1.25;margin-top:2px}.ts-ph{font-size:9.5px;margin:7px 0 3px}.ts-ph small{display:block;font-size:9px}.ts-tg{grid-template-columns:1fr!important;gap:3px}.ts-t{grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) 28px 46px;grid-template-areas:"n b v d" "t b v d";align-items:center;gap:0 8px;padding:4px 8px;border-radius:8px}.ts-tn{grid-area:n;grid-column:auto;font-size:11px;color:var(--tx);white-space:normal;line-height:1.12}.ts-tag{grid-area:t;grid-column:auto;font-size:8.5px;margin:0;line-height:1.1}.ts-tb{grid-area:b;grid-column:auto;height:7px;margin:0}.ts-tv{grid-area:v;font-size:17px;text-align:right}.ts-t em{grid-area:d;font-size:9.5px;text-align:left;align-self:center}.ts-how{font-size:11px}}'
       "</style>")
