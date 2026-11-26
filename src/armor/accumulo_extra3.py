"""Fonti aggiuntive (26/11/2026): fattori e settori dal 1926 (Fama-French), operazioni reali su CDS (DTCC), storia completa degli indici di volatilita' (CBOE).

Archivio per le ricerche future: nessuna di queste serie entra nei modelli. Le funzioni parse_* non toccano la rete e si provano con dati finti.
Gli indirizzi sono quelli noti dei siti: dalla macchina di sviluppo non sono raggiungibili, quindi il primo vero scarico avviene nel lavoro giornaliero
e il suo esito (riuscito o errore) finisce in data/accumulo_stato.json."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import store
from .accumulo_extra import BROWSER, _get, _riepilogo, slug
from .guard import run_parallel

FF_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FF_FILE = {"fattori3": "F-F_Research_Data_Factors_daily_CSV.zip", "fattori5": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
           "momentum": "F-F_Momentum_Factor_daily_CSV.zip", "settori49": "49_Industry_Portfolios_daily_CSV.zip"}


def parse_french(txt: str) -> pd.DataFrame:
    """CSV di Ken French: righe di testo, poi una tabella con data AAAAMMGG; si legge solo la prima tabella (valori pesati). -99.99 e -999 = mancante.
    Rendimenti giornalieri in percentuale."""
    righe = txt.splitlines()
    inizio = next((i for i, r in enumerate(righe) if re.match(r"^\s*\d{8}\s*,", r)), None)
    if inizio is None:
        raise RuntimeError("French: nessuna riga con data")
    intest = ["data"]
    for r in reversed(righe[:inizio]):
        if "," in r and r.strip().strip(",").strip():
            intest = [c.strip() for c in r.split(",")]
            break
    dati = []
    for r in righe[inizio:]:
        if not re.match(r"^\s*\d{8}\s*,", r):
            break
        dati.append([c.strip() for c in r.split(",")])
    n = max(len(d) for d in dati)
    cols = [intest[i] if i < len(intest) and intest[i] else f"c{i}" for i in range(n)]
    cols[0] = "data"
    df = pd.DataFrame(dati, columns=cols[:n]).replace({"": None})
    df.index = pd.to_datetime(df.pop("data"), format="%Y%m%d")
    df = df.apply(pd.to_numeric, errors="coerce")
    return df.where((df > -99) )


def _csv_da_zip(contenuto: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(contenuto))
    nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    return z.read(nome).decode("latin-1")


def aggiorna_french(stato: dict) -> None:
    def mk(nome, f):
        def job():
            df = parse_french(_csv_da_zip(_get(FF_BASE + f, headers=BROWSER, timeout=80).content))
            n = 0
            for c in df.columns:
                s = df[c].dropna()
                if len(s):
                    n += store.upsert(f"ff_{nome}_{slug(c)}", s)
            return n
        return job
    res = run_parallel({k: mk(k, v) for k, v in FF_FILE.items()}, workers=2, deadline=240)
    stato["french"] = _riepilogo(res)


# ----------------------------------------------------------------------------- CBOE: storia degli indici di volatilita'
CBOE_IDX = ["VIX", "VIX9D", "VIX3M", "VIX6M", "VIX1D", "VVIX", "SKEW", "VXN", "RVX", "OVX", "GVZ", "VXEEM", "VXD"]


def parse_cboe_storia(txt: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt))
    df.columns = [str(c).strip().lower() for c in df.columns]
    dcol = next(c for c in df.columns if "date" in c)
    df.index = pd.to_datetime(df.pop(dcol), errors="coerce")
    df = df[df.index.notna()].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    return df[~df.index.duplicated(keep="last")].sort_index()


def aggiorna_cboe_storia(stato: dict) -> None:
    def mk(nome):
        def job():
            df = parse_cboe_storia(_get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{nome}_History.csv", headers=BROWSER, timeout=60).text)
            n = 0
            for c in df.columns:
                s = df[c].dropna()
                if len(s):
                    n += store.upsert(f"cboe_{nome.lower()}_{slug(c)}", s)
            return n
        return job
    res = run_parallel({k: mk(k) for k in CBOE_IDX}, workers=3, deadline=240)
    stato["cboe_storia"] = _riepilogo(res)


# ----------------------------------------------------------------------------- DTCC: operazioni reali su CDS (diffusione pubblica dei prezzi)
DTCC_URL = "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_CREDITS_{y}_{m}_{d}.zip"


def _col(df: pd.DataFrame, *parti: str, escludi: tuple = ()) -> str | None:
    for c in df.columns:
        low = str(c).lower()
        if all(p in low for p in parti) and not any(e in low for e in escludi):
            return c
    return None


def parse_dtcc_cds(txt: str, giorno: str) -> dict:
    """Riepilogo di un giorno di operazioni su CDS: numero, importo totale e, per gli indici (CDX, iTraxx), importo e prezzo medio pesato.
    I nomi delle colonne si cercano per parole chiave, perche' il tracciato puo' cambiare."""
    df = pd.read_csv(io.StringIO(txt), dtype=str, low_memory=False)
    notc = _col(df, "notional", "amount", "1") or _col(df, "notional")
    prc = _col(df, "price", escludi=("type", "notation type", "additional", "currency", "unit"))
    testo = [c for c in df.columns if any(k in str(c).lower() for k in ("underlier", "underlying", "product", "taxonomy"))]
    if notc is None:
        raise RuntimeError("DTCC: colonna importo non trovata")
    imp = pd.to_numeric(df[notc].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")
    out = {"n_operazioni": float(len(df)), "importo_totale": float(imp.sum())}
    idx = pd.Series(False, index=df.index)
    for c in testo:
        idx |= df[c].astype(str).str.contains(r"CDX|ITRAXX|iTraxx|INDEX", case=False, regex=True, na=False)
    out["n_indici"] = float(idx.sum()); out["importo_indici"] = float(imp[idx].sum())
    if prc is not None and idx.any():
        p = pd.to_numeric(df[prc].astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
        m = idx & p.notna() & imp.notna() & (imp > 0)
        if m.any() and imp[m].sum() > 0:
            out["prezzo_medio_pesato_indici"] = float((p[m] * imp[m]).sum() / imp[m].sum())
            out["prezzo_mediano_indici"] = float(p[m].median())
    return out


def parse_dtcc_generico(txt: str) -> dict:
    """Riepilogo di un giorno per le sezioni senza distinzione indice/singola azienda (SEC, tassi, cambi, azioni, materie prime)."""
    df = pd.read_csv(io.StringIO(txt), dtype=str, low_memory=False)
    notc = _col(df, "notional", "amount", "1") or _col(df, "notional")
    out = {"n_operazioni": float(len(df))}
    if notc is not None:
        imp = pd.to_numeric(df[notc].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")
        out["importo_totale"] = float(imp.sum())
    return out


# sezione -> (cartella, nome file, usa il riepilogo con gli indici). CANADA: indirizzi supposti, non verificati (l'esito dice se esistono)
DTCC_SEZ = {"cftc_credits": ("cftc", "CFTC_CUMULATIVE_CREDITS", True), "cftc_commodities": ("cftc", "CFTC_CUMULATIVE_COMMODITIES", False),
            "cftc_equities": ("cftc", "CFTC_CUMULATIVE_EQUITIES", False), "cftc_fx": ("cftc", "CFTC_CUMULATIVE_FOREIGN_EXCHANGE", False),
            "cftc_rates": ("cftc", "CFTC_CUMULATIVE_RATES", False),
            "sec_credits": ("sec", "SEC_CUMULATIVE_CREDITS", False), "sec_equities": ("sec", "SEC_CUMULATIVE_EQUITIES", False),
            "sec_rates": ("sec", "SEC_CUMULATIVE_RATES", False),
            "canada_credits": ("canada", "CANADA_CUMULATIVE_CREDITS", False), "canada_equities": ("canada", "CANADA_CUMULATIVE_EQUITIES", False),
            "canada_rates": ("canada", "CANADA_CUMULATIVE_RATES", False), "canada_fx": ("canada", "CANADA_CUMULATIVE_FOREIGN_EXCHANGE", False),
            "canada_commodities": ("canada", "CANADA_CUMULATIVE_COMMODITIES", False)}
DTCC_GIORNI = 400   # il sito conserva circa un anno di file giornalieri


def _nome_dtcc(sez: str, g) -> str:
    return f"{DTCC_SEZ[sez][1]}_{g.year}_{g.month:02d}_{g.day:02d}.zip"


def _dtcc_giorno(sez: str, g, raw_dir: str | None = None) -> dict:
    """Scarica il file del giorno (lo conserva intero in raw_dir) e ne ricava il riepilogo."""
    import os
    cart = DTCC_SEZ[sez][0]
    nome = _nome_dtcc(sez, g)
    contenuto = _get(f"https://kgc0418-tdw-data-0.s3.amazonaws.com/{cart}/eod/{nome}", headers=BROWSER, timeout=120, tries=2).content
    if raw_dir:
        os.makedirs(raw_dir, exist_ok=True)
        with open(os.path.join(raw_dir, nome), "wb") as f:
            f.write(contenuto)
    try:
        txt = _csv_da_zip(contenuto)
        return parse_dtcc_cds(txt, str(g)) if DTCC_SEZ[sez][2] else parse_dtcc_generico(txt)
    except (pd.errors.EmptyDataError, StopIteration):   # giorno senza operazioni (fine settimana)
        return {"n_operazioni": 0.0, "importo_totale": 0.0}


def aggiorna_dtcc_cds(stato: dict) -> None:
    """Scarica TUTTO quello che il sito conserva (tutte le sezioni, tutti i giorni dell'ultimo anno), dai piu' recenti.
    Ogni file intero va in DTCC_RAW (poi caricato nell'archivio grezzo); il riepilogo giornaliero va nelle serie.
    Salta cio' che c'e' gia' (elenco in DTCC_GIA). Salva a blocchi, cosi' un'interruzione non perde il lavoro."""
    import os
    import time
    raw = os.environ.get("DTCC_RAW", "data_raw/dtcc")
    gia = set()
    if os.environ.get("DTCC_GIA") and os.path.exists(os.environ["DTCC_GIA"]):
        gia = {r.strip() for r in open(os.environ["DTCC_GIA"]) if r.strip()}
    limite = time.time() + float(os.environ.get("DTCC_SECONDI", 17000))
    oggi = datetime.now(timezone.utc).date()
    ha = {s: set(store.load(f"dtcc_{s}_n_operazioni").index.date) for s in DTCC_SEZ}
    giorni = [oggi - timedelta(days=k) for k in range(1, DTCC_GIORNI)]
    da_fare = [(s, g) for g in giorni for s in DTCC_SEZ
               if not (g in ha[s] and (not gia or _nome_dtcc(s, g) in gia))]
    fatti, err = {}, []
    for i in range(0, len(da_fare), 120):
        if time.time() > limite:
            break
        blocco = da_fare[i:i + 120]
        jobs = {f"{s}|{g}": (lambda s=s, g=g: _dtcc_giorno(s, g, raw)) for s, g in blocco}
        ris = run_parallel(jobs, workers=4, deadline=max(60.0, min(1800.0, limite - time.time())))
        righe: dict = {}
        for k, (tipo, v) in ris.items():
            sez, g = k.split("|")
            if tipo != "ok":
                err.append(f"{k}: {str(v)[:40]}")
                continue
            for nome, val in v.items():
                righe.setdefault(f"dtcc_{sez}_{nome}", {})[pd.Timestamp(g)] = val
            fatti[sez] = fatti.get(sez, 0) + 1
        for sid, d in righe.items():
            store.upsert(sid, pd.Series(d).sort_index())
    if not fatti and da_fare:
        raise RuntimeError("DTCC: nessun file scaricato: " + "; ".join(err[:2]))
    per_sez_err: dict = {}
    for e in err:
        per_sez_err[e.split("|")[0]] = per_sez_err.get(e.split("|")[0], 0) + 1
    stato["dtcc_cds"] = {"da_fare": len(da_fare), "scaricati_per_sezione": fatti, "errori_per_sezione": per_sez_err, "esempi_errori": err[:4]}
