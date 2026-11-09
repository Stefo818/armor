"""Archivio dati (pagina «Archivio dati» dell'app): che cosa Armor registra giorno per giorno per migliorare il modello in futuro.
Il valore sta soprattutto nei dati che NON si possono ricostruire dopo (opzioni, prezzi per sede, tono delle notizie, revisioni degli utili) e che chi li vende
fa pagare: Armor li raccoglie gratis un giorno alla volta. Contenuto: (1) catalogo di cosa si registra, da quando e quanti giorni; (2) tabella giorno per giorno
con scelta del gruppo di colonne; (3) CSV completo scaricabile. Non cambia nessuna previsione."""
import html as _h

import pandas as pd

from . import store
from .config import ARCHIVE, DATA

LIVE_DAILY = ARCHIVE / "live_daily.csv"
OPZIONI = ARCHIVE / "spy_options_summary.csv"
REGISTRO = DATA / "registry" / "daily.csv"

# gruppo -> (titolo, colonne [(id, etichetta, origine, decimali)])
# origine: ("serie", chiave) | ("opz", colonna) | ("live", colonna) | ("reg", colonna)
GRUPPI = {
    "vol": ("Volatilità implicita", [("vix", "VIX", ("serie", "vix"), 2), ("vix9d", "VIX 9 giorni", ("serie", "vix9d"), 2), ("vix3m", "VIX 3 mesi", ("serie", "vix3m"), 2),
                                     ("vix6m", "VIX 6 mesi", ("serie", "vix6m"), 2), ("vvix", "VVIX", ("serie", "vvix"), 1), ("skew", "SKEW", ("serie", "skew"), 1), ("move", "MOVE (tassi)", ("serie", "move"), 1)]),
    "opz": ("Opzioni SPY (solo da quando registriamo)", [("pc_volume", "Put/call volumi", ("opz", "pc_volume"), 2), ("pc_oi", "Put/call open interest", ("opz", "pc_open_interest"), 2),
                                                         ("iv30", "IV a 30 giorni", ("opz", "iv_atm_30d"), 3), ("sk90", "Skew put 90%", ("opz", "put_skew_90"), 3), ("sk80", "Skew put 80%", ("opz", "put_skew_80"), 3),
                                                         ("ivb", "IV breve (~7 g)", ("opz", "iv_atm_breve"), 3), ("ivl", "IV lunga", ("opz", "iv_atm_lunga"), 3), ("nc", "Contratti", ("opz", "n_contratti"), 0)]),
    "sedi": ("Prezzi per sede e futures (solo da quando registriamo)", [("vw", "VWCE €", ("live", "vwce"), 2), ("sede", "Sede ultimo scambio", ("live", "vwce_sede"), None), ("ns", "Sedi lette", ("live", "n_sedi"), 0),
                                                                      ("spr", "Spread tra sedi %", ("live", "spread_sedi_pct"), 3), ("es", "Futures S&P", ("live", "sp_fut"), 2), ("eur", "EUR/USD", ("live", "eurusd"), 4)]),
    "sent": ("Sentimento e notizie", [("fg", "Fear & Greed", ("serie", "fear_greed"), 0), ("rev", "Revisioni utili (diffusione)", ("serie", "rev_breadth"), 1),
                                      ("nt", "Tono notizie macro", ("reg", "news_sent_macro"), 2), ("nn", "Notizie lette", ("reg", "news_n"), 0)]),
    "cred": ("Credito e macro", [("hy", "Spread High Yield", ("serie", "hy_oas"), 2), ("baa", "Spread BAA-10Y", ("serie", "baa10y"), 2), ("cur", "Curva 10Y-3M", ("serie", "t10y3m"), 2), ("nf", "NFCI", ("serie", "nfci"), 2)]),
    "mod": ("Modelli Armor", [("aix", "Indice Armor", ("reg", "armor_index"), 0), ("p1", "Prob. calo 1 mese", ("reg", "p_1m"), 3), ("p3", "Prob. calo 3 mesi", ("reg", "p_3m"), 3), ("p6", "Prob. calo 6 mesi", ("reg", "p_6m"), 3)]),
}

# catalogo: (nome, gruppo, perché serve, tipo, a pagamento altrove, origine)   tipo: "storico" (ricostruibile) | "da oggi" (solo giorno per giorno)
CATALOGO = [
    ("VIX e curva a termine (9 giorni, 3 e 6 mesi)", "Volatilità", "Paura attesa dal mercato a più scadenze: forma della curva e premio rispetto alla volatilità realizzata.", "storico", False, ("serie", "vix6m")),
    ("VVIX e SKEW", "Volatilità", "Quanto è incerta la volatilità e quanto il mercato paga per proteggersi dai crolli.", "storico", False, ("serie", "skew")),
    ("MOVE (volatilità dei tassi)", "Volatilità", "Stress sul mercato obbligazionario, spesso in anticipo sulle azioni.", "storico", False, ("serie", "move")),
    ("Opzioni SPY: put/call, IV a 30 giorni, skew, struttura a termine", "Opzioni", "Cosa si aspettano e di cosa si proteggono i professionisti. Lo storico dei dati sulle opzioni si compra; qui si accumula un giorno alla volta.", "da oggi", True, ("opz", "iv_atm_30d")),
    ("Catena completa delle opzioni SPY (file giornaliero)", "Opzioni", "Tutti i contratti di ogni giorno: permette di ricalcolare in futuro qualunque misura (smile, superficie di volatilità).", "da oggi", True, ("catene", "")),
    ("Prezzo del VWCE per sede e spread tra sedi", "Prezzi", "Dati di dettaglio che non si ritrovano dopo: serve a capire lo scostamento tra le sedi e il prezzo vero di chiusura.", "da oggi", True, ("live", "vwce")),
    ("Futures S&P 500 e cambio EUR/USD a fine giornata", "Prezzi", "Cosa succede fuori orario di Wall Street e quanto pesa il cambio sul VWCE in euro.", "da oggi", False, ("live", "sp_fut")),
    ("Fear & Greed", "Sentimento", "Sintesi del sentimento di mercato (7 misure).", "storico", False, ("serie", "fear_greed")),
    ("Revisioni delle stime sugli utili", "Sentimento", "Se gli analisti alzano o abbassano le stime: anticipa gli utili reali. Lo storico è a pagamento.", "da oggi", True, ("serie", "rev_breadth")),
    ("Tono delle notizie (macro)", "Sentimento", "Giudizio automatico positivo/negativo dei titoli del giorno. Le notizie di ieri non si recuperano più.", "da oggi", True, ("reg", "news_sent_macro")),
    ("Spread High Yield, BAA-10Y, curva 10Y-3M, NFCI", "Credito e macro", "Stress del credito e condizioni finanziarie: spesso peggiorano prima dei cali.", "storico", False, ("serie", "hy_oas")),
    ("Previsioni dei modelli e Indice Armor", "Modelli", "Cosa prevedeva Armor ogni giorno e con quali dati: serve a misurare gli errori veri.", "da oggi", False, ("reg", "armor_index")),
]


def _leggi(path) -> pd.DataFrame:
    try:
        d = pd.read_csv(path)
        d["date"] = pd.to_datetime(d["date"])
        return d.drop_duplicates("date", keep="last").set_index("date").sort_index()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def sorgenti() -> dict:
    return {"opz": _leggi(OPZIONI), "live": _leggi(LIVE_DAILY), "reg": _leggi(REGISTRO)}


def colonna(orig: tuple, src: dict) -> pd.Series:
    tipo, k = orig
    if tipo == "serie":
        try:
            s = store.load(k).dropna()
            return s[~s.index.duplicated(keep="last")]
        except Exception:  # noqa: BLE001
            return pd.Series(dtype=float)
    d = src.get(tipo)
    if d is None or d.empty or k not in d:
        return pd.Series(dtype=float)
    return d[k]


def tabella(src: dict | None = None, giorni: int | None = 60) -> pd.DataFrame:
    """Una riga per ogni giorno di borsa (date dell'S&P 500), una colonna per ogni dato registrato; le celle vuote = dato non disponibile quel giorno."""
    src = src or sorgenti()
    cols = {}
    for g, (_t, items) in GRUPPI.items():
        for cid, _lab, orig, _dec in items:
            cols[(g, cid)] = colonna(orig, src)
    base = store.load("sp500").dropna().index
    d = pd.DataFrame({k: v.reindex(base) for k, v in cols.items()})
    d = d[d.notna().any(axis=1)].sort_index()
    return d.iloc[-giorni:] if giorni else d


def catalogo_righe(src: dict | None = None) -> list[dict]:
    src = src or sorgenti()
    out = []
    for nome, grp, perche, tipo, paga, orig in CATALOGO:
        if orig[0] == "catene":
            files = sorted((ARCHIVE / "chains").glob("spy_*.csv.gz")) if (ARCHIVE / "chains").exists() else []
            n, da, a, last = len(files), (files[0].stem.split("_")[1][:10] if files else None), (files[-1].stem.split("_")[1][:10] if files else None), f"{len(files)} file"
        else:
            s = colonna(orig, src).dropna()
            n, da, a = len(s), (str(s.index[0].date()) if len(s) else None), (str(s.index[-1].date()) if len(s) else None)
            last = None if not len(s) else (f"{s.iloc[-1]:.4g}")
        out.append({"nome": nome, "gruppo": grp, "perche": perche, "tipo": tipo, "paga": paga, "n": n, "da": da, "a": a, "ultimo": last})
    return out


def _fmt(v, dec):
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    if dec is None:
        return _h.escape(str(v))
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def nasc(g: str) -> str:
    """Attributo che nasconde le colonne dei gruppi non selezionati (all'apertura è mostrato solo il primo)."""
    return "" if g == "vol" else ' style="display:none"'


def html(src: dict | None = None, giorni: int = 60) -> str:
    src = src or sorgenti()
    cat = catalogo_righe(src)
    e = _h.escape
    righe = ""
    for r in cat:
        tag = ("<span class='badge warn'>solo da oggi</span>" if r["tipo"] == "da oggi" else "<span class='badge ok'>storico completo</span>")
        paga = " <span class='badge bad'>a pagamento altrove</span>" if r["paga"] else ""
        righe += (f"<div class='arcr'><div><b>{e(r['nome'])}</b> {tag}{paga}</div><div class='mu'>{e(r['perche'])}</div>"
                  f"<div class='mu'>{'Da ' + e(r['da']) + ' · ' if r['da'] else 'Non ancora registrato · '}{r['n']} {'giorni' if r['gruppo'] != 'Opzioni' or 'Catena' not in r['nome'] else 'file'}"
                  f"{' · ultimo ' + e(r['a']) if r['a'] else ''}{' · valore ' + e(r['ultimo']) if r['ultimo'] and 'file' not in str(r['ultimo']) else ''}</div></div>")
    t = tabella(src, giorni)
    chips = "".join(f"<button class='chip{' on' if g == 'vol' else ''}' data-arcg='{g}'>{e(tit)}</button>" for g, (tit, _i) in GRUPPI.items())
    heads, body = {}, []
    for g, (_tit, items) in GRUPPI.items():
        heads[g] = "".join(f"<th data-g='{g}'{nasc(g)}>{e(lab)}</th>" for _c, lab, _o, _d in items)
    for d, row in t.iloc[::-1].iterrows():
        tds = ""
        for g, (_tit, items) in GRUPPI.items():
            for cid, _lab, _o, dec in items:
                tds += f"<td data-g='{g}'{nasc(g)}>{_fmt(row.get((g, cid)), dec)}</td>"
        body.append(f"<tr><td>{d.strftime('%d/%m/%y')}</td>{tds}</tr>")
    tab = (f"<div class='scroll'><table class='arctab'><thead><tr><th>Giorno</th>{''.join(heads.values())}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
           if body else "<p class='muted'>Ancora nessun dato registrato.</p>")
    return ("<h2>Archivio dati: cosa registra Armor ogni giorno</h2>"
            "<div class='explain'><p><b>A cosa serve.</b> Per migliorare l'algoritmo servono dati veri, raccolti giorno per giorno. Alcuni si possono scaricare anche per il passato; "
            "altri (opzioni, prezzi per sede, notizie, revisioni degli utili) <b>non si ritrovano dopo</b>, e chi ha lo storico lo vende. Armor li raccoglie gratis, un giorno alla volta: "
            "tra qualche mese saranno la base per capire se migliorano le previsioni. Finché sono pochi giorni, non si traggono conclusioni.</p></div>"
            f"<div class='card'>{righe}</div>"
            f"<h3>Giorno per giorno (ultimi {giorni} giorni di borsa)</h3><div class='chips arcchips'>{chips}</div>{tab}"
            "<p><a class='btn' href='archivio_dati.csv' download='armor_archivio_dati.csv'>Scarica tutto (CSV)</a></p>"
            "<p class='muted'>Le celle con «–» sono dati non disponibili quel giorno. I dati mensili o settimanali compaiono solo nei giorni in cui si aggiornano.</p>")


def csv_text(src: dict | None = None) -> str:
    t = tabella(src, None)
    t.columns = [f"{g}_{c}" for g, c in t.columns]
    t.index.name = "date"
    return t.to_csv(float_format="%.6g")


CSS = ".arcr{padding:8px 0;border-top:1px solid var(--bd)}.arcr:first-child{border-top:0}.arctab td,.arctab th{white-space:nowrap;font-size:13px}.arctab thead th{position:sticky;top:0;background:var(--card)}.arcchips{margin:6px 0}"
JS = r"""<script>document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-arcg]');if(!b)return;var g=b.dataset.arcg,box=b.closest('.chips');
box.querySelectorAll('.chip').forEach(function(c){c.classList.toggle('on',c===b)});var tb=document.querySelector('.arctab');if(!tb)return;
tb.querySelectorAll('[data-g]').forEach(function(c){c.style.display=c.dataset.g===g?'':'none'});
tb.querySelectorAll('tbody tr').forEach(function(r){var has=false;r.querySelectorAll('td[data-g="'+g+'"]').forEach(function(c){if(c.textContent.trim()!=='–')has=true});r.style.display=has?'':'none'})});</script>"""


# ------------------------------------------------------------------ registrazione giornaliera dei prezzi per sede
def registra_live(live: dict | None = None, path=None) -> bool:
    """Una riga al giorno (l'ultima lettura vince): VWCE con sede e spread tra le sedi, futures, VIX, cambio. Chiamata dal ciclo giornaliero."""
    if live is None:
        from . import live as livemod
        live = livemod.load()
    q = (live or {}).get("quotes") or {}
    v = q.get("vwce")
    if not v or not v.get("time"):
        return False
    alts = v.get("alts") or {}
    prezzi = [a[0] for a in alts.values() if a and a[0]]
    row = {"date": str(v["time"])[:10], "vwce": v["price"], "vwce_sede": v.get("venue", ""), "vwce_ora": v["time"], "n_sedi": len(prezzi),
           "vwce_min_sedi": min(prezzi) if prezzi else "", "vwce_max_sedi": max(prezzi) if prezzi else "",
           "spread_sedi_pct": round((max(prezzi) / min(prezzi) - 1) * 100, 4) if len(prezzi) >= 2 else "",
           "sp500": (q.get("sp500") or {}).get("price", ""), "sp_fut": (q.get("sp_fut") or {}).get("price", ""),
           "vix": (q.get("vix") or {}).get("price", ""), "eurusd": (q.get("eurusd") or {}).get("price", "")}
    path = path or LIVE_DAILY
    path.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame([row])]).drop_duplicates("date", keep="last").sort_values("date").to_csv(path, index=False)
    return True
