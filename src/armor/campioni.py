"""SFIDANTI IN PROVA (dalla patch 26, PIANO_ARMOR3 Fase 0). Il numero principale è SEMPRE A1; FHS+VIX è affiancato, etichettato «sperimentale».
`sfidante()` calcola FHS+VIX e lo mette in pred[hz]['sfidante']; `applica()` (patch 24) non è più chiamata dal ciclo giornaliero, resta solo per i test.
La tabella sotto resta come informazione: la scelta fu fatta guardando la stessa valutazione, quindi NON è una prova. Decide il diario dal vivo.
Revisione descrittiva: 10 maggio 2027 (nessuna promozione automatica).

Un motore per ogni orizzonte (1 settimana, 1 mese, 3 mesi, 6 mesi): per ciascuno si usa quello che nella verifica funziona meglio.

Fonte: data/model_eval.json (valutazione walk-forward 1994-oggi di `valuta-modelli`, previsioni fatte solo con i dati noti a ogni data,
rifatta ogni mese). Regola fissa (decisa a novembre 2026 guardando quella stessa valutazione: c'è quindi un po' di scelta a posteriori,
per questo il confronto in ombra continua e la scelta si rifà ogni mese):
per l'orizzonte h e la soglia principale (config.PRIMARY), uno sfidante sostituisce A1 solo se
  1) ha BSS migliore di almeno 0,005 sia nel 2000-2012 sia nel 2013-oggi;
  2) l'AUC non è peggiore di oltre 0,01;
  3) sulle altre soglie dello stesso orizzonte il BSS non è peggiore di oltre 0,005.
Tra gli sfidanti che passano vince quello con il BSS più alto nel suo sottoperiodo peggiore. Sfidanti ammessi: FHS e FHS+VIX
(simulazione GARCH, eventualmente corretta con il VIX), perché si possono calcolare ogni giorno. Se nessuno passa resta A1."""
import json

import pandas as pd

from . import store
from .config import DATA, HORIZONS, PRIMARY, TARGETS
from .model import VERDICT, level_of

FILE = DATA / "campioni.json"
EVAL = DATA / "model_eval.json"
CANDIDATI = ["FHS", "FHS+VIX"]
NOMI = {"A1": "A1 (regressione logistica sui prezzi)", "FHS": "FHS (simulazione GARCH)", "FHS+VIX": "FHS + VIX (simulazione corretta con il VIX)"}
HZ_IT = {"10g": "10 giorni (circa una settimana e mezza)", "1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi"}


def scegli(metrics) -> dict:
    m = pd.DataFrame(metrics)
    m = m[(m["set"] == "modelli") & (m["kind"] == "down")]
    out = {}
    for hz in HORIZONS:
        g = m[m["hz"] == hz]
        a = g[(g["model"] == "A1") & (g["thr"] == PRIMARY[hz])]
        if a.empty:
            out[hz] = {"motore": "A1", "motivo": "valutazione non disponibile"}
            continue
        a = a.iloc[0]
        best, det = None, {}
        for c in CANDIDATI:
            r = g[(g["model"] == c) & (g["thr"] == PRIMARY[hz])]
            if r.empty:
                continue
            r = r.iloc[0]
            ok1 = r["bss_2000_12"] - a["bss_2000_12"] >= 0.005 and r["bss_2013_26"] - a["bss_2013_26"] >= 0.005
            ok2 = r["auc"] >= a["auc"] - 0.01
            ok3 = True
            for thr in TARGETS[hz]:
                if thr == PRIMARY[hz]:
                    continue
                ca, cc = g[(g["model"] == "A1") & (g["thr"] == thr)], g[(g["model"] == c) & (g["thr"] == thr)]
                if len(ca) and len(cc) and cc.iloc[0]["bss"] < ca.iloc[0]["bss"] - 0.005:
                    ok3 = False
            score = min(r["bss_2000_12"], r["bss_2013_26"])
            det[c] = {"bss_2000_12": round(float(r["bss_2000_12"]), 4), "bss_2013_26": round(float(r["bss_2013_26"]), 4), "auc": round(float(r["auc"]), 3),
                      "passa": bool(ok1 and ok2 and ok3)}
            if ok1 and ok2 and ok3 and (best is None or score > best[1]):
                best = (c, score)
        out[hz] = {"motore": best[0] if best else "A1",
                   "a1": {"bss_2000_12": round(float(a["bss_2000_12"]), 4), "bss_2013_26": round(float(a["bss_2013_26"]), 4), "auc": round(float(a["auc"]), 3)},
                   "sfidanti": det}
    return out


def aggiorna() -> dict:
    try:
        ev = json.loads(EVAL.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return load()
    d = {"date": ev.get("date"), "orizzonti": scegli(ev["metrics"])}
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[campioni] motore per orizzonte:", {hz: v["motore"] for hz, v in d["orizzonti"].items()}, flush=True)
    return d


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def applica(pred: dict, p: pd.Series, t, mid: str, camp: dict | None = None, fhs_fn=None) -> tuple[dict, str]:
    """Sostituisce le probabilità degli orizzonti in cui vince uno sfidante. A1 resta salvato in pred[hz]['p_a1']."""
    camp = camp if camp is not None else load()
    oz = (camp or {}).get("orizzonti", {})
    usati = {hz: v["motore"] for hz, v in oz.items() if v.get("motore") in CANDIDATI and hz in pred}
    if not usati:
        return pred, mid
    if fhs_fn is None:
        from . import fhs
        fhs_fn = fhs.forecast
    seed = int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31)
    cache = {}
    for hz, motore in usati.items():
        try:
            if motore not in cache:
                vix = None
                if motore == "FHS+VIX":
                    v = store.load("vix").dropna()
                    v = v[v.index <= pd.Timestamp(t)]
                    vix = float(v.iloc[-1]) if len(v) else None
                cache[motore] = fhs_fn(p, date=t, sims=5000, seed=seed, vix=vix, w=0.5 if motore == "FHS+VIX" else 0.0)
            f = cache[motore]
            r = pred[hz]
            new = {thr: float(f[hz]["down"][thr]["p"]) for thr in r["p"]}
            r["p_a1"], r["p"], r["motore"] = dict(r["p"]), new, motore
            prim = PRIMARY[hz]
            r["ratio"] = new[prim] / r["base"][prim] if r["base"][prim] > 0 else 1.0
            r["level"] = level_of(r["ratio"])
            r["verdict"] = VERDICT[r["level"]]
        except Exception as e:  # noqa: BLE001
            print(f"[campioni] {motore} non calcolato per {hz}, resta A1:", str(e)[:80], flush=True)
            usati[hz] = None
    ok = {hz: m for hz, m in usati.items() if m}
    if not ok:
        return pred, mid
    coerenza(pred)
    tag = "+".join(sorted({m.replace("+VIX", "V") for m in ok.values()}))
    return pred, f"{mid}+{tag}({','.join(h for h in HORIZONS if h in ok)})"


REVISIONE = "10 maggio 2027"
DIVERGENZA_PUNTI, DIVERGENZA_RAPPORTO = 0.05, 2.0


def divergenza(p_a1: float, p_sf: float) -> bool:
    """Badge «Divergenza»: differenza di almeno 5 punti e rapporto almeno 2 (in entrambe le direzioni)."""
    if abs(p_sf - p_a1) < DIVERGENZA_PUNTI - 1e-12:
        return False
    lo, hi = sorted((p_a1, p_sf))
    return hi >= DIVERGENZA_RAPPORTO * max(lo, 1e-9)


def _vix_a(t) -> float | None:
    v = store.load("vix").dropna()
    v = v[v.index <= pd.Timestamp(t)]
    return float(v.iloc[-1]) if len(v) and (pd.Timestamp(t) - v.index[-1]).days < 7 else None


def sfidante(pred: dict, p: pd.Series, t, fhs_fn=None, vix: float | None = None) -> dict:
    """Aggiunge a ogni orizzonte pred[hz]['sfidante'] = {'motore': 'FHS+VIX', 'p': {...}, 'div': bool}. Le probabilità principali NON cambiano."""
    if fhs_fn is None:
        from . import fhs
        fhs_fn = fhs.forecast
    try:
        vix = vix if vix is not None else _vix_a(t)
        seed = int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31)
        f = fhs_fn(p, date=t, sims=5000, seed=seed, vix=vix, w=0.5)
    except Exception as e:  # noqa: BLE001
        print("[sfidante] FHS+VIX non calcolato:", str(e)[:80], flush=True)
        return pred
    for hz, r in pred.items():
        if hz not in HORIZONS or hz not in f:
            continue
        try:
            sp = {thr: float(f[hz]["down"][thr]["p"]) for thr in r["p"]}
            prim = PRIMARY[hz]
            r["sfidante"] = {"motore": "FHS+VIX", "p": sp, "div": divergenza(r["p"][prim], sp[prim]), "vix": vix}
        except Exception as e:  # noqa: BLE001
            print(f"[sfidante] {hz}:", str(e)[:60], flush=True)
    return pred


def avvisi_coerenza(pred: dict) -> list[str]:
    """Controllo (senza modificare i numeri): un calo entro un orizzonte più lungo non può essere meno probabile dello stesso calo entro uno più breve."""
    out, visti = [], {}
    for hz in sorted((h for h in pred if h in HORIZONS), key=lambda h: HORIZONS[h]):
        for thr, v in pred[hz]["p"].items():
            if thr in visti and v < visti[thr][1] - 1e-9:
                out.append(f"calo ≥{thr}%: {HZ_IT.get(hz, hz)} {v:.0%} è sotto {HZ_IT.get(visti[thr][0], visti[thr][0])} {visti[thr][1]:.0%}")
            if thr not in visti or v > visti[thr][1]:
                visti[thr] = (hz, v)
    return out


def coerenza(pred: dict) -> dict:
    """Con motori diversi per orizzonte, un calo entro 6 mesi non può essere meno probabile dello stesso calo entro 3 mesi:
    per ogni soglia si prende il massimo con gli orizzonti più brevi (e si annota quando succede)."""
    visti: dict = {}
    for hz in sorted((h for h in pred if h in HORIZONS), key=lambda h: HORIZONS[h]):
        r = pred[hz]
        cambiato = False
        for thr in list(r["p"]):
            if thr in visti and r["p"][thr] < visti[thr]:
                r["p"][thr] = visti[thr]
                cambiato = True
            visti[thr] = max(visti.get(thr, 0.0), r["p"][thr])
        if cambiato:
            prim = PRIMARY[hz]
            r["ratio"] = r["p"][prim] / r["base"][prim] if r["base"][prim] > 0 else 1.0
            r["level"] = level_of(r["ratio"])
            r["verdict"] = VERDICT[r["level"]]
            r["coerenza"] = True
    return pred


def html() -> str:
    d = load()
    oz = d.get("orizzonti") or {}
    if not oz:
        return ""
    f = lambda x: "n.d." if x is None else f"{x:+.3f}".replace(".", ",")
    rows = ""
    for hz in HORIZONS:
        v = oz.get(hz)
        if not v:
            continue
        a1 = v.get("a1", {})
        sf = v.get("sfidanti", {})
        best = sf.get(v["motore"], {}) if v["motore"] != "A1" else {}
        alt = "; ".join(f"{c}: {f(x['bss_2000_12'])} / {f(x['bss_2013_26'])}{' ✓' if x['passa'] else ''}" for c, x in sf.items())
        rows += (f"<div class='rmr'><div class='rmh'><b>{HZ_IT.get(hz, hz)}</b><span class='badge {'ok' if v['motore'] != 'A1' else 'warn'}'>{'sfidante che passa la vecchia regola: ' + NOMI.get(v['motore'], v['motore']) if v['motore'] != 'A1' else 'nessuno sfidante passa la regola'}</span></div>"
                 f"<div class='rmg'><div><span>A1: BSS 2000-12 / 2013-oggi</span>{f(a1.get('bss_2000_12'))} / {f(a1.get('bss_2013_26'))}</div>"
                 f"<div><span>Sfidanti</span>{alt or 'nessuno'}</div></div></div>")
    return ("<p><b>Il numero principale è A1.</b> FHS+VIX è affiancato come «sperimentale»: la tabella sotto mostra come sarebbe andato nella valutazione storica "
            "(1994-oggi, con i dati noti a ogni data), ma la regola era stata fissata guardando quella stessa valutazione, quindi <b>non è una prova</b>. "
            f"Decide il diario dal vivo: prima revisione descrittiva il {REVISIONE}, nessuna promozione automatica.</p>" + rows +
            "<p class='mu'>BSS: quanto la probabilità è migliore della semplice frequenza storica (0 = uguale; più alto = meglio).</p>")
