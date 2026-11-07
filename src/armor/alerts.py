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
           today: str) -> tuple[list[dict], dict]:
    """Restituisce (avvisi da inviare, nuovo stato). Funzione pura: facile da provare."""
    msgs, new = [], dict(state)
    levels = {hz: r["level"] for hz, r in pred.items()}
    old = state.get("levels", {})
    for hz, lv in levels.items():
        if hz in old and old[hz] != lv:
            up = ORDER.index(lv) > ORDER.index(old[hz])
            msgs.append({"title": f"Rischio {'in aumento' if up else 'in calo'} a {HZ_LABEL[hz]}", "priority": 4 if up and lv in ("Elevato", "Alto") else 3,
                         "tags": ["warning" if up else "white_check_mark"],
                         "message": f"Il livello di rischio a {HZ_LABEL[hz]} passa da {old[hz]} a {lv} ({VERDICT[lv]})."})
    new["levels"] = levels
    if regime:
        if state.get("regime") and state["regime"] != regime:
            msgs.append({"title": f"Regime di mercato: ora {regime}", "priority": 4 if regime != "Calma" else 3, "tags": ["compass"],
                         "message": f"Il mercato passa da {state['regime']} a {regime}."})
        new["regime"] = regime
    b = vix_band(vix)
    if b:
        if state.get("vix") and state["vix"] != b:
            up = ["calma", "attenzione", "stress", "panico"].index(b) > ["calma", "attenzione", "stress", "panico"].index(state["vix"])
            msgs.append({"title": f"VIX: {b}", "priority": 4 if up and b in ("stress", "panico") else 3, "tags": ["chart_with_upwards_trend"],
                         "message": f"Il VIX ({vix:.1f}) entra nella fascia «{b}» (prima: {state['vix']})."})
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


def run(ctx: dict, regime: str | None, vix: float | None, event: dict | None, move: float | None) -> list[dict]:
    st = _load()
    msgs, new = detect(st, ctx["pred"], regime, vix, event, move, date.today().isoformat())
    if not os.environ.get("NTFY_TOPIC"):
        # senza canale attivo si aggiorna comunque lo stato, così al primo collegamento non arriva una raffica di avvisi vecchi
        STATE.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
        return []
    n = send(msgs)
    STATE.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[avvisi] {len(msgs)} da inviare, {n} inviati")
    return msgs
