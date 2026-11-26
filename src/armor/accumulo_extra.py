"""Fonti aggiuntive dell'archivio (23/11/2026): stress sistemico, liquidita' del Tesoro, posizionamento, attenzione del pubblico, ecc.

Ogni funzione e' indipendente, scrive su data/ e riempie lo `stato` con quanto e' riuscito. Le parti di lettura (parse_*) non toccano la rete,
cosi' si provano con dati finti. Nessuna di queste serie entra nei modelli: sono archivio per le ricerche future."""
from __future__ import annotations

import io
import json
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from . import store
from .config import DATA
from .guard import run_parallel

UA = {"User-Agent": "ArmorResearch/1.0 (+https://github.com/Stefo818/armor; ricerca personale)"}   # Wikimedia e altri chiedono un nome riconoscibile
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}   # per i siti che rifiutano i programmi (CBOE, AAII)


def _get(url: str, tries: int = 3, timeout: int = 60, headers: dict | None = None, **kw) -> requests.Response:
    """Scarica con nuovi tentativi. Se il sito dice «troppe richieste» (429) aspetta quanto indicato e riprova;
    con 400/401/403/404 non insiste (riprovare non serve e fa solo perdere tempo)."""
    last = None
    for i in range(tries):
        try:
            from .guard import with_timeout   # il timeout di requests vale per ogni lettura: un sito che gocciola lo aggira
            r = with_timeout(lambda: requests.get(url, headers=headers or UA, timeout=(15, min(timeout, 40)), **kw), min(timeout, 40) + 20, "scarico", True)
            if r.status_code == 429:
                try:
                    att = int(r.headers.get("Retry-After", 20))
                except ValueError:
                    att = 20
                last = RuntimeError("429 troppe richieste")
                time.sleep(min(60, max(5, att)))
                continue
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            cod = getattr(getattr(e, "response", None), "status_code", None)
            if cod in (400, 401, 403, 404):
                break
            time.sleep(2 * 2 ** i)
    raise RuntimeError(str(last)[:100])


def slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(t).lower()).strip("_")


def _riepilogo(res: dict) -> dict:
    ok = [k for k, (t, _) in res.items() if t == "ok"]
    return {"richieste": len(res), "riuscite": len(ok), "fallite": {k: str(v)[:60] for k, (t, v) in res.items() if t != "ok"}}


def _upsert_tutte(prefisso: str, df: pd.DataFrame) -> int:
    n = 0
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(s):
            n += store.upsert(prefisso + slug(c), s)
    return n


# ----------------------------------------------------------------------------- BCE: stress sistemico europeo, curve, cambio
def parse_bce(txt: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(txt), usecols=["TIME_PERIOD", "OBS_VALUE"])
    s = pd.Series(df.OBS_VALUE.values, index=pd.to_datetime(df.TIME_PERIOD), dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


BCE = {
    "ciss_area_euro": "CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX", "ciss_italia": "CISS/D.IT.Z0Z.4F.EC.SS_CIN.IDX", "ciss_germania": "CISS/D.DE.Z0Z.4F.EC.SS_CIN.IDX",
    "ciss_francia": "CISS/D.FR.Z0Z.4F.EC.SS_CIN.IDX", "ciss_spagna": "CISS/D.ES.Z0Z.4F.EC.SS_CIN.IDX", "ciss_usa": "CISS/D.US.Z0Z.4F.EC.SS_CIN.IDX",
    "ciss_regno_unito": "CISS/D.GB.Z0Z.4F.EC.SS_CIN.IDX", "ciss_cina": "CISS/D.CN.Z0Z.4F.EC.SS_CIN.IDX",
    "rend_aaa_2a": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y", "rend_aaa_10a": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "rend_aaa_30a": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y",
    "rend_tutti_2a": "YC/B.U2.EUR.4F.G_N_C.SV_C_YM.SR_2Y", "rend_tutti_10a": "YC/B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y", "rend_tutti_30a": "YC/B.U2.EUR.4F.G_N_C.SV_C_YM.SR_30Y",
    "tasso_bce_rifinanziamento": "FM/B.U2.EUR.4F.KR.MRR_FR.LEV", "tasso_bce_deposito": "FM/B.U2.EUR.4F.KR.DFR.LEV",
    "euro_dollaro": "EXR/D.USD.EUR.SP00.A", "euro_yen": "EXR/D.JPY.EUR.SP00.A", "euro_franco": "EXR/D.CHF.EUR.SP00.A", "euro_sterlina": "EXR/D.GBP.EUR.SP00.A",
    "euro_yuan": "EXR/D.CNY.EUR.SP00.A",
    # stress sovrano (SovCISS, BCE: stress del debito pubblico per paese) e contributi dei settori al rischio sistemico (banche, mercato monetario, azioni, obbligazioni, cambi)
    "sov_italia": "CISS/D.IT.Z0Z.4F.EC.SOV_CIN.IDX", "sov_spagna": "CISS/D.ES.Z0Z.4F.EC.SOV_CIN.IDX", "sov_francia": "CISS/D.FR.Z0Z.4F.EC.SOV_CIN.IDX",
    "sov_germania": "CISS/D.DE.Z0Z.4F.EC.SOV_CIN.IDX", "sov_grecia": "CISS/D.GR.Z0Z.4F.EC.SOV_CIN.IDX", "sov_portogallo": "CISS/D.PT.Z0Z.4F.EC.SOV_CIN.IDX",
    "sov_irlanda": "CISS/D.IE.Z0Z.4F.EC.SOV_CIN.IDX", "sov_belgio": "CISS/D.BE.Z0Z.4F.EC.SOV_CIN.IDX", "sov_olanda": "CISS/D.NL.Z0Z.4F.EC.SOV_CIN.IDX",
    "sov_austria": "CISS/D.AT.Z0Z.4F.EC.SOV_CIN.IDX", "sov_finlandia": "CISS/D.FI.Z0Z.4F.EC.SOV_CIN.IDX",
    "sov_area_euro_pesata": "CISS/D.U2.Z0Z.4F.EC.SOV_EWN.IDX", "sov_area_euro_pil": "CISS/D.U2.Z0Z.4F.EC.SOV_GDPWN.IDX",
    "ciss_belgio": "CISS/D.BE.Z0Z.4F.EC.SS_CIN.IDX", "ciss_olanda": "CISS/D.NL.Z0Z.4F.EC.SS_CIN.IDX", "ciss_irlanda": "CISS/D.IE.Z0Z.4F.EC.SS_CIN.IDX",
    "ciss_portogallo": "CISS/D.PT.Z0Z.4F.EC.SS_CIN.IDX", "ciss_austria": "CISS/D.AT.Z0Z.4F.EC.SS_CIN.IDX", "ciss_finlandia": "CISS/D.FI.Z0Z.4F.EC.SS_CIN.IDX",
    "ciss_contr_banche": "CISS/D.U2.Z0Z.4F.EC.SS_FIN.CON", "ciss_contr_monetario": "CISS/D.U2.Z0Z.4F.EC.SS_MMN.CON", "ciss_contr_azioni": "CISS/D.U2.Z0Z.4F.EC.SS_EMN.CON",
    "ciss_contr_obbligazioni": "CISS/D.U2.Z0Z.4F.EC.SS_BMN.CON", "ciss_contr_cambi": "CISS/D.U2.Z0Z.4F.EC.SS_FXN.CON", "ciss_contr_correlazione": "CISS/D.U2.Z0Z.4F.EC.SS_CON.CON",
}


def aggiorna_bce(stato: dict) -> None:
    def mk(nome, chiave):
        def job():
            old = store.load("bce_" + nome)
            inizio = "" if old.empty else "&startPeriod=" + (old.index[-1] - timedelta(days=20)).strftime("%Y-%m-%d")
            r = _get(f"https://data-api.ecb.europa.eu/service/data/{chiave}?format=csvdata{inizio}")
            return store.upsert("bce_" + nome, parse_bce(r.text))
        return job
    res = run_parallel({k: mk(k, v) for k, v in BCE.items()}, workers=4, deadline=240)
    stato["bce"] = _riepilogo(res)


# ----------------------------------------------------------------------------- OFR: indice di stress finanziario (Tesoro USA)
def parse_ofr(txt: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt))
    df.index = pd.to_datetime(df[df.columns[0]], errors="coerce")
    return df.drop(columns=df.columns[0])[df.index.notna()]


def aggiorna_ofr(stato: dict) -> None:
    df = parse_ofr(_get("https://www.financialresearch.gov/financial-stress-index/data/fsi.csv").text)
    stato["ofr_stress"] = {"colonne": len(df.columns), "righe_nuove": _upsert_tutte("ofr_", df)}


# ----------------------------------------------------------------------------- Fondi monetari USA: fonte di riserva (la serie FRED settimanale WRMFNS si e' fermata il 05/10/2026)
def parse_ofr_mmf(js) -> pd.Series:
    """Risposta dell'API OFR (lista di [data, valore], oppure dizionario con 'timeseries'/'values'): attivita' totali dei fondi monetari, mensile."""
    if isinstance(js, dict):
        for k in ("timeseries", "values", "data"):
            if k in js:
                js = js[k]
                break
        if isinstance(js, dict) and "aggregation" in js:
            js = js["aggregation"]
    righe = [r for r in js if isinstance(r, (list, tuple)) and len(r) >= 2]
    if not righe:
        raise RuntimeError("OFR fondi monetari: risposta vuota")
    s = pd.Series([r[1] for r in righe], index=pd.to_datetime([r[0] for r in righe], errors="coerce"), dtype="float64").dropna()
    return s[s.index.notna()]


def aggiorna_mmf_alt(stato: dict) -> None:
    r = _get("https://data.financialresearch.gov/v1/series/timeseries?mnemonic=MMF-MMF_TOT-M")
    s = parse_ofr_mmf(r.json())
    stato["mmf_ofr"] = {"ultima": str(s.index[-1].date()), "righe_nuove": store.upsert("mmfalt_ofr_tot", s)}


# ----------------------------------------------------------------------------- Tesoro USA: curve ufficiali giornaliere
UST = {"curva": "daily_treasury_yield_curve", "bills": "daily_treasury_bill_rates", "reali": "daily_treasury_real_yield_curve", "reali_lungo": "daily_treasury_real_long_term"}


def parse_ust(txt: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt))
    df.index = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    return df.drop(columns=["Date"])[df.index.notna()]


def aggiorna_ust(stato: dict) -> None:
    anno = datetime.now(timezone.utc).year
    n, err = 0, {}
    for nome, tipo in UST.items():
        try:
            primo = store.load(f"ust_{nome}_{'1_mo' if nome != 'reali' else '5_yr'}").empty
            anni = range(1990 if nome == "curva" else 2003, anno + 1) if primo else [anno]
            for a in anni:
                url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{a}/all?type={tipo}&field_tdr_date_value={a}&page&_format=csv"
                try:
                    n += _upsert_tutte(f"ust_{nome}_", parse_ust(_get(url, tries=2).text))
                except Exception:  # noqa: BLE001
                    if a == anno:
                        raise
        except Exception as e:  # noqa: BLE001
            err[nome] = str(e)[:60]
    stato["tesoro_curve"] = {"righe_nuove": n, "fallite": err}


# ----------------------------------------------------------------------------- Tesoro USA: cassa, debito, aste
FD = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"


def parse_tga(j: dict) -> pd.Series:
    righe = [r for r in j.get("data", []) if "clos" in str(r.get("account_type", "")).lower() and "tga" in str(r.get("account_type", "")).lower()]
    if not righe:
        righe = [r for r in j.get("data", []) if "clos" in str(r.get("account_type", "")).lower()]
    s = {}
    for r in righe:
        for campo in ("close_today_bal", "open_today_bal"):   # l'API scrive "null" come testo nel campo vuoto
            try:
                s[pd.Timestamp(r["record_date"])] = float(r.get(campo))
                break
            except (TypeError, ValueError, KeyError):
                continue
    return pd.Series(s, dtype=float).sort_index()


def _fd_righe(url: str, pagine: int = 12) -> list[dict]:
    """Legge tutte le pagine di un dataset FiscalData (10.000 righe per pagina)."""
    out: list[dict] = []
    for n in range(1, pagine + 1):
        j = _get(f"{url}&page[size]=10000&page[number]={n}").json()
        out += j.get("data", [])
        if len(j.get("data", [])) < 10000:
            break
    return out


COL_ASTE = ["auction_date", "issue_date", "security_type", "security_term", "cusip", "offering_amt", "total_tendered", "total_accepted", "bid_to_cover_ratio",
            "high_yield", "high_investment_rate", "high_discnt_rate", "avg_med_yield", "primary_dealer_accepted", "direct_bidder_accepted", "indirect_bidder_accepted",
            "primary_dealer_tendered", "direct_bidder_tendered", "indirect_bidder_tendered", "soma_accepted", "reopening"]


def aggiorna_fiscal(stato: dict) -> None:
    out: dict = {}
    # cassa del Tesoro (TGA): quando sale, drena liquidita' dalle banche
    try:
        old = store.load("fisc_tga_milioni")
        da = "2005-01-01" if old.empty else (old.index[-1] - timedelta(days=15)).strftime("%Y-%m-%d")
        out["tga_nuove"] = store.upsert("fisc_tga_milioni", parse_tga({"data": _fd_righe(f"{FD}accounting/dts/operating_cash_balance?filter=record_date:gte:{da}&sort=record_date")}))
    except Exception as e:  # noqa: BLE001
        out["tga_errore"] = str(e)[:60]
    try:
        old = store.load("fisc_debito_pubblico")
        da = "2000-01-01" if old.empty else (old.index[-1] - timedelta(days=15)).strftime("%Y-%m-%d")
        righe = _fd_righe(f"{FD.replace('/v1/', '/v2/')}accounting/od/debt_to_penny?filter=record_date:gte:{da}&sort=record_date")
        s = pd.Series({pd.Timestamp(r["record_date"]): float(r["tot_pub_debt_out_amt"]) for r in righe}).sort_index()
        out["debito_nuove"] = store.upsert("fisc_debito_pubblico", s)
    except Exception as e:  # noqa: BLE001
        out["debito_errore"] = str(e)[:60]
    # aste dei titoli di Stato: domanda (bid-to-cover), chi compra (esteri/dealer), rendimento
    try:
        base = DATA / "aste"
        base.mkdir(parents=True, exist_ok=True)
        p = base / "aste.csv"
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        da = "1990-01-01" if old.empty else (pd.Timestamp(old["auction_date"].max()) - timedelta(days=20)).strftime("%Y-%m-%d")
        j = _get(f"{FD}accounting/od/auctions_query?filter=auction_date:gte:{da}&sort=auction_date&page[size]=10000").json()
        nuovo = pd.DataFrame(j.get("data", []))
        nuovo = nuovo[[c for c in COL_ASTE if c in nuovo.columns]]
        m = pd.concat([old, nuovo], ignore_index=True).drop_duplicates(subset=["auction_date", "security_term", "security_type", "cusip"] if "cusip" in nuovo.columns else None, keep="last")
        m.sort_values("auction_date").to_csv(p, index=False)
        out["aste_righe"] = len(m)
    except Exception as e:  # noqa: BLE001
        out["aste_errore"] = str(e)[:60]
    stato["tesoro_cassa_aste"] = out


# ----------------------------------------------------------------------------- CFTC: posizionamento dei grandi operatori (settimanale)
COT_COL = ["report_date_as_yyyy_mm_dd", "market_and_exchange_names", "open_interest_all", "dealer_positions_long_all", "dealer_positions_short_all",
           "asset_mgr_positions_long", "asset_mgr_positions_short", "lev_money_positions_long", "lev_money_positions_short",
           "other_rept_positions_long", "other_rept_positions_short", "nonrept_positions_long_all", "nonrept_positions_short_all"]
COT_MERCATI = ("S&P 500", "VIX", "NASDAQ", "RUSSELL", "DJIA", "UST", "10-YEAR", "2-YEAR", "5-YEAR", "ULTRA", "EURO FX", "JAPANESE YEN", "BRITISH POUND",
               "USD INDEX", "SWISS FRANC", "CANADIAN DOLLAR", "AUSTRALIAN DOLLAR", "BITCOIN", "ETHER", "NIKKEI", "MSCI", "FED FUNDS", "SOFR", "EURODOLLAR")


def filtra_cot(righe: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(righe)
    if df.empty:
        return df
    df = df[[c for c in COT_COL if c in df.columns]]
    m = df["market_and_exchange_names"].astype(str).str.upper()
    df = df[m.apply(lambda x: any(k in x for k in COT_MERCATI))].copy()
    df["report_date_as_yyyy_mm_dd"] = df["report_date_as_yyyy_mm_dd"].astype(str).str[:10]
    return df


def aggiorna_cot(stato: dict) -> None:
    base = DATA / "cot"
    base.mkdir(parents=True, exist_ok=True)
    p = base / "tff.csv"
    old = pd.read_csv(p) if p.exists() else pd.DataFrame()
    da = "2006-01-01" if old.empty else (pd.Timestamp(old["report_date_as_yyyy_mm_dd"].max()) - timedelta(days=21)).strftime("%Y-%m-%d")
    righe, off = [], 0
    while True:
        url = ("https://publicreporting.cftc.gov/resource/gpe5-46if.json?$limit=20000&$offset=%d&$order=report_date_as_yyyy_mm_dd"
               "&$where=report_date_as_yyyy_mm_dd>'%sT00:00:00.000'" % (off, da))
        blocco = _get(url).json()
        righe += blocco
        if len(blocco) < 20000:
            break
        off += 20000
    nuovo = filtra_cot(righe)
    m = pd.concat([old, nuovo], ignore_index=True).drop_duplicates(subset=["report_date_as_yyyy_mm_dd", "market_and_exchange_names"], keep="last")
    m.sort_values(["report_date_as_yyyy_mm_dd", "market_and_exchange_names"]).to_csv(p, index=False)
    stato["cot_cftc"] = {"righe_totali": len(m), "mercati": int(m["market_and_exchange_names"].nunique())}


# ----------------------------------------------------------------------------- Wikipedia: quanta gente cerca la parola «crollo»
WIKI = ["Stock_market_crash", "Recession", "Great_Recession", "Financial_crisis_of_2007–2008", "Bank_run", "Inflation", "Stagflation", "Short_selling",
        "Margin_call", "Black_Monday_(1987)", "Credit_default_swap", "Bankruptcy", "Federal_Reserve", "Gold_as_an_investment", "Bitcoin", "Layoff", "Unemployment",
        "Debt_ceiling", "Yield_curve", "Dot-com_bubble", "Stock_market_bubble", "Great_Depression", "Subprime_mortgage_crisis", "Lehman_Brothers",
        "Silicon_Valley_Bank", "Bear_market", "Market_trend", "Stock_market", "Volatility_Index", "Hedge_fund", "Bailout", "Default_(finance)", "Sovereign_default",
        "Quantitative_easing", "Interest_rate", "Deflation", "Hyperinflation", "Capital_control", "Currency_crisis", "Bank_failure", "Liquidity_crisis", "Credit_crunch"]


def parse_wiki(j: dict) -> pd.Series:
    d = {pd.Timestamp(str(i["timestamp"])[:8]): float(i["views"]) for i in j.get("items", [])}
    return pd.Series(d, dtype=float).sort_index()


def aggiorna_wiki(stato: dict) -> None:
    ieri = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y%m%d")

    def mk(art):
        def job():
            sid = "wiki_" + slug(art)
            old = store.load(sid)
            da = "20150701" if old.empty else (old.index[-1] - timedelta(days=10)).strftime("%Y%m%d")
            url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{art}/daily/{da}/{ieri}"
            return store.upsert(sid, parse_wiki(_get(url, tries=2).json()))
        return job
    res = run_parallel({a: mk(a) for a in WIKI}, workers=3, deadline=240)
    stato["wikipedia_attenzione"] = _riepilogo(res)


# ----------------------------------------------------------------------------- GDELT: tono e quantita' delle notizie del mondo
GDELT = {"crollo_borsa": '"stock market crash"', "recessione": "recession", "crisi_bancaria": '"bank failure" OR "bank run"', "stretta_credito": '"credit crunch"',
         "default": '"debt default" OR "sovereign default"', "inflazione": "inflation", "licenziamenti": "layoffs", "panico": '"market panic"'}


def parse_gdelt(txt: str) -> pd.Series:
    if "," not in txt[:300]:
        raise RuntimeError("GDELT: risposta vuota o non CSV")
    df = pd.read_csv(io.StringIO(txt))
    col = [c for c in df.columns if c.lower() == "value"][0]
    dcol = [c for c in df.columns if c.lower() == "date"][0]
    s = pd.Series(df[col].values, index=pd.to_datetime(df[dcol]).dt.tz_localize(None).dt.normalize(), dtype=float)
    return s.groupby(level=0).mean().dropna()


def aggiorna_gdelt(stato: dict) -> None:
    n, err = 0, {}
    for nome, q in GDELT.items():
        for modo, suff in (("timelinevolraw", "volume"), ("timelinetone", "tono")):
            try:
                r = _get("https://api.gdeltproject.org/api/v2/doc/doc", tries=2, params={"query": q, "mode": modo, "format": "csv", "timespan": "3months"})
                n += store.upsert(f"gdelt_{nome}_{suff}", parse_gdelt(r.text))
            except Exception as e:  # noqa: BLE001
                err[f"{nome}_{suff}"] = str(e)[:50]
            time.sleep(9)   # il servizio accetta una richiesta ogni 5 secondi: meglio stare larghi
    stato["gdelt_notizie"] = {"righe_nuove": n, "fallite": err}


# ----------------------------------------------------------------------------- criptovalute: liquidita' in stablecoin, TVL, paura cripto
def aggiorna_cripto(stato: dict) -> None:
    out: dict = {}
    try:
        j = _get("https://stablecoins.llama.fi/stablecoincharts/all").json()
        s = pd.Series({pd.Timestamp(int(i["date"]), unit="s"): float((i.get("totalCirculatingUSD") or i.get("totalCirculating") or {}).get("peggedUSD", float("nan"))) for i in j}).dropna()
        out["stablecoin"] = store.upsert("cripto_stablecoin_totale_usd", s.sort_index())
    except Exception as e:  # noqa: BLE001
        out["stablecoin_errore"] = str(e)[:60]
    try:
        j = _get("https://api.llama.fi/v2/historicalChainTvl").json()
        s = pd.Series({pd.Timestamp(int(i["date"]), unit="s"): float(i["tvl"]) for i in j})
        out["tvl"] = store.upsert("cripto_defi_tvl_usd", s.sort_index())
    except Exception as e:  # noqa: BLE001
        out["tvl_errore"] = str(e)[:60]
    try:
        j = _get("https://api.alternative.me/fng/?limit=0&format=json").json()
        s = pd.Series({pd.Timestamp(int(i["timestamp"]), unit="s").normalize(): float(i["value"]) for i in j["data"]})
        out["paura_cripto"] = store.upsert("cripto_paura_avidita", s.sort_index())
    except Exception as e:  # noqa: BLE001
        out["paura_errore"] = str(e)[:60]
    stato["cripto"] = out


# ----------------------------------------------------------------------------- New York Fed: tassi sui prestiti overnight (tensione del finanziamento)
def parse_nyfed(j: dict, campi: dict[str, str]) -> dict[str, pd.Series]:
    righe = j.get("refRates", [])
    out = {}
    for suff, campo in campi.items():
        d = {}
        for r in righe:
            if r.get(campo) is not None:
                d[pd.Timestamp(r["effectiveDate"])] = float(r[campo])
        out[suff] = pd.Series(d, dtype=float).sort_index()
    return out


def aggiorna_nyfed(stato: dict) -> None:
    campi = {"tasso": "percentRate", "p1": "percentPercentile1", "p25": "percentPercentile25", "p75": "percentPercentile75", "p99": "percentPercentile99", "volume_mld": "volumeInBillions"}
    n, err = 0, {}
    for tasso in ("sofr", "tgcr", "bgcr"):
        try:
            j = None
            for n_giorni in (1000, 500, 250, 100):   # un numero troppo alto viene rifiutato: si scende finche' risponde
                try:
                    j = _get(f"https://markets.newyorkfed.org/api/rates/secured/{tasso}/last/{n_giorni}.json", tries=1).json()
                    break
                except Exception:  # noqa: BLE001
                    continue
            if j is None:
                raise RuntimeError("nessun intervallo accettato")
            for suff, s in parse_nyfed(j, campi).items():
                if len(s):
                    n += store.upsert(f"nyfed_{tasso}_{suff}", s)
        except Exception as e:  # noqa: BLE001
            err[tasso] = str(e)[:60]
    stato["nyfed_tassi_overnight"] = {"righe_nuove": n, "fallite": err}


# ----------------------------------------------------------------------------- TSA: persone ai controlli aeroportuali (economia reale, giornaliero)
def aggiorna_tsa(stato: dict) -> None:
    html = _get("https://www.tsa.gov/travel/passenger-volumes").text
    t = pd.read_html(io.StringIO(html))[0]
    t.index = pd.to_datetime(t.iloc[:, 0], errors="coerce")
    t = t[t.index.notna()]
    n = store.upsert("tsa_passeggeri", pd.to_numeric(t.iloc[:, 1].astype(str).str.replace(",", ""), errors="coerce").dropna())
    stato["tsa"] = {"righe_nuove": n}


# ----------------------------------------------------------------------------- FINRA: vendite allo scoperto giornaliere, titolo per titolo
def parse_finra(txt: str, tenere: set[str]) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt), sep="|")
    df = df[df["Date"].astype(str).str.fullmatch(r"\d{8}")]
    tot = pd.DataFrame([{"Date": df["Date"].iloc[0], "Symbol": "_TOTALE", "ShortVolume": df["ShortVolume"].sum(), "ShortExemptVolume": df["ShortExemptVolume"].sum(),
                         "TotalVolume": df["TotalVolume"].sum()}]) if len(df) else pd.DataFrame()
    df = df[df["Symbol"].isin(tenere)][["Date", "Symbol", "ShortVolume", "ShortExemptVolume", "TotalVolume"]]
    return pd.concat([tot, df], ignore_index=True)


def aggiorna_finra(stato: dict) -> None:
    from .accumulo import INTRADAY
    tenere = set(INTRADAY) | {"SPY", "QQQ", "IWM", "DIA", "XLF", "KRE", "HYG", "JNK", "LQD", "TLT", "GLD", "USO", "VXX", "UVXY", "SQQQ", "TQQQ", "SPXU", "SPXL", "ARKK", "IBIT", "COIN", "MSTR"}
    el = DATA / "componenti" / "elenco.csv"
    if el.exists():
        s = pd.read_csv(el)["Symbol"].astype(str)
        tenere |= set(s) | set(s.str.replace("-", ".", regex=False))
    base = DATA / "finra_short"
    base.mkdir(parents=True, exist_ok=True)
    gia = set()
    for f in base.glob("*.csv"):
        gia |= set(pd.read_csv(f, usecols=["Date"])["Date"].astype(str))
    oggi = datetime.now(timezone.utc).date()
    inizio = oggi - timedelta(days=900)
    giorni = [oggi - timedelta(days=i) for i in range(1, 900)]
    giorni = [d for d in giorni if d.weekday() < 5 and d >= inizio and d.strftime("%Y%m%d") not in gia][:60]   # al piu' 60 giorni per giro: il passato si recupera a poco a poco
    festivi = DATA / "finra_short" / "senza_file.txt"
    saltati = set(festivi.read_text().split()) if festivi.exists() else set()
    giorni = [d for d in giorni if d.strftime("%Y%m%d") not in saltati]

    def mk(d):
        def job():
            ymd = d.strftime("%Y%m%d")
            r = requests.get(f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{ymd}.txt", headers=UA, timeout=90)
            if r.status_code == 404:
                return ("assente", ymd)
            r.raise_for_status()
            return ("ok", parse_finra(r.text, tenere))
        return job
    res = run_parallel({d.strftime("%Y%m%d"): mk(d) for d in giorni}, workers=4, deadline=600)
    per_mese: dict[str, list] = {}
    righe, assenti = 0, []
    for k, (t, v) in res.items():
        if t != "ok":
            continue
        if v[0] == "assente":
            if (oggi - datetime.strptime(k, "%Y%m%d").date()).days > 5:
                assenti.append(k)
            continue
        per_mese.setdefault(k[:6], []).append(v[1])
    for ym, dfs in per_mese.items():
        p = base / f"{ym[:4]}-{ym[4:]}.csv"
        nuovo = pd.concat(dfs, ignore_index=True)
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        m = pd.concat([old, nuovo], ignore_index=True).drop_duplicates(subset=["Date", "Symbol"], keep="last").sort_values(["Date", "Symbol"])
        m.to_csv(p, index=False)
        righe += len(nuovo)
    if assenti:
        festivi.write_text("\n".join(sorted(saltati | set(assenti))), encoding="utf-8")
    stato["finra_vendite_scoperto"] = {"giorni_richiesti": len(giorni), "righe_nuove": righe, "senza_file": len(assenti), **{"fallite": {k: str(v)[:50] for k, (t, v) in res.items() if t != "ok"}}}


# ----------------------------------------------------------------------------- istantanee giornaliere di dati che altrove sono a pagamento o senza storia
# Curva dei future VIX (CBOE pubblica gratis il regolamento giornaliero di ogni scadenza), sondaggio AAII, probabilita' dei mercati di previsione.
def scadenze_vix(oggi: pd.Timestamp, indietro: int = 0, avanti: int = 9) -> list[pd.Timestamp]:
    """Scadenze mensili dei future VIX: il mercoledi' che cade 30 giorni prima del terzo venerdi' del mese successivo."""
    out = []
    for k in range(-indietro, avanti + 1):
        m = (oggi.replace(day=1) + pd.DateOffset(months=k + 1))
        primo = m.replace(day=1)
        terzo_ven = primo + pd.Timedelta(days=(4 - primo.weekday()) % 7 + 14)
        out.append(terzo_ven - pd.Timedelta(days=30))
    return out


def parse_vx(txt: str, scadenza: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    col_d = "trade_date" if "trade_date" in df.columns else df.columns[0]
    df["data"] = pd.to_datetime(df[col_d], errors="coerce").dt.strftime("%Y-%m-%d")
    df["scadenza"] = scadenza
    tieni = [c for c in ("data", "scadenza", "open", "high", "low", "close", "settle", "volume", "open_interest") if c in df.columns]
    return df.dropna(subset=["data"])[tieni]


def aggiorna_vix_future(stato: dict) -> None:
    base = DATA / "vix_futures"
    base.mkdir(parents=True, exist_ok=True)
    p = base / "vx.csv"
    old = pd.read_csv(p) if p.exists() else pd.DataFrame()
    oggi = pd.Timestamp(datetime.now(timezone.utc).date())
    sc = scadenze_vix(oggi, indietro=0 if len(old) else 14)
    pezzi, err = [], {}
    for d in sc:
        k = d.strftime("%Y-%m-%d")
        try:
            r = requests.get(f"https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{k}.csv", headers=UA, timeout=60)
            if r.status_code in (403, 404):   # scadenza non ancora listata
                continue
            r.raise_for_status()
            txt = "\n".join(l for l in r.text.splitlines() if l.strip() and not l.lower().startswith(("product", "cboe")))
            pezzi.append(parse_vx(txt, k))
        except Exception as e:  # noqa: BLE001
            err[k] = str(e)[:50]
    if pezzi:
        m = pd.concat([old] + pezzi, ignore_index=True).drop_duplicates(subset=["data", "scadenza"], keep="last").sort_values(["data", "scadenza"])
        m.to_csv(p, index=False)
    stato["vix_future_curva"] = {"scadenze_tentate": len(sc), "scaricate": len(pezzi), "fallite": err}


def parse_aaii(df: pd.DataFrame) -> pd.DataFrame:
    """Cerca la riga d'intestazione con Bullish/Bearish e restituisce data + percentuali."""
    for i in range(min(15, len(df))):
        riga = [str(x).strip().lower() for x in df.iloc[i].tolist()]
        if any("bullish" == x for x in riga) and any("bearish" == x for x in riga):
            t = df.iloc[i + 1:].copy()
            t.columns = [str(x).strip().lower() for x in df.iloc[i].tolist()]
            t = t.rename(columns={t.columns[0]: "data"})
            t["data"] = pd.to_datetime(t["data"], errors="coerce")
            t = t[t["data"].notna()].set_index("data")
            return t[[c for c in ("bullish", "neutral", "bearish") if c in t.columns]].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    raise RuntimeError("intestazione AAII non trovata")


def aggiorna_aaii(stato: dict) -> None:
    r = _get("https://www.aaii.com/files/surveys/sentiment.xls", tries=2, headers={**BROWSER, "Referer": "https://www.aaii.com/sentimentsurvey/sent_results"})
    df = pd.read_excel(io.BytesIO(r.content), header=None)
    t = parse_aaii(df)
    t = t / 100.0 if t.max().max() > 1.5 else t
    stato["aaii_sondaggio"] = {"righe_nuove": _upsert_tutte("aaii_", t)}


def aggiorna_previsioni(stato: dict) -> None:
    """Probabilita' implicite (prezzo del «si») dei mercati di previsione su recessione, tassi, crolli. Istantanea: la storia nasce da qui."""
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    righe = []
    for q in ("recession", "fed rate", "stock market crash", "S&P 500", "bank failure", "default"):
        try:
            j = _get("https://gamma-api.polymarket.com/public-search", tries=2, params={"q": q, "limit_per_type": 8}).json()
            for ev in j.get("events", [])[:8]:
                for m in ev.get("markets", [])[:6]:
                    pr = m.get("outcomePrices")
                    if isinstance(pr, str):
                        pr = json.loads(pr)
                    if pr:
                        righe.append({"data": oggi, "tema": q, "evento": str(ev.get("title", ""))[:80], "mercato": str(m.get("question", ""))[:100],
                                      "prob_si": float(pr[0]), "volume": m.get("volume"), "fine": str(m.get("endDate", ""))[:10]})
        except Exception:  # noqa: BLE001
            continue
    if not righe:
        raise RuntimeError("nessun mercato letto")
    base = DATA / "previsioni"
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{oggi[:4]}.csv"
    old = pd.read_csv(p) if p.exists() else pd.DataFrame()
    m = pd.concat([old, pd.DataFrame(righe)], ignore_index=True).drop_duplicates(subset=["data", "mercato"], keep="last")
    m.to_csv(p, index=False)
    stato["mercati_previsione"] = {"righe_oggi": len(righe)}


# ----------------------------------------------------------------------------- NY Fed: posizioni e finanziamento dei dealer primari (settimanale, gratis)
def parse_dealer(j) -> pd.DataFrame:
    """Trova ovunque nel JSON le righe con keyid, asofdate, value."""
    righe = []

    def giu(x):
        if isinstance(x, dict):
            if "keyid" in x and "asofdate" in x and "value" in x:
                righe.append((x["keyid"], x["asofdate"], x["value"]))
            else:
                for v in x.values():
                    giu(v)
        elif isinstance(x, list):
            for v in x:
                giu(v)
    giu(j)
    df = pd.DataFrame(righe, columns=["keyid", "data", "valore"])
    df["valore"] = pd.to_numeric(df["valore"], errors="coerce")
    return df.dropna()


def aggiorna_dealer(stato: dict) -> None:
    base = DATA / "dealer"
    base.mkdir(parents=True, exist_ok=True)
    lista = _get("https://markets.newyorkfed.org/api/pd/list/timeseries.json").json()
    chiavi = sorted({str(t["keyid"]) for t in _trova(lista) if t.get("keyid")})
    chiavi = [k for k in chiavi if k and k.startswith(("PDPOS", "PDFTD", "PDFTR", "PDSIOS", "PDSIOSB", "PDSOOS", "PDFI", "PDTR"))][:260]

    def mk(k):
        def job():
            return parse_dealer(_get(f"https://markets.newyorkfed.org/api/pd/get/{k}.json", tries=2).json())
        return job
    res = run_parallel({k: mk(k) for k in chiavi}, workers=4, deadline=300)
    nuovi = [v for (t, v) in res.values() if t == "ok" and len(v)]
    if nuovi:
        p = base / "dealer.csv"
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        m = pd.concat([old] + nuovi, ignore_index=True).drop_duplicates(subset=["keyid", "data"], keep="last").sort_values(["keyid", "data"])
        m.to_csv(p, index=False)
    stato["nyfed_dealer"] = {"serie_richieste": len(chiavi), **_riepilogo(res)}


def _trova(j) -> list[dict]:
    out = []

    def giu(x):
        if isinstance(x, dict):
            if "keyid" in x:
                out.append(x)
            for v in x.values():
                giu(v)
        elif isinstance(x, list):
            for v in x:
                giu(v)
    giu(j)
    return out


# ----------------------------------------------------------------------------- SEC: titoli venduti e non consegnati (fails to deliver, quindicinale)
def parse_ftd(txt: str, tenere: set[str]) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt), sep="|", dtype=str, on_bad_lines="skip")
    df.columns = [c.strip().upper() for c in df.columns]
    q = [c for c in df.columns if c.startswith("QUANTITY")][0]
    df["q"] = pd.to_numeric(df[q], errors="coerce")
    df["p"] = pd.to_numeric(df.get("PRICE"), errors="coerce")
    df["data"] = pd.to_datetime(df["SETTLEMENT DATE"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["data", "q"])
    tot = df.groupby("data").agg(fails=("q", "sum"), valore=("p", lambda s: float((s * df.loc[s.index, "q"]).sum()))).reset_index().assign(symbol="_TOTALE")
    sel = df[df["SYMBOL"].isin(tenere)].rename(columns={"SYMBOL": "symbol"}).assign(fails=lambda d: d["q"], valore=lambda d: d["q"] * d["p"])[["data", "symbol", "fails", "valore"]]
    return pd.concat([tot[["data", "symbol", "fails", "valore"]], sel], ignore_index=True)


def _titoli_chiave() -> set[str]:
    from .accumulo import INTRADAY
    t = {s for s in INTRADAY if s.isalpha()} | {"SPY", "QQQ", "IWM", "TLT", "HYG", "TQQQ", "SQQQ", "UVXY", "VXX"}
    el = DATA / "componenti" / "elenco.csv"
    if el.exists():
        t |= set(pd.read_csv(el)["Symbol"].astype(str))
    return t


def aggiorna_ftd(stato: dict) -> None:
    import zipfile

    from . import sec_dati
    tenere = _titoli_chiave()
    base = DATA / "ftd"
    base.mkdir(parents=True, exist_ok=True)
    oggi = datetime.now(timezone.utc)
    nomi = []
    for k in range(0, 5):
        d = (oggi.replace(day=1) - timedelta(days=30 * k)).strftime("%Y%m")
        nomi += [f"cnsfails{d}b.zip", f"cnsfails{d}a.zip"]
    pezzi, saltati = [], []
    for nome in nomi:
        try:
            r = requests.get(f"https://www.sec.gov/files/data/fails-deliver-data/{nome}", headers=sec_dati.ua(), timeout=90)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            pezzi.append(parse_ftd(z.read(z.namelist()[0]).decode("latin-1"), tenere))
        except Exception as e:  # noqa: BLE001
            saltati.append(f"{nome}: {str(e)[:40]}")
        time.sleep(0.3)
    if not pezzi:
        raise RuntimeError("nessun file letto: " + "; ".join(saltati[:3]))
    nuovo = pd.concat(pezzi, ignore_index=True)
    for ym, g in nuovo.groupby(nuovo["data"].str[:7]):
        p = base / f"{ym}.csv"
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        pd.concat([old, g], ignore_index=True).drop_duplicates(subset=["data", "symbol"], keep="last").sort_values(["data", "symbol"]).to_csv(p, index=False)
    stato["sec_fails_to_deliver"] = {"file_letti": len(pezzi), "righe": len(nuovo), "problemi": saltati[:5]}


# ----------------------------------------------------------------------------- FINRA: short interest (due volte al mese)
def date_short_interest(oggi: pd.Timestamp, mesi: int = 3) -> list[str]:
    """Giorni di regolamento ufficiali: il 15 e l'ultimo giorno del mese (se festivo, il giorno lavorativo prima)."""
    out = []
    for k in range(mesi + 1):
        m = oggi - pd.DateOffset(months=k)
        for d in (m.replace(day=15), m + pd.offsets.MonthEnd(0)):
            while d.weekday() >= 5:
                d -= pd.Timedelta(days=1)
            if d < oggi:
                out.append(d.strftime("%Y%m%d"))
    return sorted(set(out))


def parse_short_interest(txt: str, tenere: set[str]) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt), sep="|", dtype=str, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    sym = "symbolCode" if "symbolCode" in df.columns else df.columns[1]
    df = df[df[sym].isin(tenere)]
    ren = {sym: "symbol", "currentShortPositionQuantity": "short", "previousShortPositionQuantity": "short_prec", "averageDailyVolumeQuantity": "vol_medio",
           "daysToCoverQuantity": "giorni_per_coprire", "settlementDate": "data"}
    df = df.rename(columns=ren)
    tieni = [c for c in ("data", "symbol", "short", "short_prec", "vol_medio", "giorni_per_coprire") if c in df.columns]
    return df[tieni]


def aggiorna_short_interest(stato: dict) -> None:
    tenere = _titoli_chiave()
    base = DATA / "short_interest"
    base.mkdir(parents=True, exist_ok=True)
    pezzi, assenti = [], 0
    for d in date_short_interest(pd.Timestamp(datetime.now(timezone.utc).date())):
        r = requests.get(f"https://cdn.finra.org/equity/otcmarket/biweekly/shrt{d}.csv", headers=UA, timeout=90)
        if r.status_code in (403, 404):   # il sito risponde 403 quando il file di quella data non esiste ancora
            assenti += 1
            continue
        r.raise_for_status()
        t = parse_short_interest(r.text, tenere)
        if "data" not in t.columns:
            t["data"] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        pezzi.append(t)
    if not pezzi:
        raise RuntimeError(f"nessun file (assenti {assenti})")
    nuovo = pd.concat(pezzi, ignore_index=True)
    p = base / "short_interest.csv"
    old = pd.read_csv(p, dtype=str) if p.exists() else pd.DataFrame()
    pd.concat([old, nuovo.astype(str)], ignore_index=True).drop_duplicates(subset=["data", "symbol"], keep="last").sort_values(["data", "symbol"]).to_csv(p, index=False)
    stato["finra_short_interest"] = {"file_letti": len(pezzi), "righe": len(nuovo), "file_assenti": assenti}


# ----------------------------------------------------------------------------- ETF: patrimonio e quote in circolazione (per ricavare i flussi giorno per giorno)
ETF_FLUSSI = ("SPY IVV VOO VTI QQQ IWM DIA EFA EEM VWO AGG BND LQD HYG JNK TLT IEF SHY TIP GLD SLV USO XLF XLK XLE XLV XLY XLP XLI XLU XLB XLRE XLC KRE KBE SMH SOXX "
              "XBI IBB ARKK EMB MUB BKLN BIL SGOV SHV VXX UVXY SQQQ TQQQ SH SDS SPXU SPXL IBIT FBTC GBTC ETHE VEA IEFA IEMG IJH IJR MDY RSP SCHD VYM VNQ").split()


def aggiorna_etf_quote(stato: dict) -> None:
    import yfinance as yf
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def mk(s):
        def job():
            info = yf.Ticker(s).info or {}
            return {"data": oggi, "symbol": s, "patrimonio": info.get("totalAssets"), "quote": info.get("sharesOutstanding"), "nav": info.get("navPrice"),
                    "prezzo": info.get("regularMarketPrice") or info.get("previousClose"), "premio": info.get("bid"), "rend_ytd": info.get("ytdReturn"),
                    "rend_div": info.get("yield")}
        return job
    res = run_parallel({s: mk(s) for s in ETF_FLUSSI}, workers=4, deadline=300)
    righe = [v for (t, v) in res.values() if t == "ok" and (v.get("patrimonio") or v.get("quote"))]
    if not righe:
        raise RuntimeError("nessun dato letto")
    base = DATA / "etf_quote"
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{oggi[:4]}.csv"
    old = pd.read_csv(p) if p.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame(righe)], ignore_index=True).drop_duplicates(subset=["data", "symbol"], keep="last").to_csv(p, index=False)
    stato["etf_patrimonio_quote"] = {"richiesti": len(ETF_FLUSSI), "letti": len(righe)}
