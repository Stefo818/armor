"""Pagina «Mercati»: chi è cresciuto di più e chi è calato di più (titoli, ETF, settori, cripto, materie prime, fondi, paesi) per periodo.
Dati: Yahoo Finance (prezzi rettificati) scaricati in blocchi dal lavoro `mercati.yml`; risultato in data/mercati_mondo.json.
Rendimenti in euro (default) e in valuta locale. Le liste sono curate a mano: un ticker che Yahoo non conosce viene saltato e finisce in `mancanti`."""
import html as _h
import io
import json

import numpy as np
import pandas as pd

from .config import DATA

FILE = DATA / "mercati_mondo.json"
SP500_CSV = DATA / "universo" / "sp500.csv"
PERIODI = [("1g", "1 giorno", 1), ("1s", "1 settimana", 7), ("1m", "1 mese", 30), ("3m", "3 mesi", 91), ("6m", "6 mesi", 182), ("1a", "1 anno", 365)]
SOGLIA_MAX, SOGLIA_MIN = 3.0, -0.95   # movimenti giornalieri assurdi: l'attività viene scartata (nessuna seconda fonte gratuita affidabile)

# ticker, nome, tipo, valuta
ETF = [
    ("VWCE.DE", "Vanguard FTSE All-World (acc)", "Azionario globale", "EUR"), ("EUNL.DE", "iShares Core MSCI World", "Azionario globale", "EUR"),
    ("SXR8.DE", "iShares Core S&P 500", "Azionario USA", "EUR"), ("VUAA.DE", "Vanguard S&P 500 (acc)", "Azionario USA", "EUR"),
    ("SXRV.DE", "iShares Nasdaq 100", "Azionario USA", "EUR"), ("EQQQ.DE", "Invesco Nasdaq-100", "Azionario USA", "EUR"),
    ("EXS1.DE", "iShares Core DAX", "Azionario Europa", "EUR"), ("IS3N.DE", "iShares Core MSCI EM IMI", "Azionario emergenti", "EUR"),
    ("IUSN.DE", "iShares MSCI World Small Cap", "Azionario globale", "EUR"), ("MWEQ.DE", "Invesco MSCI World Equal Weight", "Azionario globale", "EUR"),
    ("EUNH.DE", "iShares Euro Government Bond", "Obbligazionario", "EUR"), ("IBCI.DE", "iShares Euro Inflation-Linked Bond", "Obbligazionario", "EUR"),
    ("4GLD.DE", "Xetra-Gold", "Oro", "EUR"), ("SGLD.MI", "Invesco Physical Gold", "Oro", "EUR"),
    ("SPY", "SPDR S&P 500", "Azionario USA", "USD"), ("VOO", "Vanguard S&P 500", "Azionario USA", "USD"), ("IVV", "iShares Core S&P 500", "Azionario USA", "USD"),
    ("QQQ", "Invesco QQQ (Nasdaq 100)", "Azionario USA", "USD"), ("DIA", "SPDR Dow Jones", "Azionario USA", "USD"), ("IWM", "iShares Russell 2000", "Azionario USA", "USD"),
    ("VTI", "Vanguard Total US Market", "Azionario USA", "USD"), ("VT", "Vanguard Total World", "Azionario globale", "USD"), ("VEA", "Vanguard Developed Markets", "Azionario globale", "USD"),
    ("VWO", "Vanguard Emerging Markets", "Azionario emergenti", "USD"), ("EFA", "iShares MSCI EAFE", "Azionario globale", "USD"), ("EEM", "iShares MSCI Emerging Markets", "Azionario emergenti", "USD"),
    ("IEFA", "iShares Core MSCI EAFE", "Azionario globale", "USD"), ("IEMG", "iShares Core MSCI EM", "Azionario emergenti", "USD"),
    ("MDY", "SPDR S&P MidCap 400", "Azionario USA", "USD"), ("IJH", "iShares Core S&P MidCap", "Azionario USA", "USD"), ("IJR", "iShares Core S&P SmallCap", "Azionario USA", "USD"),
    ("VB", "Vanguard Small-Cap", "Azionario USA", "USD"), ("VO", "Vanguard Mid-Cap", "Azionario USA", "USD"), ("RSP", "Invesco S&P 500 Equal Weight", "Azionario USA", "USD"),
    ("IWD", "iShares Russell 1000 Value", "Azionario USA", "USD"), ("IWF", "iShares Russell 1000 Growth", "Azionario USA", "USD"), ("VUG", "Vanguard Growth", "Azionario USA", "USD"), ("VTV", "Vanguard Value", "Azionario USA", "USD"),
    ("SCHD", "Schwab US Dividend Equity", "Azionario dividendi", "USD"), ("VIG", "Vanguard Dividend Appreciation", "Azionario dividendi", "USD"), ("VYM", "Vanguard High Dividend Yield", "Azionario dividendi", "USD"),
    ("DGRO", "iShares Core Dividend Growth", "Azionario dividendi", "USD"), ("MTUM", "iShares MSCI USA Momentum", "Azionario fattori", "USD"), ("QUAL", "iShares MSCI USA Quality", "Azionario fattori", "USD"),
    ("USMV", "iShares MSCI USA Min Vol", "Azionario fattori", "USD"), ("VLUE", "iShares MSCI USA Value Factor", "Azionario fattori", "USD"),
    ("AGG", "iShares Core US Aggregate Bond", "Obbligazionario", "USD"), ("BND", "Vanguard Total Bond Market", "Obbligazionario", "USD"), ("BNDX", "Vanguard Total International Bond", "Obbligazionario", "USD"),
    ("TLT", "iShares 20+ Year Treasury", "Obbligazionario", "USD"), ("IEF", "iShares 7-10 Year Treasury", "Obbligazionario", "USD"), ("SHY", "iShares 1-3 Year Treasury", "Obbligazionario", "USD"),
    ("LQD", "iShares Investment Grade Corporate", "Obbligazionario", "USD"), ("HYG", "iShares High Yield Corporate", "Obbligazionario", "USD"), ("JNK", "SPDR High Yield Bond", "Obbligazionario", "USD"),
    ("TIP", "iShares TIPS Bond", "Obbligazionario", "USD"), ("MUB", "iShares National Muni Bond", "Obbligazionario", "USD"), ("EMB", "iShares JPMorgan EM Bond", "Obbligazionario", "USD"),
    ("GLD", "SPDR Gold Shares", "Oro", "USD"), ("IAU", "iShares Gold Trust", "Oro", "USD"), ("SLV", "iShares Silver Trust", "Materie prime", "USD"),
    ("USO", "United States Oil Fund", "Materie prime", "USD"), ("UNG", "United States Natural Gas Fund", "Materie prime", "USD"), ("DBC", "Invesco DB Commodity Index", "Materie prime", "USD"),
    ("GSG", "iShares S&P GSCI Commodity", "Materie prime", "USD"), ("UUP", "Invesco DB US Dollar Bullish", "Valute", "USD"),
    ("AOR", "iShares Core Growth Allocation", "Multi-asset", "USD"), ("AOM", "iShares Core Moderate Allocation", "Multi-asset", "USD"), ("AOA", "iShares Core Aggressive Allocation", "Multi-asset", "USD"), ("NTSX", "WisdomTree 90/60 US Balanced", "Multi-asset", "USD"),
    ("VNQ", "Vanguard Real Estate", "Immobiliare", "USD"), ("ARKK", "ARK Innovation", "Tema", "USD"), ("ARKG", "ARK Genomic Revolution", "Tema", "USD"), ("ARKW", "ARK Next Generation Internet", "Tema", "USD"),
    ("IBIT", "iShares Bitcoin Trust", "Cripto", "USD"), ("FBTC", "Fidelity Wise Origin Bitcoin", "Cripto", "USD"), ("ETHA", "iShares Ethereum Trust", "Cripto", "USD"), ("BITO", "ProShares Bitcoin Strategy", "Cripto", "USD"),
    ("KRE", "SPDR S&P Regional Banking", "Settore", "USD"), ("KBE", "SPDR S&P Bank", "Settore", "USD"), ("XHB", "SPDR S&P Homebuilders", "Settore", "USD"), ("ITB", "iShares US Home Construction", "Settore", "USD"),
    ("XRT", "SPDR S&P Retail", "Settore", "USD"), ("JETS", "US Global Jets", "Settore", "USD"), ("XME", "SPDR S&P Metals & Mining", "Settore", "USD"), ("OIH", "VanEck Oil Services", "Settore", "USD"),
    ("XOP", "SPDR S&P Oil & Gas Exploration", "Settore", "USD"), ("AMLP", "Alerian MLP", "Settore", "USD"), ("PAVE", "Global X US Infrastructure", "Settore", "USD"),
    ("GDX", "VanEck Gold Miners", "Settore", "USD"), ("GDXJ", "VanEck Junior Gold Miners", "Settore", "USD"), ("SIL", "Global X Silver Miners", "Settore", "USD"), ("COPX", "Global X Copper Miners", "Settore", "USD"),
]
FONDI_TIPI = {"Azionario globale", "Azionario emergenti", "Azionario USA", "Azionario Europa", "Azionario dividendi", "Obbligazionario", "Oro", "Multi-asset"}

SETTORI = [("XLK", "Tecnologia"), ("XLC", "Comunicazioni"), ("XLY", "Consumi ciclici"), ("XLF", "Finanza"), ("XLI", "Industria"), ("XLE", "Energia"),
           ("XLB", "Materiali"), ("XLV", "Salute"), ("XLP", "Beni di consumo base"), ("XLU", "Servizi pubblici"), ("XLRE", "Immobiliare")]
TEMI = [("BOTZ", "Robotica e automazione"), ("ROBO", "Robotica (ROBO)"), ("AIQ", "Intelligenza artificiale"), ("SMH", "Semiconduttori"), ("URA", "Uranio e nucleare"),
        ("ITA", "Difesa e aerospazio"), ("CIBR", "Cybersecurity"), ("HACK", "Cybersecurity (HACK)"), ("UFO", "Spazio"), ("XBI", "Biotecnologie"), ("ICLN", "Energia pulita"),
        ("TAN", "Solare"), ("LIT", "Litio e batterie"), ("GRID", "Rete elettrica")]
CRIPTO = [("BTC-USD", "Bitcoin"), ("ETH-USD", "Ether"), ("XRP-USD", "XRP"), ("BNB-USD", "BNB"), ("SOL-USD", "Solana"), ("DOGE-USD", "Dogecoin"), ("ADA-USD", "Cardano"),
          ("TRX-USD", "Tron"), ("AVAX-USD", "Avalanche"), ("LINK-USD", "Chainlink"), ("DOT-USD", "Polkadot"), ("SHIB-USD", "Shiba Inu"), ("BCH-USD", "Bitcoin Cash"),
          ("LTC-USD", "Litecoin"), ("XLM-USD", "Stellar"), ("XMR-USD", "Monero"), ("ATOM-USD", "Cosmos"), ("ETC-USD", "Ethereum Classic"), ("HBAR-USD", "Hedera"),
          ("NEAR-USD", "Near"), ("ICP-USD", "Internet Computer"), ("FIL-USD", "Filecoin"), ("UNI7083-USD", "Uniswap"), ("APT21794-USD", "Aptos"), ("TON11419-USD", "Toncoin"),
          ("SUI20947-USD", "Sui"), ("AAVE-USD", "Aave"), ("ARB11841-USD", "Arbitrum"), ("OP-USD", "Optimism"), ("INJ-USD", "Injective")]
MATERIE = [("GC=F", "Oro"), ("SI=F", "Argento"), ("PL=F", "Platino"), ("HG=F", "Rame"), ("CL=F", "Petrolio WTI"), ("BZ=F", "Petrolio Brent"), ("NG=F", "Gas naturale"),
           ("ZC=F", "Mais"), ("ZW=F", "Grano"), ("ZS=F", "Soia"), ("KC=F", "Caffè"), ("CC=F", "Cacao"), ("SB=F", "Zucchero"), ("CT=F", "Cotone"), ("LE=F", "Bestiame bovino"), ("HE=F", "Suini")]
# ETF paese: ticker, nome, codice paese (Natural Earth ADM0_A3), continente
PAESI = [
    ("SPY", "Stati Uniti", "USA", "Nord America"), ("EWC", "Canada", "CAN", "Nord America"), ("EWW", "Messico", "MEX", "Nord America"),
    ("EWJ", "Giappone", "JPN", "Asia"), ("MCHI", "Cina", "CHN", "Asia"), ("INDA", "India", "IND", "Asia"), ("EWY", "Corea del Sud", "KOR", "Asia"), ("EWT", "Taiwan", "TWN", "Asia"),
    ("EWH", "Hong Kong", "HKG", "Asia"), ("EWS", "Singapore", "SGP", "Asia"), ("EIDO", "Indonesia", "IDN", "Asia"), ("EWM", "Malesia", "MYS", "Asia"), ("THD", "Thailandia", "THA", "Asia"),
    ("EPHE", "Filippine", "PHL", "Asia"), ("VNM", "Vietnam", "VNM", "Asia"), ("KSA", "Arabia Saudita", "SAU", "Asia"), ("UAE", "Emirati Arabi", "ARE", "Asia"), ("QAT", "Qatar", "QAT", "Asia"), ("ISRA", "Israele", "ISR", "Asia"),
    ("EWG", "Germania", "DEU", "Europa"), ("EWQ", "Francia", "FRA", "Europa"), ("EWI", "Italia", "ITA", "Europa"), ("EWU", "Regno Unito", "GBR", "Europa"), ("EWP", "Spagna", "ESP", "Europa"),
    ("EWL", "Svizzera", "CHE", "Europa"), ("EWN", "Paesi Bassi", "NLD", "Europa"), ("EWD", "Svezia", "SWE", "Europa"), ("EDEN", "Danimarca", "DNK", "Europa"), ("ENOR", "Norvegia", "NOR", "Europa"),
    ("EFNL", "Finlandia", "FIN", "Europa"), ("EIRL", "Irlanda", "IRL", "Europa"), ("EWO", "Austria", "AUT", "Europa"), ("EWK", "Belgio", "BEL", "Europa"), ("EPOL", "Polonia", "POL", "Europa"),
    ("TUR", "Turchia", "TUR", "Europa"), ("GREK", "Grecia", "GRC", "Europa"), ("PGAL", "Portogallo", "PRT", "Europa"),
    ("EWZ", "Brasile", "BRA", "America Latina"), ("ECH", "Cile", "CHL", "America Latina"), ("EPU", "Perù", "PER", "America Latina"), ("ARGT", "Argentina", "ARG", "America Latina"), ("GXG", "Colombia", "COL", "America Latina"),
    ("EWA", "Australia", "AUS", "Oceania"), ("ENZL", "Nuova Zelanda", "NZL", "Oceania"),
    ("EZA", "Sudafrica", "ZAF", "Africa"), ("NGE", "Nigeria", "NGA", "Africa"), ("EGPT", "Egitto", "EGY", "Africa"),
]
CONTINENTI = [("Nord America", ["SPY", "EWC"]), ("Europa", ["VGK"]), ("Asia", ["AAXJ", "EWJ"]), ("America Latina", ["ILF"]), ("Africa", ["AFK"]), ("Oceania", ["EWA", "ENZL"])]


def universo() -> list[dict]:
    """Elenco delle attività (senza i titoli): ticker, nome, categoria, tipo, valuta."""
    u = []
    for t, n, k, c in ETF:
        u.append({"t": t, "n": n, "c": "etf", "s": k, "v": c})
        if k in FONDI_TIPI:
            u.append({"t": t, "n": n, "c": "fondi", "s": k, "v": c})
    for t, n in SETTORI:
        u.append({"t": t, "n": n, "c": "settori", "s": "Settore USA (GICS)", "v": "USD"})
    for t, n in TEMI:
        u.append({"t": t, "n": n, "c": "settori", "s": "Tema", "v": "USD"})
    for t, n in CRIPTO:
        u.append({"t": t, "n": n, "c": "cripto", "s": "Cripto", "v": "USD"})
    for t, n in MATERIE:
        u.append({"t": t, "n": n, "c": "materie", "s": "Futures", "v": "USD"})
    for t, n, iso, cont in PAESI:
        u.append({"t": t, "n": n, "c": "paesi", "s": cont, "v": "USD", "iso": iso})
    for cont, tk in CONTINENTI:
        for t in tk:
            if not any(x["t"] == t and x["c"] == "paesi" for x in u):
                u.append({"t": t, "n": cont + " (" + t + ")", "c": "_cont", "s": cont, "v": "USD"})
    return u


# ---------------------------------------------------------------- calcolo (puro: testabile con dati finti)
def _prezzo_a(s: pd.Series, t: pd.Timestamp):
    x = s[s.index <= t]
    return float(x.iloc[-1]) if len(x) else None


def rendimenti(s: pd.Series, fx: pd.Series | None, valuta: str) -> tuple[list, list] | None:
    """Rendimenti nei 6 periodi: in valuta locale e in euro. s = chiusure rettificate, fx = EURUSD (dollari per euro)."""
    s = s.dropna()
    s = s[s > 0]
    if len(s) < 20:
        return None
    mv = s.pct_change().dropna()
    if len(mv) and (mv.max() > SOGLIA_MAX or mv.min() < SOGLIA_MIN):
        return None
    last, t1 = float(s.iloc[-1]), s.index[-1]
    loc, eur = [], []
    for key, _n, d in PERIODI:
        if key == "1g":
            p0, t0 = float(s.iloc[-2]), s.index[-2]
        else:
            t0 = t1 - pd.Timedelta(days=d)
            if s.index[0] > t0 + pd.Timedelta(days=4):
                loc.append(None)
                eur.append(None)
                continue
            p0 = _prezzo_a(s, t0)
        r = last / p0 - 1
        loc.append(round(float(r), 5))
        if valuta == "EUR" or fx is None or fx.empty:
            eur.append(round(float(r), 5) if valuta == "EUR" else None)
        else:
            f0, f1 = _prezzo_a(fx, t0), _prezzo_a(fx, t1)
            eur.append(round(float((1 + r) * f0 / f1 - 1), 5) if f0 and f1 else None)
    return loc, eur


def costruisci(closes: pd.DataFrame, uni: list[dict], fx: pd.Series | None, nomi_titoli: dict | None = None) -> dict:
    """closes: colonne = ticker. Restituisce il dizionario da salvare in data/mercati_mondo.json."""
    items, mancanti = [], []
    ultimo = closes.dropna(how="all").index[-1] if len(closes) else None
    for u in uni:
        t = u["t"]
        if t not in closes:
            mancanti.append(t)
            continue
        s = closes[t].dropna()
        if len(s) == 0 or (ultimo is not None and (ultimo - s.index[-1]).days > 6):
            mancanti.append(t)
            continue
        r = rendimenti(s, fx, u["v"])
        if r is None:
            mancanti.append(t)
            continue
        x = {"t": t, "n": u["n"], "c": u["c"], "s": u["s"], "v": u["v"], "p": round(float(s.iloc[-1]), 4 if s.iloc[-1] < 10 else 2), "r": r[0], "e": r[1],
             "k": [round(float(v), 4 if v < 10 else 2) for v in s.iloc[-30:].values]}
        if "iso" in u:
            x["iso"] = u["iso"]
        items.append(x)
    return {"asof": str(ultimo.date()) if ultimo is not None else None, "periodi": [[k, n] for k, n, _ in PERIODI], "items": items, "mancanti": sorted(set(mancanti)),
            "continenti": [[c, tk] for c, tk in CONTINENTI]}


def dumps(o: dict) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- download (solo nel lavoro automatico)
def sp500() -> list[dict]:
    """Titoli S&P 500 con settore. Tiene una copia in data/universo/sp500.csv (usata se Wikipedia non risponde)."""
    try:
        import requests
        r = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers={"User-Agent": "Mozilla/5.0 (Armor personal research)"}, timeout=40)
        r.raise_for_status()
        t = pd.read_html(io.StringIO(r.text))[0]
        df = pd.DataFrame({"t": t["Symbol"].astype(str).str.replace(".", "-", regex=False), "n": t["Security"], "s": t["GICS Sector"]})
        SP500_CSV.parent.mkdir(exist_ok=True)
        df.to_csv(SP500_CSV, index=False)
    except Exception:  # noqa: BLE001
        if not SP500_CSV.exists():
            return []
        df = pd.read_csv(SP500_CSV)
    return [{"t": a.t, "n": a.n, "c": "titoli", "s": a.s, "v": "USD"} for a in df.itertuples()]


def _scarica(tickers: list[str], periodo: str = "15mo", blocco: int = 80, log=print) -> pd.DataFrame:
    import yfinance as yf
    parti = []
    for i in range(0, len(tickers), blocco):
        b = tickers[i:i + blocco]
        try:
            d = yf.download(b, period=periodo, interval="1d", auto_adjust=True, threads=True, progress=False, group_by="column")
            c = d["Close"] if "Close" in d else d
            if isinstance(c, pd.Series):
                c = c.to_frame(b[0])
            parti.append(c)
        except Exception as e:  # noqa: BLE001
            log(f"[mondo] blocco {i} non scaricato: {str(e)[:100]}")
    if not parti:
        return pd.DataFrame()
    c = pd.concat(parti, axis=1)
    c = c.loc[:, ~c.columns.duplicated()]
    c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
    return c


def aggiorna(log=print) -> dict:
    uni = universo()
    try:
        uni += sp500()
    except Exception as e:  # noqa: BLE001
        log("[mondo] titoli S&P 500 non disponibili: " + str(e)[:80])
    tk = sorted({u["t"] for u in uni} | {"EURUSD=X"})
    cl = _scarica(tk, log=log)
    if cl.empty or "EURUSD=X" not in cl:
        raise RuntimeError("download Yahoo non riuscito")
    fx = cl["EURUSD=X"].dropna()
    d = costruisci(cl.drop(columns=["EURUSD=X"]), uni, fx)
    d["eurusd"] = round(float(fx.iloc[-1]), 4)
    FILE.write_text(dumps(d), encoding="utf-8")
    log(f"[mondo] {len(d['items'])} attività, {len(d['mancanti'])} mancanti, dati al {d['asof']}")
    return d


# ---------------------------------------------------------------- pagina
CSS = """<style>.mdw{margin-top:8px}.mdc{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.mdc button{padding:9px 14px;border:1px solid var(--bd);border-radius:99px;background:var(--card);color:var(--tx);font-weight:600;font-size:14px;cursor:pointer}
.mdc button.on{background:var(--ac);color:#fff;border-color:var(--ac)}.mdbig button{flex:1;font-size:16px;padding:13px 10px;border-radius:12px}.mdbig button.up.on{background:var(--ok);border-color:var(--ok)}.mdbig button.dn.on{background:var(--bad);border-color:var(--bad)}
.mdcard{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:14px;margin:12px 0}.mdcard h3{margin:0 0 8px}.mdb{display:grid;grid-template-columns:minmax(90px,34%) 1fr auto;gap:6px 8px;align-items:center;font-size:13px;margin:3px 0}
.mdb .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mdb .bar{height:14px;background:var(--bd);border-radius:4px;position:relative}.mdb .bar i{position:absolute;top:0;bottom:0;border-radius:4px}.mdb b{font-variant-numeric:tabular-nums}
.mdt td.pos,.mdb b.pos{color:var(--ok)}.mdt td.neg,.mdb b.neg{color:var(--bad)}.mdt .tk{color:var(--mu);font-size:12px}.mdt svg{width:70px;height:20px;vertical-align:middle}
.mdg{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}.mdleg{font-size:12px;line-height:1.7}.mdleg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.mdmap{width:100%;touch-action:none;background:var(--card);border:1px solid var(--bd);border-radius:12px;overflow:hidden}.mdmap svg{width:100%;height:auto;display:block}.mdmap path{stroke:var(--bg);stroke-width:.4}
.mdtip{min-height:40px;font-size:13px;margin:6px 0}.mdcont{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px;margin:6px 0}.mdcont div{border-radius:8px;padding:6px 8px;font-size:12px;background:var(--bd)}.mdcont b{display:block;font-size:15px}</style>"""

JS = r"""<script>(function(){var W=document.querySelector('[data-md]');if(!W||W.dataset.on)return;W.dataset.on=1;
var D=null,PER=0,DIR=1,EUR=1,CAT=[['titoli','Titoli'],['etf','ETF'],['settori','Settori e temi'],['cripto','Cripto'],['materie','Materie prime'],['fondi','Fondi (ETF per tipo)'],['paesi','Aree e paesi']];
var PAL=['#3b82f6','#f59e0b','#10b981','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16','#f97316','#14b8a6','#a855f7','#64748b'];
function pc(x,d){if(x==null)return '—';var s=(x*100).toFixed(d==null?1:d).replace('.',',');return (x>0?'+':'')+s+'%'}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function R(x){var v=(EUR?x.e:x.r)[PER];return v==null?(EUR?x.r[PER]:null):v}
function rank(c){var a=D.items.filter(function(x){return x.c===c&&R(x)!=null});a.sort(function(p,q){return DIR*(R(q)-R(p))});return a}
function spark(k,up){if(!k||k.length<2)return '';var mn=Math.min.apply(null,k),mx=Math.max.apply(null,k),r=mx-mn||1,p=k.map(function(v,i){return (i*69/(k.length-1)+0.5).toFixed(1)+','+(18-(v-mn)/r*16+1).toFixed(1)}).join(' ');return '<svg viewBox="0 0 70 20"><polyline fill="none" stroke="'+(up?'#1f8f55':'#c0392b')+'" stroke-width="1.5" points="'+p+'"/></svg>'}
function bars(a){var m=0;a.forEach(function(x){m=Math.max(m,Math.abs(R(x)))});m=m||1;return a.map(function(x){var v=R(x),w=Math.abs(v)/m*50;return '<div class="mdb"><span class="nm" title="'+esc(x.n)+'">'+esc(x.n)+'</span><span class="bar"><i style="'+(v>=0?'left:50%':'right:50%')+';width:'+w+'%;background:'+(v>=0?'var(--ok)':'var(--bad)')+'"></i></span><b class="'+(v>=0?'pos':'neg')+'">'+pc(v)+'</b></div>'}).join('')}
function table(a,fondi){return '<div class="scroll"><table class="tbl mdt"><tr><th>Nome</th>'+(fondi?'<th>Tipo</th>':'')+'<th>%</th><th>Prezzo</th><th>30 giorni</th></tr>'+a.map(function(x){var v=R(x);return '<tr><td>'+esc(x.n)+' <span class="tk">'+esc(x.t)+'</span></td>'+(fondi?'<td>'+esc(x.s)+'</td>':'')+'<td class="'+(v>=0?'pos':'neg')+'">'+pc(v)+'</td><td>'+x.p+' '+(x.v==='EUR'?'€':'$')+'</td><td>'+spark(x.k,v>=0)+'</td></tr>'}).join('')+'</table></div>'}
function donut(parts,tit){var tot=parts.reduce(function(s,p){return s+p[1]},0);if(!tot)return '<div class="mdcard"><h3>'+tit+'</h3><p class="mu">Dati non disponibili.</p></div>';var a=0,c=['<svg viewBox="-60 -60 120 120" style="width:150px;height:150px">'],leg=[];parts.forEach(function(p,i){var f=p[1]/tot,a1=a+f*2*Math.PI,x0=50*Math.sin(a),y0=-50*Math.cos(a),x1=50*Math.sin(a1),y1=-50*Math.cos(a1),xi=30*Math.sin(a1),yi=-30*Math.cos(a1),xj=30*Math.sin(a),yj=-30*Math.cos(a),l=f>.5?1:0,col=PAL[i%PAL.length];
if(f>=.999)c.push('<circle r="40" fill="none" stroke="'+col+'" stroke-width="20"/>');else c.push('<path d="M'+x0+' '+y0+' A50 50 0 '+l+' 1 '+x1+' '+y1+' L'+xi+' '+yi+' A30 30 0 '+l+' 0 '+xj+' '+yj+'Z" fill="'+col+'"/>');a=a1;leg.push('<div><i style="background:'+col+'"></i>'+esc(p[0])+' '+Math.round(f*100)+'%</div>')});
return '<div class="mdcard"><h3>'+tit+'</h3><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">'+c.join('')+'</svg><div class="mdleg">'+leg.join('')+'</div></div></div>'}
function groupBy(a,f){var m={};a.forEach(function(x){var k=f(x);m[k]=(m[k]||0)+1});return Object.keys(m).map(function(k){return [k,m[k]]}).sort(function(p,q){return q[1]-p[1]})}
function updown(){return '<div class="mdcard"><h3>Quante attività sono salite o scese</h3>'+CAT.map(function(c){var a=D.items.filter(function(x){return x.c===c[0]&&R(x)!=null}),u=a.filter(function(x){return R(x)>0}).length,n=a.length;if(!n)return '';var p=Math.round(u/n*100);return '<div class="mdb" style="grid-template-columns:minmax(90px,34%) 1fr auto"><span class="nm">'+c[1]+'</span><span class="bar" style="overflow:hidden"><i style="left:0;width:'+p+'%;background:var(--ok)"></i><i style="left:'+p+'%;right:0;background:var(--bad)"></i></span><b>'+u+' ▲ · '+(n-u)+' ▼</b></div>'}).join('')+'</div>'}
function colore(v,m){if(v==null||!isFinite(v))return 'transparent';var t=Math.max(-1,Math.min(1,v/m));function mix(a,b,f){return Math.round(a+(b-a)*f)}var g=[148,163,184],r=[220,38,38],gr=[22,163,74],c=t<0?r:gr,f=Math.abs(t);return 'rgb('+mix(g[0],c[0],f)+','+mix(g[1],c[1],f)+','+mix(g[2],c[2],f)+')'}
var GEO=null,MAPS=null;
function mappa(){var box=W.querySelector('#mdmap');if(!box)return;var pa=D.items.filter(function(x){return x.c==='paesi'&&x.iso&&R(x)!=null});var vals=pa.map(function(x){return Math.abs(R(x))}).sort(function(a,b){return a-b}),m=vals.length?vals[Math.min(vals.length-1,Math.floor(vals.length*.95))]:.05;m=m||.05;
var by={};pa.forEach(function(x){by[x.iso]=x});var rk=pa.slice().sort(function(a,b){return R(b)-R(a)});
function draw(){var proj=d3.geoNaturalEarth1().fitSize([960,500],GEO),path=d3.geoPath(proj);box.innerHTML='<svg viewBox="0 0 960 500"><g id="mdg">'+GEO.features.map(function(f){var x=by[f.id],fill=x?colore(R(x),m):'var(--bd)';return '<path data-i="'+f.id+'" d="'+path(f)+'" fill="'+fill+'"'+(x?'':' fill-opacity=".5"')+'/>'}).join('')+'</g></svg>';
var svg=box.querySelector('svg'),g=svg.querySelector('#mdg'),z=1,tx=0,ty=0;function ap(){g.setAttribute('transform','translate('+tx+','+ty+') scale('+z+')')}
box.onwheel=function(e){e.preventDefault();var k=e.deltaY<0?1.2:1/1.2;z=Math.max(1,Math.min(8,z*k));if(z==1){tx=ty=0}ap()};
var ptr={},d0=0,z0=1;box.onpointerdown=function(e){ptr[e.pointerId]=[e.clientX,e.clientY];var k=Object.keys(ptr);if(k.length==2){d0=Math.hypot(ptr[k[0]][0]-ptr[k[1]][0],ptr[k[0]][1]-ptr[k[1]][1]);z0=z}};
box.onpointermove=function(e){if(!ptr[e.pointerId])return;var k=Object.keys(ptr),o=ptr[e.pointerId];ptr[e.pointerId]=[e.clientX,e.clientY];if(k.length==2&&d0){var d=Math.hypot(ptr[k[0]][0]-ptr[k[1]][0],ptr[k[0]][1]-ptr[k[1]][1]);z=Math.max(1,Math.min(8,z0*d/d0));ap()}else if(k.length==1&&z>1){tx+=(e.clientX-o[0])*960/box.clientWidth;ty+=(e.clientY-o[1])*960/box.clientWidth;ap()}};
box.onpointerup=box.onpointercancel=function(e){delete ptr[e.pointerId];d0=0};
box.onclick=function(e){var p=e.target.closest&&e.target.closest('path[data-i]');var t=W.querySelector('#mdtip');if(!p){return}var x=by[p.dataset.i];if(!x){t.innerHTML='<b>'+esc(GEO.features.filter(function(f){return f.id===p.dataset.i})[0].properties.n)+'</b>: nessun ETF disponibile per questo paese.';return}t.innerHTML='<b>'+esc(x.n)+'</b> ('+esc(x.t)+'): <b class="'+(R(x)>=0?'pos':'neg')+'">'+pc(R(x))+'</b> · posizione '+(rk.indexOf(x)+1)+' di '+rk.length}}
if(GEO)draw();else if(MAPS)MAPS.then(draw)}
function continenti(){var out=D.continenti.map(function(c){var v=[];c[1].forEach(function(t){var x=D.items.filter(function(y){return y.t===t&&(y.c==='paesi'||y.c==='_cont')})[0];if(x&&R(x)!=null)v.push(R(x))});return [c[0],v.length?v.reduce(function(a,b){return a+b},0)/v.length:null]});return '<div class="mdcont">'+out.map(function(c){return '<div style="background:'+colore(c[1],.1)+';color:#111"><span>'+esc(c[0])+'</span><b>'+pc(c[1])+'</b></div>'}).join('')+'</div>'}
function render(){var nm=D.periodi[PER][1],h='';
h+='<div class="mdc mdbig"><button class="up'+(DIR>0?' on':'')+'" data-d="1">▲ Cresciuti di più</button><button class="dn'+(DIR<0?' on':'')+'" data-d="-1">▼ Calati di più</button></div>';
h+='<div class="mdc">'+D.periodi.map(function(p,i){return '<button data-p="'+i+'" class="'+(i==PER?'on':'')+'">'+p[1]+'</button>'}).join('')+'</div>';
h+='<div class="mdc"><button data-e="1" class="'+(EUR?'on':'')+'">in euro</button><button data-e="0" class="'+(EUR?'':'on')+'">in valuta locale</button></div>';
h+='<p class="mu">Dati al '+D.asof.split('-').reverse().join('/')+'. «In euro» converte con il cambio EUR/USD i titoli quotati in dollari. Rendimenti su prezzi rettificati. Non è un consiglio di acquisto.</p>';
var tit=rank('titoli').slice(0,100);
h+='<div class="mdg">'+donut(groupBy(tit,function(x){return x.s}).slice(0,10),'Settori tra i 100 titoli '+(DIR>0?'cresciuti':'calati')+' di più')+donut(groupBy(rank('paesi').slice(0,10),function(x){return x.s}),'Aree geografiche tra i 10 paesi '+(DIR>0?'cresciuti':'calati')+' di più')+'</div>'+updown();
h+='<div class="mdcard"><h3>Planisfero: rendimento per paese ('+nm+')</h3>'+continenti()+'<div class="mdmap" id="mdmap"><p class="mu" style="padding:14px">Caricamento della mappa…</p></div><div class="mdtip" id="mdtip">Tocca un paese per vedere il dettaglio. Verde = salito, rosso = sceso; colore pieno al 95° percentile del periodo. Paesi chiari: nessun ETF. Due dita per ingrandire.</div></div>';
CAT.forEach(function(c){var a=rank(c[0]);var note='';if(c[0]==='titoli')note='<p class="mu">Per ora: i 500 titoli dell\'S&amp;P 500. L\'universo completo (anche piccole società) arriva con il motore titoli.</p>';if(c[0]==='fondi')note='<p class="mu">I fondi comuni non hanno dati gratuiti affidabili: qui si usano gli ETF raggruppati per tipo.</p>';if(c[0]==='materie')note='<p class="mu">Contratti futures: nei giorni di cambio scadenza il prezzo può avere un salto.</p>';
h+='<div class="mdcard"><h3>'+c[1]+' · '+(DIR>0?'più cresciuti':'più calati')+' ('+nm+')</h3>'+(a.length?bars(a.slice(0,10))+'<details style="margin-top:8px"><summary>Mostra la tabella (fino a 50 di '+a.length+')</summary>'+table(a.slice(0,50),c[0]==='fondi')+'</details>':'<p class="mu">Nessun dato disponibile per questa categoria.</p>')+note+'</div>'});
W.innerHTML=h;
W.querySelectorAll('[data-p]').forEach(function(b){b.onclick=function(){PER=+b.dataset.p;render()}});W.querySelectorAll('[data-d]').forEach(function(b){b.onclick=function(){DIR=+b.dataset.d;render()}});W.querySelectorAll('[data-e]').forEach(function(b){b.onclick=function(){EUR=+b.dataset.e;render()}});mappa()}
function loadMap(){if(MAPS)return;MAPS=new Promise(function(ok){var s=document.createElement('script');s.src='d3geo.min.js';s.onload=function(){fetch('mondo.json').then(function(r){return r.json()}).then(function(j){GEO=j;ok()}).catch(function(){ok()})};s.onerror=function(){ok()};document.head.appendChild(s)})}
function go(j){D=j;if(!D||!D.items||!D.items.length){W.innerHTML='<p class="mu">Dati dei mercati non ancora disponibili: si generano con il lavoro automatico serale.</p>';return}render();loadMap();MAPS.then(function(){if(GEO)mappa()})}
var emb=document.getElementById('armor-md-data');if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/mercati.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(go).catch(function(){W.innerHTML='<p class="mu">Dati dei mercati non disponibili (serve la connessione, oppure il lavoro serale non è ancora girato).</p>'})}
})();</script>"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-md-data'>{data_json}</script>" if data_json else ""
    return (f"{CSS}<h2>Mercati: chi è cresciuto e chi è calato</h2><div class='explain'><p>Classifiche per periodo di titoli, ETF, settori e temi, cripto, materie prime, fondi (come ETF) e paesi, "
            "con planisfero. Scegli periodo, direzione e valuta. I dati si aggiornano ogni sera dopo la chiusura USA.</p></div>"
            f"{emb}<div class='mdw' data-md='1'></div>{JS}")


def carica() -> str | None:
    return FILE.read_text(encoding="utf-8") if FILE.exists() else None
