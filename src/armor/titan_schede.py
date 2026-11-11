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
        return pd.read_csv(FILE, index_col=0, parse_dates=True).dropna(subset=["armor_index", "super_armor_index"])
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


def _testa(nome: str, k: str, s: pd.Series, extra: str) -> str:
    v = float(s.iloc[-1])
    i = soglie.zona(k, v)
    d1, d5, d21 = _delta(s, 1), _delta(s, 5), _delta(s, 21)
    cmp_ = "".join(f"<span>{lab}: <b>{_it(float(s.iloc[-1 - n]), 0)}</b></span>" for lab, n in (("ieri", 1), ("1 settimana fa", 5), ("1 mese fa", 21)) if len(s) > n)
    return (f"<div class='ts-h'><div><div class='ts-k'>{E(nome)}</div><div class='ts-v' style='color:{soglie.COL[i]}'>{_it(v)}<small>/100</small></div></div>"
            f"<div class='ts-hc'><span class='ts-chip' style='--c:{soglie.COL[i]}'>{soglie.NOMI[i]}</span>{_freccia(d5)}<div class='ts-cmp'>{cmp_}</div></div>"
            f"<div class='ts-hs'>{_spark([float(x) for x in s.iloc[-120:]], soglie.COL[i], 40 if k == 'armor' else 45, 260, 46)}<small>ultime 120 sedute</small></div></div>{extra}")


def _riga_pil(k: str, s: pd.Series) -> str:
    nome, cosa, sale = PIL[k]
    v = float(s.iloc[-1])
    c = "#16a34a" if v < 35 else ("#64748b" if v < 40 else ("#d97706" if v < 45 else "#dc2626"))
    d5 = _delta(s, 5)
    return (f"<details class='ts-p'><summary><span class='ts-pn'><b>{E(nome)}</b></span>{_spark([float(x) for x in s.iloc[-120:]], c, 40)}"
            f"<span class='ts-pb'><i style='width:{max(2, min(100, v)):.0f}%;background:{c}'></i></span><b class='ts-pv' style='color:{c}'>{_it(v)}</b>{_freccia(d5)}</summary>"
            f"<div class='ts-pt'><p><b>Cosa guarda.</b> {E(cosa)}</p><p><b>Come leggerlo.</b> {E(sale)} Va da 1 (nessuna tensione) a 100 (tensione massima): sopra 40 è zona di attenzione.</p></div></details>")


def super_html() -> str:
    df = dati()
    if df is None:
        return ""
    s = df["super_armor_index"]
    rig = sorted(((k, df[f"{k}_stress"]) for k in PIL), key=lambda kv: -float(kv[1].iloc[-1]))
    top = rig[0]
    extra = (f"<div class='ts-n'>Il Super Armor riunisce <b>sei pilastri</b> con lo stesso peso. Oggi quello che spinge di più il numero in alto è <b>{E(PIL[top[0]][0])}</b> "
             f"({_it(float(top[1].iloc[-1]))}); quello più tranquillo è <b>{E(PIL[rig[-1][0]][0])}</b> ({_it(float(rig[-1][1].iloc[-1]))}). Tocca un pilastro per capire cosa guarda.</div>"
             + "".join(_riga_pil(k, x) for k, x in rig))
    return CSS + "<section class='b5'><div class='ts'>" + _testa("Super Armor", "super", s, extra) + "</div></section>"


def armor_html() -> str:
    df = dati()
    if df is None:
        return ""
    s = df["armor_index"]
    extra = ("<div class='ts-n'><b>Come è fatto.</b> L'Indice Armor misura quanto, oggi, il mercato è in pericolo di calo e di nervosità. Mescola due parti: una <b>veloce</b> (30%: paura sui mercati, liquidità e segnali di rimbalzo) "
             "e una <b>lenta</b> (70%: andamento dei prezzi, ciclo del credito, valutazioni, inflazione, posizione dei grandi fondi). "
             "1 = mercato sano, 100 = pericolo massimo; <b>40 è la soglia di stress</b>. A differenza del Super Armor, non è una media dei pilastri ma un giudizio più rapido e sensibile.</div>")
    return CSS + "<section class='b5'><div class='ts'>" + _testa("Indice Armor", "armor", s, extra) + "</div></section>"


def indici_html() -> str:
    a, s = armor_html(), super_html()
    return a + s if a and s else ""


def guida_html() -> str:
    if dati() is None:
        return ""
    pil = "".join(f"<li>{E(n)}</li>" for n, _c, _s in PIL.values())
    return (CSS + "<details class='gi'><summary><i>?</i><span><b>Nuovo qui? Cosa sono questi due numeri</b><small>Indice Armor e Super Armor in 30 secondi</small></span></summary><div class='gi-b'>"
            "<p class='gi-lead'>Sono due <b>termometri del rischio</b> dell'S&amp;P 500 (le 500 maggiori aziende americane, il mercato che guida le Borse del mondo, VWCE compreso). "
            "Vanno da <b>1 (mercato sano)</b> a <b>100 (pericolo massimo)</b>. Dicono <b>quanto oggi i segnali sono preoccupanti</b>, non quando scenderà la Borsa e non cosa comprare o vendere.</p>"
            "<div class='gi-cols'><div class='gi-c' style='border-top:4px solid hsl(265,75%,68%)'><h4>Indice Armor</h4><p>Un giudizio <b>rapido e sensibile</b>: mescola una parte veloce (paura, liquidità, rimbalzi) e una lenta (prezzi, credito, valutazioni). "
            "<b>40 è la soglia di stress.</b> Zone: sotto 35 tranquillo, 35-40 neutro, 40-45 allarme, da 45 pericolo.</p></div>"
            f"<div class='gi-c' style='border-top:4px solid hsl(35,90%,55%)'><h4>Super Armor</h4><p>La <b>media di sei pilastri</b> con lo stesso peso:</p><ul>{pil}</ul>"
            "<p>Zone: sotto 35 tranquillo, 35-45 neutro, 45-55 allarme, da 55 pericolo.</p></div></div>"
            "<div class='gi-diff'><b>La differenza in una riga:</b> l'Indice Armor è il termometro veloce; il Super Armor mostra <b>da quali pilastri</b> arriva il rischio.</div>"
            "<p class='gi-lim'><b>Cosa non sono:</b> non sono consigli di investimento e non prevedono il futuro. Le zone vengono dai dati storici dal 1995 (vedi «Zone di rischio»).</p></div></details>")


CSS = ("<style>.ts{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:12px 14px}.ts-h{display:grid;grid-template-columns:auto 1fr 1.2fr;gap:6px 18px;align-items:center}"
       "@media(max-width:640px){.ts-h{grid-template-columns:1fr 1fr}.ts-hs{grid-column:1/3}}"
       ".ts-k{font-size:12px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px}.ts-v{font-size:44px;font-weight:800;line-height:1}.ts-v small{font-size:14px;color:var(--mu);font-weight:600}"
       ".ts-hc{display:flex;flex-direction:column;gap:4px;align-items:flex-start}.ts-chip{font-weight:800;font-size:13px;padding:2px 12px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);background:color-mix(in srgb,var(--c) 13%,transparent)}"
       ".ts-cmp{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:11.5px;color:var(--mu)}.ts-cmp b{color:var(--tx)}.ts-d{font-size:12px;color:var(--mu);font-weight:600}"
       ".ts-hs small{display:block;font-size:10px;color:var(--mu);text-align:right}.ts-sp{width:100%;height:46px;display:block;color:var(--tx)}"
       ".ts-n{font-size:12.5px;line-height:1.5;margin:10px 0 6px}.ts-p{border-top:1px solid var(--bd)}.ts-p summary{display:grid;grid-template-columns:150px 110px 1fr 34px 130px;gap:8px;align-items:center;padding:6px 0;cursor:pointer;list-style:none;font-size:13px}"
       ".ts-p summary::-webkit-details-marker{display:none}.ts-p .ts-sp{height:26px}.ts-pb{height:8px;border-radius:99px;background:var(--bd);overflow:hidden}.ts-pb i{display:block;height:100%;border-radius:99px}.ts-pv{text-align:right}"
       "@media(max-width:640px){.ts-p summary{grid-template-columns:1fr 70px 34px}.ts-p .ts-sp,.ts-p .ts-d{display:none}.ts-pb{grid-column:1/3}}"
       ".ts-pt{font-size:12.5px;line-height:1.5;color:var(--mu);padding:0 0 8px 4px}.ts-pt p{margin:3px 0}.ts-pt b{color:var(--tx)}</style>")
