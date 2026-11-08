"""Salute delle aziende in VWCE: bilanci delle prime 30 aziende per peso (Yahoo Finance, scaricati in GitHub Actions una volta a settimana).

- Lista: ~45 grandi aziende candidate. Il peso in VWCE si stima dalla capitalizzazione (VWCE pesa le aziende per capitalizzazione):
  peso ≈ capitalizzazione / capitalizzazione di riferimento × peso noto di riferimento (data/holdings.json, altrimenti NVIDIA 5,0%).
  Si tengono le prime 30. Se Yahoo non dà le capitalizzazioni, si usa l'ordine della lista statica.
- Dati: fatturato, utile netto, utile operativo (→ margine operativo), debito totale, liquidità.
- Confronto con un anno prima (YoY): ultimo trimestre contro lo stesso trimestre dell'anno precedente se Yahoo ne dà almeno 5,
  altrimenti ultimo anno fiscale contro il precedente.
- Etichetta (regola fissa, decisa prima di vedere i dati), un punto per ciascuno:
  fatturato +3% o più (+1) / -3% o meno (-1); utile netto +5% o più (+1) / -5% o meno (-1); margine operativo +1 punto (+1) / -1 punto (-1);
  debito netto su fatturato giù di 0,05 (+1) / su di 0,05 (-1). Totale ≥ +2 «In miglioramento», ≤ -2 «In peggioramento», altrimenti «Stabile».
Se un'azienda non risponde si tiene il dato della settimana prima (segnalato); l'app non si blocca mai."""
import html as _h
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import DATA

FILE = DATA / "aziende.json"
GIORNI = 1   # bilanci riletti ogni giorno (le trimestrali escono in date diverse)
# (simbolo Yahoo, nome) in ordine indicativo di peso; la stima dalla capitalizzazione riordina
CANDIDATE = [
    ("NVDA", "NVIDIA"), ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("AMZN", "Amazon"), ("GOOGL", "Alphabet (Google)"), ("META", "Meta"),
    ("AVGO", "Broadcom"), ("TSM", "TSMC"), ("TSLA", "Tesla"), ("BRK-B", "Berkshire Hathaway"), ("JPM", "JPMorgan Chase"), ("LLY", "Eli Lilly"),
    ("MU", "Micron"), ("V", "Visa"), ("ORCL", "Oracle"), ("WMT", "Walmart"), ("MA", "Mastercard"), ("XOM", "Exxon Mobil"), ("NFLX", "Netflix"),
    ("JNJ", "Johnson & Johnson"), ("COST", "Costco"), ("ASML", "ASML"), ("005930.KS", "Samsung Electronics"), ("TCEHY", "Tencent"),
    ("HD", "Home Depot"), ("PG", "Procter & Gamble"), ("ABBV", "AbbVie"), ("BAC", "Bank of America"), ("PLTR", "Palantir"), ("AMD", "AMD"),
    ("UNH", "UnitedHealth"), ("KO", "Coca-Cola"), ("SAP", "SAP"), ("CVX", "Chevron"), ("CSCO", "Cisco"), ("IBM", "IBM"), ("GE", "GE Aerospace"),
    ("WFC", "Wells Fargo"), ("CRM", "Salesforce"), ("BABA", "Alibaba"), ("TM", "Toyota"), ("ROG.SW", "Roche"), ("NESN.SW", "Nestlé"),
    ("AZN", "AstraZeneca"), ("MS", "Morgan Stanley"), ("LIN", "Linde"), ("PM", "Philip Morris"),
]
NOMI = dict(CANDIDATE)
# valuta dei bilanci quando è diversa da quella di quotazione (ADR); le altre usano la valuta di quotazione
VALUTA_BILANCIO = {"TSM": "TWD", "ASML": "EUR", "SAP": "EUR", "TCEHY": "CNY", "BABA": "CNY", "TM": "JPY", "005930.KS": "KRW",
                   "ROG.SW": "CHF", "NESN.SW": "CHF", "AZN": "USD"}
RIF_DEFAULT = ("NVDA", 5.0)
ETICHETTE = {1: "In miglioramento", 0: "Stabile", -1: "In peggioramento"}


# ---------------------------------------------------------------- analisi (pura, testabile senza rete)
MESI_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _riga(df, nomi):
    if df is None or getattr(df, "empty", True):
        return None
    for n in nomi:
        if n in df.index:
            s = pd.to_numeric(df.loc[n], errors="coerce")
            if isinstance(s, pd.DataFrame):
                s = s.iloc[0]
            s.index = pd.to_datetime(s.index, errors="coerce")
            return s
    return None


def _date_valide(df, nomi=("Total Revenue", "Operating Revenue")) -> list:
    """Date (dalla più recente) in cui la voce principale è presente."""
    s = _riga(df, nomi)
    if s is None:
        return []
    return sorted([d for d, v in s.items() if pd.notna(d) and pd.notna(v)], reverse=True)


def _v(s, d):
    if s is None or d is None:
        return None
    try:
        x = s.get(d, np.nan)
        return None if pd.isna(x) else float(x)
    except Exception:  # noqa: BLE001
        return None


def _pct(a, b):
    if a is None or b is None or b == 0:
        return None
    if b < 0:   # base negativa: la variazione percentuale non ha senso, conta solo il segno del miglioramento
        return 100.0 if a > b else -100.0
    return (a / b - 1) * 100


def etichetta_periodo(fine, mesi: int) -> str:
    """«lug-set 2026» per un trimestre che finisce a settembre 2026; «gen-giu 2026» per un semestre."""
    try:
        f = pd.Timestamp(fine)
        if f.day < 15:   # trimestri fiscali che finiscono nei primi giorni del mese (es. 2 novembre) appartengono al mese prima
            f = f - pd.DateOffset(days=f.day)
        i = pd.Timestamp(f.year, f.month, 1) - pd.DateOffset(months=mesi - 1)
        a = f"{MESI_IT[i.month - 1]}{' ' + str(i.year) if i.year != f.year else ''}"
        return f"{a}-{MESI_IT[f.month - 1]} {f.year}"
    except Exception:  # noqa: BLE001
        return str(fine)[:7]


def _flussi(df, d0, d1):
    rev, ni = _riga(df, ("Total Revenue", "Operating Revenue")), _riga(df, ("Net Income", "Net Income Common Stockholders"))
    op = _riga(df, ("Operating Income", "Total Operating Income As Reported"))
    o = {"rev": _v(rev, d0), "ni": _v(ni, d0), "op": _v(op, d0), "rev_prev": _v(rev, d1), "ni_prev": _v(ni, d1), "op_prev": _v(op, d1)}
    o["opm"] = o["op"] / o["rev"] * 100 if o["op"] is not None and o["rev"] else None
    o["opm_prev"] = o["op_prev"] / o["rev_prev"] * 100 if o["op_prev"] is not None and o["rev_prev"] else None
    o["rev_g"], o["ni_g"] = _pct(o["rev"], o["rev_prev"]), _pct(o["ni"], o["ni_prev"])
    o["opm_d"] = o["opm"] - o["opm_prev"] if o["opm"] is not None and o["opm_prev"] is not None else None
    return o


def _anno_prima(dates, d0):
    return next((d for d in dates if d < d0 and 330 <= (d0 - d).days <= 400), None)


def analizza(inc_q=None, inc_a=None, bal_q=None, bal_a=None) -> dict:
    """Ultima trimestrale (sempre, con la durata del periodo), ultimo anno fiscale, bilancio, fatturato degli ultimi 12 mesi ed etichetta.
    Accetta i DataFrame di yfinance (righe = voci, colonne = date di fine periodo)."""
    out: dict = {}
    dq = _date_valide(inc_q)
    if dq:
        d0 = dq[0]
        gap = (d0 - dq[1]).days if len(dq) > 1 else 91
        mesi = 3 if gap <= 120 else (6 if gap <= 200 else 12)
        d1 = _anno_prima(dq, d0)
        conf = "anno" if d1 is not None else ("precedente" if len(dq) > 1 else None)
        d1 = d1 if d1 is not None else (dq[1] if len(dq) > 1 else None)
        q = {"fine": d0.strftime("%Y-%m-%d"), "mesi": mesi, "tipo": {3: "trimestre", 6: "semestre", 12: "anno"}[mesi],
             "periodo": etichetta_periodo(d0, mesi), "conf": conf,
             "periodo_conf": etichetta_periodo(d1, mesi) if d1 is not None else None, **_flussi(inc_q, d0, d1)}
        dbq = _date_valide(bal_q, ("Total Debt", "Total Assets"))
        if dbq:
            b0 = dbq[0]
            b1 = _anno_prima(dbq, b0) if conf == "anno" else (dbq[1] if len(dbq) > 1 else None)
            b1 = b1 if b1 is not None else (dbq[1] if len(dbq) > 1 else None)
            debt, cash = _riga(bal_q, ("Total Debt",)), _riga(bal_q, ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"))
            q.update({"debt": _v(debt, b0), "cash": _v(cash, b0), "debt_prev": _v(debt, b1), "cash_prev": _v(cash, b1)})
        out["q"] = q
        # fatturato degli ultimi 12 mesi: somma di 4 trimestri consecutivi
        if mesi == 3 and len(dq) >= 4 and all(70 <= (dq[i] - dq[i + 1]).days <= 110 for i in range(3)):
            rv = _riga(inc_q, ("Total Revenue", "Operating Revenue"))
            out["rev_12m"], out["rev_12m_fonte"] = float(sum(rv[d] for d in dq[:4])), "somma degli ultimi 4 trimestri"
        elif mesi == 6 and len(dq) >= 2 and 150 <= (dq[0] - dq[1]).days <= 210:
            rv = _riga(inc_q, ("Total Revenue", "Operating Revenue"))
            out["rev_12m"], out["rev_12m_fonte"] = float(rv[dq[0]] + rv[dq[1]]), "somma degli ultimi 2 semestri"
    da = _date_valide(inc_a)
    if len(da) >= 1:
        a0 = da[0]
        a1 = _anno_prima(da, a0)
        out["a"] = {"fine": a0.strftime("%Y-%m-%d"), "periodo": etichetta_periodo(a0, 12), **_flussi(inc_a, a0, a1)}
        if "rev_12m" not in out and out["a"]["rev"]:
            out["rev_12m"], out["rev_12m_fonte"] = out["a"]["rev"], "ultimo anno fiscale"
        if "q" in out and out["q"].get("debt") is None:
            dba = _date_valide(bal_a, ("Total Debt", "Total Assets"))
            if dba:
                debt, cash = _riga(bal_a, ("Total Debt",)), _riga(bal_a, ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"))
                out["q"].update({"debt": _v(debt, dba[0]), "cash": _v(cash, dba[0])})
    if "q" not in out and "a" not in out:
        out["errore"] = "bilanci non disponibili"
        return out
    # base dell'etichetta: ultima trimestrale contro lo stesso periodo di un anno prima; se non c'è, l'anno fiscale
    if out.get("q", {}).get("conf") == "anno":
        b, out["base"] = out["q"], out["q"]["tipo"]
        out["periodo"], out["periodo_prec"] = out["q"]["periodo"], out["q"]["periodo_conf"]
    elif out.get("a") and out["a"].get("rev_prev") is not None:
        b, out["base"] = out["a"], "anno"
        out["periodo"], out["periodo_prec"] = out["a"]["periodo"], "anno fiscale precedente"
    else:
        b, out["base"] = out.get("q") or out["a"], "nessun confronto annuale"
        out["periodo"], out["periodo_prec"] = b.get("periodo"), b.get("periodo_conf")
    for k in ("rev", "rev_prev", "ni", "ni_prev", "op", "op_prev", "opm", "opm_prev", "rev_g", "ni_g", "opm_d"):
        out[k] = b.get(k)
    q = out.get("q", {})
    for k in ("debt", "cash", "debt_prev", "cash_prev"):
        out[k] = q.get(k)
    mult = 12 / (q.get("mesi") or 12)
    lev = lambda d, c, r: ((d or 0) - (c or 0)) / (r * mult) if d is not None and r else None
    l0, l1 = lev(out.get("debt"), out.get("cash"), q.get("rev")), lev(out.get("debt_prev"), out.get("cash_prev"), q.get("rev_prev"))
    out["lev_d"] = (l0 - l1) if l0 is not None and l1 is not None else None
    punti, motivi = 0, []
    for key, su, giu, testo in (("rev_g", 3, -3, "fatturato"), ("ni_g", 5, -5, "utile netto"), ("opm_d", 1, -1, "margine operativo")):
        x = out.get(key)
        if x is None:
            continue
        if x >= su:
            punti += 1
            motivi.append(f"{testo} in crescita")
        elif x <= giu:
            punti -= 1
            motivi.append(f"{testo} in calo")
    if out["lev_d"] is not None:
        if out["lev_d"] <= -0.05:
            punti += 1
            motivi.append("debito netto in calo rispetto al fatturato")
        elif out["lev_d"] >= 0.05:
            punti -= 1
            motivi.append("debito netto in aumento rispetto al fatturato")
    out["punteggio"] = punti
    out["stato"] = 1 if punti >= 2 else (-1 if punti <= -2 else 0)
    out["etichetta"] = ETICHETTE[out["stato"]]
    out["motivi"] = motivi
    # cosa è aumentato e cosa è diminuito nell'ultima trimestrale
    su, giu = [], []
    if q:
        for nome, a, b2 in (("fatturato", q.get("rev"), q.get("rev_prev")), ("utile netto", q.get("ni"), q.get("ni_prev")),
                            ("utile operativo", q.get("op"), q.get("op_prev")), ("margine operativo", q.get("opm"), q.get("opm_prev")),
                            ("debito", q.get("debt"), q.get("debt_prev")), ("liquidità", q.get("cash"), q.get("cash_prev"))):
            if a is None or b2 is None or a == b2:
                continue
            (su if a > b2 else giu).append(nome)
    out["aumentati"], out["diminuiti"] = su, giu
    return out


def valutazione(cap_usd, rev_12m, fx_bilancio, rpo=None) -> dict:
    """Capitalizzazione/fatturato (12 mesi) e capitalizzazione/(fatturato + contratti già firmati non ancora fatturati, RPO)."""
    out = {}
    if cap_usd and rev_12m and fx_bilancio:
        rv = rev_12m * fx_bilancio
        out["ps"] = cap_usd / rv if rv > 0 else None
        if rpo and rpo.get("usd"):
            out["ps_rpo"] = cap_usd / (rv + rpo["usd"])
            out["rpo_anni"] = rpo["usd"] / rv if rv > 0 else None
    return out


def pesi_stimati(caps: dict, rif: tuple | None = None) -> dict:
    """caps = {simbolo: capitalizzazione in $}; peso ≈ cap / cap_rif × peso_rif."""
    sym, w = rif or RIF_DEFAULT
    base = caps.get(sym)
    if not base:
        ok = {k: v for k, v in caps.items() if v}
        tot = sum(ok.values())
        return {k: v / tot * 40 for k, v in ok.items()} if tot else {}   # le prime ~45 aziende pesano circa il 40% di VWCE
    return {k: v / base * w for k, v in caps.items() if v}


def riepilogo(rows: list) -> dict:
    ok = [r for r in rows if r.get("stato") is not None and "errore" not in r]
    r = {"n": len(ok), "migliora": sum(1 for x in ok if x["stato"] == 1), "stabile": sum(1 for x in ok if x["stato"] == 0),
         "peggiora": sum(1 for x in ok if x["stato"] == -1)}
    tot = sum(x.get("peso") or 0 for x in ok)
    for k, s in (("peso_migliora", 1), ("peso_stabile", 0), ("peso_peggiora", -1)):
        r[k] = round(sum(x.get("peso") or 0 for x in ok if x["stato"] == s), 2)
    r["peso_totale"] = round(tot, 2)
    return r


# ---------------------------------------------------------------- download (solo GitHub Actions)
_fx: dict = {}


def _usd(cur: str) -> float | None:
    if not cur or cur.upper() == "USD":
        return 1.0
    if cur not in _fx:
        try:
            import yfinance as yf
            _fx[cur] = float(yf.Ticker(f"{cur.upper()}USD=X").fast_info["last_price"])
        except Exception:  # noqa: BLE001
            _fx[cur] = None
    return _fx[cur]


def _scarica(sym: str) -> dict:
    import yfinance as yf
    tk = yf.Ticker(sym)
    out: dict = {"sym": sym, "nome": NOMI.get(sym, sym)}
    try:
        fi = tk.fast_info
        cap, cur = float(fi["market_cap"]), str(fi.get("currency") or "USD")
        out["_cur"] = cur
        fx = _usd(cur)
        out["cap_usd"] = cap * fx if fx else None
    except Exception:  # noqa: BLE001
        out["cap_usd"] = None
    frames = {}
    for k, attr in (("inc_q", "quarterly_income_stmt"), ("inc_a", "income_stmt"), ("bal_q", "quarterly_balance_sheet"), ("bal_a", "balance_sheet")):
        try:
            frames[k] = getattr(tk, attr)
        except Exception:  # noqa: BLE001
            frames[k] = None
    out.update(analizza(**frames))
    out["valuta"] = VALUTA_BILANCIO.get(sym, out.get("_cur") or "USD")
    out["fx_bilancio"] = _usd(out["valuta"])
    out.pop("_cur", None)
    return out


# ---------------------------------------------------------------- contratti già firmati (RPO) dai bilanci depositati alla SEC (gratuito)
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_CONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/{tax}/{tag}.json"
RPO_TAGS = [("us-gaap", "RevenueRemainingPerformanceObligation"), ("ifrs-full", "TransactionPriceAllocatedToRemainingPerformanceObligations")]


def _sec_get(url: str):
    import os

    import requests
    ua = os.environ.get("SEC_USER_AGENT") or "Armor personal research armor-bot@users.noreply.github.com"   # la SEC chiede un nome e un contatto
    r = requests.get(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=25)
    r.raise_for_status()
    return r.json()


def parse_rpo(js: dict) -> dict | None:
    """Ultimo valore dei contratti già firmati non ancora fatturati (RPO) e quello di circa un anno prima."""
    units = (js or {}).get("units") or {}
    for cur, rows in units.items():
        pts = {}
        for r in rows:
            if r.get("form") in ("10-Q", "10-K", "20-F", "40-F", "6-K", "10-K/A", "10-Q/A") and r.get("end") and r.get("val") is not None:
                pts[r["end"]] = float(r["val"])   # a parità di data vale l'ultimo deposito
        if not pts:
            continue
        ds = sorted(pd.to_datetime(list(pts)), reverse=True)
        d0 = ds[0]
        d1 = next((d for d in ds if 330 <= (d0 - d).days <= 400), None)
        v0 = pts[d0.strftime("%Y-%m-%d")]
        v1 = pts[d1.strftime("%Y-%m-%d")] if d1 is not None else None
        return {"valore": v0, "valuta": cur, "data": d0.strftime("%Y-%m-%d"), "prec": v1, "crescita": _pct(v0, v1)}
    return None


def rpo_sec(syms: list) -> dict:
    """{simbolo: rpo} per le aziende che depositano i bilanci alla SEC. Richieste in fila (limite SEC: 10 al secondo)."""
    import time
    out = {}
    try:
        tick = _sec_get(SEC_TICKERS)
        cik = {str(v["ticker"]).upper(): int(v["cik_str"]) for v in tick.values()}
    except Exception as e:  # noqa: BLE001
        print("[aziende] elenco SEC non disponibile:", str(e)[:80], flush=True)
        return out
    for s in syms:
        c = cik.get(s.upper()) or cik.get(s.upper().replace("-", "."))
        if not c:
            continue
        for tax, tag in RPO_TAGS:
            time.sleep(0.15)
            try:
                r = parse_rpo(_sec_get(SEC_CONCEPT.format(cik=c, tax=tax, tag=tag)))
            except Exception:  # noqa: BLE001
                r = None
            if r:
                out[s] = r
                break
    return out


def _rif() -> tuple | None:
    """Peso e simbolo di riferimento da data/holdings.json (primo titolo con capitalizzazione)."""
    try:
        d = json.loads((DATA / "holdings.json").read_text(encoding="utf-8"))
        for x in d.get("top", []):
            if len(x) > 3 and x[2] and x[1]:
                return (str(x[2]), float(x[1]))
    except Exception:  # noqa: BLE001
        pass
    return None


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def aggiorna(force: bool = False, deadline: float = 200) -> dict:
    old = load()
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not force and old.get("date") and (pd.Timestamp(oggi) - pd.Timestamp(old["date"])).days < GIORNI:
        print("[aziende] bilanci già aggiornati il", old["date"], flush=True)
        return old
    from .guard import run_parallel
    res = run_parallel({s: (lambda s=s: _scarica(s)) for s, _n in CANDIDATE}, workers=6, deadline=deadline)
    prev = {r["sym"]: r for r in old.get("aziende", [])}
    rows = []
    for s, n in CANDIDATE:
        kind, v = res.get(s, ("err", "non eseguito"))
        if kind == "ok" and "errore" not in v:
            rows.append(v)
        elif s in prev and "errore" not in prev[s]:
            r = dict(prev[s])
            r["vecchio"] = True
            rows.append(r)
        else:
            rows.append({"sym": s, "nome": n, "errore": (v.get("errore") if isinstance(v, dict) else str(v))[:100], "cap_usd": (v.get("cap_usd") if isinstance(v, dict) else None)})
    caps = {r["sym"]: r.get("cap_usd") for r in rows}
    w = pesi_stimati(caps, _rif())
    for i, r in enumerate(rows):
        r["peso"] = round(w[r["sym"]], 2) if r["sym"] in w else None
        r["ordine_statico"] = i
    if w:
        rows.sort(key=lambda r: (-(r.get("peso") or 0), r["ordine_statico"]))
    rows = rows[:30]
    try:   # contratti già firmati (RPO) dalla SEC e rapporti capitalizzazione/fatturato
        rp = rpo_sec([r["sym"] for r in rows if "errore" not in r])
    except Exception as e:  # noqa: BLE001
        print("[aziende] RPO non letti:", str(e)[:80], flush=True)
        rp = {}
    for r in rows:
        if "errore" in r:
            continue
        rr = rp.get(r["sym"]) or (r.get("rpo") if r.get("vecchio") else None)
        if rr:
            rr = dict(rr)
            rr["usd"] = rr["valore"] * (_usd(rr["valuta"]) or 0) if rr.get("valore") else None
            r["rpo"] = rr
        r.update(valutazione(r.get("cap_usd"), r.get("rev_12m"), r.get("fx_bilancio"), r.get("rpo")))
    d = {"date": oggi, "fonte": "Yahoo Finance (bilanci trimestrali e annuali); contratti già firmati (RPO): SEC EDGAR", "pesi": "stimati dalla capitalizzazione" if w else "ordine indicativo",
         "aziende": rows, "riepilogo": riepilogo(rows)}
    if d["riepilogo"]["n"] == 0 and old.get("aziende"):
        print("[aziende] nessun bilancio scaricato: tengo i dati precedenti", flush=True)
        return old
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=0, default=lambda x: None), encoding="utf-8")
    print(f"[aziende] bilanci: {d['riepilogo']['n']}/30 aziende, {d['riepilogo']['migliora']} in miglioramento, "
          f"{d['riepilogo']['stabile']} stabili, {d['riepilogo']['peggiora']} in peggioramento", flush=True)
    return d


# ---------------------------------------------------------------- pagina
SIMB = {"USD": "$", "EUR": "€", "CHF": "CHF", "JPY": "¥", "TWD": "TWD", "KRW": "KRW", "CNY": "CNY"}


def _num(x, dec=1):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mld(x, cur):
    if x is None:
        return "n.d."
    return f"{_num(x / 1e9)} mld {SIMB.get(cur, cur or '')}".strip()


def _var(x, unit="%", dec=0):
    if x is None:
        return "<span class='mu'>n.d.</span>"
    cls = "azup" if x > 0 else ("azdn" if x < 0 else "")
    return f"<b class='{cls}'>{'+' if x > 0 else ''}{_num(x, dec)}{unit}</b>"


def _var_inv(x, unit="%", dec=0):
    """Per il debito: in aumento = rosso."""
    if x is None:
        return ""
    cls = "azdn" if x > 0 else ("azup" if x < 0 else "")
    return f" <b class='{cls}'>{'+' if x > 0 else ''}{_num(x, dec)}{unit}</b>"


def _card(i: int, a: dict) -> str:
    e = _h.escape
    peso = f"peso ≈ {_num(a['peso'])}%" if a.get("peso") else ""
    if "errore" in a:
        return (f"<div class='azc'><div class='azh'><b>{i}. {e(a.get('nome', a['sym']))}</b><span class='mu'>{peso}</span></div>"
                f"<div class='mu'>Bilanci non disponibili oggi ({e(a['errore'])}).</div></div>")
    cls = {1: "ok", 0: "warn", -1: "bad"}[a["stato"]]
    cur = a.get("valuta")
    q, an = a.get("q") or {}, a.get("a") or {}
    body = ""
    if q:
        durata = {3: "3 mesi", 6: "6 mesi (l'azienda pubblica i conti ogni semestre)", 12: "12 mesi"}[q["mesi"]]
        nome_p = {3: "Ultima trimestrale", 6: "Ultima semestrale", 12: "Ultimo periodo"}[q["mesi"]]
        conf = (f"confronto con {e(q['periodo_conf'])} (stesso periodo di un anno prima)" if q.get("conf") == "anno" else
                (f"confronto con {e(q['periodo_conf'])} (periodo precedente: Yahoo non ha lo stesso periodo dell'anno prima)" if q.get("conf") else "nessun confronto disponibile"))
        dg = _pct(q.get("debt"), q.get("debt_prev"))
        cg = _pct(q.get("cash"), q.get("cash_prev"))
        body += (f"<div class='azp'><b>{nome_p}: {e(q['periodo'])}</b> <span class='mu'>({durata}) · {conf}</span></div>"
                 f"<div class='azg'><div><span>Fatturato del periodo</span>{_mld(q.get('rev'), cur)} {_var(q.get('rev_g'))}</div>"
                 f"<div><span>Utile netto del periodo</span>{_mld(q.get('ni'), cur)} {_var(q.get('ni_g'))}</div>"
                 f"<div><span>Margine operativo</span>{(_num(q['opm']) + '%') if q.get('opm') is not None else 'n.d.'} {_var(q.get('opm_d'), ' pt', 1)}</div>"
                 f"<div><span>Debito totale</span>{_mld(q.get('debt'), cur)}{_var_inv(dg)}</div>"
                 f"<div><span>Liquidità</span>{_mld(q.get('cash'), cur)} {_var(cg) if cg is not None else ''}</div></div>")
        su, giu = a.get("aumentati") or [], a.get("diminuiti") or []
        if su or giu:
            body += (f"<div class='azn'>{'<b class=azup>Aumentati:</b> ' + e(', '.join(su)) if su else ''}"
                     f"{' · ' if su and giu else ''}{'<b class=azdn>Diminuiti:</b> ' + e(', '.join(giu)) if giu else ''}</div>")
    if an and an.get("rev") is not None:
        body += (f"<div class='azp'><b>Ultimo anno fiscale: {e(an['periodo'])}</b> <span class='mu'>(12 mesi)</span></div>"
                 f"<div class='azg'><div><span>Fatturato dell'anno</span>{_mld(an.get('rev'), cur)} {_var(an.get('rev_g'))}</div>"
                 f"<div><span>Utile netto dell'anno</span>{_mld(an.get('ni'), cur)} {_var(an.get('ni_g'))}</div></div>")
    val = ""
    if a.get("ps"):
        val += f"<div><span>Capitalizzazione / fatturato 12 mesi</span><b>{_num(a['ps'])}</b></div>"
        rp = a.get("rpo")
        if a.get("ps_rpo") and rp:
            gr = f", {('+' if (rp.get('crescita') or 0) > 0 else '')}{_num(rp['crescita'], 0)}% in un anno" if rp.get("crescita") is not None else ""
            val += (f"<div><span>Capitalizzazione / (fatturato + contratti firmati)</span><b>{_num(a['ps_rpo'])}</b></div>"
                    f"<div class='azwide'><span>Contratti già firmati non ancora fatturati (RPO)</span>{_mld(rp.get('valore'), rp.get('valuta'))}"
                    f" = {_num(a.get('rpo_anni') or 0)} anni di fatturato{gr} <span class='mu'>(al {e(rp.get('data', ''))})</span></div>")
        else:
            val += "<div><span>Contratti già firmati (RPO)</span><span class='mu'>non pubblicati</span></div>"
    if val:
        body += f"<div class='azp'><b>Quanto si paga l'azienda</b></div><div class='azg'>{val}</div>"
    old = "<div class='mu azn'><b>Dato del giorno precedente</b> (Yahoo non ha risposto oggi)</div>" if a.get("vecchio") else ""
    mot = f"<div class='mu azn'>Etichetta: {e(', '.join(a.get('motivi') or []) or 'nessuna variazione rilevante')} ({e(a.get('base', ''))} {e(a.get('periodo') or '')} contro {e(a.get('periodo_prec') or '')})</div>"
    return (f"<div class='azc'><div class='azh'><b>{i}. {e(a.get('nome', a['sym']))}</b><span class='badge {cls}'>{e(a['etichetta'])}</span><span class='mu'>{peso}</span></div>"
            f"{body}{mot}{old}</div>")


def html(d: dict) -> str:
    e = _h.escape
    intro = ("<div class='explain'><p>Lo stato di salute delle <b>prime 30 aziende</b> di VWCE (circa il 40% del fondo), dai loro bilanci. "
             "Per ognuna: l'<b>ultima trimestrale</b> (con i mesi esatti; le aziende europee che pubblicano ogni sei mesi sono indicate come semestrali) "
             "confrontata con lo stesso periodo di un anno prima, cosa è aumentato e cosa è diminuito, l'ultimo anno fiscale intero e quanto si paga l'azienda: "
             "capitalizzazione divisa per il fatturato degli ultimi 12 mesi e, dove l'azienda li pubblica, anche per i <b>contratti già firmati</b> e non ancora fatturati "
             "(più sono grandi, più ricavi futuri sono già assicurati).</p>"
             "<p>Etichetta con regola fissa: un punto per fatturato (±3%), utile netto (±5%), margine operativo (±1 punto) e debito netto rispetto al fatturato; "
             "con almeno +2 punti «In miglioramento», con -2 o meno «In peggioramento».</p></div>")
    rows = d.get("aziende") or []
    if not rows:
        return intro + ("<p class='mu'>I bilanci si scaricano nel ciclo giornaliero su GitHub. Non ci sono ancora dati: "
                        "compariranno dopo il prossimo «Aggiornamento giornaliero Armor».</p>")
    r = d.get("riepilogo", {})
    pw = r.get("peso_totale") or 0
    peso_txt = (f"<p>Pesate per il loro peso nel fondo: <b>{_num(r.get('peso_migliora', 0))}%</b> di VWCE in aziende in miglioramento, "
                f"<b>{_num(r.get('peso_stabile', 0))}%</b> stabili, <b>{_num(r.get('peso_peggiora', 0))}%</b> in peggioramento (su {_num(pw)}% coperto).</p>") if pw else ""
    head = (f"<div class='azsum'><span class='badge ok'>{r.get('migliora', 0)} in miglioramento</span> <span class='badge warn'>{r.get('stabile', 0)} stabili</span> "
            f"<span class='badge bad'>{r.get('peggiora', 0)} in peggioramento</span></div>{peso_txt}")
    cards = "".join(_card(i, a) for i, a in enumerate(rows, 1))
    foot = (f"<p class='mu'>Fonte: {e(d.get('fonte', ''))}, aggiornati il {e(d.get('date', ''))}. Pesi {e(d.get('pesi', ''))} (VWCE pesa le aziende per capitalizzazione; "
            "è una stima, non il dato ufficiale del fondo). Importi nella valuta di bilancio dell'azienda. Un trimestre può essere influenzato da fattori "
            "stagionali o una tantum: l'etichetta descrive l'ultimo anno, non è una previsione.</p>")
    return intro + head + "<div class='azlist'>" + cards + "</div>" + foot


CSS = """
.azsum{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.azlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
.azc{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;color:var(--tx)}
.azh{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin-bottom:6px}.azh b{flex:1 1 auto;font-size:15px}
.azg{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:13.5px}.azg span{display:block;font-size:11.5px;color:var(--mu);font-weight:600}
.azup{color:var(--ok)}.azdn{color:var(--bad)}.azn{font-size:12px;margin-top:6px}
.azh .mu{font-size:12.5px}.azc>.mu{font-size:13px}
.azp{margin-top:8px;font-size:13.5px;color:var(--tx)}.azp .mu{font-size:12px}.azwide{grid-column:1/-1}
"""
