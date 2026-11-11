# -*- coding: utf-8 -*-
"""Le quattro zone di Indice Armor e Super Armor (verde, neutra, gialla, rossa), ricavate dallo storico Titan 1995-2026.
Per ogni zona: quanti giorni l'indice ci è stato e quante volte, nei 3 mesi successivi, l'S&P 500 è sceso di almeno il 10% dal valore del giorno (in media su tutto lo storico: 15%).
Numeri calcolati da scratch/soglie_titan.py: se si rifanno i calcoli, aggiornare ZONE e BASE qui sotto."""
import html as _h

E = _h.escape
LO, HI = 20, 70  # tratto di scala disegnato nella barra
BASE = 15  # % di giorni con un calo di almeno 10% entro 3 mesi, su tutto lo storico
COL = ["#16a34a", "#64748b", "#d97706", "#dc2626"]
NOMI = ["Tranquillo", "Neutro", "Allarme", "Pericolo"]
FRASI = ["pochi segnali di tensione", "situazione nella norma", "tensione che cresce: prudenza", "stress diffuso: massima prudenza"]
# (limite alto, % giorni, % con calo ≥10% a 3 mesi, calo peggiore medio %)
ZONE = {
    "armor": {"nome": "Indice Armor", "lim": [35, 40, 45, 100], "stat": [(28, 2, -3.0), (30, 11, -4.2), (22, 20, -5.5), (20, 34, -8.2)]},
    "super": {"nome": "Super Armor", "lim": [35, 45, 55, 100], "stat": [(30, 5, -3.8), (41, 10, -4.1), (15, 30, -6.3), (13, 38, -9.1)]},
}


def zona(k: str, v: float) -> int:
    for i, lim in enumerate(ZONE[k]["lim"]):
        if v < lim:
            return i
    return 3


def _riga(k: str, v: float | None) -> str:
    z = ZONE[k]
    if v is None:
        return ""
    i = zona(k, v)
    lim = z["lim"]
    tratti = [(0, lim[0])] + [(lim[j - 1], lim[j]) for j in range(1, 3)] + [(lim[2], 100)]
    seg = "".join(f"<i style='width:{(min(b, HI) - max(a, LO)) / (HI - LO) * 100:.1f}%;background:{COL[j]};opacity:{1 if j == i else .35}'></i>" for j, (a, b) in enumerate(tratti))
    leg = "".join(
        f"<div class='sg-z{' on' if j == i else ''}' style='--c:{COL[j]}'><b>{NOMI[j]}</b><span>{'sotto ' + str(lim[0]) if j == 0 else ('da ' + str(lim[2]) + ' in su' if j == 3 else f'{lim[j - 1]}–{lim[j]}')}</span>"
        f"<em>{z['stat'][j][1]}% di calo di almeno 10% nei 3 mesi dopo</em></div>" for j in range(4))
    s = z["stat"][i]
    return (f"<div class='sg-r'><div class='sg-t'><b>{z['nome']}</b><span class='sg-v' style='color:{COL[i]}'>{v:.0f}<small>/100</small></span>"
            f"<span class='sg-chip' style='--c:{COL[i]}'>{NOMI[i]}</span></div>"
            f"<div class='sg-bar'>{seg}<u style='left:{(min(max(v, LO), HI) - LO) / (HI - LO) * 100:.1f}%'></u></div><div class='sg-sc'><span>{LO}</span><span>scala dell'indice</span><span>{HI}</span></div><div class='sg-leg'>{leg}</div>"
            f"<div class='sg-n'>Oggi sei in zona <b>{NOMI[i].lower()}</b> ({FRASI[i]}). In passato, quando l'indice era in questa zona, nei 3 mesi successivi l'S&amp;P 500 è sceso di almeno il 10% "
            f"nel <b>{s[1]}%</b> dei casi (media di sempre: {BASE}%) e il punto più basso è stato in media <b>{str(s[2]).replace('.', ',')}%</b> sotto il livello del giorno.</div></div>")


def html(armor: float | None, super_: float | None) -> str:
    if armor is None and super_ is None:
        return ""
    return (CSS + "<section class='b5'><div class='sg'><h3>Zone di rischio: dove siamo oggi</h3>"
            "<p class='sg-i'>Le soglie vengono dai dati dal 1995 a oggi: per ogni livello dell'indice abbiamo contato quante volte, nei 3 mesi dopo, la Borsa americana è calata di almeno il 10%. "
            "Verde = molto meno del solito, grigio = nella norma, giallo = più del solito, rosso = molto più del solito. È un'osservazione sul passato, non una previsione.</p>"
            + _riga("armor", armor) + _riga("super", super_) + "</div></section>")


CSS = ("<style>.sg h3{margin:0 0 4px}.sg-i{font-size:12px;color:var(--mu);line-height:1.5;margin:0 0 8px}.sg-r{margin:12px 0 14px}"
       ".sg-t{display:flex;align-items:baseline;flex-wrap:wrap;gap:6px 10px}.sg-t>b{font-size:15px}.sg-v{font-size:26px;font-weight:800}.sg-v small{font-size:12px;color:var(--mu);font-weight:600}"
       ".sg-chip{font-weight:800;font-size:12.5px;padding:2px 10px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);background:color-mix(in srgb,var(--c) 13%,transparent)}"
       ".sg-bar{position:relative;display:flex;height:14px;border-radius:99px;overflow:visible;margin:8px 0 8px}.sg-bar i{display:block;height:100%}.sg-bar i:first-child{border-radius:99px 0 0 99px}.sg-bar i:nth-child(4){border-radius:0 99px 99px 0}"
       ".sg-bar u{position:absolute;top:-4px;width:4px;height:22px;margin-left:-2px;background:var(--tx);border-radius:2px;box-shadow:0 0 0 2px var(--card)}"
       ".sg-sc{display:flex;justify-content:space-between;font-size:10px;color:var(--mu);margin:-2px 0 6px}.sg-leg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}@media(max-width:560px){.sg-leg{grid-template-columns:repeat(2,1fr)}}"
       ".sg-z{border:1px solid var(--bd);border-top:4px solid var(--c);border-radius:10px;padding:5px 8px;background:var(--bg);opacity:.75}.sg-z.on{opacity:1;box-shadow:0 0 0 1px var(--c)}"
       ".sg-z b{display:block;font-size:12.5px;color:var(--c)}.sg-z span{font-size:13px;font-weight:700}.sg-z em{display:block;font-style:normal;font-size:10.5px;color:var(--mu);line-height:1.3;margin-top:2px}"
       ".sg-n{font-size:12.5px;line-height:1.5;margin-top:8px}</style>")
