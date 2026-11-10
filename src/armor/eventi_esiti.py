"""Eventi scorrevoli con esiti (Patch 70): per ogni evento già avvenuto, risultato atteso, risultato reale e una breve sintesi,
verde vivo se positivo per i mercati e rosso se negativo. Scorrimento con rotellina/dito e frecce al mese precedente e successivo.

Da dove vengono i numeri:
- Trimestrali: stima degli analisti e utile reale per azione da Yahoo (salvati ogni giorno in data/eventi_trimestrali.json, così restano).
- Inflazione (CPI), lavoro, tassi Fed: dato reale dalle serie ufficiali FRED già scaricate. Un «consenso» gratuito e affidabile non esiste:
  come atteso si usa un riferimento di Armor (indicato accanto al numero) oppure il consenso scritto a mano in data/eventi_attesi.csv
  (colonne: data, tipo, atteso, testo). Se il file ha la riga di quell'evento, vince quella.
- Scadenze opzioni: niente risultato, solo la reazione del mercato."""
import html as _h
import json
import math
from datetime import date, datetime, timedelta

import pandas as pd

from .config import DATA

E = _h.escape
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
MESI_C = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
FILE_TRIM = DATA / "eventi_trimestrali.json"
FILE_ATT = DATA / "eventi_attesi.csv"
GIORNI_INDIETRO = 15
GIORNI_AVANTI = 30


def _f(x, d=1, segno=False):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n.d."
    return (f"{x:+.{d}f}" if segno else f"{x:.{d}f}").replace(".", ",")


# ------------------------------------------------------------------ trimestrali (salvate nel tempo)
def aggiorna_trimestrali(tickers: dict[str, str], get=None) -> int:
    """Salva stima e risultato delle ultime trimestrali; unisce con quanto già salvato. Silenzioso se Yahoo non risponde."""
    try:
        old = json.loads(FILE_TRIM.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        old = {}
    n = 0
    for t, name in tickers.items():
        try:
            if get is not None:
                df = get(t)
            else:
                import yfinance as yf
                df = yf.Ticker(t).get_earnings_dates(limit=10)
            if df is None or len(df) == 0:
                continue
            for idx, r in df.iterrows():
                est, rep = r.get("EPS Estimate"), r.get("Reported EPS")
                if rep is None or pd.isna(rep):
                    continue
                d = str(pd.Timestamp(idx).date())
                old[f"{t}|{d}"] = {"ticker": t, "nome": name, "data": d, "stima": None if est is None or pd.isna(est) else float(est), "reale": float(rep)}
                n += 1
        except Exception:  # noqa: BLE001
            continue
    if old:
        FILE_TRIM.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    return n


def _trim_records() -> list[dict]:
    try:
        return list(json.loads(FILE_TRIM.read_text(encoding="utf-8")).values())
    except Exception:  # noqa: BLE001
        return []


def _attesi() -> dict:
    try:
        d = pd.read_csv(FILE_ATT, dtype=str)
        return {(r["data"], r["tipo"]): r for _, r in d.iterrows()}
    except Exception:  # noqa: BLE001
        return {}


# ------------------------------------------------------------------ esiti
def _serie(k):
    from . import store
    s = store.load(k)
    return s.dropna() if len(s) else s


def _mese_rif(d: date) -> pd.Timestamp:
    """Mese a cui si riferisce il dato pubblicato alla data d (il mese prima)."""
    m = pd.Timestamp(d).replace(day=1) - pd.DateOffset(months=1)
    return pd.Timestamp(m)


def _neutro(tipo_msg):
    return {"atteso": None, "reale": None, "sintesi": tipo_msg, "segno": None}


def esito_cpi(d: date, att: dict) -> dict:
    c = _serie("cpi")
    ref = _mese_rif(d)
    if not len(c) or ref not in c.index or (ref - pd.DateOffset(months=12)) not in c.index:
        return _neutro("Dato non ancora disponibile: compare quando le serie ufficiali vengono aggiornate.")
    yoy = (c.loc[ref] / c.loc[ref - pd.DateOffset(months=12)] - 1) * 100
    mom = (c.loc[ref] / c.loc[c.index[c.index.get_loc(ref) - 1]] - 1) * 100
    prev_ref = ref - pd.DateOffset(months=1)
    r = att.get((d.isoformat(), "CPI"))
    if r is not None and str(r.get("atteso", "")).strip():
        exp, fonte = float(str(r["atteso"]).replace(",", ".")), "consenso"
    elif prev_ref in c.index and (prev_ref - pd.DateOffset(months=12)) in c.index:
        exp, fonte = float((c.loc[prev_ref] / c.loc[prev_ref - pd.DateOffset(months=12)] - 1) * 100), "mese prima"
    else:
        exp, fonte = None, ""
    delta = None if exp is None else yoy - exp
    segno = None if delta is None else ("pos" if delta < -0.05 else ("neg" if delta > 0.05 else "neu"))
    txt = {"pos": "Inflazione più bassa dell'atteso: allenta il timore di tassi alti, buona notizia per le azioni.",
           "neg": "Inflazione più alta dell'atteso: i mercati temono tassi alti più a lungo, notizia negativa per le azioni.",
           "neu": "Inflazione in linea con l'atteso: nessuna sorpresa.", None: "Atteso non disponibile: nessun giudizio."}[segno]
    return {"atteso": None if exp is None else f"{_f(exp)}% annuo ({fonte})", "reale": f"{_f(float(yoy))}% annuo ({_f(float(mom), 1, True)}% sul mese)", "sintesi": txt, "segno": segno}


def esito_lavoro(d: date, att: dict) -> dict:
    p, u = _serie("payems"), _serie("unrate")
    ref = _mese_rif(d)
    if not len(p) or ref not in p.index or p.index.get_loc(ref) < 4:
        return _neutro("Dato non ancora disponibile: compare quando le serie ufficiali vengono aggiornate.")
    i = p.index.get_loc(ref)
    nuovi = float(p.iloc[i] - p.iloc[i - 1])
    media3 = float((p.iloc[i - 1] - p.iloc[i - 4]) / 3)
    r = att.get((d.isoformat(), "Lavoro USA"))
    if r is not None and str(r.get("atteso", "")).strip():
        exp, fonte = float(str(r["atteso"]).replace(",", ".")), "consenso"
    else:
        exp, fonte = media3, "media dei 3 mesi prima"
    dis = ""
    if len(u) and ref in u.index and u.index.get_loc(ref) >= 1:
        dis = f"; disoccupazione {_f(float(u.loc[ref]))}% ({_f(float(u.loc[ref] - u.iloc[u.index.get_loc(ref) - 1]), 1, True)} punti)"
    delta = nuovi - exp
    segno = "pos" if delta > 25 else ("neg" if delta < -25 else "neu")
    txt = {"pos": "Più posti di lavoro dell'atteso: l'economia regge meglio del previsto.",
           "neg": "Meno posti di lavoro dell'atteso: l'economia rallenta più del previsto.",
           "neu": "Posti di lavoro in linea con l'atteso."}[segno]
    return {"atteso": f"{_f(exp, 0, True)} mila posti ({fonte})", "reale": f"{_f(nuovi, 0, True)} mila posti{dis}", "sintesi": txt, "segno": segno}


def esito_fomc(d: date, att: dict) -> dict:
    f = _serie("fedfunds")
    if not len(f):
        return _neutro("Dato non disponibile.")
    t = pd.Timestamp(d)
    prima = f[f.index <= t - pd.Timedelta(days=1)]
    dopo = f[f.index >= t + pd.Timedelta(days=2)]
    if not len(prima) or not len(dopo):
        return _neutro("Il tasso dopo la decisione non è ancora disponibile.")
    a, b = float(prima.iloc[-1]), float(dopo.iloc[0])
    dl = round(b - a, 2)
    r = att.get((d.isoformat(), "FOMC"))
    exp_txt = str(r["testo"]) if r is not None and str(r.get("testo", "")).strip() not in ("", "nan") else f"tassi fermi a {_f(a, 2)}% (riferimento Armor)"
    if abs(dl) < 0.1:
        segno, reale, txt = "neu", f"tassi fermi a {_f(b, 2)}%", "Tassi lasciati invariati: conta il tono delle parole del presidente."
    elif dl < 0:
        segno, reale, txt = "pos", f"tassi tagliati a {_f(b, 2)}% ({_f(dl, 2, True)} punti)", "Taglio dei tassi: di solito aiuta azioni e obbligazioni."
    else:
        segno, reale, txt = "neg", f"tassi alzati a {_f(b, 2)}% ({_f(dl, 2, True)} punti)", "Rialzo dei tassi: di solito pesa su azioni e obbligazioni."
    return {"atteso": exp_txt, "reale": reale, "sintesi": txt, "segno": segno}


def esito_trimestrale(ev: dict, recs: list[dict]) -> dict:
    d = datetime.fromisoformat(ev["date"]).date()
    nome = ev["nome"].replace("Trimestrale ", "").strip().lower()
    for r in recs:
        if r["nome"].lower() != nome:
            continue
        if abs((datetime.fromisoformat(r["data"]).date() - d).days) > 3:
            continue
        if r.get("stima") is None:
            return {"atteso": "stima non disponibile", "reale": f"utile per azione {_f(r['reale'], 2)} $", "sintesi": "Conti pubblicati, ma senza stima degli analisti per il confronto.", "segno": None}
        sorpresa = (r["reale"] - r["stima"]) / abs(r["stima"]) * 100 if r["stima"] else 0
        segno = "pos" if sorpresa > 1 else ("neg" if sorpresa < -1 else "neu")
        txt = {"pos": f"Utili sopra le attese ({_f(sorpresa, 1, True)}%): conti migliori del previsto.",
               "neg": f"Utili sotto le attese ({_f(sorpresa, 1, True)}%): conti peggiori del previsto.",
               "neu": "Utili in linea con le attese."}[segno]
        return {"atteso": f"utile per azione {_f(r['stima'], 2)} $ (stima degli analisti)", "reale": f"utile per azione {_f(r['reale'], 2)} $", "sintesi": txt, "segno": segno}
    return _neutro("Risultato non salvato: compare per le trimestrali dai prossimi aggiornamenti.")


def mercato(d: date, sp: pd.Series | None, vix: pd.Series | None) -> str:
    """Reazione dell'S&P 500 nel giorno dell'evento, con la fascia attesa (8 casi su 10)."""
    try:
        from . import bande
        t = pd.Timestamp(d)
        ret = sp.dropna().pct_change() * 100
        if t not in ret.index:
            return ""
        r = float(ret.loc[t])
        pv = vix[vix.index < t]
        if not len(pv):
            return f"S&P 500 quel giorno: {_f(r, 1, True)}%"
        b = bande.band(float(pv.iloc[-1]), 1, t)
        j = "peggio del 90% dei casi" if r < b["lo"] else ("meglio del 90% dei casi" if r > b["hi"] else "nella fascia prevista")
        return f"S&P 500 quel giorno: {_f(r, 1, True)}% ({j}; fascia attesa {_f(b['lo'], 1, True)}% … {_f(b['hi'], 1, True)}%)"
    except Exception:  # noqa: BLE001
        return ""


def esito(ev: dict, today: date, sp=None, vix=None, recs=None, att=None) -> dict | None:
    d = datetime.fromisoformat(ev["date"]).date()
    if d >= today:
        return None
    att = att if att is not None else _attesi()
    tipo = ev.get("tipo")
    try:
        if tipo == "CPI":
            r = esito_cpi(d, att)
        elif tipo == "Lavoro USA":
            r = esito_lavoro(d, att)
        elif tipo == "FOMC":
            r = esito_fomc(d, att)
        elif tipo == "Trimestrale":
            r = esito_trimestrale(ev, recs if recs is not None else _trim_records())
        else:
            r = _neutro("Nessun risultato da confrontare: conta solo quanto si è mosso il mercato.")
    except Exception:  # noqa: BLE001
        r = _neutro("Risultato non disponibile.")
    r["mercato"] = mercato(d, sp, vix) if sp is not None and vix is not None else ""
    return r


# ------------------------------------------------------------------ grafica
ETICHETTA = {"pos": ("Positivo", "pos"), "neg": ("Negativo", "neg"), "neu": ("In linea", "neu"), None: ("Senza giudizio", "nd")}


def _card(ev: dict, today: date, es: dict | None, spiega: dict, imp: dict) -> str:
    d = datetime.fromisoformat(ev["date"]).date()
    tra = (d - today).days
    if es is None:
        quando = "oggi" if tra == 0 else "domani" if tra == 1 else f"tra {tra} giorni"
        cls, corpo, chip = "fut" + (" oggi" if tra == 0 else ""), "", ""
    else:
        quando = "ieri" if tra == -1 else f"{-tra} giorni fa"
        lab, c = ETICHETTA[es["segno"]]
        cls = "past " + c
        chip = f"<span class='evchip {c}'>{lab}</span>"
        righe = ""
        if es.get("atteso"):
            righe += f"<div><span>Atteso</span><b>{E(es['atteso'])}</b></div>"
        if es.get("reale"):
            righe += f"<div><span>Reale</span><b>{E(es['reale'])}</b></div>"
        corpo = (f"<div class='evres'>{righe}</div>" if righe else "") + f"<div class='evsin'>{E(es['sintesi'])}</div>" + (f"<div class='evmk'>{E(es['mercato'])}</div>" if es.get("mercato") else "")
    nome_imp, ic = imp.get(ev["peso"], imp[1])
    sp_txt = spiega.get(ev.get("tipo", ""), "")
    sp_html = f"<div class='evsp'>{E(sp_txt)}</div>" if sp_txt and es is None else ""
    return (f"<div class='evc {cls}' data-d='{ev['date']}'><div class='agd'><b>{d.day}</b><span>{MESI_C[d.month - 1]}</span></div>"
            f"<div class='agb'><div class='evh'><b>{E(ev['nome'])}</b> <span class='pvch {ic}'>{nome_imp}</span>{chip}</div><div class='mu'>{quando}</div>{sp_html}{corpo}</div></div>")


def html(today: date | None = None, sp: pd.Series | None = None, vix: pd.Series | None = None, uid: str = "evx") -> str:
    from . import extra13
    from .agenda import IMPORTANZA, SPIEGA
    today = today or date.today()
    if sp is None:
        try:
            from .features import closed_sp500
            sp = closed_sp500()
        except Exception:  # noqa: BLE001
            sp = None
    if vix is None:
        try:
            vix = _serie("vix")
        except Exception:  # noqa: BLE001
            vix = None
    a = (pd.Timestamp(today).replace(day=1) - pd.DateOffset(months=3)).date()
    z = (pd.Timestamp(today).replace(day=1) + pd.DateOffset(months=4)).date() - timedelta(days=1)
    recs, att = _trim_records(), _attesi()
    cards = ""
    for ev in extra13.all_events(a, z):
        es = esito(ev, today, sp, vix, recs, att)
        cards += _card(ev, today, es, SPIEGA, IMPORTANZA)
    if not cards:
        return "<p class='mu'>Nessun evento importante nei prossimi giorni.</p>"
    return (f"<div class='evw' id='{uid}' data-oggi='{today.isoformat()}' data-ind='{GIORNI_INDIETRO}' data-av='{GIORNI_AVANTI}'>"
            "<div class='evnav'><button type='button' data-ev='-1' aria-label='Mese precedente'>‹</button><b class='evlab'></b><button type='button' data-ev='1' aria-label='Mese successivo'>›</button>"
            "<button type='button' data-ev='0' class='evnow'>Oggi</button></div>"
            f"<div class='evscroll' tabindex='0'>{cards}<p class='mu evvuoto' hidden>Nessun evento in questo periodo.</p></div>"
            "<p class='mu'>Scorri con la rotellina o con il dito per vedere gli eventi dei giorni precedenti (ultimi 15 giorni) e quelli in arrivo; con le frecce passi al mese prima o dopo. "
            "<b style='color:#22c55e'>Verde</b> = risultato positivo per i mercati, <b style='color:#ef4444'>rosso</b> = negativo, grigio = in linea o senza giudizio. "
            "Per trimestrali il confronto è con la stima degli analisti; per inflazione, lavoro e tassi l'«atteso» è un riferimento di Armor (scritto accanto al numero) finché non si inserisce il consenso in <i>data/eventi_attesi.csv</i>. "
            "Il giudizio è automatico: serve a orientarsi, non a decidere.</p></div>") + CSS + JS


CSS = """<style>
.evnav{display:flex;align-items:center;gap:8px;margin:6px 0}.evnav button{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:12px;min-width:40px;height:36px;font-size:20px;font-weight:700;cursor:pointer}
.evnav .evnow{font-size:13px;padding:0 12px;margin-left:auto}.evlab{flex:1;text-align:center;font-size:14px}
.evscroll{max-height:470px;overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;display:grid;gap:10px;padding:2px 4px 2px 0;scroll-behavior:smooth}
.evc{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--bd);border-left-width:6px;border-radius:16px;padding:11px 13px;background:var(--card)}
.evc.fut.oggi{border-left-color:var(--ac)}.evc.past.pos{border-left-color:#22c55e;background:rgba(34,197,94,.10)}.evc.past.neg{border-left-color:#ef4444;background:rgba(239,68,68,.11)}.evc.past.neu,.evc.past.nd{border-left-color:#94a3b8}
.evh{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.evchip{font-size:11px;font-weight:800;border-radius:99px;padding:2px 10px;color:#fff}.evchip.pos{background:#16a34a}.evchip.neg{background:#dc2626}.evchip.neu,.evchip.nd{background:#64748b}
.evres{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:7px 0 4px}.evres div{background:rgba(127,127,127,.12);border-radius:10px;padding:6px 9px}.evres span{display:block;font-size:10.5px;color:var(--mu);text-transform:uppercase;letter-spacing:.4px}.evres b{font-size:13px}
.evsin{font-weight:700;font-size:13px;margin-top:4px}.evc.pos .evsin{color:#22c55e}.evc.neg .evsin{color:#ef4444}.evmk,.evsp{font-size:12px;color:var(--mu);margin-top:3px}
@media(max-width:520px){.evres{grid-template-columns:1fr}}
</style>"""

JS = r"""<script>(function(){document.querySelectorAll('.evw:not([data-on])').forEach(function(W){W.dataset.on=1;
var S=W.querySelector('.evscroll'),L=W.querySelector('.evlab'),C=[].slice.call(W.querySelectorAll('.evc')),V=W.querySelector('.evvuoto'),O=0,
T=new Date(W.dataset.oggi+'T12:00:00'),IND=+W.dataset.ind,AV=+W.dataset.av,
M=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function show(){var a,b,t;if(O===0){a=iso(new Date(T.getTime()-IND*864e5));b=iso(new Date(T.getTime()+AV*864e5));t='Ultimi '+IND+' giorni e prossimi '+AV}
else{var m=new Date(T.getFullYear(),T.getMonth()+O,1),e=new Date(m.getFullYear(),m.getMonth()+1,0);a=iso(m);b=iso(e);t=M[m.getMonth()][0].toUpperCase()+M[m.getMonth()].slice(1)+' '+m.getFullYear()}
L.textContent=t;var n=0,first=null;C.forEach(function(c){var ok=c.dataset.d>=a&&c.dataset.d<=b;c.style.display=ok?'':'none';if(ok){n++;if(!first&&c.dataset.d>=iso(T))first=c}});
V.hidden=n>0;S.style.scrollBehavior='auto';
if(O===0&&first){S.scrollTop=Math.max(first.offsetTop-S.offsetTop-6,0)}else S.scrollTop=0;S.style.scrollBehavior=''}
W.addEventListener('click',function(e){var b=e.target.closest('[data-ev]');if(!b)return;var v=+b.dataset.ev;O=v===0?0:O+v;show()});
show()})})();</script>"""
