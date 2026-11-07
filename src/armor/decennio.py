"""Analisi dei 10 anni: ogni giorno confronta la situazione di oggi con gli ultimi 10 anni indicatore per indicatore,
poi dice quanto il modello ha avuto ragione in quel periodo. Produce avvertenze, rassicurazioni e un giudizio."""
import html as _h
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import semafori
from .config import DATA, HORIZONS, HZ_LABEL, PRIMARY
from .features import fwd_maxdd, fwd_ret

CACHE = DATA / "prova10.json"
YEARS = 10


def indicators(sp: pd.Series, items: list[dict]) -> list[dict]:
    """Per ogni indicatore con semaforo: percentile negli ultimi 10 anni, ultima volta in cui era peggio, cosa è successo dopo livelli simili."""
    t0 = sp.index[-1] - pd.DateOffset(years=YEARS)
    f63, d63 = fwd_ret(sp, 63), fwd_maxdd(sp, 63)
    out = []
    for it in items:
        spec = semafori.SPEC_BY[it["key"]]
        kind = spec[3]
        if kind not in ("hi", "lo", "pct"):
            continue
        s = semafori.series_of(it["key"], sp)
        w = s[s.index >= t0]
        if len(w) < 250:
            continue
        v = it["value"]
        pct = float((w < v).mean() * 100)
        worse = pct if kind in ("hi", "pct") else 100 - pct       # 100 = il peggior valore dei 10 anni
        wh = w[w > v] if kind in ("hi", "pct") else w[w < v]
        last_worse = wh.index[-1] if len(wh) else None
        # livelli simili negli ultimi 10 anni (+-10 percentili)
        lo_q, hi_q = np.percentile(w, max(pct - 10, 0)), np.percentile(w, min(pct + 10, 100))
        sim = w[(w >= lo_q) & (w <= hi_q)]
        dd = d63.reindex(sim.index).dropna()
        rr = f63.reindex(sim.index).dropna()
        out.append({"key": it["key"], "name": it["name"], "value": v, "dec": it["dec"], "unit": it["unit"], "worse": worse, "pct": pct,
                    "last_worse": last_worse.strftime("%m/%Y") if last_worse is not None else None,
                    "min": float(w.min()), "med": float(w.median()), "max": float(w.max()),
                    "n_sim": int(len(rr)), "ret3": float(rr.mean()) if len(rr) > 30 else None, "dd10": float((dd <= -0.10).mean()) if len(dd) > 30 else None})
    return out


def track_record(p: pd.Series, use_cache: bool = True) -> dict | None:
    if use_cache and CACHE.exists():
        try:
            c = json.loads(CACHE.read_text(encoding="utf-8"))
            if datetime.fromisoformat(c["built"]) > datetime.now() - timedelta(days=6):
                return c
        except Exception:  # noqa: BLE001
            pass
    from .autoimprove import champion_engine
    from . import challenger
    eng, mid = champion_engine(p)
    idx = p.index
    start = idx[-1] - pd.DateOffset(years=YEARS)
    d = challenger._evaluate(eng, eng, idx, start, step=5)
    if d.empty:
        return None
    rows = []
    for hz in HORIZONS:
        g = d[(d.hz == hz) & (d.thr == PRIMARY[hz])].copy()
        if len(g) < 60:
            continue
        g["ratio"] = g.pa / g.base
        hi, lo = g[g.ratio >= 1.3], g[g.ratio <= 0.8]
        auc = challenger._metrics(g)[2]
        rows.append({"hz": hz, "n": int(len(g)), "base": float(g.y.mean()), "freq_hi": float(hi.y.mean()) if len(hi) >= 10 else None, "n_hi": int(len(hi)),
                     "freq_lo": float(lo.y.mean()) if len(lo) >= 10 else None, "n_lo": int(len(lo)),
                     "auc": float(auc) if auc == auc else None, "thr": PRIMARY[hz]})
    res = {"built": datetime.now().isoformat(timespec="seconds"), "model": mid, "rows": rows}
    CACHE.write_text(json.dumps(res), encoding="utf-8")
    return res


def synthesize(ind: list[dict]) -> dict:
    warn = sorted([i for i in ind if i["worse"] >= 90], key=lambda i: -i["worse"])
    calm = sorted([i for i in ind if i["worse"] <= 30], key=lambda i: i["worse"])
    mid = [i for i in ind if 30 < i["worse"] < 90]
    n = len(ind)
    score = float(np.mean([i["worse"] for i in ind])) if ind else None
    if score is None:
        verdict = "n.d."
    elif score >= 70:
        verdict = "Il quadro è tra i più tesi degli ultimi 10 anni."
    elif score >= 55:
        verdict = "Il quadro è un po' più teso della media degli ultimi 10 anni."
    elif score >= 40:
        verdict = "Il quadro è nella norma degli ultimi 10 anni."
    else:
        verdict = "Il quadro è più tranquillo della media degli ultimi 10 anni."
    return {"warn": warn, "calm": calm, "mid": mid, "n": n, "score": score, "verdict": verdict}


def _f(v, dec, unit):
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".") + unit


def html(ind: list[dict], tr: dict | None) -> str:
    if not ind:
        return "<p class='mu'>Servono più dati storici per il confronto sui 10 anni.</p>"
    sy = synthesize(ind)
    li = lambda i, extra: (f"<li><b>{_h.escape(i['name'])}</b>: {_f(i['value'], i['dec'], i['unit'])}, {extra}</li>")
    w = "".join(li(i, f"tra i valori più rischiosi degli ultimi 10 anni ({i['worse']:.0f}° percentile del rischio)" + (f"; ultima volta peggio: {i['last_worse']}" if i["last_worse"] else "; mai così rischioso in 10 anni")) if True else "" for i in sy["warn"][:6])
    c = "".join(li(i, f"tra i valori più rassicuranti dei 10 anni ({i['worse']:.0f}° percentile del rischio)") for i in sy["calm"][:6])
    out = (f"<div class='kc {'ba' if sy['score'] >= 70 else ('wa' if sy['score'] >= 55 else 'ok')}'><div class='k'>Giudizio sui 10 anni</div><div class='v' style='font-size:20px'>{sy['verdict']}</div>"
           f"<div class='s'>Su {sy['n']} indicatori: {len(sy['warn'])} in zona di massimo rischio, {len(sy['calm'])} rassicuranti, {len(sy['mid'])} intermedi.</div></div>")
    out += "<div class='hrow'><div class='hbox r'><h4>Avvertenze</h4><ul>" + (w or "<li>Nessun indicatore è ai massimi di rischio dei 10 anni.</li>") + "</ul></div>"
    out += "<div class='hbox o'><h4>Rassicurazioni</h4><ul>" + (c or "<li>Nessun indicatore è ai livelli più rassicuranti.</li>") + "</ul></div></div>"
    rows = "".join(f"<tr data-chart='{i['key']}'><td>{_h.escape(i['name'])}</td><td>{_f(i['value'], i['dec'], i['unit'])}</td><td>{_f(i['min'], i['dec'], '')} / {_f(i['med'], i['dec'], '')} / {_f(i['max'], i['dec'], '')}</td>"
                   f"<td>{i['worse']:.0f}°</td><td>{i['last_worse'] or '—'}</td><td>{('' if i['dd10'] is None else f'{i[chr(100)+chr(100)+chr(49)+chr(48)] * 100:.0f}%')}</td></tr>" for i in sorted(ind, key=lambda i: -i["worse"]))
    out += ("<details class='exp'><summary>Tutti gli indicatori contro i 10 anni</summary><div class='card scroll'><table><tr><th>Indicatore</th><th>Oggi</th><th>Min / mediana / max 10 anni</th><th>Percentile rischio</th><th>Ultima volta peggio</th><th>Calo ≥10% a 3 mesi da livelli simili</th></tr>"
            + rows + "</table></div></details>")
    if tr and tr["rows"]:
        pc = lambda x: "n.d." if x is None else (f"{x * 100:.0f}%" if x >= .1 else f"{x * 100:.1f}%".replace(".", ","))
        trr = "".join(f"<tr><td>{HZ_LABEL[r['hz']]} (calo ≥{r['thr']}%)</td><td>{pc(r['base'])}</td><td><b>{pc(r['freq_hi'])}</b> <span class='mu'>({r['n_hi']} giorni)</span></td>"
                      f"<td><b>{pc(r['freq_lo'])}</b> <span class='mu'>({r['n_lo']} giorni)</span></td><td>{'n.d.' if r['auc'] is None else f'{r[chr(97)+chr(117)+chr(99)]:.2f}'.replace('.', ',')}</td></tr>" for r in tr["rows"])
        weak = [HZ_LABEL[r["hz"]] for r in tr["rows"] if r["auc"] is not None and r["auc"] < 0.55]
        if weak:
            out += f"<div class='banner'><b>Attenzione:</b> a {' e '.join(weak)} negli ultimi 10 anni il modello non ha distinto i momenti rischiosi meglio del caso (AUC sotto 0,55). Per quei periodi usa i numeri come contesto, non come segnale.</div>"
        out += ("<h3>Prova dei 10 anni: quanto ha avuto ragione Armor</h3><table><tr><th>Periodo</th><th>Frequenza normale del calo</th><th>Dopo un livello «elevato/alto»</th><th>Dopo un livello «basso»</th><th>AUC</th></tr>" + trr + "</table>"
                "<p class='mu'>Test senza «barare»: a ogni data il modello usa solo i dati di allora (walk-forward), sugli ultimi 10 anni. Se dopo i livelli alti il calo è più frequente che dopo quelli bassi, "
                "l'app ha avuto ragione nel distinguere i momenti rischiosi. AUC 0,5 = tirare una moneta, 1 = perfetto. I giorni vicini si sovrappongono: i numeri sono indicativi, non garanzie.</p>")
    return out
