"""Indicatori candidati per il semaforo (Patch 60b, PESO ZERO): si misura se anticipano i cali con la stessa regola dei Grandi fondi
(percentile mobile a 5 anni, «alto» >= 80 o «basso» <= 20, due bersagli, due metà della storia, intervallo a blocchi).
  - curva_vix: VIX3M / VIX (sotto 1 = la paura di oggi supera quella futura); atteso: valori BASSI = più cali;
  - accelerazione_paura: variazione del VIX in 10 sedute; atteso: valori ALTI = più cali;
  - distanza_media50: distanza del prezzo dalla media a 50 sedute (deterioramento di breve); atteso: valori BASSI = più cali.
  - cmf: flusso di denaro di Chaikin a 21 sedute (serve il volume dell'S&P 500, scaricato da ^GSPC); atteso: valori BASSI = più cali.
Con 3 indicatori e 2 direzioni (6 test) un caso fortunato è possibile: un indicatore «dimostrato» passa prima a 12 mesi di prova in ombra."""
import json

import numpy as np
import pandas as pd

from . import grandi_fondi as g
from .config import DATA

FILE = DATA / "candidati.json"
CAND = {
    "curva_vix": ("Curva del VIX (paura a 3 mesi su paura a 1 mese)", "basso"),
    "accelerazione_paura": ("Accelerazione della paura (VIX rispetto a 10 sedute fa)", "alto"),
    "distanza_media50": ("Distanza del prezzo dalla media a 50 sedute", "basso"),
    "cmf": ("Flusso di denaro (CMF a 21 sedute: chiude vicino ai massimi con volumi alti = denaro che entra)", "basso"),
}


def cmf(p: pd.Series, alto: pd.Series, basso: pd.Series, vol: pd.Series, n: int = 21) -> pd.Series:
    """Chaikin Money Flow: somma del (posizione della chiusura nel range del giorno, da -1 a +1) per il volume, divisa per i volumi."""
    d = pd.DataFrame({"c": p, "h": alto, "l": basso, "v": vol}).dropna()
    rng = (d["h"] - d["l"]).replace(0, np.nan)
    mfm = (((d["c"] - d["l"]) - (d["h"] - d["c"])) / rng).clip(-1, 1)
    return ((mfm * d["v"]).rolling(n).sum() / d["v"].rolling(n).sum()).dropna()


def serie(p: pd.Series, vix: pd.Series, vix3m: pd.Series, ohlcv: tuple | None = None) -> dict[str, pd.Series]:
    v = vix.reindex(p.index, method="ffill")
    v3 = vix3m.reindex(p.index, method="ffill")
    out = {"curva_vix": (v3 / v).where(v3.notna() & v.notna()).dropna(),
           "accelerazione_paura": (v / v.shift(10) - 1).dropna(),
           "distanza_media50": (p / p.rolling(50).mean() - 1).dropna()}
    if ohlcv is not None:
        c = cmf(p, *ohlcv)
        if len(c) > 600:
            out["cmf"] = c
    return out


def run(p: pd.Series | None = None) -> dict:
    from . import store
    from .features import closed_sp500
    p = closed_sp500() if p is None else p
    out = {"data": str(p.index[-1].date()), "indicatori": {}}
    try:   # il volume arriva dal download di ^GSPC (sp_vol); senza, il CMF non si calcola
        oh = tuple(store.load(k) for k in ("sp_high", "sp_low", "sp_vol"))
        oh = oh if all(len(x) > 1000 for x in oh) else None
    except Exception:  # noqa: BLE001
        oh = None
    for k, s in serie(p, store.load("vix"), store.load("vix3m"), oh).items():
        nome, atteso = CAND[k]
        pct = g.percentile_mobile(s, 1260, 504)
        pg = pct.reindex(p.index)   # dati di mercato di fine giornata: usati dalla seduta successiva
        pg = pg.shift(1)
        pr = g.prova(p, pg)
        ult = pct.dropna()
        out["indicatori"][k] = {"nome": nome, "atteso": atteso, "valore": float(s.iloc[-1]), "percentile": float(ult.iloc[-1]) if len(ult) else None,
                                "stato": g.stato(float(ult.iloc[-1]) if len(ult) else None), "prova": pr}
    FILE.write_text(json.dumps(out, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def html() -> str:
    from html import escape as e
    d = carica()
    if not d:
        return "<p class='mu'>La prova degli indicatori candidati compare dopo la prossima verifica mensile.</p>"
    out = ["<div class='explain'><p><b>Cosa sono.</b> Segnali che potrebbero migliorare il semaforo. Prima di usarli si controlla, con una regola scritta in anticipo, se in passato hanno davvero anticipato i cali. "
           "<b>Per ora non influiscono su nulla.</b></p></div><div style='overflow-x:auto'><table class='tb'><tr><th>Indicatore</th><th>Oggi</th><th>Ha anticipato i cali?</th></tr>"]
    for k, x in d["indicatori"].items():
        v = x["prova"].get("verdetto", "n.d.")
        verd = "Sì, in entrambe le metà della storia" if v.startswith("dimostrato") else ("Non dimostrato" if v == "nessun segnale dimostrato" else "Dati insufficienti")
        pct = x.get("percentile")
        out.append(f"<tr><td>{e(x['nome'])}</td><td>{'n.d.' if pct is None else f'{pct:.0f}° percentile'} ({e(x['stato'])})</td><td>{e(verd)}</td></tr>")
    out.append("</table></div><p class='mu'>Il flusso di denaro (CMF) compare qui appena è stato scaricato il volume dell'S&amp;P 500 (primo «Aggiornamento giornaliero» dopo questa versione).</p>")
    return "".join(out)
