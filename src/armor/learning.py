"""Apprendimento dai dati reali: ogni giorno Armor confronta le previsioni scadute con quello che è successo davvero.
- calo: diario (journal) + esiti (outcomes);
- rialzo: probabilità salvate nel registro giornaliero contro il massimo reale raggiunto dopo;
- punteggio di Brier del modello contro la semplice frequenza storica (>0 = Armor fa meglio del «normale»).
I risultati si accumulano in data/learning.csv. Il controllo mensile li usa: se il modello in uso va nettamente peggio del normale
nei dati reali, si torna al modello di base."""
import html as _h

import numpy as np
import pandas as pd

from . import registry
from .config import DATA, HORIZONS, HZ_LABEL, JOURNAL, OUTCOMES, PRIMARY
from .features import fwd_maxup

LEARN = DATA / "learning.csv"
MIN_N = 20      # sotto questo numero di previsioni scadute il confronto è solo indicativo
GUARD_N = 60    # con almeno 60 previsioni scadute il confronto può far tornare al modello di base


def _brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def live_table(sp: pd.Series) -> pd.DataFrame:
    rows = []
    try:
        j, o = pd.read_csv(JOURNAL), pd.read_csv(OUTCOMES)
        d = o.merge(j[["asof", "horizon", "p1", "base1"]], on=["asof", "horizon"], how="inner")
        d["hit"] = d["hit1"].astype(str).str.lower().isin(["true", "1", "1.0"]).astype(float)
        for hz, g in d.groupby("horizon"):
            g = g.dropna(subset=["p1", "base1"])
            if len(g):
                bm, bb = _brier(g["p1"], g["hit"]), _brier(g["base1"], g["hit"])
                rows.append({"kind": "calo", "hz": hz, "n": len(g), "brier": bm, "brier_base": bb, "bss": 1 - bm / bb if bb > 0 else np.nan,
                             "avg_p": float(g["p1"].mean()), "freq": float(g["hit"].mean())})
    except Exception:  # noqa: BLE001
        pass
    try:
        r = registry.read()
        for hz, n in HORIZONS.items():
            if f"pup_{hz}" not in r:
                continue
            mx = fwd_maxup(sp, n)
            thr = PRIMARY[hz] / 100
            g = r[["date", f"pup_{hz}", f"bup_{hz}"]].dropna().copy()
            g["date"] = pd.to_datetime(g["date"])
            g["y"] = (mx.reindex(g["date"]).values >= thr).astype(float)
            g = g[mx.reindex(g["date"]).notna().values]
            if len(g):
                bm, bb = _brier(g[f"pup_{hz}"], g["y"]), _brier(g[f"bup_{hz}"], g["y"])
                rows.append({"kind": "rialzo", "hz": hz, "n": len(g), "brier": bm, "brier_base": bb, "bss": 1 - bm / bb if bb > 0 else np.nan,
                             "avg_p": float(g[f"pup_{hz}"].mean()), "freq": float(g["y"].mean())})
    except Exception:  # noqa: BLE001
        pass
    return pd.DataFrame(rows)


def update(sp: pd.Series, today=None) -> pd.DataFrame:
    """Aggiunge al diario dell'apprendimento la riga di oggi (una per tipo e orizzonte)."""
    t = live_table(sp)
    if t.empty:
        return t
    day = (today or pd.Timestamp.now()).strftime("%Y-%m-%d")
    t.insert(0, "date", day)
    old = pd.read_csv(LEARN) if LEARN.exists() else pd.DataFrame(columns=t.columns)
    out = pd.concat([old[old["date"] != day], t], ignore_index=True)
    out.to_csv(LEARN, index=False, float_format="%.5g")
    return t


def guard(sp: pd.Series) -> dict:
    """Controllo di degrado sui dati reali: True se il modello in uso va nettamente peggio del normale (BSS < -0,15) con dati sufficienti."""
    t = live_table(sp)
    t = t[(t.kind == "calo") & t.hz.isin(["1m", "3m"]) & (t.n >= GUARD_N)]
    bad = bool(len(t) and (t["bss"] < -0.15).all())
    return {"degraded": bad, "rows": t.to_dict("records")}


MIN_EVENTS_AUC = 40   # esiti con evento necessari per mostrare l'AUC dal vivo dell'Indice
EV_NAMES = {"dd5_21": "calo ≥5% in 1 mese", "dd10_63": "calo ≥10% in 3 mesi", "vol25_21": "volatilità >25% nel mese dopo"}


def index_live_auc(idx: pd.Series, ev: dict) -> dict:
    """AUC dal vivo dell'Indice Armor (2.4): solo giorni salvati nel registro con esito ormai noto. Mostrata solo con >= 40 esiti con evento."""
    from .armor_index import BANDS, _auc
    out = {"events": {}, "bands": [], "n_days": int(len(idx))}
    for k, y in ev.items():
        yy = y.reindex(idx.index)
        m = yy.notna()
        n, ne = int(m.sum()), int(yy[m].sum()) if m.any() else 0
        auc = _auc(idx[m], yy[m]) if ne >= MIN_EVENTS_AUC and n - ne >= MIN_EVENTS_AUC else None
        out["events"][k] = {"n": n, "n_events": ne, "auc": None if auc is None or auc != auc else float(auc)}
    lo = 0
    for lim, name, _t in BANDS:
        x = idx[(idx >= lo) & (idx < lim)]
        row = {"band": name, "n": int(len(x))}
        for k, y in ev.items():
            yy = y.reindex(x.index).dropna()
            row[k] = float(yy.mean()) if len(yy) else None
            row[k + "_n"] = int(len(yy))
        out["bands"].append(row)
        lo = lim
    return out


def index_live_html(sp: pd.Series) -> str:
    try:
        from . import armor_index
        reg = registry.read()
        if reg.empty or "armor_index" not in reg:
            raise ValueError("registro vuoto")
        r = reg[["date", "armor_index"]].dropna()
        idx = pd.Series(r["armor_index"].astype(float).values, index=pd.to_datetime(r["date"]))
        ev, _ = armor_index.events(sp)
        d = index_live_auc(idx, ev)
    except Exception:  # noqa: BLE001
        return "<p class='mu'>Indice Armor dal vivo: in raccolta.</p>"
    rows = ""
    for k, v in d["events"].items():
        a = ("<b>" + f"{v['auc']:.2f}".replace(".", ",") + "</b>") if v["auc"] is not None else f"in raccolta: servono {MIN_EVENTS_AUC} esiti con evento (ora {v['n_events']})"
        rows += f"<tr><td>{EV_NAMES[k]}</td><td>{v['n']}</td><td>{v['n_events']}</td><td>{a}</td></tr>"
    bands = "".join(f"<tr><td>{b['band']}</td><td>{b['n']}</td><td>{'n.d.' if b['dd10_63'] is None else str(round(b['dd10_63'] * 100)) + '%'}</td>"
                    f"<td>{'n.d.' if b['dd5_21'] is None else str(round(b['dd5_21'] * 100)) + '%'}</td></tr>" for b in d["bands"] if b["n"])
    return ("<h3>Indice Armor: verifica dal vivo</h3><div class='scroll'><table><tr><th>Evento</th><th>Giorni con esito</th><th>Con evento</th><th>AUC dal vivo (0,50 = caso)</th></tr>"
            + rows + "</table></div>"
            + (f"<div class='scroll'><table><tr><th>Fascia</th><th>Giorni salvati</th><th>Calo ≥10% a 3 mesi</th><th>Calo ≥5% a 1 mese</th></tr>{bands}</table></div>" if bands else "")
            + "<p class='mu'>Conta solo da quando Armor salva ogni giorno l'indice. I giorni vicini non sono indipendenti: servono molti mesi per un giudizio solido.</p>")


def _shadow(sp: pd.Series) -> str:
    try:
        from . import shadow
        return shadow.html(sp)
    except Exception:  # noqa: BLE001
        return ""


def html(sp: pd.Series) -> str:
    e = _h.escape
    t = live_table(sp)
    reg = registry.read()
    saved = (f"<p><b>Dati salvati ogni giorno:</b> il registro contiene <b>{len(reg)}</b> giorni (ultimo: {e(str(reg['date'].iloc[-1]))}) con tutti gli indicatori, le probabilità di calo e di rialzo e l'Indice Armor. "
             "Il diario delle previsioni è a prova di manomissione (catena di firme).</p>") if len(reg) else ""
    if t.empty:
        body = "<p class='mu'>Nessuna previsione è ancora scaduta: il confronto con la realtà comincia con la prima scadenza (10 giorni dopo la prima previsione).</p>"
    else:
        rows = ""
        for _, r in t.sort_values(["kind", "hz"], key=lambda c: c.map({"calo": 0, "rialzo": 1}) if c.name == "kind" else c.map({h: i for i, h in enumerate(HORIZONS)})).iterrows():
            ok = r["n"] >= MIN_N
            verdict = ("Armor fa meglio del normale" if r["bss"] > 0.02 else ("pari al normale" if r["bss"] > -0.05 else "peggio del normale")) if ok else "pochi casi: solo indicativo"
            cls = "" if not ok else ("up" if r["bss"] > 0.02 else ("" if r["bss"] > -0.05 else "dn"))
            rows += (f"<tr><td>{'Calo' if r['kind'] == 'calo' else 'Rialzo'} · {HZ_LABEL[r['hz']]}</td><td>{int(r['n'])}</td><td>{r['avg_p'] * 100:.0f}%</td><td>{r['freq'] * 100:.0f}%</td>"
                     f"<td class='{cls}'><b>{e(verdict)}</b></td></tr>")
        body = ("<div class='scroll'><table><tr><th>Previsione</th><th>Scadute</th><th>Probabilità media prevista</th><th>Successo reale</th><th>Esito</th></tr>" + rows + "</table></div>"
                "<p class='mu'>Se la probabilità media prevista è vicina alla frequenza reale, il modello è ben tarato. Con poche previsioni scadute il giudizio è solo indicativo.</p>")
    return ("<div class='card'><h3 style='margin-top:0'>Come impara Armor dai dati reali</h3>"
            "<div class='explain'><p>Ogni giorno Armor: <b>1)</b> salva tutti i dati; <b>2)</b> ricalcola il modello includendo anche i nuovi giorni e gli esiti ormai noti; "
            "<b>3)</b> confronta le previsioni scadute con quello che è successo davvero; <b>4)</b> ogni mese prova nuove variabili e nuovi algoritmi e adotta solo quelli nettamente migliori. "
            "Se il modello in uso, sui dati reali, va nettamente peggio del «normale», il controllo mensile torna al modello di base.</p></div>"
            + saved + body + index_live_html(sp) + _shadow(sp) + "</div>")
