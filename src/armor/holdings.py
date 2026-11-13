"""Composizione del fondo: principali titoli, settori, concentrazione. Dati live da Yahoo (fondo VT, che replica lo stesso indice
FTSE All-World di VWCE); se non disponibili si usa l'ultima fotografia nota (30/09/2026, fonte Trackinsight sui dati di VWCE)."""
import json
from datetime import datetime, timezone

import numpy as np

from .config import DATA

FILE = DATA / "holdings.json"
FALLBACK = {
    "date": "2026-09-30", "source": "Trackinsight (VWCE)",
    "top": [("NVIDIA", 5.01), ("Apple", 4.52), ("Microsoft", 3.58), ("Amazon", 2.27), ("Alphabet (A+C)", 3.40),
            ("Taiwan Semiconductor", 1.78), ("Broadcom", 1.54), ("Meta", 1.50), ("Micron", 1.13)],
    "sectors": [("Tecnologia", 38.28), ("Finanza", 17.87), ("Industria", 8.99), ("Salute", 8.04), ("Beni di consumo base", 7.88),
                ("Materiali", 4.25), ("Energia", 3.94), ("Beni di consumo ciclici", 3.72), ("Servizi di pubblica utilità", 2.24)],
}
SECT_IT = {"technology": "Tecnologia", "financial_services": "Finanza", "industrials": "Industria", "healthcare": "Salute",
           "consumer_defensive": "Beni di consumo base", "basic_materials": "Materiali", "energy": "Energia",
           "consumer_cyclical": "Beni di consumo ciclici", "utilities": "Servizi di pubblica utilità",
           "communication_services": "Comunicazioni", "realestate": "Immobiliare"}


def _cap(sym: str):
    """Capitalizzazione di mercato in miliardi di dollari (None se non disponibile)."""
    try:
        import yfinance as yf
        v = yf.Ticker({"2330.TW": "TSM"}.get(sym, sym)).fast_info["market_cap"]   # TSMC: si usa l'ADR di New York, già in dollari
        return round(float(v) / 1e9, 1) if v and float(v) > 0 else None
    except Exception:  # noqa: BLE001
        return None


BASE_INIT = "2026-11-07"   # data da cui si parte con i pesi di Yahoo già in archivio (non cambiavano da allora)
SETT_ETF = {"Tecnologia": "IXN", "Finanza": "IXG", "Industria": "EXI", "Salute": "IXJ", "Beni di consumo base": "KXI", "Materiali": "MXI", "Energia": "IXC",
            "Beni di consumo ciclici": "RXI", "Servizi di pubblica utilità": "JXI", "Comunicazioni": "IXP", "Immobiliare": "REET"}   # ETF settoriali mondiali (iShares)


def _prezzi(simboli: list[str], giorno: str | None = None) -> dict:
    """Ultimo prezzo di ogni simbolo (oppure chiusura al giorno indicato). I simboli senza dato mancano dal risultato."""
    import pandas as pd
    import yfinance as yf
    out = {}
    if giorno is None:
        for s in simboli:
            try:
                v = float(yf.Ticker(s).fast_info["last_price"])
                if v > 0:
                    out[s] = v
            except Exception:  # noqa: BLE001
                pass
        return out
    d0 = pd.Timestamp(giorno)
    for s in simboli:
        try:
            h = yf.Ticker(s).history(start=(d0 - pd.Timedelta(days=7)).strftime("%Y-%m-%d"), end=(d0 + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), auto_adjust=False)["Close"].dropna()
            if len(h):
                out[s] = float(h.iloc[-1])
        except Exception:  # noqa: BLE001
            pass
    return out


def riporta_a_oggi(base: dict, ora: dict) -> tuple[list, list, str]:
    """Pesi di oggi = peso di Yahoo × (prezzo oggi / prezzo alla data di Yahoo) ÷ (movimento del fondo VT). Se manca un prezzo il peso resta quello di Yahoo.
    I settori usano gli ETF settoriali mondiali e si riportano a 100. Restituisce (titoli, settori, nota)."""
    vt = (ora.get("VT") or 0) / (base["prezzi"].get("VT") or 1) if ora.get("VT") and base["prezzi"].get("VT") else None
    if not vt:
        return base["top"], base["sectors"], "pesi di Yahoo non riportati a oggi (prezzo del fondo non disponibile)"
    top = []
    for n, w0, sym, *_ in base["top"]:
        p0, p1 = base["prezzi"].get(sym), ora.get(sym)
        top.append([n, w0 * (p1 / p0) / vt if p0 and p1 else w0, sym])
    sec = []
    for n, w0 in base["sectors"]:
        e = SETT_ETF.get(n)
        p0, p1 = base["prezzi"].get(e), ora.get(e)
        sec.append([n, w0 * (p1 / p0) / vt if p0 and p1 else w0])
    tot = sum(x[1] for x in sec)
    if tot > 0:
        sec = sorted(([n, w * 100 / tot] for n, w in sec), key=lambda x: -x[1])
    top.sort(key=lambda x: -x[1])
    return top, sec, ""


def fetch() -> dict:
    import yfinance as yf
    fd = yf.Ticker("VT").funds_data
    top = fd.top_holdings
    sec = fd.sector_weightings
    t = [[str(r.get("Name", i)), float(r["Holding Percent"]) * 100, str(i)] for i, r in top.iterrows()] if hasattr(top, "iterrows") else []
    s = sorted(((SECT_IT.get(k, k), float(v) * 100) for k, v in dict(sec).items()), key=lambda x: -x[1])
    if not t or not s:
        raise ValueError("composizione vuota")
    chiave = [[x[2], round(x[1], 3)] for x in t] + [[n, round(w, 2)] for n, w in s]
    try:
        vecchio = json.loads(FILE.read_text(encoding="utf-8")).get("base")
    except Exception:  # noqa: BLE001
        vecchio = None
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    simboli = ["VT"] + [x[2] for x in t] + [SETT_ETF[n] for n, _ in s if n in SETT_ETF]
    if vecchio and vecchio.get("chiave") == chiave and vecchio.get("prezzi", {}).get("VT"):
        base = vecchio                    # Yahoo non ha cambiato i pesi: si resta sulla stessa data di partenza
    else:
        giorno = BASE_INIT if not vecchio else oggi   # Yahoo ha pubblicato pesi nuovi: da oggi si riparte da lì
        base = {"data": giorno, "chiave": chiave, "top": t, "sectors": [[n, w] for n, w in s], "prezzi": _prezzi(simboli, None if giorno == oggi else giorno)}
    ora = _prezzi(simboli)
    tt, ss, nota = riporta_a_oggi(base, ora)
    caps = {x[2]: _cap(x[2]) for x in tt[:10]}
    tt = [[n, w, sym, caps.get(sym)] for n, w, sym in tt]
    fonte = f"Yahoo Finance (VT, stesso indice di VWCE): pesi del {base['data']} riportati a oggi con i prezzi" + (f" ({nota})" if nota else "")
    return {"date": oggi, "source": fonte, "top": tt, "sectors": ss, "base": base}


def refresh() -> None:
    try:
        d = fetch()
        FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[holdings] composizione aggiornata:", ", ".join(f"{x[2]} {x[1]:.2f}%" for x in d["top"][:3]))
    except Exception as e:  # noqa: BLE001
        print("[holdings] non aggiornata:", str(e)[:80])


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {k: ([list(x) for x in v] if isinstance(v, list) else v) for k, v in FALLBACK.items()}


def concentration(d: dict) -> dict:
    w = np.array([x[1] for x in d["top"]]) / 100
    top10 = float(w[:10].sum())
    return {"top10": top10, "tech": next((v for k, v in d["sectors"] if k == "Tecnologia"), None)}


def html(d: dict) -> str:
    c = concentration(d)
    f = lambda x: f"{x:.1f}%".replace(".", ",")
    bar = lambda v, m: f"<div class='bar'><i style='width:{min(v / m * 100, 100):.0f}%'></i></div>"
    mt = max(x[1] for x in d["top"])
    ms = max(x[1] for x in d["sectors"])
    def cap(x):
        c = x[3] if len(x) > 3 else None
        return f"{c:,.0f}".replace(",", ".") if c else "n.d."
    t = "".join(f"<tr><td>{x[0]}</td><td>{f(x[1])}</td><td class='n'>{cap(x)}</td><td>{bar(x[1], mt)}</td></tr>" for x in d["top"][:10])
    s = "".join(f"<tr><td>{n}</td><td>{f(v)}</td><td>{bar(v, ms)}</td></tr>" for n, v in d["sectors"])
    tech = f" La tecnologia da sola pesa il {f(c['tech'])}." if c["tech"] else ""
    return (f"<p>Anche se VWCE contiene circa 3.700 aziende, i primi dieci titoli pesano il <b>{f(c['top10'] * 100)}</b>.{tech} "
            "È un fondo diversificato per numero di aziende, ma pesa molto sui grandi titoli tecnologici USA.</p>"
            f"<div class='grid2'><div><table><tr><th>Titolo</th><th>Peso</th><th>Cap. $ mld</th><th></th></tr>{t}</table></div>"
            f"<div><table><tr><th>Settore</th><th>Peso</th><th></th></tr>{s}</table></div></div>"
            f"<p class='mu'>Fonte: {d['source']}, dati al {d['date']}. Capitalizzazione in miliardi di dollari, aggiornata a ogni ciclo giornaliero. I pesi si aggiornano ogni giorno con i prezzi: un titolo che scende più del fondo pesa meno.</p>")
