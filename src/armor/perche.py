"""«Perché si muove oggi» (Patch 80-81): sotto i prezzi in tempo reale, in breve, cosa sta spingendo S&P 500 e VWCE.
Per ognuno dei due indici, in una scheda a due linguette: settori, aree del mondo, aziende e notizie.
Contributo stimato = peso indicativo × variazione. È una lettura automatica di prezzi e titoli: collega movimenti e notizie, non dimostra la causa."""
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
SETTORI = {  # S&P 500: simbolo ETF: (nome, peso indicativo %)
    "XLK": ("Tecnologia", 33.0), "XLF": ("Finanza", 13.5), "XLC": ("Comunicazioni", 10.0), "XLY": ("Consumi ciclici", 10.5), "XLV": ("Salute", 9.5),
    "XLI": ("Industria", 8.5), "XLP": ("Consumi base", 5.5), "XLE": ("Energia", 3.3), "XLU": ("Servizi pubblici", 2.3), "XLRE": ("Immobiliare", 2.0), "XLB": ("Materiali", 1.8)}
SETTORI_MONDO = {  # VWCE: ETF settoriali mondiali (iShares): simbolo: nome italiano come nella composizione del fondo (holdings.py)
    "IXN": "Tecnologia", "IXG": "Finanza", "EXI": "Industria", "IXJ": "Salute", "KXI": "Beni di consumo base", "MXI": "Materiali", "IXC": "Energia",
    "RXI": "Beni di consumo ciclici", "JXI": "Servizi di pubblica utilità", "IXP": "Comunicazioni", "REET": "Immobiliare"}
NOMI_BREVI = {"Beni di consumo base": "Consumi base", "Beni di consumo ciclici": "Consumi ciclici", "Servizi di pubblica utilità": "Servizi pubblici"}
AZIENDE = {  # S&P 500: simbolo: (nome, peso indicativo %)
    "NVDA": ("Nvidia", 7.5), "AAPL": ("Apple", 6.5), "MSFT": ("Microsoft", 6.5), "AMZN": ("Amazon", 3.9), "GOOGL": ("Alphabet", 5.0), "META": ("Meta", 2.8),
    "AVGO": ("Broadcom", 2.5), "TSLA": ("Tesla", 2.0), "BRK-B": ("Berkshire", 1.6), "JPM": ("JPMorgan", 1.4), "LLY": ("Eli Lilly", 1.2), "V": ("Visa", 0.9),
    "ORCL": ("Oracle", 0.9), "XOM": ("Exxon", 0.9), "NFLX": ("Netflix", 0.8), "MA": ("Mastercard", 0.8), "COST": ("Costco", 0.7), "WMT": ("Walmart", 0.7),
    "PLTR": ("Palantir", 0.6), "JNJ": ("J&J", 0.6), "HD": ("Home Depot", 0.6), "AMD": ("AMD", 0.5), "BAC": ("Bank of America", 0.5), "UNH": ("UnitedHealth", 0.5)}
AZIENDE_MONDO = {  # VWCE: simbolo: (nome, peso indicativo %)
    "NVDA": ("Nvidia", 5.0), "AAPL": ("Apple", 4.5), "MSFT": ("Microsoft", 3.6), "GOOGL": ("Alphabet", 3.4), "AMZN": ("Amazon", 2.3), "TSM": ("TSMC", 1.8),
    "AVGO": ("Broadcom", 1.5), "META": ("Meta", 1.5), "MU": ("Micron", 1.1), "TSLA": ("Tesla", 1.1), "JPM": ("JPMorgan", 0.8), "ASML": ("ASML", 0.6),
    "TM": ("Toyota", 0.4), "SAP": ("SAP", 0.35), "NVO": ("Novo Nordisk", 0.35)}
AREE = {  # simboli (indici di Borsa) → nome, peso indicativo % nel VWCE
    "usa": (("^GSPC",), "USA", 62.0), "eu": (("^GDAXI", "^FTSE", "^FCHI"), "Europa", 15.0), "jp": (("^N225",), "Giappone", 5.5), "asia": (("^HSI",), "Cina e Asia", 12.0)}
FX = "EURUSD=X"
ISIN = {  # codici usati da onvista per i prezzi aggiornati dal telefono (XLB e XOM non rispondono: restano i dati del server)
    "XLK": ("US81369Y8030", "FUND"), "XLF": ("US81369Y6059", "FUND"), "XLV": ("US81369Y2090", "FUND"), "XLY": ("US81369Y4070", "FUND"), "XLC": ("US81369Y8527", "FUND"),
    "XLI": ("US81369Y7040", "FUND"), "XLP": ("US81369Y3080", "FUND"), "XLE": ("US81369Y5069", "FUND"), "XLU": ("US81369Y8865", "FUND"), "XLRE": ("US81369Y8600", "FUND"),
    "NVDA": ("US67066G1040", "STOCK"), "AAPL": ("US0378331005", "STOCK"), "MSFT": ("US5949181045", "STOCK"), "AMZN": ("US0231351067", "STOCK"), "GOOGL": ("US02079K3059", "STOCK"),
    "META": ("US30303M1027", "STOCK"), "AVGO": ("US11135F1012", "STOCK"), "TSLA": ("US88160R1014", "STOCK"), "BRK-B": ("US0846707026", "STOCK"), "JPM": ("US46625H1005", "STOCK"),
    "LLY": ("US5324571083", "STOCK"), "V": ("US92826C8394", "STOCK"), "ORCL": ("US68389X1054", "STOCK"), "NFLX": ("US64110L1061", "STOCK"), "MA": ("US57636Q1040", "STOCK"),
    "COST": ("US22160K1051", "STOCK"), "WMT": ("US9311421039", "STOCK"), "PLTR": ("US69608A1088", "STOCK"), "JNJ": ("US4781601046", "STOCK"), "HD": ("US4370761029", "STOCK"),
    "AMD": ("US0079031078", "STOCK"), "BAC": ("US0605051046", "STOCK"), "UNH": ("US91324P1021", "STOCK"), "TSM": ("US8740391003", "STOCK"), "MU": ("US5951121038", "STOCK"),
    "TM": ("US8923313071", "STOCK"), "NVO": ("US6701002056", "STOCK")}
TEMI_ICONA = {"Banche centrali e tassi": "🏦", "Inflazione": "🛒", "Lavoro e crescita": "👷", "Guerre e geopolitica": "🌍", "Dazi e commercio": "🚢",
              "Energia e materie prime": "🛢️", "Utili e conti aziendali": "📊", "Intelligenza artificiale e chip": "💾", "Credito e banche": "💳", "Regole e cause legali": "⚖️"}
GRUPPI_SP = {"Mercati", "Banche centrali", "Inflazione e lavoro", "Dazi e commercio"}
GRUPPI_VW = {"Europa", "Cina e Asia", "Banche centrali", "Energia e materie prime", "Geopolitica", "Mercati"}


def _get(sym: str):
    try:
        js = requests.get(live.URL.format(sym=quote(sym, safe="")), headers=live.UA, timeout=15).json()
        return sym, live.parse_chart(js).get("chg")
    except Exception:  # noqa: BLE001
        return sym, None


def pesi_settori_mondo() -> dict[str, float]:
    """Peso % dei settori nel VWCE dalla composizione del fondo (holdings.py), in simboli ETF mondiali."""
    try:
        from . import holdings
        sect = {n: float(w) for n, w in holdings.load().get("sectors", [])}
    except Exception:  # noqa: BLE001
        sect = {}
    return {sym: sect[n] for sym, n in SETTORI_MONDO.items() if n in sect}


def raccogli_variazioni() -> dict:
    simboli = (list(SETTORI) + list(SETTORI_MONDO) + list(AZIENDE) + list(AZIENDE_MONDO) + [s for v in AREE.values() for s in v[0]] + ["ES=F", FX])
    with ThreadPoolExecutor(10) as ex:
        return {s: c for s, c in ex.map(_get, dict.fromkeys(simboli))}


def notizie_fresche(simboli: list[str], limite: int = 4) -> list[dict]:
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


def _ordina(righe: list[dict]) -> list[dict]:
    return sorted(righe, key=lambda x: -abs(x["contr"]))


def settori_di(simboli: dict, v: dict) -> list[dict]:
    return _ordina([{"s": k, "n": n, "chg": v[k] * 100, "contr": w * v[k]} for k, (n, w) in simboli.items() if v.get(k) is not None])


def aziende_di(simboli: dict, v: dict) -> list[dict]:
    return _ordina([{"s": k, "n": n, "chg": v[k] * 100, "contr": w * v[k]} for k, (n, w) in simboli.items() if v.get(k) is not None])


def aree_mondo(v: dict, sp_chg: float | None) -> list[dict]:
    """Variazione e contributo stimato al VWCE di ogni area; l'effetto cambio è a parte (euro più forte = titoli in dollari valgono meno in euro)."""
    out = []
    for _k, (simboli, nome, w) in AREE.items():
        vals = [v[s] for s in simboli if v.get(s) is not None]
        if nome == "USA" and sp_chg is not None:
            vals = [sp_chg]
        if vals:
            m = sum(vals) / len(vals)
            out.append({"n": nome, "chg": m * 100, "contr": w * m})
    fx = v.get(FX)
    if fx is not None:
        out.append({"n": "Euro/dollaro", "chg": fx * 100, "contr": -AREE["usa"][2] * fx, "fx": True})
    return _ordina(out)


def spiega_sp(chg: float | None, v: dict) -> dict | None:
    if chg is None:
        return None
    sett = settori_di({k: x for k, x in SETTORI.items()}, v)
    return {"chg": chg * 100, "settori": sett[:5], "aziende": aziende_di(AZIENDE, v)[:6], "aree": [a for a in aree_mondo(v, chg) if a["n"] != "USA"],
            "su": sum(1 for x in sett if x["chg"] > 0), "tot": len(sett)}


def spiega_vwce(chg: float | None, sp_chg: float | None, v: dict) -> dict | None:
    if chg is None:
        return None
    pesi = pesi_settori_mondo()
    sett = _ordina([{"s": k, "n": NOMI_BREVI.get(SETTORI_MONDO[k], SETTORI_MONDO[k]), "chg": v[k] * 100, "contr": pesi[k] * v[k]} for k in pesi if v.get(k) is not None])
    return {"chg": chg * 100, "settori": sett[:5], "aziende": aziende_di(AZIENDE_MONDO, v)[:6], "aree": aree_mondo(v, sp_chg),
            "su": sum(1 for x in sett if x["chg"] > 0), "tot": len(sett)}


def _nomi(lst: list[dict], verso: int, n: int = 2) -> list[dict]:
    return [x for x in lst if x["contr"] * verso > 0][:n]


def titolo_sp(d: dict) -> str:
    c = d["chg"] / 100
    verso = 1 if c >= 0 else -1
    if abs(c) < 0.0015:
        return "Giornata piatta: i settori si compensano."
    allin, az = _nomi(d["settori"], verso), _nomi(d["aziende"], verso)
    contro = next((x for x in d["settori"] if x["contr"] * verso < 0), None)
    t = ("Spinto da " if verso > 0 else "Pesano ") + (" e ".join(f"{x['n']} ({_p(x['chg'])}%)" for x in allin) if allin else "pochi titoli")
    if az:
        t += "; tra le aziende " + ", ".join(f"{x['n']} {_p(x['chg'])}%" for x in az)
    if contro:
        t += f". {'Frena' if verso > 0 else 'Regge'} {contro['n']} ({_p(contro['chg'])}%)"
    return t + "."


def titolo_vwce(d: dict) -> str:
    c = d["chg"] / 100
    if abs(c) < 0.0015:
        return "Quasi fermo: le aree del mondo si compensano."
    verso = 1 if c >= 0 else -1
    pro = _nomi(d["aree"], verso)
    contro = next((x for x in d["aree"] if x["contr"] * verso < 0), None)
    def fr(x):
        return f"{x['n']} ({_p(x['chg'])}%)" if not x.get("fx") else ("euro più debole" if x["chg"] < 0 else "euro più forte") + f" ({_p(x['chg'])}%)"
    t = ("Sale con " if verso > 0 else "Scende per ") + (" e ".join(fr(x) for x in pro) if pro else "movimento diffuso")
    if contro:
        t += f"; {'frena' if verso > 0 else 'regge'} {fr(contro)}"
    sett = _nomi(d["settori"], verso, 1)
    if sett:
        t += f". Tra i settori guida {sett[0]['n']} ({_p(sett[0]['chg'])}%)"
    return t + "."


def scegli_notizie(fresche: list[dict], archivio: list[dict], verso: int, gruppi: set, ora: datetime | None = None, n: int = 3) -> list[dict]:
    """Prima i titoli sulle aziende che si muovono di più, poi le notizie di mercato più importanti delle ultime 24 ore (gruppi preferiti e tono coerente)."""
    ora = ora or datetime.now(timezone.utc)

    def eta(t: str) -> float:
        try:
            return (ora - datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 3600
        except Exception:  # noqa: BLE001
            return 99.0
    out, visti = [], set()
    for it in fresche:
        h = eta(it.get("time", ""))
        if h <= 30 and news.norm(it["title"]) not in visti and len(out) < 2:
            visti.add(news.norm(it["title"]))
            out.append({"titolo": it["title"], "fonte": it.get("source", ""), "ore": round(h, 1), "icona": "🏢", "tag": it.get("ticker", ""), "link": it.get("link", "")})
    macro = [x for x in archivio if x.get("kind") == "macro" and eta(x.get("time", "")) <= 24]
    macro.sort(key=lambda x: -(x.get("score", 0) + (0.8 if x.get("sent", 0) * verso > 0.1 else 0) + (1.0 if x.get("group") in gruppi else 0)))
    for it in macro:
        if len(out) >= n:
            break
        if news.norm(it["title"]) in visti:
            continue
        visti.add(news.norm(it["title"]))
        tema = (it.get("themes") or [""])[0]
        out.append({"titolo": it["title"], "fonte": it.get("source", ""), "ore": round(eta(it["time"]), 1), "icona": TEMI_ICONA.get(tema, "📰"), "tag": tema, "link": it.get("link", "")})
    return out[:n]


def costruisci(v: dict | None = None, fresche: dict | None = None, quotes: dict | None = None, archivio: list[dict] | None = None, ora: datetime | None = None) -> dict:
    v = raccogli_variazioni() if v is None else v
    quotes = live.load().get("quotes", {}) if quotes is None else quotes
    sp_chg = (quotes.get("sp500") or {}).get("chg")
    if sp_chg is None:
        sp_chg = v.get("^GSPC")
    vw_chg = (quotes.get("vwce") or {}).get("chg")
    sp, vw = spiega_sp(sp_chg, v), spiega_vwce(vw_chg, sp_chg, v)
    if fresche is None:
        fresche = {"sp": notizie_fresche([x["s"] for x in (sp or {}).get("aziende", [])][:2]), "vw": notizie_fresche([x["s"] for x in (vw or {}).get("aziende", [])][:2])}
    if archivio is None:
        try:
            archivio = news.load_latest().get("items", [])
        except Exception:  # noqa: BLE001
            archivio = []
    ora = ora or datetime.now(timezone.utc)
    for d, k, g in ((sp, "sp", GRUPPI_SP), (vw, "vw", GRUPPI_VW)):
        if d:
            d["notizie"] = scegli_notizie(fresche.get(k, []), archivio, 1 if d["chg"] >= 0 else -1, g, ora)
    return {"ora": ora.strftime("%Y-%m-%dT%H:%M:%SZ"), "sp": sp, "vwce": vw, "aperto": bool((quotes.get("sp500") or {}).get("open")), "ok": bool(sp or vw),
            "live": dati_live(v, (vw or {}).get("aree", []), (vw or {}).get("settori", []))}


def dati_live(v: dict, vw_aree: list[dict], vw_sett: list[dict] | None = None) -> dict:
    """Tutto ciò che serve alla pagina per ricalcolare la scheda da sola con i prezzi aggiornati (pesi, nomi, codici, ultimo dato del server)."""
    sim = set(SETTORI) | set(AZIENDE) | set(AZIENDE_MONDO)
    return {"isin": {k: list(x) for k, x in ISIN.items()},
            "sp": {"sett": [[k, n, w] for k, (n, w) in SETTORI.items()], "az": [[k, n, w] for k, (n, w) in AZIENDE.items()]},
            "vw": {"az": [[k, n, w] for k, (n, w) in AZIENDE_MONDO.items()], "aree": vw_aree, "sett": vw_sett or []},
            "base": {k: v[k] for k in sim if v.get(k) is not None}, "usa_w": AREE["usa"][2]}


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
    print("[perche]", "ok" if d["ok"] else "dati non disponibili")
    return d


def _col(x: float) -> str:
    return "#16a34a" if x >= 0 else "#dc2626"


def _barre(righe: list[dict]) -> str:
    m = max([abs(x["contr"]) for x in righe] + [0.01])
    out = ""
    for x in righe:
        w = abs(x["contr"]) / m * 50
        pos = x["contr"] >= 0
        etic = (("euro più forte" if x["chg"] > 0 else "euro più debole") + f" {_p(x['chg'])}%") if x.get("fx") else f"{_p(x['chg'])}%"
        out += (f"<div class='pc-r'><span class='pc-n'>{_h.escape(x['n'])}</span><div class='pc-bar'><i style='left:{50 if pos else 50 - w:.0f}%;width:{w:.0f}%;background:{_col(x['contr'])}'></i><u></u></div>"
                f"<b style='color:{_col(x['contr'])}'>{etic}</b></div>")
    return out


def _pannello(k: str, d: dict, nome_aree: str, attivo: bool) -> str:
    E = _h.escape
    titolo = titolo_sp(d) if k == "sp" else titolo_vwce(d)
    chips = "".join(f"<span class='pc-chip' style='border-color:{_col(x['chg'])}'><b>{E(x['s'])}</b> <em style='color:{_col(x['chg'])}'>{_p(x['chg'])}%</em></span>" for x in d["aziende"][:6])
    nz = "".join(f"<a class='pc-n2' href='{E(x['link'])}' target='_blank' rel='noopener'><i>{x['icona']}</i><span>{E(x['titolo'][:110])}</span><small>{E(x['fonte'])} · {'meno di 1 ora' if x['ore'] < 1 else str(int(x['ore'])) + ' h'} fa</small></a>" for x in d.get("notizie", []))
    nz = f"<div class='pc-news'><div class='pc-nt'>Notizie in corso</div>{nz}</div>" if nz else ""
    nota = "<div class='pc-nota'>L'S&amp;P 500 è solo USA: le altre aree sono il contesto, non spiegano il movimento.</div>" if k == "sp" else ""
    return (f"<div class='pc-panel' data-t='{k}'{'' if attivo else ' hidden'}><div class='pc-tt'>{E(titolo)} <small>{d['su']} settori su {d['tot']} in rialzo</small></div>"
            f"<div class='pc-cols'><div><div class='pc-st'>Settori</div>{_barre(d['settori'][:5])}</div><div><div class='pc-st'>{E(nome_aree)}</div>{_barre(d['aree'][:5])}{nota}</div></div>"
            f"<div class='pc-st'>Aziende che pesano di più</div><div class='pc-chips'>{chips}</div>{nz}</div>")


def html(d: dict | None, ora_loc: datetime | None = None) -> str:
    if not d or not d.get("ok"):
        return ("<div class='pc' id='pch'><div class='pc-h'><b>Perché si muove oggi</b></div><div class='pc-t'>Lettura non disponibile in questo momento: riprova tra poco.</div></div>" + CSS)
    try:
        t = datetime.fromisoformat(d["ora"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Rome")).strftime("%H:%M")
    except Exception:  # noqa: BLE001
        t = ""
    sp, vw = d.get("sp"), d.get("vwce")
    prima = "sp" if sp else "vw"
    tabs = ""
    for k, nome, x in (("sp", "S&amp;P 500", sp), ("vw", "VWCE", vw)):
        if x:
            tabs += f"<button type='button' data-t='{k}' class='{'on' if k == prima else ''}'><b>{nome}</b><span style='color:{_col(x['chg'])}'>{'▲' if x['chg'] >= 0 else '▼'} {_p(abs(x['chg']), 2).replace('+', '')}%</span></button>"
    pan = (_pannello("sp", sp, "Aree del mondo (contesto)", prima == "sp") if sp else "") + (_pannello("vw", vw, "Aree del mondo (contributo stimato)", prima == "vw") if vw else "")
    info = ("<details class='pc-info'><summary><i>i</i> Come leggere questa scheda</summary><div>Tocca S&amp;P 500 o VWCE per vedere settori, aree del mondo, aziende e notizie di ciascuno. "
            "Le barre mostrano di quanto ogni voce muove l'indice, in punti percentuali stimati (variazione × peso indicativo): verde = spinge in su, rosso = in giù. "
            "Per «Euro/dollaro» la barra è l'effetto sul VWCE: se l'euro sale, i titoli americani valgono meno in euro. Le notizie sono i titoli più vicini al movimento, non una prova della causa. "
            "Pesi approssimati: la scheda dà l'ordine di grandezza, non il conto esatto.</div></details>")
    dati = ("<script type='application/json' id='pcd'>" + json.dumps(d["live"], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>") if d.get("live") else ""
    stato = "mercato USA aperto" if d.get("aperto") else "ultimo dato disponibile"
    return (CSS + f"<div class='pc' id='pch'><div class='pc-h'><b>Perché si muove oggi</b><span id='pcs'>aggiornato alle {t} · {stato}</span><button type='button' id='pcr' title='Aggiorna ora'>↻</button></div>"
            f"<div class='pc-tabs'>{tabs}</div>{pan}{info}{dati}</div>")


JS = """<script>(function(){var W=document.getElementById('pch');if(!W||W.dataset.on)return;W.dataset.on=1;var cur=null;
function show(){var t=cur||(W.querySelector('.pc-tabs button.on')||{dataset:{}}).dataset.t;if(!t)return;cur=t;W.querySelectorAll('.pc-tabs button').forEach(function(b){b.classList.toggle('on',b.dataset.t===t)});W.querySelectorAll('.pc-panel').forEach(function(p){p.hidden=p.dataset.t!==t})}
function ag(){var r=document.getElementById('pcr');if(r)r.classList.add('spin');fetch('perche.html?'+Date.now(),{cache:'no-store'}).then(function(x){return x.text()}).then(function(h){var t=document.createElement('div');t.innerHTML=h;var n=t.querySelector('#pch');if(n){W.innerHTML=n.innerHTML;show();if(window.pcLive)window.pcLive()}}).catch(function(){}).then(function(){var r2=document.getElementById('pcr');if(r2)setTimeout(function(){r2.classList.remove('spin')},600)})}
W.addEventListener('click',function(e){var b=e.target.closest('.pc-tabs button');if(b){cur=b.dataset.t;show();return}if(e.target.closest('#pcr'))ag()});
show();if(location.protocol.indexOf('http')===0)setInterval(ag,120000)})()</script>"""


LIVE_JS = r"""<script>(function(){var W=document.getElementById('pch');if(!W||location.protocol.indexOf('http')!==0||window.pcLiveOn)return;window.pcLiveOn=1;
var API='https://api.onvista.de/api/v1/instruments/',EVERY=45000,live={},busy=false,fails=0,timer=null,t0=0;
function E(s){return String(s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function P(x,d){var t=(x>=0?'+':'')+x.toFixed(d==null?1:d);return t.replace('.',',').replace('-','−')}
function col(x){return x>=0?'#16a34a':'#dc2626'}
function data(){var e=document.getElementById('pcd');if(!e)return null;try{return JSON.parse(e.textContent)}catch(x){return null}}
function ch(s,b){return live[s]!=null?live[s]:b[s]}
function righe(l,b){var o=[];l.forEach(function(a){var c=ch(a[0],b);if(c!=null)o.push({s:a[0],n:a[1],chg:c*100,contr:a[2]*c})});o.sort(function(x,y){return Math.abs(y.contr)-Math.abs(x.contr)});return o}
function nomi(l,v,n){return l.filter(function(x){return x.contr*v>0}).slice(0,n)}
function barre(l){var m=0.01;l.forEach(function(x){m=Math.max(m,Math.abs(x.contr))});return l.map(function(x){var w=Math.abs(x.contr)/m*50,pos=x.contr>=0,et=x.fx?((x.chg>0?'euro più forte ':'euro più debole ')+P(x.chg)+'%'):P(x.chg)+'%';
return "<div class='pc-r'><span class='pc-n'>"+E(x.n)+"</span><div class='pc-bar'><i style='left:"+(pos?50:(50-w).toFixed(0))+"%;width:"+w.toFixed(0)+"%;background:"+col(x.contr)+"'></i><u></u></div><b style='color:"+col(x.contr)+"'>"+et+"</b></div>"}).join('')}
function chips(l){return l.slice(0,6).map(function(x){return "<span class='pc-chip' style='border-color:"+col(x.chg)+"'><b>"+E(x.s)+"</b> <em style='color:"+col(x.chg)+"'>"+P(x.chg)+"%</em></span>"}).join('')}
function titSp(sett,az,c){var v=c>=0?1:-1;if(Math.abs(c)<0.0015)return 'Giornata piatta: i settori si compensano.';var a=nomi(sett,v,2),z=nomi(az,v,2),k=sett.filter(function(x){return x.contr*v<0})[0];
var t=(v>0?'Spinto da ':'Pesano ')+(a.length?a.map(function(x){return x.n+' ('+P(x.chg)+'%)'}).join(' e '):'pochi titoli');if(z.length)t+='; tra le aziende '+z.map(function(x){return x.n+' '+P(x.chg)+'%'}).join(', ');
if(k)t+='. '+(v>0?'Frena ':'Regge ')+k.n+' ('+P(k.chg)+'%)';return t+'.'}
function titVw(aree,sett,c){if(Math.abs(c)<0.0015)return 'Quasi fermo: le aree del mondo si compensano.';var v=c>=0?1:-1,pro=nomi(aree,v,2),k=aree.filter(function(x){return x.contr*v<0})[0];
function fr(x){return x.fx?((x.chg<0?'euro più debole':'euro più forte')+' ('+P(x.chg)+'%)'):x.n+' ('+P(x.chg)+'%)'}
var t=(v>0?'Sale con ':'Scende per ')+(pro.length?pro.map(fr).join(' e '):'movimento diffuso');if(k)t+='; '+(v>0?'frena ':'regge ')+fr(k);var s=nomi(sett,v,1);if(s.length)t+='. Tra i settori guida '+s[0].n+' ('+P(s[0].chg)+'%)';return t+'.'}
function tab(k,c){var b=W.querySelector(".pc-tabs button[data-t='"+k+"'] span");if(b){b.style.color=col(c);b.textContent=(c>=0?'▲ ':'▼ ')+Math.abs(c*100).toFixed(2).replace('.',',')+'%'}}
function render(){var D=data(),L=window.LIVE&&window.LIVE.quotes;if(!D||!L||!Object.keys(live).length)return;var b=D.base,sp=L.sp500&&L.sp500.chg,vw=L.vwce&&L.vwce.chg;
var P1=W.querySelector(".pc-panel[data-t='sp']"),P2=W.querySelector(".pc-panel[data-t='vw']");
if(P1&&sp!=null){var se=righe(D.sp.sett,b),az=righe(D.sp.az,b),su=se.filter(function(x){return x.chg>0}).length;
P1.querySelector('.pc-tt').innerHTML=E(titSp(se,az,sp))+" <small>"+su+" settori su "+se.length+" in rialzo</small>";var c1=P1.querySelector('.pc-cols>div');if(c1)c1.innerHTML="<div class='pc-st'>Settori</div>"+barre(se.slice(0,5));
var ch1=P1.querySelector('.pc-chips');if(ch1)ch1.innerHTML=chips(az);tab('sp',sp)}
if(P2&&vw!=null){var az2=righe(D.vw.az,b),ar=D.vw.aree.map(function(x){var y=Object.assign({},x);if(x.n==='USA'&&sp!=null){y.chg=sp*100;y.contr=D.usa_w*sp}return y});
ar.sort(function(x,y){return Math.abs(y.contr)-Math.abs(x.contr)});
P2.querySelector('.pc-tt').innerHTML=E(titVw(ar,D.vw.sett,vw))+P2.querySelector('.pc-tt small').outerHTML;var c2=P2.querySelectorAll('.pc-cols>div')[1];if(c2){var h=c2.querySelector('.pc-st');c2.innerHTML=(h?h.outerHTML:'')+barre(ar.slice(0,5))}
var ch2=P2.querySelector('.pc-chips');if(ch2)ch2.innerHTML=chips(az2);tab('vw',vw)}
var s=document.getElementById('pcs');if(s){var d=new Date(t0);s.textContent='prezzi aggiornati alle '+('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)+':'+('0'+d.getSeconds()).slice(-2)+' · USA con circa 15 minuti di ritardo'}}
window.pcLive=render;
function best(j){var Lq=[];if(j&&j.quote)Lq.push(j.quote);if(j&&j.quoteList&&j.quoteList.list)Lq=Lq.concat(j.quoteList.list);Lq=Lq.filter(function(q){return q&&q.last>0&&q.previousLast>0&&q.datetimeLast});
Lq.sort(function(a,b){return new Date(b.datetimeLast)-new Date(a.datetimeLast)});return Lq[0]}
function one(s,i){return fetch(API+i[1]+'/ISIN:'+i[0]+'/snapshot',{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var q=best(j);if(!q)return 0;var c=q.last/q.previousLast-1;if(Math.abs(c)>=0.25)return 0;live[s]=c;return 1}).catch(function(){return 0})}
function poll(){if(busy||document.hidden)return;var D=data();if(!D){return}busy=true;
Promise.all(Object.keys(D.isin).map(function(s){return one(s,D.isin[s])})).then(function(r){var n=r.reduce(function(a,b){return a+b},0);if(n>5){fails=0;t0=Date.now();render()}else fails++;busy=false}).catch(function(){busy=false;fails++})}
function loop(){poll();timer=setTimeout(loop,fails>=3?180000:EVERY)}
document.addEventListener('visibilitychange',function(){if(!document.hidden){clearTimeout(timer);loop()}});
setTimeout(loop,2500)})();</script>"""

JS = JS + LIVE_JS

CSS = """<style>
.pc{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:10px 14px;margin:0 0 12px}.pc-h{display:flex;align-items:center;gap:10px;font-size:14px}.pc-h span{color:var(--mu);font-size:11.5px;flex:1}
.pc-h button{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;width:28px;height:28px;font-size:15px;cursor:pointer}.pc-h button.spin{animation:pcs .8s linear infinite}@keyframes pcs{to{transform:rotate(360deg)}}
.pc-tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0}.pc-tabs button{display:flex;align-items:baseline;justify-content:center;gap:8px;padding:8px 10px;border:1px solid var(--bd);border-radius:12px;background:var(--bg);color:var(--tx);font:inherit;cursor:pointer;transition:.15s}
.pc-tabs button b{font-size:14px}.pc-tabs button span{font-size:15px;font-weight:800}.pc-tabs button.on{border-color:var(--tx);box-shadow:0 0 0 1px var(--tx);background:var(--card)}
.pc-panel[hidden]{display:none}.pc-panel{animation:pcf .2s ease-out}@keyframes pcf{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.pc-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:620px){.pc-cols{grid-template-columns:1fr;gap:6px}}
.pc-tt{font-size:13px;line-height:1.4;margin:2px 0 6px}.pc-tt small{color:var(--mu);font-size:11px;margin-left:4px}.pc-st{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin:6px 0 3px}
.pc-r{display:grid;grid-template-columns:96px 1fr 84px;gap:6px;align-items:center;font-size:11.5px;margin:2px 0}.pc-n{color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pc-bar{position:relative;height:9px;background:var(--bd);border-radius:99px;overflow:hidden}.pc-bar i{position:absolute;top:0;height:100%;border-radius:99px}.pc-bar u{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--tx);opacity:.4}.pc-r b{text-align:right;font-size:11px}
.pc-nota{font-size:10.5px;color:var(--mu);margin-top:3px}.pc-chips{display:flex;flex-wrap:wrap;gap:5px}.pc-chip{font-size:11px;border:1px solid;border-radius:99px;padding:1px 8px;background:var(--bg)}.pc-chip em{font-style:normal;font-weight:700}
.pc-news{margin-top:8px;border-top:1px solid var(--bd);padding-top:6px}.pc-nt{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px}
.pc-n2{display:grid;grid-template-columns:20px 1fr;column-gap:6px;font-size:12.5px;line-height:1.35;color:var(--tx);text-decoration:none;padding:3px 0}.pc-n2 span{overflow:hidden;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical}.pc-n2 small{grid-column:2;color:var(--mu);font-size:10.5px}
.pc-info{margin-top:6px;font-size:12px;line-height:1.45}.pc-info summary{cursor:pointer;color:var(--mu)}.pc-info summary i{display:inline-block;width:16px;height:16px;line-height:16px;text-align:center;border-radius:50%;background:var(--mu);color:var(--bg);font-style:normal;font-size:10px;margin-right:5px}
.pc-t{font-size:12.5px;color:var(--mu);margin-top:4px}
</style>"""
