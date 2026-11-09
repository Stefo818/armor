"""Cruscotto Armor: un solo file HTML (Armor_dashboard.html), si apre con doppio clic."""
import html
from datetime import date as _date, datetime, timedelta

import numpy as np
import pandas as pd

import json

from . import marchio
from . import analysis, journal, live as livemod, outlook, parts, registry, semafori, sitedata, store, valuations
from . import archivio_dati, economia, inclinazione, infobox, mondo, novita, opportunita, saldi, tensione, livefeed, diagnostica, vrp, pacsim, affidabilita, percorsi, serie_eur, verifica, armor_index, aziende, campioni, chiaro, ciclico, forza, confronto, cruscotto, extra13, learning, mappa, rapporto, salute, spiega, ui
from .config import (BACKTEST_RET, CALIBRATION, DATA, HORIZONS, HZ_LABEL, OUTCOMES, PRIMARY, REPORT_HTML, RISK_HISTORY,
                     TARGETS, VALIDATION, VERDICT)
from .features import closed_sp500, fwd_maxdd, fwd_maxup, fwd_ret, price_features, vwce_display, vwce_series

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


def svg_lines(series, w=680, h=190, fmt=lambda v: it(v, 1), hline=None, ymin=None, dots=None):
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
    for n, ds, c in (dots or []):
        for d, v in ds.dropna().items():
            if x0 <= d.value <= x1:
                out.append(f"<circle cx='{sx(d):.1f}' cy='{sy(v):.1f}' r='3.2' fill='{c}' stroke='var(--card)' stroke-width='1'/>")
    out.append("</svg>")
    leg = " ".join(f"<span class='lg'><i style='background:{c}'></i>{esc(n)}</span>" for n, _, c in series)
    leg += "".join(f"<span class='lg'><i style='background:{c};border-radius:50%'></i>{esc(n)}</span>" for n, _, c in (dots or []))
    return "".join(out) + f"<div class='legend'>{leg}</div>"


MAX_AGE = {"aaii_spread": 14, "aaii_bull": 14, "aaii_bear": 14, "gpr": 10, "gpr_threat": 10, "gpr_act": 10, "fear_greed": 6, "breadth50": 8, "breadth200": 8, "nh_nl": 8,
           "top_ps": 10, "top_pe": 10, "top_fcf_yield": 10, "ai_capex_ocf": 130,
           "spy_pc_volume": 10, "spy_pc_open_interest": 10, "spy_iv_atm_30d": 10, "spy_put_skew_95": 10, "eq_gdp": 160, "cape_m": 50, "pe_m": 50, "ps_m": 110, "cpi": 60, "unrate": 60}


def asof_val(s: pd.Series, date: pd.Timestamp, max_age: int = 12):
    """Ultimo valore noto alla data; None se piu' vecchio di max_age giorni (dato non aggiornato)."""
    s = s.dropna()
    s = s[s.index <= date]
    if not len(s) or (date - s.index[-1]).days > max_age:
        return None
    return float(s.iloc[-1])


def build_panel(sp: pd.Series) -> pd.DataFrame:
    ld = lambda k: store.load(k)
    df = pd.DataFrame(index=sp.index)
    df["sp500"] = sp
    limit = {"cape_m": 45, "ps_m": 100, "pe_m": 45}
    for k in ["vix", "vix3m", "vvix", "skew", "move", "hy_oas", "baa10y", "nfci", "t10y3m", "t10y2y", "cape_m", "ps_m", "rsp", "spy"]:
        s = ld(k)
        if not s.empty:
            if k in ("baa10y", "hy_oas", "t10y3m", "t10y2y", "nfci"):
                s = s.shift(1)             # i dati FRED escono con un giorno di ritardo
            full = s.reindex(pd.date_range(s.index[0], max(df.index[-1], s.index[-1]))).ffill(limit=limit.get(k, 7))
            df[k] = full.reindex(df.index)
    return df


def flags_table(panel, p):
    """Condizioni di attenzione e frequenza storica di cali >=10% a 3 mesi quando erano attive."""
    f = price_features(p)
    dd = fwd_maxdd(p, 63)
    ret = fwd_ret(p, 63)
    P = panel
    g = lambda k: P[k] if k in P else pd.Series(np.nan, index=P.index)
    conds = [
        ("VIX sopra 30", g("vix") > 30, ["vix"]),
        ("VIX in forte salita (+30% in 21 giorni)", (g("vix") / g("vix").shift(21) - 1) > 0.30, ["vix"]),
        ("Curva VIX invertita (VIX a 3 mesi sotto VIX)", (g("vix3m") / g("vix")) < 1, ["vix", "vix3m"]),
        ("S&P 500 sotto la media a 200 giorni", f["ma200"] < 0, []),
        ("S&P 500 oltre il 10% sotto i massimi dell'anno", f["dd252"] < -0.10, []),
        ("Spread BAA-10Y in salita di oltre 0,3 punti in 21 giorni", (g("baa10y") - g("baa10y").shift(21)) > 0.3, ["baa10y"]),
        ("Spread High Yield sopra 5 punti (storico FRED solo 3 anni)", g("hy_oas") > 5, ["hy_oas"]),
        ("Condizioni finanziarie strette (NFCI sopra 0)", g("nfci") > 0, ["nfci"]),
        ("SKEW sopra 150 (opzioni: paura di crolli)", g("skew") > 150, ["skew"]),
        ("Curva dei tassi 10Y-3M invertita", g("t10y3m") < 0, ["t10y3m"]),
        ("CAPE (valutazioni) sopra 30", g("cape_m") > 30, ["cape_m"]),
        ("Prezzo/fatturato S&P 500 sopra 3 (pochi periodi: statistica debole)", g("ps_m") > 3, ["ps_m"]),
    ]
    rows = []
    base = float((dd[ret.notna()] <= -0.10).mean())
    upm = fwd_maxup(p, 63)
    base_up = float((upm[ret.notna()] >= 0.10).mean())
    for name, c, keys in conds:
        c = c.reindex(p.index).fillna(False)
        m = c & ret.notna()
        nodata = any((k not in P) or pd.isna(P[k].iloc[-1]) for k in keys)
        n = int(m.sum())
        rows.append({"name": name, "today": bool(c.iloc[-1]) and not nodata, "n": n,
                     "freq": float((dd[m] <= -0.10).mean()) if n >= 150 else None,
                     "ret": float(ret[m].mean()) if n >= 150 else None, "base": base, "nodata": nodata,
                     "up": float((upm[m] >= 0.10).mean()) if n >= 150 else None, "base_up": base_up})
    return rows


INDICATORS = [
    ("Prezzi", [("S&P 500 (indice, ultimo prezzo)", "sp500", 0, 0), ("VWCE (€, ultimo prezzo)", "vwce", 0, 2), ("Distanza dai massimi 1 anno (S&P)", "dd252", -1, "pct")]),
    ("Volatilità e opzioni", [("VIX", "vix", 1, 1), ("VIX a 3 mesi / VIX (sotto 1 = inversione)", "vterm", -1, 2),
                             ("VVIX", "vvix", 1, 1), ("SKEW", "skew", 1, 1), ("MOVE (volatilità obbligazioni)", "move", 1, 1)]),
    ("Credito e liquidità", [("Spread High Yield (punti)", "hy_oas", 1, 2), ("Spread BAA-10Y (punti)", "baa10y", 1, 2),
                             ("Condizioni finanziarie NFCI (sopra 0 = strette)", "nfci", 1, 2)]),
    ("Tassi e dollaro", [("Curva 10Y-3M (punti)", "t10y3m", -1, 2), ("Curva 10Y-2Y (punti)", "t10y2y", -1, 2),
                         ("Tasso reale 10 anni (%)", "real10y", 0, 2), ("Dollaro (indice ampio)", "usd_broad", 0, 1)]),
    ("Valutazioni", [("CAPE (P/E di Shiller, utili medi 10 anni)", "cape_m", 1, 1), ("P/E (utili ultimi 12 mesi)", "pe_m", 1, 1),
                     ("Prezzo/fatturato S&P 500 (cap./vendite)", "ps_m", 1, 2),
                     ("Azioni società USA non finanziarie / PIL (trimestrale)", "eq_gdp", 1, 2)]),
    ("Materie prime, incertezza, ampiezza", [("Oro ($)", "gold", 0, 0), ("Petrolio WTI ($)", "wti", 0, 1),
                                             ("Incertezza politica (EPU)", "epu", 1, 0), ("Ampiezza: RSP/SPY (alto = mercato più largo)", "rsp_spy", -1, 3)]),
    ("Sentiment e ampiezza (dati accumulati da quando l'app li scarica)", [
        ("Sondaggio AAII: rialzisti meno ribassisti (punti %)", "aaii_spread", 0, 1),
        ("Fear & Greed CNN (0 paura, 100 euforia)", "fear_greed", 0, 0),
        ("Titoli S&P 500 sopra la media a 200 giorni (%)", "breadth200", -1, 0),
        ("Titoli S&P 500 sopra la media a 50 giorni (%)", "breadth50", -1, 0),
        ("Nuovi massimi meno nuovi minimi a 52 settimane (% titoli)", "nh_nl", -1, 1)]),
    ("Geopolitica", [("Rischio geopolitico GPR (indice)", "gpr", 1, 0), ("GPR: minacce", "gpr_threat", 1, 0), ("GPR: atti di guerra/terrore", "gpr_act", 1, 0)]),
    ("Grandi aziende (30 maggiori società USA, media pesata per capitalizzazione)", [
        ("Prezzo/fatturato", "top_ps", 1, 2), ("P/E sugli utili previsti", "top_pe", 1, 1),
        ("Rendimento da flusso di cassa libero (%)", "top_fcf_yield", -1, 2),
        ("Investimenti AI: spesa in conto capitale / flusso di cassa operativo (big tech)", "ai_capex_ocf", 1, 2)]),
    ("Opzioni su SPY (archivio proprio, nessuno storico prima di novembre 2026)", [
        ("Put/Call sui volumi", "spy_pc_volume", 1, 2), ("Put/Call sull'open interest", "spy_pc_open_interest", 1, 2),
        ("Volatilità implicita ATM a 30 giorni", "spy_iv_atm_30d", 1, 3), ("Skew put 95% (premio sulle put)", "spy_put_skew_95", 1, 3)]),
]

INDICATOR_HELP = {
    "sp500": "Livello dell'indice. Serve come riferimento: i cali si misurano da qui.",
    "vwce": "Prezzo del tuo ETF in euro.",
    "dd252": "Di quanto il prezzo è sotto il massimo dell'ultimo anno. 0% = sui massimi; −10% o meno = correzione in corso.",
    "vix": "Paura del mercato (volatilità attesa a 30 giorni). Sotto 20 tranquillo, sopra 30 panico.",
    "vterm": "VIX a 3 mesi diviso VIX a 30 giorni. Sotto 1 il mercato teme di più il breve periodo: segnale di stress.",
    "vvix": "Quanto è instabile lo stesso VIX. Alto = il mercato non sa più quanta paura avere.",
    "skew": "Quanto costano le assicurazioni contro i crolli (opzioni put). Alto = gli esperti si proteggono.",
    "move": "Il «VIX» delle obbligazioni. Alto = tensione sui titoli di Stato.",
    "hy_oas": "Quanto interesse in più pagano le aziende USA più rischiose rispetto allo Stato. Sale quando cresce la paura di fallimenti.",
    "baa10y": "Come sopra, per aziende di buona qualità. Sale nei periodi di stress.",
    "nfci": "Indice della Fed di Chicago: sopra 0 il credito è più difficile del normale, sotto 0 è facile.",
    "t10y3m": "Tassi a 10 anni meno tassi a 3 mesi. Sotto 0 (curva invertita) in passato ha preceduto molte recessioni, con anticipo anche di un anno.",
    "t10y2y": "Tassi a 10 anni meno tassi a 2 anni. Stessa idea: sotto 0 è un segnale di cautela.",
    "real10y": "Tasso a 10 anni al netto dell'inflazione. Alto = soldi costosi, le azioni faticano di più.",
    "usd_broad": "Forza del dollaro contro le altre valute. Un dollaro forte stringe le condizioni finanziarie globali.",
    "cape_m": "Prezzo diviso gli utili medi degli ultimi 10 anni. Sopra 30 il mercato è caro: non dice quando scenderà, ma i rendimenti dei prossimi anni tendono a essere più bassi.",
    "pe_m": "Prezzo diviso gli utili dell'ultimo anno. Più alto = il mercato è più caro.",
    "ps_m": "Valore delle società diviso i loro ricavi. Sopra 3 è caro rispetto alla storia.",
    "eq_gdp": "Valore delle azioni USA diviso il PIL. Più alto = Borsa «gonfiata» rispetto all'economia.",
    "gold": "Prezzo dell'oro in dollari. Sale quando gli investitori cercano rifugio.",
    "wti": "Petrolio americano in dollari al barile. Sale = costi più alti per l'economia.",
    "epu": "Indice di incertezza sulle politiche economiche (basato sulle notizie). Alto = più incertezza.",
    "rsp_spy": "Confronta le 500 società tutte con lo stesso peso (RSP) con quelle pesate per dimensione (SPY). In calo = il mercato regge solo grazie a poche grandi aziende.",
    "aaii_spread": "Sondaggio settimanale tra piccoli investitori: % rialzisti meno % ribassisti. Estremi di entusiasmo o paura spesso arrivano vicino a svolte, ma non è un segnale affidabile da solo.",
    "fear_greed": "Indice CNN che riassume 7 misure di sentimento: 0 = paura estrema, 100 = euforia.",
    "breadth200": "Quante delle 500 società sono sopra la propria media a 200 giorni. Basso = pochi titoli sostengono il mercato.",
    "breadth50": "Come sopra, ma sulla media a 50 giorni (più veloce).",
    "nh_nl": "Società ai massimi a 52 settimane meno quelle ai minimi. Negativo = più titoli in difficoltà che in forza.",
    "gpr": "Indice di rischio geopolitico (guerre, terrorismo, tensioni) basato sulle notizie. Alto = più tensione nel mondo.",
    "gpr_threat": "Parte dell'indice GPR basata sulle minacce di conflitto.",
    "gpr_act": "Parte dell'indice GPR basata su eventi già accaduti (guerre, attentati).",
    "top_ps": "Valore delle 30 maggiori società USA diviso i loro ricavi. Alto = i colossi sono cari.",
    "top_pe": "Prezzo/utili previsti dei 30 colossi. Alto = i colossi sono cari.",
    "top_fcf_yield": "Quanta cassa generano i 30 colossi rispetto al loro valore. Basso = pagati molto per quello che incassano.",
    "ai_capex_ocf": "Quanta parte della cassa operativa Microsoft, Google, Amazon, Meta, Oracle investe in capex (soprattutto AI). Vicino o sopra 1 = spendono più di quanto incassano.",
    "spy_pc_volume": "Rapporto put/call sui volumi di SPY. Sopra 1 più scommesse al ribasso (o protezioni).",
    "spy_pc_open_interest": "Come sopra, ma su tutti i contratti ancora aperti.",
    "spy_iv_atm_30d": "Volatilità attesa a 30 giorni ricavata dalle opzioni su SPY (0,20 = 20%).",
    "spy_put_skew_95": "Quanto costano in più le put 5% sotto il prezzo rispetto a quelle al prezzo attuale. Alto = più paura di un calo.",
}


def _with_live(s: pd.Series, key: str) -> pd.Series:
    """Sostituisce l'ultimo valore con il prezzo piu' recente (live), se piu' nuovo della chiusura."""
    q = livemod.load().get("quotes", {}).get(key)
    if not q or s is None or s.empty:
        return s
    t = pd.Timestamp(q["time"]).tz_localize(None).normalize()
    s = s.copy()
    s.loc[max(t, s.index[-1]) if t <= s.index[-1] + pd.Timedelta(days=4) else s.index[-1]] = q["price"]
    return s.sort_index()


def indicator_series(key, sp, p):
    if key == "sp500":
        return _with_live(sp, "sp500")
    if key == "vwce":
        return _with_live(vwce_display(), "vwce")
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
    if key.startswith("spy_"):
        d = read_csv(DATA / "archive" / "spy_options_summary.csv")
        col = key[4:]
        if d.empty or col not in d.columns:
            return pd.Series(dtype=float)
        d["date"] = pd.to_datetime(d["date"])
        return d.drop_duplicates("date", keep="last").set_index("date")[col].astype(float)
    return store.load(key)


def comparison_html(date, sp, p):
    heads = ["Adesso", "7 giorni fa", "1 mese fa", "3 mesi fa", "6 mesi fa", "1 anno fa"]
    offs = [None, 7, 30, 91, 182, 365]
    out = ["<table><thead><tr><th>Indicatore</th>" + "".join(f"<th>{h}</th>" for h in heads) + "</tr></thead><tbody>"]
    for group, items in INDICATORS:
        out.append(f"<tr class='grp'><td colspan='7'>{esc(group)}</td></tr>")
        for label, key, bad, dec in items:
            s = indicator_series(key, sp, p)
            if key.startswith('spy_') and len(s):
                s = s.copy(); s.index = [min(x, date) for x in s.index]
            vals = []
            for o in offs:
                d = date if o is None else date - pd.Timedelta(days=o)
                vals.append(asof_val(s, d, MAX_AGE.get(key, 12) + (0 if o is None else o)) if s is not None and len(s) else None)
            cells = []
            for k, v in enumerate(vals):
                if v is None:
                    cells.append("<td class='muted'>—</td>")
                    continue
                txt = f"{it(v, 1)}%" if dec == "pct" else it(v, dec)
                small = ""
                if k > 0 and vals[0] is not None and bad != 0:
                    ch = vals[0] - v
                    use_abs = dec == "pct" or abs(v) < 5
                    rel = abs(ch) if use_abs else abs(ch / v)
                    thr = 0.05 if use_abs and dec != "pct" else (1.0 if dec == "pct" else 0.05)
                    if rel >= thr and abs(ch) > 0:
                        worse = (ch > 0) == (bad > 0)
                        shown = ("+" if ch > 0 else "−") + it(abs(ch), 2 if abs(v) < 5 and dec != "pct" else (1 if dec == "pct" else 0)) + (" pt" if dec == "pct" else "")
                        if not use_abs:
                            shown = ("+" if ch > 0 else "−") + it(abs(ch / v) * 100, 0) + "%"
                        small = f"<small class='{'worse' if worse else 'better'}'>da allora {shown}</small>"
                cells.append(f"<td>{txt}{small}</td>")
            if all(v is None for v in vals):
                cells = ["<td colspan='6' class='muted'>dato non disponibile o non aggiornato</td>"]
            hp = INDICATOR_HELP.get(key, "")
            out.append(f"<tr><td data-chart='{key}'>{esc(label)}<div class='ihelp'>{esc(hp)}</div></td>{''.join(cells)}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def one_in(p):
    return f"circa 1 volta su {max(int(round(1 / p)), 1)}" if p and p > 0 else "quasi mai"


def horizon_card(hz, r, spot, rel):
    lev = r["level"]
    prim = PRIMARY[hz]
    pp, bb = r["p"][prim], r["base"][prim]
    words = {"Basso": "più basso del solito", "Normale": "nella norma", "Elevato": "più alto del solito", "Alto": "molto più alto del solito"}[lev]
    main = (f"<div class='big'>{pct(pp, 0)}</div><div class='bigl'>probabilità di un calo di almeno <b>{prim}%</b> entro {HZ_LABEL[hz]}</div>"
            f"<div class='plain'>{one_in(pp).capitalize()}. Di solito è {pct(bb, 0)} ({one_in(bb)}): oggi è <b>{words}</b>.</div>")
    other = "".join(f"<div class='prow'><span>Calo di almeno {t}% entro {HZ_LABEL[hz]}</span><b>{pct(r['p'][t])}</b></div>"
                    for t in sorted(r["p"]) if t != prim)
    ret, cop = spiega.ret_display(hz, r.get("ret"))
    rtxt = ""
    if ret:
        tgt = f" ≈ {it(spot * (1 + ret['q50']), 2)} €" if spot == spot else ""
        rtxt = (f"<div class='hyp'><span class='lab'>Se andasse come in passato in situazioni simili</span>"
                f"<b>{pct(ret['q50'], 1, True)}</b><span class='muted'>rendimento tipico{tgt}. Nell'80% dei casi tra {pct(ret['q10'], 1, True)} e {pct(ret['q90'], 1, True)}. "
                f"{cop} È un'indicazione di tendenza, non una promessa.</span></div>")
    drv = ""
    if r.get("drivers"):
        d = r["drivers"][:3]
        drv = "<div class='drv'>Pesa di più: " + "; ".join(
            f"{FEAT_IT[f]} ({'più rischio' if c > 0 else 'meno rischio'})" for f, c in d) + "</div>"
    relhtml = ""
    if rel:
        txt = {"Utile": "Nei test passati questa stima ha funzionato.", "Debole": "Nei test passati questa stima ha funzionato poco: usala solo come indizio.",
               "Non affidabile": "Nei test passati questa stima non ha funzionato: ignorala."}[rel[0]]
        relhtml = f"<span class='badge {REL_CLASS[rel[0]]}' title='{esc(rel[1])}'>{REL_TXT[rel[0]]}</span><div class='muted'>{txt}</div>"
    return (f"<div class='card hz'><div class='hzh'><h3>{HZ_LABEL[hz]}</h3><span class='badge {LEVEL_CLASS[lev]}'>Rischio {lev.lower()}</span></div>"
            f"{main}{other}{rtxt}{drv}<div class='relrow'>{relhtml}</div></div>")


LIVE_HELP = {
    "vwce": "Il prezzo del tuo ETF, in euro, all'ultimo scambio su qualsiasi borsa tedesca o italiana. La variazione è rispetto alla chiusura precedente.",
    "sp500": "Indice delle 500 maggiori società USA. È il termometro che Armor usa per stimare i rischi.",
    "sp_fut": "Contratti sull'S&P 500 negoziati quasi 24 ore su 24: anticipano dove aprirà Wall Street.",
    "vix": "L'«indice della paura»: sotto 20 il mercato è tranquillo, sopra 25-30 è nervoso. Qui il rosso significa che sta salendo (più paura).",
    "eurusd": "Quanti dollari vale 1 euro. Il VWCE investe in dollari: se l'euro sale, a parità di mercato il VWCE in euro scende un po'.",
}


def live_bar(date):
    lv = livemod.load()
    q = lv.get("quotes", {})
    cards = []
    for key in ("vwce", "sp500", "sp_fut", "vix", "eurusd"):
        x = q.get(key)
        if not x:
            continue
        dec = 4 if key == "eurusd" else 2
        cls = "" if x.get("chg") is None else ("up" if x["chg"] >= 0 else "dn")
        bad_up = key == "vix"
        if bad_up and cls:
            cls = "dn" if cls == "up" else "up"
        chg = "" if x.get("chg") is None else f"{'▲' if x['chg'] >= 0 else '▼'} {abs(x['chg']) * 100:.2f}%".replace(".", ",")
        big = " big1" if key == "vwce" else ""
        cards.append(f"<div class='lq{big}' data-k='{key}' data-chart='{key}'><div class='lqn'>{esc(x['name'])}</div>"
                     f"<div class='lqp'>{it(x['price'], dec)}{(' ' + x['ccy']) if x.get('ccy') else ''}</div>"
                     f"<div class='lqc {cls}'>{chg} <span class='muted'>{'mercato aperto' if x.get('open') else 'mercato chiuso'}</span></div>"
                     f"<div class='lqt muted'></div><div class='lqh muted'>{LIVE_HELP[key]}</div></div>")
    if not cards:
        return ("<div class='livebar'><div class='muted'>Prezzi in tempo reale non ancora scaricati: avvia l'aggiornamento "
                "(o attendi il prossimo aggiornamento automatico).</div></div>")
    err = lv.get("errors") or []
    errtxt = (f"<div class='muted'>Alcune sedi non hanno risposto: {esc('; '.join(err[:4]))}. Si usa quella più recente disponibile.</div>" if err else "")
    return (f"<div class='livebar'><div class='lqrow'>{''.join(cards)}</div>"
            f"<div class='muted' id='liveinfo'></div>{errtxt}</div>"
            f"<script>window.LIVE={json.dumps(lv, ensure_ascii=False)};</script>")


def improvement_html():
    imp = read_csv(DATA / "improvement.csv")
    try:
        reg = json.loads((DATA / "models.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        reg = {"champion": "A1", "versions": []}
    out = []
    if len(imp):
        r = imp.iloc[-1]
        vp = r.get("vs_prev")
        vp_txt = "primo calcolo: il confronto parte dal prossimo mese" if pd.isna(vp) else (
            f"<b class='{'okc' if vp >= 0 else 'dn'}'>{'+' if vp >= 0 else '−'}{it(abs(vp), 2)}</b> punti rispetto al mese scorso")
        va = r["vs_a1"]
        out.append(f"<div class='scorebox'><div><div class='lab'>Punteggio del modello (mese {esc(str(r['month']))})</div><div class='big'>{it(r['score'], 1)}</div>"
                   f"<div class='muted'>Modello in uso: <b>{esc(str(r['model']))}</b></div></div>"
                   f"<div><div class='lab'>Cambiamento</div><div class='plain'>{vp_txt}.<br>Rispetto alla versione iniziale A1: "
                   f"<b>{'+' if va >= 0 else '−'}{it(abs(va), 2)}</b> punti.</div></div></div>")
        rows = "".join(f"<tr><td>{esc(str(x['month']))}</td><td>{esc(str(x['model']))}</td><td>{it(x['score'], 2)}</td>"
                       f"<td>{'—' if pd.isna(x['vs_prev']) else ('+' if x['vs_prev'] >= 0 else '−') + it(abs(x['vs_prev']), 2)}</td>"
                       f"<td>{esc(str(x['promoted'])) if isinstance(x['promoted'], str) and x['promoted'] else '—'}</td></tr>" for _, x in imp.iloc[::-1].head(12).iterrows())
        try:
            ph = json.loads(r["per_hz"])
            out.append("<p class='muted'>Punteggio per periodo (sopra 0 = il modello batte la frequenza storica): " + "; ".join(
                f"{HZ_LABEL[h]} {'+' if v >= 0 else '−'}{it(abs(v), 1)}" for h, v in ph.items()) +
                ". L'indice complessivo è basso perché a 3 e 6 mesi il modello non ha mai funzionato davvero: è il margine su cui l'app proverà a migliorare.</p>")
        except Exception:  # noqa: BLE001
            pass
        out.append("<table><thead><tr><th>Mese</th><th>Modello</th><th>Punteggio</th><th>Variazione</th><th>Nuovo modello adottato</th></tr></thead><tbody>" + rows + "</tbody></table>")
    else:
        out.append("<p class='muted'>Il primo indice mensile verrà calcolato dal controllo automatico di inizio mese.</p>")
    out.append("<details><summary>Come migliora l'app da sola</summary><div class='expl'>"
               "<p><b>Ogni giorno</b> il modello si riaddestra con tutti i dati noti fino a ieri: più storia, stime più solide.</p>"
               "<p><b>Ogni mese</b> Armor prova da sola nuove variabili (valutazioni, credito, paura, geopolitica, ampiezza di mercato...) aggiungendole una alla volta. "
               "Una variabile entra nel modello solo se migliora le previsioni in modo netto e in entrambi i periodi di prova (2000-2012 e dal 2013), su almeno due orizzonti. "
               "Altrimenti viene scartata. Dopo un cambio di modello ne passano almeno 90 giorni prima del successivo, per non rincorrere il caso.</p>"
               "<p><b>Il punteggio del modello</b> è la media di quanto il modello batte la semplice frequenza storica dei cali, nei test dal 2013 (indice di Brier ×100). "
               "Più è alto, meglio il modello prevede i cali; zero significa «come dire sempre la frequenza storica». "
               "La variazione mensile può derivare dai dati nuovi anche senza cambiare modello. È una misura sui test passati, non una garanzia sul futuro.</p></div></details>")
    if reg.get("versions"):
        rows = "".join(f"<tr><td>{esc(v['id'])}{' (in uso)' if v['id'] == reg['champion'] else ''}</td><td>{esc(v['date'])}</td><td style='text-align:left'>{esc(v['note'])}</td></tr>" for v in reg["versions"])
        out.append("<details><summary>Versioni del modello</summary><table><thead><tr><th>Versione</th><th>Data</th><th>Cosa cambia</th></tr></thead><tbody>" + rows + "</tbody></table></details>")
    return "".join(out)


def primary_prob(r):
    """Probabilita' del calo 'principale' dell'orizzonte, da una riga del diario."""
    hz = r["horizon"]
    if r["thr1"] == PRIMARY[hz]:
        return float(r["p1"]), int(r["thr1"])
    if pd.notna(r["p2"]) and r["thr2"] == PRIMARY[hz]:
        return float(r["p2"]), int(r["thr2"])
    return float(r["p1"]), int(r["thr1"])


def history_html(date, pred, hist, jr, outc):
    """Sezione 'Storico delle previsioni': grafici per orizzonte + tabella completa del diario."""
    j = jr.copy()
    if len(j):
        j["asof"] = pd.to_datetime(j["asof"])
        pp = j.apply(primary_prob, axis=1)
        j["pp"] = [a for a, _ in pp]
        j["pthr"] = [b for _, b in pp]
    o = outc.copy() if len(outc) else pd.DataFrame()
    if len(o):
        o["asof"] = pd.to_datetime(o["asof"])
    h = pd.DataFrame()
    if len(hist):
        h = hist.copy()
        h["date"] = pd.to_datetime(h["date"])
        h = h.set_index("date")
        h = h[h.index >= date - pd.Timedelta(days=365 * 6)]
    cols = {"10g": "#d9822b", "1m": "#c0392b", "3m": "#7a4fd1", "6m": "#2a6fdb"}
    charts, btns = [], []
    for k, hz in enumerate(HORIZONS):
        if hz not in pred:
            continue
        thr = PRIMARY[hz]
        ser = (h[f"p_{hz}"] * 100) if len(h) and f"p_{hz}" in h else pd.Series(dtype=float)
        base = pred[hz]["base"][thr] * 100
        live = pd.Series(dtype=float)
        if len(j):
            g = j[j.horizon == hz].sort_values("asof")
            live = pd.Series(g["pp"].values * 100, index=g["asof"].values).groupby(level=0).last()
        today = pd.Series([pred[hz]["p"][thr] * 100], index=[date])
        ser = pd.concat([ser, today]) if len(ser) else today
        ch = svg_lines([(f"Probabilità stimata (%), calo ≥{thr}% entro {HZ_LABEL[hz]}", ser, cols[hz])],
                       fmt=lambda v: it(v, 0) + "%", ymin=0, hline=base,
                       dots=[("Previsioni registrate nel diario", live, "#1b2330")] if len(live) else None)
        charts.append(f"<div class='hzc' id='hzc-{hz}' style='{'' if k == 0 else 'display:none'}'>{ch}"
                      f"<p class='muted'>Linea tratteggiata = frequenza storica ({it(base, 0)}%). La linea colorata è la stima walk-forward sullo S&P 500 dal 2000 "
                      "(ogni punto usa solo i dati noti allora); i pallini sono le previsioni vere, registrate nel diario in tempo reale.</p></div>")
        btns.append(f"<button class='tab{' on' if k == 0 else ''}' data-hz='{hz}' onclick=\"showHz('{hz}')\">{HZ_LABEL[hz]}</button>")
    out = [f"<div class='tabs'>{''.join(btns)}</div>{''.join(charts)}"]
    if not len(j):
        out.append("<p class='muted'>Il diario è ancora vuoto: la prima previsione verrà registrata al prossimo aggiornamento.</p>")
        return "".join(out)

    j = j.sort_values(["horizon", "asof"])
    j["prev_pp"] = j.groupby("horizon")["pp"].shift(1)
    if len(o):
        o2 = o.set_index(["asof", "horizon"])
    rows = []
    for _, r in j.sort_values(["asof", "horizon"], ascending=[False, True]).iterrows():
        hz = r["horizon"]
        try:
            scad = (r["asof"] + pd.offsets.BDay(int(r["sessions"]))).strftime("%d/%m/%Y")
        except Exception:
            scad = "—"
        ch = "" if pd.isna(r["prev_pp"]) else f"{'+' if r['pp'] >= r['prev_pp'] else '−'}{it(abs(r['pp'] - r['prev_pp']) * 100, 1)} pt"
        esito, scost = "<span class='muted'>in corso</span>", "—"
        if len(o) and (r["asof"], hz) in o2.index:
            x = o2.loc[(r["asof"], hz)]
            x = x.iloc[0] if isinstance(x, pd.DataFrame) else x
            hit = x.get("hit1")
            esito = f"{pct(x['realized'], 1, True)}"
            if pd.notna(hit) and hit != "":
                esito += f" · calo ≥{int(r['thr1'])}%: {'avvenuto' if int(hit) == 1 else 'no'}"
            d_ = pd.to_numeric(x.get("discrepancy"), errors="coerce")
            scost = pct(d_, 1, True) if pd.notna(d_) else "—"
        rng = f"{pct(r['q50'], 1, True)} <small class='muted'>[{pct(r['q10'], 1, True)} … {pct(r['q90'], 1, True)}]</small>"
        rows.append(f"<tr><td>{r['asof'].strftime('%d/%m/%Y')}</td><td>{HZ_LABEL[hz]}</td>"
                    f"<td>{pct(r['pp'], 1)} <small class='muted'>calo ≥{int(r['pthr'])}%</small></td><td>{it(r['ratio'], 2)}×</td>"
                    f"<td><span class='badge {LEVEL_CLASS.get(r['level'], 'ok')}'>{esc(r['level'])}</span></td>"
                    f"<td>{rng}</td><td>{ch or '—'}</td><td>{scad}</td><td>{esito}</td><td>{scost}</td></tr>")
    head = ("<table><thead><tr><th>Data</th><th>Orizzonte</th><th>Probabilità di calo</th><th>Rispetto al normale</th><th>Livello</th>"
            "<th>Rendimento ipotizzato VWCE [80%]</th><th>Variazione rispetto alla previsione precedente</th><th>Scadenza</th>"
            "<th>Esito reale</th><th>Scostamento</th></tr></thead><tbody>")
    vis, old = rows[:48], rows[48:]
    out.append("<h3>Tutte le previsioni registrate</h3>" + head + "".join(vis) + "</tbody></table>")
    if old:
        out.append(f"<details><summary>Mostra le {len(old)} previsioni più vecchie</summary>{head}{''.join(old)}</tbody></table></details>")
    out.append("<p class='muted'>Il diario è a sola aggiunta con catena di hash: una previsione registrata non si può modificare a posteriori senza che la verifica lo segnali. "
               "Scostamento = rendimento reale − ipotizzato.</p>")
    return "".join(out)


def challengers_html():
    ch = read_csv(DATA / "challengers.csv")
    ct = read_csv(DATA / "cape_test.csv")
    cq = read_csv(DATA / "cape_quintili.csv")
    out = ["<p>Ogni nuova variabile viene aggiunta al modello in prova e confrontata con quello attuale, in test walk-forward. "
           "Regola fissata prima di guardare i risultati: la variabile entra nel modello solo se migliora l'indice di Brier di oltre 0,01 "
           "<b>e</b> l'AUC sia nel periodo 2000-2012 sia dal 2013. Finora nessuna ha superato la prova: restano mostrate come contesto, non muovono le probabilità.</p>"]
    if len(ch):
        c = ch[ch.get("principale", 0) == 1] if "principale" in ch else ch
        rows = []
        for _, r in c.iterrows():
            e = r["esito"]
            cls = "ok" if e == "CANDIDATA" else "warn"
            f = lambda v: "—" if pd.isna(v) else f"{v:+.3f}".replace(".", ",")
            rows.append(f"<tr><td>{esc(r['variabile'])}</td><td>{esc(str(r.get('target', '')))}</td><td>{f(r.get('dBSS_2000_12'))}</td><td>{f(r.get('dBSS_2013_26'))}</td>"
                        f"<td>{f(r.get('dAUC_2000_12'))}</td><td>{f(r.get('dAUC_2013_26'))}</td><td><span class='badge {cls}'>{esc(e)}</span></td></tr>")
        brk = [r for _, r in ch.iterrows() if str(r["esito"]).startswith("storico")]
        done = {rr["variabile"] for _, rr in c.iterrows()}
        for r in brk:
            if r["variabile"] not in done:
                rows.append(f"<tr><td>{esc(r['variabile'])}</td><td colspan='5' class='muted'>storico ancora troppo breve per un test onesto (si accumula giorno per giorno)</td><td><span class='badge warn'>in attesa</span></td></tr>")
        out.append("<table><thead><tr><th>Variabile aggiunta</th><th>Target</th><th>Δ Brier 2000-12</th><th>Δ Brier 2013-26</th><th>Δ AUC 2000-12</th><th>Δ AUC 2013-26</th><th>Esito</th></tr></thead><tbody>"
                   + "".join(rows) + "</tbody></table><p class='muted'>Δ positivo = la variabile migliora il modello. Servono Δ Brier &gt; 0,01 e Δ AUC &gt; 0 in entrambi i periodi.</p>")
    cape = store.load("cape_m")
    if len(ct) and len(cape):
        cur = cape.iloc[-1]
        pr = (cape < cur).mean() * 100
        out.append(f"<h3>Valutazioni (CAPE) e rendimenti a lungo termine</h3><p>CAPE oggi: <b>{it(cur, 1)}</b>, più alto del {it(pr, 0)}% dei mesi in archivio. "
                   "Un CAPE alto è una buona ragione per aspettarsi rendimenti futuri più bassi su molti anni, ma come strumento di timing non ha funzionato: "
                   "R² fuori campione sotto zero significa che fa peggio di usare la semplice media storica.</p>")
        rows = "".join(f"<tr><td>{esc(r['orizzonte'])}</td><td>{r['r2_tutto']:+.3f}</td><td>{r['r2_2000_12']:+.3f}</td><td>{r['r2_2013_26']:+.3f}</td></tr>".replace(".", ",") for _, r in ct.iterrows())
        out.append("<table><thead><tr><th>Orizzonte</th><th>R² fuori campione 2000-26</th><th>2000-12</th><th>2013-26</th></tr></thead><tbody>" + rows + "</tbody></table>")
    if len(cq):
        rows = "".join(f"<tr><td>{int(r['gruppo'])} di 5</td><td>{it(r['cape_mediano'], 1)}</td><td>{pct(r['rendimento_1a'], 1, True)}</td><td>{pct(r['positivi'], 0)}</td><td>{pct(r['p10'], 1, True)}</td></tr>" for _, r in cq.iterrows())
        out.append(f"<h3>Rendimento a 1 anno per fascia di CAPE (dal {cape.index[0].year})</h3><table><thead><tr><th>Fascia</th><th>CAPE mediano</th><th>Rendimento medio 1 anno</th><th>Casi positivi</th><th>Peggior 10%</th></tr></thead><tbody>"
                   + rows + "</tbody></table>")
    return "".join(out)


def build(ctx: dict, out=None, lazy: bool = False) -> None:
    """lazy=True (sito): solo «Oggi» e' nella pagina; le altre pagine e l'Assistente si caricano da pages/*.html alla prima apertura."""
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
    status = {k: v for k, v in store.read_status().items() if isinstance(v, dict) and "ok" in v}
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
    fl0 = flags_table(panel, p)
    strong = [f for f in fl0 if f["today"] and f["freq"] is not None and f["freq"] >= 1.5 * f["base"]]
    stress_note = (f"{len(strong)} segnali di stress sono attivi (vedi 'Segnali di attenzione'): storicamente, quando erano attivi, "
                   "i cali ≥10% a 3 mesi sono stati molto più frequenti del normale. Il modello sui soli prezzi non li vede ancora.") if len(strong) >= 2 else ""
    weak = [HZ_LABEL[h] for h in HORIZONS if rel.get(h, ("",))[0] != "Utile"]
    note_rel = ("Attenzione: il modello ha funzionato davvero nei test solo a 10 giorni e 1 mese; "
                f"per {' e '.join(weak)} l'affidabilità è debole o non dimostrata (vedi sezione Affidabilità).") if weak else ""

    # cards
    mat = outlook.probability_matrix(p)
    cards = "".join(chiaro.horizon_simple(h, pred[h], mat[h], spot, rel.get(h), horizon_card(h, pred[h], spot, rel.get(h))) for h in HORIZONS if h in pred)

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
    fl = fl0
    rows = []
    for f in sorted(fl, key=lambda x: (not x["today"], x["name"])):
        if f["nodata"]:
            st = "<td class='muted'>dato non disponibile o non aggiornato</td>"
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

    hist_html = history_html(date, pred, hist, jr, outc)
    chal_html = challengers_html()

    imp_html = improvement_html()
    live_html = live_bar(date)
    out = out or REPORT_HTML
    # ---- analisi dettagliate
    sim = outlook.similar_days(p)
    sigs = outlook.signal_table(p)
    vcards = valuations.current()
    rep_an = analysis.load_latest()
    arch_an = analysis.load_archive(14)
    chartdata = sitedata.build(INDICATORS, vw, sp, indicator_series)
    reg = registry.read()
    if len(reg):
        reg.to_csv(out.parent / "registro.csv", index=False)
    ctx_html = parts.context_section(p)
    pf_html = parts.portfolio_section()
    lvl_word = {"Basso": "basso", "Normale": "nella norma", "Elevato": "più alto del normale", "Alto": "alto"}[worst]
    # ---- parte alta: giudizio, rischi, opportunità
    chips = ""
    for hz in HORIZONS:
        if hz not in pred:
            continue
        r_ = pred[hz]
        pdn = r_["p"][PRIMARY[hz]]
        try:
            pup = mat[hz]["up"][PRIMARY[hz]]["p"]
        except Exception:  # noqa: BLE001
            pup = None
        if pup is not None:
            more = "più probabile il calo" if pdn > pup * 1.15 else ("più probabile il rialzo" if pup > pdn * 1.15 else "calo e rialzo quasi pari")
            upl = f"<div class='l up'>rialzo ≥{PRIMARY[hz]}%: <b>{pct(pup, 0)}</b></div><div class='l mo'>{more}</div>"
        else:
            upl = ""
        chips += (f"<div class='hchip'><div class='t'>{HZ_LABEL[hz].upper()}</div><div class='p'>{pct(pdn, 0)}</div>"
                  f"<div class='l'>calo ≥{PRIMARY[hz]}% · <span class='badge {LEVEL_CLASS[r_['level']]}'>{r_['level'].lower()}</span></div>{upl}</div>")
    neg = sorted([x for x in sigs if x["verdict"] == "negativo"], key=lambda x: -x["ratio"])[:3]
    pos = sorted([x for x in sigs if x["verdict"] == "positivo"], key=lambda x: x["ratio"])[:3]
    li = lambda x: (f"<li data-chart='{x['key']}'><b>{esc(x['name'])}</b> {it(x['now'], 2)}: in passato calo ≥10% a 3 mesi nel {pct(x['freq_dd10'], 0)} "
                    f"dei casi (normale {pct(x['base_dd10'], 0)})</li>")
    n_neg = sum(1 for x in sigs if x["verdict"] == "negativo")
    n_pos = sum(1 for x in sigs if x["verdict"] == "positivo")
    oneline = (f"{n_neg} indicatori su {len(sigs)} sono in zona sfavorevole, {n_pos} in zona favorevole, {len(sigs) - n_neg - n_pos} neutri." if sigs else "")
    risks_box = ("<div class='hbox r'><h4>Cosa pesa verso il calo</h4><ul>" + ("".join(li(x) for x in neg) or "<li>Nessun indicatore in zona sfavorevole.</li>")
                 + (f"<li>{esc(stress_note)}</li>" if stress_note else "") + "</ul></div>")
    opps_box = ("<div class='hbox o'><h4>Cosa pesa verso il rialzo</h4><ul>" + ("".join(li(x) for x in pos) or "<li>Nessun indicatore chiaramente favorevole.</li>")
                + "</ul></div>")
    val_line = ""
    sp_c = next((c for c in vcards if c["key"] == "sp500"), None)
    if sp_c and sp_c.get("pe"):
        val_line = f" Il mercato è {'caro' if (sp_c.get('pe_pct') or 0) >= 80 else ('nella norma' if (sp_c.get('pe_pct') or 50) >= 30 else 'economico')} rispetto alla storia (P/E S&amp;P 500 {it(sp_c['pe'], 1)})."
    ctx_line = ""
    try:
        from . import calendario as _cal, regime as _reg
        _r = _reg.compute(p)
        _e = _cal.next_big(_cal.events(days=30))
        ctx_line = f" Regime di mercato: <b>{_r['nome'].lower()}</b>."
        if _e:
            ctx_line += f" Prossimo evento chiave: {_e['nome']} ({'oggi' if _e['giorni'] == 0 else 'domani' if _e['giorni'] == 1 else 'tra ' + str(_e['giorni']) + ' giorni'})."
    except Exception:  # noqa: BLE001
        pass
    simple = [f"<b>Cosa dice la pagina in breve.</b> {oneline}{val_line}{ctx_line}",
              "Armor <b>non prevede se il mercato salirà o scenderà</b>: stima quanto è probabile un calo (o una risalita) importante, confrontando oggi con tutta la storia.",
              "Per chi investe con un PAC i cali fanno parte del percorso: la pagina serve a capire in che clima si investe, non a indovinare il momento."]
    simple_html = "".join(f"<li>{x}</li>" for x in simple)
    guide = """<details class='guide'><summary>Come leggere questa pagina (30 secondi)</summary><div class='expl'>
<p><b>In alto</b>: prezzi di adesso (toccali per aprire il grafico) e il giudizio del giorno. <span class='badge ok'>verde</span> = clima tranquillo, <span class='badge warn'>giallo</span> = prudenza, <span class='badge bad'>rosso</span> = rischio alto.</p>
<p><b>Valutazioni</b>: quanto è «caro» il mercato (P/E e P/S). <b>Grafici</b>: ogni indice con intervalli da 6 ore a tutta la storia. <b>Previsioni</b>: probabilità di cali e risalite a 10 giorni, 1, 3 e 6 mesi, con i momenti passati più simili. <b>Analisi</b>: il report quotidiano su tutti gli indici e sulle notizie. <b>Storico</b> e <b>Registro</b>: tutto ciò che Armor ha previsto e salvato giorno per giorno.</p>
<p>Le stime sono probabilità basate sul passato, non certezze e non consigli di investimento.</p></div></details>"""
    gloss = """<details><summary>Piccolo dizionario</summary><div class='expl'>
<p><b>Calo</b>: di quanto il prezzo scende dal massimo raggiunto in un periodo. «Calo di almeno 10%» = a un certo punto il prezzo è 10% sotto il massimo.</p>
<p><b>Risalita</b>: di quanto il prezzo sale sopra il livello di oggi in un periodo.</p>
<p><b>Probabilità</b>: 8% vuol dire circa 8 volte su 100, in situazioni simili nel passato.</p>
<p><b>Orizzonte</b>: per quanto tempo guardiamo avanti (10 giorni, 1 mese, 3 mesi, 6 mesi).</p>
<p><b>PAC</b>: piano di accumulo, cioè acquisti ripetuti ogni mese.</p>
<p><b>VIX</b>: l'«indice della paura». Sopra 25-30 il mercato è nervoso.</p>
<p><b>S&P 500 / Nasdaq 100</b>: indici delle 500 maggiori società USA e delle 100 maggiori società tecnologiche quotate al Nasdaq. VWCE segue l'intero mercato mondiale, per circa due terzi USA.</p>
<p><b>P/E, P/S, CAPE</b>: quanto è «caro» il mercato rispetto agli utili, ai ricavi o agli utili medi di 10 anni.</p>
<p><b>Walk-forward</b>: test onesto: a ogni data il modello usa solo ciò che si sapeva allora.</p>
<p><b>AUC e Brier (BSS)</b>: voti del modello. AUC 0,5 = tirare una moneta, 1 = perfetto. BSS sopra 0 = meglio di dire sempre «la frequenza storica».</p></div></details>"""
    def det(title, inner):
        return f"<details class='exp'><summary>{title}</summary><div class='card scroll'>{inner}</div></details>"
    help_all = dict(INDICATOR_HELP)
    help_all.update({k: v for k, v in LIVE_HELP.items()})
    help_all.update({"val_pe_vwce": "Quanti euro si pagano per ogni euro di utile annuo delle società del mercato mondiale.", "val_ps_vwce": "Quanti euro si pagano per ogni euro di ricavi.",
                     "val_pe_sp500": "P/E dell'S&P 500 (dati del fondo).", "val_ps_sp500": "Prezzo/fatturato dell'S&P 500 (dati del fondo).",
                     "val_pe_ndx": "P/E del Nasdaq 100.", "val_ps_ndx": "Prezzo/fatturato del Nasdaq 100.",
                     "risk_1m": "Probabilità stimata da Armor di un calo ≥10% nel mese successivo, ricostruita giorno per giorno dal 2000.",
                     "risk_3m": "Probabilità stimata da Armor di un calo ≥10% nei 3 mesi successivi.", "risk_6m": "Probabilità stimata da Armor di un calo ≥10% nei 6 mesi successivi.",
                     "risk_10g": "Probabilità stimata da Armor di un calo ≥5% nei 10 giorni successivi."})
    labels_all = {k: v["l"] for k, v in chartdata.items()}
    labels_all.update({"date": "Data", "vwce_ultimo": "VWCE ultimo (€)", "p_10g": "Prob. calo ≥5% a 10 giorni", "p_1m": "Prob. calo ≥10% a 1 mese",
                       "p_3m": "Prob. calo ≥10% a 3 mesi", "p_6m": "Prob. calo ≥10% a 6 mesi", "livello_10g": "Livello 10 giorni", "livello_1m": "Livello 1 mese",
                       "livello_3m": "Livello 3 mesi", "livello_6m": "Livello 6 mesi", "news_sent_macro": "Tono notizie macro", "news_neg_macro": "Notizie macro negative",
                       "news_pos_macro": "Notizie macro positive", "news_n": "Notizie lette"})
    chip_defs = [("vwce", "VWCE"), ("sp500", "S&P 500"), ("ndx", "Nasdaq 100"), ("vt", "Azioni mondiali (VT)"), ("vix", "VIX"), ("eurusd", "EUR/USD"),
                 ("risk_10g", "Rischio calo 10 giorni"), ("risk_1m", "Rischio calo 1 mese"), ("risk_3m", "Rischio calo 3 mesi"), ("risk_6m", "Rischio calo 6 mesi"),
                 ("pe_m", "P/E S&P 500"), ("ps_m", "P/S S&P 500"), ("cape_m", "CAPE"), ("val_pe_vwce", "P/E VWCE"), ("val_pe_ndx", "P/E Nasdaq"),
                 ("hy_oas", "Spread High Yield"), ("baa10y", "Spread BAA"), ("t10y3m", "Curva 10Y-3M"), ("dgs10", "Rendimento 10 anni"), ("real10y", "Tasso reale"),
                 ("gold", "Oro"), ("wti", "Petrolio"), ("usd_broad", "Dollaro"), ("unrate", "Disoccupazione"), ("aaii_spread", "Sentiment AAII"), ("gpr", "Geopolitica"),
                 ("skew", "SKEW"), ("nfci", "Condizioni finanziarie")]
    chip_opts = [(k, l) for k, l in chip_defs if k in chartdata and (chartdata[k]["d"] or chartdata[k].get("i"))]
    # ---- nuovi moduli (ognuno protetto: se uno fallisce, la pagina resta)
    from . import allarmi, bilancio, decennio, insight, mercati, news as newsmod, posizionamento, regime as regmod, semafori
    sem = semafori.compute(p, livemod.load())
    from . import armor_index
    aix = armor_index.compute(sp)
    if aix:
        armor_index.save_history(aix)
        try:
            chartdata["armor_index"] = {"l": "Indice Armor (1–100)", "dec": 0, **sitedata.ser_payload(store.load("armor_index"), 0)}
            help_all.setdefault("armor_index", "Indice sintetico 1–100 del rischio di crollo e volatilità: unisce volatilità, credito, tassi, valutazioni, tendenza, sentimento, economia e modello statistico.")
        except Exception:  # noqa: BLE001
            pass
    for i in sem:
        help_all.setdefault(i["key"], i["read"])
        if i["key"] not in chartdata:
            try:
                ss = semafori.series_of(i["key"], sp)
                if len(ss) > 5:
                    chartdata[i["key"]] = {"l": i["name"], "dec": min(i["dec"], 2), **sitedata.ser_payload(ss, min(i["dec"], 2))}
            except Exception:  # noqa: BLE001
                pass
    try:
        from . import grafico
        chartdata.update(grafico.extra_chartdata(sitedata))
    except Exception:  # noqa: BLE001
        pass
    for k, name in list(extra13.EXTRA_KEYS.items()):
        try:
            ss = store.load(k)
            if len(ss) > 5 and k not in chartdata:
                chartdata[k] = {"l": name, "dec": 1, **sitedata.ser_payload(ss, 1)}
        except Exception:  # noqa: BLE001
            pass
    for k, name in [(k, n) for k, n in mercati.REGIONS] + [(k, f"Settore {n}") for k, n, _ in mercati.SECTORS] + [("cot_lev_net", "Fondi a leva: posizione netta (% OI)"), ("cot_am_net", "Gestori patrimoniali: posizione netta (% OI)")]:
        ss = store.load(k)
        if len(ss) > 5 and k not in chartdata:
            chartdata[k] = {"l": name, "dec": 2, **sitedata.ser_payload(ss, 2)}
    labels_all.update({k: v["l"] for k, v in chartdata.items()})
    if lazy:   # una serie per file (series/<chiave>.json): si scarica solo quando si apre un grafico
        sitedata.write(out.parent / "data.json", chartdata)
    coh = insight.coherence(sem) if sem else {"gruppi": [], "discordanti": False, "calmi": [], "tesi": [], "note": []}
    try:
        ind10 = decennio.indicators(p, sem)
        tr10 = decennio.track_record(p)
    except Exception as ex:  # noqa: BLE001
        print("Analisi 10 anni non riuscita:", str(ex)[:100])
        ind10, tr10 = [], None
    sy10 = decennio.synthesize(ind10) if ind10 else None
    try:
        epis = insight.episodes_html(insight.episode_paths(p, outlook.similar_days(p, n=10)))
    except Exception as ex:  # noqa: BLE001
        epis = f"<p class='mu'>Episodi non disponibili ({type(ex).__name__}).</p>"
    ctxs = {}
    for c in vcards:
        for m, ser in (("pe", "pe_m"), ("ps", "ps_m")):
            try:
                if c["key"] == "sp500":
                    ctxs[(c["key"], m)] = valuations.history_context(ser, c.get(m))
                else:
                    own = store.load(f"val_{m}_{c['key']}")
                    ctxs[(c["key"], m)] = valuations.history_context(f"val_{m}_{c['key']}", c.get(m)) if len(own) > 400 else None
            except Exception:  # noqa: BLE001
                ctxs[(c["key"], m)] = None
    cape = None
    try:
        cs = store.load("cape_m")
        if len(cs) > 200:
            cv = float(cs.iloc[-1])
            cape = {"value": cv, "zone": "ok" if cv < 28 else ("wa" if cv < 35 else "ba"), "ctx": valuations.history_context("cape_m", cv)}
            if cape["ctx"] is None:
                cape = None
    except Exception:  # noqa: BLE001
        cape = None
    try:
        bil = json.loads((DATA / "reports" / "bilancio-latest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        bil = bilancio.day_summary(pred, None, regmod.compute(p)["nome"], newsmod.load_latest(), semaforo=semafori.overall(sem) if sem else None)
    wk = bilancio.weekly_load()
    try:
        al_opts, al_now = allarmi.options_json(p, pred)
    except Exception:  # noqa: BLE001
        al_opts, al_now = [], {}
    sc = semafori.overall(sem)
    sem_line = (f"<div class='semsum'><a href='#' class='semlk' data-semlist='ok'><span class='dot ok'></span>{sc['ok']} verdi</a> "
                f"<a href='#' class='semlk' data-semlist='wa'><span class='dot wa'></span>{sc['wa']} gialli</a> <a href='#' class='semlk' data-semlist='ba'><span class='dot ba'></span>{sc['ba']} rossi</a> "
                f"<a href='#indici' data-go='indici'>Vedi tutti i semafori ›</a></div>") if sem else ""
    disc_line = ("<div class='banner'><b>Segnali discordanti:</b> " + f"{', '.join(coh['calmi'])} sono tranquilli, {', '.join(coh['tesi'])} no. <a href='#indici' data-go='indici'>Dettagli</a></div>") if coh["discordanti"] else ""
    ten_line = (f"<div class='card'><b>Rispetto agli ultimi 10 anni:</b> {sy10['verdict']} <a href='#' data-dock='dieci'>Analisi completa ›</a></div>") if sy10 else ""
    pages = [("oggi", "Oggi"), ("notizie", "Notizie"), ("mercati", "Mercati"), ("saldi", "Saldi"), ("opportunita", "Opportunità"), ("indici", "Indici"), ("regime", "Regime di tensione"), ("valutazioni", "Valutazioni"), ("aziende", "Aziende VWCE"), ("macro", "Economia e Fed"), ("grafici", "Grafici"), ("previsioni", "Previsioni"),
             ("fiducia", "Quanto fidarsi"), ("contesto", "Contesto"), ("portafoglio", "Il mio VWCE e PAC"), ("storico", "Storico"), ("archivio", "Archivio dati"), ("allarmi", "Allarmi")]
    from . import navigazione
    nav = navigazione.html(pages)
    lazy_pages: dict[str, str] = {}

    def page(k, inner):
        if not lazy or k == "oggi":
            return f"<div class='pg' id='p-{k}'>{inner}</div>"
        late = ""
        for marker, js in (("id='epcanvas'", f"<script>{insight.EP_JS}</script>"), ("id='alkey'", f"<script>{parts.AL_JS}</script>"),
                           ("id='embedchart'", parts.LATE_JS["embedchart"]), ("id='regsel'", parts.LATE_JS["regsel"]), ("id='pacamt'", ui.PAC_JS), ("id='pscap'", pacsim.JS)):
            if marker in inner:
                late += js
        lazy_pages[k] = inner + late
        return f"<div class='pg' id='p-{k}' data-src='pages/{k}.html'><p class='mu'>Caricamento…</p></div>"
    def _safe(fn, what):
        try:
            return fn()
        except Exception as ex:  # noqa: BLE001
            return f"<p class='mu'>{what} non disponibile oggi ({type(ex).__name__}).</p>"
    today_d = _date.today()
    soon = [x for x in extra13.all_events(today_d, today_d + timedelta(days=2)) if x["peso"] >= 3]
    div = extra13.divergence(sp, aix)
    # mappa settimanale e calendario: dati in JSON a parte (sito) o incorporati (file locale)
    map_json = cal_json = None
    try:
        vw_h = vwce_display()
        mp = mappa.build_mappa(sp, aix, vw_h)
        evs_all = extra13.all_events(today_d - timedelta(days=1200), today_d + timedelta(days=75))
        cl = mappa.build_cal(sp, vw_h, store.load("vix"), aix, pd.Timestamp(today_d), evs_all)
        map_json, cal_json = (mappa.dumps(mp) if mp else None), mappa.dumps(cl)
        if lazy:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            if map_json:
                (sd / "mappa.json").write_text(map_json, encoding="utf-8")
            (sd / "cal.json").write_text(cal_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Mappa/calendario non creati:", str(ex)[:160], flush=True)
    nz_json = None
    try:
        nz_json = novita.dumps(novita.archivio())
        if lazy:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "notizie.json").write_text(nz_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Archivio notizie non creato:", str(ex)[:120], flush=True)
    md_json = None
    try:
        md_json = mondo.carica()
        if lazy and md_json:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "mercati.json").write_text(md_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Dati Mercati non letti:", str(ex)[:120], flush=True)
    sd_json = None
    try:
        sd_json = saldi.carica()
        if lazy and sd_json:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "saldi.json").write_text(sd_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Dati Saldi non letti:", str(ex)[:120], flush=True)
    op_json = None
    try:
        op_json = opportunita.carica()
        if lazy and op_json:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "opportunita.json").write_text(op_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Dati Opportunità non letti:", str(ex)[:120], flush=True)
    ec_json = None
    try:
        ec_json = economia.carica()
        if lazy and ec_json:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "economia.json").write_text(ec_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Dati Economia non letti:", str(ex)[:120], flush=True)
    cf_json = None
    try:
        cfd = confronto.build(sp, vwce_display(), aix)
        cf_json = confronto.dumps(cfd) if cfd else None
        if cf_json and lazy:
            sd = out.parent / "series"
            sd.mkdir(exist_ok=True)
            (sd / "confronto.json").write_text(cf_json, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("Grafico di confronto non creato:", str(ex)[:160], flush=True)
    cf_intro = ("<div class='explain'><p>In alto i mercati (<b>S&amp;P 500</b>, <b>VWCE</b> e altri a scelta), sotto l'<b>Indice Armor</b> e le probabilità di calo (rosso) e di rialzo (verde), giorno per giorno dal 2000. "
                "Serve a vedere se ai picchi dell'indice sono seguiti davvero cali del mercato. Puoi accendere altre linee (VIX, credito, valutazioni, oro, bitcoin…), cambiare periodo, ingrandire e scorrere. Tieni il mouse fermo o il dito premuto su un nome per leggere cosa significa.</p></div>")
    if not cf_json:
        cf_small = cf_full = "<p class='mu'>Grafico non disponibile oggi.</p>"
    elif lazy:
        cf_full = confronto.block()
        cf_small = "<div data-lazybox='pages/confronto.html'><p class='mu'>Caricamento del grafico…</p></div>"
    else:
        cf_full = confronto.block()
        cf_small = confronto.block(cf_json)
    map_intro = ("<div class='explain'><p>Ogni riga è un indicatore, ogni colonna una <b>settimana</b> (fino a 10 anni). In alto, <b>cosa hanno fatto davvero VWCE e S&amp;P 500</b> in quella settimana "
                 "(verde = salito, rosso = sceso): così vedi a che rendimenti corrispondono i colori di rischio sotto (<b>verde = calma, rosso = stress</b>). "
                 "Tocca o passa il mouse su un quadratino: compare il perché di quel valore. Tocca il nome di una riga: vedi a quali valori reali corrispondono i colori.</p></div>")
    if map_json is None:
        map_full = map_small = "<p class='mu'>Mappa non disponibile oggi.</p>"
    elif lazy:
        map_full = mappa.mappa_block(open_=True, per=156)
        map_small = "<div data-lazybox='pages/mappa.html'><p class='mu'>Caricamento della mappa…</p></div>"
    else:
        map_full = mappa.mappa_block(open_=True, per=156)
        map_small = mappa.mappa_block(open_=False, per=52, data_json=map_json)
    n_pru = sum(1 for x in sigs if x["verdict"] == "negativo")
    topbtns = "<div class='topbtns'><button class='btn pri' data-cal='1'>Calendario eventi</button><button class='btn' data-dock='oggi'>Assistente e analisi</button><button class='btn' data-dock='gloss'>Glossario</button></div>"
    hero_old = (f"<section class='hero {LEVEL_CLASS[worst]}'><div class='hlk'>Il giudizio di oggi</div><div class='hl1'>{verdict}</div>"
                f"<div class='hl2'>Il rischio di un calo importante è <b>{lvl_word}</b>.</div>{sem_line}"
                f"<div class='hrow'>{risks_box}{opps_box}</div><div class='hl3'>{esc(note_rel)}</div></section>"
                f"{disc_line}<h2>Gli indici più importanti</h2>{semafori.html(sem, keys_only=True)}{ten_line}{guide}")
    # «Oggi» in 5 blocchi: 1 cosa faccio, 2 Indice Armor + probabilita', 3 calo o rialzo (+ Perche?), 4 P/E e P/S, 5 prossimo evento
    more = ("<div class='more'>Per i dettagli: <a href='#indici' data-go='indici'>Indici</a> · <a href='#previsioni' data-go='previsioni'>Previsioni</a> · "
            "<a href='#fiducia' data-go='fiducia'>Quanto fidarsi</a> · <a href='#storico' data-go='storico'>Storico</a> · oppure apri l'Assistente in basso.</div>")
    try:
        hz3 = armor_index.horizons(aix, sp)
    except Exception as ex:  # noqa: BLE001
        print("Indici a 3 orizzonti non calcolati:", str(ex)[:120], flush=True)
        hz3 = None
    kpi = _safe(lambda: cruscotto.kpi_html(sem, sp, vwce_display(), store.load("vix")), "Indici principali")
    try:
        semafori.registra_colori(sem, today_d.isoformat())
    except Exception as ex:  # noqa: BLE001
        print("Storico semafori non salvato:", str(ex)[:100], flush=True)
    sem_new = _safe(lambda: semafori.oggi_html(sem, today_d.isoformat()), "Semafori di oggi") if sem else ""
    reg_o = _safe(lambda: tensione.oggi(), "Regime di tensione") or None
    if reg_o:
        _safe(lambda: tensione.registra_ombra(reg_o), "Registro regime")
    reg_box = _safe(lambda: tensione.CSS + tensione.box_oggi(reg_o), "Regime di tensione") if reg_o else ""
    p_regime = _safe(lambda: tensione.pagina(reg_o, None, tensione.grafico_dati()), "Pagina regime")
    p_oggi = (f"<a id='oggi'></a>{topbtns}"
              f"<section class='b5'>{armor_index.hero_html(aix, cruscotto.hero_trend(aix))}</section>{kpi}"
              f"{cruscotto.armor_window(hz3, aix)}{cruscotto.JS}"
              f"{sem_new}{reg_box}"
              f"<section class='b5'>{parts.valuations_mini(vcards)}</section>{ui.next_event_html(today_d)}"
              f"<h2 style='margin-top:22px'>Indice Armor contro i mercati, giorno per giorno</h2>{cf_intro}{cf_small}"
              f"<section class='b5'>{extra13.oggi_html(aix, div, [], n_pru)}{extra13.divergence_html(div)}</section>{_safe(diagnostica.banner, 'Avviso diario')}{_safe(affidabilita.html, 'Affidabilità')}"
              f"<section class='b5'>{chiaro.balance_html(pred, mat, FEAT_IT, n_neg, len(sigs))}</section>"
              f"{_safe(ciclico.box_rischio, 'Rischio ciclico')}{_safe(ciclico.box_simili, 'Mesi simili')}"
              f"<h2 style='margin-top:22px'>Mappa dei segnali, settimana per settimana</h2>{map_intro}{map_small}"
              "<div class='topbtns' style='margin-top:10px'><button class='btn pri' data-cal='1'>Apri il calendario: previsto e reale</button><button class='btn' data-go='indici'>Mappa completa</button></div>"
              f"{more}")
    p_indici = (hero_old + "<h2>Cruscotto degli indici: semafori e come leggerli</h2>"
                "<div class='explain'><p>Ogni scheda mostra il valore di oggi, un <b>semaforo</b> (verde = tranquillo, giallo = attenzione, rosso = allarme), come si legge l'indice e quando preoccuparsi. "
                "Tocca una scheda per aprire il grafico. Le soglie sono fisse e valgono per tutta la storia.</p></div>" +
                armor_index.detail_html(aix) + f"<div class='card'><h3 style='margin-top:0'>Coerenza dei segnali</h3>{insight.coherence_html(coh)}</div>" + semafori.html(sem)
                + "<h2 style='margin-top:26px'>Mappa settimanale dei segnali</h2>" + map_intro + map_full
                + "<h2 style='margin-top:26px'>Confronto con le grandi crisi</h2>" + _safe(lambda: extra13.crisi_html(aix, sp), "Confronto crisi"))
    p_az = ("<h2>Salute delle aziende in VWCE</h2>" + _safe(lambda: aziende.html(aziende.load()), "Aziende VWCE"))
    p_macro = ("<h2>Dati economici anticipati</h2>" + _safe(extra13.early_html, "Dati economici") + "<h2 style='margin-top:26px'>Liquidità e tassi della Fed</h2>" + _safe(extra13.fed_html, "Liquidità Fed") + _safe(lambda: economia.block(None if lazy else ec_json), "Economia nel mondo"))
    p_val = (f"<h2>Quanto è «caro» il mercato: P/E e P/S in tempo reale</h2>{parts.valuation_block(vcards, ctxs, cape)}")
    p_graf = f"<h2>Confronto: Indice Armor, S&amp;P 500 e VWCE</h2>{cf_intro}{cf_full}<h2 style='margin-top:26px'>Grafici interattivi</h2>{parts.charts_section(chip_opts)}"
    def _incl():
        pp = p[p.index >= "1985-01-01"]
        v = json.loads(inclinazione.FILE_VERIFICA.read_text(encoding="utf-8")) if inclinazione.FILE_VERIFICA.exists() else None
        return inclinazione.html(inclinazione.oggi(pp, store.load("vix"), store.load("armor_index")), v)
    p_prev = (_safe(_incl, "Inclinazione") + f"<h2 style='margin-top:26px'>Previsioni per periodo: calo o rialzo?</h2>{chiaro.PREV_INTRO}"
              f"<div class='grid4'>{cards}</div>"
              f"<h3 style='margin-top:22px'>Scenari da 1 settimana a 1 anno</h3><div class='card'>{_safe(percorsi.html, 'Scenari')}</div>"
              f"<h3 style='margin-top:22px'>Quanto ti puoi fidare: l'errore reale delle previsioni</h3><div class='card scroll'>{insight.honest_html(insight.honest(pred))}</div>"
              f"<h3 style='margin-top:22px'>Cali e risalite a tutte le soglie (1% … 20%)</h3><div class='card scroll'>{parts.matrix_html(mat, sim)}</div>"
              f"<h3 style='margin-top:22px'>Il percorso dopo i momenti più simili a oggi</h3>{epis}"
              f"<h3 style='margin-top:22px'>Quali indici danno segnali positivi o negativi</h3>{chiaro.signals_simple(sigs)}{chiaro.scenarios_html(sigs)}"
              f"<h3 style='margin-top:22px'>Segnali di stress del mercato</h3>{chiaro.flags_simple(fl0)}")
    p_ctx = (parts.context_section(p)
             + "<h3 style='margin-top:18px'>Altri mercati: il rischio è globale o solo americano?</h3><div class='card scroll'>" + _safe(lambda: mercati.html(mercati.compute()), "Confronto mercati") + "</div>"
             + "<h3 style='margin-top:18px'>Opzioni e posizionamento</h3><div class='card scroll'>" + _safe(posizionamento.html, "Posizionamento") + "</div>")
    p_an = (f"<h2>Analisi giornaliera: indici, confronto col passato e notizie</h2>{parts.analysis_section(rep_an, arch_an)}"
            f"<h2 style='margin-top:26px'>Gli ultimi 10 anni a confronto con oggi</h2><div class='card'>{_safe(lambda: decennio.html(ind10, tr10), 'Analisi dei 10 anni')}</div>"
            f"<h2 style='margin-top:26px'>Rapporto settimanale</h2>{bilancio.weekly_html(wk)}")
    p_pf = ui.PAC_HTML + pacsim.HTML + live_html + parts.portfolio_section()
    p_fid = ("<h2>Quanto mi posso fidare di Armor?</h2>" + _safe(lambda: ui.fiducia_html(sp, live=learning.live_table(sp)), "Pagina di fiducia")
             + "<h2 style='margin-top:26px'>Sfidanti in prova</h2><div class='card'>" + _safe(campioni.html, "Motori per orizzonte") + "</div>"
             + "<h2 style='margin-top:26px'>Verifica storica con margini d'errore</h2><div class='card'>" + _safe(verifica.html, "Verifica storica") + "</div>"
             + "<h2 style='margin-top:26px'>VWCE in euro</h2><div class='card'>" + _safe(serie_eur.html, "VWCE in euro") + "</div>"
             + "<h2 style='margin-top:26px'>Motore di percorsi: regola di adozione</h2><div class='card'>" + _safe(percorsi.html_verifica, "Percorsi verifica") + "</div>"
             + "<h2 style='margin-top:26px'>Esperimento: premio di volatilità (in ombra)</h2><div class='card'>" + _safe(vrp.html, "VRP") + "</div>"
             + "<h2 style='margin-top:26px'>Ricerca modello: salute delle aziende, macro e storia lunga</h2><div class='card'>" + _safe(ciclico.html_ricerca, "Ricerca modello") + "</div>")
    p_sto = (f"<h2>Storico delle previsioni</h2><p class='muted'>Cosa aveva previsto Armor, giorno per giorno, e cosa è successo davvero.</p>"
             f"<div class='explain'><p><b>Come leggere la tabella.</b> <i>Probabilità di calo</i>: la stima di quel giorno. <i>Rispetto al normale</i>: 1× = nella norma. <i>Rendimento ipotizzato</i>: cosa ci si poteva aspettare dal VWCE (tra parentesi l'intervallo dell'80% dei casi). <i>Variazione</i>: rispetto all'ultima previsione per lo stesso periodo. <i>Scadenza</i>: quando si può verificare. <i>Esito reale</i> e <i>Scostamento</i> compaiono a scadenza.</p></div><div class='card scroll'>{hist_html}</div>"
             f"<h2>Previsto contro reale</h2><div class='card'>{pv}</div>"
             f"<h2>Registro dei dati giornalieri</h2>{parts.registry_section()}"
             f"<h2>Come va l'app: miglioramento automatico</h2><div class='card scroll'>{imp_html}</div>"
             f"<h2>Dettagli per esperti</h2><p class='muted'>Tabelle e test dietro le stime. Aprile solo se vuoi approfondire.</p>"
             + det('Confronto degli indicatori con il passato', comparison_html(date, sp, p) + "<p class='muted'>Sotto ogni valore passato: di quanto è cambiato l'indicatore da allora a oggi. Rosso = verso più rischio, verde = verso meno rischio.</p>")
             + det('Affidabilità del modello (test dal 2000)', avh) + det('Variabili provate e non adottate', chal_html) + det('Dati, fonti e archivio', dc) + gloss)
    p_arc = _safe(archivio_dati.html, 'Archivio dati')
    p_nz = _safe(lambda: novita.block(None if lazy else nz_json), "Notizie")
    p_md = _safe(lambda: mondo.block(None if lazy else md_json), "Mercati")
    p_sd = _safe(lambda: saldi.block(None if lazy else sd_json), "Saldi")
    p_op = _safe(lambda: opportunita.block(None if lazy else op_json), "Opportunità")
    nz_dock = ("<p><a href='#notizie' class='btn pri' data-go='notizie'>Apri tutte le notizie</a></p>"
               + "".join(f"<div class='nzi {i.get('label', 'neutro')}'><b>{html.escape(i['title'])}</b><div class='me'>{html.escape(i.get('source', ''))} · {html.escape(i.get('group', ''))}</div></div>"
                         for i in sorted([x for x in newsmod.load_latest().get('items', []) if x.get('kind') in ('macro', 'sector')], key=lambda x: -x['score'])[:12]))
    p_al = ("<h2>Allarmi personali</h2>" + parts.alerts_section(al_opts, al_now))
    p_sto = p_sto + "<h2>Rapporto mensile</h2>" + _safe(lambda: rapporto.html(rapporto.load_latest()), "Rapporto mensile") + "<h2>Pagella mensile</h2>" + _safe(extra13.pagella_html, "Pagella") + "<h2>Salute dei dati</h2>" + _safe(diagnostica.badge, "Stato del diario") + _safe(lambda: salute.html(salute.compute()), "Salute dei dati") + "<h2>Apprendimento dai dati reali</h2>" + _safe(lambda: learning.html(sp), "Apprendimento")
    vix_s = store.load("vix")
    cal_html = _safe(lambda: extra13.calendar_html(_date.today(), sp, vix_s, mappa.cal_block(None if lazy else cal_json) if cal_json else ""), "Calendario")
    headline = (f"Indice Armor {aix['value']:.0f}/100 · " if aix else "") + verdict
    dock_tabs = [
        ("oggi", "Oggi cosa faccio", extra13.oggi_html(aix, div, soon, n_pru) + extra13.divergence_html(div) + "" + bilancio.day_html(bil)),
        ("ai", "Analisi di oggi", parts.analysis_section(rep_an, arch_an)),
        ("notizie", "Notizie", nz_dock),
        ("dieci", "Ultimi 10 anni", _safe(lambda: decennio.html(ind10, tr10), "Analisi dei 10 anni")),
        ("sett", "Rapporto settimanale", bilancio.weekly_html(wk)),
        ("mens", "Rapporto mensile", _safe(lambda: rapporto.html(rapporto.load_latest()), "Rapporto mensile")),
        ("pag", "Pagella", _safe(extra13.pagella_html, "Pagella")),
        ("cal", "Calendario", "<p>Si apre il calendario con tutti gli eventi.</p><button class='btn pri' data-cal='1'>Apri il calendario</button>"),
        ("gloss", "Glossario", extra13.glossario_html()),
    ]
    if lazy:   # l'Assistente si carica alla prima apertura (pages/dock.html)
        if map_json:
            lazy_pages["mappa"] = mappa.mappa_block(open_=False, per=52)
        if cf_json:
            lazy_pages["confronto"] = confronto.block()
        dock_frag = "".join(f"<div data-dpane='{k}'>{h}</div>" for k, _l, h in dock_tabs) + f"<div data-dpane='_cal'>{cal_html}</div>"
        lazy_pages["dock"] = dock_frag
        dock = extra13.dock_html(headline, [(k, l, "<p class='mu'>Caricamento…</p>") for k, l, _h in dock_tabs]).replace("{{CAL}}", "")
    else:
        dock = extra13.dock_html(headline, dock_tabs).replace("{{CAL}}", cal_html)

    dock_js = extra13.DOCK_JS_LAZY if lazy else extra13.DOCK_JS
    tabs_js = parts.TABS_JS_LAZY if lazy else parts.TABS_JS
    body = f"""
<header><div>{marchio.html()}<div class='muted'>Quanto è rischioso il mercato oggi per il tuo VWCE · dati del {date.strftime('%d/%m/%Y')} · pagina generata {datetime.now().strftime('%d/%m/%Y %H:%M')}</div></div>{forza.HTML}</header>
{nav}{_safe(forza.banner_dati_fermi, 'Avviso dati')}
<div id='offline' class='banner' style='display:none'></div><div id='alertbanner' class='banner' style='display:none'></div>
{stale_txt}
{page('oggi', p_oggi)}{page('indici', p_indici)}{page('regime', p_regime)}{page('valutazioni', p_val)}{page('aziende', p_az)}{page('macro', p_macro)}{page('grafici', p_graf)}{page('previsioni', p_prev)}{page('fiducia', p_fid)}{page('contesto', p_ctx)}
{page('portafoglio', p_pf)}{page('storico', p_sto)}{page('archivio', p_arc)}{page('notizie', p_nz)}{page('mercati', p_md)}{page('saldi', p_sd)}{page('opportunita', p_op)}{page('allarmi', p_al)}
{dock}{semafori.lista_html(sem) if sem else ''}
<script>window.TICKER={json.dumps(cruscotto.ticker_items(newsmod.load_latest(), soon, aix), ensure_ascii=False)};</script>{cruscotto.TICKER_JS}
<footer>Armor non è consulenza finanziaria. Le stime sono probabilità basate sul passato e possono essere sbagliate. Nessun modello prevede con certezza. Prezzi con ritardo di circa 15 minuti.</footer>
<script>window.HELP={json.dumps(help_all, ensure_ascii=False)};window.LABELS={json.dumps(labels_all, ensure_ascii=False)};</script>
{parts.MODAL}
{livefeed.JS}{infobox.JS}{semafori.OGGI_JS}{archivio_dati.JS}{dock_js}{forza.JS}{semafori.LISTA_JS}{'' if lazy else '<script>' + insight.EP_JS + '</script><script>' + parts.AL_JS + '</script>' + ui.PAC_JS}{tabs_js}
"""
    out.write_text(TEMPLATE.replace("{{JS}}", parts.JS if lazy else parts.JS_FULL).replace("{{BODY}}", body), encoding="utf-8")
    if lazy:
        pd_ = out.parent / "pages"
        pd_.mkdir(exist_ok=True)
        for k, h in lazy_pages.items():
            (pd_ / f"{k}.html").write_text(h, encoding="utf-8")
        print("Pagine caricate a richiesta:", ", ".join(sorted(lazy_pages)))
    print("Cruscotto creato:", out)


TEMPLATE = """<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Armor - rischio cali VWCE</title><meta name='theme-color' content='#0e1a3a'><link rel='manifest' href='manifest.webmanifest'><link rel='icon' href='favicon.png'><link rel='apple-touch-icon' href='apple-touch-icon.png'><meta name='apple-mobile-web-app-capable' content='yes'><meta name='mobile-web-app-capable' content='yes'><style>
:root{--bg:#f4f6f9;--card:#fff;--tx:#1b2330;--mu:#667085;--bd:#e3e8ef;--ok:#1f8f55;--warn:#c77d0a;--bad:#c0392b;--ac:#2a6fdb;--okbg:#e7f5ee;--warnbg:#fdf3e1;--badbg:#fbe9e7}
@media(prefers-color-scheme:dark){:root{--bg:#0e131b;--card:#161d28;--tx:#e8edf5;--mu:#93a0b4;--bd:#263040;--ok:#4cc38a;--warn:#f0b54a;--bad:#ff7a6b;--ac:#6ea4ff;--okbg:#12301f;--warnbg:#3a2c10;--badbg:#3d1a16}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;padding:16px;max-width:1200px;margin:auto}
header{display:flex;justify-content:space-between;margin-bottom:12px}h1{margin:0;font-size:28px;letter-spacing:.5px}h2{font-size:18px;margin:26px 0 10px}h3{margin:0 0 8px;font-size:16px}
.muted{color:var(--mu);font-size:13px}.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px;overflow-x:auto}
.hero{border-radius:16px;padding:22px;border:1px solid var(--bd)}.hero.ok{background:var(--okbg)}.hero.warn{background:var(--warnbg)}.hero.bad{background:var(--badbg)}
.hchip .l.up{color:var(--ok)}.hchip .l.mo{font-size:11px;color:var(--mu)}
.hl1{font-size:34px;font-weight:700}.hero.ok .hl1{color:var(--ok)}.hero.warn .hl1{color:var(--warn)}.hero.bad .hl1{color:var(--bad)}.hl2{margin-top:4px;font-size:16px}.hl3.stress{color:var(--bad);font-weight:600}.hl3,.hl4{margin-top:6px;color:var(--mu);font-size:13px}
.grid4{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-top:12px}
.hzh{display:flex;justify-content:space-between;align-items:center}.ratio{font-size:13px;color:var(--mu);margin-bottom:8px}
.prow{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:6px 0;border-top:1px solid var(--bd)}.prow b{font-size:20px}.prow .muted{grid-column:1/3;margin-top:-4px}
.hyp{margin-top:8px;padding:8px;border-radius:10px;background:var(--bg);display:grid;gap:2px}.hyp .lab{font-size:12px;color:var(--mu)}.hyp b{font-size:20px}.drv{margin-top:8px;font-size:13px;color:var(--mu)}.relrow{margin-top:10px}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600}.badge.ok{background:var(--okbg);color:var(--ok)}.badge.warn{background:var(--warnbg);color:var(--warn)}.badge.bad{background:var(--badbg);color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:7px 8px;border-bottom:1px solid var(--bd);text-align:right}th:first-child,td:first-child{text-align:left}thead th{font-size:12px;color:var(--mu);font-weight:600}
tr.grp td{background:var(--bg);font-weight:700;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mu)}td.worse{color:var(--bad);font-weight:600}td small{display:block;font-size:11px;font-weight:600}small.worse{color:var(--bad)}small.better{color:var(--ok)}tr.act td{background:var(--warnbg)}
.scroll{overflow-x:auto}.chart{width:100%;height:auto}.grid{stroke:var(--bd);stroke-width:1}.hl{stroke:var(--mu);stroke-dasharray:4 4}.ax{fill:var(--mu);font-size:11px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mu)}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.banner{background:var(--badbg);color:var(--bad);padding:10px 14px;border-radius:10px;margin-bottom:12px;font-weight:600}footer{margin:26px 0 8px;color:var(--mu);font-size:12px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.tab{border:1px solid var(--bd);background:var(--card);color:var(--tx);padding:6px 14px;border-radius:99px;font:inherit;cursor:pointer}.tab.on{background:var(--ac);color:#fff;border-color:var(--ac)}
details{margin-top:10px}summary{cursor:pointer;color:var(--ac)}h3{margin-top:16px}
@media(max-width:600px){body{padding:10px}.hl1{font-size:28px}}

html{scroll-behavior:smooth;scroll-padding-top:56px}body{font-size:16px;line-height:1.55}
.nav{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;padding:8px 0;background:var(--bg);margin:0 -2px 8px;-webkit-overflow-scrolling:touch}
.nav a{white-space:nowrap;padding:8px 14px;border:1px solid var(--bd);border-radius:99px;background:var(--card);color:var(--tx);text-decoration:none;font-size:14px;font-weight:600}
.livebar{margin-bottom:12px}.lqrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.lq{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:12px 14px}.lq.big1{grid-column:span 2;border-color:var(--ac)}
.explain{background:var(--card);border:1px solid var(--bd);border-left:4px solid var(--ac);border-radius:12px;padding:2px 16px;margin:8px 0 12px;font-size:14px}.explain p{margin:10px 0}.ihelp{font-size:12px;color:var(--mu);font-weight:400;margin-top:2px;max-width:420px;line-height:1.35}.lqt{font-size:12px;margin-top:2px}.lqh{font-size:12px;margin-top:6px;line-height:1.35}.lqn{font-size:13px;color:var(--mu);font-weight:600}.lqp{font-size:26px;font-weight:700;letter-spacing:-.3px}.big1 .lqp{font-size:36px}.lqc{font-size:14px;font-weight:600}
.up,.okc{color:var(--ok)}.dn{color:var(--bad)}#liveinfo{margin-top:6px}.lvd{color:var(--ok);font-size:11px;font-weight:700;white-space:nowrap}
.hlk{font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--mu);font-weight:700}
ul.simple{margin:12px 0 4px;padding-left:20px}ul.simple li{margin:6px 0}
.guide,details.exp{margin:12px 0}details>summary{cursor:pointer;font-weight:700;padding:10px 4px}details.exp>summary{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:12px 14px;color:var(--tx)}
details.exp[open]>summary{border-bottom-left-radius:0;border-bottom-right-radius:0}details.exp>.card{border-top-left-radius:0;border-top-right-radius:0;border-top:0}
.expl{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:6px 16px}.expl p{margin:10px 0}
.big{font-size:44px;font-weight:800;line-height:1.05}.bigl{font-size:15px;margin-top:2px}.plain{margin:8px 0;font-size:15px}
.scorebox{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;align-items:center;margin-bottom:12px}.lab{font-size:12px;color:var(--mu);text-transform:uppercase;letter-spacing:.5px}
.hz .hzh h3{font-size:19px}.hz .prow{border-top:1px solid var(--bd)}
@media(max-width:600px){.lq.big1{grid-column:span 2}.big{font-size:38px}.lqp{font-size:22px}.big1 .lqp{font-size:32px}}
"""+parts.CSS+semafori.CSS+armor_index.CSS+chiaro.CSS+extra13.CSS+mappa.MAPPA_CSS+cruscotto.CSS+confronto.CSS+aziende.CSS+ciclico.CSS+forza.CSS+semafori.LISTA_CSS+ui.CSS+archivio_dati.CSS+infobox.CSS+semafori.OGGI_CSS+novita.CSS+"""</style></head><body>{{BODY}}<script>function showHz(h){document.querySelectorAll('.hzc').forEach(e=>e.style.display=e.id==='hzc-'+h?'':'none');document.querySelectorAll('.tab').forEach(e=>e.classList.toggle('on',e.dataset.hz===h))}</script><script>
(function(){
function fmt(v,d){return v.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function paint(L){if(!L||!L.quotes)return;var now=Date.now();
function qdt(q,k){try{return new Date(q.time).toLocaleDateString('sv-SE',{timeZone:k==='vwce'?'Europe/Berlin':'America/New_York'})}catch(e){return ''}}
function dmy(x){return x.slice(8,10)+'/'+x.slice(5,7)}
function cell(lab,ref,now,dd,rel,risk){if(!ref)return '<div class="tcl"><span class="mu">n.d.</span></div>';var df=now-ref[1],pc=ref[1]?df/ref[1]*100:0,v=rel?pc:df,th=rel?1:0,bad=risk?v>0:v<0,ar=Math.abs(v)<th?'<span class="tr0">▬</span>':'<span class="'+(bad?'trb':'trg')+'">'+(v>0?'▲':'▼')+'</span>',t=(rel?(pc>=0?'+':'−')+fmt(Math.abs(pc),1)+'%':(df>=0?'+':'−')+fmt(Math.abs(df),dd));
return '<div class="tcl"><span class="mu">'+lab+' '+dmy(ref[0])+'</span> <b>'+fmt(ref[1],dd)+'</b> '+ar+' <span class="mu">('+t+')</span></div>'}
document.querySelectorAll('.lq').forEach(function(el){var k=el.dataset.k,q=L.quotes[k];if(!q)return;var d=k==='eurusd'?4:2,price=q.price,chg=q.chg,tr=el.querySelector('.trow[data-h]');
if(tr){var H;try{H=JSON.parse(tr.dataset.h)}catch(e){H=null}
if(H&&H.length){var last=H[H.length-1],qd=qdt(q,k)||last[0];
if(!q.live){var wd=new Date(qd+'T12:00:00Z').getUTCDay();if(qd>last[0]&&(wd===0||wd===6))qd=last[0];var hit=H.filter(function(x){return x[0]===qd})[0];if(hit)price=hit[1]}
var refs=H.filter(function(x){return x[0]<qd}),ie=refs[refs.length-1],lim=new Date(new Date(qd+'T12:00:00Z').getTime()-7*864e5).toISOString().slice(0,10),wk=refs.filter(function(x){return x[0]<=lim}),se=wk[wk.length-1],dd=+tr.dataset.d,rel=true,risk=tr.dataset.risk==='1';
tr.innerHTML=cell('Il',ie,price,dd,rel,risk)+cell('Il',se,price,dd,rel,risk);chg=ie?price/ie[1]-1:chg}}
el.querySelector('.lqp').textContent=fmt(price,d)+(q.ccy?' '+q.ccy:'');
if(q.live){var nn=el.querySelector('.lqn')||el.querySelector('.kt');if(nn&&!nn.querySelector('.lvd'))nn.insertAdjacentHTML('beforeend',' <span class="lvd">● in diretta</span>')}
var tt=el.querySelector('.lqt');if(tt&&q.time){var qd2=new Date(q.time);tt.textContent='Ultimo scambio: '+qd2.toLocaleString('it-IT',{weekday:'short',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})+(q.venue?' · '+q.venue:'')}
var c=el.querySelector('.lqc');if(chg!=null){var bad=k==='vix';var up=chg>=0;c.className='lqc '+((up!==bad)?'up':'dn');
c.innerHTML=(up?'▲ ':'▼ ')+fmt(Math.abs(chg)*100,2)+'% <span class="muted">'+(q.live?'in diretta':(q.open?'mercato aperto':'mercato chiuso'))+'</span>'}});
var u=new Date(L.updated),m=Math.round((now-u)/60000),la=L.liveAt,txt;
if(la&&now-la<90000){txt='In tempo reale: VWCE e S&P 500 si aggiornano ogni 15 secondi (ultimo controllo '+new Date(la).toLocaleTimeString('it-IT')+'). Gli altri prezzi, con ritardo di circa 15 minuti, ogni 15 minuti.'}
else{txt='Prezzi con ritardo di circa 15 minuti · aggiornati '+(m<1?'ora':(m===1?'1 minuto fa':(m<90?m+' minuti fa':Math.round(m/60)+' ore fa')))+' ('+u.toLocaleString('it-IT',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})+')'}
document.querySelectorAll('#liveinfo,.liveinfo').forEach(function(i){i.textContent=txt})}
paint(window.LIVE);window.armorPaint=function(){paint(window.LIVE)};
function refresh(){fetch('live.json?'+Date.now(),{cache:'no-store'}).then(function(r){return r.json()}).then(function(L){var o=window.LIVE;if(o&&o.quotes&&L.quotes){['vwce','sp500'].forEach(function(k){var a=o.quotes[k],b=L.quotes[k];if(a&&a.live&&b&&new Date(a.time)>=new Date(b.time))L.quotes[k]=a});L.liveAt=o.liveAt}window.LIVE=L;paint(L)}).catch(function(){})}
if(location.protocol.indexOf('http')===0){refresh();setInterval(refresh,300000);setInterval(function(){paint(window.LIVE)},60000)}
function off(){var b=document.getElementById('offline');if(!b)return;if(navigator.onLine){b.style.display='none'}else{b.style.display='';b.textContent='Sei offline: mostro gli ultimi dati salvati sul telefono.'}}
window.addEventListener('online',off);window.addEventListener('offline',off);off();
var loaded=Date.now();document.addEventListener('visibilitychange',function(){if(!document.hidden&&Date.now()-loaded>900000&&navigator.onLine&&location.protocol.indexOf('http')===0)location.reload()});
if('serviceWorker' in navigator&&location.protocol.indexOf('http')===0){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
</script>"""+"{{JS}}"+"""</body></html>"""
