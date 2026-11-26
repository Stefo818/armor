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
    per = "1 settimana"
    if d is not None and abs(d) < 0.05:   # misure lente (si aggiornano di rado): si guarda l'ultimo mese, poi gli ultimi 3
        for n, lab in ((21, "1 mese"), (63, "3 mesi")):
            d2 = _delta(s, n)
            if d2 is not None and abs(d2) >= 0.05:
                d, per = d2, lab
                break
    if d is None:
        fr = ""
    elif abs(d) < 0.05:
        fr = "<em class='ts-e' title='invariato da 3 mesi'>＝</em>"
    else:   # in questi indici salire = più rischio (rosso), scendere = meno rischio (verde)
        fr = f"<em class='{'up' if d > 0 else 'dn'}' title='variazione in {per}'>{'▲' if d > 0 else '▼'} {_it(abs(d), 1)}</em>"
    return (f"<button type='button' class='ts-t' style='--c:{c}' data-ts='{i}' data-gi='{k}'><span class='ts-tn'>{E(nome)}</span><span class='ts-tv'>{_it(v)}</span>{fr}</button>")


def _dett(i: int, k: str, s: pd.Series) -> str:
    nome, cosa, sale = PIL[k]
    c = _colp(float(s.iloc[-1]))
    return (f"<div class='ts-d2' data-tsd='{i}' hidden><div class='ts-d2s'>{_spark([float(x) for x in s.iloc[-120:]], c, 40, 260, 44)}<small>ultime 120 sedute</small></div>"
            f"<div><p><b>{E(nome)} · cosa guarda.</b> {E(cosa)}</p><p><b>Come leggerlo.</b> {E(sale)} Da 1 (nessuna tensione) a 100 (tensione massima); da 40 è zona di attenzione, da 60 di pericolo, da 80 di rischio di crollo.</p></div></div>")


def _medie(s: pd.Series) -> str:
    v = s.dropna()
    return " · ".join(f"{lab} <b>{_it(float(v.iloc[-n:].mean()))}</b>" for lab, n in (("media 1 sett.", 5), ("1 mese", 21), ("3 mesi", 63)) if len(v) >= n)


def _scheda(nome: str, k: str, s: pd.Series, nota: str, tiles: str) -> str:
    """Una scheda: valore, grafico piccolo, medie e subito sotto i suoi pilastri (tutti cliccabili)."""
    s = s.dropna()
    v = float(s.iloc[-1])
    i = soglie.zona("armor", v)
    c = soglie.COL[i]
    prev = " · ".join(f"{lab} <b>{_it(float(s.iloc[-1 - n]))}</b>" for lab, n in (("ieri", 1), ("1 sett. fa", 5), ("1 mese fa", 21)) if len(s) > n)
    return (f"<div class='ts-c ts-big' data-gi='{k}'><div class='ts-ct'><span class='ts-k'>{E(nome)}</span><span class='ts-chip' style='--c:{c}'>{soglie.NOMI[i]}</span></div>"
            f"<div class='ts-cb'><div class='ts-v' style='color:{c}'>{_it(v)}<small>/100</small></div>"
            f"<div class='ts-cs'>{_spark([float(x) for x in s.iloc[-120:]], c, 40, 150, 38)}</div></div>"
            f"<div class='ts-cm'>{_freccia(_delta(s, 5))}<span class='ts-pv2'>{prev}</span></div><div class='ts-cm'><span class='ts-pv2'>{_medie(s)}</span></div>"
            f"<div class='ts-nt'>{nota}</div><div class='ts-in'>{tiles}</div></div>")


def _gruppo(titolo: str, tiles: str, n: int, tocca: bool = False) -> str:
    return f"<div class='ts-ph'>{titolo}{' <small>· tocca una misura per il grafico</small>' if tocca else ''}</div><div class='ts-tg' style='--n:{n}'>{tiles}</div>"


def _flash_html(S: dict) -> str:
    """Come è prevista l'economia e le indicazioni flash (super_armor_flash)."""
    try:
        from . import store, super_armor_flash
        r = super_armor_flash.flash(S, store.load("sp500"))
    except Exception:  # noqa: BLE001
        return ""
    if not r:
        return ""
    sp = ", ".join(f"{E(n)} <b>{_it(v)}</b>" for n, v in r["spingono"]) or "nessuna misura in zona di allarme"
    ra = ", ".join(f"{E(n)} <b>{_it(v)}</b>" for n, v in r["rassicurano"]) or "nessuna misura molto bassa"
    fl = "".join(f"<div class='fl {t}'><b>{E(a)}.</b> {E(b)}</div>" for t, a, b in r["flash"])
    return (f"<div class='ts-fr'>{E(r['frase'])}</div><div class='ts-pr'><span>Spingono in su:</span> {sp}.<br><span>Rassicurano:</span> {ra}.</div>"
            f"<details class='ts-fx'><summary>Indicazioni flash di oggi <span>{len(r['flash'])}</span></summary><div class='ts-fl'>{fl}</div></details>")


def combo_html() -> str:
    """Due schede affiancate: Indice Armor e Super Armor, ognuna con i propri pilastri dentro (cliccabili: grafico, medie, dettaglio)."""
    df = dati()
    if df is None:
        return ""
    a = df["armor_index"]
    arm = "".join(_tile(20 + i, k, df[k], APIL[k][0], APIL[k][1]) for i, k in enumerate(APIL) if k in df and df[k].notna().any())
    arm_html = _gruppo("I 5 pilastri dell'Indice Armor", arm, 5, True) if arm else ""
    try:
        from . import super_armor_2 as s2
        from . import grafico_indici as gi
        S = s2.calcola()
        nm = lambda k: getattr(gi, "_CORTI", {}).get(k) or s2.NOMI[k]
        pil = "".join(_tile(40 + i, k, S[k].dropna(), n, t) for i, (k, n, t) in enumerate((("sa_fin", "Finanza", ""), ("sa_eco", "Economia", ""), ("sa_costi", "Costi e tassi", ""), ("sa_fam", "Famiglie e mutui", ""), ("sa_pil", "PIL USA ed Europa", ""))) if k in S)
        n_p = 4
        try:   # pilastro informativo: difensività dei grandi fondi (provato, non migliora l'indice: senza peso)
            from . import difensivita
            dj = difensivita.leggi()
            if dj and len(dj.get("ultimi", [])) > 10:
                pil += _tile(9, "i9", pd.Series(dj["ultimi"]), "Fondi (difensività)", "senza peso")
                n_p = 5
        except Exception:  # noqa: BLE001
            pass
        fin = "".join(_tile(50 + i, k, S[k].dropna(), nm(k), "peso uguale") for i, k in enumerate(s2.FIN))
        eco = "".join(_tile(70 + i, k, S[k].dropna(), nm(k), "peso uguale") for i, k in enumerate(s2.ECO))
        cos = "".join(_tile(90 + i, k, S[k].dropna(), nm(k), "") for i, k in enumerate(s2.COSTI) if k in S)
        fam = "".join(_tile(100 + i, k, S[k].dropna(), nm(k), "") for i, k in enumerate(s2.FAMIGLIE) if k in S)
        sa = S["super"].dropna()
        top = max(("sa_fin", "sa_eco"), key=lambda k: float(S[k].dropna().iloc[-1]))
        nota = ("<b>Fotografa e anticipa la situazione economica.</b> Unisce i dati della <b>finanza</b> (veloci: tassi, costo del credito, Borsa; anticipano) "
                "e quelli dell'<b>economia reale</b> (lenti: lavoro, produzione, permessi, fiducia; confermano). "
                f"Vale il più alto dei due pilastri: se uno vede guai il numero sale. Oggi finanza {_it(float(S['sa_fin'].dropna().iloc[-1]))}, economia {_it(float(S['sa_eco'].dropna().iloc[-1]))}: "
                f"spinge di più {'la finanza' if top == 'sa_fin' else 'l’economia'}. Più è alto, più l'economia dei prossimi mesi rischia di rallentare.")
        sa_card = _scheda("Super Armor", "super", sa, nota,
                          _flash_html(S) + _gruppo("I pilastri (finanza ed economia decidono il numero; gli altri sono informazioni senza peso)", pil, n_p, True) + _gruppo("Le 6 misure della finanza", fin, 6)
                          + _gruppo("Le 7 misure dell'economia", eco, 7) + _gruppo("Costi e tassi (senza peso)", cos, 5) + _gruppo("Famiglie e mutui (senza peso)", fam, 7))
    except Exception:  # noqa: BLE001
        sa_card = ""
    return (CSS + "<section class='b5'><div class='ts'><div class='ts-g'>"
            + _scheda("Indice Armor", "armor", a, "Misura la salute del mercato: quanto è nervoso, quanto è sceso dai massimi, quanto sono tesi credito e liquidità. Da 40 in difficoltà, da 60 in pericolo, da 80 rischio di crollo.", arm_html)
            + sa_card
            + "</div><details class='ts-how'><summary>Come sono fatti i due indici</summary><p><b>Indice Armor.</b> Misura la salute del mercato di oggi: nervosismo, distanza dai massimi, tensione su credito e liquidità. Mescola una parte <b>veloce</b> (30%: paura sui mercati, liquidità, segnali di rimbalzo) "
            "e una <b>lenta</b> (70%: prezzi, ciclo del credito, valutazioni, inflazione, grandi fondi). <b>Super Armor.</b> Guarda avanti all'economia dei prossimi mesi: prende il più alto fra il pilastro della <b>finanza</b> (6 misure veloci, peso uguale) e quello dell'<b>economia</b> (7 misure lente, peso uguale). "
            "Entrambi vanno da 1 (sano) a 100 (pericolo massimo); le zone di rischio sono nella scheda «Zone di rischio».</p></details></div></section>" + JS)


def super_html() -> str:
    return combo_html()


def armor_html() -> str:
    return ""   # l'Indice Armor è nella scheda compatta insieme al Super Armor (combo_html)


def indici_html() -> str:
    return combo_html()


def guida_html() -> str:
    if dati() is None:
        return ""
    return (CSS + "<details class='gi'><summary><i>?</i><span><b>Nuovo qui? Cosa sono questi due numeri</b><small>Indice Armor e Super Armor in 30 secondi</small></span></summary><div class='gi-b'>"
            "<p class='gi-lead'>Sono due <b>termometri del rischio</b> dell'S&amp;P 500 (le 500 maggiori aziende americane, il mercato che guida le Borse del mondo, VWCE compreso). "
            "Vanno da <b>1 (mercato sano)</b> a <b>100 (pericolo massimo)</b>. Dicono <b>quanto oggi i segnali sono preoccupanti</b>, non quando scenderà la Borsa e non cosa comprare o vendere.</p>"
            "<div class='gi-cols'><div class='gi-c' style='border-top:4px solid hsl(265,75%,68%)'><h4>Indice Armor</h4><p>Un giudizio <b>rapido e sensibile</b>: mescola una parte veloce (paura, liquidità, rimbalzi) e una lenta (prezzi, credito, valutazioni). "
            "<b>Le zone, tarate sulle sole crisi finanziarie dal 1986.</b> La domanda che conta è: da qui, quanto rischio di perdere ancora? "
            "Entro un mese il prezzo è sceso di almeno un altro 5% nell'<b>8%</b> dei casi sotto 40, nel <b>23%</b> fra 40 e 60, nel <b>35%</b> fra 60 e 80 e nel <b>63%</b> sopra 80. "
            "Sopra 80 però il mercato è già sceso in mediana del 20% dal massimo, e quei giorni sono tre soli episodi (1998, 2008, 2022): è la fotografia di dove sei, non la previsione di dove vai. "
            "In tutte e quattro le zone il prezzo di un mese dopo è stato in mediana più alto, non più basso: un numero alto segnala turbolenza, non discesa sicura. "
            "La scala non cambia cosa sa il modello, sposta solo dove cadono i confini.</p></div>"
            f"<div class='gi-c' style='border-top:4px solid hsl(35,90%,55%)'><h4>Super Armor</h4><p>Guarda <b>l'economia dei prossimi mesi</b>: vale il più alto fra due pilastri a peso uguale al loro interno.</p><ul><li>Finanza (veloce): curve dei tassi, costo del credito, condizioni finanziarie, Borsa a 12 mesi</li><li>Economia (lenta): lavoro, produzione, permessi, fiducia</li></ul>"
            "<p>Soglie come l'Indice Armor: 40, 60, 80.</p></div></div>"
            "<div class='gi-diff'><b>La differenza in una riga:</b> l'Indice Armor misura la salute del mercato oggi; il Super Armor guarda l'economia dei prossimi mesi.</div>"
            "<p class='gi-lim'><b>Cosa non sono:</b> non sono consigli di investimento e non prevedono il futuro. Le zone vengono dai dati storici dal 1995 (vedi «Zone di rischio»).</p></div></details>")


JS = ""

CSS = ("<style>.ts{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:10px 12px}.ts-g{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:900px){.ts-g{grid-template-columns:1fr}}"
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
       ".ts-fr{font-size:14px;font-weight:800;margin:6px 0 4px}.ts-pr{font-size:12px;color:var(--mu);margin-bottom:6px}.ts-pr span{font-weight:700;color:var(--tx)}.ts-fh{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--mu);margin:8px 0 4px}.ts-fl{display:grid;gap:4px}.fl{font-size:12.5px;line-height:1.35;padding:5px 8px;border-left:4px solid var(--bd);background:var(--bg);border-radius:6px}.fl.r{border-left-color:#dc2626}.fl.a{border-left-color:#f59e0b}.fl.v{border-left-color:#16a34a}.fl.n{border-left-color:#64748b}.ts-big{cursor:pointer}.ts-in{cursor:default;margin-top:6px}.ts-in .ts-tg{grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:4px}.ts-in .ts-t{grid-template-columns:minmax(0,1fr) auto auto;align-items:center;gap:0 6px;padding:3px 8px}.ts-in .ts-tn{grid-column:auto;font-size:11px}.ts-in .ts-tv{font-size:16px}.ts-in .ts-t em{font-size:10px}.ts-fx{margin:8px 0 4px;border:1px solid var(--bd);border-radius:10px;background:var(--bg)}.ts-fx>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--mu)}.ts-fx>summary::-webkit-details-marker{display:none}.ts-fx>summary::before{content:'▸';transition:.15s;color:var(--tx)}.ts-fx[open]>summary::before{transform:rotate(90deg)}.ts-fx>summary span{margin-left:auto;font-size:10px;padding:0 7px;border-radius:99px;background:var(--bd);color:var(--tx)}.ts-fx .ts-fl{padding:0 8px 8px}.ts-in .ts-ph{margin:8px 0 4px;font-size:10.5px}.ts-in .ts-tg{grid-template-columns:repeat(auto-fill,minmax(148px,1fr))!important;gap:4px}.ts-in .ts-t{border:0;border-left:3px solid var(--c);border-radius:7px;background:color-mix(in srgb,var(--c) 8%,var(--bg));padding:3px 7px 3px 8px;grid-template-columns:minmax(0,1fr) auto auto;gap:0 6px}.ts-in .ts-t:hover{background:color-mix(in srgb,var(--c) 15%,var(--bg))}.ts-in .ts-t.on{box-shadow:0 0 0 1.5px var(--c)}.ts-in .ts-tn{color:var(--tx);opacity:.82;font-size:11px}.ts-in .ts-tv{color:var(--c);font-size:16px;font-weight:800;font-variant-numeric:tabular-nums}.ts-t em.up,.ts-t em.dn,.ts-t em.ts-e{font-style:normal;font-size:10px;font-weight:700;padding:1px 5px;border-radius:99px;white-space:nowrap;font-variant-numeric:tabular-nums;justify-self:end}.ts-t em.up{color:#dc2626;background:rgba(220,38,38,.13)}.ts-t em.dn{color:#16a34a;background:rgba(22,163,74,.14)}.ts-t em.ts-e{color:var(--mu);background:var(--bd)}.ts-how{font-size:12px;color:var(--mu);margin-top:8px}.ts-how summary{cursor:pointer;font-weight:700;color:var(--tx)}.ts-how p{margin:5px 0 0;line-height:1.5}"
       '@media(max-width:560px){.ts{padding:8px 7px}.ts-g{grid-template-columns:1fr!important;gap:8px}.ts-c{padding:6px 7px}.ts-k{font-size:9.5px;letter-spacing:.2px}.ts-chip{font-size:9px;padding:0 6px;border-width:1px}.ts-cb{gap:4px}.ts-v{font-size:28px}.ts-v small{font-size:10px}.ts-cs{max-width:none}.ts-sp{height:24px}.ts-cm{font-size:9px;gap:0 6px}.ts-d{font-size:9.5px}.ts-nt{font-size:9.5px;line-height:1.25;margin-top:2px}.ts-ph{font-size:9.5px;margin:7px 0 3px}.ts-ph small{display:block;font-size:9px}.ts-tg,.ts-in .ts-tg{grid-template-columns:1fr 1fr!important;gap:3px}.ts-t,.ts-in .ts-t{grid-template-columns:minmax(0,1fr) auto auto;grid-template-areas:"n v d";align-items:center;gap:0 8px;padding:3px 8px;border-radius:8px}.ts-tn{grid-area:n;grid-column:auto;font-size:11px;color:var(--tx);white-space:normal;line-height:1.12}.ts-tag{grid-area:t;grid-column:auto;font-size:8.5px;margin:0;line-height:1.1}.ts-tb{grid-area:b;grid-column:auto;height:7px;margin:0}.ts-tv{grid-area:v;font-size:17px;text-align:right}.ts-t em{grid-area:d;font-size:9.5px;text-align:left;align-self:center}.ts-how{font-size:11px}}'
       "</style>")
