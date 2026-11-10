"""Super Armor Index (Patch 64): un numero da 1 (mercato sano) a 100 (mercato pericoloso e instabile) che riassume 5 grandi indicatori.
Pilastri (ognuno da 1 a 100, 100 = pericolo) e pesi FISSI, scritti prima di guardare i risultati:
  previsione 30 (quanto è alto il rischio di calo rispetto al normale, da due modelli: posizione di oggi dentro la storia 1990-oggi)
  Indice Armor 25 · economia reale 25 (8 misure: lavoro, produzione, vendite, fiducia, curva dei tassi...) · paura e opzioni 20 (VIX, sua curva, VVIX, SKEW, put/call)
  grandi fondi 0 (nessun loro segnale ha ancora dimostrato di anticipare i cali: prende peso, 10, solo se supera la prova di grandi_fondi.py).
I pesi dei pilastri mancanti si ridistribuiscono sugli altri. L'Indice Armor contiene già in parte la paura: il doppio conteggio è dichiarato, per questo la paura pesa meno.
Fasce: 1-25 sano · 25-40 tranquillo · 40-55 attenzione · 55-70 teso · 70-100 pericoloso e instabile.
Storia: ricostruita dal 2000 con le regole di oggi (il pilastro «previsione» è quello vero walk-forward dei modelli); da qui in avanti ogni giorno si registra il valore reale.
Prova: data/super_armor_prova.json dice quanto spesso, dopo ogni fascia, è arrivato un calo (S&P 500, dal 2000)."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import store
from .config import ARCHIVE, DATA

STORIA = DATA / "super_armor_storia.csv"
PREV = DATA / "super_armor_prev_storia.csv"
PROVA = DATA / "super_armor_prova.json"
PESI = {"previsione": 30.0, "armor": 25.0, "economia": 25.0, "vix": 20.0, "fondi": 0.0}
NOMI = {"previsione": "Previsione", "armor": "Indice Armor", "vix": "Paura e opzioni", "fondi": "Grandi fondi", "economia": "Economia reale"}
FASCE = [(25, "Sano", "Mercato sano"), (40, "Tranquillo", "Mercato tranquillo"), (55, "Attenzione", "Zona di attenzione"), (70, "Teso", "Mercato teso"), (101, "Pericoloso", "Mercato pericoloso e instabile")]
COL_PIL = {"previsione": "hsl(215,85%,62%)", "armor": "hsl(265,75%,68%)", "vix": "hsl(35,90%,55%)", "economia": "hsl(165,60%,45%)", "fondi": "hsl(0,0%,60%)"}


def _n(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def fascia(v: float) -> int:
    for i, (lim, *_r) in enumerate(FASCE):
        if v < lim:
            return i
    return len(FASCE) - 1


def colore(v: float) -> str:
    """Verde-giallo-arancio-rosso ancorato al centro di ogni fascia, così il colore dell'etichetta coincide con quello della fascia."""
    h = float(np.interp(v, [12, 32, 47, 62, 85], [125, 92, 52, 24, 0]))
    return f"hsl({h:.0f},74%,45%)"


def _lin(x, xp, fp):
    x = pd.Series(x) if not isinstance(x, pd.Series) else x
    return pd.Series(np.interp(x.values, xp, fp), index=x.index).where(x.notna())


def _media(comp: pd.DataFrame, w: dict, minimo: int = 1) -> pd.Series:
    ww = pd.Series(w).reindex(comp.columns)
    ok = comp.notna()
    den = (ok * ww).sum(axis=1)
    num = (comp.fillna(0) * ww).sum(axis=1)
    return (num / den).where(ok.sum(axis=1) >= minimo)


def _asof(s: pd.Series, idx: pd.DatetimeIndex, lag: int, tol: int = 120) -> pd.Series:
    s = s.dropna().copy()
    s.index = s.index + pd.Timedelta(days=lag)   # data in cui il dato era davvero noto
    return s.reindex(s.index.union(idx)).ffill().reindex(idx).where(lambda x: x.index >= s.index[0])


# ---------------- pilastri ----------------
ECO = {   # chiave: (nome semplice, ritardo di pubblicazione in giorni)
    "sahm": ("disoccupazione in aumento (indicatore di Sahm)", 40), "icsa": ("richieste di sussidio di disoccupazione", 5), "indpro": ("produzione industriale", 45),
    "cfnai": ("attività economica nazionale (indice di Chicago)", 45), "t10y3m": ("curva dei tassi (titoli a 10 anni contro 3 mesi)", 1), "payems": ("posti di lavoro", 37),
    "retail": ("vendite al dettaglio", 45), "umcsent": ("fiducia dei consumatori", 20)}


def eco_componenti(idx: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rischio 0-1, valore grezzo) per ognuna delle 8 misure dell'economia reale, con i ritardi di pubblicazione."""
    risk, raw = {}, {}

    def put(k, v, xp, fp):
        raw[k] = v
        risk[k] = _lin(v, xp, fp)
    try:
        s = _asof(store.load("sahm"), idx, ECO["sahm"][1]); put("sahm", s, [0.0, 0.5, 1.0], [0.0, 0.85, 1.0])
    except Exception:  # noqa: BLE001
        pass
    try:
        c = store.load("icsa").dropna()
        m4 = c.rolling(4).mean()
        r = m4 / m4.rolling(52).min()
        put("icsa", _asof(r, idx, ECO["icsa"][1], 30), [1.05, 1.35], [0.0, 1.0])
    except Exception:  # noqa: BLE001
        pass
    for k, per, xp, fp in (("indpro", 12, [-3.0, 3.0], [1.0, 0.0]), ("payems", 12, [-0.5, 1.8], [1.0, 0.0]), ("retail", 12, [-1.0, 5.0], [1.0, 0.0])):
        try:
            y = store.load(k).dropna().pct_change(per) * 100
            put(k, _asof(y.dropna(), idx, ECO[k][1]), xp, fp)
        except Exception:  # noqa: BLE001
            pass
    try:
        put("cfnai", _asof(store.load("cfnai").dropna().rolling(3).mean(), idx, ECO["cfnai"][1]), [-0.8, 0.1], [1.0, 0.0])
    except Exception:  # noqa: BLE001
        pass
    try:
        put("t10y3m", _asof(store.load("t10y3m"), idx, ECO["t10y3m"][1], 10), [-0.8, 1.0], [1.0, 0.0])
    except Exception:  # noqa: BLE001
        pass
    try:
        put("umcsent", _asof(store.load("umcsent"), idx, ECO["umcsent"][1]), [50.0, 95.0], [1.0, 0.0])
    except Exception:  # noqa: BLE001
        pass
    return pd.DataFrame(risk, index=idx), pd.DataFrame(raw, index=idx)


def serie_economia(idx) -> pd.Series:
    r, _ = eco_componenti(idx)
    m = _media(r, {k: 1.0 for k in r.columns}, minimo=4)
    return 1 + 99 * m


def vix_componenti(idx: pd.DatetimeIndex) -> pd.DataFrame:
    out = {}
    v = store.load("vix").reindex(idx, method="ffill")
    out["vix"] = _lin(v, [13, 20, 30, 45], [0, .35, .8, 1])
    try:
        v3 = store.load("vix3m").reindex(idx, method="ffill")
        out["curva"] = _lin(v3 / v, [0.85, 0.95, 1.05, 1.2], [1, .75, .3, 0]).where(v3.notna())
    except Exception:  # noqa: BLE001
        pass
    for k, sid, xp, fp in (("vvix", "vvix", [75, 95, 130], [0, .4, 1]), ("skew", "skew", [118, 135, 150], [0, .4, 1])):
        try:
            out[k] = _lin(store.load(sid).reindex(idx, method="ffill"), xp, fp)
        except Exception:  # noqa: BLE001
            pass
    return pd.DataFrame(out, index=idx)
VIXW = {"vix": .40, "curva": .25, "vvix": .10, "skew": .05, "putcall": .20}


def serie_vix(idx) -> pd.Series:
    return 1 + 99 * _media(vix_componenti(idx), VIXW)


def putcall_rischio() -> tuple[float | None, float | None]:
    """(rischio 0-1, percentile) dal put/call sulle posizioni aperte, solo se ci sono almeno 60 giorni di archivio."""
    try:
        d = pd.read_csv(ARCHIVE / "spy_options_summary.csv").dropna(subset=["pc_open_interest"])
        if len(d) < 60:
            return None, None
        pct = float((d["pc_open_interest"] < d["pc_open_interest"].iloc[-1]).mean() * 100)
        return float(np.interp(pct, [20, 50, 90], [0.1, 0.4, 1.0])), pct
    except Exception:  # noqa: BLE001
        return None, None


def rapporti_storici(p: pd.Series, pr: dict) -> pd.DataFrame:
    """Rapporto modello/normale per ogni data di prova (stessa definizione del semaforo del rischio)."""
    from . import modeleval
    from .semaforo_rischio import BERSAGLI
    ra, rf = [], []
    for hz, thr in BERSAGLI:
        a = pr["A1"][(pr["A1"].hz == hz) & (pr["A1"].thr == thr)].set_index("date")["p"]
        f = pr["FHS+VIX"][(pr["FHS+VIX"].hz == hz) & (pr["FHS+VIX"].thr == thr)].set_index("date")["p"]
        idx = a.index.intersection(f.index)
        b = modeleval.purged_base(p, idx, hz, "down", thr).reindex(idx)
        ra.append((a.loc[idx] / b).rename(f"{hz}_{thr}")); rf.append((f.loc[idx] / b).rename(f"{hz}_{thr}"))
    A, F = pd.concat(ra, axis=1).dropna(), pd.concat(rf, axis=1).dropna()
    idx = A.index.intersection(F.index)
    d = pd.DataFrame({"r_a1": A.loc[idx].mean(axis=1), "r_fhs": F.loc[idx].mean(axis=1)})
    d["ratio"] = d.mean(axis=1)
    return d


def salva_prev_storia(p: pd.Series, pr: dict) -> int:
    d = rapporti_storici(p, pr)
    d.round(4).to_csv(PREV, index_label="date")
    return len(d)


def prev_storia() -> pd.DataFrame | None:
    try:
        return pd.read_csv(PREV, index_col=0, parse_dates=True)
    except Exception:  # noqa: BLE001
        return None


def punteggio_previsione(ratio, ref: np.ndarray) -> float:
    """1-100: quanto il rapporto di oggi è alto dentro tutta la storia dei rapporti (percentile)."""
    return float(1 + 99 * (ref < ratio).mean() + 99 * 0.5 * (ref == ratio).mean())


def serie_previsione(idx) -> pd.Series | None:
    d = prev_storia()
    if d is None or d.empty:
        return None
    ref = np.sort(d["ratio"].values)
    sc = pd.Series(1 + 99 * (np.searchsorted(ref, d["ratio"].values, side="left") + 0.5 * (np.searchsorted(ref, d["ratio"].values, side="right") - np.searchsorted(ref, d["ratio"].values, side="left"))) / len(ref), index=d.index)
    return sc.reindex(sc.index.union(idx)).ffill(limit=12).reindex(idx).where(lambda x: x.index >= sc.index[0])


def combina(P: pd.DataFrame, pesi: dict | None = None) -> pd.Series:
    w = pd.Series(pesi or PESI).reindex(P.columns).fillna(0.0)
    ok = P.notna() & (w > 0)
    den = (ok * w).sum(axis=1)
    num = (P.fillna(0) * w).sum(axis=1)
    return (num / den).where(ok.sum(axis=1) >= 3)


def ricostruisci(p: pd.Series, armor_hist: pd.Series, dal: str = "2000-01-03") -> pd.DataFrame:
    idx = p.index[p.index >= dal]
    P = pd.DataFrame({"armor": armor_hist.reindex(idx, method="ffill", limit=5), "economia": serie_economia(idx), "vix": serie_vix(idx)}, index=idx)
    sp = serie_previsione(idx)
    P["previsione"] = sp if sp is not None else np.nan
    try:
        from . import grandi_fondi
        P["fondi"] = grandi_fondi.serie_tensione(idx)
    except Exception:  # noqa: BLE001
        P["fondi"] = np.nan
    P = P[["previsione", "armor", "vix", "economia", "fondi"]]
    P["sai"] = combina(P)
    P["sai_ombra"] = combina(P[["previsione", "armor", "vix", "economia", "fondi"]], {**PESI, "fondi": 10.0}).where(P["fondi"].notna())
    return P.dropna(subset=["sai"]).round(2)


def storia() -> pd.DataFrame | None:
    try:
        return pd.read_csv(STORIA, index_col=0, parse_dates=True)
    except Exception:  # noqa: BLE001
        return None


# ---------------- oggi ----------------
def _fondi_oggi() -> dict:
    try:
        from . import grandi_fondi
        d = grandi_fondi.carica() or {}
    except Exception:  # noqa: BLE001
        d = {}
    sg = d.get("segnali") or {}
    alti = [v["nome"].split(" (")[0] for v in sg.values() if v.get("stato") == "alto"]
    bassi = [v["nome"].split(" (")[0] for v in sg.values() if v.get("stato") == "basso"]
    prov = [k for k, v in sg.items() if str((v.get("prova") or {}).get("verdetto", "")).startswith("dimostrato")]
    return {"n": len(sg), "alti": alti, "bassi": bassi, "dimostrati": prov, "tensione": d.get("tensione")}


def pilastri_oggi(aix: dict | None, p: pd.Series) -> dict:
    """{pilastro: {score, testo, dettagli}} con i dati di oggi."""
    t = p.index[-1]
    idx = pd.DatetimeIndex([t])
    out = {}
    # Indice Armor
    if aix:
        g = sorted([x for x in aix["groups"] if x.get("score") is not None], key=lambda x: -x["score"])
        top = ", ".join(f"{x['name']} ({100 * x['score']:.0f}/100)" if x["score"] <= 1 else f"{x['name']} ({x['score']:.0f}/100)" for x in g[:3])
        out["armor"] = {"score": float(aix["value"]), "testo": f"L'Indice Armor sta a {aix['value']:.0f}/100. Le famiglie più in tensione: {top}." if top else f"L'Indice Armor sta a {aix['value']:.0f}/100."}
    # previsione
    try:
        o = json.loads((DATA / "semaforo_rischio_oggi.json").read_text(encoding="utf-8"))
        d = prev_storia()
        ratio = (o["r_a1"] + o["r_fhs"]) / 2
        sc = punteggio_previsione(ratio, d["ratio"].values) if d is not None else None
        if sc is not None:
            conc = " I due modelli però non sono d'accordo: leggi il numero con cautela." if o.get("grezzo") == "Grigio" else ""
            out["previsione"] = {"score": sc, "testo": f"Il modello base vede un rischio di calo pari a {_n(o['r_a1'])} volte il normale, il modello che tiene conto della paura {_n(o['r_fhs'])} volte (1 = normale). Oggi è più alto che nel {sc - 1:.0f}% dei giorni dal 1990." + conc,
                                 "grezzo": o.get("grezzo")}
    except Exception:  # noqa: BLE001
        pass
    # paura e opzioni
    try:
        C = vix_componenti(idx)
        rk, pctl = putcall_rischio()
        if rk is not None:
            C["putcall"] = rk
        s = float(1 + 99 * _media(C, VIXW).iloc[0])
        v = float(store.load("vix").iloc[-1])
        vt = float(store.load("vix3m").iloc[-1]) / v if "curva" in C and pd.notna(C["curva"].iloc[0]) else None
        txt = f"L'indice della paura (VIX) è a {v:.0f}" + (" (calma)" if v < 16 else " (nella norma)" if v < 20 else " (nervosismo)" if v < 30 else " (stress)")
        if vt:
            txt += f"; la curva a 3 mesi su 1 mese è {_n(vt, 2)}" + (" (capovolta: la paura di oggi supera quella futura)" if vt < 1 else "")
        txt += f"; i put (le protezioni) sono al {pctl:.0f}° percentile." if pctl is not None else "."
        out["vix"] = {"score": s, "testo": txt}
    except Exception:  # noqa: BLE001
        pass
    # economia reale
    try:
        R, W = eco_componenti(idx)
        r = R.iloc[0].dropna()
        if len(r) >= 4:
            sc = float(1 + 99 * r.mean())
            peg = [ECO[k][0] for k in r.sort_values(ascending=False).index[:2] if r[k] >= 0.5]
            mig = [ECO[k][0] for k in r.sort_values().index[:2] if r[k] <= 0.25]
            txt = f"{len(r)} misure dell'economia reale. " + (f"In difficoltà: {', '.join(peg)}. " if peg else "Nessuna misura è in forte difficoltà. ") + (f"In buona salute: {', '.join(mig)}." if mig else "")
            out["economia"] = {"score": sc, "testo": txt.strip(), "componenti": {k: float(v) for k, v in r.items()}}
    except Exception:  # noqa: BLE001
        pass
    # grandi fondi
    f = _fondi_oggi()
    if f["n"]:
        txt = (f"{len(f['alti'])} segnali alti e {len(f['bassi'])} bassi su {f['n']}; " if (f["alti"] or f["bassi"]) else f"{f['n']} segnali, tutti nella norma; ")
        t = f.get("tensione") or {}
        conf = (f"Valore di confronto {t['score']:.0f}/100 (quanto i grandi fondi sono fuori dalla norma, in qualsiasi direzione). " if t.get("score") is not None else "")
        out["fondi"] = {"score": t.get("score"), "testo": conf + txt + ("alcuni hanno superato la prova e contano nel valore." if f["dimostrati"] else "nessuno ha ancora dimostrato di anticipare i cali: per questo non pesa sul valore, ma lo seguiamo ogni giorno per decidere."), "dim": f["dimostrati"]}
    else:
        out["fondi"] = {"score": None, "testo": "Dati in arrivo (fondi monetari, futures, 13F, insider): finché non ce n'è abbastanza storia non pesano sul valore.", "dim": []}
    return out


def pesi_effettivi(pil: dict) -> dict:
    w = {k: PESI[k] for k in PESI}
    if pil.get("fondi", {}).get("dim") and pil["fondi"].get("score") is not None:
        w["fondi"] = 10.0
    attivi = {k: w[k] for k in w if pil.get(k, {}).get("score") is not None and w[k] > 0}
    s = sum(attivi.values()) or 1.0
    return {k: v / s for k, v in attivi.items()}


def calcola(aix: dict | None, p: pd.Series) -> dict | None:
    pil = pilastri_oggi(aix, p)
    w = pesi_effettivi(pil)
    if len(w) < 3:
        return None
    sai = float(sum(w[k] * pil[k]["score"] for k in w))
    sc = np.array([pil[k]["score"] for k in w])
    std = float(sc.std())
    conc = "concordi" if std < 12 else ("abbastanza concordi" if std < 22 else "discordi")
    contr = {k: w[k] * pil[k]["score"] for k in w}
    tot = sum(contr.values()) or 1.0
    mercato = [k for k in ("previsione", "armor", "vix") if k in w]
    mv = float(sum(w[k] * pil[k]["score"] for k in mercato) / sum(w[k] for k in mercato)) if mercato else None
    ombra = None
    if pil.get("fondi", {}).get("score") is not None and "fondi" not in w:   # SAI di confronto: stessi pesi + grandi fondi al 10% (non è il valore ufficiale)
        w2 = {k: PESI[k] for k in PESI if k != "fondi" and pil.get(k, {}).get("score") is not None}
        w2["fondi"] = 10.0
        s2 = sum(w2.values())
        so = float(sum(w2[k] * pil[k]["score"] for k in w2) / s2)
        ombra = {"sai": so, "delta": so - sai}
    return {"data": str(p.index[-1].date()), "sai": sai, "pesi": w, "pilastri": pil, "concordanza": conc, "dispersione": std, "quote": {k: v / tot for k, v in contr.items()},
            "mercato": mv, "economia": pil.get("economia", {}).get("score"), "ombra": ombra}


def confronti(oggi: dict, st: pd.DataFrame | None) -> dict:
    """Valore di ieri, 1 settimana e 1 mese fa dalla storia (le righe di prima della data di oggi)."""
    out = {}
    if st is None or st.empty:
        return out
    t = pd.Timestamp(oggi["data"])
    prima = st[st.index < t]
    for nome, giorni in (("ieri", 1), ("settimana", 7), ("mese", 30)):
        x = prima[prima.index <= t - pd.Timedelta(days=giorni)] if giorni > 1 else prima
        if x.empty:
            continue
        r = x.iloc[-1]
        out[nome] = {"data": str(x.index[-1].date()), "sai": float(r["sai"]), "delta": oggi["sai"] - float(r["sai"]),
                     "pil": {k: float(r[k]) for k in ("previsione", "armor", "vix", "economia", "fondi") if k in r and pd.notna(r[k])},
                     "ombra": float(r["sai_ombra"]) if "sai_ombra" in r and pd.notna(r["sai_ombra"]) else None}
    return out


def tendenza(c: dict) -> str:
    d5 = c.get("settimana", {}).get("delta")
    d21 = c.get("mese", {}).get("delta")
    if (d21 is not None and d21 >= 4) or (d5 is not None and d5 >= 3):
        return "salita"
    if (d21 is not None and d21 <= -4) or (d5 is not None and d5 <= -3):
        return "discesa"
    return "stabile"


TITOLI = {
    0: {"stabile": "Mercato sano: tutti i segnali sono tranquilli.", "salita": "Il mercato è sano, ma qualche segnale comincia a peggiorare.", "discesa": "Il mercato è sano e i segnali continuano a migliorare."},
    1: {"stabile": "Mercato tranquillo, senza segnali preoccupanti.", "salita": "Il mercato è tranquillo, ma emergono i primi segni di incertezza.", "discesa": "Il mercato si sta calmando: l'incertezza diminuisce."},
    2: {"stabile": "Zona di attenzione: l'incertezza c'è, ma è stabile.", "salita": "Il mercato sta dando crescenti segni di incertezza.", "discesa": "L'incertezza è ancora alta, ma sta lentamente calando."},
    3: {"stabile": "Mercato teso: i segnali di fragilità sono diffusi.", "salita": "Il mercato si fa sempre più teso e fragile.", "discesa": "Il mercato è ancora teso, ma la pressione sta calando."},
    4: {"stabile": "Mercato pericoloso e instabile: molti segnali sono in allarme.", "salita": "Il mercato peggiora: pericolo e instabilità in aumento.", "discesa": "Il mercato è ancora pericoloso, ma comincia a migliorare."},
}


def titolo(oggi: dict, c: dict) -> str:
    t = TITOLI[fascia(oggi["sai"])][tendenza(c)]
    if oggi["concordanza"] == "discordi":
        t += " I segnali però non sono d'accordo tra loro."
    return t


def cause(oggi: dict, c: dict) -> str:
    """Cosa è cambiato rispetto a ieri (o all'ultimo dato) e cosa pesa di più."""
    pil = oggi["pilastri"]
    righe = []
    top = sorted(oggi["quote"].items(), key=lambda kv: -kv[1])[:2]
    righe.append("Pesano di più sul valore: " + " e ".join(f"{NOMI[k].lower()} ({pil[k]['score']:.0f})" for k, _ in top) + ".")
    ie = c.get("ieri")
    if ie and ie["pil"]:
        diff = {k: pil[k]["score"] - ie["pil"][k] for k in ie["pil"] if k in pil and pil[k].get("score") is not None}
        if diff:
            k, v = max(diff.items(), key=lambda kv: abs(kv[1]))
            if abs(v) >= 1:
                righe.append(f"Rispetto all'ultima seduta è cambiato soprattutto {NOMI[k].lower()}: {'+' if v > 0 else ''}{v:.0f} punti.".replace(".0 ", " "))
    return " ".join(righe)


# ---------------- registrazione e prova ----------------
def registra(oggi: dict) -> None:
    st = storia()
    riga = {"sai": round(oggi["sai"], 2), **{k: round(oggi["pilastri"][k]["score"], 2) for k in ("previsione", "armor", "vix", "economia", "fondi") if k in oggi["pilastri"] and oggi["pilastri"][k].get("score") is not None}}
    if oggi.get("ombra"):
        riga["sai_ombra"] = round(oggi["ombra"]["sai"], 2)
    df = pd.DataFrame([riga], index=[pd.Timestamp(oggi["data"])])
    st = df if st is None else pd.concat([st[st.index != df.index[0]], df]).sort_index()
    st.to_csv(STORIA, index_label="date")


def valuta(p: pd.Series, st: pd.DataFrame | None = None, step: int = 5) -> dict:
    """Dopo ogni fascia, quanto spesso è arrivato un calo (≥5% in 1 mese, ≥10% in 3 mesi) e quanto bene ordina i giorni (AUC) rispetto ai singoli pilastri."""
    from sklearn.metrics import roc_auc_score
    from . import modeleval
    st = storia() if st is None else st
    d = st[st.index >= "2000-01-01"]
    dates = d.index[::step]
    out = {"data": str(p.index[-1].date()), "fasce": [], "auc": {}, "n": 0}
    ys = {"1m_5": modeleval.outcome(p, dates, "1m", "down", 5), "3m_10": modeleval.outcome(p, dates, "3m", "down", 10)}
    ok = np.all([y.notna().values for y in ys.values()], axis=0)
    dd, v = dates[ok], d.loc[dates[ok], "sai"].values
    Y = {k: y.values[ok].astype(float) for k, y in ys.items()}
    out["n"] = int(len(dd))
    f_idx = np.array([fascia(x) for x in v])
    for i, (_lim, nome, _l) in enumerate(FASCE):
        m = f_idx == i
        row = {"fascia": nome, "n": int(m.sum()), "quota": float(m.mean())}
        for k in Y:
            row[k] = float(Y[k][m].mean()) if m.sum() >= 10 else None
            row[k + "_tutte"] = float(Y[k].mean())
        out["fasce"].append(row)
    ok_f = [r for r in out["fasce"] if r["1m_5"] is not None]
    out["ordine"] = bool(len(ok_f) >= 3 and all(all(ok_f[i][k] <= ok_f[i + 1][k] + 1e-9 for i in range(len(ok_f) - 1)) for k in ("1m_5", "3m_10")))
    anni = dd.year.values
    for nome in ("sai", "sai_ombra", "previsione", "armor", "vix", "economia", "fondi"):
        if nome not in d or d[nome].notna().sum() < 200:
            continue
        x = d.loc[dd, nome].values
        r = {}
        for k in Y:
            for etich, m in (("tutta", np.ones(len(dd), bool)), ("2000-2012", anni < 2013), ("2013-oggi", anni >= 2013)):
                mm = m & np.isfinite(x)
                r[f"{k}|{etich}"] = float(roc_auc_score(Y[k][mm], x[mm])) if mm.sum() > 50 and 0 < Y[k][mm].sum() < mm.sum() else None
        out["auc"][nome] = r
    PROVA.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def prova() -> dict | None:
    try:
        return json.loads(PROVA.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ---------------- grafica ----------------
def _arco(cx, cy, r, v0, v1):
    def pt(v):
        a = np.pi * (1 - v / 100)
        return cx + r * np.cos(a), cy - r * np.sin(a)
    x0, y0 = pt(v0)
    x1, y1 = pt(v1)
    return f"M{x0:.1f} {y0:.1f}A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}"


def gauge(v: float) -> str:
    cx, cy, r = 75, 74, 58
    segs, a = [], 0.0
    for lim, *_x in FASCE:
        b = min(lim, 100)
        segs.append(f"<path d='{_arco(cx, cy, r, a + 0.7, b - 0.7)}' stroke='{colore((a + b) / 2)}' stroke-width='13' fill='none' stroke-linecap='round'/>")
        a = b
    ang = np.pi * (1 - min(max(v, 0), 100) / 100)
    mx, my = cx + r * np.cos(ang), cy - r * np.sin(ang)
    return (f"<svg viewBox='0 0 150 92' class='sai-gs' role='img' aria-label='Super Armor Index {v:.0f} su 100'>{''.join(segs)}"
            f"<circle cx='{mx:.1f}' cy='{my:.1f}' r='9' fill='var(--card)' stroke='{colore(v)}' stroke-width='3.5'/><circle cx='{mx:.1f}' cy='{my:.1f}' r='3' fill='{colore(v)}'/>"
            f"<text x='75' y='72' text-anchor='middle' class='sai-num' fill='{colore(v)}'>{v:.0f}</text><text x='75' y='88' text-anchor='middle' class='sai-sub'>su 100</text></svg>")


def anello(score: float | None, dim: int = 44, sottile: bool = False) -> str:
    c = 2 * np.pi * 17
    if score is None:
        return (f"<svg viewBox='0 0 44 44' width='{dim}' height='{dim}'><circle cx='22' cy='22' r='17' fill='none' stroke='var(--bd)' stroke-width='5' stroke-dasharray='3 4'/>"
                f"<text x='22' y='26' text-anchor='middle' font-size='12' font-weight='800' fill='var(--mu)'>–</text></svg>")
    col = colore(score)
    return (f"<svg viewBox='0 0 44 44' width='{dim}' height='{dim}'><circle cx='22' cy='22' r='17' fill='none' stroke='var(--bd)' stroke-width='5'/>"
            f"<circle cx='22' cy='22' r='17' fill='none' stroke='{col}' stroke-width='5' stroke-linecap='round' stroke-dasharray='{c * score / 100:.1f} {c:.1f}' transform='rotate(-90 22 22)'/>"
            f"<text x='22' y='26.5' text-anchor='middle' font-size='13' font-weight='800' fill='{col}'>{score:.0f}</text></svg>")


def ciambella(quote: dict, dim: int = 96) -> str:
    c = 2 * np.pi * 34
    off, segs = 0.0, []
    for k, q in sorted(quote.items(), key=lambda kv: -kv[1]):
        segs.append(f"<circle cx='50' cy='50' r='34' fill='none' stroke='{COL_PIL[k]}' stroke-width='16' stroke-dasharray='{c * q - 1.2:.1f} {c:.1f}' stroke-dashoffset='{-off:.1f}' transform='rotate(-90 50 50)'/>")
        off += c * q
    return f"<svg viewBox='0 0 100 100' width='{dim}' height='{dim}' role='img' aria-label='Quanto pesa ogni pilastro sul valore'>{''.join(segs)}</svg>"


def freccia(d: float, soglia: float = 1.5) -> tuple[str, str, str]:
    """(simbolo, parola, classe): salire = peggioramento, scendere = miglioramento."""
    if d >= soglia:
        return "▲", "in peggioramento", "sai-up"
    if d <= -soglia:
        return "▼", "in miglioramento", "sai-dn"
    return "▬", "stabile", "sai-fl"


def _dati_grafico(st: pd.DataFrame, oggi: dict) -> dict:
    s = st["sai"].copy()
    s.loc[pd.Timestamp(oggi["data"])] = oggi["sai"]
    s = s.sort_index()
    rec = s.iloc[-130:]
    vecchio = s.iloc[:-130].iloc[::5]
    z = pd.concat([vecchio, rec])
    return {"d": [str(i.date()) for i in z.index], "v": [round(float(x), 1) for x in z.values], "b": [lim for lim, *_x in FASCE[:-1]], "c": [colore(m) for m in (12, 32, 47, 62, 85)]}


def html(aix: dict | None, p: pd.Series) -> str:
    o = calcola(aix, p)
    if not o:
        return ""
    st = storia()
    c = confronti(o, st)
    v = o["sai"]
    fi = fascia(v)
    nome_f = FASCE[fi][2]
    tit = titolo(o, c)
    ca = cause(o, c)
    ie = c.get("ieri")
    chip = ""
    if ie:
        s_, w_, k_ = freccia(ie["delta"])
        chip = f"<span class='sai-ch {k_}'>{s_} {ie['delta']:+.0f} rispetto a ieri</span>".replace("+-", "-")
    tiles = ""
    for k in ("previsione", "armor", "vix", "fondi", "economia"):
        pl = o["pilastri"].get(k) or {}
        sc = pl.get("score")
        peso = o["pesi"].get(k)
        tiles += (f"<div class='sai-tile' data-saiop='1'>{anello(sc)}<span>{_h.escape(NOMI[k])}</span>" + ("" if peso else "<em>peso 0</em>") + "</div>")
    righe = ""
    for k in ("previsione", "armor", "vix", "economia", "fondi"):
        pl = o["pilastri"].get(k)
        if not pl:
            continue
        peso = o["pesi"].get(k)
        righe += (f"<div class='sai-r'>{anello(pl.get('score'), 40)}<div><b>{_h.escape(NOMI[k])}</b> <span class='sai-w'>{'pesa ' + format(peso * 100, '.0f') + '%' if peso else 'non pesa ancora'}</span>"
                  f"<div class='sai-t2'>{_h.escape(pl['testo'])}</div></div></div>")
    leg = "".join(f"<div><i style='background:{COL_PIL[k]}'></i>{_h.escape(NOMI[k])} {q * 100:.0f}%</div>" for k, q in sorted(o["quote"].items(), key=lambda kv: -kv[1]))
    mer = f"<div class='sai-bar'><span>Mercato (giorni e settimane)</span><b style='color:{colore(o['mercato'])}'>{o['mercato']:.0f}</b></div>" if o["mercato"] is not None else ""
    eco = f"<div class='sai-bar'><span>Economia (mesi)</span><b style='color:{colore(o['economia'])}'>{o['economia']:.0f}</b></div>" if o["economia"] is not None else ""
    conc = {"concordi": "I pilastri sono concordi: raccontano la stessa storia.", "abbastanza concordi": "I pilastri sono abbastanza concordi.", "discordi": "Attenzione: i pilastri non sono d'accordo tra loro, il numero unico nasconde opinioni diverse."}[o["concordanza"]]
    # tabella confronti
    conf = f"<tr><td>Oggi</td><td><b style='color:{colore(v)}'>{v:.0f}</b></td><td></td><td>{_h.escape(nome_f)}</td></tr>"
    for k, lab in (("ieri", "Ieri"), ("settimana", "Una settimana fa"), ("mese", "Un mese fa")):
        if k in c:
            s_, w_, kk = freccia(c[k]["delta"])
            conf += f"<tr><td>{lab}</td><td>{c[k]['sai']:.0f}</td><td class='{kk}'>{s_} {c[k]['delta']:+.0f}</td><td class='{kk}'>{w_}</td></tr>".replace("+-", "-")
    pr = prova()
    aff = ""
    if pr:
        tr = "".join(f"<tr><td><span class='sai-dot' style='background:{colore([12, 32, 47, 62, 85][i])}'></span>{_h.escape(f['fascia'])}</td><td>{f['quota'] * 100:.0f}%</td>"
                     f"<td>{'n.d.' if f['1m_5'] is None else format(f['1m_5'] * 100, '.0f') + '%'}</td><td>{'n.d.' if f['3m_10'] is None else format(f['3m_10'] * 100, '.0f') + '%'}</td></tr>" for i, f in enumerate(pr["fasce"]))
        base1 = pr["fasce"][0]["1m_5_tutte"]
        base3 = pr["fasce"][0]["3m_10_tutte"]
        au = pr["auc"].get("sai", {})
        a1 = au.get("1m_5|tutta")
        aff = (f"<h4>Quanto è affidabile</h4><p class='sai-t2'>Dal 2000 a oggi, dopo ogni fascia del numero, quanto spesso l'S&amp;P 500 ha perso almeno il 5% entro un mese e almeno il 10% entro tre mesi "
               f"(in media: {base1 * 100:.0f}% e {base3 * 100:.0f}%).</p><table class='sai-tb'><tr><th>Fascia</th><th>Quanti giorni</th><th>Calo ≥5% in 1 mese</th><th>Calo ≥10% in 3 mesi</th></tr>{tr}</table>"
               f"<p class='sai-t2'>{'Più sale il numero, più cali sono arrivati: le fasce sono in ordine.' if pr.get('ordine') else 'Attenzione: le fasce non sono perfettamente in ordine.'} "
               f"Capacità di distinguere i giorni a rischio: {a1 * 100:.0f} su 100 (50 = come tirare a sorte, 100 = perfetta). "
               "È simile a quella dei singoli pilastri: il numero unico non li batte, ma è più stabile e racconta tutto insieme. L'economia reale descrive la salute di fondo, non prevede i cali di breve. "
               "Storia ricostruita con le regole di oggi; non è una promessa per il futuro.</p>") if a1 else ""
    dati = json.dumps(_dati_grafico(st, o), separators=(",", ":")) if st is not None else "null"
    pesi_txt = ", ".join(f"{NOMI[k].lower()} {w * 100:.0f}%" for k, w in sorted(o["pesi"].items(), key=lambda kv: -kv[1]))
    return (f"{CSS}<section class='sai' style='--sc:{colore(v)}' id='sai'><div class='sai-top'><div class='sai-g' data-saim='1' title='Tocca per vedere lo storico'>{gauge(v)}</div>"
            f"<div class='sai-tx'><div class='sai-k'>Super Armor Index</div><div class='sai-lab' style='color:{colore(v)}'>{_h.escape(nome_f)} {chip}</div>"
            f"<div class='sai-head' data-saiex='1'>{_h.escape(tit)} <span class='sai-chev'>▾</span></div></div></div>"
            f"<div class='sai-tiles'>{tiles}</div>"
            f"<div class='sai-ex'><div class='sai-ca'>{_h.escape(ca)}</div>{righe}"
            f"<div class='sai-mix'><div class='sai-don'>{ciambella(o['quote'])}</div><div><b>Cosa pesa sul valore</b><div class='sai-leg'>{leg}</div></div></div>"
            f"<div class='sai-two'>{mer}{eco}</div><p class='sai-t2'>{_h.escape(conc)} Come è calcolato: media dei pilastri con pesi fissi scritti in anticipo ({_h.escape(pesi_txt)}). "
            "L'Indice Armor contiene già in parte la paura dei mercati: per questo la paura pesa meno. Grandi fondi non pesa finché nessuno dei suoi segnali ha dimostrato di anticipare i cali. "
            "Non è una consulenza finanziaria.</p><button class='sai-btn' data-saim='1'>Storico e confronto ›</button></div>"
            f"<div class='sai-mod' id='saimod'><div class='sai-card'><button class='sai-x' data-saix='1' aria-label='Chiudi'>×</button><h3>Super Armor Index: storico</h3>"
            f"<table class='sai-tb'><tr><th></th><th>Valore</th><th>Variazione</th><th></th></tr>{conf}</table>"
            f"<div class='sai-rg'><button data-r='90' class='on'>3 mesi</button><button data-r='260'>1 anno</button><button data-r='1300'>5 anni</button><button data-r='99999'>Tutto</button></div>"
            f"<svg id='saich' viewBox='0 0 320 130' preserveAspectRatio='none'></svg><div class='sai-t2' id='saich-i'></div>{aff}</div></div>"
            f"<script type='application/json' id='sai-data'>{dati}</script>{JS}</section>")


CSS = """<style>
.sai{background:linear-gradient(140deg,var(--card),var(--bg));border:1px solid var(--bd);border-radius:20px;padding:10px 12px 8px;margin:0 0 12px;box-shadow:0 8px 28px -12px var(--sc),0 0 0 1px color-mix(in srgb,var(--sc) 22%,transparent) inset}
.sai-top{display:flex;gap:6px;align-items:center}.sai-g{flex:0 0 138px;cursor:pointer}.sai-gs{width:100%;display:block;overflow:visible}.sai-num{font-size:36px;font-weight:800}.sai-sub{font-size:9.5px;fill:var(--mu);font-weight:700}
.sai-tx{flex:1;min-width:0}.sai-k{font-size:10.5px;font-weight:800;letter-spacing:.7px;text-transform:uppercase;color:var(--mu)}.sai-lab{font-weight:800;font-size:15px;line-height:1.2;margin:1px 0 3px}
.sai-ch{font-size:11px;font-weight:700;padding:1px 7px;border-radius:99px;margin-left:4px;white-space:nowrap;background:var(--bg);display:inline-block}
.sai-up{color:var(--bad)}.sai-dn{color:var(--ok)}.sai-fl{color:var(--mu)}
.sai-head{font-size:13px;line-height:1.3;font-weight:600;cursor:pointer}.sai-chev{display:inline-block;transition:transform .25s;color:var(--mu)}.sai.open .sai-chev{transform:rotate(180deg)}
.sai-tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:2px;margin-top:4px}.sai-tile{display:flex;flex-direction:column;align-items:center;gap:1px;font-size:10px;line-height:1.1;text-align:center;color:var(--mu);font-weight:700;cursor:pointer}
.sai-tile em{font-style:normal;font-size:9px;opacity:.75}
.sai-ex{display:none;border-top:1px dashed var(--bd);margin-top:8px;padding-top:8px;font-size:13px}.sai.open .sai-ex{display:block;animation:saif .25s}@keyframes saif{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.sai-ca{font-weight:700;margin-bottom:6px}.sai-r{display:flex;gap:8px;align-items:flex-start;margin:7px 0}.sai-r>svg{flex:0 0 40px}.sai-w{font-size:11px;color:var(--mu);font-weight:600;margin-left:4px}
.sai-t2{font-size:12.5px;line-height:1.38;color:var(--mu);margin:2px 0}.sai-mix{display:flex;gap:12px;align-items:center;margin:10px 0 6px}.sai-don{flex:0 0 96px}
.sai-leg div{font-size:12px;margin:2px 0;display:flex;align-items:center;gap:6px}.sai-leg i{width:10px;height:10px;border-radius:3px;display:inline-block}
.sai-two{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0}.sai-bar{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:6px 10px;display:flex;justify-content:space-between;align-items:center;font-size:12px}.sai-bar b{font-size:20px}
.sai-btn{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:7px 14px;font:inherit;font-weight:700;cursor:pointer;margin-top:4px}
.sai-mod{display:none;position:fixed;inset:0;background:rgba(10,14,22,.62);z-index:40;align-items:center;justify-content:center;padding:14px}.sai-mod.show{display:flex}
.sai-card{background:var(--card);color:var(--tx);border-radius:18px;max-width:560px;width:100%;max-height:88vh;overflow:auto;padding:16px 16px 12px;position:relative;border:1px solid var(--bd)}
.sai-card h3{margin:0 0 8px}.sai-card h4{margin:12px 0 4px}.sai-x{position:absolute;right:10px;top:8px;border:0;background:none;color:var(--mu);font-size:26px;cursor:pointer;line-height:1}
.sai-tb{width:100%;border-collapse:collapse;font-size:13px}.sai-tb th{font-size:11px;color:var(--mu);text-align:left;padding:3px 4px}.sai-tb td{padding:5px 4px;border-top:1px solid var(--bd)}.sai-tb td:first-child{white-space:nowrap}.sai-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.sai-rg{display:flex;gap:6px;margin:10px 0 4px}.sai-rg button{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;padding:3px 11px;font:inherit;font-size:12px;cursor:pointer}.sai-rg button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
#saich{width:100%;height:130px;display:block;background:var(--bg);border-radius:10px}
</style>"""

JS = r"""<script>(function(){var S=document.getElementById('sai');if(!S||S.dataset.on)return;S.dataset.on=1;
var M=document.getElementById('saimod'),D=null;try{D=JSON.parse(document.getElementById('sai-data').textContent)}catch(e){}
function draw(n){var svg=document.getElementById('saich');if(!svg||!D)return;var v=D.v,d=D.d,k=v.length,s=0;
if(n<99999){var cut=(n>=260)?Math.max(0,k-130-Math.ceil((n-130)/5)):Math.max(0,k-n);s=cut}
v=v.slice(s);d=d.slice(s);var W=320,H=130,N=v.length,x=function(i){return N<2?0:i*W/(N-1)},y=function(a){return H-3-(a-1)*(H-6)/99};
var o='',lo=1,B=D.b.concat([100]);for(var j=0;j<B.length;j++){var a=y(B[j]),b=y(j?B[j-1]:1);o+="<rect x='0' y='"+a+"' width='"+W+"' height='"+(b-a)+"' fill='"+D.c[j]+"' opacity='.16'/>"}
var pts=v.map(function(a,i){return x(i).toFixed(1)+','+y(a).toFixed(1)}).join(' ');
o+="<polyline fill='none' stroke='var(--tx)' stroke-width='1.6' vector-effect='non-scaling-stroke' points='"+pts+"'/>";
o+="<circle cx='"+x(N-1)+"' cy='"+y(v[N-1])+"' r='3' fill='var(--tx)'/>";svg.innerHTML=o;
var mn=Math.min.apply(null,v),mx=Math.max.apply(null,v);document.getElementById('saich-i').textContent='Dal '+d[0].split('-').reverse().join('/')+': minimo '+mn.toFixed(0)+', massimo '+mx.toFixed(0)+', oggi '+v[N-1].toFixed(0)+'.'}
S.addEventListener('click',function(e){var t=e.target;
if(t.closest('[data-saiex],[data-saiop]')){S.classList.toggle('open');return}
if(t.closest('[data-saim]')){M.classList.add('show');draw(90);return}
if(t.closest('[data-saix]')||t===M){M.classList.remove('show');return}
var r=t.closest('.sai-rg button');if(r){S.querySelectorAll('.sai-rg button').forEach(function(b){b.classList.toggle('on',b===r)});draw(+r.dataset.r)}});
})();</script>"""
