"""Controllo di coerenza dei dati: confronta le serie salvate con i riferimenti (tabella VIX dell'utente, L&S per VWCE) e fra loro.
Scrive data/audit_dati.json. Uso: python -m armor audit-dati  (esce con 1 se trova incoerenze gravi)."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import config, store

RIF = config.DATA / "riferimenti" / "vix_utente.csv"
OUT = config.DATA / "audit_dati.json"


def _tol(a, b, t):
    return abs(float(a) - float(b)) <= t


def controlla(vix=None, sp=None, ls=None, xe=None, rif=None) -> list[dict]:
    vix = store.load("vix") if vix is None else vix
    sp = store.load("sp500") if sp is None else sp
    ls = store.load("vwce_ls") if ls is None else ls
    xe = store.load("vwce_de") if xe is None else xe
    if rif is None:
        rif = pd.read_csv(RIF, parse_dates=["date"]).set_index("date") if RIF.exists() else pd.DataFrame()
    out = []

    def add(nome, ok, dett, grave=True):
        out.append({"controllo": nome, "ok": bool(ok), "dettaglio": dett, "grave": grave})

    # 1) VIX contro la tabella dell'utente (chiusura, e massimo/minimo se indicati)
    for d, r in rif.iterrows():
        if d not in vix.index:
            add(f"VIX {d:%d/%m}", False, "seduta mancante nell'archivio")
            continue
        add(f"VIX {d:%d/%m}", _tol(vix[d], r["close"], 0.05), f"archivio {vix[d]:.2f} · riferimento {r['close']:.2f}")
    # 2) date: le serie principali finiscono nello stesso giorno (o al massimo uno scarto di una seduta)
    ultime = {n: s.dropna().index[-1] for n, s in (("VIX", vix), ("S&P 500", sp), ("VWCE (L&S)", ls)) if len(s.dropna())}
    if len(ultime) > 1:
        mx, mn = max(ultime.values()), min(ultime.values())
        add("Date allineate", (mx - mn).days <= 3, ", ".join(f"{k} {v:%d/%m}" for k, v in ultime.items()))
    # 3) VWCE: L&S contro Xetra (differenze oltre 2,5% in un giorno sono sospette; fino a ~1,5% e' normale: orari di chiusura diversi)
    if len(ls) and len(xe):
        c = pd.concat([ls, xe], axis=1, keys=["ls", "xe"]).dropna().tail(60)
        dif = (c["ls"] / c["xe"] - 1).abs() * 100
        add("VWCE: L&S vs Xetra (ultimi 60 giorni)", dif.max() < 2.5 if len(dif) else True,
            f"scarto massimo {dif.max():.2f}%" if len(dif) else "nessuna data in comune", grave=False)
    # 4) nessun valore assurdo e nessun duplicato
    for nome, s in (("VIX", vix), ("S&P 500", sp), ("VWCE (L&S)", ls)):
        s = s.dropna()
        if s.empty:
            continue
        add(f"{nome}: valori validi", bool((s > 0).all() and s.index.is_unique and s.index.is_monotonic_increasing), f"{len(s)} righe")
        r = s.pct_change().abs().tail(250)
        add(f"{nome}: salti giornalieri plausibili", bool(r.max() < (0.9 if nome == "VIX" else 0.15)), f"massimo {r.max() * 100:.1f}% in un giorno", grave=False)
    return out


def esegui(scrivi: bool = True) -> dict:
    res = controlla()
    gravi = [x for x in res if not x["ok"] and x["grave"]]
    doc = {"generato": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "ok": not gravi,
           "n_controlli": len(res), "n_falliti": sum(not x["ok"] for x in res), "controlli": res}
    if scrivi:
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in res:
        print(("OK   " if x["ok"] else "FAIL ") + x["controllo"] + " — " + x["dettaglio"])
    return doc
