"""Confronto con altri mercati: Europa, Giappone, emergenti e settori USA. Serve a capire se il rischio è globale o solo americano."""
import html as _h

import numpy as np
import pandas as pd

from . import store

REGIONS = [("sp500", "S&P 500 (USA)"), ("nasdaq100", "Nasdaq 100 (USA tech)"), ("stoxx50", "Euro Stoxx 50"), ("dax", "DAX (Germania)"),
           ("ftsemib", "FTSE MIB (Italia)"), ("nikkei", "Nikkei 225 (Giappone)"), ("eem", "Mercati emergenti (EEM)"), ("vt", "Mondo (VT, in $)")]
SECTORS = [("sec_xlk", "Tecnologia", "ciclico"), ("sec_xlc", "Comunicazioni", "ciclico"), ("sec_xly", "Consumi ciclici", "ciclico"),
           ("sec_xlf", "Finanza", "ciclico"), ("sec_xli", "Industria", "ciclico"), ("sec_xle", "Energia", "ciclico"), ("sec_xlb", "Materiali", "ciclico"),
           ("sec_xlv", "Salute", "difensivo"), ("sec_xlp", "Beni di consumo base", "difensivo"), ("sec_xlu", "Servizi pubblici", "difensivo"),
           ("sec_xlre", "Immobiliare", "difensivo")]


def stats(s: pd.Series) -> dict | None:
    s = s.dropna()
    if len(s) < 260:
        return None
    last = s.iloc[-1]

    def ret(days):
        t = s.index[-1] - pd.Timedelta(days=days)
        s0 = s[s.index <= t]
        return float(last / s0.iloc[-1] - 1) if len(s0) else None
    ytd0 = s[s.index < pd.Timestamp(s.index[-1].year, 1, 1)]
    lr = np.log(s).diff()
    return {"d1": float(last / s.iloc[-2] - 1), "m1": ret(30), "m3": ret(91), "y1": ret(365),
            "ytd": float(last / ytd0.iloc[-1] - 1) if len(ytd0) else None,
            "dd": float(last / s.iloc[-252:].max() - 1), "ma200": float(last / s.iloc[-200:].mean() - 1),
            "vol": float(lr.iloc[-21:].std() * np.sqrt(252)), "date": s.index[-1].strftime("%d/%m")}


def compute() -> dict:
    reg, sec = [], []
    for k, name in REGIONS:
        st = stats(store.load(k))
        if st:
            reg.append({"key": k, "name": name, **st})
    for k, name, kind in SECTORS:
        st = stats(store.load(k))
        if st:
            sec.append({"key": k, "name": name, "kind": kind, **st})
    out = {"reg": reg, "sec": sec}
    if len(reg) >= 3:
        down = [r for r in reg if r["dd"] <= -0.05]
        below = [r for r in reg if r["ma200"] < 0]
        out["n_dd"], out["n"], out["n_below"] = len(down), len(reg), len(below)
        us = next((r for r in reg if r["key"] == "sp500"), None)
        out["verdict"] = ("globale" if len(down) >= max(3, len(reg) // 2) else ("solo americano" if us and us["dd"] <= -0.05 and len(down) <= 2
                                                                                  else ("contenuto" if len(down) <= 1 else "parziale")))
    if len(sec) >= 6:
        cyc = [x["m3"] for x in sec if x["kind"] == "ciclico" and x["m3"] is not None]
        dif = [x["m3"] for x in sec if x["kind"] == "difensivo" and x["m3"] is not None]
        if cyc and dif:
            out["risk_on"] = float(np.mean(cyc) - np.mean(dif))
    return out


def _pc(x):
    return "—" if x is None else f"{x * 100:+.1f}%".replace(".", ",")


def _cell(x):
    cl = "" if x is None else ("up" if x > 0 else "dn")
    return f"<td class='{cl}'>{_pc(x)}</td>"


def html(m: dict) -> str:
    if not m["reg"]:
        return "<p class='mu'>Dati sugli altri mercati non ancora scaricati: compaiono dopo il prossimo aggiornamento giornaliero.</p>"
    def _row(r):
        dd = f"{r['dd'] * 100:.1f}".replace(".", ",")
        ma = "sopra" if r["ma200"] > 0 else "sotto"
        return (f"<tr data-chart='{r['key']}'><td>{_h.escape(r['name'])}</td>{_cell(r['d1'])}{_cell(r['m1'])}{_cell(r['m3'])}{_cell(r['ytd'])}{_cell(r['y1'])}"
                f"<td>{dd}%</td><td>{ma}</td></tr>")
    rows = "".join(_row(r) for r in m["reg"])
    out = ("<table><tr><th>Mercato</th><th>Ieri</th><th>1 mese</th><th>3 mesi</th><th>Da inizio anno</th><th>1 anno</th><th>Dal massimo</th><th>Media 200g</th></tr>" + rows + "</table>")
    if "verdict" in m:
        txt = {"globale": "Il calo è <b>diffuso</b>: più mercati sono sotto il massimo di almeno 5%. Il rischio è globale e la diversificazione geografica protegge poco.",
               "solo americano": "Il calo è concentrato <b>negli USA</b>: gli altri mercati tengono. La diversificazione geografica (VWCE ha circa un terzo fuori dagli USA) attenua.",
               "contenuto": "La maggior parte dei mercati è vicina ai massimi: nessun segnale di rischio diffuso.",
               "parziale": "Alcuni mercati sono in calo e altri no: il quadro è misto."}[m["verdict"]]
        out += f"<p><b>Rischio globale o solo americano?</b> {m['n_dd']} mercati su {m['n']} sono sotto il massimo annuale di almeno 5%, {m['n_below']} sotto la media a 200 giorni. {txt}</p>"
    if m["sec"]:
        sec = sorted(m["sec"], key=lambda x: -(x["m3"] or -9))
        r2 = "".join(f"<tr data-chart='{x['key']}'><td>{_h.escape(x['name'])} <span class='mu'>({x['kind']})</span></td>{_cell(x['d1'])}{_cell(x['m1'])}{_cell(x['m3'])}{_cell(x['y1'])}</tr>" for x in sec)
        out += "<h3>Settori USA (ordinati per andamento a 3 mesi)</h3><table><tr><th>Settore</th><th>Ieri</th><th>1 mese</th><th>3 mesi</th><th>1 anno</th></tr>" + r2 + "</table>"
        if "risk_on" in m:
            ro = m["risk_on"]
            out += (f"<p><b>Appetito per il rischio:</b> i settori ciclici fanno {_pc(ro)} rispetto ai difensivi negli ultimi 3 mesi. "
                    + ("Il mercato premia i settori ciclici: clima di fiducia." if ro > 0.02 else ("Il mercato si rifugia nei settori difensivi: clima prudente." if ro < -0.02 else "Nessuna preferenza netta.")) + "</p>")
    return out + "<p class='mu'>Tocca una riga per aprire il grafico. Ritorni sui prezzi di chiusura (senza dividendi); i mercati in valute diverse non sono corretti per il cambio.</p>"
