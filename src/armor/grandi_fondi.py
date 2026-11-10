"""Grandi fondi (Patch 61-62): cosa fanno i grandi operatori e se i loro movimenti hanno mai anticipato i cali. PESO ZERO nel modello.
Segnali disponibili in modo verificabile (dati pubblici settimanali, già scaricati dall'app):
  - liquidità nei fondi monetari USA (FRED WRMFNS): crescita su 13 settimane;
  - futures E-mini S&P 500 (CFTC): posizione netta di fondi a leva, gestori patrimoniali e intermediari (dealer).
Dati SEC (sec_dati.py): 13F trimestrali (protezioni e quota in ETF indicizzati dei 50 maggiori fondi, pannello fissato dal trimestre precedente, disponibili 46 giorni dopo la fine del trimestre), Form 4 degli insider (acquisti su acquisti+vendite, 13 settimane), nuovi depositi Schedule 13D (13 settimane).
Regola fissata prima di guardare i dati (vedi PROTOCOLLO_GRANDI_FONDI.md):
  percentile = posizione del valore dentro gli ultimi 5 anni (solo passato); «alto» >= 80, «basso» <= 20;
  bersagli: calo >= 5% entro 1 mese e calo >= 10% entro 3 mesi (S&P 500, massimo calo dal giorno della lettura);
  ritardo di pubblicazione: i dati CFTC valgono 4 giorni dopo la data, i fondi monetari 2 giorni dopo;
  un segnale è «dimostrato» solo se la differenza tra la frequenza dei cali con segnale alto (o basso) e quella normale ha intervallo al 90% (a blocchi)
  che esclude lo zero, nella stessa direzione, sia nella prima sia nella seconda metà della storia disponibile, su entrambi i bersagli."""
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA

FILE = DATA / "grandi_fondi.json"
REGISTRO = DATA / "grandi_fondi_badge_registro.csv"
BERSAGLI = (("1m", 5), ("3m", 10))
FINESTRA = 260       # 5 anni di settimane
MIN_OBS = 104
ALTO, BASSO = 80.0, 20.0
# chiave: (nome, ritardo di pubblicazione in giorni, finestra del percentile, osservazioni minime)
SEGNALI = {
    "mmf": ("Liquidità nei fondi monetari (crescita a 13 settimane)", 2, FINESTRA, MIN_OBS),
    "cot_lev": ("Fondi a leva sui futures S&P 500 (posizione netta)", 4, FINESTRA, MIN_OBS),
    "cot_am": ("Gestori patrimoniali sui futures S&P 500 (posizione netta)", 4, FINESTRA, MIN_OBS),
    "cot_dealer": ("Intermediari (dealer) sui futures S&P 500 (posizione netta)", 4, FINESTRA, MIN_OBS),
    "f13_protezione": ("Protezioni sugli ETF indicizzati dei 50 maggiori fondi (13F, trimestrale)", 46, 20, 12),
    "f13_indicizzati": ("Quota in ETF indicizzati dei 50 maggiori fondi (13F, trimestrale)", 46, 20, 12),
    "insider": ("Acquisti degli insider sul totale acquisti+vendite (13 settimane)", 1, FINESTRA, MIN_OBS),
    "d13": ("Nuove partecipazioni oltre il 5% con intenti attivi, Schedule 13D (13 settimane)", 1, FINESTRA, MIN_OBS),
}


def percentile_mobile(s: pd.Series, finestra: int = FINESTRA, min_obs: int = MIN_OBS) -> pd.Series:
    """Percentile (0-100) di ogni valore dentro le ultime `finestra` osservazioni, incluso il valore stesso: nessun dato futuro."""
    v = s.dropna()
    out = np.full(len(v), np.nan)
    a = v.values
    for i in range(len(a)):
        w = a[max(0, i - finestra + 1): i + 1]
        if len(w) >= min_obs:
            out[i] = (w < a[i]).mean() * 100 + 0.5 * (w == a[i]).mean() * 100
    return pd.Series(out, index=v.index)


def carica_segnali() -> dict[str, pd.Series]:
    out = {}
    try:
        m = store.load("mmf_assets")
        if len(m) > MIN_OBS + 13:
            out["mmf"] = m.pct_change(13) * 100
    except Exception:  # noqa: BLE001
        pass
    for k, sid in (("cot_lev", "cot_lev_net"), ("cot_am", "cot_am_net"), ("cot_dealer", "cot_dealer_net")):
        try:
            s = store.load(sid)
            if len(s) > 30:
                out[k] = s
        except Exception:  # noqa: BLE001
            pass
    try:   # dati SEC (data/grandi_fondi/*.csv, prodotti da sec_dati.py)
        d = DATA / "grandi_fondi"
        if (d / "f13_segnali.csv").exists():
            f = pd.read_csv(d / "f13_segnali.csv", index_col=0, parse_dates=True)
            for k, c in (("f13_protezione", "protezione"), ("f13_indicizzati", "indicizzati")):
                if len(f) >= 14:
                    out[k] = f[c]
        if (d / "insider_settimane.csv").exists():
            i = pd.read_csv(d / "insider_settimane.csv", index_col=0, parse_dates=True)
            a, v = i["acquisti"].rolling(13).sum(), i["vendite"].rolling(13).sum()
            r = (a / (a + v)).dropna()
            if len(r) > MIN_OBS:
                out["insider"] = r
        if (d / "d13_settimane.csv").exists():
            n = pd.read_csv(d / "d13_settimane.csv", index_col=0, parse_dates=True)["n"].rolling(13).sum().dropna()
            if len(n) > MIN_OBS:
                out["d13"] = n
    except Exception:  # noqa: BLE001
        pass
    return {k: v[~v.index.duplicated(keep="last")].sort_index() for k, v in out.items()}


def su_giorni(pct: pd.Series, giorni: pd.DatetimeIndex, ritardo: int) -> pd.Series:
    """Percentile disponibile a ogni seduta, tenendo conto del ritardo di pubblicazione."""
    d = pct.dropna().copy()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d.index = d.index + pd.Timedelta(days=ritardo)
    return d.reindex(giorni, method="ffill")


def _blocco_ci(y: np.ndarray, grp: np.ndarray, step: int = 5, reps: int = 400, seed: int = 1):
    """Intervallo al 90% della differenza di frequenza tra gruppo (True) e resto, con blocchi di ~63 sedute."""
    n = len(y)
    L = max(int(np.ceil(63 / step)), 1)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / L))
    d = []
    for _ in range(reps):
        st = rng.integers(0, max(n - L, 1), nb)
        ix = np.concatenate([np.arange(s, min(s + L, n)) for s in st])[:n]
        g, yy = grp[ix], y[ix]
        if g.sum() < 5 or (~g).sum() < 5:
            continue
        d.append(yy[g].mean() - yy[~g].mean())
    if len(d) < 50:
        return (float("nan"), float("nan"))
    return float(np.percentile(d, 5)), float(np.percentile(d, 95))


def prova(p: pd.Series, pct_giorni: pd.Series, step: int = 5) -> dict:
    """Frequenza dei cali con segnale alto / basso / normale, con intervalli, sull'intera storia e sulle due metà."""
    from . import modeleval
    pg = pct_giorni.dropna()
    dates = pg.index[::step]
    res = {"n_date": int(len(dates)), "da": str(dates.min().date()) if len(dates) else None, "a": str(dates.max().date()) if len(dates) else None, "bersagli": {}}
    if len(dates) < 150:
        res["verdetto"] = "dati insufficienti"
        return res
    metà = dates[len(dates) // 2]
    segni = {}
    for hz, thr in BERSAGLI:
        y = modeleval.outcome(p, dates, hz, "down", thr)
        ok = y.notna().values
        yy, pp, dd = y.values[ok].astype(float), pg.reindex(dates).values[ok], dates[ok]
        r = {"freq_tutte": float(yy.mean())}
        for nome, grp in (("alto", pp >= ALTO), ("basso", pp <= BASSO)):
            blocchi = {}
            for etich, mm in (("tutta", np.ones(len(dd), bool)), ("prima_meta", dd < metà), ("seconda_meta", dd >= metà)):
                g, y2 = grp[mm], yy[mm]
                if g.sum() < 10 or (~g).sum() < 10:
                    blocchi[etich] = {"n": int(g.sum()), "freq": None, "diff": None}
                    continue
                lo, hi = _blocco_ci(y2, g, step)
                blocchi[etich] = {"n": int(g.sum()), "freq": float(y2[g].mean()), "freq_resto": float(y2[~g].mean()), "diff": float(y2[g].mean() - y2[~g].mean()), "lo": lo, "hi": hi}
            r[nome] = blocchi
            segni[(hz, thr, nome)] = [blocchi[k].get("lo") is not None and np.isfinite(blocchi[k].get("lo", np.nan)) and (blocchi[k]["lo"] > 0 or blocchi[k]["hi"] < 0)
                                      and (np.sign(blocchi[k]["diff"]) == np.sign(blocchi["tutta"]["diff"])) for k in ("prima_meta", "seconda_meta")] if blocchi["tutta"].get("diff") is not None else [False, False]
        res["bersagli"][f"{hz}_{thr}"] = r
    dim = []
    for nome in ("alto", "basso"):
        if all(all(segni[(hz, thr, nome)]) for hz, thr in BERSAGLI):
            dim.append(nome)
    res["verdetto"] = "dimostrato: " + ", ".join(dim) if dim else "nessun segnale dimostrato"
    return res


def stato(pct: float | None) -> str:
    if pct is None or not np.isfinite(pct):
        return "n.d."
    return "alto" if pct >= ALTO else ("basso" if pct <= BASSO else "normale")


def tensione_di(percentili: dict) -> dict | None:
    """«Tensione» dei grandi fondi, 1-100: quanto i loro segnali sono fuori dalla norma, senza dire in che direzione.
    Per ogni segnale 2 × |percentile − 50| (50° = nella norma → 0; 0° o 100° → 100); poi la media dei segnali disponibili.
    Direzione non assunta perché nessun segnale ha ancora dimostrato se «alto» o «basso» anticipi i cali: la prova resta a due code (alto e basso)."""
    v = {k: 2 * abs(p - 50) for k, p in percentili.items() if p is not None and np.isfinite(p)}
    if not v:
        return None
    return {"score": round(float(np.clip(np.mean(list(v.values())), 1, 100)), 1), "n": len(v), "dettaglio": {k: round(x, 1) for k, x in v.items()}}


def serie_tensione(giorni: pd.DatetimeIndex) -> pd.Series:
    """Tensione dei grandi fondi giorno per giorno sulla storia, con i ritardi di pubblicazione (nessun dato futuro)."""
    cols = {}
    for k, s in carica_segnali().items():
        nome, rit, fin, mino = SEGNALI[k]
        s = s[~s.index.duplicated(keep="last")].sort_index()
        pg = su_giorni(percentile_mobile(s, fin, mino), giorni, rit)
        cols[k] = 2 * (pg - 50).abs()
    if not cols:
        return pd.Series(np.nan, index=giorni)
    return pd.DataFrame(cols).mean(axis=1).clip(lower=1, upper=100)


MAX_STORIA = 270


def run(p: pd.Series | None = None) -> dict:
    from .features import closed_sp500
    p = closed_sp500() if p is None else p
    out = {"data": str(p.index[-1].date()), "segnali": {}}
    righe = []
    for k, s in carica_segnali().items():
        nome, rit, fin, mino = SEGNALI[k]
        s = s[~s.index.duplicated(keep="last")].sort_index()
        pct = percentile_mobile(s, fin, mino)
        pg = su_giorni(pct, p.index, rit)
        ult = pct.dropna()
        d = {"nome": nome, "ultimo_dato": str(s.dropna().index[-1].date()), "valore": float(s.dropna().iloc[-1]),
             "percentile": float(ult.iloc[-1]) if len(ult) else None, "n_osservazioni": int(s.dropna().shape[0])}
        d["stato"] = stato(d["percentile"])
        sv = s.dropna().iloc[-MAX_STORIA:]
        pc = pct.reindex(sv.index)
        sp = p.reindex(sv.index, method="ffill")
        d["storia"] = {"d": [str(i.date()) for i in sv.index], "v": [round(float(x), 3) for x in sv.values],
                       "p": [None if pd.isna(x) else round(float(x), 1) for x in pc.values], "sp": [None if pd.isna(x) else round(float(x), 1) for x in sp.values]}
        if len(ult) >= 2:
            d["precedente"] = {"data": str(s.dropna().index[-2].date()), "valore": float(s.dropna().iloc[-2]), "percentile": float(ult.iloc[-2])}
        if len(ult) >= 14 and k in ("cot_lev", "cot_am", "cot_dealer", "mmf", "insider", "d13"):
            d["trimestre_fa"] = {"data": str(ult.index[-14].date()), "percentile": float(ult.iloc[-14]), "valore": float(s.dropna().iloc[-14])}
        try:
            d["prova"] = prova(p, pg)
        except Exception as e:  # noqa: BLE001
            d["prova"] = {"verdetto": "prova non riuscita: " + str(e)[:60]}
        out["segnali"][k] = d
        righe.append({"data": out["data"], "segnale": k, "valore": round(d["valore"], 3), "percentile": None if d["percentile"] is None else round(d["percentile"], 1), "stato": d["stato"], "peso": 0})
    out["tensione"] = tensione_di({k: v.get("percentile") for k, v in out["segnali"].items()})
    FILE.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    if righe:
        try:
            old = pd.read_csv(REGISTRO)
            old = old[old["data"].astype(str) != out["data"]]
        except Exception:  # noqa: BLE001
            old = pd.DataFrame()
        pd.concat([old, pd.DataFrame(righe)], ignore_index=True).to_csv(REGISTRO, index=False)
    return out


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _pc(x):
    return "n.d." if x is None else f"{x * 100:.0f}%"


def html() -> str:
    from html import escape as e
    d = carica()
    intro = ("<div class='explain'><p><b>Che cos'è.</b> Cosa fanno i grandi operatori (fondi a leva, gestori patrimoniali, liquidità nei fondi monetari) e se in passato i loro movimenti "
             "hanno anticipato i cali dell'S&amp;P 500. <b>Qui non influiscono sulle previsioni</b>: sono informazioni di contesto finché non dimostrano di funzionare. "
             "«Percentile» = dove sta il valore di oggi rispetto agli ultimi 5 anni (100 = il più alto).</p></div>")
    if not d or not d.get("segnali"):
        return intro + "<p class='mu'>I dati compaiono dopo il prossimo aggiornamento: servono almeno 2 anni di storia settimanale.</p>"
    out = [intro, "<div style='overflow-x:auto'><table class='tb'><tr><th>Segnale</th><th>Percentile oggi</th><th>Lettura</th><th>Ha mai anticipato i cali?</th></tr>"]
    for k, s in d["segnali"].items():
        pv = s.get("prova") or {}
        pct = s.get("percentile")
        lettura = {"alto": "Livello alto rispetto agli ultimi 5 anni", "basso": "Livello basso rispetto agli ultimi 5 anni", "normale": "Livello nella norma", "n.d.": "Storia ancora troppo corta"}[s["stato"]]
        v = pv.get("verdetto", "n.d.")
        verd = ("Sì, in entrambe le metà della storia" if v.startswith("dimostrato") else ("Non dimostrato" if v == "nessun segnale dimostrato" else "Dati ancora insufficienti per dirlo"))
        out.append(f"<tr><td>{e(s['nome'])}<br><small class='mu'>dato del {e(s['ultimo_dato'])}</small></td><td><b>{'n.d.' if pct is None else f'{pct:.0f}°'}</b></td><td>{e(lettura)}</td><td>{e(verd)}</td></tr>")
    out.append("</table></div><p class='mu'>Un segnale conta come «dimostrato» solo se, con valore alto (o basso), i cali del mese e dei 3 mesi successivi sono stati chiaramente più frequenti del normale, "
               "con margine di errore che esclude il caso, sia nella prima sia nella seconda metà della storia. Finché non succede, peso zero. "
               "I dati SEC (13F, insider, 13D) si aggiornano ogni settimana e la storia si completa in più giri: finché mancano, la riga compare come «storia troppo corta».</p>")
    return "".join(out)


def badge_html() -> str:
    """Riga di contesto a PESO ZERO per Saldi e Opportunità: non cambia punteggi né ordine."""
    from html import escape as e
    d = carica()
    if not d or not d.get("segnali"):
        return ""
    pezzi = []
    for k, sg in d["segnali"].items():
        if sg["stato"] in ("alto", "basso"):
            pezzi.append(f"{e(sg['nome'].split(' (')[0])}: {sg['stato']}")
    txt = "; ".join(pezzi) if pezzi else "nessun segnale dei grandi fondi fuori dalla norma"
    return ("<p class='mu' style='font-size:12px'><b>Contesto grandi fondi</b> (non influisce su punteggi e classifiche, nessun segnale ha ancora dimostrato di anticipare i cali): " + txt + ".</p>")
