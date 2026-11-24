# -*- coding: utf-8 -*-
"""Laboratorio vivo e semaforo «terreno». Regole in PROTOCOLLO_LABORATORIO.md (congelamento 24/11/2026). Peso zero: informativo."""
import html as _h
import json

import numpy as np
import pandas as pd

from .config import DATA

REG = DATA / "laboratorio_registro.csv"
OUT = DATA / "laboratorio.json"
CONGELAMENTO = "2026-11-24"
IPOTESI = [  # chiave, nome semplice, segno atteso, storia
    ("v1", "Salto rapido dell'indice", 1, "indizio debole (PROTOCOLLO_VELOCITA)"),
    ("d2", "Indice in salita mentre il mercato sale", 1, "vede molti crolli ma sbaglia spesso"),
    ("calma", "Terreno calmo", -1, "l'unica cosa che ha retto nei test: meno cali"),
    ("bolla_rosso", "Bolla rossa", 1, "indizio, non dimostrato"),
    ("cred_rosso", "Credito rosso", 1, "provato su pochi casi"),
    ("fondi_alto", "Fondi molto difensivi", 1, "non supportato nella storia"),
]
# probabilità storiche (ESITO_CONVERGENZA, S&P 500 1990-2020, senza shock esterni): calo -8% in 63 sedute
P_CALMA = {"calmo": (0.11, 0.14), "altri": (0.23, 0.19)}


def stati(a: pd.Series, px: pd.Series) -> pd.DataFrame:
    """Stati giornalieri dell'indice (definizioni fissate nei protocolli DIVERGENZA, VELOCITA, CONVERGENZA)."""
    px = px.reindex(a.index).ffill()
    mkt = ((px / px.rolling(252, min_periods=126).max() - 1) >= -0.03) & ((px / px.shift(63) - 1) >= 0.03)
    m10 = a.rolling(10).mean(); da = a - a.shift(10)
    f = lambda x: x.fillna(False).astype(bool)
    d1 = f(mkt & ((m10 - m10.shift(42)) >= 6)); d2 = f(mkt & ((m10 - m10.shift(21)) >= 4))
    d3 = f(mkt & (m10 >= 45)); v1 = f((da >= 10) & (a < 60))
    w = lambda x: x.rolling(21, min_periods=1).max().astype(bool)
    n = w(d1 | d2).astype(int) + w(v1).astype(int) + w(d3).astype(int)
    calma = f((n == 0) & ((m10 - m10.shift(42)) < 2))
    return pd.DataFrame({"v1": v1, "d2": d2, "calma": calma, "n": n})


def _carica():
    from . import store
    t = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
    return t["armor_tarato"].dropna(), store.load("sp500").dropna()


def oggi() -> dict:
    a, px = _carica(); s = stati(a, px).iloc[-1]; row = {"data": str(a.index[-1].date()), "armor": float(a.iloc[-1])}
    row.update({k: int(bool(s[k])) for k in ("v1", "d2", "calma")}); row["n"] = int(s["n"])
    try:
        sk = json.loads((DATA / "territori.json").read_text(encoding="utf-8"))["sick"]
        row["bolla"] = float(sk["bolla"]["valore"]); row["cred"] = float(sk["cred"]["valore"])
    except Exception:  # noqa: BLE001
        row["bolla"] = row["cred"] = np.nan
    try:
        row["fondi"] = float(json.loads((DATA / "difensivita.json").read_text(encoding="utf-8"))["valore"])
    except Exception:  # noqa: BLE001
        row["fondi"] = np.nan
    row["bolla_rosso"] = int(row["bolla"] >= 80); row["cred_rosso"] = int(row["cred"] >= 80); row["fondi_alto"] = int(row["fondi"] >= 80)
    return row


def registra(row: dict) -> None:
    new = pd.DataFrame([row]); old = pd.read_csv(REG) if REG.exists() else pd.DataFrame()
    pd.concat([old, new], ignore_index=True).drop_duplicates(subset=["data"], keep="last").sort_values("data").to_csv(REG, index=False)


def _episodi(s: np.ndarray, gap: int = 126) -> int:
    n, ult = 0, -10 ** 9
    for i in np.flatnonzero(s):
        if i - ult >= gap: n += 1
        ult = i
    return n


def valuta(reg: pd.DataFrame, px: pd.Series, congelamento: str = CONGELAMENTO) -> dict:
    """Verdetto per ipotesi con i soli giorni dopo il congelamento e finestra futura completa."""
    out = {}
    reg = reg[reg["data"] >= congelamento].copy()
    if reg.empty:
        return {k: {"giorni": 0, "episodi": 0, "verdetto": "in attesa", "motivo": "nessun giorno registrato"} for k, *_ in IPOTESI}
    reg["data"] = pd.to_datetime(reg["data"]); idx = px.index
    pos = idx.get_indexer(reg["data"]); pv = px.to_numpy()
    def fw(i, h, x):
        if i < 0 or i + h >= len(pv): return np.nan
        return float(pv[i + 1:i + h + 1].min() / pv[i] - 1 <= -x)
    Y = {"T2": np.array([fw(i, 63, 0.08) for i in pos]), "T3": np.array([fw(i, 21, 0.05) for i in pos])}
    mesi = reg["data"].dt.to_period("M").astype(str).to_numpy(); um = np.unique(mesi); rng = np.random.default_rng(7)
    for k, nome, segno, _ in IPOTESI:
        s = reg[k].fillna(0).astype(int).to_numpy().astype(bool)
        ok = ~np.isnan(Y["T2"]); gg = int(ok.sum()); ep = _episodi(s & ok)
        r = {"giorni": gg, "episodi": ep}
        if gg < 126 or ep < 6:
            r.update(verdetto="in attesa", motivo=f"servono almeno 126 giorni valutabili e 6 episodi: ora {gg} giorni e {ep} episodi")
            out[k] = r; continue
        dr, ic = {}, {}
        for yn, y in Y.items():
            m = ~np.isnan(y)
            def f(mm):
                a_, b_ = y[mm & s], y[mm & ~s]
                return np.nan if len(a_) < 5 or len(b_) < 5 else a_.mean() - b_.mean()
            dr[yn] = f(m); bs = []
            for _ in range(400):
                pick = rng.choice(um, len(um)); mm = np.isin(mesi, pick) & m
                v = f(mm)
                if not np.isnan(v): bs.append(v)
            ic[yn] = (np.percentile(bs, 5), np.percentile(bs, 95)) if bs else (np.nan, np.nan)
        sg = lambda v: np.sign(v) * segno
        giusto = [yn for yn in Y if not np.isnan(dr[yn]) and sg(dr[yn]) > 0]
        escl = [yn for yn in giusto if (ic[yn][0] > 0 if segno > 0 else ic[yn][1] < 0)]
        sbag = [yn for yn in Y if not np.isnan(dr[yn]) and (ic[yn][1] < 0 if segno > 0 else ic[yn][0] > 0)]
        if len(giusto) == 2 and escl: v = "confermata"
        elif (not giusto) or sbag: v = "smentita"
        else: v = "non conclusiva"
        r.update(verdetto=v, motivo="differenze " + ", ".join(f"{yn} {dr[yn] * 100:+.0f} punti" for yn in Y if not np.isnan(dr[yn])), dr={k2: (None if np.isnan(x) else round(float(x), 4)) for k2, x in dr.items()})
        out[k] = r
    return out


def run() -> dict:
    row = oggi(); registra(row)
    _, px = _carica()
    reg = pd.read_csv(REG); ver = valuta(reg, px)
    res = {"data": row["data"], "congelamento": CONGELAMENTO, "oggi": {k: bool(row[k]) for k, *_ in IPOTESI}, "n": row["n"], "verdetti": ver,
           "terreno": terreno(row)}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[laboratorio] {row['data']}: terreno {res['terreno']['stato']}, accese {[k for k, *_ in IPOTESI if row[k]]}", flush=True)
    return res


def leggi() -> dict | None:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def terreno(row: dict) -> dict:
    """Semaforo informativo. Verde = nessun segnale e indice fermo (l'unica lettura che ha retto nei test)."""
    rosso = bool(row.get("bolla_rosso") or row.get("cred_rosso"))
    if rosso:
        return {"stato": "rosso", "titolo": "Terreno instabile", "colore": "#ef4444",
                "frase": "Bolla o Credito sono nella zona rossa: in passato il mercato in situazioni simili ha avuto più oscillazioni. Non è un consiglio di vendere."}
    if row.get("calma"):
        (a1, a2), (b1, b2) = P_CALMA["calmo"], P_CALMA["altri"]
        return {"stato": "verde", "titolo": "Terreno calmo", "colore": "#22c55e",
                "frase": f"Nessun segnale acceso e indice fermo. In passato, in giorni così, un calo dell'8% nei tre mesi successivi è arrivato circa {a1 * 100:.0f}-{a2 * 100:.0f} volte su 100, contro {b2 * 100:.0f}-{b1 * 100:.0f} negli altri giorni."}
    return {"stato": "neutro", "titolo": "Terreno nella norma", "colore": "#f59e0b" if row.get("n", 0) >= 1 else "#94a3b8",
            "frase": "Né calmo né in zona rossa. " + ("Un segnale debole si è acceso nelle ultime quattro settimane: erano indizi, non previsioni. " if row.get("n", 0) >= 1 else "") + "Il piano di accumulo resta la regola da battere."}


def striscia_html() -> str:
    d = leggi()
    if not d:
        return ""
    t = d["terreno"]
    ver = d["verdetti"]
    righe = "".join(
        f"<tr><td>{_h.escape(nome)}</td><td>{'acceso' if d['oggi'][k] else 'spento'}</td><td>{_h.escape(ver[k]['verdetto'])}</td></tr>"
        for k, nome, *_ in IPOTESI)
    css = ("<style>.tn{border:1px solid var(--bd);border-left:6px solid var(--c);border-radius:12px;padding:9px 12px;background:var(--card);margin:8px 0}"
           ".tn b.t{font-size:15px;display:block}.tn .d{font-size:12.5px;color:var(--mu);line-height:1.45;margin-top:3px}"
           ".tn details{margin-top:6px}.tn summary{list-style:none;cursor:pointer;font-size:12px;color:var(--mu);display:flex;align-items:center;gap:6px}"
           ".tn summary::-webkit-details-marker{display:none}.tn summary::after{content:\"\";width:6px;height:6px;border-right:2px solid var(--mu);border-bottom:2px solid var(--mu);transform:rotate(45deg);transition:transform .18s}"
           ".tn details[open]>summary::after{transform:rotate(225deg)}"
           ".tn table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}.tn td{padding:3px 4px;border-top:1px solid var(--bd)}"
           ".tn .x{font-size:12px;color:var(--mu);line-height:1.5;margin-top:6px}</style>")
    return (css + f"<div class='tn' style='--c:{t['colore']}'><b class='t'>{_h.escape(t['titolo'])}</b><div class='d'>{_h.escape(t['frase'])}</div>"
            "<details><summary>Laboratorio: le ipotesi in prova</summary>"
            f"<div class='x'>Ogni ipotesi viene registrata ogni giorno dal {CONGELAMENTO[8:]}/{CONGELAMENTO[5:7]}/{CONGELAMENTO[:4]} con la sua soglia già fissata. Quando ci sono abbastanza giorni (almeno 126) e casi (almeno 6), l'app scrive da sola se è confermata o smentita. Finché dice «in attesa», non è una prova.</div>"
            f"<table>{righe}</table></details></div>")
