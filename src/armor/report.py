"""Cruscotto Armor: un solo file HTML (Armor_dashboard.html), si apre con doppio clic."""
import html
from datetime import datetime

import numpy as np
import pandas as pd

from . import journal, store
from .config import (BACKTEST_RET, CALIBRATION, HORIZONS, HZ_LABEL, OUTCOMES, PRIMARY, REPORT_HTML, RISK_HISTORY,
                     TARGETS, VALIDATION, VERDICT)
from .features import closed_sp500, fwd_maxdd, fwd_ret, price_features, vwce_series

FEAT_IT = {"rv21": "volatilità recente (21 giorni)", "rv63": "volatilità a 3 mesi",
           "rv_ratio": "volatilità recente rispetto al normale", "dd252": "distanza dai massimi dell'ultimo anno",
           "ma200": "prezzo rispetto alla media a 200 giorni", "ma50_200": "media a 50 giorni rispetto a quella a 200",
           "mom63": "andamento degli ultimi 3 mesi", "worst_day": "peggior giornata dell'ultimo mese"}
LEVEL_CLASS = {"Basso": "ok", "Normale": "ok", "Elevato": "warn", "Alto": "bad"}
REL_TXT = {"Utile": "Affidabilità: utile", "Debole": "Affidabilità: debole", "Non affidabile": "Affidabilità: non dimostrata"}
REL_CLASS = {"Utile": "ok", "Debole": "warn", "Non affidabile": "bad"}


def it(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1, sign=False):
    if x is None or pd.isna(x):
        return "—"
    return (f"{x * 100:+.{d}f}" if sign else f"{x * 100:.{d}f}").replace(".", ",") + "%"


def esc(s):
    return html.escape(str(s))


def read_csv(p):
    try:
        return pd.read_csv(p) if p.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def svg_lines(series, w=680, h=190, fmt=lambda v: it(v, 1), hline=None, ymin=None):
    """Grafico a linee in SVG semplice. series = [(nome, Series, colore)]."""
    series = [(n, s.dropna(), c) for n, s, c in series if s is not None and not s.dropna().empty]
    if not series:
        return "<p class='muted'>Dati non disponibili.</p>"
    x0 = min(s.index[0] for _, s, _ in series).value
    x1 = max(s.index[-1] for _, s, _ in series).value
    ys = np.concatenate([s.values for _, s, _ in series])
    lo, hi = float(np.nanmin(ys)), float(np.nanmax(ys))
    if hline is not None:
        lo, hi = min(lo, hline), max(hi, hline)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    if ymin is not None:
        lo = ymin
    L, R, T, B = 52, 8, 8, 22
    sx = lambda d: L + (d.value - x0) / max(x1 - x0, 1) * (w - L - R)
    sy = lambda v: T + (hi - v) / (hi - lo) * (h - T - B)
    out = [f"<svg viewBox='0 0 {w} {h}' class='chart' role='img'>"]
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        out.append(f"<line x1='{L}' x2='{w - R}' y1='{sy(v):.1f}' y2='{sy(v):.1f}' class='grid'/>"
                   f"<text x='{L - 6}' y='{sy(v) + 4:.1f}' class='ax' text-anchor='end'>{esc(fmt(v))}</text>")
    if hline is not None:
        out.append(f"<line x1='{L}' x2='{w - R}' y1='{sy(hline):.1f}' y2='{sy(hline):.1f}' class='hl'/>")
    first = series[0][1]
    for k, d in enumerate((first.index[0], first.index[len(first) // 2], first.index[-1])):
        anc = ("start", "middle", "end")[k]
        out.append(f"<text x='{sx(d):.1f}' y='{h - 6}' class='ax' text-anchor='{anc}'>{d.strftime('%m/%Y')}</text>")
    for n, s, c in series:
        step = max(len(s) // 700, 1)
        pts = " ".join(f"{sx(d):.1f},{sy(v):.1f}" for d, v in s.iloc[::step].items())
        out.append(f"<polyline points='{pts}' fill='none' stroke='{c}' stroke-width='1.8' stroke-linejoin='round'/>")
    out.append("</svg>")
    leg = " ".join(f"<span class='lg'><i style='background:{c}'></i>{esc(n)}</span>" for n, _, c in series)
    return "".join(out) + f"<div class='legend'>{leg}</div>"


def asof_val(s: pd.Series, date: pd.Timestamp):
    s = s.dropna()
    s = s[s.index <= date]
    return float(s.iloc[-1]) if len(s) else None


def build_panel(sp: pd.Series) -> pd.DataFrame:
    ld = lambda k: store.load(k)
    df = pd.DataFrame(index=sp.index)
    df["sp500"] = sp
    for k in ["vix", "vix3m", "vvix", "skew", "move", "hy_oas", "baa10y", "nfci", "t10y3m", "t10y2y", "cape", "rsp", "spy"]:
        s = ld(k)
        if not s.empty:
            if k in ("baa10y", "hy_oas", "t10y3m", "t10y2y", "nfci"):
                s = s.shift(1)             # i dati FRED escono con un giorno di ritardo
            if k == "cape":
                s = s.shift(1, freq="MS")  # Shiller: pubblicato con ritardo, uso a ritroso
            df[k] = s.reindex(df.index.union(s.index)).ffill().reindex(df.index)
    return df


def flags_table(panel, p):
    """Condizioni di attenzione e frequenza storica di cali >=10% a 3 mesi quando erano attive."""
    f = price_features(p)
    dd = fwd_maxdd(p, 63)
    ret = fwd_ret(p, 63)
    P = panel
    g = lambda k: P[k] if k in P else pd.Series(np.nan, index=P.index)
    conds = [
        ("VIX sopra 30", g("vix") > 30),
        ("VIX in forte salita (+30% in 21 giorni)", (g("vix") / g("vix").shift(21) - 1) > 0.30),
        ("Curva VIX invertita (VIX a 3 mesi sotto VIX)", (g("vix3m") / g("vix")) < 1),
        ("S&P 500 sotto la media a 200 giorni", f["ma200"] < 0),
        ("S&P 500 oltre il 10% sotto i massimi dell'anno", f["dd252"] < -0.10),
        ("Spread BAA-10Y in salita di oltre 0,3 punti in 21 giorni", (g("baa10y") - g("baa10y").shift(21)) > 0.3),
        ("Spread High Yield sopra 5 punti", g("hy_oas") > 5),
        ("Condizioni finanziarie strette (NFCI sopra 0)", g("nfci") > 0),
        ("SKEW sopra 150 (opzioni: paura di crolli)", g("skew") > 150),
        ("Curva dei tassi 10Y-3M invertita", g("t10y3m") < 0),
        ("CAPE (valutazioni) sopra 30", g("cape") > 30),
    ]
    rows = []
    base = float((dd[ret.notna()] <= -0.10).mean())
    for name, c in conds:
        c = c.reindex(p.index).fillna(False)
        valid = c.notna() & ret.notna()
        m = c & valid
        today = bool(c.iloc[-1]) if len(c) else False
        has_data = c.any()
        n = int(m.sum())
        rows.append({"name": name, "today": today, "n": n,
                     "freq": float((dd[m] <= -0.10).mean()) if n >= 150 else None,
                     "ret": float(ret[m].mean()) if n >= 150 else None, "base": base,
                     "nodata": not has_data})
    return rows


INDICATORS = [
    ("Prezzi", [("S&P 500", "sp500", 0, 0), ("VWCE (€)", "vwce", 0, 2), ("Distanza dai massimi 1 anno (S&P)", "dd252", -1, "pct")]),
    ("Volatilità e opzioni", [("VIX", "vix", 1, 1), ("VIX a 3 mesi / VIX (sotto 1 = inversione)", "vterm", -1, 2),
                             ("VVIX", "vvix", 1, 1), ("SKEW", "skew", 1, 1), ("MOVE (volatilità obbligazioni)", "move", 1, 1)]),
    ("Credito e liquidità", [("Spread High Yield (punti)", "hy_oas", 1, 2), ("Spread BAA-10Y (punti)", "baa10y", 1, 2),
                             ("Condizioni finanziarie NFCI (sopra 0 = strette)", "nfci", 1, 2)]),
    ("Tassi e dollaro", [("Curva 10Y-3M (punti)", "t10y3m", -1, 2), ("Curva 10Y-2Y (punti)", "t10y2y", -1, 2),
                         ("Tasso reale 10 anni (%)", "real10y", 0, 2), ("Dollaro (indice ampio)", "usd_broad", 0, 1)]),
    ("Valutazioni", [("CAPE (Shiller)", "cape", 1, 1), ("P/E (utili ultimi 12 mesi)", "pe_trailing", 1, 1),
                     ("Capitalizzazione azioni / PIL", "eq_gdp", 1, 2)]),
    ("Materie prime, incertezza, ampiezza", [("Oro ($)", "gold", 0, 0), ("Petrolio WTI ($)", "wti", 0, 1),
                                             ("Incertezza politica (EPU)", "epu", 1, 0), ("Ampiezza: RSP/SPY (alto = mercato più largo)", "rsp_spy", -1, 3)]),
]


def indicator_series(key, sp, p):
    if key == "sp500":
        return sp
    if key == "vwce":
        return vwce_series()
    if key == "dd252":
        return price_features(p)["dd252"] * 100
    if key == "vterm":
        a, b = store.load("vix3m"), store.load("vix")
        return (a / b.reindex(a.index)).dropna() if not a.empty else a
    if key == "eq_gdp":
        a, b = store.load("equity_value"), store.load("gdp")
        return (a / (b.reindex(a.index.union(b.index)).ffill().reindex(a.index) * 1000)).dropna() if not a.empty and not b.empty else a
    if key == "rsp_spy":
        a, b = store.load("rsp"), store.load("spy")
        return (a / b.reindex(a.index)).dropna() if not a.empty else a
    return store.load(key)


def comparison_html(date, sp, p):
    heads = ["Adesso", "7 giorni fa", "1 mese fa", "3 mesi fa", "6 mesi fa", "1 anno fa"]
    offs = [None, 7, 30, 91, 182, 365]
    out = ["<table><thead><tr><th>Indicatore</th>" + "".join(f"<th>{h}</th>" for h in heads) + "</tr></thead><tbody>"]
    for group, items in INDICATORS:
        out.append(f"<tr class='grp'><td colspan='7'>{esc(group)}</td></tr>")
        for label, key, bad, dec in items:
            s = indicator_series(key, sp, p)
            vals = []
            for o in offs:
                d = date if o is None else date - pd.Timedelta(days=o)
                vals.append(asof_val(s, d) if s is not None and len(s) else None)
            cells = []
            for k, v in enumerate(vals):
                if v is None:
                    cells.append("<td class='muted'>—</td>")
                    continue
                txt = f"{v:+.1f}%".replace(".", ",") if dec == "pct" else it(v, dec)
                if dec == "pct":
                    txt = f"{it(v, 1)}%"
                extra = ""
                if k > 0 and vals[0] is not None and bad != 0 and v != 0:
                    ch = vals[0] - v
                    worse = (ch > 0) == (bad > 0) and abs(ch / v) > 0.05 if v else False
                    better = (ch > 0) != (bad > 0) and abs(ch / v) > 0.05 if v else False
                    extra = " class='worse'" if worse else (" class='better'" if better else "")
                cells.append(f"<td{extra}>{txt}</td>")
            if all(v is None for v in vals):
                cells = ["<td colspan='6' class='muted'>in attesa del primo scaricamento di questa serie</td>"]
            out.append(f"<tr><td>{esc(label)}</td>{''.join(cells)}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def horizon_card(hz, r, spot, rel):
    lev = r["level"]
    prim = PRIMARY[hz]
    thrs = sorted(r["p"])
    lines = "".join(
        f"<div class='prow'><span>Calo di almeno {t}% entro {HZ_LABEL[hz]}</span><b>{pct(r['p'][t])}</b>"
        f"<span class='muted'>normale: {pct(r['base'][t])}</span></div>" for t in thrs)
    ret = r.get("ret")
    rtxt = ""
    if ret:
        tgt = f" → circa {it(spot * (1 + ret['q50']), 2)} € (da {it(spot * (1 + ret['q10']), 2)} a {it(spot * (1 + ret['q90']), 2)})" if spot == spot else ""
        rtxt = (f"<div class='hyp'><span class='lab'>Ipotesi di rendimento (mediana)</span><b>{pct(ret['q50'], 1, True)}</b>"
                f"<span class='muted'>intervallo 80%: {pct(ret['q10'], 1, True)} … {pct(ret['q90'], 1, True)}{tgt}</span></div>")
    drv = ""
    if r.get("drivers"):
        d = r["drivers"][:2]
        drv = "<div class='drv'>Pesa di più: " + "; ".join(
            f"{FEAT_IT[f]} ({'↑ rischio' if c > 0 else '↓ rischio'})" for f, c in d) + "</div>"
    relhtml = ""
    if rel:
        relhtml = f"<span class='badge {REL_CLASS[rel[0]]}' title='{esc(rel[1])}'>{REL_TXT[rel[0]]}</span>"
    return (f"<div class='card hz'><div class='hzh'><h3>{HZ_LABEL[hz]}</h3><span class='badge {LEVEL_CLASS[lev]}'>Rischio {lev.lower()}</span></div>"
            f"<div class='ratio'>{it(r['ratio'], 1)}× la frequenza storica</div>{lines}{rtxt}{drv}<div class='relrow'>{relhtml}</div></div>")


def build(ctx: dict) -> None:
    date: pd.Timestamp = ctx["date"]
    pred, spot = ctx["pred"], ctx["spot"]
    p = closed_sp500()
    sp = p
    vw = vwce_series()
    val = read_csv(VALIDATION)
    cal = read_csv(CALIBRATION)
    hist = read_csv(RISK_HISTORY)
    bt = read_csv(BACKTEST_RET)
    outc = read_csv(OUTCOMES)
    jr = journal.read()
    status = store.read_status()
    panel = build_panel(sp)

    rel = {}
    for hz in HORIZONS:
        row = val[(val.get("model") == "armor") & (val.get("target") == f"{hz}_{PRIMARY[hz]}")] if len(val) else pd.DataFrame()
        if len(row):
            r0 = row.iloc[0]
            rel[hz] = (r0["reliability"], f"AUC 2013-26: {r0['auc_2013_26']}; indice di Brier (BSS): {r0['bss_all']}")

    # verdetto generale: il peggiore tra 1 mese e 3 mesi
    order = ["Basso", "Normale", "Elevato", "Alto"]
    worst = max((pred[h]["level"] for h in ("1m", "3m") if h in pred), key=order.index)
    verdict = VERDICT[worst]
    r3 = pred.get("3m", {})
    why = (f"Il rischio di un calo di almeno 10% in 3 mesi è stimato al {pct(r3['p'][10])}, "
           f"cioè {it(r3['ratio'], 1)} volte la frequenza storica ({pct(r3['base'][10])}).") if r3 else ""
    weak = [HZ_LABEL[h] for h in HORIZONS if rel.get(h, ("",))[0] != "Utile"]
    note_rel = ("Attenzione: il modello ha funzionato davvero nei test solo a 10 giorni e 1 mese; "
                f"per {' e '.join(weak)} l'affidabilità è debole o non dimostrata (vedi sezione Affidabilità).") if weak else ""

    # cards
    cards = "".join(horizon_card(h, pred[h], spot, rel.get(h)) for h in HORIZONS if h in pred)

    # grafici
    cut = date - pd.Timedelta(days=730)
    ch_price = svg_lines([("VWCE (€)", vw[vw.index >= cut], "#2a6fdb")], fmt=lambda v: it(v, 0))
    ch_vix = svg_lines([("VIX", store.load("vix").loc[lambda s: s.index >= cut], "#d9822b")], fmt=lambda v: it(v, 0))
    ch_risk = ""
    if len(hist):
        hh = hist.copy()
        hh["date"] = pd.to_datetime(hh["date"])
        hh = hh.set_index("date")
        hh = hh[hh.index >= date - pd.Timedelta(days=365 * 6)]
        add = pd.DataFrame({"p_1m": [pred["1m"]["p"][10]], "p_3m": [pred["3m"]["p"][10]]}, index=[date])
        hh = pd.concat([hh[["p_1m", "p_3m"]], add]) * 100
        ch_risk = svg_lines([("Calo ≥10% entro 1 mese (%)", hh["p_1m"], "#c0392b"), ("Calo ≥10% entro 3 mesi (%)", hh["p_3m"], "#7a4fd1")],
                            fmt=lambda v: it(v, 0) + "%", ymin=0)

    # previsto vs reale
    pv = ""
    if len(outc):
        o = outc.copy()
        o["asof"] = pd.to_datetime(o["asof"])
        rows = []
        for _, r in o.sort_values("asof", ascending=False).head(20).iterrows():
            disc = r["discrepancy"]
            rows.append(f"<tr><td>{r['asof'].strftime('%d/%m/%Y')}</td><td>{HZ_LABEL[r['horizon']]}</td><td>{pct(r['q50'], 1, True)}</td>"
                        f"<td>{pct(r['realized'], 1, True)}</td><td class='{'worse' if pd.notna(disc) and disc < -0.02 else ''}'>{pct(disc, 1, True) if disc != '' else '—'}</td>"
                        f"<td>{'sì' if r['in_range'] == 1 else 'no'}</td><td>{pct(r['realized_maxdd'], 1)}</td></tr>")
        pv += ("<h3>Le tue previsioni dal diario (VWCE)</h3><table><thead><tr><th>Data previsione</th><th>Orizzonte</th><th>Previsto</th><th>Reale</th>"
               "<th>Scostamento</th><th>Dentro l'intervallo 80%</th><th>Calo massimo reale</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")
        s = o.copy()
        s["disc"] = pd.to_numeric(s["discrepancy"], errors="coerce")
        pv += ("<p class='muted'>Scostamento medio per orizzonte: " + "; ".join(
            f"{HZ_LABEL[h]} {pct(g.disc.mean(), 1, True)} (n={len(g)})" for h, g in s.groupby('horizon') if g.disc.notna().any()) + "</p>")
    else:
        first = pd.Timestamp(jr["asof"].iloc[0]).strftime("%d/%m/%Y") if len(jr) else "oggi"
        pv += (f"<p class='muted'>Il diario è partito il {first}: i primi esiti reali arriveranno dopo 10 giorni di borsa "
               "(1 mese, 3 mesi e 6 mesi a seguire). Intanto vedi come sarebbe andata nel passato (backtest onesto).</p>")
    if len(bt):
        b = bt.copy()
        b["horizon"] = pd.Categorical(b["horizon"], list(HORIZONS), ordered=True)
        agg = b.groupby("horizon", observed=True).agg(n=("realized", "size"), disc=("discrepancy", "mean"),
                                                       med=("discrepancy", "median"), inr=("in_range", "mean"),
                                                       mae=("discrepancy", lambda x: x.abs().mean()))
        rows = "".join(f"<tr><td>{HZ_LABEL[h]}</td><td>{int(r.n)}</td><td>{pct(r.disc, 1, True)}</td><td>{pct(r.med, 1, True)}</td>"
                       f"<td>{pct(r.mae, 1)}</td><td>{pct(r.inr, 0)}</td></tr>" for h, r in agg.iterrows())
        pv += ("<h3>Backtest dell'ipotesi di rendimento (S&P 500, dal 2000, walk-forward)</h3>"
               "<table><thead><tr><th>Orizzonte</th><th>Previsioni</th><th>Scostamento medio</th><th>Scostamento mediano</th>"
               "<th>Errore medio assoluto</th><th>Reale dentro intervallo 80%</th></tr></thead><tbody>" + rows + "</tbody></table>"
               "<p class='muted'>Scostamento = reale − previsto. Se l'ipotesi fosse perfetta il reale starebbe dentro l'intervallo nell'80% dei casi. "
               "L'errore medio è grande: l'ipotesi di rendimento indica una tendenza, non un valore.</p>")

    # affidabilità
    avh = ""
    if len(val):
        v = val[val.model == "armor"].copy()
        s_ = val[val.model == "semplice"].set_index("target")
        rows = []
        for _, r in v.iterrows():
            cmp_ = s_.loc[r["target"]] if r["target"] in s_.index else None
            beats = "" if cmp_ is None else ("sì" if r["auc_2013_26"] > cmp_["auc_2013_26"] else "no")
            rows.append(f"<tr><td>Calo ≥{int(r['thr'])}% entro {HZ_LABEL[r['hz']]}</td><td>{pct(r['base_rate'], 1)}</td><td>{r['auc_all']}</td>"
                        f"<td>{r['auc_2013_26']}</td><td>{r['bss_all']}</td><td>{r['bss_2013_26']}</td><td>{beats}</td>"
                        f"<td><span class='badge {REL_CLASS[r['reliability']]}'>{r['reliability']}</span></td></tr>")
        avh = ("<table><thead><tr><th>Che cosa stima</th><th>Frequenza storica</th><th>AUC 2000-26</th><th>AUC 2013-26</th><th>BSS 2000-26</th>"
               "<th>BSS 2013-26</th><th>Meglio del modello semplice (2013-26)</th><th>Giudizio</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
               "<p class='muted'>AUC: 0,5 = come tirare una moneta, 1 = perfetto. BSS: sopra 0 = meglio che dire sempre la frequenza storica. "
               "Test walk-forward dal 2000: a ogni data il modello usa solo ciò che era noto allora. A 3 e 6 mesi dopo il 2013 il modello non ha funzionato.</p>")
        if len(cal):
            cr = cal[cal.target.isin(["1m_10", "3m_10", "6m_10"])]
            rows = "".join(f"<tr><td>{HZ_LABEL[t.split('_')[0]]} · gruppo {k + 1} di {len(g)}{' (meno rischioso)' if k == 0 else (' (più rischioso)' if k == len(g) - 1 else '')}</td><td>{pct(r.prev, 1)}</td><td>{pct(r.real, 1)}</td><td>{int(r.n)}</td></tr>" for t, g in cr.groupby('target') for k, (_, r) in enumerate(g.iterrows()))
            avh += ("<h3>Taratura: probabilità stimata contro frequenza reale (calo ≥10%)</h3><table><thead><tr><th>Orizzonte</th><th>Stimato</th><th>Reale</th><th>Casi</th></tr></thead><tbody>"
                    + rows + "</tbody></table><p class='muted'>Ogni riga è un quinto dei giorni, dal meno al più rischioso. Più stimato e reale sono vicini, meglio il modello è tarato.</p>")

    # segnali
    fl = flags_table(panel, p)
    rows = []
    for f in sorted(fl, key=lambda x: (not x["today"], x["name"])):
        if f["nodata"]:
            st = "<td class='muted'>serie non ancora scaricata</td>"
        else:
            st = f"<td>{'ATTIVO' if f['today'] else 'no'}</td>"
        hist_txt = (f"{pct(f['freq'], 0)} (contro {pct(f['base'], 0)} sempre); rendimento medio a 3 mesi {pct(f['ret'], 1, True)}; {f['n']} giorni"
                    if f["freq"] is not None else "storico insufficiente")
        rows.append(f"<tr class='{'act' if f['today'] and not f['nodata'] else ''}'><td>{esc(f['name'])}</td>{st}<td>{hist_txt}</td></tr>")
    flags_html = ("<table><thead><tr><th>Condizione</th><th>Oggi</th><th>Storicamente, quando era attiva: calo ≥10% entro 3 mesi</th></tr></thead><tbody>"
                  + "".join(rows) + "</tbody></table><p class='muted'>Statistiche descrittive su tutta la storia disponibile (non sono una prova). "
                  "Un VIX alto spesso precede rimbalzi: aumenta il rischio di cali nel periodo, non dice che il mercato scenderà.</p>")

    # data center
    bad = {k: v for k, v in status.items() if not v.get("ok")}
    rows = []
    for k, v in sorted(status.items(), key=lambda kv: (kv[1].get("ok", False), kv[0])):
        age = ""
        if v.get("last_date"):
            age = (pd.Timestamp(date) - pd.Timestamp(v["last_date"])).days
        rows.append(f"<tr class='{'' if v.get('ok') else 'act'}'><td>{esc(k)}</td><td>{'ok' if v.get('ok') else 'ERRORE'}</td><td>{v.get('last_date') or '—'}</td>"
                    f"<td>{age}</td><td>{v.get('rows', 0)}</td><td class='muted'>{esc(v.get('msg', ''))}</td></tr>")
    ok_j, msg_j = journal.verify()
    dc = (f"<p>Diario previsioni: <b>{'integro' if ok_j else 'PROBLEMA'}</b> ({esc(msg_j)}). Serie con errore: <b>{len(bad)}</b> su {len(status)}.</p>"
          "<table><thead><tr><th>Serie</th><th>Stato</th><th>Ultimo dato</th><th>Giorni di ritardo</th><th>Righe</th><th>Messaggio</th></tr></thead><tbody>"
          + "".join(rows) + "</tbody></table>") if status else "<p class='muted'>Nessun aggiornamento ancora eseguito su questo computer.</p>"

    stale = (datetime.utcnow().date() - date.date()).days
    stale_txt = f"<div class='banner'>Ultimo dato disponibile: {date.strftime('%d/%m/%Y')} ({stale} giorni fa). Esegui l'aggiornamento.</div>" if stale > 4 else ""

    body = f"""
<header><div><h1>Armor</h1><div class='muted'>Rischio di cali su VWCE · aggiornato ai dati del {date.strftime('%d/%m/%Y')} · generato {datetime.now().strftime('%d/%m/%Y %H:%M')}</div></div></header>
{stale_txt}
<section class='hero {LEVEL_CLASS[worst]}'>
  <div class='hl1'>{verdict}</div>
  <div class='hl2'>{esc(why)}</div>
  <div class='hl3'>{esc(note_rel)}</div>
  <div class='hl4'>VWCE: {it(spot, 2)} € · Armor stima il rischio di cali, non la direzione: nei test la direzione non è prevedibile.</div>
</section>
<h2>Previsioni per orizzonte</h2><div class='grid4'>{cards}</div>
<h2>Andamento del rischio</h2><div class='card'>{ch_risk}<p class='muted'>Probabilità stimata di un calo ≥10% (S&P 500, stima walk-forward fino a oggi). Dopo le crisi (2008, 2020, 2022) la linea sale.</p></div>
<div class='grid2'><div class='card'><h3>VWCE ultimi 2 anni</h3>{ch_price}</div><div class='card'><h3>VIX ultimi 2 anni</h3>{ch_vix}</div></div>
<h2>Segnali di attenzione</h2><div class='card'>{flags_html}</div>
<h2>Confronto con il passato</h2><div class='card scroll'>{comparison_html(date, sp, p)}<p class='muted'>Rosso: l'indicatore è cambiato in senso più rischioso rispetto ad allora (oltre il 5%); verde: meno rischioso.</p></div>
<h2>Previsto contro reale</h2><div class='card'>{pv}</div>
<h2>Affidabilità del modello</h2><div class='card scroll'>{avh}</div>
<h2>Dati e archivio</h2><div class='card scroll'>{dc}</div>
<footer>Armor non è consulenza finanziaria. Le stime sono probabilità basate sul passato e possono essere sbagliate. Nessun modello prevede con certezza.</footer>
"""
    REPORT_HTML.write_text(TEMPLATE.replace("{{BODY}}", body), encoding="utf-8")
    print("Cruscotto creato:", REPORT_HTML)


TEMPLATE = """<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Armor - rischio cali VWCE</title><style>
:root{--bg:#f4f6f9;--card:#fff;--tx:#1b2330;--mu:#667085;--bd:#e3e8ef;--ok:#1f8f55;--warn:#c77d0a;--bad:#c0392b;--ac:#2a6fdb;--okbg:#e7f5ee;--warnbg:#fdf3e1;--badbg:#fbe9e7}
@media(prefers-color-scheme:dark){:root{--bg:#0e131b;--card:#161d28;--tx:#e8edf5;--mu:#93a0b4;--bd:#263040;--ok:#4cc38a;--warn:#f0b54a;--bad:#ff7a6b;--ac:#6ea4ff;--okbg:#12301f;--warnbg:#3a2c10;--badbg:#3d1a16}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;padding:16px;max-width:1200px;margin:auto}
header{display:flex;justify-content:space-between;margin-bottom:12px}h1{margin:0;font-size:28px;letter-spacing:.5px}h2{font-size:18px;margin:26px 0 10px}h3{margin:0 0 8px;font-size:16px}
.muted{color:var(--mu);font-size:13px}.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px;overflow-x:auto}
.hero{border-radius:16px;padding:22px;border:1px solid var(--bd)}.hero.ok{background:var(--okbg)}.hero.warn{background:var(--warnbg)}.hero.bad{background:var(--badbg)}
.hl1{font-size:34px;font-weight:700}.hero.ok .hl1{color:var(--ok)}.hero.warn .hl1{color:var(--warn)}.hero.bad .hl1{color:var(--bad)}.hl2{margin-top:4px;font-size:16px}.hl3,.hl4{margin-top:6px;color:var(--mu);font-size:13px}
.grid4{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-top:12px}
.hzh{display:flex;justify-content:space-between;align-items:center}.ratio{font-size:13px;color:var(--mu);margin-bottom:8px}
.prow{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:6px 0;border-top:1px solid var(--bd)}.prow b{font-size:20px}.prow .muted{grid-column:1/3;margin-top:-4px}
.hyp{margin-top:8px;padding:8px;border-radius:10px;background:var(--bg);display:grid;gap:2px}.hyp .lab{font-size:12px;color:var(--mu)}.hyp b{font-size:20px}.drv{margin-top:8px;font-size:13px;color:var(--mu)}.relrow{margin-top:10px}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600}.badge.ok{background:var(--okbg);color:var(--ok)}.badge.warn{background:var(--warnbg);color:var(--warn)}.badge.bad{background:var(--badbg);color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:7px 8px;border-bottom:1px solid var(--bd);text-align:right}th:first-child,td:first-child{text-align:left}thead th{font-size:12px;color:var(--mu);font-weight:600}
tr.grp td{background:var(--bg);font-weight:700;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mu)}td.worse{color:var(--bad);font-weight:600}td.better{color:var(--ok);font-weight:600}tr.act td{background:var(--warnbg)}
.scroll{overflow-x:auto}.chart{width:100%;height:auto}.grid{stroke:var(--bd);stroke-width:1}.hl{stroke:var(--mu);stroke-dasharray:4 4}.ax{fill:var(--mu);font-size:11px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mu)}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.banner{background:var(--badbg);color:var(--bad);padding:10px 14px;border-radius:10px;margin-bottom:12px;font-weight:600}footer{margin:26px 0 8px;color:var(--mu);font-size:12px}
@media(max-width:600px){body{padding:10px}.hl1{font-size:28px}}
</style></head><body>{{BODY}}</body></html>"""
