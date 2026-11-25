"""Scheda «Quadro di oggi»: Indice Armor, Super Armor, Status index (Crollo, Minimi, Stato), Sick Index (Bolla, Credito) su una sola riga.

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
SOPRA60 = {"Indice Armor": (44.7, 26), "Super Armor": (54.8, 17)}   # il Crollo e' cambiato il 25/11/2026: va rimisurato
BASE_3M = 16.8
# etichette piccole sotto ogni indice; per l'Indice crollo l'unico orizzonte che ha retto alla verifica e' la settimana
SOTTO = {"Indice Armor": "Salute mercato", "Super Armor": "Economia nei prossimi mesi",
         "Indice crollo": "Rischio di crollo, prossima settimana"}
BREVE_ZONA = {"minimi": ["Lontano dai minimi", "Passaggio", "Discesa possibile", "Verso un minimo", "Discesa in corso"],
              "stato": ["Solido", "Passaggio", "Fragile", "Molto fragile", "Estremo"]}


def _col(v: float) -> str:
    return "#8b5cf6" if v >= 80 else ("#ef4444" if v >= 60 else ("#f59e0b" if v >= 40 else "#22c55e"))


def _col5(v: float) -> str:
    """Colori dello Status index: stesse fasce dell'Indice crollo (35 / 40 / 60 / 80), valore sul limite nella fascia piu' bassa."""
    return "#8b5cf6" if v > 80 else ("#ef4444" if v > 60 else ("#f59e0b" if v > 40 else ("#9ca3af" if v > 35 else "#22c55e")))


def _freccia(dv: float) -> str:
    """Freccia accanto al numero: rossa in su se il rischio sale, verde in giù se scende, assente se stabile."""
    if abs(dv) < 2:
        return "<span class='qd-a' title='Stabile nell&#39;ultima settimana' style='color:var(--mu)'>&#8594;</span>"
    su = dv > 0
    return (f"<span class='qd-a' title='{'In salita' if su else 'In discesa'} da una settimana: {dv:+.1f} punti' "
            f"style='color:{'#ef4444' if su else '#22c55e'}'>{'&#9650;' if su else '&#9660;'}</span>")


def _freschezza(data: str) -> str:
    """Dice con chiarezza a quando si riferiscono i dati: ultima chiusura di Borsa, oppure avviso se sono vecchi."""
    import datetime as _dt
    d = pd.Timestamp(data).normalize()
    oggi = pd.Timestamp.now(tz="Europe/Rome").tz_localize(None)
    # l'ultima seduta americana completa: ieri se e' un giorno feriale, altrimenti il venerdi'
    att = oggi.normalize() - pd.Timedelta(days=1)
    while att.weekday() > 4:
        att -= pd.Timedelta(days=1)
    if oggi.weekday() <= 4 and oggi.hour >= 23:   # dopo la chiusura americana anche oggi e' completo
        att = oggi.normalize()
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    et = f"{d.day} {mesi[d.month - 1]}"
    if d >= att:
        return f"ultima chiusura di Borsa: {et}"
    return f"<span style='color:var(--bad);font-weight:700'>dati fermi al {et}: da aggiornare</span>"


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
    # tendenza: oggi contro 5 sedute fa (una settimana); sotto 2 punti di differenza e' stabile
    def _tr(x):
        x = x.dropna()
        return float(x.iloc[-1] - x.iloc[-6]) if len(x) > 5 else 0.0
    tend = {"armor": _tr(d[col]), "super": _tr(d["super_armor_index"]), "crollo": _tr(st)}
    out = {"tendenza": tend, "data": str(d.index[-1].date()), "armor": arm, "super": sup, "crollo": cro, "crollo_m5": m5,
           "sopra60_5sedute": sop, "settimana_acceso": m5 >= 60}
    try:   # Minimi e Stato (status_index.py)
        from . import status_index
        si = status_index.leggi()
        if si:
            out["status"] = si["oggi"]
            out["tendenza"]["minimi"] = si["oggi"]["minimi"]["tendenza"]
            out["tendenza"]["stato"] = si["oggi"]["stato"]["tendenza"]
            if "super" in si["oggi"]:   # Super Armor versione 2 (economia dei prossimi mesi)
                out["super"] = si["oggi"]["super"]["valore"]; out["tendenza"]["super"] = si["oggi"]["super"]["tendenza"]
                out["sopra60_5sedute"]["Super Armor"] = si["oggi"]["super"]["sopra60"]
    except Exception:  # noqa: BLE001
        pass
    return out


def _tessera_sick() -> tuple[str, int]:
    """Quarto riquadro: Sick Index = Bolla + Credito (0-100). Informativo; in zona rossa mostra i casi simili del passato."""
    import html as _h
    try:
        from . import territori
        t = territori.leggi()
    except Exception:  # noqa: BLE001
        t = None
    if not t or not t.get("sick"):
        return "", 3
    celle = []
    for k, nome, sotto in (("bolla", "Bolla", "prezzi e concentrazione"), ("cred", "Credito", "stress su credito e banche")):
        d = t["sick"][k]
        v = d["valore"]
        col = "#8b5cf6" if v >= 90 else ("#ef4444" if v >= 80 else ("#f59e0b" if v >= 60 else "#22c55e"))
        rosso = v >= 80
        tit = _h.escape(territori.testo_sick(d) + " " + d["spiega"].capitalize() + ". " + d["stato"].capitalize() + ".", quote=True)
        riga = territori.riga_sick(d) if rosso else ("Nella norma" if v < 60 else "Sopra la norma, non ancora rosso")
        a = d.get("analoghi")
        breve = (f"Rosso: {a['salita_max']['med'] * 100:+.0f}% / {a['calo_max']['med'] * 100:+.0f}%" if rosso and a else ("Nella norma" if v < 60 else "Sopra la norma"))
        celle.append(f"<div class='sk' data-gi='{k}'><div class='qd-n' style='color:{col}'>{v:.0f}{_freccia(d['tendenza'])}</div><div class='qd-l'>{nome}</div>"
                     f"<div class='qd-u'>{sotto}</div><div class='qd-s' title='{tit}' style='color:{('#ef4444' if rosso else 'var(--mu)')};font-weight:{700 if rosso else 400}'><span class='lg'>{_h.escape(riga)}</span><span class='sh'>{_h.escape(breve)}</span></div></div>")
    return (f"<div class='qd-c qd-sick'><div class='sk-t'>Sick Index<span class='lg'> · il mercato è malato?</span></div>{''.join(celle)}</div>"), 5


def _tessera_status(d: dict) -> tuple[str, int]:
    """Riquadro «Status index»: Crollo, Minimi, Stato (1-100, stesse fasce di colore). Ogni cella si tocca per il grafico."""
    import html as _h
    st = d.get("status")
    if not st:
        return "", 0
    celle = []
    voci = (("crollo", "Crollo", "Rischio di crollo, prossima settimana",
             f"{d['sopra60_5sedute']['Indice crollo']}/5 sedute sopra 60", f"{d['sopra60_5sedute']['Indice crollo']}/5 sopra 60"),
            ("minimi", "Minimi", "Verso un minimo o lontano da esso?", None, None),
            ("stato", "Stato", "Quanto è fragile il terreno", None, None))
    for k, nome, sotto, lg, sh in voci:
        x = st[k]
        v = d["crollo"] if k == "crollo" else x["valore"]
        tr = d["tendenza"].get(k, 0.0)
        if lg is None:
            lg = x["zona"]
            from . import status_index as _si
            sh = BREVE_ZONA[k][_si.livello(k, v)]
        celle.append(f"<div class='sk' data-gi='{k}'><div class='qd-n' style='color:{_col5(v)}'>{v:.0f}{_freccia(tr)}</div><div class='qd-l'>{nome}</div>"
                     f"<div class='qd-u'>{_h.escape(sotto)}</div><div class='qd-s'><span class='lg'>{_h.escape(lg)}</span><span class='sh'>{_h.escape(sh)}</span></div></div>")
    return ("<div class='qd-c qd-sick qd-status' style='grid-column:span 3;grid-template-columns:repeat(3,1fr)'>"
            "<div class='sk-t'>Status index<span class='lg'> · come sta il mercato</span></div>" + "".join(celle) + "</div>"), 3


def _striscia_territori() -> str:
    try:
        from . import territori
        return territori.striscia_html()
    except Exception:  # noqa: BLE001
        return ""


def _terreno() -> str:
    try:
        from . import laboratorio
        return laboratorio.striscia_html()
    except Exception:  # noqa: BLE001
        return ""


def html() -> str:
    import html as _h
    d = leggi()
    if not d:
        return ""
    quarta, _ncs = _tessera_sick()
    nsick = 2 if quarta else 0
    status, nst = _tessera_status(d)
    due = "".join(
        f"<div class='qd-c' data-gi='{g}'><div class='qd-n' style='color:{_col(v)}'>{v:.0f}{_freccia(d['tendenza'][g])}</div><div class='qd-l'>{_h.escape(n)}</div><div class='qd-u'>{_h.escape(SOTTO[n])}</div>"
        f"<div class='qd-s'><span class='lg'>{d['sopra60_5sedute'][n]}/5 sedute sopra 60</span><span class='sh'>{d['sopra60_5sedute'][n]}/5 sopra 60</span></div></div>"
        for n, v, g in (("Indice Armor", d["armor"], "armor"), ("Super Armor", d["super"], "super")))
    if not status:   # senza i dati nuovi: come prima, con l'Indice crollo accanto agli altri due
        due += (f"<div class='qd-c' data-gi='crollo'><div class='qd-n' style='color:{_col5(d['crollo'])}'>{d['crollo']:.0f}{_freccia(d['tendenza']['crollo'])}</div>"
                f"<div class='qd-l'>Crollo</div><div class='qd-u'>{_h.escape(SOTTO['Indice crollo'])}</div><div class='qd-s'><span class='lg'>{d['sopra60_5sedute']['Indice crollo']}/5 sedute sopra 60</span>"
                f"<span class='sh'>{d['sopra60_5sedute']['Indice crollo']}/5 sopra 60</span></div></div>")
        nst = 1
    tre = due + status + quarta
    ncol = 2 + nst + nsick
    m5 = d["crollo_m5"]
    acceso = m5 >= 60
    cls = "bad" if acceso else "ok"
    tit = "Settimana a rischio sopra la norma" if acceso else "Settimana senza segnale"
    det = (f"La media a 5 sedute del Crollo è <b>{m5:.0f}</b>. Sopra 60 il calo del 3% entro cinque sedute "
           "è arrivato nel <b>17%</b> dei casi dal 2015 (nel 24% prima), contro il 6% normale." if acceso else
           f"La media a 5 sedute del Crollo è <b>{m5:.0f}</b>, sotto la soglia di 60: nessun segnale per i prossimi cinque giorni.")
    righe60 = "".join(
        f"<li>{_h.escape(n)} sopra 60 per una settimana: calo dell'8% entro tre mesi nel <b>{p:.0f}%</b> dei casi "
        f"(normale {BASE_3M:.0f}%), su {e} episodi</li>" for n, (p, e) in SOPRA60.items())
    return (
        """<style>
.qd{border:1px solid var(--bd);border-radius:14px;background:var(--card);padding:11px 13px 9px;margin:10px 0}
.qd-h{font-size:11px;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}
.qd-g{display:grid;grid-template-columns:repeat(var(--nc,3),1fr);grid-auto-rows:auto;column-gap:8px;row-gap:0;text-align:center;align-items:start}
.qd-c,.sk{display:grid;grid-row:span 4;grid-template-rows:subgrid;row-gap:0;justify-items:center;align-content:start;padding:15px 2px 4px}
.qd-sick{grid-column:span 2;grid-template-columns:1fr 1fr;column-gap:8px;position:relative;background:rgba(127,127,127,.07);border-radius:11px;padding:15px 6px 4px;align-items:start}
.qd-sick>.sk{padding:0}
.sk-t{position:absolute;top:4px;left:0;right:0;text-align:center;font-size:9.5px;letter-spacing:.5px;text-transform:uppercase;color:var(--mu)}
.qd-status{background:rgba(56,132,244,.11)}
.qd-c,.sk{min-width:0}
.sk{cursor:pointer}.qd-l{white-space:nowrap}.qd-u,.qd-s{max-width:100%}
.qd-s .sh{display:none}
@media(max-width:560px){.qd{padding:9px 8px 7px}.qd-h{font-size:9.5px;margin-bottom:4px}.qd-g{grid-template-columns:repeat(var(--nc,5),1fr)!important;column-gap:1px}
.qd .qd-n{font-size:18px}.qd .qd-a{font-size:7.5px;margin-left:1px}.qd .qd-l{font-size:9.5px;white-space:normal;line-height:1.12;margin-top:3px}.qd-u{display:none}
.qd .qd-s{font-size:8px;line-height:1.15}.qd-s .lg{display:none}.qd-s .sh{display:inline}.qd-sick .sk-t .lg{display:none}
.qd-c,.sk{padding:13px 1px 3px}.qd-sick{grid-column:span 2;margin:0;padding:13px 2px 3px;column-gap:2px;border-radius:9px}.qd-sick>.sk{padding:0}.sk-t{font-size:8.5px;top:3px}}
.qd-n{font-size:28px;font-weight:800;line-height:1}
.qd-a{font-size:15px;margin-left:5px;vertical-align:middle}
.qd-l{font-size:11.5px;font-weight:600;margin-top:2px}
.qd-u{font-size:9.5px;color:var(--mu);margin-top:1px;line-height:1.2}
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
        f"<div class='qd'><div class='qd-h'>Quadro di oggi · {_freschezza(d['data'])} · tocca un numero per il grafico · freccia = andamento in una settimana</div>"
        f"<div class='qd-g' style='--nc:{ncol}'>{tre}</div>"
        f"<div class='qd-b {cls}'><div class='qd-t'>{tit}</div><div class='qd-d'>{det}</div></div>"
        f"{_terreno()}{_striscia_territori()}"
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
        "<p><b>Le cause dei crolli «di pancia»</b> (bolle, leva, credito, obbligazioni che drenano soldi, Europa, dollaro) sono state provate dal 1971: "
        "nessuna, da sola o insieme alle altre, né un modello a punteggio, ha retto la verifica sugli ultimi anni. Sono mostrate come clima del mercato, non come previsione.</p>"
        "<p><b>Il Sovraccarico non è un indice di rischio dimostrato.</b> Misura quanto il mercato è sbilanciato su pochi titoli e sulla tecnologia "
        "e quanto in fretta lo sta diventando. Dal 1990 è un indizio che anticipa di mesi e non di giorni; prima del 1990 non funzionava. Non pesa su nessun altro indice, "
        "e ogni giorno viene registrato per verificarlo in avanti.</p>"
        "<p>Gli episodi indipendenti sono pochi (da 17 a 68): sono ordini di grandezza, non probabilità precise. "
        "E un numero alto segnala turbolenza, non discesa sicura: in tutte le fasce il prezzo di un mese dopo è stato "
        "in mediana più alto.</p>"
        "</div></details></div>")
