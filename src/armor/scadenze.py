"""Scheda «Verifiche e scadenze» (Patch 78): quando si possono rivedere i modelli, a che punto è la raccolta dei dati e notifica quando arriva il momento.
Le date seguono le regole scritte in anticipo (PROTOCOLLO_*.md). La notifica parte una volta 7 giorni prima e una volta alla scadenza (fuori dal limite di 1 al giorno: sono pochissime all'anno)."""
import html as _h
import json
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import DATA

STATO = DATA / "scadenze_stato.json"
PROT = date(2026, 11, 10)
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
AZIONE = "Apri una chat con Claude e scrivi: «Rivediamo: {n}». Controlla i risultati e propone i miglioramenti; decidi tu."


def _it(d: date) -> str:
    return f"{d.day} {MESI[d.month - 1]} {d.year}"


def _carica() -> dict:
    try:
        return json.loads(STATO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _prima(file: str, default: date, col: str = "data") -> date:
    try:
        d = pd.read_csv(DATA / file)[col].astype(str).min()
        return date.fromisoformat(d[:10])
    except Exception:  # noqa: BLE001
        return default


def _auc(score: np.ndarray, y: np.ndarray) -> float | None:
    pos, neg = int(y.sum()), int((~y).sum())
    if pos < 1 or neg < 1:
        return None
    r = pd.Series(score).rank().values
    return float((r[y].sum() - pos * (pos + 1) / 2) / (pos * neg))


def armor_live(a: pd.Series | None = None, p: pd.Series | None = None, dal: date = PROT) -> dict | None:
    """Prova dal vivo dell'Indice Armor: giorni con esito a 3 mesi noto, eventi di calo ≥10%, AUC (None finché non ci sono eventi e non eventi)."""
    try:
        from . import store
        from .features import closed_sp500, fwd_maxdd
        a = store.load("armor_index") if a is None else a
        p = closed_sp500() if p is None else p
        a = a.dropna()
        a = a[~a.index.duplicated(keep="last")].sort_index()
        dd = fwd_maxdd(p.reindex(a.index).ffill(), 63)
        m = (a.index >= pd.Timestamp(dal)) & dd.notna().values
        n = int(m.sum())
        y = (dd[m] <= -0.10).values
        return {"giorni": n, "eventi": int(y.sum()), "auc": _auc(a[m].values, y) if n else None}
    except Exception:  # noqa: BLE001
        return None


def elenco(oggi: date | None = None, sp: pd.Series | None = None, stato: dict | None = None, live: dict | None = None) -> list[dict]:
    oggi = oggi or date.today()
    st = _carica() if stato is None else stato
    fatte = st.get("fatte", {})
    out: list[dict] = []

    def add(id_, nome, inizio, scad, cosa, regola, extra="", progresso=None, evento=False):
        giorni = None if scad is None else (scad - oggi).days
        if id_ in fatte:
            stt = "fatta"
        elif scad is None:
            stt = "attesa_evento"
        else:
            stt = "da_fare" if giorni <= 0 else "in_arrivo" if giorni <= 7 else "raccolta"
        if progresso is None and scad is not None and inizio is not None:
            progresso = min(max((oggi - inizio).days / max((scad - inizio).days, 1), 0.0), 1.0)
        out.append({"id": id_, "nome": nome, "inizio": inizio, "scadenza": scad, "giorni": giorni, "stato": stt, "progresso": progresso or 0.0,
                    "cosa": cosa, "regola": regola, "extra": extra, "azione": AZIONE.format(n=nome), "fatta_il": fatte.get(id_)})

    # Opportunità: pesi v2
    ini = _prima("opportunita_ombra_v2.csv", date(2026, 11, 7))
    try:
        ad = json.loads((DATA / "opportunita_adozione.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        ad = {}
    w1 = int(ad.get("settimane_1m", 0) or 0)
    add("opp_v2", "Opportunità: pesi v2", ini, ini + timedelta(days=84 + 28),
        "Se i nuovi pesi (v2) scelgono titoli meglio di quelli attuali (v1).",
        "Servono 12 settimane di scelte con esito a 1 mese; la v2 deve battere la v1 di almeno 0,5 punti, in entrambe le metà del periodo. Il controllo è automatico ogni sabato.",
        f"Settimane già valutate: {w1} su 12. Verdetto attuale: {ad.get('motivo', 'in raccolta')}", min(w1 / 12, 1.0))
    # Semaforo e due modelli
    ini = _prima("semaforo_rischio_stato.csv", date(2026, 11, 6))
    add("sem_6m", "Semaforo del rischio: prima valutazione", ini, ini + timedelta(days=183),
        "Se il semaforo e i due modelli (base e con la paura) stanno funzionando nei primi mesi di vita.",
        "Si guardano le stime a 1 e 3 mesi contro cosa è successo davvero. Con pochi cali veri è una valutazione provvisoria.")
    add("sem_12m", "Semaforo del rischio: valutazione completa", ini, ini + timedelta(days=365),
        "Come sopra, ma con un anno di dati: abbastanza per decidere se tenere, correggere o sostituire un modello.",
        "Si confrontano i due modelli e il semaforo con la frequenza storica normale.")
    # Regime di tensione
    ini = _prima("regime_ombra.csv", date(2026, 11, 6))
    add("regime_6m", "Regime di tensione: prime verifiche", ini, ini + timedelta(days=184),
        "Se lo stato «tensione» che registriamo ogni giorno è davvero seguito da cali nei 6 mesi dopo.",
        "Il registro in ombra usa un orizzonte di 126 sedute (circa 6 mesi): prima di allora non ci sono righe con esito noto.")
    add("regime_12m", "Regime di tensione: conclusione", ini, ini + timedelta(days=365),
        "Se il regime può diventare un indicatore ufficiale.", "Regola di adozione scritta in PROTOCOLLO_REGIME.md: diventa ufficiale solo se supera la verifica fuori campione.")
    # Grandi fondi nel Super Armor Index
    ini = _prima("grandi_fondi_badge_registro.csv", date(2026, 11, 6))
    add("fondi_6m", "Grandi fondi nel Super Armor Index", ini, ini + timedelta(days=183),
        "Se i segnali dei grandi fondi aiutano a prevedere i cali e meritano un peso nel Super Armor Index (oggi 0, in prova).",
        "Regola in PROTOCOLLO_GRANDI_FONDI.md. I dati SEC sono trimestrali: in 6 mesi sono pochi punti, quindi la prima verifica è prudente.")
    # Brevetti e bilanci trimestrali
    add("brevetti_12m", "Brevetti e bilanci trimestrali SEC", PROT, PROT + timedelta(days=365),
        "Se brevetti, ricerca e sviluppo e accelerazione dei ricavi aiutano a scegliere i titoli (oggi solo informativi, peso 0).",
        "Servono almeno 4 trimestri di dati. Entrano nei punteggi solo dopo il confronto con i pesi attuali.")
    # Indice Armor
    lv = armor_live() if live is None else live
    ex = ""
    if lv and lv["giorni"]:
        auc = "non ancora calcolabile (serve almeno un calo)" if lv["auc"] is None else f"{lv['auc']:.2f} (storico 0,72)"
        ex = f"Prova dal vivo: {lv['giorni']} giorni con esito noto, {lv['eventi']} cali di almeno il 10%; AUC {auc}."
    else:
        ex = "Prova dal vivo: ancora nessun giorno con esito a 3 mesi noto."
    add("armor_pesi", "Indice Armor: revisione dei pesi", PROT, PROT + timedelta(days=365),
        "Se i pesi delle 8 famiglie si possono migliorare con i dati nuovi.",
        "PROTOCOLLO_INDICE_ARMOR.md: si cambiano solo se nel periodo dal vivo c'è stato almeno un calo del 10% e la prova su dati separati migliora di 0,02. Altrimenti rinvio di 6 mesi.", ex)
    # Evento: primo calo ≥10%
    calo = st.get("calo")
    if calo:
        d0 = date.fromisoformat(calo)
        add("armor_evento", "Indice Armor: verifica dopo il calo", d0, d0 + timedelta(days=90),
            f"L'S&P 500 è sceso di almeno il 10% dal massimo (dal {_it(d0)}): il momento migliore per vedere se l'Indice si era acceso in tempo.",
            "Revisione straordinaria 90 giorni dopo l'inizio del calo (PROTOCOLLO_INDICE_ARMOR.md).")
    else:
        add("armor_evento", "Indice Armor: verifica dopo un calo", None, None,
            "Scatta da sola 90 giorni dopo il primo calo dell'S&P 500 di almeno il 10% dal massimo.", "Finché non c'è un calo, resta in attesa. Se la Borsa resta calma non succede nulla, ed è normale.")
    return out


def da_notificare(el: list[dict], stato: dict) -> list[dict]:
    done = set(stato.get("notificate", []))
    msgs = []
    for x in el:
        if x["stato"] in ("fatta", "attesa_evento", "raccolta"):
            continue
        k = x["id"] + (":" + stato.get("calo", "") if x["id"] == "armor_evento" else "")
        if x["stato"] == "da_fare" and k + ":due" not in done:
            msgs.append({"key": k + ":due", "title": f"Scadenza oggi: {x['nome']}", "priority": 3, "tags": ["calendar"],
                         "message": f"È arrivato il momento di rivedere «{x['nome']}». {x['azione']}"})
        elif x["stato"] == "in_arrivo" and k + ":pre" not in done:
            msgs.append({"key": k + ":pre", "title": f"Tra {x['giorni']} giorni: {x['nome']}", "priority": 2, "tags": ["calendar"],
                         "message": f"Tra {x['giorni']} giorni ({_it(x['scadenza'])}) si può rivedere «{x['nome']}»."})
    return msgs


def notifica(oggi: date | None = None, sp: pd.Series | None = None) -> int:
    """Registra l'eventuale primo calo ≥10% e invia le notifiche di scadenza (una sola volta ciascuna)."""
    oggi = oggi or date.today()
    st = _carica()
    try:
        if sp is None:
            from .features import closed_sp500
            sp = closed_sp500()
        dd = float(sp.iloc[-1] / sp.iloc[-252:].max() - 1)
        if dd <= -0.10 and not st.get("calo"):
            st["calo"] = oggi.isoformat()
    except Exception:  # noqa: BLE001
        pass
    msgs = da_notificare(elenco(oggi, stato=st, live={"giorni": 0, "eventi": 0, "auc": None}), st)
    n = 0
    if msgs and os.environ.get("NTFY_TOPIC"):
        from . import alerts
        for m in msgs:
            if alerts.send([{k: v for k, v in m.items() if k != "key"}]):
                st.setdefault("notificate", []).append(m["key"])
                n += 1
    STATO.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[scadenze] {len(msgs)} da avvisare, {n} notifiche inviate")
    return n


def segna_fatta(id_: str, oggi: date | None = None) -> bool:
    st = _carica()
    if id_ not in {x["id"] for x in elenco(oggi, stato=st, live={"giorni": 0, "eventi": 0, "auc": None})}:
        return False
    st.setdefault("fatte", {})[id_] = (oggi or date.today()).isoformat()
    STATO.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


STATI = {"da_fare": ("DA FARE ORA", "#dc2626"), "in_arrivo": ("IN ARRIVO", "#d97706"), "raccolta": ("IN RACCOLTA DATI", "#3b82f6"),
         "attesa_evento": ("IN ATTESA DI UN CALO", "#64748b"), "fatta": ("FATTA", "#16a34a")}


def banner(el: list[dict]) -> str:
    q = [x for x in el if x["stato"] in ("da_fare", "in_arrivo")]
    if not q:
        return ""
    righe = "".join(f"<li><b>{_h.escape(x['nome'])}</b> · " + ("<b>da fare ora</b>" if x["stato"] == "da_fare" else f"tra {x['giorni']} giorni ({_it(x['scadenza'])})") + "</li>" for x in q)
    return (f"<div class='banner'><b>Verifiche in scadenza</b><ul style='margin:4px 0 4px 18px;padding:0'>{righe}</ul>"
            "<a href='#verifiche' data-go='verifiche'>Apri la scheda delle scadenze ›</a></div>")


def html(el: list[dict] | None = None, oggi: date | None = None) -> str:
    oggi = oggi or date.today()
    el = elenco(oggi) if el is None else el
    E = _h.escape
    ordine = {"da_fare": 0, "in_arrivo": 1, "raccolta": 2, "attesa_evento": 3, "fatta": 4}
    el = sorted(el, key=lambda x: (ordine[x["stato"]], x["scadenza"] or date(2100, 1, 1)))
    ap = [x for x in el if x["stato"] not in ("fatta",) and x["scadenza"]]
    num = {x["id"]: i + 1 for i, x in enumerate(ap)}
    marc = ""
    for x in ap:
        pos = min(max((x["scadenza"] - oggi).days / 365, 0.0), 1.0) * 100
        marc += f"<b class='sc-pt' style='left:{pos:.1f}%;background:{STATI[x['stato']][1]}'>{num[x['id']]}</b>"
    mesi = "".join(f"<span style='left:{i / 12 * 100:.1f}%'>{MESI[(oggi.month - 1 + i) % 12]}</span>" for i in range(0, 13, 3))
    tl = (f"<div class='sc-tl'><div class='sc-bar'>{marc}</div><div class='sc-mesi'>{mesi}</div></div>"
          "<p class='sc-t'>Ogni cerchio numerato è una scadenza nei prossimi 12 mesi (stesso numero delle schede sotto). Il colore dice a che punto è.</p>")
    n_ora = sum(x["stato"] == "da_fare" for x in el)
    n_arr = sum(x["stato"] == "in_arrivo" for x in el)
    n_rac = sum(x["stato"] in ("raccolta", "attesa_evento") for x in el)
    tiles = (f"<div class='sc-tiles'><div style='border-top:4px solid #dc2626'><b>{n_ora}</b><span>da fare ora</span></div><div style='border-top:4px solid #d97706'><b>{n_arr}</b><span>in arrivo (7 giorni)</span></div>"
             f"<div style='border-top:4px solid #3b82f6'><b>{n_rac}</b><span>in raccolta dati</span></div></div>")
    cards = ""
    for x in el:
        lab, col = STATI[x["stato"]]
        n = f"<i class='sc-n' style='background:{col}'>{num[x['id']]}</i>" if x["id"] in num else f"<i class='sc-n' style='background:{col}'>·</i>"
        if x["stato"] == "fatta":
            quando = f"Fatta il {x['fatta_il']}"
        elif x["scadenza"] is None:
            quando = "Nessuna data fissa: scatta quando succede"
        else:
            g = x["giorni"]
            quando = f"{_it(x['scadenza'])} · " + ("scaduta da " + str(-g) + " giorni" if g < 0 else "oggi" if g == 0 else f"mancano {g} giorni")
        prog = (f"<div class='sc-pb'><i style='width:{x['progresso'] * 100:.0f}%;background:{col}'></i></div><div class='sc-pl'><span>raccolta dati: <b>{x['progresso'] * 100:.0f}%</b></span></div>"
                if x["scadenza"] else "")
        ex = f"<div class='sc-ex'>{E(x['extra'])}</div>" if x["extra"] else ""
        cards += (f"<div class='sc-card' style='border-left:5px solid {col}'><div class='sc-h'>{n}<b>{E(x['nome'])}</b><em style='color:{col}'>{lab}</em></div>"
                  f"<div class='sc-q'>{quando}</div>{prog}{ex}"
                  f"<details><summary>Cosa si controlla e cosa fare</summary><div class='sc-d'><p><b>Cosa si controlla.</b> {E(x['cosa'])}</p><p><b>Regola decisa in anticipo.</b> {E(x['regola'])}</p>"
                  f"<p><b>Cosa fare.</b> {E(x['azione'])}</p></div></details></div>")
    info = ("<details class='sc-info'><summary><i>i</i> Come funzionano le scadenze e gli avvisi</summary><div><p>Ogni modello ha una regola scritta <b>prima</b> di vedere i risultati: quanti dati servono e quando si decide. "
            "Questa scheda conta quanti dati sono stati raccolti e dice quando si può rivedere.</p><p>Sul telefono ricevi un avviso <b>7 giorni prima</b> e uno <b>il giorno della scadenza</b> (solo se hai attivato gli avvisi). "
            "Gli avvisi sono pochi: a volte nessuno per mesi.</p><p>«Rivedere» non vuol dire cambiare: se i risultati non bastano, il modello resta com'è.</p></div></details>")
    return (CSS + "<h2>Verifiche e scadenze</h2><div class='explain'><p>Quando possiamo <b>rivedere e migliorare</b> ogni modello di Armor, e a che punto è la raccolta dei dati. "
            "Prima di quella data i dati sono troppo pochi per giudicare: cambiare presto vorrebbe dire adattarsi al caso.</p></div>" + tiles + tl + cards + info)


CSS = """<style>
.sc-tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}.sc-tiles div{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px 10px;text-align:center}
.sc-tiles b{display:block;font-size:30px;font-weight:800;line-height:1.1}.sc-tiles span{font-size:11.5px;color:var(--mu)}
.sc-tl{margin:14px 6px 4px}.sc-bar{position:relative;height:10px;border-radius:99px;background:var(--bd)}.sc-pt{position:absolute;top:-8px;width:26px;height:26px;margin-left:-13px;border-radius:50%;color:#fff;font-size:12px;line-height:26px;text-align:center;border:2px solid var(--card);box-sizing:border-box}
.sc-mesi{position:relative;height:18px;margin-top:14px;font-size:10.5px;color:var(--mu)}.sc-mesi span{position:absolute;transform:translateX(-50%)}
.sc-t{font-size:12.5px;line-height:1.5;color:var(--mu);margin:6px 0}
.sc-card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:10px 14px;margin:10px 0}.sc-h{display:flex;align-items:center;gap:8px;font-size:15px;flex-wrap:wrap}.sc-h em{font-style:normal;font-size:11px;font-weight:800;margin-left:auto}
.sc-n{display:inline-block;width:22px;height:22px;border-radius:50%;color:#fff;font-style:normal;font-size:12px;line-height:22px;text-align:center;flex:none}
.sc-q{font-size:13.5px;margin:6px 0}.sc-pb{height:8px;border-radius:99px;background:var(--bd);overflow:hidden}.sc-pb i{display:block;height:100%;border-radius:99px}.sc-pl{font-size:11.5px;color:var(--mu);margin-top:3px}
.sc-ex{font-size:12.5px;color:var(--mu);margin-top:6px;line-height:1.5}.sc-card details{margin-top:8px;font-size:13px}.sc-card summary{cursor:pointer;font-weight:700}.sc-d p{margin:6px 0;line-height:1.5}
.sc-info{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:10px 0;font-size:13px;line-height:1.5}.sc-info summary{cursor:pointer;font-weight:700}
.sc-info summary i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:50%;background:var(--tx);color:var(--bg);font-style:normal;font-size:12px;margin-right:6px}.sc-info p{margin:8px 0}
</style>"""
