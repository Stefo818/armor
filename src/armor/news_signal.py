"""Tono delle notizie (FinBERT) come variabile dei modelli (4.3): PRONTO MA SPENTO.
Si accende solo se (1) ATTIVO = True (scelta manuale), (2) ci sono almeno 18 mesi (548 giorni) di storia giornaliera salvata nel registro
e (3) il modello con la variabile supera la regola di adozione (ensemble.adoption / challenger). Fino ad allora il tono resta solo informativo.
Prima data utile (stima): 18 mesi dopo la prima riga del registro con tono delle notizie."""
import numpy as np
import pandas as pd

ATTIVO = False
MIN_GIORNI = 548
COL = "news_sent_macro"


def storia(reg: pd.DataFrame | None = None) -> pd.Series:
    """Serie giornaliera del tono delle notizie macro salvata nel registro (vuota se manca)."""
    if reg is None:
        from . import registry
        reg = registry.read()
    if reg is None or reg.empty or COL not in reg:
        return pd.Series(dtype=float)
    s = pd.Series(pd.to_numeric(reg[COL], errors="coerce").values, index=pd.to_datetime(reg["date"])).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def giorni_di_storia(s: pd.Series) -> int:
    return int((s.index[-1] - s.index[0]).days) if len(s) > 1 else 0


def idoneo(s: pd.Series) -> tuple[bool, str]:
    if not ATTIVO:
        return False, "disattivato: il tono delle notizie resta solo informativo"
    g = giorni_di_storia(s)
    if g < MIN_GIORNI:
        return False, f"storia insufficiente: {g} giorni su {MIN_GIORNI} richiesti"
    return True, "ok"


def feature(idx: pd.DatetimeIndex, reg: pd.DataFrame | None = None) -> pd.DataFrame | None:
    """Media a 21 giorni del tono, spostata di un giorno (nessuno sguardo al futuro). None finche' non e' idoneo."""
    s = storia(reg)
    ok, _ = idoneo(s)
    if not ok:
        return None
    t = s.rolling(21, min_periods=10).mean()
    full = t.reindex(pd.date_range(t.index[0], idx[-1])).ffill(limit=5).shift(1)
    return pd.DataFrame({"news_tone21": full.reindex(idx)})


def stato(reg: pd.DataFrame | None = None) -> dict:
    s = storia(reg)
    ok, why = idoneo(s)
    return {"attivo": ok, "motivo": why, "giorni": giorni_di_storia(s), "richiesti": MIN_GIORNI,
            "pronto_dal": None if s.empty else str((s.index[0] + pd.Timedelta(days=MIN_GIORNI)).date())}
