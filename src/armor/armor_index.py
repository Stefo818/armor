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
# nuovi indicatori di credito (suggeriti da DeepSeek): monitorati da subito, entrano nell'Indice solo se il test automatico li adotta (data/armor_extra.json)
NEW_IND = {"anfci": ("hi", 0, 0.5), "sloos": ("hi", 10, 30), "credit_gap": ("hi", 2, 10)}
# indicatori nuovi del PIANO_MODELLO (salute delle aziende, inflazione, liquidità, mercato interno): stessa regola di adozione,
# ognuno provato dentro la famiglia dell'Indice più vicina. Finché non sono adottati restano solo nei semafori («monitorato»).
NEW_IND_FOND = {
    "eps_g12": ("Economia reale", "lo", 0, -10), "delinq_biz": ("Economia reale", "hi", 1.5, 2.5),
    "chargeoff_biz": ("Economia reale", "hi", 0.6, 1.0), "busloans_g6": ("Economia reale", "lo", 0, -3),
    "cfnai": ("Economia reale", "lo", -0.35, -0.7), "claims_up": ("Economia reale", "hi", 15, 25),
    "ccsa_yoy": ("Economia reale", "hi", 10, 20), "permit_yoy": ("Economia reale", "lo", -10, -20),
    "cpi_yoy": ("Tassi e obbligazioni", "hi", 3, 4.5), "core_yoy": ("Tassi e obbligazioni", "hi", 3, 4),
    "real_ff": ("Tassi e obbligazioni", "hi", 1.5, 2.5),
    "net_liq_13w": ("Credito e liquidità", "lo", 0, -4), "m2_yoy": ("Credito e liquidità", "lo", 2, 0),
    "nfci_leverage": ("Credito e liquidità", "hi", 0, 0.5), "kcfsi": ("Credito e liquidità", "hi", 0, 1),
    "ciss": ("Credito e liquidità", "hi", 0.2, 0.4), "margin_yoy": ("Credito e liquidità", "hi", 30, 50),
    "rel_small": ("Sentimento e ampiezza", "lo", -3, -8), "rel_eqw": ("Sentimento e ampiezza", "lo", -3, -6),
    "rel_cicl": ("Sentimento e ampiezza", "lo", -3, -8), "rel_credito": ("Sentimento e ampiezza", "lo", -1.5, -4),
}
FREQ_FOND = {"eps_g12": "m", "delinq_biz": "q", "chargeoff_biz": "q", "busloans_g6": "m", "cfnai": "m", "claims_up": "w", "ccsa_yoy": "w",
             "permit_yoy": "m", "cpi_yoy": "m", "core_yoy": "m", "real_ff": "m", "net_liq_13w": "w", "m2_yoy": "m", "nfci_leverage": "w",
             "kcfsi": "m", "ciss": "d", "margin_yoy": "m"}


def _new_items() -> list:
    """(chiave, famiglia, tipo, soglia gialla, soglia rossa) di tutti gli indicatori candidati all'Indice."""
    return [(k, "Credito e liquidità", *v) for k, v in NEW_IND.items()] + [(k, *v) for k, v in NEW_IND_FOND.items()]


def _apply_extra() -> None:
    try:
        ad = json.loads(EXTRA_FILE.read_text(encoding="utf-8")).get("adopted", [])
    except Exception:  # noqa: BLE001
        ad = []
    for k, fam, kind, y, r in _new_items():
        items = GROUPS[fam][1]
        if k in ad and k not in {x for x, *_ in items}:
            items.append((k, kind, y, r))


_apply_extra()
WEIGHTS_FILE = DATA / "armor_weights.json"
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
    if key in FREQ_FOND:
        return {"q": 120, "m": LAGS["monthly"], "w": LAGS["weekly"], "d": LAGS["daily"]}[FREQ_FOND[key]]
    if key in ("sloos", "credit_gap"):
        return 120   # dati trimestrali: restano validi per ~un trimestre
    if key == "anfci":
        return LAGS["weekly"]
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


def weights_in_use() -> dict:
    """Pesi delle famiglie: quelli fissi, oppure quelli stimati se la verifica annuale (check_weights) li ha adottati."""
    w = {g: float(GROUPS[g][0]) for g in GROUPS}
    try:
        c = json.loads(WEIGHTS_FILE.read_text(encoding="utf-8"))
        if c.get("adopted") and set(c.get("weights_est", {})) == set(w):
            return {g: float(c["weights_est"][g]) for g in w}
    except Exception:  # noqa: BLE001
        pass
    return w


def combine(S: pd.DataFrame, weights: dict | None = None) -> tuple[pd.Series, pd.DataFrame]:
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
    w = pd.Series(weights or weights_in_use())
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


def events(sp: pd.Series) -> tuple[dict, pd.Series]:
    """Eventi futuri (NaN dove l'esito non e' ancora noto): calo>=5% in 21 sedute, calo>=10% in 63, volatilita'>=25% nelle 21 successive."""
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
    return ev, pd.Series(fut_min63, index=p.index)


def iso_probs(idx: pd.Series, ev: dict, v: float, start: str = START_EVAL, band: float = 5.0) -> dict:
    """Dall'indice alla probabilita' (2.1): regressione isotonica crescente tra l'indice del giorno e l'evento nei giorni successivi,
    solo con esiti gia' noti. Restituisce per ogni evento la probabilita' con indice = v, la frequenza media (normale) e i giorni simili."""
    from sklearn.isotonic import IsotonicRegression
    out = {"v": float(v), "events": {}}
    x0 = idx[start:].dropna()
    for k, y in ev.items():
        d = pd.concat([x0.rename("i"), y.reindex(x0.index).rename("y")], axis=1).dropna()
        if len(d) < 200 or d["y"].sum() < 20:
            continue
        m = IsotonicRegression(increasing=True, y_min=0, y_max=1, out_of_bounds="clip").fit(d["i"].values, d["y"].values)
        out["events"][k] = {"p": float(m.predict([v])[0]), "base": float(d["y"].mean()),
                            "n_near": int(((d["i"] - v).abs() <= band).sum()), "n": int(len(d))}
    return out


def evaluate(sp: pd.Series, idx: pd.Series) -> dict:
    """Verifica storica onesta: indice di ieri contro eventi dei giorni successivi (dal 2000)."""
    ev, fm63 = events(sp)
    p = sp[sp.index >= "1995-01-01"]
    fut_min63 = fm63.values
    lag = idx.shift(1)[START_EVAL:]
    vnow = idx.dropna()
    prob = iso_probs(idx, ev, float(vnow.iloc[-1])) if len(vnow) else {}
    out = {"prob": prob, "auc": {}, "base": {}, "buckets": [], "n_days": int(lag.notna().sum()), "from": str(lag.dropna().index[0].date()) if lag.notna().any() else None}
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
            groups.append({"name": g, "weight": weights_in_use()[g], "score": None if pd.isna(sc) else float(sc), "items": its})
        prev = float(idx.iloc[-6]) if len(idx) > 6 else val
        return {"value": val, "date": t, "hist": idx, "groups": groups, "eval": ev, "change5": val - prev, "G": G, "S": S}
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


def prob_line(d: dict | None) -> str:
    """Frase sull'indice come probabilita' storica (isotonica)."""
    try:
        e = d["eval"]["prob"]["events"]
        v = d["eval"]["prob"]["v"]
        a, b = e["dd10_63"], e["dd5_21"]
        f = lambda x: f"{x * 100:.0f}%"
        return (f"Con un indice a {v:.0f}, in passato un calo ≥10% entro 3 mesi è arrivato nel <b>{f(a['p'])}</b> dei casi (normale {f(a['base'])}); "
                f"un calo ≥5% entro 1 mese nel <b>{f(b['p'])}</b> (normale {f(b['base'])}).")
    except Exception:  # noqa: BLE001
        return ""


def hero_html(d: dict | None, extra: str = "") -> str:
    if not d:
        return ""
    v = d["value"]
    name, txt = band(v)
    ch = d["change5"]
    arrow = "▲" if ch > 1 else ("▼" if ch < -1 else "▬")
    return (f"<div class='aix' data-amod='1'><div class='aixt'>{thermometer(v)}</div>"
            f"<div class='aixb'><div class='aixk'>Indice Armor</div><div class='aixv' style='color:{color(v)}'>{v:.0f}<span>/100</span></div>"
            f"<div class='aixl' style='color:{color(v)}'>Rischio {name}</div><div class='aixd'>{_h.escape(txt)}</div>"
            f"<div class='aixp'>{prob_line(d)}</div><div class='aixc'>{arrow} {ch:+.0f} punti in 5 sedute · <a href='#indici' data-go='indici'>Come è calcolato ›</a></div>{extra}<div class='aixc'><b>Tocca per vedere i tre indici: 1 settimana, 1 mese, 3 mesi ›</b></div></div></div>")


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
            f"<p>{prob_line(d)} <span class='mu'>(regressione isotonica sui giorni dal 2000, solo esiti già noti; giorni con indice simile: {d['eval'].get('prob', {}).get('events', {}).get('dd10_63', {}).get('n_near', 'n.d.')}; i giorni vicini non sono indipendenti)</span></p>"
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
.aixp{font-size:13px;margin-top:6px}.aixl{font-weight:800;font-size:16px}.aixd{font-size:13px;margin-top:2px}.aixc{font-size:12px;opacity:.75;margin-top:4px}
.gb{width:120px;height:9px;background:rgba(128,128,128,.25);border-radius:5px;overflow:hidden}.gb i{display:block;height:100%}
@media (prefers-color-scheme:dark){.aix{background:rgba(255,255,255,.08)}}
"""


# ---------- 2.3 famiglie come variabili del modello ----------
FAM_MV = ["Paura e stress dei mercati", "Credito e liquidità", "Tassi e obbligazioni", "Valutazioni", "Tendenza dei prezzi", "Economia reale"]
FAM_LAG = {"Valutazioni": 30, "Economia reale": 30, "Credito e liquidità": 5}   # sedute di ritardo (dati mensili/settimanali); le altre 1
FAM_SHORT = {"Paura e stress dei mercati": "fam_paura", "Credito e liquidità": "fam_credito", "Tassi e obbligazioni": "fam_tassi",
             "Valutazioni": "fam_valut", "Tendenza dei prezzi": "fam_tend", "Economia reale": "fam_econ"}


def family_features(sp: pd.Series) -> pd.DataFrame:
    """Punteggi 0-1 delle famiglie con storia lunga, spostati del ritardo di pubblicazione (nessuno sguardo al futuro).
    Escluse: «Sentimento e ampiezza» (storia corta) e «Modello statistico Armor» (circolare: usa le previsioni del modello stesso)."""
    S, _ = build_scores(sp)
    _i, G = combine(S)
    out = {}
    for g in FAM_MV:
        if g in G:
            out[FAM_SHORT[g]] = G[g].shift(FAM_LAG.get(g, 1))
    return pd.DataFrame(out)


# ---------- 2.2 pesi stimati contro pesi fissi ----------
def _auc_np(score, y) -> float:
    return _auc(pd.Series(score), pd.Series(y))


def fit_weights_logit(G: np.ndarray, Y: list, lam: float = 1e-3) -> np.ndarray:
    """Coefficienti >= 0 sulle famiglie (una logistica per evento con intercetta propria, coefficienti condivisi)."""
    from scipy.optimize import minimize
    k = G.shape[1]
    ne = len(Y)

    def f(th):
        c, b = th[:k], th[k:]
        tot = 0.0
        for j, (m, y) in enumerate(Y):
            z = G[m] @ c + b[j]
            tot += np.mean(np.logaddexp(0, z) - y * z)
        return tot / ne + lam * float(c @ c)
    r = minimize(f, np.r_[np.ones(k), np.full(ne, -2.0)], method="L-BFGS-B", bounds=[(0, None)] * k + [(None, None)] * ne)
    return r.x[:k]


def check_weights(sp: pd.Series, today=None, force: bool = False, train_end: str = "2012-09-30", test_start: str = "2013-01-01") -> dict:
    """Verifica dei pesi (2.2). Pesi stimati con dati fino a train_end (con 63 sedute di distanza dai test); li adotta solo se l'AUC
    dal 2013 migliora di almeno 0,02 su almeno 2 eventi su 3 rispetto ai pesi fissi. Si rifa' al massimo una volta l'anno."""
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    if WEIGHTS_FILE.exists() and not force:
        try:
            c = json.loads(WEIGHTS_FILE.read_text(encoding="utf-8"))
            if (today - pd.Timestamp(c["date"])).days < 365:
                return c
        except Exception:  # noqa: BLE001
            pass
    S, _ = build_scores(sp)
    _i, G = combine(S)
    names = list(GROUPS)
    Gf = G[names].shift(1)                                   # solo informazioni del giorno prima
    Gf = Gf.apply(lambda r: r.fillna(r.mean()), axis=1)      # famiglia mancante = media delle altre
    ev, _fm = events(sp)
    Gf = Gf.dropna(how="any")
    wf = np.array([GROUPS[g][0] for g in names], float)
    tr = Gf[(Gf.index >= START_EVAL) & (Gf.index <= train_end)]
    te = Gf[Gf.index >= test_start]
    Y = []
    for k in ("dd5_21", "dd10_63", "vol25_21"):
        y = ev[k].reindex(tr.index)
        m = y.notna().values
        Y.append((np.where(m)[0], y.values[m]))
    # nota: gli indici in Y si riferiscono alle righe di tr
    c = fit_weights_logit(tr.values, [(m, y) for m, y in Y])
    west = c / c.sum() * 100 if c.sum() > 0 else wf
    res = {"date": str(today.date()), "train_end": train_end, "test_start": test_start, "auc_fixed": {}, "auc_est": {}, "gain": {}}
    better = 0
    for k in ("dd5_21", "dd10_63", "vol25_21"):
        y = ev[k].reindex(te.index)
        af, ae = _auc_np((te.values @ wf)[y.notna().values], y.dropna().values), _auc_np((te.values @ west)[y.notna().values], y.dropna().values)
        res["auc_fixed"][k], res["auc_est"][k], res["gain"][k] = af, ae, ae - af
        better += int(ae - af >= 0.02)
    res["better_events"] = better
    res["adopted"] = bool(better >= 2)
    res["weights_fixed"] = {g: float(w) for g, w in zip(names, wf)}
    res["weights_est"] = {g: float(w) for g, w in zip(names, west)}
    res["rule"] = "adottati solo se l'AUC dal 2013 migliora di almeno 0,02 su 2 eventi su 3; verifica al massimo una volta l'anno"
    try:
        WEIGHTS_FILE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return res


# ---------- tre orizzonti: settimana, mese, 3 mesi (pesi fissati in anticipo, non stimati) ----------
HZ_WEIGHTS = {
    "settimana": {"Paura e stress dei mercati": 34, "Credito e liquidità": 14, "Tassi e obbligazioni": 4, "Valutazioni": 2, "Tendenza dei prezzi": 22,
                  "Sentimento e ampiezza": 10, "Economia reale": 2, "Modello statistico Armor": 12},
    "mese": {g: float(v[0]) for g, v in GROUPS.items()},
    "3 mesi": {"Paura e stress dei mercati": 14, "Credito e liquidità": 22, "Tassi e obbligazioni": 10, "Valutazioni": 20, "Tendenza dei prezzi": 8,
               "Sentimento e ampiezza": 6, "Economia reale": 10, "Modello statistico Armor": 10},
}
HZ_FILE = DATA / "armor_horizons.json"
HZ_EVENT = {"settimana": ("calo ≥5% in 10 sedute", 10, 0.05), "mese": ("calo ≥5% in 21 sedute", 21, 0.05), "3 mesi": ("calo ≥10% in 63 sedute", 63, 0.10)}


def horizons(d: dict | None, sp: pd.Series, recompute: bool = False) -> dict | None:
    """Tre indici (1-100) con pesi diversi per orizzonte + AUC storica di ciascuno contro il suo evento (cache mensile in data/armor_horizons.json)."""
    if not d:
        return None
    S = d["S"]
    out = {"orizzonti": {}, "media": None}
    cache = {}
    try:
        cache = json.loads(HZ_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    series = {k: combine(S, w)[0].dropna() for k, w in HZ_WEIGHTS.items()}
    vals = {}
    for k, ser in series.items():
        vals[k] = {"v": float(ser.iloc[-1]), "ieri": float(ser.iloc[-2]), "sett": float(ser.iloc[-6])}
    ok = cache.get("date") == str(d["date"].date()) and not recompute
    if not ok:
        p = sp[sp.index >= "1995-01-01"]
        v = p.values
        ev = {}
        for k, (_n, h, thr) in HZ_EVENT.items():
            fm = np.full(len(p), np.nan)
            for i in range(len(p) - h):
                fm[i] = v[i + 1:i + h + 1].min() / v[i] - 1
            ev[k] = pd.Series(np.where(np.isnan(fm), np.nan, (fm <= -thr).astype(float)), index=p.index)
        std = d["hist"]
        cache = {"date": str(d["date"].date()), "auc": {}}
        for k, ser in series.items():
            lag = ser.shift(1)[START_EVAL:]
            lag_s = std.shift(1)[START_EVAL:]
            y = ev[k].reindex(lag.index)
            y13 = y[y.index >= "2013-01-01"]
            cache["auc"][k] = {"nuovo": _auc(lag, y), "standard": _auc(lag_s, y), "nuovo_2013": _auc(lag[lag.index >= "2013-01-01"], y13),
                               "standard_2013": _auc(lag_s[lag_s.index >= "2013-01-01"], y13), "evento": HZ_EVENT[k][0]}
        try:
            HZ_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    for k in vals:
        vals[k]["auc"] = cache.get("auc", {}).get(k)
    out["orizzonti"] = vals
    out["media"] = float(np.mean([x["v"] for x in vals.values()]))
    out["pesi"] = HZ_WEIGHTS
    return out


def test_new_indicators(sp: pd.Series, force: bool = False) -> dict:
    """Prova onesta dei nuovi indicatori (credito: ANFCI, SLOOS, Credit-to-GDP gap; PIANO_MODELLO: salute delle aziende, inflazione, liquidità, mercato interno): ognuno si aggiunge alla sua famiglia (credito: «Credito e liquidità») e si confronta
    l'AUC dell'Indice (indice di ieri contro i 3 eventi, dal 2013) con e senza. Si adotta solo se migliora di ≥0,01 in almeno 2 eventi su 3 e nessuno peggiora di più di 0,01
    (stessa regola usata per gli altri modelli). Rifatta al massimo una volta al mese; scrive data/armor_extra.json."""
    import datetime as _dt
    old = {}
    try:
        old = json.loads(EXTRA_FILE.read_text(encoding="utf-8"))
        if not force and old.get("date", "")[:7] == _dt.date.today().isoformat()[:7]:
            return old
    except Exception:  # noqa: BLE001
        pass
    ev, _fm = events(sp)
    idx_s = sp.index[sp.index >= "1995-01-01"]
    S, _ = build_scores(sp)
    base_idx = combine(S)[0]
    res = {"date": _dt.date.today().isoformat(), "adopted": [], "dettaglio": {}}
    from . import fondamentali
    for key, fam, kind, y, r in _new_items():
        try:
            s_raw = semafori.series_of(key, sp).dropna()
            if len(s_raw) < 60:
                res["dettaglio"][key] = {"stato": "dati non ancora disponibili"}
                continue
            lag = {"sloos": 60, "credit_gap": 90}.get(key, 5) if key in NEW_IND else max(1, int(round(fondamentali.LAG.get(key, 1) * 5 / 7)))
            a = s_raw.copy()
            a.index = a.index + pd.Timedelta(days=0)
            a = a.reindex(a.index.union(idx_s)).ffill(limit=_limit(key) + lag).reindex(idx_s).shift(lag if lag > 5 else 1)
            pr = a.rolling(WINDOW, min_periods=250).rank(pct=True)
            sc = (0.6 * _thresh_score(a, kind, y, r) + 0.4 * pr).fillna(_thresh_score(a, kind, y, r))
            S2 = S.copy()
            S2[key] = sc
            GROUPS[fam][1].append((key, kind, y, r))
            try:
                new_idx = combine(S2)[0]
            finally:
                GROUPS[fam][1].pop()
            det, better, worse = {}, 0, 0
            for ek, yy in ev.items():
                lo = START_EVAL if False else "2013-01-01"
                a_old = _auc(base_idx.shift(1)[lo:], yy.reindex(base_idx.shift(1)[lo:].index))
                a_new = _auc(new_idx.shift(1)[lo:], yy.reindex(new_idx.shift(1)[lo:].index))
                det[ek] = {"senza": a_old, "con": a_new}
                if a_new - a_old >= 0.01:
                    better += 1
                if a_new - a_old < -0.01:
                    worse += 1
            ok = better >= 2 and worse == 0
            res["dettaglio"][key] = {"auc": det, "migliorati": better, "peggiorati": worse, "adottato": ok, "dal": str(s_raw.index[0].date()), "famiglia": fam}
            if ok:
                res["adopted"].append(key)
        except Exception as e:  # noqa: BLE001
            res["dettaglio"][key] = {"stato": "errore: " + str(e)[:80]}
    try:
        EXTRA_FILE.write_text(json.dumps(res, ensure_ascii=False, default=lambda x: None if x != x else float(x)), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return res
