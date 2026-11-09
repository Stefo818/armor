"""Eventi, notizie e temi per singolo titolo (PIANO_ESPANSIONE Patch 45.5-45.7). Nessuna AI a pagamento: dizionario di regole (Appendice B),
estrazione dell'importo dei contratti, confronto col settore, temi tecnologici con forza (notizie GDELT + forza relativa dell'ETF) e catalizzatori biotech.
Le regole sono in inglese (le notizie lo sono); l'esito è in italiano. Quando le regole non trovano nulla il titolo resta «causa non identificata»."""
import re

import numpy as np

# evento: (parole chiave EN, etichetta IT, effetto Saldi, effetto Opportunità). Effetti: valori -2..+2 (molto negativo..molto positivo), None = nessuno.
# Ordine = priorità (il primo che trova una parola vince).
EVENTI = [
    ("spam", ("investor alert", "class action reminder", "shareholder rights", "rosen law", "pomerantz", "levi & korsinsky", "bragar", "investors who lost money",
              "securities class action", "law offices", "encourages investors", "deadline alert", "lead plaintiff"), "Avviso di studio legale (ignorato)", 0, 0),
    ("fallimento", ("chapter 11", "bankruptcy", "delisting notice", "minimum bid price", "going concern", "chapter 7"), "Fallimento o rischio di delisting", -2, -2),
    ("indagine", ("sec investigation", "doj ", "subpoena", "accounting irregularities", "restatement", "fraud probe", "wells notice"), "Indagine o irregolarità contabili", -2, -2),
    ("short", ("short report", "hindenburg", "muddy waters", "short seller", "short-seller", "citron research", "culper"), "Rapporto di uno short seller", -1, None),
    ("crl", ("complete response letter", " crl ", "fda declines", "fda rejects", "refuse to file", "clinical hold"), "Rifiuto o blocco FDA", -2, -2),
    ("fda_ok", ("fda approves", "fda approval", "granted approval", "receives fda approval", "fda clears", "fda grants"), "Approvazione FDA", None, 2),
    ("studio_ko", ("did not meet", "failed to meet", "discontinued trial", "trial failed", "missed primary endpoint", "halts trial", "halts study"), "Studio clinico fallito", -2, -2),
    ("studio_ok", ("met primary endpoint", "positive topline", "statistically significant", "positive phase", "positive results", "meets primary"), "Studio clinico riuscito", None, 1),
    ("guid_giu", ("cuts guidance", "lowers outlook", "withdraws guidance", "lowers guidance", "slashes forecast", "cuts forecast", "cuts outlook", "warns on profit", "profit warning"), "Previsioni tagliate", -2, None),
    ("guid_su", ("raises guidance", "raises outlook", "lifts forecast", "raises forecast", "boosts outlook", "raises full-year"), "Previsioni alzate", None, 1),
    ("sotto_attese", ("misses", "below estimates", "falls short", "revenue miss", "disappoints", "weaker than expected", "misses estimates"), "Risultati sotto le attese", -1, None),
    ("sopra_attese", ("beats estimates", "tops estimates", "above estimates", "beats expectations", "better than expected", "record revenue", "record quarter"), "Risultati sopra le attese", None, 1),
    ("acq_target", ("to be acquired", "agrees to be bought", "buyout", "to be taken private", "agrees to be acquired", "take-private", "merger agreement"), "Società in acquisizione", "escludi", "escludi"),
    ("capitale", ("public offering", "priced offering", "at-the-market", "registered direct", "convertible notes offering", "share offering", "dilution"), "Aumento di capitale o diluizione", -1, -1),
    ("contratto", ("awarded", "wins contract", "order worth", "multi-year agreement", "secures contract", "signs agreement", "contract win", "selected by"), "Contratto vinto", None, 1),
    ("downgrade", ("downgrade", "downgraded", "cut to sell", "lowered to underperform", "cuts price target", "lowers price target"), "Declassamento degli analisti", -1, None),
    ("upgrade", ("upgrade", "upgraded", "raised to buy", "raises price target", "lifts price target", "initiated with buy"), "Promozione degli analisti", None, 1),
    ("ceo", ("ceo steps down", "ceo resigns", "ceo to step down", "cfo resigns", "cfo steps down", "ceo departure", "abrupt departure"), "Uscita del CEO o del CFO", -1, -1),
    ("richiamo", ("recall", "product recall", "safety alert"), "Richiamo di prodotto", -1, None),
    ("partner", ("partnership", "collaboration", "strategic alliance", "joint venture", "teams up"), "Partnership", None, 1),
    ("regole", ("tariff", "export ban", "export controls", "antitrust", "regulatory", "ban on"), "Dazi o regole", -1, None),
    ("causa", ("lawsuit", "sued", "class action", "settlement", "litigation"), "Causa legale", -1, None),
]
SPAM = {e[0] for e in EVENTI if e[0] == "spam"}
IMPORTO = re.compile(r"(?:US\$|\$|€|£)\s?(\d+(?:[.,]\d+)?)\s?(billion|bn|million|mn|m|b|thousand|k)?", re.I)
MOLT = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
PDUFA = re.compile(r"PDUFA[^.]{0,60}?(?:date|goal)[^.]{0,30}?(?:of|is|on)\s+([A-Z][a-z]+\.? \d{1,2},? \d{4})", re.I)


def importo(testo: str) -> float | None:
    """Importo massimo citato nel testo (valuta unica: solo il numero), es. «$1.2 billion» → 1.2e9."""
    best = None
    for m in IMPORTO.finditer(testo or ""):
        try:
            v = float(m.group(1).replace(",", ".")) * MOLT.get((m.group(2) or "").lower(), 1.0)
        except ValueError:
            continue
        if v >= 1e5 and (best is None or v > best):
            best = v
    return best


def classifica(titolo: str, riassunto: str = "") -> dict | None:
    """Evento riconosciuto nel titolo (e nel riassunto breve), con effetti e importo. None se nessuna regola scatta."""
    low = " " + (titolo or "").lower() + " "
    for chiave, parole, etichetta, es, eo in EVENTI:
        if any(p in low for p in parole):
            return {"evento": chiave, "etichetta": etichetta, "saldi": es, "opp": eo, "importo": importo((titolo or "") + " " + (riassunto or "")), "spam": chiave in SPAM}
    return None


def pct_fatturato(imp: float | None, ricavi_annui: float | None) -> float | None:
    return None if not imp or not ricavi_annui or ricavi_annui <= 0 else round(imp / ricavi_annui, 3)


def riassumi(notizie: list[dict], ricavi_annui: float | None = None) -> dict:
    """Notizie di un titolo → eventi (senza spam), ordinati dal più recente. Ogni notizia: title, time, source, link."""
    ev = []
    for n in notizie:
        c = classifica(n.get("title", ""), n.get("summary", ""))
        if not c or c["spam"]:
            continue
        ev.append({**c, "titolo": n.get("title"), "data": (n.get("time") or "")[:10], "fonte": n.get("source"), "link": n.get("link"),
                   "pct_fatturato": pct_fatturato(c["importo"], ricavi_annui) if c["evento"] == "contratto" else None})
    ev.sort(key=lambda e: e["data"], reverse=True)
    return {"eventi": ev[:8], "escludi": any(e["saldi"] == "escludi" for e in ev), "n_spam": sum(1 for n in notizie if (classifica(n.get("title", "")) or {}).get("spam"))}


def causa_calo(r_titolo: float | None, r_settore: float | None, beta: float, eventi: list[dict]) -> dict:
    """Perché è sceso? Rendimento in eccesso = titolo − β·settore. Se il settore spiega la maggior parte del calo → «settore/mercato»."""
    if r_titolo is None:
        return {"tipo": "ignota", "testo": "Dati insufficienti."}
    ecc = None if r_settore is None else r_titolo - beta * r_settore
    neg = [e for e in eventi if e.get("saldi") not in (None, "escludi", 0) and e["saldi"] < 0]
    if ecc is not None and r_titolo < 0 and abs(ecc) < 0.3 * abs(r_titolo):
        return {"tipo": "settore", "ecc": ecc, "testo": "Il calo segue quello del settore o del mercato: non c'è una causa legata solo all'azienda."}
    if neg:
        return {"tipo": "azienda", "ecc": ecc, "testo": neg[0]["etichetta"] + (f" ({neg[0]['data']})" if neg[0].get("data") else "") + "."}
    return {"tipo": "ignota", "ecc": ecc, "testo": "Causa non identificata dalle notizie disponibili."}


# ---------------------------------------------------------------- temi tecnologici (45.7)
# tema: (parole chiave IT/EN, ETF di riferimento, query GDELT)
TEMI = {
    "Robotica": (("robot", "robotics", "robotica", "humanoid", "automation"), "BOTZ", "robotics humanoid robot"),
    "Intelligenza artificiale": (("artificial intelligence", "intelligenza artificiale", "generative ai", "machine learning", "llm", "data center"), "AIQ", "artificial intelligence"),
    "Semiconduttori": (("semiconductor", "semiconduttori", "chip", "foundry", "wafer", "gpu"), "SMH", "semiconductor chip"),
    "Nucleare e SMR": (("nuclear", "nucleare", "uranium", "uranio", "small modular reactor", "smr"), "URA", "nuclear uranium reactor"),
    "Quantum": (("quantum", "quantistico", "qubit"), "QTUM", "quantum computing"),
    "Spazio": (("space", "spazio", "satellite", "rocket", "launch vehicle", "orbital"), "UFO", "space satellite launch"),
    "Difesa": (("defense", "difesa", "defence", "missile", "military", "drone"), "ITA", "defense military spending"),
    "Farmaci per l'obesità (GLP-1)": (("glp-1", "obesity", "obesità", "semaglutide", "tirzepatide", "weight loss drug"), "XLV", "GLP-1 obesity drug"),
    "Cybersecurity": (("cybersecurity", "cyber security", "ransomware", "zero trust", "endpoint security"), "CIBR", "cybersecurity ransomware"),
    "Reti elettriche e data center": (("power grid", "rete elettrica", "transformer", "data center power", "utilities demand", "grid"), "GRID", "power grid data center electricity"),
    "Editing genetico": (("crispr", "gene editing", "editing genetico", "gene therapy", "base editing"), "ARKG", "crispr gene editing"),
    "Batterie e litio": (("lithium", "litio", "battery", "batterie", "solid-state", "ev battery"), "LIT", "lithium battery"),
}
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=timelinevolraw&timespan=14weeks&format=json"


def temi_di(testo: str) -> list[str]:
    low = " " + (testo or "").lower() + " "
    return [t for t, (parole, _e, _q) in TEMI.items() if any((" " + p) in low for p in parole)]


def accelerazione(volumi: list[float], recenti: int = 14) -> float | None:
    """Volume di notizie delle ultime 2 settimane (giorni) rispetto alla media delle 12 settimane precedenti, normalizzata a pari durata."""
    v = [float(x) for x in volumi if x is not None]
    if len(v) < recenti + 28:
        return None
    ult, prima = np.mean(v[-recenti:]), np.mean(v[:-recenti])
    return None if prima <= 0 else float(ult / prima)


def forza_tema(accel: float | None, rs_1m: float | None, rs_3m: float | None) -> dict:
    """50% accelerazione delle notizie (0,8× → 0 punti; 2× o più → 100) + 50% forza relativa dell'ETF a 1 e 3 mesi contro MSCI World (−10% → 0; +20% → 100)."""
    n = None if accel is None else float(np.clip((accel - 0.8) / 1.2, 0, 1) * 100)
    rs = [x for x in (rs_1m, rs_3m) if x is not None]
    m = None if not rs else float(np.clip((np.mean(rs) + 0.10) / 0.30, 0, 1) * 100)
    parti = [x for x in (n, m) if x is not None]
    return {"forza": None if not parti else round(float(np.mean(parti))), "notizie": None if n is None else round(n), "prezzi": None if m is None else round(m),
            "completa": n is not None and m is not None}


def gdelt_volumi(tema: str, get=None) -> list[float]:
    """Serie giornaliera del volume di notizie del tema (GDELT DOC 2.0, gratuita). Lista vuota se il servizio non risponde."""
    import urllib.parse
    q = urllib.parse.quote(TEMI[tema][2])
    try:
        if get is None:
            import requests
            r = requests.get(GDELT.format(q=q), timeout=40, headers={"User-Agent": "Mozilla/5.0 (Armor personal research)"})
            r.raise_for_status()
            j = r.json()
        else:
            j = get(GDELT.format(q=q))
        return [float(p["value"]) for p in j["timeline"][0]["data"]]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------- biotech (45.6)
def catalizzatori_studi(j: dict, oggi: str, mesi: int = 6) -> list[dict]:
    """Studi di fase 2/3 con completamento primario nei prossimi `mesi` mesi, dalla risposta di ClinicalTrials.gov API v2."""
    out = []
    limite = np.datetime64(oggi) + np.timedelta64(mesi * 30, "D")
    for s in (j or {}).get("studies", []):
        try:
            p = s["protocolSection"]
            fasi = p["designModule"].get("phases", [])
            if not any(f in ("PHASE2", "PHASE3", "PHASE2/PHASE3") for f in fasi):
                continue
            d = p["statusModule"]["primaryCompletionDateStruct"]["date"]
            d = d if len(d) == 10 else d + "-28" if len(d) == 7 else None
            if d is None or not (np.datetime64(oggi) <= np.datetime64(d) <= limite):
                continue
            out.append({"id": p["identificationModule"].get("nctId"),
                        "titolo": p["identificationModule"].get("briefTitle"), "fase": "/".join(f.replace("PHASE", "") for f in fasi), "data": d})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda x: x["data"])


def clinicaltrials_url(sponsor: str) -> str:
    import urllib.parse
    return ("https://clinicaltrials.gov/api/v2/studies?query.spons=" + urllib.parse.quote(sponsor)
            + "&filter.overallStatus=RECRUITING,ACTIVE_NOT_RECRUITING&pageSize=50&fields=NCTId,BriefTitle,Phase,PrimaryCompletionDate")


def rischio_binario(industria: str | None, ricavi_ttm: float | None, n_candidati_fase23: int | None, cap: float | None = None) -> dict | None:
    """Etichetta «rischio binario»: biotech con ricavi quasi nulli e al massimo un prodotto in fase avanzata: un solo studio può dimezzare o raddoppiare il prezzo."""
    if not industria or "biotech" not in industria.lower():
        return None
    if (ricavi_ttm or 0) < 5e6 and (n_candidati_fase23 is None or n_candidati_fase23 <= 1):
        return {"testo": "Rischio binario: ricavi quasi nulli e al massimo un prodotto in fase avanzata. L'esito di un solo studio può dimezzare o raddoppiare il prezzo."}
    return None
