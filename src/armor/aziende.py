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
GIORNI = 6
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
def _riga(df, nomi):
    if df is None or getattr(df, "empty", True):
        return None
    for n in nomi:
        if n in df.index:
            s = pd.to_numeric(df.loc[n], errors="coerce")
            if isinstance(s, pd.DataFrame):
                s = s.iloc[0]
            return s
    return None


def _cols(df) -> list:
    if df is None or getattr(df, "empty", True):
        return []
    c = sorted(pd.to_datetime(df.columns, errors="coerce").dropna(), reverse=True)
    return c


def _coppia(df, nomi_ricavi=("Total Revenue", "Operating Revenue")):
    """(data recente, data di un anno prima) se esistono colonne a ~1 anno di distanza con fatturato presente."""
    cols = _cols(df)
    if len(cols) < 2:
        return None
    rev = _riga(df, nomi_ricavi)
    for i, d0 in enumerate(cols):
        if rev is not None and pd.isna(rev.get(d0, np.nan)) and i < len(cols) - 1:
            continue
        for d1 in cols[i + 1:]:
            if 330 <= (d0 - d1).days <= 400:
                return d0, d1
        break
    return None


def _v(s, d):
    if s is None:
        return None
    try:
        x = s.get(d, np.nan) if hasattr(s, "get") else np.nan
        if pd.isna(x):
            x = s[pd.to_datetime(s.index) == d]
            x = x.iloc[0] if len(x) else np.nan
        return None if pd.isna(x) else float(x)
    except Exception:  # noqa: BLE001
        return None


def _pct(a, b):
    if a is None or b is None or b == 0:
        return None
    if b < 0:   # base negativa: la variazione percentuale non ha senso, conta solo il segno del miglioramento
        return 100.0 if a > b else -100.0
    return (a / b - 1) * 100


def analizza(inc_q=None, inc_a=None, bal_q=None, bal_a=None) -> dict:
    """Confronto con un anno prima e etichetta. Accetta i DataFrame di yfinance (righe = voci, colonne = date)."""
    out: dict = {}
    for df, base in ((inc_q, "trimestre"), (inc_a, "anno")):
        cp = _coppia(df)
        if cp:
            d0, d1 = cp
            rev, ni = _riga(df, ("Total Revenue", "Operating Revenue")), _riga(df, ("Net Income", "Net Income Common Stockholders"))
            op = _riga(df, ("Operating Income", "Total Operating Income As Reported"))
            out.update({"base": base, "periodo": d0.strftime("%Y-%m"), "periodo_prec": d1.strftime("%Y-%m"),
                        "rev": _v(rev, d0), "rev_prev": _v(rev, d1), "ni": _v(ni, d0), "ni_prev": _v(ni, d1),
                        "op": _v(op, d0), "op_prev": _v(op, d1)})
            break
    for df in (bal_q, bal_a):
        cp = _coppia(df, ("Total Debt", "Total Assets"))
        if cp:
            d0, d1 = cp
            debt, cash = _riga(df, ("Total Debt",)), _riga(df, ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"))
            out.update({"bil_data": d0.strftime("%Y-%m"), "debt": _v(debt, d0), "debt_prev": _v(debt, d1), "cash": _v(cash, d0), "cash_prev": _v(cash, d1)})
            break
    if "base" not in out:
        out["errore"] = "bilanci non disponibili"
        return out
    rv, rp = out.get("rev"), out.get("rev_prev")
    out["rev_g"] = _pct(rv, rp)
    out["ni_g"] = _pct(out.get("ni"), out.get("ni_prev"))
    opm = (out["op"] / rv * 100) if out.get("op") is not None and rv else None
    opp = (out["op_prev"] / rp * 100) if out.get("op_prev") is not None and rp else None
    out["opm"], out["opm_prev"] = opm, opp
    out["opm_d"] = (opm - opp) if opm is not None and opp is not None else None
    lev = lambda d, c, r: ((d or 0) - (c or 0)) / (r * (4 if out["base"] == "trimestre" else 1)) if d is not None and r else None
    l0, l1 = lev(out.get("debt"), out.get("cash"), rv), lev(out.get("debt_prev"), out.get("cash_prev"), rp)
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
    out.pop("_cur", None)
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
    d = {"date": oggi, "fonte": "Yahoo Finance (bilanci trimestrali e annuali)", "pesi": "stimati dalla capitalizzazione" if w else "ordine indicativo",
         "aziende": rows, "riepilogo": riepilogo(rows)}
    if d["riepilogo"]["n"] == 0 and old.get("aziende"):
        print("[aziende] nessun bilancio scaricato: tengo i dati precedenti", flush=True)
        return old
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=0, default=lambda x: None), encoding="utf-8")
    print(f"[aziende] bilanci: {d['riepilogo']['n']}/30 aziende, {d['riepilogo']['migliora']} in miglioramento, "
          f"{d['riepilogo']['stabile']} stabili, {d['riepilogo']['peggiora']} in peggioramento", flush=True)
    return d


# ---------------------------------------------------------------- pagina
def _mld(x, cur):
    if x is None:
        return "n.d."
    sym = {"USD": "$", "EUR": "€", None: ""}.get(cur, cur or "")
    v = x / 1e9
    s = f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} mld {sym}".strip()


def _var(x, unit="%", dec=0):
    if x is None:
        return "<span class='mu'>n.d.</span>"
    cls = "azup" if x > 0 else ("azdn" if x < 0 else "")
    s = f"{x:+,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"<b class='{cls}'>{s}{unit}</b>"


MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _mese(ym):
    try:
        y, m = ym.split("-")
        return f"{MESI[int(m) - 1]} {y}"
    except Exception:  # noqa: BLE001
        return ym or ""


def html(d: dict) -> str:
    e = _h.escape
    intro = ("<div class='explain'><p>Lo stato di salute delle <b>prime 30 aziende</b> di VWCE (circa il 40% del fondo), dai loro bilanci. "
             "Per ognuna si confrontano gli ultimi dati con quelli di un anno prima: fatturato, utile netto, margine operativo (quanta parte delle vendite "
             "resta come utile della gestione), debito e liquidità. L'etichetta segue una regola fissa: un punto per fatturato (±3%), utile netto (±5%), "
             "margine operativo (±1 punto) e debito netto rispetto al fatturato; con almeno +2 punti «In miglioramento», con -2 o meno «In peggioramento».</p></div>")
    rows = d.get("aziende") or []
    if not rows:
        return intro + ("<p class='mu'>I bilanci si scaricano nel ciclo giornaliero su GitHub, una volta a settimana. Non ci sono ancora dati: "
                        "compariranno dopo il prossimo «Aggiornamento giornaliero Armor».</p>")
    r = d.get("riepilogo", {})
    f = lambda x: f"{x:.1f}".replace(".", ",")
    pw = r.get("peso_totale") or 0
    peso_txt = (f"<p>Pesate per il loro peso nel fondo: <b>{f(r.get('peso_migliora', 0))}%</b> di VWCE in aziende in miglioramento, "
                f"<b>{f(r.get('peso_stabile', 0))}%</b> stabili, <b>{f(r.get('peso_peggiora', 0))}%</b> in peggioramento (su {f(pw)}% coperto).</p>") if pw else ""
    head = (f"<div class='azsum'><span class='badge ok'>{r.get('migliora', 0)} in miglioramento</span> <span class='badge warn'>{r.get('stabile', 0)} stabili</span> "
            f"<span class='badge bad'>{r.get('peggiora', 0)} in peggioramento</span></div>{peso_txt}")
    cards = []
    for i, a in enumerate(rows, 1):
        peso = f"peso ≈ {f(a['peso'])}%" if a.get("peso") else ""
        if "errore" in a:
            cards.append(f"<div class='azc'><div class='azh'><b>{i}. {e(a.get('nome', a['sym']))}</b><span class='mu'>{peso}</span></div>"
                         f"<div class='mu'>Bilanci non disponibili questa settimana ({e(a['errore'])}).</div></div>")
            continue
        cls = {1: "ok", 0: "warn", -1: "bad"}[a["stato"]]
        cur = a.get("valuta")
        base = ("ultimo trimestre" if a.get("base") == "trimestre" else "ultimo anno fiscale")
        conf = f"Confronto: {base} ({_mese(a.get('periodo'))}) con un anno prima ({_mese(a.get('periodo_prec'))})"
        old = " · <b>dato della settimana scorsa</b> (Yahoo non ha risposto)" if a.get("vecchio") else ""
        mot = (" · " + ", ".join(a.get("motivi") or [])) if a.get("motivi") else ""
        opm = (f"{f(a['opm'])}%" if a.get("opm") is not None else "n.d.")
        cards.append(
            f"<div class='azc'><div class='azh'><b>{i}. {e(a.get('nome', a['sym']))}</b><span class='badge {cls}'>{e(a['etichetta'])}</span><span class='mu'>{peso}</span></div>"
            f"<div class='azg'><div><span>Fatturato</span>{_mld(a.get('rev'), cur)} {_var(a.get('rev_g'))}</div>"
            f"<div><span>Utile netto</span>{_mld(a.get('ni'), cur)} {_var(a.get('ni_g'))}</div>"
            f"<div><span>Margine operativo</span>{opm} {_var(a.get('opm_d'), ' pt', 1)}</div>"
            f"<div><span>Debito totale</span>{_mld(a.get('debt'), cur)}</div>"
            f"<div><span>Liquidità</span>{_mld(a.get('cash'), cur)}</div></div>"
            f"<div class='mu azn'>{conf}{mot}{old}</div></div>")
    foot = (f"<p class='mu'>Fonte: {e(d.get('fonte', ''))}, aggiornati il {e(d.get('date', ''))}. Pesi {e(d.get('pesi', ''))} (VWCE pesa le aziende per capitalizzazione; "
            "è una stima, non il dato ufficiale del fondo). Importi nella valuta di bilancio dell'azienda. Un trimestre può essere influenzato da fattori "
            "stagionali o una tantum: l'etichetta descrive l'ultimo anno, non è una previsione.</p>")
    return intro + head + "<div class='azlist'>" + "".join(cards) + "</div>" + foot


CSS = """
.azsum{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.azlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
.azc{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;color:var(--tx)}
.azh{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin-bottom:6px}.azh b{flex:1 1 auto;font-size:15px}
.azg{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:13.5px}.azg span{display:block;font-size:11.5px;color:var(--mu);font-weight:600}
.azup{color:var(--ok)}.azdn{color:var(--bad)}.azn{font-size:12px;margin-top:6px}
.azh .mu{font-size:12.5px}.azc>.mu{font-size:13px}
"""
