"""Bilanci trimestrali SEC a più trimestri, con la data di pubblicazione (Patch 71).
Dai «fatti» ufficiali della SEC (companyfacts) si ricostruiscono fino a 12 trimestri di ricavi e utile operativo. Ogni valore ha la data in cui
è stato depositato (`filed`): con `asof` si usano solo i dati già pubblici a quella data (nessun dato dal futuro, utile per i test storici).
Il quarto trimestre non è mai un fatto a sé: si ottiene dal bilancio annuale meno i primi tre trimestri.
Indicatori:
- accelerazione dei ricavi: crescita sull'anno prima dell'ultimo trimestre meno quella del trimestre precedente (in punti percentuali);
- leva operativa: quanto cresce l'utile operativo per ogni 1% di crescita dei ricavi (solo se entrambi positivi);
- margine operativo: variazione sull'anno prima, e svolta (da perdita a utile)."""
import numpy as np

CONCETTI_RICAVI = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax")
CONCETTI_UTILE_OP = ("OperatingIncomeLoss",)


def _giorni(a: str, b: str) -> int:
    return int((np.datetime64(b) - np.datetime64(a)).astype(int))


def trimestri(facts: dict, concetti: tuple[str, ...], asof: str | None = None, massimo: int = 12) -> list[dict]:
    """Elenco [{fine, val, deposito}] ordinato per fine trimestre, solo fatti con deposito ≤ asof. Usa il primo concetto che dà almeno 5 trimestri."""
    try:
        us = facts["facts"]["us-gaap"]
    except (KeyError, TypeError):
        return []
    for nome in concetti:
        try:
            units = us[nome]["units"]["USD"]
        except (KeyError, TypeError):
            continue
        rows = []
        for r in units:
            try:
                if r.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                    continue
                if asof is not None and r.get("filed", "9999") > asof:
                    continue
                rows.append({"start": r["start"], "end": r["end"], "val": float(r["val"]), "filed": r.get("filed", ""), "dur": _giorni(r["start"], r["end"])})
            except (KeyError, ValueError, TypeError):
                continue
        # per ogni periodo (start, end) vale l'ultimo deposito (rettifiche incluse)
        per: dict[tuple, dict] = {}
        for r in sorted(rows, key=lambda x: x["filed"]):
            per[(r["start"], r["end"])] = r
        q = {}
        for (s, e), r in per.items():
            if 80 <= r["dur"] <= 100:
                q[e] = {"fine": e, "val": r["val"], "deposito": r["filed"]}
        for (s, e), r in per.items():      # quarto trimestre = anno − primi tre trimestri dello stesso anno fiscale
            if 350 <= r["dur"] <= 380 and e not in q:
                prime = [v for (s2, e2), v in per.items() if 80 <= v["dur"] <= 100 and s <= s2 and e2 < e]
                if len(prime) >= 3:
                    prime = sorted(prime, key=lambda v: v["end"])[-3:]
                    if _giorni(prime[0]["start"], prime[-1]["end"]) > 0 and _giorni(prime[-1]["end"], e) <= 110:
                        q[e] = {"fine": e, "val": r["val"] - sum(v["val"] for v in prime), "deposito": r["filed"]}
        out = sorted(q.values(), key=lambda x: x["fine"])
        if len(out) >= 5:
            return out[-massimo:]
    return []


def _anno_prima(serie: list[dict], i: int) -> dict | None:
    for j in range(i - 1, -1, -1):
        d = _giorni(serie[j]["fine"], serie[i]["fine"])
        if 350 <= d <= 380:
            return serie[j]
        if d > 380:
            break
    return None


def _crescita(serie: list[dict], i: int) -> float | None:
    p = _anno_prima(serie, i)
    if not p or p["val"] <= 0:
        return None
    return serie[i]["val"] / p["val"] - 1


def indicatori(facts: dict, asof: str | None = None) -> dict:
    """{accel, leva_op, margine_op_var, svolta, n_trim, ultimo_deposito} (None se non calcolabile)."""
    ric = trimestri(facts, CONCETTI_RICAVI, asof)
    out = {"accel": None, "leva_op": None, "margine_op_var": None, "svolta": None, "n_trim": len(ric), "ultimo_deposito": ric[-1]["deposito"] if ric else None}
    if len(ric) < 6:
        return out
    g0, g1 = _crescita(ric, len(ric) - 1), _crescita(ric, len(ric) - 2)
    if g0 is not None and g1 is not None:
        out["accel"] = float((g0 - g1) * 100)     # punti percentuali
    ut = {q["fine"]: q for q in trimestri(facts, CONCETTI_UTILE_OP, asof)}
    if not ut or ric[-1]["fine"] not in ut:
        return out
    r0 = ric[-1]
    rp = _anno_prima(ric, len(ric) - 1)
    u0 = ut[r0["fine"]]["val"]
    up = ut.get(rp["fine"], {}).get("val") if rp else None
    if rp and up is not None and r0["val"] > 0 and rp["val"] > 0:
        m0, mp = u0 / r0["val"], up / rp["val"]
        out["margine_op_var"] = float((m0 - mp) * 100)
        out["svolta"] = bool(up < 0 <= u0)
        gr = r0["val"] / rp["val"] - 1
        if up > 0 and u0 > 0 and gr > 0.02:
            out["leva_op"] = float(np.clip((u0 / up - 1) / gr, -5, 10))
    return out
