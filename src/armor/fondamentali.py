"""Salute delle aziende, inflazione, economia reale, liquidità, leva, mercato interno, Europa e storia lunga (PIANO_MODELLO, Fase A).

- `aggiorna_fonti()`: scarica le serie nuove (FRED, BCE, FINRA, Shiller). Quelle mensili o trimestrali si riscaricano al massimo
  una volta ogni 6 giorni (stato in data/fonti_lente.json), così il ciclo giornaliero resta veloce. Ogni fonte è indipendente.
- `raccogli_revisioni()`: ogni giorno, revisioni delle stime di utile e crescita attesa sui titoli principali (Yahoo). Lo storico parte da oggi.
- `calcola()` / `aggiorna_derivate()`: serie derivate (crescita utili, margini, inflazione annua, liquidità Fed, forza relativa...).
- `LAG` + `nota_al()` + `mensile()`: ogni dato entra solo dal giorno in cui era davvero noto (ritardo di pubblicazione), per la ricerca.

Le serie nuove sono solo MONITORATE: entrano nell'Indice Armor solo se lo promuove la verifica automatica (armor_index.test_new_indicators)."""
import io
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import store
from .config import DATA, SERIES

STATE = DATA / "fonti_lente.json"
GIORNI_LENTE = 6

# id -> codice FRED (verificati alla prima esecuzione: se un codice non esiste la serie risulta ERR in data/status.json e le altre proseguono)
FRED_NUOVE = {
    # salute delle aziende
    "cp": "CP", "delinq_biz": "DRBLACBS", "chargeoff_biz": "CORBLACBS", "delinq_cc": "DRCCLACBS", "busloans": "BUSLOANS",
    # inflazione
    "core_cpi": "CPILFESL", "core_pce": "PCEPILFE", "infl5y5y": "T5YIFR",
    # economia reale e recessione (usrec solo come etichetta; recprob solo come contesto perché viene rivista)
    "cfnai": "CFNAI", "sahm_rt": "SAHMREALTIME", "ccsa": "CCSA", "permit": "PERMIT", "isratio": "ISRATIO",
    "usrec": "USREC", "recprob": "RECPROUSM156N",
    # liquidità e stress
    "m2": "M2SL", "nfci_credit": "NFCICREDIT", "nfci_leverage": "NFCILEVERAGE", "nfci_risk": "NFCIRISK", "kcfsi": "KCFSI",
    # storia lunga mensile
    "baa_m": "BAA", "aaa_m": "AAA", "gs10_m": "GS10", "tb3ms": "TB3MS", "cpi_nsa": "CPIAUCNS",
}
CISS_URL = "https://data-api.ecb.europa.eu/service/data/CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX?format=csvdata"
FINRA_PAGES = ["https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics",
               "https://www.finra.org/finra-data/browse-catalog/industry-snapshot/margin-statistics"]   # la prima è quella attuale (la seconda dava 404)

# Ritardo di pubblicazione: giorni tra la DATA del dato (FRED: inizio del periodo) e il giorno in cui è noto. Prudente.
LAG = {
    # mercato e tassi giornalieri
    "sp500": 1, "vix": 1, "spy": 1, "iwm": 1, "rsp": 1, "smh": 1, "iyt": 1, "kre": 1, "copper": 1, "gold": 1, "hyg": 1, "ief": 1,
    "sec_xly": 1, "sec_xlp": 1, "eem": 1, "vt": 1, "dgs10": 1, "dgs2": 1, "t10y3m": 1, "t10y2y": 1, "baa10y": 1, "fedfunds": 1,
    "real10y": 1, "be10y": 1, "infl5y5y": 1, "rrp": 1, "epu": 2, "ciss": 2, "aaii_spread": 1, "rev_breadth": 1, "fwd_growth": 1,
    "skew": 1, "move": 1,
    # settimanali
    "icsa": 6, "ccsa": 12, "nfci": 6, "anfci": 6, "nfci_credit": 6, "nfci_leverage": 6, "nfci_risk": 6, "stlfsi": 7,
    "walcl": 2, "tga": 2, "wresbal": 2,
    # mensili (data = inizio del mese)
    "cpi": 45, "core_cpi": 45, "cpi_nsa": 45, "core_pce": 60, "indpro": 47, "payems": 37, "unrate": 37, "sahm_rt": 37,
    "retail": 45, "umcsent": 30, "permit": 48, "isratio": 75, "cfnai": 55, "m2": 55, "busloans": 40, "neworder": 57,
    "dgorder": 57, "philly": 20, "empire": 20, "kcfsi": 40, "margin_debt": 52, "recprob": 90, "usrec": 365,
    "gs10_m": 32, "tb3ms": 32, "baa_m": 32, "aaa_m": 32, "pe_m": 60, "cape_m": 60, "earn_shiller": 120, "cape": 120,
    # trimestrali (data = inizio del trimestre, ps_m = fine trimestre)
    "cp": 150, "gdp": 120, "delinq_biz": 150, "chargeoff_biz": 150, "delinq_cc": 150, "sloos": 40, "credit_ratio": 210,
    "ps_m": 60,
}
# serie derivate: ritardo = il più lungo tra quelli dei dati da cui nascono
DERIV_IN = {
    "eps_sp": ["pe_m", "sp500"], "eps_g12": ["pe_m"], "eps_g3": ["pe_m"], "sales_g12": ["ps_m"], "margin_sp": ["ps_m", "pe_m"],
    "erp": ["pe_m", "gs10_m"], "cp_g4": ["cp"], "cp_gdp": ["cp", "gdp"], "busloans_g6": ["busloans"],
    "cpi_yoy": ["cpi"], "cpi_yoy_lungo": ["cpi_nsa"], "core_yoy": ["core_cpi"], "core_pce_yoy": ["core_pce"], "infl_acc": ["cpi"],
    "real_ff": ["core_cpi", "fedfunds"], "net_liq": ["walcl", "tga", "rrp"], "net_liq_13w": ["walcl", "tga", "rrp"], "m2_yoy": ["m2"],
    "claims_up": ["icsa"], "ccsa_yoy": ["ccsa"], "permit_yoy": ["permit"], "margin_yoy": ["margin_debt"], "indpro_g12": ["indpro"],
    "sahm": ["unrate"], "curve_lunga": ["gs10_m", "tb3ms"], "baa_lungo": ["baa_m", "gs10_m"],
    "rel_small": ["iwm"], "rel_eqw": ["rsp"], "rel_cicl": ["sec_xly"], "rel_semi": ["smh"], "rel_trasp": ["iyt"], "rel_banche": ["kre"],
    "rel_rame_oro": ["copper"], "rel_credito": ["hyg"], "rel_emergenti": ["eem"],
}
# Utili ricavati dal P/E mensile (multpl/Shiller): gli utili mensili storici sono interpolati tra trimestri e pubblicati 2-3 mesi dopo la fine
# del trimestre, quindi il dato di un mese era davvero noto fino a ~5 mesi dopo. Prova di sensibilità (nov 2026, calo ≥10% entro 6 mesi,
# 2000-2018): ritardo 60 gg AUC 0,75; 120 gg 0,66; 180 gg 0,63. Si usa 150 giorni (prudente): con meno, parte dell'abilità sarebbe sguardo al futuro.
LAG.update({"eps_sp": 150, "eps_g12": 150, "eps_g3": 150, "margin_sp": 150})
for _k, _ins in DERIV_IN.items():
    LAG.setdefault(_k, max(LAG.get(i, 1) for i in _ins))

# forza relativa a 3 mesi: (id, numeratore, denominatore)
RELATIVI = [("rel_small", "iwm", "spy"), ("rel_eqw", "rsp", "spy"), ("rel_cicl", "sec_xly", "sec_xlp"), ("rel_semi", "smh", "spy"),
            ("rel_trasp", "iyt", "spy"), ("rel_banche", "kre", "spy"), ("rel_rame_oro", "copper", "gold"), ("rel_credito", "hyg", "ief"),
            ("rel_emergenti", "eem", "vt")]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _due(stato: dict, sid: str, force: bool) -> bool:
    if force or store.load(sid).empty or sid not in stato:
        return True
    return (pd.Timestamp(_today()) - pd.Timestamp(stato[sid])).days >= GIORNI_LENTE


# ---------------------------------------------------------------- fonti diverse da FRED
def parse_ciss(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values, index=pd.to_datetime(df["TIME_PERIOD"]))
    return s.dropna().sort_index()


def fetch_ciss() -> pd.Series:
    from .sources import _get
    old = store.load("ciss")
    url = CISS_URL + ("" if old.empty else f"&startPeriod={(old.index[-1] - pd.Timedelta(days=60)).strftime('%Y-%m-%d')}")
    return parse_ciss(_get(url, tries=2, timeout=40).text)


def parse_finra(df: pd.DataFrame) -> pd.Series:
    """Tabella FINRA (margin statistics): prima colonna mese ('2026-09' o data), colonna con 'Debit' = debito sui conti a margine."""
    hdr = None
    for i in range(min(len(df), 15)):
        if any("debit" in str(c).lower() for c in df.iloc[i]):
            hdr = i
            break
    if hdr is None and any("debit" in str(c).lower() for c in df.columns):
        body, cols = df, [str(c) for c in df.columns]
    elif hdr is not None:
        body, cols = df.iloc[hdr + 1:], [str(c) for c in df.iloc[hdr]]
    else:
        raise ValueError("FINRA: colonna 'Debit' non trovata")
    j = next(k for k, c in enumerate(cols) if "debit" in c.lower())
    dt = pd.to_datetime(body.iloc[:, 0].astype(str).str.strip(), errors="coerce", format="mixed")
    v = pd.to_numeric(body.iloc[:, j], errors="coerce")
    s = pd.Series(v.values, index=dt.values).dropna()
    s = s[s.index.notna()]
    if s.empty:
        raise ValueError("FINRA: nessun valore")
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    return s.sort_index()


def fetch_finra_margin() -> pd.Series:
    from urllib.parse import urljoin
    from .sources import _get
    last = None
    for pg in FINRA_PAGES:
        try:
            page = _get(pg, tries=1, timeout=30).text
            m = re.search(r'href="([^"]+?\.xlsx[^"]*)"', page, re.I)
            if not m:
                raise ValueError("link al file Excel non trovato")
            raw = _get(urljoin(pg, m.group(1)), tries=1, timeout=60).content
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise ValueError(f"FINRA: {str(last)[:100]}")
    return parse_finra(pd.read_excel(io.BytesIO(raw), header=None))


def aggiorna_fonti(st: dict | None = None, force: bool = False, limite: float = 200) -> dict:
    """Scarica le serie nuove entro `limite` secondi (poi si ferma e riprende al ciclo dopo). Restituisce lo stato (lo scrive chi chiama)."""
    import time as _t
    from . import sources
    st = st if st is not None else store.read_status()
    stato = _state()
    t0 = _t.time()
    fails, n = 0, 0
    resto = lambda: limite - (_t.time() - t0)
    for sid, code in FRED_NUOVE.items():
        if not _due(stato, sid, force):
            continue
        if resto() < 30:
            store.set_status(st, sid, False, "rimandata: tempo del ciclo esaurito (si riprova al prossimo)")
            continue
        if fails >= 2:   # FRED non risponde: si salta il resto invece di aspettare per ogni serie
            store.set_status(st, sid, False, "saltata: FRED non risponde (si riprova al prossimo ciclo)")
            continue
        try:
            store.set_status(st, sid, True, "", store.upsert(sid, sources.fetch_fred(code, sources._fred_start(sid))))
            stato[sid] = _today()
            fails, n = 0, n + 1
        except Exception as e:  # noqa: BLE001
            fails += 1
            store.set_status(st, sid, False, f"FRED {code}: {str(e)[:120]}")
    for sid, fn, lenta in (("ciss", fetch_ciss, False), ("margin_debt", fetch_finra_margin, True)):
        if (lenta and not _due(stato, sid, force)) or resto() < 45:
            continue
        try:
            store.set_status(st, sid, True, "", store.upsert(sid, fn()))
            stato[sid] = _today()
        except Exception as e:  # noqa: BLE001
            store.set_status(st, sid, False, str(e)[:150])
    if _due(stato, "earn_shiller", force) and resto() > 40:
        try:
            from .guard import with_timeout
            for sid, ser in with_timeout(sources.fetch_shiller, int(min(60, resto() - 10)), "Shiller").items():
                store.set_status(st, sid, True, "", store.upsert(sid, ser))
            stato["earn_shiller"] = _today()
        except Exception as e:  # noqa: BLE001
            store.set_status(st, "earn_shiller", False, f"Shiller: {str(e)[:120]}")
    STATE.write_text(json.dumps(stato, indent=1, sort_keys=True), encoding="utf-8")
    print(f"[fondamentali] fonti lente: {n} serie FRED aggiornate in {_t.time() - t0:.0f}s", flush=True)
    return st


# ---------------------------------------------------------------- revisioni degli utili (storico da oggi)
REV_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK-B", "JPM", "LLY", "V", "ORCL", "XOM", "MA",
               "NFLX", "COST", "WMT", "TSM", "ASML", "MU", "UNH", "HD", "PG", "JNJ", "BAC", "KO", "ABBV", "AMD", "CRM"]


def _col(row, name: str):
    for k in row.index:
        if str(k).lower() == name.lower():
            v = pd.to_numeric(row[k], errors="coerce")
            return None if pd.isna(v) else float(v)
    return None


def _rev_uno(sym: str) -> dict:
    import yfinance as yf
    tk = yf.Ticker(sym)
    out: dict = {"sym": sym}
    try:
        r = tk.eps_revisions
        row = r.loc["0y"] if "0y" in r.index else r.iloc[-2]
        out["up"], out["dn"] = _col(row, "upLast30days"), _col(row, "downLast30days")
    except Exception:  # noqa: BLE001
        pass
    try:
        e = tk.earnings_estimate
        row = e.loc["+1y"] if "+1y" in e.index else e.iloc[-1]
        g = _col(row, "growth")
        out["g"] = None if g is None else g * 100
    except Exception:  # noqa: BLE001
        pass
    try:
        out["cap"] = float(tk.fast_info["market_cap"])
    except Exception:  # noqa: BLE001
        out["cap"] = None
    return out


def calcola_revisioni(rows: list[dict]) -> dict:
    """Ampiezza delle revisioni = media pesata di (rialzi - ribassi)/(rialzi + ribassi) x 100; crescita attesa = media pesata (%).
    Pesi = capitalizzazione (uguali se manca). Servono almeno 10 titoli validi."""
    def media(vals):
        ok = [(v, w) for v, w in vals if v is not None and np.isfinite(v)]
        if len(ok) < 10:
            return None
        w = np.array([x[1] for x in ok], float)
        return float(np.average([x[0] for x in ok], weights=w))
    capw = lambda r: r.get("cap") if r.get("cap") and r["cap"] > 0 else 1e11
    br = [(((r["up"] - r["dn"]) / (r["up"] + r["dn"]) * 100) if r.get("up") is not None and r.get("dn") is not None and (r["up"] + r["dn"]) > 0
           else (0.0 if r.get("up") == 0 and r.get("dn") == 0 else None), capw(r)) for r in rows]
    gr = [(r.get("g"), capw(r)) for r in rows]
    return {"rev_breadth": media(br), "fwd_growth": media(gr), "n": sum(1 for v, _ in br if v is not None)}


def raccogli_revisioni(deadline: float = 75) -> dict:
    from .guard import run_parallel
    res = run_parallel({s: (lambda s=s: _rev_uno(s)) for s in REV_TICKERS}, workers=6, deadline=deadline)
    rows = [v for k, (kind, v) in res.items() if kind == "ok"]
    out = calcola_revisioni(rows)
    day = pd.Timestamp(_today())
    for sid in ("rev_breadth", "fwd_growth"):
        if out[sid] is not None:
            store.upsert(sid, pd.Series({day: out[sid]}))
    (DATA / "revisioni_oggi.json").write_text(json.dumps({"date": _today(), "titoli": rows, **out}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[fondamentali] revisioni utili: {out['n']} titoli, ampiezza {out['rev_breadth']}, crescita attesa {out['fwd_growth']}", flush=True)
    return out


# ---------------------------------------------------------------- serie derivate
def _ms(s: pd.Series, how: str = "last") -> pd.Series:
    return getattr(s.dropna().resample("MS"), how)().dropna()


def calcola(load=store.load) -> dict:
    """Serie derivate, datate come il dato d'origine (il ritardo di pubblicazione si applica dopo, con `nota_al`)."""
    from collections import defaultdict
    g = defaultdict(lambda: pd.Series(dtype=float))   # una serie mancante non deve mai fermare il calcolo delle altre
    g.update({k: load(k).dropna() for k in set(sum(DERIV_IN.values(), [])) | {"spy", "gold", "ief", "sec_xlp", "vt", "dgs10", "fedfunds"}})
    out: dict = {}
    pct = lambda s, n: (s / s.shift(n) - 1) * 100

    def put(k, s):
        s = s.replace([np.inf, -np.inf], np.nan).dropna()
        if len(s):
            out[k] = s
    sp, pe = g["sp500"], g["pe_m"]
    if len(sp) and len(pe):
        pe_ms = _ms(pe)
        eps = (_ms(sp, "mean") / pe_ms).dropna()
        put("eps_sp", eps)
        put("eps_g12", pct(eps, 12))
        put("eps_g3", pct(eps, 3))
        y10 = _ms(g["gs10_m"]) if len(g["gs10_m"]) else pd.Series(dtype=float)
        if len(g["dgs10"]):
            y10 = _ms(g["dgs10"], "mean").combine_first(y10)
        if len(y10):
            put("erp", 100 / pe_ms - y10.reindex(pe_ms.index))
        ps = g["ps_m"]
        if len(ps):
            psq = ps.groupby(ps.index.to_period("Q")).tail(1)   # ultimo dato di ogni trimestre, con la SUA data (mai date future)
            spq = sp.reindex(sp.index.union(psq.index)).ffill().reindex(psq.index)
            sales = (spq / psq).dropna()
            prev = sales.reindex(sales.index - pd.DateOffset(years=1), method="ffill", tolerance=pd.Timedelta(days=100))   # trimestri mancanti: confronto per data
            put("sales_g12", pd.Series((sales.values / prev.values - 1) * 100, index=sales.index))
            eq = eps.copy()
            eq.index = eq.index + pd.offsets.MonthEnd(0)
            epsq = eq.reindex(eq.index.union(sales.index)).ffill().reindex(sales.index)
            put("margin_sp", epsq / sales * 100)
    if len(g["cp"]):
        put("cp_g4", pct(g["cp"], 4))
        if len(g["gdp"]):
            put("cp_gdp", g["cp"] / g["gdp"].reindex(g["cp"].index) * 100)
    if len(g["busloans"]):
        put("busloans_g6", pct(_ms(g["busloans"]), 6))
    for k, src in (("cpi_yoy", "cpi"), ("cpi_yoy_lungo", "cpi_nsa"), ("core_yoy", "core_cpi"), ("core_pce_yoy", "core_pce"),
                   ("m2_yoy", "m2"), ("permit_yoy", "permit"), ("margin_yoy", "margin_debt"), ("indpro_g12", "indpro")):
        if len(g[src]):
            put(k, pct(_ms(g[src]), 12))
    if "cpi_yoy" in out:
        put("infl_acc", out["cpi_yoy"] - out["cpi_yoy"].shift(6))
    if "core_yoy" in out and len(g["fedfunds"]):
        put("real_ff", _ms(g["fedfunds"], "mean") - out["core_yoy"])
    w, t, r = g["walcl"], g["tga"], g["rrp"]
    if len(w) and len(t):
        rr = r.reindex(r.index.union(w.index)).ffill().reindex(w.index).fillna(0) if len(r) else 0
        nl = w / 1000 - t.reindex(t.index.union(w.index)).ffill().reindex(w.index) / 1000 - rr   # miliardi di dollari (WALCL e TGA in milioni, RRP in miliardi)
        put("net_liq", nl)
        put("net_liq_13w", pct(nl.dropna(), 13))
    ic = g["icsa"]
    if len(ic) > 60:
        put("claims_up", (ic.rolling(4).mean() / ic.rolling(52).min() - 1) * 100)
    if len(g["ccsa"]) > 60:
        put("ccsa_yoy", pct(g["ccsa"], 52))
    u = g["unrate"]
    if len(u) > 18:
        m = _ms(u).rolling(3).mean()
        put("sahm", m - m.rolling(12).min())
    if len(g["gs10_m"]) and len(g["tb3ms"]):
        put("curve_lunga", g["gs10_m"] - g["tb3ms"].reindex(g["gs10_m"].index))
    if len(g["baa_m"]) and len(g["gs10_m"]):
        put("baa_lungo", g["baa_m"] - g["gs10_m"].reindex(g["baa_m"].index))
    for k, a, b in RELATIVI:
        x, y = g.get(a, pd.Series(dtype=float)), g.get(b, pd.Series(dtype=float))
        if len(x) > 100 and len(y) > 100:
            rel = (x / y.reindex(x.index)).dropna()
            put(k, pct(rel, 63))
    return out


def _scrivi(sid: str, s: pd.Series) -> None:
    SERIES.mkdir(parents=True, exist_ok=True)
    o = s.rename("value").rename_axis("date").reset_index()
    o["date"] = pd.to_datetime(o["date"]).dt.strftime("%Y-%m-%d")
    o.to_csv(store.path(sid), index=False, float_format="%.6g")


def aggiorna_derivate() -> list:
    out = calcola()
    for k, s in out.items():
        _scrivi(k, s)
    print(f"[fondamentali] serie derivate: {len(out)}", flush=True)
    return sorted(out)


# ---------------------------------------------------------------- ritardi di pubblicazione
def nota_al(s: pd.Series, sid: str) -> pd.Series:
    """La stessa serie ma datata al giorno in cui il dato era noto (data + ritardo)."""
    s = s.dropna().copy()
    if s.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    s.index = pd.DatetimeIndex(s.index) + pd.Timedelta(days=int(LAG.get(sid, 1)))
    return s


def mensile(ids: list, load=store.load, start: str = "1927-12-31", end=None, max_age: int = 400, con_oggi: bool = False) -> pd.DataFrame:
    """Tabella a fine mese: per ogni serie l'ultimo valore NOTO a quella data (dopo il ritardo); vuoto se l'ultimo è più vecchio di max_age giorni.
    Con con_oggi=True aggiunge una riga per la data finale (oggi) se non è già un fine mese."""
    fine = pd.Timestamp(end or pd.Timestamp.now().normalize())
    idx = pd.date_range(start, fine, freq="ME")
    if con_oggi and (len(idx) == 0 or idx[-1] < fine):
        idx = idx.append(pd.DatetimeIndex([fine]))
    cols = {}
    for sid in ids:
        s = nota_al(load(sid), sid)
        if s.empty:
            cols[sid] = pd.Series(np.nan, index=idx)
            continue
        s = s[~s.index.duplicated(keep="last")].sort_index()
        pos = s.index.searchsorted(idx, side="right") - 1
        v = np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)
        age = np.where(pos >= 0, (idx - s.index[np.clip(pos, 0, None)]).days, 10 ** 6)
        cols[sid] = pd.Series(np.where(age <= max_age, v, np.nan), index=idx)
    return pd.DataFrame(cols, index=idx)
