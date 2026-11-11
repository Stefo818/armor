# -*- coding: utf-8 -*-
"""Riquadro «Da quanto tempo l'indice Armor è sopra 40?» (sostituisce i passi 1-3 del regime di tensione).

Cosa mostra, in modo semplice:
  - da quante sedute di Borsa di fila l'indice è sopra (o sotto) 40;
  - per le ultime 10, 30, 90 e 120 sedute: quante volte è stato sopra 40 e qual è la media;
  - un giudizio in tre parole: sotto stress, in ripresa, neutro.
40 è la soglia di ingresso nella zona di stress della scala Armor (1 = ottimo, 100 = pericolo massimo).

Le regole del giudizio sono fisse e descrittive (non sono una previsione):
  sotto stress  = oggi sopra 40 e media delle ultime 10 sedute sopra 40;
  in ripresa    = oggi sotto 40, almeno 5 sedute sopra 40 nelle ultime 30 e media a 10 sedute più bassa di quella a 30;
  neutro        = tutti gli altri casi.
"""
import html as _h

import pandas as pd

SOGLIA = 40.0
FINESTRE = (10, 30, 90, 120)
COL = {"stress": "#dc2626", "ripresa": "#0d9488", "neutro": "#64748b"}
NOME = {"stress": "Mercato sotto stress", "ripresa": "Mercato in ripresa", "neutro": "Mercato neutro"}


def _it(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def classifica(oggi: float, fin: dict) -> str:
    if oggi >= SOGLIA and fin[10]["media"] >= SOGLIA:
        return "stress"
    if oggi < SOGLIA and fin[30]["sopra"] >= 5 and fin[10]["media"] < fin[30]["media"]:
        return "ripresa"
    return "neutro"


def metriche(a: pd.Series) -> dict | None:
    a = a.dropna()
    if len(a) < max(FINESTRE):
        return None
    v = a.values.astype(float)
    oggi = float(v[-1])
    sopra = oggi >= SOGLIA
    di_fila = 0
    for x in v[::-1]:
        if (x >= SOGLIA) == sopra:
            di_fila += 1
        else:
            break
    fin = {}
    for k in FINESTRE:
        w = v[-k:]
        fin[k] = {"sopra": int((w >= SOGLIA).sum()), "n": int(len(w)), "media": float(w.mean())}
    return {"data": str(a.index[-1].date()), "oggi": oggi, "sopra": sopra, "di_fila": int(di_fila), "fin": fin,
            "stato": classifica(oggi, fin), "serie": [round(float(x), 1) for x in v[-max(FINESTRE):]]}


def frase(m: dict) -> str:
    f, n, st = m["fin"], m["di_fila"], m["stato"]
    if st == "stress":
        return (f"L'indice è sopra 40 da <b>{n}</b> sedute di Borsa di fila e la media delle ultime 10 è <b>{_it(f[10]['media'])}</b>: "
                f"la tensione non è un episodio di un giorno, dura.")
    if st == "ripresa":
        return (f"L'indice è tornato sotto 40 (da <b>{n}</b> sedute), ma negli ultimi 30 giorni di Borsa è stato sopra 40 per <b>{f[30]['sopra']}</b> sedute. "
                f"La media recente (<b>{_it(f[10]['media'])}</b>) è più bassa di quella a 30 sedute (<b>{_it(f[30]['media'])}</b>): la tensione si sta riassorbendo.")
    if m["sopra"]:
        return (f"L'indice è sopra 40 solo da <b>{n}</b> {'seduta' if n == 1 else 'sedute'} e la media delle ultime 10 è ancora sotto (<b>{_it(f[10]['media'])}</b>): "
                f"per ora è un segnale isolato, non una tensione che dura.")
    return (f"L'indice è sotto 40 da <b>{n}</b> sedute di Borsa di fila: nessuna tensione prolungata. "
            f"Negli ultimi 30 giorni di Borsa è stato sopra 40 per {f[30]['sopra']} {'seduta' if f[30]['sopra'] == 1 else 'sedute'}.")


def _spark(m: dict) -> str:
    """Grafico delle ultime 120 sedute. Le scritte sono in HTML fuori dal disegno, così non si sovrappongono mai alla linea."""
    s = m["serie"]
    n = len(s)
    lo, hi = min(min(s), 30.0) - 2, max(max(s), 50.0) + 2
    W, H, L, R, T, B = 720, 90, 4, 6, 6, 4
    X = lambda i: L + (W - L - R) * i / (n - 1)
    Y = lambda v: T + (H - T - B) * (1 - (v - lo) / (hi - lo))
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s))
    y40 = Y(SOGLIA)
    area = f"{X(0):.1f},{Y(lo):.1f} {pts} {X(n - 1):.1f},{Y(lo):.1f}"
    col = COL[m["stato"]]
    guide = "".join(f"<line x1='{X(n - k):.1f}' x2='{X(n - k):.1f}' y1='{T}' y2='{H - B}' stroke='currentColor' opacity='.15' stroke-dasharray='2 3'/>" for k in (90, 30, 10))
    ticks = "".join(f"<span style='left:{(n - k) / (n - 1) * 100:.1f}%'>{k}</span>" for k in (90, 30, 10))
    return ("<div class='t4-sw'><div class='t4-lg'><span><i style='background:#dc2626'></i>indice Armor</span><span><i class='t4-d'></i>40 = soglia di stress</span>"
            "<span><i style='background:#d97706;opacity:.5'></i>tratto sopra 40</span></div>"
            f"<svg viewBox='0 0 {W} {H}' preserveAspectRatio='none' class='t4-sp' role='img' aria-label='Indice Armor, ultime 120 sedute, con la linea a 40'>"
            f"<defs><clipPath id='t4up'><rect x='0' y='0' width='{W}' height='{y40:.1f}'/></clipPath></defs>"
            f"<rect x='0' y='{y40:.1f}' width='{W}' height='{H - B - y40:.1f}' fill='#16a34a' opacity='.08'/>"
            f"<polygon points='{area}' fill='#d97706' opacity='.30' clip-path='url(#t4up)'/>{guide}"
            f"<line x1='0' x2='{W}' y1='{y40:.1f}' y2='{y40:.1f}' stroke='currentColor' stroke-dasharray='6 4' opacity='.6' vector-effect='non-scaling-stroke'/>"
            f"<polyline points='{pts}' fill='none' stroke='{col}' stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round' vector-effect='non-scaling-stroke'/></svg>"
            f"<i class='t4-pt' style='left:{X(n - 1) / W * 100:.2f}%;top:{Y(s[-1]) / H * 100:.2f}%;background:{col}'></i>"
            f"<div class='t4-ax'><span style='left:0'>120 sedute fa</span>{ticks}<span style='right:0'>oggi</span></div></div>")


def _cella(k: int, f: dict) -> str:
    q = f["sopra"] / f["n"]
    alto = f["media"] >= SOGLIA
    c = "#dc2626" if alto else "#16a34a"
    return (f"<div class='t4-c'><div class='t4-ck'>Ultime {k} sedute</div>"
            f"<div class='t4-cn'><b>{f['sopra']}</b><small> su {f['n']}</small></div><div class='t4-cl'>sopra 40</div>"
            f"<div class='t4-bar'><i style='width:{q * 100:.0f}%;background:{'#d97706' if f['sopra'] else 'transparent'}'></i></div>"
            f"<div class='t4-cm' style='color:{c}'>{'▲' if alto else '▼'} media {_it(f['media'])}</div></div>")


def html(m: dict | None) -> str:
    if not m:
        return ""
    st, col = m["stato"], COL[m["stato"]]
    dove = "sopra" if m["sopra"] else "sotto"
    n = m["di_fila"]
    return ("<div class='t4'>"
            f"<div class='t4-top'><span class='t4-chip' style='--c:{col}'><i></i>{NOME[st]}</span>"
            f"<span class='t4-big'>{dove} 40 da <b>{n}</b> {'seduta' if n == 1 else 'sedute'} di fila</span></div>"
            f"<div class='t4-t'>{frase(m)}</div>{_spark(m)}"
            f"<div class='t4-grid'>{''.join(_cella(k, m['fin'][k]) for k in FINESTRE)}</div>"
            "<div class='t4-nota'><b>Come leggerlo.</b> «Alto» vuol dire <b>sopra 40</b>: è la soglia in cui l'Indice Armor (1 = ottimo, 100 = pericolo massimo) entra nella zona di stress. "
            "Una <b>seduta</b> è un giorno di Borsa aperta. Le quattro caselle contano, per ogni periodo, quante sedute sono state sopra 40 e la media dell'indice "
            "(▲ media sopra 40, ▼ sotto). Il giudizio segue regole fisse: <b>sotto stress</b> se oggi e la media delle ultime 10 sedute sono sopra 40; <b>in ripresa</b> se oggi è sotto 40 "
            "dopo almeno 5 sedute sopra 40 negli ultimi 30 giorni e la media recente scende; <b>neutro</b> negli altri casi. Descrive la situazione, non prevede cosa succederà.</div></div>")


CSS = ("<style>.t4{margin:10px 0 4px}.t4-top{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}"
       ".t4-chip{display:inline-flex;align-items:center;gap:7px;font-weight:800;font-size:15px;padding:4px 12px 4px 9px;border-radius:99px;border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);color:var(--c)}"
       ".t4-chip i{width:10px;height:10px;border-radius:50%;background:var(--c)}.t4-big{font-size:13px;color:var(--mu)}.t4-big b{color:var(--tx);font-size:15px}"
       ".t4-t{font-size:13px;line-height:1.5;margin:7px 0 4px}.t4-sw{position:relative;margin:4px 0 6px;color:var(--tx)}.t4-sp{width:100%;height:84px;display:block}.t4-lg{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11px;color:var(--mu);margin-bottom:3px}.t4-lg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:5px;vertical-align:middle}.t4-lg i.t4-d{background:none;border-top:2px dashed var(--tx);height:0;opacity:.7}.t4-pt{position:absolute;width:10px;height:10px;border-radius:50%;margin:-5px 0 0 -5px;box-shadow:0 0 0 2px var(--card)}.t4-ax{position:relative;height:14px;font-size:10px;color:var(--mu)}.t4-ax span{position:absolute;transform:translateX(-50%);white-space:nowrap}.t4-ax span:first-child{transform:none}.t4-ax span:last-child{transform:none}"
       ".t4-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}@media(max-width:520px){.t4-grid{grid-template-columns:repeat(2,1fr)}}"
       ".t4-c{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:7px 9px}.t4-ck{font-size:10.5px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.3px}"
       ".t4-cn{margin-top:2px;line-height:1}.t4-cn b{font-size:24px;font-weight:800}.t4-cn small{font-size:11.5px;color:var(--mu)}.t4-cl{font-size:10.5px;color:var(--mu);margin-top:1px}"
       ".t4-bar{height:6px;border-radius:99px;background:var(--bd);margin:5px 0 4px;overflow:hidden}.t4-bar i{display:block;height:100%;border-radius:99px}.t4-cm{font-size:12px;font-weight:700}"
       ".t4-nota{font-size:11.5px;line-height:1.5;color:var(--mu);margin-top:8px;border-left:3px solid var(--bd);padding-left:9px}.t4-nota b{color:var(--tx)}</style>")
