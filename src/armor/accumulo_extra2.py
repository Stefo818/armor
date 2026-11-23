"""Terza ondata di fonti (23/11/2026): segnali «laterali» gratuiti.
- moduli depositati alla SEC (quante IPO, quante societa' in ritardo coi bilanci, quante escono dalla Borsa) e parole di stress nei documenti (EDGAR full-text);
- leva e paura del mondo cripto (finanziamento dei perpetui, posizioni aperte, DVOL, put/call), capitalizzazione totale;
- curva dei titoli di Stato giapponesi (carry trade); testi delle banche centrali e titoli di giornale su parole di crisi; fervore degli investitori retail.
Ogni funzione e' indipendente e riempie `stato`; i parser non usano la rete cosi' si provano con dati finti."""
from __future__ import annotations

import io
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

from . import store
from .accumulo_extra import UA, _get, slug
from .config import DATA


# ----------------------------------------------------------------------------- SEC: conteggio giornaliero dei moduli depositati
MODULI = ("8-K", "10-K", "10-Q", "NT 10-K", "NT 10-Q", "15-12G", "15-12B", "25-NSE", "25", "S-1", "S-1/A", "F-1", "424B4", "424B5", "S-3", "S-3ASR", "SC 13D", "SC 13G", "SC TO-I",
          "SC 14D9", "425", "SC 13E3", "4", "3", "144", "D", "N-CSR", "8-K12B", "RW", "AW", "EFFECT", "S-4", "DEF 14A", "DEFM14A", "SC TO-T", "SC13D", "SCHEDULE 13D")
RIGA_FORM = re.compile(r"^(\S.*?)\s{2,}.*?(\d{4}-\d{2}-\d{2})\s+edgar/")


def conta_moduli(righe, tenere=MODULI) -> pd.DataFrame:
    """Dal form.idx trimestrale: conteggio per (data, modulo)."""
    c: dict[tuple[str, str], int] = {}
    t = set(tenere)
    for r in righe:
        m = RIGA_FORM.match(r)
        if m and m.group(1).strip() in t:
            k = (m.group(2), m.group(1).strip())
            c[k] = c.get(k, 0) + 1
    return pd.DataFrame([{"data": d, "modulo": f, "n": n} for (d, f), n in c.items()])


def aggiorna_moduli_sec(stato: dict) -> None:
    from . import sec_dati
    base = DATA / "sec_moduli"
    base.mkdir(parents=True, exist_ok=True)
    fatti_f = base / "fatti.txt"
    fatti = set(fatti_f.read_text().split()) if fatti_f.exists() else set()
    oggi = datetime.now(timezone.utc)
    q_ora = (oggi.year, (oggi.month - 1) // 3 + 1)
    elenco = [(y, q) for y in range(2015, oggi.year + 1) for q in (1, 2, 3, 4) if (y, q) <= q_ora]
    recenti = elenco[-2:]
    vecchi = [x for x in elenco[:-2] if f"{x[0]}q{x[1]}" not in fatti][-4:]   # al piu' 4 trimestri passati per giro: la storia si completa col tempo
    nuovi, letti, err = [], 0, {}
    for y, q in recenti + vecchi:
        try:
            r = sec_dati._get(sec_dati.INDICE.format(y=y, q=q), stream=True, timeout=300)
            righe = r.content.decode("latin-1").splitlines()
            nuovi.append(conta_moduli(righe))
            letti += 1
            if (y, q) in vecchi or (y, q) != q_ora:
                fatti.add(f"{y}q{q}")
        except Exception as e:  # noqa: BLE001
            err[f"{y}q{q}"] = str(e)[:60]
    if not nuovi:
        raise RuntimeError("nessun indice letto: " + "; ".join(list(err.values())[:2]))
    t = pd.concat(nuovi, ignore_index=True)
    t["data"] = pd.to_datetime(t["data"])
    n = 0
    for f, g in t.groupby("modulo"):
        s = g.groupby("data")["n"].sum().astype(float)
        n += store.upsert("secmod_" + slug(f), s)
    fatti_f.write_text("\n".join(sorted(fatti)))
    stato["sec_moduli_depositati"] = {"trimestri_letti": letti, "moduli": int(t["modulo"].nunique()), "righe_nuove": n, "problemi": err}


# ----------------------------------------------------------------------------- SEC: parole di stress nei documenti depositati (ricerca a testo pieno)
TERMINI = {"going_concern": '"going concern"', "dubbio_sostanziale": '"substantial doubt"', "violazione_covenant": '"covenant" "waiver"', "chapter_11": '"chapter 11"',
           "forbearance": "forbearance", "margin_call": '"margin call"', "riduzione_personale": '"reduction in force"', "svalutazione_avviamento": '"goodwill impairment"',
           "linea_credito_ritirata": '"revolving credit" "terminated"', "ristrutturazione_debito": '"debt restructuring"', "default_cross": '"cross-default"', "ritardo_bilancio": '"unable to file"'}


def totale_efts(j: dict) -> int:
    h = j.get("hits", {}).get("total", {})
    return int(h.get("value", h) if isinstance(h, dict) else h)


def aggiorna_parole_sec(stato: dict) -> None:
    from . import sec_dati
    oggi = datetime.now(timezone.utc).date()
    n, err, richieste = 0, {}, 0
    for nome, q in TERMINI.items():
        sid = "efts_" + nome
        old = store.load(sid)
        ultimo = old.index[-1].date() if len(old) else oggi - timedelta(days=40)
        giorni = [ultimo - timedelta(days=3) + timedelta(days=i) for i in range(1, (oggi - ultimo).days + 3)]
        giorni = [d for d in giorni if d < oggi and d.weekday() < 5][-20:]
        dati = {}
        for d in giorni:
            try:
                r = requests.get("https://efts.sec.gov/LATEST/search-index", params={"q": q, "dateRange": "custom", "startdt": d.isoformat(), "enddt": d.isoformat(), "forms": "8-K,10-Q,10-K"},
                                 headers=sec_dati.ua(), timeout=60)
                richieste += 1
                r.raise_for_status()
                dati[pd.Timestamp(d)] = float(totale_efts(r.json()))
            except Exception as e:  # noqa: BLE001
                err[nome] = str(e)[:50]
                break
            time.sleep(0.15)
        if dati:
            n += store.upsert(sid, pd.Series(dati))
    stato["sec_parole_di_stress"] = {"richieste": richieste, "righe_nuove": n, "problemi": err}


# ----------------------------------------------------------------------------- cripto: leva (perpetui), paura (DVOL), put/call, totale di mercato
def parse_dvol(j: dict) -> pd.Series:
    d = j.get("result", {}).get("data", [])
    return pd.Series({pd.Timestamp(int(r[0]), unit="ms").normalize(): float(r[4]) for r in d}, dtype=float).sort_index()


def put_call_deribit(j: dict) -> dict:
    put = call = 0.0
    for r in j.get("result", []):
        nome = str(r.get("instrument_name", ""))
        oi = float(r.get("open_interest") or 0)
        if nome.endswith("-P"):
            put += oi
        elif nome.endswith("-C"):
            call += oi
    return {"put_oi": put, "call_oi": call, "put_call": put / call if call else float("nan")}


def aggiorna_cripto_leva(stato: dict) -> None:
    oggi = pd.Timestamp(datetime.now(timezone.utc).date())
    out, n = {}, 0
    for coin in ("BTC", "ETH"):
        try:
            old = store.load(f"cripto_dvol_{coin.lower()}")
            da = datetime(2021, 3, 1) if old.empty else old.index[-1].to_pydatetime() - timedelta(days=10)
            j = _get("https://www.deribit.com/api/v2/public/get_volatility_index_data", tries=2,
                     params={"currency": coin, "start_timestamp": int(da.timestamp() * 1000), "end_timestamp": int(time.time() * 1000), "resolution": "1D"}).json()
            n += store.upsert(f"cripto_dvol_{coin.lower()}", parse_dvol(j))
            pc = put_call_deribit(_get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency", tries=2, params={"currency": coin, "kind": "option"}).json())
            for k, v in pc.items():
                if v == v:
                    n += store.upsert(f"cripto_deribit_{coin.lower()}_{k}", pd.Series({oggi: v}))
        except Exception as e:  # noqa: BLE001
            out[f"deribit_{coin}"] = str(e)[:50]
    for sym in ("BTC", "ETH", "SOL"):
        try:
            f = _get(f"https://www.okx.com/api/v5/public/funding-rate?instId={sym}-USDT-SWAP", tries=2).json()["data"][0]
            n += store.upsert(f"cripto_okx_{sym.lower()}_funding", pd.Series({oggi: float(f["fundingRate"])}))
            o = _get(f"https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId={sym}-USDT-SWAP", tries=2).json()["data"][0]
            n += store.upsert(f"cripto_okx_{sym.lower()}_posizioni_aperte_usd", pd.Series({oggi: float(o.get("oiUsd") or 0)}))
        except Exception as e:  # noqa: BLE001
            out[f"okx_{sym}"] = str(e)[:50]
    try:
        g = _get("https://api.coingecko.com/api/v3/global", tries=2).json()["data"]
        n += store.upsert("cripto_capitalizzazione_totale_usd", pd.Series({oggi: float(g["total_market_cap"]["usd"])}))
        n += store.upsert("cripto_dominanza_bitcoin", pd.Series({oggi: float(g["market_cap_percentage"]["btc"])}))
    except Exception as e:  # noqa: BLE001
        out["coingecko"] = str(e)[:50]
    stato["cripto_leva"] = {"righe_nuove": n, "problemi": out}


# ----------------------------------------------------------------------------- Giappone: curva dei titoli di Stato
def parse_jgb(txt: str) -> pd.DataFrame:
    righe = txt.splitlines()
    i = next(k for k, r in enumerate(righe) if r.lower().startswith("date"))
    df = pd.read_csv(io.StringIO("\n".join(righe[i:])), na_values=["-", ""])
    df.index = pd.to_datetime(df[df.columns[0]], format="%Y/%m/%d", errors="coerce")
    return df.drop(columns=df.columns[0])[df.index.notna()]


def aggiorna_jgb(stato: dict) -> None:
    from .accumulo_extra import _upsert_tutte
    r = _get("https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv")
    df = parse_jgb(r.text)
    stato["giappone_curva_titoli_di_stato"] = {"colonne": len(df.columns), "righe_nuove": _upsert_tutte("jgb_", df)}


# ----------------------------------------------------------------------------- testi delle banche centrali e titoli di giornale su parole di crisi
FEED = {"fed_comunicati": "https://www.federalreserve.gov/feeds/press_all.xml", "fed_discorsi": "https://www.federalreserve.gov/feeds/speeches_and_testimony.xml",
        "bce_comunicati": "https://www.ecb.europa.eu/rss/press.html", "sec_comunicati": "https://www.sec.gov/news/pressreleases.rss"}
GNEWS = {"corsa_agli_sportelli": '"bank run"', "margin_call": '"margin call"', "stretta_di_credito": '"credit crunch"', "crisi_di_liquidita": '"liquidity crisis"',
         "crollo_di_borsa": '"stock market crash"', "timori_recessione": '"recession fears"', "licenziamenti": "layoffs", "fallimento": '"files for bankruptcy"',
         "taglio_rating": "downgrade", "default": '"debt default"', "fondo_in_difficolta": '"hedge fund" losses', "banca_in_difficolta": '"bank shares plunge"'}


def parse_rss(txt: str) -> list[dict]:
    root = ET.fromstring(txt)
    out = []
    for it in list(root.iter("item")) + list(root.iter("{http://www.w3.org/2005/Atom}entry")):
        def t(*nomi):
            for n in nomi:
                e = it.find(n)
                if e is not None and (e.text or "").strip():
                    return e.text.strip()
            return ""
        data = t("pubDate", "{http://www.w3.org/2005/Atom}updated", "{http://purl.org/dc/elements/1.1/}date")
        try:
            d = parsedate_to_datetime(data) if "," in data else pd.Timestamp(data).to_pydatetime()
        except Exception:  # noqa: BLE001
            continue
        out.append({"data": pd.Timestamp(d).tz_convert("UTC").strftime("%Y-%m-%d") if pd.Timestamp(d).tzinfo else pd.Timestamp(d).strftime("%Y-%m-%d"),
                    "titolo": re.sub(r"\s+", " ", t("title", "{http://www.w3.org/2005/Atom}title"))[:200], "link": t("link")[:200]})
    return out


def aggiorna_testi(stato: dict) -> None:
    base = DATA / "testi"
    base.mkdir(parents=True, exist_ok=True)
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    righe, err = [], {}
    for nome, url in FEED.items():
        try:
            righe += [{**r, "fonte": nome} for r in parse_rss(_get(url, tries=2).text)]
        except Exception as e:  # noqa: BLE001
            err[nome] = str(e)[:50]
    conteggi = {}
    for nome, q in GNEWS.items():
        try:
            it = parse_rss(_get("https://news.google.com/rss/search", tries=2, params={"q": q + " when:7d", "hl": "en-US", "gl": "US", "ceid": "US:en"}).text)
            c = pd.Series([r["data"] for r in it]).value_counts()
            conteggi[nome] = {pd.Timestamp(d): float(v) for d, v in c.items() if d < oggi}   # solo giorni completi
            righe += [{**r, "fonte": "giornali_" + nome} for r in it]
        except Exception as e:  # noqa: BLE001
            err[nome] = str(e)[:50]
        time.sleep(1)
    n = sum(store.upsert("gnews_" + k, pd.Series(v)) for k, v in conteggi.items() if v)
    if righe:
        p = base / f"{oggi[:4]}.csv"
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        pd.concat([old, pd.DataFrame(righe)], ignore_index=True).drop_duplicates(subset=["fonte", "data", "titolo"], keep="first").to_csv(p, index=False)
    stato["testi_e_giornali"] = {"titoli_oggi": len(righe), "righe_conteggi_nuove": n, "problemi": err}


# ----------------------------------------------------------------------------- fervore dei piccoli investitori (menzioni sui forum)
def parse_apewisdom(j: dict, data: str) -> pd.DataFrame:
    return pd.DataFrame([{"data": data, "ticker": r.get("ticker"), "rank": r.get("rank"), "menzioni": r.get("mentions"), "voti_positivi": r.get("upvotes"),
                          "rank_24h": r.get("rank_24h_ago"), "menzioni_24h": r.get("mentions_24h_ago")} for r in j.get("results", [])])


def aggiorna_retail(stato: dict) -> None:
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pezzi = [parse_apewisdom(_get(f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{p}", tries=2).json(), oggi) for p in (1, 2)]
    t = pd.concat(pezzi, ignore_index=True)
    if t.empty:
        raise RuntimeError("nessun dato")
    base = DATA / "retail"
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{oggi[:4]}.csv"
    old = pd.read_csv(p) if p.exists() else pd.DataFrame()
    pd.concat([old, t], ignore_index=True).drop_duplicates(subset=["data", "ticker"], keep="last").to_csv(p, index=False)
    n = store.upsert("retail_menzioni_totali", pd.Series({pd.Timestamp(oggi): float(pd.to_numeric(t["menzioni"], errors="coerce").sum())}))
    stato["retail_forum"] = {"titoli": len(t), "righe_nuove": n}
