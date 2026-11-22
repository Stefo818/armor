# -*- coding: utf-8 -*-
"""Previsione del VWCE a 1, 3, 6 e 12 ore (PROTOCOLLO_MINIMI.md, parte L).
Idea: il VWCE chiude alle 17:30 (Xetra) o alle 22-23 (sedi serali), ma Wall Street e i futures americani continuano a muoversi. Il «valore equo» del VWCE si ricava dai futures sull'S&P 500 e dal cambio euro/dollaro:
quando il prezzo del VWCE non li ha ancora seguiti, c'è un salto in arrivo. Sulle 570 notti 2024-2026 il salto all'apertura è stimato per l'86% da questi due dati (86% anche su dati non usati per tarare).
Oltre al salto si stima l'ampiezza dei movimenti (dalla paura del mercato, VIX, con la forma reale degli ultimi due anni) e l'effetto delle trimestrali dei grandi titoli (oggi Nvidia).
Non prevede la direzione di una sorpresa: dice che cosa è già successo e non ancora riflesso, e quanto può oscillare. File: data/ore.json, diario data/ore_diario.csv."""
import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import radar
from .config import DATA

FILE = DATA / "ore.json"
DIARIO = DATA / "ore_diario.csv"
STATO = DATA / "ore_state.json"
ORIZZONTI = {"1 ora": 1.0, "3 ore": 3.0, "6 ore": 6.0, "12 ore": 12.0}
# Tarati sulle 570 notti 2024-2026 (prima metà per tarare, seconda per provare): variazione del VWCE tra chiusura e apertura = 0,83 × futures S&P − 0,50 × cambio EUR/USD
BETA_ES, BETA_FX, SD_RESIDUO = 0.83, -0.50, 0.0028
SD_TRACK = 0.0012          # scarto normale tra VWCE e valore equo a mercato aperto (per ora, in radice)
SOGLIA_CALO = -0.005       # salto atteso da cui parte l'avviso «calo atteso» (64 notti su 570; in 9 su 10 il VWCE ha davvero aperto almeno a -0,5%)
SOGLIA_CALO_FORTE = -0.010  # «calo forte atteso»: 22 notti su 570, sempre confermato
SOGLIA_SHOCK_ES = -0.010   # futures giù di almeno l'1% in un'ora: «movimento brusco in corso»
SOGLIA_FORTE = -0.015      # «forte ribasso» = -1,5% o più
# Rimbalzo statistico debole: dopo un calo dei futures di almeno 1% nelle ultime 24 ore, su 5.500 ore (2024-2026) il VWCE-equivalente è salito dopo 3/6/12 ore un po' più spesso che sceso (54-60%, mediana +0,04/+0,07/+0,11%), in entrambe le metà dei dati.
# Segnale debole e poco indipendente tra un'ora e l'altra: lo si aggiunge piccolo e lo si dichiara.
# La deriva è espressa in frazione dello scarto tipico, non in punti fissi: così sparisce da sola quando
# i mercati sono chiusi e non può più muoversi nulla (prima restava intera e la probabilità di rialzo schizzava).
DERIVA_RIMBALZO = {1.0: 0.095, 3.0: 0.111, 6.0: 0.134, 12.0: 0.149}
SOGLIA_RIMBALZO = -0.010
# Emendamento 1: su 13.710 ore (2024-2026) il rimbalzo dopo un calo dell'1% esiste solo con l'indice sopra
# la media a 200 giorni (sale nel 55-57% dei casi, 1.111 ore). Sotto quella media si rovescia: 46-50%
# (380 ore), e con il mercato oltre il 7% sotto il massimo 46-49% con mediana negativa. Sotto la media
# la deriva viene quindi azzerata: si toglie una spinta che i dati contraddicono, senza scommettere al
# contrario su un campione piccolo.
# eventi: ticker -> (nome, peso approssimato nel VWCE %, moltiplicatore di contagio, mossa tipica %, ora di pubblicazione ET o None = dopo la chiusura 16:20)
# contagio 1,6 per Nvidia: sulle ultime 12 trimestrali l'S&P 500 si è mosso 0,09 volte la mossa di Nvidia, circa 1,6 volte il suo peso nell'indice mondiale
EVENTI = {"NVDA": ("Nvidia", 3.7, 1.6, 5.6), "AAPL": ("Apple", 4.3, 1.0, 3.0), "MSFT": ("Microsoft", 3.1, 1.0, 4.4), "AMZN": ("Amazon", 2.0, 1.0, 6.4), "GOOGL": ("Alphabet", 1.7, 1.0, 5.5),
          "AVGO": ("Broadcom", 1.3, 1.5, 6.3), "META": ("Meta", 1.3, 1.0, 10.0), "TSLA": ("Tesla", 1.0, 1.0, 7.7),
          "BRK-B": ("Berkshire Hathaway", 0.8, 1.0, 2.0), "JPM": ("JPMorgan", 0.8, 1.0, 1.4), "LLY": ("Eli Lilly", 0.9, 1.0, 2.3), "V": ("Visa", 0.6, 1.0, 2.7), "MA": ("Mastercard", 0.5, 1.0, 3.0),
          "ORCL": ("Oracle", 0.6, 1.3, 7.0), "XOM": ("Exxon Mobil", 0.6, 1.0, 2.5), "NFLX": ("Netflix", 0.4, 1.0, 8.0), "COST": ("Costco", 0.5, 1.0, 3.0), "WMT": ("Walmart", 0.6, 1.0, 4.0),
          "TSM": ("TSMC", 1.1, 1.4, 2.0), "ASML": ("ASML", 0.4, 1.3, 6.0), "MU": ("Micron", 0.2, 1.4, 8.0)}
# mossa tipica = media del valore assoluto della reazione il giorno dopo i conti (misurata su 12 titoli, 24 trimestri, dove disponibile; altrimenti stima). Pesi nel VWCE approssimati.
NOMI_EVENTO = {"Nvidia": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet (Google)": "GOOGL", "Alphabet": "GOOGL", "Broadcom": "AVGO", "Meta": "META", "Tesla": "TSLA",
               "Berkshire Hathaway": "BRK-B", "JPMorgan": "JPM", "Eli Lilly": "LLY", "Visa": "V", "Mastercard": "MA", "Oracle": "ORCL", "Exxon Mobil": "XOM", "Netflix": "NFLX", "Costco": "COST",
               "Walmart": "WMT", "TSMC": "TSM", "ASML": "ASML", "Micron": "MU"}
ZQ = {1: [-2.207, -1.666, -1.431, -1.276, -1.162, -1.062, -0.986, -0.905, -0.846, -0.794, -0.742, -0.702, -0.667, -0.632, -0.598, -0.565, -0.536, -0.509, -0.487, -0.462, -0.437, -0.413, -0.389, -0.368, -0.351, -0.333, -0.313, -0.294, -0.273, -0.256, -0.239, -0.222, -0.204, -0.187, -0.171, -0.157, -0.142, -0.128, -0.114, -0.1, -0.087, -0.075, -0.062, -0.048, -0.037, -0.025, -0.012, 0.0, 0.016, 0.027, 0.037, 0.049, 0.064, 0.077, 0.09, 0.104, 0.118, 0.13, 0.144, 0.158, 0.171, 0.181, 0.197, 0.209, 0.224, 0.238, 0.253, 0.27, 0.283, 0.299, 0.314, 0.329, 0.347, 0.368, 0.388, 0.406, 0.424, 0.444, 0.467, 0.49, 0.511, 0.537, 0.561, 0.585, 0.61, 0.644, 0.671, 0.703, 0.736, 0.78, 0.833, 0.885, 0.938, 1.013, 1.087, 1.199, 1.348, 1.586, 1.969], 3: [-2.206, -1.757, -1.504, -1.323, -1.193, -1.102, -1.02, -0.956, -0.881, -0.825, -0.771, -0.724, -0.682, -0.643, -0.61, -0.574, -0.546, -0.517, -0.497, -0.465, -0.441, -0.414, -0.392, -0.371, -0.349, -0.329, -0.307, -0.288, -0.27, -0.252, -0.234, -0.218, -0.201, -0.186, -0.172, -0.156, -0.139, -0.121, -0.105, -0.092, -0.079, -0.066, -0.052, -0.035, -0.022, -0.007, 0.005, 0.02, 0.033, 0.047, 0.059, 0.075, 0.086, 0.1, 0.115, 0.128, 0.14, 0.152, 0.169, 0.182, 0.196, 0.209, 0.225, 0.238, 0.254, 0.267, 0.283, 0.299, 0.317, 0.332, 0.35, 0.366, 0.383, 0.402, 0.417, 0.434, 0.452, 0.471, 0.493, 0.511, 0.531, 0.555, 0.579, 0.599, 0.624, 0.65, 0.676, 0.712, 0.749, 0.786, 0.832, 0.875, 0.922, 0.976, 1.048, 1.138, 1.264, 1.431, 1.754], 6: [-2.15, -1.76, -1.537, -1.391, -1.263, -1.157, -1.067, -0.986, -0.924, -0.866, -0.809, -0.763, -0.713, -0.676, -0.642, -0.605, -0.576, -0.548, -0.52, -0.497, -0.467, -0.438, -0.415, -0.39, -0.37, -0.349, -0.327, -0.308, -0.286, -0.267, -0.248, -0.228, -0.208, -0.187, -0.172, -0.153, -0.135, -0.118, -0.103, -0.09, -0.076, -0.06, -0.045, -0.03, -0.015, 0.0, 0.014, 0.029, 0.047, 0.061, 0.075, 0.09, 0.104, 0.119, 0.135, 0.15, 0.165, 0.181, 0.195, 0.208, 0.226, 0.238, 0.255, 0.273, 0.288, 0.301, 0.318, 0.336, 0.352, 0.365, 0.384, 0.399, 0.413, 0.43, 0.446, 0.464, 0.482, 0.503, 0.523, 0.542, 0.565, 0.586, 0.608, 0.63, 0.655, 0.677, 0.704, 0.73, 0.765, 0.8, 0.835, 0.879, 0.927, 0.991, 1.06, 1.153, 1.257, 1.425, 1.727], 12: [-2.121, -1.78, -1.617, -1.44, -1.318, -1.193, -1.087, -1.013, -0.949, -0.893, -0.84, -0.793, -0.75, -0.7, -0.656, -0.626, -0.587, -0.553, -0.53, -0.505, -0.471, -0.438, -0.418, -0.395, -0.372, -0.351, -0.329, -0.312, -0.29, -0.269, -0.249, -0.229, -0.212, -0.194, -0.175, -0.16, -0.14, -0.123, -0.103, -0.09, -0.074, -0.059, -0.045, -0.031, -0.015, 0.0, 0.012, 0.028, 0.045, 0.06, 0.074, 0.087, 0.106, 0.122, 0.138, 0.156, 0.172, 0.192, 0.204, 0.219, 0.236, 0.25, 0.263, 0.28, 0.3, 0.32, 0.337, 0.351, 0.369, 0.389, 0.405, 0.424, 0.442, 0.461, 0.484, 0.5, 0.516, 0.534, 0.551, 0.576, 0.598, 0.618, 0.64, 0.663, 0.687, 0.709, 0.737, 0.767, 0.809, 0.838, 0.88, 0.927, 0.974, 1.031, 1.09, 1.17, 1.296, 1.442, 1.675]}
SHARE = {0: 0.0232, 1: 0.0217, 2: 0.0115, 3: 0.009, 4: 0.0081, 5: 0.0158, 6: 0.0168, 7: 0.0299, 8: 0.0261, 9: 0.0188, 10: 0.0278, 11: 0.0354, 12: 0.0409, 13: 0.0755, 14: 0.1294, 15: 0.0968, 16: 0.0656, 17: 0.1428, 18: 0.0598, 19: 0.08, 20: 0.0493, 21: 0.0049, 22: 0.0011, 23: 0.0101}


def _n(x: float, d: int = 1, segno: bool = False) -> str:
    return (f"{x:+.{d}f}" if segno else f"{x:.{d}f}").replace(".", ",")


def _chiuso_es(t: datetime) -> bool:
    """I futures sull'S&P 500 sono fermi dal venerdì 22 UTC alla domenica 23 UTC."""
    w, h = t.weekday(), t.hour
    return (w == 4 and h >= 22) or w == 5 or (w == 6 and h < 23)


def quota_varianza(t0: datetime, ore: float) -> float:
    """Parte della varianza giornaliera dei futures che cade nella finestra (t0, t0+ore], per fasce orarie UTC misurate negli ultimi due anni."""
    tot, t, fine = 0.0, t0, t0 + timedelta(hours=ore)
    while t < fine:
        prossima = min(fine, t.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        frac = (prossima - t).total_seconds() / 3600.0
        if not _chiuso_es(t):
            tot += SHARE.get(t.hour, 0.0) * frac
        t = prossima
    return tot


def _mc_z(h: float, n: int, rng) -> np.ndarray:
    """Campioni della variazione standardizzata dei futures: forma empirica degli ultimi due anni per la durata più vicina."""
    chiavi = [1, 3, 6, 12]
    k = min(chiavi, key=lambda c: abs(c - h))
    q = np.array(ZQ[k])
    return q[rng.integers(0, len(q), n)] + rng.normal(0, 0.03, n)


def gap_equo(prezzo_vwce_t: float | None, es_ora: float, es_ancora: float, fx_ora: float, fx_ancora: float) -> float:
    """Variazione attesa del VWCE non ancora riflessa: 0,83 × futures − 0,50 × cambio (dal momento dell'ultimo scambio del VWCE)."""
    return BETA_ES * (es_ora / es_ancora - 1.0) + BETA_FX * (fx_ora / fx_ancora - 1.0)


def rilascio_evento(data: str, ticker: str) -> datetime:
    """Ora (UTC) della pubblicazione: i grandi titoli americani riportano di norma alle 16:20 ora di New York, dopo la chiusura."""
    d = datetime.strptime(data, "%Y-%m-%d").replace(hour=16, minute=20, tzinfo=ZoneInfo("America/New_York"))
    return d.astimezone(timezone.utc)


def eventi_vicini(t0: datetime, calendario: list[dict], entro_ore: float = 40.0) -> list[dict]:
    """Trimestrali dei grandi titoli e dati macro (Fed, inflazione, lavoro) nelle prossime ore, con l'ora esatta di uscita."""
    out = []
    for e in calendario or []:
        nome = (e.get("nome") or "").replace("Trimestrale ", "").strip()
        tk = NOMI_EVENTO.get(nome)
        if not tk or tk not in EVENTI or e.get("tipo", "Trimestrale") != "Trimestrale":
            continue
        r = rilascio_evento(e["date"], tk)
        if timedelta(hours=-6) <= r - t0 <= timedelta(hours=entro_ore):
            n, peso, cont, mossa = EVENTI[tk]
            out.append({"tipo": "trimestrale", "ticker": tk, "nome": n, "corto": n, "quando": r.strftime("%Y-%m-%dT%H:%MZ"), "peso": peso, "k": round(peso / 100 * cont, 4), "mossa_tipica": mossa, "gia_uscita": bool(r <= t0)})
    out += radar.macro_da_calendario(t0, calendario, entro_ore)
    return sorted(out, key=lambda x: x["quando"])


def sd_evento(e: dict) -> float:
    """Deviazione standard della scossa sul VWCE (in frazione): dato macro misurato, oppure peso × contagio × 1,25 × mossa tipica del titolo."""
    if e.get("tipo") == "macro":
        return float(e["sd"])
    return e["k"] * 1.25 * e["mossa_tipica"] / 100.0


def previsione(t0: datetime, vwce: dict, mercato: dict, eventi: list[dict], sims: int = 20000, seed: int | None = None) -> dict:
    """vwce: {prezzo, ora (datetime UTC), aperto}. mercato: {es_ora, es_ancora, fx_ora, fx_ancora, vix}. Restituisce gap atteso e, per ogni orizzonte, intervallo e probabilità."""
    aperto = bool(vwce.get("aperto"))
    ha_ancora = all(mercato.get(k) for k in ("es_ora", "es_ancora", "fx_ora", "fx_ancora"))
    gap = 0.0 if (aperto or not ha_ancora) else gap_equo(vwce.get("prezzo"), mercato["es_ora"], mercato["es_ancora"], mercato["fx_ora"], mercato["fx_ancora"])
    vix = float(mercato.get("vix") or 20.0)
    sd_giorno = vix / 100.0 / math.sqrt(252.0)
    rng = np.random.default_rng(seed if seed is not None else int(t0.timestamp()) % (2 ** 31))
    res = {}
    for nome, h in ORIZZONTI.items():
        q = quota_varianza(t0, h)
        scala = BETA_ES * sd_giorno * math.sqrt(q)
        x = gap + scala * _mc_z(h, sims, rng)
        x = x + rng.normal(0, (SD_TRACK * math.sqrt(h)) if aperto else SD_RESIDUO, sims)
        rimb = (mercato.get("es_24h") is not None and mercato["es_24h"] <= SOGLIA_RIMBALZO
                and not mercato.get("sotto_ma200", False))
        if rimb:
            x = x + DERIVA_RIMBALZO[h] * scala
        ev_h = []
        for e in eventi:
            r = datetime.strptime(e["quando"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
            if t0 < r <= t0 + timedelta(hours=h):
                sd_n = sd_evento(e) * (radar.FATTORE_1H if (e.get("tipo") == "macro" and h <= 1.0) else 1.0)   # una mossa tipica = media del valore assoluto = 0,8 deviazioni standard
                x = x + sd_n * rng.standard_t(5, sims) * math.sqrt(3.0 / 5.0)
                if sd_n >= 0.0015 or e.get("tipo") == "macro":
                    ev_h.append(e.get("corto") or e["nome"])
        p = np.quantile(x, [0.05, 0.10, 0.50, 0.90, 0.95])
        giu, su = x[x < 0], x[x > 0]
        qz = np.quantile(x - gap, np.arange(1, 100) / 100.0)   # forma della distribuzione senza il salto: la pagina la rimette in gioco con i prezzi in diretta
        res[nome] = {"qz": [round(float(v), 5) for v in qz], "ore": h, "atteso": float(gap), "mediana": float(p[2]), "media": float(x.mean()), "p_su": float((x > 0).mean()), "rimbalzo": bool(rimb),
                     "giu_medio": float(giu.mean()) if len(giu) else 0.0, "su_medio": float(su.mean()) if len(su) else 0.0, "p10": float(p[1]), "p90": float(p[3]), "p05": float(p[0]), "p95": float(p[4]),
                     "p_meno1": float((x <= -0.01).mean()), "p_meno15": float((x <= SOGLIA_FORTE).mean()), "p_meno2": float((x <= -0.02).mean()), "p_piu1": float((x >= 0.01).mean()),
                     "eventi": ev_h, "quota_varianza": round(q, 3)}
    return {"gap": float(gap), "aperto": aperto, "orizzonti": res}


def giudizio(r: dict) -> dict:
    """Etichetta semplice: calo forte / rischio di calo / oscillazioni ampie / normale / rialzo, dal salto atteso, dalla probabilità di -1,5% e dal VIX."""
    g = r["gap"]
    p6 = r["orizzonti"]["6 ore"]["p_meno15"]
    p12 = r["orizzonti"]["12 ore"]["p_meno15"]
    vix = (r.get("mercato") or {}).get("vix") or 0
    ev = any(a["eventi"] for a in r["orizzonti"].values())
    if g <= SOGLIA_CALO_FORTE or max(p6, p12) >= 0.20:
        return {"livello": "forte", "testo": "Calo forte probabile", "classe": "bad"}
    if g <= SOGLIA_CALO or max(p6, p12) >= 0.10:
        return {"livello": "calo", "testo": "Rischio di calo", "classe": "warn"}
    if g >= 0.004:
        return {"livello": "su", "testo": "Più probabile un rialzo", "classe": "ok"}
    if vix >= 25 or ev:
        return {"livello": "ampie", "testo": "Oscillazioni più ampie del solito", "classe": "warn"}
    return {"livello": "norm", "testo": "Oscillazioni nella norma", "classe": "ok"}


def scenari(eventi: list[dict]) -> list[dict]:
    """«Se Nvidia sale o scende di x% dopo i conti, il VWCE si muove circa di k×x%»: elenco per ciascun evento."""
    out = []
    for e in eventi:
        if e.get("gia_uscita") or e.get("tipo") == "macro":
            continue
        out.append({"nome": e["nome"], "ticker": e["ticker"], "quando": e["quando"], "mossa_tipica": e["mossa_tipica"],
                    "righe": [{"titolo": x, "vwce": round(e["k"] * x, 2)} for x in (-10, -5, 5, 10)]})
    return out


def _mossa_implicita(tk: str) -> float | None:
    """Mossa attesa dalle opzioni (prezzo della coppia call+put alla pari sulla prima scadenza dopo i conti), in %. None se non disponibile."""
    try:
        import yfinance as yf
        t = yf.Ticker(tk)
        S = float(t.history(period="1d")["Close"].iloc[-1])
        ex = [d for d in t.options if (pd.Timestamp(d) - pd.Timestamp.now()).days >= 1][:1]
        if not ex:
            return None
        ch = t.option_chain(ex[0])
        k = ch.calls["strike"].iloc[(ch.calls["strike"] - S).abs().argsort().iloc[0]]
        c = float(ch.calls.loc[ch.calls["strike"] == k, "lastPrice"].iloc[0])
        p = float(ch.puts.loc[ch.puts["strike"] == k, "lastPrice"].iloc[0])
        m = (c + p) / S * 100.0
        return round(m, 1) if 0.5 < m < 30 else None
    except Exception:  # noqa: BLE001
        return None


def _storia(sym: str, intervallo: str = "5m", periodo: str = "7d") -> pd.Series:
    import yfinance as yf
    h = yf.Ticker(sym).history(period=periodo, interval=intervallo)["Close"].dropna()
    h.index = pd.to_datetime(h.index).tz_convert("UTC")
    return h


def _al(s: pd.Series, t: datetime) -> float | None:
    x = s[s.index <= pd.Timestamp(t)]
    return float(x.iloc[-1]) if len(x) and (pd.Timestamp(t) - x.index[-1]) < pd.Timedelta(hours=30) else None


def leggi_mercato(vwce_t: datetime) -> dict:
    es, fx, vx = _storia("ES=F"), _storia("EURUSD=X"), _storia("^VIX")
    rec = {"es_ora": float(es.iloc[-1]), "es_ancora": _al(es, vwce_t), "fx_ora": float(fx.iloc[-1]), "fx_ancora": _al(fx, vwce_t), "vix": float(vx.iloc[-1]),
           "ora_dati": es.index[-1].strftime("%Y-%m-%dT%H:%MZ")}
    ora = es.index[-1]
    unora = es[es.index <= ora - pd.Timedelta(minutes=58)]
    if len(unora):
        rec["es_1h"] = float(es.iloc[-1] / unora.iloc[-1] - 1.0)
    ventiquattro = es[es.index <= ora - pd.Timedelta(hours=24)]
    if len(ventiquattro) and (ora - ventiquattro.index[-1]) < pd.Timedelta(hours=30):
        rec["es_24h"] = float(es.iloc[-1] / ventiquattro.iloc[-1] - 1.0)
    try:   # tendenza di fondo: sotto la media a 200 giorni il rimbalzo dopo i cali non c'è (emendamento 1)
        from . import store
        sp = store.load("sp500").dropna()
        if len(sp) > 200:
            rec["sotto_ma200"] = bool(float(sp.iloc[-1]) < float(sp.rolling(200).mean().iloc[-1]))
    except Exception:  # noqa: BLE001
        pass
    vun = vx[vx.index <= ora - pd.Timedelta(minutes=58)]
    if len(vun):
        rec["vix_1h"] = float(vx.iloc[-1] / vun.iloc[-1] - 1.0)
    return rec


def leggi_vwce() -> dict | None:
    try:
        q = json.loads((DATA / "live.json").read_text(encoding="utf-8"))["quotes"]["vwce"]
        t = datetime.strptime(q["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return {"prezzo": float(q["price"]), "ora": t, "prev": q.get("prev"), "sede": q.get("venue")}
    except Exception:  # noqa: BLE001
        return None


def _notizie(t0: datetime) -> dict:
    try:
        return radar.notizie(t0)
    except Exception:  # noqa: BLE001
        return {"n": 0, "elenco": [], "tono": None, "temi": {}}


def calcola(adesso: datetime | None = None, con_opzioni: bool = True) -> dict:
    t0 = (adesso or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    v = leggi_vwce()
    if not v:
        raise RuntimeError("prezzo del VWCE non disponibile")
    v["aperto"] = (t0 - v["ora"]) <= timedelta(minutes=20) and not _chiuso_es(t0)
    m = leggi_mercato(v["ora"])
    try:
        cal = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cal = []
    ev = eventi_vicini(t0, cal)
    if con_opzioni:
        try:
            ev = radar.unisci(ev, radar.leggi_ff(t0))
        except Exception:  # noqa: BLE001
            pass
    for e in ev:
        if e.get("tipo") == "macro":
            continue
        st = radar.storico(e["ticker"])
        if st and st["n"] >= 8:
            e["mossa_tipica"] = st["media_abs"]          # misurata sui trimestri passati
        if con_opzioni and not e["gia_uscita"]:
            imp = _mossa_implicita(e["ticker"])
            if imp:
                e["mossa_implicita"] = imp
                e["mossa_tipica"] = imp                    # il mercato la prezza con le opzioni: vale più dello storico
        try:
            radar.arricchisci(e, t0, con_rete=con_opzioni)
        except Exception:  # noqa: BLE001
            pass
    r = previsione(t0, v, m, ev)
    r.update({"ora": t0.strftime("%Y-%m-%dT%H:%MZ"), "vwce": {"prezzo": v["prezzo"], "ora": v["ora"].strftime("%Y-%m-%dT%H:%MZ"), "sede": v.get("sede")}, "mercato": m, "eventi": ev,
              "scenari": scenari(ev), "notizie": _notizie(t0), "giudizio": giudizio(r), "es_1h": m.get("es_1h"), "vix_1h": m.get("vix_1h"),
              "live": {"beta_es": BETA_ES, "beta_fx": BETA_FX, "s_calo": SOGLIA_CALO, "s_calo_forte": SOGLIA_CALO_FORTE, "s_forte": SOGLIA_FORTE}})
    return r


def registra(r: dict) -> None:
    """Una riga per ora nel diario: serve a controllare, in avanti, se le previsioni erano giuste."""
    try:
        d = pd.read_csv(DIARIO)
    except Exception:  # noqa: BLE001
        d = pd.DataFrame(columns=["ora", "prezzo", "gap", "p10_3", "p90_3", "p10_12", "p90_12", "giudizio"])
    chiave = r["ora"][:13]
    if len(d) and d["ora"].astype(str).str[:13].eq(chiave).any():
        return
    a3, a12 = r["orizzonti"]["3 ore"], r["orizzonti"]["12 ore"]
    row = {"ora": r["ora"], "prezzo": r["vwce"]["prezzo"], "gap": round(r["gap"], 5), "p10_3": round(a3["p10"], 5), "p90_3": round(a3["p90"], 5), "p10_12": round(a12["p10"], 5), "p90_12": round(a12["p90"], 5), "giudizio": r["giudizio"]["livello"]}
    pd.concat([d, pd.DataFrame([row])]).tail(4000).to_csv(DIARIO, index=False)


def verifica() -> dict:
    """Confronta le previsioni a 3 e a 12 ore del diario con il prezzo reale del VWCE 3 e 12 ore dopo (solo righe già verificabili)."""
    try:
        d = pd.read_csv(DIARIO)
    except Exception:  # noqa: BLE001
        return {"n": 0}
    if len(d) < 30:
        return {"n": int(len(d)), "pronto": False}
    d["t"] = pd.to_datetime(d["ora"], utc=True)
    s = d.set_index("t")["prezzo"]
    out = {"pronto": True}
    for nome, h, a, b in (("3 ore", 3, "p10_3", "p90_3"), ("12 ore", 12, "p10_12", "p90_12")):
        ok = tot = 0
        for t, row in d.set_index("t").iterrows():
            fut = s[(s.index >= t + pd.Timedelta(hours=h)) & (s.index <= t + pd.Timedelta(hours=h + 1))]
            if not len(fut):
                continue
            r = fut.iloc[0] / row["prezzo"] - 1
            tot += 1
            ok += int(row[a] <= r <= row[b])
        out[nome] = {"n": tot, "dentro": None if not tot else round(ok / tot, 3)}
    return out


def aggiorna(log=print, con_opzioni: bool = True) -> dict | None:
    try:
        r = calcola(con_opzioni=con_opzioni)
    except Exception as e:  # noqa: BLE001
        log("[ore] non calcolata: " + str(e)[:120])
        return carica()
    try:
        registra(r)
        r["verifica"] = verifica()
    except Exception as e:  # noqa: BLE001
        log("[ore] diario non aggiornato: " + str(e)[:80])
    FILE.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    a = r["orizzonti"]["6 ore"]
    log(f"[ore] salto atteso {r['gap'] * 100:+.2f}%, 6 ore: {a['p10'] * 100:+.1f}% … {a['p90'] * 100:+.1f}% · {r['giudizio']['testo']}")
    return r


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- avvisi
def avvisi(r: dict, stato: dict, adesso: datetime | None = None) -> tuple[list[dict], dict]:
    """Funzione pura: decide quali notifiche mandare e il nuovo stato. Tipi: calo atteso (salto stimato ≤ -0,5%; forte se ≤ -1%), movimento brusco in corso (futures ≤ -1% in un'ora),
    evento in arrivo (una volta per evento, entro 8 ore). Mai due volte lo stesso avviso entro 4 ore, a meno che la stima peggiori di 0,5 punti; al massimo 4 al giorno; di notte (23-5 UTC) solo il calo atteso."""
    t0 = adesso or datetime.strptime(r["ora"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    oggi = t0.strftime("%Y-%m-%d")
    st = dict(stato or {})
    if st.get("giorno") != oggi:
        st["giorno"], st["inviati"] = oggi, 0
    out = []

    def ok_invio(tipo: str, valore: float) -> bool:
        u = (st.get("ultimo") or {}).get(tipo)
        if st["inviati"] >= 4:
            return False
        if not u:
            return True
        passato = (t0 - datetime.strptime(u["ora"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)).total_seconds() / 3600
        return passato >= 4 or valore <= u["valore"] - 0.005

    def segna(tipo: str, valore: float):
        st.setdefault("ultimo", {})[tipo] = {"ora": t0.strftime("%Y-%m-%dT%H:%MZ"), "valore": valore}
        st["inviati"] += 1

    gap = r["gap"]
    prezzo = r["vwce"]["prezzo"]
    if gap <= SOGLIA_CALO and not r.get("aperto") and ok_invio("calo", gap):
        forte = gap <= SOGLIA_CALO_FORTE
        out.append({"title": f"VWCE: {'calo forte' if forte else 'calo'} atteso {_n(gap * 100)}%", "priority": 5 if forte else 4, "tags": ["rotating_light"],
                    "message": f"Wall Street e i futures sono scesi dopo l'ultimo scambio del VWCE ({_n(prezzo, 2)} €): all'apertura il valore equo è circa {_n(prezzo * (1 + gap), 2)} € ({_n(gap * 100)}%). Apri l'app, sezione «Prossime ore»."})
        segna("calo", gap)
    es1 = r.get("es_1h")
    if es1 is not None and es1 <= SOGLIA_SHOCK_ES and 5 <= t0.hour < 23 and ok_invio("shock", es1):
        paura = f"La paura del mercato (VIX) è salita del {_n((r.get('vix_1h') or 0) * 100, 0)}% nell'ultima ora. " if r.get("vix_1h") is not None else ""
        out.append({"title": f"Movimento brusco: futures {_n(es1 * 100)}% in un'ora", "priority": 5, "tags": ["warning"],
                    "message": paura + "Il VWCE sta seguendo o seguirà. Apri l'app, sezione «Prossime ore»."})
        segna("shock", es1)
    for e in r.get("eventi") or []:
        quando = datetime.strptime(e["quando"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        chiave = f"{e['ticker']}|{e['quando'][:10]}"
        sd = sd_evento(e)
        if sd < 0.0015:
            continue                                          # eventi troppo piccoli per disturbare
        if not e.get("gia_uscita") and timedelta(0) < quando - t0 <= timedelta(hours=8) and chiave not in (st.get("eventi") or []) and st["inviati"] < 4:
            ora_it = quando.astimezone(ZoneInfo("Europe/Rome")).strftime("%H:%M")
            if e.get("tipo") == "macro":
                titolo = f"{e['nome']} alle {ora_it}"
                msg = f"Dato che può muovere i mercati: sul VWCE la scossa tipica è di circa ±{_n(sd * 100)}% nelle ore dopo l'uscita. {e['cosa']} Apri l'app, sezione «Prossime ore»."
            else:
                titolo = f"{'Stasera' if quando.astimezone(ZoneInfo('Europe/Rome')).hour >= 17 else 'Oggi'} i conti di {e['nome']} (ore {ora_it})"
                msg = (f"Mossa tipica del titolo ±{_n(e['mossa_tipica'], 0)}%: sul VWCE vale in media circa ±{_n(sd / 1.25 * 100)}% al giorno dopo. "
                       "Prima dei conti il rischio di oscillazioni è più alto. Apri l'app, sezione «Prossime ore».")
            out.append({"title": titolo, "priority": 4, "tags": ["calendar"], "message": msg})
            st.setdefault("eventi", []).append(chiave)
            st["inviati"] += 1
    st["eventi"] = (st.get("eventi") or [])[-20:]
    return out, st


def run_avvisi(log=print) -> int:
    """Calcola, salva e invia gli avvisi (serve NTFY_TOPIC). Pensata per girare ogni 15 minuti."""
    import os
    from . import alerts
    r = aggiorna(log)
    if not r:
        return 0
    try:
        st = json.loads(STATO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    msgs, new = avvisi(r, st)
    if msgs and os.environ.get("NTFY_TOPIC"):
        n = alerts.send(msgs)
        log(f"[ore] avvisi inviati: {n} su {len(msgs)}")
    elif msgs:
        log(f"[ore] {len(msgs)} avvisi pronti, ma manca NTFY_TOPIC: " + "; ".join(m["title"] for m in msgs))
    STATO.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(msgs)
