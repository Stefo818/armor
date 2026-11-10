"""Pagina «Previsioni» (Patch 57): tutte le previsioni in un posto solo, con grafica immediata.
1) Direzione per orizzonte (1 settimana … 1 anno) dal motore di simulazione, con fascia di incertezza e confronto con la norma storica;
2) tutti i modelli (in uso e in ombra) affiancati;
3) tabella lunga delle previsioni passate contro il risultato reale, colorata da rosso (opposto) a verde (indovinata), con lo scostamento.
Descrittivo e probabilistico: non è una promessa né una consulenza finanziaria."""
import html as _h
import json

import numpy as np
import pandas as pd

from .config import BACKTEST_RET, DATA, JOURNAL, OUTCOMES

HZ = [("1s", "1 settimana"), ("1m", "1 mese"), ("3m", "3 mesi"), ("6m", "6 mesi"), ("12m", "1 anno")]
HZ_NOME = dict(HZ) | {"10g": "10 giorni"}
SOGLIA_DIR = 0.05      # punti di probabilità di rialzo sopra/sotto la norma storica per parlare di inclinazione
E = _h.escape


def _pc(x, d=0):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%".replace(".", ",").replace("-", "−")


def _sg(x, d=1):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%".replace(".", ",").replace("-", "−")


def direzione(p_up: float, base_up: float | None) -> tuple[str, str]:
    """(classe, testo): confronto della probabilità di rialzo con la norma storica dello stesso orizzonte."""
    if p_up < 0.5:
        return "ba", "Più probabile un calo che un rialzo"
    if base_up is None:
        return "wa", "Rialzo probabile, senza norma di confronto"
    d = p_up - base_up
    if d >= SOGLIA_DIR:
        return "ok", "Più favorevole del solito: spinta verso l'alto"
    if d <= -SOGLIA_DIR:
        return "ba", "Meno favorevole del solito: spinta verso il basso"
    return "wa", "Come al solito: nessuna spinta netta, né in su né in giù"


def nome_sim(v: str) -> str:
    """Nome comprensibile delle varianti di simulazione (V0/V1/V2 = come si stima la nervosità di partenza)."""
    if "HAR" in str(v):
        return f"Simulazione con previsione di volatilità HAR ({v})"
    base = {"V0": "Simulazione base", "V1": "Simulazione che tiene conto dell'indice della paura (VIX)", "V2": "Simulazione che confronta paura a breve e a lungo termine"}.get(str(v)[:2], f"Simulazione {v}")
    return f"{base} ({v})"


def _leggi_json(nome):
    try:
        return json.loads((DATA / nome).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def ventaglio(r: dict) -> str:
    """Barra SVG: fascia 5-95, fascia 25-75, mediana e zero (il tratto verticale)."""
    m = max(abs(r["q5"]), abs(r["q95"]), 1e-4) * 1.08
    X = lambda v: 50 + v / m * 50
    return ("<svg viewBox='0 0 100 26' preserveAspectRatio='none' class='pvfan' role='img' aria-label='Fascia dei rendimenti possibili'>"
            f"<rect x='{X(r['q5']):.1f}' y='8' width='{X(r['q95']) - X(r['q5']):.1f}' height='10' rx='5' fill='var(--mu)' opacity='.25'/>"
            f"<rect x='{X(r['q25']):.1f}' y='6' width='{X(r['q75']) - X(r['q25']):.1f}' height='14' rx='6' fill='var(--ac)' opacity='.45'/>"
            f"<line x1='50' x2='50' y1='1' y2='25' stroke='var(--tx)' stroke-width='.6' stroke-dasharray='1.5 1.5'/>"
            f"<line x1='{X(r['q50']):.1f}' x2='{X(r['q50']):.1f}' y1='3' y2='23' stroke='var(--tx)' stroke-width='2.2' vector-effect='non-scaling-stroke'/></svg>")


def carte() -> str:
    o = _leggi_json("percorsi_oggi.json")
    if not o:
        return "<p class='mu'>Previsioni non ancora disponibili (serve il lavoro giornaliero).</p>"
    res = (o.get("varianti") or {}).get(o.get("mostrata"))
    if not res:
        return "<p class='mu'>Previsioni non ancora disponibili.</p>"
    basi = o.get("basi", {})
    out = []
    for hz, nome in HZ:
        x = res.get(hz)
        if not x:
            continue
        b = basi.get(hz, {})
        p_up = 1 - x["p_neg"]
        base_up = None if b.get("p_neg") is None else 1 - b["p_neg"]
        cl, txt = direzione(p_up, base_up)
        d10 = x["down"].get("10", x["down"].get(10)) if isinstance(x["down"], dict) else None
        r = x["ret"]
        out.append(f"<div class='pvc {cl}'><div class='pvh'>{nome}</div><div class='pvbig'>{_pc(p_up)}<small> di chiudere in rialzo</small></div>"
                   f"<div class='pvd'>{E(txt)}</div>{ventaglio(r)}<div class='pvr'><span>{_sg(r['q10'])}<i>caso brutto</i></span><span><b>{_sg(r['q50'])}</b><i>tipico</i></span><span>{_sg(r['q90'])}<i>caso buono</i></span></div>"
                   f"<div class='pvm'>Di solito, in passato, il mercato saliva il {_pc(base_up)} delle volte · probabilità di perdere almeno il 10% da oggi: <b>{_pc(d10, 1)}</b></div></div>")
    asof = o.get("asof", "")
    return f"<div class='pvg'>{''.join(out)}</div><p class='mu'><b>Come leggere le schede:</b> il numero grande è la probabilità che il mercato, alla fine del periodo, valga più di oggi. «Di solito» è quante volte è successo in passato in generale. Il colore dice se oggi è meglio (verde), uguale (giallo) o peggio (rosso) del solito. La barra mostra dove può finire il mercato: la parte grigia copre 9 casi su 10, quella blu 5 casi su 10, il tratto nero pieno è il caso più probabile, il tratteggiato è lo zero (nessuna variazione). Simulazione del {E(asof)}. Sono probabilità, non promesse.</p>"


LIV = {"Basso": ("ok", "Rischio basso"), "Normale": ("wa", "Rischio nella norma"), "Moderato": ("wa", "Rischio moderato"), "Elevato": ("or", "Rischio elevato"), "Alto": ("ba", "Rischio alto")}
COLONNE = [("10g", "10 giorni"), ("1s", "1 settimana"), ("1m", "1 mese"), ("3m", "3 mesi"), ("6m", "6 mesi"), ("12m", "1 anno")]


def _modelli_celle(pred: dict | None) -> dict:
    """{nome: {stato, tipo, celle: {orizzonte: (classe, testo, sottotesto)}}}: ogni modello con la sua indicazione per ogni periodo, tradotta in un colore comune."""
    out: dict = {}
    o = _leggi_json("percorsi_oggi.json") or {}
    basi = o.get("basi", {})
    for nome_v, res in (o.get("varianti") or {}).items():
        celle = {}
        for hz, _l in COLONNE:
            x = res.get(hz) if isinstance(res, dict) else None
            if not x:
                continue
            b = basi.get(hz, {})
            pu = 1 - x["p_neg"]
            cl, _t = direzione(pu, None if b.get("p_neg") is None else 1 - b["p_neg"])
            celle[hz] = (cl, f"Rialzo {_pc(pu)}", f"tipico {_sg(x['ret']['q50'])}")
        out[nome_sim(nome_v)] = {"stato": "mostrato" if nome_v == o.get("mostrata") else "in ombra", "tipo": "sim", "celle": celle}
    if pred:
        celle = {}
        for hz in ("10g", "1m", "3m", "6m"):
            if hz in pred:
                cl, t = LIV.get(pred[hz].get("level", ""), ("wa", "Rischio nella norma"))
                q50 = (pred[hz].get("ret") or {}).get("q50")
                celle[hz] = (cl, t, f"tipico {_sg(q50)}" if q50 is not None else "")
        out["Modello principale (A1)"] = {"stato": "in uso", "tipo": "risk", "celle": celle}
    try:
        sh = pd.read_csv(DATA / "journal_shadow.csv")
        ult = sh[sh["asof"] == sh["asof"].max()]
        for x in ult.itertuples():
            m = out.setdefault(str(x.model), {"stato": "in ombra", "tipo": "risk", "celle": {}})
            cl, t = LIV.get(str(x.level), ("wa", "Rischio nella norma"))
            q50 = None if pd.isna(x.q50) else float(x.q50)
            m["celle"][x.horizon] = (cl, t, f"tipico {_sg(q50)}" if q50 is not None else "")
    except Exception:  # noqa: BLE001
        pass
    return out


def matrice(pred: dict | None) -> str:
    M = _modelli_celle(pred)
    if not M:
        return "<p class='mu'>Nessun modello disponibile.</p>"
    ordine = sorted(M, key=lambda n: ({"in uso": 0, "mostrato": 1}.get(M[n]["stato"], 2), n))
    chips = "<button data-pm='' class='on'>Tutti i modelli</button>" + "".join(f"<button data-pm='{i}'>{E(n.split(' (')[0] if len(n) > 30 else n)}</button>" for i, n in enumerate(ordine))
    testa = "<div class='pmh'>Modello</div>" + "".join(f"<div class='pmh c'>{l}</div>" for _k, l in COLONNE)
    righe = ""
    for i, n in enumerate(ordine):
        m = M[n]
        celle = ""
        for hz, _l in COLONNE:
            c = m["celle"].get(hz)
            celle += (f"<div class='pmc {c[0]}'><b>{E(c[1])}</b><small>{E(c[2])}</small></div>" if c else "<div class='pmc nd'>—</div>")
        stato = {"in uso": "<span class='pvst inuso'>in uso</span>", "mostrato": "<span class='pvst inuso'>mostrato</span>"}.get(m["stato"], "<span class='pvst'>in ombra</span>")
        righe += f"<div class='pmn' data-m='{i}'>{E(n)}<br>{stato}</div>" + celle.replace("<div class='pmc", f"<div data-m='{i}' class='pmc", 99)
    # riga di sintesi: quanti modelli per colore, per periodo
    sint = "<div class='pmn pms'><b>Sintesi</b><br><span class='mu'>quanti modelli per colore</span></div>"
    for hz, _l in COLONNE:
        cs = [M[n]["celle"][hz][0] for n in ordine if hz in M[n]["celle"]]
        if not cs:
            sint += "<div class='pmc nd'>—</div>"
            continue
        tot = len(cs)
        seg = "".join(f"<i class='{k}' style='flex:{cs.count(k)}'></i>" for k in ("ok", "wa", "or", "ba") if cs.count(k))
        neg = cs.count("or") + cs.count("ba")
        verdetto = "Quasi tutti favorevoli" if cs.count("ok") >= tot * .6 else ("Prevale la cautela" if neg > tot / 2 else "Segnali misti")
        sint += f"<div class='pmc pmsum'><div class='pmbar'>{seg}</div><small>{verdetto} ({tot})</small></div>"
    js = ("<script>(function(){var W=document.querySelector('[data-pmw]');if(!W||W.dataset.on)return;W.dataset.on=1;W.querySelectorAll('[data-pm]').forEach(function(b){b.onclick=function(){var v=b.dataset.pm;W.querySelectorAll('[data-pm]').forEach(function(x){x.classList.toggle('on',x===b)});"
          "W.querySelectorAll('[data-m]').forEach(function(e){e.style.display=(v===''||e.dataset.m===v)?'':'none'});var dt=document.querySelector('[data-pmt]');if(dt)dt.querySelectorAll('tr[data-m]').forEach(function(r){r.style.display=(v===''||r.dataset.m===v)?'':'none'})}})})();</script>")
    leg = ("<div class='pmleg'><span class='pmc ok'>favorevole / rischio basso</span><span class='pmc wa'>nella norma</span><span class='pmc or'>cautela / rischio elevato</span><span class='pmc ba'>sfavorevole / rischio alto</span></div>")
    return (f"<div data-pmw='1'><div class='pvf'>{chips}</div>{leg}<div class='scroll'><div class='pmg'>{testa}{righe}{sint}</div></div>{js}</div>"
            "<p class='mu'><b>Come leggere:</b> ogni riga è un modello, ogni colonna un periodo. Il colore è uguale per tutti: verde = clima favorevole, rosso = clima sfavorevole. Il testo è l'indicazione propria del modello: "
            "alcuni dicono «probabilità di rialzo», altri «rischio di calo». «Tipico» è la variazione più probabile. «In uso» decide i numeri principali; «in ombra» = modello concorrente che non conta finché non dimostra di essere più bravo. Un'indicazione sola non basta: guarda se i modelli concordano (riga «Sintesi»).</p>")


def modelli(pred: dict | None) -> str:
    righe = []
    o = _leggi_json("percorsi_oggi.json") or {}
    c = _leggi_json("campioni.json") or {}
    M = _modelli_celle(pred)
    ordine = sorted(M, key=lambda n: ({"in uso": 0, "mostrato": 1}.get(M[n]["stato"], 2), n))
    tr = ""
    for i, n in enumerate(ordine):
        for hz, lab in COLONNE:
            cc = M[n]["celle"].get(hz)
            if cc:
                tr += f"<tr data-m='{i}'><td>{lab}</td><td><b>{E(n)}</b></td><td>{M[n]['stato']}</td><td><span class='pvch {cc[0]}'>{E(cc[1])}</span></td><td>{E(cc[2].replace('tipico ', ''))}</td></tr>"
    ciclici = ""
    try:
        oc = pd.read_csv(DATA / "ombra_ciclica.csv")
        oc = oc[oc["date"] == oc["date"].max()]
        trc = ""
        for x in oc.itertuples():
            if pd.isna(x.p):
                continue
            r = x.p / x.base if x.base else 1
            cl = "ba" if r >= 1.3 else "wa" if r >= 1.0 else "ok"
            trc += (f"<tr><td>{E(str(x.modello))}</td><td>calo ≥10% entro {int(x.h)} mesi</td><td><b>{_pc(x.p)}</b></td><td>{_pc(x.base)}</td>"
                    f"<td><span class='pvch {cl}'>{str(round(r, 1)).replace('.', ',')}× la norma</span></td></tr>")
        if trc:
            ciclici = ("<h3>Modelli sui cicli economici (in ombra)</h3><div class='scroll'><table class='t'><tr><th>Modello</th><th>Cosa stima</th><th>Oggi</th><th>Norma</th><th>Lettura</th></tr>" + trc + "</table></div>")
    except Exception:  # noqa: BLE001
        pass
    reg = ""
    try:
        rg = pd.read_csv(DATA / "regime_ombra.csv").iloc[-1]
        reg = f"<p class='mu'>Livello di tensione del mercato (in ombra): stato «{E(str(rg['stato']))}», indice {float(rg['indice']):.0f}, minimo a 20 giorni {float(rg['min20']):.0f}.</p>"
    except Exception:  # noqa: BLE001
        pass
    mot = ""
    if c.get("orizzonti"):
        mot = "<p class='mu'>Modello scelto per ogni periodo con una regola fissa: " + " · ".join(f"{HZ_NOME.get(h, h)}: <b>{E(str(v.get('motore')))}</b>" for h, v in c["orizzonti"].items()) + ".</p>"
    tab = ("<details class='pvdet2'><summary>Tabella dettagliata di tutti i modelli</summary><div class='scroll'><table class='t pvt' data-pmt='1'><tr><th>Periodo</th><th>Modello</th><th>Stato</th><th>Indicazione</th><th>Caso tipico</th></tr>" + tr + "</table></div></details>") if tr else ""
    return matrice(pred) + tab + mot + ciclici + reg


# ---------------------------------------------------------------- storico previsto contro reale
STRUMENTI = [("sp", "S&P 500", None), ("vw", "VWCE (il tuo fondo)", None), ("rsp", "S&P 500 a pesi uguali", "rsp"), ("mweq", "Mondo a pesi uguali", "mweq"), ("nasdaq100", "Nasdaq 100", "nasdaq100"),
             ("urth", "Mondo (MSCI World)", "urth"), ("stoxx600", "Europa (STOXX 600)", "stoxx600"), ("dax", "Germania (DAX)", "dax"), ("ftsemib", "Italia (FTSE MIB)", "ftsemib"),
             ("nikkei", "Giappone (Nikkei)", "nikkei"), ("iwm", "Piccole aziende USA", "iwm"), ("eem", "Paesi emergenti", "eem")]


def _serie_strumento(k: str):
    if k == "vw":
        from .features import vwce_series
        return vwce_series().dropna()
    from . import store
    d = dict((a, c) for a, _l, c in STRUMENTI).get(k)
    if not d:
        return None
    x = store.load(d)
    return None if x is None or len(x) == 0 else x[x > 0].dropna()


def storico_dati(asset: str = "sp") -> list[list]:
    """[data, orizzonte, q10, q50, q90, reale, origine] in percentuale; origine 'p' = test sul passato, 'v' = diario firmato dal vivo."""
    righe: list[list] = []
    vw = None
    if asset != "sp":
        try:
            from .features import closed_sp500
            from .config import HORIZONS
            vw, spx = _serie_strumento(asset), closed_sp500()
            if vw is None or len(vw) < 300:
                return []
        except Exception:  # noqa: BLE001
            return []
    try:
        b = pd.read_csv(BACKTEST_RET)
        for x in b.itertuples():
            if pd.notna(x.realized):
                real = x.realized
                if vw is not None:
                    a = pd.Timestamp(x.asof)
                    if a not in spx.index or a < vw.index[0]:
                        continue
                    i = spx.index.get_loc(a)
                    n = HORIZONS.get(x.horizon)
                    if n is None or i + n >= len(spx):
                        continue
                    v0 = vw.reindex([a, spx.index[i + n]], method="ffill")
                    if v0.isna().any():
                        continue
                    real = float(v0.iloc[1] / v0.iloc[0] - 1)
                righe.append([x.asof, x.horizon, round(x.q10 * 100, 2), round(x.q50 * 100, 2), round(x.q90 * 100, 2), round(real * 100, 2), "p"])
    except Exception:  # noqa: BLE001
        pass
    try:
        j = pd.read_csv(JOURNAL)
        o = pd.read_csv(OUTCOMES)
        j = j[j["model"] == j["model"].iloc[0]][["asof", "horizon", "q10", "q50", "q90"]].drop_duplicates(["asof", "horizon"])
        m = o.merge(j, on=["asof", "horizon"], how="inner", suffixes=("", "_j"))
        for x in m.itertuples():
            if pd.notna(x.realized) and pd.notna(x.q10) and pd.notna(x.q90):
                righe.append([x.asof, x.horizon, round(x.q10 * 100, 2), round(x.q50_j * 100 if hasattr(x, "q50_j") and pd.notna(x.q50_j) else x.q50 * 100, 2), round(x.q90 * 100, 2), round((x.sp_realized if asset == "sp" and hasattr(x, "sp_realized") and pd.notna(x.sp_realized) else x.realized) * 100, 2), "v"])
    except Exception:  # noqa: BLE001
        pass
    righe.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return righe


def punteggio(q10, q50, q90, real) -> float:
    """0 = risultato lontanissimo dalla previsione, 1 = identico al caso tipico; 0,5 = al bordo della fascia 10-90."""
    return float(1 - min(1.0, abs(real - q50) / max((q90 - q10) / 2 * 2, 1e-6)))


def riepilogo(righe: list[list]) -> list[dict]:
    out = []
    for hz in ("10g", "1m", "3m", "6m"):
        rr = [r for r in righe if r[1] == hz]
        if len(rr) < 20:
            continue
        a = np.array([[r[2], r[3], r[4], r[5]] for r in rr], float)
        dentro = ((a[:, 3] >= a[:, 0]) & (a[:, 3] <= a[:, 2])).mean()
        segno = (np.sign(a[:, 3]) == np.sign(a[:, 1])).mean()
        sale = (a[:, 3] > 0).mean()
        out.append({"hz": hz, "n": len(rr), "dentro": float(dentro), "segno": float(segno), "sale": float(sale), "disc": float(np.mean(a[:, 3] - a[:, 1])), "abs": float(np.mean(np.abs(a[:, 3] - a[:, 1])))})
    return out


CSS = """<style>
.pvw h2{margin:6px 0 4px}.pvw h3{margin:20px 0 6px}
.pvg{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:10px 0}
.pvc{border:1px solid var(--bd);border-left:6px solid var(--mu);border-radius:18px;padding:14px 14px 12px;background:var(--card);box-shadow:0 2px 10px rgba(0,0,0,.12)}
.pvc.ok{border-left-color:var(--ok);background:linear-gradient(160deg,var(--okbg),var(--card) 60%)}.pvc.ba{border-left-color:var(--bad);background:linear-gradient(160deg,var(--badbg),var(--card) 60%)}.pvc.wa{border-left-color:var(--warn);background:linear-gradient(160deg,var(--warnbg),var(--card) 60%)}
.pvh{font-weight:800;font-size:15px;letter-spacing:.2px}.pvbig{font-size:32px;font-weight:900;line-height:1.1;margin:4px 0}.pvbig small{display:block;font-size:12px;font-weight:600;color:var(--mu)}
.pvd{font-size:13px;font-weight:700;margin:2px 0 6px}.pvc.ok .pvd{color:var(--ok)}.pvc.ba .pvd{color:var(--bad)}.pvc.wa .pvd{color:var(--warn)}
.pvfan{width:100%;height:30px;display:block}.pvr{display:flex;justify-content:space-between;font-size:12px;font-variant-numeric:tabular-nums;margin-top:2px}.pvr span{text-align:center}.pvr i{display:block;font-style:normal;font-size:10px;color:var(--mu)}
.pvm{font-size:11.5px;color:var(--mu);margin-top:8px;border-top:1px dashed var(--bd);padding-top:6px}
.pvt td,.pvt th{font-size:12.5px}.pvst{padding:2px 9px;border-radius:99px;font-size:11px;font-weight:800;background:var(--bg);color:var(--mu);border:1px solid var(--bd)}.pvst.inuso{background:var(--ac);color:#fff;border-color:var(--ac)}
.pvch{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11.5px;font-weight:700}.pvch.ok{background:var(--okbg);color:var(--ok)}.pvch.ba{background:var(--badbg);color:var(--bad)}.pvch.wa{background:var(--warnbg);color:var(--warn)}
.pvk{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}.pvk div{border:1px solid var(--bd);border-radius:14px;padding:10px 12px;background:var(--card)}.pvk b{display:block;font-size:20px}.pvk span{font-size:11.5px;color:var(--mu)}
.pvf{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.pvf select,.pvf button{padding:8px 12px;border-radius:99px;border:1px solid var(--bd);background:var(--card);color:var(--tx);font:inherit;font-size:13px}.pvf button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.pvs{display:flex;flex-wrap:wrap;gap:2px;margin:6px 0 10px}.pvs i{width:9px;height:18px;border-radius:3px;display:block}
.pvl{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}.pvl th{position:sticky;top:0;background:var(--card);text-align:left;padding:7px 6px;border-bottom:2px solid var(--bd);font-size:11.5px}.pvl td{padding:6px;border-bottom:1px solid var(--bd)}
.pvdet>summary{cursor:pointer;font-weight:800;padding:10px 0;font-size:15px;border-top:1px solid var(--bd);margin-top:20px}.pvl td.s{font-weight:800;border-radius:8px;text-align:center;color:#111;white-space:nowrap}.pvlg{display:flex;gap:4px;align-items:center;font-size:11.5px;color:var(--mu);flex-wrap:wrap}.pvlg i{width:28px;height:10px;border-radius:3px;display:inline-block}

.pvw2{border:1px solid var(--bd);border-radius:18px;overflow:hidden;background:var(--card)}.pvlr{padding:11px 14px 10px;border-top:1px solid var(--bd);font-variant-numeric:tabular-nums}.pvlr:first-child{border-top:0}
.pvt1{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13.5px}.pvt1 .s{font-weight:800;border-radius:99px;color:#111;padding:4px 12px;font-size:12.5px;white-space:nowrap}.pvt1 .s small{font-weight:700;opacity:.8}
.pvb{position:relative;height:26px;margin:8px 0 4px}.pvb .z{position:absolute;left:50%;top:0;bottom:0;border-left:1px dashed var(--mu);opacity:.7}.pvb .band{position:absolute;top:8px;height:10px;border-radius:99px;background:var(--mu);opacity:.28}.pvb .tip{position:absolute;top:4px;height:18px;border-left:3px solid var(--tx);transform:translateX(-50%)}
.pvb .dot{position:absolute;top:3px;width:20px;height:20px;border-radius:50%;transform:translateX(-50%);box-shadow:0 0 0 3px var(--card),0 2px 6px rgba(0,0,0,.45)}.pvt2{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:12.5px}.pvt2 i{font-style:normal;color:var(--mu);font-size:11.5px}
.pvpg{display:grid;gap:10px;margin:8px 0 14px}.pvpr{border:1px solid var(--bd);border-radius:14px;padding:10px 12px;background:var(--card)}.pvpn{display:flex;justify-content:space-between;font-size:13.5px}.pvsb{display:flex;height:16px;border-radius:99px;overflow:hidden;margin:6px 0}.pvsb i{display:block;min-width:0}.pvpl{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11.5px;color:var(--mu)}

.pmg{display:grid;grid-template-columns:minmax(150px,1.5fr) repeat(6,minmax(84px,1fr));gap:5px;min-width:700px;align-items:stretch}.pmh{font-size:11px;font-weight:800;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;padding:4px 2px}.pmh.c{text-align:center}
.cls{display:flex;flex-direction:column;gap:6px;margin:8px 0}.clr{display:flex;gap:10px;align-items:center;background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:8px 10px}.clp{font-weight:800;font-size:15px;min-width:24px;text-align:center;color:var(--mu)}.clm{flex:1;display:flex;flex-direction:column;gap:3px;font-size:13px}.clm small{font-size:11px;color:var(--mu)}.clch{display:flex;gap:4px;flex-wrap:wrap}.clc{font-size:10.5px;font-weight:700;background:var(--bg);border-radius:8px;padding:1px 6px}.clv{border-radius:12px;padding:6px 10px;text-align:center;min-width:54px;border:1px solid transparent}.clv b{font-size:20px;display:block}.clv small{font-size:10px}.clv.ok{background:var(--okbg);color:var(--ok);border-color:var(--ok)}.clv.wa{background:var(--warnbg);color:var(--warn);border-color:var(--warn)}.clv.ba{background:var(--badbg);color:var(--bad);border-color:var(--bad)}
.pmn{font-size:12.5px;font-weight:700;padding:8px 6px;border-radius:12px;background:var(--card);border:1px solid var(--bd);display:flex;flex-direction:column;justify-content:center;gap:3px}.pmn.pms{background:var(--bg)}
.pmc{border-radius:12px;padding:8px 4px;text-align:center;font-size:12px;display:flex;flex-direction:column;justify-content:center;gap:2px;border:1px solid transparent}.pmc small{font-size:10.5px;opacity:.85;font-weight:600}
.pmc.ok{background:var(--okbg);color:var(--ok);border-color:var(--ok)}.pmc.wa{background:var(--warnbg);color:var(--warn);border-color:var(--warn)}.pmc.or{background:rgba(249,115,22,.16);color:#f97316;border-color:#f97316}.pmc.ba{background:var(--badbg);color:var(--bad);border-color:var(--bad)}.pmc.nd{color:var(--mu);background:transparent}
.pmleg{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px}.pmleg .pmc{padding:4px 10px;border-radius:99px;font-size:11.5px;font-weight:700;display:inline-block}
.pmsum{background:var(--card);border:1px solid var(--bd)}.pmbar{display:flex;height:14px;border-radius:99px;overflow:hidden;margin:2px 4px}.pmbar i{display:block}.pmbar i.ok{background:var(--ok)}.pmbar i.wa{background:var(--warn)}.pmbar i.or{background:#f97316}.pmbar i.ba{background:var(--bad)}
.pvdet2>summary{cursor:pointer;font-weight:700;padding:10px 0}
</style>"""

JS = r"""<script>(function(){var W=document.querySelector('[data-pvh]');if(!W||W.dataset.on)return;W.dataset.on=1;var D=JSON.parse(document.getElementById('armor-pv-data').textContent),HZ='',OR='',SOLO=false,N=120,AS='sp',DS=function(){return D.a[AS].r};
function col(s){var h=Math.round(120*Math.max(0,Math.min(1,s)));return 'hsl('+h+',70%,'+(h>70?'52%':'58%')+')'}
function sc(r){var w=Math.max((r[4]-r[2]),1e-6);return 1-Math.min(1,Math.abs(r[5]-r[3])/w)}
function ex(s,r){var dentro=r[5]>=r[2]&&r[5]<=r[4],opp=Math.sign(r[5])!==Math.sign(r[3])&&!dentro;return opp?'Opposto':(s>=.75?'Indovinata':(dentro?'Nella fascia':'Fuori fascia'))}
function nf(x,d){return (x>0?'+':'')+x.toFixed(d==null?1:d).replace('.',',').replace('-','−')+'%'}
function dm(s){var a=s.split('-');return a[2]+'/'+a[1]+'/'+a[0]}
var NOM={'10g':'10 giorni','1m':'1 mese','3m':'3 mesi','6m':'6 mesi'};
function bar(r,s){var M=Math.max(Math.abs(r[2]),Math.abs(r[4]),Math.abs(r[5]),.5)*1.12,X=function(v){return (50+v/M*50).toFixed(1)};
return '<div class="pvb"><i class="z"></i><i class="band" style="left:'+X(r[2])+'%;width:'+(X(r[4])-X(r[2])).toFixed(1)+'%"></i><i class="tip" style="left:'+X(r[3])+'%"></i><b class="dot" style="left:'+X(r[5])+'%;background:'+col(s)+'"></b></div>'}
function pagella(R){var h='<div class="pvpg">';['10g','1m','3m','6m'].forEach(function(k){var x=R.filter(function(r){return r[1]===k});if(x.length<5)return;var c={Indovinata:0,'Nella fascia':0,'Fuori fascia':0,Opposto:0};x.forEach(function(r){c[ex(sc(r),r)]++});var n=x.length,P=function(v){return Math.round(v/n*100)};
h+='<div class="pvpr"><div class="pvpn"><b>'+NOM[k]+'</b><span class="mu">'+n+' previsioni</span></div><div class="pvsb"><i style="flex:'+c.Indovinata+';background:'+col(1)+'" title="Indovinata"></i><i style="flex:'+c['Nella fascia']+';background:'+col(.7)+'" title="Nella fascia"></i><i style="flex:'+c['Fuori fascia']+';background:'+col(.35)+'" title="Fuori fascia"></i><i style="flex:'+c.Opposto+';background:'+col(0)+'" title="Opposto"></i></div><div class="pvpl"><span>'+P(c.Indovinata)+'% indovinate</span><span>'+P(c['Nella fascia'])+'% nella fascia</span><span>'+P(c['Fuori fascia'])+'% fuori</span><span>'+P(c.Opposto)+'% opposte</span></div></div>'});
return h+'</div>'}
function rows(){return DS().filter(function(r){return (!HZ||r[1]===HZ)&&(!OR||r[6]===OR)&&(!SOLO||ex(sc(r),r)==='Opposto'||ex(sc(r),r)==='Fuori fascia')})}
function render(){var R=rows(),h='<div class="pvlg" style="margin:4px 0"><b>Su quale mercato guardare le previsioni?</b></div><div class="pvf">'+Object.keys(D.a).map(function(k){return '<button data-a="'+k+'" class="'+(AS===k?'on':'')+'">'+D.a[k].l+'</button>'}).join('')+'</div><div class="pvk">'+D.a[AS].k+'</div><div class="pvlg" style="margin:4px 0">Quante previsioni sono andate bene (su tutte quelle del periodo scelto sotto):</div>'+pagella(DS().filter(function(r){return !OR||r[6]===OR}));
h+='<div class="pvf">'+['','10g','1m','3m','6m'].map(function(k){return '<button data-h="'+k+'" class="'+(HZ===k?'on':'')+'">'+(k?NOM[k]:'Tutti i periodi')+'</button>'}).join('')+'</div>';
h+='<div class="pvf">'+[['','Storico e dal vivo'],['v','Solo dal vivo (diario firmato)'],['p','Solo test sul passato']].map(function(k){return '<button data-o="'+k[0]+'" class="'+(OR===k[0]?'on':'')+'">'+k[1]+'</button>'}).join('')+'<button data-x="1" class="'+(SOLO?'on':'')+'">Solo errori grandi</button></div>';
var ST=R.slice(0,160).reverse();h+='<div class="pvlg">Ultime '+ST.length+' previsioni, dalla più vecchia alla più recente: <i style="background:'+col(0)+'"></i> opposto <i style="background:'+col(.5)+'"></i> al bordo della fascia <i style="background:'+col(1)+'"></i> indovinata</div><div class="pvs">'+ST.map(function(r){return '<i title="'+dm(r[0])+' · '+NOM[r[1]]+': previsto '+nf(r[3])+', reale '+nf(r[5])+'" style="background:'+col(sc(r))+'"></i>'}).join('')+'</div>';
h+='<div class="pvw2">';
R.slice(0,N).forEach(function(r){var s=sc(r),e=ex(s,r);h+='<div class="pvlr"><div class="pvt1"><div><b>'+dm(r[0])+'</b>'+(r[6]==='v'?' <b title="previsione registrata dal vivo">●</b>':'')+' <span class="mu">· '+NOM[r[1]]+'</span></div><div class="s" style="background:'+col(s)+'">'+e+' <small>'+(r[5]-r[3]>0?'+':'')+(r[5]-r[3]).toFixed(1).replace('.',',').replace('-','−')+' punti</small></div></div>'+bar(r,s)+'<div class="pvt2"><span>Previsto: <b>'+nf(r[3])+'</b> <i>(possibile da '+nf(r[2],0)+' a '+nf(r[4],0)+')</i></span><span>È successo: <b>'+nf(r[5])+'</b></span></div></div>'});
h+='</div>';if(R.length>N)h+='<div class="pvf"><button data-more="1">Mostra altre '+Math.min(200,R.length-N)+' (su '+R.length+')</button></div>';if(!R.length)h+='<p class="mu">Nessuna previsione con questi filtri.</p>';
W.innerHTML=h;W.querySelectorAll('[data-a]').forEach(function(b){b.onclick=function(){AS=b.dataset.a;N=120;render()}});W.querySelectorAll('[data-h]').forEach(function(b){b.onclick=function(){HZ=b.dataset.h;N=120;render()}});W.querySelectorAll('[data-o]').forEach(function(b){b.onclick=function(){OR=b.dataset.o;N=120;render()}});
var x=W.querySelector('[data-x]');if(x)x.onclick=function(){SOLO=!SOLO;N=120;render()};var m=W.querySelector('[data-more]');if(m)m.onclick=function(){N+=200;render()}}
render()})();</script>"""


def _kpi(righe: list[list]) -> str:
    return "".join(f"<div><span>{HZ_NOME[x['hz']]} · {x['n']} previsioni</span><b>{_pc(x['dentro'])}</b><span>dentro la fascia prevista (dovrebbe essere circa 80%)</span><span style='display:block;margin-top:4px'>Mercato salito il {_pc(x['sale'])} delle volte · "
                   f"la direzione prevista è stata giusta il {_pc(x['segno'])} · sbaglio medio {str(round(x['abs'], 1)).replace('.', ',')} punti percentuali</span></div>" for x in riepilogo(righe))


def storico_html(righe: list[list]) -> str:
    if not righe:
        return "<p class='mu'>Storico previsioni non disponibile: servono i test sul passato (convalida mensile) e il diario.</p>"
    A = {}
    for k, lab, _c in STRUMENTI:
        try:
            rr = righe if k == "sp" else storico_dati(k)
        except Exception:  # noqa: BLE001
            rr = []
        if len(rr) >= 40:
            A[k] = {"l": lab, "r": rr, "k": _kpi(rr)}
    dati = json.dumps({"a": A}, separators=(",", ":"))
    return ("<div class='explain'><p><b>Come leggere ogni riga.</b> La barra grigia è l'intervallo in cui il mercato poteva finire secondo la previsione (il tratto nero è il caso più probabile, il tratteggiato è lo zero). Il pallino colorato è dove il mercato è finito davvero. Verde = il risultato è stato vicino alla previsione; giallo = al limite di quanto previsto come possibile; rosso = lontano, spesso nel verso opposto. "
            "Il caso tipico previsto è quasi sempre in rialzo (il mercato in media sale), quindi «aver indovinato la direzione» vale poco da solo. La domanda utile è: la fascia indicata era onesta? Cioè il risultato è finito dentro la fascia circa 8 volte su 10? "
            "● = previsione registrata dal vivo con firma (non modificabile); le altre sono prove sul passato, fatte usando a ogni data solo ciò che si sapeva allora.</p>"
            "<p><b>Quale indice?</b> I modelli sono costruiti sull'S&amp;P 500. Con i pulsanti in alto puoi vedere come la <i>stessa previsione</i> si comporta su altri mercati: il VWCE (il fondo che compri, in euro), l'S&amp;P 500 a pesi uguali (ogni azienda conta uguale, non per grandezza), il Nasdaq, l'Europa, ecc. Il «reale» viene ricalcolato sul prezzo di ciascuno. "
            "Dove la storia è più corta (per esempio il VWCE parte dal 2008, il pesi uguali dal 2003) trovi meno previsioni. Gli indici esteri sono nella loro valuta. Più un mercato è diverso dall'S&amp;P 500, meno la previsione è precisa: è normale.</p></div>"
            f"<script type='application/json' id='armor-pv-data'>{dati}</script><div data-pvh='1'></div>{JS}")


def recenti(n: int = 16) -> str:
    """Ultime previsioni con esito, colorate: per la pagina Calendario."""
    righe = [r for r in storico_dati() if r[1] in ("10g", "1m")][: n * 2]
    if not righe:
        return "<p class='mu'>Nessuna previsione verificata disponibile.</p>"
    def col(r):
        s = punteggio(r[2], r[3], r[4], r[5])
        return f"hsl({round(120 * max(0, min(1, s)))},70%,{'52%' if s > .58 else '58%'})"
    tr = "".join(f"<tr><td>{r[0][8:]}/{r[0][5:7]}/{r[0][:4]}</td><td>{HZ_NOME.get(r[1], r[1])}</td><td>{_sg(r[3] / 100)}</td><td><b>{_sg(r[5] / 100)}</b></td>"
                 f"<td style='background:{col(r)};color:#111;font-weight:800;border-radius:8px;text-align:center'>{_sg((r[5] - r[3]) / 100)}</td></tr>" for r in righe[:n])
    return ("<div class='scroll'><table class='t'><tr><th>Data</th><th>Periodo</th><th>Previsto (tipico)</th><th>Reale</th><th>Scostamento</th></tr>" + tr + "</table></div>"
            "<p class='mu'>Colore dello scostamento: verde = vicino al previsto, rosso = lontano.</p>")


def _classifica() -> str:
    try:
        from . import classifica
        return classifica.html()
    except Exception as ex:  # noqa: BLE001
        return "<p class='mu'>Classifica non disponibile: " + _h.escape(str(ex)[:80]) + "</p>"


def _semaforo() -> str:
    try:
        from . import semaforo_rischio
        return semaforo_rischio.html()
    except Exception as ex:  # noqa: BLE001
        return "<p class='mu'>Semaforo non disponibile: " + _h.escape(str(ex)[:80]) + "</p>"


def html(pred: dict | None = None) -> str:
    righe = storico_dati()
    return (CSS + "<div class='pvw'><h2>Previsioni: cosa dicono i modelli</h2><div class='explain'><p><b>In breve.</b> Per ogni periodo, la probabilità di chiudere in rialzo, la fascia dei rendimenti possibili e il confronto con quello che succede normalmente. "
            "Sotto trovi tutti i modelli affiancati e la tabella completa delle previsioni passate contro il risultato reale. Sono probabilità, non promesse.</p></div>"
            + carte() + "<h3>Semaforo del rischio di calo</h3>" + _semaforo() + "<h3>Classifica dei modelli (voto da 1 a 100, aggiornata ogni giorno)</h3>" + _classifica() + "<h3>Tutti i modelli, in uso e in ombra</h3>" + modelli(pred) + "<h3>Previsioni passate e risultato reale</h3>" + storico_html(righe) + "</div>")
