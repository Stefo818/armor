"""Bilancio del giorno, agenda del mattino e rapporto settimanale."""
import html as _h
import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import calendario, live as livemod, store
from .config import DATA, HORIZONS, HZ_LABEL, PRIMARY

REPORTS = DATA / "reports"
SAFE = "Evita decisioni d'impulso: un piano di accumulo funziona proprio perché non dipende dall'umore del giorno."


WD = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


def _it(x, d=2):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _dd(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{WD[d.weekday()]} {d.strftime('%d/%m')}"


def _pc(x, d=1):
    return "n.d." if x is None else f"{x * 100:+.{d}f}%".replace(".", ",")


def _chg(key: str, q: dict):
    c = (q.get(key) or {}).get("chg")
    if c is not None:
        return c
    s = store.load(key)
    return float(s.iloc[-1] / s.iloc[-2] - 1) if len(s) > 1 else None


def _earn_today(day: date) -> list[str]:
    try:
        ev = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return [e["nome"] for e in ev if e["date"] == day.isoformat()]


def day_summary(pred: dict, prev_levels: dict | None, regime: str | None, news: dict | None, today: date | None = None,
                semaforo: dict | None = None) -> dict:
    today = today or date.today()
    q = livemod.load().get("quotes", {})
    lines = []
    vw, sp, nq, vx = _chg("vwce", q), _chg("sp500", q), _chg("ndx", q), (q.get("vix") or {}).get("price")
    lines.append(f"<b>Mercati:</b> VWCE {_pc(vw)}, S&amp;P 500 {_pc(sp)}, Nasdaq 100 {_pc(nq)}" + (f", VIX {vx:.1f}".replace(".", ",") if vx else "") + ".")
    lv = {hz: r["level"] for hz, r in pred.items()}
    ch = [f"{HZ_LABEL[h]}: {prev_levels[h]} → {lv[h]}" for h in lv if prev_levels and h in prev_levels and prev_levels[h] != lv[h]]
    lines.append("<b>Rischio:</b> " + (("cambiato — " + "; ".join(ch)) if ch else "nessun cambio di livello (" + ", ".join(f"{HZ_LABEL[h]} {lv[h].lower()}" for h in lv) + ")") + ".")
    if regime:
        lines.append(f"<b>Regime di mercato:</b> {regime.lower()}.")
    if semaforo:
        lines.append(f"<b>Semafori:</b> {semaforo['ba']} rossi, {semaforo['wa']} gialli, {semaforo['ok']} verdi.")
    if news and news.get("items"):
        macro = [i for i in news["items"] if i["kind"] == "macro"]
        if macro:
            avg = sum(i["sent"] for i in macro) / len(macro)
            tc = {}
            for i in macro:
                for t in i["themes"]:
                    tc[t] = tc.get(t, 0) + 1
            top = ", ".join(t for t, _ in sorted(tc.items(), key=lambda kv: -kv[1])[:3])
            lines.append(f"<b>Notizie:</b> tono {'negativo' if avg <= -0.1 else ('positivo' if avg >= 0.1 else 'neutro')} ({avg:+.2f}). Temi: {top or 'vari'}.".replace(".", ",", 0))
    evs = calendario.events(today, 7)
    big = [e for e in evs if e["peso"] >= 3][:3]
    if big:
        lines.append("<b>In arrivo:</b> " + "; ".join(f"{e['nome']} il {datetime.fromisoformat(e['date']).strftime('%d/%m')}" for e in big) + ".")
    try:
        from . import salute
        rn = salute.red_names(salute.compute())
        if rn:
            lines.append(f"<b>Attenzione ai dati:</b> {', '.join(rn)} non si aggiorna come dovrebbe: le stime di oggi sono meno affidabili.")
    except Exception:  # noqa: BLE001
        pass
    lines.append(f"<b>Consiglio di metodo:</b> {SAFE}")
    return {"date": today.isoformat(), "lines": lines, "levels": lv}


def day_html(d: dict) -> str:
    return ("<div class='card bil'><h3 style='margin-top:0'>Bilancio del giorno</h3><ul>" + "".join(f"<li>{x}</li>" for x in d["lines"]) + "</ul>"
            f"<div class='mu'>Aggiornato il {d['date']}. Non è consulenza finanziaria.</div></div>")


def plain(html_line: str) -> str:
    import re
    return _h.unescape(re.sub("<[^>]+>", "", html_line))


def evening_message(d: dict) -> dict:
    return {"title": "Bilancio del giorno", "priority": 3, "tags": ["bar_chart"], "message": "\n".join(plain(x) for x in d["lines"][:5])}


def morning_message(today: date | None = None) -> dict | None:
    today = today or date.today()
    evs = calendario.events(today, 7)
    earn = _earn_today(today)
    lines = []
    todays = [e for e in evs if e["date"] == today.isoformat()]
    if todays:
        lines.append("Oggi: " + "; ".join(e["nome"] for e in todays))
    if earn:
        lines.append("Trimestrali oggi: " + ", ".join(earn))
    wk = [e for e in evs if e["peso"] >= 3 and e["date"] != today.isoformat()][:3]
    if wk:
        lines.append("Prossimi giorni: " + "; ".join(f"{e['nome']} ({_dd(e['date'])})" for e in wk))
    q = livemod.load().get("quotes", {})
    vx = (q.get("vix") or {}).get("price")
    if vx:
        lines.append(f"VIX {vx:.1f}".replace(".", ","))
    if not lines:
        return None
    return {"title": "Agenda di oggi", "priority": 3, "tags": ["sunrise"], "message": "\n".join(lines)}


# ---------------------------------------------------------------- settimanale
def weekly(pred: dict, regime: str | None, sem_items: list[dict], news_hist: dict | None = None, today: date | None = None) -> dict:
    today = today or date.today()
    start = today - timedelta(days=7)
    lines, watch = [], []
    for key, name in (("vwce_de", "VWCE"), ("sp500", "S&P 500"), ("nasdaq100", "Nasdaq 100"), ("vix", "VIX"), ("eurusd", "EUR/USD")):
        s = store.load(key)
        if key == "vwce_de":
            from .features import vwce_series
            s = vwce_series()
        s = s.dropna()
        if len(s) < 8:
            continue
        a = s[s.index <= pd.Timestamp(start)]
        if a.empty:
            continue
        ch = float(s.iloc[-1] / a.iloc[-1] - 1)
        w = s[s.index > pd.Timestamp(start)]
        rng = f" (da {_it(w.min())} a {_it(w.max())})" if len(w) else ""
        lines.append(f"{name}: {_pc(ch)} nella settimana{rng}, ultimo {_it(float(s.iloc[-1]))}")
    j = None
    try:
        from . import journal
        j = journal.read()
    except Exception:  # noqa: BLE001
        pass
    risk = []
    if j is not None and len(j):
        for hz in pred:
            old = j[(j["horizon"] == hz) & (j["asof"] <= start.isoformat())].tail(1)
            if len(old):
                r = old.iloc[0]
                pv = r["p1"] if r["thr1"] == PRIMARY[hz] else r["p2"]
                now = pred[hz]["p"][PRIMARY[hz]]
                if pd.notna(pv):
                    risk.append(f"{HZ_LABEL[hz]}: {pv * 100:.0f}% → {now * 100:.0f}%")
    nextw = [e for e in calendario.events(today + timedelta(days=1), 8) if e["peso"] >= 2][:6]
    for e in nextw[:3]:
        watch.append(f"{e['nome']} — {_dd(e['date'])}")
    bad = [i for i in sem_items if i["light"] == "ba"][:2]
    for i in bad:
        watch.append(f"{i['name']} è in rosso: controlla se rientra")
    if not bad:
        yel = [i for i in sem_items if i["light"] == "wa"][:2]
        for i in yel:
            watch.append(f"{i['name']} è in giallo: osserva l'evoluzione")
    return {"date": today.isoformat(), "week_of": start.isoformat(), "moves": lines, "risk": risk, "regime": regime, "watch": watch[:5],
            "events": [f"{e['nome']} ({datetime.fromisoformat(e['date']).strftime('%d/%m')})" for e in nextw]}


def weekly_save(w: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(w, ensure_ascii=False)
    (REPORTS / f"weekly-{w['date']}.json").write_text(txt, encoding="utf-8")
    (REPORTS / "weekly-latest.json").write_text(txt, encoding="utf-8")
    for p in sorted(REPORTS.glob("weekly-20*.json"))[:-26]:
        p.unlink()


def weekly_load() -> dict | None:
    try:
        return json.loads((REPORTS / "weekly-latest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def weekly_html(w: dict | None) -> str:
    if not w:
        return "<p class='mu'>Il rapporto settimanale compare dopo la prima chiusura di venerdì sera.</p>"
    li = lambda xs: "".join(f"<li>{_h.escape(x)}</li>" for x in xs) or "<li>—</li>"
    return (f"<div class='card'><h3 style='margin-top:0'>Settimana al {w['date']}</h3><h4>Com'è andata</h4><ul>{li(w['moves'])}</ul>"
            f"<h4>Il rischio nella settimana</h4><ul>{li(['Probabilità di calo — ' + x for x in w['risk']])}</ul>"
            + (f"<p>Regime di mercato: <b>{_h.escape(w['regime'])}</b>.</p>" if w.get("regime") else "")
            + f"<h4>Le 3 cose da guardare la prossima settimana</h4><ol>{li(w['watch'][:3])}</ol>"
            f"<div class='mu'>Generato ogni venerdì sera. Gli eventi sono quelli del calendario ufficiale.</div></div>")
