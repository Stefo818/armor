"""Prove dell'Indice Occasione, delle fasce e della salute (PROTOCOLLO_OCCASIONE.md). Lento (1-3 minuti): gira nella convalida mensile.
Scrive data/occasione_verifica.json, da cui l'app prende tutti i numeri che mostra (nessun numero scritto a mano)."""
import hashlib
import json

import numpy as np
import pandas as pd

from . import fasi, occasione, store
from .config import DATA, ROOT

FILE = DATA / "occasione_verifica.json"
EPOCHE = (("1928", "1949"), ("1950", "1967"), ("1968", "1989"), ("1990", "2007"), ("2008", "2026"))


def protocollo_hash() -> str:
    f = ROOT / "PROTOCOLLO_OCCASIONE.md"
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:24] if f.exists() else ""


def _dopo(sp: pd.Series, h: int) -> pd.Series:
    """Rendimento dalle chiusura del giorno dopo il segnale alle h sedute successive."""
    return sp.shift(-1 - h) / sp.shift(-1) - 1


def _discesa(sp: pd.Series, h: int) -> pd.Series:
    """Ulteriore discesa massima nelle h sedute dopo l'ingresso."""
    fut = sp[::-1].rolling(h, min_periods=1).min()[::-1].shift(-2)
    return (fut / sp.shift(-1) - 1).clip(upper=0)


def gruppi(mask: np.ndarray, gap: int = 126) -> list:
    """Primo giorno di ogni gruppo di segnali separati da almeno `gap` sedute."""
    out, last = [], -10 ** 9
    for i in np.flatnonzero(mask):
        if i - last >= gap:
            out.append(int(i))
        last = i
    return out


def epoche(d: pd.DataFrame) -> list:
    sp = d["sp"]
    f6, f12, m = _dopo(sp, 126), _dopo(sp, 252), _discesa(sp, 126)
    out = []
    for a, b in EPOCHE:
        s = d.loc[a:b]
        r = {"periodo": f"{a}-{b}"}
        for nome, mask in (("tutti", pd.Series(True, index=s.index)), ("occ50", s["occasione"] >= 50), ("occ70", s["occasione"] >= 70), ("coltello", s["stato"] == "coltello")):
            x6, x12, xm = f6.reindex(s.index)[mask].dropna(), f12.reindex(s.index)[mask].dropna(), m.reindex(s.index)[mask].dropna()
            r[nome] = {"giorni": int(mask.sum()), "gruppi": len(gruppi(mask.reindex(d.index, fill_value=False).values)),
                       "m6": round(float(x6.median()) * 100, 1), "m12": round(float(x12.median()) * 100, 1), "pos12": round(float((x12 > 0).mean()) * 100),
                       "discesa6m": round(float(xm.mean()) * 100, 1)} if mask.sum() and len(x12) else {"giorni": int(mask.sum())}
        out.append(r)
    return out


def discese(sp: pd.Series, soglia: float = 0.15) -> list:
    """Episodi dal massimo dell'anno al minimo, fino al ritorno sul massimo."""
    v, hi, out, i, n = sp.values, sp.rolling(252, min_periods=60).max().values, [], 0, len(sp)
    while i < n:
        if v[i] >= hi[i] - 1e-9:
            pk, lo, j = i, i, i + 1
            while j < n and v[j] < v[pk]:
                if v[j] < v[lo]:
                    lo = j
                j += 1
            if v[lo] / v[pk] - 1 <= -soglia:
                out.append((pk, lo, j - 1))
            i = j
        else:
            i += 1
    return out


def episodi(d: pd.DataFrame) -> list:
    d = d.loc["1990":]
    sp, out = d["sp"], []
    for pk, lo, fine in discese(sp):
        seg = (d["occasione"].iloc[pk:fine + 1] >= 50).values
        r = {"massimo": str(sp.index[pk].date()), "minimo": str(sp.index[lo].date()), "calo": round((sp.iloc[lo] / sp.iloc[pk] - 1) * 100, 1), "segnali": len(gruppi(seg, 21))}
        sig = np.flatnonzero(seg)
        if len(sig):
            k = min(pk + sig[0] + 1, len(sp) - 1)
            r.update(primo=str(sp.index[k].date()), sedute_dal_minimo=int(k - lo), sopra_minimo=round((sp.iloc[k] / sp.iloc[lo] - 1) * 100, 1),
                     discesa_dopo=round((sp.iloc[k:lo + 1].min() / sp.iloc[k] - 1) * 100, 1) if k <= lo else 0.0)
        out.append(r)
    return out


def soldi(d: pd.DataFrame) -> dict:
    """Prova A: soldi che arrivano un giorno qualsiasi. Valore dopo 5 anni contro chi investe subito (prezzo + dividendi; soldi fermi al tasso a 3 mesi)."""
    sp, ix, n, T = d["sp"], d.index, len(d), 1260
    al = lambda s: s.reindex(s.index.union(ix)).ffill().reindex(ix)
    dy = (store.load("div_shiller") / store.load("price_shiller")).dropna()
    tr = (sp.pct_change().fillna(0) + al(dy).fillna(0.03) / 252 + 1).cumprod().values
    ci = (1 + al(store.load("tb3ms")).fillna(1.0) / 100 / 252).cumprod().values
    sig = np.nan_to_num(d["occasione"].values) >= 50
    val = lambda a, piani: sum(q * ci[k] / ci[a] * tr[a + T] / tr[k] for k, q in piani)

    def attesa(a, maxw=252):
        w = np.flatnonzero(sig[a:a + maxw])
        return [(a + (w[0] + 1 if len(w) else maxw), 1.0)]
    mesi = pd.Series(np.arange(n), index=ix).groupby([ix.year, ix.month]).first().values
    out = {}
    for per, (a0, a1) in {"1990-2021": ("1990-01-01", "2021-10-31"), "1934-1989": ("1934-06-01", "1984-12-31")}.items():
        arr = [a for a in mesi if pd.Timestamp(a0) <= ix[a] <= pd.Timestamp(a1) and a + T + 260 < n]
        base = np.array([val(a, [(a, 1.0)]) for a in arr])
        r = {"arrivi": len(arr)}
        for nome, f in (("rate", lambda a: [(a + 21 * j, 1 / 12) for j in range(12)]), ("attesa", attesa)):
            q = np.array([val(a, f(a)) for a in arr]) / base
            r[nome] = {"media": round(float(q.mean() - 1) * 100, 1), "vince": round(float((q > 1).mean()) * 100), "peggior_10": round(float(np.quantile(q, .1) - 1) * 100, 1),
                       "miglior_10": round(float(np.quantile(q, .9) - 1) * 100, 1)}
        out[per] = r
    return out


def _pin(y, q, a):
    e = y - q
    return np.maximum(a * e, (a - 1) * e)


def fasce(passo: int = 5) -> dict:
    """Fascia «paura simile» contro fascia storica semplice, fuori campione dal 2000, due metà."""
    sp = store.load("sp500").dropna().loc["1990":]
    ix, v = sp.index, sp.values
    vx = store.load("vix").reindex(ix).ffill(limit=5).values
    start = ix.get_indexer([pd.Timestamp("2000-01-03")], method="bfill")[0]
    out = {}
    for nome, h, _ in fasi.ORIZZONTI:
        f, rec = fasi._avanti(v, h), []
        for i in range(start, len(v) - h, passo):
            nn, c = fasi.simili(vx, f, i, h)
            if nn is None:
                continue
            a, b = np.quantile(f[nn], (.1, .5, .9)), np.quantile(f[c], (.1, .5, .9))
            rec.append((i, f[i], *a, *b))
        D = pd.DataFrame(rec, columns=["i", "y", "a10", "a50", "a90", "b10", "b50", "b90"])
        D["data"] = ix[D["i"].values]
        r = {}
        for per, (p0, p1) in {"2000-2012": ("2000", "2012"), "2013-2026": ("2013", "2026")}.items():
            s = D[(D["data"] >= p0) & (D["data"] <= p1 + "-12-31")]
            L = {t: np.mean([_pin(s["y"], s[f"{t}{int(q * 100)}"], q).mean() for q in (.1, .5, .9)]) for t in "ab"}
            r[per] = {"n": int(len(s)), "copertura": round(float(((s["y"] >= s["a10"]) & (s["y"] <= s["a90"])).mean()) * 100),
                      "copertura_storica": round(float(((s["y"] >= s["b10"]) & (s["y"] <= s["b90"])).mean()) * 100), "abilita": round(float(1 - L["a"] / L["b"]) * 100, 1)}
        r["regge"] = all(r[p]["abilita"] > 0 for p in ("2000-2012", "2013-2026"))
        out[nome] = r
    return out


def tendenza() -> dict:
    """Fase di tendenza per epoca: quota di rialzi e fascia 10°-90° nei 1 e 3 mesi dopo."""
    sp = store.load("sp500").dropna()
    fz, out = fasi.tendenza(sp), {}
    for a, b in (("1928", "1949"), ("1950", "1989"), ("1990", "2007"), ("2008", "2026")):
        for hn, h in (("1 mese", 21), ("3 mesi", 63)):
            f = (sp.shift(-h) / sp - 1).loc[a:b]
            out[f"{a}-{b} {hn}"] = {l: {"quota": round(float((fz.loc[a:b] == l).mean()) * 100), "su": round(float((f[fz.loc[a:b] == l].dropna() > 0).mean()) * 100),
                                         "q10": round(float(f[fz.loc[a:b] == l].quantile(.1)) * 100, 1), "q90": round(float(f[fz.loc[a:b] == l].quantile(.9)) * 100, 1)}
                                     for l in ("rialzo", "laterale", "ribasso")}
    return out


def salute() -> dict:
    """Quota di giorni seguiti da una discesa di almeno 10% entro 3 mesi, per stato di salute, in due metà."""
    p = DATA / "titan_storia.csv"
    if not p.exists():
        return {}
    t = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    sp = store.load("sp500").dropna().loc["1990":]
    ev = ((sp[::-1].rolling(63, min_periods=1).min()[::-1].shift(-1) / sp - 1) <= -0.10).astype(float)
    ev.iloc[-63:] = np.nan
    out = {}
    from . import soglie
    for k, col in (("mercato", "armor_index"), ("economia", "super_armor_index")):
        x, tagli = t[col].reindex(sp.index), soglie.ZONE["armor" if k == "mercato" else "super"]["lim"][:3]
        out[k] = {}
        for a, b in (("1995", "2010"), ("2011", "2026"), ("1995", "2026")):
            xx, ee = x.loc[a:b], ev.loc[a:b]
            z = np.digitize(xx, tagli)
            out[k][f"{a}-{b}"] = [{"giorni": round(float((z == j).mean()) * 100), "discesa": round(float(ee[z == j].mean()) * 100, 1)} for j in range(4)]
            out[k][f"{a}-{b}"].append({"base": round(float(ee.mean()) * 100, 1)})
    return out


def esegui(scrivi: bool = True) -> dict:
    d = occasione.calcola(occasione.serie_archivio())
    out = {"protocollo": protocollo_hash(), "asof": str(d.index[-1].date()), "epoche": epoche(d), "episodi": episodi(d), "soldi": soldi(d),
           "fasce": fasce(), "tendenza": tendenza(), "salute": salute()}
    if scrivi:
        FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
