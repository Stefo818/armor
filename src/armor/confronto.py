"""Grafico di confronto giornaliero: in alto i mercati azionari (linee continue, base 100), sotto Indice Armor, probabilità, famiglie, volatilità, credito, valutazioni,
materie prime, cripto, sentimento: tutto attivabile a piacere, con scheda descrittiva e scorrimento/zoom. Dati in series/confronto.json (caricati a richiesta)."""
import json

import numpy as np
import pandas as pd

from . import semafori, store
from .config import DATA

GRUPPI = [("a", "Mercati azionari (linee in alto, base 100)"), ("rischio", "Indici Armor e pilastri Titan"), ("prev", "Previsioni dei modelli: probabilità di calo"), ("vol", "Volatilità"), ("cred", "Credito e tassi"),
          ("val", "Valutazioni"), ("mat", "Materie prime e cripto"), ("sent", "Sentimento, ampiezza e valute"), ("mer", "Mercato")]

# chiave, etichetta, colore, unità, acceso all'inizio, gruppo
SERIES = [
    ("sp500", "S&P 500", "#e6a700", "", 1, "a"), ("vwce", "VWCE", "#3b82f6", "", 1, "a"), ("nasdaq100", "Nasdaq 100", "#a855f7", "", 0, "a"),
    ("mweq", "MSCI World Equal Weight (MWEQ)", "#14b8a6", "", 0, "a"), ("rsp", "S&P 500 Equal Weight", "#f97316", "", 0, "a"),
    ("urth", "MSCI World (URTH)", "#84cc16", "", 0, "a"), ("stoxx600", "Europa STOXX 600", "#ec4899", "", 0, "a"), ("eem", "Mercati emergenti", "#ef4444", "", 0, "a"),
    ("dax", "DAX", "#06b6d4", "", 0, "a"), ("ftsemib", "FTSE MIB", "#22c55e", "", 0, "a"), ("nikkei", "Nikkei 225", "#eab308", "", 0, "a"), ("iwm", "Small cap USA", "#8b5cf6", "", 0, "a"),
    ("armor", "Indice Armor", "tx", "", 1, "rischio"), ("super", "Super Armor (SAI)", "#f59e0b", "", 1, "rischio"), ("regime", "Regime: pressione accumulata (0-100)", "#b91c1c", "", 0, "rischio"),
    ("t_p1", "Pilastro Andamento dei prezzi", "#8b5cf6", "", 0, "rischio"), ("t_p2", "Pilastro Credito", "#14b8a6", "", 0, "rischio"), ("t_p3", "Pilastro Paura sui mercati", "#06b6d4", "", 0, "rischio"),
    ("t_p4", "Pilastro Rischio tra i mercati", "#ec4899", "", 0, "rischio"), ("t_p5", "Pilastro Lavoro ed economia", "#84cc16", "", 0, "rischio"), ("t_p6", "Pilastro Liquidità", "#3b82f6", "", 0, "rischio"),
    ("pm_Titan_10g", "Titan (riferimento) · calo ≥5% a 10 giorni", "#eab308", "%", 0, "prev"),
    ("pm_Titan_1m", "Titan (riferimento) · calo ≥10% a 1 mese", "#eab308", "%", 1, "prev"),
    ("pm_Titan_3m", "Titan (riferimento) · calo ≥10% a 3 mesi", "#eab308", "%", 1, "prev"),
    ("pm_Titan_6m", "Titan (riferimento) · calo ≥10% a 6 mesi", "#eab308", "%", 0, "prev"),
    ("pm_FHS+VIX_10g", "FHS+VIX · calo ≥5% a 10 giorni", "#6366f1", "%", 0, "prev"),
    ("pm_FHS+VIX_1m", "FHS+VIX · calo ≥10% a 1 mese", "#6366f1", "%", 0, "prev"),
    ("pm_FHS+VIX_3m", "FHS+VIX · calo ≥10% a 3 mesi", "#6366f1", "%", 0, "prev"),
    ("pm_FHS+VIX_6m", "FHS+VIX · calo ≥10% a 6 mesi", "#6366f1", "%", 0, "prev"),
    ("pm_FHS_10g", "FHS · calo ≥5% a 10 giorni", "#0ea5e9", "%", 0, "prev"),
    ("pm_FHS_1m", "FHS · calo ≥10% a 1 mese", "#0ea5e9", "%", 0, "prev"),
    ("pm_FHS_3m", "FHS · calo ≥10% a 3 mesi", "#0ea5e9", "%", 0, "prev"),
    ("pm_FHS_6m", "FHS · calo ≥10% a 6 mesi", "#0ea5e9", "%", 0, "prev"),
    ("pm_A1_10g", "A1 · calo ≥5% a 10 giorni", "#f59e0b", "%", 0, "prev"),
    ("pm_A1_1m", "A1 · calo ≥10% a 1 mese", "#f59e0b", "%", 0, "prev"),
    ("pm_A1_3m", "A1 · calo ≥10% a 3 mesi", "#f59e0b", "%", 0, "prev"),
    ("pm_A1_6m", "A1 · calo ≥10% a 6 mesi", "#f59e0b", "%", 0, "prev"),
    ("vix", "VIX", "#f59e0b", "", 0, "vol"), ("vix_ratio", "VIX / VIX3M", "#fb923c", "", 0, "vol"), ("vvix", "VVIX", "#fbbf24", "", 0, "vol"),
    ("move", "MOVE (volatilità obbligazioni)", "#f87171", "", 0, "vol"), ("skew", "SKEW", "#c084fc", "", 0, "vol"),
    ("hy_oas", "Spread High Yield", "#a16207", " %", 0, "cred"), ("ig_oas", "Spread Investment Grade", "#ca8a04", " %", 0, "cred"),
    ("baa10y", "Spread BAA-10Y", "#b45309", " %", 0, "cred"), ("dgs10", "Rendimento 10 anni USA", "#38bdf8", " %", 0, "cred"),
    ("real10y", "Rendimento reale 10 anni", "#0ea5e9", " %", 0, "cred"), ("t10y3m", "Curva 10Y-3M", "#2dd4bf", " %", 0, "cred"),
    ("t10y2y", "Curva 10Y-2Y", "#34d399", " %", 0, "cred"), ("nfci", "Condizioni finanziarie (NFCI)", "#94a3b8", "", 0, "cred"),
    ("pe_m", "P/E S&P 500", "#f472b6", "", 0, "val"), ("ps_m", "P/S S&P 500", "#e879f9", "", 0, "val"), ("cape_m", "CAPE (Shiller)", "#d946ef", "", 0, "val"),
    ("pe_fwd", "P/E previsto S&P 500", "#fb7185", "", 0, "val"), ("ps_fwd", "P/S previsto S&P 500", "#fda4af", "", 0, "val"),
    ("buffett", "Buffett indicator (azioni/PIL)", "#c026d3", " %", 0, "val"), ("erp", "Premio per il rischio azionario", "#a78bfa", " %", 0, "val"),
    ("btc", "Bitcoin", "#f7931a", " $", 0, "mat"), ("eth", "Ether", "#818cf8", " $", 0, "mat"), ("gold", "Oro", "#facc15", " $", 0, "mat"),
    ("silver", "Argento", "#cbd5e1", " $", 0, "mat"), ("wti", "Petrolio WTI", "#78716c", " $", 0, "mat"), ("copper", "Rame", "#c2410c", " $", 0, "mat"),
    ("rame_oro", "Rapporto rame/oro", "#ea580c", "", 0, "mat"), ("natgas", "Gas naturale", "#60a5fa", " $", 0, "mat"),
    ("putcall", "Put/Call", "#fb7185", "", 0, "sent"), ("aaii", "AAII rialzisti-ribassisti", "#4ade80", "", 0, "sent"),
    ("breadth200", "% titoli sopra media 200 giorni", "#2dd4bf", " %", 0, "sent"), ("dxy", "Dollaro (indice)", "#a3e635", "", 0, "sent"), ("eurusd", "EUR/USD", "#22d3ee", "", 0, "sent"),
    ("dd252", "Distanza dai massimi (S&P)", "#64748b", " %", 0, "mer"), ("rsp_spy", "Ampiezza: RSP/SPY", "#94a3b8", "", 0, "mer"),
]
FAM = {"g_paura": "Paura e stress dei mercati", "g_credito": "Credito e liquidità", "g_tassi": "Tassi e obbligazioni", "g_valutazioni": "Valutazioni",
       "g_tendenza": "Tendenza dei prezzi", "g_sentimento": "Sentimento e ampiezza", "g_economia": "Economia reale", "g_modello": "Modello statistico Armor"}
SIMPLE = {"vix": "vix", "vvix": "vvix", "move": "move", "skew": "skew", "hy_oas": "hy_oas", "ig_oas": "ig_oas", "baa10y": "baa10y", "dgs10": "dgs10",
          "real10y": "real10y", "t10y3m": "t10y3m", "t10y2y": "t10y2y", "nfci": "nfci", "pe_m": "pe_m", "ps_m": "ps_m", "cape_m": "cape_m", "pe_fwd": "pe_fwd",
          "ps_fwd": "ps_fwd", "erp": "erp", "btc": "btc", "eth": "eth", "gold": "gold", "silver": "silver", "wti": "wti", "copper": "copper", "natgas": "natgas",
          "aaii": "aaii_spread", "breadth200": "breadth200", "dxy": "dxy", "eurusd": "eurusd",
          "nasdaq100": "nasdaq100", "mweq": "mweq", "rsp": "rsp", "urth": "urth", "stoxx600": "stoxx600", "eem": "eem", "dax": "dax", "ftsemib": "ftsemib",
          "nikkei": "nikkei", "iwm": "iwm"}
LIM = {"pe_m": 45, "ps_m": 100, "cape_m": 45, "pe_fwd": 10, "ps_fwd": 10, "erp": 45, "buffett": 100, "nfci": 7, "aaii": 7, "breadth200": 5, "putcall": 5}
RIF_DATE = ("2008-10-10", "2020-03-20", "2022-10-12")


def _ref(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return None
    out = []
    for d in RIF_DATE:
        t = pd.Timestamp(d)
        out.append(None if s.index[0] > t else round(float(s[s.index <= t].iloc[-1]), 2))
    out.append(round(float(s.iloc[-1]), 2))
    return out


def _decimali(s: pd.Series) -> int:
    m = float(s.dropna().abs().median()) if s.notna().any() else 1.0
    return 0 if m >= 1000 else (1 if m >= 20 else 2)


def build(sp: pd.Series, vw: pd.Series, aix: dict | None) -> dict | None:
    if not aix:
        return None
    from . import glossario_serie
    sp = sp.dropna()
    sp = sp[sp.index >= "2000-01-03"]
    idx = sp.index

    def al(s: pd.Series, limit: int = 7) -> pd.Series:
        s = s.dropna()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        return s.reindex(s.index.union(idx)).ffill(limit=limit).reindex(idx)

    out = {"sp500": al(sp), "vwce": al(vw, 5) if len(vw) else pd.Series(np.nan, index=idx)}
    out["armor"] = al(aix["hist"], 3)
    try:
        from . import tensione
        out["regime"] = al(tensione.pct_espanso(tensione.pressione(aix["hist"].dropna())) * 100, 3)
    except Exception:  # noqa: BLE001
        pass
    try:   # indici e pilastri del motore Titan (storia completa dal 1990)
        t = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
        out["super"] = al(t["super_armor_index"], 3)
        for i in range(1, 7):
            out[f"t_p{i}"] = al(t[f"p{i}_stress"], 3)
    except Exception:  # noqa: BLE001
        pass
    try:   # probabilità di calo storiche dei modelli (Titan, FHS+VIX, FHS, A1): data/modelli_preds.csv
        from . import modelli_preds
        mp = modelli_preds.carica()
        if mp is not None:
            for (m, h), g in mp.groupby(["model", "hz"]):
                out[f"pm_{m}_{h}"] = al(g.drop_duplicates("date").set_index("date")["p"] * 100, 12)
    except Exception:  # noqa: BLE001
        pass
    for k, key in SIMPLE.items():
        try:
            x = store.load(key)
            if len(x.dropna()) >= 30:
                out[k] = al(x, LIM.get(k, 5))
        except Exception:  # noqa: BLE001
            pass
    try:
        v, v3 = store.load("vix"), store.load("vix3m")
        out["vix_ratio"] = al((v / v3.reindex(v.index)).dropna(), 5)
        out["rame_oro"] = al((store.load("copper") / store.load("gold").reindex(store.load("copper").index) * 1000).dropna(), 5)
        out["rsp_spy"] = al((store.load("rsp") / store.load("spy").reindex(store.load("rsp").index) * 100).dropna(), 5)
        out["buffett"] = al((store.load("equity_value") / 1000 / store.load("gdp").reindex(store.load("equity_value").index).ffill() * 100).dropna(), 100)
    except Exception:  # noqa: BLE001
        pass
    try:   # Put/Call: serie storica CBOE (fino al ~2019) + archivio Armor delle opzioni SPY (recente)
        pc = pd.concat([store.load("putcall_cboe"), semafori._arch_series("pc_volume")])
        pc = pc[~pc.index.duplicated(keep="last")].sort_index()
        if len(pc) >= 30:
            out["putcall"] = al(pc, 5)
    except Exception:  # noqa: BLE001
        pass
    try:
        from .features import price_features
        out["dd252"] = al(-price_features(sp)["dd252"] * 100, 3)
    except Exception:  # noqa: BLE001
        pass
    ser, meta = {}, []
    for k, n, c, u, on, g in SERIES:
        s = out.get(k)
        if s is None or s.notna().sum() < 30:
            continue
        d = _decimali(s)
        v = s.values
        first = int(np.argmax(~np.isnan(v)))
        vals = [None if pd.isna(x) else round(float(x), max(d, 1) if g != "a" else 2) for x in v[first:]]
        ser[k] = {"o": first, "v": vals}
        gl = glossario_serie.scheda(k)
        meta.append({"k": k, "n": n, "c": c, "u": u, "on": on, "g": g, "d": d, "r": None if g == "a" else _ref(s), "i": list(gl) if gl else None})
    return {"d": [int(t.value // 86_400_000_000_000) for t in idx], "s": ser, "meta": meta,
            "gruppi": [[a, b] for a, b in GRUPPI], "asof": str(idx[-1].date())}


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


CSS = """
.cfw{margin:8px 0}.cfbar{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}.cfbar button,.cfchips label{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
.cfbar button.on{background:var(--ac);color:#fff;border-color:var(--ac);font-weight:700}.cfchips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.cfchips label{display:flex;align-items:center;gap:6px}.cfchips label.on{border-width:2px;font-weight:700}
.cfchips i{display:inline-block;width:14px;height:4px;border-radius:2px}.cfwrap{position:relative;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:6px 4px}
.cfwrap canvas{width:100%;display:block;touch-action:pan-y;user-select:none;-webkit-user-select:none}.cftip{position:absolute;pointer-events:none;background:var(--card);color:var(--tx);border:1px solid var(--ac);border-radius:10px;padding:8px 10px;font-size:12px;line-height:1.45;box-shadow:0 6px 20px rgba(0,0,0,.4);display:none;z-index:5;min-width:170px}
.cfst{font-size:13px;margin:8px 0}.cfl{font-size:12px;color:var(--mu);display:flex;gap:14px;flex-wrap:wrap;margin:4px 6px}.cfl i{display:inline-block;width:18px;border-top:3px solid;margin-right:5px;vertical-align:middle}.cfl span{display:inline-flex;align-items:center}
.cfchips label{transition:box-shadow .15s,opacity .15s}.cfchips label:not(.on){opacity:.55}.cfchips label.on i{box-shadow:0 0 8px 1px currentColor}
.cfzoom{font-size:13px;margin:4px 0;min-height:30px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.cfzoom button{border:1px solid var(--ac);background:var(--ac);color:#fff;border-radius:99px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer}
.cfchips{display:block}.cfwrap canvas{cursor:crosshair;outline:none}.cfhint{font-size:12px;margin:6px 0}.cfg{margin:6px 0;border:1px solid var(--bd);border-radius:10px;padding:2px 10px;background:var(--card)}.cfg>summary{cursor:pointer;font-weight:700;font-size:13px;padding:6px 0;list-style:none}.cfg>summary::-webkit-details-marker{display:none}.cfg>summary::before{content:"▸ ";color:var(--mu)}.cfg[open]>summary::before{content:"▾ "}.cfn{font-size:11px;font-weight:600;color:var(--ac);margin-left:6px}.cfc{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 8px}.cfzoom button{background:var(--card);color:var(--tx);border-color:var(--bd);padding:4px 10px}.cfzoom button.pri{background:var(--ac);color:#fff;border-color:var(--ac)}
.cfchips{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:8px;align-items:start}.cfchips .cfg{margin:0}
.cfw.cfull{position:fixed;inset:0;z-index:60;background:var(--bg);overflow:auto;padding:10px;margin:0}body.cfno{overflow:hidden}.cfzoom .cfbig{margin-left:auto}
@media(max-width:600px){.cfchips{grid-template-columns:1fr}.cfbar{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:2px}.cfbar b,.cfbar button{flex:0 0 auto;white-space:nowrap}.cfbar button{padding:5px 10px}.cfchips label{padding:4px 9px;font-size:13px}.cfc{gap:5px}.cfg{padding:0 8px}.cfg>summary{padding:8px 0;font-size:14px}.cfhint{font-size:12px;line-height:1.4}.cfwrap{padding:4px 2px;margin:0 -4px;border-radius:10px}.cftip{min-width:0;max-width:62%;font-size:12px;padding:6px 8px}.cfl{font-size:11.5px;gap:8px}.cfzoom{gap:5px}}
"""

JS = r"""
<script>
(function(){
function nf(x,d){return x==null?'n.d.':x.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function init(root){
if(root.dataset.on)return;root.dataset.on='1';root.innerHTML='<p class="mu">Caricamento del grafico…</p>';
var D=null,per=756,lastPer=756,view=null,act={},openG={rischio:true,prev:true},meta={},dragA=null,dragB=null,tstart=null,pan=null,pin=null,hov=null,lastTap=null,COARSE=!!(window.matchMedia&&matchMedia('(pointer:coarse)').matches);
var emb=document.getElementById('armor-cf-data');
function expand(j){var n=j.d.length;j.m={};j.meta.forEach(function(m){j.m[m.k]=m;var o=j.s[m.k];if(o&&o.v){var a=new Array(n);for(var i=0;i<n;i++)a[i]=null;for(var q=0;q<o.v.length;q++)a[o.o+q]=o.v[q];j.s[m.k]=a}})}
function go(j){if(!j.m)expand(j);D=j;D.meta.forEach(function(m){act[m.k]=!!m.on;meta[m.k]=m});build()}
if(window.__ARMOR_CF){setTimeout(function(){go(window.__ARMOR_CF)},0)}else if(emb){setTimeout(function(){go(JSON.parse(emb.textContent))},0)}else{fetch('series/confronto.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){window.__ARMOR_CF=j;go(j)}).catch(function(){root.innerHTML='<p class="mu">Grafico non disponibile (serve la connessione).</p>'})}
var TX=getComputedStyle(document.body).color;
function colr(m){return m.c==='tx'?TX:m.c}
var P=[[63,'3 mesi'],[126,'6 mesi'],[252,'1 anno'],[756,'3 anni'],[1260,'5 anni'],[2520,'10 anni'],[99999,'Tutto (dal 2000)']];
function info(m){var i=m.i,s=[];if(i){s=[['Cos\'è',i[0]],['Cosa rappresenta per chi ha VWCE',i[1]],['Come si legge',i[2]],['Fonte e frequenza',i[3]]]}else s=[['Cos\'è',m.n]];
 if(m.r){var r=m.r,u=m.u||'';function f(v){return v==null?'n.d.':nf(v,m.d)+u}s.push(['Valori di riferimento','ott 2008: '+f(r[0])+' · mar 2020: '+f(r[1])+' · ott 2022: '+f(r[2])+' · ultimo: '+f(r[3])])}
 return {t:m.n,s:s}}
function chip(m){var c=colr(m),on=act[m.k];return '<label data-k="'+m.k+'" data-armorinfo="1" class="'+(on?'on':'')+'" style="'+(on?'border-color:'+c+';box-shadow:0 0 10px '+c+'66,inset 0 0 6px '+c+'33':'')+'"><i style="background:'+c+';color:'+c+'"></i>'+m.n+'<em class="aii" data-armorinfo="1" data-k="'+m.k+'">i</em></label>'}
function build(){
 var h='<div class="cfbar"><b>Periodo:</b>'+P.map(function(p){return '<button data-p="'+p[0]+'"'+(per===p[0]?' class="on"':'')+'>'+p[1]+'</button>'}).join('')+'</div>'+
 '<div class="cfzoom"></div><div class="cfl"></div>'+
 '<div class="cfwrap"><canvas id="cfc" tabindex="0"></canvas><div class="cftip"></div></div>'+
 '<div class="cfhint mu">'+(COARSE?'<b>Tocca</b> il grafico: vedi i valori, e se scorri il dito cambiano subito. <b>Due dita</b>: sposti il grafico. <b>Doppio tocco e trascina</b>: ingrandisci quella zona. <b>Doppio tocco veloce</b>: torna alla vista normale. Tieni premuta una voce per la spiegazione.':'Passa il mouse: data e valori. <b>Trascina</b> per ingrandire un periodo; <b>tasto destro + trascina</b> (o i tasti ← →) per scorrere; <b>doppio clic</b> per tornare alla vista normale. Con «Schermo intero» il grafico occupa tutto lo schermo. Su ogni voce il mouse fermo apre la spiegazione.')+'</div>'+
 '<div class="cfchips">';
 D.gruppi.forEach(function(g){var ms=D.meta.filter(function(m){return m.g===g[0]});if(!ms.length)return;var n=ms.filter(function(m){return act[m.k]}).length;
  h+='<details class="cfg" data-g="'+g[0]+'"'+((openG[g[0]]||g[0]==='a')?' open':'')+'><summary>'+g[1]+(n?' <span class="cfn">'+n+' attive</span>':'')+'</summary><div class="cfc">'+ms.map(chip).join('')+'</div></details>'});
 h+='</div><div class="cfst"></div><div class="mu">Con una sola linea attiva in basso la scala è quella reale; con più linee ognuna è riportata a 0–100% del suo minimo e massimo nel periodo (i valori reali sono nel riquadro). In alto tutte le linee partono da 100 nel primo giorno in cui sono tutte disponibili.</div>';
 root.innerHTML=h;
 root.querySelectorAll('label[data-k],em.aii').forEach(function(el){var m=meta[el.dataset.k];if(m&&window.armorInfo)window.armorInfo.attach(el,function(){return info(m)})});
 draw()}
var cv,ctx,W,H1=190,H2=190,GAP=22,L=40,R=8,T=8,i0,i1,BASE=0,IB=null;
function rng(arr,a,b){var mn=1e18,mx=-1e18;for(var i=a;i<=b;i++){var v=arr[i];if(v==null)continue;if(v<mn)mn=v;if(v>mx)mx=v}return mn>mx?null:[mn,mx]}
function setRange(){var n=D.d.length;if(view){i0=Math.max(0,Math.min(view[0],n-2));i1=Math.max(i0+1,Math.min(view[1],n-1))}else{i1=n-1;i0=Math.max(0,n-per)}}
function xa(i){return L+(i-i0)/Math.max(1,i1-i0)*(W-L-R)}
function draw(){cv=root.querySelector('#cfc');if(!cv)return;setRange();var full=root.classList.contains('cfull'),vw=window.innerWidth;if(full){H1=H2=Math.max(110,Math.floor((window.innerHeight-(vw<600?150:170)-T-GAP-22)/2))}else if(vw>=900){H1=H2=Math.min(300,Math.max(220,Math.floor(window.innerHeight*0.3)))}else if(vw<=600){H1=165;H2=150}else{H1=H2=190}var w=cv.parentNode.clientWidth-8;W=w;var dpr=window.devicePixelRatio||1;var Ht=T+H1+GAP+H2+22;cv.width=w*dpr;cv.height=Ht*dpr;cv.style.height=Ht+'px';ctx=cv.getContext('2d');ctx.scale(dpr,dpr);
 var tx=TX,bd=getComputedStyle(document.body).getPropertyValue('--bd')||'#8884',mu=getComputedStyle(document.body).getPropertyValue('--mu')||'#888';
 function X(i){return xa(i)}
 var ka=D.meta.filter(function(m){return m.g==='a'&&act[m.k]&&D.s[m.k]}),kb=D.meta.filter(function(m){return m.g!=='a'&&act[m.k]&&D.s[m.k]});
 // base comune: primo giorno della finestra in cui tutte le linee in alto esistono
 IB=null;for(var q=i0;q<=i1&&ka.length;q++){var ok=true;for(var z=0;z<ka.length;z++){if(D.s[ka[z].k][q]==null){ok=false;break}}if(ok){IB=q;break}}
 var AR={},lo=1e9,hi=-1e9;
 if(IB!=null)ka.forEach(function(m){var arr=D.s[m.k],b=arr[IB],o=[];for(var i=IB;i<=i1;i++)o[i]=arr[i]!=null?arr[i]/b*100:null;AR[m.k]=o;var r=rng(o,IB,i1);if(r){lo=Math.min(lo,r[0]);hi=Math.max(hi,r[1])}});
 if(lo>hi){lo=90;hi=110}var pad=(hi-lo)*0.06||1;lo-=pad;hi+=pad;
 function Y1(v){return T+(1-(v-lo)/(hi-lo))*H1}
 ctx.font='10px system-ui';ctx.fillStyle=mu;ctx.strokeStyle=bd;ctx.lineWidth=1;
 for(var g=0;g<=4;g++){var v=lo+(hi-lo)*g/4,y=Y1(v);ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillText(nf(v,0),2,y+3)}
 function line(arr,Y,color,lw,from){ctx.beginPath();var st=false;ctx.strokeStyle=color;ctx.lineWidth=lw||1.6;ctx.setLineDash([]);for(var i=from==null?i0:from;i<=i1;i++){var v=arr[i];if(v==null){st=false;continue}var x=X(i),y=Y(v);if(!st){ctx.moveTo(x,y);st=true}else ctx.lineTo(x,y)}ctx.stroke()}
 ka.forEach(function(m){if(AR[m.k])line(AR[m.k],Y1,colr(m),2,IB)});
 var y0=T+H1+GAP;
 function Y2(v,r){return y0+(1-(v-r[0])/Math.max(1e-9,(r[1]-r[0])))*H2}
 var single=kb.length===1,rs={};kb.forEach(function(m){var r=rng(D.s[m.k],i0,i1);if(r){var p=(r[1]-r[0])*0.06||1;rs[m.k]=[r[0]-p,r[1]+p]}});
 ctx.strokeStyle=bd;ctx.fillStyle=mu;
 for(var g2=0;g2<=4;g2++){var y=y0+H2*g2/4;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();var lab=single&&rs[kb[0].k]?nf(rs[kb[0].k][1]-(rs[kb[0].k][1]-rs[kb[0].k][0])*g2/4,kb[0].d):nf(100-25*g2,0)+'%';ctx.fillText(lab,2,y+3)}
 kb.forEach(function(m){var r=rs[m.k];if(!r)return;line(D.s[m.k],function(v){return Y2(v,r)},colr(m),m.k==='armor'?2.6:1.6)});
 ctx.fillStyle=mu;var nt=5;for(var t=0;t<=nt;t++){var i=Math.round(i0+(i1-i0)*t/nt),dt=new Date(D.d[i]*86400000);ctx.textAlign=t===0?'left':(t===nt?'right':'center');ctx.fillText(('0'+(dt.getUTCMonth()+1)).slice(-2)+'/'+dt.getUTCFullYear(),X(i),T+H1+GAP+H2+14)}ctx.textAlign='left';
 ctx.fillStyle=tx;ctx.fillText(ka.length?'Mercati (base 100)':'Accendi almeno una linea di mercato (sotto)',L+4,T+10);ctx.fillText(!kb.length?'Accendi almeno un indicatore (sotto)':(single?kb[0].n:'Indicatori (scala relativa 0–100%)'),L+4,y0+10);
 if(dragA!=null&&dragB!=null){var xa_=X(Math.min(dragA,dragB)),xb_=X(Math.max(dragA,dragB));ctx.fillStyle='rgba(120,160,255,.22)';ctx.fillRect(xa_,T,xb_-xa_,T+H1+GAP+H2-T);ctx.strokeStyle='rgba(120,160,255,.9)';ctx.lineWidth=1;ctx.strokeRect(xa_,T,xb_-xa_,T+H1+GAP+H2-T)}
 if(hov!=null&&hov>=i0&&hov<=i1&&dragA==null&&!pan){var x=X(hov);ctx.strokeStyle=tx;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,T+H1+GAP+H2);ctx.stroke()}
 var lg=root.querySelector('.cfl');if(lg)lg.innerHTML=ka.map(function(m){return '<span><i style="border-color:'+colr(m)+';color:'+colr(m)+'"></i>'+m.n+'</span>'}).join('')+(ka.length&&IB!=null&&IB>i0+5?'<span class="mu">(il confronto parte dal '+fd(IB)+': prima non tutte le linee esistono)</span>':'');
 stats();zbar()}
function fd(i){var d=new Date(D.d[i]*86400000);return d.getUTCDate()+'/'+(d.getUTCMonth()+1)+'/'+d.getUTCFullYear()}
function zbar(){var z=root.querySelector('.cfzoom');if(!z)return;var cust=!!view;root.querySelectorAll('.cfbar button[data-p]').forEach(function(b){b.classList.toggle('on',!cust&&per===+b.dataset.p)});
 z.innerHTML='<button data-sh="-1" title="Indietro nel tempo">◀</button><button data-sh="1" title="Avanti nel tempo">▶</button><span>'+(cust?'Vista: <b>'+fd(i0)+' – '+fd(i1)+'</b> ('+(i1-i0+1)+' sedute)':'<span class="mu">'+(COARSE?'Tocca per leggere i valori':'Trascina per ingrandire')+'</span>')+'</span>'+(cust?'<button data-z="0" class="pri">Azzera zoom</button>':'')+'<button data-fs="1" class="cfbig">'+(root.classList.contains('cfull')?'✕ Chiudi':'⛶ Schermo intero')+'</button>'}
function stats(){var el=root.querySelector('.cfst');if(!el)return;var arm=D.s.armor,sp=D.s.sp500;if(!arm||!sp){el.innerHTML='';return}var hi=[],lo=[];
 for(var i=i0;i<=i1-21;i++){if(arm[i]==null||sp[i]==null||sp[i+21]==null)continue;var f=(sp[i+21]/sp[i]-1)*100;if(arm[i]>=45)hi.push(f);else if(arm[i]<35)lo.push(f)}
 function av(a){return a.length?a.reduce(function(x,y){return x+y},0)/a.length:null}
 el.innerHTML='<b>Nel periodo scelto</b> (descrittivo, non una previsione): dopo i giorni con Indice Armor in zona pericolo (45 o più) l\'S&amp;P 500 ha reso in media <b>'+nf(av(hi),1)+'%</b> nel mese successivo ('+hi.length+' giorni); dopo quelli in zona tranquilla (sotto 35), <b>'+nf(av(lo),1)+'%</b> ('+lo.length+' giorni).'}
function idx(cx){var rc=cv.getBoundingClientRect(),i=Math.round(i0+(cx-rc.left-L)/(W-L-R)*(i1-i0));return Math.max(i0,Math.min(i1,i))}
function tip(clientX){var rc=cv.getBoundingClientRect(),x=clientX-rc.left,i=idx(clientX);hov=i;draw();
 var t=root.querySelector('.cftip'),dt=new Date(D.d[i]*86400000);var h='<b>'+dt.getUTCDate()+'/'+(dt.getUTCMonth()+1)+'/'+dt.getUTCFullYear()+'</b>';
 D.meta.filter(function(m){return act[m.k]&&D.s[m.k]}).forEach(function(m){var v=D.s[m.k][i],e='';if(m.g==='a'&&IB!=null&&v!=null&&D.s[m.k][IB])e=' ('+nf((v/D.s[m.k][IB]-1)*100,1)+'% dalla base)';h+='<br><span style="color:'+colr(m)+'">■</span> '+m.n+': '+nf(v,m.g==='a'?2:m.d)+(m.g==='a'?'':(m.u||''))+e});
 t.innerHTML=h;t.style.display='block';var tw=t.offsetWidth;var lx=x+14;if(lx+tw>rc.width)lx=x-tw-14;t.style.left=Math.max(0,lx)+'px';t.style.top='10px'}
function hideTip(){var t=root.querySelector('.cftip');if(t)t.style.display='none'}
function clampView(a,b){var n=D.d.length,sp=b-a;if(sp<19)sp=19;if(sp>n-1)sp=n-1;if(a<0){a=0}if(a+sp>n-1)a=n-1-sp;return [Math.max(0,a),Math.max(0,a)+sp]}
function shift(k){setRange();var sp=i1-i0,d=Math.round(sp*0.25)*k;view=clampView(i0+d,i1+d);per=0;draw()}
function endSel(){if(dragA==null)return;var a=Math.min(dragA,dragB==null?dragA:dragB),b=Math.max(dragA,dragB==null?dragA:dragB);dragA=dragB=null;if(b-a>=5){view=[a,b];per=0;hov=null;hideTip()}draw()}
function fsw(on){root.classList.toggle('cfull',on);document.body.classList.toggle('cfno',on);hov=null;hideTip();if(on)root.scrollTop=0;draw()}
window.addEventListener('keydown',function(e){if(e.key==='Escape'&&root.classList.contains('cfull'))fsw(false)});
root.addEventListener('dblclick',function(e){if(e.target.id==='cfc'){dragA=dragB=null;view=null;per=lastPer;hov=null;hideTip();build()}});
root.addEventListener('click',function(e){var fb=e.target.closest('button[data-fs]');if(fb){fsw(!root.classList.contains('cfull'));return}var zb=e.target.closest('button[data-z]');if(zb){view=null;per=lastPer;hov=null;build();return}
 var sb=e.target.closest('button[data-sh]');if(sb){shift(+sb.dataset.sh);return}
 var b=e.target.closest('button[data-p]');if(b){per=lastPer=+b.dataset.p;view=null;hov=null;build();return}
 var l=e.target.closest('label[data-k]');if(l&&!e.target.closest('.aii')){var k=l.dataset.k;act[k]=!act[k];build();return}});
root.addEventListener('toggle',function(e){var d=e.target;if(d.classList&&d.classList.contains('cfg'))openG[d.dataset.g]=d.open},true);
root.addEventListener('contextmenu',function(e){if(e.target.id==='cfc')e.preventDefault()});
root.addEventListener('mousedown',function(e){if(e.target.id!=='cfc')return;if(e.button===0){dragA=idx(e.clientX);dragB=dragA;e.preventDefault();cv.focus()}else if(e.button===2){setRange();pan={x:e.clientX,a:i0,b:i1};cv.style.cursor='grabbing';e.preventDefault()}});
root.addEventListener('mousemove',function(e){if(pan){var ppi=(W-L-R)/(pan.b-pan.a),d=Math.round((e.clientX-pan.x)/ppi);view=clampView(pan.a-d,pan.b-d);per=0;hov=null;hideTip();draw();return}
 if(dragA!=null){dragB=idx(e.clientX);draw();return}if(e.target.id==='cfc')tip(e.clientX)});
window.addEventListener('mouseup',function(){if(!D)return;if(pan){pan=null;if(cv)cv.style.cursor=''}if(dragA!=null)endSel()});
root.addEventListener('mouseleave',function(){hov=null;hideTip();if(D&&!pan&&dragA==null)draw()});
root.addEventListener('keydown',function(e){if(e.target.id==='cfc'&&(e.key==='ArrowLeft'||e.key==='ArrowRight')){shift(e.key==='ArrowLeft'?-0.4:0.4);e.preventDefault()}});
function two(e){var a=e.touches[0],b=e.touches[1];return {x:(a.clientX+b.clientX)/2,d:Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)||1}}
function pdef(e){if(e.cancelable)e.preventDefault()}
root.addEventListener('touchstart',function(e){if(e.target.id!=='cfc')return;
 if(e.touches.length===2){setRange();var t=two(e),rc=cv.getBoundingClientRect();pin={x:t.x,d:t.d,a:i0,b:i1,c:i0+(t.x-rc.left-L)/(W-L-R)*(i1-i0)};dragA=dragB=null;tstart=null;lastTap=null;return}
 if(e.touches.length===1){var q=e.touches[0],now=Date.now(),dbl=!!lastTap&&now-lastTap.t<330&&Math.abs(q.clientX-lastTap.x)<40&&Math.abs(q.clientY-lastTap.y)<40;
  tstart={x:q.clientX,y:q.clientY,t:now,moved:false,dbl:dbl,dir:null};
  if(dbl){dragA=idx(q.clientX);dragB=dragA;hov=null;hideTip();draw()}else tip(q.clientX)}},{passive:true});
root.addEventListener('touchmove',function(e){if(e.target.id!=='cfc'&&!pin&&!tstart)return;
 if(pin&&e.touches.length===2){pdef(e);var t=two(e),rc=cv.getBoundingClientRect(),sp0=pin.b-pin.a,sp=Math.max(19,Math.min(D.d.length-1,Math.round(sp0*pin.d/t.d))),fr=(t.x-rc.left-L)/(W-L-R),a=Math.round(pin.c-fr*sp);view=clampView(a,a+sp);per=0;hov=null;hideTip();draw();return}
 if(!tstart||!e.touches[0])return;var q=e.touches[0],dx=q.clientX-tstart.x,dy=q.clientY-tstart.y;
 if(!tstart.moved&&Math.abs(dx)+Math.abs(dy)>8){tstart.moved=true;tstart.dir=(tstart.dbl||Math.abs(dx)>=Math.abs(dy)*0.7)?'h':'v'}
 if(!tstart.moved||tstart.dir==='v')return;
 pdef(e);if(tstart.dbl){dragB=idx(q.clientX);draw()}else tip(q.clientX)},{passive:false});
root.addEventListener('touchend',function(e){if(pin){if(e.touches.length<2)pin=null;tstart=null;lastTap=null;pdef(e);return}
 if(!tstart)return;var s=tstart;tstart=null;
 if(s.dbl){pdef(e);lastTap=null;if(s.moved){endSel()}else{dragA=dragB=null;view=null;per=lastPer;hov=null;hideTip();build()}return}
 if(!s.moved){lastTap={t:Date.now(),x:s.x,y:s.y}}else lastTap=null;
 if(e.target.id==='cfc')pdef(e)},{passive:false});
root.addEventListener('touchcancel',function(){tstart=null;pin=null;dragA=dragB=null;lastTap=null});
document.addEventListener('touchstart',function(e){if(D&&hov!=null&&!root.contains(e.target)){hov=null;hideTip();draw()}},{passive:true});
window.addEventListener('resize',function(){if(D&&root.querySelector('#cfc'))draw()});
}
window.armorConfronto=function(scope){(scope||document).querySelectorAll('.cfw[data-cf]').forEach(init)};
window.armorConfronto();
})();
</script>
"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-cf-data'>{data_json}</script>" if data_json else ""
    return f"{emb}<div class='cfw' data-cf='1'></div>{JS}"
