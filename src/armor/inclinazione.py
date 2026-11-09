"""Inclinazione del mercato (Patch 55-56): tendenza osservata e direzione letta per SITUAZIONE, solo dove i dati storici la sostengono in più epoche.
Perché per situazione: «sotto la media a 200 giorni» da sola sembra funzionare nel 2000-2012 e fallire dopo, ma quel periodo contiene due soli mercati orso contati
migliaia di volte. Le differenze robuste sono altre: la PERSISTENZA sotto la media (orso confermato, ≥40 sedute) e la PAURA (VIX alto = di solito si compra, non si vende).
ATTENZIONE: le situazioni sono state scelte DOPO un'analisi della storia 1985-2026, quindi sono in parte adattate ai dati già visti. La prova vera è il registro che parte dal giorno dell'attivazione (Patch 56). Da qui in poi non modificarle:
  Situazioni (in ordine di priorità): panico (VIX>30) · paura in tendenza intatta (sopra la media a 200 sedute e VIX 25-30) · orso confermato (sotto la media da ≥40 sedute)
  · correzione (sotto da meno di 40 sedute) · calma estrema (sopra, massimo a meno del 2% e VIX<15) · tendenza normale (tutto il resto).
  Sovrapposizioni con l'Indice Armor (dal 2000): «sopra la media con Indice ≥55» e «sotto la media con Indice ≥55».
  Epoche: 1991-1999, 2000-2012, 2013-oggi. Una situazione conta in un'epoca solo con ≥100 giorni e ≥3 episodi indipendenti (separati da 63 sedute).
  Verdetto a 1 e 3 mesi: «rialzo» se in TUTTE le epoche valide (almeno 2) la frequenza di rialzo supera la normale dell'epoca di ≥3 punti, «ribasso» se la inferisce di ≥3 punti
  in tutte; altrimenti «nessun segnale affidabile». Affidabilità: «più solida» con 3 epoche concordanti, «media» con 2.
Ogni giorno la situazione e il verdetto sono registrati in data/inclinazione_registro2.csv e ogni mese si misura se hanno battuto la frequenza normale."""
import json

import numpy as np
import pandas as pd

from .config import DATA

REGISTRO = DATA / "inclinazione_registro2.csv"
FILE_VERIFICA = DATA / "inclinazione_verifica.json"
ORIZZ = {"1m": 21, "3m": 63}
SOGLIA = 0.03
EPOCHE = [("1991-1999", "1991-01-01", "1999-12-31"), ("2000-2012", "2000-01-01", "2012-12-31"), ("2013-oggi", "2013-01-01", "2100-12-31")]
MIN_N, MIN_EP = 100, 3
SIT = {"panico": ("Panico: paura estrema (VIX sopra 30)", "Storicamente è stato quasi sempre un momento in cui chi vendeva ha venduto vicino ai minimi."),
       "paura": ("Paura in una tendenza ancora sana (VIX 25-30, sopra la media a 200 giorni)", "Il mercato è nervoso ma non rotto: di solito i rimbalzi arrivano."),
       "orso": ("Orso confermato (sotto la media a 200 giorni da almeno 40 sedute)", "Le prime settimane sotto la media sono spesso solo correzioni; dopo 40 sedute il mercato è in una fase debole vera."),
       "correzione": ("Correzione recente (sotto la media a 200 giorni da meno di 40 sedute)", "Un calo recente senza conferma: spesso rimbalza, ma può diventare orso."),
       "calma": ("Calma estrema (sopra la media, vicino ai massimi, VIX sotto 15)", "Poca paura: i rendimenti successivi sono stati nella norma o appena sotto."),
       "normale": ("Tendenza normale (sopra la media a 200 giorni)", "Nessuna condizione particolare."),
       "aix_sopra": ("Indice Armor alto (≥55) ma prezzi sopra la media", "Rischio elevato con prezzi che reggono: storicamente i mesi successivi sono stati buoni."),
       "aix_sotto": ("Indice Armor alto (≥55) e prezzi sotto la media", "Rischio elevato e prezzi deboli insieme.")}
ORDINE = ["panico", "paura", "orso", "correzione", "calma", "normale", "aix_sopra", "aix_sotto"]


def segnali(p: pd.Series, vix: pd.Series | None = None, aix: pd.Series | None = None) -> pd.DataFrame:
    lp = np.log(p)
    f = pd.DataFrame({"trend200": lp - np.log(p.rolling(200).mean()), "mom12_1": lp.shift(21) - lp.shift(252), "mom3": lp - lp.shift(63),
                      "dd": p / p.rolling(252).max() - 1, "r10": p / p.shift(10) - 1})
    f["neg10"] = (p.pct_change() < 0).rolling(10).sum()
    f["score3"] = (f["trend200"] > 0).astype(int) + (f["mom12_1"] > 0).astype(int) + (f["mom3"] > 0).astype(int)
    f["lungo"] = f["score3"].map({3: "rialzista", 0: "ribassista", 1: "mista", 2: "mista"})
    f["breve"] = np.where(f["r10"] < -0.03, "in calo", np.where(f["r10"] > 0.03, "in rialzo", "laterale"))
    sotto = (f["trend200"] < 0)
    f["run"] = sotto.groupby((~sotto).cumsum()).cumsum()
    f["vix"] = (vix.reindex(p.index.union(vix.index)).ffill().reindex(p.index).shift(1) if vix is not None else np.nan)
    f["aix"] = (aix.reindex(p.index.union(aix.index)).ffill().reindex(p.index).shift(1) if aix is not None else np.nan)
    v = f["vix"]
    sit = np.select([v > 30, (~sotto) & (v >= 25), sotto & (f["run"] >= 40), sotto, (~sotto) & (f["dd"] > -0.02) & (v < 15)], ["panico", "paura", "orso", "correzione", "calma"], "normale")
    f["sit"] = np.where(v.isna(), "", sit)
    f["aix_sopra"] = (~sotto) & (f["aix"] >= 55)
    f["aix_sotto"] = sotto & (f["aix"] >= 55)
    return f.dropna(subset=["trend200", "mom12_1", "mom3", "r10"])


def _maschera(f: pd.DataFrame, s: str) -> pd.Series:
    return f[s] if s.startswith("aix_") else (f["sit"] == s)


def _episodi(idx, h: int, posizioni: np.ndarray) -> int:
    if len(posizioni) == 0:
        return 0
    return int(1 + (np.diff(posizioni) > h).sum())


def frequenze(p: pd.Series, f: pd.DataFrame, s: str) -> dict:
    """Per una situazione e ogni orizzonte: frequenza di rialzo e normale in ogni epoca, mediana, caso brutto, verdetto e affidabilità."""
    out = {}
    msk = _maschera(f, s)
    for nome, h in ORIZZ.items():
        r = (p.shift(-h) / p - 1).reindex(f.index)
        ok = r.notna()
        ep, deltas = [], []
        for et, a, b in EPOCHE:
            m = (f.index >= a) & (f.index <= b)
            base = (r[ok & m] > 0).mean()
            sel = ok & m & msk
            n = int(sel.sum())
            pos = np.flatnonzero(np.asarray(sel))
            nep = _episodi(f.index, h, pos)
            valida = n >= MIN_N and nep >= MIN_EP
            pu = float((r[sel] > 0).mean()) if n else None
            ep.append({"e": et, "n": n, "ep": nep, "p": pu, "base": None if np.isnan(base) else float(base), "ok": valida})
            if valida:
                deltas.append(pu - base)
        if len(deltas) >= 2 and min(deltas) >= SOGLIA:
            v = "rialzo"
        elif len(deltas) >= 2 and max(deltas) <= -SOGLIA:
            v = "ribasso"
        else:
            v = "nd"
        q = r[ok & msk]
        out[nome] = {"epoche": ep, "verdetto": v, "aff": ("più solida" if len(deltas) == 3 else "media") if v != "nd" else "", "mediana": float(q.median()) if len(q) >= MIN_N else None,
                     "p10": float(q.quantile(.10)) if len(q) >= MIN_N else None, "base_tot": float((r[ok] > 0).mean())}
    return out


def oggi(p: pd.Series, vix: pd.Series | None = None, aix: pd.Series | None = None) -> dict | None:
    f = segnali(p, vix, aix)
    if len(f) < 500:
        return None
    u = f.iloc[-1]
    sit = u["sit"] or "normale"
    attive = [sit] + [s for s in ("aix_sopra", "aix_sotto") if bool(u[s])]
    return {"data": str(f.index[-1].date()), "lungo": u["lungo"], "breve": u["breve"], "score3": int(u["score3"]), "trend200": float(u["trend200"]), "mom12_1": float(u["mom12_1"]),
            "mom3": float(u["mom3"]), "dd": float(u["dd"]), "r10": float(u["r10"]), "neg10": int(u["neg10"]), "vix": None if pd.isna(u["vix"]) else float(u["vix"]),
            "aix": None if pd.isna(u["aix"]) else float(u["aix"]), "run": int(u["run"]), "sit": sit, "attive": attive, "freq": {s: frequenze(p, f, s) for s in attive},
            "tutte": {s: {h: {"v": x[h]["verdetto"], "aff": x[h]["aff"]} for h in ORIZZ} for s, x in ((s, frequenze(p, f, s)) for s in ORDINE if (f["sit"] == s).any() or s.startswith("aix_"))}}


def verdetto(d: dict) -> dict:
    """Sintesi: per orizzonte, il verdetto della situazione principale; se le sovrapposizioni con l'Indice Armor concordano lo rafforzano, se contraddicono si torna a «nessun segnale»."""
    out = {}
    for h in ORIZZ:
        vs = [(s, d["freq"][s][h]["verdetto"]) for s in d["attive"]]
        base = vs[0][1]
        altri = [v for _, v in vs[1:] if v != "nd"]
        if base == "nd" and altri and all(a == altri[0] for a in altri):
            out[h] = altri[0]
        elif base != "nd" and any(a != base for a in altri):
            out[h] = "nd"
        else:
            out[h] = base
    return out


def registra(d: dict, file=None) -> bool:
    _f = file or REGISTRO
    esiste = _f.exists() and _f.stat().st_size > 0
    if esiste and _f.read_text(encoding="utf-8").splitlines()[-1].startswith(d["data"] + ","):
        return False
    v = verdetto(d)
    riga = ",".join([d["data"], d["lungo"], d["breve"], d["sit"], "+".join(d["attive"][1:]), v["1m"], v["3m"]])
    with open(_f, "a", encoding="utf-8") as fh:
        if not esiste:
            fh.write("data,lungo,breve,sit,extra,v1m,v3m\n")
        fh.write(riga + "\n")
    return True


def verifica(p: pd.Series, file=None) -> dict:
    """Esiti maturati: per ogni verdetto, quante volte il mercato è davvero salito, contro la frequenza normale di tutte le date registrate."""
    _f = file or REGISTRO
    if not _f.exists():
        return {"n": 0}
    g = pd.read_csv(_f, parse_dates=["data"])
    out = {"n": len(g), "orizzonti": {}}
    for nome, h in ORIZZ.items():
        r = (p.shift(-h) / p - 1)
        g[nome] = [r.iloc[r.index.searchsorted(d)] if r.index.searchsorted(d) < len(r) else np.nan for d in g["data"]]
        m = g[g[nome].notna()]
        if len(m) == 0:
            out["orizzonti"][nome] = {"maturi": 0}
            continue
        y = (m[nome] > 0)
        o = {"maturi": len(m), "salito_tot": float(y.mean()), "per_verdetto": {}}
        for v in ("rialzo", "ribasso", "nd"):
            s = m["v" + nome] == v
            if s.sum():
                o["per_verdetto"][v] = {"n": int(s.sum()), "salito": float(y[s].mean())}
        out["orizzonti"][nome] = o
    return out


def aggiorna(p: pd.Series, vix=None, aix=None, log=print) -> dict | None:
    d = oggi(p, vix, aix)
    if not d:
        return None
    nuova = registra(d)
    FILE_VERIFICA.write_text(json.dumps(verifica(p), ensure_ascii=False), encoding="utf-8")
    v = verdetto(d)
    log(f"[inclinazione] {d['data']} situazione={d['sit']} extra={d['attive'][1:]} v1m={v['1m']} v3m={v['3m']} registrata={nuova}")
    return d


# ---------------------------------------------------------------- pagina
def _pc(x):
    return "n/d" if x is None else f"{x * 100:.0f}%"


def _sg(x, d=1):
    return f"{x * 100:+.{d}f}%".replace(".", ",").replace("-", "−")


VT = {"rialzo": "<b class='tx-ok'>Inclinazione al rialzo</b>", "ribasso": "<b class='tx-ba'>Inclinazione al ribasso</b>", "nd": "<b>Nessun segnale affidabile</b>"}


def html(d: dict | None, ver: dict | None = None) -> str:
    if not d:
        return ""
    cl = d["lungo"]
    col = {"rialzista": "ok", "ribassista": "ba", "mista": "wa"}[cl]
    sopra = "sopra" if d["trend200"] > 0 else "sotto"
    frase = {"rialzista": "tutti e tre i segnali di tendenza sono positivi", "ribassista": "tutti e tre i segnali di tendenza sono negativi", "mista": f"{d['score3']} segnali su 3 sono positivi"}[cl]
    v = verdetto(d)
    righe = []
    for s in d["attive"]:
        for nome, et in (("1m", "1 mese"), ("3m", "3 mesi")):
            x = d["freq"][s][nome]
            celle = "".join(f"<td>{_pc(e['p']) if e['ok'] else 'pochi casi'}<br><span class='mu'>normale {_pc(e['base'])} · {e['ep']} episodi</span></td>" for e in x["epoche"])
            righe.append(f"<tr><td><b>{et}</b><br><span class='mu'>{SIT[s][0]}</span></td><td>{VT[x['verdetto']]}" + (f"<br><span class='mu'>affidabilità {x['aff']}</span>" if x["aff"] else "") + f"</td>{celle}"
                         f"<td>{_sg(x['mediana']) if x['mediana'] is not None else 'n/d'}<br><span class='mu'>10% dei casi peggio di {_sg(x['p10'], 0) if x['p10'] is not None else 'n/d'}</span></td></tr>")
    tutte = []
    for s in ORDINE:
        if s not in d["tutte"]:
            continue
        x = d["tutte"][s]
        cl_hi = " class='hi'" if s in d["attive"] else ""
        tutte.append(f"<tr{cl_hi}><td>{SIT[s][0]}<br><span class='mu'>{SIT[s][1]}</span></td><td>{VT[x['1m']['v']]}</td><td>{VT[x['3m']['v']]}</td></tr>")
    vt = ""
    if ver and ver.get("n"):
        parti = []
        for nome, et in (("1m", "1 mese"), ("3m", "3 mesi")):
            o = (ver.get("orizzonti") or {}).get(nome) or {}
            if o.get("maturi"):
                dett = ", ".join(f"«{k}»: {x['n']} giorni, salito il {_pc(x['salito'])}" for k, x in o["per_verdetto"].items())
                parti.append(f"{et}: {o['maturi']} giorni verificati, mercato salito il {_pc(o['salito_tot'])} delle volte ({dett})")
        vt = ("<p class='mu'><b>Verifica reale dal giorno in cui l'app è attiva:</b> " + ("; ".join(parti) if parti else "ancora nessun esito maturato (servono almeno 21 sedute).") + "</p>")
    sintesi = ("<b>Direzione a 1 mese:</b> " + VT[v["1m"]] + " · <b>a 3 mesi:</b> " + VT[v["3m"]])
    extra = f"VIX {d['vix']:.1f}".replace(".", ",") + " · " if d["vix"] is not None else ""
    extra += f"Indice Armor {d['aix']:.0f} · " if d["aix"] is not None else ""
    return ("<h2>Inclinazione del mercato: tendenza e direzione</h2><div class='explain'><p><b>In breve.</b> La <b>tendenza</b> descrive cosa ha fatto il mercato (è un fatto, non una previsione). "
            "La <b>direzione</b> viene letta per <b>situazione</b> (panico, correzione, orso confermato…) e viene indicata solo se, in passato, quella situazione ha battuto la frequenza normale in <b>tutte</b> le epoche (anni '90, 2000-2012, dal 2013), con casi indipendenti sufficienti. "
            "Altrimenti l'app dice «nessun segnale affidabile» invece di mostrare un ottimismo di default. «Normale» = quante volte il mercato sale comunque (circa 6 volte su 10 a un mese).</p></div>"
            f"<div class='b5 {col}' style='padding:14px;border-radius:14px'><b style='font-size:18px'>Tendenza di fondo: {cl}</b> · situazione: <b>{SIT[d['sit']][0]}</b><br>{extra}Oggi {frase}: l'S&amp;P 500 è {sopra} la media a 200 giorni ({_sg(d['trend200'])}), "
            f"da {d['run']} sedute sotto la media, rendimento a 12 mesi (escluso l'ultimo) {_sg(d['mom12_1'])}, a 3 mesi {_sg(d['mom3'])}, {abs(d['dd']) * 100:.0f}% sotto il massimo dell'ultimo anno.<br>"
            f"<b>Ultime 10 sedute: {d['breve']}</b> ({_sg(d['r10'])}, {d['neg10']} sedute su 10 in calo).<br>{sintesi}</div>"
            "<div class='tw'><table class='t'><tr><th>Orizzonte e situazione</th><th>Direzione</th>" + "".join(f"<th>Salito {e[0]}</th>" for e in EPOCHE) + "<th>Dopo situazioni come questa</th></tr>" + "".join(righe) + "</table></div>"
            "<details><summary>Tutte le situazioni e il loro verdetto storico</summary><div class='tw'><table class='t'><tr><th>Situazione</th><th>1 mese</th><th>3 mesi</th></tr>" + "".join(tutte) + "</table></div></details>"
            + vt + "<p class='mu'>Le situazioni sono state individuate analizzando la storia già nota: la prova vera è la verifica reale qui sopra, che si accumula da oggi. Con circa 35 anni di dati gli episodi indipendenti sono pochi, quindi anche i verdetti «più solidi» possono smettere di valere. Descrittivo, non una previsione e non una consulenza finanziaria. Aggiornato al " + d["data"] + ".</p>")
