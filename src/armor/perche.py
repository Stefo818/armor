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
    return {"ora": ora.strftime("%Y-%m-%dT%H:%M:%SZ"), "sp": sp, "vwce": vw, "aperto": bool((quotes.get("sp500") or {}).get("open")), "ok": bool(sp or vw)}


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
    stato = "mercato USA aperto" if d.get("aperto") else "ultimo dato disponibile"
    return (CSS + f"<div class='pc' id='pch'><div class='pc-h'><b>Perché si muove oggi</b><span>aggiornato alle {t} · {stato}</span><button type='button' id='pcr' title='Aggiorna ora'>↻</button></div>"
            f"<div class='pc-tabs'>{tabs}</div>{pan}{info}</div>")


JS = """<script>(function(){var W=document.getElementById('pch');if(!W||W.dataset.on)return;W.dataset.on=1;var cur=null;
function show(){var t=cur||(W.querySelector('.pc-tabs button.on')||{dataset:{}}).dataset.t;if(!t)return;cur=t;W.querySelectorAll('.pc-tabs button').forEach(function(b){b.classList.toggle('on',b.dataset.t===t)});W.querySelectorAll('.pc-panel').forEach(function(p){p.hidden=p.dataset.t!==t})}
function ag(){var r=document.getElementById('pcr');if(r)r.classList.add('spin');fetch('perche.html?'+Date.now(),{cache:'no-store'}).then(function(x){return x.text()}).then(function(h){var t=document.createElement('div');t.innerHTML=h;var n=t.querySelector('#pch');if(n){W.innerHTML=n.innerHTML;show()}}).catch(function(){}).then(function(){var r2=document.getElementById('pcr');if(r2)setTimeout(function(){r2.classList.remove('spin')},600)})}
W.addEventListener('click',function(e){var b=e.target.closest('.pc-tabs button');if(b){cur=b.dataset.t;show();return}if(e.target.closest('#pcr'))ag()});
show();if(location.protocol.indexOf('http')===0)setInterval(ag,300000)})()</script>"""

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
