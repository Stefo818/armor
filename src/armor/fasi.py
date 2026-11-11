"""Fase del mercato, fasce di rendimento per orizzonte e stato di salute (PROTOCOLLO_OCCASIONE.md, parti 3 e 4).
Cosa ha retto alla prova e quindi si mostra: la fase di tendenza (regola dei 200 giorni), la larghezza della fascia in base alla paura di oggi,
gli stati di salute da Indice Armor e Super Armor. Cosa NON ha retto e quindi non si mostra: la previsione della direzione."""
import numpy as np
import pandas as pd

from . import soglie, store
from .config import DATA

ORIZZONTI = [("1 settimana", 5, 0.03), ("1 mese", 21, 0.05), ("3 mesi", 63, 0.08), ("6 mesi", 126, 0.10), ("12 mesi", 252, 0.10)]   # nome, sedute, soglia di perdita/guadagno
SALUTE = ["In salute", "Neutro", "Rischio", "Pericolo"]
FASI = {"rialzo": ("Rialzo", "il prezzo è sopra la sua media di lungo periodo, che sta salendo"),
        "ribasso": ("Ribasso", "il prezzo è sotto la sua media di lungo periodo, che sta scendendo"),
        "laterale": ("Di passaggio", "prezzo e media di lungo periodo non vanno nella stessa direzione: la tendenza sta cambiando o è ferma")}


def tendenza(sp: pd.Series) -> pd.Series:
    """Regola classica: prezzo contro media di 200 sedute, e direzione della media nelle ultime 21 sedute."""
    ma = sp.rolling(200).mean()
    f = pd.Series("laterale", index=sp.index)
    f[(sp > ma) & (ma > ma.shift(21))] = "rialzo"
    f[(sp < ma) & (ma < ma.shift(21))] = "ribasso"
    f[ma.isna()] = "nd"
    return f


def simili(vx: np.ndarray, f: np.ndarray, i: int, h: int):
    """Indici dei giorni passati con paura simile a quella del giorno i (5% più vicino, almeno 150) e di tutti i giorni passati con esito già noto."""
    c = np.flatnonzero(~np.isnan(vx[:max(i - h, 0)]))
    c = c[~np.isnan(f[c])]
    if len(c) < 300 or np.isnan(vx[i]):
        return None, c
    k = max(150, int(0.05 * len(c)))
    return c[np.argpartition(np.abs(np.log(vx[c] / vx[i])), k)[:k]], c


def _avanti(v: np.ndarray, h: int) -> np.ndarray:
    f = np.full(len(v), np.nan)
    f[:len(v) - h] = v[h:] / v[:len(v) - h] - 1
    return f


def fasce(sp: pd.Series, vix: pd.Series) -> list:
    """Per ogni orizzonte: fascia 10°-90° e centro dei rendimenti dopo giorni con paura simile a oggi, più le probabilità di perdere o guadagnare oltre la soglia."""
    sp = sp.dropna().loc["1990":]
    vx = vix.reindex(sp.index).ffill(limit=5).values
    v = sp.values
    i = len(v) - 1
    out = []
    for nome, h, sg in ORIZZONTI:
        f = _avanti(v, h)
        nn, c = simili(vx, f, i, h)
        if nn is None:
            continue
        y, y0 = f[nn], f[c]
        out.append({"nome": nome, "sedute": h, "soglia": sg, "q10": float(np.quantile(y, .1)), "q50": float(np.quantile(y, .5)), "q90": float(np.quantile(y, .9)),
                    "su": float((y > 0).mean()), "perdita": float((y <= -sg).mean()), "guadagno": float((y >= sg).mean()),
                    "sto10": float(np.quantile(y0, .1)), "sto90": float(np.quantile(y0, .9)), "sto_su": float((y0 > 0).mean()), "n": int(len(y)),
                    "finora": float(v[i] / v[i - h] - 1) if i >= h else None})
    return out


def salute(armor: float | None, super_: float | None) -> dict:
    """Stato di salute del mercato (Indice Armor) e di economia e finanza (Super Armor), con la posizione nella storia dal 1990."""
    out = {}
    p = DATA / "titan_storia.csv"
    st = pd.read_csv(p) if p.exists() else None
    for k, v, col in (("mercato", armor, "armor_index"), ("economia", super_, "super_armor_index")):
        if v is None:
            continue
        z = soglie.zona("armor" if k == "mercato" else "super", v)
        pos = float((st[col].dropna() < v).mean()) if st is not None and col in st else None
        out[k] = {"valore": round(float(v), 1), "zona": z, "stato": SALUTE[z], "posizione": pos}
    return out


def oggi() -> dict:
    sp, vix = store.load("sp500"), store.load("vix")
    f = tendenza(sp.dropna())
    fs = fasce(sp, vix)
    rap = (fs[1]["q90"] - fs[1]["q10"]) / (fs[1]["sto90"] - fs[1]["sto10"]) if len(fs) > 1 else 1.0   # fascia a 1 mese contro fascia storica
    umore = "agitato" if rap > 1.15 else "calmo" if rap < 0.85 else "normale"
    return {"tendenza": f.iloc[-1], "umore": umore, "agitato": umore == "agitato", "fasce": fs, "paura": float(vix.dropna().iloc[-1]) if len(vix.dropna()) else None}
