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
        v = yf.Ticker(sym).fast_info["market_cap"]
        return round(float(v) / 1e9, 1) if v and float(v) > 0 else None
    except Exception:  # noqa: BLE001
        return None


def fetch() -> dict:
    import yfinance as yf
    fd = yf.Ticker("VT").funds_data
    top = fd.top_holdings
    sec = fd.sector_weightings
    t = [[str(r.get("Name", i)), float(r["Holding Percent"]) * 100, str(i), _cap(str(i))] for i, r in top.iterrows()] if hasattr(top, "iterrows") else []
    s = sorted(((SECT_IT.get(k, k), float(v) * 100) for k, v in dict(sec).items()), key=lambda x: -x[1])
    if not t or not s:
        raise ValueError("composizione vuota")
    return {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "source": "Yahoo Finance (VT, stesso indice di VWCE)", "top": t, "sectors": s}


def refresh() -> None:
    try:
        d = fetch()
        FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[holdings] composizione aggiornata")
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
            f"<p class='mu'>Fonte: {d['source']}, dati al {d['date']}. Capitalizzazione in miliardi di dollari, aggiornata a ogni ciclo giornaliero. I pesi cambiano lentamente.</p>")
