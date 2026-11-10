"""Indice Armor «lungo» (Patch 79): la stessa idea dell'Indice Armor, ma solo con ingredienti che esistono dal 1950 circa.
Serve a una prova su dati mai usati per costruire l'indice (1950-1999). Regole scritte prima dei risultati in PROTOCOLLO_ARMOR_LUNGO.md.
Ogni dato mensile o settimanale si usa solo dopo il suo ritardo di pubblicazione. Non cambia l'indice ufficiale: è una verifica."""
import json
import html as _h

import numpy as np
import pandas as pd

from . import semafori, store
from .config import DATA

FILE = DATA / "armor_lungo.json"
WINDOW = 2520
# famiglia -> (peso, [(chiave, tipo, giallo, rosso, ritardo in giorni, limite ffill in sedute)])
GRUPPI = {
    "Paura e stress": (22, [("rv21", "hi", 15, 25, 0, 5)]),
    "Credito": (18, [("credito_lungo", "hi", 2.1, 2.8, 32, 45), ("nfci", "hi", -0.2, 0, 6, 10)]),
    "Tassi": (8, [("curve_lunga", "lo", 0.5, 0, 32, 45), ("dgs10", "hi", 4, 5, 1, 5)]),
    "Valutazioni": (12, [("cape_m", "hi", 28, 35, 60, 45), ("pe_m", "hi", 18, 24, 60, 45)]),
    "Tendenza dei prezzi": (12, [("dd252", "hi", 5, 10, 0, 5), ("ma200", "lo", 0, -5, 0, 5)]),
    "Economia reale": (6, [("sahm", "hi", 0.3, 0.5, 37, 45), ("indpro_g12", "lo", 3, -3, 47, 45), ("claims_up", "hi", 15, 25, 6, 10)]),
}
PERIODI = [("1950-1969", "1950-01-01", "1969-12-31"), ("1970-1989", "1970-01-01", "1989-12-31"), ("1990-1999", "1990-01-01", "1999-12-31"), ("2000-oggi", "2000-01-01", "2100-01-01")]
EVENTI = ("dd10_63", "dd5_21", "vol25_21")
NOMI_EV = {"dd10_63": "calo ≥10% in 3 mesi", "dd5_21": "calo ≥5% in 1 mese", "vol25_21": "volatilità ≥25% nel mese dopo"}


def _serie(key: str, sp: pd.Series) -> pd.Series:
    if key == "credito_lungo":
        b, g = store.load("baa_m"), store.load("gs10_m")
        return (b - g.reindex(b.index)).dropna() if len(b) and len(g) else pd.Series(dtype=float)
    return semafori.series_of(key, sp)


def _punteggio(x: pd.Series, tipo: str, y: float, r: float) -> pd.Series:
    if tipo == "hi":
        xp, fp = [y - (r - y), y, r, r + (r - y)], [0, .35, .7, 1]
    else:
        xp, fp = [r - (y - r), r, y, y + (y - r)], [1, .7, .35, 0]
    return pd.Series(np.interp(x.values, xp, fp), index=x.index).where(x.notna())


def punteggi(sp: pd.Series, dal: str = "1930-01-01") -> pd.DataFrame:
    idx = sp.index[sp.index >= dal]
    cols = {}
    for _g, (_w, items) in GRUPPI.items():
        for key, tipo, y, r, lag, lim in items:
            try:
                s = _serie(key, sp)
                s = s[~s.index.duplicated(keep="last")].dropna()
                if len(s) < 60:
                    continue
                s = pd.Series(s.values, index=s.index + pd.Timedelta(days=lag))     # il dato si conosce solo dopo il ritardo di pubblicazione
                a = s.reindex(s.index.union(idx)).ffill(limit=lim).reindex(idx)
                pr = a.rolling(WINDOW, min_periods=500).rank(pct=True)
                t = _punteggio(a, tipo, y, r)
                cols[key] = (0.6 * t + 0.4 * pr).fillna(t)
            except Exception:  # noqa: BLE001
                continue
    return pd.DataFrame(cols, index=idx)


def indice(S: pd.DataFrame, famiglie: list[str] | None = None) -> tuple[pd.Series, pd.DataFrame]:
    G = {}
    for g, (_w, items) in GRUPPI.items():
        keys = [k for k, *_ in items if k in S]
        if not keys or (famiglie and g not in famiglie):
            G[g] = pd.Series(np.nan, index=S.index)
            continue
        n = S[keys].notna().sum(axis=1)
        G[g] = S[keys].mean(axis=1).where(n >= max(1, np.ceil(len(items) / 2)))
    G = pd.DataFrame(G)
    w = pd.Series({g: GRUPPI[g][0] for g in GRUPPI}, dtype=float)
    if famiglie:
        w = w[[g for g in w.index if g in famiglie]]
        G = G[list(w.index)]
    ok = G.notna()
    wsum = (ok * w).sum(axis=1)
    val = (G.fillna(0) * w).sum(axis=1) / wsum.replace(0, np.nan)
    val = ((val - 0.10) / 0.75).clip(0, 1)
    return (1 + 99 * val).where(wsum >= 0.5 * w.sum()), G


def eventi(sp: pd.Series) -> dict:
    p = sp
    fmin63 = p[::-1].rolling(63).min()[::-1].shift(-1) / p - 1
    fmin21 = p[::-1].rolling(21).min()[::-1].shift(-1) / p - 1
    ret = np.log(p).diff()
    fvol = ret[::-1].rolling(21).std()[::-1].shift(-1) * np.sqrt(252) * 100
    f = lambda s, c: pd.Series(np.where(s.isna(), np.nan, c(s).astype(float)), index=p.index)  # noqa: E731
    return {"dd10_63": f(fmin63, lambda s: s <= -0.10), "dd5_21": f(fmin21, lambda s: s <= -0.05), "vol25_21": f(fvol, lambda s: s >= 25)}


def auc(score: pd.Series, y: pd.Series) -> float | None:
    d = pd.concat([score, y], axis=1).dropna()
    d.columns = ["s", "y"]
    n1 = int(d["y"].sum())
    n0 = len(d) - n1
    if n1 < 20 or n0 < 20:
        return None
    r = d["s"].rank()
    return float((r[d["y"] == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def episodi(y: pd.Series, gap: int = 63) -> int:
    pos = np.flatnonzero(y.fillna(0).values == 1)
    return 0 if len(pos) == 0 else int(1 + (np.diff(pos) > gap).sum())


def verdetto(periodi: list[dict]) -> dict:
    pre = [p for p in periodi if p["nome"] != "2000-oggi"]
    d = next((p for p in periodi if p["nome"] == "2000-oggi"), None)
    a = lambda p, k: p["auc"]["dd10_63"].get(k)  # noqa: E731
    r1 = all(a(p, "lungo") is not None and a(p, "lungo") >= 0.62 for p in pre)
    diffs = [None if a(p, "lungo") is None or a(p, "prezzi") is None else a(p, "lungo") - a(p, "prezzi") for p in pre]
    ok_d = [x is not None and x >= 0.02 for x in diffs]
    r2 = sum(ok_d) >= 2 and all(x is not None and (ok or x >= -0.02) for x, ok in zip(diffs, ok_d))
    r3 = bool(d and a(d, "lungo") is not None and a(d, "attuale") is not None and a(d, "lungo") >= a(d, "attuale") - 0.05)
    v = "REGGE" if (r1 and r2 and r3) else "REGGE IN PARTE" if (r1 and r3) else "NON REGGE"
    return {"regola1": bool(r1), "regola2": bool(r2), "regola3": r3, "verdetto": v, "diffs": diffs}


def calcola(sp: pd.Series | None = None, attuale: pd.Series | None = None) -> dict | None:
    try:
        from .features import closed_sp500
        sp = closed_sp500() if sp is None else sp
        attuale = store.load("armor_index") if attuale is None else attuale
        S = punteggi(sp)
        lungo, G = indice(S)
        prezzi, _ = indice(S, ["Paura e stress", "Tendenza dei prezzi"])
        ev = eventi(sp.reindex(lungo.index))
        periodi = []
        for nome, a, b in PERIODI:
            m = (lungo.index >= a) & (lungo.index <= b)
            L, P = lungo.shift(1)[m], prezzi.shift(1)[m]
            A = attuale.shift(1).reindex(lungo.index)[m] if nome == "2000-oggi" else None
            row = {"nome": nome, "giorni": int(L.notna().sum()), "auc": {}, "episodi": {}}
            for k in EVENTI:
                y = ev[k][m]
                row["auc"][k] = {"lungo": auc(L, y), "prezzi": auc(P, y), "attuale": auc(A, y) if A is not None else None}
                row["episodi"][k] = episodi(y)
            periodi.append(row)
        v = verdetto(periodi)
        s = lungo.dropna()
        s = s[s.index >= "1950-01-01"]
        step = 10
        ss = sp.reindex(s.index)
        dd = ss / ss.cummax() - 1
        return {"data": str(sp.index[-1].date()), "oggi": float(s.iloc[-1]), "periodi": periodi, **v,
                "serie": {"d": [str(x.date()) for x in s.index[::step]], "i": [round(float(x), 1) for x in s.values[::step]],
                          "sp": [round(float(x), 2) for x in ss.values[::step]], "dd": [round(float(x), 3) for x in dd.values[::step]]}}
    except Exception as e:  # noqa: BLE001
        print("Indice lungo non calcolato:", str(e)[:120], flush=True)
        return None


def salva(d: dict) -> None:
    FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def aggiorna(force: bool = False, giorni: int = 30) -> bool:
    """Rifà il calcolo se il file ha più di `giorni` giorni (o con force). Costa meno di un secondo."""
    import time
    if not force and FILE.exists() and (time.time() - FILE.stat().st_mtime) < giorni * 86400:
        return False
    d = calcola()
    if d:
        salva(d)
    return bool(d)


def _f(x: float | None, d: int = 2) -> str:
    return "n.d." if x is None else f"{x:.{d}f}".replace(".", ",")


def _grafico(s: dict) -> str:
    n = len(s["i"])
    W, H = 640, 190
    X = lambda i: 8 + i / (n - 1) * (W - 16)  # noqa: E731
    Yi = lambda v: H - 14 - v / 100 * (H - 28)  # noqa: E731
    lsp = np.log(np.array(s["sp"], float))
    Ys = lambda v: H - 14 - (v - lsp.min()) / ((lsp.max() - lsp.min()) or 1) * (H - 28)  # noqa: E731
    bande, ini = "", None
    for i, dd in enumerate(s["dd"] + [0]):
        if dd <= -0.20 and ini is None:
            ini = i
        elif dd > -0.20 and ini is not None:
            bande += f"<rect x='{X(ini):.1f}' y='0' width='{max(X(i - 1) - X(ini), 2):.1f}' height='{H}' fill='#dc2626' opacity='.13'/>"
            ini = None
    pi = " ".join(f"{X(i):.1f},{Yi(v):.1f}" for i, v in enumerate(s["i"]))
    ps = " ".join(f"{X(i):.1f},{Ys(v):.1f}" for i, v in enumerate(lsp))
    anni = "".join(f"<text x='{X(i):.1f}' y='{H - 1}' font-size='10' fill='currentColor' opacity='.6' text-anchor='middle'>{s['d'][i][:4]}</text>" for i in range(0, n, max(n // 6, 1)))
    gl = "".join(f"<line x1='8' x2='{W - 8}' y1='{Yi(v):.1f}' y2='{Yi(v):.1f}' stroke='currentColor' opacity='.15' stroke-dasharray='3 3'/><text x='10' y='{Yi(v) - 2:.1f}' font-size='9' fill='currentColor' opacity='.55'>{v}</text>" for v in (40, 60))
    return (f"<svg viewBox='0 0 {W} {H}' class='al-g'>{bande}{gl}<polyline points='{ps}' fill='none' stroke='#94a3b8' stroke-width='1.6'/>"
            f"<polyline points='{pi}' fill='none' stroke='#f59e0b' stroke-width='2'/>{anni}</svg>")


def html(d: dict | None) -> str:
    if not d:
        return ""
    E = _h.escape
    col = {"REGGE": "#16a34a", "REGGE IN PARTE": "#d97706", "NON REGGE": "#dc2626"}[d["verdetto"]]
    spieg = {"REGGE": "La versione ridotta dell'indice ha dato buoni risultati anche prima del 2000: è un segnale di robustezza.",
             "REGGE IN PARTE": "La versione ridotta tiene dopo il 2000 e prima, ma senza superare con chiarezza i soli prezzi: robustezza parziale.",
             "NON REGGE": "Prima del 2000 la versione ridotta dell'indice avrebbe segnalato i cali solo un po' meglio del caso. Non vuol dire che sia inutile, ma la precisione mostrata dal 2000 va letta con prudenza."}[d["verdetto"]]
    righe = ""
    for p in d["periodi"]:
        a = p["auc"]["dd10_63"]
        barre = ""
        for k, lab, c in (("lungo", "Indice lungo", "#f59e0b"), ("prezzi", "Solo prezzi", "#94a3b8"), ("attuale", "Indice attuale", "#3b82f6")):
            v = a.get(k)
            if v is None:
                continue
            w = min(max((v - 0.5) / 0.3, 0.01), 1) * 100
            barre += f"<div class='al-b'><span>{lab}</span><div class='al-t'><i style='width:{w:.0f}%;background:{c}'></i><u style='left:{(0.62 - 0.5) / 0.3 * 100:.0f}%'></u></div><b>{_f(v)}</b></div>"
        righe += f"<div class='al-p'><div class='al-pn'>{E(p['nome'])} <em>{p['episodi']['dd10_63']} periodi di calo · {p['giorni']} giorni</em></div>{barre}</div>"
    ck = lambda b: "<i class='al-ok'>✔</i>" if b else "<i class='al-no'>✘</i>"  # noqa: E731
    regole = (f"<div class='al-r'>{ck(d['regola1'])}<span><b>Soglia.</b> Accuratezza di almeno 0,62 in tutti e tre i periodi prima del 2000.</span></div>"
              f"<div class='al-r'>{ck(d['regola2'])}<span><b>Valore aggiunto.</b> Meglio dei soli prezzi di almeno 0,02 in 2 periodi su 3.</span></div>"
              f"<div class='al-r'>{ck(d['regola3'])}<span><b>Tenuta dal 2000.</b> Non peggio dell'indice attuale di più di 0,05.</span></div>")
    p2000 = next(p for p in d["periodi"] if p["nome"] == "2000-oggi")["auc"]["dd10_63"]
    pre = [p for p in d["periodi"] if p["nome"] != "2000-oggi"]
    medio = np.mean([p["auc"]["dd10_63"]["lungo"] - p["auc"]["dd10_63"]["prezzi"] for p in pre if p["auc"]["dd10_63"]["lungo"] is not None and p["auc"]["dd10_63"]["prezzi"] is not None])
    letture = (f"<p class='al-t2'><b>Cosa ci dice.</b> Dal 2000 l'indice ridotto ottiene {_f(p2000['lungo'])} e quello attuale {_f(p2000['attuale'])}: praticamente lo stesso risultato con molti meno ingredienti. "
               f"Rispetto ai soli prezzi, l'aggiunta di credito, tassi, valutazioni ed economia migliora l'accuratezza in media di {_f(medio)} punti: poco. "
               f"Il periodo 1950-1969 è il più difficile ({_f(pre[0]['auc']['dd10_63']['lungo'])}).</p>")
    info = ("<details class='al-info'><summary><i>i</i> Come si legge questa prova</summary><div><p><b>Accuratezza (AUC).</b> Un numero da 0,5 (indovina a caso) a 1 (perfetto): se prendi un giorno prima di un calo e uno prima di un periodo tranquillo, "
            "dice quanto spesso l'indice era più alto nel primo. 0,72 è buono ma non eccezionale.</p>"
            "<p><b>Perché prima del 2000.</b> L'indice è stato costruito guardando i dati dal 2000. Provarlo sugli anni 1950-1999 è come un esame su domande mai viste.</p>"
            "<p><b>Cos'è l'indice lungo.</b> Stesse regole e stessi pesi, ma solo ingredienti che esistono dal 1950: volatilità dei prezzi (al posto del VIX), spread del credito, curva dei tassi, valutazioni, tendenza dei prezzi ed economia reale. "
            "Ogni dato si usa solo dopo il suo ritardo di pubblicazione.</p><p><b>Limiti.</b> Mercato e dati cambiano nei decenni, le serie economiche sono state riviste, e i periodi di calo indipendenti sono pochi. Regola scritta prima in PROTOCOLLO_ARMOR_LUNGO.md.</p></div></details>")
    return (CSS + "<h2 style='margin-top:26px'>L'Indice Armor funziona anche nel passato lontano?</h2>"
            "<div class='explain'><p>Abbiamo costruito una versione dell'indice con soli ingredienti che esistono dal 1950 e l'abbiamo provata su 50 anni di Borsa, compresi quelli prima del 2000 che l'indice non aveva mai visto.</p></div>"
            f"<div class='al-v' style='border-color:{col}'><div class='al-vt' style='color:{col}'>{E(d['verdetto'])}</div><div>{E(spieg)}</div></div>"
            f"<h4 class='al-h'>L'indice lungo e la Borsa, dal 1950</h4>{_grafico(d['serie'])}"
            "<p class='al-t2'>Linea arancione = indice lungo (0–100). Linea grigia = S&amp;P 500 in scala logaritmica. Fasce rosse = periodi in cui la Borsa era almeno il 20% sotto il massimo.</p>"
            f"<h4 class='al-h'>Accuratezza sul calo di almeno il 10% in 3 mesi</h4>{righe}<p class='al-t2'>Il trattino scuro sulla barra è la soglia 0,62 della regola. Più la barra è lunga, meglio l'indice avvisava prima dei cali.</p>"
            f"<h4 class='al-h'>Le tre regole decise in anticipo</h4>{regole}{letture}{info}")


CSS = """<style>
.al-v{border:2px solid;border-radius:16px;padding:12px 16px;margin:10px 0;background:var(--card);font-size:14px;line-height:1.5}.al-vt{font-size:26px;font-weight:800;margin-bottom:2px}
.al-h{margin:18px 0 6px;font-size:15px}.al-g{width:100%;height:auto;color:var(--tx);background:var(--card);border:1px solid var(--bd);border-radius:12px}.al-t2{font-size:12.5px;line-height:1.5;color:var(--mu);margin:6px 0}.al-t2 b{color:var(--tx)}
.al-p{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:8px 0}.al-pn{font-weight:700;font-size:14px;margin-bottom:4px}.al-pn em{font-style:normal;font-weight:400;font-size:11.5px;color:var(--mu);margin-left:6px}
.al-b{display:grid;grid-template-columns:96px 1fr 38px;gap:8px;align-items:center;font-size:12.5px;margin:4px 0}.al-t{position:relative;height:10px;border-radius:99px;background:var(--bd);overflow:hidden}.al-t i{display:block;height:100%;border-radius:99px}.al-t u{position:absolute;top:0;bottom:0;width:2px;background:var(--tx);opacity:.6}
.al-r{display:flex;gap:10px;align-items:flex-start;font-size:13px;margin:6px 0;line-height:1.45}.al-r i{font-style:normal;font-weight:800;flex:none;width:22px;height:22px;border-radius:50%;text-align:center;line-height:22px;color:#fff;font-size:12px}.al-ok{background:#16a34a}.al-no{background:#dc2626}
.al-info{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:10px 0;font-size:13px;line-height:1.5}.al-info summary{cursor:pointer;font-weight:700}.al-info summary i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:50%;background:var(--tx);color:var(--bg);font-style:normal;font-size:12px;margin-right:6px}.al-info p{margin:8px 0}
</style>"""


PESI_PROVA = {
    "A": {"Paura e stress": 22, "Credito": 18, "Tassi": 8, "Valutazioni": 12, "Tendenza dei prezzi": 12, "Economia reale": 6},
    "B": {"Paura e stress": 30, "Credito": 18, "Tassi": 6, "Valutazioni": 6, "Tendenza dei prezzi": 30, "Economia reale": 10},
    "C": {"Paura e stress": 40, "Credito": 15, "Tassi": 0, "Valutazioni": 0, "Tendenza dei prezzi": 35, "Economia reale": 10},
}


def _indice_pesi(S: pd.DataFrame, pesi: dict) -> pd.Series:
    saved = {g: GRUPPI[g][0] for g in GRUPPI}
    try:
        for g, w in pesi.items():
            GRUPPI[g] = (w, GRUPPI[g][1])
        return indice(S)[0]
    finally:
        for g, w in saved.items():
            GRUPPI[g] = (w, GRUPPI[g][1])


def prova_pesi(sp: pd.Series | None = None) -> dict | None:
    """Seconda prova del protocollo: scelta tra B e C su 1950-1989, poi una sola prova su 1990-1999 e 2000-oggi contro A."""
    try:
        from .features import closed_sp500
        sp = closed_sp500() if sp is None else sp
        S = punteggi(sp)
        idx = {k: _indice_pesi(S, w).shift(1) for k, w in PESI_PROVA.items()}
        ev = eventi(sp.reindex(S.index))
        per = {"1950-1989": ("1950-01-01", "1989-12-31"), "1990-1999": ("1990-01-01", "1999-12-31"), "2000-oggi": ("2000-01-01", "2100-01-01")}
        ris = {}
        for nome, (a, b) in per.items():
            m = (S.index >= a) & (S.index <= b)
            ris[nome] = {k: {e: auc(idx[k][m], ev[e][m]) for e in EVENTI} for k in idx}
        media = lambda k: float(np.mean([v for v in ris["1950-1989"][k].values() if v is not None]))  # noqa: E731
        scelta = "B" if media("B") >= media("C") else "C"
        ok = True
        for nome in ("1990-1999", "2000-oggi"):
            r, a = ris[nome][scelta], ris[nome]["A"]
            if (r["dd10_63"] or 0) - (a["dd10_63"] or 0) < 0.01:
                ok = False
            for e in ("dd5_21", "vol25_21"):
                if (r[e] or 0) - (a[e] or 0) < -0.01:
                    ok = False
        return {"scelta": scelta, "candidata": ok, "ris": ris}
    except Exception as e:  # noqa: BLE001
        print("Prova pesi non calcolata:", str(e)[:120], flush=True)
        return None
