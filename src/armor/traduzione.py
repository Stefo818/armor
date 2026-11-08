"""Traduzione in italiano dei titoli delle notizie (gratuita, senza chiavi né IA a pagamento): servizi web pubblici provati in ordine,
con una cache in data/news/traduzioni.json (un titolo si traduce una sola volta). Se nessun servizio risponde il titolo resta in inglese e non succede altro:
il ciclo delle notizie non si ferma mai per colpa della traduzione."""
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .config import DATA

CACHE = DATA / "news" / "traduzioni.json"
MAX_CACHE = 4000
UA = {"User-Agent": "Mozilla/5.0 (Armor personal dashboard)"}


def _k(t: str) -> str:
    return hashlib.sha1(t.strip().lower().encode("utf-8")).hexdigest()[:16]


def _google(t: str) -> str:
    r = requests.get("https://translate.googleapis.com/translate_a/single", headers=UA, timeout=12,
                     params={"client": "gtx", "sl": "en", "tl": "it", "dt": "t", "q": t})
    r.raise_for_status()
    return "".join(seg[0] for seg in r.json()[0] if seg and seg[0])


def _mymemory(t: str) -> str:
    r = requests.get("https://api.mymemory.translated.net/get", headers=UA, timeout=12, params={"q": t[:450], "langpair": "en|it"})
    r.raise_for_status()
    out = (r.json().get("responseData") or {}).get("translatedText", "")
    if not out or "MYMEMORY WARNING" in out.upper() or "QUERY LENGTH LIMIT" in out.upper():
        raise RuntimeError("limite del servizio")
    return out


SERVIZI = (_google, _mymemory)


def traduci_uno(t: str, servizi=SERVIZI) -> str | None:
    for fn in servizi:
        for tentativo in range(2):
            try:
                out = fn(t).strip()
                if out:
                    return out
            except Exception:  # noqa: BLE001
                time.sleep(1 + tentativo)
    return None


def traduci(titoli: list[str], cache_path=None, servizi=SERVIZI, tempo_max: float = 150.0, workers: int = 6) -> dict[str, str]:
    """{titolo inglese: titolo italiano} per i titoli tradotti (quelli già in cache più i nuovi). I titoli non tradotti mancano dal risultato."""
    path = cache_path or CACHE
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cache = {}
    mancano = [t for t in dict.fromkeys(titoli) if t and _k(t) not in cache]
    t0 = time.time()
    nuovi = 0
    if mancano:
        def _job(t):
            if time.time() - t0 > tempo_max:
                return t, None
            return t, traduci_uno(t, servizi)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for t, it in ex.map(_job, mancano):
                if it:
                    cache[_k(t)] = it
                    nuovi += 1
        if nuovi:
            if len(cache) > MAX_CACHE:
                cache = dict(list(cache.items())[-MAX_CACHE:])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"[traduzione] {len(titoli) - len(mancano)} da cache, {nuovi} nuovi, {len(mancano) - nuovi} non tradotti", flush=True)
    return {t: cache[_k(t)] for t in titoli if _k(t) in cache}


def applica(news: dict, cache_path=None, servizi=SERVIZI, tempo_max: float = 150.0) -> int:
    """Mette in italiano il campo `title` di ogni notizia (l'originale resta in `title_en`). Restituisce quanti titoli sono in italiano."""
    items = news.get("items", [])
    tr = traduci([i.get("title_en") or i["title"] for i in items], cache_path, servizi, tempo_max)
    n = 0
    for i in items:
        en = i.get("title_en") or i["title"]
        if en in tr:
            i["title_en"], i["title"] = en, tr[en]
            n += 1
    news["traduzione"] = {"titoli_in_italiano": n, "totale": len(items)}
    return n
