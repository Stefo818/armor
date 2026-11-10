"""Grafica del Super Armor Index: blocco compatto in «Oggi» + schede che si aprono al tocco (sintesi, storico, metodo, e una scheda di dettaglio per ogni pilastro)."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import store
from .config import DATA
from .super_armor import (COL_PIL, ECO, FASCE, NOMI, PESI, VIXW, _n, anello, calcola, ciambella, cause, colore, confronti, eco_componenti, fascia, freccia, gauge, prova,
                          putcall_rischio, storia, titolo, vix_componenti)

E = _h.escape
BANDE = [f[1] for f in FASCE]
MID = [12, 32, 47, 62, 85]
ORDINE = ("previsione", "armor", "vix", "fondi", "economia")
COLONNA = {"previsione": "previsione", "armor": "armor", "vix": "vix", "economia": "economia"}


def _leggi(nome):
    try:
        return json.loads((DATA / nome).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def barra(r: float, scala: bool = True) -> str:
    r = min(max(float(r), 0), 1)
    col = colore(1 + 99 * r)
    return (f"<div class='sai-b2'><i style='width:{max(r * 100, 2):.0f}%;background:{col}'></i></div>"
            + ("<div class='sai-sc'><span>nessun rischio</span><span>rischio pieno</span></div>" if scala else ""))


def _riga(n, v, r, s, sub="") -> str:
    return (f"<div class='sai-cr'><div class='sai-cn'><b>{E(n)}</b><span class='sai-cv' style='color:{colore(1 + 99 * r) if r is not None else 'var(--mu)'}'>{E(v)}</span></div>"
            + (barra(r, False) if r is not None else "") + f"<div class='sai-t2'>{s}</div>{sub}</div>")


# ---------------- dettagli dei pilastri ----------------
ECO_INFO = {
    "sahm": ("Disoccupazione in aumento (regola di Sahm)", "Di quanto la disoccupazione è salita rispetto al suo minimo dell'ultimo anno. Da 0,5 punti in su, in passato, è iniziata una recessione.", lambda x: f"{x:.1f} punti", "Rischio da 0 (nessun aumento) a pieno a 1 punto di aumento."),
    "icsa": ("Richieste di sussidio di disoccupazione", "Quante persone chiedono ogni settimana il sussidio dopo aver perso il lavoro, rispetto al livello più basso dell'ultimo anno.", lambda x: f"{(x - 1) * 100:+.0f}% sul minimo", "Rischio da 0 (+5%) a pieno (+35% sul minimo)."),
    "indpro": ("Produzione industriale", "Quanto producono fabbriche, miniere e centrali elettriche, rispetto a un anno fa.", lambda x: f"{x:+.1f}% in un anno", "Rischio da 0 (+3% o più) a pieno (-3% o meno)."),
    "cfnai": ("Attività economica nazionale (indice di Chicago)", "Un riassunto di 85 dati mensili calcolato dalla banca centrale di Chicago: sotto zero l'economia cresce meno della norma (media degli ultimi 3 mesi).", lambda x: f"{x:+.2f}", "Rischio da 0 (+0,1 o più) a pieno (-0,8 o meno)."),
    "t10y3m": ("Curva dei tassi (10 anni contro 3 mesi)", "Differenza tra il tasso dei titoli di Stato a 10 anni e a 3 mesi. Se è negativa («curva invertita») in passato ha spesso anticipato le recessioni.", lambda x: f"{x:+.2f} punti", "Rischio da 0 (+1 o più) a pieno (-0,8 o meno)."),
    "payems": ("Posti di lavoro", "Di quanto sono cresciuti i lavoratori dipendenti rispetto a un anno fa.", lambda x: f"{x:+.1f}% in un anno", "Rischio da 0 (+1,8% o più) a pieno (-0,5% o meno)."),
    "retail": ("Vendite al dettaglio", "Quanto spendono le famiglie nei negozi rispetto a un anno fa (senza togliere l'inflazione).", lambda x: f"{x:+.1f}% in un anno", "Rischio da 0 (+5% o più) a pieno (-1% o meno)."),
    "umcsent": ("Fiducia dei consumatori", "Sondaggio dell'Università del Michigan: quanto le famiglie sono ottimiste sul proprio futuro economico (più basso = più pessimismo).", lambda x: f"{x:.0f} punti", "Rischio da 0 (95 o più) a pieno (50 o meno)."),
}


def det_previsione(o: dict) -> dict:
    from . import previsione_ui, semaforo_rischio
    d = _leggi("semaforo_rischio_oggi.json") or {}
    tab = _leggi("semaforo_rischio_tabella.json") or {}
    return {"comp": previsione_ui.html(d, tab, semaforo_rischio.variazione()),
            "come": ("Questo pilastro risponde a una domanda: <b>quanto è probabile che l'S&amp;P 500 (le 500 maggiori aziende americane) perda almeno il 5% entro un mese, o almeno il 10% entro tre mesi?</b> "
                     "Due modelli statistici stimano questa probabilità, e ognuna viene confrontata con quella abituale, cioè quante volte in media, dal 1990, quel calo è davvero arrivato. "
                     "Il <b>modello base</b> usa prezzi, tassi e credito. Il <b>modello con la paura</b> considera anche quanto il mercato è nervoso oggi. "
                     "Si fa la media dei due e dei due periodi, e si guarda quanto il valore di oggi è alto rispetto a tutti i giorni dal 1990: un punteggio di 82 vuol dire che oggi il rischio stimato è più alto dell'81% dei giorni."),
            "glossario": [("S&P 500", "indice delle 500 maggiori aziende quotate negli Stati Uniti"), ("Probabilità abituale", "quante volte, in media dal 1990, è arrivato quel calo"),
                          ("1×", "rischio come al solito; 2× è il doppio del solito, 0,5× la metà"), ("Indice della paura (VIX)", "misura quanto gli investitori si aspettano oscillazioni forti nel prossimo mese"),
                          ("Semaforo", "il colore che riassume quanto il rischio è sopra o sotto il solito")]}


def det_armor(o: dict, aix: dict | None) -> dict:
    if not aix:
        return {"comp": "", "come": "", "glossario": []}
    righe = ""
    for g in sorted([x for x in aix["groups"] if x.get("score") is not None], key=lambda x: -x["score"]):
        r = g["score"] if g["score"] <= 1 else g["score"] / 100
        voci = "".join(f"<li><span>{E(i['name'])}</span><b>{'' if i.get('value') is None else _fmt(i['value'])}</b><em style='color:{colore(1 + 99 * i['score'])}'>{i['score'] * 100:.0f}</em></li>"
                       for i in sorted(g["items"], key=lambda i: -i["score"])[:3])
        righe += (f"<div class='sai-cr'><div class='sai-cn'><b>{E(g['name'])}</b><span class='sai-cv' style='color:{colore(1 + 99 * r)}'>{r * 100:.0f}/100 · pesa {g['weight']:.0f}%</span></div>{barra(r, False)}"
                  f"<details class='sai-dt'><summary>Gli indicatori che pesano di più</summary><ul class='sai-ul'>{voci}</ul></details></div>")
    return {"comp": "<p class='sai-t2'>L'Indice Armor riunisce 8 famiglie di indicatori. Questo è il punteggio di rischio di ognuna (più la barra è piena, più c'è tensione).</p>" + righe,
            "come": ("L'Indice Armor raccoglie circa 30 indicatori in 8 famiglie: paura dei mercati, credito, tassi, valutazioni, tendenza dei prezzi, sentimento degli investitori, economia reale e modello statistico. "
                     "Ogni indicatore diventa un punteggio di rischio tra 0 e 1: il 60% viene da soglie fisse (per esempio «VIX sopra 30 = stress») e il 40% da quanto il valore è alto rispetto agli ultimi 10 anni. "
                     "Poi si fa la media dei punteggi di ogni famiglia e la media pesata delle famiglie, con pesi fissi. Il risultato va da 1 a 100."),
            "glossario": [("VIX", "indice della paura: quanto costa proteggersi dai cali del mese prossimo"), ("CAPE", "rapporto tra prezzi e utili medi degli ultimi 10 anni: più è alto, più i titoli sono cari"), ("Spread", "il rendimento in più che chiedono le aziende rischiose rispetto allo Stato")]}


def _fmt(x) -> str:
    try:
        x = float(x)
    except Exception:  # noqa: BLE001
        return str(x)
    return f"{x:,.0f}".replace(",", ".") if abs(x) >= 1000 else f"{x:.2f}".replace(".", ",").rstrip("0").rstrip(",")


def det_vix(idx, o) -> dict:
    C = vix_componenti(idx)
    rk, pct = putcall_rischio()
    v = float(store.load("vix").iloc[-1])
    righe = [("Indice della paura (VIX)", f"{_n(v)}", float(C["vix"].iloc[0]) if "vix" in C else None,
              "Quanto costa proteggersi dai cali del prossimo mese. Sotto 16 c'è calma, sopra 20 nervosismo, sopra 30 stress.", f"Peso {VIXW['vix'] * 100:.0f}%.")]
    if "curva" in C and pd.notna(C["curva"].iloc[0]):
        vt = float(store.load("vix3m").iloc[-1]) / v
        righe.append(("Curva della paura (3 mesi su 1 mese)", _n(vt, 2), float(C["curva"].iloc[0]),
                      "Confronta la paura a 3 mesi con quella di oggi. Di solito è sopra 1; sotto 1 («curva capovolta») la paura di oggi supera quella futura: succede nei momenti di stress.", f"Peso {VIXW['curva'] * 100:.0f}%."))
    for k, nome, sid, sp, fmt in (("vvix", "VVIX (nervosità della paura)", "vvix", "Misura quanto il VIX stesso è instabile. Sopra 100 ci si aspetta scosse.", 0), ("skew", "SKEW (protezione dai crolli)", "skew", "Quanto costa assicurarsi contro un crollo improvviso. Sopra 135 i professionisti si coprono più del solito.", 0)):
        if k in C and pd.notna(C[k].iloc[0]):
            righe.append((nome, _n(float(store.load(sid).iloc[-1]), 0), float(C[k].iloc[0]), sp, f"Peso {VIXW[k] * 100:.0f}%."))
    if rk is not None:
        righe.append(("Put/call sulle opzioni SPY", f"{pct:.0f}° percentile", rk, "Rapporto tra opzioni put (protezioni o scommesse al ribasso) e call (scommesse al rialzo): più è alto rispetto al solito, più protezioni.", f"Peso {VIXW['putcall'] * 100:.0f}%."))
    else:
        righe.append(("Put/call sulle opzioni SPY", "in raccolta", None, "Servono almeno 60 giorni di archivio: per ora non pesa sul valore e gli altri pesi si ridistribuiscono.", f"Peso previsto {VIXW['putcall'] * 100:.0f}%."))
    return {"comp": "".join(_riga(n, v_, r, s + " " + pe) for n, v_, r, s, pe in righe),
            "come": ("Questo pilastro guarda quanto gli operatori professionisti pagano per proteggersi dai ribassi, cioè il prezzo delle <b>opzioni</b> (contratti che permettono di assicurarsi contro un calo). "
                     "Ogni misura diventa un rischio tra 0 e 100% con soglie fisse (per esempio VIX: 13 = 0%, 20 = 35%, 30 = 80%, 45 = 100%). Poi si fa una media pesata. "
                     "Attenzione: l'Indice Armor contiene già in parte la paura dei mercati, quindi questo pilastro pesa solo il 20%."),
            "glossario": [("VIX", "indice della paura dell'S&P 500 basato sul prezzo delle opzioni a 30 giorni"), ("VVIX", "quanto oscilla il VIX stesso"), ("SKEW", "costo delle protezioni contro i crolli rispetto ai cali normali"),
                          ("Opzione put / call", "contratto che guadagna se il mercato scende (put) o sale (call)"), ("SPY", "il fondo che replica l'S&P 500, su cui si scambiano moltissime opzioni")]}


def det_economia(idx) -> dict:
    R, W = eco_componenti(idx)
    r = R.iloc[0].dropna()
    righe = ""
    for k in sorted(r.index, key=lambda k: -r[k]):
        n, s, f, soglia = ECO_INFO[k]
        righe += _riga(n, f(float(W[k].iloc[0])), float(r[k]), s + " " + soglia)
    return {"comp": "<p class='sai-t2'>Otto misure dell'economia reale. Ognuna ha una barra di rischio: più è piena, più quella misura indica difficoltà.</p>" + righe,
            "come": ("Questo pilastro misura la salute di fondo dell'economia americana, non il rischio di calo dei prossimi giorni. Prende 8 misure ufficiali (lavoro, produzione, vendite, fiducia, curva dei tassi), "
                     "trasforma ciascuna in un rischio tra 0 e 100% con soglie fisse e fa la media. I dati escono con settimane di ritardo e li usiamo solo dal giorno in cui sono stati davvero pubblicati. "
                     "Nei test dal 2000 queste misure descrivono bene le recessioni ma non anticipano i cali di mercato di breve periodo: per questo l'economia è tenuta separata dalle altre nella lettura «mercato contro economia»."),
            "glossario": [("Recessione", "periodo in cui l'economia si restringe per diversi mesi"), ("Curva invertita", "quando i tassi a breve superano quelli a lungo: spesso anticipa le recessioni"), ("Regola di Sahm", "segnale di recessione basato sull'aumento della disoccupazione")]}


def det_fondi(o) -> dict:
    d = _leggi("grandi_fondi.json") or {}
    sg = d.get("segnali") or {}
    righe = ""
    for k, s in sg.items():
        pct = s.get("percentile")
        v = (s.get("prova") or {}).get("verdetto", "n.d.")
        verd = "Ha anticipato i cali in entrambe le metà della storia" if str(v).startswith("dimostrato") else ("Non ha dimostrato di anticipare i cali" if v == "nessun segnale dimostrato" else "Storia ancora troppo corta per dirlo")
        righe += _riga(s["nome"], "n.d." if pct is None else f"{pct:.0f}° percentile", None if pct is None else pct / 100,
                       f"Dato del {E(s['ultimo_dato'])}. Livello {E(s['stato'])} rispetto agli ultimi 5 anni (100° = il più alto). <b>{E(verd)}.</b>")
    if not righe:
        righe = "<p class='sai-t2'>I dati sono in arrivo: compaiono dopo i primi aggiornamenti.</p>"
    t = d.get("tensione") or {}
    top = ""
    if t.get("score") is not None:
        om = (o.get("ombra") or {}) if isinstance(o, dict) else {}
        conf = (f"<p class='sai-t2'><b>Confronto in prova:</b> con i grandi fondi al 10% il Super Armor Index sarebbe <b>{om['sai']:.0f}</b> ({om['delta']:+.1f} punti rispetto all'ufficiale). "
                "Lo confrontiamo ogni giorno per decidere nelle prossime settimane se validarlo.</p>".replace(".", ",") if om.get("sai") is not None else "")
        top = (f"<div class='sai-two'><div class='sai-bar'><span>Tensione dei grandi fondi<br><small>0 = tutto nella norma, 100 = tutto agli estremi</small></span><b>{t['score']:.0f}</b></div></div>"
               "<p class='sai-t2'>Non dice se il mercato scenderà o salirà: dice quanto i grandi fondi sono lontani dal loro comportamento abituale.</p>" + conf)
    top += "<p class='sai-t2'><a href='#fondi' data-go='fondi' style='color:var(--ac);font-weight:700'>Apri la pagina completa «Grandi fondi» ›</a></p>"
    return {"comp": top + "<p class='sai-t2'>Qui non si misura il «rischio»: si guarda dove si trova ogni segnale rispetto agli ultimi 5 anni. Le barre mostrano il percentile, non un pericolo.</p>" + righe,
            "come": ("Questo pilastro osserva cosa fanno i grandi operatori: i fondi che scommettono con la leva, i gestori di patrimoni, la liquidità parcheggiata nei fondi monetari, le posizioni dichiarate alla SEC (l'autorità di controllo dei mercati americani), gli acquisti dei dirigenti delle aziende. "
                     "Ogni segnale viene confrontato con gli ultimi 5 anni. Poi si verifica, con una regola scritta in anticipo, se in passato valori alti o bassi hanno anticipato i cali. "
                     "<b>Finché nessun segnale supera la prova, il pilastro pesa 0%</b> e non cambia il valore del Super Armor Index; se uno la supera, entra con il 10%."),
            "glossario": [("Futures", "contratti per comprare o vendere l'S&P 500 a una data futura"), ("13F", "elenco trimestrale delle azioni possedute dai grandi fondi, depositato alla SEC"), ("Form 4", "comunicazione con cui i dirigenti dichiarano acquisti e vendite di azioni della propria azienda"),
                          ("Schedule 13D", "avviso di chi supera il 5% di un'azienda con intenzioni attive"), ("Fondi monetari", "fondi che parcheggiano denaro in strumenti sicuri a breve: tanta liquidità = tanti soldi fermi")]}


# ---------------- analisi testuale ----------------
def analisi(k: str, pil: dict, c: dict, st, o: dict) -> str:
    s = pil.get("score")
    if s is None:
        return "<p class='sai-an'>Questo pilastro è in osservazione e non pesa ancora sul valore del Super Armor Index.</p>"
    perc = None
    if st is not None and k in st and st[k].notna().sum() > 100:
        perc = float((st[k].dropna() < s).mean() * 100)
    txt = f"Oggi questo pilastro segna <b>{s:.0f} su 100</b>, cioè «{FASCE[fascia(s)][1].lower()}»."
    if perc is not None:
        txt += f" È più alto del {perc:.0f}% dei giorni dal 2000."
    conf = []
    for nome, lab in (("settimana", "una settimana fa"), ("mese", "un mese fa")):
        x = c.get(nome, {}).get("pil", {}).get(k)
        if x is not None:
            sim, par, _ = freccia(s - x, 3)
            conf.append(f"{lab} era {x:.0f} ({sim} {s - x:+.0f}, {par})")
    if conf:
        txt += " Rispetto al passato: " + "; ".join(conf) + "."
    q = o["quote"].get(k)
    if q:
        txt += f" Oggi pesa per il {q * 100:.0f}% sul valore finale."
    return f"<p class='sai-an'>{txt}</p>".replace("+-", "-")


# ---------------- storico ----------------
def episodi(p: pd.Series, st: pd.DataFrame, v: float, tol: float = 4.0, quanti: int = 8) -> dict:
    s = st["sai"]
    sim = s[(s >= v - tol) & (s <= v + tol)]
    sim = sim[sim.index < p.index[-1] - pd.Timedelta(days=45)]
    if sim.empty:
        return {"righe": [], "n": 0}
    eps, ultimo = [], None
    for d in sim.index:
        if ultimo is None or (d - ultimo).days > 60:
            eps.append(d)
        ultimo = d
    righe = []
    for d in eps:
        if d not in p.index:
            continue
        i = p.index.get_loc(d)
        if i + 63 >= len(p):
            continue
        w1, w3 = p.iloc[i + 1: i + 22].values / p.iloc[i] - 1, p.iloc[i + 1: i + 64].values / p.iloc[i] - 1
        righe.append({"d": d, "sai": float(s.loc[d]), "dd1": float(w1.min()), "r1": float(w1[-1]), "dd3": float(w3.min()), "r3": float(w3[-1])})
    if not righe:
        return {"righe": [], "n": 0}
    return {"righe": righe[-quanti:], "n": len(righe), "med_dd1": float(np.median([r["dd1"] for r in righe])), "med_dd3": float(np.median([r["dd3"] for r in righe])),
            "quota5": float(np.mean([r["dd1"] <= -0.05 for r in righe])), "quota10": float(np.mean([r["dd3"] <= -0.10 for r in righe]))}


def dati_grafico(st: pd.DataFrame, oggi: dict, p: pd.Series) -> dict:
    s = st.copy()
    r = {"sai": oggi["sai"], **{k: oggi["pilastri"][k]["score"] for k in COLONNA if oggi["pilastri"].get(k, {}).get("score") is not None}}
    s.loc[pd.Timestamp(oggi["data"]), list(r)] = list(r.values())
    s = s.sort_index()
    z = pd.concat([s.iloc[:-400].iloc[::5], s.iloc[-400:]])
    dd = (p / p.cummax() - 1).reindex(z.index, method="ffill") * 100
    nn = lambda x: None if pd.isna(x) else round(float(x), 1)
    return {"d": [str(i.date()) for i in z.index], "v": [nn(x) for x in z["sai"]], "pr": [nn(x) for x in z.get("previsione", [])], "ar": [nn(x) for x in z.get("armor", [])],
            "vx": [nn(x) for x in z.get("vix", [])], "ec": [nn(x) for x in z.get("economia", [])], "dd": [nn(x) for x in dd], "b": [lim for lim, *_x in FASCE[:-1]], "c": [colore(m) for m in MID], "n": BANDE}


def _mercato_economia(o: dict) -> str:
    m, e = o["mercato"], o["economia"]
    if m is None:
        return ""
    def sca(x, titolo, sott):
        return (f"<div class='sai-me'><div class='sai-met'><b>{titolo}</b><span style='color:{colore(x)}'>{x:.0f}</span></div><div class='sai-scale'><i style='left:{min(max(x, 1), 100)}%;border-color:{colore(x)}'></i></div>"
                f"<div class='sai-sc'><span>1 sano</span><span>100 pericoloso</span></div><p class='sai-t2'>{sott}</p></div>")
    out = sca(m, "Mercato (giorni e settimane)", "È la media di <b>previsione, Indice Armor e paura e opzioni</b>. Sono segnali veloci: cambiano ogni giorno e dicono quanto il mercato è nervoso e quanto è alto il rischio di un calo nelle prossime settimane.")
    if e is not None:
        out += sca(e, "Economia (mesi)", "È il pilastro <b>economia reale</b>: otto misure ufficiali su lavoro, produzione, vendite e fiducia. Sono dati lenti, aggiornati una volta al mese, e dicono se l'economia di fondo sta bene o male.")
        if m >= 45 and e < 45:
            f = "Il nervosismo è nei prezzi e nei modelli, mentre l'economia di fondo regge. Descrive un mercato teso ma senza (per ora) un problema nell'economia reale."
        elif m >= 45:
            f = "Sia il mercato sia l'economia mostrano segnali di difficoltà: è la combinazione più delicata."
        elif e >= 45:
            f = "Il mercato è calmo ma l'economia di fondo è in affanno: i suoi problemi non sono ancora nei prezzi."
        else:
            f = "Mercato calmo ed economia in buona salute: nessun segnale di allarme."
        out += f"<div class='sai-lett'><b>Come leggerli insieme.</b> {f}</div>"
    return out


def html(aix: dict | None, p: pd.Series) -> str:
    o = calcola(aix, p)
    if not o:
        return ""
    st = storia()
    c = confronti(o, st)
    v = o["sai"]
    nome_f = FASCE[fascia(v)][2]
    idx = pd.DatetimeIndex([p.index[-1]])
    pil = o["pilastri"]
    det = {"previsione": det_previsione(o), "armor": det_armor(o, aix), "vix": det_vix(idx, o), "economia": det_economia(idx), "fondi": det_fondi(o)}
    ie = c.get("ieri")
    chip = ""
    if ie:
        s_, _w, k_ = freccia(ie["delta"])
        chip = f"<span class='sai-ch {k_}'>{s_} {ie['delta']:+.0f} rispetto a ieri</span>".replace("+-", "-")
    tit = titolo(o, c)
    tiles = "".join(f"<div class='sai-tile' data-saip='{k}'>{anello((pil.get(k) or {}).get('score'))}<span>{E(NOMI[k])}</span>" + ("" if o["pesi"].get(k) else ("<em>peso 0 · in prova</em>" if k == "fondi" else "<em>peso 0</em>")) + "</div>" for k in ORDINE)
    # --- sintesi
    righe = ""
    for k in ("previsione", "armor", "vix", "economia", "fondi"):
        pl = pil.get(k)
        if not pl:
            continue
        pe = o["pesi"].get(k)
        righe += (f"<div class='sai-r' data-saip='{k}'>{anello(pl.get('score'), 42)}<div class='sai-rt'><b>{E(NOMI[k])}</b> <span class='sai-w'>{'pesa ' + format(pe * 100, '.0f') + '%' if pe else 'non pesa ancora'}</span>"
                  f"<div class='sai-t2'>{E(pl['testo'])}</div></div><span class='sai-go'>›</span></div>")
    leg = "".join(f"<div><i style='background:{COL_PIL[k]}'></i>{E(NOMI[k])} {q * 100:.0f}%</div>" for k, q in sorted(o["quote"].items(), key=lambda kv: -kv[1]))
    conc = {"concordi": "I pilastri sono concordi: raccontano la stessa storia.", "abbastanza concordi": "I pilastri sono abbastanza concordi.", "discordi": "Attenzione: i pilastri non sono d'accordo tra loro, e il numero unico nasconde opinioni diverse."}[o["concordanza"]]
    sintesi = (f"<div class='sai-hd'><div class='sai-gb'>{gauge(v)}</div><div><div class='sai-lab' style='color:{colore(v)}'>{E(nome_f)}</div><div class='sai-sub2'>{E(tit)}</div>{chip}</div></div>"
               f"<div class='sai-ca'>{E(cause(o, c))}</div><h4>I cinque grandi indicatori <small>(tocca per il dettaglio)</small></h4>{righe}"
               f"<h4>Cosa pesa sul valore</h4><div class='sai-mix'><div class='sai-don'>{ciambella(o['quote'])}</div><div><div class='sai-leg'>{leg}</div><p class='sai-t2'>Ogni spicchio è il contributo del pilastro: peso fisso × punteggio di oggi.</p></div></div>"
               f"<h4>Mercato contro economia</h4>{_mercato_economia(o)}<p class='sai-t2'>{E(conc)}</p>")
    # --- confronti e storico
    conf = f"<tr><td>Oggi</td><td><b style='color:{colore(v)}'>{v:.0f}</b></td><td></td><td>{E(nome_f)}</td></tr>"
    for k, lab in (("ieri", "Ieri"), ("settimana", "Una settimana fa"), ("mese", "Un mese fa")):
        if k in c:
            s_, w_, kk = freccia(c[k]["delta"])
            conf += f"<tr><td>{lab}</td><td>{c[k]['sai']:.0f}</td><td class='{kk}'>{s_} {c[k]['delta']:+.0f}</td><td class='{kk}'>{w_}</td></tr>".replace("+-", "-")
    perc = float((st["sai"] < v).mean() * 100) if st is not None else None
    pr = prova()
    aff = ""
    if pr:
        tr = "".join(f"<tr><td><span class='sai-dot' style='background:{colore(MID[i])}'></span>{E(f['fascia'])}</td><td>{f['quota'] * 100:.0f}%</td>"
                     f"<td>{'n.d.' if f['1m_5'] is None else format(f['1m_5'] * 100, '.0f') + '%'}</td><td>{'n.d.' if f['3m_10'] is None else format(f['3m_10'] * 100, '.0f') + '%'}</td></tr>" for i, f in enumerate(pr["fasce"]))
        a1 = pr["auc"].get("sai", {}).get("1m_5|tutta")
        aff = (f"<h4>Quanto è affidabile</h4><p class='sai-t2'>Dal 2000, dopo ogni fascia, quanto spesso l'S&amp;P 500 ha perso almeno il 5% entro un mese e almeno il 10% entro tre mesi (in media: {pr['fasce'][0]['1m_5_tutte'] * 100:.0f}% e {pr['fasce'][0]['3m_10_tutte'] * 100:.0f}%).</p>"
               f"<div class='sai-tw'><table class='sai-tb'><tr><th>Fascia</th><th>Quanti giorni</th><th>Calo ≥5% in 1 mese</th><th>Calo ≥10% in 3 mesi</th></tr>{tr}</table></div>"
               f"<p class='sai-t2'>{'Più sale il numero, più cali sono arrivati: le fasce sono in ordine. ' if pr.get('ordine') else 'Attenzione: le fasce non sono perfettamente in ordine. '}"
               + (f"Capacità di distinguere i giorni a rischio: {a1 * 100:.0f} su 100 (50 = come tirare a sorte, 100 = perfetta). È simile a quella dei singoli pilastri: il numero unico non li batte, ma li riassume in modo più stabile. " if a1 else "")
               + "La storia è ricostruita con le regole di oggi: non è una promessa per il futuro.</p>")
    ep = episodi(p, st, v) if st is not None else {"righe": [], "n": 0}
    eptab = ""
    if ep["righe"]:
        tr = "".join(f"<tr><td>{r['d'].strftime('%d/%m/%Y')}</td><td>{r['sai']:.0f}</td><td>{r['dd1'] * 100:.0f}%</td><td>{r['r1'] * 100:+.0f}%</td><td>{r['dd3'] * 100:.0f}%</td><td>{r['r3'] * 100:+.0f}%</td></tr>" for r in reversed(ep["righe"]))
        eptab = (f"<h4>Quando il numero era simile a oggi</h4><p class='sai-t2'>Le volte, dal 2000, in cui il Super Armor Index era entro 4 punti da {v:.0f} (una per episodio) e cosa ha fatto l'S&amp;P 500 dopo. "
                 f"In {ep['quota5'] * 100:.0f}% degli {ep['n']} episodi c'è stato un calo di almeno il 5% entro un mese, in {ep['quota10'] * 100:.0f}% di almeno il 10% entro tre mesi.</p>"
                 f"<div class='sai-tw'><table class='sai-tb'><tr><th>Data</th><th>Indice</th><th>Peggior calo 1 mese</th><th>Dopo 1 mese</th><th>Peggior calo 3 mesi</th><th>Dopo 3 mesi</th></tr>{tr}</table></div>")
    storico = (f"<table class='sai-tb'><tr><th></th><th>Valore</th><th>Variazione</th><th></th></tr>{conf}</table>"
               + (f"<p class='sai-t2'>Oggi è più alto del <b>{perc:.0f}%</b> dei giorni dal 2000.</p>" if perc is not None else "")
               + "<div class='sai-rg' data-rg='1'><button data-r='30'>1 mese</button><button data-r='90' class='on'>3 mesi</button><button data-r='180'>6 mesi</button><button data-r='365'>1 anno</button><button data-r='1825'>5 anni</button><button data-r='99999'>Tutto</button></div>"
               "<div class='sai-chw'><svg id='saich' viewBox='0 0 640 330' preserveAspectRatio='none'></svg><div class='sai-tip' id='saitip'></div></div>"
               "<p class='sai-t2'>Tocca o scorri il dito sul grafico per vedere il valore di ogni giorno. In basso, la linea mostra quanto l'S&amp;P 500 era sotto il suo massimo.</p>"
               "<div class='sai-tg' id='saitg'><button data-l='pr' style='--lc:" + COL_PIL['previsione'] + "'>Previsione</button><button data-l='ar' style='--lc:" + COL_PIL['armor'] + "'>Indice Armor</button><button data-l='vx' style='--lc:" + COL_PIL['vix'] + "'>Paura e opzioni</button><button data-l='ec' style='--lc:" + COL_PIL['economia'] + "'>Economia reale</button></div>"
               "<div class='sai-stats' id='saist'></div><div id='saifs'></div>" + eptab + aff)
    # --- metodo
    pesi_tab = "".join(f"<div class='sai-pw'><i style='background:{COL_PIL[k]};width:{PESI[k] * 3}%'></i><span><b>{E(NOMI[k])}</b> pesa {PESI[k]:.0f}%</span></div>" for k in ("previsione", "armor", "economia", "vix")) + \
        f"<div class='sai-pw'><i style='background:{COL_PIL['fondi']};width:3%'></i><span><b>{E(NOMI['fondi'])}</b> pesa 0% (10% se supera la prova)</span></div>"
    bande = "".join(f"<div class='sai-bd'><i style='background:{colore(MID[i])}'></i><b>{E(FASCE[i][2])}</b><span>{lim0}–{min(FASCE[i][0], 100)}</span></div>" for i, lim0 in enumerate([1, 25, 40, 55, 70]))
    metodo = ("<h4>Che cos'è</h4><p class='sai-t2'>Un solo numero da 1 a 100 che riassume cinque grandi indicatori. <b>1 = mercato sano, 100 = mercato pericoloso e instabile.</b> Non è un consiglio di acquisto o di vendita: dice solo quanto, oggi, i segnali sono preoccupanti.</p>"
              f"<h4>Come si calcola</h4><p class='sai-t2'>Ogni pilastro ha un punteggio da 1 a 100. Il Super Armor Index è la media pesata dei pilastri. I pesi sono fissi e scritti prima di guardare i risultati, per non adattarli al passato:</p>{pesi_tab}"
              "<p class='sai-t2'>Se un pilastro manca, gli altri si dividono il suo peso. L'Indice Armor contiene già in parte la paura dei mercati: per questo «paura e opzioni» pesa meno.</p>"
              f"<h4>Le cinque fasce</h4><div class='sai-bds'>{bande}</div>"
              "<h4>Cosa ho verificato</h4><p class='sai-t2'>Dal 2000, più sale il numero, più spesso sono arrivati cali dell'S&amp;P 500. Il numero unico distingue i giorni a rischio quanto i migliori pilastri da soli, non meglio: il suo vantaggio è riassumere tutto in modo più stabile. "
              "L'economia reale descrive la salute di fondo ma non anticipa i cali di breve periodo: per questo si legge a parte («mercato contro economia»).</p>"
              "<h4>Limiti</h4><p class='sai-t2'>La storia prima di oggi è ricostruita con le regole attuali. I cali di mercato improvvisi, causati da eventi imprevedibili, non si possono prevedere. Non è una consulenza finanziaria.</p>")
    # --- schede dei pilastri
    pane_p = ""
    for k in ORDINE:
        pl = pil.get(k) or {}
        sc = pl.get("score")
        d = det[k]
        pe = o["pesi"].get(k)
        gl = "".join(f"<li><b>{E(a)}</b>: {E(b)}.</li>" for a, b in d["glossario"])
        mini = (f"<h4>Come è andato nel tempo</h4><div class='sai-rg' data-rgm='{k}'><button data-r='90'>3 mesi</button><button data-r='365' class='on'>1 anno</button><button data-r='1825'>5 anni</button><button data-r='99999'>Tutto</button></div>"
                f"<svg class='sai-mini' data-k='{k}' viewBox='0 0 640 150' preserveAspectRatio='none'></svg><div class='sai-t2 sai-mi' data-ki='{k}'></div>") if k in COLONNA else ""
        pane_p += (f"<div class='sai-pane' data-pane='p-{k}'><button class='sai-back' data-saiback='1'>‹ Indietro</button>"
                   f"<div class='sai-ph'>{anello(sc, 64)}<div><h3>{E(NOMI[k])}</h3><div class='sai-lab' style='color:{colore(sc) if sc is not None else 'var(--mu)'}'>{E(FASCE[fascia(sc)][2]) if sc is not None else 'In osservazione'}</div>"
                   f"<span class='sai-w'>{'pesa ' + format(pe * 100, '.0f') + '% sul valore finale' if pe else 'non pesa ancora sul valore finale'}</span></div></div>"
                   f"{analisi(k, pl, c, st, o)}<div class='sai-t2'>{E(pl.get('testo', ''))}</div>"
                   f"<h4>Gli elementi che contano di più</h4>{d['comp']}{mini}<h4>Come è calcolato</h4><p class='sai-t2'>{d['come']}</p><h4>Parole difficili</h4><ul class='sai-gl'>{gl}</ul></div>")
    dati = json.dumps(dati_grafico(st, o, p), separators=(",", ":")) if st is not None else "null"
    return (f"{CSS}<section class='sai' style='--sc:{colore(v)}' id='sai'><div class='sai-top'><div class='sai-g' data-saim='sum' title='Tocca per aprire'>{gauge(v)}</div>"
            f"<div class='sai-tx' data-saim='sum'><div class='sai-k'>Super Armor Index</div><div class='sai-lab' style='color:{colore(v)}'>{E(nome_f)} {chip}</div>"
            f"<div class='sai-head'>{E(tit)} <span class='sai-chev'>›</span></div></div></div><div class='sai-tiles'>{tiles}</div>"
            f"<div class='sai-mod' id='saimod'><div class='sai-card'><button class='sai-x' data-saix='1' aria-label='Chiudi'>×</button>"
            f"<div class='sai-tabs' id='saitabs'><button data-saim='sum' class='on'>Sintesi</button><button data-saim='sto'>Storico</button><button data-saim='met'>Come funziona</button></div>"
            f"<div class='sai-pane on' data-pane='sum'>{sintesi}</div><div class='sai-pane' data-pane='sto'>{storico}</div><div class='sai-pane' data-pane='met'>{metodo}</div>{pane_p}</div></div>"
            f"<script type='application/json' id='sai-data'>{dati}</script>{JS}</section>")


CSS = """<style>
.sai{background:linear-gradient(140deg,var(--card),var(--bg));border:1px solid var(--bd);border-radius:20px;padding:10px 12px 8px;margin:0 0 12px;box-shadow:0 8px 28px -12px var(--sc),0 0 0 1px color-mix(in srgb,var(--sc) 22%,transparent) inset}
.sai h3,.sai h4{margin:0}.sai h4{margin:16px 0 6px;font-size:14.5px}.sai h4 small{font-weight:500;color:var(--mu);font-size:11.5px}
.sai-top{display:flex;gap:6px;align-items:center}.sai-g{flex:0 0 138px;cursor:pointer}.sai-gs{width:100%;display:block;overflow:visible}.sai-num{font-size:36px;font-weight:800}.sai-sub{font-size:9.5px;fill:var(--mu);font-weight:700}
.sai-tx{flex:1;min-width:0;cursor:pointer}.sai-k{font-size:10.5px;font-weight:800;letter-spacing:.7px;text-transform:uppercase;color:var(--mu)}.sai-lab{font-weight:800;font-size:15px;line-height:1.2;margin:1px 0 3px}
.sai-ch{font-size:11px;font-weight:700;padding:1px 7px;border-radius:99px;margin-left:4px;white-space:nowrap;background:var(--bg);display:inline-block}.sai-up{color:var(--bad)}.sai-dn{color:var(--ok)}.sai-fl{color:var(--mu)}
.sai-head{font-size:13px;line-height:1.3;font-weight:600}.sai-chev{color:var(--ac);font-weight:800;font-size:16px}
.sai-tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:2px;margin-top:4px}.sai-tile{display:flex;flex-direction:column;align-items:center;gap:1px;font-size:10px;line-height:1.1;text-align:center;color:var(--mu);font-weight:700;cursor:pointer;border-radius:12px;padding:2px 0;transition:background .15s}.sai-tile:active,.sai-tile:hover{background:var(--bg)}.sai-tile em{font-style:normal;font-size:9px;opacity:.75}
.sai-mod{display:none;position:fixed;inset:0;background:rgba(8,12,20,.66);backdrop-filter:blur(3px);z-index:40;align-items:flex-end;justify-content:center;padding:0}.sai-mod.show{display:flex}
.sai-card{background:var(--card);color:var(--tx);border-radius:22px 22px 0 0;max-width:680px;width:100%;height:92vh;overflow:auto;padding:14px 16px 28px;position:relative;border:1px solid var(--bd);animation:saiup .28s ease-out;overscroll-behavior:contain}
@media(min-width:720px){.sai-mod{align-items:center;padding:20px}.sai-card{height:auto;max-height:90vh;border-radius:22px}}
@keyframes saiup{from{transform:translateY(40px);opacity:.4}to{transform:none;opacity:1}}
.sai-x{position:absolute;right:12px;top:8px;border:0;background:var(--bg);color:var(--mu);font-size:22px;cursor:pointer;line-height:1;width:32px;height:32px;border-radius:50%;z-index:3}
.sai-tabs{display:flex;gap:6px;margin:0 40px 10px 0;position:sticky;top:-14px;background:var(--card);padding:8px 0;z-index:2}.sai-tabs button{flex:1;border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;padding:6px 4px;font:inherit;font-size:13px;font-weight:700;cursor:pointer}.sai-tabs button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.sai-pane{display:none}.sai-pane.on{display:block;animation:saif .22s}@keyframes saif{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.sai-hd{display:flex;gap:8px;align-items:center;background:linear-gradient(135deg,var(--bg),transparent);border-radius:16px;padding:6px}.sai-gb{flex:0 0 150px}.sai-sub2{font-size:13.5px;line-height:1.35;font-weight:600;margin-bottom:4px}
.sai-ca{font-weight:700;font-size:13px;margin:8px 0}
.sai-r{display:flex;gap:10px;align-items:center;background:var(--bg);border:1px solid var(--bd);border-radius:14px;padding:8px 10px;margin:6px 0;cursor:pointer}.sai-r:active{transform:scale(.99)}.sai-r>svg{flex:0 0 42px}.sai-rt{flex:1;min-width:0}.sai-go{font-size:24px;color:var(--mu)}
.sai-w{font-size:11px;color:var(--mu);font-weight:600;margin-left:4px}.sai-t2{font-size:12.5px;line-height:1.42;color:var(--mu);margin:3px 0}
.sai-an{font-size:14px;line-height:1.5;margin:10px 0;background:var(--bg);border-left:4px solid var(--ac);border-radius:10px;padding:8px 12px}
.sai-ph{display:flex;gap:12px;align-items:center;margin:6px 0}.sai-ph h3{font-size:19px}
.sai-back{border:0;background:none;color:var(--ac);font:inherit;font-weight:700;cursor:pointer;padding:2px 0;margin-bottom:2px}
.sai-mix{display:flex;gap:12px;align-items:center;margin:6px 0}.sai-don{flex:0 0 96px}.sai-leg div{font-size:12.5px;margin:3px 0;display:flex;align-items:center;gap:6px}.sai-leg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.sai-two{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0}.sai-bar{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:6px 10px;display:flex;justify-content:space-between;align-items:center;font-size:12px}.sai-bar b{font-size:22px}.sai-bar small{color:var(--mu)}
.sai-me{background:var(--bg);border:1px solid var(--bd);border-radius:14px;padding:10px 12px;margin:8px 0}.sai-met{display:flex;justify-content:space-between;align-items:baseline}.sai-met b{font-size:14px}.sai-met span{font-size:28px;font-weight:800}
.sai-scale{position:relative;height:10px;border-radius:99px;background:linear-gradient(90deg,hsl(125,74%,45%),hsl(92,74%,45%) 25%,hsl(52,74%,45%) 45%,hsl(24,74%,45%) 62%,hsl(0,74%,45%));margin:8px 0 3px}.sai-scale i{position:absolute;top:-4px;width:16px;height:16px;margin-left:-8px;border-radius:50%;background:var(--card);border:4px solid}
.sai-sc{display:flex;justify-content:space-between;font-size:10px;color:var(--mu)}.sai-lett{background:var(--bg);border-left:4px solid var(--ac);border-radius:10px;padding:8px 12px;font-size:13px;line-height:1.45;margin:8px 0}
.sai-cr{border-top:1px solid var(--bd);padding:9px 0}.sai-cn{display:flex;justify-content:space-between;gap:8px;align-items:baseline;font-size:13.5px}.sai-cv{font-weight:800;white-space:nowrap}
.sai-b2{height:8px;border-radius:99px;background:var(--bd);overflow:hidden;margin:5px 0 3px}.sai-b2 i{display:block;height:100%;border-radius:99px}
.sai-pb{display:grid;grid-template-columns:118px 1fr 40px;gap:6px;align-items:center;font-size:12px;margin:3px 0}.sai-pb>div{height:9px;background:var(--bd);border-radius:99px;overflow:hidden}.sai-pb i{display:block;height:100%;border-radius:99px}.sai-pb b{text-align:right}
.sai-dt{margin:4px 0 0;font-size:12px}.sai-dt summary{cursor:pointer;color:var(--ac);font-weight:600}.sai-ul{list-style:none;padding:0;margin:4px 0}.sai-ul li{display:flex;gap:8px;justify-content:space-between;font-size:12px;padding:2px 0}.sai-ul li span{flex:1}.sai-ul li em{font-style:normal;font-weight:800;min-width:24px;text-align:right}
.sai-gl{padding-left:18px;margin:4px 0;font-size:12.5px;color:var(--mu);line-height:1.5}
.sai-tw{overflow-x:auto}.sai-tb{width:100%;border-collapse:collapse;font-size:12.5px}.sai-tb th{font-size:10.5px;color:var(--mu);text-align:left;padding:3px 4px;vertical-align:bottom}.sai-tb td{padding:5px 4px;border-top:1px solid var(--bd);white-space:nowrap}.sai-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.sai-rg{display:flex;gap:5px;margin:10px 0 6px;flex-wrap:wrap}.sai-rg button{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;padding:3px 11px;font:inherit;font-size:12px;cursor:pointer}.sai-rg button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.sai-chw{position:relative;touch-action:pan-y}#saich{width:100%;height:auto;aspect-ratio:640/330;display:block;background:var(--bg);border-radius:12px}.sai-mini{width:100%;height:120px;display:block;background:var(--bg);border-radius:10px}
.sai-tip{position:absolute;top:6px;display:none;pointer-events:none;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:7px 10px;font-size:12px;box-shadow:0 6px 18px rgba(0,0,0,.28);min-width:150px;z-index:2}.sai-tip b{font-size:20px}.sai-tip div{display:flex;justify-content:space-between;gap:10px}.sai-tip i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
.sai-tg{display:flex;gap:5px;flex-wrap:wrap;margin:6px 0}.sai-tg button{border:1.5px solid var(--lc);background:transparent;color:var(--tx);border-radius:99px;padding:3px 10px;font:inherit;font-size:12px;cursor:pointer;opacity:.6}.sai-tg button.on{background:var(--lc);color:#fff;opacity:1}
.sai-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:8px 0}.sai-stats div{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:6px 8px;font-size:11px;color:var(--mu)}.sai-stats b{display:block;font-size:17px;color:var(--tx)}
.sai-fs{display:flex;height:16px;border-radius:99px;overflow:hidden;margin:6px 0 3px}.sai-fs i{display:block}.sai-pw{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}.sai-pw i{display:block;height:12px;border-radius:99px;min-width:6px}
.sai-bds{display:grid;gap:5px}.sai-bd{display:flex;align-items:center;gap:8px;font-size:13px}.sai-bd i{width:14px;height:14px;border-radius:4px}.sai-bd span{margin-left:auto;color:var(--mu)}
</style>"""

JS = r"""<script>(function(){var S=document.getElementById('sai');if(!S||S.dataset.on)return;S.dataset.on=1;
var M=document.getElementById('saimod'),D=null,card=M.querySelector('.sai-card'),cur='sum',IT=function(s){var d=new Date(s);return d.toLocaleDateString('it-IT',{day:'numeric',month:'short',year:'numeric'})};
try{D=JSON.parse(document.getElementById('sai-data').textContent)}catch(e){}
var T=D?D.d.map(function(s){return Date.parse(s)}):[],COL={pr:'hsl(215,85%,62%)',ar:'hsl(265,75%,68%)',vx:'hsl(35,90%,55%)',ec:'hsl(165,60%,45%)'},NM={pr:'Previsione',ar:'Indice Armor',vx:'Paura e opzioni',ec:'Economia reale'};
var RANGE=90,ON={};
function band(v){for(var i=0;i<D.b.length;i++)if(v<D.b[i])return i;return D.b.length}
function show(name){cur=name;M.querySelectorAll('.sai-pane').forEach(function(p){p.classList.toggle('on',p.dataset.pane===name)});
var main=(name==='sum'||name==='sto'||name==='met');document.getElementById('saitabs').style.display=main?'flex':'none';
M.querySelectorAll('#saitabs button').forEach(function(b){b.classList.toggle('on',b.dataset.saim===name)});card.scrollTop=0;
if(name==='sto')chart();else if(name.indexOf('p-')===0)mini(name.slice(2),365)}
function open(name){M.classList.add('show');document.body.style.overflow='hidden';show(name)}
function close(){M.classList.remove('show');document.body.style.overflow=''}
function sel(n){var s=0;if(n>=99999)return 0;var cut=T[T.length-1]-n*864e5;while(s<T.length-1&&T[s]<cut)s++;return s}
function ser(k){return k==='v'?D.v:D[k]}
function chart(){var svg=document.getElementById('saich');if(!svg||!D)return;var s=sel(RANGE),N=T.length,W=640,PL=26,PR=6,X0=T[s],X1=T[N-1],xs=function(t){return PL+(t-X0)/(X1-X0||1)*(W-PL-PR)};
var Y=function(v){return 10+(100-v)*1.9},o='',B=D.b.concat([100]);
for(var j=0;j<B.length;j++){var a=Y(B[j]),b=Y(j?B[j-1]:0);o+="<rect x='"+PL+"' y='"+a+"' width='"+(W-PL-PR)+"' height='"+(b-a)+"' fill='"+D.c[j]+"' opacity='.17'/><text x='"+(W-PR-3)+"' y='"+(a+10)+"' font-size='8' fill='var(--mu)' text-anchor='end'>"+D.n[j]+"</text>"}
[0,25,40,55,70,100].forEach(function(g){o+="<line x1='"+PL+"' x2='"+(W-PR)+"' y1='"+Y(g)+"' y2='"+Y(g)+"' stroke='var(--bd)' stroke-width='.6'/><text x='2' y='"+(Y(g)+3)+"' font-size='8' fill='var(--mu)'>"+g+"</text>"});
Object.keys(ON).forEach(function(k){if(!ON[k])return;var p=[];for(var i=s;i<N;i++)if(D[k][i]!=null)p.push(xs(T[i]).toFixed(1)+','+Y(D[k][i]).toFixed(1));o+="<polyline fill='none' stroke='"+COL[k]+"' stroke-width='1.4' stroke-dasharray='4 2' opacity='.95' points='"+p.join(' ')+"'/>"});
var pts=[];for(var i=s;i<N;i++)pts.push(xs(T[i]).toFixed(1)+','+Y(D.v[i]).toFixed(1));
o+="<polyline fill='none' stroke='var(--tx)' stroke-width='2.4' stroke-linejoin='round' points='"+pts.join(' ')+"'/>";
var le=D.v[N-1];o+="<circle cx='"+xs(T[N-1])+"' cy='"+Y(le)+"' r='4.5' fill='"+D.c[band(le)]+"' stroke='var(--card)' stroke-width='2'/>";
var mn=0;for(var i=s;i<N;i++)if(D.dd[i]!=null&&D.dd[i]<mn)mn=D.dd[i];mn=Math.min(mn,-5);var Z=function(v){return 232+(-v/-mn)*70};
o+="<text x='2' y='226' font-size='8.5' fill='var(--mu)' font-weight='700'>S&amp;P 500: quanto sotto il suo massimo</text><line x1='"+PL+"' x2='"+(W-PR)+"' y1='232' y2='232' stroke='var(--bd)' stroke-width='.8'/>";
var d1=[],dp=[];for(var i=s;i<N;i++)if(D.dd[i]!=null){d1.push(xs(T[i]).toFixed(1)+','+Z(D.dd[i]).toFixed(1))}
if(d1.length){o+="<polygon fill='hsl(0,70%,55%)' opacity='.28' points='"+xs(T[s]).toFixed(1)+",232 "+d1.join(' ')+" "+xs(T[N-1]).toFixed(1)+",232'/><polyline fill='none' stroke='hsl(0,70%,58%)' stroke-width='1.3' points='"+d1.join(' ')+"'/>"}
o+="<text x='"+(PL+2)+"' y='"+(Z(mn)-2)+"' font-size='8.5' fill='hsl(0,70%,60%)'>"+Math.round(mn)+"%</text>";
var nt=4;for(var q=0;q<=nt;q++){var t=X0+(X1-X0)*q/nt;o+="<text x='"+xs(t)+"' y='322' font-size='9' fill='var(--mu)' text-anchor='"+(q==0?'start':q==nt?'end':'middle')+"'>"+new Date(t).toLocaleDateString('it-IT',{month:'short',year:'2-digit'})+"</text>"}
o+="<g id='saicr' style='display:none'><line id='saicl' y1='10' y2='300' stroke='var(--tx)' stroke-width='1' stroke-dasharray='3 3'/><circle id='saicd' r='5' fill='var(--card)' stroke='var(--tx)' stroke-width='2'/></g>";
svg.innerHTML=o;svg._s=s;svg._xs=xs;svg._Y=Y;stats(s)}
function stats(s){var N=T.length,v=D.v.slice(s),d=D.d.slice(s),sum=0,mn=1e9,mx=-1,im=0,ix=0,cnt=[0,0,0,0,0];
for(var i=0;i<v.length;i++){sum+=v[i];if(v[i]<mn){mn=v[i];im=i}if(v[i]>mx){mx=v[i];ix=i}cnt[band(v[i])]++}
var ch=v[v.length-1]-v[0],f=function(x){return Math.round(x)};
document.getElementById('saist').innerHTML="<div>Media<b>"+f(sum/v.length)+"</b></div><div>Minimo<b>"+f(mn)+"</b>"+IT(d[im])+"</div><div>Massimo<b>"+f(mx)+"</b>"+IT(d[ix])+"</div><div>Variazione<b style='color:var(--"+(ch>1.5?'bad':ch<-1.5?'ok':'mu')+")'>"+(ch>0?'+':'')+f(ch)+"</b>nel periodo</div>";
var tot=v.length,h="<h4>Quanto tempo in ogni fascia</h4><div class='sai-fs'>";for(var j=0;j<5;j++)h+="<i style='width:"+(cnt[j]/tot*100)+"%;background:"+D.c[j]+"'></i>";h+="</div><div class='sai-t2'>";
for(var j=0;j<5;j++)if(cnt[j])h+="<span style='color:"+D.c[j]+"'>●</span> "+D.n[j]+" "+Math.round(cnt[j]/tot*100)+"% &nbsp; ";document.getElementById('saifs').innerHTML=h+"</div>"}
function tip(ev){var svg=document.getElementById('saich');if(!svg||!svg._xs)return;var r=svg.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width*640,t=svg._xs.length?null:null;
var s=svg._s,N=T.length,best=s,bd=1e18;for(var i=s;i<N;i++){var dx=Math.abs(svg._xs(T[i])-x);if(dx<bd){bd=dx;best=i}}
var cx=svg._xs(T[best]),g=document.getElementById('saicr'),l=document.getElementById('saicl'),c=document.getElementById('saicd');g.style.display='';l.setAttribute('x1',cx);l.setAttribute('x2',cx);c.setAttribute('cx',cx);c.setAttribute('cy',svg._Y(D.v[best]));
var b=band(D.v[best]),tp=document.getElementById('saitip'),h="<div style='color:var(--mu)'>"+IT(D.d[best])+"</div><div><b style='color:"+D.c[b]+"'>"+Math.round(D.v[best])+"</b><span style='align-self:end'>"+D.n[b]+"</span></div>";
Object.keys(ON).forEach(function(k){if(ON[k]&&D[k][best]!=null)h+="<div><span><i style='background:"+COL[k]+"'></i>"+NM[k]+"</span><b style='font-size:12px'>"+Math.round(D[k][best])+"</b></div>"});
if(D.dd[best]!=null)h+="<div style='color:var(--mu)'><span>S&P 500 sotto il massimo</span><span>"+Math.round(D.dd[best])+"%</span></div>";
tp.innerHTML=h;tp.style.display='block';var wr=tp.parentNode.getBoundingClientRect(),left=(cx/640)*r.width+10;if(left+170>wr.width)left=(cx/640)*r.width-170;tp.style.left=Math.max(left,4)+'px'}
function mini(k,n){var key={previsione:'pr',armor:'ar',vix:'vx',economia:'ec'}[k];if(!key||!D)return;var svg=M.querySelector('.sai-mini[data-k="'+k+'"]');if(!svg)return;
var s=sel(n),N=T.length,W=640,H=150,X0=T[s],X1=T[N-1],xs=function(t){return 24+(t-X0)/(X1-X0||1)*(W-30)},Y=function(v){return 6+(100-v)*1.38},o='',B=D.b.concat([100]);
for(var j=0;j<B.length;j++){var a=Y(B[j]),b=Y(j?B[j-1]:0);o+="<rect x='24' y='"+a+"' width='"+(W-30)+"' height='"+(b-a)+"' fill='"+D.c[j]+"' opacity='.17'/>"}
[0,50,100].forEach(function(g){o+="<text x='2' y='"+(Y(g)+3)+"' font-size='8' fill='var(--mu)'>"+g+"</text>"});
var p=[],mn=1e9,mx=-1,vals=[];for(var i=s;i<N;i++){var v=D[key][i];if(v==null)continue;p.push(xs(T[i]).toFixed(1)+','+Y(v).toFixed(1));vals.push(v);mn=Math.min(mn,v);mx=Math.max(mx,v)}
o+="<polyline fill='none' stroke='var(--tx)' stroke-width='2.2' stroke-linejoin='round' points='"+p.join(' ')+"'/>";var lv=vals[vals.length-1];o+="<circle cx='"+xs(T[N-1])+"' cy='"+Y(lv)+"' r='4' fill='"+D.c[band(lv)]+"' stroke='var(--card)' stroke-width='2'/>";
o+="<text x='24' y='146' font-size='9' fill='var(--mu)'>"+new Date(X0).toLocaleDateString('it-IT',{month:'short',year:'2-digit'})+"</text><text x='"+(W-6)+"' y='146' font-size='9' fill='var(--mu)' text-anchor='end'>oggi</text>";
svg.innerHTML=o;var inf=M.querySelector('.sai-mi[data-ki="'+k+'"]');if(inf)inf.textContent='Nel periodo: minimo '+Math.round(mn)+', massimo '+Math.round(mx)+', oggi '+Math.round(lv)+'.'}
S.addEventListener('click',function(e){var t=e.target,x;
if(t.closest('a[data-go]'))close();
if(t.closest('[data-saix]')||t===M){close();return}
if(x=t.closest('[data-saip]')){open('p-'+x.dataset.saip);return}
if(t.closest('[data-saiback]')){show('sum');return}
if(x=t.closest('[data-saim]')){if(M.classList.contains('show'))show(x.dataset.saim);else open(x.dataset.saim);return}
var r=t.closest('.sai-rg button');if(r){var g=r.parentNode;g.querySelectorAll('button').forEach(function(b){b.classList.toggle('on',b===r)});if(g.dataset.rgm)mini(g.dataset.rgm,+r.dataset.r);else{RANGE=+r.dataset.r;chart()}return}
var tg=t.closest('#saitg button');if(tg){var k=tg.dataset.l;ON[k]=!ON[k];tg.classList.toggle('on',ON[k]);chart()}});
var ch=document.getElementById('saich');if(ch){['pointermove','pointerdown'].forEach(function(n){ch.addEventListener(n,tip)});ch.addEventListener('pointerleave',function(){var g=document.getElementById('saicr');if(g)g.style.display='none';document.getElementById('saitip').style.display='none'})}
document.addEventListener('keydown',function(e){if(e.key==='Escape')close()});
})();</script>"""
