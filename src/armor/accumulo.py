"""Accumulo dati per le ricerche future (23/11/2026).

Scopo: registrare ogni giorno quanto piu' dato possibile (mercati, tassi, credito, materie prime, valute, economia,
intraday a 5 minuti, opzioni, componenti dell'S&P 500), perche' fra qualche mese si potranno cercare correlazioni
sui dati nuovi con la regola «scelta sul passato, verifica in avanti». Nessuna di queste serie entra nei modelli
o nelle schede: sono solo archivio. Ogni fonte e' indipendente: se una fallisce, le altre continuano.

Struttura (tutta dentro data/):
- series/x_<simbolo>.csv e xv_<simbolo>.csv  chiusure e volumi giornalieri di Yahoo Finance
- series/f_<codice>.csv                       serie economiche e finanziarie di FRED
- series/cboe_pc_<nome>.csv                   rapporti put/call CBOE (totale, azioni, indici, S&P 500, VIX)
- ohlc/<simbolo>.csv                          apertura/massimo/minimo/chiusura/volume giornalieri degli strumenti chiave
- vedi accumulo_extra.py per BCE, OFR, Tesoro, CFTC, Wikipedia, GDELT, criptovalute, NY Fed, TSA, FINRA
- intraday/AAAA-MM/AAAA-MM-GG.csv.gz           barre a 5 minuti (UTC): un file per giorno con tutti gli strumenti (colonna sym)
- componenti/{close,vol}_AAAA-MM.csv.gz       prezzi e volumi giornalieri delle aziende dell'S&P 500 (colonne = titoli)
- opzioni_ext/AAAA-MM.csv                     riepilogo giornaliero delle catene di opzioni per scadenza (volumi, OI, volatilita', asimmetria, gamma)
- accumulo_stato.json                         cosa e' stato scritto oggi e cosa e' fallito
"""
from __future__ import annotations

import gzip
import io
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from . import sources, store
from .config import DATA
from .guard import run_parallel

UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
STATO = DATA / "accumulo_stato.json"

# ----------------------------------------------------------------------------- elenchi
YAHOO = {
    "indici_usa": "^DJI ^IXIC ^NYA ^OEX ^MID ^SML ^DJT ^DJU ^BKX ^XAX ^NDX ^RUT ^SOX ^GSPC",
    "volatilita": "^VIX1D ^VXN ^VXD ^OVX ^GVZ ^COR1M ^COR3M ^COR6M ^VXTLT ^VXEEM ^VXEWZ ^TYVIX ^VVIX ^SKEW ^VIX9D ^VIX3M ^VIX6M",
    "borse_estere": "^FTSE ^FCHI ^GDAXI ^IBEX ^AEX ^SSMI ^OMXS30 ^BFX ^ATX ^N225 ^HSI ^KS11 ^TWII ^AXJO ^NSEI ^BSESN ^BVSP ^MXX ^GSPTSE ^JKSE ^STI 000001.SS 399001.SZ ^TA125.TA ^MERV ^XU100.IS ^STOXX50E ^STOXX FTSEMIB.MI",
    "paesi_etf": "EWJ EWG EWU EWQ EWI EWP EWL EWC EWA EWZ EWW EWY EWT EWH FXI MCHI INDA EZA TUR EIDO THD VNM EPOL ARGT EWS EWN EWD EWK EIS KSA UAE QAT",
    "settori_industrie": "XLK XLF XLE XLV XLY XLP XLI XLU XLB XLRE XLC XBI IBB XHB XRT XME XOP OIH KRE KBE KIE IAK IYR VNQ REM SOXX SMH IGV SKYY CLOU HACK ARKK ITB JETS XAR ITA ICLN TAN LIT URA BOTZ IYT XTN FDN SOCL MOO PBW XPH IHI XSD",
    "stili_fattori": "SPY QQQ IWM IWF IWD IWN IWO IWP IWS IJH IJR MDY VTV VUG MTUM QUAL USMV SPLV SPHB VLUE SIZE RSP EQAL DIA VOO VTI VEA VWO ACWI VXUS EFA EEM IEFA IEMG SCHD VYM DVY HDV NOBL COWZ",
    "obbligazioni_credito": "SHY IEI IEF TLH TLT GOVT AGG BND LQD VCIT VCSH HYG JNK USHY SJNK BKLN SRLN EMB MUB TIP VTIP MBB BIL SHV FLOT PFF CWB ANGL BIZD EMLC LEMB BNDX IGIB IGSB SPSB VGSH VGIT VGLT ZROZ EDV TMF TBT TBF",
    "tassi_usa": "^TNX ^FVX ^IRX ^TYX",
    "valute": "EURUSD=X GBPUSD=X USDCHF=X USDJPY=X AUDUSD=X NZDUSD=X USDCAD=X USDCNY=X USDINR=X USDMXN=X USDBRL=X USDZAR=X USDTRY=X USDKRW=X USDSEK=X USDNOK=X EURJPY=X EURGBP=X EURCHF=X USDRUB=X USDIDR=X USDTHB=X USDSGD=X USDHKD=X USDPLN=X USDHUF=X DX-Y.NYB UUP UDN FXE FXY FXA FXF FXB FXC CEW",
    "materie_prime": "CL=F BZ=F NG=F HO=F RB=F GC=F SI=F PL=F PA=F HG=F ZC=F ZW=F ZS=F ZL=F ZM=F KC=F SB=F CT=F CC=F LE=F HE=F OJ=F USO UNG GLD SLV DBC DBA PDBC CPER WEAT CORN SOYB DBB DBE DBP PPLT PALL GDX GDXJ SIL COPX REMX",
    "futures_indici": "ES=F NQ=F YM=F RTY=F ZN=F ZB=F ZF=F ZT=F",
    "crypto": "BTC-USD ETH-USD SOL-USD BNB-USD XRP-USD ADA-USD DOGE-USD AVAX-USD LINK-USD IBIT GBTC ETHE COIN MSTR MARA RIOT",
    "banche_estere": "DB UBS BCS SAN ING BBVA HSBC NWG LYG ITUB BMA TD RY BNS",
    "economia_reale_trasporti": "BDRY ZIM SBLK MATX LBR=F BCI GSG WOOD UPS FDX XTN IYT",
    "credito_privato_gestori": "ARCC OBDC BXSL FSK GBDC OWL APO KKR BX CG ARES PRIV",
    "immobiliare_commerciale": "VNO SLG BXP MPW NLY AGNC MORT REM SRVR INDS",
    "volatilita_etf": "VXX UVXY SVXY VIXY SQQQ TQQQ SH SDS SPXU SPXL TZA TNA UPRO TLT TMV",
}
# serie FRED (id = f_<codice minuscolo>)
FRED_EXT = """
DGS1MO DGS3MO DGS6MO DGS1 DGS3 DGS5 DGS7 DGS20 DGS30 DFII5 DFII7 DFII20 DFII30 T5YIE T5YIFR T10YFF T5YFF DTB3 DTB6 DTB1YR SOFR OBFR EFFR DPRIME DCPF3M DCPN3M MORTGAGE30US MORTGAGE15US DFEDTARU DFEDTARL IORB
BAMLC0A1CAAA BAMLC0A2CAA BAMLC0A3CA BAMLC0A4CBBB BAMLH0A1HYBB BAMLH0A2HYB BAMLH0A3HYC BAMLEMCBPIOAS BAMLHE00EHYIOAS BAMLCC0A0CMTRIV BAMLH0A0HYM2EY BAMLC0A0CMEY BAMLHYH0A0HYM2TRIV BAMLEMRECRPIEMAOAS
TOTLL BUSLOANS CONSUMER REALLN TOTCI DPSACBW027SBOG CCLACBW027SBOG DRTSCIS DRTSCLCC DRSDCILM DRTSSP DRCCLACBS DRBLACBS DRSFRMACBS
WSHOSHO WSHOMCB WLCFLL WLRRAL WCURCIR RESBALNS TOTRESNS BOGMBASE M1SL M2SL M2V CURRCIR
NFCIRISK NFCICREDIT NFCILEVERAGE NFCINONFINLEVERAGE KCFSI
VIXCLS VXVCLS OVXCLS GVZCLS VXNCLS RVXCLS VXDCLS EMVOVERALLEMV GEPUCURRENT USEPUINDXM WLEMUINDXD
U6RATE CIVPART EMRATIO JTSJOL JTSQUR JTSHIR JTSLDR CCSA LNS14000012 AWHAETP CES0500000003 CPILFESL PCEPI PCEPILFE PPIFIS PPIACO CUSR0000SAH1 MICH EXPINF1YR EXPINF10YR
RRSFS PCE PCEC96 DSPIC96 PI W875RX1 TCU IPMAN AMTMNO UMDMNO BUSINV CMRMTSPL ISRATIO HOUST HOUST1F UNDCONTSA MSACSR EXHOSLUSM495S CSUSHPINSA RHORUSQ156N BOPGSTB IMPGS EXPGS GDPC1 GDPPOT CP CPATAX
BACTSAMFRBDAL TOTALSA CFNAIMA3 CFNAIDIFF USSLIND TLAACBW027SBOG GFDEGDQ188S HDTGPDUSQ163N BCNSDODNS TCMDO TDSP FODSP MDOAH
DEXJPUS DEXUSUK DEXCHUS DEXSZUS DEXCAUS DEXMXUS DEXINUS DEXBZUS DEXKOUS DTWEXAFEGS DTWEXEMEGS
IRLTLT01DEM156N IRLTLT01JPM156N IRLTLT01GBM156N IRLTLT01ITM156N IRLTLT01FRM156N IRSTCI01EZM156N IR3TIB01EZM156N CP0000EZ19M086NEST LRHUTTTTEZM156S LRHUTTTTJPM156S ECBASSETSW JPNASSETS
DCOILWTICO DCOILBRENTEU DHHNGSP GASREGW PCOPPUSDM PALUMUSDM PNGASEUUSDM PWHEAMTUSDM PCOTTINDUSDM
NASDAQCOM DJIA NIKKEI225 SP500 BOGZ1LM153064486Q
RECPROUSM156N SAHMREALTIME USREC STLENI
RRPONTSYD RPONTSYD RRPONTTLD WTREGEN WDTGAL WLCFLPCL WLCFLSECW SWPT WALCL WSHOICB WSHOTSL WSHOFDSL WORAL WRESBAL WGCAL H41RESPPALGTRFNWW
THREEFYTP10 ACMTP10 ACMTP02 THREEFF1 T10Y2Y T10Y3M T10YIE T5YIE DFF DAAA DBAA AAA10Y BAA10Y TEDRATE
STLFSI4 STLFSI3 DRTSCILM DRTSCIS DRTSSP DEMDEBT DRCLACBS NETFI NETMANUALLIQ TOTBKCR LOANS INVEST TLAACBW027SBOG DPSACBW027SBOG
GDPNOW WEI ICSA IC4WSA CCSA CONTCLAIMS UMCSENT CSCICP03USM665S IHLIDXUS IHLIDXUSTPSOFTDEVE RETAILSMSA RSAFS RSXFS TOTALSA MRTSSM44X72USS
GACDISA066MSFRBNY GACDFSA066MSFRBPHI BACTSAMFRBDAL TXFSIRCP MANEMP USCONS USGOOD USTPU AWHMAN PERMIT HSN1F MORTGAGE5US MSPUS ASPUS
DTWEXBGS DEXUSEU DEXUSAL DEXUSNZ DEXTHUS DEXSIUS DEXHKUS DEXMAUS DEXTAUS DEXVZUS DEXSFUS
BOGZ1FL073164003Q BOGZ1FL664090005Q NCBEILQ027S CMDEBT BOGZ1FL104104016Q TNWBSHNO FBCELLQ027S
BAMLC0A0CM BAMLH0A0HYM2 BAMLEMCBPIOAS BAMLC1A0C13Y BAMLC4A0C710Y BAMLC8A0C15PY BAMLH0A1HYBB BAMLHYH0A3CMTRIV
IR14210 IR14220 IQ12260 IQ12220 IR10040 COMPUTSA
""".split()
CBOE_PC = {"totale": "totalpc", "azioni": "equitypc", "indici": "indexpc", "spx": "spxpc", "vix": "vixpc", "etf": "etfpc"}
CBOE_URL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/{}.csv"
INTRADAY = ("^GSPC ^NDX ^RUT ^DJI ^VIX ^VIX9D ^VIX3M ^VVIX ^SKEW SPY QQQ IWM DIA TLT IEF HYG LQD JNK GLD SLV USO UUP "
            "XLF XLK XLE XLV XLY XLP XLI XLU XLB XLRE XLC KRE SMH ES=F NQ=F YM=F RTY=F ZN=F ZB=F CL=F GC=F NG=F HG=F "
            "^TNX ^FVX ^TYX EURUSD=X USDJPY=X BTC-USD ETH-USD").split()
OPZIONI = ["SPY", "QQQ", "IWM", "TLT", "HYG", "GLD", "USO", "XLF", "_SPX", "_VIX"]
CBOE_OPT = "https://cdn.cboe.com/api/global/delayed_quotes/options/{}.json"
CONSTITUENTS = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"


def slug(sym: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", sym.lower()).strip("_")


def yahoo_simboli() -> dict[str, str]:
    """slug -> simbolo, senza doppioni e senza le serie che l'app archivia gia'."""
    gia = {v[0] for v in sources.YF.values()}
    out: dict[str, str] = {}
    for _, txt in YAHOO.items():
        for sym in txt.split():
            if sym in gia or sym in ("^GSPC",):
                continue
            out.setdefault(slug(sym), sym)
    return out


# ----------------------------------------------------------------------------- Yahoo (API grafico, senza libreria)
def chart(sym: str, interval: str = "1d", period1: str | None = None, rng: str | None = None, tries: int = 3) -> pd.DataFrame:
    """Barre open/high/low/close/volume. Indice = istante UTC (barre intraday) o data di borsa (barre giornaliere)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(sym)}?interval={interval}"
    if rng:
        url += f"&range={rng}"
    else:
        p1 = int(pd.Timestamp(period1 or "1990-01-01").timestamp())
        url += f"&period1={p1}&period2={int(time.time()) + 86400}"
    last = ""
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code == 404:
                raise RuntimeError("simbolo inesistente")
            r.raise_for_status()
            j = r.json()["chart"]["result"][0]
            ts = j.get("timestamp")
            if not ts:
                raise RuntimeError("nessun dato")
            q = j["indicators"]["quote"][0]
            df = pd.DataFrame({"o": q.get("open"), "h": q.get("high"), "l": q.get("low"), "c": q.get("close"), "v": q.get("volume")},
                              index=pd.to_datetime(ts, unit="s", utc=True))
            if interval == "1d":
                off = (j.get("meta") or {}).get("gmtoffset", 0) or 0
                df.index = (df.index + pd.Timedelta(seconds=off)).tz_localize(None).normalize()
                df = df[~df.index.duplicated(keep="last")]
            return df.dropna(subset=["c"])
        except Exception as e:  # noqa: BLE001
            last = str(e)[:80]
            if "inesistente" in last:
                break
            time.sleep(2 * 2 ** i)
    raise RuntimeError(last or "errore")


def _scarta_oggi(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    """La barra di oggi puo' essere parziale (futures, crypto, mercati aperti): si salva dal giorno dopo."""
    oggi = pd.Timestamp(datetime.now(timezone.utc).date())
    if len(df) and (sym.endswith("=F") or sym.endswith("-USD") or sym.endswith("=X") or df.index[-1] >= oggi):
        df = df[df.index < oggi]
    return df


def aggiorna_ohlc(stato: dict) -> None:
    """Apertura, massimo, minimo, chiusura e volume giornalieri degli strumenti chiave (anche quelli gia' archiviati dall'app):
    servono a misurare l'ampiezza dei movimenti dentro la giornata. File di testo (non compressi): git li registra come righe aggiunte."""
    base = DATA / "ohlc"
    base.mkdir(parents=True, exist_ok=True)

    def mk(sym):
        def job():
            p = base / f"{slug(sym)}.csv"
            old = pd.read_csv(p, index_col=0, parse_dates=True) if p.exists() else pd.DataFrame()
            df = chart(sym, "1d", "2000-01-01" if old.empty else (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d"))
            df = _scarta_oggi(df, sym)
            m = df.combine_first(old) if len(old) else df
            m = m[~m.index.duplicated(keep="last")].sort_index()
            m.round(5).to_csv(p, index_label="date")
            return len(m) - len(old)
        return job
    res = run_parallel({s: mk(s) for s in INTRADAY}, workers=6, deadline=240)
    ok = [k for k, (t, _) in res.items() if t == "ok"]
    stato["ohlc"] = {"richieste": len(INTRADAY), "riuscite": len(ok), "fallite": {k: str(v)[:60] for k, (t, v) in res.items() if t != "ok"}}
    print(f"[accumulo] OHLC: {len(ok)}/{len(INTRADAY)}", flush=True)


def aggiorna_yahoo(stato: dict) -> None:
    sim = yahoo_simboli()

    def mk(sl, sym):
        def job():
            nuovo = store.load("x_" + sl).empty
            df = chart(sym, "1d", None if nuovo else (datetime.now(timezone.utc) - timedelta(days=20)).strftime("%Y-%m-%d"))
            df = _scarta_oggi(df, sym)
            n = store.upsert("x_" + sl, df["c"][df["c"] > 0])
            if df["v"].fillna(0).sum() > 0 and not sym.startswith("^") and "=" not in sym:
                v = df["v"].dropna()
                v = v[v.index >= "2015-01-01"]
                if len(v):
                    store.upsert("xv_" + sl, v)
            return n
        return job
    res = run_parallel({sl: mk(sl, s) for sl, s in sim.items()}, workers=8, deadline=420)
    ok = [k for k, (t, _) in res.items() if t == "ok"]
    err = {k: str(v)[:60] for k, (t, v) in res.items() if t != "ok"}
    stato["yahoo"] = {"richieste": len(sim), "riuscite": len(ok), "nuove_righe": int(sum(v for k, (t, v) in res.items() if t == "ok")), "fallite": err}
    print(f"[accumulo] Yahoo giornaliere: {len(ok)}/{len(sim)}", flush=True)


# ----------------------------------------------------------------------------- FRED
_FRED_LOCK = threading.Lock()
_FRED_ULTIMA = [0.0]
FRED_INVALIDE = DATA / "accumulo_fred_invalide.json"   # codici che FRED dichiara inesistenti: non si richiedono piu'


def _fred_pausa(intervallo: float = 0.7) -> None:
    """FRED accetta circa 120 richieste al minuto: una ogni 0,7 secondi in tutto il programma, qualunque sia il numero di thread."""
    with _FRED_LOCK:
        att = _FRED_ULTIMA[0] + intervallo - time.time()
        if att > 0:
            time.sleep(att)
        _FRED_ULTIMA[0] = time.time()


class FredInesistente(RuntimeError):
    pass


def fetch_fred_acc(code: str, start: str | None = None, chiave: str | None = None) -> pd.Series:
    """FRED per l'accumulo: solo API ufficiale (il CSV pubblico da GitHub resta appeso), ritmo controllato,
    attesa e nuovo tentativo su «troppe richieste», messaggio vero di FRED nell'errore."""
    import os
    key = (chiave if chiave is not None else os.environ.get("FRED_API_KEY", "")).strip()
    if not key:
        return sources.fetch_fred(code, start)
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={code}&api_key={key}&file_type=json"
    if start:
        url += f"&observation_start={start}"
    ultimo = ""
    for i in range(4):
        _fred_pausa()
        try:
            r = requests.get(url, timeout=45)
        except requests.RequestException as e:
            ultimo = type(e).__name__
            time.sleep(3)
            continue
        if r.status_code == 429:
            ultimo = "429 troppe richieste"
            time.sleep(15 * (i + 1))
            continue
        if r.status_code == 200:
            return sources.parse_fred_json(r.text)
        try:
            msg = str(r.json().get("error_message", ""))[:80]
        except ValueError:
            msg = r.text[:80]
        if r.status_code == 400 and "does not exist" in msg.lower():
            raise FredInesistente(f"FRED: la serie {code} non esiste ({msg})")
        ultimo = f"{r.status_code} {msg}".replace(key, "***")
        if r.status_code in (400, 401, 403, 404):
            break
    raise RuntimeError(f"FRED {code}: {ultimo}")


def aggiorna_fred(stato: dict) -> None:
    ids = {"f_" + c.lower(): c for c in FRED_EXT}
    gia = set(sources.FRED.values())
    ids = {k: c for k, c in ids.items() if c not in gia}
    try:
        invalide = set(json.loads(FRED_INVALIDE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        invalide = set()
    saltate = sorted(c for c in ids.values() if c in invalide)
    ids = {k: c for k, c in ids.items() if c not in invalide}

    def mk(sid, code):
        def job():
            old = store.load(sid)
            start = None if old.empty else (old.index[-1] - timedelta(days=400)).strftime("%Y-%m-%d")
            try:
                return store.upsert(sid, fetch_fred_acc(code, start))
            except FredInesistente:
                invalide.add(code)
                raise
        return job
    res = run_parallel({k: mk(k, c) for k, c in ids.items()}, workers=3, deadline=900)
    if invalide:
        FRED_INVALIDE.write_text(json.dumps(sorted(invalide)), encoding="utf-8")
    ok = [k for k, (t, _) in res.items() if t == "ok"]
    err = {k: str(v)[:60] for k, (t, v) in res.items() if t != "ok"}
    stato["fred"] = {"richieste": len(ids), "riuscite": len(ok), "nuove_righe": int(sum(v for k, (t, v) in res.items() if t == "ok")), "fallite": err,
                     "codici_inesistenti_saltati": saltate}
    print(f"[accumulo] FRED: {len(ok)}/{len(ids)}", flush=True)


# ----------------------------------------------------------------------------- CBOE put/call
def parse_cboe_pc_largo(text: str) -> pd.Series:
    """Come sources.parse_cboe_pc ma tollera intestazioni diverse (S&P 500, VIX): cerca la riga con DATE e, se manca
    la colonna del rapporto, lo ricava da put e call."""
    try:
        return sources.parse_cboe_pc(text)
    except Exception:  # noqa: BLE001
        pass
    righe = text.splitlines()
    k = next((i for i, ln in enumerate(righe) if "DATE" in ln.upper() and "," in ln), None)
    if k is None:
        raise RuntimeError("CBOE: intestazione non trovata")
    df = pd.read_csv(io.StringIO("\n".join(righe[k:])))
    df.columns = [str(c).strip().upper() for c in df.columns]
    dc = next(c for c in df.columns if "DATE" in c)
    idx = pd.to_datetime(df[dc], errors="coerce")
    col = next((c for c in df.columns if "P/C" in c or "RATIO" in c), None)
    if col is not None:
        v = pd.to_numeric(df[col], errors="coerce")
    else:
        pc = next(c for c in df.columns if "PUT" in c and "RATIO" not in c)
        cc = next(c for c in df.columns if "CALL" in c and "RATIO" not in c)
        v = pd.to_numeric(df[pc], errors="coerce") / pd.to_numeric(df[cc], errors="coerce")
    s = pd.Series(v.values, index=idx).dropna()
    s = s[s > 0]
    if s.empty:
        raise RuntimeError("CBOE: nessun valore")
    return s


def aggiorna_cboe_pc(stato: dict) -> None:
    ok, err = 0, {}
    for nome, f in CBOE_PC.items():
        try:
            s = parse_cboe_pc_largo(sources._get(CBOE_URL.format(f), tries=1).text)
            store.upsert("cboe_pc_" + nome, s)
            ok += 1
        except Exception as e:  # noqa: BLE001
            err[nome] = str(e)[:60]
    stato["cboe_putcall"] = {"richieste": len(CBOE_PC), "riuscite": ok, "fallite": err}
    print(f"[accumulo] CBOE put/call: {ok}/{len(CBOE_PC)}", flush=True)


# ----------------------------------------------------------------------------- intraday a 5 minuti
def _leggi_gz(p) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, compression="gzip", index_col=0, parse_dates=True)
    return df


def _scrivi_gz(p, df: pd.DataFrame) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    df.to_csv(buf, float_format="%.6g", index_label="ts")
    with p.open("wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as g:   # mtime fisso: file uguale se i dati non cambiano
        g.write(buf.getvalue().encode("utf-8"))


_LOCK = threading.Lock()   # piu' strumenti scrivono lo stesso file di giorno: uno alla volta


def salva_giorni(base, sym: str, df: pd.DataFrame) -> int:
    """Un file per giorno (UTC) con tutti gli strumenti in colonna `sym`: il file di un giorno passato non cambia piu',
    cosi' il repository non si gonfia riscrivendo ogni giorno gli stessi dati compressi. Restituisce le righe nuove."""
    with _LOCK:
        return _salva_giorni(base, sym, df)


def _salva_giorni(base, sym: str, df: pd.DataFrame) -> int:
    nuove = 0
    df = df.copy()
    df.insert(0, "sym", sym)
    for giorno, g in df.groupby(df.index.strftime("%Y-%m-%d")):
        p = base / giorno[:7] / f"{giorno}.csv.gz"
        old = _leggi_gz(p)
        if len(old):
            old = old.reset_index()
        nuovo = g.reset_index(names="ts")
        m = pd.concat([old, nuovo], ignore_index=True) if len(old) else nuovo
        m["ts"] = pd.to_datetime(m["ts"])
        m = m.drop_duplicates(subset=["sym", "ts"], keep="last").sort_values(["sym", "ts"])
        nuove += len(m) - len(old)
        if len(m) != len(old):
            _scrivi_gz(p, m.set_index("ts"))
    return nuove


def aggiorna_intraday(stato: dict) -> None:
    base = DATA / "intraday"

    def mk(sym):
        def job():
            df = chart(sym, "5m", rng="5d")
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            return salva_giorni(base, sym, df)
        return job
    res = run_parallel({s: mk(s) for s in INTRADAY}, workers=6, deadline=240)
    ok = [k for k, (t, _) in res.items() if t == "ok"]
    err = {k: str(v)[:60] for k, (t, v) in res.items() if t != "ok"}
    stato["intraday_5m"] = {"richieste": len(INTRADAY), "riuscite": len(ok), "barre_nuove": int(sum(v for k, (t, v) in res.items() if t == "ok")), "fallite": err}
    print(f"[accumulo] intraday 5m: {len(ok)}/{len(INTRADAY)}", flush=True)


# ----------------------------------------------------------------------------- componenti dell'S&P 500
def aggiorna_componenti(stato: dict) -> None:
    base = DATA / "componenti"
    base.mkdir(parents=True, exist_ok=True)
    try:
        lista = pd.read_csv(io.StringIO(sources._get(CONSTITUENTS, tries=2).text))
    except Exception as e:  # noqa: BLE001
        stato["componenti"] = {"errore": "elenco non scaricato: " + str(e)[:60]}
        return
    lista = lista[["Symbol", "GICS Sector"]].dropna()
    lista["yf"] = lista["Symbol"].str.replace(".", "-", regex=False)
    lista[["Symbol", "GICS Sector"]].to_csv(base / "elenco.csv", index=False)
    st_file = base / "stato.json"
    ultimo = json.loads(st_file.read_text(encoding="utf-8")) if st_file.exists() else {}
    oggi = datetime.now(timezone.utc).date()

    def mk(sym):
        def job():
            l_ = ultimo.get(sym)
            p1 = "2015-01-01" if not l_ else (pd.Timestamp(l_) - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            df = chart(sym, "1d", p1)
            df = df[df.index < pd.Timestamp(oggi)]
            return df
        return job
    res = run_parallel({s: mk(s) for s in lista["yf"]}, workers=8, deadline=600)
    chiusure, volumi, err = {}, {}, {}
    for s, (t, v) in res.items():
        if t == "ok" and len(v):
            chiusure[s] = v["c"]; volumi[s] = v["v"]
            ultimo[s] = str(v.index[-1].date())
        else:
            err[s] = str(v)[:50]
    if chiusure:
        for tipo, dati in (("close", chiusure), ("vol", volumi)):
            W = pd.DataFrame(dati).sort_index()
            for ym, g in W.groupby(W.index.strftime("%Y-%m")):
                p = base / f"{tipo}_{ym}.csv.gz"
                old = _leggi_gz(p)
                m = g.combine_first(old) if len(old) else g
                m = m.sort_index()
                _scrivi_gz(p, m.round(4) if tipo == "close" else m)
    st_file.write_text(json.dumps(ultimo, sort_keys=True), encoding="utf-8")
    stato["componenti"] = {"titoli": len(lista), "riusciti": len(chiusure), "falliti": len(err), "esempi_errori": dict(list(err.items())[:10]),
                           "avviso": "elenco di oggi: i titoli usciti dall'indice in passato non ci sono (sopravvivenza)"}
    print(f"[accumulo] componenti S&P 500: {len(chiusure)}/{len(lista)}", flush=True)


# ----------------------------------------------------------------------------- opzioni (catene CBOE ritardate)
def _parse_opt(sym: str):
    m = re.match(r"^(.*?)(\d{6})([CP])(\d{8})$", sym)
    if not m:
        return None
    return m.group(1), pd.Timestamp("20" + m.group(2)), m.group(3), int(m.group(4)) / 1000.0


def riepilogo_catena(j: dict, data: str, simbolo: str) -> list[dict]:
    """Per ogni scadenza: volumi e posizioni aperte call/put, volatilita' al centro, asimmetria (put 25 delta meno call 25 delta), gamma netta."""
    d = j.get("data") or {}
    spot = d.get("current_price") or d.get("close") or d.get("prev_day_close")
    righe = []
    for o in d.get("options", []):
        p = _parse_opt(o.get("option", ""))
        if not p:
            continue
        righe.append({"exp": p[1], "tipo": p[2], "k": p[3], "iv": o.get("iv"), "delta": o.get("delta"), "gamma": o.get("gamma"),
                      "vol": o.get("volume") or 0, "oi": o.get("open_interest") or 0})
    if not righe or not spot:
        return []
    df = pd.DataFrame(righe)
    for c in ("iv", "delta", "gamma", "vol", "oi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = []
    t0 = pd.Timestamp(data)
    for exp, g in list(df.groupby("exp")) + [("TOTALE", df)]:
        c, p = g[g.tipo == "C"], g[g.tipo == "P"]
        row = {"data": data, "simbolo": simbolo, "scadenza": "TOTALE" if exp == "TOTALE" else exp.strftime("%Y-%m-%d"),
               "giorni": -1 if exp == "TOTALE" else int((exp - t0).days), "spot": round(float(spot), 4),
               "call_vol": int(c.vol.sum()), "put_vol": int(p.vol.sum()), "call_oi": int(c.oi.sum()), "put_oi": int(p.oi.sum())}
        row["pc_vol"] = round(row["put_vol"] / row["call_vol"], 4) if row["call_vol"] else None
        row["pc_oi"] = round(row["put_oi"] / row["call_oi"], 4) if row["call_oi"] else None
        if exp != "TOTALE":
            near = g.iloc[(g.k - spot).abs().argsort()[:4]]
            row["iv_atm"] = round(float(near.iv.mean()), 5) if near.iv.notna().any() else None
            pp = p[(p.delta.notna()) & p.iv.notna()]
            cc = c[(c.delta.notna()) & c.iv.notna()]
            if len(pp) and len(cc):
                ip = pp.iloc[(pp.delta + 0.25).abs().argsort()[:1]].iv.iloc[0]
                ic = cc.iloc[(cc.delta - 0.25).abs().argsort()[:1]].iv.iloc[0]
                row["iv_put25"] = round(float(ip), 5); row["iv_call25"] = round(float(ic), 5); row["skew25"] = round(float(ip - ic), 5)
        gx = (df.gamma.fillna(0) * df.oi * 100 * float(spot) ** 2 * 0.01 * np.where(df.tipo == "C", 1, -1))
        gg = gx[df.exp == exp] if exp != "TOTALE" else gx
        row["gex_milioni"] = round(float(gg.sum()) / 1e6, 3)
        out.append(row)
    return out


def catena_yahoo(sym: str, max_scadenze: int = 8) -> dict:
    """Riserva quando CBOE rifiuta: catena di opzioni da Yahoo, riportata nello stesso formato di CBOE
    (volatilita' di Yahoo; delta e gamma ricavati con Black-Scholes, tasso 4%, senza dividendi)."""
    import yfinance as yf
    from scipy.stats import norm
    ticker = {"_SPX": "^SPX", "_VIX": "^VIX"}.get(sym, sym)
    t = yf.Ticker(ticker)
    spot = float(t.fast_info["last_price"])
    oggi = pd.Timestamp(datetime.now(timezone.utc).date())
    radice = sym.strip("_")
    opzioni = []
    for exp in list(t.options)[:max_scadenze]:
        T = max((pd.Timestamp(exp) - oggi).days, 1) / 365.0
        ch = t.option_chain(exp)
        for tipo, df in (("C", ch.calls), ("P", ch.puts)):
            for _, r in df.iterrows():
                iv = float(r.get("impliedVolatility") or 0)
                k = float(r["strike"])
                if iv <= 0.01 or k <= 0:
                    continue
                d1 = (np.log(spot / k) + (0.04 + iv * iv / 2) * T) / (iv * np.sqrt(T))
                delta = norm.cdf(d1) if tipo == "C" else norm.cdf(d1) - 1
                gamma = norm.pdf(d1) / (spot * iv * np.sqrt(T))
                vol = r.get("volume")
                oi = r.get("openInterest")
                opzioni.append({"option": f"{radice}{pd.Timestamp(exp).strftime('%y%m%d')}{tipo}{int(round(k * 1000)):08d}", "iv": iv, "delta": float(delta),
                                "gamma": float(gamma), "volume": 0 if pd.isna(vol) else float(vol), "open_interest": 0 if pd.isna(oi) else float(oi)})
    return {"data": {"current_price": spot, "options": opzioni}}


def aggiorna_opzioni(stato: dict) -> None:
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = DATA / "opzioni_ext"
    base.mkdir(parents=True, exist_ok=True)

    def mk(sym):
        def job():
            try:
                r = requests.get(CBOE_OPT.format(sym), headers={**BROWSER, "Referer": "https://www.cboe.com/", "Origin": "https://www.cboe.com"}, timeout=60)
                r.raise_for_status()
                return riepilogo_catena(r.json(), oggi, sym.strip("_"))
            except Exception:  # noqa: BLE001
                return riepilogo_catena(catena_yahoo(sym), oggi, sym.strip("_"))   # CBOE rifiuta i server di GitHub: si ripiega su Yahoo
        return job
    res = run_parallel({s: mk(s) for s in OPZIONI}, workers=3, deadline=240)
    righe, err = [], {}
    for s, (t, v) in res.items():
        if t == "ok" and v:
            righe += v
        else:
            err[s] = str(v)[:60] if t != "ok" else "nessuna riga"
    if righe:
        p = base / f"{oggi[:7]}.csv"
        nuovo = pd.DataFrame(righe)
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        m = pd.concat([old, nuovo], ignore_index=True)
        m = m.drop_duplicates(subset=["data", "simbolo", "scadenza"], keep="last")
        m.to_csv(p, index=False)
    stato["opzioni"] = {"richieste": len(OPZIONI), "righe_oggi": len(righe), "fallite": err}
    print(f"[accumulo] opzioni: {len(righe)} righe, {len(err)} errori", flush=True)


# ----------------------------------------------------------------------------- orchestrazione
def aggiorna_bis_dsr(stato: dict) -> None:
    """Debito di famiglie e imprese (BIS), trimestrale: copia di sicurezza nell'accumulo, peso zero."""
    from . import bis_dsr
    r = bis_dsr.aggiorna(full=False, log=lambda m: print(m, flush=True))
    stato["bis_dsr"] = {"serie": len(r), "nuove_righe": int(sum(r.values()))}


def aggiorna(solo: list[str] | None = None) -> dict:
    stato: dict = {"data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    from . import accumulo_derivati as dv
    from . import accumulo_extra as ex
    from . import accumulo_extra2 as ex2
    passi = (("yahoo", aggiorna_yahoo), ("ohlc", aggiorna_ohlc), ("fred", aggiorna_fred), ("cboe_putcall", aggiorna_cboe_pc), ("intraday", aggiorna_intraday),
             ("opzioni", aggiorna_opzioni), ("componenti", aggiorna_componenti),
             ("bce", ex.aggiorna_bce), ("ofr", ex.aggiorna_ofr), ("mmf_alt", ex.aggiorna_mmf_alt), ("tesoro_curve", ex.aggiorna_ust), ("tesoro_cassa_aste", ex.aggiorna_fiscal), ("cot", ex.aggiorna_cot),
             ("wikipedia", ex.aggiorna_wiki), ("cripto", ex.aggiorna_cripto), ("nyfed", ex.aggiorna_nyfed), ("tsa", ex.aggiorna_tsa),
             ("finra", ex.aggiorna_finra), ("gdelt", ex.aggiorna_gdelt),
             ("vix_future", ex.aggiorna_vix_future), ("aaii", ex.aggiorna_aaii), ("previsioni", ex.aggiorna_previsioni),
             ("dealer", ex.aggiorna_dealer), ("ftd", ex.aggiorna_ftd), ("short_interest", ex.aggiorna_short_interest), ("etf_quote", ex.aggiorna_etf_quote),
             ("moduli_sec", ex2.aggiorna_moduli_sec), ("parole_sec", ex2.aggiorna_parole_sec), ("cripto_leva", ex2.aggiorna_cripto_leva), ("jgb", ex2.aggiorna_jgb),
             ("testi", ex2.aggiorna_testi), ("retail", ex2.aggiorna_retail), ("wiki_lingue", ex2.aggiorna_wiki_lingue), ("trends", ex2.aggiorna_trends),
             ("bis_dsr", aggiorna_bis_dsr), ("derivati_componenti", dv.aggiorna_derivati_componenti), ("derivati_intraday", dv.aggiorna_derivati_intraday))
    for nome, fn in passi:
        if solo and nome not in solo:
            continue
        t0 = time.time()
        try:
            fn(stato)
        except Exception as e:  # noqa: BLE001
            stato[nome] = {"errore": str(e)[:120]}
            print(f"[accumulo] {nome} ERRORE: {str(e)[:120]}", flush=True)
        print(f"[accumulo] {nome} fatto in {time.time() - t0:.0f}s", flush=True)
    STATO.write_text(json.dumps(stato, ensure_ascii=False, indent=1), encoding="utf-8")
    return stato
