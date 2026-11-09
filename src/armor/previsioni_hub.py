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


def modelli(pred: dict | None) -> str:
    righe = []
    o = _leggi_json("percorsi_oggi.json") or {}
    c = _leggi_json("campioni.json") or {}
    basi = o.get("basi", {})
    for nome_v, res in (o.get("varianti") or {}).items():
        adottata = o.get("adottate") or {}
        for hz, lab in HZ:
            x = res.get(hz) if isinstance(res, dict) else None
            if not x:
                continue
            b = basi.get(hz, {})
            cl, txt = direzione(1 - x["p_neg"], None if b.get("p_neg") is None else 1 - b["p_neg"])
            stato = "in uso" if nome_v == o.get("mostrata") and hz in adottata else ("mostrata" if nome_v == o.get("mostrata") else "in ombra")
            righe.append((lab, nome_sim(nome_v), stato, 1 - x["p_neg"], x["ret"]["q50"], cl, txt))
    for hz, lab in (("10g", "10 giorni"), ("1m", "1 mese"), ("3m", "3 mesi"), ("6m", "6 mesi")):
        if pred and hz in pred and pred[hz].get("ret"):
            r = pred[hz]
            q50 = r["ret"].get("q50")
            lvl = r.get("level", "")
            cl = {"Basso": "ok", "Moderato": "wa", "Alto": "ba", "Molto alto": "ba"}.get(lvl, "wa")
            righe.append((lab, "Modello principale (A1)", "in uso", None, q50, cl, f"Rischio di calo: {lvl.lower()} rispetto al normale"))
    try:
        sh = pd.read_csv(DATA / "journal_shadow.csv")
        ult = sh[sh["asof"] == sh["asof"].max()]
        for x in ult.itertuples():
            q50 = None if pd.isna(x.q50) else float(x.q50)
            lvl = str(x.level)
            cl = {"Basso": "ok", "Moderato": "wa", "Alto": "ba", "Molto alto": "ba"}.get(lvl, "wa")
            righe.append((HZ_NOME.get(x.horizon, x.horizon), f"{x.model}", "in ombra", None, q50, cl, f"Rischio di calo: {lvl.lower()}"))
    except Exception:  # noqa: BLE001
        pass
    ordine = {l: i for i, (_k, l) in enumerate([("10g", "10 giorni")] + HZ)}
    righe.sort(key=lambda r: (ordine.get(r[0], 9), r[2] != "in uso", r[1]))
    tr = "".join(f"<tr><td>{E(a)}</td><td><b>{E(b)}</b></td><td><span class='pvst {s.replace(' ', '')}'>{s}</span></td>"
                 f"<td>{'—' if pu is None else _pc(pu)}</td><td>{_sg(q50) if q50 is not None else 'n/d'}</td><td><span class='pvch {cl}'>{E(t)}</span></td></tr>" for a, b, s, pu, q50, cl, t in righe)
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
    if not righe:
        return "<p class='mu'>Nessun modello disponibile.</p>" + ciclici + reg
    return ("<div class='scroll'><table class='t pvt'><tr><th>Periodo</th><th>Modello</th><th>Stato</th><th>Rialzo</th><th>Caso tipico</th><th>Lettura</th></tr>" + tr + "</table></div>"
            "<p class='mu'><b>Come leggere:</b> «in uso» = il modello che decide i numeri principali dell'app. «In ombra» = un modello concorrente che scrive la sua previsione ogni giorno ma non conta finché non dimostra di essere più bravo. «Rialzo» = probabilità di chiudere sopra il prezzo di oggi. «Caso tipico» = variazione più probabile.</p>" + mot + ciclici + reg)


# ---------------------------------------------------------------- storico previsto contro reale
def storico_dati() -> list[list]:
    """[data, orizzonte, q10, q50, q90, reale, origine] in percentuale; origine 'p' = test sul passato, 'v' = diario firmato dal vivo."""
    righe: list[list] = []
    try:
        b = pd.read_csv(BACKTEST_RET)
        for x in b.itertuples():
            if pd.notna(x.realized):
                righe.append([x.asof, x.horizon, round(x.q10 * 100, 2), round(x.q50 * 100, 2), round(x.q90 * 100, 2), round(x.realized * 100, 2), "p"])
    except Exception:  # noqa: BLE001
        pass
    try:
        j = pd.read_csv(JOURNAL)
        o = pd.read_csv(OUTCOMES)
        j = j[j["model"] == j["model"].iloc[0]][["asof", "horizon", "q10", "q50", "q90"]].drop_duplicates(["asof", "horizon"])
        m = o.merge(j, on=["asof", "horizon"], how="inner", suffixes=("", "_j"))
        for x in m.itertuples():
            if pd.notna(x.realized) and pd.notna(x.q10) and pd.notna(x.q90):
                righe.append([x.asof, x.horizon, round(x.q10 * 100, 2), round(x.q50_j * 100 if hasattr(x, "q50_j") and pd.notna(x.q50_j) else x.q50 * 100, 2), round(x.q90 * 100, 2), round(x.realized * 100, 2), "v"])
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

.pvw2{border:1px solid var(--bd);border-radius:16px;overflow:hidden;background:var(--card)}.pvlh,.pvlr{display:grid;grid-template-columns:1.05fr 1.25fr 1fr;gap:8px;align-items:center;padding:8px 12px;font-variant-numeric:tabular-nums}
.pvlh{font-size:11px;font-weight:800;color:var(--mu);background:var(--bg);text-transform:uppercase;letter-spacing:.4px}.pvlr{border-top:1px solid var(--bd);font-size:13.5px}.pvlr small{display:block;font-size:11px;color:var(--mu);font-weight:600}
.pvlr .s{font-weight:800;border-radius:10px;text-align:center;color:#111;padding:6px 4px}.pvlr .s small{color:#222;font-weight:700}
</style>"""

JS = r"""<script>(function(){var W=document.querySelector('[data-pvh]');if(!W||W.dataset.on)return;W.dataset.on=1;var D=JSON.parse(document.getElementById('armor-pv-data').textContent),HZ='',OR='',SOLO=false,N=120;
function col(s){var h=Math.round(120*Math.max(0,Math.min(1,s)));return 'hsl('+h+',70%,'+(h>70?'52%':'58%')+')'}
function sc(r){var w=Math.max((r[4]-r[2]),1e-6);return 1-Math.min(1,Math.abs(r[5]-r[3])/w)}
function ex(s,r){var dentro=r[5]>=r[2]&&r[5]<=r[4],opp=Math.sign(r[5])!==Math.sign(r[3])&&!dentro;return opp?'Opposto':(s>=.75?'Indovinata':(dentro?'Nella fascia':'Fuori fascia'))}
function nf(x,d){return (x>0?'+':'')+x.toFixed(d==null?1:d).replace('.',',').replace('-','−')+'%'}
function dm(s){var a=s.split('-');return a[2]+'/'+a[1]+'/'+a[0]}
var NOM={'10g':'10 giorni','1m':'1 mese','3m':'3 mesi','6m':'6 mesi'};
function rows(){return D.r.filter(function(r){return (!HZ||r[1]===HZ)&&(!OR||r[6]===OR)&&(!SOLO||ex(sc(r),r)==='Opposto'||ex(sc(r),r)==='Fuori fascia')})}
function render(){var R=rows(),h='';
h+='<div class="pvf">'+['','10g','1m','3m','6m'].map(function(k){return '<button data-h="'+k+'" class="'+(HZ===k?'on':'')+'">'+(k?NOM[k]:'Tutti i periodi')+'</button>'}).join('')+'</div>';
h+='<div class="pvf">'+[['','Storico e dal vivo'],['v','Solo dal vivo (diario firmato)'],['p','Solo test sul passato']].map(function(k){return '<button data-o="'+k[0]+'" class="'+(OR===k[0]?'on':'')+'">'+k[1]+'</button>'}).join('')+'<button data-x="1" class="'+(SOLO?'on':'')+'">Solo errori grandi</button></div>';
var ST=R.slice(0,160).reverse();h+='<div class="pvlg">Ultime '+ST.length+' previsioni, dalla più vecchia alla più recente: <i style="background:'+col(0)+'"></i> opposto <i style="background:'+col(.5)+'"></i> al bordo della fascia <i style="background:'+col(1)+'"></i> indovinata</div><div class="pvs">'+ST.map(function(r){return '<i title="'+dm(r[0])+' · '+NOM[r[1]]+': previsto '+nf(r[3])+', reale '+nf(r[5])+'" style="background:'+col(sc(r))+'"></i>'}).join('')+'</div>';
h+='<div class="pvw2"><div class="pvlh"><span>Data e periodo</span><span>Previsto → reale</span><span>Esito</span></div>';
R.slice(0,N).forEach(function(r){var s=sc(r),e=ex(s,r);h+='<div class="pvlr"><div><b>'+dm(r[0])+'</b>'+(r[6]==='v'?' <b title="diario firmato">●</b>':'')+'<small>'+NOM[r[1]]+'</small></div><div>'+nf(r[3])+' → <b>'+nf(r[5])+'</b><small>fascia '+nf(r[2],0)+' / '+nf(r[4],0)+'</small></div><div class="s" style="background:'+col(s)+'">'+e+'<small>'+nf(r[5]-r[3])+'</small></div></div>'});
h+='</div>';if(R.length>N)h+='<div class="pvf"><button data-more="1">Mostra altre '+Math.min(200,R.length-N)+' (su '+R.length+')</button></div>';if(!R.length)h+='<p class="mu">Nessuna previsione con questi filtri.</p>';
W.innerHTML=h;W.querySelectorAll('[data-h]').forEach(function(b){b.onclick=function(){HZ=b.dataset.h;N=120;render()}});W.querySelectorAll('[data-o]').forEach(function(b){b.onclick=function(){OR=b.dataset.o;N=120;render()}});
var x=W.querySelector('[data-x]');if(x)x.onclick=function(){SOLO=!SOLO;N=120;render()};var m=W.querySelector('[data-more]');if(m)m.onclick=function(){N+=200;render()}}
render()})();</script>"""


def storico_html(righe: list[list]) -> str:
    if not righe:
        return "<p class='mu'>Storico previsioni non disponibile: servono i test sul passato (convalida mensile) e il diario.</p>"
    rs = riepilogo(righe)
    k = "".join(f"<div><span>{HZ_NOME[x['hz']]} · {x['n']} previsioni</span><b>{_pc(x['dentro'])}</b><span>dentro la fascia prevista (dovrebbe essere circa 80%)</span><span style='display:block;margin-top:4px'>Mercato salito il {_pc(x['sale'])} delle volte · "
                f"la direzione prevista è stata giusta il {_pc(x['segno'])} · sbaglio medio {str(round(x['abs'] * 100, 1)).replace('.', ',')} punti percentuali</span></div>" for x in rs)
    dati = json.dumps({"r": righe}, separators=(",", ":"))
    return (f"<div class='pvk'>{k}</div><div class='explain'><p><b>Come leggere i colori.</b> Per ogni riga vedi cosa era stato previsto, cosa è successo davvero e di quanto ci si è sbagliati. Verde = il risultato è stato vicino alla previsione; giallo = al limite di quanto previsto come possibile; rosso = lontano, spesso nel verso opposto. "
            "Il caso tipico previsto è quasi sempre in rialzo (il mercato in media sale), quindi «aver indovinato la direzione» vale poco da solo. La domanda utile è: la fascia indicata era onesta? Cioè il risultato è finito dentro la fascia circa 8 volte su 10? "
            "● = previsione registrata dal vivo con firma (non modificabile); le altre sono prove sul passato, fatte usando a ogni data solo ciò che si sapeva allora.</p></div>"
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


def html(pred: dict | None = None) -> str:
    righe = storico_dati()
    return (CSS + "<div class='pvw'><h2>Previsioni: cosa dicono i modelli</h2><div class='explain'><p><b>In breve.</b> Per ogni periodo, la probabilità di chiudere in rialzo, la fascia dei rendimenti possibili e il confronto con quello che succede normalmente. "
            "Sotto trovi tutti i modelli affiancati e la tabella completa delle previsioni passate contro il risultato reale. Sono probabilità, non promesse.</p></div>"
            + carte() + "<h3>Tutti i modelli, in uso e in ombra</h3>" + modelli(pred) + "<h3>Previsioni passate e risultato reale</h3>" + storico_html(righe) + "</div>")
