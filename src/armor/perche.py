"""«Perché si muove oggi» (Patch 80): sotto i prezzi in tempo reale, in breve, cosa sta spingendo S&P 500 e VWCE.
Si legge cosa fanno i 11 settori e le aziende più pesanti (contributo stimato = peso indicativo × variazione) e si abbinano le notizie più vicine.
È una lettura automatica di prezzi e titoli: collega movimenti e notizie, non dimostra la causa. Pesi indicativi, non esatti."""
import html as _h
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

from . import live, news
from .config import DATA

FILE = DATA / "perche.json"
SETTORI = {  # simbolo ETF: (nome, peso indicativo % nell'S&P 500)
    "XLK": ("Tecnologia", 33.0), "XLF": ("Finanza", 13.5), "XLC": ("Comunicazioni", 10.0), "XLY": ("Consumi ciclici", 10.5), "XLV": ("Salute", 9.5),
    "XLI": ("Industria", 8.5), "XLP": ("Consumi base", 5.5), "XLE": ("Energia", 3.3), "XLU": ("Servizi pubblici", 2.3), "XLRE": ("Immobiliare", 2.0), "XLB": ("Materiali", 1.8)}
AZIENDE = {  # simbolo: (nome, peso indicativo % nell'S&P 500)
    "NVDA": ("Nvidia", 7.5), "AAPL": ("Apple", 6.5), "MSFT": ("Microsoft", 6.5), "AMZN": ("Amazon", 3.9), "GOOGL": ("Alphabet", 5.0), "META": ("Meta", 2.8),
    "AVGO": ("Broadcom", 2.5), "TSLA": ("Tesla", 2.0), "BRK-B": ("Berkshire", 1.6), "JPM": ("JPMorgan", 1.4), "LLY": ("Eli Lilly", 1.2), "V": ("Visa", 0.9),
    "ORCL": ("Oracle", 0.9), "XOM": ("Exxon", 0.9), "NFLX": ("Netflix", 0.8), "MA": ("Mastercard", 0.8), "COST": ("Costco", 0.7), "WMT": ("Walmart", 0.7),
    "PLTR": ("Palantir", 0.6), "JNJ": ("J&J", 0.6), "HD": ("Home Depot", 0.6), "AMD": ("AMD", 0.5), "BAC": ("Bank of America", 0.5), "UNH": ("UnitedHealth", 0.5)}
MONDO = {  # componenti del VWCE: chiave: (simbolo, nome, peso indicativo %)
    "eu": (("^GDAXI", "^FTSE", "^FCHI"), "Europa", 15.0), "jp": (("^N225",), "Giappone", 5.5), "asia": (("^HSI",), "Asia e emergenti", 12.0)}
PESO_USA = 62.0
ALTRI = ("ES=F", "EURUSD=X")
TEMI_ICONA = {"Banche centrali e tassi": "🏦", "Inflazione": "🛒", "Lavoro e crescita": "👷", "Guerre e geopolitica": "🌍", "Dazi e commercio": "🚢",
              "Energia e materie prime": "🛢️", "Utili e conti aziendali": "📊", "Intelligenza artificiale e chip": "💾", "Credito e banche": "💳", "Regole e cause legali": "⚖️"}


def _get(sym: str):
    try:
        js = requests.get(live.URL.format(sym=quote(sym, safe="")), headers=live.UA, timeout=15).json()
        q = live.parse_chart(js)
        return sym, q.get("chg")
    except Exception:  # noqa: BLE001
        return sym, None


def raccogli_variazioni() -> dict:
    simboli = list(SETTORI) + list(AZIENDE) + [s for v in MONDO.values() for s in v[0]] + list(ALTRI)
    with ThreadPoolExecutor(8) as ex:
        return {s: c for s, c in ex.map(_get, simboli)}


def notizie_fresche(simboli: list[str], limite: int = 3) -> list[dict]:
    out = []
    for s in simboli[:limite]:
        try:
            r = requests.get(news.YAHOO.format(s=quote(s)), headers=news.UA, timeout=15)
            for it in news.parse_rss(r.text)[:2]:
                it.update(ticker=s)
                out.append(it)
        except Exception:  # noqa: BLE001
            continue
    return out


def _p(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def _parola(c: float) -> str:
    return "quasi fermo" if abs(c) < 0.0015 else ("sale" if c > 0 else "scende")


def spiega_sp(chg: float | None, v: dict) -> dict | None:
    """Contributi stimati (punti percentuali) di settori e aziende alla variazione dell'S&P 500."""
    if chg is None:
        return None
    sett = sorted(({"s": k, "n": SETTORI[k][0], "chg": v[k] * 100, "contr": SETTORI[k][1] * v[k]} for k in SETTORI if v.get(k) is not None), key=lambda x: -abs(x["contr"]))
    az = sorted(({"s": k, "n": AZIENDE[k][0], "chg": v[k] * 100, "contr": AZIENDE[k][1] * v[k]} for k in AZIENDE if v.get(k) is not None), key=lambda x: -abs(x["contr"]))
    su = sum(1 for x in sett if x["chg"] > 0)
    return {"chg": chg * 100, "settori": sett[:5], "aziende": az[:6], "su": su, "tot": len(sett)}


def titolo_sp(d: dict) -> str:
    c = d["chg"] / 100
    verso = 1 if c >= 0 else -1
    if abs(c) < 0.0015:
        return "Giornata piatta: i settori si compensano."
    allin = [x for x in d["settori"] if x["contr"] * verso > 0][:2]
    az = [x for x in d["aziende"] if x["contr"] * verso > 0][:2]
    contro = next((x for x in d["settori"] if x["contr"] * verso < 0), None)
    parti = []
    if allin:
        parti.append(" e ".join(f"{x['n']} ({_p(x['chg'])}%)" for x in allin))
    t = ("Spinto da " if verso > 0 else "Pesano ") + (" e ".join(parti) if parti else "pochi titoli")
    if az:
        t += "; tra le aziende " + ", ".join(f"{x['n']} {_p(x['chg'])}%" for x in az)
    if contro:
        t += f". Frena {contro['n']} ({_p(contro['chg'])}%)" if verso > 0 else f". Regge {contro['n']} ({_p(contro['chg'])}%)"
    return t + "."


def spiega_vwce(chg: float | None, sp_chg: float | None, v: dict) -> dict | None:
    if chg is None:
        return None
    parti = []
    usa = v.get("ES=F") if v.get("ES=F") is not None else sp_chg
    if sp_chg is not None:
        usa = sp_chg if sp_chg is not None else usa
    if usa is not None:
        parti.append({"n": "USA", "chg": usa * 100, "contr": PESO_USA * usa})
    for k, (simboli, nome, w) in MONDO.items():
        vals = [v[s] for s in simboli if v.get(s) is not None]
        if vals:
            m = sum(vals) / len(vals)
            parti.append({"n": nome, "chg": m * 100, "contr": w * m})
    fx = v.get("EURUSD=X")
    if fx is not None:
        parti.append({"n": "Euro/dollaro", "chg": fx * 100, "contr": -PESO_USA * fx})
    parti.sort(key=lambda x: -abs(x["contr"]))
    return {"chg": chg * 100, "parti": parti}


def titolo_vwce(d: dict) -> str:
    c = d["chg"] / 100
    if abs(c) < 0.0015:
        return "Quasi fermo: le aree del mondo si compensano."
    verso = 1 if c >= 0 else -1
    pro = [x for x in d["parti"] if x["contr"] * verso > 0][:2]
    contro = next((x for x in d["parti"] if x["contr"] * verso < 0), None)
    t = ("Sale con " if verso > 0 else "Scende per ") + " e ".join(f"{x['n']} ({_p(x['chg'])}%)" for x in pro) if pro else "Movimento diffuso"
    if contro:
        t += f"; {('frena' if verso > 0 else 'regge')} {contro['n']} ({_p(contro['chg'])}%)"
    return t + "."


def scegli_notizie(fresche: list[dict], archivio: list[dict], tickers_top: list[str], verso: int, ora: datetime | None = None, n: int = 3) -> list[dict]:
    """Prima i titoli sulle aziende che si muovono di più, poi le notizie di mercato più importanti delle ultime 24 ore (con tono coerente)."""
    ora = ora or datetime.now(timezone.utc)

    def eta(t: str) -> float:
        try:
            return (ora - datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 3600
        except Exception:  # noqa: BLE001
            return 99.0
    out, visti = [], set()
    for it in fresche:
        h = eta(it.get("time", ""))
        if h <= 30 and news.norm(it["title"]) not in visti:
            visti.add(news.norm(it["title"]))
            out.append({"titolo": it["title"], "fonte": it.get("source", ""), "ore": round(h, 1), "icona": "🏢", "tag": it.get("ticker", ""), "link": it.get("link", "")})
    macro = [x for x in archivio if x.get("kind") == "macro" and eta(x.get("time", "")) <= 24]
    macro.sort(key=lambda x: -(x.get("score", 0) + (0.8 if x.get("sent", 0) * verso > 0.1 else 0)))
    for it in macro:
        if len(out) >= n + 1:
            break
        if news.norm(it["title"]) in visti:
            continue
        visti.add(news.norm(it["title"]))
        tema = (it.get("themes") or [""])[0]
        out.append({"titolo": it["title"], "fonte": it.get("source", ""), "ore": round(eta(it["time"]), 1), "icona": TEMI_ICONA.get(tema, "📰"), "tag": tema, "link": it.get("link", "")})
    return out[:n]


def costruisci(v: dict | None = None, fresche: list[dict] | None = None, quotes: dict | None = None, archivio: list[dict] | None = None, ora: datetime | None = None) -> dict:
    v = raccogli_variazioni() if v is None else v
    quotes = live.load().get("quotes", {}) if quotes is None else quotes
    sp_chg = (quotes.get("sp500") or {}).get("chg")
    if sp_chg is None:
        sp_chg = v.get("^GSPC")
    vw_chg = (quotes.get("vwce") or {}).get("chg")
    sp = spiega_sp(sp_chg, v)
    vw = spiega_vwce(vw_chg, sp_chg, v)
    top = [x["s"] for x in (sp or {}).get("aziende", [])][:3]
    if fresche is None:
        fresche = notizie_fresche(top)
    if archivio is None:
        try:
            archivio = news.load_latest().get("items", [])
        except Exception:  # noqa: BLE001
            archivio = []
    verso = 1 if (sp_chg or 0) >= 0 else -1
    nz = scegli_notizie(fresche, archivio, top, verso, ora)
    ora = ora or datetime.now(timezone.utc)
    return {"ora": ora.strftime("%Y-%m-%dT%H:%M:%SZ"), "sp": sp, "vwce": vw, "notizie": nz,
            "aperto": bool((quotes.get("sp500") or {}).get("open")), "ok": bool(sp or vw)}


def salva(d: dict) -> None:
    FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def carica() -> dict | None:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def aggiorna() -> dict:
    d = costruisci()
    salva(d)
    print("[perche]", "ok" if d["ok"] else "dati non disponibili", "·", len(d["notizie"]), "notizie")
    return d


def _col(x: float) -> str:
    return "#16a34a" if x >= 0 else "#dc2626"


def _barre(righe: list[dict], k: str = "contr") -> str:
    m = max([abs(x[k]) for x in righe] + [0.01])
    out = ""
    for x in righe:
        w = abs(x[k]) / m * 50
        pos = x[k] >= 0
        out += (f"<div class='pc-r'><span class='pc-n'>{_h.escape(x['n'])}</span><div class='pc-bar'><i style='left:{50 if pos else 50 - w:.0f}%;width:{w:.0f}%;background:{_col(x[k])}'></i><u></u></div>"
                f"<b style='color:{_col(x[k])}'>{_p(x['chg'])}%</b></div>")
    return out


def html(d: dict | None, ora_loc: datetime | None = None) -> str:
    if not d or not d.get("ok"):
        return ("<div class='pc' id='pch'><div class='pc-h'><b>Perché si muove oggi</b></div><div class='pc-t'>Lettura non disponibile in questo momento: riprova tra poco.</div></div>" + CSS)
    E = _h.escape
    try:
        t = datetime.fromisoformat(d["ora"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Rome")).strftime("%H:%M")
    except Exception:  # noqa: BLE001
        t = ""
    sp, vw = d.get("sp"), d.get("vwce")
    colonna_sp = colonna_vw = ""
    if sp:
        c = sp["chg"]
        chips = "".join(f"<span class='pc-chip' style='border-color:{_col(x['chg'])}'><b>{E(x['s'])}</b> <em style='color:{_col(x['chg'])}'>{_p(x['chg'])}%</em></span>" for x in sp["aziende"][:5])
        colonna_sp = (f"<div class='pc-c'><div class='pc-ch'><b>S&amp;P 500</b><span style='color:{_col(c)}'>{'▲' if c >= 0 else '▼'} {_p(abs(c), 2).replace('+', '')}%</span>"
                      f"<small>{sp['su']} settori su {sp['tot']} in rialzo</small></div><div class='pc-tt'>{E(titolo_sp(sp))}</div>"
                      f"{_barre(sp['settori'][:4])}<div class='pc-chips'>{chips}</div></div>")
    if vw:
        c = vw["chg"]
        colonna_vw = (f"<div class='pc-c'><div class='pc-ch'><b>VWCE</b><span style='color:{_col(c)}'>{'▲' if c >= 0 else '▼'} {_p(abs(c), 2).replace('+', '')}%</span><small>azioni di tutto il mondo, in euro</small></div>"
                      f"<div class='pc-tt'>{E(titolo_vwce(vw))}</div>{_barre(vw['parti'][:4])}</div>")
    nz = "".join(f"<a class='pc-n2' href='{E(x['link'])}' target='_blank' rel='noopener'><i>{x['icona']}</i><span>{E(x['titolo'][:110])}</span><small>{E(x['fonte'])} · {'meno di 1 ora' if x['ore'] < 1 else str(int(x['ore'])) + ' h'} fa</small></a>" for x in d.get("notizie", []))
    nz = f"<div class='pc-news'><div class='pc-nt'>Notizie in corso</div>{nz}</div>" if nz else ""
    info = ("<details class='pc-info'><summary><i>i</i> Come leggere questa scheda</summary><div>Le barre mostrano di quanto ogni settore o area muove l'indice, in punti percentuali stimati "
            "(variazione × peso indicativo nell'indice). Verde = spinge in su, rosso = in giù. Per «Euro/dollaro» il numero è la variazione del cambio: se l'euro sale, i titoli americani valgono meno in euro e la barra è rossa. Le notizie sono i titoli più vicini al movimento, non una prova della causa. "
            "Pesi approssimati: la scheda dà l'ordine di grandezza, non il conto esatto.</div></details>")
    stato = "mercato USA aperto" if d.get("aperto") else "ultimo dato disponibile"
    return (CSS + f"<div class='pc' id='pch'><div class='pc-h'><b>Perché si muove oggi</b><span>aggiornato alle {t} · {stato}</span><button type='button' id='pcr' title='Aggiorna ora'>↻</button></div>"
            f"<div class='pc-cols'>{colonna_sp}{colonna_vw}</div>{nz}{info}</div>")


JS = """<script>(function(){var b=document.getElementById('pcr');function ag(){fetch('perche.html?'+Date.now(),{cache:'no-store'}).then(function(r){return r.text()}).then(function(h){var w=document.getElementById('pch');if(!w||!h)return;
var t=document.createElement('div');t.innerHTML=h;var n=t.querySelector('#pch');if(n){w.innerHTML=n.innerHTML;var r=document.getElementById('pcr');if(r)r.onclick=ag}}).catch(function(){})}
if(b)b.onclick=function(){b.classList.add('spin');ag();setTimeout(function(){b.classList.remove('spin')},1200)};
if(location.protocol.indexOf('http')===0)setInterval(ag,300000)})()</script>"""

CSS = """<style>
.pc{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:10px 14px;margin:0 0 12px}.pc-h{display:flex;align-items:center;gap:10px;font-size:14px}.pc-h span{color:var(--mu);font-size:11.5px;flex:1}
.pc-h button{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;width:28px;height:28px;font-size:15px;cursor:pointer}.pc-h button.spin{animation:pcs .8s linear infinite}@keyframes pcs{to{transform:rotate(360deg)}}
.pc-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px}@media(max-width:620px){.pc-cols{grid-template-columns:1fr;gap:8px}}
.pc-ch{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.pc-ch b{font-size:15px}.pc-ch span{font-size:17px;font-weight:800}.pc-ch small{color:var(--mu);font-size:11px}
.pc-tt{font-size:13px;line-height:1.4;margin:3px 0 6px}.pc-r{display:grid;grid-template-columns:92px 1fr 52px;gap:6px;align-items:center;font-size:11.5px;margin:2px 0}.pc-n{color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pc-bar{position:relative;height:9px;background:var(--bd);border-radius:99px;overflow:hidden}.pc-bar i{position:absolute;top:0;height:100%;border-radius:99px}.pc-bar u{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--tx);opacity:.4}.pc-r b{text-align:right;font-size:11.5px}
.pc-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}.pc-chip{font-size:11px;border:1px solid;border-radius:99px;padding:1px 8px;background:var(--bg)}.pc-chip em{font-style:normal;font-weight:700}
.pc-news{margin-top:8px;border-top:1px solid var(--bd);padding-top:6px}.pc-nt{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px}
.pc-n2{display:grid;grid-template-columns:20px 1fr;column-gap:6px;font-size:12.5px;line-height:1.35;color:var(--tx);text-decoration:none;padding:3px 0}.pc-n2 span{overflow:hidden;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical}.pc-n2 small{grid-column:2;color:var(--mu);font-size:10.5px}
.pc-info{margin-top:4px;font-size:12px;line-height:1.45}.pc-info summary{cursor:pointer;color:var(--mu)}.pc-info summary i{display:inline-block;width:16px;height:16px;line-height:16px;text-align:center;border-radius:50%;background:var(--mu);color:var(--bg);font-style:normal;font-size:10px;margin-right:5px}
.pc-t{font-size:12.5px;color:var(--mu);margin-top:4px}
</style>"""
