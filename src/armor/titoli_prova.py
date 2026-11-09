"""Prova su un solo titolo: python -m armor titoli-prova NVDA. Stampa gli indicatori, l'RPO e gli 8-K (se c'è il segreto SEC_USER_AGENT) e le notizie classificate."""
import json

from . import news, titoli_eventi as ev, titoli_fond as tf


def main(t: str) -> None:
    d = tf.da_yf(t)
    if not d:
        print("yfinance non ha restituito dati per", t)
        return
    rpo = ev8k = None
    try:
        cik = tf.cik_map().get(t.upper())
        if cik:
            rpo = tf.rpo_da_facts(tf.sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json") or {})
            ev8k = tf.eventi_8k(tf.sec_json(f"https://data.sec.gov/submissions/CIK{cik}.json") or {})
        else:
            print("SEC: nessun CIK (segreto SEC_USER_AGENT mancante o titolo non USA)")
    except Exception as e:  # noqa: BLE001
        print("SEC non raggiunta:", str(e)[:100])
    ind = tf.indicatori(d, rpo)
    print(json.dumps(ind, indent=1, default=str, ensure_ascii=False)[:3500])
    print("8-K recenti:", ev8k)
    try:
        import requests
        xml = requests.get(news.GOOGLE.format(q=f'"{ind.get("nome") or t}"+stock'), timeout=40, headers=news.UA).text
        r = ev.riassumi(news.parse_rss(xml)[:25], ind.get("ricavi_ttm"))
        print("Eventi dalle notizie:", json.dumps(r, indent=1, ensure_ascii=False)[:2500])
    except Exception as e:  # noqa: BLE001
        print("Notizie non lette:", str(e)[:100])
