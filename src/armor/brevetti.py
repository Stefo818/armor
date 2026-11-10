"""Brevetti per azienda quotata (Patch 68).

Problema: i brevetti sono intestati a NOMI di società («Microsoft Technology Licensing, LLC»), le azioni hanno SIMBOLI (MSFT).
Soluzione senza fonti a pagamento, in quattro livelli, sempre dichiarata nel file di uscita:
  1. alias scritti a mano per i grandi gruppi (Google → GOOGL, Facebook → META…), estendibili da data/universo/alias_brevetti.json;
  2. nome identico a quello dell'elenco ufficiale SEC (società quotate USA, anche ADR): «Apple Inc.» ↔ «Apple Inc.» ;
  3. nome che INIZIA col nome della società quotata, se questo è abbastanza distintivo (≥ 7 lettere o ≥ 2 parole, mai parole generiche): «Microsoft Technology Licensing» ↔ «Microsoft»;
  4. altrimenti niente abbinamento: meglio non avere il dato che attribuirlo alla società sbagliata.
Ogni settimana si scrive anche l'elenco dei titolari con più brevetti NON abbinati (data/brevetti_non_abbinati.csv): serve a completare gli alias.
Fonte dei brevetti: file gratuiti di PatentsView (USPTO), brevetti concessi. Il comando `brevetti-sonda` verifica indirizzi, dimensioni e nomi delle colonne.
Limite: copre le società presenti nell'elenco SEC (USA e ADR); le società quotate solo all'estero (Siemens, Samsung…) richiedono alias."""
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

from . import titoli_eventi as ev
from .config import DATA

FILE = DATA / "brevetti.json"
NON_ABBINATI = DATA / "brevetti_non_abbinati.csv"
ALIAS_FILE = DATA / "universo" / "alias_brevetti.json"
CACHE = DATA / "_cache" / "brevetti"
URL_BULK = {
    "brevetti": ["https://s3.amazonaws.com/data.patentsview.org/download/g_patent.tsv.zip", "https://data.patentsview.org/download/g_patent.tsv.zip"],
    "titolari": ["https://s3.amazonaws.com/data.patentsview.org/download/g_assignee_disambiguated.tsv.zip", "https://data.patentsview.org/download/g_assignee_disambiguated.tsv.zip"],
}
COL_ORG = ("disambig_assignee_organization", "assignee_organization", "organization")
UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}

# nome normalizzato del titolare → ticker (gruppi con filiali che brevettano con altri nomi). Esteso da data/universo/alias_brevetti.json.
ALIAS_BASE = {
    "google": "GOOGL", "waymo": "GOOGL", "verily life sciences": "GOOGL", "deepmind technologies": "GOOGL", "x development": "GOOGL",
    "facebook": "META", "facebook technologies": "META", "meta platforms technologies": "META", "meta platforms": "META",
    "amazon technologies": "AMZN", "amazon com": "AMZN", "amazon.com": "AMZN",
    "microsoft technology licensing": "MSFT", "microsoft": "MSFT", "linkedin": "MSFT", "github": "MSFT",
    "apple": "AAPL", "international business machines": "IBM", "intel": "INTC", "qualcomm": "QCOM", "nvidia": "NVDA", "oracle international": "ORCL",
    "ford global technologies": "F", "general motors global technology operations": "GM", "gm global technology operations": "GM", "tesla": "TSLA",
    "boeing": "BA", "the boeing": "BA", "lockheed martin": "LMT", "raytheon technologies": "RTX", "raytheon": "RTX", "general electric": "GE", "ge aviation systems": "GE",
    "medtronic": "MDT", "johnson johnson": "JNJ", "ethicon": "JNJ", "janssen pharmaceutica": "JNJ", "pfizer": "PFE", "merck sharp dohme": "MRK", "eli lilly": "LLY",
    "abbvie": "ABBV", "amgen": "AMGN", "gilead sciences": "GILD", "regeneron pharmaceuticals": "REGN", "applied materials": "AMAT", "lam research": "LRCX",
    "micron technology": "MU", "texas instruments": "TXN", "taiwan semiconductor manufacturing": "TSM", "broadcom": "AVGO", "cisco technology": "CSCO",
}
GENERICI = {"general", "american", "united", "national", "first", "new", "international", "global", "advanced", "applied", "digital", "energy", "technology",
            "technologies", "systems", "medical", "health", "pharma", "pharmaceuticals", "therapeutics", "biosciences", "bio", "labs", "industries", "solutions",
            "services", "financial", "capital", "partners", "resources", "materials", "power", "electric", "software", "networks", "data", "life", "sciences", "science"}
MIN_LUNGO = 7


def indice_nomi(voci: list[tuple[str, str, str]]) -> dict:
    """voci: (ticker, cik, titolo SEC). Restituisce nome normalizzato → {"cik", "tickers"}. I nomi condivisi da società diverse (CIK diversi) si scartano."""
    out, ambigui = {}, set()
    for tk, cik, titolo in voci:
        n = ev.normalizza_nome(titolo)
        if not n:
            continue
        if n in out and out[n]["cik"] != cik:
            ambigui.add(n)
        elif n in out:
            out[n]["tickers"].append(tk)
        else:
            out[n] = {"cik": cik, "tickers": [tk]}
    for n in ambigui:
        out.pop(n, None)
    return out


def carica_alias() -> dict:
    a = {ev.normalizza_nome(k): v for k, v in ALIAS_BASE.items()}
    try:
        a.update({ev.normalizza_nome(k): v for k, v in json.loads(ALIAS_FILE.read_text(encoding="utf-8")).items()})
    except Exception:  # noqa: BLE001
        pass
    return a


def abbina(titolare: str, indice: dict, alias: dict | None = None) -> tuple[list[str], str] | None:
    """Titolare del brevetto → (tickers, livello) oppure None. Livelli: «alias», «esatto», «prefisso»."""
    alias = ALIAS_BASE if alias is None else alias
    n = ev.normalizza_nome(titolare)
    if not n:
        return None
    if n in alias:
        return [alias[n]], "alias"
    if n in indice:
        return list(indice[n]["tickers"]), "esatto"
    parole = n.split()
    for k in range(len(parole) - 1, 0, -1):
        p = " ".join(parole[:k])
        if p in alias:
            return [alias[p]], "alias"
        if p in indice and p not in GENERICI and (k >= 2 or len(p) >= MIN_LUNGO):
            return list(indice[p]["tickers"]), "prefisso"
    return None


def conta(df: pd.DataFrame, indice: dict, oggi: str, alias: dict | None = None) -> dict:
    """df: colonne `org` (titolare) e `data` (data di concessione). Per ogni ticker abbinato: brevetti degli ultimi 12 mesi, dei 12 precedenti, variazione.
    Restituisce {"t": {ticker: {...}}, "meta": {...}, "non_abbinati": Counter}."""
    d = pd.to_datetime(df["data"], errors="coerce")
    o = pd.Timestamp(oggi)
    ult = (d > o - pd.Timedelta(days=365)) & (d <= o)
    pre = (d > o - pd.Timedelta(days=730)) & (d <= o - pd.Timedelta(days=365))
    g = pd.DataFrame({"org": df["org"].fillna(""), "ult": ult.astype(int), "pre": pre.astype(int)}).groupby("org").sum()
    g = g[(g["ult"] > 0) | (g["pre"] > 0)]
    out, mancanti, livelli = {}, Counter(), Counter()
    tot_ult = abbinati_ult = 0
    for org, r in g.iterrows():
        tot_ult += int(r["ult"])
        if not org:
            continue
        m = abbina(org, indice, alias)
        if not m:
            mancanti[org] += int(r["ult"])
            continue
        tickers, liv = m
        abbinati_ult += int(r["ult"])
        livelli[liv] += int(r["ult"])
        for tk in tickers:
            x = out.setdefault(tk, {"n12": 0, "n12p": 0})
            x["n12"] += int(r["ult"])
            x["n12p"] += int(r["pre"])
    for x in out.values():
        x["crescita"] = None if x["n12p"] < 10 else round(x["n12"] / x["n12p"] - 1, 3)
    meta = {"asof": oggi, "titolari": int(len(g)), "societa_abbinate": len(out), "brevetti_12m": tot_ult,
            "quota_abbinata": None if not tot_ult else round(abbinati_ult / tot_ult, 3), "per_livello": dict(livelli)}
    return {"t": out, "meta": meta, "non_abbinati": mancanti}


# ---------------------------------------------------------------- file PatentsView
def _colonna(cols, candidati):
    for c in candidati:
        if c in cols:
            return c
    return None


def leggi_bulk(zip_brevetti: Path, zip_titolari: Path, oggi: str, chunk: int = 500_000) -> pd.DataFrame:
    """Unisce i due file: patent_id → data di concessione (solo ultimi ~25 mesi) e patent_id → titolare organizzazione. Legge a pezzi per non esaurire la memoria."""
    limite = pd.Timestamp(oggi) - pd.Timedelta(days=740)

    def apri(z: Path):
        zf = zipfile.ZipFile(z)
        nome = [n for n in zf.namelist() if n.lower().endswith(".tsv")][0]
        return zf.open(nome)
    date = {}
    with apri(zip_brevetti) as f:
        for ch in pd.read_csv(f, sep="\t", dtype=str, chunksize=chunk, usecols=lambda c: c in ("patent_id", "patent_date", "patent_type"), on_bad_lines="skip"):
            ch = ch.dropna(subset=["patent_id", "patent_date"])
            if "patent_type" in ch:
                ch = ch[ch["patent_type"].fillna("utility").str.contains("utility", case=False)]
            dt = pd.to_datetime(ch["patent_date"], errors="coerce")
            ch = ch[dt >= limite]
            date.update(zip(ch["patent_id"], ch["patent_date"]))
    righe = []
    with apri(zip_titolari) as f:
        it = pd.read_csv(f, sep="\t", dtype=str, chunksize=chunk, on_bad_lines="skip")
        for ch in it:
            col = _colonna(ch.columns, COL_ORG)
            if col is None:
                raise ValueError("colonna del titolare non trovata: " + ", ".join(ch.columns))
            ch = ch[ch["patent_id"].isin(date)]
            righe.append(pd.DataFrame({"org": ch[col], "data": ch["patent_id"].map(date)}))
    return pd.concat(righe, ignore_index=True).dropna(subset=["org"]) if righe else pd.DataFrame(columns=["org", "data"])


def scarica(chiave: str, log=print) -> Path | None:
    import requests
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / (chiave + ".zip")
    for url in URL_BULK[chiave]:
        try:
            with requests.get(url, headers=UA, stream=True, timeout=120) as r:
                if r.status_code != 200:
                    log(f"[brevetti] {url}: HTTP {r.status_code}")
                    continue
                with open(dest, "wb") as f:
                    for blocco in r.iter_content(1 << 20):
                        f.write(blocco)
            log(f"[brevetti] scaricato {chiave}: {dest.stat().st_size / 1e6:.0f} MB da {url}")
            return dest
        except Exception as e:  # noqa: BLE001
            log(f"[brevetti] {url}: {str(e)[:80]}")
    return None


def sonda(log=print) -> str:
    """Verifica che i file PatentsView siano raggiungibili e quanto pesano (richiesta HEAD), e che l'elenco SEC dia nomi e simboli."""
    import requests
    for chiave, urls in URL_BULK.items():
        for u in urls:
            try:
                r = requests.head(u, headers=UA, timeout=40, allow_redirects=True)
                log(f"{chiave}: {u} → HTTP {r.status_code}, {int(r.headers.get('content-length', 0)) / 1e6:.0f} MB")
            except Exception as e:  # noqa: BLE001
                log(f"{chiave}: {u} → errore {str(e)[:80]}")
    try:
        from . import titoli_fond as tf
        voci = tf.titoli_sec()
        log(f"elenco SEC: {len(voci)} società; esempi: {voci[:3]}")
        idx = indice_nomi(voci)
        for prova in ("Apple Inc.", "Microsoft Technology Licensing, LLC", "Google LLC", "NVIDIA Corporation", "Qualcomm Incorporated", "Taiwan Semiconductor Manufacturing Co., Ltd."):
            log(f"  {prova!r} → {abbina(prova, idx, carica_alias())}")
    except Exception as e:  # noqa: BLE001
        log("elenco SEC non disponibile: " + str(e)[:100])
    return "fine"


def aggiorna(oggi: str | None = None, log=print) -> dict:
    """Scarica i due file, conta i brevetti per società quotata, scrive data/brevetti.json e l'elenco dei titolari non abbinati."""
    from . import titoli_fond as tf
    oggi = oggi or str(pd.Timestamp.today().date())
    zb, zt = scarica("brevetti", log), scarica("titolari", log)
    if not zb or not zt:
        log("[brevetti] file non disponibili: nessun aggiornamento (l'esito non è un errore)")
        return {}
    df = leggi_bulk(zb, zt, oggi)
    log(f"[brevetti] {len(df)} coppie brevetto-titolare negli ultimi 25 mesi")
    idx = indice_nomi(tf.titoli_sec())
    r = conta(df, idx, oggi, carica_alias())
    FILE.write_text(json.dumps({"meta": r["meta"], "t": r["t"]}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pd.DataFrame(r["non_abbinati"].most_common(300), columns=["titolare", "brevetti_12m"]).to_csv(NON_ABBINATI, index=False)
    log(f"[brevetti] {r['meta']}")
    for f in (zb, zt):
        f.unlink(missing_ok=True)
    return r["meta"]


def carica() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8")).get("t", {})
    except Exception:  # noqa: BLE001
        return {}


def frase(b: dict | None, rd_cap: float | None = None) -> str | None:
    """Frase in italiano semplice sui brevetti di un'azienda, o None se non c'è nulla di notevole."""
    if not b or b.get("n12", 0) < 5:
        return None
    t = f"{b['n12']} brevetti concessi negli ultimi 12 mesi"
    if b.get("crescita") is not None:
        t += f" ({b['crescita'] * 100:+.0f}% rispetto ai 12 mesi prima)"
    if rd_cap:
        t += f"; spende in ricerca e sviluppo il {rd_cap * 100:.1f}% del proprio valore di Borsa all'anno".replace(".", ",")
    return t.replace("+-", "-")
