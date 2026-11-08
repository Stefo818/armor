"""VWCE in euro con segmenti dichiarati (PIANO ARMOR 3, Fase 3). Mai uniti senza dirlo.

  (a) VWCE.DE reale: ad accumulazione, già in euro (dal primo dato scaricato, 29/07/2019). Nessuna conversione.
  (b) VT (rettificato per i dividendi) convertito in euro: livello in dollari / F(t), con F = dollari per euro (2008-2019). Collegato ad (a) con un solo fattore di scala.
  (c) S&P 500 convertito in euro (livello / F): solo prove di robustezza, MAI chiamato «VWCE».
F = DEXUSEU (FRED, mezzogiorno di New York) se presente, altrimenti EURUSD=X di Yahoo (23:59 UTC).
Limiti del segmento (b): VT segue il FTSE Global All Cap (comprende le piccole aziende), VWCE il FTSE All-World; VT chiude alle 22:00 italiane, VWCE.DE alle 17:30
(per confrontare le serie si usano rendimenti settimanali); ritenute sui dividendi diverse."""
import json

import numpy as np
import pandas as pd

from . import fhs, store
from .config import DATA

FILE = DATA / "serie_eur.json"
OGGI_EUR = DATA / "percorsi_eur_oggi.json"
LIMITI = ("VT segue il FTSE Global All Cap (comprende le piccole aziende), VWCE il FTSE All-World; VT chiude alle 22:00 italiane e VWCE.DE alle 17:30 "
          "(per confrontare si usano rendimenti settimanali); ritenute sui dividendi diverse.")


def usd_per_eur() -> tuple[pd.Series, str]:
    d = store.load("dexuseu").dropna()
    if len(d) > 1000:
        return d, "FRED DEXUSEU"
    return store.load("eurusd").dropna(), "Yahoo EURUSD=X"


def converti(livello_usd: pd.Series, F: pd.Series) -> pd.Series:
    """Livello in euro = livello in dollari / F(t) (F = dollari per euro), con F dell'ultimo giorno noto."""
    F = F.reindex(livello_usd.index.union(F.index)).ffill().reindex(livello_usd.index)
    return (livello_usd / F).dropna()


def collega(proxy: pd.Series, reale: pd.Series) -> pd.Series:
    """Serie unica: proxy fino al giorno prima del primo dato reale (moltiplicato per un solo fattore di scala), poi il reale."""
    if reale.empty:
        return proxy
    if proxy.empty:
        return reale
    k = reale.iloc[0] / proxy.reindex([reale.index[0]], method="ffill").iloc[0]
    return pd.concat([proxy[proxy.index < reale.index[0]] * k, reale]).sort_index()


def costruisci() -> dict:
    F, fonte = usd_per_eur()
    vt, sp, vw = store.load("vt").dropna(), store.load("sp500").dropna(), store.load("vwce_de").dropna()
    b = converti(vt, F)
    c = converti(sp[sp.index >= F.index[0]], F)
    vwce = collega(b, vw)
    seg = [{"id": "b", "nome": "VT convertito in euro", "da": str(b.index[0].date()), "a": str((vw.index[0] - pd.Timedelta(days=1)).date() if len(vw) else b.index[-1].date())},
           {"id": "a", "nome": "VWCE.DE reale", "da": str(vw.index[0].date()) if len(vw) else "", "a": str(vw.index[-1].date()) if len(vw) else ""}]
    return {"vwce_eur": vwce, "sp_eur": c, "vt_eur": b, "vwce_reale": vw, "fonte_cambio": fonte,
            "segmenti": seg + [{"id": "c", "nome": "S&P 500 in euro (solo robustezza)", "da": str(c.index[0].date()), "a": str(c.index[-1].date())}]}


def confronto_segmenti(b: pd.Series, vw: pd.Series) -> dict:
    """Nel periodo in cui VT convertito e VWCE.DE esistono insieme: correlazione dei rendimenti settimanali e differenza annua."""
    w = pd.concat([b.resample("W-FRI").last(), vw.resample("W-FRI").last()], axis=1, keys=["vt", "vw"]).dropna()
    r = w.pct_change().dropna()
    if len(r) < 30:
        return {}
    anni = len(r) / 52
    return {"da": str(w.index[0].date()), "settimane": int(len(r)), "correlazione": float(r.corr().iloc[0, 1]),
            "diff_annua": float((w.vw.iloc[-1] / w.vw.iloc[0]) ** (1 / anni) - (w.vt.iloc[-1] / w.vt.iloc[0]) ** (1 / anni)),
            "vol_annua_vwce": float(r.vw.std() * np.sqrt(52)), "vol_annua_vt": float(r.vt.std() * np.sqrt(52))}


def stima_oggi(p_eur: pd.Series, variante: str = "V0T1", n_paths: int | None = None, scrivi: bool = True) -> dict:
    """Motore di percorsi stimato sui rendimenti di VWCE in euro (dal 2008). Solo varianti senza VIX: l'indice di volatilità è quello dell'S&P 500."""
    from . import percorsi as P
    r = fhs.log_returns(p_eur)
    seed = int(p_eur.index[-1].strftime("%Y%m%d")) % (2 ** 31)
    res = P.stima(r.values, variante, seed, n_paths=n_paths or P.N_LIVE, extra=True)
    out = {"asof": str(p_eur.index[-1].date()), "variante": variante, "n_rendimenti": int(len(r)), "da": str(p_eur.index[0].date()), "risultati": res,
           "basi": P.basi_storiche(p_eur) if len(p_eur) > 800 else {}}
    if scrivi:
        OGGI_EUR.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def confronta_motori(p_eur: pd.Series, p_sp: pd.Series, da: str = "2011-07-01", step: int = 5, reps: int = 1000, log=print) -> dict:
    """Quale prevede meglio gli esiti reali di VWCE in euro? (A) motore stimato sull'S&P 500 in dollari, (B) motore stimato sui rendimenti di VWCE in euro.
    Variante V0T1 per entrambi (nessun VIX). Esito: perdita da oggi ≥ soglia del prezzo di VWCE in euro; base = frequenza storica nota a ogni data."""
    from . import percorsi as P
    from . import verifica as V
    from .features import fwd_maxdd
    dates = p_eur.index[p_eur.index >= da][::step]
    A = P.walk_forward(p_sp, dates, store.load("vix"), store.load("vix3m"), varianti=["V0T1"], sims=2000, log=log)["V0T1"]
    B = P.walk_forward(p_eur, dates, store.load("vix"), store.load("vix3m"), varianti=["V0T1"], sims=2000, fit_start="2000-01-01", log=log)["V0T1"]
    pos = pd.Series(np.arange(len(p_eur)), index=p_eur.index).reindex(dates)
    out = {"da": da, "righe": []}
    for hz, thr in (("1m", 5), ("1m", 10), ("3m", 10)):
        n = P.ORIZZONTI[hz]
        dd = fwd_maxdd(p_eur, n)
        y = (dd <= -thr / 100).astype(float).where(dd.notna()).reindex(dates)
        cs, cn = (dd <= -thr / 100).astype(float).where(dd.notna()).fillna(0).cumsum(), dd.notna().astype(int).cumsum()
        ps = p_eur.index.get_indexer(dates)
        base = pd.Series(cs.values[np.maximum(ps - n, 0)] / np.maximum(cn.values[np.maximum(ps - n, 0)], 1), index=dates)
        sel = {}
        for nome, df in (("S&P 500 in dollari", A), ("VWCE in euro", B)):
            if df.empty:
                continue
            g = df[(df.hz == hz) & (df.kind == "down") & (df.thr == thr)].set_index("date")["p"].dropna()
            sel[nome] = g
        if len(sel) < 2:
            continue
        d = V.prepara(dates, pos, y, base, sel)
        if len(d) < 60:
            continue
        r = V.valuta_modello(d, "VWCE in euro", n, step, "S&P 500 in dollari", reps)
        ra = V.valuta_modello(d, "S&P 500 in dollari", n, step, "S&P 500 in dollari", reps)
        out["righe"].append({"hz": hz, "soglia": thr, "n": int(len(d)), "episodi": r["episodi"]["episodi"], "frequenza": r["freq"],
                             "brier_sp": ra["brier"], "brier_eur": r["brier"], "bss_sp": ra["bss"], "bss_eur": r["bss"],
                             "diff": r["vs_ref"]["intero"], "p_dm": r["vs_ref"]["dm"]["p"]})
    return out


def run(log=print, con_confronto: bool = True) -> dict:
    s = costruisci()
    res = {"data": pd.Timestamp.now().strftime("%Y-%m-%d"), "fonte_cambio": s["fonte_cambio"], "segmenti": s["segmenti"], "limiti": LIMITI,
           "sovrapposizione": confronto_segmenti(s["vt_eur"], s["vwce_reale"]),
           "robustezza_sp_eur": {"da": s["segmenti"][-1]["da"], "ultimo": float(s["sp_eur"].iloc[-1])}}
    if con_confronto:
        try:
            res["confronto_motori"] = confronta_motori(s["vwce_eur"], store.load("sp500").dropna(), log=log)
        except Exception as e:  # noqa: BLE001
            res["confronto_motori"] = {"errore": str(e)[:120]}
            log("[euro] confronto non riuscito: " + str(e)[:120])
    FILE.write_text(json.dumps(res, ensure_ascii=False, default=float, indent=1), encoding="utf-8")
    return res


def oggi() -> None:
    """Passo del ciclo giornaliero: stima di oggi sui rendimenti in euro (la verifica storica si rifà col comando «serie-euro»)."""
    s = costruisci()
    if len(s["vwce_eur"]) > 800:
        stima_oggi(s["vwce_eur"])


def _pc(x, d=0):
    return (f"{x * 100:.{d}f}%").replace(".", ",")


def html() -> str:
    """«VWCE in euro»: segmenti dichiarati, confronto tra i segmenti, scenari stimati sui rendimenti in euro, confronto tra i due motori."""
    import html as h
    try:
        v = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    righe = "".join(f"<tr><td>{h.escape(s['nome'])}</td><td>{s['da']}</td><td>{s['a']}</td></tr>" for s in v["segmenti"])
    so = v.get("sovrapposizione") or {}
    out = ("<p>Il rischio che conta è quello di VWCE <b>in euro</b>. La serie in euro è fatta di segmenti che non vengono mai uniti senza dirlo:</p>"
           f"<div class='scroll'><table><tr><th>Segmento</th><th>Dal</th><th>Al</th></tr>{righe}</table></div>"
           f"<p class='mu'>Cambio: {h.escape(v['fonte_cambio'])}; livello in euro = livello in dollari ÷ dollari per euro. {h.escape(v['limiti'])}</p>")
    if so:
        out += (f"<p>Dove VT convertito e VWCE si sovrappongono (dal {so['da']}, {so['settimane']} settimane): correlazione dei rendimenti settimanali "
                f"<b>{str(round(so['correlazione'], 2)).replace('.', ',')}</b>; differenza di rendimento annuo (VWCE meno VT in euro) {str(round(so['diff_annua'] * 100, 1)).replace('.', ',')} punti; "
                f"volatilità annua {_pc(so['vol_annua_vwce'])} contro {_pc(so['vol_annua_vt'])}. Quindi il segmento prima del 2019 è una stima, non il fondo vero.</p>")
    try:
        o = json.loads(OGGI_EUR.read_text(encoding="utf-8"))
        res, basi = o["risultati"], o.get("basi", {})
        nomi = {"1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi", "12m": "1 anno"}
        rr = ""
        for hz in ("1m", "3m", "6m", "12m"):
            x, b = res[hz], basi.get(hz, {})
            g = lambda d, k: d.get(str(k), d.get(k))
            rr += (f"<tr><td><b>{nomi[hz]}</b></td><td>{_pc(x['ret']['q10'])} / {_pc(x['ret']['q50'])} / {_pc(x['ret']['q90'])}</td><td>{_pc(x['p_neg'])}</td>"
                   f"<td>{_pc(g(x['down'], 10))}</td><td>{_pc(g(x['mdd'], 10))}</td></tr>")
        out += (f"<h4 style='margin:14px 0 4px'>Scenari stimati sui rendimenti di VWCE in euro (dal {o['da'][:4]}, {o['n_rendimenti']} giorni)</h4>"
                "<div class='scroll'><table><tr><th>Orizzonte</th><th>Caso brutto / tipico / buono</th><th>Chiudere in negativo</th><th>Perdita ≥10% da oggi</th><th>Drawdown ≥10%</th></tr>" + rr + "</table></div>"
                f"<p class='mu'>Motore di percorsi, variante {o['variante']} (senza VIX: la volatilità implicita è quella dell'S&amp;P 500). Storia corta: solo una crisi grave (2008) e due cali forti (2020, 2022), quindi stime meno affidabili di quelle sull'S&amp;P 500.</p>")
    except Exception:  # noqa: BLE001
        pass
    cm = (v.get("confronto_motori") or {}).get("righe") or []
    if cm:
        rr = ""
        for r in cm:
            d = r["diff"]
            rr += (f"<tr><td>Calo ≥{r['soglia']}% in {r['hz'].replace('1m', '1 mese').replace('3m', '3 mesi')}</td><td>{r['episodi']}</td><td>{str(round(r['bss_sp'], 3)).replace('.', ',')}</td><td>{str(round(r['bss_eur'], 3)).replace('.', ',')}</td>"
                   f"<td>{str(round(d['diff'], 4)).replace('.', ',')} [{str(round(d['lo'], 4)).replace('.', ',')}; {str(round(d['hi'], 4)).replace('.', ',')}]</td></tr>")
        out += ("<h4 style='margin:14px 0 4px'>Quale motore prevede meglio gli esiti reali di VWCE in euro? (dal luglio 2011)</h4>"
                "<div class='scroll'><table><tr><th>Esito</th><th>Episodi</th><th>BSS motore S&amp;P in dollari</th><th>BSS motore su VWCE in euro</th><th>Differenza di Brier (euro − dollari) [90%]</th></tr>" + rr + "</table></div>"
                "<p class='mu'>Differenza positiva = il motore sull'S&amp;P 500 in dollari fa meglio. Nessuna differenza è netta: il motore sull'S&amp;P 500 (storia dal 1950) resta il riferimento, quello in euro è un controllo.</p>")
    return out
