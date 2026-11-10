"""Classifica dei modelli di previsione (Patch 60a): un voto da 1 a 100 per ogni modello, ricalcolato ogni giorno.
50 = «come dire: succede quello che succede di solito» (nessuna abilità). Sopra 50 il modello ha fatto meglio, sotto 50 peggio.
Voto passato = 50 + 400 × media, sugli orizzonti principali, di (metà BSS su tutta la storia + metà BSS dal 2013); BSS = quanto l'errore del modello è più piccolo di quello della frequenza storica.
Voto dal vivo = stesso calcolo sulle previsioni scadute del diario. Peso del vivo = n / (n + 400): all'inizio quasi nullo.
Le fonti sono le valutazioni già salvate (valutazione mensile, motore di percorsi, esperimento sulla volatilità, taratura): nessun modello è promosso da questa classifica."""
import json
import math

import numpy as np
import pandas as pd

from .config import DATA, HORIZONS, PRIMARY

STORIA = DATA / "classifica_storia.csv"
FILE = DATA / "classifica.json"
HZ = ("10g", "1m", "3m", "6m")
PESO_VIVO = 400.0

NOMI = {
    "A1": "A1: modello base sui prezzi",
    "FHS": "FHS: simulazione della nervosità del mercato",
    "FHS+VIX": "FHS+VIX: la stessa simulazione, aggiustata con l'indice della paura",
    "MV-logit": "Multi-variabile (prezzi, macro, credito), regressione",
    "MV-GBM": "Multi-variabile (prezzi, macro, credito), alberi",
    "MVF-logit": "Multi-variabile con le famiglie dell'Indice Armor, regressione",
    "MVF-GBM": "Multi-variabile con le famiglie dell'Indice Armor, alberi",
    "Combinato": "Combinato: media pesata dei modelli con correzione",
    "Combinato-B": "Combinato senza correzione (media pesata)",
    "V0T1": "Simulazione base (V0T1)",
    "V1T1": "Simulazione con l'indice della paura (V1T1)",
    "HAR-X": "Simulazione con previsione di volatilità HAR e VIX (dal 2011)",
    "Media A1 e FHS+VIX": "Media semplice di A1 e FHS+VIX",
    "A1 + Platt": "A1 tarato (correzione a 2 parametri)",
    "A1 + isotonica": "A1 tarato (correzione a gradini)",
    "FHS+VIX + Platt": "FHS+VIX tarato (correzione a 2 parametri)",
    "FHS+VIX + isotonica": "FHS+VIX tarato (correzione a gradini)",
    "Combinato-Tarato": "Miscela di A1 e FHS+VIX, tarata",
}
LIVE_MAP = {"Combinato-pesi": "Combinato-B"}


def _num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except Exception:  # noqa: BLE001
        return None


def _leggi(nome):
    try:
        return json.loads((DATA / nome).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def fonti() -> dict:
    """{modello: {orizzonte: {bss, lo, hi, rec, n}}, ...} dalle valutazioni salvate."""
    out: dict = {}
    dett: dict = {}

    def put(m, hz, bss, lo, hi, rec, n, da):
        if _num(bss) is None:
            return
        out.setdefault(m, {})[hz] = {"bss": _num(bss), "lo": _num(lo), "hi": _num(hi), "rec": _num(rec), "n": n}
        dett.setdefault(m, da)
    ev = _leggi("model_eval.json")
    if ev:
        vist = set()
        for pri in ("modelli", "famiglie", "finale"):
            for r in ev.get("metrics", []):
                if r["set"] != pri or r["kind"] != "down" or r["model"] == "Normale" or int(r["thr"]) != PRIMARY.get(r["hz"], -1) or r["hz"] not in HZ:
                    continue
                if (r["model"], r["hz"]) in vist:
                    continue
                vist.add((r["model"], r["hz"]))
                put(r["model"], r["hz"], r["bss"], r.get("bss_lo"), r.get("bss_hi"), r.get("bss_2013_26"), r["n"], "Prova sul passato dal 1990")
    pv = _leggi("percorsi_verifica.json")
    if pv:
        for hz, o in (pv.get("orizzonti") or {}).items():
            for v in ("V0T1", "V1T1"):
                x = (o.get("varianti") or {}).get(v)
                if x and hz in HZ:
                    ci = x.get("bss_ci") or {}
                    put(v, hz, x.get("bss"), ci.get("lo"), ci.get("hi"), x.get("bss_2013_oggi"), x.get("n"), "Prova sul passato dal 1994")
    vr = _leggi("vrp_ombra.json")
    if vr:
        for b in vr.get("bersagli", []):
            if b.get("tipo") != "down" or b.get("hz") not in HZ:
                continue
            x = (b.get("modelli") or {}).get("HAR-X")
            if x:
                ci = x.get("bss_ci") or {}
                put("HAR-X", b["hz"], x.get("bss"), ci.get("lo"), ci.get("hi"), x.get("bss_2013_oggi"), x.get("n"), "Prova sul passato dal 2011")
    tr = _leggi("taratura.json")
    if tr:
        for r in tr.get("righe", []):
            if r.get("principale") and r["modello"] not in ("A1", "FHS+VIX") and r["hz"] in HZ:
                put(r["modello"], r["hz"], r["bss"], r.get("bss_lo"), r.get("bss_hi"), r.get("bss_2013_26"), r["n"], "Prova sul passato dal 1990 (taratura)")
    for m in out:
        out[m]["_da"] = dett.get(m, "")
    return out


def _voto(s):
    return float(np.clip(50 + 400 * s, 1, 100))


def voto_passato(per_hz: dict):
    """(voto, voto_lo, voto_hi, {hz: voto}) o None."""
    vh, ss, lo, hi = {}, [], [], []
    for hz in HZ:
        x = per_hz.get(hz)
        if not x:
            continue
        s = x["bss"] if x["rec"] is None else 0.5 * x["bss"] + 0.5 * x["rec"]
        vh[hz] = _voto(s)
        ss.append(s)
        if x["lo"] is not None and x["hi"] is not None:
            lo.append(x["lo"])
            hi.append(x["hi"])
    if not ss:
        return None
    m = float(np.mean(ss))
    k = 0.5 if len(per_hz) else 0
    # il margine usa l'intervallo del BSS su tutta la storia, portato sulla stessa scala del voto
    vlo = _voto(m - (float(np.mean([x["bss"] for x in per_hz.values() if isinstance(x, dict) and x.get("lo") is not None])) - float(np.mean(lo))) ) if lo else None
    vhi = _voto(m + (float(np.mean(hi)) - float(np.mean([x["bss"] for x in per_hz.values() if isinstance(x, dict) and x.get("hi") is not None]))) ) if hi else None
    return _voto(m), vlo, vhi, vh


def dal_vivo(sp: pd.Series | None = None) -> dict:
    """{modello: {n, bss}} sulle previsioni scadute dei diari (soglia 1 di ogni riga; esito = calo massimo oltre la soglia)."""
    if sp is None:
        from .features import closed_sp500
        sp = closed_sp500()
    righe = []
    for f in ("journal.csv", "journal_shadow.csv"):
        try:
            righe.append(pd.read_csv(DATA / f))
        except Exception:  # noqa: BLE001
            pass
    if not righe:
        return {}
    j = pd.concat(righe, ignore_index=True)
    res: dict = {}
    idx = sp.index
    for r in j.itertuples():
        try:
            a = pd.Timestamp(r.asof)
            if a not in idx:
                continue
            i = idx.get_loc(a)
            n = int(r.sessions)
            if i + n >= len(idx) or pd.isna(r.p1) or pd.isna(r.base1):
                continue
            seg = sp.iloc[i + 1: i + n + 1].values / float(sp.iloc[i]) - 1
            y = float(seg.min() <= -float(r.thr1) / 100)
            m = LIVE_MAP.get(str(r.model), str(r.model))
            e = res.setdefault(m, {"n": 0, "err": 0.0, "err_b": 0.0})
            e["n"] += 1
            e["err"] += (float(r.p1) - y) ** 2
            e["err_b"] += (float(r.base1) - y) ** 2
        except Exception:  # noqa: BLE001
            continue
    return {m: {"n": e["n"], "bss": (1 - e["err"] / e["err_b"]) if e["err_b"] > 0 else None} for m, e in res.items()}


def _stato(m: str, in_uso: str = "A1") -> str:
    if m == in_uso:
        return "in uso"
    if m in ("FHS+VIX", "V1T1"):
        return "sfidante"
    if m in ("A1 + Platt", "A1 + isotonica", "FHS+VIX + Platt", "FHS+VIX + isotonica", "Combinato-Tarato", "Media A1 e FHS+VIX"):
        return "in prova"
    return "in ombra"


def calcola(sp: pd.Series | None = None) -> list[dict]:
    F = fonti()
    vivo = dal_vivo(sp)
    righe = []
    for m, ph in F.items():
        da = ph.pop("_da", "")
        v = voto_passato(ph)
        if not v:
            continue
        vp, vlo, vhi, vh = v
        lv = vivo.get(m) or {}
        n = int(lv.get("n", 0))
        w = n / (n + PESO_VIVO) if n and lv.get("bss") is not None else 0.0
        vv = _voto(lv["bss"]) if w else None
        voto = (1 - w) * vp + w * (vv if vv is not None else vp)
        righe.append({"modello": m, "nome": NOMI.get(m, m), "stato": _stato(m), "voto": round(voto, 1), "lo": None if vlo is None else round(vlo, 1), "hi": None if vhi is None else round(vhi, 1),
                      "passato": round(vp, 1), "vivo": None if vv is None else round(vv, 1), "n_vivo": n, "peso_vivo": round(w, 3), "per_hz": {k: round(x, 1) for k, x in vh.items()}, "fonte": da})
    righe.sort(key=lambda r: -r["voto"])
    for i, r in enumerate(righe, 1):
        r["posto"] = i
    return righe


def storia() -> pd.DataFrame:
    try:
        return pd.read_csv(STORIA)
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["data", "modello", "voto", "posto"])


def registra(data: str, righe: list[dict] | None = None) -> bool:
    """Una riga per modello al giorno (l'ultima lettura del giorno vince): serve a vedere come cambia la classifica."""
    righe = righe if righe is not None else calcola()
    if not righe:
        return False
    s = storia()
    s = s[s["data"].astype(str) != data]
    new = pd.DataFrame([{"data": data, "modello": r["modello"], "voto": r["voto"], "posto": r["posto"]} for r in righe])
    pd.concat([s, new], ignore_index=True).to_csv(STORIA, index=False)
    FILE.write_text(json.dumps({"data": data, "righe": righe}, ensure_ascii=False), encoding="utf-8")
    return True


def variazioni(righe: list[dict], data: str, giorni: int = 30) -> dict:
    """{modello: variazione di voto rispetto a ~giorni fa} dalla storia salvata (vuoto finché non c'è storia)."""
    s = storia()
    if s.empty:
        return {}
    d = pd.to_datetime(s["data"])
    lim = pd.Timestamp(data) - pd.Timedelta(days=giorni)
    old = s[d <= lim]
    if old.empty:
        return {}
    ult = old[pd.to_datetime(old["data"]) == pd.to_datetime(old["data"]).max()].set_index("modello")["voto"]
    return {r["modello"]: round(r["voto"] - float(ult[r["modello"]]), 1) for r in righe if r["modello"] in ult.index}


def html() -> str:
    """Classifica per la pagina Previsioni."""
    from html import escape as e
    try:
        righe = calcola()
    except Exception:  # noqa: BLE001
        righe = []
    if not righe:
        return "<p class='mu'>La classifica comparirà dopo la prima valutazione dei modelli.</p>"
    try:
        from .features import closed_sp500
        oggi = str(closed_sp500().index[-1].date())
    except Exception:  # noqa: BLE001
        oggi = ""
    var = variazioni(righe, oggi) if oggi else {}
    best = righe[0]["voto"]
    out = ["<div class='cls'>"]
    for r in righe:
        v = r["voto"]
        cl = "ok" if v >= 60 else ("wa" if v >= 45 else "ba")
        marg = f"{r['lo']:.0f}–{r['hi']:.0f}" if r["lo"] is not None and r["hi"] is not None else "n.d."
        d = var.get(r["modello"])
        dv = "" if d is None else f" · {'+' if d > 0 else ''}{d:.1f} in 30 giorni".replace(".", ",")
        chips = "".join(f"<span class='clc'>{k}: {x:.0f}</span>" for k, x in r["per_hz"].items())
        vivo = (f"dal vivo {r['vivo']:.0f} su {r['n_vivo']} previsioni (peso {r['peso_vivo']*100:.0f}%)" if r["vivo"] is not None
                else f"dal vivo: {r['n_vivo']} previsioni chiuse, ancora poche per pesare")
        out.append(f"<div class='clr'><div class='clp'>{r['posto']}</div><div class='clm'><b>{e(r['nome'])}</b><small>{e(r['stato'])} · {e(r['fonte'])}</small>"
                   f"<div class='clch'>{chips}</div><small>Margine di incertezza del voto: {marg}{e(dv)} · {e(vivo)}</small></div>"
                   f"<div class='clv {cl}'><b>{v:.0f}</b><small>su 100</small></div></div>")
    out.append("</div>")
    note = ("<div class='explain'><p><b>Come leggere il voto.</b> 50 vuol dire «come usare la frequenza storica», senza alcuna abilità. Sopra 50 il modello ha sbagliato meno, sotto 50 più. "
            "Si basa su quanto l'errore sulle probabilità di calo è più piccolo di quello della frequenza storica (media sui 4 orizzonti, metà sull'intera storia e metà dal 2013). "
            "Man mano che le previsioni reali scadono, il loro risultato pesa di più. I margini sono larghi: due modelli a pochi punti di distanza non sono distinguibili. "
            "<b>La classifica non cambia da sola il modello in uso</b>: serve la regola scritta in PROTOCOLLO_TARATURA.md. I modelli «tarati» non l'hanno superata, quindi i numeri restano non corretti.</p></div>")
    return note + "".join(out)
