# -*- coding: utf-8 -*-
"""Grafico a comparsa per Indice Armor, Super Armor e Indice crollo.

Si apre toccando uno dei tre indici (qualunque scheda con l'attributo data-gi). Mostra l'andamento con
intervalli 1 settimana ... massimo, scorrevole con un dito e ingrandibile con due dita (o rotella del mouse),
le medie delle ultime 1/4/13 settimane e i valori di ieri, una e due settimane fa.
I dati sono incorporati nella pagina in forma compatta (date a differenze, valori x10 interi).
"""
import json

import pandas as pd

from . import store
from .config import DATA

DESC = {
    "armor": "Salute del mercato: da 40 mercato in difficoltà, da 60 in pericolo, da 80 rischio di crollo.",
    "super": "Come sarà l'economia nei prossimi mesi. Vale il peggiore fra due pilastri: la finanza (veloce, anticipa) e l'economia vera (lenta). Misurato dal 2005: è collegato a come va l'economia nei sei mesi dopo (0,61 su 1; il Super Armor di prima 0,31). Stesse soglie dell'Indice Armor: 40, 60, 80.",
    "crollo": "Rischio di crollo nella prossima settimana: fino a 35 tranquillo, da 40 teso, da 60 molto teso, da 80 panico.",
}
NOMI = {"armor": "Indice Armor", "super": "Super Armor", "crollo": "Indice crollo"}
try:   # i sei pilastri del Super Armor: stessa scala, con la spiegazione di cosa guardano
    from .titan_schede import PIL as _PIL
    for _k, (_n, _c, _s) in _PIL.items():
        NOMI[_k] = _n
        DESC[_k] = f"{_c} {_s}"
except Exception:  # noqa: BLE001
    pass
# soglie e colori delle zone; stessa scala 40/60/80 per Armor e Super Armor, quella a cinque fasce per l'Indice crollo
ZONE = {
    "armor": {"lim": [40, 60, 80], "col": ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"],
              "nom": ["Tranquillo", "Mercato in difficoltà", "Mercato in pericolo", "Rischio di crollo"]},
    "crollo": {"lim": [35, 40, 60, 80], "col": ["#22c55e", "#9ca3af", "#f59e0b", "#ef4444", "#8b5cf6"],
               "nom": ["Nessuna tensione", "Zona di passaggio", "Mercato teso", "Mercato molto teso", "Mercato in panico"]},
}
ZONE["sea"] = {**ZONE["armor"], "nom": ["Economia in salute", "Segnali di rallentamento", "Economia in difficoltà", "Economia in forte difficoltà"]}
ZONE["super"] = {**ZONE["armor"], "nom": ["Economia solida", "Segnali di rallentamento", "Rallentamento probabile", "Forte rallentamento atteso"]}
# pilastri mostrati dentro ogni indice (chiave -> figli, nell'ordine in cui compaiono)
KIDS = {
    "armor": ["a_paura", "a_liquidita", "a_rimbalzo", "a_stress", "a_ciclo"],
    "sea": ["sa_eco", "sa_pil", "sa_fam"],
    "super": ["sa_fin", "sa_eco", "sa_costi", "sa_fam"],
    "sa_costi": ["sc_infl", "sc_infl_acc", "sc_petrolio", "sc_tassi", "sc_tassi2"],
    "sa_fam": ["sm_mutuo_var", "sm_mutuo", "sm_insol_mutui", "sm_insol_carte", "sm_stretta", "sm_consumo", "sm_debito"],
    "sa_fin": ["sf_curva", "sf_cred", "sf_cred6", "sf_nfci", "sf_mom", "sf_curva2"],
    "sa_eco": ["se_sussidi", "se_lavoro", "se_prod", "se_chicago", "se_permessi", "se_sahm", "se_fiducia"],
    "crollo": ["cr_paura", "cr_curva", "cr_tend", "cr_cred", "cr_rot", "cr_tassi"],
    "minimi": ["mi_modello", "mi_semplice"],
    "mi_semplice": ["mf_rimb", "mf_dur", "mf_pend", "mf_neri", "mf_vol"],
    "stato": ["st_cape", "st_buffett", "st_margin", "st_f5", "st_f4", "st_f6", "st_f10", "st_f11", "st_nfci", "st_liq"],
    "sovr": ["sacc"],
    "bolla": ["sovr", "b_m1"],
    "cred": ["c_m3", "c_m5"],
}
PAR = {k: p for p, ks in KIDS.items() for k in ks}
TAG = {"sacc": "quanto in fretta sale", "a_paura": "parte veloce", "a_liquidita": "parte veloce", "a_rimbalzo": "parte veloce",
       "a_stress": "parte lenta", "a_ciclo": "parte lenta", "i7": "solo informativo", "i8": "solo informativo", "i9": "senza peso"}
for _k in PAR:
    ZONE[_k] = ZONE["armor"]
try:   # varianti in prova dell'Indice crollo: compaiono dentro la sua finestra, ognuna con il proprio grafico
    from .crollo_varianti import VARIANTI as _VAR
    KIDS["crollo_var"] = list(_VAR)
    for _k, (_n, _c, _d) in _VAR.items():
        PAR[_k] = "crollo"
        ZONE[_k] = ZONE["crollo"]
        NOMI[_k] = _n
        DESC[_k] = _d + " Non sostituisce l'Indice crollo: è una prova, da giudicare con i mesi che passano."
        TAG[_k] = "in prova"
except Exception:  # noqa: BLE001
    pass
NOMI.update({"a_paura": "Paura sui mercati", "a_liquidita": "Liquidità", "a_rimbalzo": "Segnali di rimbalzo",
             "a_stress": "Stress di mercato e credito", "a_ciclo": "Ciclo, prezzi e valutazioni",
             "i7": "7° Fondi a breve termine", "i8": "8° Indice Buffett", "i9": "Fondi (difensività)"})
DESC.update({
    "i9": "Quanto i grandi fondi sono difensivi: liquidità nei fondi monetari che cresce più del mercato e oro che batte le azioni (percentile rispetto alla storia dal 1984; più alto = più difensivi). "
          "Provato come 7° pilastro del Super Armor: non lo migliora in modo stabile (peggiora fino al 2014, migliora dopo), quindi non ha peso. Non anticipa i crolli: un valore basso coincide con mercati in salita.",
    "a_paura": "Parte veloce dell'Indice Armor (peso 30% insieme alle altre due). Cosa guarda: indice della paura, sua curva, volatilità delle obbligazioni.",
    "a_liquidita": "Parte veloce dell'Indice Armor. Cosa guarda: quanta moneta circola e quanto è facile ottenerla.",
    "a_rimbalzo": "Parte veloce dell'Indice Armor. Misura se ci sono segnali di rimbalzo (credito che migliora, acquisti istituzionali). Qui il numero è il rischio: più è alto, meno segnali di rimbalzo.",
    "a_stress": "Parte lenta dell'Indice Armor (peso 70% insieme al ciclo). Unisce paura, costo del credito e distanza dai massimi dell'ultimo anno: è il termometro di fondo dello stress.",
    "a_ciclo": "Parte lenta dell'Indice Armor. Riassume ciclo economico, prezzi, valutazioni, inflazione e movimenti dei grandi fondi. Si muove piano: oscilla di meno degli altri.",
    "i7": "Fondi a leva che riducono il rischio (percentuale rispetto alla storia disponibile, dal 2010). Solo informativo: provato come 7° pilastro, non è entrato nel Super Armor perché non lo migliorava.",
    "i8": "Valore di tutte le azioni USA diviso il PIL (indice Buffett), come percentuale rispetto alla storia. Solo informativo: provato come 8° pilastro, non è entrato nel Super Armor perché non lo migliorava.",
})


NOMI.update({"sovr": "Sovraccarico del mercato", "sacc": "Accelerazione dello sbilanciamento"})
DESC.update({
    "sovr": "Quanto il mercato americano è sbilanciato su pochi titoli e sulla tecnologia, rispetto alla sua storia (da 0 a 100: 80 vuol dire più sbilanciato dell'80% dei giorni dal 1971). "
            "Non è un indice di rischio dimostrato: dal 1990 è un indizio, che anticipa di mesi e non di giorni. Peso zero negli altri indici.",
    "sacc": "Quanto in fretta sale lo sbilanciamento del mercato (0-100, rispetto alla storia). Insieme al sovraccarico sopra 80 forma lo stato «sbilanciato e in accelerazione».",
})
_ZSOV = {"lim": [60, 80, 90], "col": ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"], "nom": ["Nella norma", "Sbilanciato", "Molto sbilanciato", "Estremo"]}
ZONE["sovr"] = _ZSOV
ZONE["sacc"] = _ZSOV
ZONE["bolla"] = {"lim": [60, 80, 90], "col": _ZSOV["col"], "nom": ["Nella norma", "Caldo", "Molto caldo", "Estremo"]}
ZONE["cred"] = {"lim": [60, 80, 90], "col": _ZSOV["col"], "nom": ["Credito sereno", "Credito teso", "Molto teso", "Estremo"]}
for _k in ("b_m1", "c_m3", "c_m5"):
    ZONE[_k] = ZONE["bolla"] if _k.startswith("b") else ZONE["cred"]
NOMI.update({"bolla": "Indice Bolla", "cred": "Indice Credito", "b_m1": "Prezzi da bolla", "c_m3": "Credito e banche", "c_m5": "Stress del debito europeo"})
DESC.update({
    "bolla": "Quanto il mercato somiglia a una bolla: unisce prezzi alti rispetto agli utili, salita forte negli ultimi tre anni e concentrazione su pochi titoli (il Sovraccarico). "
             "Da 0 a 100: 80 vuol dire più bolla dell'80% dei giorni dal 1971. È un indizio, non dimostrato: nei due casi del passato (2000 e 2022) era acceso prima del picco, ma sono pochi. Peso zero negli altri indici.",
    "cred": "Quanto il credito è sotto stress: spread che si allargano, banche che irrigidiscono i prestiti, curva dei tassi rovesciata e tensione sul debito europeo. Da 0 a 100: 80 vuol dire più teso dell'80% dei giorni dal 1971. "
            "Era acceso prima di 4 picchi su 4 (1990, 2007, 2011, 2023), ma dal 2015 non ha più previsto i cali: pochi casi, non una certezza. Peso zero negli altri indici.",
    "b_m1": "Prezzi da bolla: valutazioni delle azioni (rapporto prezzo/utili corretto per il ciclo) e salita dell'S&P 500 negli ultimi tre anni, come percentile della storia.",
    "c_m3": "Credito e banche: allargamento dello spread tra obbligazioni aziendali e titoli di Stato, banche che irrigidiscono i prestiti, curva dei tassi rovesciata, condizioni finanziarie sul credito.",
    "c_m5": "Stress del debito e delle banche europee: indice di stress sistemico dell'area euro e quanto è salito negli ultimi tre mesi.",
})
# ---- Status index (Crollo, Minimi, Stato): scala 1-100 con fasce 35/40/60/80; il valore sul limite sta nella fascia piu' bassa
try:
    from . import status_index as _si
    for _k in ("crollo", "minimi", "stato"):
        ZONE[_k] = {"lim": _si.ZONE_LIM, "col": _si.ZONE_COL, "nom": _si.NOMI_ZONE[_k], "le": 1}
    NOMI.update({"sea": "Salute dell'economia", "super": "Super Armor", "crollo": "Crollo", "minimi": "Minimi", "stato": "Stato", "mi_modello": "Modello su 14 mercati", "mi_semplice": "Cinque segnali semplici"})
    # nome corto sulle tessere, nome intero nella spiegazione
    _CORTI = {"cr_paura": "Paura", "cr_curva": "Paura a breve", "cr_tend": "Sotto le medie", "cr_cred": "Debito aziende", "cr_rot": "Fuga dai rischiosi", "cr_tassi": "Tassi",
              "mp_caduta": "Caduta", "mp_paura": "Paura", "mp_breve": "Paura a breve", "mp_credito": "Credito", "mp_sotto": "Sotto la media",
              "ms_rientra": "Paura rientra", "ms_curva": "Curva normale", "ms_credstop": "Credito stabile", "ms_risale": "Prezzo risale", "ms_ampiezza": "Settori risalgono",
              "st_cape": "Mercato caro", "st_buffett": "Borsa vs economia", "st_margin": "Debiti in Borsa", "st_f5": "Debito aziende", "st_f4": "Assicurazioni",
              "st_f6": "Tassi", "st_f10": "Fuga dai rischiosi", "st_f11": "Titoli di Stato", "st_nfci": "Condizioni fin.", "st_liq": "Liquidità"}
    _LUNGHI = {}
    try:
        from . import super_armor_2 as _s2
        for _k, _n in _s2.NOMI.items():
            _LUNGHI[_k] = _n; _CORTI.setdefault(_k, {"sa_fin": "Finanza (veloce)", "sa_eco": "Economia (lenta)", "sa_costi": "Costi e tassi", "sa_fam": "Famiglie e mutui", "sa_pil": "PIL USA ed Europa", "sa_w6": "Prova: tre pilastri", "sc_infl": "Inflazione", "sc_infl_acc": "Inflazione in salita", "sc_petrolio": "Petrolio", "sc_tassi": "Rialzo tassi", "sc_tassi2": "Rialzo tassi 2 anni", "sm_mutuo_var": "Mutui: rialzo tassi", "sm_mutuo": "Tasso del mutuo", "sm_insol_mutui": "Mutui non pagati", "sm_insol_carte": "Carte non pagate", "sm_stretta": "Banche e famiglie", "sm_consumo": "Credito al consumo", "sm_debito": "Debito sul reddito", "sf_curva": "Curva tassi", "sf_cred": "Spread credito", "sf_cred6": "Credito in 6 mesi",
                    "sf_nfci": "Condizioni fin.", "sf_mom": "Borsa a 12 mesi", "sf_curva2": "Curva 10-2 anni", "se_sussidi": "Sussidi", "se_lavoro": "Posti di lavoro", "se_prod": "Produzione",
                    "se_chicago": "Indice Chicago", "se_permessi": "Permessi edili", "se_sahm": "Disoccupazione", "se_fiducia": "Fiducia"}.get(_k, _n))
    except Exception:  # noqa: BLE001
        pass
    for _k, (_c, _n) in {**_si.CROLLO_KIDS, **_si.MINIMI_PAN, **_si.MINIMI_SVO}.items():
        _LUNGHI[_k] = _n[0].upper() + _n[1:]
    try:
        from .predisposizione import NOMI as _PN
        for _c, _n in _PN.items():
            _LUNGHI["st_" + _c] = _n[0].upper() + _n[1:]
    except Exception:  # noqa: BLE001
        pass
    for _k, _n in _LUNGHI.items():
        NOMI[_k] = _CORTI.get(_k, _n)
except Exception:  # noqa: BLE001
    pass
_PESI_C = {"cr_paura": 23, "cr_curva": 23, "cr_tend": 19, "cr_cred": 12, "cr_rot": 12, "cr_tassi": 12}
TAG.update({k: f"peso {v}%" for k, v in _PESI_C.items()})
TAG.update({"st_" + c: "peso uguale" for c in ("cape", "buffett", "margin", "f5", "f4", "f6", "f10", "f11", "nfci", "liq")})
TAG.update({"mi_modello": "peso uguale", "mi_semplice": "peso uguale"})
TAG.update({"sa_costi": "senza peso", "sa_pil": "peso uguale", "sa_fam": "peso uguale", "sa_eco": "peso uguale", **{k: "senza peso" for k in ("sc_infl", "sc_infl_acc", "sc_petrolio", "sc_tassi", "sc_tassi2", "sm_mutuo_var", "sm_mutuo", "sm_insol_mutui", "sm_insol_carte", "sm_stretta", "sm_consumo", "sm_debito")}, "sa_fin": "il peggiore dei due decide", "sa_eco": "peso uguale", **{k: "peso uguale nel pilastro" for k in ("sf_curva", "sf_cred", "sf_cred6", "sf_nfci", "sf_mom", "sf_curva2", "se_sussidi", "se_lavoro", "se_prod", "se_chicago", "se_permessi", "se_sahm", "se_fiducia")}})
DESC.update({
    "crollo": "Quanto è teso il mercato adesso e nella prossima settimana: unisce la paura (e la sua curva), il prezzo sotto le medie, il costo del debito delle aziende, "
              "la fuga dai settori rischiosi e le scosse sui tassi. Da 1 a 100: fino a 35 verde, da 40 giallo, da 60 rosso, da 80 viola. "
              "Anticipa di pochi giorni (misurato), non di settimane. Dal 25 novembre 2026 non usa più la distanza dal massimo: la differenza misurata è piccola, scelta per coerenza con l'obiettivo.",
    "minimi": "In che fase del ciclo è il mercato: sta andando verso un minimo oppure si sta allontanando dai minimi per fare nuovi massimi? 1 (verde) = si allontana dai minimi: la discesa, se c'è stata, è alle spalle e il mercato tende a risalire verso nuovi massimi. 100 (rosso) = sta andando verso un minimo: la discesa è in corso e il fondo non si intravede ancora. Si calcola mescolando in parti uguali un modello statistico (addestrato ogni anno su 14 borse nelle discese del passato) e cinque segnali semplici. COSA HA DIMOSTRATO IL PASSATO: separa i giorni «prima del fondo» da quelli «dopo il fondo» molto meglio del caso (punteggio 0,77 su 1; il caso è 0,5), in 14 mercati e anche sul solo S&P 500. ATTENZIONE: riconosce soprattutto quando il fondo è già alle spalle (conferma, con ritardo di giorni o settimane); non indica la data del minimo né di quanto scenderà ancora. Considera solo crisi interne al mercato: i cigni neri esterni sono stati esclusi dalla misura.",
    "mi_modello_vecchio": "Il punto più alto del panico negli ultimi tre mesi (media di cinque voci: caduta, paura, paura a breve, credito, prezzo sotto la media). Per un minimo serve che il panico ci sia stato.",
    "sea": "Salute dell'economia di oggi, da 1 (ottima) a 100 (economia allo sfascio come nelle forti recessioni del passato, 2008-09 e 2020). Non guarda al futuro (quello è il Super Armor) ed è staccata dall'Indice Armor. Sono 16 misure con lo stesso peso, in tre gruppi: lavoro e produzione (7), PIL degli Stati Uniti e dell'area euro (2) e famiglie e mutui (7). Una retta le trasforma in un voto, tarato sulle recessioni: 100 = gravità media delle forti recessioni, 60 = quelle lievi (1990 e 2001), 0 = economia che cresce. Costi e tassi (inflazione, petrolio, rialzo dei tassi) sono stati tolti dal voto perché salgono anche quando l'economia cresce: gonfiavano il numero (prima 88, oggi un numero molto più basso). Provate 24 combinazioni, tenendo fuori una recessione alla volta: questa ha sbagliato di meno (errore medio 18 punti su 100 contro 50 della formula precedente). Limite: solo quattro recessioni; il PIL arriva con circa quattro mesi di ritardo.",
    "sa_pil": "PIL di Stati Uniti e area euro: quanto cresce l'economia in 12 mesi rispetto alla storia (percentile). Alto = crescita debole. Arriva a trimestri, con circa quattro mesi di ritardo. Fa parte della Salute dell'economia.",
    "sa_costi": "Costi e tassi, senza peso: inflazione, accelerazione dell'inflazione, prezzo del petrolio e rialzo dei tassi (banca centrale e tassi a 2 anni). Nei test aggiungerli al Super Armor ha peggiorato il punteggio: nel passato salivano anche nelle fasi di crescita, quindi non anticipavano il rallentamento. Restano come informazione e alimentano le indicazioni flash.",
    "sa_fam": "Famiglie e mutui, senza peso: tasso e rialzo del tasso dei mutui, mutui e carte di credito non pagati, banche che stringono il credito alle famiglie (l'accesso), credito al consumo e quota del reddito che serve a ripagare i debiti. Nessuna combinazione ha superato la soglia del caso nei test; la più utile da sola è la stretta delle banche. Informazione in più, senza peso.",
    "sa_fin": "Pilastro finanza, la parte veloce: media di sei misure con lo stesso peso (curva dei tassi, costo del debito delle aziende e sua crescita, condizioni finanziarie, andamento della Borsa a 12 mesi, seconda curva dei tassi). I prezzi anticipano l'economia ma danno anche falsi allarmi. Il Super Armor prende il più alto fra questo pilastro e quello dell'economia.",
    "sa_eco": "Pilastro economia, la parte lenta: media di sette misure con lo stesso peso (sussidi di disoccupazione, posti di lavoro, produzione, indice di Chicago, permessi di costruzione, indicatore di Sahm, fiducia dei consumatori). Dice dove si trova l'economia vera, con ritardi di settimane o mesi. Il Super Armor prende il più alto fra questo pilastro e quello della finanza.",
    "mi_semplice": "Cinque segnali semplici, senza addestramento (media dei loro percentili storici): poco rimbalzo dal minimo recente, pochi giorni dal massimo, media a 50 giorni in discesa, molti giorni neri nell'ultimo mese, volatilità ancora vicina al picco. Più è alto, più il mercato è ancora in discesa.",
    "mi_modello": "Un modello statistico (regressione) addestrato ogni anno sulle discese di 14 borse: confronta 15 misure di prezzo e volatilità con quelle dei giorni che precedevano il fondo in passato. Più è alto, più la situazione somiglia ai giorni prima di un minimo.",
    "stato": "Quanto il terreno è fragile rispetto alla storia, da 1 (terreno solido) a 100 (molto fragile). Media di dieci misure: mercato caro, Borsa grande rispetto all'economia, debiti per comprare azioni, "
             "costo del debito, assicurazioni sul ribasso, tassi, fuga dai settori rischiosi, titoli di Stato, condizioni finanziarie, liquidità. Dice quanto il mercato è predisposto, non quando scende.",
})
_LUNGHI = globals().get("_LUNGHI", {})
for _k in list(NOMI):
    if _k.startswith(("cr_", "mf_", "st_", "sf_", "se_", "sc_", "sm_")) and _k not in DESC:
        DESC[_k] = (_LUNGHI.get(_k, NOMI[_k]) + ". Una delle voci che compongono l'indice, come posizione rispetto alla storia (da 0 a 100: più è alto, più è sotto stress). " + TAG.get(_k, "")).strip()
CFG_SOVR = {"val": 1, "dec": 0, "u": "", "pp": "sul giorno precedente", "def": 2,
            "rng": [["1M", 30], ["3M", 91], ["1A", 365], ["5A", 1826], ["20A", 7305], ["Max", 0]],
            "prev": [["Ieri", 1], ["Una settimana fa", 7], ["Due settimane fa", 14], ["Un mese fa", 30], ["3 mesi fa", 91], ["6 mesi fa", 182]],
            "mean": [["Ultima settimana", 7], ["Ultimo mese", 30], ["Ultimi 3 mesi", 91]],
            "hint": "Verde nella norma, giallo sbilanciato, rosso molto sbilanciato, viola estremo. Freccia rossa = oggi è più sbilanciato di allora. Fino al 2020 un punto a settimana."}


def _serie(s: pd.Series) -> dict | None:
    s = s.dropna()
    if len(s) < 10:
        return None
    t = (s.index.normalize() - pd.Timestamp("1970-01-01")).days.astype(int).tolist()
    dt = [0] + [t[i] - t[i - 1] for i in range(1, len(t))]
    return {"t0": t[0], "dt": dt, "v": [int(round(float(x) * 10)) for x in s.values]}


VAL = {   # valutazioni del mercato: piu' alto = piu' caro = peggio
    "cape": ("CAPE S&P 500", "prezzo su utili medi di 10 anni", 1, ""),
    "pe": ("P/E S&P 500", "prezzo su utili di un anno", 1, ""),
    "buffett": ("Indice Buffett", "valore della Borsa su prodotto interno lordo", 0, "%"),
}
VAL_NOM = ["Nella norma", "Sopra la norma", "Caro", "Estremo"]
VAL_COL = ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"]
VAL_DESC = {
    "cape": "Prezzo delle 500 maggiori aziende americane diviso la media dei loro utili degli ultimi 10 anni, corretta per l'inflazione. Più è alto, più il mercato è caro rispetto a quanto guadagna: in passato valori alti hanno preceduto rendimenti più bassi e cali più profondi. Non dice quando.",
    "pe": "Prezzo delle 500 maggiori aziende americane diviso gli utili dell'ultimo anno. Più è alto, più si paga caro ogni euro di utile. Verde nella norma storica, giallo sopra la norma, rosso caro, viola estremo.",
    "buffett": "Valore di tutte le azioni americane diviso il prodotto interno lordo (la ricchezza prodotta in un anno). Sopra 100% si paga la Borsa più di quanto produce il Paese. Il dato arriva ogni trimestre, con ritardo.",
}


def val_serie(k: str):
    try:
        if k == "cape":
            return store.load("cape_m").dropna()
        if k == "pe":
            return store.load("pe_m").dropna()
        from . import semafori
        return semafori.series_of("buffett").dropna()
    except Exception:  # noqa: BLE001
        return None


def val_info() -> dict:
    """Per ogni valutazione: valore di oggi, posizione nella storia, soglie (50/80/95 per cento della storia) e colori."""
    out = {}
    for k, (nome, sub_, dec, u) in VAL.items():
        s = val_serie(k)
        if s is None or len(s) < 100:
            continue
        v = float(s.iloc[-1])
        lim = [round(float(s.quantile(q)), 2) for q in (0.50, 0.80, 0.95)]
        i = sum(v >= x for x in lim)
        out[k] = {"nome": nome, "sub": sub_, "dec": dec, "u": u, "v": v, "pos": float((s < v).mean()), "lim": lim, "i": i,
                  "col": VAL_COL[i], "nom": VAL_NOM[i], "mediana": float(s.median()), "dal": int(s.index[0].year),
                  "data": s.index[-1], "ieri": float(s.iloc[-2]) if len(s) > 1 else None,
                  "sett": float(s[s.index <= s.index[-1] - pd.Timedelta(days=7)].iloc[-1]) if (s.index <= s.index[-1] - pd.Timedelta(days=7)).any() else None}
    return out


def _it(x: float, d: int = 0) -> str:
    return f"{x:.{d}f}".replace(".", ",").replace("-", "\u2212")


def val_cards() -> str:
    """Tre schede per «Paura, protezioni e prezzi»: CAPE, P/E, Buffett con colore e grafico toccando."""
    info = val_info()
    if not info:
        return ""
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    out = ""
    for k, x in info.items():
        zone = ["verde", "gialla", "rossa", "viola"]
        seg = "".join(f"<i style='flex:{w};background:{c};opacity:{1 if j == x['i'] else .3}'></i>" for j, (w, c) in enumerate(zip((50, 30, 15, 5), VAL_COL)))
        pos = min(max(x["pos"] * 100, 1), 99)
        freschezza = ""
        if (pd.Timestamp.now() - x["data"]).days > 20:
            freschezza = f"<div class='mu'>Dato al {x['data'].day} {mesi[x['data'].month - 1]} {x['data'].year}: arriva ogni trimestre.</div>"
        prev = ""
        if x["ieri"] is not None and not freschezza:
            d = x["v"] - x["ieri"]
            colv = "var(--bad)" if d > 0 else "var(--ok)"
            frv = "\u25b2" if d > 0 else "\u25bc"
            prev = (f"<div class='vl-p'>ieri <b>{_it(x['ieri'], x['dec'])}{x['u']}</b> "
                    f"<span style='color:{colv}'>{frv} {_it(abs(d), x['dec'])}</span></div>")
        tip = (f"{x['sub']}. Più alto del {x['pos'] * 100:.0f}% dei dati dal {x['dal']}, tipico {_it(x['mediana'], x['dec'])}{x['u']}."
               + (f" Una settimana fa {_it(x['sett'], x['dec'])}{x['u']}." if x["sett"] is not None else "")).replace("'", "&#39;")
        out += (f"<div class='kc vl' data-gi='{k}' title='{tip}'><div class='kt'>{x['nome']} "
                f"<small style='display:block;color:{x['col']};font-weight:700'>{x['nom']}</small></div>"
                f"<div class='kv' style='color:{x['col']}'>{_it(x['v'], x['dec'])}{x['u']}</div>"
                f"<div class='vl-s'>{x['sub']}</div>"
                f"<div class='vl-g'>{seg}<u style='left:{pos:.0f}%'></u></div>"
                f"<div class='vl-p'>Più alto del <b>{x['pos'] * 100:.0f}%</b> dei dati · tipico {_it(x['mediana'], x['dec'])}{x['u']}</div>"
                f"{prev}{freschezza}<div class='mu'>Tocca per il grafico ›</div></div>")
    return out


def val_cfg() -> tuple[dict, dict, dict]:
    """Configurazione del grafico per le valutazioni: serie, opzioni, zone (soglie in unita' reali)."""
    ser, cfg, zone = {}, {}, {}
    info = val_info()
    for k, x in info.items():
        s = val_serie(k)
        r = _serie(s)
        if not r:
            continue
        ser[k] = r
        zone[k] = {"lim": x["lim"], "col": VAL_COL, "nom": VAL_NOM}
        trim = k == "buffett"
        cfg[k] = {"val": 1, "dec": x["dec"], "u": x["u"], "pp": "sul dato precedente",
                  "rng": [["1A", 365], ["3A", 1096], ["5A", 1826], ["10A", 3652], ["20A", 7305], ["Max", 0]] if trim else [["1M", 30], ["3M", 91], ["1A", 365], ["5A", 1826], ["20A", 7305], ["Max", 0]],
                  "prev": [["3 mesi fa", 91], ["6 mesi fa", 182], ["1 anno fa", 365]] if trim else [["Ieri", 1], ["Una settimana fa", 7], ["Un mese fa", 30]],
                  "mean": None if trim else [["Ultima settimana", 7], ["Ultimo mese", 30], ["Ultimi 3 mesi", 91]],
                  "def": 1 if trim else 1}
        NOMI[k] = x["nome"]
        DESC[k] = VAL_DESC[k]
    return ser, cfg, zone


def dati() -> dict:
    out: dict = {}
    try:
        d = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
        col = "armor_tarato" if "armor_tarato" in d else "armor_index"
        for k, c in (("armor", col), ("super", "super_armor_index")) + tuple((f"p{i}", f"p{i}_stress") for i in range(1, 7)) + tuple((a, a) for a in KIDS["armor"]):
            if c in d:
                x = _serie(d[c])
                if x:
                    out[k] = x
    except Exception:  # noqa: BLE001
        pass
    try:
        out.update(val_cfg()[0])
    except Exception:  # noqa: BLE001
        pass
    try:   # pilastri 7 e 8: informativi, in percentile rispetto alla propria storia, sull'asse dei giorni Titan
        from . import semafori
        d = pd.read_csv(DATA / "titan_storia.csv", index_col=0, parse_dates=True)
        for k, key in (("i7", "fondi_breve"), ("i8", "buffett")):
            s = semafori.series_of(key).dropna()
            if len(s) > 60:
                pct = s.expanding(min_periods=40).rank(pct=True) * 100
                x = _serie(pct.dropna().reindex(d.index, method="ffill").dropna().clip(1, 100))
                if x:
                    out[k] = x
    except Exception:  # noqa: BLE001
        pass
    try:   # difensivita' dei grandi fondi (7° pilastro informativo del Super Armor)
        from . import difensivita
        dj = difensivita.leggi()
        if dj and dj.get("serie"):
            out["i9"] = dj["serie"]
    except Exception:  # noqa: BLE001
        pass
    try:   # Sick Index (bolla e credito): serie compatte calcolate da territori.run()
        from . import territori
        tj = territori.leggi()
        for k in ("bolla", "cred", "b_m1", "c_m3", "c_m5"):
            if tj and tj.get("serie", {}).get(k):
                out[k] = tj["serie"][k]
    except Exception:  # noqa: BLE001
        pass
    try:   # sovraccarico del mercato (concentrazione): serie gia' compatta, calcolata da concentrazione.run()
        from . import concentrazione
        cj = concentrazione.leggi()
        for k, ch in (("sovr", "sovr"), ("sacc", "acc")):
            if cj and cj["serie"].get(ch):
                out[k] = cj["serie"][ch]
    except Exception:  # noqa: BLE001
        pass
    try:
        c = pd.read_csv(DATA / "indice_crollo_storia.csv", index_col=0, parse_dates=True)["indice"]
        x = _serie(c)
        if x:
            out["crollo"] = x
    except Exception:  # noqa: BLE001
        pass
    try:   # Status index: serie lunghe (dal 1990) di Crollo, Minimi, Stato e delle loro componenti
        from . import status_index
        si = status_index.leggi()
        if si:
            out.update(si["serie"])
    except Exception:  # noqa: BLE001
        pass
    return out


# Picchi dell'S&P 500 prima di crolli nati DENTRO il sistema finanziario (lista di PROTOCOLLO_TERRITORI.md; esclusi gli shock esterni come il Covid).
PICCHI_ENDOGENI = ["1990-07-16", "1997-10-07", "1998-07-17", "2000-03-24", "2007-10-09", "2010-04-23", "2011-04-29",
                   "2018-01-26", "2018-09-20", "2022-01-03", "2023-02-02", "2024-07-16"]
FINESTRA_PRIMA = 10   # sedute (2 settimane) prima del picco (richiesta del 26/11/2026: accorgersene qualche giorno prima, non mesi)


def _maschere():
    """Giorni di Borsa 'calmi' (S&P 500 a meno del 5% dal massimo di un anno e nessun calo oltre il 5% nelle 63 sedute dopo)
    e, per ogni crollo endogeno, la finestra delle 20 sedute fino al picco incluso (data iniziale, data del picco)."""
    try:
        from . import store
        sp = store.load("sp500").dropna()
        sp = sp[~sp.index.duplicated()].loc["1989-01-01":]
        ora = sp / sp.rolling(252, min_periods=60).max() - 1
        a = sp.to_numpy()
        fmin = pd.Series([a[i + 1:i + 64].min() / a[i] - 1 if i + 63 < len(a) else float("nan") for i in range(len(a))], index=sp.index)
        calmo = ((ora > -0.05) & (fmin > -0.05)).where(fmin.notna())
        fin = []; picchi = []
        for p in PICCHI_ENDOGENI:
            t = pd.Timestamp(p)
            i = sp.index.get_loc(sp.index[sp.index.searchsorted(t)])
            fin.append((sp.index[max(0, i - FINESTRA_PRIMA + 1)], sp.index[i]))
            picchi.append(i)
        _maschere.cal = sp.index; _maschere.picchi = picchi
        return calmo, fin
    except Exception:  # noqa: BLE001
        return None


SOGLIE_ATTIVA = (60, 50)   # l'indice «inizia a dare informazioni importanti» quando supera 60 (se troppo raro, 50)
MAX_PRIMA = 60            # si guarda al massimo 60 sedute (circa 3 mesi) prima del picco


def _anticipo(v, cal, picchi, soglia):
    """Per ogni crollo: quante sedute prima del picco l'indice supera per la prima volta la soglia (entro MAX_PRIMA). None se non la supera."""
    out = []
    for i in picchi:
        w = v[(v.index >= cal[max(0, i - MAX_PRIMA)]) & (v.index <= cal[i] + pd.Timedelta(days=1))]
        s = w[w >= soglia]
        out.append(int((cal[i] >= s.index[0]) and cal.searchsorted(cal[i]) - cal.searchsorted(s.index[0])) if len(s) else None)
    return out


def storia(d: dict) -> dict:
    """Per ogni serie: [media di sempre, media nei mercati calmi, media prima dei crolli endogeni (ogni crollo pesa uno), numero di crolli con dati,
    in quanti di questi la media supera quella dei mercati calmi, sedute prima del crollo a cui si riferisce la media, soglia usata, crolli in cui l'indice
    ha superato la soglia]. Le sedute sono la mediana, fra i crolli in cui l'indice supera la soglia, dell'anticipo con cui la supera la prima volta."""
    m = _maschere()
    out: dict = {}
    for k, r in d.items():
        try:
            t = pd.to_datetime(pd.Series(r["dt"]).cumsum() + r["t0"], unit="D")
            v = pd.Series([x / 10 for x in r["v"]], index=t.values)
            v = v[~v.index.duplicated()]
            row = [round(float(v.mean()), 1), None, None, 0, 0, FINESTRA_PRIMA, 0, 0, None]   # [8] = media delle ultime 5 sedute prima del picco
            if m is not None:
                cal, picchi = _maschere.cal, _maschere.picchi
                z = m[0].reindex(v.index, method="ffill", tolerance=pd.Timedelta(days=7)).fillna(False).astype(bool).to_numpy()
                if z.sum() >= 5:
                    row[1] = round(float(v[z].mean()), 1)
                n_sed, soglia, att = FINESTRA_PRIMA, 0, 0   # finestra fissa: 10 sedute (2 settimane); si guarda anche la media delle ultime 5
                eps, eps5 = [], []
                for i in picchi:
                    w = v[(v.index >= cal[max(0, i - n_sed + 1)]) & (v.index <= cal[i] + pd.Timedelta(days=1))]
                    w5 = v[(v.index >= cal[max(0, i - 4)]) & (v.index <= cal[i] + pd.Timedelta(days=1))]
                    if len(w):
                        eps.append(float(w.mean()))
                    if len(w5):
                        eps5.append(float(w5.mean()))
                if len(eps) >= 5:
                    row[2] = round(sum(eps) / len(eps), 1)
                    row[3] = len(eps)
                    row[5], row[6], row[7] = n_sed, soglia, att
                    row[8] = round(sum(eps5) / len(eps5), 1) if eps5 else None
                    if row[1] is not None:
                        row[4] = sum(1 for e in eps if e > row[1])
            out[k] = row
        except Exception:  # noqa: BLE001
            continue
    return out


CSS = """<style>
[data-gi]{cursor:pointer;-webkit-tap-highlight-color:transparent}
#gi-ov{position:fixed;inset:0;z-index:9999;display:none;align-items:flex-end;justify-content:center;background:rgba(8,12,20,.5);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);opacity:0;transition:opacity .2s}
#gi-ov.on{display:flex}#gi-ov.in{opacity:1}
#gi-sh{width:100%;max-width:580px;max-height:94vh;overflow:auto;overscroll-behavior:contain;background:var(--card);color:var(--tx);border:1px solid var(--bd);border-radius:22px 22px 0 0;padding:12px 14px calc(14px + env(safe-area-inset-bottom));transform:translateY(40px);transition:transform .25s cubic-bezier(.2,.8,.2,1);box-shadow:0 -10px 40px rgba(0,0,0,.25)}
#gi-ov.in #gi-sh{transform:none}
@media(min-width:700px){#gi-ov{align-items:center}#gi-sh{border-radius:22px}}
.gi-hd{display:flex;align-items:flex-start;gap:10px}
.gi-t{flex:1;min-width:0}
.gi-nm{font-size:12px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.gi-zn{font-size:11px;font-weight:800;padding:1px 9px;border-radius:99px;border:1.5px solid var(--c);color:var(--c);text-transform:none;letter-spacing:0;background:color-mix(in srgb,var(--c) 14%,transparent)}
.gi-big{display:flex;align-items:baseline;gap:8px;margin-top:2px;flex-wrap:wrap}
.gi-v{font-size:42px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.gi-dd{font-size:12px;color:var(--mu)}
.gi-x{flex:none;width:36px;height:36px;border-radius:50%;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:20px;line-height:1;cursor:pointer;display:grid;place-items:center;padding:0}
.gi-x:active{transform:scale(.92)}
.gi-bk{flex:none;align-self:center;border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:99px;padding:6px 11px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}
.gi-bk[hidden]{display:none}
.gi-kt{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin:12px 0 5px}
.gi-kt small{text-transform:none;font-weight:400;letter-spacing:0}
.gi-kg{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
.gi-k{border:1px solid var(--bd);background:var(--bg);color:var(--tx);border-radius:12px;padding:6px 8px 7px;text-align:left;font:inherit;cursor:pointer;position:relative;overflow:hidden;transition:.15s}
.gi-k:active{transform:scale(.97)}
.gi-k.inf{border-style:dashed}
.gi-kn{font-size:10.5px;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gi-kv{display:flex;align-items:baseline;justify-content:space-between;gap:4px}
.gi-kv b{font-size:21px;font-weight:800;line-height:1.15;color:var(--c);font-variant-numeric:tabular-nums}
.gi-kv em{font-style:normal;font-size:10.5px;font-weight:700}
.gi-kb{height:4px;border-radius:99px;background:var(--bd);overflow:hidden;margin-top:3px}
.gi-kb i{display:block;height:100%;background:var(--c)}
.gi-kg2{font-size:9.5px;color:var(--mu);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kc.vl{cursor:pointer}.vl-s{font-size:11px;color:var(--mu);margin-top:-2px}
.vl-g{display:flex;position:relative;height:8px;border-radius:99px;margin:9px 0 4px}
.vl-g i{display:block;height:100%}.vl-g i:first-child{border-radius:99px 0 0 99px}.vl-g i:nth-child(4){border-radius:0 99px 99px 0}
.vl-g u{position:absolute;top:-4px;width:3px;height:16px;border-radius:2px;background:var(--tx);box-shadow:0 0 0 2px var(--card);transform:translateX(-1px)}
.vl-p{font-size:11.5px;color:var(--mu);line-height:1.4}.vl-p b{color:var(--tx)}
.gi-hs{margin:8px 0 0}.gi-hr{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.gi-hc{border:1px solid var(--bd);background:var(--bg);border-radius:10px;padding:6px 7px;text-align:center}.gi-hc b{display:block;font-size:20px;font-weight:800;line-height:1.1;font-variant-numeric:tabular-nums}.gi-hc span{display:block;font-size:11px;font-weight:700;color:var(--tx)}.gi-hc small{display:block;font-size:9.5px;color:var(--mu);line-height:1.2;margin-top:1px}.gi-ds{font-size:11.5px;color:var(--mu);line-height:1.4;margin:6px 0 0}
.gi-rg{display:flex;gap:5px;margin:10px 0 6px;overflow-x:auto;scrollbar-width:none;padding-bottom:1px}
.gi-rg::-webkit-scrollbar{display:none}
.gi-rg button{flex:1 0 auto;min-width:38px;border:1px solid var(--bd);background:var(--bg);color:var(--mu);border-radius:99px;padding:5px 9px;font:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:.15s}
.gi-rg button.on{background:var(--tx);color:var(--card);border-color:var(--tx)}
#gi-cv{display:block;width:100%;height:clamp(210px,36vh,290px);touch-action:none;border-radius:12px;background:var(--bg);cursor:crosshair;user-select:none;-webkit-user-select:none}
.gi-hint{font-size:10.5px;color:var(--mu);text-align:center;margin:4px 0 0}
.gi-sc{font-size:11px;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin:12px 0 5px}
.gi-g{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
.gi-c{border:1px solid var(--bd);border-radius:12px;background:var(--bg);padding:7px 6px 6px;text-align:center;position:relative;overflow:hidden}
.gi-c::before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:var(--c)}
.gi-cn{font-size:23px;font-weight:800;line-height:1.1;color:var(--c);font-variant-numeric:tabular-nums}
.gi-cl{font-size:11.5px;font-weight:600;margin-top:1px}
.gi-cs{font-size:10.5px;color:var(--mu);margin-top:1px;min-height:13px}
.gi-cs b{font-weight:700}
</style>"""

JS = r"""<script>(function(){
if(window.giOn)return;window.giOn=1;
var el=document.getElementById('gi-dati');if(!el)return;
var RAW=JSON.parse(el.textContent),Z=JSON.parse(document.getElementById('gi-zone').textContent),NM=JSON.parse(document.getElementById('gi-nomi').textContent),DS=JSON.parse(document.getElementById('gi-desc').textContent),KD=JSON.parse(document.getElementById('gi-kids').textContent),CF=JSON.parse(document.getElementById('gi-cfg').textContent),ST=JSON.parse((document.getElementById('gi-storia')||{textContent:'{}'}).textContent);
var S={};Object.keys(RAW).forEach(function(k){var r=RAW[k],t=[],a=r.t0;for(var i=0;i<r.dt.length;i++){a+=r.dt[i];t.push(a)}S[k]={t:t,v:r.v.map(function(x){return x/10})}});
var ov=document.getElementById('gi-ov');document.body.appendChild(ov);
var sh=document.getElementById('gi-sh'),cv=document.getElementById('gi-cv'),cx=cv.getContext('2d');
var cur=null,T,V,ZN,v0,v1,t0,t1,ya,yb,tya,tyb,cursor=null,W=0,H=0,dpr=1,raf=0,rangeDays=null,C={};
var M={l:8,r:30,t:12,b:22};
var RGD=[['1S',7],['1M',30],['3M',91],['6M',182],['1A',365],['3A',1096],['5A',1826],['Max',0]],RG=RGD;
function cfg(){return CF[cur]||{}}
function fv(v,d){var c=cfg();return it(v,d==null?(c.dec||0):d)+(c.u||'')}
function chips(){var box=document.getElementById('gi-rg');box.innerHTML=RG.map(function(r,i){return '<button type="button" data-i="'+i+'">'+r[0]+'</button>'}).join('');box.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){range(+b.dataset.i)})})}
function it(x,d){var s=x.toFixed(d==null?0:d).replace('.',',');return s.replace('-','−')}
function zi(k,v){var l=Z[k].lim;for(var i=0;i<l.length;i++){if(Z[k].le?v<=l[i]:v<l[i])return i}return l.length}
function zc(v){return Z[cur].col[zi(cur,v)]}
function dfmt(d,o){return new Date(d*864e5).toLocaleDateString('it-IT',Object.assign({timeZone:'UTC'},o))}
function dlong(d){return dfmt(d,{weekday:'short',day:'numeric',month:'short',year:'numeric'})}
function dshort(d){return dfmt(d,{day:'numeric',month:'short'})}
function bs(x){var lo=0,hi=T.length-1;while(lo<hi){var m=(lo+hi+1)>>1;if(T[m]<=x)lo=m;else hi=m-1}return lo}
function setTheme(){var cs=getComputedStyle(document.documentElement);C.tx=cs.getPropertyValue('--tx').trim()||'#222';C.mu=cs.getPropertyValue('--mu').trim()||'#888';C.bd=cs.getPropertyValue('--bd').trim()||'#ddd';C.bg=cs.getPropertyValue('--bg').trim()||'#f4f6f9';C.card=cs.getPropertyValue('--card').trim()||'#fff'}
function size(){dpr=Math.min(3,window.devicePixelRatio||1);W=cv.clientWidth;H=cv.clientHeight;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cx.setTransform(dpr,0,0,dpr,0,0)}
function pw(){return W-M.l-M.r}
function X(d){return M.l+(d-v0)/(v1-v0)*pw()}
function Y(v){return M.t+(1-(v-ya)/(yb-ya))*(H-M.t-M.b)}
function fit(){var a=bs(v0),b=bs(v1),lo=1e9,hi=-1e9;a=Math.max(0,a-1);b=Math.min(T.length-1,b+1);for(var i=a;i<=b;i++){if(V[i]<lo)lo=V[i];if(V[i]>hi)hi=V[i]}var vl=cfg().val,ms=vl?Math.max(1,.14*Math.abs((hi+lo)/2)):16;if(hi-lo<ms){var m=(hi+lo)/2;lo=m-ms/2;hi=m+ms/2}var p=(hi-lo)*.14;if(vl){tya=Math.max(0,lo-p);tyb=hi+p}else{tya=Math.max(0,lo-p);tyb=Math.min(100,hi+p);if(tyb-tya<12){tya=Math.max(0,tyb-12)}}}
function clampView(){var full=T[T.length-1]-T[0],sp=v1-v0;var mn=6,mx=full*1.06+3;if(sp<mn){var c=(v0+v1)/2;v0=c-mn/2;v1=c+mn/2;sp=mn}if(sp>mx){v0=v1-mx;sp=mx}var pad=sp*.04;var lo=T[0]-pad,hi=T[T.length-1]+pad;if(v0<lo){v1+=lo-v0;v0=lo}if(v1>hi){v0-=v1-hi;v1=hi}}
function nice(span,n){var r=span/n,p=Math.pow(10,Math.floor(Math.log10(r))),f=r/p;return(f<1.5?1:f<3?2:f<7?5:10)*p}
function xticks(){var sp=v1-v0,n=Math.max(2,Math.floor(pw()/78)),C0=[['d',1],['d',2],['d',7],['d',14],['m',1],['m',2],['m',3],['m',6],['y',1],['y',2],['y',5],['y',10]],u=null;
for(var i=0;i<C0.length;i++){var a=C0[i],dd=a[0]==='d'?a[1]:a[0]==='m'?30.44*a[1]:365.25*a[1];if(sp/dd<=n){u=a;break}}if(!u)u=['y',10];var out=[],k=u[1];
if(u[0]==='d'){var s=k===7?Math.ceil((v0-4)/7)*7+4:Math.ceil(v0/k)*k;for(var t=s;t<=v1;t+=k)out.push([t,dshort(t)])}
else{var d0=new Date(v0*864e5),y=d0.getUTCFullYear(),m=d0.getUTCMonth();
if(u[0]==='m'){while(true){if(m%k===0){var t2=Date.UTC(y,m,1)/864e5;if(t2>v1)break;if(t2>=v0){var lab=dfmt(t2,{month:'short'});if(sp>400||m===0)lab+=" ’"+String(y).slice(2);out.push([t2,lab])}}m++;if(m>11){m=0;y++}if(y>2200)break}}
else{while(true){if(y%k===0){var t3=Date.UTC(y,0,1)/864e5;if(t3>v1)break;if(t3>=v0)out.push([t3,String(y)])}y++;if(y>2200)break}}}
return out}
function draw(){
if(!cur)return;cx.clearRect(0,0,W,H);var l=Z[cur].lim,co=Z[cur].col,pl=M.l,pr=W-M.r,pt=M.t,pb=H-M.b;
// fasce di colore
for(var i=0;i<co.length;i++){var lo=i===0?-1e3:l[i-1],hi=i===l.length?1e3:l[i];var ya1=Math.max(pt,Math.min(pb,Y(hi))),yb1=Math.max(pt,Math.min(pb,Y(lo)));if(yb1-ya1>.5){cx.globalAlpha=.075;cx.fillStyle=co[i];cx.fillRect(pl,ya1,pr-pl,yb1-ya1)}}
cx.globalAlpha=1;cx.font='10px system-ui,sans-serif';cx.textBaseline='middle';cx.textAlign='left';
// griglia
var st=nice(yb-ya,4);cx.strokeStyle=C.bd;cx.lineWidth=1;cx.fillStyle=C.mu;
for(var g=Math.ceil(ya/st)*st;g<=yb;g+=st){var yy=Math.round(Y(g))+.5;cx.globalAlpha=.7;cx.beginPath();cx.moveTo(pl,yy);cx.lineTo(pr,yy);cx.stroke();cx.globalAlpha=1;cx.fillText(st<1?g.toFixed(1):String(Math.round(g)),pr+4,yy)}
// soglie
cx.setLineDash([4,4]);for(var j=0;j<l.length;j++){var ys=Y(l[j]);if(ys>pt&&ys<pb){cx.strokeStyle=co[j+1]||co[j];cx.globalAlpha=.55;cx.beginPath();cx.moveTo(pl,ys);cx.lineTo(pr,ys);cx.stroke();cx.globalAlpha=1;cx.fillStyle=co[j+1]||co[j];cx.font='700 10px system-ui,sans-serif';cx.fillText(it(l[j],cfg().dec||0),pr+4,ys);cx.font='10px system-ui,sans-serif'}}cx.setLineDash([]);
// asse x
var tk=xticks();cx.fillStyle=C.mu;cx.textAlign='center';cx.textBaseline='top';
tk.forEach(function(q){var xx=X(q[0]);if(xx<pl+8||xx>pr-8)return;cx.strokeStyle=C.bd;cx.globalAlpha=.6;cx.beginPath();cx.moveTo(Math.round(xx)+.5,pb);cx.lineTo(Math.round(xx)+.5,pb+4);cx.stroke();cx.globalAlpha=1;cx.fillText(q[1],xx,pb+6)});
// linea (con pochi punti si disegna tutto; con molti si tiene minimo e massimo di ogni gruppo)
var a=Math.max(0,bs(v0)-1),b=Math.min(T.length-1,bs(v1)+1),n=b-a+1,pts=[],cap=Math.max(60,Math.floor(pw()*1.2));
if(n<=cap){for(var i2=a;i2<=b;i2++)pts.push(i2)}else{var bk=Math.ceil(n/(cap/2));for(var s0=a;s0<=b;s0+=bk){var e0=Math.min(b,s0+bk-1),im=s0,iM=s0;for(var q2=s0;q2<=e0;q2++){if(V[q2]<V[im])im=q2;if(V[q2]>V[iM])iM=q2}if(im<iM){pts.push(im);if(iM!==im)pts.push(iM)}else{pts.push(iM);if(iM!==im)pts.push(im)}}if(pts[pts.length-1]!==b)pts.push(b)}
cx.save();cx.beginPath();cx.rect(pl,pt-2,pr-pl+1,pb-pt+4);cx.clip();
var gr=cx.createLinearGradient(0,pt,0,pb);function stop(o,c){gr.addColorStop(Math.max(0,Math.min(1,o)),c)}
for(var r2=co.length-1;r2>=0;r2--){var hi2=r2===l.length?1e3:l[r2],lo2=r2===0?-1e3:l[r2-1];stop((Y(hi2)-pt)/(pb-pt),co[r2]);stop((Y(lo2)-pt)/(pb-pt),co[r2])}
cx.beginPath();pts.forEach(function(i3,k){var px=X(T[i3]),py=Y(V[i3]);if(k)cx.lineTo(px,py);else cx.moveTo(px,py)});
cx.lineJoin='round';cx.lineCap='round';cx.lineWidth=2.2;cx.strokeStyle=gr;cx.stroke();
var lx=X(T[pts[pts.length-1]]);cx.lineTo(lx,pb);cx.lineTo(X(T[pts[0]]),pb);cx.closePath();cx.globalAlpha=.16;cx.fillStyle=gr;cx.fill();cx.globalAlpha=1;cx.restore();
// ultimo punto
var li=T.length-1;if(T[li]>=v0&&T[li]<=v1){var ex=X(T[li]),ey=Y(V[li]),c0=zc(V[li]);cx.fillStyle=c0;cx.globalAlpha=.25;cx.beginPath();cx.arc(ex,ey,7,0,7);cx.fill();cx.globalAlpha=1;cx.beginPath();cx.arc(ex,ey,3.6,0,7);cx.fill();cx.strokeStyle=C.bg;cx.lineWidth=1.5;cx.stroke()}
// cursore
if(cursor!=null){var ci=cursor,cxp=X(T[ci]);if(cxp>=pl&&cxp<=pr){var cyp=Y(V[ci]),cc=zc(V[ci]);cx.strokeStyle=C.mu;cx.globalAlpha=.7;cx.setLineDash([3,3]);cx.lineWidth=1;cx.beginPath();cx.moveTo(cxp,pt);cx.lineTo(cxp,pb);cx.stroke();cx.setLineDash([]);cx.globalAlpha=1;
cx.fillStyle=cc;cx.beginPath();cx.arc(cxp,cyp,5,0,7);cx.fill();cx.strokeStyle=C.card;cx.lineWidth=2;cx.stroke();
var tx=dshort(T[ci])+(v1-v0>300?' '+dfmt(T[ci],{year:'2-digit'}):'')+' · '+fv(V[ci],1);cx.font='700 11px system-ui,sans-serif';var tw=cx.measureText(tx).width+14,bx=Math.max(pl,Math.min(pr-tw,cxp-tw/2)),by=pt+2;
cx.fillStyle=C.tx;cx.globalAlpha=.92;rr(bx,by,tw,20,10);cx.fill();cx.globalAlpha=1;cx.fillStyle=C.card;cx.textAlign='center';cx.textBaseline='middle';cx.fillText(tx,bx+tw/2,by+10.5)}}
}
function rr(x,y,w,h,r){cx.beginPath();cx.moveTo(x+r,y);cx.arcTo(x+w,y,x+w,y+h,r);cx.arcTo(x+w,y+h,x,y+h,r);cx.arcTo(x,y+h,x,y,r);cx.arcTo(x,y,x+w,y,r);cx.closePath()}
function head(){var i=cursor!=null?cursor:T.length-1,v=V[i],c=zc(v),pv=i>0?V[i-1]:null;
var big=document.getElementById('gi-v');big.textContent=fv(v);big.style.color=c;
var d=document.getElementById('gi-dd'),txt=dlong(T[i]);if(pv!=null){var df=v-pv;txt+=' · <b style="color:'+(Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)')+'">'+(Math.abs(df)<.05?'invariato':(df>0?'▲ +':'▼ −')+it(Math.abs(df),1))+'</b> '+(cfg().pp||'sulla seduta precedente')}d.innerHTML=txt;
var zn=document.getElementById('gi-zn');zn.textContent=Z[cur].nom[zi(cur,v)];zn.style.setProperty('--c',c)}
function loop(){raf=0;var go=false,ease=.22;
if(Math.abs(tv0-v0)>.02||Math.abs(tv1-v1)>.02){v0+=(tv0-v0)*ease;v1+=(tv1-v1)*ease;go=true}else{v0=tv0;v1=tv1}
fit0();if(Math.abs(tya-ya)>.02||Math.abs(tyb-yb)>.02){ya+=(tya-ya)*ease;yb+=(tyb-yb)*ease;go=true}else{ya=tya;yb=tyb}
draw();if(go)raf=requestAnimationFrame(loop)}
var tv0,tv1;function fit0(){var s0=v0,s1=v1;fit()}
function kick(){if(!raf)raf=requestAnimationFrame(loop)}
function setView(a,b,anim){tv0=a;tv1=b;if(!anim){v0=a;v1=b}kick()}
function hit(c){var n=ov.querySelectorAll('.gi-rg button');n.forEach(function(x){x.classList.toggle('on',x.dataset.i===String(c))})}
function range(i){var n=RG[i][1],last=T[T.length-1],first=T[0],b=last+Math.max(1,(n||last-first)*.03),a=n?Math.max(first,last-n):first;tv0=a;tv1=b;rangeDays=i;hit(i);cursor=null;head();kick()}
function atDay(days){var tt=T[T.length-1]-days,i=bs(tt);return i}
function statsVal(){var n=T.length-1,box=document.getElementById('gi-st'),c=cfg(),h='';
function tile(lbl,v,sub){var cc=zc(v);return '<div class="gi-c" style="--c:'+cc+'"><div class="gi-cn">'+fv(v)+'</div><div class="gi-cl">'+lbl+'</div><div class="gi-cs">'+sub+'</div></div>'}
if(c.mean){h+='<div class="gi-sc">Valore medio</div><div class="gi-g">'+c.mean.map(function(m){var a=atDay(m[1]),s=0,k=0;for(var i=a+1;i<=n;i++){s+=V[i];k++}if(!k){s=V[n];k=1}return tile(m[0],s/k,m[1]+' giorni')}).join('')+'</div>'}
h+='<div class="gi-sc">Com\u2019era prima</div><div class="gi-g">'+c.prev.map(function(m){var i=atDay(m[1]),df=V[n]-V[i],cl=Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)';return tile(m[0],V[i],dshort(T[i])+' \u00b7 <b style="color:'+cl+'">'+(Math.abs(df)<.05?'=':(df>0?'\u25b2 ':'\u25bc ')+it(Math.abs(df),c.dec||0))+'</b>')}).join('')+'</div>';
h+='<div class="gi-hint" style="margin-top:6px">'+(c.hint||'Colori rispetto alla storia: verde nella norma, giallo sopra la norma, rosso caro, viola estremo. Freccia rossa = oggi \u00e8 pi\u00f9 caro di allora.')+'</div>';
box.innerHTML=h}
function stats(){if(cfg().val)return statsVal();var n=T.length-1,box=document.getElementById('gi-st'),h='';
function tile(lbl,v,sub){var c=zc(v);return '<div class="gi-c" style="--c:'+c+'"><div class="gi-cn">'+it(v)+'</div><div class="gi-cl">'+lbl+'</div><div class="gi-cs">'+sub+'</div></div>'}
function mean(k){var a=Math.max(0,n-k+1),s=0;for(var i=a;i<=n;i++)s+=V[i];return s/(n-a+1)}
h+='<div class="gi-sc">Valore medio</div><div class="gi-g">'+tile('Ultima settimana',mean(5),'5 sedute')+tile('Ultimo mese',mean(21),'21 sedute')+tile('Ultimi 3 mesi',mean(63),'63 sedute')+'</div>';
function prev(lbl,k){if(n-k<0)return '';var v=V[n-k],df=V[n]-v,c=Math.abs(df)<.05?'var(--mu)':df>0?'var(--bad)':'var(--ok)';return tile(lbl,v,dshort(T[n-k])+' · <b style="color:'+c+'">'+(Math.abs(df)<.05?'=':(df>0?'▲ ':'▼ ')+it(Math.abs(df),1))+'</b>')}
h+='<div class="gi-sc">Com’era prima</div><div class="gi-g">'+prev('Ieri',1)+prev('Una settimana fa',5)+prev('Un mese fa',21)+prev('3 mesi fa',63)+prev('6 mesi fa',126)+'</div>';
h+='<div class="gi-hint" style="margin-top:6px">La freccia mostra di quanto è cambiato l’indice da allora a oggi: rossa se il numero è salito, verde se è sceso.</div>';
box.innerHTML=h}
function kidsGroup(k,ks,title,sub){var h='<div class="gi-kt">'+title+' <small>'+(sub||'(tocca per il grafico)')+'</small></div><div class="gi-kg">';
ks.forEach(function(x){var t=S[x].t,v=S[x].v,n=v.length-1,val=v[n],dv=n>=5?val-v[n-5]:0,c=Z[x].col[zi(x,val)],ar=Math.abs(dv)<.5?'':'<em style="color:'+(dv>0?'var(--bad)':'var(--ok)')+'">'+(dv>0?'\u25b2':'\u25bc')+it(Math.abs(dv),1)+'</em>',tg=KD.tag[x]||'';
h+='<button type="button" class="gi-k'+(x==='i7'||x==='i8'||x==='i9'?' inf':'')+'" data-k="'+x+'" style="--c:'+c+'"><div class="gi-kn">'+NM[x]+'</div><div class="gi-kv"><b>'+it(val)+'</b>'+ar+'</div><div class="gi-kb"><i style="width:'+Math.max(3,Math.min(100,val))+'%"></i></div>'+(tg?'<div class="gi-kg2">'+tg+'</div>':'')+'</button>'});
return h+'</div>'}
function kids(k){var box=document.getElementById('gi-kd'),ks=(KD.kids[k]||[]).filter(function(x){return S[x]}),vs=k==='crollo'?(KD.kids.crollo_var||[]).filter(function(x){return S[x]}):[];if(!ks.length&&!vs.length){box.innerHTML='';return}
var h='';if(ks.length)h+=kidsGroup(k,ks,((k==='sovr'||k==='bolla'||k==='cred'||k==='crollo'||k==='minimi'||k==='stato'||k==='mi_modello'||k==='mi_semplice'||k==='sea'||k==='super'||k==='sa_fin'||k==='sa_eco'||k==='sa_costi'||k==='sa_fam'||k==='sa_pil')?'Da cosa dipende':k==='armor'?'I pilastri dell\u2019Indice Armor':'I pilastri del Super Armor'));
if(vs.length)h+=kidsGroup(k,vs,'Varianti in prova','(altre formule per lo stesso rischio, non sostituiscono l\u2019indice \u00b7 tocca per il grafico)');
box.innerHTML=h;box.querySelectorAll('.gi-k').forEach(function(b){b.addEventListener('click',function(){open(b.dataset.k)})})}
function storiaBox(k){var b=document.getElementById('gi-hs'),r=ST[k];if(!b)return;if(!r){b.innerHTML='';return}
function f(x){return x==null?'\u2013':(cfg().val&&fv?fv(x):it(x,1))}
function t(l,x,s,c){return '<div class="gi-hc"><b style="color:'+(x==null?'var(--mu)':zc(x))+'">'+f(x)+'</b><span>'+l+'</span><small>'+s+'</small></div>'}
b.innerHTML='<div class="gi-hr">'+t('Media storica',r[0],'tutti i giorni, comprese le discese già in corso')+t('Mercati calmi',r[1],'Borsa vicina ai massimi, nessun calo in vista')+t('Prima di un crollo',r[2],r[3]?('media delle 10 sedute (2 settimane) prima del picco di '+r[3]+' crolli nati dentro la finanza'+(r[8]!=null?('; nelle ultime 5: '+String(r[8]).replace('.',',')):'')+'; sopra i mercati calmi in '+r[4]+' su '+r[3]+(r[1]!=null?('. Rispetto ai mercati calmi: '+(r[2]>=r[1]?'+':'')+(r[2]-r[1]).toFixed(1).replace('.',',')+' punti. È sotto la media storica perché questa include le fasi di discesa già avviate, quando l\u2019indice è alto'):'')):'dati troppo pochi')+'</div>'}
function open(k){if(!S[k])return;cur=k;T=S[k].t;V=S[k].v;setTheme();document.getElementById('gi-nm').firstChild.nodeValue=NM[k];document.getElementById('gi-ds').textContent=DS[k]||'';storiaBox(k);RG=cfg().rng||RGD;chips();
document.body.style.overflow='hidden';ov.classList.add('on');requestAnimationFrame(function(){ov.classList.add('in')});size();
cursor=null;range(cfg().def!=null?cfg().def:2);v0=tv0;v1=tv1;fit();ya=tya;yb=tyb;stats();kids(k);var pr=KD.par[k],bk=document.getElementById('gi-bk');if(pr){bk.hidden=false;bk.textContent='\u2039 '+NM[pr];bk.onclick=function(){open(pr)}}else{bk.hidden=true}head();draw();sh.scrollTop=0}
function close(){ov.classList.remove('in');document.body.style.overflow='';setTimeout(function(){if(!ov.classList.contains('in'))ov.classList.remove('on')},220)}
// ---- gesti
var P={},g0=null;
function pos(e){var r=cv.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
function d2x(px){return v0+(px-M.l)/pw()*(v1-v0)}
function near(px){var i=bs(d2x(px));if(i<T.length-1&&Math.abs(T[i+1]-d2x(px))<Math.abs(T[i]-d2x(px)))i++;return Math.max(0,Math.min(T.length-1,i))}
function manual(){rangeDays=null;hit(-1)}
cv.addEventListener('pointerdown',function(e){cv.setPointerCapture(e.pointerId);P[e.pointerId]=pos(e);var ks=Object.keys(P);
if(ks.length===1){g0={m:false,x:P[ks[0]].x,v0:v0,v1:v1,t:e.timeStamp,touch:e.pointerType!=='mouse'}}
else if(ks.length===2){var a=P[ks[0]],b=P[ks[1]];g0={pin:true,d:Math.max(20,Math.abs(a.x-b.x)),c:(a.x+b.x)/2,v0:v0,v1:v1,m:true}}});
cv.addEventListener('pointermove',function(e){var p=pos(e);
if(!P[e.pointerId]){if(e.pointerType==='mouse'){cursor=near(p.x);head();kick()}return}
P[e.pointerId]=p;var ks=Object.keys(P);if(!g0)return;
if(ks.length>=2&&g0.pin){var a=P[ks[0]],b=P[ks[1]],dist=Math.max(20,Math.abs(a.x-b.x)),mid=(a.x+b.x)/2,sp0=g0.v1-g0.v0,sp=sp0*g0.d/dist,anc=g0.v0+(g0.c-M.l)/pw()*sp0,n0=anc-(mid-M.l)/pw()*sp;v0=n0;v1=n0+sp;clampView();tv0=v0;tv1=v1;manual();cursor=null;head();fit();ya=tya;yb=tyb;draw();return}
if(ks.length===1&&!g0.pin){var dx=p.x-g0.x;if(Math.abs(dx)>5)g0.m=true;if(g0.m){var sp1=g0.v1-g0.v0,sh0=-dx/pw()*sp1;v0=g0.v0+sh0;v1=g0.v1+sh0;clampView();tv0=v0;tv1=v1;manual();cursor=null;fit();ya=tya;yb=tyb;draw();head()}else if(!g0.touch){cursor=near(p.x);head();draw()}}});
function up(e){var had=P[e.pointerId];delete P[e.pointerId];var ks=Object.keys(P);
if(g0&&!g0.m&&!g0.pin&&had&&ks.length===0){cursor=near(had.x);head();kick()}
if(ks.length===1&&g0&&g0.pin){var q=P[ks[0]];g0={m:true,x:q.x,v0:v0,v1:v1,touch:true}}
if(ks.length===0)g0=null}
cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
cv.addEventListener('pointerleave',function(e){if(e.pointerType==='mouse'&&!P[e.pointerId]){cursor=null;head();kick()}});
cv.addEventListener('wheel',function(e){e.preventDefault();var p=pos(e),f=Math.exp(e.deltaY*.0015),sp=v1-v0,anc=d2x(p.x),ns=sp*f;v0=anc-(p.x-M.l)/pw()*ns;v1=v0+ns;clampView();tv0=v0;tv1=v1;manual();fit();ya=tya;yb=tyb;draw()},{passive:false});
cv.addEventListener('dblclick',function(){range(RG.length-1)});
// ---- apertura/chiusura
document.addEventListener('click',function(e){var t=e.target;if(t.closest('#gi-ov'))return;var c=t.closest('[data-gi]');if(!c)return;var bl=t.closest('details,summary,a,button,input,select');if(bl&&bl!==c&&c.contains(bl)&&!bl.hasAttribute('data-gi'))return;open(c.getAttribute('data-gi'))});
document.getElementById('gi-xb').addEventListener('click',close);
ov.addEventListener('click',function(e){if(e.target===ov)close()});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&ov.classList.contains('on'))close()});

window.addEventListener('resize',function(){if(ov.classList.contains('on')){size();kick()}});
})()</script>"""


def html() -> str:
    d = dati()
    if not d:
        return ""
    vser, vcfg, vzone = val_cfg()
    zone = {k: {"lim": ZONE[k]["lim"], "col": ZONE[k]["col"], "nom": ZONE[k]["nom"]} for k in d if k in ZONE}
    zone.update(vzone)
    vcfg = {**vcfg, **{k: CFG_SOVR for k in ("sovr", "sacc", "bolla", "cred", "b_m1", "c_m3", "c_m5")}}
    try:
        from . import concentrazione
        cj = concentrazione.leggi()
        if cj:
            DESC["sovr"] = DESC["sovr"] + " " + cj["testo"]["dettaglio"] + " " + concentrazione.testo_analoghi(cj.get("analoghi")) + " " + concentrazione.testo_orizzonti(cj.get("orizzonti"))
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import territori
        tj = territori.leggi()
        for k in ("bolla", "cred"):
            if tj and k in tj.get("sick", {}):
                DESC[k] = DESC[k] + " " + territori.testo_sick(tj["sick"][k])
    except Exception:  # noqa: BLE001
        pass
    return (
        CSS
        + f"<script type='application/json' id='gi-dati'>{json.dumps(d, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-zone'>{json.dumps(zone, ensure_ascii=False, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-nomi'>{json.dumps(NOMI, ensure_ascii=False)}</script>"
        + f"<script type='application/json' id='gi-kids'>{json.dumps({'kids': KIDS, 'par': PAR, 'tag': TAG}, ensure_ascii=False)}</script>"
        + f"<script type='application/json' id='gi-cfg'>{json.dumps(vcfg, ensure_ascii=False, separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-storia'>{json.dumps(storia(d), separators=(',', ':'))}</script>"
        + f"<script type='application/json' id='gi-desc'>{json.dumps(DESC, ensure_ascii=False)}</script>"
        + "<div id='gi-ov' role='dialog' aria-modal='true' aria-label='Grafico dell&#39;indice'><div id='gi-sh'>"
        "<div class='gi-hd'><div class='gi-t'><div class='gi-nm' id='gi-nm'>x<span class='gi-zn' id='gi-zn'></span></div>"
        "<div class='gi-big'><span class='gi-v' id='gi-v'></span><span class='gi-dd' id='gi-dd'></span></div></div>"
        "<button type='button' class='gi-bk' id='gi-bk' hidden></button><button type='button' class='gi-x' id='gi-xb' aria-label='Chiudi'>&times;</button></div>"
        "<div class='gi-ds' id='gi-ds'></div><div class='gi-hs' id='gi-hs'></div>"
        f"<div class='gi-rg' id='gi-rg'></div>"
        "<canvas id='gi-cv'></canvas>"
        "<div class='gi-hint'>Trascina per scorrere · pizzica con due dita per ingrandire · tocca per leggere un giorno</div>"
        "<div id='gi-kd'></div><div id='gi-st'></div></div></div>"
        + JS)
