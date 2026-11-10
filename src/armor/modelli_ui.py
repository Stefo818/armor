"""Pagina «Modelli» (Patch 81): tutti i modelli di previsione, chi è il riferimento, chi vince per orizzonte e per periodo, come è calcolato ognuno.
Dati: model_eval.json (valutazione mensile), modelli_finestre.json (vincitori per periodo), classifica (voto cumulativo). La pagina non cambia nessun modello:
il riferimento (FHS+VIX) cambia solo con la regola annuale di PROTOCOLLO_MODELLI.md."""
import html as _h
import json

from .config import DATA, PRIMARY

RIFERIMENTO = "FHS+VIX"
HZ = ("10g", "1m", "3m", "6m")
HZ_NOME = {"10g": "Una settimana", "1m": "Un mese", "3m": "Tre mesi", "6m": "Sei mesi"}
HZ_SEDUTE = {"10g": "7 sedute", "1m": "21 sedute", "3m": "63 sedute", "6m": "126 sedute"}
COL = {"Normale": "#94a3b8", "A1": "#f59e0b", "FHS": "#0ea5e9", "FHS+VIX": "#6366f1", "MV-logit": "#14b8a6", "MV-GBM": "#ec4899", "MVF-logit": "#84cc16", "MVF-GBM": "#a855f7", "Combinato": "#ef4444", "Combinato-B": "#64748b", "Pari": "#cbd5e1"}
NOMI = {"Normale": "Normale (frequenza storica)", "A1": "A1 · solo prezzi", "FHS": "FHS · simulazione della nervosità", "FHS+VIX": "FHS+VIX · simulazione + indice della paura",
        "MV-logit": "Multi-variabile (regressione)", "MV-GBM": "Multi-variabile (alberi)", "MVF-logit": "Multi-variabile + famiglie (regressione)", "MVF-GBM": "Multi-variabile + famiglie (alberi)", "Combinato": "Combinato (miscela)", "Combinato-B": "Combinato senza correzione"}
BREVI = {"Normale": "Normale", "A1": "A1", "FHS": "FHS", "FHS+VIX": "FHS+VIX", "MV-logit": "MV regress.", "MV-GBM": "MV alberi", "MVF-logit": "MVF regress.", "MVF-GBM": "MVF alberi", "Combinato": "Combinato", "Combinato-B": "Combinato B"}


def etichetta(r: dict | None) -> tuple[str, str]:
    """Affidabilità dell'orizzonte per il modello di riferimento: (parola, colore). Regola fissa:
    Buona = margine di incertezza tutto sopra zero e dal 2013 almeno +0,03; Modesta = sopra zero ma poco o solo in parte; Non dimostrata = il margine include lo zero."""
    if not r:
        return "n.d.", "#94a3b8"
    lo, rec = r.get("lo"), r.get("b3")
    if lo is None or rec is None or lo != lo or rec != rec:
        return "n.d.", "#94a3b8"
    if lo > 0 and rec >= 0.03:
        return "Buona", "#16a34a"
    if lo > 0 and rec > 0:
        return "Modesta", "#d97706"
    return "Non dimostrata", "#dc2626"


def _ok(x):
    return x is not None and x == x


def dati(ev: dict | None, fin: dict | None) -> dict:
    """Dati per la pagina: per orizzonte, righe (una per modello) sul bersaglio principale + taratura + vincitori per periodo."""
    out: dict = {}
    if not ev:
        return out
    mets = ev.get("metrics", [])
    cal = ev.get("calibration", [])
    for hz in HZ:
        thr = PRIMARY[hz]
        righe, altre = [], []
        for x in mets:
            if x["hz"] != hz or x["kind"] != "down" or x["thr"] != thr:
                continue
            r = {"m": x["model"], "set": x["set"], "n": x["n"], "da": x["da"], "bss": x["bss"], "lo": x["bss_lo"] if _ok(x.get("bss_lo")) else None, "hi": x["bss_hi"] if _ok(x.get("bss_hi")) else None,
                 "auc": x["auc"], "b1": x.get("bss_1990_2012"), "b2": x.get("bss_2000_12"), "b3": x.get("bss_2013_26"), "freq": x["freq"]}
            r = {k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
            (righe if x["set"] == "modelli" else altre).append(r)
        have = {r["m"] for r in righe}
        for r in altre:
            if r["m"] not in have and r["m"] != "Normale":
                r["altro"] = True
                righe.append(r)
                have.add(r["m"])
        c = {}
        for x in cal:
            if x["hz"] == hz and x["kind"] == "down" and x["thr"] == thr and x["set"] == "modelli":
                c.setdefault(x["model"], []).append([round(x["prev"], 4), round(x["real"], 4), x["n"]])
        o = {"nome": HZ_NOME[hz], "thr": thr, "sedute": HZ_SEDUTE[hz], "righe": righe, "cal": c}
        ref = next((r for r in righe if r["m"] == RIFERIMENTO), None)
        o["et"] = etichetta(ref)
        if fin and hz in fin.get("orizzonti", {}):
            f = fin["orizzonti"][hz]
            o["fin"] = {"periodi": f["periodi"], "anni": f["anni"], "anni_n": f.get("anni_n", {}), "tot": f["tot"], "da": f["da"], "n": f["n_date"]}
        out[hz] = o
    return out


def _podio(d: dict) -> str:
    E = _h.escape
    celle = ""
    for hz in HZ:
        o = d.get(hz)
        if not o:
            continue
        ranked = sorted([r for r in o["righe"] if not r.get("altro") and r["m"] != "Normale"], key=lambda r: -(r["bss"] or -9))
        et, ecol = o["et"]
        medaglie = ["🥇", "🥈", "🥉"]
        righe = ""
        mx = max([abs(r["bss"] or 0) for r in ranked] + [0.05])
        for i, r in enumerate(ranked[:4]):
            w = max(2, abs(r["bss"] or 0) / mx * 100)
            neg = (r["bss"] or 0) < 0
            ref = " md-ref" if r["m"] == RIFERIMENTO else ""
            righe += (f"<div class='md-pr{ref}'><span class='md-med'>{medaglie[i] if i < 3 else str(i + 1)}</span><span class='md-pn'>{E(BREVI.get(r['m'], r['m']))}</span>"
                      f"<div class='md-pb'><i style='width:{w:.0f}%;background:{'#dc2626' if neg else COL.get(r['m'], '#64748b')}'></i></div><b>{(r['bss'] or 0) * 100:+.1f}%</b></div>".replace(".", ","))
        celle += (f"<div class='md-pod'><div class='md-ph'><b>{o['nome']}</b><small>{o['sedute']} · calo ≥{o['thr']}%</small></div>{righe}"
                  f"<div class='md-et' style='border-color:{ecol};color:{ecol}'>Affidabilità: <b>{et}</b></div></div>")
    return f"<div class='md-podi'>{celle}</div>"


def _heat(d: dict) -> str:
    modelli = ["A1", "FHS", "FHS+VIX", "MV-logit", "MV-GBM"]
    head = "".join(f"<div class='md-hh'>{HZ_NOME[h]}</div>" for h in HZ)
    out = f"<div class='md-heat' role='table' aria-label='Abilità dei modelli per orizzonte'><div></div>{head}"
    for m in modelli:
        out += f"<div class='md-hm'><i style='background:{COL[m]}'></i>{_h.escape(BREVI[m])}</div>"
        for h in HZ:
            r = next((x for x in d.get(h, {}).get("righe", []) if x["m"] == m), None)
            if not r or r["bss"] is None:
                out += "<div class='md-hc'>–</div>"
                continue
            b = r["bss"]
            a = min(abs(b) / 0.10, 1)
            bg = f"rgba(22,163,74,{.12 + a * .6:.2f})" if b >= 0 else f"rgba(220,38,38,{.12 + a * .6:.2f})"
            sig = "" if (r["lo"] is not None and r["lo"] > 0) else "<sup title='Margine di incertezza compreso lo zero: non dimostrato'>*</sup>"
            out += f"<div class='md-hc' style='background:{bg}' title='{_h.escape(NOMI[m])} · {HZ_NOME[h]}: {b * 100:+.1f}%'>{b * 100:+.1f}%{sig}</div>".replace(".", ",")
    return out + "</div><p class='md-nota'>* = il margine di incertezza comprende lo zero: la bravura non è dimostrata. Verde = sbaglia meno della frequenza storica, rosso = di più.</p>"


SCHEDE = [
    ("Normale", "La frequenza storica", "Dice: «in passato, in situazioni qualsiasi, il calo è successo X volte su 100».",
     "Conta quante volte, nella storia già conclusa, l'S&P 500 è sceso del 5% o del 10% entro l'orizzonte scelto. Non guarda la situazione di oggi.",
     "Serve da metro: ogni altro modello vale solo se sbaglia meno di lui. Non è un modello da battere facilmente, perché è onesto e non ha il problema di adattarsi al caso."),
    ("A1", "Il modello base sui prezzi", "Guarda solo come si è mosso il prezzo.",
     "Otto misure ricavate dai prezzi (nervosità a 1 e 3 mesi, distanza dal massimo, medie mobili, slancio, peggior giorno) alimentano una regressione logistica, riaddestrata ogni 63 sedute sui dati dal 1928, senza mai usare esiti futuri.",
     "Semplice e stabile. Non vede la paura del mercato in tempo reale e dal 2013 a 3 e 6 mesi è peggiorato: lo teniamo come seconda opinione."),
    ("FHS", "Simulazione della nervosità", "Simula 5000 possibili futuri e conta in quanti il mercato scende troppo.",
     "Un modello della volatilità (GJR-GARCH con code spesse) stima quanto sarà nervoso il mercato e ne simula i percorsi giorno per giorno fino a 126 sedute. La probabilità è la quota di percorsi in calo.",
     "Reagisce subito quando il mercato si agita; usa solo prezzi."),
    ("FHS+VIX", "Simulazione + indice della paura (riferimento)", "Come la FHS, ma ancorata a ciò che le opzioni prezzano oggi (il VIX).",
     "Stessa simulazione, ma la nervosità iniziale è corretta con il VIX, tenendo conto che il VIX in media sovrastima il rischio vero (fattore 0,8). Il VIX aiuta soprattutto nei momenti di stress.",
     "È il riferimento per tutti gli orizzonti perché ha l'errore totale più basso o pari al più basso. Attenzione: è quasi gemello della FHS, il vantaggio è piccolo."),
    ("MV-logit", "Multi-variabile con regressione", "Mette insieme prezzi, macro e credito.",
     "Alle misure sui prezzi aggiunge indicatori economici e di credito, con una regressione.", "Nel test peggiora rispetto alla frequenza storica: più ingredienti non hanno migliorato la previsione."),
    ("MV-GBM", "Multi-variabile con alberi", "Come sopra, ma con alberi decisionali (più flessibile).", "Gli alberi cercano combinazioni non lineari degli stessi indicatori.", "Anche questo non batte la frequenza storica: troppa flessibilità, pochi cali veri da imparare."),
    ("Combinato", "Miscela dei modelli", "Media pesata di più modelli, con correzione.", "I pesi cambiano in base a quanto ogni modello ha funzionato nel passato.", "Non ha superato la regola di adozione: resta solo informativo."),
]


def _schede(d: dict) -> str:
    E = _h.escape
    out = ""
    for m, tit, uno, come, lim in SCHEDE:
        rs = []
        for hz in HZ:
            r = next((x for x in d.get(hz, {}).get("righe", []) if x["m"] == m), None)
            if r and r["bss"] is not None and m != "Normale":
                rs.append(f"{HZ_NOME[hz]} {r['bss'] * 100:+.1f}%".replace(".", ","))
        num = ("<p><b>Risultato (bravura rispetto alla frequenza storica):</b> " + " · ".join(rs) + ".</p>") if rs else ""
        ref = " <em class='md-tag'>riferimento</em>" if m == RIFERIMENTO else (" <em class='md-tag md-t2'>seconda opinione</em>" if m == "A1" else "")
        out += (f"<details class='md-sc' style='border-left:5px solid {COL[m]}'><summary><b>{E(tit)}</b>{ref}<small>{E(uno)}</small></summary>"
                f"<div><p><b>Come è calcolato.</b> {E(come)}</p>{num}<p><b>Punti forti e limiti.</b> {E(lim)}</p></div></details>")
    return out


def revisione(storia, ref: str = RIFERIMENTO, minimo_mesi: int = 12) -> dict:
    """Regola annuale (PROTOCOLLO_MODELLI.md): uno sfidante sostituisce il riferimento solo se, a OGNI fine mese dell'ultimo anno, il suo voto cumulativo
    è più alto di quello del riferimento. Servono almeno 12 fine-mese con voti di entrambi. «storia» = tabella data, modello, voto (classifica_storia.csv)."""
    import pandas as pd
    if storia is None or len(storia) == 0:
        return {"mesi": 0, "sfidanti": {}, "cambia": None}
    s = storia.copy()
    s["data"] = pd.to_datetime(s["data"])
    s["mese"] = s["data"].dt.to_period("M")
    fine = s.sort_values("data").groupby(["mese", "modello"]).tail(1).pivot(index="mese", columns="modello", values="voto")
    fine = fine.tail(12)
    if ref not in fine.columns:
        return {"mesi": 0, "sfidanti": {}, "cambia": None}
    out = {}
    for m in fine.columns:
        if m == ref:
            continue
        ok = fine[[m, ref]].dropna()
        out[m] = {"sopra": int((ok[m] > ok[ref]).sum()), "mesi": int(len(ok))}
    mesi = int(fine[ref].notna().sum())
    vinc = [m for m, x in out.items() if x["mesi"] >= minimo_mesi and x["sopra"] == x["mesi"]]
    return {"mesi": mesi, "sfidanti": out, "cambia": vinc[0] if vinc else None}


def revisione_html() -> str:
    try:
        from . import classifica
        r = revisione(classifica.storia())
    except Exception:  # noqa: BLE001
        r = {"mesi": 0, "sfidanti": {}, "cambia": None}
    E = _h.escape
    righe = "".join(f"<div class='md-rv'><span>{E(NOMI.get(m, m))}</span><b>{x['sopra']} su {x['mesi']}</b></div>" for m, x in sorted(r["sfidanti"].items(), key=lambda kv: -kv[1]["sopra"])[:5])
    stato = (f"Controlli mensili raccolti: <b>{r['mesi']} su 12</b>. " + ("Nessuno sfidante ha superato il riferimento a ogni fine mese: il riferimento non cambia." if not r["cambia"] else f"Attenzione: {E(r['cambia'])} è sopra il riferimento a tutti i controlli: valutare il cambio a novembre."))
    return (f"<div class='explain'><p>{stato}</p>" + (f"<div class='md-rvs'>{righe}<small>fine mesi in cui lo sfidante ha il voto più alto del riferimento</small></div>" if righe else "")
            + "<p>Servono almeno 12 controlli (uno a fine mese). Se la regola non scatta a novembre, il riferimento resta FHS+VIX e si riparte.</p></div>")


def html(ev: dict | None = None, fin: dict | None = None, classifica_html: str = "") -> str:
    if ev is None:
        try:
            ev = json.loads((DATA / "model_eval.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            ev = None
    if fin is None:
        from . import modelli_finestre
        fin = modelli_finestre.carica()
    d = dati(ev, fin)
    if not d:
        return CSS + "<h2>Modelli</h2><p class='mu'>La scheda comparirà dopo la prima valutazione dei modelli.</p>"
    dj = _h.escape(json.dumps({"d": d, "col": COL, "nomi": NOMI, "brevi": BREVI, "ref": RIFERIMENTO}, ensure_ascii=False, separators=(",", ":")), quote=True)
    hero = ("<div class='md-hero'><div><small>MODELLO DI RIFERIMENTO · TUTTI GLI ORIZZONTI</small><h3>FHS+VIX</h3>"
            "<p>È il modello con cui si misura tutto il resto. <b>A1</b> resta come seconda opinione: il semaforo continua a mostrare la stima dei due insieme e, se si contraddicono, diventa grigio.</p></div>"
            "<div class='md-rule'><b>Regola decisa in anticipo</b><p>Il riferimento cambia solo se un altro modello ha un voto cumulativo più alto del riferimento <b>per l'intero anno</b> (a ogni fine mese). "
            "La valutazione si fa <b>ogni novembre</b>: la prossima è a novembre 2027. Se la regola non scatta, non si cambia nulla.</p></div></div>")
    come = ("<details class='md-info'><summary><i>i</i> Come leggere i numeri</summary><div><p>Per ogni modello si guarda la probabilità di calo che aveva previsto e si confronta con quello che è successo davvero. "
            "<b>Bravura</b> (in inglese BSS) = di quanto il suo errore è più piccolo di quello della <b>frequenza storica</b>. +7% vuol dire che sbaglia il 7% in meno; 0% che non aggiunge niente; negativo che peggiora.</p>"
            "<p>Le <b>righe sottili</b> sono il margine di incertezza (90%): se includono lo zero, non si può dire che il modello sia davvero meglio del caso. "
            "<b>AUC</b> = quanto bene mette in ordine i giorni: 50 vuol dire a caso, 100 perfetto.</p>"
            "<p>I calcoli usano la storia dal 1990 e solo informazioni note al momento della previsione.</p></div></details>")
    esplora = (f"<div id='mdroot' data-d=\"{dj}\"><div class='md-sel' role='tablist' aria-label='Scegli l'orizzonte'></div>"
               "<div id='md-ex'><p class='mu'>Caricamento dei grafici…</p></div></div>")
    vincere = ("<div class='explain'><p><b>Vincere spesso non vuol dire sbagliare meno in totale.</b> La FHS e la FHS+VIX sono quasi uguali: la FHS vince più periodi ma quasi sempre di pochissimo, "
               "mentre sommando gli errori la FHS+VIX è appena sotto (o pari). Per questo si guardano insieme le <b>vittorie</b> e l'<b>errore totale</b>. "
               "In una singola settimana c'è una sola previsione: il vincitore è in gran parte fortuna. Il verdetto serio arriva con trimestri e semestri.</p></div>")
    return (CSS + "<div id='mdpage'><h2>Modelli</h2><div class='explain'><p>Qui ci sono <b>tutti i modelli che prevedono i cali del mercato</b>: chi è il riferimento, chi è più bravo a ogni orizzonte (una settimana, un mese, tre mesi, sei mesi), "
            "chi ha vinto in ogni periodo e come è calcolato ciascuno. Nessun modello cambia da solo: valgono regole scritte prima.</p></div>"
            + hero + "<h3>Il podio per orizzonte</h3><p class='md-nota'>Bravura rispetto alla frequenza storica, sul calo principale di ogni orizzonte. «Affidabilità» dice quanto ci si può fidare del riferimento a quell'orizzonte.</p>"
            + _podio(d) + "<h3>Mappa della bravura</h3>" + _heat(d) + come
            + "<h3>Esplora: classifica, vincitori, andamento nel tempo e taratura</h3>" + esplora + vincere
            + "<h3>Classifica cumulativa dei voti</h3><p class='md-nota'>Voto da 1 a 100: 50 = nessuna abilità. È il voto che decide la revisione di novembre.</p>" + classifica_html
            + "<h3>Revisione annuale di novembre</h3>" + revisione_html() + "<h3>Come è calcolato ogni modello</h3>" + _schede(d)
            + "<p class='md-nota'>Le regole complete sono in PROTOCOLLO_MODELLI.md. La prossima revisione è nella scheda <a href='#verifiche' data-go='verifiche'>Verifiche e scadenze</a>.</p></div>" + JS)


JS = r"""<script>(function(){var R=document.getElementById('mdroot');if(!R||R.dataset.on)return;R.dataset.on=1;var D;try{D=JSON.parse(R.dataset.d)}catch(e){return}
var HZ=['10g','1m','3m','6m'],st={hz:'1m',per:'mese',rec:false,sort:'bss',hide:{}};
function E(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function P(x,d){return x==null?'–':((x*100>=0?'+':'−')+Math.abs(x*100).toFixed(d==null?1:d)).replace('.',',')+'%'}
function sel(){var h='';HZ.forEach(function(k){var o=D.d[k];if(o)h+='<button type="button" role="tab" aria-selected="'+(k===st.hz)+'" class="'+(k===st.hz?'on':'')+'" data-hz="'+k+'">'+E(o.nome)+'</button>'});R.querySelector('.md-sel').innerHTML=h}
function tabella(o){var rs=o.righe.slice().filter(function(r){return r.m!=='Normale'});var k=st.sort;rs.sort(function(a,b){return (b[k]==null?-9:b[k])-(a[k]==null?-9:a[k])});
var mn=-0.12,mx=0.2;var sc=function(v){return Math.max(0,Math.min(100,(v-mn)/(mx-mn)*100))};
var h='<div class="md-sorts" role="group" aria-label="Ordina per">Ordina per: '+[['bss','Bravura'],['auc','AUC'],['b3','Dal 2013'],['b1','Fino al 2012']].map(function(x){return '<button type="button" data-sort="'+x[0]+'" class="'+(k===x[0]?'on':'')+'">'+x[1]+'</button>'}).join('')+'</div><div class="md-tab">';
rs.forEach(function(r,i){var col=D.col[r.m]||'#64748b';var lo=r.lo,hi=r.hi;
h+='<div class="md-tr'+(r.m===D.ref?' md-ref':'')+'"><span class="md-tp">'+(i+1)+'</span><div class="md-tm"><b><i style="background:'+col+'"></i>'+E(D.nomi[r.m]||r.m)+'</b><small>'+(r.altro?'confronto su un altro insieme di date · ':'')+'AUC '+(r.auc!=null?(r.auc*100).toFixed(0):'–')+' · fino al 2012 '+P(r.b1)+' · dal 2013 '+P(r.b3)+'</small></div>'+
'<div class="md-sk" aria-hidden="true"><u style="left:'+sc(0)+'%"></u>'+(lo!=null&&hi!=null?'<s style="left:'+sc(lo)+'%;width:'+(sc(hi)-sc(lo))+'%"></s>':'')+'<i style="left:'+sc(r.bss)+'%;background:'+(r.bss<0?'#dc2626':col)+'"></i></div><b class="md-bv" style="color:'+(r.bss<0?'#dc2626':'inherit')+'">'+P(r.bss)+'</b></div>'});
return h+'</div><p class="md-nota">Il pallino è la bravura, la riga sottile il margine di incertezza (90%), la linea verticale è lo zero = come la frequenza storica. '+o.righe[0].n+' previsioni dal '+E(o.righe[0].da.slice(0,4))+'.</p>'}
function vincitori(o){var f=o.fin;if(!f)return '<p class="mu">I vincitori per periodo compaiono dopo la prossima valutazione mensile.</p>';var pers=[['settimana','Settimana'],['mese','Mese'],['trimestre','Trimestre'],['semestre','Semestre']];
var ms=['Normale','A1','FHS','FHS+VIX','Pari'];
var h='<div class="md-sorts" role="group" aria-label="Periodo">Periodo: '+pers.map(function(p){return '<button type="button" data-per="'+p[0]+'" class="'+(st.per===p[0]?'on':'')+'">'+p[1]+'</button>'}).join('')+' <span class="md-sp"></span><button type="button" data-rec="0" class="'+(st.rec?'':'on')+'">Tutta la storia</button><button type="button" data-rec="1" class="'+(st.rec?'on':'')+'">Ultimi 12 anni</button></div>';
pers.forEach(function(p){var x=f.periodi[p[0]];if(!x)return;var q=st.rec?x.quote_12a:x.quote;h+='<div class="md-wrow'+(st.per===p[0]?' on':'')+'"><span>'+p[1]+'<small>'+x.n+' periodi</small></span><div class="md-stack" role="img" aria-label="'+ms.map(function(m){return m+' '+q[m]+'%'}).join(', ')+'">'+ms.map(function(m){return q[m]>0?'<i style="width:'+q[m]+'%;background:'+D.col[m]+'" title="'+E(m)+': '+q[m]+'% dei periodi">'+(q[m]>=9?Math.round(q[m]):'')+'</i>':''}).join('')+'</div></div>'});
h+='<div class="md-leg">'+ms.map(function(m){return '<span><i style="background:'+D.col[m]+'"></i>'+E(m)+'</span>'}).join('')+'<small>% di periodi vinti</small></div>';
var u=f.periodi[st.per].ultimi;h+='<div class="md-ult"><b>Ultimi periodi ('+E(st.per)+')</b><div>'+u.map(function(z){return '<span class="md-chip" style="background:'+D.col[z.v]+';color:'+(z.v==='Pari'||z.v==='Normale'?'#0f172a':'#fff')+'" title="'+E(z.p)+': vince '+E(z.v)+' ('+z.n+' previsioni)">'+E(z.p.replace(/^\d{4}-/,'').replace(/^(\d\d)$/,function(m){return ['','gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic'][+m]||m}))+'<small>'+E(z.v)+'</small></span>'}).join('')+'</div></div>';return h}
function nel(o){var f=o.fin;if(!f)return '';var ys=Object.keys(f.anni).sort();var ms=['Normale','A1','FHS','FHS+VIX'];var cum={};ms.forEach(function(m){cum[m]=[]});var sm={},sn=0;ms.forEach(function(m){sm[m]=0});
ys.forEach(function(y){var n=f.anni_n[y]||1;ms.forEach(function(m){sm[m]+=f.anni[y][m]*n});ms.forEach(function(m){cum[m].push(m==='Normale'?0:1-sm[m]/sm.Normale)})});
var W=640,H=240,L=44,Rr=10,T=10,B=26;var all=[];ms.forEach(function(m){if(m!=='Normale')all=all.concat(cum[m].slice(2))});var lo=Math.min(-0.02,Math.min.apply(null,all)),hi=Math.max(0.02,Math.max.apply(null,all));
var X=function(i){return L+i/(ys.length-1)*(W-L-Rr)},Y=function(v){return T+(hi-v)/(hi-lo)*(H-T-B)};
var s='<svg viewBox="0 0 '+W+' '+H+'" class="md-svg" role="img" aria-label="Bravura cumulativa nel tempo">';for(var g=0;g<=4;g++){var v=lo+(hi-lo)*g/4;s+='<line x1="'+L+'" x2="'+(W-Rr)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="currentColor" opacity=".12"/><text x="'+(L-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" font-size="10" fill="currentColor" opacity=".6">'+(v*100).toFixed(0)+'%</text>'}
s+='<line x1="'+L+'" x2="'+(W-Rr)+'" y1="'+Y(0)+'" y2="'+Y(0)+'" stroke="currentColor" opacity=".5"/>';ys.forEach(function(y,i){if(i%5===0)s+='<text x="'+X(i)+'" y="'+(H-8)+'" text-anchor="middle" font-size="10" fill="currentColor" opacity=".6">'+y+'</text>'});
ms.forEach(function(m){if(m==='Normale'||st.hide[m])return;var pts=cum[m].map(function(v,i){return i<2?null:X(i).toFixed(1)+','+Y(v).toFixed(1)}).filter(Boolean).join(' ');s+='<polyline points="'+pts+'" fill="none" stroke="'+D.col[m]+'" stroke-width="'+(m===D.ref?3:2)+'" stroke-linejoin="round"/>'});s+='</svg>';
var leg='<div class="md-leg">'+ms.filter(function(m){return m!=='Normale'}).map(function(m){return '<button type="button" data-hide="'+m+'" class="md-lb'+(st.hide[m]?' off':'')+'" aria-pressed="'+(!st.hide[m])+'"><i style="background:'+D.col[m]+'"></i>'+E(m)+' '+P(cum[m][cum[m].length-1])+'</button>'}).join('')+'<small>tocca per nascondere</small></div>';
return s+leg+'<p class="md-nota">Ogni linea parte dal 1990 e somma gli errori anno dopo anno: è la bravura cumulativa. Se le linee si sfiorano, i modelli sono praticamente alla pari.</p>'}
function taratura(o){var ms=['A1','FHS','FHS+VIX'].filter(function(m){return o.cal[m]});if(!ms.length)return '';var S=240,L=34,B=26,T=8;var mx=0;ms.forEach(function(m){o.cal[m].forEach(function(p){mx=Math.max(mx,p[0],p[1])})});mx=Math.max(0.05,Math.ceil(mx*20)/20);
var X=function(v){return L+v/mx*(S-L-8)},Y=function(v){return S-B-v/mx*(S-B-T)};var s='<svg viewBox="0 0 '+S+' '+S+'" class="md-svg md-sq" role="img" aria-label="Previsto contro reale">';
for(var g=0;g<=4;g++){var v=mx*g/4;s+='<line x1="'+L+'" x2="'+(S-8)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="currentColor" opacity=".1"/><text x="'+(L-4)+'" y="'+(Y(v)+3)+'" text-anchor="end" font-size="9" fill="currentColor" opacity=".6">'+Math.round(v*100)+'</text><text x="'+X(v)+'" y="'+(S-10)+'" text-anchor="middle" font-size="9" fill="currentColor" opacity=".6">'+Math.round(v*100)+'</text>'}
s+='<line x1="'+X(0)+'" y1="'+Y(0)+'" x2="'+X(mx)+'" y2="'+Y(mx)+'" stroke="currentColor" stroke-dasharray="4 3" opacity=".5"/>';
ms.forEach(function(m){o.cal[m].forEach(function(p){s+='<circle cx="'+X(p[0])+'" cy="'+Y(p[1])+'" r="'+(m===D.ref?4.5:3.5)+'" fill="'+D.col[m]+'" fill-opacity=".8"><title>'+E(m)+': previsto '+(p[0]*100).toFixed(1)+'%, avvenuto '+(p[1]*100).toFixed(1)+'% ('+p[2]+' casi)</title></circle>'})});
s+='<text x="'+(S/2)+'" y="'+(S-1)+'" text-anchor="middle" font-size="9" fill="currentColor" opacity=".7">previsto (%)</text></svg>';
return '<div class="md-cal">'+s+'<p class="md-nota">Ogni pallino raggruppa giorni con previsioni simili (da bassa ad alta). <b>Sulla linea tratteggiata</b> = previsione onesta: quando il modello dice 10%, succede circa 10 volte su 100. Sopra la linea il modello sottostima il rischio, sotto lo sovrastima.</p></div>'}
function draw(){var o=D.d[st.hz];if(!o)return;var et=o.et;
R.querySelector('#md-ex').innerHTML='<div class="md-hint" style="border-color:'+et[1]+'"><b>'+E(o.nome)+'</b> · calo ≥'+o.thr+'% in '+o.sedute+' · affidabilità del riferimento: <b style="color:'+et[1]+'">'+et[0]+'</b></div>'+
'<h4>Classifica</h4>'+tabella(o)+'<h4>Chi vince nei periodi</h4>'+vincitori(o)+'<h4>Bravura cumulativa nel tempo</h4>'+nel(o)+'<h4>Le previsioni sono oneste? (taratura)</h4>'+taratura(o);sel()}
R.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;if(b.dataset.hz){st.hz=b.dataset.hz}else if(b.dataset.sort){st.sort=b.dataset.sort}else if(b.dataset.per){st.per=b.dataset.per}else if(b.dataset.rec!=null){st.rec=b.dataset.rec==='1'}else if(b.dataset.hide){st.hide[b.dataset.hide]=!st.hide[b.dataset.hide]}else return;draw()});
sel();draw()})()</script>"""

CSS = """<style>
.md-hero{display:grid;grid-template-columns:1.2fr 1fr;gap:12px;margin:10px 0}@media(max-width:700px){.md-hero{grid-template-columns:1fr}}
.md-hero>div{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:12px 16px}.md-hero small{color:var(--mu);font-size:10.5px;letter-spacing:.5px;font-weight:700}
.md-hero h3{margin:2px 0 4px;font-size:28px;color:#6366f1}.md-hero p{font-size:13px;line-height:1.5;margin:4px 0}.md-rule{border-left:5px solid #6366f1!important}
.md-podi{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:8px 0}.md-pod{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:10px 12px}
.md-ph{display:flex;flex-direction:column;margin-bottom:6px}.md-ph small{color:var(--mu);font-size:11px}.md-pr{display:grid;grid-template-columns:24px 66px 1fr 52px;gap:6px;align-items:center;font-size:12px;margin:3px 0}.md-pr.md-ref .md-pn{font-weight:800}
.md-pb{height:9px;background:var(--bd);border-radius:99px;overflow:hidden}.md-pb i{display:block;height:100%;border-radius:99px}.md-pr b{text-align:right;font-size:12px}.md-et{margin-top:8px;border:1.5px solid;border-radius:99px;padding:3px 10px;font-size:12px;text-align:center}
.md-heat{display:grid;grid-template-columns:96px repeat(4,1fr);gap:4px;margin:8px 0;font-size:12px}.md-hh{text-align:center;font-weight:700;font-size:11px;color:var(--mu)}.md-hm{display:flex;align-items:center;gap:6px;font-weight:700}.md-hm i{width:10px;height:10px;border-radius:3px}
.md-hc{text-align:center;padding:9px 2px;border-radius:8px;font-weight:700;border:1px solid var(--bd)}.md-nota{font-size:12px;color:var(--mu);line-height:1.5;margin:4px 0 8px}
.md-info,.md-sc{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px 14px;margin:8px 0;font-size:13px;line-height:1.5}.md-info summary,.md-sc summary{cursor:pointer}.md-info summary i{display:inline-block;width:16px;height:16px;line-height:16px;text-align:center;border-radius:50%;background:var(--mu);color:var(--bg);font-style:normal;font-size:10px;margin-right:6px}
.md-sc summary{display:flex;flex-direction:column;gap:2px}.md-sc summary small{color:var(--mu);font-size:12px}.md-tag{font-style:normal;font-size:10.5px;font-weight:800;background:#6366f1;color:#fff;border-radius:99px;padding:1px 8px;margin-left:6px}.md-t2{background:#f59e0b}
.md-sel{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.md-sel button,.md-sorts button,.md-lb{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 14px;font:inherit;font-size:13px;cursor:pointer}
.md-sel button.on,.md-sorts button.on{background:var(--tx);color:var(--bg);border-color:var(--tx)}.md-sorts{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--mu);margin:6px 0}.md-sorts button{padding:4px 11px;font-size:12px}.md-sp{flex:1}
.md-hint{border-left:5px solid;background:var(--card);border-radius:10px;padding:8px 12px;font-size:13px;margin:6px 0}#md-ex h4{margin:16px 0 4px;font-size:14px}
.md-tr{display:grid;grid-template-columns:22px 1fr 150px 54px;gap:8px;align-items:center;padding:7px 8px;border-radius:10px;border:1px solid var(--bd);background:var(--card);margin:4px 0}@media(max-width:560px){.md-tr{grid-template-columns:20px 1fr 54px}.md-sk{display:none}}
.md-tr.md-ref{border-color:#6366f1;box-shadow:0 0 0 1px #6366f1}.md-tp{font-weight:800;color:var(--mu)}.md-tm b{font-size:13px;display:flex;align-items:center;gap:6px}.md-tm i{width:10px;height:10px;border-radius:3px;flex:none}.md-tm small{display:block;color:var(--mu);font-size:11px;margin-top:1px}
.md-sk{position:relative;height:12px;background:var(--bd);border-radius:99px}.md-sk u{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--tx);opacity:.5}.md-sk s{position:absolute;top:5px;height:2px;background:var(--tx);opacity:.55}.md-sk i{position:absolute;top:-1px;width:14px;height:14px;margin-left:-7px;border-radius:50%;border:2px solid var(--card)}.md-bv{text-align:right;font-size:14px}
.md-wrow{display:grid;grid-template-columns:96px 1fr;gap:8px;align-items:center;margin:4px 0;opacity:.75}.md-wrow.on{opacity:1}.md-wrow span{font-size:12px;font-weight:700}.md-wrow small{display:block;font-weight:400;color:var(--mu);font-size:10.5px}
.md-stack{display:flex;height:24px;border-radius:8px;overflow:hidden;border:1px solid var(--bd)}.md-stack i{display:flex;align-items:center;justify-content:center;font-style:normal;font-size:10.5px;font-weight:700;color:#fff}
.md-leg{display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-size:12px;margin:8px 0}.md-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px}.md-leg small{color:var(--mu);margin-left:auto}.md-lb.off{opacity:.4;text-decoration:line-through}.md-lb{padding:3px 10px;font-size:12px}
.md-ult>div{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.md-chip{display:flex;flex-direction:column;align-items:center;border-radius:10px;padding:4px 10px;font-size:12px;font-weight:700}.md-chip small{font-size:10px;font-weight:600;opacity:.9}
.md-rvs{margin:6px 0}.md-rv{display:flex;justify-content:space-between;border-top:1px solid var(--bd);padding:4px 0;font-size:13px}.md-rvs small{color:var(--mu);font-size:11px}
.md-svg{width:100%;max-width:640px;height:auto;color:var(--tx)}.md-sq{max-width:280px}.md-cal{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.md-cal p{flex:1;min-width:220px}
</style>"""
