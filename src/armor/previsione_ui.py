"""Blocco «Rischio di calo» in parole semplici e con grafica (Patch 73): le due stime, la scala «meno / come / più del solito», il semaforo e la storia.
Usato sia nel Super Armor Index (pilastro Previsione) sia nella pagina del semaforo. Nessun numero nuovo: stessi dati di prima, spiegati meglio."""
import html as _h
import math

E = _h.escape
SOGLIE = (0.8, 1.3, 2.0)     # le stesse del semaforo (semaforo_rischio.SOGLIE)
COL = {"Verde": "hsl(125,65%,42%)", "Giallo": "hsl(50,85%,48%)", "Arancione": "hsl(24,90%,52%)", "Rosso": "hsl(0,78%,52%)", "Grigio": "hsl(215,10%,55%)"}
BASE_C, PAURA_C = "hsl(215,90%,62%)", "hsl(35,95%,55%)"
ORIZZONTI = (("1m_5", "calo di almeno il 5% entro 1 mese"), ("3m_10", "calo di almeno il 10% entro 3 mesi"))


def _n(x, d=1):
    return "n.d." if x is None else f"{x:.{d}f}".replace(".", ",")


def _pct(x):
    return "n.d." if x is None else f"{x * 100:.0f}%"


def _zona(r: float) -> str:
    return "Verde" if r < SOGLIE[0] else "Giallo" if r < SOGLIE[1] else "Arancione" if r < SOGLIE[2] else "Rosso"


def _pos(r: float) -> float:
    """Posizione 0-100 sulla scala (logaritmica, 1× al centro; da 0,25× a 4×)."""
    return 100 * min(max((math.log2(max(r, 1e-3)) + 2) / 4, 0.02), 0.98)


def frase_rapporto(r: float | None) -> str:
    if r is None:
        return "n.d."
    if r >= 1.95:
        return f"circa {_n(r)} volte il solito"
    if abs(r - 1) < 0.05:
        return "come il solito"
    return f"il {abs(r - 1) * 100:.0f}% {'in più' if r > 1 else 'in meno'} del solito"


def scala(p: dict, chiave: str, titolo: str) -> str:
    """Una riga: scala a zone con i due modelli. Posizione = probabilità del modello / probabilità abituale."""
    x = p.get(chiave)
    if not x or not x.get("normale"):
        return ""
    n, a, f = x["normale"], x["A1"], x["FHS+VIX"]
    ra, rf = a / n, f / n
    zone = "".join(f"<i style='left:{l:.1f}%;width:{w:.1f}%;background:{COL[c]}'></i>" for l, w, c in (
        (0, _pos(SOGLIE[0]), "Verde"), (_pos(SOGLIE[0]), _pos(SOGLIE[1]) - _pos(SOGLIE[0]), "Giallo"),
        (_pos(SOGLIE[1]), _pos(SOGLIE[2]) - _pos(SOGLIE[1]), "Arancione"), (_pos(SOGLIE[2]), 100 - _pos(SOGLIE[2]), "Rosso")))
    return (f"<div class='pv-sc'><div class='pv-sct'>Probabilità di un <b>{E(titolo)}</b></div>"
            f"<div class='pv-trk'>{zone}<u style='left:50%'></u>"
            f"<b class='pv-m' style='left:{_pos(ra):.1f}%;background:{BASE_C}' title='Modello base'>B</b><b class='pv-m' style='left:{_pos(rf):.1f}%;background:{PAURA_C}' title='Modello con la paura'>P</b></div>"
            "<div class='pv-lab'><span>meno del solito</span><span>come il solito</span><span>più del solito</span></div>"
            f"<div class='pv-num'><span><i style='background:{BASE_C}'></i>Base: <b>{_pct(a)}</b></span><span><i style='background:{PAURA_C}'></i>Paura: <b>{_pct(f)}</b></span>"
            f"<span><i style='background:var(--mu)'></i>Di solito: <b>{_pct(n)}</b></span></div></div>")


def carta(nome: str, sotto: str, r: float | None, colore: str, p: dict, chiave_modello: str) -> str:
    z = _zona(r) if r is not None else "Grigio"
    righe = ""
    for k, t in ORIZZONTI:
        x = (p or {}).get(k)
        if x and x.get("normale"):
            righe += f"<div class='pv-r'>{E(t.capitalize())}: <b>{_pct(x[chiave_modello])}</b> <span>(di solito {_pct(x['normale'])})</span></div>"
    if r is None:
        grande, verso = "n.d.", ""
    elif abs(r - 1) < 0.05:
        grande, verso = "= solito", "rischio uguale al solito"
    elif r >= 1.95:
        grande, verso = f"{_n(r)} volte", "il rischio abituale"
    else:
        grande, verso = f"{'+' if r > 1 else '−'}{abs(r - 1) * 100:.0f}%", f"rischio di calo {'più alto' if r > 1 else 'più basso'} del solito"
    return (f"<div class='pv-card' style='border-top:4px solid {colore}'><div class='pv-cn'>{E(nome)}</div><div class='pv-cs'>{E(sotto)}</div>"
            f"<div class='pv-big' style='color:{COL[z]}'>{grande}</div><div class='pv-fr'><b>{E(verso)}</b> <span class='pv-x'>(indice {_n(r, 2)}×)</span></div>"
            f"<div class='pv-sp'>In pratica, oggi questo modello stima:</div>{righe}</div>")


def legenda_semaforo() -> str:
    voci = (("Verde", "meno del solito (sotto 0,8×)"), ("Giallo", "nella norma (0,8× – 1,3×)"), ("Arancione", "più del solito (1,3× – 2×)"), ("Rosso", "almeno il doppio (2× o più)"),
            ("Grigio", "i due modelli non sono d'accordo"))
    return "<div class='pv-leg'>" + "".join(f"<span><i style='background:{COL[c]}'></i><b>{c}</b> {t}</span>" for c, t in voci) + "</div>"


def storia(t: dict | None, oggi: str | None) -> str:
    if not t or not t.get("righe"):
        return ""
    righe = [r for r in t["righe"] if "quota" in r]
    base = righe[0]["1m_5"]["freq_tutte"] if righe else None
    mx = max([r["1m_5"]["freq"] for r in righe] + [r["3m_10"]["freq"] for r in righe] + [base or 0]) or 1
    out = ""
    for r in righe:
        c = r["colore"]
        a, b = r["1m_5"]["freq"], r["3m_10"]["freq"]
        def riga(fr, ref):
            lineetta = "" if ref is None else "<s style='left:" + f"{ref / mx * 100:.0f}" + "%'></s>"
            return f"<div class='pv-hb'><div style='width:{fr / mx * 100:.0f}%;background:{COL[c]}'></div>{lineetta}</div>"
        out += (f"<div class='pv-h{' oggi' if c == oggi else ''}'><div class='pv-hc'><i style='background:{COL[c]}'></i><b>{c}</b>"
                f"<span>{r['quota'] * 100:.0f}% dei giorni{' · poche date' if r['n'] < 100 else ''}</span>{'<em>OGGI</em>' if c == oggi else ''}</div>"
                f"<div class='pv-hr'><span>In 1 mese un calo ≥5% è arrivato <b>{a * 100:.0f} volte su 100</b></span>{riga(a, r['1m_5']['freq_tutte'])}</div>"
                f"<div class='pv-hr'><span>In 3 mesi un calo ≥10% è arrivato <b>{b * 100:.0f} volte su 100</b></span>{riga(b, r['3m_10']['freq_tutte'])}</div></div>")
    rosso = next((r for r in righe if r["colore"] == "Rosso"), None)
    verde = next((r for r in righe if r["colore"] == "Verde"), None)
    es = ""
    if rosso and verde:
        es = (f"<p class='pv-t2'><b>Esempio.</b> Quando il semaforo era <b>Rosso</b> (solo il {rosso['quota'] * 100:.0f}% dei giorni), nel mese dopo l'S&amp;P 500 ha perso almeno il 5% in "
              f"<b>{rosso['1m_5']['freq'] * 100:.0f} casi su 100</b>. Quando era <b>Verde</b>, in <b>{verde['1m_5']['freq'] * 100:.0f} su 100</b>. "
              f"La lineetta scura su ogni barra è la media di tutti i giorni (circa {_pct(base)} per il calo a 1 mese): barra oltre la lineetta = più cali del solito.</p>")
    return (f"<h4 class='pv-h4'>E in passato? Dal {E(t.get('da', '1990')[:4])} a oggi, dopo ogni colore</h4>"
            "<p class='pv-t2'>Per ogni colore del semaforo: quante volte, nei giorni di quel colore, l'S&amp;P 500 è poi sceso davvero.</p>" + out + es)


def html(o: dict | None, t: dict | None, variazione: dict | None = None) -> str:
    """o = semaforo_rischio_oggi.json, t = tabella storica, variazione = semaforo_rischio.variazione()."""
    if not o:
        return "<p class='pv-t2'>Il semaforo del rischio compare al prossimo aggiornamento giornaliero.</p>"
    p = o.get("p") or {}
    ra, rf = o.get("r_a1"), o.get("r_fhs")
    medio = (ra + rf) / 2 if ra is not None and rf is not None else None
    mostrato = o.get("mostrato", "Grigio")
    x = p.get("1m_5") or {}
    lo, hi, nor = (min(x["A1"], x["FHS+VIX"]), max(x["A1"], x["FHS+VIX"]), x["normale"]) if x else (None, None, None)
    disaccordo = o.get("grezzo") == "Grigio"
    # 1) la risposta subito
    if x:
        titolo = {"Verde": "più basso del solito", "Giallo": "nella norma", "Arancione": "più alto del solito", "Rosso": "molto più alto del solito",
                  "Grigio": "incerto: i due modelli non sono d'accordo"}[mostrato]
        sub = ("Uno dei due modelli vede più calma, l’altro più tensione: il numero va letto con cautela." if disaccordo
               else "I due modelli sono abbastanza d’accordo.")
        testa = (f"<div class='pv-top' style='border-color:{COL[mostrato]}'><div class='pv-q'>Rischio di un calo di Borsa oggi</div>"
                 f"<div class='pv-hl'><i style='background:{COL[mostrato]}'></i><span>{E(titolo.capitalize())}</span></div>"
                 f"<div class='pv-tiles'><div><small>Stima dei due modelli</small><b>{lo * 100:.0f}% – {hi * 100:.0f}%</b></div>"
                 f"<div><small>Di solito</small><b>{nor * 100:.0f}%</b></div></div>"
                 f"<div class='pv-a'>È la probabilità che l'S&amp;P 500 (le 500 maggiori aziende americane) perda <b>almeno il 5% entro 1 mese</b>.</div>"
                 f"<div class='pv-v'>{sub} Semaforo: <b>{E(mostrato)}</b>.</div></div>")
    else:
        testa = ""
    # 2) variazione: ogni modello e la media
    def riga_var(nome, col, prima, ora, media=False):
        d = ora - prima
        sale, scende = d > 0.005, d < -0.005
        simb = "▲" if sale else "▼" if scende else "="
        cf = "hsl(0,75%,55%)" if sale else "hsl(125,60%,45%)" if scende else "var(--mu)"
        return (f"<div class='pv-vr{' pv-vm' if media else ''}'><span class='pv-vn'><i style='background:{col}'></i>{nome}</span>"
                f"<span class='pv-vv'>{_n(prima, 2)}× → <b>{_n(ora, 2)}×</b></span><span class='pv-vs' style='color:{cf}'>{simb}</span></div>")
    if variazione and all(k in variazione for k in ("a1_prima", "a1", "fhs_prima", "fhs", "medio_prima", "medio", "d_medio", "da")):
        pm = variazione.get("p_medio")
        sale, scende = variazione["d_medio"] > 0.005, variazione["d_medio"] < -0.005
        verbo = "salito" if sale else "sceso" if scende else "rimasto uguale"
        quanto = f" del {abs(pm):.0f}%" if pm is not None and (sale or scende) else ""
        giorno = f"{variazione['da'][8:]}/{variazione['da'][5:7]}"
        var = ("<h4 class='pv-h4'>Cosa è cambiato rispetto a ieri</h4><div class='pv-varb'>"
               f"<div class='pv-vh'><span></span><span>{giorno} → oggi</span><span></span></div>"
               + riga_var("Modello base", BASE_C, variazione["a1_prima"], variazione["a1"])
               + riga_var("Modello con la paura", PAURA_C, variazione["fhs_prima"], variazione["fhs"])
               + riga_var("Media dei due", "var(--tx)", variazione["medio_prima"], variazione["medio"], True) + "</div>"
               f"<p class='pv-t2'>Ogni numero dice <b>quante volte il rischio di calo è più alto del solito</b> (1× = normale). "
               f"La <b>media dei due modelli</b> è il numero che decide il colore del semaforo: rispetto all'ultimo giorno registrato ({giorno}) è {verbo}{quanto}.</p>")
    else:
        var = "<p class='pv-t2'><b>Rispetto a ieri:</b> non ancora disponibile. Il confronto compare dal secondo giorno registrato.</p>"
    # 3) le due stime + info
    info = ("<details class='pv-info'><summary><i>i</i> Come funzionano i due modelli, nel dettaglio</summary><div>"
            "<p><b>Il numero «×».</b> Ogni modello stima la probabilità di due cali: almeno −5% entro 1 mese e almeno −10% entro 3 mesi. Ogni stima si divide per la probabilità «normale» "
            "(quante volte, in passato, quel calo è davvero arrivato, contando solo i casi già conclusi a quella data). Si fa la media dei due periodi: ecco il «×» del modello. "
            "Poi si fa la media dei due modelli: quella decide il colore.</p>"
            f"<p><b><i style='background:{BASE_C}' class='pv-d'></i>Modello base</b> (nome tecnico: A1, regressione logistica). Una formula statistica imparata dalla storia dell'S&amp;P 500 dal 1928. "
            "Guarda 8 misure ricavate solo dal prezzo: l'agitazione del mercato nell'ultimo mese e negli ultimi 3 mesi (e il loro rapporto), quanto il prezzo è sotto il massimo dell'ultimo anno, "
            "quanto è sopra o sotto la media degli ultimi 200 giorni, il rapporto tra le medie a 50 e 200 giorni, l'andamento degli ultimi 3 mesi e il peggior giorno dell'ultimo mese. "
            "Ogni giorno viene riaddestrato usando solo ciò che si sapeva già quel giorno. Non conosce il VIX.</p>"
            f"<p><b><i style='background:{PAURA_C}' class='pv-d'></i>Modello con la paura</b> (nome tecnico: FHS+VIX, simulazione storica filtrata). Stima quanto il mercato oscilla con un modello di volatilità (GJR-GARCH, dati dal 1950), "
            "poi porta la stima di oggi verso quella dell'indice VIX (la «paura» che i professionisti pagano per assicurarsi, ridotta all'80% perché di solito esagera). "
            "Infine simula 5.000 possibili futuri pescando a caso tra gli scossoni veri del passato, e conta in quanti il mercato scende del 5% in 1 mese o del 10% in 3 mesi.</p>"
            "<p><b>Perché due.</b> Il primo impara dai prezzi passati, il secondo sente il nervosismo di oggi. Se concordano il segnale è più affidabile; se no il semaforo diventa Grigio.</p></div></details>")
    carte = ("<h4 class='pv-h4'>Le due stime, in parole semplici</h4><div class='pv-cards'>"
             + carta("Modello base", "Guarda solo l'andamento del prezzo dell'S&P 500 negli ultimi mesi e anni. Non conosce il VIX.", ra, BASE_C, p, "A1")
             + carta("Modello con la paura", "Guarda anche quanto il mercato è agitato oggi (l'indice della paura, il VIX) e simula migliaia di possibili futuri.", rf, PAURA_C, p, "FHS+VIX") + "</div>"
             "<p class='pv-t2'><b>Come leggere il numero grande.</b> Confronta il rischio di oggi con quello <b>di tutti i giorni della storia</b>. "
             "«+37%» = oggi un calo è il 37% più probabile del solito; «−33%» = il 33% meno probabile; «= solito» = come sempre. "
             "Sotto ci sono le probabilità vere: per esempio «16% (di solito 19%)» vuol dire che oggi il modello stima 16 casi su 100 di un calo importante, contro i 19 abituali. "
             "Il numero «×» tra parentesi è lo stesso confronto espresso come rapporto (1× = uguale, 2× = il doppio) ed è la media dei due periodi, un mese e tre mesi.</p>" + info)
    # 4) scala
    sc = "<h4 class='pv-h4'>Dove cadono oggi i due modelli</h4>" + "".join(scala(p, k, t_) for k, t_ in ORIZZONTI) + \
        "<p class='pv-t2'><b>B</b> = modello base, <b>P</b> = modello con la paura. Più il pallino è a destra, più il modello vede un calo probabile rispetto al solito; il centro è il livello abituale.</p>"
    # 5) semaforo
    sem = (f"<h4 class='pv-h4'>Il semaforo</h4><div class='pv-sem'><i style='background:{COL[mostrato]}'></i><div><b>{E(mostrato)}</b> "
           f"<span>Il colore riassume la media dei due modelli ({_n(medio, 2)}× il solito).</span></div></div>" + legenda_semaforo()
           + "<p class='pv-t2'>Il colore cambia solo dopo 3 giorni uguali di fila (Grigio e Rosso scattano subito), così non salta ogni giorno. "
             "Non è un consiglio di comprare o vendere: dice solo quanto è probabile un calo.</p>")
    return CSS + testa + var + carte + sc + sem + storia(t, mostrato)


CSS = """<style>
.pv-top{border:2px solid var(--mu);border-radius:18px;padding:16px 18px;margin:6px 0 12px;background:var(--card)}
.pv-hl{display:flex;align-items:center;gap:10px;font-size:22px;font-weight:800;line-height:1.2;margin:8px 0 10px}.pv-hl i{width:20px;height:20px;border-radius:50%;flex:none}
.pv-tiles{display:grid;grid-template-columns:1.4fr 1fr;gap:10px;margin:6px 0}.pv-tiles div{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:8px 12px}
.pv-tiles small{display:block;font-size:11.5px;color:var(--mu)}.pv-tiles b{font-size:26px;font-weight:800}
.pv-varb{border:1px solid var(--bd);border-radius:14px;padding:6px 12px;background:var(--card)}.pv-vh,.pv-vr{display:grid;grid-template-columns:1.5fr 1.3fr 24px;gap:6px;align-items:center;padding:6px 0;font-size:13.5px}
.pv-vh{font-size:11.5px;color:var(--mu)}.pv-vr+.pv-vr{border-top:1px solid var(--bd)}.pv-vm{font-weight:700}.pv-vn i,.pv-d{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}.pv-vs{font-size:18px;font-weight:800;text-align:center}
.pv-info{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:10px 0;background:var(--card);font-size:13px;line-height:1.5}.pv-info summary{cursor:pointer;font-weight:700}
.pv-info summary i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:50%;background:var(--tx);color:var(--bg);font-style:normal;font-size:12px;margin-right:6px}.pv-info p{margin:8px 0}
.pv-q{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mu);font-weight:700}.pv-a{font-size:17px;line-height:1.4;margin:6px 0}.pv-v{font-size:14px;color:var(--mu)}.pv-v b{color:var(--tx)}
.pv-varx{display:flex;gap:10px;align-items:center;border:1px dashed var(--bd);border-radius:12px;padding:8px 12px;font-size:13.5px;margin:8px 0}.pv-ar{font-size:22px;font-weight:800;min-width:24px;text-align:center}
.pv-x{font-size:11.5px;color:var(--mu);font-weight:400}.pv-sp{font-size:11.5px;color:var(--mu);margin-top:6px}.pv-h4{margin:22px 0 6px;font-size:16px}.pv-t2{font-size:13px;line-height:1.5;color:var(--mu);margin:6px 0}.pv-t2 b{color:var(--tx)}
.pv-cards{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:520px){.pv-cards{grid-template-columns:1fr}}
.pv-card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:12px 14px}.pv-cn{font-weight:800;font-size:15px}.pv-cs{font-size:12px;color:var(--mu);margin:3px 0 8px;line-height:1.4}
.pv-big{font-size:38px;font-weight:800;line-height:1}.pv-fr{font-size:13px;margin:4px 0 8px}.pv-r{font-size:12.5px;color:var(--tx);margin-top:3px}.pv-r span{color:var(--mu)}
.pv-sc{margin:12px 0}.pv-sct{font-size:13.5px;margin-bottom:6px}.pv-trk{position:relative;height:16px;border-radius:99px;overflow:hidden;background:var(--bd)}
.pv-trk i{position:absolute;top:0;height:100%;opacity:.55}.pv-trk u{position:absolute;top:0;height:100%;width:2px;background:var(--tx);opacity:.7;z-index:1}
.pv-trk b.pv-m{position:absolute;top:-1px;width:18px;height:18px;margin-left:-9px;border-radius:50%;color:#fff;font-size:10px;line-height:18px;text-align:center;z-index:2;border:2px solid var(--card);box-sizing:content-box;top:-3px}
.pv-trk{overflow:visible}.pv-trk i:first-child{border-radius:99px 0 0 99px}.pv-trk i:nth-of-type(4){border-radius:0 99px 99px 0}
.pv-lab{display:flex;justify-content:space-between;font-size:10.5px;color:var(--mu);margin-top:6px}
.pv-num{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;margin-top:6px}.pv-num i,.pv-leg i,.pv-sem i,.pv-hc i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
.pv-leg{display:grid;gap:5px;font-size:12.5px;margin:8px 0}.pv-sem{display:flex;gap:10px;align-items:center;font-size:15px}.pv-sem i{width:28px;height:28px;margin:0}.pv-sem span{display:block;font-size:12.5px;color:var(--mu)}
.pv-h{border:1px solid var(--bd);border-radius:14px;padding:10px 12px;margin:8px 0;background:var(--card)}.pv-h.oggi{border-color:var(--tx);box-shadow:0 0 0 1px var(--tx)}
.pv-hc{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:14px}.pv-hc span{color:var(--mu);font-size:12px}.pv-hc em{font-style:normal;font-size:10.5px;font-weight:800;background:var(--tx);color:var(--bg);border-radius:99px;padding:1px 8px}
.pv-hr{margin-top:7px;font-size:12.5px}.pv-hr span b{color:var(--tx)}.pv-hb{position:relative;height:9px;background:var(--bd);border-radius:99px;margin-top:4px}.pv-hb div{height:100%;border-radius:99px}.pv-hb s{position:absolute;top:-3px;width:2px;height:15px;background:var(--tx);opacity:.7}
</style>"""
