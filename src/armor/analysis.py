"""Analisi giornaliera: legge tutti gli indicatori, li confronta con il passato e li commenta; poi riassume le notizie.
Tutto a regole e statistiche sui dati (nessuna IA): ogni frase deriva da un numero che trovi nel registro."""
import html
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import journal, news as newsmod, outlook, store
from .config import DATA, HORIZONS, HZ_LABEL, PRIMARY

REPORTS = DATA / "reports"
e = html.escape


def num(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1, sign=False):
    return ("+" if sign and x >= 0 else "") + num(x * 100, d).replace("-", "−") + "%"


def asof(key: str, date: pd.Timestamp, days_back: int = 0, max_age: int = 400):
    s = store.load(key)
    if s.empty:
        return None
    d = date - pd.Timedelta(days=days_back)
    s = s[s.index <= d]
    if s.empty or (d - s.index[-1]).days > max_age:
        return None
    return float(s.iloc[-1])


def pctile(key: str, v: float):
    s = store.load(key).dropna()
    return float((s < v).mean() * 100) if len(s) > 200 else None


def ordinal_pct(p: float) -> str:
    if p >= 95:
        return "tra i valori più alti di sempre"
    if p >= 80:
        return "nella fascia alta della storia"
    if p <= 5:
        return "tra i valori più bassi di sempre"
    if p <= 20:
        return "nella fascia bassa della storia"
    return "in una fascia intermedia"


# regole: (soglia, testo) valutate dall'alto verso il basso: il primo test vero vince
def band(v, rules, default=""):
    for test, text in rules:
        if test(v):
            return text
    return default


RULES = {
    "vix": [(lambda v: v < 14, "molto bassa: il mercato è rilassato, a volte troppo (la calma estrema precede spesso risvegli di volatilità)"),
            (lambda v: v < 20, "nella norma"), (lambda v: v < 25, "sopra la norma: nervosismo moderato"),
            (lambda v: v < 30, "alta: il mercato teme movimenti bruschi"), (lambda v: True, "molto alta: zona di panico")],
    "skew": [(lambda v: v > 150, "molto alto: gli investitori professionali si assicurano contro i crolli"),
             (lambda v: v > 135, "alto: la protezione contro i crolli costa più del solito"), (lambda v: True, "nella norma")],
    "move": [(lambda v: v > 120, "alta tensione sui titoli di Stato"), (lambda v: v > 90, "elevata"), (lambda v: True, "bassa")],
    "hy_oas": [(lambda v: v > 6, "stress forte nel credito rischioso"), (lambda v: v > 4.5, "elevato"),
               (lambda v: v > 3, "nella norma"), (lambda v: True, "molto basso: fiducia alta ma poco margine di sicurezza")],
    "baa10y": [(lambda v: v > 2.8, "stress"), (lambda v: v > 2.1, "elevato"), (lambda v: True, "nella norma")],
    "nfci": [(lambda v: v > 0, "condizioni finanziarie più strette della media"), (lambda v: True, "condizioni più facili della media")],
    "stlfsi": [(lambda v: v > 1, "stress finanziario alto"), (lambda v: v > 0, "stress sopra la media"), (lambda v: True, "stress sotto la media")],
    "t10y3m": [(lambda v: v < 0, "curva invertita: in passato ha preceduto molte recessioni, con mesi di anticipo"), (lambda v: True, "curva normale (i tassi lunghi sopra quelli corti)")],
    "t10y2y": [(lambda v: v < 0, "curva invertita: segnale di cautela"), (lambda v: True, "curva normale")],
    "real10y": [(lambda v: v > 2, "alto: i titoli di Stato rendono bene al netto dell'inflazione e fanno concorrenza alle azioni"),
                (lambda v: v > 0.5, "positivo e moderato"), (lambda v: True, "basso o negativo: favorevole alle azioni")],
    "dgs10": [(lambda v: v > 5, "oltre il 5%: forte pressione sulle valutazioni azionarie"), (lambda v: v > 4, "tra 4% e 5%: impegnativo per le azioni care"),
              (lambda v: True, "sotto il 4%: pressione contenuta")],
    "wti": [(lambda v: v > 95, "alto: pesa su inflazione e consumi"), (lambda v: v < 55, "basso: aiuta i consumi, ma può segnalare domanda debole"),
            (lambda v: True, "in una fascia intermedia")],
    "cape_m": [(lambda v: v > 35, "livello raggiunto solo ai picchi di fine anni '90 e nel 2021: rendimenti futuri a molti anni tendenzialmente più bassi"),
               (lambda v: v > 28, "alto"), (lambda v: v > 18, "intermedio"), (lambda v: True, "basso")],
    "pe_m": [(lambda v: v > 24, "alto"), (lambda v: v > 17, "intermedio"), (lambda v: True, "basso")],
    "ps_m": [(lambda v: v > 3, "molto alto rispetto alla storia dal 2000"), (lambda v: v > 2, "alto"), (lambda v: True, "nella norma")],
    "aaii_spread": [(lambda v: v < -20, "pessimismo diffuso: in passato spesso vicino a minimi di breve periodo, non un segnale da solo"),
                    (lambda v: v > 25, "euforia: in passato spesso vicino a massimi di breve periodo"), (lambda v: True, "equilibrato")],
    "fear_greed": [(lambda v: v < 25, "paura estrema"), (lambda v: v < 45, "paura"), (lambda v: v < 55, "neutro"), (lambda v: v < 75, "avidità"),
                   (lambda v: True, "avidità estrema")],
    "breadth200": [(lambda v: v < 40, "debole: pochi titoli sostengono l'indice"), (lambda v: v > 70, "forte: il rialzo è condiviso"), (lambda v: True, "intermedia")],
}


def change_phrase(key: str, date, dec: int = 1, rel: bool = True) -> str:
    now = asof(key, date)
    parts = []
    for lab, d in (("1 settimana", 7), ("1 mese", 30), ("3 mesi", 91), ("1 anno", 365)):
        old = asof(key, date, d, 400)
        if old is None or now is None or old == 0:
            continue
        ch = (now / old - 1) if rel and abs(old) > 1e-9 else (now - old)
        parts.append(f"{'+' if ch >= 0 else '−'}{num(abs(ch) * 100, 0) + '%' if rel else num(abs(ch), dec)} su {lab}")
    return "; ".join(parts[:3])


def indicator_line(key, label, date, sigs, dec=1, unit="", rel=True):
    now = asof(key, date)
    if now is None:
        return ""
    p = pctile(key, now)
    rule = band(now, RULES[key]) if key in RULES else ""
    chg = change_phrase(key, date, dec, rel)
    sg = sigs.get(key)
    hist = ""
    if sg:
        word = {"negativo": "segnale <b class='dn'>sfavorevole</b>", "positivo": "segnale <b class='up'>favorevole</b>", "neutro": "segnale neutro"}[sg["verdict"]]
        hist = (f" <i>Nel passato</i>: nelle volte in cui valeva come oggi (stessa fascia, dal {sg['since']}), l'S&amp;P 500 ha avuto un calo ≥10% "
                f"entro 3 mesi nel {pct(sg['freq_dd10'], 0)} dei casi (normalmente {pct(sg['base_dd10'], 0)}) e un rendimento medio di {pct(sg['ret'], 1, True)}: {word}.")
    pct_txt = f" ({ordinal_pct(p)}, {num(p, 0)}° percentile)" if p is not None else ""
    rule_txt = f" Lettura: {e(rule)}." if rule else ""
    chg_txt = f" Variazioni: {chg}." if chg else ""
    return f"<li><b>{e(label)}: {num(now, dec)}{unit}</b>{pct_txt}.{rule_txt}{chg_txt}{hist}</li>"


def section(title, intro, lines, extra=""):
    lines = [l for l in lines if l]
    if not lines and not extra:
        return ""
    return f"<div class='asec'><h3>{e(title)}</h3><p>{intro}</p><ul>{''.join(lines)}</ul>{extra}</div>"


def episodes_html(key, p, label, dec=1):
    eps = outlook.episodes_for_value(key, p)
    if not eps:
        return ""
    rows = "".join(f"<li>{x['date']}: {e(label)} {num(x['value'], dec)}, poi l'S&amp;P 500 a 3 mesi {pct(x['ret_3m'], 1, True)} (calo massimo {pct(x['maxdd'], 1)})</li>" for x in eps)
    return f"<p class='muted'>Quando {e(label)} valeva come oggi: </p><ul class='eps'>{rows}</ul>"


def generate(date: pd.Timestamp, pred: dict, spot: float, sp: pd.Series, live: dict, news: dict, valuations: list) -> dict:
    sigs_l = outlook.signal_table(sp)
    sigs = {s["key"]: s for s in sigs_l}
    secs = []
    vers = {"Basso": "basso", "Normale": "nella norma", "Elevato": "più alto del normale", "Alto": "alto"}
    # ---------- sintesi
    j = journal.read()
    chg_txt = []
    for hz in HORIZONS:
        if hz not in pred:
            continue
        p_now = pred[hz]["p"][PRIMARY[hz]]
        prev = j[(j["horizon"] == hz) & (j["asof"] < date.strftime("%Y-%m-%d"))].tail(1) if len(j) else pd.DataFrame()
        arrow = ""
        if len(prev):
            r = prev.iloc[0]
            pv = r["p1"] if r["thr1"] == PRIMARY[hz] else r["p2"]
            if pd.notna(pv):
                arrow = f" ({'+' if p_now >= pv else '−'}{num(abs(p_now - pv) * 100, 1)} punti rispetto alla previsione del {r['asof']})"
        chg_txt.append(f"<li>{HZ_LABEL[hz]}: probabilità di un calo ≥{PRIMARY[hz]}% pari a <b>{pct(p_now, 0)}</b>, livello <b>{vers[pred[hz]['level']]}</b>{arrow}.</li>")
    neg = sorted([s for s in sigs_l if s["verdict"] == "negativo"], key=lambda s: -s["ratio"])[:4]
    posi = sorted([s for s in sigs_l if s["verdict"] == "positivo"], key=lambda s: s["ratio"])[:4]
    r_txt = "".join(f"<li><b>{e(s['name'])}</b> ({num(s['now'], 2)}, {num(s['pct'], 0)}° percentile): in passato, in queste condizioni, calo ≥10% a 3 mesi nel {pct(s['freq_dd10'], 0)} dei casi contro {pct(s['base_dd10'], 0)} normale.</li>" for s in neg)
    o_txt = "".join(f"<li><b>{e(s['name'])}</b> ({num(s['now'], 2)}, {num(s['pct'], 0)}° percentile): in passato, in queste condizioni, calo ≥10% a 3 mesi nel {pct(s['freq_dd10'], 0)} dei casi contro {pct(s['base_dd10'], 0)} normale.</li>" for s in posi)
    q = live.get("quotes", {})
    px = ""
    if q.get("vwce"):
        x = q["vwce"]
        px = f"VWCE a {num(x['price'], 2)} € ({pct(x['chg'], 2, True) if x.get('chg') is not None else '—'} sull'ultima chiusura"
        px += f", ultimo scambio {x.get('venue', '')}). "
    vx = asof("vix", date)
    summary = (f"<p>{px}Dati di mercato al {date.strftime('%d/%m/%Y')}. Il VIX è a {num(vx, 1) if vx else '—'}"
               f"{' (' + band(vx, RULES['vix']) + ')' if vx else ''}.</p><ul>{''.join(chg_txt)}</ul>"
               f"<div class='two'><div><h4>Segnali di rischio oggi</h4><ul>{r_txt or '<li>Nessun indicatore in zona sfavorevole.</li>'}</ul></div>"
               f"<div><h4>Segnali favorevoli oggi</h4><ul>{o_txt or '<li>Nessun indicatore in zona chiaramente favorevole.</li>'}</ul></div></div>")
    secs.append(f"<div class='asec'><h3>Sintesi della giornata</h3>{summary}</div>")
    L = lambda k, lab, **kw: indicator_line(k, lab, date, sigs, **kw)
    secs.append(section("Volatilità e paura", "Il VIX misura quanta oscillazione si aspetta il mercato nel prossimo mese; è il termometro della paura. Va letto insieme alla protezione contro i crolli (SKEW) e alla tensione sulle obbligazioni (MOVE).",
                        [L("vix", "VIX"), L("skew", "SKEW"), L("move", "MOVE"), L("vvix", "VVIX")], episodes_html("vix", sp, "il VIX", 1)))
    secs.append(section("Credito e liquidità", "Quando le aziende fanno fatica a finanziarsi e gli investitori chiedono più interesse per prestare, di solito il mercato azionario è sotto pressione. È uno dei segnali di stress più utili.",
                        [L("hy_oas", "Spread High Yield", dec=2), L("baa10y", "Spread BAA-10Y", dec=2), L("nfci", "Condizioni finanziarie NFCI", dec=2),
                         L("stlfsi", "Stress finanziario (St. Louis)", dec=2)]))
    secs.append(section("Tassi, curva e obbligazioni", "I tassi dei titoli di Stato sono il prezzo del denaro: se salgono molto, i prezzi delle azioni, soprattutto quelle care, ne risentono. La curva (tassi lunghi meno corti) sotto zero ha preceduto molte recessioni.",
                        [L("dgs10", "Rendimento Treasury 10 anni", dec=2, unit="%", rel=False), L("dgs2", "Rendimento Treasury 2 anni", dec=2, unit="%", rel=False),
                         L("t10y3m", "Curva 10Y-3M", dec=2, rel=False), L("t10y2y", "Curva 10Y-2Y", dec=2, rel=False),
                         L("real10y", "Tasso reale a 10 anni", dec=2, unit="%", rel=False), L("fedfunds", "Tasso della Fed", dec=2, unit="%", rel=False)]))
    secs.append(section("Dollaro e cambio euro/dollaro", "Il VWCE investe soprattutto in dollari ma tu lo vedi in euro. Se il dollaro si indebolisce, a parità di mercato il tuo VWCE in euro rende meno; se si rafforza, rende di più.",
                        [L("usd_broad", "Dollaro (indice ampio)"), L("eurusd", "Cambio EUR/USD", dec=4)]))
    secs.append(section("Oro, petrolio e materie prime", "L'oro sale quando cresce il bisogno di rifugio; il petrolio incide su inflazione e costi. Vanno letti come indizi sul clima, non come previsioni sull'azionario.",
                        [L("gold", "Oro ($)", dec=0), L("wti", "Petrolio WTI ($)")]))
    # valutazioni
    vcards = "".join(f"<li><b>{e(c['name'])}</b>: P/E {num(c['pe'], 1) if c['pe'] else 'n.d.'}, prezzo/fatturato {num(c['ps'], 2) if c['ps'] else 'n.d.'}"
                     f"{' (P/E al ' + num(c['pe_pct'], 0) + '° percentile storico)' if c.get('pe_pct') is not None else ''}.</li>" for c in valuations)
    secs.append(section("Valutazioni: quanto è «caro» il mercato", "Capitalizzazione/utili (P/E) e capitalizzazione/fatturato (P/S) dicono quanto si paga ogni euro di utile o di ricavi. Valutazioni alte non fanno scendere il mercato domani, ma riducono il margine di errore e i rendimenti attesi a molti anni; con il mercato 'caro' un brutto evento fa più danni.",
                        [vcards, L("cape_m", "CAPE (utili medi 10 anni)"), L("pe_m", "P/E S&P 500 (utili 12 mesi)"), L("ps_m", "Prezzo/fatturato S&P 500", dec=2),
                         L("top_fcf_yield", "Rendimento da cassa libera dei 30 colossi", dec=2, unit="%", rel=False), L("ai_capex_ocf", "Investimenti AI / cassa operativa (big tech)", dec=2, rel=False)]))
    # lavoro
    sahm = ""
    u = store.load("unrate")
    if len(u) > 24:
        a = u.rolling(3).mean()
        val = float(a.iloc[-1] - a.rolling(12).min().iloc[-1])
        sahm = (f"<li><b>Indicatore di recessione di Sahm: {num(val, 2)} punti</b>. Scatta oltre 0,50 (media a 3 mesi della disoccupazione 0,5 punti sopra il minimo dell'anno): "
                f"oggi {'È SCATTATO, segnale di recessione' if val >= 0.5 else 'non è scattato'}.</li>")
    cpi = store.load("cpi")
    infl = ""
    if len(cpi) > 14:
        yoy = float(cpi.iloc[-1] / cpi.iloc[-13] - 1)
        infl = f"<li><b>Inflazione USA (CPI) su 12 mesi: {pct(yoy, 1)}</b>. Sopra il 3% la Fed ha meno spazio per tagliare i tassi; sotto il 2,5% ne ha di più.</li>"
    secs.append(section("Lavoro, inflazione ed economia", "L'economia reale decide gli utili delle aziende: lavoro e inflazione guidano le mosse delle banche centrali.",
                        [L("unrate", "Disoccupazione USA", dec=1, unit="%", rel=False), sahm, infl, L("icsa", "Richieste settimanali di sussidio", dec=0)]))
    secs.append(section("Sentiment e ampiezza del mercato", "Ampiezza = quante società partecipano al rialzo. Un mercato che sale con pochi titoli è più fragile. Il sentiment estremo (troppa paura o troppa euforia) segnala spesso svolte, ma non è affidabile da solo.",
                        [L("aaii_spread", "Sondaggio AAII (rialzisti − ribassisti)", unit=" pt", rel=False), L("fear_greed", "Fear & Greed CNN", dec=0, rel=False),
                         L("breadth200", "Titoli sopra la media a 200 giorni", dec=0, unit="%", rel=False), L("breadth50", "Titoli sopra la media a 50 giorni", dec=0, unit="%", rel=False),
                         L("nh_nl", "Nuovi massimi meno nuovi minimi", dec=1, unit="%", rel=False)]))
    secs.append(section("Geopolitica e incertezza", "Gli indici di incertezza contano le notizie su guerre, minacce e politica economica. Sono alti nelle crisi, ma da soli non dicono se il mercato scenderà: contano se si sommano a stress finanziario.",
                        [L("gpr", "Rischio geopolitico (GPR)", dec=0), L("epu", "Incertezza politica (EPU)", dec=0)]))
    secs = [s for s in secs if s]
    # ---------- notizie
    items = news.get("items", [])
    ns = ""
    if items:
        macro = [i for i in items if i["kind"] == "macro"]
        comp = [i for i in items if i["kind"] == "company"]
        tcount = {}
        for i in macro:
            for t in i["themes"] or ["Altro"]:
                tcount[t] = tcount.get(t, 0) + 1
        top_t = sorted(tcount.items(), key=lambda kv: -kv[1])[:6]
        avg = np.mean([i["sent"] for i in macro]) if macro else 0
        hist = newsmod.history_sentiment(14)
        base = np.mean(list(hist.values())[:-1]) if len(hist) > 3 else None
        tone = ("negativo" if avg <= -0.1 else ("positivo" if avg >= 0.1 else "neutro"))
        cmp_txt = ""
        if base is not None:
            cmp_txt = f" Rispetto alla media degli ultimi giorni ({num(base, 2)}) il tono è {'più negativo' if avg < base - 0.05 else ('più positivo' if avg > base + 0.05 else 'simile')}."
        ns += (f"<div class='asec'><h3>Notizie: finanza e geopolitica</h3><p>Ho letto {len(items)} titoli degli ultimi giorni da fonti pubbliche. "
               f"Tono medio dei titoli macro: <b>{tone}</b> ({num(avg, 2)}, scala da −1 a +1).{cmp_txt} Temi più frequenti: "
               f"{', '.join(f'{e(t)} ({n})' for t, n in top_t)}.</p>")
        ns += "<ul class='news'>" + "".join(_news_li(i) for i in macro[:14]) + "</ul></div>"
        ns += "<div class='asec'><h3>Le 20 maggiori società: cosa dicono le notizie</h3><p>Per ogni società: tono medio dei titoli recenti e le notizie più rilevanti. Un tono negativo non significa che il titolo scenderà: segnala dove c'è attenzione o preoccupazione.</p>"
        by = {}
        for i in comp:
            by.setdefault(i["group"], []).append(i)
        rows = []
        for t, name in newsmod.TOP20:
            g = f"{name} ({t})"
            its = by.get(g, [])
            if not its:
                continue
            a = np.mean([i["sent"] for i in its])
            rows.append((a, g, its))
        for a, g, its in sorted(rows, key=lambda r: r[0]):
            lab = newsmod.label_of(a)
            ns += (f"<details class='co'><summary><b>{e(g)}</b> · tono <span class='tag {lab}'>{lab}</span> ({num(a, 2)}) · {len(its)} titoli</summary>"
                   f"<ul class='news'>{''.join(_news_li(i) for i in its[:4])}</ul></details>")
        ns += "</div>"
        # lettura
        neg_t = [t for t, n in top_t if any(i["label"] == "negativo" and t in i["themes"] for i in macro)][:3]
        read = ("<div class='asec'><h3>Come leggere le notizie di oggi</h3><ul>"
                f"<li>Il mercato reagisce alle sorprese, non alle notizie già note: un titolo negativo già scontato dai prezzi conta poco.</li>"
                f"<li>I temi con più titoli negativi oggi: {e(', '.join(neg_t)) if neg_t else 'nessuno in particolare'}. Controlla se coincidono con segnali di stress nei dati (VIX, credito, tassi): quando notizie negative e stress nei dati vanno insieme, il rischio è più concreto.</li>"
                "<li>Un tono dei titoli molto negativo, da solo, in passato è stato spesso un indicatore contrario di breve periodo (la paura si concentra vicino ai minimi): non è un segnale di acquisto, ma non va inseguito.</li>"
                "<li>Questo riassunto legge titoli e brevi descrizioni, non gli articoli completi: per decisioni importanti verifica sempre la fonte.</li></ul></div>")
        ns += read
    else:
        ns = "<div class='asec'><h3>Notizie</h3><p class='muted'>Notizie non ancora scaricate: compaiono al prossimo aggiornamento automatico.</p></div>"
    out = {"date": date.strftime("%Y-%m-%d"), "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "html": "".join(secs) + ns, "n_sig": len(sigs_l), "risks": [s["name"] for s in neg], "opps": [s["name"] for s in posi]}
    return out


def _news_li(i) -> str:
    when = ""
    try:
        when = datetime.fromisoformat(i["time"].replace("Z", "+00:00")).strftime("%d/%m %H:%M")
    except Exception:  # noqa: BLE001
        pass
    th = ", ".join(i["themes"][:2])
    return (f"<li><span class='tag {i['label']}'>{i['label']}</span> <a href='{e(i['link'])}' target='_blank' rel='noopener'>{e(i['title'])}</a> "
            f"<span class='muted'>{e(i['source'])}{' · ' + when if when else ''}{' · ' + e(th) if th else ''}</span></li>")


def save(rep: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{rep['date']}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    (REPORTS / "latest.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    for p in sorted(REPORTS.glob("20*.json"))[:-60]:
        p.unlink()


def load_latest() -> dict:
    try:
        return json.loads((REPORTS / "latest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def load_archive(n: int = 14) -> list[dict]:
    out = []
    for p in sorted(REPORTS.glob("20*.json"))[-n:][::-1]:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out
