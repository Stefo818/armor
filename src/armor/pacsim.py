"""Simulatore del PAC (PIANO ARMOR 3, Fase 5). I dati dell'utente restano nel browser; i percorsi dei rendimenti mensili sono calcolati qui (data/pac_sim.json, copiato in site/).

Percorsi (1.000, seme fisso per data), rendimenti mensili di VWCE IN EURO per 60 mesi:
  - mesi 1-12: dal motore di percorsi condizionato allo stato di oggi (variante V0T1 stimata sui rendimenti di VWCE in euro, `serie_eur`), a blocchi di 21 sedute;
  - mesi 13-60: bootstrap stazionario a blocchi (blocco medio 6 mesi) dei rendimenti mensili storici in euro. Non condizionato: dopo circa 63 sedute il GARCH ha già
    dimenticato lo stato di oggi e le sue code non sono affidabili.
Due scenari sempre insieme: «storico» (rendimenti del campione) e «prudente» (gli stessi con 3 punti all'anno in meno). Il risultato dipende molto dal rendimento medio del campione.
Il simulatore non suggerisce mai di sospendere: confronta soltanto."""
import json

import numpy as np
import pandas as pd

from . import fhs
from .config import DATA

FILE = DATA / "pac_sim.json"
MESI, N_PERCORSI, BLOCCO_MESI = 60, 1000, 6
PRUDENTE = 0.03          # punti all'anno in meno nello scenario prudente
TER_PREDEFINITO = 0.14   # % annuo: VWCE dal 28/07/2026 (0,19% prima). DA VERIFICARE sulla scheda Vanguard; modificabile dall'utente.


def rendimenti_mensili(p_eur: pd.Series) -> np.ndarray:
    m = p_eur.resample("ME").last().dropna()
    return (m / m.shift(1) - 1).dropna().values


def bootstrap_mensile(r_m: np.ndarray, n_paths: int, mesi: int, blocco: float, rng) -> np.ndarray:
    """Bootstrap stazionario (Politis-Romano) dei rendimenti mensili: matrice (n_paths, mesi)."""
    from .verifica import indici_stazionari
    idx = indici_stazionari(len(r_m), blocco, n_paths, rng)           # (n_paths, len(r_m))
    if mesi <= idx.shape[1]:
        return r_m[idx[:, :mesi]]
    return np.concatenate([r_m[idx] for _ in range(int(np.ceil(mesi / idx.shape[1])))], axis=1)[:, :mesi]


def costruisci(p_eur: pd.Series, n_paths: int = N_PERCORSI, mesi: int = MESI, seme: int | None = None) -> dict:
    from . import percorsi as P
    seme = seme if seme is not None else int(p_eur.index[-1].strftime("%Y%m%d")) % (2 ** 31)
    r = fhs.log_returns(p_eur)
    st = P.stato(r.values)
    s0, _ = P.varianza_iniziale(st, "V0T1", None, None)
    paths = P.simula(st, s0, "T1", n_paths, seme)                    # (252, n_paths), base 1
    liv = np.vstack([np.ones((1, n_paths)), paths])
    primi = np.stack([liv[21 * (k + 1)] / liv[21 * k] - 1 for k in range(12)], axis=1)
    rng = np.random.default_rng(seme + 1)
    r_m = rendimenti_mensili(p_eur)
    resto = bootstrap_mensile(r_m, n_paths, mesi - 12, BLOCCO_MESI, rng)
    tutti = np.concatenate([primi, resto], axis=1)
    bp = np.rint(tutti * 10000).astype(int)
    return {"asof": str(p_eur.index[-1].date()), "mesi": mesi, "n": n_paths, "prudente": PRUDENTE, "ter": TER_PREDEFINITO, "persistenza": float(st["rho"]),
            "rendimento_storico_annuo": float((1 + r_m).prod() ** (12 / len(r_m)) - 1), "mesi_storici": int(len(r_m)), "paths": bp.tolist()}


def aggiorna(scrivi: bool = True) -> dict:
    from . import serie_eur
    s = serie_eur.costruisci()
    out = costruisci(s["vwce_eur"])
    if scrivi:
        FILE.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return out


# ------------------------------------------------------------------ specchio Python del calcolo in JavaScript (stessa logica, per i test)
def patrimonio(bp_path, C: float, M: float, giorno: int = 1, costo: float = 0.0, ter: float = 0.0, prudente: bool = False, sospendi: int = 0, modo: str = "ferma", K: float | None = None) -> dict:
    """C = VALORE DI MERCATO oggi di ciò che si possiede già (non il versato). K = costo storico (quanto è stato versato davvero), facoltativo: se manca si assume K = C.
    «versato» = K + M·mesi, il confronto per «sotto il versato». Patrimonio mese per mese su un percorso di rendimenti mensili in punti base. sospendi = mesi senza rata; modo 'ferma' (liquidità ferma) o 'inv' (investita alla ripresa)."""
    f = (1 - ter / 100) ** (1 / 12) * ((1 - PRUDENTE) ** (1 / 12) if prudente else 1.0)
    W, cash, peak, mdd, out = C, 0.0, C, 0.0, []
    for t, b in enumerate(bp_path):
        g = (1 + b / 10000.0) * f
        contrib = 0.0
        if t < sospendi:
            cash += M
        else:
            gross = M
            if modo == "inv" and t == sospendi and cash > 0:
                gross += cash
                cash = 0.0
            contrib = max(gross - costo, 0.0)
        W = W * g + contrib * g ** (1 - (giorno - 1) / 30.0)
        tot = W + cash
        peak = max(peak, tot)
        mdd = min(mdd, tot / peak - 1)
        out.append({"mese": t + 1, "valore": tot, "versato": (C if K is None else K) + M * (t + 1), "mdd": mdd})
    return {"serie": out}


HTML = """<div class='card' id='pacsim'><h3 style='margin-top:0'>Simulatore del PAC: scenari a 1, 3 e 5 anni</h3>
<p class='mu'>Inserisci i tuoi dati (restano <b>solo in questo telefono</b>). Mostra l'intervallo dei risultati possibili, non una previsione. Non è consulenza finanziaria.</p>
<div class='pacform'><label>Valore di mercato oggi di ciò che hai già investito (€)<input id='pscap' type='number' min='0' step='100' inputmode='decimal' placeholder='es. 5000'></label>
<label>Costo storico, cioè quanto hai versato davvero (€, facoltativo)<input id='pskc' type='number' min='0' step='100' inputmode='decimal' placeholder='se vuoto: uguale al valore'></label>
<label>Versamento mensile (€)<input id='psm' type='number' min='0' step='10' inputmode='decimal' placeholder='es. 200'></label>
<label>Giorno di acquisto (1-28)<input id='psd' type='number' min='1' max='28' step='1' inputmode='numeric' value='1'></label>
<label>Costo per acquisto (€)<input id='psc' type='number' min='0' step='0.5' inputmode='decimal' value='0'></label>
<label>Costo annuo del fondo, TER (%)<input id='pst' type='number' min='0' max='2' step='0.01' inputmode='decimal' value='0.14'></label>
<button class='btn pri' id='pssave'>Simula</button></div>
<p class='mu'>TER predefinito 0,14%: valore riportato da fonti di stampa per VWCE dal 28/07/2026 (0,19% prima); <b>verificalo sulla scheda Vanguard del fondo</b> e correggilo se serve. I rendimenti storici del segmento VWCE sono già al netto del costo, quindi applicarlo per intero è prudente.</p>
<div id='psout' class='pacout'></div></div>"""

JS = r"""<script>(function(){var B=document.getElementById('pscap');if(!B)return;var O=document.getElementById('psout'),K='armor_pacsim_v1',DATA=null;
var IDS=['pscap','psm','psd','psc','pst','pskc'];
function fm(v,d){return v.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function eur(v){return fm(v,0)+' €'}
function get(){try{return JSON.parse(localStorage.getItem(K)||'null')}catch(e){return null}}
function put(o){try{localStorage.setItem(K,JSON.stringify(o))}catch(e){}}
var s0=get();if(s0)IDS.forEach(function(i,n){if(s0[n]!==undefined&&s0[n]!==null)document.getElementById(i).value=s0[n]});
function pct(a,q){var i=(a.length-1)*q,lo=Math.floor(i),hi=Math.ceil(i);return a[lo]+(a[hi]-a[lo])*(i-lo)}
function run(paths,o){var f=Math.pow(1-o.ter/100,1/12)*(o.prud?Math.pow(1-DATA.prudente,1/12):1),H=[12,36,60],res={12:[],36:[],60:[]},dd={12:[],36:[],60:[]};
for(var p=0;p<paths.length;p++){var W=o.C,cash=0,peak=o.C,mdd=0,r=paths[p];
for(var t=0;t<60;t++){var g=(1+r[t]/10000)*f,c=0;
if(t<o.sosp){cash+=o.M}else{var gr=o.M;if(o.modo==='inv'&&t===o.sosp&&cash>0){gr+=cash;cash=0}c=Math.max(gr-o.cost,0)}
W=W*g+c*Math.pow(g,1-(o.d-1)/30);var tot=W+cash;if(tot>peak)peak=tot;var x=tot/peak-1;if(x<mdd)mdd=x;
if(t===11||t===35||t===59){res[t+1].push(tot);dd[t+1].push(mdd)}}}
return {res:res,dd:dd}}
function stat(o){var R=run(DATA.paths,o),out={};[12,36,60].forEach(function(h){var a=R.res[h].slice().sort(function(x,y){return x-y}),d=R.dd[h].slice().sort(function(x,y){return x-y}),paid=(o.K>0?o.K:o.C)+o.M*h,below=0;
for(var i=0;i<R.res[h].length;i++)if(R.res[h][i]<paid)below++;
out[h]={q:[.05,.10,.25,.5,.75,.9,.95].map(function(q){return pct(a,q)}),below:below/a.length,mddMed:pct(d,.5),mddBad:pct(d,.1),paid:paid,raw:R.res[h]}});return out}
function tab(S){var h='<div class="scroll"><table><tr><th>Dopo</th><th>Versato</th><th>5%</th><th>25%</th><th>Mediana</th><th>75%</th><th>95%</th><th>Sotto il versato</th><th>Calo massimo (mediana / caso brutto)</th></tr>';
[12,36,60].forEach(function(k){var x=S[k];h+='<tr><td>'+(k/12)+(k===12?' anno':' anni')+'</td><td>'+eur(x.paid)+'</td><td>'+eur(x.q[0])+'</td><td>'+eur(x.q[2])+'</td><td><b>'+eur(x.q[3])+'</b></td><td>'+eur(x.q[4])+'</td><td>'+eur(x.q[6])+'</td><td>'+fm(x.below*100,0)+'%</td><td>'+fm(x.mddMed*100,0)+'% / '+fm(x.mddBad*100,0)+'%</td></tr>'});
return h+'</table></div>'}
function calc(){var v=IDS.map(function(i){return parseFloat(document.getElementById(i).value)});
var o={K:v[5]||0,C:v[0]||0,M:v[1]||0,d:Math.min(Math.max(v[2]||1,1),28),cost:v[3]||0,ter:isNaN(v[4])?0.14:v[4],sosp:0,modo:'ferma',prud:false};
if(!(o.C>0)&&!(o.M>0)){O.innerHTML='<p class="muted">Inserisci almeno il capitale o il versamento mensile.</p>';return}
put(v);if(!DATA){O.innerHTML='<p class="mu">Caricamento dei percorsi…</p>';return}
var h='',a=stat(o);o.prud=true;var b=stat(o);o.prud=false;
h+='<h4>Scenario storico</h4>'+tab(a)+'<h4>Scenario prudente (3 punti all\'anno in meno)</h4>'+tab(b);
h+='<p class="mu">I percorsi sono '+DATA.n+' simulazioni di VWCE in euro: i primi 12 mesi dal motore di rischio di oggi, poi rendimenti mensili storici ricampionati (dal 2008, '+DATA.mesi_storici+' mesi, media storica '+fm(DATA.rendimento_storico_annuo*100,1)+'% all\'anno: <b>il risultato dipende molto da questo campione</b>, di un periodo favorevole alle azioni). Tasse non incluse. 5% e 95% sono stime grezze con '+DATA.n+' percorsi.</p>';
h+='<h4>Continuare o fermarsi per qualche mese: solo un confronto</h4><div class="scroll"><table><tr><th>A 5 anni (scenario storico)</th><th>Mediana</th><th>Caso brutto (10%)</th><th>Più alto del «continuo» in</th></tr>';
var base=a[60],cmp=function(lbl,oo){var s=stat(oo)[60],w=0;for(var i=0;i<s.raw.length;i++)if(s.raw[i]>base.raw[i])w++;return '<tr><td>'+lbl+'</td><td>'+eur(s.q[3])+'</td><td>'+eur(s.q[1])+'</td><td>'+fm(w/s.raw.length*100,0)+'% dei percorsi</td></tr>'};
h+='<tr><td><b>Continuo senza pause</b></td><td><b>'+eur(base.q[3])+'</b></td><td>'+eur(base.q[1])+'</td><td>—</td></tr>';
[3,6].forEach(function(k){h+=cmp('Sospendo '+k+' mesi, soldi fermi in liquidità',Object.assign({},o,{sosp:k,modo:'ferma'}));h+=cmp('Sospendo '+k+' mesi, tutto investito alla ripresa',Object.assign({},o,{sosp:k,modo:'inv'}))});
h+='</table></div><p class="mu">Due ipotesi sui soldi non versati: restano fermi (nessun rendimento) oppure vengono investiti tutti insieme alla ripresa. Il simulatore non suggerisce di sospendere: mostra solo cosa cambierebbe.</p>';
h+='<p><b>Per chi accumula a rate:</b> i cali dei primi anni comprano più quote; il rischio pesa di più vicino al momento in cui si disinveste.</p>';
O.innerHTML=h}
fetch('pac_sim.json?'+Date.now()).then(function(r){return r.ok?r.json():null}).then(function(j){DATA=j;if(s0)calc()}).catch(function(){O.innerHTML='<p class="muted">Percorsi non disponibili ora.</p>'});
document.getElementById('pssave').onclick=calc;window.__pacsim={run:run,setData:function(d){DATA=d},stat:stat};
})();</script>"""
