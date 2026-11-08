"""Modalita' ombra (4.1): ogni giorno i motori sfidanti scrivono la loro previsione in data/journal_shadow.csv
(stessa catena di firme del diario vero). Non influenzano l'app: dopo circa 6 mesi si confrontano con il modello in uso."""
import html as _h

import numpy as np
import pandas as pd

from . import journal
from .config import DATA, HORIZONS, HZ_LABEL, PRIMARY, TARGETS
from .features import fwd_maxdd
from .model import level_of

SHADOW = DATA / "journal_shadow.csv"
EVAL = DATA / "model_eval.json"
NOMI = {"FHS": "FHS (simulazione)", "FHS+VIX": "FHS + VIX (simulazione corretta con il VIX)", "MV-logit": "Multi-variabile (logistica)", "MV-GBM": "Multi-variabile (alberi)",
        "MVF-GBM": "Multi-variabile + famiglie Indice (alberi)", "Combinato-pesi": "Combinato (pesi, senza taratura)"}
MIN_MONTHS = 6   # prima di questo il confronto e' solo indicativo


def _pred(ps: dict, a1: dict, ret: dict | None = None) -> dict:
    """Costruisce una previsione nel formato del diario: probabilita' per le soglie di TARGETS, normale e livello del modello in uso."""
    out = {}
    for hz, p in ps.items():
        if hz not in a1 or any(t not in p for t in TARGETS[hz]):
            continue
        base = {t: a1[hz]["base"][t] for t in TARGETS[hz]}
        prim = PRIMARY[hz]
        ratio = p[prim] / base[prim] if base[prim] > 0 else 1.0
        row = {"p": {t: float(p[t]) for t in TARGETS[hz]}, "base": base, "ratio": float(ratio), "level": level_of(ratio)}
        if ret and hz in ret:
            row["ret"] = ret[hz]
        out[hz] = row
    return out


def _mv(p: pd.Series, t, algo: str, fam: bool) -> dict:
    from .model_mv import MVEngine
    eng = MVEngine(p, algo, fam)
    if t not in eng.F.index:
        return {}
    pr = eng.predict(eng.fit(t), t)
    return {hz: pr[hz]["p"] for hz in pr}


def combined(raw: dict[str, dict]) -> dict:
    """Media pesata dei motori con i pesi stimati nell'ultima convalida mensile (senza taratura isotonica)."""
    import json
    try:
        W = json.loads(EVAL.read_text(encoding="utf-8"))["ensemble"]["weights"]
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for hz in HORIZONS:
        w = W.get(f"{hz}|down")
        if not w or any(m not in raw or hz not in raw[m] for m in w["modelli"]):
            continue
        out[hz] = {t: float(sum(x * raw[m][hz][t] for m, x in zip(w["modelli"], w["pesi"]))) for t in TARGETS[hz]}
    return out


def predictions(p: pd.Series, t, a1: dict) -> dict[str, dict]:
    """Previsioni di oggi dei motori sfidanti, ognuna nel formato del diario. Un motore che fallisce viene saltato."""
    from . import fhs
    raw, ret, out = {"A1": {hz: a1[hz]["p"] for hz in a1}}, {}, {}
    try:
        f = fhs.forecast(p, date=t, sims=3000, seed=int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31))
        raw["FHS"] = {hz: {th: f[hz]["down"][th]["p"] for th in TARGETS[hz]} for hz in HORIZONS if th_ok(f, hz)}
        ret["FHS"] = {hz: {k: f[hz]["ret_analog"][k] for k in ("q10", "q50", "q90")} for hz in HORIZONS}
    except Exception as e:  # noqa: BLE001
        print("[ombra] FHS non calcolato:", str(e)[:80])
    try:   # sfidante in prova: stessa simulazione corretta con il VIX (peso 0,5), dalla patch 26 nel diario ombra
        from . import campioni
        v = campioni._vix_a(t)
        f2 = fhs.forecast(p, date=t, sims=3000, seed=int(pd.Timestamp(t).strftime("%Y%m%d")) % (2 ** 31), vix=v, w=0.5)
        raw["FHS+VIX"] = {hz: {th: f2[hz]["down"][th]["p"] for th in TARGETS[hz]} for hz in HORIZONS if th_ok(f2, hz)}
        ret["FHS+VIX"] = {hz: {k: f2[hz]["ret_analog"][k] for k in ("q10", "q50", "q90")} for hz in HORIZONS}
    except Exception as e:  # noqa: BLE001
        print("[ombra] FHS+VIX non calcolato:", str(e)[:80])
    for name, algo, fam in (("MV-logit", "logit", False), ("MV-GBM", "gbm", False), ("MVF-GBM", "gbm", True)):
        try:
            r = _mv(p, t, algo, fam)
            if r:
                raw[name] = r
        except Exception as e:  # noqa: BLE001
            print(f"[ombra] {name} non calcolato:", str(e)[:80])
    for name in ("FHS", "FHS+VIX", "MV-logit", "MV-GBM", "MVF-GBM"):
        if name in raw:
            out[name] = _pred(raw[name], a1, ret.get(name))
    c = combined(raw)
    if c:
        out["Combinato-pesi"] = _pred(c, a1)
    return out


def th_ok(f: dict, hz: str) -> bool:
    return all(t in f[hz]["down"] for t in TARGETS[hz])


def run(p: pd.Series, t, a1: dict, spot: float, path=None) -> int:
    """Scrive nel diario ombra le previsioni di oggi. Restituisce il numero di righe nuove."""
    path = path or SHADOW
    n = 0
    for name, pred in predictions(p, t, a1).items():
        n += journal.append(pd.Timestamp(t).strftime("%Y-%m-%d"), spot, pred, model=name, path=path)
    print(f"[ombra] {n} righe nuove in {path.name}")
    return n


def scores_from(shadow: pd.DataFrame, main: pd.DataFrame, sp: pd.Series) -> pd.DataFrame:
    """Brier di ogni motore contro il normale sulle sole previsioni scadute, confrontando alla pari con il modello in uso.
    Esito: calo massimo dell'S&P 500 nelle sedute dell'orizzonte (>= soglia primaria della riga)."""
    d = pd.concat([shadow.assign(src="ombra"), main.assign(src="uso")], ignore_index=True)
    if d.empty:
        return pd.DataFrame()
    rows = []
    cache = {}
    for r in d.itertuples():
        n = HORIZONS.get(r.horizon)
        if n is None:
            continue
        if n not in cache:
            cache[n] = fwd_maxdd(sp, n)
        a = pd.Timestamp(r.asof)
        e = cache[n].get(a, np.nan)
        if pd.isna(e):
            continue
        rows.append({"asof": r.asof, "hz": r.horizon, "model": r.model, "src": r.src, "p": float(r.p1), "base": float(r.base1),
                     "y": float(e <= -float(r.thr1) / 100)})
    if not rows:
        return pd.DataFrame()
    x = pd.DataFrame(rows)
    # confronto alla pari: solo (data, orizzonte) presenti in tutti i modelli
    k = x.groupby(["asof", "hz"]).model.nunique()
    ok = k[k == x.model.nunique()].index
    x = x.set_index(["asof", "hz"]).loc[ok].reset_index() if len(ok) else x.iloc[0:0]
    out = []
    for (m, hz), g in x.groupby(["model", "hz"]):
        bm, bb = float(((g.p - g.y) ** 2).mean()), float(((g.base - g.y) ** 2).mean())
        out.append({"model": m, "hz": hz, "n": int(len(g)), "brier": bm, "brier_base": bb, "bss": 1 - bm / bb if bb > 0 else np.nan,
                    "first": str(g["asof"].min())})
    return pd.DataFrame(out)


def html(sp: pd.Series) -> str:
    e = _h.escape
    try:
        sh, mn = journal.read(SHADOW), journal.read()
        n_days = sh.asof.nunique() if len(sh) else 0
        sc = scores_from(sh, mn, sp)
    except Exception:  # noqa: BLE001
        return ""
    head = ("<h3>Motori sfidanti in modalità ombra</h3><p class='mu'>Ogni giorno FHS e i modelli multi-variabile scrivono la loro previsione in un diario a parte, senza influenzare l'app. "
            f"Dopo circa {MIN_MONTHS} mesi si confrontano dal vivo con il modello in uso. Giorni registrati finora: <b>{n_days}</b>.</p>")
    if sc.empty:
        return head + "<p class='mu'>Nessuna previsione ombra è ancora scaduta: il confronto comincia dopo la prima scadenza.</p>"
    rows = ""
    for r in sc.sort_values(["hz", "model"]).itertuples():
        nm = NOMI.get(r.model, "Modello in uso (" + r.model + ")")
        rows += f"<tr><td>{HZ_LABEL[r.hz]}</td><td>{e(nm)}</td><td>{r.n}</td><td>{r.brier:.4f}</td><td>{r.bss:+.2f}</td></tr>".replace(".", ",")
    return head + ("<div class='scroll'><table><tr><th>Orizzonte</th><th>Motore</th><th>Previsioni scadute</th><th>Brier</th><th>BSS contro il normale</th></tr>" + rows + "</table></div>"
                   "<p class='mu'>Meno Brier = meglio; BSS &gt; 0 = meglio del «normale». Previsioni vicine nel tempo si sovrappongono: pochi casi indipendenti, giudizio solo indicativo.</p>")
