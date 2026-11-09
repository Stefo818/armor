"""Motore titoli (PIANO_ESPANSIONE Patch 45.1-45.2): universo «tutto il mercato», filtri, archivio dei prezzi e metriche di prezzo.
Il lavoro pesante gira in GitHub Actions (titoli.yml); l'archivio dei prezzi sta in data/_cache (actions/cache), non nel repository.
Nel repository va solo il risultato compatto data/titoli_top.json (classifiche per periodo), usato da «Mercati», «Saldi» e «Opportunità»."""
import gzip
import io
import json
import pickle
import re
import time

import numpy as np
import pandas as pd

from .config import DATA

CACHE = DATA / "_cache"
PREZZI = CACHE / "titoli_prezzi.pkl.gz"
TOP = DATA / "titoli_top.json"
NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}
PERIODI = [("1g", 1), ("3g", 3), ("1s", 5), ("1m", 21), ("3m", 63), ("6m", 126), ("1a", 252)]
MIN_PREZZO, MIN_CAP, MIN_CONTROVALORE = 1.0, 50e6, 500e3
REGIONI = ["de", "it", "fr", "gb", "nl", "es", "ch", "se", "dk", "no", "fi", "jp", "kr", "tw", "hk", "cn", "in", "au", "ca", "br", "mx", "za"]
ESCLUDI_NOME = re.compile(r"\b(warrants?|rights?|units?|acquisition corp(?:oration)?|acquisition co\b|spac|preferred|pfd|depositary|notes due|"
                          r"2x|3x|-1x|-2x|-3x|ultra(?:pro|short)?|leveraged|inverse|bear|short|etn|trust units?)\b", re.I)


# ---------------------------------------------------------------- universo
def parse_nasdaq_listed(testo: str) -> pd.DataFrame:
    """nasdaqlisted.txt: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares (ultima riga: File Creation Time)."""
    df = pd.read_csv(io.StringIO(testo), sep="|", dtype=str)
    df = df[df["Symbol"].notna() & ~df["Symbol"].str.startswith("File Creation")]
    return pd.DataFrame({"t": df["Symbol"], "n": df["Security Name"], "etf": df["ETF"].eq("Y"), "test": df["Test Issue"].eq("Y"), "borsa": "NASDAQ"})


def parse_other_listed(testo: str) -> pd.DataFrame:
    """otherlisted.txt: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol."""
    df = pd.read_csv(io.StringIO(testo), sep="|", dtype=str)
    df = df[df["ACT Symbol"].notna() & ~df["ACT Symbol"].str.startswith("File Creation")]
    return pd.DataFrame({"t": df["ACT Symbol"], "n": df["Security Name"], "etf": df["ETF"].eq("Y"), "test": df["Test Issue"].eq("Y"), "borsa": df["Exchange"]})


def filtra_elenco(df: pd.DataFrame) -> pd.DataFrame:
    """Toglie ETF, titoli di prova, SPAC, warrant, diritti, unità, privilegiate, fondi a leva o inversi e simboli con caratteri strani."""
    d = df[~df["etf"] & ~df["test"]].copy()
    d = d[~d["n"].fillna("").str.contains(ESCLUDI_NOME)]
    d = d[d["t"].str.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?")]
    d["t"] = d["t"].str.replace(".", "-", regex=False)
    return d.drop_duplicates("t").reset_index(drop=True)


def universo_usa(get=None) -> pd.DataFrame:
    import requests
    g = get or (lambda u: requests.get(u, headers=UA, timeout=60).text)
    return filtra_elenco(pd.concat([parse_nasdaq_listed(g(NASDAQ_LISTED)), parse_other_listed(g(OTHER_LISTED))], ignore_index=True))


def universo_estero(log=print) -> pd.DataFrame:
    """Resto del mondo con yfinance.screen (EquityQuery), una query per regione e pagina da 250. Se la funzione non esiste o fallisce, la regione si salta."""
    righe = []
    try:
        import yfinance as yf
        from yfinance import EquityQuery
    except Exception:  # noqa: BLE001
        log("[titoli] yfinance.screen non disponibile: universo estero saltato")
        return pd.DataFrame(columns=["t", "n", "etf", "test", "borsa"])
    for reg in REGIONI:
        for off in range(0, 1000, 250):
            try:
                q = EquityQuery("and", [EquityQuery("eq", ["region", reg]), EquityQuery("gt", ["intradaymarketcap", MIN_CAP]), EquityQuery("gt", ["intradayprice", MIN_PREZZO])])
                r = yf.screen(q, offset=off, size=250, sortField="intradaymarketcap", sortAsc=False)
                qs = r.get("quotes", [])
            except Exception as e:  # noqa: BLE001
                log(f"[titoli] screen {reg}@{off}: {str(e)[:70]}")
                break
            for x in qs:
                righe.append({"t": x["symbol"], "n": x.get("longName") or x.get("shortName") or x["symbol"], "etf": False, "test": False, "borsa": x.get("fullExchangeName", reg),
                              "cap": x.get("marketCap"), "valuta": x.get("currency")})
            if len(qs) < 250:
                break
    d = pd.DataFrame(righe)
    if d.empty:
        return pd.DataFrame(columns=["t", "n", "etf", "test", "borsa"])
    d = d[~d["n"].str.contains(ESCLUDI_NOME)]
    return d.drop_duplicates("t").reset_index(drop=True)


# ---------------------------------------------------------------- prezzi
def carica_prezzi() -> dict | None:
    if not PREZZI.exists():
        return None
    try:
        with gzip.open(PREZZI, "rb") as f:
            return pickle.load(f)
    except Exception:  # noqa: BLE001
        return None


def salva_prezzi(d: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    with gzip.open(PREZZI, "wb") as f:
        pickle.dump(d, f)


def scarica_blocco(tk: list[str], periodo: str, log=print):
    import yfinance as yf
    try:
        d = yf.download(tk, period=periodo, interval="1d", auto_adjust=True, threads=True, progress=False, group_by="column")
    except Exception as e:  # noqa: BLE001
        log(f"[titoli] blocco non scaricato: {str(e)[:80]}")
        return None, None
    if d is None or d.empty:
        return None, None
    c, v = d["Close"], d["Volume"]
    if isinstance(c, pd.Series):
        c, v = c.to_frame(tk[0]), v.to_frame(tk[0])
    return c, v


def aggiorna_prezzi(tickers: list[str], blocco: int = 100, log=print, scarica=scarica_blocco, giorni: int = 280) -> dict:
    """Archivio incrementale: se esiste, scarica solo gli ultimi 10 giorni (e l'intera storia dei titoli nuovi); altrimenti 14 mesi per tutti."""
    arch = carica_prezzi() or {"close": pd.DataFrame(), "vol": pd.DataFrame()}
    nuovi = [t for t in tickers if t not in arch["close"].columns]
    vecchi = [t for t in tickers if t in arch["close"].columns]
    pezzi_c, pezzi_v = [], []
    for lista, per in ((vecchi, "10d"), (nuovi, "14mo")):
        for i in range(0, len(lista), blocco):
            c, v = scarica(lista[i:i + blocco], per, log)
            if c is not None:
                pezzi_c.append(c)
                pezzi_v.append(v)
    for nome, pezzi in (("close", pezzi_c), ("vol", pezzi_v)):
        if pezzi:
            nu = pd.concat(pezzi, axis=1, sort=True)
            nu.index = pd.to_datetime(nu.index).tz_localize(None).normalize()
            nu = nu.loc[:, ~nu.columns.duplicated()]
            arch[nome] = nu.combine_first(arch[nome]) if not arch[nome].empty else nu
        arch[nome] = arch[nome].sort_index().iloc[-giorni:]
    arch["close"] = arch["close"].reindex(columns=[t for t in arch["close"].columns if t in set(tickers)])
    arch["vol"] = arch["vol"].reindex(columns=arch["close"].columns)
    arch["ts"] = time.time()
    salva_prezzi(arch)
    return arch


# ---------------------------------------------------------------- metriche
def metriche(close: pd.DataFrame, vol: pd.DataFrame, ref: pd.Series | None = None) -> pd.DataFrame:
    """Per ogni titolo: rendimenti a 1g, 3g, 1s, 1m, 3m, 6m, 12m, volatilità annua a 63 sedute, volume relativo (5 giorni / 60), beta contro `ref`,
    momentum 12-1, distanza dal massimo a 52 settimane, controvalore medio giornaliero a 20 sedute e il flag `anomalo` (dati sospetti)."""
    c = close.dropna(how="all")
    last = c.ffill().iloc[-1]
    out = pd.DataFrame(index=c.columns)
    out["prezzo"] = last
    for nome, n in PERIODI:
        if len(c) > n:
            out["r" + nome] = last / c.ffill().iloc[-1 - n] - 1
    lr = np.log(c.ffill()).diff()
    out["vol63"] = lr.iloc[-63:].std() * np.sqrt(252)
    v = vol.reindex(c.index)
    out["volrel"] = v.iloc[-5:].mean() / v.iloc[-60:].mean().replace(0, np.nan)
    out["controvalore20"] = (c.ffill() * v).iloc[-20:].mean()
    out["dd52"] = last / c.iloc[-252:].max() - 1
    if len(c) > 252:
        out["mom12_1"] = c.ffill().iloc[-22] / c.ffill().iloc[-253] - 1
    if ref is not None:
        rr = np.log(ref.reindex(c.index).ffill()).diff().iloc[-252:]
        x = lr.iloc[-252:]
        cov = x.apply(lambda s: s.cov(rr))
        out["beta"] = (cov / rr.var()).clip(-1, 4)
    mv = c.ffill().pct_change().iloc[-30:]
    out["anomalo"] = (mv.max() >= 4.0) | (mv.min() <= -0.8)
    out["n_giorni"] = c.notna().sum()
    return out


def liquidi(m: pd.DataFrame, cap: pd.Series | None = None) -> pd.DataFrame:
    """Filtri di liquidità e qualità: prezzo ≥ 1, controvalore medio ≥ 500 mila, capitalizzazione ≥ 50 milioni (se nota), almeno 120 sedute, nessuna anomalia."""
    ok = (m["prezzo"] >= MIN_PREZZO) & (m["controvalore20"] >= MIN_CONTROVALORE) & ~m["anomalo"].astype(bool) & (m["n_giorni"] >= 120)
    if cap is not None:
        c = cap.reindex(m.index)
        ok &= c.isna() | (c >= MIN_CAP)
    return m[ok]


SETTORI = DATA / "universo" / "settori.json"


def completa_settori(tickers: list[str], log=print, max_nuovi: int = 400) -> dict:
    """Settore, industria, paese e capitalizzazione dei titoli in classifica (yfinance.info, una chiamata per titolo, memorizzati in data/universo/settori.json)."""
    try:
        cache = json.loads(SETTORI.read_text(encoding="utf-8")) if SETTORI.exists() else {}
    except Exception:  # noqa: BLE001
        cache = {}
    nuovi = [t for t in tickers if t not in cache][:max_nuovi]
    if nuovi:
        import yfinance as yf
        for t in nuovi:
            try:
                i = yf.Ticker(t).info or {}
                cache[t] = {"s": i.get("sector"), "i": i.get("industry"), "p": i.get("country"), "cap": i.get("marketCap"), "v": i.get("currency")}
            except Exception:  # noqa: BLE001
                cache[t] = {}
        SETTORI.parent.mkdir(exist_ok=True)
        SETTORI.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log(f"[titoli] settori aggiunti: {len(nuovi)}")
    return cache


def top_json(m: pd.DataFrame, close: pd.DataFrame, nomi: dict, settori: dict | None = None, n: int = 150, fx: pd.Series | None = None) -> dict:
    """Classifiche compatte (n migliori e n peggiori per periodo) nello schema di «Mercati»: t, n, c='titoli', s=settore, v, p, r (6 periodi), e (euro), k (30 giorni).
    I rendimenti mostrati sono calcolati come in «Mercati» (giorni di calendario, in valuta locale e in euro)."""
    from . import mondo
    chiavi = ["r1g", "r1s", "r1m", "r3m", "r6m", "r1a"]
    sel = set()
    for k in chiavi + ["r3g"]:
        if k in m:
            s = m[k].dropna().sort_values()
            sel |= set(s.index[:n]) | set(s.index[-n:])
    settori = settori or {}
    items = []
    for t in sorted(sel):
        inf = settori.get(t) or {}
        valuta = inf.get("v") or "USD"
        r = mondo.rendimenti(close[t], fx, valuta if valuta in ("USD", "EUR") else "USD")
        if r is None:
            continue
        loc, eur = r
        if valuta not in ("USD", "EUR"):
            eur = [None] * 6   # altre valute: niente conversione (resta il rendimento in valuta locale)
        items.append({"t": t, "n": nomi.get(t, t), "c": "titoli", "s": inf.get("s") or "n/d", "v": valuta, "p": round(float(m.at[t, "prezzo"]), 2), "r": loc, "e": eur,
                      "k": [round(float(x), 4 if x < 10 else 2) for x in close[t].dropna().iloc[-30:].values], "cap": inf.get("cap"),
                      "x3": None if "r3g" not in m or pd.isna(m.at[t, "r3g"]) else round(float(m.at[t, "r3g"]), 5),
                      "beta": None if "beta" not in m or pd.isna(m.at[t, "beta"]) else round(float(m.at[t, "beta"]), 2),
                      "k6": [round(float(x), 4 if x < 10 else 2) for x in close[t].dropna().iloc[-126::2].values], "paese": inf.get("p"), "ind": inf.get("i")})
    return {"asof": str(close.dropna(how="all").index[-1].date()), "universo": int(len(m)), "items": items}


def ausiliari() -> list[str]:
    """Simboli nell'archivio prezzi che non sono titoli da classificare: benchmark, cambio ed ETF dei temi."""
    from . import titoli_eventi as _ev
    return ["SPY", "EURUSD=X", "VT"] + sorted({v[1] for v in _ev.TEMI.values()})


def aggiorna(log=print, usa_estero: bool = True) -> dict:
    """Lavoro giornaliero: universo → prezzi → filtri → metriche → data/titoli_top.json."""
    uni = universo_usa()
    if usa_estero:
        est = universo_estero(log)
        uni = pd.concat([uni, est], ignore_index=True).drop_duplicates("t")
    log(f"[titoli] universo: {len(uni)} simboli")
    extra = ausiliari()
    tk = sorted(set(uni["t"]) | set(extra))
    arch = aggiorna_prezzi(tk, log=log)
    c, v = arch["close"], arch["vol"]
    ref = c["SPY"] if "SPY" in c else None
    fx = c["EURUSD=X"].dropna() if "EURUSD=X" in c else None
    cc = c.drop(columns=[x for x in extra if x in c])
    m = metriche(cc, v.reindex(columns=cc.columns), ref)
    capi = uni.set_index("t")["cap"] if "cap" in uni else None
    m = liquidi(m, capi)
    log(f"[titoli] dopo i filtri: {len(m)} titoli")
    nomi = dict(zip(uni["t"], uni["n"]))
    d0 = top_json(m, cc, nomi, None, fx=fx)
    settori = completa_settori([i["t"] for i in d0["items"]], log)
    d = top_json(m, cc, nomi, settori, fx=fx)
    TOP.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"[titoli] scritto {TOP.name}: {len(d['items'])} titoli nelle classifiche")
    return d
