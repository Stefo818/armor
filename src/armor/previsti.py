"""P/E e P/S «previsti» dell'S&P 500: somma delle capitalizzazioni / somma degli utili (o ricavi) attesi a 12 mesi dagli analisti.
Una riga a settimana in data/series/pe_fwd.csv e ps_fwd.csv (la storia parte dal primo giro). Fonte: yfinance su ~500 titoli."""
import io
from datetime import date

import pandas as pd
import requests

from . import store

WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def lista_sp500() -> list[str]:
    r = requests.get(WIKI, headers={"User-Agent": "Mozilla/5.0 (Armor personal research)"}, timeout=40)
    r.raise_for_status()
    t = pd.read_html(io.StringIO(r.text))[0]
    return [str(x).replace(".", "-") for x in t["Symbol"].tolist()]


def aggrega(righe: list[dict]) -> dict | None:
    """righe: marketCap, epsF (utile per azione atteso x azioni = utile atteso), revF (ricavi attesi). Esclude i titoli senza stima."""
    pe = [(r["cap"], r["utile"]) for r in righe if r.get("cap") and r.get("utile") and r["utile"] > 0]
    ps = [(r["cap"], r["ricavi"]) for r in righe if r.get("cap") and r.get("ricavi") and r["ricavi"] > 0]
    if len(pe) < 100 or len(ps) < 100:
        return None
    return {"pe_fwd": sum(c for c, _ in pe) / sum(u for _, u in pe), "ps_fwd": sum(c for c, _ in ps) / sum(v for _, v in ps),
            "n_pe": len(pe), "n_ps": len(ps)}


def _una(sym: str) -> dict:
    import yfinance as yf
    t = yf.Ticker(sym)
    info = t.info or {}
    cap = info.get("marketCap")
    sh = info.get("sharesOutstanding")
    eps_f = info.get("forwardEps")
    ricavi = None
    try:
        re_ = t.revenue_estimate
        if re_ is not None and len(re_):
            for lab in ("+1y", "0y"):
                if lab in re_.index and pd.notna(re_.loc[lab, "avg"]):
                    ricavi = float(re_.loc[lab, "avg"])
                    break
    except Exception:  # noqa: BLE001
        pass
    return {"cap": cap, "utile": (eps_f * sh) if (eps_f and sh) else None, "ricavi": ricavi}


def aggiorna(forza: bool = False) -> str:
    old = store.load("pe_fwd")
    if not forza and len(old) and (pd.Timestamp(date.today()) - old.index[-1]).days < 6:
        return "già aggiornato questa settimana"
    from .guard import run_parallel
    syms = lista_sp500()
    res = run_parallel({s: (lambda s=s: _una(s)) for s in syms}, workers=8, deadline=900)
    righe = [v for k, v in res.values() if k == "ok"]
    a = aggrega(righe)
    if not a:
        return f"dati insufficienti ({len(righe)} titoli)"
    d = pd.Timestamp(date.today())
    store.upsert("pe_fwd", pd.Series([a["pe_fwd"]], index=[d]))
    store.upsert("ps_fwd", pd.Series([a["ps_fwd"]], index=[d]))
    return f"P/E previsto {a['pe_fwd']:.1f} ({a['n_pe']} titoli), P/S previsto {a['ps_fwd']:.2f} ({a['n_ps']} titoli)"
