"""Calendario degli eventi che muovono i mercati: Fed (FOMC), inflazione USA (CPI), lavoro USA, scadenze opzioni, trimestrali.
Le date FOMC e CPI sono quelle ufficiali pubblicate (Federal Reserve, BLS). Lavoro USA e opzioni sono regole: il primo venerdi' del
mese e il terzo venerdi' del mese (di norma). Le trimestrali si leggono da Yahoo quando disponibili."""
from datetime import date, datetime, timedelta

FOMC = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
        "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08"]
FOMC_SEP = {"2026-03-18", "2026-06-17", "2026-09-16", "2026-12-09", "2027-03-17", "2027-06-09", "2027-09-15", "2027-12-08"}
CPI = ["2026-11-10", "2026-12-10", "2027-01-13"]

HELP = {
    "FOMC": "Decisione della banca centrale americana sui tassi: spesso muove forte azioni e obbligazioni.",
    "CPI": "Inflazione USA: se sorprende al rialzo, i mercati temono tassi alti più a lungo.",
    "Lavoro USA": "Rapporto sui nuovi posti di lavoro e disoccupazione USA: una sorpresa muove tassi e azioni.",
    "Opzioni": "Scadenza mensile di opzioni e futures: spesso volumi alti e oscillazioni intraday.",
    "Trimestrale": "Conti trimestrali di una delle grandi aziende del tuo indice.",
}


def _nth_friday(y: int, m: int, n: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(4 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def events(today: date | None = None, days: int = 45, earnings: list | None = None) -> list[dict]:
    today = today or date.today()
    end = today + timedelta(days=days)
    out = []
    for s in FOMC:
        out.append({"date": s, "tipo": "FOMC", "nome": "Decisione Fed sui tassi" + (" (con previsioni)" if s in FOMC_SEP else ""), "peso": 3})
    for s in CPI:
        out.append({"date": s, "tipo": "CPI", "nome": "Inflazione USA (CPI)", "peso": 3})
    y, m = today.year, today.month
    for k in range(0, 4):
        mm = (m - 1 + k) % 12 + 1
        yy = y + (m - 1 + k) // 12
        out.append({"date": _nth_friday(yy, mm, 1).isoformat(), "tipo": "Lavoro USA", "nome": "Rapporto lavoro USA (di norma)", "peso": 3})
        t = _nth_friday(yy, mm, 3)
        quad = mm in (3, 6, 9, 12)
        out.append({"date": t.isoformat(), "tipo": "Opzioni", "nome": "Scadenza trimestrale opzioni/futures (\"tre streghe\")" if quad else "Scadenza mensile opzioni", "peso": 2 if quad else 1})
    for e in earnings or []:
        out.append(e)
    res = [e for e in out if today.isoformat() <= e["date"] <= end.isoformat()]
    return sorted(res, key=lambda e: (e["date"], -e["peso"]))


def fetch_earnings(tickers: dict[str, str], get=None) -> list[dict]:
    """Prossime trimestrali dei titoli indicati (ticker -> nome). Silenzioso se Yahoo non risponde."""
    out = []
    try:
        import yfinance as yf
    except Exception:  # noqa: BLE001
        return out
    for t, name in tickers.items():
        try:
            cal = yf.Ticker(t).calendar
            d = cal.get("Earnings Date") if isinstance(cal, dict) else None
            if d:
                d = d[0] if isinstance(d, (list, tuple)) else d
                out.append({"date": str(d)[:10], "tipo": "Trimestrale", "nome": f"Trimestrale {name}", "peso": 2})
        except Exception:  # noqa: BLE001
            continue
    return out


def next_big(evs: list[dict], today: date | None = None) -> dict | None:
    today = today or date.today()
    big = [e for e in evs if e["peso"] >= 3]
    if not big:
        return None
    e = big[0]
    e = dict(e)
    e["giorni"] = (datetime.fromisoformat(e["date"]).date() - today).days
    return e


def html(evs: list[dict], today: date | None = None) -> str:
    today = today or date.today()
    if not evs:
        return "<p class='mu'>Nessun evento importante nei prossimi giorni.</p>"
    rows = []
    for e in evs[:14]:
        g = (datetime.fromisoformat(e["date"]).date() - today).days
        quando = "oggi" if g == 0 else ("domani" if g == 1 else f"tra {g} giorni")
        cls = "hi" if e["peso"] >= 3 else ""
        rows.append(f"<tr class='{cls}'><td>{datetime.fromisoformat(e['date']).strftime('%d/%m')}</td><td><b>{e['nome']}</b><br><span class='mu'>{HELP.get(e['tipo'], '')}</span></td><td>{quando}</td></tr>")
    return ("<table class='cal'><tr><th>Data</th><th>Evento</th><th>Quando</th></tr>" + "".join(rows) + "</table>"
            "<p class='mu'>Nei giorni degli eventi in evidenza la volatilità tende ad essere più alta: è un buon momento per non reagire d'istinto. "
            "Date FOMC e CPI: fonti ufficiali (Fed, BLS). Rapporto lavoro e opzioni: regola del calendario, può spostarsi di un giorno.</p>")
