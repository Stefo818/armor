"""Indicatori fondamentali per singolo titolo (PIANO_ESPANSIONE Patch 45, Appendice A).
Le funzioni di calcolo sono pure (dati in ingresso → numero) e testate; i recuperi di dati (yfinance, SEC EDGAR) sono in fondo, con cache di 7 giorni e
sempre protetti: se una fonte non risponde il campo resta None e non si inventa nulla."""
import json
import os
import time

import numpy as np

from .config import DATA

CACHE_DIR = DATA / "_cache" / "fond"      # non committata (vedi .gitignore): in Actions sta in actions/cache
CACHE_GIORNI = 7


def _n(x):
    try:
        v = float(x)
        return None if np.isnan(v) or np.isinf(v) else v
    except (TypeError, ValueError):
        return None


def _div(a, b):
    a, b = _n(a), _n(b)
    return None if a is None or b in (None, 0) else a / b


# ---------------------------------------------------------------- formule (Appendice A)
def piotroski(cur: dict, prev: dict) -> dict | None:
    """F-score 0-9. cur/prev: ni, cfo, assets, ltd, ca, cl, shares, revenue, gross. I criteri senza dati non contano; sotto 6 criteri valutabili → None."""
    pt, tot = [], []

    def test(nome, a, b=None, cmp=None):
        if a is None:
            return
        if cmp == "gt0":
            ok = a > 0
        else:
            if b is None:
                return
            ok = (a > b) if cmp == "up" else (a < b) if cmp == "down" else (a <= b)
        tot.append(nome)
        if ok:
            pt.append(nome)
    roa_c, roa_p = _div(cur.get("ni"), cur.get("assets")), _div(prev.get("ni"), prev.get("assets"))
    cfo_c = _n(cur.get("cfo"))
    test("ROA positivo", roa_c, cmp="gt0")
    test("flusso di cassa operativo positivo", cfo_c, cmp="gt0")
    test("ROA in crescita", roa_c, roa_p, "up")
    ni_c = _n(cur.get("ni"))
    if cfo_c is not None and ni_c is not None:
        tot.append("flusso operativo > utile")
        if cfo_c > ni_c:
            pt.append("flusso operativo > utile")
    lev_c, lev_p = _div(cur.get("ltd"), cur.get("assets")), _div(prev.get("ltd"), prev.get("assets"))
    test("leva in calo", lev_c, lev_p, "down")
    cr_c, cr_p = _div(cur.get("ca"), cur.get("cl")), _div(prev.get("ca"), prev.get("cl"))
    test("current ratio in aumento", cr_c, cr_p, "up")
    sh_c, sh_p = _n(cur.get("shares")), _n(prev.get("shares"))
    if sh_c is not None and sh_p is not None:
        tot.append("nessuna nuova emissione")
        if sh_c <= sh_p * 1.005:
            pt.append("nessuna nuova emissione")
    gm_c, gm_p = _div(cur.get("gross"), cur.get("revenue")), _div(prev.get("gross"), prev.get("revenue"))
    test("margine lordo in aumento", gm_c, gm_p, "up")
    at_c, at_p = _div(cur.get("revenue"), cur.get("assets")), _div(prev.get("revenue"), prev.get("assets"))
    test("rotazione dell'attivo in aumento", at_c, at_p, "up")
    if len(tot) < 6:
        return None
    return {"score": len(pt), "su": len(tot), "ok": pt, "ko": [t for t in tot if t not in pt]}


def altman(x: dict, manifatturiera: bool = True) -> dict | None:
    """Z (manifatturiere) o Z'' (altre). x: ca, cl, assets, retained, ebit, cap, liab, revenue, equity_book. Banche e assicurazioni: non usare."""
    A, L = _n(x.get("assets")), _n(x.get("liab"))
    if not A or not L:
        return None
    wc, re_, ebit = _n(x.get("ca")), _n(x.get("retained")), _n(x.get("ebit"))
    cl = _n(x.get("cl"))
    if None in (wc, cl, re_, ebit):
        return None
    x1, x2, x3 = (wc - cl) / A, re_ / A, ebit / A
    if manifatturiera:
        cap, rev = _n(x.get("cap")), _n(x.get("revenue"))
        if cap is None or rev is None:
            return None
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * cap / L + 1.0 * rev / A
        zona = "critica" if z < 1.81 else "sicura" if z > 2.99 else "grigia"
        return {"z": round(z, 2), "tipo": "Z", "zona": zona}
    eq = _n(x.get("equity_book"))
    if eq is None:
        return None
    z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * eq / L
    return {"z": round(z, 2), "tipo": "Z''", "zona": "critica" if z < 1.1 else "sicura" if z > 2.6 else "grigia"}


def mesi_cassa(cassa, fcf_trimestre):
    """(cassa + investimenti a breve) / consumo trimestrale × 3, solo se il flusso di cassa libero è negativo."""
    c, f = _n(cassa), _n(fcf_trimestre)
    if c is None or f is None or f >= 0:
        return None
    return round(c / (-f) * 3, 1)


def diluizione(azioni_oggi, azioni_1a):
    return _div(azioni_oggi, azioni_1a) and (_n(azioni_oggi) / _n(azioni_1a) - 1)


def accruals(utile, cfo, attivo_medio):
    u, c = _n(utile), _n(cfo)
    return None if u is None or c is None else _div(u - c, attivo_medio)


def sue(eps_eff, eps_att, storico_sorprese=None):
    """(EPS effettivo − atteso) / dev. standard delle sorprese degli ultimi 8 trimestri; senza storico: sorpresa % semplice."""
    e, a = _n(eps_eff), _n(eps_att)
    if e is None or a is None:
        return None
    if storico_sorprese is not None and len([s for s in storico_sorprese if _n(s) is not None]) >= 4:
        sd = float(np.std([float(s) for s in storico_sorprese if _n(s) is not None][-8:], ddof=1))
        if sd > 0:
            return {"sue": round((e - a) / sd, 2), "tipo": "sue"}
    return {"sue": None if a == 0 else round((e - a) / abs(a), 3), "tipo": "pct"}


def momentum_12_1(p_1m_fa, p_12m_fa):
    return _div(p_1m_fa, p_12m_fa) and (_n(p_1m_fa) / _n(p_12m_fa) - 1)


def eccesso(r_titolo, r_etf, beta):
    if None in (_n(r_titolo), _n(r_etf)):
        return None
    return float(r_titolo) - (_n(beta) if _n(beta) is not None else 1.0) * float(r_etf)


def freccia(ora, prima):
    """▲ / ▼ / = per il confronto di un valore con un valore precedente."""
    o, p = _n(ora), _n(prima)
    if o is None or p in (None, 0):
        return None
    v = o / abs(p) - 1
    return {"var": round(v, 4), "f": "▲" if v > 0.005 else "▼" if v < -0.005 else "="}


def rapporti(cap, ricavi_ttm, utile_ttm, ricavi_attesi, utile_atteso, rpo=None, ev=None, ebitda=None):
    """P/S, P/E, P/S previsto, P/E previsto, EV/EBITDA, capitalizzazione/RPO, RPO/ricavi annui («anni di fatturato già firmati»)."""
    ps = _div(cap, ricavi_ttm)
    pe = _div(cap, utile_ttm) if (_n(utile_ttm) or 0) > 0 else None
    psf = _div(cap, ricavi_attesi) if (_n(ricavi_attesi) or 0) > 0 else None
    pef = _div(cap, utile_atteso) if (_n(utile_atteso) or 0) > 0 else None
    eve = _div(ev, ebitda) if (_n(ebitda) or 0) > 0 else None
    return {"ps": ps, "pe": pe, "ps_f": psf, "pe_f": pef, "ev_ebitda": eve, "cap_rpo": _div(cap, rpo), "rpo_anni": _div(rpo, ricavi_ttm)}


# ---------------------------------------------------------------- SEC EDGAR (USA)
def rpo_da_facts(facts: dict, asof: str | None = None) -> dict | None:
    """Ultimo valore di RevenueRemainingPerformanceObligation (contratti firmati non ancora fatturati) con data di deposito (`filed`) ≤ asof."""
    try:
        units = facts["facts"]["us-gaap"]["RevenueRemainingPerformanceObligation"]["units"]["USD"]
    except (KeyError, TypeError):
        return None
    righe = [r for r in units if r.get("form") in ("10-Q", "10-K") and (asof is None or r.get("filed", "9999") <= asof)]
    if not righe:
        return None
    righe.sort(key=lambda r: (r["end"], r.get("filed", "")))
    u = righe[-1]
    prec = [r for r in righe if r["end"] < u["end"]]
    anno = [r for r in prec if 330 <= (np.datetime64(u["end"]) - np.datetime64(r["end"])).astype(int) <= 400]
    return {"rpo": float(u["val"]), "fine": u["end"], "deposito": u.get("filed"), "rpo_1a": float(anno[-1]["val"]) if anno else None}


ITEM_8K = {
    "1.01": ("contratto rilevante firmato", "pos"), "1.02": ("contratto rilevante terminato", "neg"), "1.03": ("fallimento", "neg"),
    "2.02": ("risultati trimestrali", "neu"), "2.05": ("costi di ristrutturazione", "neg"), "2.06": ("svalutazione rilevante", "neg"),
    "3.01": ("avviso di delisting", "neg"), "4.01": ("cambio del revisore", "neg"), "4.02": ("bilanci non affidabili (restatement)", "neg"),
    "5.02": ("uscita o nomina di dirigenti", "neu"), "7.01": ("comunicazione (Reg FD)", "neu"), "8.01": ("altro evento", "neu"), "1.05": ("incidente informatico", "neg"),
}


def eventi_8k(submissions: dict, giorni: int = 30, oggi: str | None = None) -> list[dict]:
    """8-K recenti dalle «submissions» SEC: data, item, significato."""
    try:
        r = submissions["filings"]["recent"]
        forme, date, items, acc = r["form"], r["filingDate"], r.get("items", [""] * len(r["form"])), r.get("accessionNumber", [""] * len(r["form"]))
    except (KeyError, TypeError):
        return []
    oggi_d = np.datetime64(oggi) if oggi else np.datetime64("today")
    out = []
    for f, d, it, a in zip(forme, date, items, acc):
        if f != "8-K" or (oggi_d - np.datetime64(d)).astype(int) > giorni:
            continue
        for code in [c.strip() for c in str(it).split(",") if c.strip()]:
            if code in ITEM_8K:
                out.append({"data": d, "item": code, "evento": ITEM_8K[code][0], "tono": ITEM_8K[code][1], "acc": a})
    return out


FORME_DILUIZIONE = ("S-3", "S-3ASR", "F-3", "F-3ASR", "424B5", "424B4", "S-1")


def moduli_diluizione(submissions: dict, giorni: int = 90, oggi: str | None = None) -> list[dict]:
    """Moduli con cui un'azienda si prepara a emettere nuove azioni (registrazione a scaffale S-3, supplemento 424B5, S-1), nei `giorni` indicati.
    Restituisce voci nello stesso formato degli 8-K con item «DIL», così Saldi e Opportunità le trattano insieme."""
    try:
        r = submissions["filings"]["recent"]
        forme, date, acc = r["form"], r["filingDate"], r.get("accessionNumber", [""] * len(r["form"]))
    except (KeyError, TypeError):
        return []
    oggi_d = np.datetime64(oggi) if oggi else np.datetime64("today")
    out = []
    for f, d, a in zip(forme, date, acc):
        if f in FORME_DILUIZIONE and 0 <= (oggi_d - np.datetime64(d)).astype(int) <= giorni:
            out.append({"data": d, "item": "DIL", "evento": f"deposito {f} (nuove azioni)", "tono": "neg", "acc": a, "form": f})
    return out


def rd_da_facts(facts: dict, asof: str | None = None) -> dict | None:
    """Spesa annua in ricerca e sviluppo (ResearchAndDevelopmentExpense, bilancio annuale 10-K) con data di deposito ≤ asof, e quella dell'anno prima."""
    try:
        units = facts["facts"]["us-gaap"]["ResearchAndDevelopmentExpense"]["units"]["USD"]
    except (KeyError, TypeError):
        return None
    righe = []
    for r in units:
        try:
            durata = (np.datetime64(r["end"]) - np.datetime64(r["start"])).astype(int)
        except (KeyError, ValueError):
            continue
        if r.get("form") in ("10-K", "10-K/A") and 350 <= durata <= 380 and (asof is None or r.get("filed", "9999") <= asof):
            righe.append(r)
    if not righe:
        return None
    righe.sort(key=lambda r: (r["end"], r.get("filed", "")))
    u = righe[-1]
    prec = [r for r in righe if 330 <= (np.datetime64(u["end"]) - np.datetime64(r["end"])).astype(int) <= 400]
    return {"rd": float(u["val"]), "fine": u["end"], "deposito": u.get("filed"), "rd_1a": float(prec[-1]["val"]) if prec else None}


def trova_ex99(indice: dict) -> str | None:
    """Dal file index.json di un deposito, il nome del comunicato stampa (Exhibit 99.1): ex99-1.htm, ex-99_1.htm, exhibit991.htm…"""
    import re
    try:
        nomi = [x["name"] for x in indice["directory"]["item"]]
    except (KeyError, TypeError):
        return None
    cand = [n for n in nomi if re.search(r"ex[-_]?99[-_.]?0?1|exhibit[-_]?99[-_.]?0?1|ex99", n, re.I) and n.lower().endswith((".htm", ".html", ".txt"))]
    return sorted(cand, key=len)[0] if cand else None


def testo_pulito(grezzo: str, massimo: int = 4000) -> str:
    """Testo leggibile dell'inizio di un comunicato: via tag, script, spazi doppi e le formule di rito."""
    import html as _html
    import re
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", grezzo or "")
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(?i)^(exhibit 99\.1\s*)?(for immediate release|news release|press release)\s*[:\-]?\s*", "", t)
    return t[:massimo]


def comunicato_8k(cik: str, acc: str, get_json=None, get_testo=None) -> str | None:
    """Testo (primi 4.000 caratteri) del comunicato allegato a un 8-K. `acc` come in EDGAR (0001234567-26-000123)."""
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"
    gj = get_json or sec_json
    gt = get_testo or sec_testo
    nome = trova_ex99(gj(base + "index.json") or {})
    if not nome:
        return None
    raw = gt(base + nome)
    return testo_pulito(raw) if raw else None


def notizia_da_comunicato(testo: str, data: str, link: str) -> dict:
    """Il comunicato come se fosse una notizia: titolo = primi 400 caratteri (titolo e sottotitolo), riassunto = il resto fino a 4.000 (per gli importi)."""
    return {"title": testo[:400], "summary": testo[400:4000], "time": data + "T00:00:00Z", "source": "SEC 8-K (comunicato)", "link": link}


ITEM_COMUNICATO = ("1.01", "2.02", "7.01", "8.01", "5.02", "2.05", "2.06")


def _sec_headers() -> dict | None:
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"} if ua else None


def cik_map() -> dict:
    """ticker → CIK a 10 cifre (file ufficiale SEC). Vuoto senza segreto SEC_USER_AGENT."""
    h = _sec_headers()
    if not h:
        return {}
    import requests
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=h, timeout=40)
    r.raise_for_status()
    return {v["ticker"].upper(): f"{int(v['cik_str']):010d}" for v in r.json().values()}


def titoli_sec() -> list[tuple[str, str, str]]:
    """Elenco ufficiale SEC delle società quotate: (ticker, CIK a 10 cifre, nome). Serve ad abbinare i titolari dei brevetti ai simboli di Borsa."""
    h = _sec_headers()
    if not h:
        return []
    import requests
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=h, timeout=40)
    r.raise_for_status()
    return [(v["ticker"].upper(), f"{int(v['cik_str']):010d}", v["title"]) for v in r.json().values()]


def sec_json(url: str):
    h = _sec_headers()
    if not h:
        return None
    import requests
    time.sleep(0.12)   # massimo 10 richieste al secondo
    r = requests.get(url, headers=h, timeout=40)
    return r.json() if r.status_code == 200 else None


def sec_testo(url: str) -> str | None:
    h = _sec_headers()
    if not h:
        return None
    import requests
    time.sleep(0.12)
    r = requests.get(url, headers=h, timeout=40)
    return r.text[:200000] if r.status_code == 200 else None


# ---------------------------------------------------------------- yfinance (tutti i mercati)
ALIAS = {
    "ni": ("Net Income", "Net Income Common Stockholders"), "revenue": ("Total Revenue", "Operating Revenue"), "gross": ("Gross Profit",),
    "cfo": ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"), "assets": ("Total Assets",), "ca": ("Current Assets", "Total Current Assets"),
    "cl": ("Current Liabilities", "Total Current Liabilities"), "ltd": ("Long Term Debt", "Long Term Debt And Capital Lease Obligation"),
    "shares": ("Ordinary Shares Number", "Share Issued"), "retained": ("Retained Earnings",), "ebit": ("EBIT", "Operating Income"),
    "liab": ("Total Liabilities Net Minority Interest", "Total Liabilities"), "equity_book": ("Stockholders Equity", "Common Stock Equity"),
    "cash": ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"), "fcf": ("Free Cash Flow",), "ebitda": ("EBITDA",),
    "interest": ("Interest Expense",), "debt": ("Total Debt",),
}


def _riga(df, nomi, col):
    if df is None or getattr(df, "empty", True) or col >= df.shape[1]:
        return None
    for n in nomi:
        if n in df.index:
            return _n(df.loc[n].iloc[col])
    return None


def estrai(df_list: list, col: int) -> dict:
    """Unisce income/balance/cashflow in un solo dizionario per la colonna `col` (0 = ultimo periodo)."""
    out = {}
    for k, nomi in ALIAS.items():
        for df in df_list:
            v = _riga(df, nomi, col)
            if v is not None:
                out[k] = v
                break
    return out


INFO_CAMPI = ("longName", "sector", "industry", "country", "currency", "marketCap", "trailingPE", "forwardPE", "priceToSalesTrailing12Months", "enterpriseValue",
              "enterpriseToRevenue", "enterpriseToEbitda", "grossMargins", "operatingMargins", "profitMargins", "revenueGrowth", "earningsGrowth", "debtToEquity",
              "currentRatio", "freeCashflow", "totalCash", "returnOnEquity", "shortPercentOfFloat", "heldPercentInsiders", "targetMeanPrice", "targetLowPrice",
              "targetHighPrice", "recommendationMean", "numberOfAnalystOpinions", "sharesOutstanding", "totalRevenue", "forwardEps", "trailingEps", "bookValue", "priceToBook", "longBusinessSummary")


def da_yf(ticker: str) -> dict | None:
    """Fondamentali di un titolo da yfinance (lento: una chiamata per titolo). Cache di 7 giorni in data/_cache/fond/."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / (ticker.replace("/", "_") + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < CACHE_GIORNI * 86400:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}
        qi, qb, qc = t.quarterly_income_stmt, t.quarterly_balance_sheet, t.quarterly_cashflow
        ai, ab, ac = t.income_stmt, t.balance_sheet, t.cashflow
    except Exception:  # noqa: BLE001
        return None
    d = {"info": {k: info.get(k) for k in INFO_CAMPI if info.get(k) is not None}, "ts": time.time()}
    if d["info"].get("longBusinessSummary"):
        d["info"]["longBusinessSummary"] = d["info"]["longBusinessSummary"][:700]
    q = [qi, qb, qc]
    d["q"] = [estrai(q, i) for i in range(min(5, qi.shape[1] if qi is not None and not qi.empty else 0))]
    a = [ai, ab, ac]
    d["a0"], d["a1"] = estrai(a, 0), estrai(a, 1)
    try:
        d["analisti"] = {"rev_stima": _n(t.revenue_estimate.loc["+1y", "avg"]) if "+1y" in t.revenue_estimate.index else None,
                         "eps_stima": _n(t.earnings_estimate.loc["+1y", "avg"]) if "+1y" in t.earnings_estimate.index else None}
    except Exception:  # noqa: BLE001
        d["analisti"] = {}
    try:   # revisioni delle stime EPS a +1 anno (corrente contro 30 e 90 giorni fa) e rapporto su/giù degli ultimi 30 giorni
        tr, rv = t.eps_trend, t.eps_revisions
        riga = "+1y" if "+1y" in tr.index else None
        if riga:
            cur = _n(tr.loc[riga, "current"])
            d["revisioni"] = {"eps": cur, "eps_30": _n(tr.loc[riga, "30daysAgo"]), "eps_90": _n(tr.loc[riga, "90daysAgo"]),
                              "su": _n(rv.loc[riga, "upLast30days"]) if rv is not None and riga in rv.index else None,
                              "giu": _n(rv.loc[riga, "downLast30days"]) if rv is not None and riga in rv.index else None}
    except Exception:  # noqa: BLE001
        d["revisioni"] = None
    try:   # sorprese delle ultime trimestrali (EPS effettivo e atteso)
        eh = t.earnings_history
        d["sorprese"] = [[_n(a), _n(b)] for a, b in zip(eh["epsActual"].tolist(), eh["epsEstimate"].tolist())] if eh is not None and not eh.empty else None
    except Exception:  # noqa: BLE001
        d["sorprese"] = None
    try:   # prossima trimestrale
        cal = t.calendar
        ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
        d["prossima_trimestrale"] = str(ed[0]) if ed else None
    except Exception:  # noqa: BLE001
        d["prossima_trimestrale"] = None
    try:
        ins = t.insider_purchases
        d["insider_acq_90g"] = int(_n(ins.iloc[0, 1]) or 0) if ins is not None and not ins.empty else None
    except Exception:  # noqa: BLE001
        d["insider_acq_90g"] = None
    try:
        f.write_text(json.dumps(d, default=lambda o: None), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return d


def indicatori(d: dict, rpo: dict | None = None, rd: dict | None = None) -> dict:
    """Tutti gli indicatori del titolo a partire da `da_yf` (e, per gli USA, dall'RPO SEC)."""
    info, q = d.get("info", {}), d.get("q", [])
    cap = _n(info.get("marketCap"))
    ric_q = [_n(x.get("revenue")) for x in q]
    ttm = sum(ric_q[:4]) if len(ric_q) >= 4 and None not in ric_q[:4] else _n(info.get("totalRevenue"))
    ut_q = [_n(x.get("ni")) for x in q]
    ut_ttm = sum(ut_q[:4]) if len(ut_q) >= 4 and None not in ut_q[:4] else None
    a0, a1 = d.get("a0", {}), d.get("a1", {})
    banca = (info.get("sector") == "Financial Services")
    fcf_q = _n(q[0].get("fcf")) if q else None
    cassa = _n(q[0].get("cash")) if q else _n(info.get("totalCash"))
    an = d.get("analisti", {})
    ricavi_att = an.get("rev_stima")
    utile_att = (an.get("eps_stima") or 0) * (_n(info.get("sharesOutstanding")) or 0) or None
    rapp = rapporti(cap, ttm, ut_ttm, ricavi_att, utile_att, rpo.get("rpo") if rpo else None, info.get("enterpriseValue"), a0.get("ebitda"))
    x = dict(a0)
    x["cap"] = cap
    ebit, intr = _n(a0.get("ebit")), _n(a0.get("interest"))
    return {
        "nome": info.get("longName"), "valuta": info.get("currency"), "settore": info.get("sector"), "industria": info.get("industry"), "paese": info.get("country"), "cap": cap,
        "ricavi_q": ric_q[0] if ric_q else None, "ricavi_q_1a": freccia(ric_q[0], ric_q[4]) if len(ric_q) >= 5 else None,
        "ricavi_q_prec": freccia(ric_q[0], ric_q[1]) if len(ric_q) >= 2 else None, "ricavi_ttm": ttm, "utile_ttm": ut_ttm, **rapp,
        "piotroski": piotroski(a0, a1) if a0 and a1 else None,
        "altman": None if banca else altman(x, manifatturiera=(info.get("sector") in ("Industrials", "Basic Materials", "Consumer Cyclical", "Consumer Defensive", "Technology"))),
        "copertura_interessi": None if not ebit or not intr else round(ebit / abs(intr), 1),
        "debito_netto_ebitda": None if banca or not a0.get("ebitda") else _div((_n(a0.get("debt")) or 0) - (_n(cassa) or 0), a0.get("ebitda")),
        "current_ratio": _n(info.get("currentRatio")), "margine_lordo": _n(info.get("grossMargins")), "margine_fcf": _div(info.get("freeCashflow"), ttm),
        "roe": _n(info.get("returnOnEquity")), "mesi_cassa": mesi_cassa(cassa, fcf_q), "diluizione": diluizione(a0.get("shares"), a1.get("shares")),
        "accruals": accruals(a0.get("ni"), a0.get("cfo"), _n(a0.get("assets"))), "rpo": rpo, "banca": banca,
        "rd": rd, "rd_cap": _div(rd["rd"], cap) if rd else None, "rd_ricavi": _div(rd["rd"], ttm) if rd else None,
        "rd_crescita": (_div(rd["rd"], rd["rd_1a"]) - 1) if rd and rd.get("rd_1a") else None,
        "analisti": {"raccomandazione": _n(info.get("recommendationMean")), "target": _n(info.get("targetMeanPrice")), "target_min": _n(info.get("targetLowPrice")),
                     "target_max": _n(info.get("targetHighPrice")), "n": _n(info.get("numberOfAnalystOpinions"))},
        "short_float": _n(info.get("shortPercentOfFloat")), "insider_acq_90g": d.get("insider_acq_90g"),
        "rev_eps_30": _div((d.get("revisioni") or {}).get("eps"), (d.get("revisioni") or {}).get("eps_30")) and _n(_div((d.get("revisioni") or {}).get("eps"), (d.get("revisioni") or {}).get("eps_30")) - 1),
        "rev_eps_90": _div((d.get("revisioni") or {}).get("eps"), (d.get("revisioni") or {}).get("eps_90")) and _n(_div((d.get("revisioni") or {}).get("eps"), (d.get("revisioni") or {}).get("eps_90")) - 1),
        "rev_su": (d.get("revisioni") or {}).get("su"), "rev_giu": (d.get("revisioni") or {}).get("giu"),
        "sue": (sue(d["sorprese"][0][0], d["sorprese"][0][1], [(a - b) for a, b in d["sorprese"] if a is not None and b is not None]) if d.get("sorprese") and d["sorprese"][0][0] is not None else None),
        "crescita_ricavi": _n(info.get("revenueGrowth")), "gross_su_attivo": _div(a0.get("gross"), a0.get("assets")),
        "prossima_trimestrale": d.get("prossima_trimestrale"), "descrizione": info.get("longBusinessSummary"), "sw": info.get("industry") in ("Software - Application", "Software - Infrastructure"),
    }
