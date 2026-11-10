"""Dati SEC gratuiti per i Grandi fondi (peso zero): 13F trimestrali, operazioni degli insider (Form 4), nuove partecipazioni oltre il 5% (Schedule 13D).
Scarica i pacchetti pubblici, tiene SOLO aggregati piccoli in data/grandi_fondi/ (mai i file grezzi) ed è incrementale: ogni esecuzione aggiunge al massimo
`MAX_NUOVI` pacchetti, così la storia si completa in più giri senza superare i tempi di GitHub. Ogni passo è isolato: se uno fallisce gli altri vanno avanti.
La SEC chiede di dichiarare chi scarica: imposta il segreto SEC_USER_AGENT (nome e contatto) nel repository; senza, si usa un nome generico.
I nomi delle colonne sono letti dalle intestazioni dei file e verificati: se non coincidono con quelli attesi il passo si ferma con un messaggio chiaro."""
import io
import os
import re
import time
import zipfile
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests

from .config import DATA

DIR = DATA / "grandi_fondi"
LISTA_13F = "https://www.sec.gov/dera/data/form-13f"
LISTA_345 = "https://www.sec.gov/dera/data/form-345"
BASE_13F = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{y}q{q}_form13f.zip"
BASE_345 = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{y}q{q}_form345.zip"
INDICE = "https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.idx"
DAL = 2013
MAX_NUOVI = 10
PANNELLO = 50          # i primi 50 depositanti per valore nel trimestre PRECEDENTE (regola ex ante)
TENERE = 300           # per ogni pacchetto si conservano i primi 300 depositanti per valore (servono a fissare il pannello)
CUSIP_INDICI = {"78462F103", "464287200", "922908363", "46090E103", "464287655", "78467X109"}   # SPY, IVV, VOO, QQQ, IWM, DIA
NOME_INDICI = re.compile(r"S&P 500 ETF|SPDR S&P 500|ISHARES CORE S&P 500|VANGUARD S&P 500|INVESCO QQQ|QQQ TRUST|RUSSELL 2000 ETF|SPDR DOW JONES|DIAMONDS", re.I)


def ua() -> dict:
    return {"User-Agent": os.environ.get("SEC_USER_AGENT", "").strip() or "Armor personal research (set SEC_USER_AGENT)", "Accept-Encoding": "gzip, deflate"}


def _get(url: str, stream: bool = False, tries: int = 3, timeout: int = 120):
    err = None
    for i in range(tries):
        try:
            time.sleep(0.2)   # la SEC chiede al massimo ~10 richieste al secondo
            r = requests.get(url, headers=ua(), timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            err = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:80]
        time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url}: {err}")


def trova_zip(lista: str, suffisso: str, base: str) -> list[tuple[str, str]]:
    """[(chiave ordinabile, url)] dei pacchetti disponibili: legge la pagina elenco, altrimenti prova i nomi trimestrali noti."""
    out = {}
    try:
        r = _get(lista, timeout=40)
        for h in re.findall(r'href=["\']([^"\']+' + re.escape(suffisso) + r')["\']', r.text, re.I):
            u = urljoin(r.url, h)
            f = u.rsplit("/", 1)[-1].lower()
            m = re.match(r"(\d{4})q(\d)", f)
            if m:
                out[f"{m.group(1)}{m.group(2)}"] = u
            else:   # nomi a intervallo di date (dal 2024): 01jun2024-31aug2024_form13f.zip
                m = re.search(r"-(\d{1,2})([a-z]{3})(\d{4})", f)
                if m:
                    d = pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)}")
                    out[f"{d.year}{(d.month - 1) // 3 + 1}x{d.strftime('%m%d')}"] = u
    except Exception as e:  # noqa: BLE001
        print(f"[sec] elenco non letto ({str(e)[:70]}): provo i nomi trimestrali noti", flush=True)
    if not out:
        oggi = pd.Timestamp.now()
        for y in range(DAL, oggi.year + 1):
            for q in range(1, 5):
                if pd.Timestamp(y, 3 * q - 2, 1) <= oggi:
                    out[f"{y}{q}"] = base.format(y=y, q=q)
    return sorted((k, u) for k, u in out.items() if int(k[:4]) >= DAL)


def _tsv(z: zipfile.ZipFile, nome: str, usecols=None, chunksize=None):
    cand = [n for n in z.namelist() if n.upper().endswith(nome.upper())]
    if not cand:
        raise KeyError(f"{nome} non trovato nel pacchetto ({', '.join(z.namelist())[:200]})")
    f = z.open(cand[0])
    return pd.read_csv(f, sep="\t", dtype=str, usecols=(lambda c: c.upper() in usecols) if usecols else None, chunksize=chunksize, low_memory=False, on_bad_lines="skip", encoding="latin-1")


def _controlla(df: pd.DataFrame, attese: set, nome: str) -> pd.DataFrame:
    df.columns = [c.upper() for c in df.columns]
    mancano = attese - set(df.columns)
    if mancano:
        raise KeyError(f"{nome}: colonne attese non trovate {sorted(mancano)}; trovate {list(df.columns)[:20]}")
    return df


# ---------- 13F ----------
def aggrega_13f(z: zipfile.ZipFile) -> pd.DataFrame:
    """Un pacchetto 13F -> una riga per depositante e periodo: valore totale e quote su ETF indicizzati (put, call, azioni)."""
    sub = _controlla(_tsv(z, "SUBMISSION.tsv"), {"ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"}, "SUBMISSION")
    sub = sub[sub["SUBMISSIONTYPE"].str.upper() == "13F-HR"][["ACCESSION_NUMBER", "FILING_DATE", "CIK", "PERIODOFREPORT"]]
    acc = set(sub["ACCESSION_NUMBER"])
    try:
        cov = _controlla(_tsv(z, "COVERPAGE.tsv"), {"ACCESSION_NUMBER", "FILINGMANAGER_NAME"}, "COVERPAGE")[["ACCESSION_NUMBER", "FILINGMANAGER_NAME"]]
    except KeyError:
        cov = pd.DataFrame(columns=["ACCESSION_NUMBER", "FILINGMANAGER_NAME"])
    parti = []
    for ch in _tsv(z, "INFOTABLE.tsv", chunksize=400000):
        ch = _controlla(ch, {"ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "SSHPRNAMTTYPE", "PUTCALL"}, "INFOTABLE")
        ch = ch[ch["ACCESSION_NUMBER"].isin(acc)]
        v = pd.to_numeric(ch["VALUE"], errors="coerce").fillna(0.0)
        idx = ch["CUSIP"].fillna("").str.upper().isin(CUSIP_INDICI) | ch["NAMEOFISSUER"].fillna("").str.contains(NOME_INDICI)
        pc = ch["PUTCALL"].fillna("").str.upper()
        parti.append(pd.DataFrame({"ACCESSION_NUMBER": ch["ACCESSION_NUMBER"], "tot": v,
                                   "put_idx": np.where(idx & (pc == "PUT"), v, 0.0), "call_idx": np.where(idx & (pc == "CALL"), v, 0.0),
                                   "sh_idx": np.where(idx & (pc == ""), v, 0.0), "n": 1}).groupby("ACCESSION_NUMBER").sum())
    if not parti:
        return pd.DataFrame()
    g = pd.concat(parti).groupby(level=0).sum().reset_index().merge(sub, on="ACCESSION_NUMBER").merge(cov, on="ACCESSION_NUMBER", how="left")
    g["periodo"] = pd.to_datetime(g["PERIODOFREPORT"], errors="coerce")
    g["deposito"] = pd.to_datetime(g["FILING_DATE"], errors="coerce")
    g = g.dropna(subset=["periodo"]).sort_values("tot", ascending=False).head(TENERE)
    return g.rename(columns={"CIK": "cik", "FILINGMANAGER_NAME": "nome"})[["cik", "nome", "periodo", "deposito", "tot", "put_idx", "call_idx", "sh_idx", "n"]]


def serie_13f(df: pd.DataFrame) -> pd.DataFrame:
    """Dai depositanti ai segnali per periodo, con il pannello fissato dal trimestre precedente (nessuna informazione futura).
    protezione = put su ETF indicizzati / valore totale del pannello; indicizzati = azioni+call su ETF indicizzati / valore totale."""
    if df.empty:
        return pd.DataFrame(columns=["protezione", "indicizzati", "n_depositanti"])
    df = df.copy()
    df["periodo"] = pd.to_datetime(df["periodo"])
    df["cik"] = df["cik"].astype(str)
    df = df.sort_values("deposito").drop_duplicates(["cik", "periodo"], keep="last")
    per = sorted(df["periodo"].unique())
    righe = {}
    for i, pr in enumerate(per):
        if i == 0:
            continue
        prec = df[df["periodo"] == per[i - 1]].nlargest(PANNELLO, "tot")
        cur = df[(df["periodo"] == pr) & df["cik"].isin(set(prec["cik"]))]
        if len(cur) < PANNELLO * 0.6 or cur["tot"].sum() <= 0:
            continue
        t = cur["tot"].sum()
        righe[pd.Timestamp(pr)] = {"protezione": cur["put_idx"].sum() / t * 100, "indicizzati": (cur["sh_idx"].sum() + cur["call_idx"].sum()) / t * 100, "n_depositanti": int(len(cur))}
    return pd.DataFrame.from_dict(righe, orient="index").sort_index()


def aggiorna_13f(max_nuovi: int = MAX_NUOVI) -> str:
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / "f13_depositanti.csv"
    vecchio = pd.read_csv(f, parse_dates=["periodo", "deposito"]) if f.exists() else pd.DataFrame()
    fatti = set(open(DIR / "f13_fatti.txt").read().split()) if (DIR / "f13_fatti.txt").exists() else set()
    zip_ = trova_zip(LISTA_13F, "_form13f.zip", BASE_13F)
    ultimi = {k for k, _ in zip_[-2:]}   # gli ultimi due si riscaricano sempre (depositi tardivi)
    da_fare = [(k, u) for k, u in zip_ if k not in fatti or k in ultimi][:max_nuovi + 2]
    nuovi = []
    n = 0
    for k, u in da_fare:
        if k in fatti and k not in ultimi:
            continue
        if k not in fatti and n >= max_nuovi:
            continue
        try:
            r = _get(u, stream=True, timeout=300)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            a = aggrega_13f(z)
            print(f"[13F] {k}: {len(a)} depositanti, periodi {sorted(a['periodo'].dt.strftime('%Y-%m-%d').unique())[:3] if len(a) else '-'}", flush=True)
            nuovi.append(a)
            fatti.add(k)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"[13F] {k} saltato: {str(e)[:200]}", flush=True)
    if nuovi:
        tutto = pd.concat([vecchio] + nuovi, ignore_index=True) if len(vecchio) else pd.concat(nuovi, ignore_index=True)
        tutto = tutto.sort_values("deposito").drop_duplicates(["cik", "periodo"], keep="last")
        tutto.to_csv(f, index=False)
        open(DIR / "f13_fatti.txt", "w").write("\n".join(sorted(fatti)))
        s = serie_13f(tutto)
        s.to_csv(DIR / "f13_segnali.csv", index_label="periodo")
        return f"13F: {len(s)} periodi di segnale, {len(fatti)} pacchetti elaborati"
    return "13F: nulla di nuovo"


# ---------- Form 4 (insider) ----------
def aggrega_345(z: zipfile.ZipFile) -> pd.DataFrame:
    """Un pacchetto insider -> per settimana di deposito: valore acquisti (codice P) e vendite (codice S) a mercato aperto."""
    sub = _controlla(_tsv(z, "SUBMISSION.tsv"), {"ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE"}, "SUBMISSION")
    sub = sub[sub["DOCUMENT_TYPE"].str.upper().str.startswith("4")][["ACCESSION_NUMBER", "FILING_DATE"]]
    tr = _controlla(_tsv(z, "NONDERIV_TRANS.tsv"), {"ACCESSION_NUMBER", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE"}, "NONDERIV_TRANS")
    tr = tr[tr["TRANS_CODE"].isin(["P", "S"])].merge(sub, on="ACCESSION_NUMBER")
    tr["val"] = pd.to_numeric(tr["TRANS_SHARES"], errors="coerce") * pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")
    tr["data"] = pd.to_datetime(tr["FILING_DATE"], errors="coerce")
    tr = tr.dropna(subset=["val", "data"])
    tr = tr[(tr["val"] > 0) & (tr["val"] < 5e9)]   # valori impossibili = colonne lette male
    tr["settimana"] = tr["data"].dt.to_period("W-FRI").dt.end_time.dt.normalize()
    out = tr.pivot_table(index="settimana", columns="TRANS_CODE", values="val", aggfunc="sum", fill_value=0.0)
    for c in ("P", "S"):
        if c not in out:
            out[c] = 0.0
    return out.rename(columns={"P": "acquisti", "S": "vendite"})[["acquisti", "vendite"]]


def aggiorna_insider(max_nuovi: int = MAX_NUOVI) -> str:
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / "insider_settimane.csv"
    vecchio = pd.read_csv(f, index_col=0, parse_dates=True) if f.exists() else pd.DataFrame(columns=["acquisti", "vendite"])
    fatti = set(open(DIR / "insider_fatti.txt").read().split()) if (DIR / "insider_fatti.txt").exists() else set()
    zip_ = trova_zip(LISTA_345, "_form345.zip", BASE_345)
    ultimi = {k for k, _ in zip_[-1:]}
    nuovi, n = [], 0
    for k, u in zip_:
        if (k in fatti and k not in ultimi) or (k not in fatti and n >= max_nuovi):
            continue
        try:
            z = zipfile.ZipFile(io.BytesIO(_get(u, stream=True, timeout=300).content))
            a = aggrega_345(z)
            print(f"[insider] {k}: {len(a)} settimane", flush=True)
            nuovi.append(a)
            fatti.add(k)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"[insider] {k} saltato: {str(e)[:200]}", flush=True)
    if nuovi:
        if len(vecchio):   # i pacchetti riscaricati sostituiscono le settimane che contengono
            vecchio = vecchio[~vecchio.index.isin(pd.concat(nuovi).index)]
        tutto = pd.concat([vecchio] + nuovi).sort_index()
        tutto = tutto.groupby(level=0).sum() if tutto.index.duplicated().any() else tutto
        tutto.to_csv(f, index_label="settimana")
        open(DIR / "insider_fatti.txt", "w").write("\n".join(sorted(fatti)))
        return f"Insider: {len(tutto)} settimane, {len(fatti)} pacchetti"
    return "Insider: nulla di nuovo"


# ---------- 13D ----------
RIGA_IDX = re.compile(r"^(SC 13D(?:/A)?|SCHEDULE 13D(?:/A)?)\s{2,}.*?(\d{4}-\d{2}-\d{2})\s+edgar/")


def conta_13d(righe) -> pd.Series:
    """Dal testo di form.idx: numero di nuovi depositi 13D (non gli emendamenti) per settimana."""
    d = [pd.Timestamp(m.group(2)) for r in righe if (m := RIGA_IDX.match(r)) and "/A" not in m.group(1)]
    if not d:
        return pd.Series(dtype=float)
    s = pd.Series(1.0, index=pd.DatetimeIndex(d)).resample("W-FRI").sum()
    return s


def aggiorna_13d(max_nuovi: int = MAX_NUOVI) -> str:
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / "d13_settimane.csv"
    vecchio = pd.read_csv(f, index_col=0, parse_dates=True)["n"] if f.exists() else pd.Series(dtype=float)
    fatti = set(open(DIR / "d13_fatti.txt").read().split()) if (DIR / "d13_fatti.txt").exists() else set()
    oggi = pd.Timestamp.now()
    trim = [(y, q) for y in range(DAL, oggi.year + 1) for q in range(1, 5) if pd.Timestamp(y, 3 * q - 2, 1) <= oggi]
    corrente = trim[-1]
    nuovi, n = [], 0
    for y, q in trim:
        k = f"{y}{q}"
        if (k in fatti and (y, q) != corrente) or (k not in fatti and n >= max_nuovi):
            continue
        try:
            r = _get(INDICE.format(y=y, q=q), stream=True, timeout=300)
            righe = (ln.decode("latin-1") for ln in r.iter_lines())
            s = conta_13d(righe)
            print(f"[13D] {k}: {int(s.sum()) if len(s) else 0} depositi", flush=True)
            nuovi.append(s)
            if (y, q) != corrente:
                fatti.add(k)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"[13D] {k} saltato: {str(e)[:200]}", flush=True)
    if nuovi:
        nu = pd.concat(nuovi)
        vecchio = vecchio[~vecchio.index.isin(nu.index)]
        tutto = pd.concat([vecchio, nu]).sort_index()
        tutto.rename("n").to_csv(f, index_label="settimana")
        open(DIR / "d13_fatti.txt", "w").write("\n".join(sorted(fatti)))
        return f"13D: {len(tutto)} settimane"
    return "13D: nulla di nuovo"


def aggiorna_tutto(max_nuovi: int = MAX_NUOVI) -> None:
    for nome, fn in (("13F", aggiorna_13f), ("insider", aggiorna_insider), ("13D", aggiorna_13d)):
        try:
            print("[sec]", fn(max_nuovi), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[sec] {nome} non aggiornato: {str(e)[:300]}", flush=True)


def sonda() -> str:
    """Esecuzione di prova: mostra elenco, nomi dei file e intestazioni dell'ultimo pacchetto per 13F e insider, e le prime righe di form.idx."""
    out = []
    for nome, lista, suff, base in (("13F", LISTA_13F, "_form13f.zip", BASE_13F), ("INSIDER", LISTA_345, "_form345.zip", BASE_345)):
        try:
            zl = trova_zip(lista, suff, base)
            out.append(f"== {nome}: {len(zl)} pacchetti; primo {zl[0]}; ultimo {zl[-1]}")
            z = zipfile.ZipFile(io.BytesIO(_get(zl[-1][1], stream=True, timeout=300).content))
            out.append("file nel pacchetto: " + ", ".join(z.namelist()))
            for n in z.namelist():
                if n.lower().endswith(".tsv"):
                    df = pd.read_csv(z.open(n), sep="\t", dtype=str, nrows=2, encoding="latin-1")
                    out.append(f"-- {n}: colonne {list(df.columns)}")
                    out.append(df.head(2).to_string()[:600])
        except Exception as e:  # noqa: BLE001
            out.append(f"== {nome}: ERRORE {str(e)[:300]}")
    try:
        r = _get(INDICE.format(y=pd.Timestamp.now().year - 1, q=4), stream=True, timeout=120)
        n13 = 0
        for i, ln in enumerate(r.iter_lines()):
            t = ln.decode("latin-1")
            if i < 12 or ("13D" in t and n13 < 4):
                out.append(t[:160])
                n13 += ("13D" in t)
            if i > 400000:
                break
    except Exception as e:  # noqa: BLE001
        out.append(f"== form.idx: ERRORE {str(e)[:300]}")
    txt = "\n".join(out)
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "sonda.txt").write_text(txt, encoding="utf-8")
    return txt
