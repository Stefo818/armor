"""Indice crollo: un numero da 1 a 100 in cima alla scheda Oggi.

Regole e risultati: PROTOCOLLO_INDICE_CROLLO.md (con emendamento 1, solo crisi finanziarie) e
ESITO_INDICE_CROLLO.md. Etichetta della prova: «Non coerente» (la fascia viola non ha superato R2).
La scheda e' quindi un termometro dello stress, non una previsione, e lo dichiara.

Numeri misurati che compaiono nei testi (verifica dal 2015, sole crisi finanziarie):
- mercato entro il 2% dal massimo: il calo arriva al 10% nel 5,5% dei casi se verde, 11,7% se giallo o peggio
- mercato fra il 2% e il 7% sotto il massimo: 6,5% se verde, 23,0% se giallo, 28,0% se rosso o viola
- dopo le letture rosse il mercato e' poi salito, in mediana, del 2,95% in 10 sedute (72% dei casi positivi)
"""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

SETTORI = {"sec_xlk": "tecnologia", "sec_xlf": "finanza", "sec_xle": "energia", "sec_xli": "industria",
           "sec_xlv": "salute", "sec_xlp": "beni di base", "sec_xly": "consumi discrezionali",
           "sec_xlb": "materiali", "sec_xlu": "servizi pubblici"}

FILE = DATA / "indice_crollo.json"
STORIA = DATA / "indice_crollo_storia.csv"
REGISTRO = DATA / "indice_crollo_registro.csv"   # append-only: la prova pulita si fa in avanti, non sul passato
MIN_STORIA = 500

# protocollo parte 6: percentile del punteggio -> numero da 1 a 100
TRATTI = ((0.00, 0.55, 1, 35), (0.55, 0.65, 36, 40), (0.65, 0.85, 41, 60), (0.85, 0.96, 61, 80), (0.96, 1.01, 81, 100))
FASCE = (
    (35, "verde", "Nessuna tensione particolare", "ok", "var(--ok)"),
    (40, "grigio", "Zona di passaggio", "ok", "#9ca3af"),
    (60, "giallo", "Mercato teso", "warn", "#f59e0b"),
    (80, "rosso", "Mercato molto teso", "bad", "#ef4444"),
    (100, "viola", "Mercato in panico", "bad", "#8b5cf6"),
)
# protocollo parte 4, modello M2: pesi fissati prima dei risultati
PESI = {"f1_paura": 0.30, "f3_curva": 0.30, "f5_credito": 0.15, "f7_tendenza": 0.25, "f8_perdita": 0.25,
        "f10_rotaz": 0.15, "f6_tassi": 0.15}
NOMI = {
    "f1_paura": "paura del mercato",
    "f2_salto": "salto improvviso della paura",
    "f3_curva": "paura a breve più alta che a tre mesi",
    "f4_protez": "costo delle assicurazioni sul ribasso",
    "f5_credito": "costo del debito delle aziende",
    "f6_tassi": "scosse sui tassi americani",
    "f7_tendenza": "prezzo sotto le sue medie",
    "f8_perdita": "quanto siamo sotto il massimo dell'anno",
    "f9_volat": "quanto balla il prezzo ogni giorno",
    "f10_rotaz": "fuga dai settori che rischiano di più",
    "f11_bond": "nervosismo sui titoli di Stato",
    "f12_armor": "Indice Armor",
}


def _pct(s: pd.Series) -> pd.Series:
    return s.expanding(min_periods=MIN_STORIA).rank(pct=True) * 100.0


def _lag(s: pd.Series, giorni: int) -> pd.Series:
    if giorni <= 0:
        return s
    out = s.copy()
    out.index = out.index + pd.Timedelta(days=giorni)
    return out


def famiglie(sp_override: pd.Series | None = None) -> pd.DataFrame:
    """Le 12 famiglie del protocollo, ognuna in percentile su storia crescente."""
    sp = (store.load("sp500") if sp_override is None else sp_override).dropna()
    cal = sp.index

    def g(sid, lag=0):
        return _lag(store.load(sid).dropna(), lag).reindex(cal).ffill()

    vix, vix3m, skew, pput = g("vix"), g("vix3m"), g("skew"), g("pput")
    baa, d10, d2, move = g("baa10y", 1), g("dgs10", 1), g("dgs2", 1), g("move")
    armor = g("armor_index")
    r = np.log(sp).diff()
    ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean()
    sotto = (sp < ma200).astype(float)
    rotta = sotto.groupby((sotto != sotto.shift()).cumsum()).cumsum() * sotto

    X = pd.DataFrame(index=cal)
    X["f1_paura"] = _pct(vix)
    X["f2_salto"] = (_pct(vix / vix.shift(5) - 1) + _pct(vix / vix.shift(10) - 1)) / 2
    X["f3_curva"] = _pct(vix / vix3m)
    X["f4_protez"] = (_pct(skew) + _pct(pput)) / 2
    X["f5_credito"] = (_pct(baa) + _pct(baa - baa.shift(20))) / 2
    X["f6_tassi"] = (_pct((d10 - d10.shift(5)).abs()) + _pct((d10 - d10.shift(20)).abs()) + _pct(-(d10 - d2))) / 3
    X["f7_tendenza"] = (_pct(-(sp / ma50 - 1)) + _pct(-(sp / ma200 - 1)) + _pct(rotta)) / 3
    X["f8_perdita"] = _pct(-(sp / sp.rolling(252, min_periods=60).max() - 1))
    X["f9_volat"] = (_pct(r.rolling(20).std()) + _pct(r.clip(upper=0).rolling(20).std())) / 2
    rot = [_pct(-(s / s.rolling(60).mean() - 1)) for s in (g("rel_semi"), g("rel_small"), g("rel_banche"), g("rel_rame_oro"))]
    X["f10_rotaz"] = pd.concat(rot, axis=1).mean(axis=1)
    X["f11_bond"] = _pct(move)
    X["f12_armor"] = _pct(armor)
    X["sp500"] = sp
    return X


def calcola_serie(sp_override: pd.Series | None = None) -> pd.DataFrame:
    X = famiglie(sp_override)
    w = pd.Series(PESI)
    w = w / w.sum()
    punteggio = sum(X[c].fillna(50.0) * w[c] for c in w.index)
    # la scala si calibra dal 1990, come nella verifica: prima non esistono paura e curva della paura
    pq = punteggio[punteggio.index >= "1990-01-02"]
    q = pq.expanding(min_periods=MIN_STORIA).rank(pct=True).reindex(punteggio.index)
    idx = pd.Series(np.nan, index=X.index)
    for a, b, lo, hi in TRATTI:
        m = (q >= a) & (q < b)
        idx[m] = lo + (q[m] - a) / (b - a) * (hi - lo)
    X["punteggio"] = punteggio
    X["indice"] = idx.clip(1, 100)
    sp = X["sp500"]
    X["sotto_massimo"] = (sp / sp.rolling(252, min_periods=60).max() - 1) * 100
    # settore piu' rotto: quanto il peggiore dei nove settori sta sotto il proprio massimo a 6 mesi
    SP = pd.DataFrame({k: store.load(k).dropna().reindex(X.index).ffill() for k in SETTORI})
    giu = SP / SP.rolling(126, min_periods=60).max() - 1
    X["settore_giu"] = giu.min(axis=1) * 100
    ok = giu.notna().any(axis=1)
    quale = pd.Series(pd.NA, index=X.index, dtype=object)
    quale[ok] = giu[ok].idxmin(axis=1)
    X["settore_quale"] = quale
    return X[X.index >= "1990-01-02"]


def _fascia(v: float):
    for lim, nome, titolo, classe, colore in FASCE:
        if v <= lim:
            return nome, titolo, classe, colore
    return FASCE[-1][1], FASCE[-1][2], FASCE[-1][3], FASCE[-1][4]


def situazione(indice: float, sotto_massimo: float) -> dict:
    """La chiave di lettura: lo stesso numero vale in modo diverso secondo quanto siamo già scesi.

    Percentuali misurate sulle sole crisi finanziarie (ESITO_INDICE_CROLLO.md).
    Il campo "usare" dice cosa ne hanno fatto i prezzi dopo, perché cambia molto fra le tre zone.
    """
    giallo = indice >= 41
    rimbalzo = ("Un numero alto dice che il mercato è teso adesso, non che devi vendere: dopo le letture rosse il mercato "
                "era più alto dieci sedute dopo in 7 casi su 10, in mediana del 2,9%.")
    if sotto_massimo > -2:
        t = ("Il mercato è ancora vicino ai suoi massimi. Con una lettura come quella di oggi il calo è poi arrivato al 10% "
             "nell'11,7% dei casi, contro il 5,5% quando l'indice è verde.") if giallo else (
            "Il mercato è vicino ai suoi massimi e l'indice è basso: la situazione più tranquilla fra quelle misurate, "
            "con il calo al 10% arrivato nel 5,5% dei casi.")
        return {"zona": "vicino ai massimi", "prob": 11.7 if giallo else 5.5, "confronto": 5.5, "testo": t, "usare": rimbalzo}
    if sotto_massimo > -7:
        if indice > 60:
            t = ("Questa è la situazione in cui l'indice serve davvero: il mercato è scivolato fra il 2% e il 7% sotto il massimo. "
                 "Con una lettura rossa o viola il calo è poi arrivato al 10% nel 28% dei casi, contro il 6,5% se l'indice resta verde.")
            p = 28.0
        elif giallo:
            t = ("Questa è la situazione in cui l'indice serve davvero: il mercato è scivolato fra il 2% e il 7% sotto il massimo. "
                 "Con una lettura gialla il calo è poi arrivato al 10% nel 23% dei casi, contro il 6,5% se l'indice resta verde.")
            p = 23.0
        else:
            t = ("Il mercato è scivolato un po' sotto il massimo ma l'indice resta basso: in passato lo scivolamento è proseguito "
                 "fino al 10% solo nel 6,5% dei casi.")
            p = 6.5
        return {"zona": "già scivolato", "prob": p, "confronto": 6.5, "testo": t, "usare": rimbalzo}
    return {"zona": "in correzione", "prob": 33.0, "confronto": None,
            "testo": ("Il mercato è già più del 7% sotto il massimo: la correzione è in corso e non è più una cosa da prevedere. "
                      "Delle 9 crisi finanziarie passate che hanno superato questo punto, 3 sono arrivate a un calo del 20% e 6 si "
                      "sono fermate prima, fra il 10% e il 19%. Sono 9 casi: è un ordine di grandezza, non una probabilità precisa."),
            "usare": ("Qui il rimbalzo che si vede nelle altre zone non c'è più: una volta scesi oltre il 7%, nelle crisi finanziarie "
                      "il mese successivo è stato in media piatto, positivo solo in poco più di metà dei casi. L'indice dice quanto è "
                      "teso il mercato adesso, non cosa farà.")}


def aggiorna(log=print) -> dict:
    df = calcola_serie()
    ult = df.dropna(subset=["indice"]).iloc[-1]
    v = float(ult["indice"])
    nome, titolo, classe, colore = _fascia(v)
    fam = sorted(((c, float(ult[c])) for c in NOMI if pd.notna(ult.get(c))), key=lambda x: -x[1])
    res = {
        "data": str(df.dropna(subset=["indice"]).index[-1].date()),
        "indice": round(v, 0), "fascia": nome, "titolo": titolo, "classe": classe, "colore": colore,
        "sotto_massimo": round(float(ult["sotto_massimo"]), 1),
        "situazione": situazione(v, float(ult["sotto_massimo"])),
        "spinte": [{"nome": NOMI[c], "valore": round(p, 0)} for c, p in fam[:3]],
        "calme": [{"nome": NOMI[c], "valore": round(p, 0)} for c, p in fam[-2:]],
        "etichetta": "Non coerente",
    }
    if pd.notna(ult.get("settore_giu")) and isinstance(ult.get("settore_quale"), str):
        res["settore"] = {"nome": SETTORI[ult["settore_quale"]], "giu": round(float(ult["settore_giu"]), 0),
                          "rotto": bool(float(ult["settore_giu"]) <= -15)}
    _registra(res, ult)
    FILE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    df[["indice", "punteggio", "sotto_massimo"]].tail(2520).round(2).to_csv(STORIA, index_label="date")
    log(f"[indice_crollo] {res['data']} · {res['indice']:.0f} su 100 · {nome}")
    return res


def _registra(res: dict, ult) -> None:
    """Riga giornaliera che non si riscrive mai: serve per la verifica prospettica.

    Sei analisi sugli stessi undici episodi hanno esaurito quello che il passato può dire. Da qui in poi
    l'unica prova non inquinata è in avanti, a formula ferma. Il registro la rende possibile.
    """
    import csv
    import hashlib
    firma = hashlib.sha1(json.dumps({k: round(v, 4) for k, v in sorted(PESI.items())}).encode()).hexdigest()[:8]
    riga = {"data": res["data"], "scritto_il": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M"),
            "indice": res["indice"], "fascia": res["fascia"], "sotto_massimo": res["sotto_massimo"],
            "zona": res["situazione"]["zona"], "settore_rotto": (res.get("settore") or {}).get("nome", ""),
            "settore_giu": (res.get("settore") or {}).get("giu", ""), "versione_pesi": firma,
            **{c: (round(float(ult[c]), 1) if pd.notna(ult.get(c)) else "") for c in NOMI}}
    try:
        viste = set()
        if REGISTRO.exists():
            with REGISTRO.open(encoding="utf-8") as f:
                viste = {r["data"] for r in csv.DictReader(f)}
        if riga["data"] in viste:
            return
        nuovo = not REGISTRO.exists()
        with REGISTRO.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(riga))
            if nuovo:
                w.writeheader()
            w.writerow(riga)
    except Exception:  # noqa: BLE001
        pass   # il registro non deve mai bloccare il giro giornaliero


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _settore_html(d: dict) -> str:
    """Il settore più rotto: descrizione, non previsione. L'assetto a due chiavi non ha superato R16 (3 episodi su 6)."""
    import html as _h
    s = d.get("settore")
    if not s:
        return ""
    base = (f"<div class='ic-m'><b>Settore più in difficoltà:</b> {_h.escape(s['nome'])}, {abs(s['giu']):.0f}% sotto il suo massimo "
            "degli ultimi sei mesi.")
    if not s.get("rotto"):
        return base + " Nessun settore è rotto oltre il 15%.</div>"
    vicino = d.get("sotto_massimo", -99) > -5
    if vicino and d.get("indice", 0) >= 34:
        return (base + " Questo settore è rotto oltre il 15% mentre l'indice è ancora vicino ai massimi e la tensione è alta: "
                "è l'assetto del 2000, del 2007 e di oggi. In quelle condizioni il calo è poi arrivato al 10% nel 42% dei casi "
                "contro il 9% normale — ma su soli 165 giorni concentrati in tre episodi, e questo schema ha mancato le crisi "
                "del 2015, 2018 e 2022. È un indizio trovato al quarto tentativo, non una regola provata.</div>")
    return base + " Un settore rotto oltre il 15% è normale a correzione iniziata: conta quando l'indice è ancora sui massimi.</div>"


def oggi_html() -> str:
    import html as _h
    d = carica()
    if not d:
        return ""
    v = int(d["indice"])
    sp = "".join(f"<li>{_h.escape(s['nome'])}</li>" for s in d.get("spinte", []))
    sit = d.get("situazione", {}).get("testo", "")
    return (
        "<style>.ic{border:1px solid var(--bd);border-radius:14px;background:var(--card);padding:12px 14px;margin:10px 0}"
        ".ic.ok{border-left:6px solid var(--ok)}.ic.warn{border-left:6px solid var(--warn,#f59e0b)}.ic.bad{border-left:6px solid var(--bad)}"
        ".ic-top{display:flex;align-items:baseline;gap:10px}.ic-n{font-size:40px;font-weight:800;line-height:1}"
                ".ic-t{font-size:16px;font-weight:700;margin-top:6px}.ic-p{font-size:13px;line-height:1.5;margin-top:6px;color:var(--fg)}"
        ".ic-m{font-size:12px;line-height:1.45;margin-top:8px;color:var(--mu)}.ic ul{margin:4px 0 0;padding-left:18px;font-size:13px}"
        ".ic-s{display:flex;height:8px;border-radius:999px;overflow:hidden;margin:10px 0 4px}.ic-s i{display:block;height:100%}"
        ".ic-k{font-size:11px;color:var(--mu);display:flex;justify-content:space-between}</style>"
        f"<div class='ic {d['classe']}'>"
        f"<div class='ic-top'><div class='ic-n' style='color:{d.get('colore', 'inherit')}'>{v}</div>"
        f"<div style='font-size:13px;color:var(--mu)'>su 100</div></div>"
        f"<div class='ic-t'>Indice crollo · {_h.escape(d['titolo'])}</div>"
        "<div class='ic-s'><i style='flex:35;background:var(--ok)'></i><i style='flex:5;background:#9ca3af'></i>"
        "<i style='flex:20;background:#f59e0b'></i><i style='flex:20;background:#ef4444'></i><i style='flex:20;background:#8b5cf6'></i></div>"
        "<div class='ic-k'><span>1 tranquillo</span><span>100 panico</span></div>"
        f"<div class='ic-p'>{_h.escape(sit)}</div>"
        f"<div class='ic-m'>Oggi il mercato è {abs(d['sotto_massimo']):.1f}% sotto il massimo dell'anno. Cosa spinge l'indice in alto:</div><ul>{sp}</ul>"
        f"{_settore_html(d)}"
        f"<div class='ic-m'><b>Come usarlo.</b> {_h.escape(d.get('situazione', {}).get('usare', ''))} "
        "Nella prova, vendere quando l'indice entrava in rosso avrebbe reso il 143% invece del 236% restando investito, senza ridurre la perdita peggiore.</div>"
        "<div class='ic-m'><b>Quanto preavviso ha dato in passato.</b> Nelle crisi finanziarie dal 1990 è entrato in giallo "
        "in mediana 25 sedute prima che il calo arrivasse al 10%, in 9 episodi su 11 (in questo, il 16 ottobre, 26 sedute prima). "
        "Ma nello stesso periodo è stato giallo o peggio per 500 giorni senza che seguisse nulla: prende quasi tutti i cali veri "
        "proprio perché si accende spesso.</div>"
        "<div class='ic-m'>Prova fatta una volta sola sulle 11 crisi finanziarie dal 1990, escluse quelle da dazi, guerre e pandemia. "
        "Non ha superato la prova sulla fascia viola, quindi è un termometro e non una previsione: dal 1990 ci sono stati 229 periodi di "
        "allarme, 61 seguiti da un calo del 10% e 168 no. Al massimo di tutti gli 11 episodi l'indice era basso: i crolli non si vedono dalla cima.</div>"
        "</div>")
