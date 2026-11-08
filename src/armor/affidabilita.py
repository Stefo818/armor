"""Indice di affidabilità (PIANO ARMOR 3, Fase 4): nessun punteggio con pesi inventati, ma cinque segnali con soglie fissate prima e mostrati uno per uno.

| Segnale | Quando si accende |
| Disaccordo | |sfidante − A1| ≥ 5 punti e rapporto ≥ 2 su una soglia principale |
| Dati vecchi | qualche serie chiave rossa in salute.py |
| Situazione mai vista | distanza di Mahalanobis dello stato di oggi (variabili di A1 + VIX + spread BAA + curva 10Y-3M) oltre il 99° percentile della storia di addestramento |
| Errori recenti | Brier delle ultime previsioni scadute nel diario peggiore della frequenza storica (solo con almeno 12 finestre scadute non sovrapposte) |
| Instabilità | la probabilità cambia di oltre 3 punti stimando il GARCH su finestre diverse (dal 1950, dal 1990, ultimi 15 anni) |
Livello: 0 segnali accesi = alta; 1 = media; 2 o più = bassa, con l'avviso «stima poco affidabile: …». Un segnale non valutabile (None) non conta."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import fhs, store
from .config import DATA, FEATURES, HORIZONS, PRIMARY
from .features import fwd_maxdd, price_features

FILE = DATA / "affidabilita.json"
SOGLIA_INSTABILITA = 0.03
PERCENTILE_NUOVO = 0.99
MIN_FINESTRE = 12
LIVELLI = {0: "alta", 1: "media"}
NOMI = {"disaccordo": "Disaccordo tra i modelli", "dati": "Dati non aggiornati", "mai_visto": "Situazione mai vista", "errori": "Errori recenti", "instabilita": "Stima instabile"}


ETICHETTA_HZ = {"10g": "10 giorni", "1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi"}


def _a1(hz: str, r: dict) -> float:
    """Probabilità principale di A1 (se un altro motore fosse adottato, A1 resta in p_a1)."""
    return float((r.get("p_a1") or r["p"])[PRIMARY[hz]])


def segnale_disaccordo(pred: dict) -> dict:
    acceso = [hz for hz, r in pred.items() if (r.get("sfidante") or {}).get("div")]
    if not any("sfidante" in r for r in pred.values()):
        return {"id": "disaccordo", "acceso": None, "dettaglio": "sfidante non calcolato oggi"}
    det = "; ".join(f"{ETICHETTA_HZ.get(hz, hz)}: calo ≥{PRIMARY[hz]}% → A1 {_a1(hz, pred[hz]):.0%}, sfidante {pred[hz]['sfidante']['p'][PRIMARY[hz]]:.0%}" for hz in acceso) if acceso else "i due modelli sono d'accordo"
    return {"id": "disaccordo", "acceso": bool(acceso), "dettaglio": det}


def segnale_dati(rows: list[dict]) -> dict:
    rosse = [r["name"] for r in rows if r["light"] == "ba"]
    return {"id": "dati", "acceso": bool(rosse), "dettaglio": (", ".join(rosse[:5]) + ("…" if len(rosse) > 5 else "")) if rosse else "tutte le serie chiave sono regolari"}


def stato_variabili(p: pd.Series) -> pd.DataFrame:
    f = price_features(p)[FEATURES]
    ex = pd.DataFrame({"vix": store.load("vix"), "baa10y": store.load("baa10y"), "t10y3m": store.load("t10y3m")})
    ex = ex.reindex(f.index).ffill(limit=7)
    return pd.concat([f, ex], axis=1).dropna()


def mahalanobis(X: pd.DataFrame, x: np.ndarray) -> tuple[float, float, int]:
    """(distanza di oggi, soglia al 99° percentile delle distanze storiche, numero di date). Covarianza con piccola regolarizzazione."""
    A = X.values
    mu = A.mean(axis=0)
    C = np.cov(A, rowvar=False) + 1e-9 * np.eye(A.shape[1])
    Ci = np.linalg.inv(C)
    d = np.sqrt(np.einsum("ij,jk,ik->i", A - mu, Ci, A - mu))
    d0 = float(np.sqrt((x - mu) @ Ci @ (x - mu)))
    return d0, float(np.quantile(d, PERCENTILE_NUOVO)), len(A)


def segnale_mai_visto(p: pd.Series, t) -> dict:
    try:
        S = stato_variabili(p[p.index <= t])
        if len(S) < 1000 or S.index[-1] != pd.Timestamp(t):
            return {"id": "mai_visto", "acceso": None, "dettaglio": "variabili di oggi non tutte disponibili"}
        d0, soglia, n = mahalanobis(S.iloc[:-1], S.iloc[-1].values)
        return {"id": "mai_visto", "acceso": bool(d0 > soglia), "dettaglio": f"distanza dalla norma {d0:.1f}, limite {soglia:.1f} (superato solo dall'1% dei {n} giorni di storia)", "valore": d0, "soglia": soglia}
    except Exception as e:  # noqa: BLE001
        return {"id": "mai_visto", "acceso": None, "dettaglio": "non calcolabile: " + str(e)[:60]}


def segnale_errori(diario: pd.DataFrame, p: pd.Series, orizzonte: str = "1m", modello: str | None = None) -> dict:
    """Brier delle previsioni scadute del diario (una per finestra non sovrapposta) contro quello della frequenza storica. Serve un minimo di finestre."""
    n = HORIZONS[orizzonte]
    d = diario[diario["horizon"] == orizzonte].copy()
    if modello:
        d = d[d["model"].str.startswith(modello)]
    d = d.drop_duplicates("asof").sort_values("asof")
    dd = fwd_maxdd(p, n)
    pos = pd.Series(np.arange(len(p)), index=p.index)
    sel, last = [], -10 ** 9
    for r in d.itertuples():
        a = pd.Timestamp(r.asof)
        if a not in p.index or pd.isna(dd.get(a, np.nan)):
            continue
        if pos[a] - last >= n:
            sel.append((float(r.p1), float(r.base1), float(dd[a] <= -float(r.thr1) / 100)))
            last = pos[a]
    if len(sel) < MIN_FINESTRE:
        return {"id": "errori", "acceso": None, "dettaglio": f"non ancora valutabile: servono {MIN_FINESTRE} previsioni a 1 mese già verificate e indipendenti, ce ne sono {len(sel)} (ne maturano circa una al mese)", "finestre": len(sel)}
    a = np.array(sel)
    bp, bb = float(np.mean((a[:, 0] - a[:, 2]) ** 2)), float(np.mean((a[:, 1] - a[:, 2]) ** 2))
    return {"id": "errori", "acceso": bool(bp > bb), "dettaglio": f"errore medio {bp:.4f} contro {bb:.4f} di chi indovina sempre la frequenza storica, su {len(sel)} previsioni verificate", "finestre": len(sel)}


def segnale_instabilita(p: pd.Series, t, vix: float | None = None) -> dict:
    """Probabilità principale a 1 e 3 mesi (simulazione GARCH) stimando i parametri su tre finestre di storia diverse."""
    try:
        pp = p[p.index <= t]
        seed = int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31)
        inizi = {"dal 1950": "1950-01-01", "dal 1990": "1990-01-01", "ultimi 15 anni": str((pd.Timestamp(t) - pd.DateOffset(years=15)).date())}
        ris = {}
        for nome, da in inizi.items():
            f = fhs.forecast(pp, sims=3000, seed=seed, fit_start=da)
            ris[nome] = {hz: float(f[hz]["down"][PRIMARY[hz]]["p"]) for hz in ("1m", "3m")}
        spread = {hz: max(v[hz] for v in ris.values()) - min(v[hz] for v in ris.values()) for hz in ("1m", "3m")}
        peggio = max(spread, key=spread.get)
        return {"id": "instabilita", "acceso": bool(spread[peggio] > SOGLIA_INSTABILITA),
                "dettaglio": f"a {peggio.replace('1m', '1 mese').replace('3m', '3 mesi')} la probabilità va da {min(v[peggio] for v in ris.values()):.0%} a {max(v[peggio] for v in ris.values()):.0%} a seconda di quanta storia si usa per stimare il modello (dal 1950, dal 1990, ultimi 15 anni)",
                "per_finestra": ris}
    except Exception as e:  # noqa: BLE001
        return {"id": "instabilita", "acceso": None, "dettaglio": "non calcolabile: " + str(e)[:60]}


def livello(segnali: list[dict]) -> dict:
    accesi = [s for s in segnali if s["acceso"]]
    n = len(accesi)
    lv = LIVELLI.get(n, "bassa")
    avviso = ("Stima poco affidabile: " + "; ".join(f"{NOMI[s['id']].lower()} ({s['dettaglio']})" for s in accesi) + ".") if n >= 2 else ""
    return {"livello": lv, "n_accesi": n, "avviso": avviso}


def orizzonti(pred: dict) -> list[dict]:
    """Per ogni orizzonte: probabilità di A1, dello sfidante (se c'è) e frequenza storica «normale», sulla soglia principale."""
    out = []
    for hz in ("10g", "1m", "3m", "6m"):
        r = pred.get(hz)
        if not r:
            continue
        try:
            thr = PRIMARY[hz]
            sf = (r.get("sfidante") or {}).get("p", {}).get(thr)
            out.append({"hz": hz, "soglia": thr, "a1": _a1(hz, r), "sfidante": None if sf is None else float(sf), "normale": float(r["base"][thr])})
        except Exception:  # noqa: BLE001
            continue
    return out


def calcola(pred: dict, p: pd.Series, t, diario: pd.DataFrame | None = None, salute_rows: list[dict] | None = None, scrivi: bool = True) -> dict:
    from . import journal, salute
    segnali = [segnale_disaccordo(pred), segnale_dati(salute_rows if salute_rows is not None else salute.compute()), segnale_mai_visto(p, t),
               segnale_errori(diario if diario is not None else journal.read(), p), segnale_instabilita(p, t)]
    out = {"asof": str(pd.Timestamp(t).date()), "segnali": segnali, **livello(segnali), "orizzonti": orizzonti(pred)}
    if scrivi:
        FILE.write_text(json.dumps(out, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    return out


SPIEGA = {
    "disaccordo": ("Il modello ufficiale (A1, guarda i prezzi passati) e lo sfidante (guarda anche la volatilità di oggi e il VIX) danno risposte molto diverse.",
                   "Quando sono lontani, la verità sta in un intervallo ampio: usa la fascia tra i due numeri, non uno solo."),
    "dati": ("Controlla che le serie usate dal modello (prezzi, VIX, spread, ecc.) siano aggiornate.", "Se acceso, il numero può essere basato su dati vecchi."),
    "mai_visto": ("Misura quanto le condizioni di oggi assomigliano a quelle già viste dal 1990.", "Se acceso, il modello non ha esempi simili e la stima vale meno."),
    "errori": ("Confronta le previsioni passate del diario con ciò che è successo davvero.", "Serve tempo per avere abbastanza previsioni verificate."),
    "instabilita": ("Rifà il calcolo usando periodi di storia diversi: se il risultato cambia molto, dipende dalle scelte e non solo dal mercato.",
                    "Se acceso, considera il numero come un ordine di grandezza."),
}
GUIDA = {
    "alta": ("Stima affidabile", "ok", "I modelli concordano e non c'è nulla di anomalo. Il numero è una buona guida, nei limiti di ogni previsione: indica quanto è probabile un calo, non quando arriva.",
             "Leggi la probabilità e confrontala con il «normale». Nessuna azione richiesta."),
    "media": ("Stima da leggere con cautela", "warn", "Un segnale di attenzione è acceso. Il numero è utile come ordine di grandezza, non come valore preciso.",
              "Guarda la fascia tra i due modelli invece del singolo numero e controlla quale segnale è acceso."),
    "bassa": ("Stima poco affidabile oggi", "bad", "Più segnali sono accesi: oggi il numero è incerto, non necessariamente il mercato è in pericolo. Non è un allarme di crollo, è un avviso che la stima ha un margine d'errore ampio.",
              "Usa la fascia «da … a …» di ogni orizzonte qui sotto. Il PAC non si decide su questo numero: Armor non dà indicazioni di acquisto o vendita."),
}


def _lettura(o: dict) -> str:
    """Una frase per orizzonte: fascia tra i modelli e confronto con il normale."""
    vals = [v for v in (o["a1"], o["sfidante"]) if v is not None]
    lo, hi = min(vals), max(vals)
    n = o["normale"]
    fascia = f"{lo:.0%}" if abs(hi - lo) < 0.005 else f"da {lo:.0%} a {hi:.0%}"
    if n > 0:
        r1, r2 = lo / n, hi / n
        conf = (f"{r1:.1f}× il normale" if abs(r2 - r1) < 0.1 else f"da {r1:.1f}× a {r2:.1f}× il normale").replace(".", ",")
    else:
        conf = ""
    return fascia, conf


def html() -> str:
    try:
        a = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    titolo, cls, cosa, muovi = GUIDA[a["livello"]]
    e = _h.escape
    out = [f"<div class='card'><div class='hzh'><h3 style='margin:0'>Quanto fidarsi della stima di oggi</h3><span class='badge {cls}'>{e(titolo)}</span></div>",
           f"<p style='margin:10px 0 4px'><b>In breve.</b> {e(cosa)}</p>",
           f"<p style='margin:4px 0 10px'><b>Come muoverti.</b> {e(muovi)}</p>"]
    ori = a.get("orizzonti") or []
    if ori:
        out.append("<div class='mu' style='margin:8px 0 4px'><b>Cosa aspettarti, orizzonte per orizzonte</b> — probabilità di un calo almeno pari alla soglia. A1 = modello ufficiale, sfidante = modello in prova (FHS+VIX), «normale» = quanto succede in media nella storia</div>")
        for o in ori:
            fascia, conf = _lettura(o)
            doppio = o["sfidante"] is not None and abs(o["a1"] - o["sfidante"]) >= 0.005
            dett = (f"A1 {o['a1']:.0%} · sfidante {o['sfidante']:.0%} · normale {o['normale']:.0%}" if doppio else f"A1 {o['a1']:.0%} · normale {o['normale']:.0%}")
            out.append(f"<div style='border-top:1px solid rgba(128,128,128,.25);padding:6px 0'><b>{e(ETICHETTA_HZ[o['hz']])}, calo ≥{o['soglia']}%:</b> {e(fascia)}"
                       f"{' (' + e(conf) + ')' if conf else ''}<div class='mu'>{e(dett)}</div></div>")
    out.append("<div class='mu' style='margin:10px 0 4px'><b>Perché</b> — i cinque controlli (acceso = attenzione)</div>")
    for sg in a["segnali"]:
        st = {True: ("bad", "acceso"), False: ("ok", "spento"), None: ("warn", "in attesa")}[sg["acceso"]]
        cosa_s, se_acceso = SPIEGA[sg["id"]]
        if sg["id"] == "disaccordo" and sg["acceso"]:
            sg = {**sg, "dettaglio": f"su {sg['dettaglio'].count('→')} orizzonti su 4 i due modelli sono lontani (vedi sopra)"}
        out.append(f"<div style='border-top:1px solid rgba(128,128,128,.25);padding:6px 0'><span class='badge {st[0]}'>{st[1]}</span> <b>{e(NOMI[sg['id']])}</b>"
                   f"<div>{e(sg['dettaglio'][:1].upper() + sg['dettaglio'][1:])}.</div><div class='mu'>{e(cosa_s)} {e(se_acceso) if sg['acceso'] else ''}</div></div>")
    out.append("<details style='margin-top:8px'><summary class='mu'><b>Come leggere questi numeri</b></summary>"
               "<p class='mu'>La probabilità è una frequenza, non una promessa: «11%» vuol dire che in situazioni come questa, in 100 casi, circa 11 hanno avuto quel calo. "
               "Il «normale» è la frequenza media storica: oltre 1× il rischio è sopra la media, sotto 1× è sotto. "
               "L'affidabilità non misura se il mercato salirà o scenderà: misura quanto ci si può fidare del calcolo di oggi. "
               "Livello alto = 0 controlli accesi, medio = 1, basso = 2 o più; un controllo «in attesa» non conta. Non è consulenza finanziaria.</p></details></div>")
    return "".join(out)
