"""Funzioni aggiuntive: calendario completo, finestra «Assistente», oggi cosa faccio, mappa mensile, divergenze, pagella,
confronto con le crisi, dati economici anticipati, liquidità della Fed, glossario."""
import calendar as _cal
import html as _h
import json
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from . import armor_index, calendario, store
from .config import DATA, OUTCOMES, JOURNAL

e = _h.escape
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
SIGLA = {"FOMC": "Fed", "CPI": "CPI", "Lavoro USA": "Lav", "Opzioni": "Opz", "Trimestrale": "Tri"}


def _p(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n.d."
    return (f"{x:+.{d}f}%" if sign else f"{x:.{d}f}%").replace(".", ",")


# ---------------------------------------------------------------- calendario
def _earn():
    try:
        return json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def all_events(start: date, end: date) -> list[dict]:
    out = []
    for s in calendario.FOMC:
        out.append({"date": s, "tipo": "FOMC", "nome": "Decisione Fed sui tassi" + (" (con previsioni)" if s in calendario.FOMC_SEP else ""), "peso": 3})
    for s in calendario.CPI:
        out.append({"date": s, "tipo": "CPI", "nome": "Inflazione USA (CPI)", "peso": 3})
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append({"date": calendario._nth_friday(y, m, 1).isoformat(), "tipo": "Lavoro USA", "nome": "Rapporto lavoro USA (di norma)", "peso": 3})
        t = calendario._nth_friday(y, m, 3)
        quad = m in (3, 6, 9, 12)
        out.append({"date": t.isoformat(), "tipo": "Opzioni", "nome": "Scadenza trimestrale opzioni/futures" if quad else "Scadenza mensile opzioni", "peso": 2 if quad else 1})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    out += _earn()
    return sorted([x for x in out if start.isoformat() <= x["date"] <= end.isoformat()], key=lambda x: (x["date"], -x["peso"]))


def _last(key):
    s = store.load(key)
    return s.dropna() if len(s) else s


def _last_data(tipo: str) -> str:
    try:
        if tipo == "CPI":
            c = _last("cpi")
            if len(c) > 13:
                return f"inflazione a/a ultima: <b>{_p((c.iloc[-1] / c.iloc[-13] - 1) * 100)}</b>"
        if tipo == "Lavoro USA":
            u = _last("unrate")
            if len(u):
                return f"disoccupazione ultima: <b>{_p(float(u.iloc[-1]))}</b>"
        if tipo == "FOMC":
            f = _last("fedfunds")
            if len(f):
                return f"tasso effettivo Fed: <b>{_p(float(f.iloc[-1]), 2)}</b>"
    except Exception:  # noqa: BLE001
        pass
    return "—"


def calendar_html(today: date, sp: pd.Series, vix: pd.Series) -> str:
    sp = sp.dropna()
    ret = sp.pct_change() * 100
    vlast = float(vix.iloc[-1]) if len(vix) else None
    evs = all_events(today - timedelta(days=75), today + timedelta(days=75))
    by = {}
    for x in evs:
        by.setdefault(x["date"], []).append(x)
    months = []
    for k in (-1, 0, 1):
        mm = today.month - 1 + k
        y, m = today.year + mm // 12, mm % 12 + 1
        cells = ""
        for wk in _cal.Calendar(0).monthdates(y, m) if False else _cal.Calendar(0).monthdatescalendar(y, m):
            for d in wk:
                if d.month != m:
                    cells += "<div class='cd o'></div>"
                    continue
                iso = d.isoformat()
                r = ret.get(pd.Timestamp(d)) if pd.Timestamp(d) in ret.index else None
                bg = ""
                rtxt = ""
                if r is not None and not np.isnan(r):
                    a = min(abs(r) / 2.5, 1) * 0.55 + 0.08
                    bg = f"style='background:rgba({'31,143,85' if r >= 0 else '192,57,43'},{a:.2f})'"
                    rtxt = f"<small>{r:+.1f}%</small>".replace(".", ",")
                ev = "".join(f"<em class='ev w{x['peso']}'>{SIGLA.get(x['tipo'], x['tipo'][:3])}</em>" for x in by.get(iso, []) if x["peso"] >= 2 or x["tipo"] == "Opzioni")
                cells += f"<div class='cd{' today' if d == today else ''}' {bg}><b>{d.day}</b>{rtxt}{ev}</div>"
        months.append(f"<div class='cmon' style='{'' if k == 0 else 'display:none'}'><div class='cmh'><button class='btn cprev'>‹</button><b>{MESI[m - 1].capitalize()} {y}</b><button class='btn cnext'>›</button></div>"
                      "<div class='cdg'>" + "".join(f"<div class='cw'>{d}</div>" for d in ["L", "M", "M", "G", "V", "S", "D"]) + cells + "</div></div>")
    up = [x for x in evs if x["date"] >= today.isoformat() and x["peso"] >= 2][:12]
    exp = f"±{vlast / 15.87:.1f}%".replace(".", ",") if vlast else "n.d."
    rows = ""
    for x in up:
        d = datetime.fromisoformat(x["date"]).date()
        g = (d - today).days
        q = "oggi" if g == 0 else ("domani" if g == 1 else f"tra {g} giorni")
        rows += (f"<tr class='{'hi' if x['peso'] >= 3 else ''}'><td>{d.strftime('%d/%m')}<div class='mu'>{q}</div></td><td><b>{e(x['nome'])}</b><div class='mu'>{e(calendario.HELP.get(x['tipo'], ''))}</div></td>"
                 f"<td>{_last_data(x['tipo'])}</td><td>{exp if x['peso'] >= 3 else '—'}</td></tr>")
    past = [x for x in evs if x["date"] < today.isoformat() and x["peso"] >= 3][-8:][::-1]
    prow = ""
    for x in past:
        t = pd.Timestamp(x["date"])
        if t not in ret.index:
            continue
        prev_v = vix[vix.index < t]
        exp_p = float(prev_v.iloc[-1]) / 15.87 if len(prev_v) else None
        r = float(ret.loc[t])
        if exp_p:
            q = abs(r) / exp_p
            jd = "più forte del previsto" if q > 1.3 else ("più calmo del previsto" if q < 0.6 else "in linea")
            cls = "dn" if q > 1.3 else ""
        else:
            jd, cls = "—", ""
        prow += (f"<tr><td>{t.strftime('%d/%m')}</td><td>{e(x['nome'])}</td><td>{('±' + _p(exp_p)) if exp_p else 'n.d.'}</td>"
                 f"<td class='{'up' if r >= 0 else 'dn'}'><b>{_p(r, 1, True)}</b></td><td class='{cls}'>{jd}</td></tr>")
    return ("<h3 style='margin-top:0'>Calendario degli eventi</h3>"
            "<div class='explain'><p>Ogni giorno passato è colorato in base a quanto ha mosso l'S&amp;P 500 (verde = salito, rosso = sceso). Le sigle sono gli eventi: Fed = tassi, CPI = inflazione, Lav = lavoro USA, Opz = scadenza opzioni, Tri = trimestrale.</p></div>"
            f"<div class='calm'>{''.join(months)}</div>"
            "<h4>Prossimi eventi: ultimo dato reale e oscillazione attesa</h4>"
            f"<div class='scroll'><table class='cal'><tr><th>Data</th><th>Evento</th><th>Ultimo dato reale</th><th>Oscillazione attesa dell'S&amp;P (dal VIX)</th></tr>{rows}</table></div>"
            "<h4>Eventi passati: movimento previsto e reale</h4>"
            f"<div class='scroll'><table class='cal'><tr><th>Data</th><th>Evento</th><th>Previsto (dal VIX)</th><th>Reale S&amp;P 500</th><th>Esito</th></tr>{prow or '<tr><td colspan=5 class=mu>Nessun dato.</td></tr>'}</table></div>"
            "<p class='mu'>«Previsto» = oscillazione giornaliera che il mercato si aspettava la sera prima, ricavata dal VIX (VIX ÷ 15,9). Le previsioni degli economisti sui singoli dati (consenso) non sono disponibili gratuitamente, per questo non sono mostrate. "
            "Le date di lavoro USA e opzioni seguono la regola del calendario e possono spostarsi di un giorno.</p>")


# ---------------------------------------------------------------- oggi cosa faccio
def divergence(sp: pd.Series, aix: dict | None) -> dict | None:
    try:
        from .features import fwd_maxdd, price_features
        G = aix["G"].dropna(how="all")
        f = price_features(sp)["dd252"].reindex(G.index)
        near = f > -0.03
        d = G.diff(63)
        conds = {"Credito e liquidità": "il credito si sta irrigidendo", "Sentimento e ampiezza": "meno titoli sostengono il rialzo / sentimento in peggioramento",
                 "Paura e stress dei mercati": "la paura (VIX, opzioni) sale mentre i prezzi tengono", "Economia reale": "i dati sul lavoro peggiorano"}
        flags = {g: (d[g] >= 0.08) for g in conds if g in d}
        cnt = sum(v.astype(int) for v in flags.values())
        now_near = bool(near.iloc[-1])
        now = [conds[g] for g, v in flags.items() if bool(v.iloc[-1])]
        mask = near & (cnt >= 2)
        dd = fwd_maxdd(sp, 63).reindex(G.index)
        ok = dd.notna()
        n = int((mask & ok).sum())
        hist = float((dd[mask & ok] <= -0.10).mean()) if n >= 60 else None
        base = float((dd[ok] <= -0.10).mean())
        return {"near": now_near, "now": now, "active": now_near and len(now) >= 2, "n": n, "hist": hist, "base": base, "dd": float(f.iloc[-1])}
    except Exception:  # noqa: BLE001
        return None


def divergence_html(d: dict | None) -> str:
    if not d:
        return ""
    if d["active"]:
        h = f" In passato, quando è successo, un calo ≥10% nei 3 mesi dopo c'è stato nel <b>{_p(d['hist'] * 100, 0)}</b> dei casi (normale {_p(d['base'] * 100, 0)})." if d["hist"] is not None else ""
        return ("<div class='banner'><b>Allarme divergenza:</b> i prezzi sono vicini ai massimi ma " + "; ".join(d["now"]) + "." + h + " Non dice quando, dice che il rialzo è meno solido di quanto sembri.</div>")
    if d["near"] and d["now"]:
        return f"<div class='card'><b>Divergenza lieve:</b> prezzi vicini ai massimi e un segnale che peggiora ({e(d['now'][0])}). Un solo segnale non basta per l'allarme.</div>"
    return ""


def oggi_html(aix, div, evs_soon, sig_n) -> str:
    v = aix["value"] if aix else None
    bandn = armor_index.band(v)[0] if v else None
    if v is None:
        head, why = "Oggi: non fare nulla di particolare.", "Mancano dati per un giudizio completo; con un PAC la regola resta continuare con regolarità."
        cls = "ok"
    elif v < 60:
        head, why, cls = "Oggi: non fare nulla. Continua il tuo PAC.", f"Il rischio è {bandn} (Indice Armor {v:.0f}/100): nessun motivo per cambiare piano.", "ok"
    elif v < 80:
        head, why, cls = "Oggi: non fare nulla, ma niente decisioni d'impulso.", f"Il rischio è {bandn} (Indice Armor {v:.0f}/100): il PAC serve proprio nei periodi nervosi. Evita di vendere o di fermare tutto per paura.", "warn"
    else:
        head, why, cls = "Oggi: resta fermo. Non vendere per paura.", f"Il rischio è {bandn} (Indice Armor {v:.0f}/100). Nei momenti peggiori le vendite d'impulso sono l'errore più costoso: il PAC continua come previsto.", "bad"
    extra = ""
    if evs_soon:
        extra += f"<li>Evento in arrivo: <b>{e(evs_soon[0]['nome'])}</b> ({datetime.fromisoformat(evs_soon[0]['date']).strftime('%d/%m')}). Nei giorni degli eventi i prezzi oscillano di più: non reagire d'istinto.</li>"
    if div and div["active"]:
        extra += "<li>C'è una divergenza (prezzi alti, segnali interni in peggioramento): è un motivo per guardare l'app con più attenzione, non per cambiare piano.</li>"
    if sig_n:
        extra += f"<li>{sig_n} indicatori sono in zona di prudenza: è il clima, non una previsione.</li>"
    return (f"<div class='todo {cls}'><div class='hlk'>Oggi cosa faccio?</div><div class='td1'>{head}</div><div>{e(why)}</div>"
            f"{('<ul>' + extra + '</ul>') if extra else ''}<div class='mu'>Valido per chi investe a rate costanti (PAC) con orizzonte di anni. Non è consulenza finanziaria.</div></div>")


# ---------------------------------------------------------------- mappa mensile
def heatmap_html(aix: dict | None, months: int = 24) -> str:
    if not aix:
        return "<p class='mu'>Mappa non disponibile.</p>"
    G = aix["G"].copy()
    G["Indice Armor"] = (aix["hist"] - 1) / 99
    G = G[G.index >= G.index[-1] - pd.DateOffset(months=months)]
    M = G.resample("ME").mean().dropna(how="all")
    rows = ""
    order = ["Indice Armor"] + [c for c in aix["G"].columns]
    head = "<th></th>" + "".join(f"<th>{MESI[d.month - 1][:3]}<br><small>{str(d.year)[2:]}</small></th>" for d in M.index)
    for g in order:
        cells = ""
        for d in M.index:
            x = M.loc[d, g]
            if pd.isna(x):
                cells += "<td class='hm'></td>"
                continue
            sc = (x - 0.10) / 0.75 if g != "Indice Armor" else x
            sc = min(max(sc, 0), 1)
            cells += f"<td class='hm' style='background:{armor_index.color(1 + 99 * sc)}' title='{e(g)}: {1 + 99 * sc:.0f}'>{1 + 99 * sc:.0f}</td>"
        rows += f"<tr><th class='hr'>{e(g)}</th>{cells}</tr>"
    return ("<div class='explain'><p>Ogni riga è una famiglia di indicatori, ogni colonna un mese. <b>Verde = calma, rosso = rischio</b>. Serve a vedere da quando una tensione si sta formando e quali famiglie la guidano.</p></div>"
            f"<div class='scroll'><table class='hmt'><tr>{head}</tr>{rows}</table></div>")


# ---------------------------------------------------------------- pagella mensile
def pagella_html(today: date | None = None) -> str:
    today = today or date.today()
    try:
        j = pd.read_csv(JOURNAL)
        o = pd.read_csv(OUTCOMES)
    except Exception:  # noqa: BLE001
        return "<p class='mu'>La pagella compare quando ci sono previsioni scadute da valutare.</p>"
    if o.empty:
        return "<p class='mu'>Ancora nessuna previsione è scaduta: la prima pagella compare dopo la prima scadenza.</p>"
    d = o.merge(j[["asof", "horizon", "p1", "base1", "thr1"]], on=["asof", "horizon"], how="left")
    d["target"] = pd.to_datetime(d["target_date"])
    first = date(today.year, today.month, 1)
    pm_end = first - timedelta(days=1)
    pm_start = date(pm_end.year, pm_end.month, 1)
    mth = d[(d["target"] >= pd.Timestamp(pm_start)) & (d["target"] <= pd.Timestamp(pm_end))]
    label = f"{MESI[pm_start.month - 1]} {pm_start.year}"
    if mth.empty:
        mth = d[d["target"] >= pd.Timestamp(today - timedelta(days=30))]
        label = "ultimi 30 giorni"
    if mth.empty:
        return "<p class='mu'>Nessuna previsione scaduta nell'ultimo mese.</p>"
    hit = mth["hit1"].astype(str).str.lower().isin(["true", "1", "1.0"]).astype(float)
    ok = mth["p1"].notna()
    n = len(mth)
    brier = float(((mth.loc[ok, "p1"] - hit[ok]) ** 2).mean()) if ok.any() else None
    brier_b = float(((mth.loc[ok, "base1"] - hit[ok]) ** 2).mean()) if ok.any() else None
    inr = mth["in_range"].astype(str).str.lower().isin(["true", "1", "1.0"]).mean()
    right = int(((mth["p1"] < 0.5) & (hit == 0)).sum() + ((mth["p1"] >= 0.5) & (hit == 1)).sum())
    ev = int(hit.sum())
    better = (brier is not None and brier_b is not None and brier <= brier_b)
    learn = ""
    try:
        im = pd.read_csv(DATA / "improvement.csv")
        last = im.iloc[-1]
        learn = (f"Nel test mensile il modello in uso ha ottenuto {last['score']:.2f} su {int(last['tested'])} prove; " +
                 ("è stato sostituito da uno migliore." if str(last.get("promoted")).lower() in ("true", "1") else "è rimasto il migliore tra le alternative provate."))
    except Exception:  # noqa: BLE001
        pass
    return (f"<div class='card'><h3 style='margin-top:0'>Pagella di {e(label)}</h3>"
            f"<div class='grid2'><div class='kc'><div class='k'>Previsioni scadute</div><div class='v'>{n}</div><div class='s'>{ev} con un calo che si è davvero verificato</div></div>"
            f"<div class='kc {'ok' if better else 'wa'}'><div class='k'>Armor contro la media storica</div><div class='v'>{'meglio' if better else 'peggio'}</div>"
            f"<div class='s'>errore {('%.3f' % brier).replace('.', ',') if brier is not None else 'n.d.'} contro {('%.3f' % brier_b).replace('.', ',') if brier_b is not None else 'n.d.'} (più basso = meglio)</div></div></div>"
            f"<p>In <b>{right} casi su {n}</b> la previsione è stata giusta (probabilità sotto 50% e nessun calo, oppure sopra 50% e calo). "
            f"Il rendimento reale è caduto nella fascia prevista nel <b>{_p(float(inr) * 100, 0)}</b> dei casi (attesi circa 80%).</p>"
            f"<p class='mu'>{e(learn)} Con pochi casi la pagella è solo indicativa.</p></div>")


# ---------------------------------------------------------------- confronto con le crisi
CRISES = [("Bolla internet 2000", "2000-03-24"), ("Crisi finanziaria 2008", "2007-10-09"), ("Covid 2020", "2020-02-19"), ("Rialzo dei tassi 2022", "2022-01-03")]


def crisi_html(aix: dict | None, sp: pd.Series) -> str:
    if not aix:
        return "<p class='mu'>Confronto non disponibile.</p>"
    idx, G = aix["hist"], aix["G"]
    rows = ""
    now_vec = G.iloc[-1]
    sims = []
    for name, d in CRISES:
        t = pd.Timestamp(d)
        i0 = idx[:t]
        if i0.empty:
            continue
        v0 = float(i0.iloc[-1])
        seg = sp[(sp.index >= t) & (sp.index <= t + pd.Timedelta(days=500))]
        trough = float(seg.min() / seg.iloc[0] - 1)
        tdate = seg.idxmin()
        vmax = float(idx[(idx.index >= t) & (idx.index <= tdate)].max())
        vix = _last("vix")
        vx = float(vix[:t].iloc[-1]) if len(vix[:t]) else None
        vec = G[:t].iloc[-1]
        both = [g for g in G.columns if pd.notna(vec[g]) and pd.notna(now_vec[g])]
        dist = float(np.sqrt(np.mean([(vec[g] - now_vec[g]) ** 2 for g in both]))) if len(both) >= 4 else None
        sims.append((dist, name))
        rows += (f"<tr><td><b>{e(name)}</b><div class='mu'>prima del calo: {t.strftime('%m/%Y')}</div></td><td>{v0:.0f}</td><td>{_p(vx, 0).replace('%', '') if vx else 'n.d.'}</td>"
                 f"<td class='dn'>{_p(trough * 100, 0)}</td><td>{vmax:.0f}</td></tr>")
    vnow = float(idx.iloc[-1])
    vixn = _last("vix")
    rows += (f"<tr class='hi'><td><b>Oggi</b></td><td><b>{vnow:.0f}</b></td><td>{_p(float(vixn.iloc[-1]), 0).replace('%', '') if len(vixn) else 'n.d.'}</td><td>—</td><td>—</td></tr>")
    sims = [s for s in sims if s[0] is not None]
    near = min(sims)[1] if sims else None
    txt = (f"<p>Per profilo di indicatori, oggi somiglia di più a: <b>{e(near)}</b> (somiglianza solo relativa).</p>" if near else "")
    return ("<div class='explain'><p>Quanto valeva l'Indice Armor poco prima delle quattro grandi crisi, quanto è sceso poi l'S&amp;P 500 (entro circa 16 mesi) e quanto è arrivato a valere l'indice durante la discesa. "
            "Serve a capire se oggi il livello di rischio somiglia a quello dei momenti peggiori.</p></div>"
            f"<div class='scroll'><table><tr><th>Crisi</th><th>Indice prima</th><th>VIX prima</th><th>Calo massimo dell'S&amp;P</th><th>Indice al picco</th></tr>{rows}</table></div>{txt}"
            "<p class='mu'>Ogni crisi ha avuto cause diverse (bolla, banche, pandemia, tassi): il confronto indica il clima, non prevede il prossimo evento.</p>")


# ---------------------------------------------------------------- dati economici anticipati e Fed
EARLY = [
    ("umcsent", "Fiducia dei consumatori (Michigan)", "level", (75, 60), "Sotto 75 i consumatori sono preoccupati, sotto 60 è un livello da recessione. Anticipa i consumi, che sono circa il 70% dell'economia USA.", 1),
    ("philly", "Indice manifatturiero Philadelphia (tipo PMI)", "level", (0, -10), "Sopra 0 l'industria della zona cresce, sotto 0 si contrae. È un'alternativa gratuita al PMI.", 1),
    ("empire", "Indice manifatturiero New York (tipo PMI)", "level", (0, -10), "Come sopra, per lo stato di New York. Sotto 0 = contrazione.", 1),
    ("dgorder", "Ordini di beni durevoli", "mom", (0, -3), "Ordini di beni come macchine e auto. Un calo mensile indica imprese che frenano gli investimenti.", 0),
    ("neworder", "Ordini industriali: beni d'investimento (escl. aerei)", "mom", (0, -3), "Ordini di macchinari delle imprese: anticipa gli investimenti e la produzione.", 0),
    ("indpro", "Produzione industriale", "yoy", (0, -2), "Variazione sull'anno della produzione di fabbriche e miniere. Sotto 0 = industria in calo.", 1),
    ("payems", "Nuovi posti di lavoro (variazione mensile, migliaia)", "diff", (100, 0), "Sotto 100 mila al mese il mercato del lavoro rallenta, sotto 0 perde posti.", 0),
    ("retail", "Vendite al dettaglio", "mom", (0, -1), "Quanto spendono i consumatori: un calo mensile segnala domanda debole.", 1),
]
FED = [("walcl", "Bilancio della Fed (miliardi $)"), ("wresbal", "Riserve delle banche presso la Fed (miliardi $)"), ("rrp", "Reverse repo (miliardi $)"), ("tga", "Conto del Tesoro presso la Fed (miliardi $)")]
EXTRA_KEYS = {k: n for k, n, *_ in EARLY} | {k: n for k, n in FED} | {"fedfunds": "Tasso effettivo Fed (%)", "net_liq": "Liquidità netta della Fed (miliardi $)"}


def _bn(s: pd.Series) -> pd.Series:
    return s / 1000 if len(s) and float(s.dropna().abs().median()) > 1e5 else s


def early_html() -> str:
    cards = ""
    n_ok = n_all = 0
    for key, name, kind, (a, b), txt, dec in EARLY:
        s = _last(key)
        if len(s) < 3:
            cards += (f"<div class='sem na'><div class='sh'><span class='dot'></span><span class='sn'>{e(name)}</span><span class='st'>in arrivo</span></div>"
                      f"<div class='sr'>Dato non ancora scaricato: compare dopo il prossimo aggiornamento giornaliero riuscito.</div></div>")
            continue
        last = float(s.iloc[-1])
        if kind == "level":
            val, shown = last, f"{last:.{dec}f}"
        elif kind == "mom":
            val = (last / float(s.iloc[-2]) - 1) * 100
            shown = _p(val, 1, True)
        elif kind == "yoy":
            val = (last / float(s.iloc[-13]) - 1) * 100 if len(s) > 13 else float("nan")
            shown = _p(val, 1, True)
        else:
            val = last - float(s.iloc[-2])
            shown = f"{val:+.0f}"
        shown = shown.replace(".", ",")
        light = "na" if np.isnan(val) else ("ok" if val > a else ("wa" if val > b else "ba"))
        n_all += 1
        n_ok += light == "ok"
        trend = ""
        if len(s) > 4:
            prev = float(s.iloc[-4])
            trend = " · in miglioramento" if last > prev * (1.01 if prev > 0 else 0.99) else (" · in peggioramento" if last < prev else "")
        cards += (f"<div class='sem {light}' data-chart='{key}'><div class='sh'><span class='dot'></span><span class='sn'>{e(name)}</span>"
                  f"<span class='st'>{ {'ok': 'Solido', 'wa': 'Attenzione', 'ba': 'Debole', 'na': ''}[light] }</span></div><div class='sv'>{shown}</div>"
                  f"<div class='sr'>{e(txt)}</div><div class='mu'>dato del {s.index[-1].strftime('%d/%m/%Y')}{trend}</div></div>")
    head = f"<div class='sumline'><span class='badge {'ok' if n_all and n_ok / n_all > .6 else 'warn'}'>{n_ok} dati solidi su {n_all} disponibili</span></div>" if n_all else ""
    return ("<div class='explain'><p>Sono i dati che di solito <b>cambiano prima</b> dei prezzi: fiducia, ordini, produzione, lavoro. Verde = economia solida, giallo = attenzione, rosso = debole. "
            "Un dato debole da solo non basta: conta se più dati peggiorano insieme.</p></div>" + head + f"<div class='semgrid'>{cards}</div>")


def fed_html() -> str:
    ser = {k: _bn(_last(k)) for k, _ in FED}
    ff = _last("fedfunds")
    cards = ""
    for k, name in FED:
        s = ser[k]
        if len(s) < 20:
            cards += f"<div class='sem na'><div class='sh'><span class='dot'></span><span class='sn'>{e(name)}</span><span class='st'>in arrivo</span></div><div class='sr'>Dato non ancora scaricato.</div></div>"
            continue
        last = float(s.iloc[-1])
        ch = (last / float(s.iloc[-14]) - 1) * 100 if len(s) > 14 and float(s.iloc[-14]) else float("nan")
        if k == "rrp" or k == "tga":
            light = "na"
        else:
            light = "ok" if ch > 1 else ("wa" if ch > -3 else "ba")
        note = {"walcl": "Quando la Fed compra titoli il bilancio cresce e immette soldi nei mercati; quando lo riduce li toglie.",
                "wresbal": "Soldi che le banche tengono alla Fed. Se scendono molto, le banche hanno meno margine e il credito si può irrigidire.",
                "rrp": "Soldi parcheggiati alla Fed dai fondi monetari. Se calano, quei soldi tornano al mercato.",
                "tga": "Il «conto corrente» dello Stato USA. Quando sale, assorbe liquidità dal mercato."}[k]
        cards += (f"<div class='sem {light}' data-chart='{k}'><div class='sh'><span class='dot'></span><span class='sn'>{e(name)}</span></div>"
                  f"<div class='sv'>{last:,.0f}</div><div class='sr'>{note}</div><div class='mu'>3 mesi: {_p(ch, 1, True)} · dato del {s.index[-1].strftime('%d/%m/%Y')}</div></div>".replace(",", "."))
    net_txt = ""
    try:
        w, t, r = ser["walcl"], ser["tga"], ser["rrp"]
        if len(w) > 20 and len(t) > 20 and len(r) > 20:
            idx = w.index
            net = (w - t.reindex(idx, method="ffill") - r.reindex(idx, method="ffill")).dropna()
            if len(net) > 14:
                ch = (float(net.iloc[-1]) / float(net.iloc[-14]) - 1) * 100
                verdict = "sta crescendo: è un sostegno ai mercati" if ch > 1 else ("è stabile" if ch > -3 else "si sta riducendo: è un freno per i mercati")
                net_txt = (f"<div class='card'><b>Liquidità netta stimata della Fed:</b> circa {float(net.iloc[-1]):,.0f} miliardi $, in 3 mesi {_p(ch, 1, True)}: {verdict}. "
                           "(bilancio − conto del Tesoro − reverse repo)</div>").replace(",", ".")
    except Exception:  # noqa: BLE001
        pass
    band = ""
    if len(ff):
        v = float(ff.iloc[-1])
        lo = round((v - 0.08) * 4) / 4
        band = (f"<div class='card'><b>Tassi della Fed:</b> tasso effettivo <b>{v:.2f}%</b> (fascia obiettivo circa {lo:.2f}–{lo + 0.25:.2f}%). ").replace(".", ",")
        band += "Tassi alti = denaro più caro: pesano sulle azioni care. L'effetto dei tassi arriva con mesi di ritardo.</div>"
    return ("<div class='explain'><p>La <b>liquidità</b> è la quantità di denaro che circola nei mercati. Quando la Fed la riduce, di solito i mercati faticano; quando la aumenta, li sostiene. "
            "Verde = liquidità in crescita, rosso = in forte calo.</p></div>" + band + net_txt + f"<div class='semgrid'>{cards}</div>")


# ---------------------------------------------------------------- glossario
GLOSS = [
    ("PAC", "Piano di accumulo: investi una cifra fissa ogni mese, qualunque sia il prezzo.", "Metti 200 € al mese nel VWCE: quando il prezzo scende compri più quote, quando sale ne compri meno."),
    ("VWCE", "ETF che replica circa 3.700 aziende di tutto il mondo.", "Con una sola quota possiedi un pezzettino di Apple, Nestlé, Toyota e migliaia di altre."),
    ("Drawdown (calo dal massimo)", "Di quanto il prezzo è sceso rispetto al suo massimo precedente.", "Il prezzo massimo era 100, oggi 85: il drawdown è −15%."),
    ("VIX", "Indice della paura: la volatilità che gli operatori si aspettano per il mese prossimo sull'S&P 500.", "VIX a 15 = mercato tranquillo; VIX a 35 = molta paura."),
    ("Volatilità", "Quanto i prezzi oscillano. Più è alta, più sono grandi i saliscendi.", "Volatilità 20% annua = un giorno tipico muove l'indice di circa 1,3%."),
    ("Put e Call", "Opzioni: la put guadagna se il prezzo scende (serve a proteggersi), la call se sale.", "Molte put comprate = molti si stanno proteggendo."),
    ("Put/Call ratio", "Rapporto tra put e call scambiate. Alto = più protezioni o scommesse al ribasso.", "Rapporto 1,3 significa 13 put ogni 10 call."),
    ("P/E", "Prezzo diviso utili annui: quanto paghi per 1 € di profitto.", "P/E 25: paghi 25 € per ogni euro di utile annuo."),
    ("P/S", "Prezzo diviso ricavi: quanto paghi per 1 € di vendite.", "P/S 3: paghi 3 € per ogni euro di fatturato."),
    ("CAPE", "P/E calcolato sugli utili medi di 10 anni, corretti per l'inflazione (Shiller).", "CAPE 38: i prezzi sono molto alti rispetto agli utili di lungo periodo."),
    ("Capitalizzazione", "Valore in borsa di un'azienda: prezzo × numero di azioni.", "Se un'azienda ha 1 miliardo di azioni a 50 €, capitalizza 50 miliardi."),
    ("Spread high yield", "Interesse extra che pagano le aziende più rischiose rispetto allo Stato.", "Se sale da 3% a 7%, gli investitori temono fallimenti."),
    ("Curva dei tassi invertita", "I tassi a breve superano quelli a lungo: in passato ha spesso preceduto recessioni.", "10Y−3M sotto zero."),
    ("NFCI", "Indice della Fed di Chicago sulle condizioni del credito. Sopra 0 = credito più difficile del normale.", "−0,5 = credito molto facile."),
    ("Liquidità", "Quanto denaro circola nei mercati. Più liquidità tende a sostenere i prezzi.", "Se la Fed riduce il bilancio, la liquidità cala."),
    ("Percentile storico", "Posizione di un valore nella storia: 90° = più alto del 90% dei giorni passati.", "VIX al 90° percentile: solo il 10% dei giorni è stato più teso."),
    ("Probabilità e «normale»", "La probabilità di oggi si confronta con la frequenza media storica dello stesso evento.", "Calo ≥10%: oggi 8%, normale 15% → oggi il rischio è più basso del solito."),
    ("Scenario", "Una delle possibili strade del mercato (forte calo, laterale, forte rialzo…) con la sua probabilità.", "Laterale 40% = in 4 casi su 10 il mercato è rimasto tra −3% e +3%."),
    ("Indice Armor", "Numero da 1 a 100 che riassume il rischio di crollo e volatilità unendo decine di indicatori.", "20 = molto calmo, 50 = moderato, 85 = stress diffuso."),
    ("Divergenza", "I prezzi salgono ma gli indicatori interni peggiorano: il rialzo è meno solido.", "Indice ai massimi mentre meno titoli lo sostengono."),
    ("Ampiezza di mercato", "Quanti titoli partecipano al rialzo.", "Se solo 30% dei titoli è sopra la media a 200 giorni, il mercato è fragile."),
    ("FOMC", "Il comitato della Fed che decide i tassi, 8 volte l'anno.", "Una decisione a sorpresa muove azioni e obbligazioni."),
    ("CPI", "Indice dei prezzi al consumo USA: misura l'inflazione.", "CPI sopra le attese → timore di tassi alti più a lungo."),
    ("Tre streghe", "Scadenza trimestrale di opzioni e futures (terzo venerdì di marzo, giugno, settembre, dicembre).", "Volumi alti e oscillazioni nel giorno."),
    ("Regime di mercato", "Stato generale del mercato stimato statisticamente: Calma, Tensione, Crisi.", "In «Tensione» le oscillazioni sono più ampie."),
    ("Cambio EUR/USD", "Quanti dollari vale un euro. Il VWCE investe soprattutto in dollari.", "Se l'euro sale, il VWCE in euro scende un po' a parità di mercato."),
    ("Rendimento reale", "Rendimento al netto dell'inflazione.", "Titolo al 4% con inflazione 2% → reale 2%."),
    ("AUC", "Misura da 0,5 (caso) a 1 (perfetto) di quanto un indicatore distingue i periodi a rischio.", "AUC 0,72: discreto, non perfetto."),
    ("Backtest", "Prova sul passato usando solo i dati che c'erano allora.", "Si guarda l'indice di ieri e cosa è successo nei mesi dopo."),
    ("Non è consulenza", "Armor mostra probabilità basate sul passato; nessun modello prevede i mercati con certezza.", "Decisioni importanti: parlane con un consulente indipendente."),
]


def glossario_html() -> str:
    items = "".join(f"<details class='gl'><summary>{e(t)}</summary><p>{e(d)}</p><p class='mu'><b>Esempio:</b> {e(x)}</p></details>" for t, d, x in GLOSS)
    return ("<input id='glq' type='search' placeholder='Cerca un termine (es. VIX, P/E, PAC)…' class='glq'>" + f"<div id='gllist'>{items}</div>"
            "<script>(function(){var q=document.getElementById('glq');if(!q)return;q.oninput=function(){var v=q.value.toLowerCase();document.querySelectorAll('#gllist details').forEach(function(d){d.style.display=d.textContent.toLowerCase().indexOf(v)>=0?'':'none'})}})();</script>")


# ---------------------------------------------------------------- finestra in basso
def dock_html(headline: str, tabs: list[tuple[str, str, str]]) -> str:
    btns = "".join(f"<button data-d='{k}'{' class=on' if i == 0 else ''}>{e(l)}</button>" for i, (k, l, _h2) in enumerate(tabs))
    panes = "".join(f"<div class='dpane{' on' if i == 0 else ''}' id='d-{k}'>{h}</div>" for i, (k, _l, h) in enumerate(tabs))
    return (f"<div id='dock'><button id='dockbar' aria-expanded='false'><span class='dk1'>Assistente Armor</span><span class='dk2'>{e(headline)}</span><span class='dka'>▲</span></button>"
            f"<div id='dockbody'><nav class='dnav'>{btns}</nav><div class='dpanes'>{panes}</div></div></div>"
            "<div id='calm' class='cmodal'><div class='cbox'><button class='cx' aria-label='Chiudi'>×</button><div class='cbody' id='calbody'></div></div></div>"
            "<template id='caltpl'>{{CAL}}</template>")


DOCK_JS = r"""
<script>
(function(){var d=document.getElementById('dock');if(!d)return;var bar=document.getElementById('dockbar');
function set(o){d.classList.toggle('open',o);bar.setAttribute('aria-expanded',o);bar.querySelector('.dka').textContent=o?'▼':'▲';document.body.classList.toggle('dockopen',o)}
bar.onclick=function(){set(!d.classList.contains('open'))};
d.querySelectorAll('.dnav button').forEach(function(b){b.onclick=function(){d.querySelectorAll('.dnav button').forEach(function(x){x.classList.toggle('on',x===b)});
d.querySelectorAll('.dpane').forEach(function(p){p.classList.toggle('on',p.id==='d-'+b.dataset.d)});if(b.dataset.d==='cal'){openCal();return}document.getElementById('dockbody').scrollTop=0}});
var cm=document.getElementById('calm');
function openCal(){var t=document.getElementById('caltpl');if(!t)return;var body=document.getElementById('calbody');if(!body.innerHTML)body.innerHTML=t.innerHTML;cm.classList.add('show');wire()}
function wire(){var mons=cm.querySelectorAll('.cmon'),i=0;mons.forEach(function(m,k){if(m.style.display!=='none')i=k});
function go(n){i=Math.max(0,Math.min(mons.length-1,n));mons.forEach(function(m,k){m.style.display=k===i?'':'none'})}
cm.querySelectorAll('.cprev').forEach(function(b){b.onclick=function(){go(i-1)}});cm.querySelectorAll('.cnext').forEach(function(b){b.onclick=function(){go(i+1)}})}
cm.addEventListener('click',function(e){if(e.target===cm||e.target.classList.contains('cx'))cm.classList.remove('show')});
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('[data-cal]');if(a){e.preventDefault();openCal()}});
window.armorDock=function(id){set(true);var b=d.querySelector('.dnav button[data-d="'+id+'"]');if(b)b.click()};
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('[data-dock]');if(a){e.preventDefault();window.armorDock(a.dataset.dock)}})})();
</script>
"""

CSS = """
.todo{border-radius:16px;padding:16px 18px;margin:0 0 14px;border:1px solid var(--bd);border-left-width:8px}.todo.ok{background:var(--okbg);border-left-color:var(--ok)}.todo.warn{background:var(--warnbg);border-left-color:var(--warn)}.todo.bad{background:var(--badbg);border-left-color:var(--bad)}
.td1{font-size:24px;font-weight:800;line-height:1.2;margin:4px 0 6px}.todo ul{margin:8px 0;padding-left:20px}
.topbtns{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px}.topbtns .btn{padding:9px 16px;font-weight:700}
.btn{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 14px;font:inherit;cursor:pointer}.btn.pri{background:var(--ac);color:#fff;border-color:var(--ac)}
#dock{position:fixed;left:0;right:0;bottom:0;z-index:15;max-width:1200px;margin:auto;background:var(--card);border:1px solid var(--bd);border-bottom:0;border-radius:18px 18px 0 0;box-shadow:0 -6px 22px rgba(0,0,0,.25)}
#dockbar{display:flex;align-items:center;gap:10px;width:100%;border:0;background:transparent;color:var(--tx);font:inherit;padding:12px 16px;cursor:pointer;text-align:left}
.dk1{font-weight:800}.dk2{flex:1;font-size:13px;color:var(--mu);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dka{font-size:16px;color:var(--ac)}
#dockbody{display:none;height:68vh;overflow:auto;border-top:1px solid var(--bd);padding:0 14px 14px}#dock.open #dockbody{display:block}
.dnav{position:sticky;top:0;background:var(--card);display:flex;gap:6px;overflow-x:auto;padding:10px 0}.dnav button{white-space:nowrap;border:1px solid var(--bd);background:var(--bg);color:var(--tx);padding:7px 13px;border-radius:99px;font:inherit;font-size:14px;cursor:pointer}.dnav button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.dpane{display:none}.dpane.on{display:block}body{padding-bottom:64px}body.dockopen{padding-bottom:calc(68vh + 64px)}
#calm{z-index:25}.calm .cmh{display:flex;justify-content:space-between;align-items:center;margin:6px 0}.cdg{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}.cw{text-align:center;font-size:12px;color:var(--mu);font-weight:700}
.cd{min-height:58px;border:1px solid var(--bd);border-radius:8px;padding:3px 4px;font-size:12px;background:var(--card);display:flex;flex-direction:column;gap:1px;overflow:hidden}.cd.o{border:0;background:transparent}.cd b{font-size:13px}.cd small{font-size:10px;font-weight:700}
.cd.today{outline:2px solid var(--ac)}.ev{font-style:normal;font-size:10px;font-weight:800;background:var(--warn);color:#fff;border-radius:5px;padding:0 4px;align-self:flex-start}.ev.w3{background:var(--bad)}
.hmt{font-size:12px;border-collapse:separate;border-spacing:2px}.hmt th{font-size:10px;font-weight:600;text-align:center;color:var(--mu);padding:2px}.hmt th.hr{text-align:left;white-space:nowrap;font-size:12px;color:var(--tx);position:sticky;left:0;background:var(--card)}
.hmt td.hm{min-width:30px;height:28px;text-align:center;color:#fff;font-weight:700;border-radius:5px;padding:0}
details.gl{border:1px solid var(--bd);border-radius:10px;padding:0 12px;margin:6px 0;background:var(--card)}details.gl summary{padding:10px 0;font-weight:700;color:var(--tx)}.glq{width:100%;padding:10px 14px;border-radius:99px;border:1px solid var(--bd);background:var(--card);color:var(--tx);font:inherit;margin:4px 0 8px}
"""
