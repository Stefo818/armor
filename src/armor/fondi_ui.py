"""Pagina «Grandi fondi»: chi sono, cosa stanno facendo, come leggere le loro mosse (Patch 69).
Tutto è informativo: i segnali dei grandi fondi NON pesano sul Super Armor Index finché non superano la prova. In parallelo si calcola un valore di
confronto («Super Armor Index con i grandi fondi al 10%») e lo si segue ogni giorno accanto a quello ufficiale, per decidere nelle prossime settimane."""
import html as _h
import json

import numpy as np
import pandas as pd

from . import grandi_fondi as gf

E = _h.escape

# chiave: (chi sono, cosa vuol dire «alto», cosa vuol dire «basso», dove nasce il dato, unità)
INFO = {
    "cot_lev": ("I fondi speculativi (hedge fund) che usano il debito per scommettere sui futures dell'S&P 500.",
                "Sono molto «comprati» rispetto al solito: tanti sono già dentro e restano pochi nuovi compratori. Se il mercato gira, possono vendere tutti insieme.",
                "Sono molto «venduti» rispetto al solito: scommettono al ribasso o si proteggono. Se il mercato sale, devono ricomprare in fretta e possono spingerlo ancora più su.",
                "CFTC (autorità USA sui futures), rapporto del venerdì sui dati del martedì", "% dei contratti aperti, al netto di chi compra e chi vende"),
    "cot_am": ("I gestori di grandi patrimoni (fondi pensione, assicurazioni, fondi comuni): investitori lenti e di lungo periodo.",
               "Sono molto investiti: la fiducia è già quasi tutta nei prezzi, c'è meno «carburante» per ulteriori acquisti.",
               "Hanno ridotto molto: prudenza forte. Può voler dire che il peggio è già scontato oppure che vedono rischi.",
               "CFTC, rapporto del venerdì sui dati del martedì", "% dei contratti aperti, al netto di chi compra e chi vende"),
    "cot_dealer": ("Gli intermediari (le grandi banche che fanno da controparte a tutti gli altri).",
                   "Hanno molte posizioni comprate perché i clienti stanno vendendo.",
                   "Hanno molte posizioni vendute perché i clienti stanno comprando. Di solito le loro mosse sono lo specchio di quelle degli altri: si leggono insieme ai fondi a leva e ai gestori.",
                   "CFTC, rapporto del venerdì sui dati del martedì", "% dei contratti aperti, al netto di chi compra e chi vende"),
    "mmf": ("I fondi monetari: il «parcheggio» dei soldi che le persone e le aziende tengono al sicuro in attesa.",
            "Tanta liquidità sta entrando nei fondi monetari: prudenza diffusa. È anche «polvere da sparo» per un eventuale ritorno al mercato.",
            "La liquidità sta uscendo dai fondi monetari: i soldi tornano verso azioni e obbligazioni.",
            "Federal Reserve (FRED, serie WRMFNS)", "variazione % degli ultimi 3 mesi del totale dei fondi monetari"),
    "f13_protezione": ("I 50 maggiori gestori americani, osservati nei loro elenchi trimestrali (modulo 13F) alla SEC.",
                       "Si coprono con opzioni put sugli ETF indicizzati più del solito: temono un calo.",
                       "Si coprono meno del solito: più tranquilli.",
                       "SEC, moduli 13F (uno ogni trimestre, depositati entro 45 giorni dalla fine)", "quota delle protezioni sul totale degli ETF indicizzati posseduti"),
    "f13_indicizzati": ("I 50 maggiori gestori americani (13F).",
                        "Tengono una parte più grande in ETF che replicano l'intero mercato: scelte meno selettive.",
                        "Tengono meno ETF e più titoli scelti uno per uno.",
                        "SEC, moduli 13F", "quota degli ETF indicizzati sul totale posseduto"),
    "insider": ("I dirigenti e gli amministratori delle aziende quotate, che comprano o vendono azioni della propria azienda.",
                "I dirigenti comprano più del solito: chi conosce meglio l'azienda ci crede. È uno dei segnali più studiati.",
                "I dirigenti vendono molto: si legge poco, perché spesso vendono per piani programmati o per esigenze personali.",
                "SEC, modulo 4 (comunicazione obbligatoria entro 2 giorni)", "quota degli acquisti sul totale acquisti più vendite, ultime 13 settimane"),
    "d13": ("Gli investitori che superano il 5% di un'azienda quotata con l'intenzione di influenzarla (investitori «attivisti»).",
            "Più investitori attivisti del solito entrano nelle aziende: spesso vedono valore nascosto o vogliono cambiamenti.",
            "Pochi nuovi ingressi attivisti.",
            "SEC, modulo Schedule 13D", "numero di nuovi depositi nelle ultime 13 settimane"),
}
ORDINE = ["cot_lev", "cot_am", "cot_dealer", "mmf", "f13_protezione", "f13_indicizzati", "insider", "d13"]
GRUPPI = [("Futures sull'S&P 500 (ogni settimana)", ["cot_lev", "cot_am", "cot_dealer"]), ("Liquidità parcheggiata", ["mmf"]),
          ("Grandi gestori (ogni trimestre)", ["f13_protezione", "f13_indicizzati"]), ("Chi conosce le aziende dall'interno", ["insider", "d13"])]


def _num(x, d=1):
    return "n.d." if x is None else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _col_t(t: float) -> str:
    """Colore della tensione 0-100: blu (nella norma) → ambra → rosso (molto fuori dalla norma). Non è una scala di pericolo."""
    return f"hsl({int(210 - 2.1 * min(max(t, 0), 100))},70%,52%)"


def _asse(pct, w: int = 100) -> str:
    """Barra 0-100 del percentile con zone «basso» (≤20) e «alto» (≥80) e un segnaposto."""
    if pct is None:
        return "<div class='fd-ax'><span class='fd-nd'>storia ancora troppo corta</span></div>"
    return (f"<div class='fd-ax'><i class='lo'></i><i class='hi'></i><b style='left:{min(max(pct, 1), 99):.0f}%'></b></div>"
            "<div class='fd-axl'><span>molto basso</span><span>nella norma</span><span>molto alto</span></div>")


def _lettura(s: dict) -> tuple[str, str]:
    st = s["stato"]
    return {"alto": ("Alto", "hsl(0,70%,58%)"), "basso": ("Basso", "hsl(210,75%,60%)"), "normale": ("Nella norma", "hsl(150,55%,48%)")}.get(st, ("Storia troppo corta", "var(--mu)"))


def _prova_txt(s: dict) -> str:
    pv = s.get("prova") or {}
    v = str(pv.get("verdetto", "n.d."))
    if v.startswith("dimostrato"):
        return "<b style='color:hsl(150,55%,48%)'>Ha anticipato i cali in entrambe le metà della storia</b>: conta nel valore."
    if v == "nessun segnale dimostrato":
        return "<b>Non ha dimostrato di anticipare i cali</b>: non conta nel valore."
    return "<b>Storia ancora troppo corta</b> per dire se anticipa i cali: non conta nel valore."


def _dopo(s: dict) -> str:
    """Cosa è successo in passato dopo valori alti e bassi (calo ≥5% in 1 mese), con numeri; solo se la prova li ha."""
    b = ((s.get("prova") or {}).get("bersagli") or {}).get("1m_5")
    if not b:
        return ""
    righe = []
    for nome, lab in (("alto", "valore alto (≥ 80°)"), ("basso", "valore basso (≤ 20°)")):
        t = (b.get(nome) or {}).get("tutta") or {}
        if t.get("freq") is None:
            righe.append(f"<tr><td>{lab}</td><td>{t.get('n', 0)} date</td><td colspan='2'>troppo poche per concludere</td></tr>")
        else:
            righe.append(f"<tr><td>{lab}</td><td>{t['n']} date</td><td><b>{t['freq'] * 100:.0f}%</b></td><td>{t['freq_resto'] * 100:.0f}%</td></tr>")
    return ("<table class='fd-tb'><tr><th>Quando il segnale era…</th><th>Date</th><th>Calo ≥5% nel mese dopo</th><th>Negli altri casi</th></tr>" + "".join(righe) + "</table>"
            f"<p class='fd-t2'>In media, dal 2006 (o da quando c'è il dato), un calo ≥5% in un mese è arrivato nel {b['freq_tutte'] * 100:.0f}% dei casi.</p>")


def _delta_txt(s: dict) -> str:
    pr = s.get("precedente")
    if not pr or s.get("percentile") is None:
        return ""
    dv = s["valore"] - pr["valore"]
    dp = s["percentile"] - pr["percentile"]
    fr = "▲" if dp > 0.5 else ("▼" if dp < -0.5 else "=")
    return f"<span class='fd-d'>{fr} rispetto alla lettura precedente ({pr['data'][8:]}/{pr['data'][5:7]}): valore {dv:+.1f}, percentile {dp:+.0f}</span>".replace(".", ",").replace("+-", "-")


def scheda(k: str, s: dict | None) -> str:
    nome = gf.SEGNALI[k][0]
    chi, alto, basso, fonte, unita = INFO[k]
    rit = gf.SEGNALI[k][1]
    if not s:
        stato = "In raccolta: compare dopo i prossimi aggiornamenti dei dati (servono almeno 2 anni di storia per i segnali settimanali e 3 per quelli trimestrali)." if k.startswith(("f13", "mmf")) else "In raccolta: compare dopo i prossimi aggiornamenti dei dati."
        return (f"<div class='fd-c fd-wait'><h4>{E(nome)}</h4><p class='fd-t2'><b>Chi:</b> {E(chi)}</p><p class='fd-t2'>{stato}</p>"
                f"<p class='fd-t2'><b>Se sarà alto:</b> {E(alto)}</p><p class='fd-t2'><b>Se sarà basso:</b> {E(basso)}</p></div>")
    lett, col = _lettura(s)
    pct = s.get("percentile")
    data = json.dumps(s.get("storia") or {}, separators=(",", ":"))
    tri = s.get("trimestre_fa")
    tri_txt = f"<span class='fd-d'>3 mesi fa: {tri['percentile']:.0f}° percentile</span>" if tri else ""
    return (f"<div class='fd-c'><h4>{E(nome)}</h4>"
            f"<div class='fd-top'><div class='fd-big'>{_num(s['valore'])}<small>{E(unita.split(',')[0])}</small></div>"
            f"<div class='fd-pill' style='border-color:{col};color:{col}'>{lett}{'' if pct is None else f' · {pct:.0f}° percentile'}</div></div>"
            f"{_asse(pct)}<div class='fd-dd'>{_delta_txt(s)}{tri_txt}</div>"
            f"<p class='fd-t2'><b>Chi sono.</b> {E(chi)}</p>"
            f"<p class='fd-t2'><b>Come leggerlo.</b> <u>Se è alto:</u> {E(alto)} <u>Se è basso:</u> {E(basso)}</p>"
            f"<div class='fd-chw'><svg class='fd-ch' viewBox='0 0 640 190' preserveAspectRatio='none' data-k='{k}' data-d='{E(data)}'></svg><div class='fd-tip'></div></div>"
            f"<p class='fd-t2 fd-mu'>Linea scura: percentile (0 = il più basso degli ultimi 5 anni, 100 = il più alto); fasce colorate: sotto 20 e sopra 80. Linea sotto: S&amp;P 500. Tocca o scorri il dito sul grafico.</p>"
            f"{_dopo(s)}<p class='fd-t2'>{_prova_txt(s)}</p>"
            f"<p class='fd-t2 fd-mu'>Fonte: {E(fonte)}. Misura: {E(unita)}. Ultimo dato del {s['ultimo_dato'][8:]}/{s['ultimo_dato'][5:7]}/{s['ultimo_dato'][:4]}; viene reso pubblico circa {rit} giorni dopo e Armor lo usa solo da allora.</p></div>")


def _confronto(st: pd.DataFrame | None, ombra: dict | None, sai: float | None) -> str:
    if st is None or "sai_ombra" not in st or st["sai_ombra"].notna().sum() < 20:
        return ("<p class='fd-t2'>Il confronto giornaliero tra il Super Armor Index ufficiale e quello con i grandi fondi al 10% parte appena ci sono abbastanza giorni registrati.</p>"
                + (f"<p class='fd-t2'>Oggi: ufficiale <b>{sai:.0f}</b>, con grandi fondi <b>{ombra['sai']:.0f}</b> ({ombra['delta']:+.1f}).</p>".replace(".", ",") if ombra and sai is not None else ""))
    s = st.dropna(subset=["sai_ombra"]).iloc[-260:]
    n = len(s)
    W, H = 640, 150
    xs = lambda i: 6 + i / max(n - 1, 1) * (W - 12)
    Y = lambda v: 8 + (100 - v) * (H - 16) / 100
    a = " ".join(f"{xs(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["sai"].values))
    b = " ".join(f"{xs(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["sai_ombra"].values))
    diff = (s["sai_ombra"] - s["sai"])
    svg = (f"<svg viewBox='0 0 {W} {H}' preserveAspectRatio='none' class='fd-cmp'><polyline fill='none' stroke='var(--tx)' stroke-width='2.2' points='{a}'/>"
           f"<polyline fill='none' stroke='hsl(35,95%,58%)' stroke-width='1.8' stroke-dasharray='5 3' points='{b}'/></svg>")
    return (f"{svg}<p class='fd-t2'><span style='color:var(--tx)'>▬</span> ufficiale &nbsp; <span style='color:hsl(35,95%,58%)'>╍</span> con i grandi fondi al 10%. "
            f"Negli ultimi {n} giorni registrati la differenza media è {diff.mean():+.1f} punti e il massimo scarto {diff.abs().max():.1f}.</p>".replace(".", ",").replace("+-", "-"))


def _regola(pr: dict | None) -> str:
    txt = ("<p class='fd-t2'><b>Come decideremo.</b> I grandi fondi restano a peso 0 nel Super Armor Index. Entrano al 10% automaticamente solo se un loro segnale supera la prova scritta in anticipo: "
           "in entrambe le metà della storia, e per il calo ≥5% a 1 mese e ≥10% a 3 mesi, valori alti (o bassi) devono avere anticipato cali chiaramente più frequenti del normale, con margine di errore che esclude il caso. "
           "Intanto il valore con i grandi fondi si calcola ogni giorno: se dopo qualche settimana non è né migliore né peggiore dell'ufficiale, non c'è motivo di cambiarlo.</p>")
    if pr and pr.get("auc"):
        a = pr["auc"]
        def f(k):
            x = (a.get(k) or {}).get("1m_5|tutta")
            return None if x is None else x * 100
        so, s0 = f("sai_ombra"), f("sai")
        if so is not None and s0 is not None:
            txt += (f"<p class='fd-t2'><b>Sul passato</b> (calo ≥5% in 1 mese, dal 2000): capacità di distinguere i giorni a rischio, da 50 (come tirare a sorte) a 100 (perfetta): "
                    f"ufficiale <b>{s0:.1f}</b>, con grandi fondi <b>{so:.1f}</b> ({so - s0:+.1f}). Una differenza così piccola non basta per adottarli.</p>".replace(".", ","))
    return txt


GLOSSARIO = [("Percentile", "dove sta il valore di oggi tra gli ultimi 5 anni: 50 = a metà, 100 = il più alto, 0 = il più basso"), ("Futures", "contratti per comprare o vendere l'S&P 500 a una data futura"),
             ("Posizione netta", "contratti comprati meno contratti venduti: sopra zero il gruppo è «comprato», sotto zero è «venduto»"), ("Tensione", "quanto i segnali dei grandi fondi sono lontani dalla norma, senza dire in che direzione"),
             ("13F", "elenco trimestrale delle azioni possedute dai grandi gestori, depositato alla SEC"), ("SEC", "l'autorità che controlla i mercati americani"),
             ("Put", "contratto che guadagna se il mercato scende: si compra per proteggersi o per scommettere al ribasso")]


def html() -> str:
    d = gf.carica() or {}
    sg = d.get("segnali") or {}
    t = d.get("tensione") or {}
    from . import super_armor as sa
    st = sa.storia()
    ombra = None
    sai = None
    if st is not None and not st.empty:
        r = st.iloc[-1]
        sai = float(r["sai"])
        ombra = {"sai": float(r["sai_ombra"]), "delta": float(r["sai_ombra"] - r["sai"])} if "sai_ombra" in r and pd.notna(r["sai_ombra"]) else None
    pr = sa.prova()
    ts = t.get("score")
    n_alti = sum(1 for s in sg.values() if s["stato"] == "alto")
    n_bassi = sum(1 for s in sg.values() if s["stato"] == "basso")
    intro = ("<div class='explain'><p><b>Che cos'è.</b> Qui vedi cosa stanno facendo i grandi operatori del mercato: fondi speculativi, gestori di grandi patrimoni, fondi che tengono liquidità, grandi gestori americani e dirigenti delle aziende. "
             "Muovono cifre enormi: capire se sono molto «comprati», molto «venduti» o molto prudenti aiuta a capire quanto un movimento è affollato.</p>"
             "<p><b>Come si legge.</b> Ogni segnale ha un <b>percentile</b>: dove sta il valore di oggi rispetto agli ultimi 5 anni (100° = il più alto, 0° = il più basso). "
             "Sotto 20° è «basso», sopra 80° è «alto», in mezzo è nella norma. <b>Un livello estremo non dice quando il mercato girerà</b>: dice quanto una parte del mercato è sbilanciata.</p>"
             "<p><b>Attenzione.</b> Per ora nessun segnale ha dimostrato di anticipare i cali: <b>non pesano</b> sul Super Armor Index. Li seguiamo ogni giorno per decidere nelle prossime settimane se meritano di entrare.</p></div>")
    cru = ""
    if ts is not None:
        stato = "tutti i segnali nella norma" if not (n_alti or n_bassi) else f"{n_alti} segnali alti e {n_bassi} bassi su {len(sg)}"
        cru = (f"<div class='fd-c'><h3>Il valore di oggi: tensione dei grandi fondi</h3><div class='fd-top'><div class='fd-big' style='color:{_col_t(ts)}'>{ts:.0f}<small>su 100</small></div>"
               f"<div class='fd-t2' style='flex:1'>{E(stato).capitalize()}. <b>0</b> = tutti i segnali nella norma, <b>100</b> = tutti agli estremi. Non è un livello di pericolo: misura solo quanto i grandi fondi sono fuori dalla norma, in qualsiasi direzione.</div></div>"
               f"<div class='fd-scale'><i style='left:{min(max(ts, 1), 99):.0f}%;border-color:{_col_t(ts)}'></i></div><div class='fd-axl'><span>nella norma</span><span>tutti agli estremi</span></div>"
               f"<p class='fd-t2'>Calcolato su {t['n']} segnali disponibili su {len(INFO)}; gli altri compaiono man mano che si completano i dati.</p></div>"
               f"<div class='fd-c'><h3>Confronto: Super Armor Index con e senza grandi fondi</h3>"
               + (f"<div class='fd-two'><div><span>Ufficiale (fondi a peso 0)</span><b>{sai:.0f}</b></div><div><span>Con i grandi fondi al 10%</span><b>{ombra['sai']:.0f}</b><small>{ombra['delta']:+.1f} punti</small></div></div>".replace(".", ",") if ombra and sai is not None else "")
               + _confronto(st, ombra, sai) + _regola(pr) + "</div>")
    blocchi = ""
    for titolo, ks in GRUPPI:
        blocchi += f"<h3 class='fd-h3'>{E(titolo)}</h3>" + "".join(scheda(k, sg.get(k)) for k in ks)
    mancano = [gf.SEGNALI[k][0] for k in ORDINE if k not in sg]
    stato_dati = ("<p class='fd-t2'>Segnali già attivi: " + ", ".join(E(gf.SEGNALI[k][0].split(" (")[0]) for k in ORDINE if k in sg) + ". In arrivo: "
                  + (", ".join(E(x.split(" (")[0]) for x in mancano) if mancano else "nessuno, i dati sono completi") + ".</p>")
    glos = "<h3 class='fd-h3'>Parole difficili</h3><ul class='fd-gl'>" + "".join(f"<li><b>{E(a)}</b>: {E(b)}.</li>" for a, b in GLOSSARIO) + "</ul>"
    come = ("<h3 class='fd-h3'>Come funziona la prova</h3><p class='fd-t2'>Per ogni segnale e per ogni giorno si guarda se, quando il segnale era alto (≥ 80°) o basso (≤ 20°), l'S&amp;P 500 è poi sceso di almeno il 5% nel mese o del 10% nei tre mesi "
            "più spesso del normale. Il confronto usa blocchi di date vicine (le date vicine non sono indipendenti) e si ripete separatamente sulla prima e sulla seconda metà della storia: serve che funzioni in entrambe. "
            "Usiamo ogni dato solo dal giorno in cui è stato davvero pubblicato, mai prima.</p>")
    try:
        from . import fondi_nomi
        nomi = fondi_nomi.html()
    except Exception:  # noqa: BLE001
        nomi = ""
    return (f"<div id='fdroot'><h2>Grandi fondi: cosa fanno e come leggere le loro mosse</h2>{intro}{nomi}<h3 class='fd-h3'>I segnali complessivi dei grandi operatori</h3>{stato_dati}{cru}{blocchi}{come}{glos}"
            f"<p class='fd-t2 fd-mu'>Dati al {E(str(d.get('data', 'n.d.')))}. Informazioni di contesto: non sono una consulenza finanziaria.</p></div>{CSS}")


def riga_rischio() -> str:
    """Riga per la pagina Indici: valore di confronto dei grandi fondi, in evidenza ma a peso zero."""
    d = gf.carica() or {}
    t = d.get("tensione")
    if not t or t.get("score") is None:
        return ("<div class='card'><b>Grandi fondi</b> (in prova, non pesano): dati in arrivo. <a href='#fondi' data-go='fondi'>Apri la pagina ›</a></div>")
    sg = d.get("segnali") or {}
    na, nb = sum(1 for s in sg.values() if s["stato"] == "alto"), sum(1 for s in sg.values() if s["stato"] == "basso")
    stato = "tutti nella norma" if not (na or nb) else f"{na} alti e {nb} bassi su {len(sg)}"
    from . import super_armor as sa
    st = sa.storia()
    conf = ""
    if st is not None and "sai_ombra" in st and pd.notna(st["sai_ombra"].iloc[-1]):
        conf = f" Super Armor Index con i fondi: <b>{st['sai_ombra'].iloc[-1]:.0f}</b> contro <b>{st['sai'].iloc[-1]:.0f}</b> ufficiale."
    return (f"<div class='card'><b>Grandi fondi</b> <span class='mu'>(in prova, non pesano sul valore)</span>: tensione <b style='color:{_col_t(t['score'])}'>{t['score']:.0f}/100</b>, {stato}.{conf} "
            "<a href='#fondi' data-go='fondi'>Apri la pagina ›</a></div>")


CSS = """<style>
.fd-c{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:12px 14px;margin:10px 0}.fd-c h3,.fd-c h4{margin:0 0 6px}.fd-c h4{font-size:15px}
.fd-h3{margin:22px 0 4px;font-size:16px}.fd-wait{opacity:.8;border-style:dashed}
.fd-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.fd-big{font-size:34px;font-weight:800;line-height:1}.fd-big small{font-size:11px;font-weight:600;color:var(--mu);margin-left:6px;display:block}
.fd-pill{border:1.5px solid;border-radius:99px;padding:3px 11px;font-weight:700;font-size:13px;white-space:nowrap}
.fd-ax,.fd-scale{position:relative;height:10px;border-radius:99px;background:var(--bd);margin:10px 0 3px}.fd-ax i.lo,.fd-ax i.hi{position:absolute;top:0;height:100%}.fd-ax i.lo{left:0;width:20%;background:hsl(210,70%,45%);opacity:.55;border-radius:99px 0 0 99px}.fd-ax i.hi{right:0;width:20%;background:hsl(0,70%,50%);opacity:.55;border-radius:0 99px 99px 0}
.fd-ax b,.fd-scale i{position:absolute;top:-4px;width:16px;height:16px;margin-left:-8px;border-radius:50%;background:var(--card);border:4px solid var(--tx);box-sizing:border-box}
.fd-scale{background:linear-gradient(90deg,hsl(210,70%,52%),hsl(105,60%,50%),hsl(40,85%,52%),hsl(0,75%,52%))}.fd-scale i{border:4px solid}
.fd-axl{display:flex;justify-content:space-between;font-size:10px;color:var(--mu)}.fd-nd{font-size:12px;color:var(--mu)}
.fd-dd{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0}.fd-d{font-size:11.5px;color:var(--mu);background:var(--bg);border-radius:99px;padding:2px 9px}
.fd-t2{font-size:12.8px;line-height:1.45;color:var(--mu);margin:5px 0}.fd-mu{font-size:11.5px;opacity:.85}.fd-t2 b{color:var(--tx)}
.fd-chw{position:relative;margin:8px 0 2px;touch-action:pan-y}.fd-ch{width:100%;height:auto;aspect-ratio:640/190;display:block;background:var(--bg);border-radius:12px}
.fd-tip{position:absolute;top:6px;display:none;pointer-events:none;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:6px 10px;font-size:12px;box-shadow:0 6px 18px rgba(0,0,0,.28);min-width:140px;z-index:2}.fd-tip b{font-size:18px}
.fd-tb{width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0}.fd-tb th{font-size:10.5px;color:var(--mu);text-align:left;padding:3px 4px}.fd-tb td{padding:5px 4px;border-top:1px solid var(--bd)}
.fd-two{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0}.fd-two div{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:8px 10px;display:flex;flex-direction:column}.fd-two span{font-size:11.5px;color:var(--mu)}.fd-two b{font-size:28px}.fd-two small{color:var(--mu)}
.fd-cmp{width:100%;height:auto;aspect-ratio:640/150;background:var(--bg);border-radius:12px;display:block;margin:6px 0}.fd-gl{padding-left:18px;font-size:12.8px;color:var(--mu);line-height:1.5}
</style>"""

JS = r"""<script>(function(){var R=document.getElementById('fdroot');if(!R||R.dataset.on)return;R.dataset.on=1;
var IT=function(s){return new Date(s).toLocaleDateString('it-IT',{day:'numeric',month:'short',year:'numeric'})};
function draw(svg,D){var n=D.d.length;if(n<3)return;var W=640,PL=24,PR=6,xs=function(i){return PL+i/(n-1)*(W-PL-PR)},Y=function(v){return 8+(100-v)*1.0},o='';
o+="<rect x='"+PL+"' y='"+Y(100)+"' width='"+(W-PL-PR)+"' height='"+(Y(80)-Y(100))+"' fill='hsl(0,70%,50%)' opacity='.16'/><rect x='"+PL+"' y='"+Y(20)+"' width='"+(W-PL-PR)+"' height='"+(Y(0)-Y(20))+"' fill='hsl(210,70%,50%)' opacity='.18'/>";
[0,20,50,80,100].forEach(function(g){o+="<line x1='"+PL+"' x2='"+(W-PR)+"' y1='"+Y(g)+"' y2='"+Y(g)+"' stroke='var(--bd)' stroke-width='.6'/><text x='2' y='"+(Y(g)+3)+"' font-size='8' fill='var(--mu)'>"+g+"</text>"});
var sp=D.sp.filter(function(x){return x!=null}),mn=Math.min.apply(null,sp),mx=Math.max.apply(null,sp),Z=function(v){return 178-(v-mn)/((mx-mn)||1)*62};
var a=[],b=[];for(var i=0;i<n;i++){if(D.p[i]!=null)a.push(xs(i).toFixed(1)+','+Y(D.p[i]).toFixed(1));if(D.sp[i]!=null)b.push(xs(i).toFixed(1)+','+Z(D.sp[i]).toFixed(1))}
o+="<polyline fill='none' stroke='var(--tx)' stroke-width='2.2' stroke-linejoin='round' points='"+a.join(' ')+"'/><polyline fill='none' stroke='hsl(215,15%,55%)' stroke-width='1.4' points='"+b.join(' ')+"'/>";
o+="<text x='"+PL+"' y='114' font-size='8' fill='var(--mu)'>S&amp;P 500</text>";
var t0=new Date(D.d[0]).toLocaleDateString('it-IT',{month:'short',year:'2-digit'}),t1=new Date(D.d[n-1]).toLocaleDateString('it-IT',{month:'short',year:'2-digit'});
o+="<text x='"+PL+"' y='188' font-size='9' fill='var(--mu)'>"+t0+"</text><text x='"+(W-PR)+"' y='188' font-size='9' fill='var(--mu)' text-anchor='end'>"+t1+"</text>";
o+="<g class='cr' style='display:none'><line y1='8' y2='180' stroke='var(--tx)' stroke-width='1' stroke-dasharray='3 3'/></g>";
svg.innerHTML=o;svg._x=xs;svg._n=n}
R.querySelectorAll('.fd-ch').forEach(function(svg){var D;try{D=JSON.parse(svg.getAttribute('data-d'))}catch(e){return}if(!D.d)return;draw(svg,D);
var tip=svg.parentNode.querySelector('.fd-tip');
function mv(ev){var r=svg.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width*640,best=0,bd=1e9;for(var i=0;i<svg._n;i++){var dx=Math.abs(svg._x(i)-x);if(dx<bd){bd=dx;best=i}}
var g=svg.querySelector('.cr'),l=g.querySelector('line'),cx=svg._x(best);g.style.display='';l.setAttribute('x1',cx);l.setAttribute('x2',cx);
var h="<div style='color:var(--mu)'>"+IT(D.d[best])+"</div><div>Valore <b>"+(D.v[best]).toLocaleString('it-IT',{maximumFractionDigits:1})+"</b></div><div>Percentile "+(D.p[best]==null?'n.d.':'<b>'+Math.round(D.p[best])+'°</b>')+"</div>"+(D.sp[best]!=null?"<div style='color:var(--mu)'>S&P 500 "+Math.round(D.sp[best]).toLocaleString('it-IT')+"</div>":'');
tip.innerHTML=h;tip.style.display='block';var w=svg.parentNode.getBoundingClientRect().width,left=cx/640*w+10;if(left+160>w)left=cx/640*w-160;tip.style.left=Math.max(left,4)+'px'}
['pointermove','pointerdown'].forEach(function(n){svg.addEventListener(n,mv)});svg.addEventListener('pointerleave',function(){svg.querySelector('.cr').style.display='none';tip.style.display='none'})})})();</script>"""
