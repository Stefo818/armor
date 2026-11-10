"""Grandi fondi con nome (Patch 82): quali fondi guardiamo, cosa hanno fatto nell'ultimo trimestre (13F della SEC), che strategia seguono e le notizie che li riguardano.
Le posizioni vengono dai depositi 13F: sono una FOTO a fine trimestre, pubblicata fino a 45 giorni dopo, solo su titoli e opzioni quotati negli USA. Non mostrano ciò che il fondo fa oggi.
Lo stile («strategia») è la descrizione generale e nota di ogni fondo, non è dedotta dai dati. La parte «cosa ha fatto» invece è calcolata dai dati."""
import html as _h
import re

import numpy as np
import pandas as pd

from .config import DATA

FILE = DATA / "grandi_fondi" / "f13_roster.csv"
TOP_POS = 60   # posizioni conservate per fondo e trimestre
# id: (nome, espressione per riconoscere il depositante nel 13F, stile, cosa fa, come leggerlo, interroga news)
ROSTER = {
    "berkshire": ("Berkshire Hathaway", r"^BERKSHIRE HATHAWAY INC", "Valore concentrato", "Compra poche aziende solide a un prezzo che ritiene conveniente e le tiene per anni. Quando non trova affari lascia accumulare liquidità.",
                  "Se vende più di quanto compra, di solito non trova prezzi convenienti: non è un allarme, è prudenza."),
    "vanguard": ("Vanguard", r"^VANGUARD GROUP INC", "Indicizzato (passivo)", "Gestisce fondi che copiano gli indici: non sceglie i titoli. Le sue variazioni seguono i soldi che i risparmiatori mettono o tolgono.",
                 "Comprare o vendere qui non è un giudizio sul mercato: riflette gli afflussi dei clienti."),
    "blackrock": ("BlackRock", r"^BLACKROCK,? INC", "Indicizzato + gestione attiva", "Il più grande gestore al mondo (ETF iShares). Per lo più copia gli indici, con una parte di gestione attiva.",
                  "Le variazioni seguono soprattutto gli afflussi nei suoi ETF."),
    "statestreet": ("State Street", r"^STATE STREET CORP", "Indicizzato (passivo)", "Gestore degli ETF SPDR, tra cui SPY, il più scambiato sull'S&P 500. Copia gli indici.",
                    "Come per Vanguard, le mosse riflettono gli afflussi dei clienti."),
    "bridgewater": ("Bridgewater Associates", r"^BRIDGEWATER ASSOCIATES", "Macro (economia e tassi)", "Investe guardando economia, inflazione e tassi di tutto il mondo e bilancia il rischio tra azioni, obbligazioni e materie prime.",
                    "Il 13F mostra solo la parte americana quotata: è una piccola finestra sul fondo."),
    "renaissance": ("Renaissance Technologies", r"^RENAISSANCE TECHNOLOGIES", "Quantitativo (modelli matematici)", "Usa modelli matematici e moltissime piccole scommesse di breve durata.",
                    "Le posizioni cambiano molto da un trimestre all'altro: leggere i singoli titoli dice poco, conta il quadro generale."),
    "citadel": ("Citadel Advisors", r"^CITADEL ADVISORS", "Multi-strategia", "Molte squadre che fanno strategie diverse (azioni, opzioni, relative value) con rischio molto controllato.",
                "Ha tante opzioni: put e call servono spesso a coprirsi, non a scommettere in una direzione."),
    "millennium": ("Millennium Management", r"^MILLENNIUM MANAGEMENT", "Multi-strategia", "Centinaia di squadre indipendenti, ognuna con un rischio limitato. Posizioni molto frammentate.",
                   "Come Citadel: le opzioni sono spesso coperture."),
    "twosigma": ("Two Sigma", r"^TWO SIGMA INVESTMENTS", "Quantitativo (dati e algoritmi)", "Usa grandi quantità di dati e modelli automatici per scegliere i titoli.",
                 "Molte posizioni piccole: guarda il quadro generale."),
    "deshaw": ("D. E. Shaw", r"^D\.? ?E\.? SHAW & CO", "Quantitativo + discrezionale", "Unisce modelli matematici e scelte dei gestori su azioni, opzioni e altro.", "Molte posizioni e opzioni: guarda il quadro generale."),
    "aqr": ("AQR Capital", r"^AQR CAPITAL MANAGEMENT", "Quantitativo (fattori)", "Compra titoli con caratteristiche che storicamente rendono di più: prezzi bassi, slancio, qualità.", "Cambia in modo graduale e per regole: sorprese rare."),
    "point72": ("Point72", r"^POINT72 ASSET MANAGEMENT", "Azioni long/short", "Compra titoli che ritiene sottovalutati e scommette al ribasso su altri, con molte squadre di analisti.", "Posizioni numerose e variabili."),
    "soros": ("Soros Fund Management", r"^SOROS FUND MANAGEMENT", "Macro tattico", "Investe in modo flessibile seguendo le tendenze dell'economia e dei mercati; cambia idea in fretta.", "Le sue mosse sono spesso tattiche, di pochi mesi."),
    "tiger": ("Tiger Global", r"^TIGER GLOBAL MANAGEMENT", "Crescita (tecnologia)", "Punta su aziende tecnologiche e internet in forte crescita, con posizioni concentrate.", "Molto sensibile ai tassi: quando salgono, tende a ridurre."),
    "pershing": ("Pershing Square", r"^PERSHING SQUARE CAPITAL", "Attivista concentrato", "Poche grandi posizioni su aziende di qualità, a volte con pressioni sui vertici per cambiare strategia.", "Ogni singola mossa pesa molto: poche posizioni, grandi quote."),
    "thirdpoint": ("Third Point", r"^THIRD POINT LLC", "Attivista / eventi societari", "Cerca aziende dove può cambiare qualcosa (fusioni, nuovi dirigenti) e spinge perché accada.", "Poche posizioni importanti."),
    "elliott": ("Elliott", r"^ELLIOTT INVESTMENT MANAGEMENT", "Attivista", "Entra nel capitale di aziende che ritiene gestite male e spinge per cambiare.", "Le sue mosse arrivano spesso con notizie sull'azienda."),
    "coatue": ("Coatue", r"^COATUE MANAGEMENT", "Crescita (tecnologia)", "Scommette su tecnologia e società in crescita, con posizioni lunghe e corte.", "Come Tiger Global: più prudente quando i tassi salgono."),
}
PREFISSI = {"INC", "CORP", "CO", "LTD", "PLC", "COM", "CL", "CLASS", "NEW", "THE", "HLDGS", "HOLDINGS", "GROUP", "SPONSORED", "ADR", "SHS", "ORD", "A", "B", "C"}


def riconosci(nome: str) -> str | None:
    n = str(nome or "").upper().strip()
    for k, (_a, rx, *_r) in ROSTER.items():
        if re.search(rx, n):
            return k
    return None


def pulisci(n: str) -> str:
    parole = [w for w in re.sub(r"[^A-Za-z0-9&\. ]", " ", str(n)).split() if w.upper().strip(".") not in PREFISSI]
    s = " ".join(parole[:3]).title() or str(n).title()
    return s.replace("&", "&")


def carica() -> pd.DataFrame:
    try:
        return pd.read_csv(FILE, parse_dates=["periodo"], dtype={"cusip": str, "putcall": str}).fillna({"putcall": ""})
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def analizza_fondo(cur: pd.DataFrame, prev: pd.DataFrame | None) -> dict:
    """Da due trimestri di posizioni (colonne: issuer, cusip, putcall, value, shares, tot) a cosa ha fatto il fondo."""
    azioni = cur[cur["putcall"] == ""]
    tot = float(cur["tot"].iloc[0]) if len(cur) else 0.0
    top = [{"n": pulisci(r.issuer), "pct": r.value / tot * 100 if tot else 0.0} for r in azioni.nlargest(5, "value").itertuples()]
    put = float(cur.loc[cur["putcall"].str.upper() == "PUT", "value"].sum())
    out = {"tot": tot, "n": int(len(azioni)), "top": top, "put_pct": put / tot * 100 if tot else 0.0, "put_prec": None, "flusso": None, "postura": "n.d.", "compra": [], "vende": [], "nuove": [], "chiuse": []}
    if prev is None or not len(prev):
        return out
    tot0 = float(prev["tot"].iloc[0])
    out["put_prec"] = float(prev.loc[prev["putcall"].str.upper() == "PUT", "value"].sum()) / tot0 * 100 if tot0 else 0.0
    a0 = prev[prev["putcall"] == ""].set_index("cusip")
    a1 = azioni.set_index("cusip")
    flussi = []
    for c in a1.index.union(a0.index):
        in1, in0 = c in a1.index, c in a0.index
        if in1 and in0:
            s1, s0 = float(a1.at[c, "shares"]), float(a0.at[c, "shares"])
            if s0 <= 0 or s1 <= 0:
                continue
            var = s1 / s0 - 1
            if var > 3:   # salto enorme: quasi sempre un frazionamento delle azioni, non un acquisto
                continue
            f = (s1 - s0) * float(a1.at[c, "value"]) / s1
            flussi.append((pulisci(a1.at[c, "issuer"]), f, var))
        elif in1:
            v = float(a1.at[c, "value"])
            if tot and v / tot >= 0.01:
                out["nuove"].append(pulisci(a1.at[c, "issuer"]))
            flussi.append((pulisci(a1.at[c, "issuer"]), v, None))
        else:
            v = float(a0.at[c, "value"])
            if tot0 and v / tot0 >= 0.01:
                out["chiuse"].append(pulisci(a0.at[c, "issuer"]))
            flussi.append((pulisci(a0.at[c, "issuer"]), -v, None))
    netto = sum(f for _n, f, _v in flussi)
    out["flusso"] = netto / tot0 * 100 if tot0 else None
    ordine = sorted(flussi, key=lambda x: -x[1])
    out["compra"] = [{"n": n, "eur": f, "var": v} for n, f, v in ordine[:3] if f > 0]
    out["vende"] = [{"n": n, "eur": f, "var": v} for n, f, v in ordine[::-1][:3] if f < 0]
    fl = out["flusso"]
    out["postura"] = "n.d." if fl is None else "compra" if fl > 1.5 else "vende" if fl < -1.5 else "stabile"
    return out


def _m(x: float) -> str:
    """Valore in dollari in forma leggibile."""
    a = abs(x)
    s = f"{a / 1e9:.1f} mld $" if a >= 1e9 else f"{a / 1e6:.0f} mln $"
    return s.replace(".", ",")


def frase(info: dict) -> str:
    """Una frase semplice su cosa ha fatto il fondo nell'ultimo trimestre."""
    if info["postura"] == "n.d.":
        return "Dati dell'ultimo trimestre non ancora disponibili."
    p = {"compra": "Nel complesso ha comprato", "vende": "Nel complesso ha venduto", "stabile": "Nel complesso è rimasto fermo"}[info["postura"]]
    s = p + (f" (circa {abs(info['flusso']):.1f}% del portafoglio)".replace(".", ",") if info["postura"] != "stabile" else "") + "."
    if info["compra"]:
        s += " Ha aumentato soprattutto " + ", ".join(x["n"] for x in info["compra"][:2]) + "."
    if info["vende"]:
        s += " Ha ridotto soprattutto " + ", ".join(x["n"] for x in info["vende"][:2]) + "."
    if info["nuove"]:
        s += " Nuovo tra le posizioni principali: " + ", ".join(info["nuove"][:2]) + "."
    if info["chiuse"]:
        s += " Uscito: " + ", ".join(info["chiuse"][:2]) + "."
    if info["put_prec"] is not None and abs(info["put_pct"] - info["put_prec"]) >= 0.5:
        s += f" Coperture con opzioni put: {info['put_pct']:.1f}% del portafoglio (prima {info['put_prec']:.1f}%)".replace(".", ",") + (": più prudente." if info["put_pct"] > info["put_prec"] else ": meno prudente.")
    return s


def breve(testo: str, n: int = 150) -> str:
    """Frasi intere fino a circa n caratteri (mai tagliate a metà)."""
    out = ""
    for fr in re.split(r"(?<=\.)\s+", testo):
        if out and len(out) + len(fr) + 1 > n:
            break
        out = (out + " " + fr).strip()
    return out


def costruisci(df: pd.DataFrame | None = None) -> dict:
    """{id: info del fondo} per ogni fondo del roster; chi non ha dati ha postura n.d."""
    df = carica() if df is None else df
    out = {}
    for k, (nome, _rx, stile, fa, guarda) in ROSTER.items():
        base = {"id": k, "nome": nome, "stile": stile, "fa": fa, "guarda": guarda, "periodo": None, "prec": None}
        g = df[df["fondo"] == k] if len(df) else df
        if len(g):
            per = sorted(g["periodo"].unique())
            cur = g[g["periodo"] == per[-1]]
            prev = g[g["periodo"] == per[-2]] if len(per) > 1 else None
            base.update(analizza_fondo(cur, prev), periodo=str(pd.Timestamp(per[-1]).date()), prec=str(pd.Timestamp(per[-2]).date()) if len(per) > 1 else None)
            base["frase"] = frase(base)
        else:
            base.update(tot=0.0, n=0, top=[], put_pct=0.0, put_prec=None, flusso=None, postura="n.d.", compra=[], vende=[], nuove=[], chiuse=[], frase="Dati dell'ultimo trimestre non ancora disponibili.")
        out[k] = base
    return out


# ---------- notizie ----------
def _prima_parola(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower().split(" ")[0]) if str(s).strip() else ""


def notizie_di(fondo: dict, items: list[dict]) -> list[dict]:
    """Notizie sul fondo stesso e sulle sue prime posizioni (se tra le aziende seguite), con tono positivo/neutro/negativo."""
    sue = [dict(i, rel="fondo") for i in items if i.get("kind") == "fondo" and i.get("fondo") == fondo["id"]]
    prime = {_prima_parola(x["n"]) for x in fondo.get("top", [])}
    pos = []
    for i in items:
        if i.get("kind") == "company":
            nome = re.sub(r"\s*\(.*$", "", i.get("group", ""))
            if _prima_parola(nome) in prime and _prima_parola(nome):
                pos.append(dict(i, rel="posizione", azienda=nome))
    out = sue + pos
    out.sort(key=lambda x: -x.get("score", 0))
    return out[:6]


COL = {"positivo": "#16a34a", "negativo": "#dc2626", "neutro": "#64748b"}
POSTURA = {"compra": ("Compra", "#16a34a"), "vende": ("Vende", "#dc2626"), "stabile": ("Stabile", "#64748b"), "n.d.": ("Dati in arrivo", "#94a3b8")}


def html(info: dict | None = None, items: list[dict] | None = None) -> str:
    E = _h.escape
    info = costruisci() if info is None else info
    if items is None:
        try:
            from . import news
            items = news.load_latest().get("items", [])
        except Exception:  # noqa: BLE001
            items = []
    con_dati = [x for x in info.values() if x["postura"] != "n.d."]
    nc = sum(x["postura"] == "compra" for x in con_dati)
    nv = sum(x["postura"] == "vende" for x in con_dati)
    sommario = (f"<p class='fn-sum'>Dei <b>{len(con_dati)}</b> fondi con dati recenti: <b style='color:{COL['positivo']}'>{nc} comprano</b>, <b style='color:{COL['negativo']}'>{nv} vendono</b>, {len(con_dati) - nc - nv} sono fermi.</p>"
                if con_dati else "<p class='fn-sum'>I depositi trimestrali della SEC si caricano ogni settimana: le schede si completano man mano. Intanto trovi stile e notizie.</p>")
    cards = ""
    tutte = []
    for k, f in info.items():
        lab, col = POSTURA[f["postura"]]
        notizie = notizie_di(f, items)
        tutte += [dict(n, fondo_nome=f["nome"]) for n in notizie if n.get("rel") == "fondo"]
        if f["top"]:
            mx = max(x["pct"] for x in f["top"]) or 1
            top = "".join(f"<div class='fn-p'><span>{E(x['n'])}</span><div><i style='width:{x['pct'] / mx * 100:.0f}%'></i></div><b>{x['pct']:.1f}%</b></div>".replace(".", ",") for x in f["top"])
            top = f"<div class='fn-st'>Posizioni principali (quota del portafoglio)</div>{top}"
        else:
            top = ""
        news_h = ""
        for n in notizie:
            c = COL.get(n.get("label", "neutro"), COL["neutro"])
            ru = f"Sul fondo" if n["rel"] == "fondo" else f"Su {E(n.get('azienda', ''))}, una sua posizione"
            ver = {"positivo": "positiva", "negativo": "negativa", "neutro": "neutra"}.get(n.get("label", "neutro"), "neutra")
            news_h += (f"<a class='fn-n' href='{E(n.get('link', '#'))}' target='_blank' rel='noopener' style='border-left-color:{c}'><span>{E(n['title'][:120])}</span>"
                       f"<small>{ru} · notizia <b style='color:{c}'>{ver}</b> · {E(n.get('source', ''))}</small></a>")
        news_h = f"<div class='fn-st'>Notizie</div>{news_h}" if news_h else ""
        quando = f"Foto al {E(f['periodo'])}" if f["periodo"] else "In attesa dei dati"
        cards += (f"<details class='fn-c' style='border-left:5px solid {col}'><summary><div class='fn-h'><b>{E(f['nome'])}</b><em class='fn-tag'>{E(f['stile'])}</em></div>"
                  f"<div class='fn-sm'><span class='fn-ps' style='background:{col}'>{lab}</span><small>{E(breve(f['frase']))}</small></div></summary>"
                  f"<div class='fn-b'><div class='fn-st'>Strategia</div><p>{E(f['fa'])}</p><p class='fn-g'><b>Come leggerlo.</b> {E(f['guarda'])}</p>"
                  f"<div class='fn-st'>Cosa ha fatto ({quando})</div><p>{E(f['frase'])}</p>{top}{news_h}</div></details>")
    tutte.sort(key=lambda x: -x.get("score", 0))
    feed = "".join(f"<a class='fn-n' href='{E(n.get('link', '#'))}' target='_blank' rel='noopener' style='border-left-color:{COL.get(n.get('label', 'neutro'), COL['neutro'])}'><span>{E(n['title'][:130])}</span><small><b>{E(n['fondo_nome'])}</b> · {E(n.get('source', ''))}</small></a>" for n in tutte[:8])
    feed = f"<h4 class='fn-h4'>Ultime notizie sui fondi</h4>{feed}" if feed else ""
    key = (f"<div class='fn-key'><span><i style='background:{COL['positivo']}'></i>Verde: positivo (acquista, notizia favorevole)</span><span><i style='background:{COL['negativo']}'></i>Rosso: negativo (vende, notizia sfavorevole)</span>"
           f"<span><i style='background:{COL['neutro']}'></i>Grigio: neutro o stabile</span></div>")
    avviso = ("<div class='explain'><p><b>Attenzione a cosa guardi.</b> Le posizioni dei fondi arrivano dal modulo 13F della SEC: sono una <b>foto di fine trimestre, pubblicata fino a 45 giorni dopo</b>, e riguardano solo titoli e opzioni quotati negli Stati Uniti. "
              "Non dicono cosa il fondo fa oggi. Il colore «Compra» o «Vende» riassume solo il trimestre passato. La strategia è la descrizione generale del fondo, non è dedotta dai dati. "
              "Il tono delle notizie è una stima automatica dei titoli, non un giudizio.</p></div>")
    return CSS + (f"<h3 class='fd-h3'>I fondi che osserviamo: chi sono e cosa stanno facendo</h3>{avviso}{sommario}{key}<div class='fn-grid'>{cards}</div>{feed}")


CSS = """<style>
.fn-sum{font-size:13.5px;margin:6px 0}.fn-key{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;color:var(--mu);margin:6px 0}.fn-key i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px}
.fn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}.fn-c{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:8px 12px;font-size:13px;line-height:1.45}
.fn-c summary{cursor:pointer;list-style:none}.fn-c summary::-webkit-details-marker{display:none}.fn-h{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.fn-h b{font-size:15px}
.fn-tag{font-style:normal;font-size:10.5px;font-weight:700;border:1px solid var(--bd);border-radius:99px;padding:1px 8px;color:var(--mu);background:var(--bg)}
.fn-sm{display:flex;gap:8px;align-items:flex-start;margin-top:5px}.fn-sm small{color:var(--mu);font-size:11.5px;line-height:1.35}.fn-ps{flex:none;color:#fff;font-size:11px;font-weight:800;border-radius:99px;padding:2px 10px}
.fn-b{margin-top:8px;border-top:1px solid var(--bd);padding-top:6px}.fn-b p{margin:4px 0}.fn-g{color:var(--mu);font-size:12.5px}.fn-st{font-size:10.5px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.4px;margin:8px 0 3px}
.fn-p{display:grid;grid-template-columns:110px 1fr 46px;gap:6px;align-items:center;font-size:12px;margin:2px 0}.fn-p div{height:8px;background:var(--bd);border-radius:99px;overflow:hidden}.fn-p i{display:block;height:100%;background:#6366f1;border-radius:99px}.fn-p b{text-align:right}
.fn-n{display:flex;flex-direction:column;gap:1px;border-left:4px solid;padding:3px 8px;margin:4px 0;color:var(--tx);text-decoration:none;font-size:12.5px;background:var(--bg);border-radius:0 8px 8px 0}.fn-n small{color:var(--mu);font-size:10.5px}
.fn-h4{margin:14px 0 4px;font-size:14px}
</style>"""
