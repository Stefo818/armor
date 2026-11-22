"""Scheda «Quadro di oggi»: i tre indici e l'unico segnale che ha superato la gara.

Regole e risultati: PROTOCOLLO_GARA_INDICI.md e ESITO_GARA_INDICI.md.
Gara fra 81 candidati (3 indici x 9 misure x 3 orizzonti), scelta sul 1990-2014 e verifica sul 2015-2026,
sole crisi finanziarie. La soglia del caso (migliore su 81 con bersagli rumore, 95° percentile) e' 0,7460.

Promosso: Indice crollo, media delle ultime 5 sedute, sul bersaglio a una settimana.
AUC 0,7493 nella verifica, intervallo al 90% [0,6505 - 0,8014]; nel quinto piu' alto il calo del 3% entro
cinque sedute e' arrivato nel 18,0% dei casi contro il 6,7% di base.
A un mese e a tre mesi nessun candidato ha superato le regole: i vincitori della scelta (medie lunghe
dell'Indice Armor, 0,74-0,81) crollano a 0,54 nella verifica. Per quegli orizzonti la scheda dice che non
c'e' un segnale affidabile, e non ripiega sul meno peggio.
"""
import json

import pandas as pd

from .config import DATA

STORIA = DATA / "titan_storia.csv"
SOGLIA_PROMOSSO = 0.80   # quinto piu' alto della media a 5 sedute dell'Indice crollo, sulla scala 0-100

# numeri misurati (ESITO_GARA_INDICI.md): persistenza sopra 60 -> calo dell'8% entro tre mesi
SOPRA60 = {"Indice Armor": (44.7, 26), "Super Armor": (54.8, 17), "Indice crollo": (39.2, 68)}
BASE_3M = 16.8


def _col(v: float) -> str:
    return "#8b5cf6" if v > 80 else ("#ef4444" if v > 60 else ("#f59e0b" if v > 40 else "var(--ok)"))


def leggi() -> dict | None:
    try:
        d = pd.read_csv(STORIA, index_col=0, parse_dates=True).dropna(subset=["armor_index"])
        ic = json.loads((DATA / "indice_crollo.json").read_text(encoding="utf-8"))
        st = pd.read_csv(DATA / "indice_crollo_storia.csv", index_col=0, parse_dates=True)["indice"].dropna()
    except Exception:  # noqa: BLE001
        return None
    if d.empty or st.empty:
        return None
    u = d.iloc[-1]
    arm = float(u.get("armor_tarato", u["armor_index"]))
    sup = float(u["super_armor_index"])
    cro = float(ic["indice"])
    m5 = float(st.tail(5).mean())
    # quante delle ultime 5 sedute sopra 60, per ogni indice
    col = "armor_tarato" if "armor_tarato" in d else "armor_index"
    sop = {"Indice Armor": int((d[col].tail(5) > 60).sum()), "Super Armor": int((d["super_armor_index"].tail(5) > 60).sum()),
           "Indice crollo": int((st.tail(5) > 60).sum())}
    return {"data": str(d.index[-1].date()), "armor": arm, "super": sup, "crollo": cro, "crollo_m5": m5,
            "sopra60_5sedute": sop, "settimana_acceso": m5 >= 60}


def html() -> str:
    import html as _h
    d = leggi()
    if not d:
        return ""
    tre = "".join(
        f"<div class='qd-c' data-gi='{g}'><div class='qd-n' style='color:{_col(v)}'>{v:.0f}</div><div class='qd-l'>{_h.escape(n)}</div>"
        f"<div class='qd-s'>{d['sopra60_5sedute'][n]}/5 sedute sopra 60</div></div>"
        for n, v, g in (("Indice Armor", d["armor"], "armor"), ("Super Armor", d["super"], "super"), ("Indice crollo", d["crollo"], "crollo")))
    m5 = d["crollo_m5"]
    acceso = m5 >= 60
    cls = "bad" if acceso else "ok"
    tit = "Settimana a rischio sopra la norma" if acceso else "Settimana senza segnale"
    det = (f"La media a 5 sedute dell'Indice crollo è <b>{m5:.0f}</b>. Sopra 60 il calo del 3% entro cinque sedute "
           "è arrivato nel <b>18%</b> dei casi, contro il 7% normale." if acceso else
           f"La media a 5 sedute dell'Indice crollo è <b>{m5:.0f}</b>, sotto la soglia di 60: nessun segnale per i prossimi cinque giorni.")
    righe60 = "".join(
        f"<li>{_h.escape(n)} sopra 60 per una settimana: calo dell'8% entro tre mesi nel <b>{p:.0f}%</b> dei casi "
        f"(normale {BASE_3M:.0f}%), su {e} episodi</li>" for n, (p, e) in SOPRA60.items())
    return (
        """<style>
.qd{border:1px solid var(--bd);border-radius:14px;background:var(--card);padding:11px 13px 9px;margin:10px 0}
.qd-h{font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}
.qd-g{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}
.qd-n{font-size:28px;font-weight:800;line-height:1}
.qd-l{font-size:11.5px;font-weight:600;margin-top:2px}
.qd-s{font-size:10.5px;color:var(--mu);margin-top:1px}
.qd-b{border-left:4px solid;border-radius:8px;padding:7px 10px;margin-top:10px;background:rgba(127,127,127,.06)}
.qd-b.bad{border-color:var(--bad)}.qd-b.ok{border-color:var(--ok)}
.qd-t{font-size:13.5px;font-weight:700}.qd-d{font-size:12.5px;color:var(--mu);line-height:1.45;margin-top:2px}
.qd-d b{color:var(--tx)}
details.qdd{margin-top:8px;border-top:1px solid var(--bd);padding-top:6px}
details.qdd>summary{list-style:none;cursor:pointer;font-size:12px;color:var(--mu);display:flex;align-items:center;gap:6px}
details.qdd>summary::-webkit-details-marker{display:none}
details.qdd>summary::after{content:"";width:7px;height:7px;border-right:2px solid var(--mu);border-bottom:2px solid var(--mu);transform:rotate(45deg);transition:transform .18s}
details.qdd[open]>summary::after{transform:rotate(225deg)}
.qd-x{font-size:12.5px;color:var(--mu);line-height:1.5}
.qd-x p{margin:8px 0 0}.qd-x b{color:var(--tx)}.qd-x ul{margin:5px 0 0;padding-left:18px}
</style>""" +
        f"<div class='qd'><div class='qd-h'>Quadro di oggi · {_h.escape(d['data'])} · tocca un numero per il grafico</div>"
        f"<div class='qd-g'>{tre}</div>"
        f"<div class='qd-b {cls}'><div class='qd-t'>{tit}</div><div class='qd-d'>{det}</div></div>"
        "<details class='qdd'><summary>Cosa è stato provato, e cosa non funziona</summary><div class='qd-x'>"
        "<p><b>A un mese e a tre mesi non c'è un segnale affidabile.</b> Sono stati messi in gara 81 candidati "
        "(i tre indici per nove modi di misurarli per tre orizzonti), scegliendo sui dati fino al 2014 e verificando "
        "dal 2015 in poi, sulle sole crisi finanziarie. I vincitori a un mese e a tre mesi sembravano i migliori "
        "nella scelta (0,74 e 0,81 su 1) ma nella verifica scendono a 0,54, cioè quasi al caso. Non vengono mostrati: "
        "meglio dire che non si sa.</p>"
        "<p><b>L'unico promosso è la settimana</b>, con la media a 5 sedute dell'Indice crollo: 0,7493 nella verifica, "
        "appena sopra la soglia di 0,7460 che la migliore di 81 raggiunge per puro caso. Anche questo, quindi, è un "
        "indizio stretto e non una certezza.</p>"
        f"<p><b>Quando un indice resta sopra 60 per una settimana</b>, il calo dell'8% entro tre mesi è poi arrivato:</p><ul>{righe60}</ul>"
        "<p>Gli episodi indipendenti sono pochi (da 17 a 68): sono ordini di grandezza, non probabilità precise. "
        "E un numero alto segnala turbolenza, non discesa sicura: in tutte le fasce il prezzo di un mese dopo è stato "
        "in mediana più alto.</p>"
        "</div></details></div>")
