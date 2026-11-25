# -*- coding: utf-8 -*-
"""Indicazioni «flash» del Super Armor: come e' prevista l'economia nei prossimi mesi e perche', in frasi semplici.
Tutto dedotto dai valori di oggi e dalla loro variazione nelle ultime 4 settimane (20 sedute): nessun numero scritto a mano."""
from __future__ import annotations

import pandas as pd

CORTI = {"sf_curva": "curva dei tassi", "sf_cred": "costo del credito alle aziende", "sf_cred6": "credito in aumento", "sf_nfci": "condizioni finanziarie", "sf_mom": "Borsa a 12 mesi",
         "sf_curva2": "curva 10-2 anni", "se_sussidi": "sussidi di disoccupazione", "se_lavoro": "posti di lavoro", "se_prod": "produzione", "se_chicago": "indice di Chicago",
         "se_permessi": "permessi edili", "se_sahm": "disoccupazione", "se_fiducia": "fiducia dei consumatori"}
MISURE = list(CORTI)


def _ult(S, k, n=0):
    x = S.get(k)
    if x is None or len(x) <= n:
        return None
    return float(x.iloc[-1 - n])


def _it(v):
    return f"{v:.0f}"


def flash(S: dict, sp: pd.Series | None = None) -> dict:
    """S = super_armor_2.calcola(); sp = prezzi S&P 500. Restituisce frase, misure che spingono e rassicurano, lista di indicazioni (tono, titolo, testo)."""
    sup, fin, eco = _ult(S, "super"), _ult(S, "sa_fin"), _ult(S, "sa_eco")
    if sup is None or fin is None or eco is None:
        return {}
    dfin = fin - (_ult(S, "sa_fin", 20) or fin); deco = eco - (_ult(S, "sa_eco", 20) or eco); dsup = sup - (_ult(S, "super", 20) or sup)
    if sup < 40:
        frase = "Economia prevista solida nei prossimi mesi: pochi segnali di allarme."
    elif sup < 60:
        frase = "Economia prevista in lieve rallentamento nei prossimi mesi: i segnali sono misti, né di calma né di pericolo."
    elif sup < 80:
        frase = "Rallentamento probabile nei prossimi mesi: diversi segnali sono sopra il livello di guardia."
    else:
        frase = "Forte rallentamento, o recessione, possibile nei prossimi mesi: quasi tutti i segnali sono in allarme."
    ms = {k: _ult(S, k) for k in MISURE if _ult(S, k) is not None}
    alti = sorted(ms.items(), key=lambda kv: -kv[1])
    spingono = [(CORTI[k], v) for k, v in alti[:3] if v >= 60]
    rassicurano = [(CORTI[k], v) for k, v in alti[::-1][:3] if v < 40]
    v = lambda k: _ult(S, k)
    r1 = r3 = dd = None
    if sp is not None and len(sp) > 260:
        sp = sp.dropna(); r1 = float(sp.iloc[-1] / sp.iloc[-22] - 1) * 100; dd = float(sp.iloc[-1] / sp.iloc[-252:].max() - 1) * 100
    F = []   # (gravita 0-3, tono, titolo, testo)
    if deco >= 4:
        F.append((3 if eco >= 60 else 2, "r" if eco >= 60 else "a", "L'economia si sta indebolendo",
                  f"Il pilastro economia è salito di {_it(deco)} punti in 4 settimane (ora {_it(eco)}): i dati reali peggiorano."))
    elif deco <= -4:
        F.append((0, "v", "L'economia si sta rafforzando", f"Il pilastro economia è sceso di {_it(-deco)} punti in 4 settimane (ora {_it(eco)})."))
    if fin - eco >= 10:
        F.append((2, "a", "I mercati vedono più guai dell'economia", f"Finanza {_it(fin)} contro economia {_it(eco)}. I prezzi di solito anticipano: se l'economia non migliora, il rallentamento può arrivare nei prossimi mesi."))
    elif eco - fin >= 10:
        F.append((2, "a", "L'economia è già più debole dei mercati", f"Economia {_it(eco)} contro finanza {_it(fin)}. I mercati potrebbero non aver ancora scontato la debolezza dei dati reali."))
    if r1 is not None and r1 <= -3 and eco >= 55:
        F.append((3, "r", "I mercati flettono perché l'economia è in difficoltà", f"La Borsa ha perso il {_it(-r1)}% in un mese e l'economia dà ragione al calo (pilastro {_it(eco)})."))
    elif r1 is not None and r1 <= -3 and eco < 45:
        F.append((1, "n", "Il calo dei mercati non è spiegato dall'economia", f"La Borsa ha perso il {_it(-r1)}% in un mese, ma l'economia regge (pilastro {_it(eco)}): più probabile paura o valutazioni."))
    if dd is not None and dd > -3 and eco >= 60:
        F.append((2, "a", "Borsa vicina ai massimi, economia in difficoltà", "I prezzi non mostrano ancora il problema che i dati reali segnalano: è il tipo di divergenza da tenere d'occhio."))
    if fin >= 60 and eco >= 60:
        F.append((3, "r", "Doppio allarme", f"Finanza ({_it(fin)}) ed economia ({_it(eco)}) sono entrambe sopra 60."))
    if fin < 40 and eco < 40:
        F.append((0, "v", "Doppia luce verde", f"Finanza ({_it(fin)}) ed economia ({_it(eco)}) sono entrambe sotto 40."))
    if max(v("se_lavoro") or 0, v("se_sussidi") or 0) >= 65:
        F.append((2, "a", "Il mercato del lavoro si raffredda", f"Posti di lavoro {_it(v('se_lavoro') or 0)}, sussidi di disoccupazione {_it(v('se_sussidi') or 0)} (0-100, più alto = più debole)."))
    if max(v("sf_cred") or 0, v("sf_cred6") or 0) >= 65:
        F.append((2, "a", "Il credito alle aziende costa di più", f"Costo del credito {_it(v('sf_cred') or 0)}, aumento in 6 mesi {_it(v('sf_cred6') or 0)}: per le imprese è più difficile finanziarsi."))
    if (v("sf_curva") or 0) >= 75 or (v("sf_curva2") or 0) >= 75:
        try:
            from . import store
            raw = float(store.load("t10y3m").dropna().iloc[-1])
        except Exception:  # noqa: BLE001
            raw = None
        if raw is not None and raw < 0:
            F.append((2, "a", "Curva dei tassi invertita", f"I tassi a 3 mesi sono sopra quelli a 10 anni ({raw:.2f} punti): in passato è stato uno dei segnali più affidabili di rallentamento entro un anno.".replace(".", ",")))
        else:
            F.append((1, "a", "Curva dei tassi piatta", "I tassi lunghi superano di poco quelli corti, più della norma storica: non è ancora l'inversione, ma è un segnale di rallentamento."))
    if (v("se_permessi") or 0) >= 75 or (v("se_prod") or 0) >= 65:
        F.append((2, "a", "Edilizia e industria frenano", f"Permessi di costruzione {_it(v('se_permessi') or 0)}, produzione {_it(v('se_prod') or 0)}."))
    if (v("se_fiducia") or 0) >= 65:
        F.append((1, "a", "Le famiglie hanno meno fiducia", f"Fiducia dei consumatori {_it(v('se_fiducia'))}: spesso frena i consumi dopo qualche mese."))
    infl, tassi2, pet = v("sc_infl"), v("sc_tassi2"), v("sc_petrolio")
    if infl is not None and tassi2 is not None and infl >= 70 and tassi2 >= 70:
        F.append((1, "a", "Inflazione e tassi alti pesano", f"Inflazione {_it(infl)} e rialzo dei tassi a 2 anni {_it(tassi2)}. Nel passato non hanno migliorato il punteggio: sono un'informazione in più, senza peso."))
    if pet is not None and pet >= 75:
        F.append((1, "a", "Il petrolio costa molto di più di un anno fa", f"Petrolio {_it(pet)}: pesa sui costi di imprese e famiglie, ma nel passato non ha anticipato bene l'economia."))
    st, mu, mv = v("sm_stretta"), v("sm_mutuo_var"), v("sm_insol_carte")
    if st is not None and st >= 65:
        F.append((2, "a", "Le banche stringono il credito alle famiglie", f"Accesso al credito {_it(st)}: tra le misure sulle famiglie è quella che in passato ha anticipato meglio l'economia."))
    if mu is not None and mu >= 80:
        F.append((1, "a", "Mutui: tassi in forte rialzo in 12 mesi", f"Variazione del tasso del mutuo {_it(mu)}: l'accesso al mutuo è più caro."))
    if mv is not None and mv >= 65:
        F.append((1, "a", "Più carte di credito non pagate", f"Insolvenze {_it(mv)}: le famiglie fanno più fatica a ripagare i debiti."))
    if dsup >= 8:
        F.append((2, "a", "Il Super Armor sale in fretta", f"+{_it(dsup)} punti in 4 settimane (ora {_it(sup)})."))
    elif dsup <= -8:
        F.append((0, "v", "Il Super Armor scende in fretta", f"{_it(dsup)} punti in 4 settimane (ora {_it(sup)})."))
    if not F:
        F.append((0, "n", "Nessun segnale speciale", "Nessuna misura è in zona di allarme e il quadro non cambia in fretta."))
    F.sort(key=lambda x: -x[0])
    return {"frase": frase, "spingono": spingono, "rassicurano": rassicurano, "flash": [(t, a, b) for _, t, a, b in F[:10]]}
