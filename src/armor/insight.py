"""Coerenza dei segnali, episodi simili animati, fasce di errore reali delle previsioni."""
import html as _h
import json
import math

import numpy as np
import pandas as pd

from .config import CALIBRATION, HORIZONS, HZ_LABEL, PRIMARY

GROUPS = {
    "Paura e opzioni": ["vix", "vterm", "vvix", "skew", "move", "pc_oi"],
    "Credito e liquidità": ["hy_oas", "baa10y", "nfci", "stlfsi"],
    "Tassi e obbligazioni": ["t10y3m", "t10y2y", "dgs10", "real10y"],
    "Valutazioni": ["cape_m", "pe_m", "ps_m"],
    "Sentiment e ampiezza": ["aaii_spread", "fear_greed", "breadth200"],
    "Prezzi e tendenza": ["dd252", "rv21", "ma200"],
    "Economia": ["sahm", "icsa"],
}
SC = {"ok": 0, "wa": 1, "ba": 2}


def coherence(items: list[dict]) -> dict:
    """Per ogni gruppo di indicatori: tranquillo / misto / teso. Poi cerca i gruppi in disaccordo."""
    by = {i["key"]: i for i in items}
    res = []
    for g, keys in GROUPS.items():
        v = [SC[by[k]["light"]] for k in keys if k in by and by[k]["light"] in SC]
        if not v:
            continue
        m = float(np.mean(v))
        res.append({"gruppo": g, "score": m, "n": len(v), "stato": "calmo" if m < 0.5 else ("teso" if m >= 1.2 else "misto"),
                    "rossi": [by[k]["name"] for k in keys if k in by and by[k]["light"] == "ba"]})
    calm = [r for r in res if r["stato"] == "calmo"]
    tense = [r for r in res if r["stato"] == "teso"]
    disc = bool(calm and tense)
    notes = []
    names = {r["gruppo"]: r["stato"] for r in res}
    if names.get("Valutazioni") == "teso" and names.get("Paura e opzioni") == "calmo":
        notes.append("Mercato caro ma tranquillo: c'è poco margine di sicurezza se arriva una sorpresa negativa. Non è un segnale di calo imminente.")
    if names.get("Paura e opzioni") == "teso" and names.get("Credito e liquidità") == "calmo":
        notes.append("Paura nelle opzioni ma credito sereno: spesso è nervosismo di breve periodo, finché il credito non si irrigidisce.")
    if names.get("Credito e liquidità") == "teso":
        notes.append("Il credito è sotto stress: è uno dei segnali più seri, perché tocca il finanziamento delle aziende.")
    if names.get("Sentiment e ampiezza") == "teso" and names.get("Prezzi e tendenza") == "calmo":
        notes.append("Prezzi alti ma ampiezza o sentiment fragili: il rialzo regge su pochi titoli o su troppo ottimismo.")
    if names.get("Tassi e obbligazioni") == "teso" and names.get("Valutazioni") == "teso":
        notes.append("Tassi alti e valutazioni care insieme: combinazione che storicamente pesa sulle azioni nel medio periodo.")
    return {"gruppi": res, "discordanti": disc, "calmi": [r["gruppo"] for r in calm], "tesi": [r["gruppo"] for r in tense], "note": notes}


def coherence_html(c: dict) -> str:
    rows = "".join(f"<tr><td>{_h.escape(r['gruppo'])}</td><td><span class='badge {'ok' if r['stato'] == 'calmo' else ('bad' if r['stato'] == 'teso' else 'warn')}'>{r['stato']}</span></td>"
                   f"<td>{_h.escape(', '.join(r['rossi'])) if r['rossi'] else '—'}</td></tr>" for r in c["gruppi"])
    head = ("<div class='banner'><b>Segnali discordanti.</b> " + f"{', '.join(c['calmi'])} dicono «tranquillo»; {', '.join(c['tesi'])} dicono «attenzione». "
            "Quando gli indicatori non concordano il quadro è meno chiaro: conviene guardare quale gruppo si muove per primo.</div>") if c["discordanti"] else \
        "<p>I gruppi di indicatori concordano abbastanza tra loro: il quadro è coerente.</p>"
    notes = "".join(f"<li>{_h.escape(n)}</li>" for n in c["note"])
    return (head + f"<table><tr><th>Gruppo</th><th>Stato</th><th>Indicatori in rosso</th></tr>{rows}</table>"
            + (f"<ul>{notes}</ul>" if notes else "") +
            "<p class='mu'>Ogni gruppo riassume i semafori dei suoi indicatori: calmo = in media verdi, teso = in media rossi. Le letture sono generali, non statistiche.</p>")


# ---------------------------------------------------------------- episodi simili animati
def episode_paths(p: pd.Series, sims: list[dict], days: int = 126) -> dict:
    out = []
    for s in sims[:10]:
        i = p.index.get_loc(pd.Timestamp(s["date"]))
        seg = p.iloc[i:i + days + 1]
        out.append({"d": s["date"], "v": [round(float(x / seg.iloc[0] * 100 - 100), 2) for x in seg]})
    n = max((len(o["v"]) for o in out), default=0)
    med = [round(float(np.median([o["v"][k] for o in out if k < len(o["v"])])), 2) for k in range(n)] if out else []
    return {"paths": out, "median": med, "days": days}


def episodes_html(data: dict) -> str:
    if not data["paths"]:
        return "<p class='mu'>Nessun episodio simile disponibile.</p>"
    return ("<div class='card'><div class='epbar'><button class='chip on' id='epplay'>▶ Avvia</button><button class='chip' id='epreset'>↺ Da capo</button>"
            "<span class='mu' id='eplab'></span></div><canvas id='epcanvas' style='width:100%;height:300px'></canvas>"
            "<div class='mu' id='eplegend'></div></div>"
            "<div class='explain'><p><b>Cosa vedi.</b> Le linee sottili sono i 10 momenti del passato più simili a oggi (per volatilità, distanza dai massimi e andamento recente). "
            "Ognuna parte da 0 nel giorno di allora e mostra come è andato l'S&amp;P 500 nei 6 mesi successivi (circa 126 giorni di borsa). La linea spessa è la mediana. "
            "Premi «Avvia» per vederle crescere giorno dopo giorno. Sono esempi, non previsioni: se le linee vanno in direzioni opposte significa che da situazioni simili sono nati futuri molto diversi.</p></div>"
            f"<script>window.EPIS={json.dumps(data)};</script>")


EP_JS = r"""
(function(){var cv=document.getElementById('epcanvas');if(!cv||!window.EPIS)return;var D=window.EPIS,k=0,run=false,raf=null,btn=document.getElementById('epplay');
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function draw(){var dpr=window.devicePixelRatio||1,w=cv.clientWidth,h=cv.clientHeight;if(!w)return;cv.width=w*dpr;cv.height=h*dpr;var g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
var all=[];D.paths.forEach(function(p){p.v.forEach(function(x){all.push(x)})});var lo=Math.min.apply(null,all.concat([0])),hi=Math.max.apply(null,all.concat([0])),pad=(hi-lo)*.08;lo-=pad;hi+=pad;var L=44,R=8,T=8,B=22;
var X=function(i){return L+i/D.days*(w-L-R)},Y=function(v){return T+(hi-v)/(hi-lo)*(h-T-B)};
g.font='11px system-ui';g.fillStyle=css('--mu');g.strokeStyle=css('--bd');g.textAlign='right';
for(var q=0;q<=4;q++){var v=lo+(hi-lo)*q/4,y=Y(v);g.beginPath();g.moveTo(L,y);g.lineTo(w-R,y);g.stroke();g.fillText((v>=0?'+':'')+v.toFixed(0)+'%',L-4,y+4)}
g.textAlign='center';[0,21,63,126].forEach(function(d){g.fillText(d===0?'oggi':(d===21?'1 mese':d===63?'3 mesi':'6 mesi'),X(d),h-6)});
g.strokeStyle=css('--mu');g.setLineDash([4,4]);g.beginPath();g.moveTo(L,Y(0));g.lineTo(w-R,Y(0));g.stroke();g.setLineDash([]);
var pal=['#2a6fdb','#c0392b','#1f8f55','#d9822b','#7a4fd1','#17a2b8','#e83e8c','#6c757d','#8d6e63','#009688'];
D.paths.forEach(function(p,j){g.strokeStyle=pal[j%10]+'99';g.lineWidth=1.3;g.beginPath();for(var i=0;i<=Math.min(k,p.v.length-1);i++){i?g.lineTo(X(i),Y(p.v[i])):g.moveTo(X(i),Y(p.v[i]))}g.stroke()});
g.strokeStyle=css('--tx');g.lineWidth=3;g.beginPath();for(var m=0;m<=Math.min(k,D.median.length-1);m++){m?g.lineTo(X(m),Y(D.median[m])):g.moveTo(X(m),Y(D.median[m]))}g.stroke();
var lab=document.getElementById('eplab');if(lab)lab.textContent=' giorno '+Math.min(k,D.days)+' · mediana '+(D.median[Math.min(k,D.median.length-1)]>=0?'+':'')+D.median[Math.min(k,D.median.length-1)].toFixed(1)+'%'}
function step(){if(!run)return;k+=1;draw();if(k>=D.days){run=false;btn.textContent='▶ Rivedi';return}raf=requestAnimationFrame(function(){setTimeout(step,40)})}
btn.onclick=function(){if(k>=D.days)k=0;run=!run;btn.textContent=run?'⏸ Pausa':'▶ Avvia';if(run)step()};
document.getElementById('epreset').onclick=function(){run=false;k=0;btn.textContent='▶ Avvia';draw()};
k=D.days;draw();window.addEventListener('resize',draw);document.addEventListener('tabshown',draw);
var lg=document.getElementById('eplegend');if(lg)lg.textContent='Episodi: '+D.paths.map(function(p){return p.d.slice(0,7)}).join(' · ')})();
"""


# ---------------------------------------------------------------- fasce di errore reali
def wilson(k: float, n: float, z: float = 1.645) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def honest(pred: dict) -> list[dict]:
    """Per ogni orizzonte: nelle previsioni passate vicine a quella di oggi, quante volte è accaduto davvero il calo."""
    try:
        cal = pd.read_csv(CALIBRATION)
    except Exception:  # noqa: BLE001
        return []
    rows = []
    for hz in HORIZONS:
        if hz not in pred:
            continue
        thr = PRIMARY[hz]
        c = cal[cal.target == f"{hz}_{thr}"].sort_values("prev")
        if c.empty:
            continue
        p = pred[hz]["p"][thr]
        # le due classi di previsione più vicine: si usa una media pesata
        c = c.assign(d=(c.prev - p).abs()).nsmallest(2, "d")
        n = float(c.n.sum())
        real = float((c.real * c.n).sum() / n)
        lo, hi = wilson(real * n / 4, n / 4)  # i giorni vicini si sovrappongono: si conta un quarto dei casi (stima prudente)
        rows.append({"hz": hz, "p": p, "real": real, "lo": lo, "hi": hi, "prev_bin": float((c.prev * c.n).sum() / n), "n": int(n), "thr": thr})
    return rows


def honest_html(rows: list[dict]) -> str:
    if not rows:
        return "<p class='mu'>Fasce di errore non disponibili: servono i test sul passato (convalida mensile).</p>"
    pc = lambda x: f"{x * 100:.0f}%" if x >= 0.1 else f"{x * 100:.1f}%".replace(".", ",")
    tr = "".join(f"<tr><td>{HZ_LABEL[r['hz']]} (calo ≥{r['thr']}%)</td><td><b>{pc(r['p'])}</b></td>"
                 f"<td>{pc(r['prev_bin'])}</td><td><b>{pc(r['real'])}</b></td><td>{pc(r['lo'])} – {pc(r['hi'])}</td></tr>" for r in rows)
    return (f"<table><tr><th>Periodo</th><th>Stima di oggi</th><th>Stime passate simili (media)</th><th>Cosa è successo davvero</th><th>Fascia plausibile (90%)</th></tr>{tr}</table>"
            "<p class='mu'>Lettura: nei test sul passato (senza «barare», usando a ogni data solo ciò che si sapeva allora), quando Armor stimava un valore simile a quello di oggi, "
            "il calo si è verificato nella percentuale indicata. La fascia è prudente perché i giorni vicini sono molto simili tra loro. "
            "Se la fascia è larga o la stima passata e quella reale differiscono molto, fidati meno del numero esatto.</p>")
