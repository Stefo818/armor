"""Indice Occasione (0-100): riconosce i minimi mentre si formano, per decidere le entrate extra.
Due parti: «Panico» (quanto è forte la discesa) e «Svolta» (segni che la discesa si esaurisce). Regole fissate in PROTOCOLLO_OCCASIONE.md.
Tutte le funzioni sono pure e usano solo dati noti quel giorno (nessuno sguardo al futuro)."""
import numpy as np
import pandas as pd

from . import store

SETTORI = ("sec_xlk", "sec_xlf", "sec_xlv", "sec_xly", "sec_xli", "sec_xlp", "sec_xle", "sec_xlu", "sec_xlb")
VOCI_P = {"caduta": "Caduta dal massimo dell'anno", "paura": "Paura", "breve": "Paura a breve più alta di quella a tre mesi",
          "credito": "Credito in peggioramento", "sotto": "Prezzo sotto la media di lungo periodo"}
VOCI_S = {"rientra": "Paura che rientra", "curva": "Curva della paura tornata normale", "cred_stop": "Credito che smette di peggiorare",
          "risale": "Prezzo che risale dal minimo", "ampiezza": "Ampiezza: settori che risalgono"}
SOGLIA, SOGLIA_FORTE = 50, 70


def _lin(x, zero: float, pieno: float):
    """Da 0 (al valore `zero`) a 100 (al valore `pieno`), lineare e tagliato."""
    return ((x - zero) / (pieno - zero)).clip(0, 1) * 100


def serie_archivio() -> dict:
    """Serie dall'archivio di Armor."""
    return {"sp": store.load("sp500"), "vix": store.load("vix"), "vix3m": store.load("vix3m"), "baa10y": store.load("baa10y"),
            "settori": {s: store.load(s) for s in SETTORI}}


def calcola(S: dict) -> pd.DataFrame:
    """Tabella giornaliera: voci, panico, svolta, panico_rec, occasione, stato."""
    sp = S["sp"].dropna()
    ix = sp.index
    al = lambda s, lim=5: s.reindex(s.index.union(ix)).ffill(limit=lim).reindex(ix) if len(s) else pd.Series(np.nan, index=ix)
    vix, vix3m = al(S.get("vix", pd.Series(dtype=float))), al(S.get("vix3m", pd.Series(dtype=float)))
    spread = al(S.get("baa10y", pd.Series(dtype=float))).shift(1)            # il dato esce il giorno dopo
    rv = sp.pct_change().rolling(21).std() * np.sqrt(252)                     # volatilità reale: sostituisce il VIX prima del 1990
    ha_vix = vix.notna()
    d = pd.DataFrame(index=ix)
    d["sp"] = sp
    dd = sp / sp.rolling(252, min_periods=60).max() - 1
    d["dd"] = dd
    d["caduta"] = _lin(dd, -0.05, -0.25)
    d["paura"] = _lin(vix, 20, 45).where(ha_vix, _lin(rv, 0.15, 0.45))
    rapporto = vix / vix3m
    d["breve"] = _lin(rapporto, 0.95, 1.15)
    d["credito"] = _lin(spread - spread.shift(63), 0.10, 1.00)
    d["sotto"] = _lin(sp / sp.rolling(200).mean() - 1, 0.0, -0.15)
    vmax = vix.rolling(63, min_periods=21).max()
    rmax = rv.rolling(63, min_periods=21).max()
    rientra_v = _lin(vix / vmax - 1, 0.0, -0.35).where(vmax >= 28, 0.0)
    rientra_r = _lin(rv / rmax - 1, 0.0, -0.35).where(rmax >= 0.25, 0.0)
    d["rientra"] = rientra_v.where(ha_vix, rientra_r)
    d["curva"] = _lin(rapporto, 1.05, 0.95)
    d["cred_stop"] = _lin(spread.rolling(21).mean() - spread, 0.0, 0.15)
    d["risale"] = _lin(sp / sp.rolling(63, min_periods=21).min() - 1, 0.03, 0.12)
    sett = pd.DataFrame({k: al(v) for k, v in S.get("settori", {}).items() if len(v)})
    if len(sett.columns) >= 6:
        media = sett.rolling(20).mean()
        sopra = (sett > media).astype(float).where(media.notna())
        d["ampiezza"] = _lin(sopra.mean(axis=1).where(sopra.notna().sum(axis=1) >= 6), 0.30, 0.90)
    else:
        d["ampiezza"] = np.nan
    minimo = np.where(ha_vix, 3, 2)                                           # versione lunga senza VIX: bastano 2 voci
    for nome, voci in (("panico", VOCI_P), ("svolta", VOCI_S)):
        m = d[list(voci)]
        d[nome] = m.mean(axis=1).where(m.notna().sum(axis=1) >= minimo)
    d["panico_rec"] = d["panico"].rolling(63, min_periods=1).max()
    d["occasione"] = d[["panico_rec", "svolta"]].min(axis=1, skipna=False)
    d["stato"] = stato(d["panico"], d["svolta"], d["panico_rec"], d["occasione"])
    return d


def stato(panico, svolta, panico_rec, occasione) -> pd.Series:
    s = pd.Series("osservazione", index=occasione.index)
    s[panico_rec < 30] = "nessun_panico"
    s[(panico >= 40) & (svolta < 40)] = "coltello"
    s[occasione >= SOGLIA] = "occasione"
    s[occasione >= SOGLIA_FORTE] = "occasione_forte"
    s[occasione.isna()] = "nd"
    return s


STATI = {"nessun_panico": ("Nessun panico", "Mercato senza forti discese: nessuna occasione particolare, vale il piano mensile."),
         "osservazione": ("In osservazione", "C'è stata tensione ma manca il panico vero oppure manca ancora la svolta."),
         "coltello": ("Coltello che cade", "Il mercato scende con forza e non ci sono ancora segni di svolta: storicamente conveniva aspettare."),
         "occasione": ("Occasione", "C'è stato panico e ora ci sono segni di svolta: in passato da qui i mesi successivi sono stati migliori del normale."),
         "occasione_forte": ("Occasione forte", "Panico forte seguito da una svolta chiara: è la situazione che in passato ha accompagnato i minimi importanti."),
         "nd": ("Dati insufficienti", "Mancano troppi dati per calcolare l'indice.")}


# ---------------------------------------------------------------- lavoro giornaliero
def aggiorna(scrivi: bool = True) -> dict:
    """Valori di oggi (data/occasione.json): indice, stato, voci, sconto dal massimo, livelli degli scaglioni, fase, fasce e salute."""
    import json

    from . import fasi
    from .config import DATA
    d = calcola(serie_archivio())
    u = d.dropna(subset=["occasione"]).iloc[-1]
    mass = float(d["sp"].rolling(252, min_periods=60).max().iloc[-1])
    num = lambda x: None if pd.isna(x) else round(float(x), 1)
    out = {"data": str(u.name.date()), "occasione": num(u["occasione"]), "stato": u["stato"], "panico": num(u["panico"]), "panico_rec": num(u["panico_rec"]), "svolta": num(u["svolta"]),
           "voci_panico": {k: num(u[k]) for k in VOCI_P}, "voci_svolta": {k: num(u[k]) for k in VOCI_S},
           "sconto": round(float(u["dd"]) * 100, 1), "sp": round(float(u["sp"]), 1), "massimo": round(mass, 1),
           "scaglioni": [{"calo": c, "livello": round(mass * (1 - c / 100), 0), "manca": round((mass * (1 - c / 100) / float(u["sp"]) - 1) * 100, 1)} for c in (10, 20, 30)],
           "storia": [[str(i.date()), num(r["occasione"]), num(r["panico"]), num(r["svolta"])] for i, r in d.iloc[-260::5].iterrows()]}
    try:
        out["fasi"] = fasi.oggi()
        tj = DATA / "titan.json"
        t = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() else {}
        out["salute"] = fasi.salute(t.get("armor_index"), t.get("super_armor"))
        out["titan_calo"] = {k: v.get("calo") for k, v in (t.get("previsioni") or {}).items()}
    except Exception as e:      # le fasce non devono mai bloccare l'indice
        out["errore_fasi"] = str(e)[:120]
    if scrivi:
        (DATA / "occasione.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
