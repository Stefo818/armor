"""Semafori: per ogni indice, valore di oggi, colore (verde/giallo/rosso), come si legge e quando preoccuparsi.
Le soglie sono fissate in anticipo e valgono per tutta la storia (non si adattano ai dati di oggi)."""
import html as _h

import numpy as np
import pandas as pd

from . import store

# (chiave, nome, gruppo, tipo, soglia1, soglia2, unità, decimali, come si legge, quando preoccuparsi)
# hi: più alto = peggio (giallo da s1, rosso da s2); lo: più basso = peggio (giallo sotto s1, rosso sotto s2)
# band: (basso_rosso, basso_giallo, alto_giallo, alto_rosso); pct: percentile nella storia propria (giallo >70, rosso >90)
SPEC = [
    ("vix", "VIX (indice della paura)", "Paura e opzioni", "hi", 20, 30, "", 1,
     "Quanto costa proteggersi dai ribassi del mese prossimo. Sale quando gli operatori hanno paura.",
     "Sopra 20 il mercato è nervoso, sopra 30 è in stress, sopra 40 è panico. Sotto 14 è calma estrema, spesso prima di un risveglio."),
    ("vterm", "Curva del VIX (VIX3M / VIX)", "Paura e opzioni", "lo", 1.05, 0.95, "", 2,
     "Confronta la paura a 3 mesi con quella a 1 mese. Normalmente la paura a 3 mesi è maggiore.",
     "Sotto 1 la paura di oggi supera quella futura: è tipico dei momenti di stress acuto."),
    ("vvix", "VVIX (volatilità del VIX)", "Paura e opzioni", "hi", 100, 120, "", 0,
     "Misura quanto è instabile la paura stessa. Alto = ci si aspetta scosse nel VIX.",
     "Sopra 100 attenzione, sopra 120 forte tensione."),
    ("skew", "SKEW (protezione dai crolli)", "Paura e opzioni", "hi", 135, 150, "", 0,
     "Quanto costa assicurarsi contro un crollo improvviso rispetto a un normale calo.",
     "Sopra 135 i professionisti si coprono più del solito, sopra 150 molto."),
    ("move", "MOVE (volatilità dei titoli di Stato)", "Paura e opzioni", "hi", 90, 120, "", 0,
     "Il «VIX delle obbligazioni»: quanto sono nervosi i titoli di Stato USA.",
     "Sopra 90 attenzione, sopra 120 tensione forte che può contagiare le azioni."),
    ("pc_oi", "Put/Call sulle opzioni SPY (posizioni aperte)", "Paura e opzioni", "pct", None, None, "", 2,
     "Rapporto tra opzioni put (scommesse al ribasso o protezioni) e call (scommesse al rialzo). Piu' alto = più protezioni.",
     "Valori molto alti rispetto alla storia dell'app indicano protezione diffusa: può precedere cali, ma anche rimbalzi (è un indicatore contrario)."),
    ("hy_oas", "Spread dei bond High Yield", "Credito e liquidità", "hi", 4.5, 6, " %", 2,
     "Il rendimento extra che le aziende più rischiose devono pagare. Sale quando il credito si irrigidisce.",
     "Sopra 4,5% attenzione, sopra 6% stress forte nel credito. Sotto 3% fiducia alta e poco margine di sicurezza."),
    ("baa10y", "Spread BAA - Titoli di Stato 10 anni", "Credito e liquidità", "hi", 2.1, 2.8, " %", 2,
     "Quanto in più rendono le aziende solide rispetto allo Stato USA.",
     "Sopra 2,1% attenzione, sopra 2,8% stress."),
    ("nfci", "Condizioni finanziarie (NFCI)", "Credito e liquidità", "hi", -0.2, 0, "", 2,
     "Indice della Fed di Chicago: quanto è facile o difficile trovare credito. Sotto zero = condizioni più facili del normale.",
     "Sopra 0 le condizioni sono più strette della media: frenano economia e mercati."),
    ("stlfsi", "Stress finanziario (St. Louis)", "Credito e liquidità", "hi", 0, 1, "", 2,
     "Indice composito di stress dei mercati finanziari. Zero = stress medio.",
     "Sopra 0 stress sopra la media, sopra 1 stress alto."),
    ("anfci", "Condizioni finanziarie corrette per il ciclo (ANFCI)", "Credito e liquidità", "hi", 0, 0.5, "", 2,
     "Indice settimanale della Fed di Chicago: condizioni finanziarie (rischio, credito, leva) al netto dell'effetto del ciclo economico.",
     "Sopra 0 le condizioni sono più tese di quanto il ciclo giustifichi; sopra 0,5 la tensione è marcata."),
    ("sloos", "Banche che irrigidiscono i prestiti alle imprese (SLOOS)", "Credito e liquidità", "hi", 10, 30, " %", 0,
     "Indagine trimestrale della Fed: percentuale netta di banche che stringe i criteri per prestare alle imprese.",
     "Sopra 10% il credito si sta chiudendo, sopra 30% è tipico di recessioni e di forti cali."),
    ("credit_gap", "Credit-to-GDP gap (BIS)", "Credito e liquidità", "hi", 2, 10, " punti", 1,
     "Quanto il credito al settore privato supera il suo trend di lungo periodo (in punti di PIL, filtro HP unilaterale come BIS).",
     "Sopra 2 punti inizia l'eccesso di credito, sopra 10 la BIS lo considera segnale di allerta per crisi bancarie."),
    ("t10y3m", "Curva dei tassi 10 anni - 3 mesi", "Tassi e obbligazioni", "lo", 0.5, 0, " %", 2,
     "Differenza tra i tassi a lungo e a breve termine. Normalmente positiva.",
     "Sotto zero (curva invertita) in passato ha preceduto molte recessioni, con mesi o anni di anticipo."),
    ("t10y2y", "Curva dei tassi 10 anni - 2 anni", "Tassi e obbligazioni", "lo", 0.3, 0, " %", 2,
     "Come sopra, con i tassi a 2 anni.", "Sotto zero la curva è invertita: segnale di cautela, non di crisi imminente."),
    ("dgs10", "Rendimento titoli di Stato USA 10 anni", "Tassi e obbligazioni", "hi", 4, 5, " %", 2,
     "Quanto rende un titolo di Stato USA a 10 anni: fa concorrenza alle azioni.",
     "Sopra 4% è impegnativo per le azioni care, sopra 5% la pressione è forte."),
    ("real10y", "Tasso reale a 10 anni", "Tassi e obbligazioni", "hi", 1.5, 2.2, " %", 2,
     "Rendimento a 10 anni al netto dell'inflazione attesa.", "Sopra 1,5% pesa sulle valutazioni, sopra 2,2% molto."),
    ("usd_broad", "Dollaro (indice ampio)", "Dollaro e materie prime", "pct", None, None, "", 1,
     "Forza del dollaro contro le principali valute. Un dollaro molto forte stringe le condizioni finanziarie globali.",
     "Preoccupa un rialzo rapido (in poche settimane), più del livello."),
    ("gold", "Oro", "Dollaro e materie prime", "info", None, None, " $", 0,
     "Bene rifugio: sale quando cresce la sfiducia o calano i tassi reali.", "Un rialzo forte insieme a un VIX alto indica ricerca di sicurezza."),
    ("wti", "Petrolio (WTI)", "Dollaro e materie prime", "band", 45, 55, " $", 1,
     "Prezzo del greggio USA: pesa su inflazione e consumi.", "Sopra 95-110 $ spinge l'inflazione; sotto 45 $ può segnalare domanda debole."),
    ("cape_m", "CAPE (P/E su 10 anni, Shiller)", "Valutazioni", "hi", 28, 35, "", 1,
     "Prezzo diviso la media degli utili degli ultimi 10 anni (corretti per l'inflazione).",
     "Sopra 28 è caro, sopra 35 è ai livelli del 2000 e del 2021: rendimenti futuri a molti anni mediamente più bassi."),
    ("pe_m", "P/E S&P 500", "Valutazioni", "hi", 18, 24, "", 1,
     "Quanti dollari si pagano per 1 dollaro di utile annuo.", "Sopra 18 è sopra la media storica, sopra 24 è nel decimo più caro della storia."),
    ("ps_m", "P/S S&P 500", "Valutazioni", "hi", 2, 3, "", 2,
     "Quanti dollari si pagano per 1 dollaro di fatturato.", "Sopra 2 è alto, sopra 3 è un massimo storico."),
    ("aaii_spread", "Sentiment investitori (AAII)", "Sentiment e ampiezza", "band", -30, -20, "", 0,
     "Rialzisti meno ribassisti tra gli investitori individuali USA.",
     "Sopra +25 euforia (spesso vicino a massimi di breve), sotto -20 pessimismo (spesso vicino a minimi di breve). Indicatore contrario."),
    ("fear_greed", "Fear & Greed (CNN)", "Sentiment e ampiezza", "band", 15, 25, "", 0,
     "Misura da 0 (paura estrema) a 100 (avidità estrema).", "Oltre 75-80 avidità estrema: mercato fragile. Sotto 25 paura: spesso occasione, non certezza."),
    ("breadth200", "Ampiezza: titoli sopra la media a 200 giorni", "Sentiment e ampiezza", "lo", 55, 40, " %", 0,
     "Quanti titoli dell'indice sono in tendenza rialzista.", "Sotto 40% pochi titoli sostengono l'indice: rialzo fragile."),
    ("dd252", "Distanza dal massimo a 1 anno (S&P 500)", "Prezzi", "hi", 5, 10, " %", 1,
     "Di quanto l'S&P 500 è sceso dal massimo degli ultimi 12 mesi.", "Sopra 5% correzione in corso, sopra 10% correzione profonda, sopra 20% mercato ribassista."),
    ("rv21", "Volatilità realizzata a 1 mese (S&P 500)", "Prezzi", "hi", 15, 25, " %", 1,
     "Quanto si muove davvero l'indice (annualizzato).", "Sopra 15% oscilla più del normale, sopra 25% è in tensione."),
    ("ma200", "Prezzo contro media a 200 giorni (S&P 500)", "Prezzi", "lo", 0, -5, " %", 1,
     "Quanto l'indice è sopra (positivo) o sotto (negativo) la sua media a 200 giorni.", "Sotto la media la tendenza è ribassista; sotto -5% è una rottura netta."),
    ("sahm", "Regola di Sahm (disoccupazione)", "Economia", "hi", 0.3, 0.5, " punti", 2,
     "Aumento della disoccupazione USA rispetto al minimo dell'ultimo anno.", "Da 0,5 punti in su, in passato, è iniziata una recessione."),
    ("icsa", "Richieste di sussidio di disoccupazione (settimanali)", "Economia", "hi", 250000, 300000, "", 0,
     "Quante persone chiedono il sussidio per la prima volta ogni settimana: segnala presto il mercato del lavoro.",
     "Sopra 250.000 il lavoro si raffredda, sopra 300.000 è un segnale di recessione."),
]
SPEC_BY = {s[0]: s for s in SPEC}
LIGHT_TXT = {"ok": "Tranquillo", "wa": "Attenzione", "ba": "Allarme", "na": "Informativo"}
KEY_ORDER = ["vix", "pc_oi", "pe_m", "ps_m", "cape_m", "rv21", "hy_oas", "nfci", "t10y3m", "move", "skew", "dd252"]


def _arch_series(col: str) -> pd.Series:
    from .config import ARCHIVE
    f = ARCHIVE / "spy_options_summary.csv"
    if not f.exists():
        return pd.Series(dtype=float)
    d = pd.read_csv(f)
    if col not in d:
        return pd.Series(dtype=float)
    return pd.Series(d[col].values, index=pd.to_datetime(d["date"])).dropna()


def credit_gap(ratio: pd.Series, lam: float = 400000.0, min_n: int = 40) -> pd.Series:
    """Credit-to-GDP gap: rapporto credito/PIL meno il suo trend, con filtro HP UNILATERALE (a ogni data usa solo dati fino a quella data), lambda 400.000 come la BIS."""
    r = ratio.dropna()
    if len(r) < min_n + 4:
        return pd.Series(dtype=float)
    y = r.values.astype(float)
    out = []
    for t in range(min_n, len(y)):
        n = t + 1
        D = np.zeros((n - 2, n))
        for i in range(n - 2):
            D[i, i:i + 3] = (1, -2, 1)
        trend = np.linalg.solve(np.eye(n) + lam * D.T @ D, y[:n])
        out.append(y[t] - trend[-1])
    return pd.Series(out, index=r.index[min_n:])


def series_of(key: str, sp: pd.Series | None = None) -> pd.Series:
    if key in ("dd252", "rv21", "ma200"):
        from .features import price_features
        f = price_features(sp)
        return (f[key] * 100).dropna() if key != "dd252" else (-f[key] * 100).dropna()
    if key == "vterm":
        a, b = store.load("vix3m"), store.load("vix")
        return (a / b.reindex(a.index)).dropna() if len(a) and len(b) else pd.Series(dtype=float)
    if key == "pc_oi":
        return _arch_series("pc_open_interest")
    if key == "credit_gap":
        return credit_gap(store.load("credit_ratio"))
    if key == "sahm":
        u = store.load("unrate")
        if len(u) < 18:
            return pd.Series(dtype=float)
        m = u.rolling(3).mean()
        return (m - m.rolling(12).min()).dropna()
    s = store.load(key)
    return s.dropna()


def light_of(spec, v: float, s: pd.Series) -> str:
    _k, _n, _g, kind, a, b, *_ = spec
    if kind == "hi":
        return "ok" if v < a else ("wa" if v < b else "ba")
    if kind == "lo":
        return "ok" if v > a else ("wa" if v > b else "ba")
    if kind == "band":
        if _k == "wti":
            return "ok" if 55 <= v <= 95 else ("wa" if 45 <= v < 55 or 95 < v <= 110 else "ba")
        if _k == "aaii_spread":
            return "ba" if v > 35 else ("wa" if v > 25 or v < -20 else "ok")
        if _k == "fear_greed":
            return "ba" if v > 80 else ("wa" if v > 70 or v < 25 else "ok")
    if kind == "pct":
        if len(s) < 60:
            return "na"
        p = (s < v).mean()
        return "ba" if p > 0.9 else ("wa" if p > 0.7 else "ok")
    return "na"


def zone_text(spec) -> str:
    k, _n, _g, kind, a, b, unit, dec, *_ = spec
    f = lambda x: f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if kind == "hi":
        return f"verde sotto {f(a)} · giallo {f(a)}–{f(b)} · rosso sopra {f(b)}"
    if kind == "lo":
        return f"verde sopra {f(a)} · giallo {f(b)}–{f(a)} · rosso sotto {f(b)}"
    if kind == "pct":
        return "confronto con la storia dei dati salvati: giallo oltre il 70° percentile, rosso oltre il 90°"
    if k == "wti":
        return "verde 55–95 · giallo 45–55 o 95–110 · rosso fuori"
    if k == "aaii_spread":
        return "verde tra -20 e +25 · giallo oltre quei limiti · rosso sopra +35"
    if k == "fear_greed":
        return "verde 25–70 · giallo 70–80 o sotto 25 · rosso sopra 80"
    return ""


def compute(sp: pd.Series, live: dict | None = None) -> list[dict]:
    out = []
    q = (live or {}).get("quotes", {})
    for spec in SPEC:
        key, name, group, kind, a, b, unit, dec, read, worry = spec
        try:
            s = series_of(key, sp)
            if s.empty:
                continue
            v = float(s.iloc[-1])
            if key == "vix" and (q.get("vix") or {}).get("price"):
                v = float(q["vix"]["price"])
            if (pd.Timestamp.now().normalize() - s.index[-1]).days > 400:
                continue
            light = light_of(spec, v, s)
            pct = float((s < v).mean() * 100) if len(s) > 200 else None
            out.append({"key": key, "name": name, "group": group, "value": v, "dec": dec, "unit": unit, "light": light,
                        "date": s.index[-1].strftime("%d/%m/%Y"), "read": read, "worry": worry, "zones": zone_text(spec), "pct": pct})
        except Exception:  # noqa: BLE001
            continue
    return out


def overall(items: list[dict]) -> dict:
    n = {"ok": 0, "wa": 0, "ba": 0}
    for i in items:
        if i["light"] in n:
            n[i["light"]] += 1
    return n


def fmt(v: float, dec: int, unit: str) -> str:
    s = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + unit


def card(i: dict, big: bool = False) -> str:
    e = _h.escape
    pc = f" · {i['pct']:.0f}° percentile storico" if i.get("pct") is not None else ""
    return (f"<div class='sem {i['light']}{' big' if big else ''}' data-chart='{i['key']}'>"
            f"<div class='sh'><span class='dot'></span><span class='sn'>{e(i['name'])}</span><span class='st'>{LIGHT_TXT[i['light']]}</span></div>"
            f"<div class='sv'>{fmt(i['value'], i['dec'], i['unit'])}</div>"
            f"<div class='sr'>{e(i['read'])}</div>"
            f"<details onclick='event.stopPropagation()'><summary>Quando preoccuparsi</summary><div class='sw'>{e(i['worry'])}<br><span class='mu'>Soglie: {e(i['zones'])}{pc} · dato del {i['date']}</span></div></details></div>")


def html(items: list[dict], keys_only: bool = False) -> str:
    if not items:
        return "<p class='mu'>Semafori non disponibili: mancano i dati.</p>"
    if keys_only:
        sel = [next((i for i in items if i["key"] == k), None) for k in KEY_ORDER]
        return "<div class='semgrid'>" + "".join(card(i, True) for i in sel if i) + "</div>"
    groups = {}
    for i in items:
        groups.setdefault(i["group"], []).append(i)
    out = []
    for g, its in groups.items():
        out.append(f"<h3>{_h.escape(g)}</h3><div class='semgrid'>" + "".join(card(i) for i in its) + "</div>")
    return "".join(out)


CSS = """
.semgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.sem{background:var(--card);border:1px solid var(--bd);border-left-width:6px;border-radius:12px;padding:10px 12px;cursor:pointer}
.sem.ok{border-left-color:var(--ok)}.sem.wa{border-left-color:var(--warn)}.sem.ba{border-left-color:var(--bad)}.sem.na{border-left-color:var(--bd)}
.sem .sh{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600}.sem .sn{flex:1}.sem .dot{width:11px;height:11px;border-radius:50%;background:var(--mu)}
.sem.ok .dot{background:var(--ok)}.sem.wa .dot{background:var(--warn)}.sem.ba .dot{background:var(--bad)}
.sem .st{font-size:11px;font-weight:700;text-transform:uppercase;color:var(--mu)}.sem.ok .st{color:var(--ok)}.sem.wa .st{color:var(--warn)}.sem.ba .st{color:var(--bad)}
.sem .sv{font-size:26px;font-weight:800;line-height:1.2;margin:2px 0}.sem.big .sv{font-size:32px}.sem .sr{font-size:13px;color:var(--mu)}
.sem details{margin-top:6px}.sem summary{font-size:12px;font-weight:700;color:var(--ac);cursor:pointer}.sem .sw{font-size:12.5px;margin-top:4px}
"""
