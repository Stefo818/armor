"""Concentrazione del mercato: quanto il mercato e' sbilanciato su pochi titoli e sulla tecnologia, e se lo sbilanciamento accelera.

Regole: PROTOCOLLO_CONCENTRAZIONE.md (+ Emendamento 1). Risultato: ESITO_CONCENTRAZIONE.md, in sintesi
**non dimostrato**: indizio dal 1990, anticipo di mesi e non di giorni. Per questo l'indicatore e' informativo e ha peso ZERO
nei calcoli degli altri indici. Qui si calcola ogni giorno e si registra, per verificarlo in avanti (PROTOCOLLO_CONCENTRAZIONE_AVANTI.md).

Come si misura (senza pesi veri delle singole aziende, che gratis non esistono): rapporti fra indici
(Nasdaq/NYSE, Nasdaq 100/S&P 500, tecnologici/S&P, S&P 100/S&P 500, S&P 500/medie, S&P 500/stesso peso).
- livello: posizione del rapporto nella propria storia (percentile 0-1);
- accelerazione: quanto in fretta sta salendo, in percentile;
- stati: «sbilanciato e accelera» = livello e accelerazione entrambi >= 0,80.
- rottura: almeno due fra rendimenti a 10 anni in salita, stretta della banca centrale, spread di credito che si allarga,
  condizioni finanziarie che si irrigidiscono.
File: data/concentrazione.json (stato di oggi + grafico), data/concentrazione_registro.csv (una riga al giorno).
"""
from __future__ import annotations

import json
from datetime import timedelta

import numpy as np
import pandas as pd

from . import store
from .config import DATA

SIMBOLI = {"IXIC": "^IXIC", "NYA": "^NYA", "NDX": "^NDX", "GSPC": "^GSPC", "OEX": "^OEX", "MID": "^MID", "XLK": "XLK", "SPY": "SPY", "RSP": "RSP", "SPXEW": "^SPXEW"}
PROXY = {"TEC1": ("IXIC", "NYA"), "TEC2": ("NDX", "GSPC"), "TEC3": ("XLK", "SPY"), "GRA1": ("OEX", "GSPC"), "GRA2": ("GSPC", "MID"), "GRA3": ("SPY", "RSP"), "GRA4": ("GSPC", "SPXEW")}
SOGLIA = 0.80
INIZIO = "1971-06-01"
ARCH = DATA / "concentrazione.json"
REG = DATA / "concentrazione_registro.csv"
FASI = {"calmo": "Nessun allarme", "alto": "Sbilanciato, senza accelerazione", "carico": "Sbilanciato e in accelerazione",
        "riprezzamento": "Fase di riprezzamento"}


# ----------------------------------------------------------------------------- dati
def aggiorna_prezzi() -> dict[str, pd.Series]:
    """Prezzi giornalieri dei dieci indici/fondi (Yahoo), tenuti in data/series/cn_*.csv: ogni giorno si scaricano solo gli ultimi giorni."""
    from . import accumulo
    out: dict[str, pd.Series] = {}
    for k, sym in SIMBOLI.items():
        sid = "cn_" + k.lower()
        old = store.load(sid)
        try:
            da = "1960-01-01" if old.empty else (old.index[-1] - timedelta(days=20)).strftime("%Y-%m-%d")
            df = accumulo._scarta_oggi(accumulo.chart(sym, "1d", da), sym)
            store.upsert(sid, df["c"][df["c"] > 0])
        except Exception as e:  # noqa: BLE001
            print(f"[concentrazione] {sym} non aggiornato: {str(e)[:60]}", flush=True)
        s = store.load(sid)
        if not s.empty:
            out[k] = s
    return out


def lag(s: pd.Series, giorni: int) -> pd.Series:
    """Sposta in avanti la data di disponibilita' di un dato (un dato economico arriva dopo, non il giorno a cui si riferisce)."""
    s = s.dropna().copy()
    s.index = s.index + pd.Timedelta(days=giorni)
    return s[~s.index.duplicated(keep="last")]


def pct_esp(s: pd.Series) -> pd.Series:
    """Percentile di ogni valore rispetto a tutto il passato (mai al futuro)."""
    s = s.dropna()
    nativo_mensile = len(s) > 10 and (s.index[-1] - s.index[0]).days / len(s) > 10
    return s.expanding(min_periods=60 if nativo_mensile else 252).rank(pct=True)


def zroll(x: pd.Series, fin: int = 1260, minimo: int = 750) -> pd.Series:
    return (x - x.rolling(fin, min_periods=minimo).mean()) / x.rolling(fin, min_periods=minimo).std()


def proxy_misure(P: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    liv, acc, zz = {}, {}, {}
    for nome, (a, b) in PROXY.items():
        if a not in P or b not in P:
            continue
        r = np.log(P[a] / P[b].reindex(P[a].index)).dropna()
        z = zroll(r)
        d63 = r - r.shift(63)
        a1 = zroll(d63)
        a2 = zroll(d63 - d63.shift(63))
        idx = a2.dropna().index.union(a1.dropna().index)
        liv[nome] = pct_esp(z.dropna())
        acc[nome] = (pct_esp(a1.dropna()).reindex(idx) + pct_esp(a2.dropna()).reindex(idx)) / 2
        zz[nome] = z
    return pd.DataFrame(liv), pd.DataFrame(acc), pd.DataFrame(zz)


def inneschi(cal: pd.DatetimeIndex) -> pd.DataFrame:
    """I quattro segnali di rottura (tassi, banca centrale, credito, condizioni finanziarie), ognuno vero se e' nel 20% peggiore della sua storia."""
    L = lambda k: store.load(k).dropna()  # noqa: E731
    r1 = pct_esp(lag(L("dgs10"), 1).diff(63).dropna())
    r2 = pct_esp(lag(L("fedfunds"), 1).diff(126).dropna())
    spread_m = (L("baa_lungo") - L("gs10_m").reindex(L("baa_lungo").index)).dropna()
    c_m = pct_esp(lag(spread_m, 35).diff(3).dropna())
    c_d = pct_esp(lag(L("baa10y"), 1).diff(63).dropna())
    c1 = pd.concat([c_m[c_m.index < "1986-06-01"], c_d[c_d.index >= "1986-06-01"]])
    f1 = pct_esp(lag(L("nfci"), 5).diff(13).dropna())
    df = pd.DataFrame({k: s.reindex(cal, method="ffill") for k, s in {"R1": r1, "R2": r2, "C1": c1, "F1": f1}.items()})
    vera = df >= SOGLIA
    disp = df.notna()
    rt = (vera.sum(axis=1) >= 2) & (disp.sum(axis=1) >= 2)
    return pd.DataFrame({**{k: vera[k] & disp[k] for k in df}, "RT": rt, "n_disp": disp.sum(axis=1)})


def calcola(P: dict[str, pd.Series], sp: pd.Series) -> pd.DataFrame:
    """Serie giornaliera dal 1971: livello, accelerazione, z, inversione di leadership, segnali di rottura e stati."""
    cal = sp.index[sp.index >= INIZIO]
    liv, acc, zz = proxy_misure(P)
    LIV = liv.mean(axis=1).reindex(cal, method="ffill")
    ACC = acc.mean(axis=1).reindex(cal, method="ffill")
    Z = zz.mean(axis=1).reindex(cal, method="ffill")
    alto, acce = LIV >= SOGLIA, ACC >= SOGLIA
    rec = LIV.rolling(126, min_periods=1).max() >= SOGLIA
    inv = rec & (Z < Z.rolling(63, min_periods=40).mean())   # la guida passa ad altri settori dopo un massimo di sbilanciamento
    inn = inneschi(cal)
    rt = inn["RT"]
    out = pd.DataFrame({"livello": LIV, "accel": ACC, "z": Z, "inversione": inv, "R1": inn["R1"], "R2": inn["R2"], "C1": inn["C1"], "F1": inn["F1"], "rottura": rt})
    out["S1"] = alto & acce
    out["S3"] = alto & acce & rt
    out["S4"] = alto & inv
    out["riprezzamento"] = alto & (inv | rt) & ~out["S1"]
    for k in liv.columns:
        out["liv_" + k] = liv[k].reindex(cal, method="ffill")
        out["acc_" + k] = acc[k].reindex(cal, method="ffill")
    out["fase"] = np.select([out["S1"], out["riprezzamento"], alto], ["carico", "riprezzamento", "alto"], default="calmo")
    return out


# ----------------------------------------------------------------------------- statistiche sugli episodi passati
def inizi_episodi(stato: pd.Series, gap: int = 126) -> list[int]:
    """Posizioni del primo giorno di ogni episodio: due accensioni a meno di `gap` sedute di distanza sono lo stesso episodio."""
    idx = np.flatnonzero(stato.to_numpy())
    if not len(idx):
        return []
    out = [int(idx[0])]
    for a, b in zip(idx[:-1], idx[1:]):
        if b - a >= gap:
            out.append(int(b))
    return out


def episodio_carico(p: np.ndarray, i0: int, finestra: int = 378, calo: float = 0.10) -> dict:
    """Dall'accensione: quanto e' salito il prezzo prima del picco, dopo quanto tempo, e se e' arrivato un calo di almeno il 10% dal massimo."""
    fine = min(len(p) - 1, i0 + finestra)
    mass, ip = p[i0], i0
    scatto = None
    for i in range(i0 + 1, fine + 1):
        if p[i] > mass:
            mass, ip = p[i], i
        elif p[i] <= mass * (1 - calo):
            scatto = i
            break
    if scatto is None and fine - i0 < finestra:
        return {"completo": False}
    fondo = p[ip:min(len(p), ip + 127)].min()
    return {"completo": True, "calo_arrivato": scatto is not None, "salita": float(mass / p[i0] - 1), "sedute_al_picco": int(ip - i0),
            "sedute_al_calo": None if scatto is None else int(scatto - i0), "calo_dal_picco": float(fondo / mass - 1)}


def episodio_riprezzamento(p: np.ndarray, i0: int, finestra: int = 126) -> dict:
    fine = min(len(p) - 1, i0 + finestra)
    if fine - i0 < finestra:
        return {"completo": False}
    w = p[i0:fine + 1]
    return {"completo": True, "calo": float(w.min() / p[i0] - 1), "sedute_al_minimo": int(w.argmin())}


def statistiche(sp: pd.Series, m: pd.DataFrame, dal: str = "1990-01-01") -> dict:
    """Numeri storici (solo dal 1990, quando l'indizio compare) per i testi della scheda. Sono descrittivi: pochi episodi."""
    p = sp.reindex(m.index).to_numpy()
    out: dict = {"dal": dal[:4]}
    c = [(i, episodio_carico(p, i)) for i in inizi_episodi(m["S1"]) if m.index[i] >= pd.Timestamp(dal)]
    cc = [e for _, e in c if e.get("completo")]
    if cc:
        sal = [e["salita"] for e in cc]
        arr = [e for e in cc if e["calo_arrivato"]]
        out["carico"] = {"episodi": len(c), "valutabili": len(cc), "con_calo": len(arr),
                         "salita_mediana": float(np.median(sal)), "salita_media": float(np.mean(sal)),
                         "mesi_al_picco_mediana": float(np.median([e["sedute_al_picco"] for e in cc]) / 21),
                         "mesi_al_calo_mediana": float(np.median([e["sedute_al_calo"] for e in arr]) / 21) if arr else None,
                         "mesi_al_calo_max": float(max(e["sedute_al_calo"] for e in arr) / 21) if arr else None,
                         "calo_mediano": float(np.median([e["calo_dal_picco"] for e in arr])) if arr else None,
                         "date": [str(m.index[i].date()) for i, _ in c]}
    # confronto: un giorno qualunque dello stesso periodo (uno ogni 5 sedute)
    giorni = [i for i in range(0, len(m), 5) if m.index[i] >= pd.Timestamp(dal)]
    bc = [e for e in (episodio_carico(p, i) for i in giorni) if e.get("completo")]
    br = [e for e in (episodio_riprezzamento(p, i) for i in giorni) if e.get("completo")]
    out["base"] = {"calo10_18mesi": float(np.mean([e["calo_arrivato"] for e in bc])) if bc else None,
                   "salita_mediana": float(np.median([e["salita"] for e in bc])) if bc else None,
                   "calo5_6mesi": float(np.mean([e["calo"] <= -0.05 for e in br])) if br else None,
                   "calo_mediano": float(np.median([e["calo"] for e in br])) if br else None,
                   "calo8_6mesi": float(np.mean([e["calo"] <= -0.08 for e in br])) if br else None}
    r = [(i, episodio_riprezzamento(p, i)) for i in inizi_episodi(m["riprezzamento"]) if m.index[i] >= pd.Timestamp(dal)]
    rr = [e for _, e in r if e.get("completo")]
    if rr:
        out["riprezzamento"] = {"episodi": len(r), "valutabili": len(rr), "con_calo_5": int(sum(e["calo"] <= -0.05 for e in rr)), "con_calo_8": int(sum(e["calo"] <= -0.08 for e in rr)),
                                "calo_mediano": float(np.median([e["calo"] for e in rr])), "calo_medio": float(np.mean([e["calo"] for e in rr])),
                                "mesi_al_minimo_mediana": float(np.median([e["sedute_al_minimo"] for e in rr]) / 21)}
    return out


def oggi_in_episodio(sp: pd.Series, m: pd.DataFrame, colonna: str) -> dict | None:
    """Se lo stato e' acceso oggi: da quanti giorni e di quanto e' salito/sceso il prezzo da quando e' iniziato."""
    s = m[colonna]
    if not bool(s.iloc[-1]):
        return None
    i0 = inizi_episodi(s)[-1]   # l'ultimo inizio e' quello dell'episodio in corso
    p = sp.reindex(m.index)
    return {"dal": str(m.index[i0].date()), "sedute": int(len(m) - 1 - i0), "variazione": float(p.iloc[-1] / p.iloc[i0] - 1)}


def analoghi(sp: pd.Series, m: pd.DataFrame, orizzonte: int = 126, k: int = 300, dal: str = "1990-01-01") -> dict | None:
    """Situazioni analoghe del passato: i `k` giorni dal 1990 con livello e accelerazione piu' vicini a quelli di oggi
    (esclusi gli ultimi 6 mesi, che non hanno ancora il futuro). Per ognuno: quanto e' salito al massimo, quanto e' sceso al minimo
    e dove si trovava dopo `orizzonte` sedute (circa 6 mesi). Si usa l'S&P 500 perche' ha storia lunga; il VWCE (mondo) e' piu' diversificato."""
    from numpy.lib.stride_tricks import sliding_window_view as swv
    p = sp.reindex(m.index).to_numpy(dtype=float)
    n = len(p)
    if n <= orizzonte + k:
        return None
    w = swv(p, orizzonte + 1)                      # riga i = prezzi da i a i+orizzonte
    fin = w[:, -1] / w[:, 0] - 1
    mx = w[:, 1:].max(axis=1) / w[:, 0] - 1
    mn = w[:, 1:].min(axis=1) / w[:, 0] - 1
    liv, acc = m["livello"].to_numpy()[: len(w)], m["accel"].to_numpy()[: len(w)]
    ok = (m.index[: len(w)] >= pd.Timestamp(dal)) & ~np.isnan(liv) & ~np.isnan(acc)
    d = np.where(ok, np.hypot(liv - m["livello"].iloc[-1], acc - m["accel"].iloc[-1]), np.inf)
    sel = np.sort(np.argsort(d)[:k])
    ep = 1 + int(np.sum(np.diff(sel) >= orizzonte))

    def q(x, qs):
        return [float(np.quantile(x, a)) for a in qs]
    base = ok
    return {"orizzonte_sedute": orizzonte, "giorni": int(len(sel)), "episodi": ep, "distanza_max": float(d[sel].max()),
            "salita_max": dict(zip(("p25", "med", "p75"), q(mx[sel], (.25, .5, .75)))),
            "calo_max": dict(zip(("p25", "med", "p75"), q(mn[sel], (.25, .5, .75)))),
            "fine": dict(zip(("p10", "med", "p90"), q(fin[sel], (.1, .5, .9)))),
            "base": {"salita_max_med": float(np.median(mx[base])), "calo_max_med": float(np.median(mn[base])), "fine_med": float(np.median(fin[base]))}}


# ----------------------------------------------------------------------------- uscita giornaliera
def _serie_grafico(s: pd.Series) -> dict | None:
    """Settimanale fino al 2020 e giornaliero dopo (grafico leggero); stesso formato compatto degli altri indici."""
    s = s.dropna()
    vecchio = s[s.index < "2021-01-01"].resample("W-FRI").last().dropna()
    nuovo = s[s.index >= "2021-01-01"]
    s = pd.concat([vecchio, nuovo])
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 10:
        return None
    t = (s.index.normalize() - pd.Timestamp("1970-01-01")).days.astype(int).tolist()
    return {"t0": t[0], "dt": [0] + [t[i] - t[i - 1] for i in range(1, len(t))], "v": [int(round(float(x) * 10)) for x in s.values]}


def testo_stato(fase: str, stat: dict, ep: dict | None) -> dict:
    """Frase piccola sotto il numero: margine tipico ancora disponibile, oppure calo tipico in programma, oppure nessun allarme.
    Le frasi lunghe dicono sempre anche cosa succede in un giorno qualunque, cosi' si vede se la differenza c'e'."""
    car, rip, base = stat.get("carico"), stat.get("riprezzamento"), stat.get("base", {})
    so_far = ep["variazione"] if ep else 0.0
    if fase == "carico" and car:
        res = max(0.0, car["salita_mediana"] - so_far)
        det = (f"Da quando lo stato è acceso il mercato è salito del {so_far * 100:+.1f}%. Dal {stat['dal']}, in {car['episodi']} casi simili la salita tipica prima del picco è stata "
               f"+{car['salita_mediana'] * 100:.0f}% in circa {car['mesi_al_picco_mediana']:.0f} mesi (in un giorno qualunque +{(base.get('salita_mediana') or 0) * 100:.0f}%). "
               f"Poi è arrivato un calo di almeno il 10% in {car['con_calo']} casi su {car['valutabili']}, dopo circa {car['mesi_al_calo_mediana'] or 0:.0f} mesi (mai oltre {car['mesi_al_calo_max'] or 0:.0f}); "
               f"in un giorno qualunque succede nel {(base.get('calo10_18mesi') or 0) * 100:.0f}% dei casi. Calo tipico dal picco: {(car['calo_mediano'] or 0) * 100:.0f}%.")
        return {"tipo": "margine", "valore": res, "riga": f"margine tipico ancora +{res * 100:.0f}% prima del calo", "dettaglio": det}
    if fase == "riprezzamento" and rip:
        res = min(0.0, rip["calo_mediano"] - so_far)
        det = (f"Fase in cui lo sbilanciamento è alto e la guida del mercato sta cambiando o tassi e credito si stringono. Dal {stat['dal']}, in {rip['episodi']} casi nei 6 mesi successivi "
               f"il calo tipico dal punto di partenza è stato {rip['calo_mediano'] * 100:.0f}% (medio {rip['calo_medio'] * 100:.0f}%), massimo dopo circa {rip['mesi_al_minimo_mediana']:.0f} mesi. "
               f"In un giorno qualunque il calo tipico a 6 mesi è {(base.get('calo_mediano') or 0) * 100:.0f}%: la differenza è piccola. "
               f"Un calo forte (8% o più) è arrivato in {rip['con_calo_8']} casi su {rip['valutabili']}, contro il {(base.get('calo8_6mesi') or 0) * 100:.0f}% dei giorni normali: "
               "questa fase non è, finora, un segnale di crollo imminente ma di assestamento. Indicazione debole.")
        return {"tipo": "calo", "valore": res, "riga": f"fase di riprezzamento: calo tipico {rip['calo_mediano'] * 100:.0f}%", "dettaglio": det}
    if fase == "alto":
        return {"tipo": "alto", "valore": None, "riga": "sbilanciato, senza accelerazione", "dettaglio": "Lo sbilanciamento è alto ma non sta accelerando: nessun segnale."}
    return {"tipo": "calmo", "valore": None, "riga": "nessun allarme", "dettaglio": "Lo sbilanciamento non è nella fascia alta della sua storia."}


def costruisci(P: dict[str, pd.Series] | None = None) -> dict:
    P = P or aggiorna_prezzi()
    sp = store.load("sp500").dropna()
    sp = sp[sp.index >= "1971-01-01"]
    m = calcola(P, sp)
    m = m[m["livello"].notna()]
    stat = statistiche(sp, m)
    u = m.iloc[-1]
    fase = str(u["fase"])
    col = {"carico": "S1", "riprezzamento": "riprezzamento"}.get(fase)
    ep = oggi_in_episodio(sp, m, col) if col else None
    txt = testo_stato(fase, stat, ep)
    an = analoghi(sp, m)
    sovr = (m["livello"] * 100).round(1)
    tr = float(sovr.iloc[-1] - sovr.iloc[-6]) if len(sovr) > 5 else 0.0
    out = {"data": str(m.index[-1].date()), "sovraccarico": float(sovr.iloc[-1]), "accelerazione": float(m["accel"].iloc[-1] * 100), "z": float(u["z"]),
           "tendenza": tr, "fase": fase, "fase_nome": FASI[fase], "testo": txt, "analoghi": an, "episodio_in_corso": ep, "statistiche": stat,
           "inversione": bool(u["inversione"]), "rottura": bool(u["rottura"]), "inneschi": {k: bool(u[k]) for k in ("R1", "R2", "C1", "F1")},
           "proxy": {k[4:]: {"livello": float(u[k]), "accel": float(u["acc_" + k[4:]])} for k in m.columns if k.startswith("liv_") and pd.notna(u[k])},
           "serie": {"sovr": _serie_grafico(sovr), "acc": _serie_grafico((m["accel"] * 100).round(1))}}
    out["_riga_registro"] = {"data": out["data"], "sp500": round(float(sp.iloc[-1]), 2), "sovraccarico": out["sovraccarico"], "accelerazione": round(out["accelerazione"], 1),
                             "z": round(out["z"], 3), "inversione": int(out["inversione"]), "rottura": int(out["rottura"]),
                             **{k: int(v) for k, v in out["inneschi"].items()}, "fase": fase,
                             **({"an_giorni": an["giorni"], "an_episodi": an["episodi"], "an_salita_med": round(an["salita_max"]["med"], 4), "an_calo_med": round(an["calo_max"]["med"], 4),
                                 "an_fine_med": round(an["fine"]["med"], 4)} if an else {}),
                             **{f"liv_{k}": round(v["livello"], 4) for k, v in out["proxy"].items()}, **{f"acc_{k}": round(v["accel"], 4) for k, v in out["proxy"].items()}}
    return out


def registra(riga: dict) -> None:
    """Una riga per ogni giorno di borsa: serve a verificare in avanti, fra qualche mese, se l'indizio regge."""
    new = pd.DataFrame([riga])
    old = pd.read_csv(REG) if REG.exists() else pd.DataFrame()
    m = pd.concat([old, new], ignore_index=True).drop_duplicates(subset=["data"], keep="last").sort_values("data")
    m.to_csv(REG, index=False)


def run() -> dict:
    out = costruisci()
    riga = out.pop("_riga_registro")
    registra(riga)
    ARCH.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[concentrazione] {out['data']}: sovraccarico {out['sovraccarico']:.0f}, accelerazione {out['accelerazione']:.0f}, fase {out['fase']}", flush=True)
    return out


def leggi() -> dict | None:
    try:
        return json.loads(ARCH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def riga_analoghi(an: dict | None) -> str:
    """Frase breve per la tessera: dove e' arrivato, al massimo e al minimo, il mercato nei 6 mesi dopo situazioni simili."""
    if not an:
        return ""
    return f"6 mesi dopo casi simili: fino a {an['salita_max']['med'] * 100:+.0f}% · giù a {an['calo_max']['med'] * 100:+.0f}%"


def testo_analoghi(an: dict | None) -> str:
    if not an:
        return ""
    sm, cm, f, b = an["salita_max"], an["calo_max"], an["fine"], an["base"]
    return (f"Situazioni analoghe del passato (dal 1990, {an['giorni']} giorni in {an['episodi']} periodi distinti con sbilanciamento e accelerazione simili a oggi): nei 6 mesi successivi il mercato "
            f"ha toccato in tipico {sm['med'] * 100:+.0f}% al massimo (un caso su quattro oltre {sm['p75'] * 100:+.0f}%) e {cm['med'] * 100:+.0f}% al minimo (un caso su quattro sotto {cm['p25'] * 100:+.0f}%); "
            f"dopo 6 mesi si trovava in tipico a {f['med'] * 100:+.0f}% (otto casi su dieci fra {f['p10'] * 100:+.0f}% e {f['p90'] * 100:+.0f}%). "
            f"In un giorno qualunque: massimo {b['salita_max_med'] * 100:+.0f}%, minimo {b['calo_max_med'] * 100:+.0f}%, a 6 mesi {b['fine_med'] * 100:+.0f}%. "
            "Calcolato sull'S&P 500, perché il VWCE ha solo pochi anni di storia: il VWCE (in euro, diversificato sul mondo) può differire. Sono statistiche passate, non una previsione.")
