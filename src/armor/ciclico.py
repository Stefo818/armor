"""Rischio ciclico (6-12 mesi), mesi del passato più simili a oggi, modelli in ombra e sezione «Ricerca modello» (PIANO_MODELLO, Fase C).

Ogni giorno `aggiorna()`:
- legge lo stato dei segnali classici (soglie fisse di ricerca.SEGNALI) con i valori NOTI oggi (ritardi di pubblicazione inclusi);
- calcola i mesi più simili a oggi (k vicini, storia lunga) e cosa è successo dopo;
- per i modelli promossi in ombra (data/ricerca/promossi.json) scrive la previsione di oggi in data/ombra_ciclica.csv (non entra nei numeri dell'app);
- salva tutto in data/ciclico_oggi.json, che le pagine leggono.
Le frequenze storiche «acceso/spento» vengono dalla ricerca (data/ricerca/fase_b.json, esiti chiusi entro il 2018)."""
import html as _h
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import ricerca, store
from .config import DATA

FILE = DATA / "ciclico_oggi.json"
OMBRA = DATA / "ombra_ciclica.csv"
R = ricerca.OUT


def _j(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def aggiorna(load=store.load) -> dict:
    X, Y, sp = ricerca.dataset_completo(load, con_oggi=True)
    oggi = X.index[-1]
    ops = {"<": np.less, ">": np.greater, ">=": np.greater_equal}
    stati = []
    for nome, (col, op, thr) in ricerca.SEGNALI.items():
        v = X[col].iloc[-1] if col in X else np.nan
        stati.append({"segnale": nome, "colonna": col, "valore": None if pd.isna(v) else round(float(v), 2),
                      "acceso": None if pd.isna(v) else bool(ops[op](v, thr))})
    n_on = sum(1 for s in stati if s["acceso"])
    hist = X["n_segnali"].dropna()
    hist = hist[hist.index >= "1990-01-01"]
    pct = float((hist < n_on).mean() * 100 + (hist == n_on).mean() * 50) if len(hist) else None
    an = ricerca.analoghi(X, Y, ricerca.colonne_disponibili(X, ricerca.LUNGO, "1955-12-31"))
    # modelli promossi in ombra: previsione di oggi addestrata su tutti gli esiti già noti
    prom = _j(R / "promossi.json").get("promossi", [])
    ombra = []
    C = ricerca.candidati(X)
    for pm in prom:
        try:
            spec = next(m for m in C[pm["periodo_tipo"]]["modelli"] if m[0] == pm["modello"])
            y = Y[f"{pm['ob']}_{pm['h']}"]
            p = ricerca.modello(spec[1], X, y, pm["h"], pm["ob"], (oggi.year, oggi.year), spec[2], load=load, extra=spec[3], oggi=True)
            if p is not None:
                base = float(y[(X.index + pd.DateOffset(months=pm["h"])) < oggi].mean())
                ombra.append({"modello": pm["modello"], "ob": pm["ob"], "h": pm["h"], "p": round(p, 4), "base": round(base, 4)})
        except Exception as e:  # noqa: BLE001
            print("[ciclico] ombra non calcolata per", pm.get("modello"), str(e)[:80], flush=True)
    d = {"date": oggi.strftime("%Y-%m-%d"), "segnali": stati, "accesi": n_on, "totale": sum(1 for s in stati if s["acceso"] is not None),
         "percentile_accesi": None if pct is None else round(pct), "analoghi": an, "ombra": ombra}
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=0, default=str), encoding="utf-8")
    if ombra:
        df = pd.DataFrame([{"date": d["date"], **o} for o in ombra])
        old = pd.read_csv(OMBRA) if OMBRA.exists() else pd.DataFrame()
        df = pd.concat([old, df]).drop_duplicates(["date", "modello", "ob", "h"], keep="last") if len(old) else df
        df.to_csv(OMBRA, index=False)
    print(f"[ciclico] segnali accesi {n_on}/{d['totale']}; modelli in ombra: {len(ombra)}", flush=True)
    return d


def load() -> dict:
    return _j(FILE)


# ---------------------------------------------------------------- riquadri per la pagina Oggi
def _f(x, dec=1):
    return "n.d." if x is None else f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def box_rischio(d: dict | None = None) -> str:
    d = d or load()
    if not d.get("segnali"):
        return ""
    fb = _j(R / "fase_b.json")
    freq = {s["segnale"]: s for s in fb.get("segnali_dal_1990", []) if "p_calo10_6m_acceso" in s}
    ad = _j(R / "adottati.json").get("adottati", [])
    e = _h.escape
    righe = []
    for s in d["segnali"]:
        if s["acceso"] is None:
            continue
        fq = freq.get(s["segnale"])
        st = "<span class='badge bad'>acceso</span>" if s["acceso"] else "<span class='badge ok'>spento</span>"
        stat = (f"calo ≥10% entro 6 mesi: <b>{_f(fq['p_calo10_6m_acceso'], 0)}%</b> se acceso, {_f(fq['p_calo10_6m_spento'], 0)}% se spento · "
                f"S&amp;P a 12 mesi {_f(fq['ret12_acceso'])}% / {_f(fq['ret12_spento'])}%") if fq else "frequenze storiche non ancora calcolate"
        righe.append(f"<div class='cyr{' on' if s['acceso'] else ''}'><div class='cyh'>{st}<b>{e(s['segnale'])}</b><span class='mu'>oggi {_f(s['valore'], 2)}</span></div>"
                     f"<div class='mu cys'>{stat}</div></div>")
    n, tot, pc = d.get("accesi", 0), d.get("totale", 0), d.get("percentile_accesi")
    liv = "basso" if (pc or 0) < 40 else ("medio" if (pc or 0) < 75 else "alto")
    mod = ""
    if ad:
        a = ad[0]
        mod = f"<p>Modello adottato ({e(a['modello'])}): vedi la sezione Ricerca modello in «Quanto fidarsi».</p>"
    else:
        mod = ("<p class='mu'>Nessun modello a 6-12 mesi ha superato la prova finale sugli anni 2019-2026, quindi qui non c'è una percentuale: "
               "solo i segnali e cosa è successo in passato quando erano accesi (1990-2018). Dettagli in «Quanto fidarsi» → Ricerca modello.</p>")
    return (f"<div class='card cybox'><h3 style='margin-top:0'>Rischio ciclico 6-12 mesi: i segnali classici</h3>"
            f"<p><b>{n} segnali accesi su {tot}</b> · livello <b>{liv}</b> rispetto alla storia dal 1990"
            f"{f' ({pc}° percentile)' if pc is not None else ''}. Dati aggiornati al {e(pd.Timestamp(d['date']).strftime('%d/%m/%Y')) if d.get('date') else ''}, ognuno con il suo ritardo di pubblicazione.</p>"
            f"<details><summary>Vedi i {tot} segnali e le frequenze storiche</summary>{''.join(righe)}</details>{mod}</div>")


def box_simili(d: dict | None = None) -> str:
    d = d or load()
    a = d.get("analoghi") or {}
    if not a.get("mesi"):
        return ""
    fb = _j(R / "fase_b.json")
    valid = bool(fb.get("analoghi_validati"))
    k = a["k"]
    warn = ("<span class='badge ok'>verificato</span>" if valid else
            "<span class='badge warn'>descrittivo, non è una previsione</span>")
    nota = ("" if valid else "<p class='mu'>Nella verifica storica (1960-2018 e 2000-2018) il metodo dei mesi simili non ha battuto il riferimento: "
            "è un modo di vedere cosa è successo in situazioni somiglianti, non una stima affidabile.</p>")
    mesi = "".join(f"<span class='cym'>{_h.escape(m['mese'])}: <b class='{'azup' if m['ret_12'] > 0 else 'azdn'}'>{_f(m['ret_12'], 0)}%</b></span>" for m in a["mesi"])
    return (f"<div class='card cybox'><h3 style='margin-top:0'>I {k} mesi del passato più simili a oggi {warn}</h3>"
            f"<p>Dopo 12 mesi l'S&amp;P 500 era salito in <b>{a['rialzo_12_su_k']} casi su {k}</b> (mediana {_f(a['mediana_12'])}%, "
            f"8 casi su 10 tra {_f(a['p10_12'], 0)}% e {_f(a['p90_12'], 0)}%); lungo la strada c'è stato un calo di almeno il 10% in "
            f"<b>{a['calo10_12_su_k']} casi su {k}</b>.</p>{nota}"
            f"<details><summary>Quali mesi e come è andata dopo 12 mesi</summary><div class='cyml'>{mesi}</div>"
            f"<p class='mu'>Somiglianza calcolata su utili, valutazioni, credito, curva dei tassi, inflazione, produzione, disoccupazione e tendenza dei prezzi.</p></details></div>")


# ---------------------------------------------------------------- sezione «Ricerca modello» (Quanto fidarsi)
BADGE_OMBRA = "<span class='badge ok'>promosso in ombra</span>"
NOMI_OB = {("calo10", 3): "calo ≥10% entro 3 mesi", ("calo10", 6): "calo ≥10% entro 6 mesi", ("calo10", 12): "calo ≥10% entro 12 mesi",
           ("calo20", 12): "calo ≥20% entro 12 mesi"}


def html_ricerca() -> str:
    fb, pf = _j(R / "fase_b.json"), _j(R / "prova_finale.json")
    if not fb:
        return "<p class='mu'>La ricerca non è ancora stata eseguita (workflow «Ricerca modello Armor»).</p>"
    e = _h.escape
    f3 = lambda x: "n.d." if x is None else f"{x:.2f}".replace(".", ",")
    pct = lambda x: "n.d." if x is None else f"{x * 100:.0f}"
    righe = ""
    for per in ("lungo", "recente"):
        for ob, h in ricerca.PRIMARI:
            rs = [x for x in fb["risultati"] if x.get("periodo_tipo") == per and x.get("ob") == ob and x.get("h") == h and x["modello"] != "_riferimenti"]
            rf = next((x for x in fb["risultati"] if x.get("periodo_tipo") == per and x.get("ob") == ob and x.get("h") == h and x["modello"] == "_riferimenti"), None)
            if not rs or not rf:
                continue
            best = max((x for x in rs if x.get("auc") is not None), key=lambda x: x["auc"], default=None)
            ref_name = best["riferimento"] if best else None
            ref = rf["rif"].get(ref_name, {}) if ref_name else {}
            prom = [x["modello"] for x in rs if x.get("promosso")]
            righe += (f"<div class='rmr'><div class='rmh'><b>{NOMI_OB[(ob, h)]}</b><span class='mu'>{'1960-2018' if per == 'lungo' else '2000-2018'}</span>"
                      + (BADGE_OMBRA if prom else "") + "</div>"
                      f"<div class='rmg'><div><span>Migliore</span>{e(best['modello']) if best else '—'}: <b>{pct(best.get('auc')) if best else 'n.d.'}</b> su 100</div>"
                      f"<div><span>Riferimento</span>{e(ref_name or '—')}: <b>{pct(ref.get('auc'))}</b> su 100</div></div>"
                      + (f"<div class='mu rmn'>Promossi: {e(', '.join(prom))}</div>" if prom else "") + "</div>")
    fin = ""
    if pf:
        rr = ""
        for es in pf.get("esiti", []):
            rif = es.get("riferimenti", {})
            ia, a1 = rif.get("Indice Armor", {}), rif.get("A1", {})
            mods = es.get("modelli", [])
            mtxt = "; ".join(f"{e(m['modello'])}: {pct(m.get('auc'))} su 100 (Indice sugli stessi mesi {pct(m.get('auc_indice_stessi_mesi'))}) "
                             f"→ <b>{'adottato' if m['adottato'] else 'non adottato'}</b>" for m in mods) or "nessun modello promosso"
            rr += (f"<div class='rmr'><div class='rmh'><b>{NOMI_OB[(es['ob'], es['h'])]}</b></div>"
                   f"<div class='rmg'><div><span>Indice Armor</span><b>{pct(ia.get('auc'))}</b> su 100</div><div><span>A1</span>{('<b>' + pct(a1.get('auc')) + '</b> su 100') if a1 else '—'}</div></div>"
                   f"<div class='rmn'>{mtxt}</div></div>")
        ado = pf.get("adottati", [])
        verdict = ("<p><b>Esito:</b> " + (f"{len(ado)} modello/i adottato/i nei numeri dell'app." if ado else
                   "nessun modello nuovo ha battuto l'Indice Armor sugli anni 2019-2026: i numeri principali dell'app restano quelli di prima. "
                   "I modelli promossi continuano in ombra (data/ombra_ciclica.csv) per raccogliere prove dal vivo.") + "</p>")
        fin = (f"<h4>Prova finale, una sola volta, sugli anni {e(pf.get('anni', ''))} (mai usati prima)</h4>"
               f"{rr}"
               f"<p class='mu'>Numeri «su 100»: su 100 confronti tra un mese prima di un calo e un mese tranquillo, quante volte il modello indica come più "
               f"rischioso quello giusto (50 = caso). Anni 2019-2026: {e(str(pf['esiti'][0]['riferimenti'].get('Indice Armor', {}).get('n', '')))} mesi, pochi eventi "
               f"(2020, 2022, 2025): i numeri ballano molto.</p>{verdict}")
    dir_ = fb.get("direzione_prevedibile") or []
    dir_txt = ("Nessun modello ha previsto la direzione (salita/discesa) meglio della frequenza storica: resta imprevedibile." if not dir_ else
               "Direzione con abilità minima: " + ", ".join(f"{e(x['modello'])} a {x['h']} mesi (BSS {f3(x['bss'])})" for x in dir_) + " (troppo poco per mostrarla).")
    ep = fb.get("episodi") or {}
    ept = ""
    if ep.get("episodi"):
        ept = "".join(f"<tr><td>{x['massimo']}</td><td>{x['calo']:.0f}%".replace(".", ",") + f"</td><td>{x['mesi_in_allarme_prima']} su {x['mesi_valutati']}</td></tr>"
                      for x in ep["episodi"])
        ept = (f"<h4>Grandi cali (≥20%) 1960-2018: mesi di allarme nei 12 mesi prima del massimo ({e(ep.get('modello', ''))}, calo ≥10% entro 12 mesi)</h4>"
               f"<div class='scroll'><table class='fq'><tr><th>Massimo</th><th>Calo</th><th>Mesi in allarme</th></tr>{ept}</table></div>"
               f"<p class='mu'>Mesi in allarme in tutto: {ep.get('mesi_in_allarme')}, di cui falsi allarmi (nessun calo ≥10% nei 12 mesi dopo): {ep.get('falsi_allarmi')}.</p>")
    return (f"<p>Dopo aver aggiunto i dati sulla salute delle aziende, l'inflazione, la liquidità, il mercato interno e la storia lunga dal 1919, "
            f"sono state provate <b>{fb.get('prove_totali_registro', 'n.d.')} combinazioni</b> in tutto (segnali e famiglie; 7 tipi di modello × 8 obiettivi × 2 periodi; "
            f"riferimenti e prova finale), tutte nel registro data/ricerca/registro_prove.csv. "
            f"Regole decise prima: verifica solo sul futuro, ritardi di pubblicazione, anni 2019-2026 tenuti da parte.</p>"
            f"<h4>Ricerca 1960-2018 e 2000-2018: il migliore per obiettivo</h4>"
            f"{righe}"
            f"<p class='mu'>Promosso = batte il riferimento di almeno 0,02 in 2 sottoperiodi su 3, senza peggiorare in nessuno, e ha probabilità meglio tarate della frequenza storica.</p>"
            f"{fin}<p><b>Direzione:</b> {dir_txt}</p>{ept}")


CSS = """
.cybox details{margin-top:6px}.cybox summary{font-weight:700;color:var(--ac);cursor:pointer;font-size:13.5px}
.cyr{border-top:1px solid var(--bd);padding:7px 0}.cyh{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.cyh b{flex:1 1 60%;font-size:13.5px;color:var(--tx)}
.cys{font-size:12.5px;margin-top:2px}.cyml{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.cym{border:1px solid var(--bd);border-radius:8px;padding:2px 7px;font-size:12.5px;color:var(--tx)}
.rmr{border-top:1px solid var(--bd);padding:8px 0}.rmh{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.rmh b{flex:1 1 auto;color:var(--tx)}
.rmh .mu{font-size:12.5px}.rmg{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:13.5px;margin-top:4px}
.rmg span{display:block;font-size:11.5px;color:var(--mu);font-weight:600}.rmn{font-size:13px;margin-top:4px}
"""
