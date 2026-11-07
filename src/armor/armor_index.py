"""Indice Armor: un solo numero da 1 (rischio minimo) a 100 (rischio altissimo di crollo e volatilità).

Come è costruito (tutto verificabile):
1. Ogni indicatore è trasformato in un punteggio di rischio 0-1: 60% dalle soglie fisse (le stesse dei semafori,
   interpolate in modo continuo) e 40% dalla posizione rispetto agli ultimi 10 anni (percentile).
2. Gli indicatori sono raggruppati in 8 famiglie; il punteggio di famiglia è la media degli indicatori disponibili.
3. L'indice è la media pesata delle famiglie (pesi fissi), portata sulla scala 1-100.
4. Il modello è verificato sulla storia dal 2000 usando solo dati disponibili il giorno prima (nessuno sguardo al futuro).
"""
import html as _h
import json

import numpy as np
import pandas as pd

from . import semafori, store
from .config import DATA

# gruppo -> (peso, [(chiave, tipo, giallo, rosso)])  tipo: hi = più alto peggio, lo = più basso peggio, pct = solo percentile
GROUPS = {
    "Paura e stress dei mercati": (22, [("vix", "hi", 20, 30), ("vterm", "lo", 1.05, 0.95), ("vvix", "hi", 100, 120), ("skew", "hi", 135, 150),
                                        ("move", "hi", 90, 120), ("rv21", "hi", 15, 25)]),
    "Credito e liquidità": (18, [("hy_oas", "hi", 4.5, 6), ("baa10y", "hi", 2.1, 2.8), ("nfci", "hi", -0.2, 0), ("stlfsi", "hi", 0, 1)]),
    "Tassi e obbligazioni": (8, [("t10y3m", "lo", 0.5, 0), ("t10y2y", "lo", 0.3, 0), ("real10y", "hi", 1.5, 2.2), ("dgs10", "hi", 4, 5)]),
    "Valutazioni": (12, [("cape_m", "hi", 28, 35), ("pe_m", "hi", 18, 24), ("ps_m", "hi", 2, 3)]),
    "Tendenza dei prezzi": (12, [("dd252", "hi", 5, 10), ("ma200", "lo", 0, -5)]),
    "Sentimento e ampiezza": (8, [("aaii_spread", "hi", 10, 30), ("breadth200", "lo", 55, 40), ("usd_broad", "pct", None, None)]),
    "Economia reale": (6, [("sahm", "hi", 0.3, 0.5), ("icsa", "hi", 250000, 300000)]),
    "Modello statistico Armor": (14, [("risk_1m", "pct", None, None), ("risk_3m", "pct", None, None)]),
}
LAGS = {"daily": 5, "weekly": 10, "monthly": 45}
WINDOW = 2520   # circa 10 anni di sedute
START_EVAL = "2000-01-01"
CACHE = DATA / "armor_index_eval.json"
BANDS = [(20, "molto basso", "Calma: il mercato è stabile, i segnali di rischio sono pochi."),
         (40, "basso", "Rischio contenuto: nessun segnale diffuso di tensione."),
         (60, "moderato", "Rischio nella norma alta: qualche segnale di tensione, nessun allarme generale."),
         (80, "elevato", "Rischio elevato: più famiglie di indicatori segnalano tensione. Prudenza."),
         (101, "molto alto", "Rischio molto alto: stress diffuso, tipico dei momenti di crisi.")]


def band(v: float) -> tuple[str, str]:
    for lim, name, txt in BANDS:
        if v < lim:
            return name, txt
    return BANDS[-1][1], BANDS[-1][2]


def color(v: float) -> str:
    h = 125 * (1 - min(max((v - 1) / 99, 0), 1))   # verde (125) -> rosso (0)
    return f"hsl({h:.0f},70%,45%)"


def _thresh_score(x: pd.Series, kind: str, y: float, r: float) -> pd.Series:
    if kind == "hi":
        xp, fp = [y - (r - y), y, r, r + (r - y)], [0, .35, .7, 1]
    else:  # lo: più basso = peggio, y > r
        xp, fp = [r - (y - r), r, y, y + (y - r)], [1, .7, .35, 0]
    return pd.Series(np.interp(x.values, xp, fp), index=x.index).where(x.notna())


def _raw_series(key: str, sp: pd.Series) -> pd.Series:
    if key in ("risk_1m", "risk_3m"):
        f = DATA / "risk_history.csv"
        if not f.exists():
            return pd.Series(dtype=float)
        h = pd.read_csv(f)
        return pd.Series(h["p_" + key[5:]].values, index=pd.to_datetime(h["date"])).dropna()
    return semafori.series_of(key, sp)


def _limit(key: str) -> int:
    if key in ("cape_m", "pe_m", "ps_m", "sahm"):
        return LAGS["monthly"]
    if key in ("risk_1m", "risk_3m"):
        return LAGS["monthly"]
    if key in ("nfci", "stlfsi", "icsa", "aaii_spread"):
        return LAGS["weekly"]
    return LAGS["daily"]


def build_scores(sp: pd.Series) -> tuple[pd.DataFrame, dict]:
    """Punteggi di rischio 0-1 per indicatore, allineati ai giorni di borsa (senza ritardo). Restituisce (tabella, valori grezzi ultimi)."""
    idx = sp.index[sp.index >= "1995-01-01"]
    cols, last = {}, {}
    for _g, (_w, items) in GROUPS.items():
        for key, kind, y, r in items:
            try:
                s = _raw_series(key, sp)
                s = s[~s.index.duplicated(keep="last")].dropna()
                if len(s) < 60 or (idx[-1] - s.index[-1]).days > 400:
                    continue
                a = s.reindex(s.index.union(idx)).ffill(limit=_limit(key)).reindex(idx)
                pr = a.rolling(WINDOW, min_periods=500).rank(pct=True)
                if kind == "pct":
                    sc = pr
                else:
                    sc = 0.6 * _thresh_score(a, kind, y, r) + 0.4 * pr
                    sc = sc.fillna(_thresh_score(a, kind, y, r))   # senza abbastanza storia si usano solo le soglie
                cols[key] = sc
                last[key] = float(s.iloc[-1])
            except Exception:  # noqa: BLE001
                continue
    return pd.DataFrame(cols, index=idx), last


def combine(S: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Indice 1-100 e punteggi di famiglia (NaN se mancano più di metà degli indicatori della famiglia)."""
    G = {}
    for g, (_w, items) in GROUPS.items():
        keys = [k for k, *_ in items if k in S]
        if not keys:
            G[g] = pd.Series(np.nan, index=S.index)
            continue
        n = S[keys].notna().sum(axis=1)
        G[g] = S[keys].mean(axis=1).where(n >= max(1, np.ceil(len(items) / 2)))
    G = pd.DataFrame(G)
    w = pd.Series({g: GROUPS[g][0] for g in GROUPS})
    ok = G.notna()
    wsum = (ok * w).sum(axis=1)
    val = (G.fillna(0) * w).sum(axis=1) / wsum.replace(0, np.nan)
    val = ((val - 0.10) / 0.75).clip(0, 1)   # scala: gli indicatori non sono mai tutti al massimo insieme, neppure nel 2008 (raw ≈ 0,78)
    idx = (1 + 99 * val).where(wsum >= 0.5 * w.sum())
    return idx, G


def _auc(score: pd.Series, y: pd.Series) -> float:
    d = pd.concat([score, y], axis=1).dropna()
    d.columns = ["s", "y"]
    n1 = int(d["y"].sum())
    n0 = len(d) - n1
    if n1 < 20 or n0 < 20:
        return float("nan")
    r = d["s"].rank()
    return float((r[d["y"] == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def evaluate(sp: pd.Series, idx: pd.Series) -> dict:
    """Verifica storica onesta: indice di ieri contro eventi dei giorni successivi (dal 2000)."""
    p = sp[sp.index >= "1995-01-01"]
    n = len(p)
    v = p.values
    fut_min63 = np.full(n, np.nan)
    fut_min21 = np.full(n, np.nan)
    for i in range(n - 63):
        fut_min63[i] = v[i + 1:i + 64].min() / v[i] - 1
    for i in range(n - 21):
        fut_min21[i] = v[i + 1:i + 22].min() / v[i] - 1
    ret = np.log(p).diff()
    fvol = ret[::-1].rolling(21).std()[::-1].shift(-1) * np.sqrt(252) * 100
    ev = {
        "dd10_63": pd.Series(np.where(np.isnan(fut_min63), np.nan, (fut_min63 <= -0.10).astype(float)), index=p.index),
        "dd5_21": pd.Series(np.where(np.isnan(fut_min21), np.nan, (fut_min21 <= -0.05).astype(float)), index=p.index),
        "vol25_21": pd.Series(np.where(fvol.isna(), np.nan, (fvol >= 25).astype(float)), index=p.index),
    }
    lag = idx.shift(1)[START_EVAL:]
    out = {"auc": {}, "base": {}, "buckets": [], "n_days": int(lag.notna().sum()), "from": str(lag.dropna().index[0].date()) if lag.notna().any() else None}
    for k, y in ev.items():
        y = y.reindex(lag.index)
        out["auc"][k] = _auc(lag, y)
        out["base"][k] = float(y.mean())
    d = pd.concat([lag.rename("i"), ev["dd10_63"].reindex(lag.index).rename("a"), ev["dd5_21"].reindex(lag.index).rename("b"),
                   ev["vol25_21"].reindex(lag.index).rename("c"), pd.Series(fut_min63, index=p.index).reindex(lag.index).rename("m")], axis=1).dropna(subset=["i"])
    for lo, hi in [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]:
        x = d[(d["i"] >= lo) & (d["i"] < hi)]
        out["buckets"].append({"lo": lo, "hi": min(hi, 100), "n": int(len(x)), "dd10_63": None if x["a"].dropna().empty else float(x["a"].mean()),
                               "dd5_21": None if x["b"].dropna().empty else float(x["b"].mean()),
                               "vol25_21": None if x["c"].dropna().empty else float(x["c"].mean()),
                               "worst": None if x["m"].dropna().empty else float(x["m"].mean())})
    return out


def compute(sp: pd.Series, use_cache: bool = True) -> dict | None:
    try:
        S, last = build_scores(sp)
        if S.empty:
            return None
        idx, G = combine(S)
        idx = idx.dropna()
        if idx.empty:
            return None
        t = idx.index[-1]
        val = float(idx.iloc[-1])
        ev = None
        if use_cache and CACHE.exists():
            try:
                c = json.loads(CACHE.read_text(encoding="utf-8"))
                if c.get("date") == str(t.date()):
                    ev = c["eval"]
            except Exception:  # noqa: BLE001
                ev = None
        if ev is None:
            ev = evaluate(sp, combine(S)[0])
            try:
                CACHE.write_text(json.dumps({"date": str(t.date()), "eval": ev}), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
        groups = []
        for g, (w, items) in GROUPS.items():
            sc = G.loc[t, g] if g in G else np.nan
            its = []
            for key, *_ in items:
                if key in S and pd.notna(S.loc[t, key]):
                    nm = semafori.SPEC_BY[key][1] if key in semafori.SPEC_BY else {"risk_1m": "Probabilità di calo a 1 mese (Armor)", "risk_3m": "Probabilità di calo a 3 mesi (Armor)"}.get(key, key)
                    its.append({"key": key, "name": nm, "score": float(S.loc[t, key]), "value": last.get(key)})
            groups.append({"name": g, "weight": w, "score": None if pd.isna(sc) else float(sc), "items": its})
        prev = float(idx.iloc[-6]) if len(idx) > 6 else val
        return {"value": val, "date": t, "hist": idx, "groups": groups, "eval": ev, "change5": val - prev}
    except Exception as e:  # noqa: BLE001
        print("Indice Armor non calcolato:", str(e)[:120], flush=True)
        return None


def save_history(d: dict) -> None:
    """Salva la storia nelle serie (così l'indice si può aprire e guardare nei grafici)."""
    try:
        store.upsert("armor_index", d["hist"][d["hist"].index >= "2000-01-01"])
    except Exception:  # noqa: BLE001
        pass


def thermometer(v: float, h: int = 150) -> str:
    """Termometro in SVG: verde in basso (calma), rosso in alto (rischio); il livello indica l'indice."""
    pctv = min(max((v - 1) / 99, 0), 1)
    top, bot = 10, h - 34
    ylev = bot - (bot - top) * pctv
    return (f"<svg class='thermo' viewBox='0 0 70 {h}' width='62' height='{h}' role='img' aria-label='Termometro del rischio: {v:.0f} su 100'>"
            f"<defs><linearGradient id='tg' x1='0' y1='1' x2='0' y2='0'><stop offset='0' stop-color='hsl(125,65%,42%)'/><stop offset='.5' stop-color='hsl(55,80%,48%)'/>"
            f"<stop offset='1' stop-color='hsl(0,75%,48%)'/></linearGradient><clipPath id='tc'><rect x='24' y='{ylev:.1f}' width='16' height='{h}'/></clipPath></defs>"
            f"<rect x='24' y='{top}' width='16' height='{bot - top + 8}' rx='8' fill='none' stroke='currentColor' stroke-opacity='.35' stroke-width='2'/>"
            f"<g clip-path='url(#tc)'><rect x='26' y='{top}' width='12' height='{bot - top + 10}' rx='6' fill='url(#tg)'/>"
            f"<circle cx='32' cy='{h - 20}' r='14' fill='url(#tg)'/></g>"
            f"<circle cx='32' cy='{h - 20}' r='15' fill='none' stroke='currentColor' stroke-opacity='.35' stroke-width='2'/>"
            f"<circle cx='32' cy='{h - 20}' r='11' fill='{color(v)}'/>"
            f"<line x1='44' y1='{ylev:.1f}' x2='54' y2='{ylev:.1f}' stroke='{color(v)}' stroke-width='3'/>"
            f"<text x='68' y='{top + 4}' font-size='9' text-anchor='end' fill='currentColor'>100</text>"
            f"<text x='68' y='{bot + 2}' font-size='9' text-anchor='end' fill='currentColor'>1</text></svg>")


def hero_html(d: dict | None) -> str:
    if not d:
        return ""
    v = d["value"]
    name, txt = band(v)
    ch = d["change5"]
    arrow = "▲" if ch > 1 else ("▼" if ch < -1 else "▬")
    return (f"<div class='aix' data-chart='armor_index'><div class='aixt'>{thermometer(v)}</div>"
            f"<div class='aixb'><div class='aixk'>Indice Armor</div><div class='aixv' style='color:{color(v)}'>{v:.0f}<span>/100</span></div>"
            f"<div class='aixl' style='color:{color(v)}'>Rischio {name}</div><div class='aixd'>{_h.escape(txt)}</div>"
            f"<div class='aixc'>{arrow} {ch:+.0f} punti in 5 sedute · <a href='#indici' data-go='indici'>Come è calcolato ›</a></div></div></div>")


def _pc(x) -> str:
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.0f}%".replace(".", ",")


def detail_html(d: dict | None) -> str:
    if not d:
        return "<div class='card'><h3 style='margin-top:0'>Indice Armor</h3><p class='mu'>Non ancora disponibile: servono i dati degli indicatori (si completano dopo il prossimo aggiornamento giornaliero).</p></div>"
    v = d["value"]
    name, txt = band(v)
    rows = ""
    contrib = []
    avail_w = sum(g["weight"] for g in d["groups"] if g["score"] is not None)
    for g in d["groups"]:
        sc = g["score"]
        bar = "" if sc is None else f"<div class='gb'><i style='width:{sc * 100:.0f}%;background:{color(1 + 99 * sc)}'></i></div>"
        rows += (f"<tr><td>{_h.escape(g['name'])}</td><td>{g['weight']}</td><td>{'n.d.' if sc is None else f'{1 + 99 * min(max((sc - 0.10) / 0.75, 0), 1):.0f}'}</td><td>{bar}</td></tr>")
        if sc is not None:
            for it in g["items"]:
                contrib.append((it["score"] * g["weight"] / max(len(g["items"]), 1) / avail_w, it))
    contrib.sort(key=lambda x: -x[0])
    top = "".join(f"<li><b>{_h.escape(i['name'])}</b>: rischio {i['score'] * 100:.0f}/100</li>" for _c, i in contrib[:5])
    low = "".join(f"<li>{_h.escape(i['name'])}: {i['score'] * 100:.0f}/100</li>" for _c, i in sorted(contrib, key=lambda x: x[1]["score"])[:3])
    ev = d["eval"]
    auc = ev["auc"]
    b = ""
    for x in ev["buckets"]:
        b += (f"<tr><td>{x['lo'] or 1}–{x['hi']}</td><td>{x['n']:,}".replace(",", ".") +
              f"</td><td>{_pc(x['dd5_21'])}</td><td>{_pc(x['dd10_63'])}</td><td>{_pc(x['vol25_21'])}</td>"
              f"<td>{'n.d.' if x['worst'] is None else f'{x[chr(119) + chr(111) + chr(114) + chr(115) + chr(116)] * 100:.1f}%'.replace('.', ',')}</td></tr>")
    f = lambda k: "n.d." if np.isnan(auc[k]) else f"{auc[k]:.2f}".replace(".", ",")
    return (f"<div class='card'><h3 style='margin-top:0'>Indice Armor: come è calcolato</h3>"
            f"<p>Oggi l'indice vale <b>{v:.0f}</b> su 100 (<b>rischio {name}</b>). {_h.escape(txt)}</p>"
            "<p class='mu'>1 = rischio minimo, 100 = rischio altissimo di crollo e volatilità. Unisce decine di indicatori in 8 famiglie con pesi fissi. "
            "Ogni indicatore pesa per il 60% dalle soglie dei semafori e per il 40% da quanto il valore è alto o basso rispetto agli ultimi 10 anni.</p>"
            f"<table><tr><th>Famiglia</th><th>Peso</th><th>Rischio (1–100)</th><th></th></tr>{rows}</table>"
            f"<div class='hrow'><div class='hbox r'><h4>Cosa spinge l'indice in alto</h4><ul>{top}</ul></div><div class='hbox o'><h4>Cosa lo tiene basso</h4><ul>{low}</ul></div></div>"
            f"<details><summary><b>Quanto è affidabile? Verifica sulla storia dal {ev['from'][:4] if ev['from'] else '2000'}</b></summary>"
            f"<p>Ogni giorno si guarda l'indice <b>del giorno prima</b> e si conta cosa è successo dopo. Più l'indice è alto, più dovrebbero essere frequenti i cali.</p>"
            f"<table><tr><th>Indice</th><th>Giorni</th><th>Calo ≥5% in 1 mese</th><th>Calo ≥10% in 3 mesi</th><th>Volatilità &gt;25% nel mese dopo</th><th>Calo massimo medio a 3 mesi</th></tr>{b}</table>"
            f"<p class='mu'>Capacità di distinguere i periodi a rischio (AUC; 0,50 = caso, 1,00 = perfetto): calo ≥5% a 1 mese <b>{f('dd5_21')}</b>, calo ≥10% a 3 mesi <b>{f('dd10_63')}</b>, "
            f"volatilità alta <b>{f('vol25_21')}</b>. Frequenza media: {_pc(ev['base']['dd5_21'])}, {_pc(ev['base']['dd10_63'])}, {_pc(ev['base']['vol25_21'])}.</p>"
            "<p class='mu'>Limiti onesti: i giorni vicini non sono indipendenti, alcuni indicatori hanno storia più corta, i crolli improvvisi (es. 2020) non si prevedono. "
            "È una misura dello stato di tensione del mercato, non una previsione certa.</p></details></div>")


CSS = """
.aix{display:flex;gap:14px;align-items:center;background:rgba(255,255,255,.55);border-radius:14px;padding:10px 14px;margin:10px 0;cursor:pointer;color:var(--fg)}
.aixb{flex:1;min-width:0}.aixk{font-size:12px;font-weight:700;text-transform:uppercase;opacity:.7}.aixv{font-size:44px;font-weight:800;line-height:1.05}.aixv span{font-size:16px;opacity:.6}
.aixl{font-weight:800;font-size:16px}.aixd{font-size:13px;margin-top:2px}.aixc{font-size:12px;opacity:.75;margin-top:4px}
.gb{width:120px;height:9px;background:rgba(128,128,128,.25);border-radius:5px;overflow:hidden}.gb i{display:block;height:100%}
@media (prefers-color-scheme:dark){.aix{background:rgba(255,255,255,.08)}}
"""
