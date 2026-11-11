# -*- coding: utf-8 -*-
"""Registro dei valori di Titan nel tempo: per ogni data del diario e ogni giorno di lavoro, la probabilità di calo (e il punteggio di rialzo) sugli stessi
quattro orizzonti del diario (10 giorni, 1, 3 e 6 mesi). Serve alla pagina Storico (linea e colonna di Titan). I valori di date passate sono ricalcolati
con i soli dati noti allora (nessuno sguardo al futuro). File: data/titan_registro.csv (date, hz, calo, rialzo)."""
import pandas as pd

from . import titan
from .config import DATA

FILE = DATA / "titan_registro.csv"
HZ = {"10g": (7, 0.05), "1m": (21, 0.10), "3m": (63, 0.10), "6m": (126, 0.10)}


def carica() -> pd.DataFrame:
    if not FILE.exists():
        return pd.DataFrame(columns=["date", "hz", "calo", "rialzo"])
    d = pd.read_csv(FILE, parse_dates=["date"])
    return d.drop_duplicates(["date", "hz"], keep="last")


def valori_al(df: pd.DataFrame, data) -> dict:
    """{orizzonte: (calo, rialzo)} per la data indicata, con i soli dati fino a quel giorno."""
    cut = df.loc[:pd.Timestamp(data)]
    n, out = len(cut), {}
    for hz, (h, th) in HZ.items():
        r = titan.walk_forward(cut, h, th, include_today=True, from_idx=max(0, n - 1 - (h + 420)))
        last = r.iloc[-1]
        out[hz] = (float(last["p_dd_v40"]), float(last["p_up_v40"]))
    return out


def aggiorna(df: pd.DataFrame | None = None, date_diario=None, log=print) -> int:
    """Aggiunge le date mancanti (date del diario e ultima seduta). Restituisce quante date nuove."""
    if df is None:
        from . import titan_job
        df = titan_job.costruisci()
    old = carica()
    fatte = set(pd.to_datetime(old["date"]).dt.normalize()) if len(old) else set()
    cand = {df.index[-1]}
    if date_diario is not None:
        cand |= {pd.Timestamp(x).normalize() for x in date_diario}
    nuove = sorted(x for x in cand if x in df.index and x not in fatte and x >= df.index[1000])
    righe = []
    for x in nuove:
        try:
            for hz, (c, r) in valori_al(df, x).items():
                righe.append({"date": x.strftime("%Y-%m-%d"), "hz": hz, "calo": round(c, 5), "rialzo": round(r, 5)})
        except Exception as e:  # noqa: BLE001
            log(f"[titan-registro] {x.date()} non calcolata: {str(e)[:80]}")
    if righe:
        tot = pd.concat([old.assign(date=pd.to_datetime(old["date"]).dt.strftime("%Y-%m-%d")), pd.DataFrame(righe)]).drop_duplicates(["date", "hz"], keep="last")
        tot.sort_values(["date", "hz"]).to_csv(FILE, index=False)
    return len(nuove)


def serie_hz(hz: str, anni: int = 6) -> pd.Series:
    """Probabilità di calo di Titan (in %) nel tempo per un orizzonte: storia walk-forward (data/modelli_preds.csv, ogni 5 sedute) e valori del registro."""
    parti = []
    p = DATA / "modelli_preds.csv"
    if p.exists():
        m = pd.read_csv(p, parse_dates=["date"])
        m = m[(m["model"] == "Titan") & (m["hz"] == hz)]
        if len(m):
            parti.append(m.set_index("date")["p"].astype(float) * 100)
    r = carica()
    r = r[r["hz"] == hz]
    if len(r):
        parti.append(r.set_index("date")["calo"].astype(float) * 100)
    if not parti:
        return pd.Series(dtype=float)
    s = pd.concat(parti)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s.index >= s.index[-1] - pd.Timedelta(days=365 * anni)]


def per_data() -> dict:
    """{(data, orizzonte): (calo, rialzo)} dal registro."""
    r = carica()
    return {(x.date, x.hz): (float(x.calo), float(x.rialzo)) for x in r.itertuples()}
