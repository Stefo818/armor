"""Semaforo del rischio di calo (Patch 60b), a 5 stati, senza cambiare i numeri dei modelli.
Per ogni data si confrontano le probabilità di calo di A1 e di FHS+VIX con la frequenza storica normale:
  rapporto = probabilità del modello / frequenza storica (1 = rischio normale, 2 = il doppio del normale).
Si usano due bersagli: calo di almeno 5% entro 1 mese e di almeno 10% entro 3 mesi; il rapporto è la media dei due e dei due modelli.
Colori (soglie fissate qui, prima di guardare i risultati):
  Verde < 0,8 · Giallo 0,8-1,3 · Arancione 1,3-2,0 · Rosso >= 2,0
  Grigio = i due modelli non concordano (i loro rapporti differiscono di oltre il 60% del valore medio): meglio non fidarsi del colore.
Precedenza se più condizioni valgono: Grigio, poi Rosso, Arancione, Giallo, Verde.
Isteresi: il colore mostrato cambia solo dopo 3 sedute consecutive con lo stesso nuovo colore, tranne Grigio e Rosso che scattano subito (prudenza).
La tabella storica dice cosa è successo davvero dopo ogni colore (dal 1990); non è una promessa per il futuro."""
import json

import numpy as np
import pandas as pd

from .config import DATA

FILE = DATA / "semaforo_rischio_tabella.json"
STATO = DATA / "semaforo_rischio_stato.csv"
BERSAGLI = (("1m", 5), ("3m", 10))
SOGLIE = (0.8, 1.3, 2.0)
DISACCORDO = 0.6
ISTERESI = 3
COLORI = ("Verde", "Giallo", "Arancione", "Rosso", "Grigio")
SPIEGA = {
    "Verde": "Rischio di calo sotto il normale.",
    "Giallo": "Rischio di calo nella norma o appena sopra.",
    "Arancione": "Rischio di calo chiaramente sopra il normale.",
    "Rosso": "Rischio di calo almeno doppio del normale.",
    "Grigio": "I due modelli non sono d'accordo: il colore non è affidabile, guarda i numeri.",
}


def colore(r_a: float, r_f: float) -> str:
    """Colore dai due rapporti (modello / normale), con la precedenza Grigio > Rosso > Arancione > Giallo > Verde."""
    m = (r_a + r_f) / 2
    if m > 0 and abs(r_a - r_f) / m >= DISACCORDO:
        return "Grigio"
    if m >= SOGLIE[2]:
        return "Rosso"
    if m >= SOGLIE[1]:
        return "Arancione"
    if m >= SOGLIE[0]:
        return "Giallo"
    return "Verde"


def mostrato(grezzi: list[str], precedente: str | None) -> str:
    """Colore da mostrare dopo l'ultima seduta: isteresi di 3 sedute; Grigio e Rosso subito."""
    if not grezzi:
        return precedente or "Grigio"
    ult = grezzi[-1]
    if precedente is None or ult in ("Grigio", "Rosso"):
        return ult
    if len(grezzi) >= ISTERESI and len(set(grezzi[-ISTERESI:])) == 1:
        return ult
    return precedente


def _rapporti(pa: dict, pf: dict, base: dict) -> tuple[float, float] | None:
    ra, rf = [], []
    for hz, thr in BERSAGLI:
        try:
            b = float(base[hz][thr])
            ra.append(float(pa[hz][thr]) / b)
            rf.append(float(pf[hz][thr]) / b)
        except Exception:  # noqa: BLE001
            return None
    return float(np.mean(ra)), float(np.mean(rf))


def _get(d, k):
    return d.get(k, d.get(str(k)))


def oggi_da_pred(pred: dict) -> dict | None:
    """Dai risultati di forecast(): pred[hz]['p'] (o 'p_a1'), pred[hz]['sfidante']['p'], pred[hz]['base']."""
    pa, pf, base = {}, {}, {}
    for hz, thr in BERSAGLI:
        r = pred.get(hz)
        if not r or not r.get("sfidante"):
            return None
        a = r.get("p_a1") or r["p"]
        pa.setdefault(hz, {})[thr] = _get(a, thr)
        pf.setdefault(hz, {})[thr] = _get(r["sfidante"]["p"], thr)
        base.setdefault(hz, {})[thr] = _get(r["base"], thr)
    rr = _rapporti(pa, pf, base)
    if not rr:
        return None
    return {"r_a1": rr[0], "r_fhs": rr[1], "grezzo": colore(*rr),
            "p": {f"{hz}_{thr}": {"A1": float(pa[hz][thr]), "FHS+VIX": float(pf[hz][thr]), "normale": float(base[hz][thr])} for hz, thr in BERSAGLI}}


def stato_storia() -> pd.DataFrame:
    try:
        return pd.read_csv(STATO)
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["data", "grezzo", "mostrato", "r_a1", "r_fhs"])


def registra(data: str, oggi: dict) -> dict:
    """Aggiorna lo stato (una riga per data) e restituisce il colore mostrato con isteresi."""
    s = stato_storia()
    s = s[s["data"].astype(str) != data]
    graz = list(s["grezzo"]) + [oggi["grezzo"]]
    prec = s["mostrato"].iloc[-1] if len(s) else None
    m = mostrato(graz, prec)
    riga = {"data": data, "grezzo": oggi["grezzo"], "mostrato": m, "r_a1": round(oggi["r_a1"], 3), "r_fhs": round(oggi["r_fhs"], 3)}
    pd.concat([s, pd.DataFrame([riga])], ignore_index=True).to_csv(STATO, index=False)
    return {**oggi, "data": data, "mostrato": m, "giorni_stesso_colore": _serie(graz, m)}


def _serie(graz, m):
    n = 0
    for c in reversed(graz):
        if c == m:
            n += 1
        else:
            break
    return n


def tabella_storica(p: pd.Series, pr: dict) -> dict:
    """Cosa è successo dopo ogni colore: frequenza dei cali, confrontata con quella di tutte le date."""
    from . import modeleval
    ser = {}
    for hz, thr in BERSAGLI:
        a = pr["A1"][(pr["A1"].hz == hz) & (pr["A1"].thr == thr)].set_index("date")["p"]
        f = pr["FHS+VIX"][(pr["FHS+VIX"].hz == hz) & (pr["FHS+VIX"].thr == thr)].set_index("date")["p"]
        idx = a.index.intersection(f.index)
        ser[(hz, thr)] = (a.loc[idx], f.loc[idx], modeleval.purged_base(p, idx, hz, "down", thr).reindex(idx),
                          modeleval.outcome(p, idx, hz, "down", thr).reindex(idx))
    comuni = None
    for v in ser.values():
        comuni = v[3].dropna().index if comuni is None else comuni.intersection(v[3].dropna().index)
    for v in ser.values():
        comuni = comuni.intersection(v[2].dropna().index)
    ra = np.mean([(v[0].loc[comuni] / v[2].loc[comuni]).values for v in ser.values()], axis=0)
    rf = np.mean([(v[1].loc[comuni] / v[2].loc[comuni]).values for v in ser.values()], axis=0)
    col = np.array([colore(a, b) for a, b in zip(ra, rf)])
    anni = comuni.year.values
    righe = []
    for c in COLORI:
        m = col == c
        if m.sum() < 5:
            righe.append({"colore": c, "n": int(m.sum())})
            continue
        r = {"colore": c, "n": int(m.sum()), "quota": float(m.mean())}
        for (hz, thr), v in ser.items():
            y = v[3].loc[comuni].values.astype(float)
            pm = ((v[0].loc[comuni].values + v[1].loc[comuni].values) / 2)
            k = f"{hz}_{thr}"
            r[k] = {"freq": float(y[m].mean()), "freq_tutte": float(y.mean()), "p_media": float(pm[m].mean()),
                    "freq_2000_12": float(y[m & (anni >= 2000) & (anni < 2013)].mean()) if (m & (anni >= 2000) & (anni < 2013)).sum() >= 5 else None,
                    "freq_2013_26": float(y[m & (anni >= 2013)].mean()) if (m & (anni >= 2013)).sum() >= 5 else None}
        righe.append(r)
    ordine = [r for r in righe if r["colore"] != "Grigio" and "quota" in r]
    mono = {}
    for hz, thr in BERSAGLI:
        k = f"{hz}_{thr}"
        f = [r[k]["freq"] for r in ordine]
        mono[k] = bool(all(f[i] <= f[i + 1] + 1e-9 for i in range(len(f) - 1)))
    return {"righe": righe, "monotona": mono, "da": str(comuni.min().date()), "a": str(comuni.max().date()), "n": int(len(comuni))}


def run(cache: str | None = None, log=print) -> dict:
    from . import taratura
    from .features import closed_sp500
    from . import store
    p = closed_sp500()
    try:
        vix = store.load("vix")
    except Exception:  # noqa: BLE001
        vix = None
    pr = taratura.predizioni(p, vix, cache=cache, log=log)
    t = tabella_storica(p, pr)
    t["data"] = str(p.index[-1].date())
    try:   # storia dei rapporti col normale: serve al pilastro «previsione» del Super Armor Index
        from . import super_armor
        super_armor.salva_prev_storia(p, pr)
    except Exception as e:  # noqa: BLE001
        log("[super armor] storia della previsione non salvata: " + str(e)[:80])
    FILE.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    return t


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


OGGI = DATA / "semaforo_rischio_oggi.json"


def aggiorna(pred: dict, data: str) -> dict | None:
    """Chiamata ogni giorno da jobs.tutto con le previsioni di oggi: calcola, applica l'isteresi e salva."""
    o = oggi_da_pred(pred)
    if not o:
        return None
    r = registra(data, o)
    OGGI.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


def variazione() -> dict | None:
    """Di quanto è cambiato il rapporto (rischio stimato / rischio normale) rispetto al giorno registrato prima. None finché non ci sono due giorni."""
    try:
        d = pd.read_csv(STATO).drop_duplicates("data", keep="last").sort_values("data")
        if len(d) < 2:
            return None
        a, b = d.iloc[-2], d.iloc[-1]
        m1, m0 = (b["r_a1"] + b["r_fhs"]) / 2, (a["r_a1"] + a["r_fhs"]) / 2
        return {"da": str(a["data"]), "a": str(b["data"]), "medio": float(m1), "d_medio": float(m1 - m0), "p_medio": float((m1 / m0 - 1) * 100) if m0 else None,
                "d_a1": float(b["r_a1"] - a["r_a1"]), "d_fhs": float(b["r_fhs"] - a["r_fhs"])}
    except Exception:  # noqa: BLE001
        return None


def variazione_html() -> str:
    v = variazione()
    f = lambda x, d=2: f"{x:+.{d}f}".replace(".", ",")
    if not v:
        return ("<p class='sai-t2'><b>Variazione rispetto a ieri:</b> non ancora disponibile. Il rapporto viene registrato ogni giorno: "
                "la prima variazione compare dal secondo giorno registrato.</p>")
    fr = "▲ in aumento" if v["d_medio"] > 0.005 else ("▼ in calo" if v["d_medio"] < -0.005 else "= invariato")
    pc = "" if v["p_medio"] is None else f" ({f(v['p_medio'], 1)}%)"
    return (f"<p class='sai-t2'><b>Variazione rispetto al giorno precedente ({v['da'][8:]}/{v['da'][5:7]}):</b> {fr}. Rapporto medio {f(v['d_medio'])} volte{pc}; "
            f"modello base {f(v['d_a1'])}, modello con la paura {f(v['d_fhs'])}. Un aumento vuol dire che il rischio stimato di calo cresce rispetto al normale.</p>")


def _pc(x):
    return f"{x * 100:.0f}%" if x is not None else "n.d."


def html() -> str:
    from html import escape as e
    try:
        o = json.loads(OGGI.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        o = None
    t = carica()
    css = {"Verde": "ok", "Giallo": "wa", "Arancione": "or", "Rosso": "ba", "Grigio": "nd"}
    from . import previsione_ui
    out = ["<div class='explain'><p><b>Che cos'è.</b> Il semaforo risponde a una domanda: oggi è più o meno probabile del solito un calo importante della Borsa americana? "
           "Due modelli stimano la probabilità e il colore riassume la loro media. Non è un segnale per comprare o vendere.</p></div>", previsione_ui.html(o, t, variazione())]
    try:
        from . import semaforo_mercati
        out.append(semaforo_mercati.html())
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import candidati
        out.append("<h4>Altri indicatori in prova (peso zero)</h4>" + candidati.html())
    except Exception:  # noqa: BLE001
        pass
    return "".join(out)
