"""Allarmi personali: soglie scelte dall'utente nell'app (salvate in data/alert_rules.json), controllate ogni 15 minuti da GitHub e inviate con ntfy."""
import json

import pandas as pd

from . import alerts, live as livemod, semafori
from .config import DATA

RULES_FILE = DATA / "alert_rules.json"
STATE_FILE = DATA / "alerts_custom_state.json"
EXTRA = {
    "vwce_price": ("Prezzo VWCE (€)", ""), "vwce_chg": ("VWCE variazione di oggi (%)", "%"), "sp500_chg": ("S&P 500 variazione di oggi (%)", "%"),
    "ndx_chg": ("Nasdaq 100 variazione di oggi (%)", "%"), "eurusd_live": ("Cambio EUR/USD", ""),
    "risk_10g": ("Probabilità di calo ≥5% a 10 giorni (%)", "%"), "risk_1m": ("Probabilità di calo ≥10% a 1 mese (%)", "%"),
    "risk_3m": ("Probabilità di calo ≥10% a 3 mesi (%)", "%"), "risk_6m": ("Probabilità di calo ≥10% a 6 mesi (%)", "%"),
    "val_pe_sp500": ("P/E S&P 500 (live)", ""), "val_ps_sp500": ("P/S S&P 500 (live)", ""), "val_pe_vwce": ("P/E VWCE (live)", ""), "val_pe_ndx": ("P/E Nasdaq 100 (live)", ""),
}


def values(sp: pd.Series, pred: dict | None = None) -> dict[str, dict]:
    """Tutti i valori su cui si può impostare un allarme: chiave -> {label, value}."""
    out = {}
    lv = livemod.load()
    q = lv.get("quotes", {})
    for i in semafori.compute(sp, lv):
        out[i["key"]] = {"label": i["name"], "value": i["value"]}
    if (q.get("vwce") or {}).get("price"):
        out["vwce_price"] = {"label": EXTRA["vwce_price"][0], "value": q["vwce"]["price"]}
    for k, kk in (("vwce_chg", "vwce"), ("sp500_chg", "sp500"), ("ndx_chg", "ndx")):
        c = (q.get(kk) or {}).get("chg")
        if c is not None:
            out[k] = {"label": EXTRA[k][0], "value": c * 100}
    if (q.get("eurusd") or {}).get("price"):
        out["eurusd_live"] = {"label": EXTRA["eurusd_live"][0], "value": q["eurusd"]["price"]}
    if pred:
        for hz, r in pred.items():
            from .config import PRIMARY
            out[f"risk_{hz}"] = {"label": EXTRA[f"risk_{hz}"][0], "value": r["p"][PRIMARY[hz]] * 100}
    try:
        from . import valuations
        for c in valuations.current():
            for m in ("pe", "ps"):
                if c.get(m):
                    out[f"val_{m}_{c['key']}"] = {"label": f"{m.upper()} {c['name']} (live)", "value": c[m]}
    except Exception:  # noqa: BLE001
        pass
    return out


def load_rules() -> list[dict]:
    try:
        return [r for r in json.loads(RULES_FILE.read_text(encoding="utf-8")).get("rules", []) if r.get("key") and r.get("op") in (">", "<")]
    except Exception:  # noqa: BLE001
        return []


def evaluate(rules: list[dict], vals: dict, state: dict) -> tuple[list[dict], dict]:
    """Un avviso parte solo quando la condizione PASSA da falsa a vera; si riarma quando torna falsa."""
    msgs, new = [], dict(state)
    for r in rules:
        v = (vals.get(r["key"]) or {}).get("value")
        if v is None:
            continue
        hit = v > float(r["value"]) if r["op"] == ">" else v < float(r["value"])
        rid = str(r.get("id") or f"{r['key']}{r['op']}{r['value']}")
        if hit and not state.get(rid):
            lab = (vals[r["key"]]["label"])
            msgs.append({"title": r.get("name") or f"Allarme: {lab}", "priority": 4, "tags": ["bell"],
                         "message": f"{lab} è {v:.2f} ({'sopra' if r['op'] == '>' else 'sotto'} la tua soglia {r['value']}).".replace(".", ",", 1) if False else
                                f"{lab} è {f'{v:.2f}'.replace('.', ',')} ({'sopra' if r['op'] == '>' else 'sotto'} la tua soglia {str(r['value']).replace('.', ',')})."})
        new[rid] = bool(hit)
    return msgs, new


def run() -> None:
    from .features import closed_sp500
    rules = load_rules()
    if not rules:
        print("[allarmi] nessuna regola impostata")
        return
    try:
        livemod.run()
    except Exception as e:  # noqa: BLE001
        print("[allarmi] prezzi live non aggiornati:", str(e)[:80])
    sp = closed_sp500()
    try:
        from .jobs import forecast
        pred = forecast(write=False)["pred"]
    except Exception:  # noqa: BLE001
        pred = None
    vals = values(sp, pred)
    try:
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    msgs, new = evaluate(rules, vals, st)
    n = alerts.send(msgs)
    STATE_FILE.write_text(json.dumps(new, indent=1), encoding="utf-8")
    print(f"[allarmi] {len(rules)} regole, {len(msgs)} scattate, {n} avvisi inviati")


def options_json(sp: pd.Series, pred: dict | None) -> tuple[list[dict], dict]:
    """Per la pagina: elenco di voci scelte e valori attuali."""
    v = values(sp, pred)
    opts = [{"k": k, "l": d["label"]} for k, d in v.items()]
    opts.sort(key=lambda o: o["l"])
    return opts, {k: round(float(d["value"]), 4) for k, d in v.items()}
