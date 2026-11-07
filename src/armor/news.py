"""Notizie di finanza, geopolitica e delle 20 maggiori societa': raccolta da feed pubblici (gratuiti), classificazione per
tema e giudizio automatico con un vocabolario finanziario (nessuna IA a pagamento: e' una lettura dei titoli, non degli articoli)."""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests

from . import finbert
from .config import DATA

NEWS_DIR = DATA / "news"
UA = {"User-Agent": "Mozilla/5.0 (Armor personal dashboard)"}
TOP20 = [("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "Nvidia"), ("AMZN", "Amazon"), ("GOOGL", "Alphabet (Google)"),
         ("META", "Meta"), ("AVGO", "Broadcom"), ("TSLA", "Tesla"), ("BRK-B", "Berkshire Hathaway"), ("JPM", "JPMorgan"),
         ("LLY", "Eli Lilly"), ("V", "Visa"), ("ORCL", "Oracle"), ("XOM", "Exxon Mobil"), ("MA", "Mastercard"),
         ("NFLX", "Netflix"), ("COST", "Costco"), ("WMT", "Walmart"), ("TSM", "TSMC"), ("ASML", "ASML"), ("MU", "Micron")]
# peso approssimativo nel fondo VWCE (%), per pesare il tono delle notizie sulle societa' piu' grandi
VWCE_W = {"NVDA": 5.0, "AAPL": 4.5, "MSFT": 3.6, "AMZN": 2.3, "GOOGL": 3.4, "TSM": 1.8, "AVGO": 1.5, "META": 1.5, "MU": 1.1}
SECTOR_QUERIES = [  # settori dominanti nel fondo (tecnologia 38%, finanza 18%, industria 9%, salute 8%, consumi 8%, energia 4%)
    ("Tecnologia e chip", "technology stocks OR semiconductors OR AI chips"), ("Finanza e banche", "bank stocks OR financials earnings OR bank profits"),
    ("Industria", "industrial stocks OR manufacturing PMI OR factory output"), ("Salute e farmaceutico", "healthcare stocks OR pharma OR biotech"),
    ("Consumi", "consumer spending OR retail sales OR consumer confidence"), ("Energia", "energy stocks OR oil majors OR natural gas prices"),
    ("Mercati emergenti", "emerging markets stocks OR Asia stocks OR India China markets")]
MACRO_QUERIES = [  # (tema del feed, query Google News)
    ("Mercati", "stock market OR Wall Street OR S&P 500"), ("Banche centrali", "Federal Reserve OR ECB interest rates"),
    ("Inflazione e lavoro", "inflation OR jobs report OR unemployment"), ("Geopolitica", "war OR sanctions OR geopolitics OR ceasefire"),
    ("Dazi e commercio", "tariffs OR trade war OR export controls"), ("Energia e materie prime", "oil prices OR OPEC OR gold price"),
    ("Cina e Asia", "China economy OR Taiwan OR Japan yen"), ("Europa", "eurozone economy OR Europe markets")]
GOOGLE = "https://news.google.com/rss/search?q={q}+when:2d&hl=en-US&gl=US&ceid=US:en"
YAHOO = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={s}&region=US&lang=en-US"
GOOD_SOURCES = ["reuters", "bloomberg", "wall street journal", "wsj", "financial times", "ft.com", "cnbc", "associated press", "ap news",
                "barron", "marketwatch", "economist", "bbc", "il sole 24 ore", "yahoo finance", "investopedia"]

THEMES = {
    "Banche centrali e tassi": ["fed ", "federal reserve", "powell", "ecb", "lagarde", "rate cut", "rate hike", "interest rate", "bank of japan", "boe ", "fomc"],
    "Inflazione": ["inflation", "cpi", "consumer prices", "ppi", "price pressures"],
    "Lavoro e crescita": ["jobs report", "payrolls", "unemployment", "jobless", "gdp", "recession", "slowdown", "growth forecast", "pmi"],
    "Guerre e geopolitica": ["war", "missile", "attack", "ceasefire", "sanction", "invasion", "nato", "ukraine", "russia", "israel", "gaza", "iran", "taiwan", "north korea", "troops"],
    "Dazi e commercio": ["tariff", "trade war", "export control", "trade deal", "embargo", "customs"],
    "Energia e materie prime": ["oil", "opec", "crude", "natural gas", "gold ", "copper", "brent"],
    "Utili e conti aziendali": ["earnings", "revenue", "profit", "guidance", "quarter", "forecast", "outlook", "buyback", "dividend"],
    "Intelligenza artificiale e chip": ["artificial intelligence", " ai ", "chip", "semiconductor", "data center", "nvidia", "openai"],
    "Credito e banche": ["default", "bankruptcy", "credit", "bank run", "debt", "bond yields", "treasury"],
    "Regole e cause legali": ["lawsuit", "antitrust", "probe", "investigation", "regulator", "fine ", "sec ", "settlement"],
}
POS = {"surge": 2, "soar": 2, "rally": 2, "jump": 1.5, "gain": 1, "rise": 1, "climb": 1, "record high": 2, "record": 1, "beat": 1.5,
       "beats": 1.5, "upgrade": 1.5, "strong": 1, "growth": 1, "optimism": 1.5, "recover": 1.5, "rebound": 1.5, "boost": 1,
       "approval": 1, "deal": 0.5, "ceasefire": 1.5, "peace": 1.5, "cut rates": 1, "rate cut": 1, "easing": 1, "profit": 0.5, "outperform": 1.5,
       "raises forecast": 2, "buyback": 1, "wins": 1, "expands": 0.5, "resilient": 1, "cooling inflation": 1.5, "soft landing": 1.5}
NEG = {"plunge": 2, "crash": 2.5, "slump": 2, "tumble": 2, "sink": 1.5, "fall": 1, "drop": 1, "slide": 1, "selloff": 2, "sell-off": 2,
       "miss": 1.5, "misses": 1.5, "downgrade": 1.5, "weak": 1, "recession": 2, "fear": 1.5, "worry": 1, "warns": 1.5, "warning": 1.5,
       "cut forecast": 2, "layoffs": 1.5, "lawsuit": 1, "probe": 1, "investigation": 1, "fine": 0.5, "default": 2, "bankruptcy": 2.5,
       "war": 1.5, "attack": 1.5, "missile": 1.5, "sanctions": 1, "tariff": 1, "tariffs": 1, "crisis": 2, "turmoil": 2, "volatile": 1,
       "inflation surge": 2, "hike": 1, "shutdown": 1.5, "default risk": 2, "bubble": 1.5, "plummet": 2, "losses": 1, "outflows": 1, "escalat": 2,
       "hot inflation": 1.5, "stagflation": 2, "bank run": 2.5}
NEGATORS = ("not ", "no ", "avoid", "avoids", "averts", "ease", "eases", "easing", "ends", "end of")


def strip_html(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def parse_rss(xml: str) -> list[dict]:
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        title = strip_html(it.findtext("title") or "")
        src = strip_html(it.findtext("source") or "")
        if not src and " - " in title:
            title, src = title.rsplit(" - ", 1)
        try:
            when = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc)
        except Exception:  # noqa: BLE001
            when = None
        out.append({"title": title, "source": src, "link": (it.findtext("link") or "").strip(),
                    "summary": strip_html(it.findtext("description") or "")[:300],
                    "time": when.strftime("%Y-%m-%dT%H:%M:%SZ") if when else ""})
    return out


def themes_of(text: str) -> list[str]:
    low = " " + text.lower() + " "
    return [t for t, ks in THEMES.items() if any(k in low for k in ks)]


def sentiment(text: str) -> float:
    """Da -1 (molto negativo) a +1 (molto positivo): conta parole del vocabolario finanziario, con inversione se c'e' una negazione."""
    low = " " + text.lower() + " "
    pos = sum(w for k, w in POS.items() if k in low)
    neg = sum(w for k, w in NEG.items() if k in low)
    if any(n in low for n in NEGATORS) and neg > pos:
        pos, neg = neg * 0.5, pos
    return round((pos - neg) / (pos + neg + 1.5), 2)


def label_of(s: float) -> str:
    return "positivo" if s >= 0.2 else ("negativo" if s <= -0.2 else "neutro")


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower())[:80]


def importance(item: dict, now: datetime) -> float:
    w = 1.0 + (0.6 if any(g in item["source"].lower() for g in GOOD_SOURCES) else 0.0)
    w += 0.4 * len(item["themes"]) + abs(item["sent"]) * 0.8
    try:
        age_h = (now - datetime.fromisoformat(item["time"].replace("Z", "+00:00"))).total_seconds() / 3600
        w *= max(0.25, 1.0 - age_h / 96)
    except Exception:  # noqa: BLE001
        w *= 0.5
    return round(w, 3)


def _get_text(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=25)
    r.raise_for_status()
    return r.text


def enrich(items: list[dict], now: datetime, kind: str, group: str) -> list[dict]:
    out = []
    for it in items:
        text = it["title"] + ". " + it["summary"]
        it.update(themes=themes_of(text), sent=sentiment(it["title"] + " " + it["summary"][:160]), kind=kind, group=group)
        it["label"] = label_of(it["sent"])
        it["score"] = importance(it, now)
        out.append(it)
    return out


def collect(get=None, now: datetime | None = None, scorer=None) -> dict:
    now = now or datetime.now(timezone.utc)
    get = get or _get_text
    items, errors, seen = [], [], set()
    jobs = [("macro", g, GOOGLE.format(q=quote(q))) for g, q in MACRO_QUERIES]
    jobs += [("sector", g, GOOGLE.format(q=quote(q))) for g, q in SECTOR_QUERIES]
    jobs += [("company", f"{n} ({t})", YAHOO.format(s=t)) for t, n in TOP20]
    for kind, group, url in jobs:
        try:
            raw = parse_rss(get(url))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{group}: {str(e)[:60]}")
            continue
        cutoff = now - timedelta(days=7)
        fresh = []
        for it in raw:
            k = norm(it["title"])
            if not k or k in seen:
                continue
            if it["time"] and datetime.fromisoformat(it["time"].replace("Z", "+00:00")) < cutoff:
                continue
            seen.add(k)
            fresh.append(it)
        items += enrich(fresh[:25], now, kind, group)
    model = "vocabolario"
    try:
        sc = (scorer or finbert.score)([i["title"] for i in items])
        if sc and len(sc) == len(items):
            for it, v in zip(items, sc):
                it["sent_lex"] = it["sent"]
                it["sent"] = round(0.75 * v + 0.25 * it["sent"], 2)
                it["label"] = label_of(it["sent"])
                it["score"] = importance(it, now)
            model = "FinBERT"
    except Exception as e:  # noqa: BLE001
        errors.append(f"finbert: {str(e)[:60]}")
    items.sort(key=lambda x: -x["score"])
    return {"fetched": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items, "errors": errors, "model": model}


def summary(news: dict) -> dict:
    its = news.get("items", [])
    if not its:
        return {}
    macro = [i for i in its if i["kind"] == "macro"]
    n = lambda xs, lab: sum(1 for i in xs if i["label"] == lab)
    return {"news_n": len(its), "news_neg_macro": n(macro, "negativo"), "news_pos_macro": n(macro, "positivo"),
            "news_sent_macro": round(sum(i["sent"] for i in macro) / max(len(macro), 1), 3)}


def run() -> dict:
    news = collect()
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (NEWS_DIR / f"{day}.json").write_text(json.dumps(news, ensure_ascii=False), encoding="utf-8")
    (NEWS_DIR / "latest.json").write_text(json.dumps(news, ensure_ascii=False), encoding="utf-8")
    # conserva solo gli ultimi 45 giorni
    files = sorted(p for p in NEWS_DIR.glob("20*.json"))
    for p in files[:-45]:
        p.unlink()
    print(f"Notizie: {len(news['items'])} titoli, {len(news['errors'])} fonti con errore, analisi: {news.get('model')}")
    for e in news["errors"][:5]:
        print("ERR", e)
    return news


def load_latest() -> dict:
    try:
        return json.loads((NEWS_DIR / "latest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def history_sentiment(days: int = 14) -> dict[str, float]:
    """Sentiment medio dei titoli macro per giorno (per confrontare oggi con la settimana scorsa)."""
    out = {}
    for p in sorted(NEWS_DIR.glob("20*.json"))[-days:]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            m = [i["sent"] for i in d.get("items", []) if i.get("kind") == "macro"]
            if m:
                out[p.stem] = sum(m) / len(m)
        except Exception:  # noqa: BLE001
            continue
    return out
