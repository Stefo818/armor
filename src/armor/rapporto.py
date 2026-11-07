"""Rapporto mensile automatico (4.4): il 1 del mese (o alla prima esecuzione utile dopo) riassume il mese appena chiuso:
cosa ha previsto Armor, cosa e' successo davvero, se il modello e' cambiato e perche' (da models.json e learning.csv)."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import journal
from .config import DATA, HZ_LABEL, OUTCOMES

REPORTS = DATA / "reports"
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _pc(x, d=1, sign=False):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%").replace(".", ",")


def build(first: pd.Timestamp, sp: pd.Series, jr: pd.DataFrame, outc: pd.DataFrame, reg: dict, learn: pd.DataFrame, aix: pd.Series | None) -> dict:
    """Funzione pura. first = primo giorno del mese appena chiuso."""
    last = first + pd.offsets.MonthEnd(0)
    d = {"mese": f"{MESI[first.month - 1]} {first.year}", "key": first.strftime("%Y-%m")}
    m = sp[(sp.index >= first) & (sp.index <= last)]
    if len(m) > 1:
        prev = sp[sp.index < first]
        base = float(prev.iloc[-1]) if len(prev) else float(m.iloc[0])
        d["mercato"] = {"rend": float(m.iloc[-1] / base - 1), "calo_max": float((m / m.cummax() - 1).min()), "giorni": int(len(m))}
    if aix is not None and len(aix):
        a = aix[(aix.index >= first) & (aix.index <= last)]
        if len(a):
            d["indice"] = {"min": float(a.min()), "max": float(a.max()), "fine": float(a.iloc[-1])}
    prev_m = {}
    if len(jr):
        j = jr.copy()
        j["asof"] = pd.to_datetime(j["asof"])
        j = j[(j["asof"] >= first) & (j["asof"] <= last)]
        for hz, g in j.groupby("horizon"):
            prev_m[hz] = {"n": int(len(g)), "p_media": float(g["p1"].mean()), "normale": float(g["base1"].mean()), "livello": str(g["level"].iloc[-1])}
    d["previsto"] = prev_m
    sc = {}
    if len(outc):
        o = outc.copy()
        o["target_date"] = pd.to_datetime(o["target_date"])
        o = o[(o.target_date >= first) & (o.target_date <= last)]
        if len(o) and len(jr):
            x = o.merge(jr[["asof", "horizon", "p1"]], on=["asof", "horizon"], how="left")
            for hz, g in x.groupby("horizon"):
                hit = g["hit1"].astype(str).str.lower().isin(["true", "1", "1.0"])
                sc[hz] = {"n": int(len(g)), "p_media": float(g["p1"].mean()), "successo": float(hit.mean())}
    d["scadute"] = sc
    ch = []
    for v in (reg or {}).get("versions", []):
        if str(v.get("date", ""))[:7] == d["key"] and v.get("id") != "A1":
            ch.append(f"Modello {v['id']}: {v.get('note', '')}")
    for t in (reg or {}).get("tentativi", []):
        if str(t.get("data", ""))[:7] == d["key"]:
            ch.append(f"Prova «{t['id']}»: {'adottata' if t.get('adottato') else 'non adottata (regola di adozione non superata): resta ' + str(t.get('campione', 'A1'))}")
    d["modello"] = {"in_uso": (reg or {}).get("champion", "A1"), "cambiamenti": ch}
    if len(learn):
        l = learn[learn["kind"] == "calo"].copy()
        l = l.sort_values("date").groupby("hz").tail(1)
        d["apprendimento"] = [{"hz": r.hz, "n": int(r.n), "bss": float(r.bss)} for r in l.itertuples() if r.bss == r.bss]
    return d


def html(d: dict | None) -> str:
    e = _h.escape
    if not d:
        return "<p class='mu'>Il primo rapporto mensile arriverà il 1° del prossimo mese.</p>"
    out = [f"<div class='card'><h3 style='margin-top:0'>Rapporto di {e(d['mese'])}</h3>"]
    mk = d.get("mercato")
    if mk:
        out.append(f"<p><b>Cosa è successo:</b> l'S&amp;P 500 ha reso {_pc(mk['rend'], 1, True)} nel mese, con un calo massimo dai picchi del mese di {_pc(mk['calo_max'])}.")
        ix = d.get("indice")
        if ix:
            out[-1] += f" L'Indice Armor è andato da {ix['min']:.0f} a {ix['max']:.0f} (fine mese: {ix['fine']:.0f})."
        out[-1] += "</p>"
    if d.get("previsto"):
        out.append("<p><b>Cosa aveva previsto Armor:</b> " + "; ".join(
            f"{HZ_LABEL.get(h, h)}: probabilità media di calo {_pc(v['p_media'], 0)} (normale {_pc(v['normale'], 0)}), livello a fine mese «{e(v['livello'])}»" for h, v in d["previsto"].items()) + ".</p>")
    if d.get("scadute"):
        out.append("<p><b>Previsioni scadute nel mese:</b> " + "; ".join(
            f"{HZ_LABEL.get(h, h)}: {v['n']} (previsto {_pc(v['p_media'], 0)}, avvenuto {_pc(v['successo'], 0)})" for h, v in d["scadute"].items()) + ".</p>")
    mo = d.get("modello", {})
    out.append(f"<p><b>Il modello è cambiato?</b> {'Sì: ' + ' '.join(e(c) for c in mo['cambiamenti']) if mo.get('cambiamenti') else 'No: resta il modello ' + e(str(mo.get('in_uso', 'A1'))) + '.'}</p>")
    if d.get("apprendimento"):
        out.append("<p><b>Dai dati reali:</b> " + "; ".join(f"{HZ_LABEL.get(a['hz'], a['hz'])}: {a['bss']:+.2f} sul «normale» ({a['n']} previsioni scadute)".replace(".", ",") for a in d["apprendimento"])
                   + ". Più di 0 = meglio della media storica; con poche previsioni scadute il giudizio è solo indicativo.</p>")
    out.append("</div>")
    return "".join(out)


def message(d: dict) -> dict:
    mk = d.get("mercato") or {}
    txt = f"S&P 500 {_pc(mk.get('rend'), 1, True)} nel mese." if mk else ""
    ch = d.get("modello", {}).get("cambiamenti")
    txt += " " + (ch[0] if ch else "Modello invariato.")
    return {"title": f"Rapporto mensile Armor: {d['mese']}", "tags": ["calendar"], "message": txt.strip()}


def load_latest() -> dict | None:
    try:
        return json.loads((REPORTS / "mensile-latest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def run(sp: pd.Series, today=None, force: bool = False) -> dict | None:
    """Genera il rapporto del mese precedente se non esiste ancora (accade il 1 del mese o alla prima esecuzione dopo)."""
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    first = (today.replace(day=1) - pd.offsets.MonthBegin(1)).normalize()
    f = REPORTS / f"mensile-{first.strftime('%Y-%m')}.json"
    if f.exists() and not force:
        return {**json.loads(f.read_text(encoding="utf-8")), "nuovo": False}
    try:
        outc = pd.read_csv(OUTCOMES) if OUTCOMES.exists() else pd.DataFrame()
    except Exception:  # noqa: BLE001
        outc = pd.DataFrame()
    try:
        reg = json.loads((DATA / "models.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        reg = {}
    try:
        learn = pd.read_csv(DATA / "learning.csv")
    except Exception:  # noqa: BLE001
        learn = pd.DataFrame()
    try:
        from . import store
        aix = store.load("armor_index")
    except Exception:  # noqa: BLE001
        aix = None
    d = build(first, sp, journal.read(), outc, reg, learn, aix)
    REPORTS.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (REPORTS / "mensile-latest.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return {**d, "nuovo": True}
