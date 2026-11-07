"""Analisi finanziaria della situazione: unisce tono delle notizie (macro, settori, grandi società), temi, e dati dei semafori."""
import html as _h

import numpy as np

from . import news as newsmod, semafori
from .config import HZ_LABEL


def sg(x):
    return f"{x:+.2f}".replace(".", ",")


def _avg(xs):
    return float(np.mean(xs)) if xs else None


def tone(a):
    return "n.d." if a is None else ("negativo" if a <= -0.1 else ("positivo" if a >= 0.1 else "neutro"))


def financial_view(items: list[dict], pred: dict, sp) -> str:
    macro = [i for i in items if i["kind"] == "macro"]
    sect = [i for i in items if i["kind"] == "sector"]
    comp = [i for i in items if i["kind"] == "company"]
    by_sect = {}
    for i in sect:
        by_sect.setdefault(i["group"], []).append(i["sent"])
    sect_tone = {g: _avg(v) for g, v in by_sect.items()}
    # tono pesato delle società più grandi del fondo
    wsum = tsum = 0.0
    for t, name in newsmod.TOP20:
        w = newsmod.VWCE_W.get(t)
        its = [i["sent"] for i in comp if i["group"] == f"{name} ({t})"]
        if w and its:
            wsum += w
            tsum += w * float(np.mean(its))
    big = tsum / wsum if wsum else None
    m_avg = _avg([i["sent"] for i in macro])
    hist = newsmod.history_sentiment(14)
    base = float(np.mean(list(hist.values())[:-1])) if len(hist) > 3 else None
    tc = {}
    for i in macro + sect:
        for t in i["themes"]:
            tc[t] = tc.get(t, 0) + (1 if i["sent"] > -0.2 else 0) + (0 if i["sent"] > -0.2 else 1)
    top_themes = [t for t, _ in sorted(tc.items(), key=lambda kv: -kv[1])[:4]]
    neg_themes = {}
    for i in macro + sect:
        if i["label"] == "negativo":
            for t in i["themes"]:
                neg_themes[t] = neg_themes.get(t, 0) + 1
    worst = [t for t, _ in sorted(neg_themes.items(), key=lambda kv: -kv[1])[:3]]
    sem = semafori.compute(sp)
    n = semafori.overall(sem)
    stress_data = n["ba"] >= 6 or (n["ba"] + n["wa"]) >= 0.6 * max(len(sem), 1)
    parts = []
    if m_avg is not None:
        cmp_t = ""
        if base is not None:
            cmp_t = " più negativo dei giorni scorsi" if m_avg < base - 0.05 else (" più positivo dei giorni scorsi" if m_avg > base + 0.05 else " in linea con i giorni scorsi")
        parts.append(f"Il tono delle notizie macro (finanza e geopolitica) è <b>{tone(m_avg)}</b> ({sg(m_avg)}){cmp_t}.")
    if big is not None:
        parts.append(f"Le notizie sulle maggiori società del fondo (pesate per la loro importanza) hanno tono <b>{tone(big)}</b> ({sg(big)}).")
    if sect_tone:
        s_sorted = sorted(((g, v) for g, v in sect_tone.items() if v is not None), key=lambda kv: kv[1])
        parts.append(f"Settore con le notizie più deboli: <b>{_h.escape(s_sorted[0][0])}</b> ({sg(s_sorted[0][1])}); più solide: <b>{_h.escape(s_sorted[-1][0])}</b> ({sg(s_sorted[-1][1])}).")
    if worst:
        parts.append(f"I temi con più titoli negativi: {_h.escape(', '.join(worst))}.")
    ta = "".join(f"<li>{x}</li>" for x in parts)
    # incrocio con i dati
    lv = pred.get("3m", {}).get("level") or pred.get("1m", {}).get("level") or "Normale"
    cross = []
    if m_avg is not None and m_avg <= -0.1 and stress_data:
        cross.append("<b>Notizie negative e dati in tensione vanno insieme:</b> è la combinazione che storicamente ha più peso. Il rischio non è solo «percepito».")
    elif m_avg is not None and m_avg <= -0.1:
        cross.append("<b>Notizie negative ma dati ancora calmi:</b> il mercato non sta ancora prezzando un problema. Controlla se nei prossimi giorni VIX, credito e curva dei tassi iniziano a muoversi.")
    elif m_avg is not None and m_avg >= 0.1 and stress_data:
        cross.append("<b>Notizie buone ma dati in tensione:</b> l'ottimismo dei titoli non è confermato dai numeri. Prudenza.")
    else:
        cross.append("<b>Notizie e dati sono abbastanza coerenti</b> tra loro: nessuna divergenza evidente.")
    risks = [f"Semafori: {n['ba']} rossi e {n['wa']} gialli su {len(sem)}."] if sem else []
    if worst:
        risks.append(f"Temi negativi da seguire: {', '.join(worst)}.")
    opps = []
    if big is not None and big >= 0.1:
        opps.append("Le grandi società del fondo hanno notizie favorevoli: sostegno ai prezzi dell'indice.")
    if sect_tone:
        best = max(((g, v) for g, v in sect_tone.items() if v is not None), key=lambda kv: kv[1])
        if best[1] >= 0.1:
            opps.append(f"Settore con buone notizie: {best[0]}.")
    if m_avg is not None and m_avg <= -0.3:
        opps.append("Quando il pessimismo dei titoli è estremo, in passato era spesso vicino a minimi di breve: non è un segnale di acquisto, ma non va inseguito.")
    li = lambda xs: "".join(f"<li>{_h.escape(x) if '<' not in x else x}</li>" for x in xs) or "<li>—</li>"
    return ("<div class='asec'><h3>Analisi finanziaria della situazione (notizie + dati)</h3>"
            f"<ul>{ta}</ul><p>{''.join(cross)}</p>"
            f"<div class='hrow'><div class='hbox r'><h4>Rischi</h4><ul>{li(risks)}</ul></div><div class='hbox o'><h4>Opportunità</h4><ul>{li(opps)}</ul></div></div>"
            f"<p class='muted'>Livello di rischio stimato dal modello a 3 mesi: <b>{_h.escape(lv.lower())}</b>. Lettura dei titoli e delle brevi descrizioni con analisi automatica del tono "
            "(FinBERT quando disponibile): è un riassunto, non la lettura di un analista.</p></div>")
