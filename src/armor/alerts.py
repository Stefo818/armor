"""Avvisi sul telefono con ntfy (gratuito, senza account). Si inviano solo i CAMBIAMENTI importanti, mai ripetizioni.
Serve il segreto NTFY_TOPIC (un nome lungo e casuale scelto da te). Senza segreto, nessun avviso e nessun errore."""
import json
import os
from datetime import date

import requests

from .config import DATA, HZ_LABEL, VERDICT

STATE = DATA / "alerts_state.json"
SITE = "https://stefo818.github.io/armor/"
ORDER = ["Basso", "Normale", "Elevato", "Alto"]


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def vix_band(v: float | None) -> str | None:
    if v is None:
        return None
    return "calma" if v < 20 else ("attenzione" if v < 25 else ("stress" if v < 30 else "panico"))


def detect(state: dict, pred: dict, regime: str | None, vix: float | None, event: dict | None, move: float | None,
           today: str, aix_band: str | None = None, divergence: bool | None = None,
           minimi: dict | None = None, fase: str | None = None, segnali: dict | None = None) -> tuple[list[dict], dict]:
    """Restituisce (avvisi da inviare, nuovo stato). Funzione pura: facile da provare.
    Si avvisa SOLO quando cambia qualcosa di importante: fascia dell'Indice Armor, divergenza attivata, evento importante oggi/domani,
    previsione a 1 mese che passa da basso/normale a elevato/alto, movimento enorme del VWCE."""
    msgs, new = [], dict(state)
    levels = {hz: r["level"] for hz, r in pred.items()}
    old = state.get("levels", {})
    if "1m" in levels and old.get("1m") in ORDER[:2] and levels["1m"] in ORDER[2:]:
        msgs.append({"title": "Rischio in aumento a 1 mese", "priority": 4, "tags": ["warning"],
                     "message": f"Il livello di rischio a {HZ_LABEL['1m']} passa da {old['1m']} a {levels['1m']} ({VERDICT[levels['1m']]})."})
    new["levels"] = levels
    if aix_band:
        ob = state.get("aix_band")
        if ob and ob != aix_band:
            names = ["molto basso", "basso", "moderato", "elevato", "molto alto"]
            up = names.index(aix_band) > names.index(ob) if ob in names and aix_band in names else True
            msgs.append({"title": f"Indice Armor: rischio {aix_band}", "priority": 4 if up and aix_band in ("elevato", "molto alto") else 3,
                         "tags": ["thermometer"], "message": f"L'Indice Armor passa dalla fascia «{ob}» alla fascia «{aix_band}»."})
        new["aix_band"] = aix_band
    if divergence is not None:
        if divergence and not state.get("divergence"):
            msgs.append({"title": "Allarme divergenza attivato", "priority": 4, "tags": ["eyes"],
                         "message": "I prezzi sono vicini ai massimi ma più segnali peggiorano: il rialzo è meno solido di quanto sembri. Apri l'app per i dettagli."})
        new["divergence"] = bool(divergence)
    if minimi:   # una scala diventa «minimo probabile» (ieri non lo era); PROTOCOLLO_MINIMI.md, parte G
        vecchi = state.get("minimi", {})
        nuovi = {k: s["verdetto"] for k, s in minimi["scale"].items()}
        for k, v in nuovi.items():
            if v == "probabile" and vecchi.get(k) != "probabile":
                s = minimi["scale"][k]
                msgs.append({"title": f"Minimo probabile a {s['nome']}", "priority": 5 if k in ("3m", "1a") else 4, "tags": ["chart_with_downwards_trend"],
                             "message": f"Il prezzo è vicino al minimo di {s['nome']} e la stima che non scenda molto di più è {s['q'] * 100:.0f}%. Apri l'app: pagina «Minimi e lungo periodo»."})
        new["minimi"] = nuovi
    if fase:
        of = state.get("fase")
        if of and of != fase:
            msgs.append({"title": "Cambia la fase di lungo periodo", "priority": 4, "tags": ["hourglass"],
                         "message": f"La fase del mercato a lungo termine passa da «{of}» a «{fase}». Apri l'app per vedere che cosa cambia."})
        new["fase"] = fase
    if segnali:   # trend dell'S&P 500 (prezzo sopra/sotto la media a 200 giorni) e semaforo della crescita: PROTOCOLLO_MINIMI.md, parti H e J
        if segnali.get("t1") is not None:
            ot = state.get("t1")
            if ot is not None and bool(ot) != bool(segnali["t1"]):
                su = bool(segnali["t1"])
                msgs.append({"title": "S&P 500 " + ("torna sopra" if su else "scende sotto") + " la media a 200 giorni", "priority": 3 if su else 4, "tags": ["chart_with_upwards_trend" if su else "chart_with_downwards_trend"],
                             "message": "Il prezzo " + ("è tornato sopra" if su else "è sceso sotto") + " la sua media degli ultimi 200 giorni. È un segnale di contesto, non un ordine: apri l'app, pagina «Segnali di fondo»."})
            new["t1"] = bool(segnali["t1"])
        sem = segnali.get("crescita")
        if sem:
            os_ = state.get("crescita")
            if os_ and os_ != sem and sem == "rosso":
                msgs.append({"title": "Crescita economica: semaforo rosso", "priority": 4, "tags": ["traffic_light"],
                             "message": "La stima della crescita in tempo reale o gli indicatori di recessione sono peggiorati. Apri l'app, pagina «Segnali di fondo»."})
            new["crescita"] = sem
    if regime:
        new["regime"] = regime
    b = vix_band(vix)
    if b:
        new["vix"] = b
    if event and event.get("giorni") is not None and event["giorni"] <= 1 and state.get("event") != f"{event['date']}":
        msgs.append({"title": "Evento importante " + ("domani" if event["giorni"] == 1 else "oggi"), "priority": 3, "tags": ["calendar"],
                     "message": f"{event['nome']}. Nei giorni degli eventi la volatilità sale: evita decisioni d'impulso."})
        new["event"] = event["date"]
    if move is not None and abs(move) >= 3.0 and state.get("move_day") != today:
        msgs.append({"title": f"VWCE {move:+.1f}% oggi".replace(".", ","), "priority": 4, "tags": ["rotating_light"],
                     "message": "Movimento molto ampio per un indice mondiale. Controlla la sezione notizie dell'app."})
        new["move_day"] = today
    return msgs, new


def pick_daily(msgs: list[dict], pending: list[dict], state: dict, today: str) -> tuple[list[dict], dict]:
    """Massimo 1 notifica al giorno (gli allarmi personali sono a parte). Con piu' cambiamenti ne parte uno solo (il piu' importante)
    che elenca gli altri; se non ci sono cambiamenti, parte al massimo un messaggio periodico in coda (rapporto settimanale/mensile)."""
    new = dict(state)
    if state.get("sent_day") == today:
        return [], new
    pool = msgs or pending
    if not pool:
        return [], new
    best = max(pool, key=lambda m: m.get("priority", 3))
    out = dict(best)
    others = [m["title"] for m in pool if m is not best]
    if others:
        out["message"] = out["message"] + "\nAltri cambiamenti: " + "; ".join(others)
    new["sent_day"] = today
    return [out], new


def queue(msg: dict, today: str | None = None) -> None:
    """Mette in coda un messaggio periodico (priorita' bassa): parte solo se oggi non c'e' nessun cambiamento importante."""
    today = today or date.today().isoformat()
    st = _load()
    pend = st.get("pending") or {}
    lst = pend.get("msgs", []) if pend.get("day") == today else []
    st["pending"] = {"day": today, "msgs": [m for m in lst if m["title"] != msg["title"]] + [{**msg, "priority": 2}]}
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def notify_once(msgs: list[dict], today: str | None = None) -> int:
    """Invia al massimo un messaggio se oggi non ne e' gia' partito uno (usata dall'agenda del mattino)."""
    today = today or date.today().isoformat()
    st = _load()
    out, new = pick_daily(msgs, [], st, today)
    n = send(out) if os.environ.get("NTFY_TOPIC") else 0
    if n:
        STATE.write_text(json.dumps({**st, "sent_day": new["sent_day"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def send(msgs: list[dict], topic: str | None = None, post=requests.post) -> int:
    topic = topic or os.environ.get("NTFY_TOPIC", "").strip()
    if not topic or not msgs:
        return 0
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    n = 0
    for m in msgs:
        try:
            r = post(server, json={"topic": topic, "title": m["title"], "message": m["message"], "priority": m.get("priority", 3),
                                   "tags": m.get("tags", []), "click": SITE}, timeout=20)
            n += int(r.ok)
        except Exception as e:  # noqa: BLE001
            print("[avvisi] invio non riuscito:", type(e).__name__)
    return n


def run(ctx: dict, regime: str | None, vix: float | None, event: dict | None, move: float | None,
        aix_band: str | None = None, divergence: bool | None = None) -> list[dict]:
    st = _load()
    today = date.today().isoformat()
    try:
        from . import lungo_periodo, minimi
        mo = minimi.carica_oggi()
        lp = lungo_periodo.carica()
        fase = (lp or {}).get("fase", {}).get("nome")
    except Exception:  # noqa: BLE001
        mo, fase = None, None
    try:
        from . import crescita, trend
        tr, cr = trend.carica(), crescita.carica()
        seg = {"t1": (tr or {}).get("T1"), "crescita": ((cr or {}).get("semaforo") or {}).get("colore")}
    except Exception:  # noqa: BLE001
        seg = None
    msgs, new = detect(st, ctx["pred"], regime, vix, event, move, today, aix_band, divergence, mo, fase, seg)
    pend = st.get("pending") or {}
    pending = pend.get("msgs", []) if pend.get("day") == today else []
    new.pop("pending", None)
    if not os.environ.get("NTFY_TOPIC"):
        # senza canale attivo si aggiorna comunque lo stato, così al primo collegamento non arriva una raffica di avvisi vecchi
        STATE.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
        return []
    out, new = pick_daily(msgs, pending, new, today)
    n = send(out)
    if not n:
        new["sent_day"] = st.get("sent_day")   # invio non riuscito: non conta come notifica del giorno
    STATE.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[avvisi] {len(msgs)} cambiamenti, {n} notifiche inviate (max 1 al giorno)")
    return out
