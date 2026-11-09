"""Finestra sul mondo dell'economia (Patch 54): inflazione, lavoro, crescita, fiducia, casa e mutui, debito, tassi dei titoli di stato, credito e insolvenze,
cambi e materie prime, per Mondo, America, Europa e Asia-Pacifico. Fonti gratuite: FRED (include serie della Banca Mondiale, FMI e BRI), BCE ed Eurostat.
Ogni indicatore mostra la data del dato: se la fonte non lo aggiorna da troppo tempo compare «dato non recente». Descrittivo, non una previsione."""
import concurrent.futures as cf
import io
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from .config import DATA

FILE = DATA / "economia.json"
UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}
AREE = [("mondo", "Mondo"), ("america", "America"), ("europa", "Europa"), ("asia", "Asia e Pacifico")]
CATS = [("inflazione", "Inflazione e prezzi"), ("lavoro", "Lavoro"), ("crescita", "Crescita e consumi"), ("fiducia", "Fiducia dei consumatori"), ("casa", "Casa e mutui"),
        ("debito", "Debito pubblico e privato"), ("tassi", "Tassi e titoli di stato"), ("credito", "Credito e insolvenze"), ("mercati", "Cambi, materie prime e incertezza")]
MAXAGE = {"D": 12, "W": 24, "M": 100, "Q": 270, "A": 800}   # giorni oltre i quali il dato è «non recente» (contati dalla FINE del periodo)
PERIODO = {"D": 0, "W": 0, "M": 31, "Q": 92, "A": 365}


def S(id_, cat, g, nome, area, src, code, tr="lvl", u="%", bene=0, per=12, fr="M", dec=1):
    return {"id": id_, "cat": cat, "g": g, "n": nome, "a": area, "src": src, "code": code, "tr": tr, "u": u, "bene": bene, "per": per, "fr": fr, "dec": dec}


def F(id_, cat, g, nome, area, code, **k):
    return S(id_, cat, g, nome, area, "fred", code, **k)


def _hicp(paese, area, code):
    return F("hicp_" + paese, "inflazione", "infl", paese, area, code, tr="yoy", bene="t")


CAT = [
    # ---- inflazione (annua, mensile)
    F("cpi_us", "inflazione", "infl", "USA · prezzi al consumo", "america", "CPIAUCSL", tr="yoy", bene="t"),
    F("core_us", "inflazione", "infl", "USA · senza energia e alimentari", "america", "CPILFESL", tr="yoy", bene="t"),
    F("pce_us", "inflazione", "infl", "USA · PCE core (indice della Fed)", "america", "PCEPILFE", tr="yoy", bene="t"),
    S("hicp_ea", "inflazione", "infl", "Eurozona · prezzi al consumo", "europa", "ecb", "ICP/M.U2.N.000000.4.ANR", bene="t"),
    _hicp("Germania", "europa", "CP0000DEM086NEST"), _hicp("Francia", "europa", "CP0000FRM086NEST"), _hicp("Italia", "europa", "CP0000ITM086NEST"),
    _hicp("Spagna", "europa", "CP0000ESM086NEST"), _hicp("Paesi Bassi", "europa", "CP0000NLM086NEST"),
    F("ppi_us", "inflazione", "infl2", "USA · prezzi alla produzione", "america", "PPIACO", tr="yoy"),
    F("shelter_us", "inflazione", "infl2", "USA · costo dell'abitazione nell'indice prezzi", "america", "CUSR0000SAH1", tr="yoy"),
    F("food_us", "inflazione", "infl2", "USA · alimentari a casa", "america", "CUSR0000SAF11", tr="yoy"),
    F("wage_us", "inflazione", "infl2", "USA · salari orari medi", "america", "CES0500000003", tr="yoy", bene=1),
    F("exp_us", "inflazione", "infl2", "USA · inflazione attesa dai consumatori (12 mesi)", "america", "MICH", bene="t"),
] + [F("wb_" + c, "inflazione", "infl_a", n, a, "FPCPITOTLZG" + c, bene="t", fr="A", dec=1) for c, n, a in [
    ("WLD", "Mondo", "mondo"), ("USA", "USA", "america"), ("BRA", "Brasile", "america"), ("EMU", "Area euro", "europa"), ("DEU", "Germania", "europa"), ("FRA", "Francia", "europa"),
    ("ITA", "Italia", "europa"), ("GBR", "Regno Unito", "europa"), ("JPN", "Giappone", "asia"), ("CHN", "Cina", "asia"), ("IND", "India", "asia"), ("KOR", "Corea del Sud", "asia"),
    ("IDN", "Indonesia", "asia"), ("AUS", "Australia", "asia")]] + [
    # ---- lavoro
    F("u_us", "lavoro", "disocc", "USA", "america", "UNRATE", bene=-1), F("u6_us", "lavoro", "disocc", "USA · definizione più ampia (U-6)", "america", "U6RATE", bene=-1),
    F("u_ca", "lavoro", "disocc", "Canada", "america", "LRHUTTTTCAM156S", bene=-1), F("u_mx", "lavoro", "disocc", "Messico", "america", "LRHUTTTTMXM156S", bene=-1),
    F("u_de", "lavoro", "disocc", "Germania", "europa", "LRHUTTTTDEM156S", bene=-1), F("u_fr", "lavoro", "disocc", "Francia", "europa", "LRHUTTTTFRM156S", bene=-1),
    F("u_it", "lavoro", "disocc", "Italia", "europa", "LRHUTTTTITM156S", bene=-1), F("u_es", "lavoro", "disocc", "Spagna", "europa", "LRHUTTTTESM156S", bene=-1),
    F("u_gb", "lavoro", "disocc", "Regno Unito", "europa", "LRHUTTTTGBM156S", bene=-1), F("u_nl", "lavoro", "disocc", "Paesi Bassi", "europa", "LRHUTTTTNLM156S", bene=-1),
    F("u_se", "lavoro", "disocc", "Svezia", "europa", "LRHUTTTTSEM156S", bene=-1), F("u_pl", "lavoro", "disocc", "Polonia", "europa", "LRHUTTTTPLM156S", bene=-1),
    S("u_ea", "lavoro", "disocc", "Eurozona", "europa", "ecb", "LFSI/M.I9.S.UNEHRT.TOTAL0.15_74.T", bene=-1),
    F("u_jp", "lavoro", "disocc", "Giappone", "asia", "LRHUTTTTJPM156S", bene=-1), F("u_kr", "lavoro", "disocc", "Corea del Sud", "asia", "LRHUTTTTKRM156S", bene=-1),
    F("u_au", "lavoro", "disocc", "Australia", "asia", "LRHUTTTTAUM156S", bene=-1),
    F("part_us", "lavoro", "occ", "USA · partecipazione al lavoro", "america", "CIVPART", bene=1), F("emp_us", "lavoro", "occ", "USA · occupati sul totale della popolazione", "america", "EMRATIO", bene=1),
    F("pay_us", "lavoro", "occ", "USA · nuovi posti di lavoro al mese (migliaia)", "america", "PAYEMS", tr="diff", u="k", bene=1, dec=0),
    F("jolts_us", "lavoro", "occ", "USA · posti vacanti (migliaia)", "america", "JTSJOL", u="k", bene=0, dec=0),
    F("claims_us", "lavoro", "occ", "USA · nuove richieste di sussidio (settimanali)", "america", "ICSA", u="", bene=-1, fr="W", dec=0),
    F("cclaims_us", "lavoro", "occ", "USA · richieste di sussidio continuative", "america", "CCSA", u="", bene=-1, fr="W", dec=0),
    F("sahm_us", "lavoro", "occ", "USA · regola di Sahm (≥0,5 = segnale di recessione)", "america", "SAHMREALTIME", u="pt", bene=-1, dec=2),
    # ---- crescita e consumi
    F("gdp_us", "crescita", "pil", "USA · PIL reale, su base annua", "america", "GDPC1", tr="yoy", per=4, fr="Q", bene=1),
    S("gdp_ea", "crescita", "pil", "Eurozona · PIL reale, su base annua", "europa", "ecb", "MNA/Q.Y.I9.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY", fr="Q", bene=1),
    F("ip_us", "crescita", "cons", "USA · produzione industriale, su base annua", "america", "INDPRO", tr="yoy", bene=1),
    F("rs_us", "crescita", "cons", "USA · vendite al dettaglio, su base annua", "america", "RSAFS", tr="yoy", bene=1),
    F("inc_us", "crescita", "cons", "USA · reddito disponibile reale, su base annua", "america", "DSPIC96", tr="yoy", bene=1),
    F("sav_us", "crescita", "cons", "USA · tasso di risparmio delle famiglie", "america", "PSAVERT", bene=0),
    # ---- fiducia
    F("conf_us", "fiducia", "fid", "USA (Univ. Michigan)", "america", "UMCSENT", bene=1),
    S("conf_ea", "fiducia", "fid", "Eurozona", "europa", "eurostat", "ei_bsco_m|geo=EA20", bene=1), S("conf_de", "fiducia", "fid", "Germania", "europa", "eurostat", "ei_bsco_m|geo=DE", bene=1),
    S("conf_fr", "fiducia", "fid", "Francia", "europa", "eurostat", "ei_bsco_m|geo=FR", bene=1), S("conf_it", "fiducia", "fid", "Italia", "europa", "eurostat", "ei_bsco_m|geo=IT", bene=1),
    S("conf_es", "fiducia", "fid", "Spagna", "europa", "eurostat", "ei_bsco_m|geo=ES", bene=1), S("conf_nl", "fiducia", "fid", "Paesi Bassi", "europa", "eurostat", "ei_bsco_m|geo=NL", bene=1),
    S("conf_pl", "fiducia", "fid", "Polonia", "europa", "eurostat", "ei_bsco_m|geo=PL", bene=1), S("conf_eu", "fiducia", "fid", "Unione europea (27)", "europa", "eurostat", "ei_bsco_m|geo=EU27_2020", bene=1),
    F("conf_jp", "fiducia", "fid", "Giappone (indicatore OECD)", "asia", "CSCICP02JPM460S", bene=1), F("conf_cn", "fiducia", "fid", "Cina (indicatore OECD)", "asia", "CSCICP02CNM460S", bene=1),
    # ---- casa e mutui
    F("m30_us", "casa", "mutuo", "USA · mutuo a 30 anni", "america", "MORTGAGE30US", fr="W", u="%", dec=2), F("m15_us", "casa", "mutuo", "USA · mutuo a 15 anni", "america", "MORTGAGE15US", fr="W", dec=2),
    F("mj_us", "casa", "mutuo", "USA · mutuo «jumbo» a 30 anni", "america", "OBMMIJUMBO30YF", fr="W", dec=2),
    S("m_ea", "casa", "mutuo", "Eurozona · nuovi mutui per la casa", "europa", "ecb", "MIR/M.U2.B.A2C.AM.R.A.2250.EUR.N", dec=2),
    F("cs_us", "casa", "prezzi", "USA · prezzi delle case (Case-Shiller, annuo)", "america", "CSUSHPINSA", tr="yoy"),
] + [F("hp_" + c, "casa", "prezzi", n, a, "Q%sR628BIS" % c, tr="yoy", per=4, fr="Q") for c, n, a in [
    ("US", "USA · prezzi reali delle case (BRI, annuo)", "america"), ("DE", "Germania · prezzi reali delle case", "europa"), ("FR", "Francia · prezzi reali delle case", "europa"),
    ("GB", "Regno Unito · prezzi reali delle case", "europa"), ("ES", "Spagna · prezzi reali delle case", "europa"), ("IT", "Italia · prezzi reali delle case", "europa"),
    ("JP", "Giappone · prezzi reali delle case", "asia"), ("KR", "Corea del Sud · prezzi reali delle case", "asia"), ("CN", "Cina · prezzi reali delle case", "asia"),
    ("AU", "Australia · prezzi reali delle case", "asia")]] + [
    F("medp_us", "casa", "us_casa", "USA · prezzo mediano delle case vendute ($)", "america", "MSPUS", u="$", fr="Q", dec=0),
    F("list_us", "casa", "us_casa", "USA · prezzo mediano delle case in vendita ($)", "america", "MEDLISPRIUS", u="$", dec=0),
    F("act_us", "casa", "us_casa", "USA · case in vendita (numero)", "america", "ACTLISCOUUS", u="", dec=0),
    F("hs_us", "casa", "us_casa", "USA · cantieri avviati (migliaia, annualizzati)", "america", "HOUST", u="k", bene=0, dec=0),
    F("perm_us", "casa", "us_casa", "USA · permessi di costruzione (migliaia)", "america", "PERMIT", u="k", dec=0),
    F("ns_us", "casa", "us_casa", "USA · vendite di case nuove (migliaia)", "america", "HSN1F", u="k", bene=1, dec=0),
    F("es_us", "casa", "us_casa", "USA · vendite di case esistenti", "america", "EXHOSLUSM495S", u="", bene=1, dec=0),
    F("sup_us", "casa", "us_casa", "USA · mesi di offerta di case nuove", "america", "MSACSR", bene=-1),
    F("aff_us", "casa", "us_casa", "USA · accessibilità della casa (100 = redditto mediano compra casa mediana)", "america", "FIXHAI", bene=1),
    F("own_us", "casa", "us_casa", "USA · famiglie proprietarie di casa", "america", "RHORUSQ156N", fr="Q"),
    F("vac_us", "casa", "us_casa", "USA · affitti sfitti", "america", "RRVRUSQ156N", fr="Q"),
    F("rent_us", "casa", "us_casa", "USA · affitti, su base annua", "america", "CUSR0000SEHA", tr="yoy"),
    # ---- debito
    F("dp_us", "debito", "dpub_t", "USA · debito federale / PIL", "america", "GFDEGDQ188S", fr="Q", bene=-1),
] + [F("dpub_" + c, "debito", "dpub", n, a, "GGGDTA%sA188N" % c, fr="A", bene=-1, dec=0) for c, n, a in [
    ("US", "USA", "america"), ("DE", "Germania", "europa"), ("FR", "Francia", "europa"), ("IT", "Italia", "europa"), ("ES", "Spagna", "europa"), ("GB", "Regno Unito", "europa"),
    ("JP", "Giappone", "asia"), ("CN", "Cina", "asia"), ("IN", "India", "asia"), ("KR", "Corea del Sud", "asia")]
] + [F("dfam_" + c, "debito", "dfam", n, a, "Q%sHAM770A" % c, fr="Q", bene=-1) for c, n, a in [
    ("US", "USA", "america"), ("BR", "Brasile", "america"), ("DE", "Germania", "europa"), ("FR", "Francia", "europa"), ("GB", "Regno Unito", "europa"), ("IT", "Italia", "europa"), ("ES", "Spagna", "europa"),
    ("JP", "Giappone", "asia"), ("CN", "Cina", "asia"), ("KR", "Corea del Sud", "asia"), ("AU", "Australia", "asia")]] + [
    F("dpriv_" + c, "debito", "dpriv", n, a, "Q%sPAM770A" % c, fr="Q", bene=-1, dec=0) for c, n, a in [
    ("US", "USA", "america"), ("DE", "Germania", "europa"), ("FR", "Francia", "europa"), ("GB", "Regno Unito", "europa"), ("IT", "Italia", "europa"), ("ES", "Spagna", "europa"),
    ("JP", "Giappone", "asia"), ("CN", "Cina", "asia"), ("KR", "Corea del Sud", "asia"), ("AU", "Australia", "asia")]] + [
    F("tdsp_us", "debito", "dfam_us", "USA · rate dei debiti / reddito disponibile", "america", "TDSP", fr="Q", bene=-1, dec=1),
    F("mdsp_us", "debito", "dfam_us", "USA · rate dei mutui / reddito disponibile", "america", "MDSP", fr="Q", bene=-1, dec=1),
    F("hdebt_us", "debito", "dfam_us", "USA · debiti delle famiglie (milioni $)", "america", "CMDEBT", fr="Q", u="", bene=0, dec=0),
    # ---- tassi
    F("ff_us", "tassi", "uff", "USA · tasso della Fed", "america", "FEDFUNDS", dec=2), F("ecb_dep", "tassi", "uff", "Eurozona · tasso sui depositi BCE", "europa", "ECBDFR", fr="D", dec=2),
    F("ecb_mro", "tassi", "uff", "Eurozona · tasso di rifinanziamento BCE", "europa", "ECBMRRFR", fr="D", dec=2),
    F("y2_us", "tassi", "b2", "USA · 2 anni", "america", "DGS2", fr="D", dec=2), F("y30_us", "tassi", "b2", "USA · 30 anni", "america", "DGS30", fr="D", dec=2),
    F("c10_2", "tassi", "b2", "USA · differenza 10 anni - 2 anni (negativa = curva invertita)", "america", "T10Y2Y", fr="D", dec=2),
    F("b_us", "tassi", "b10", "USA", "america", "DGS10", fr="D", dec=2), F("b_ca", "tassi", "b10", "Canada", "america", "IRLTLT01CAM156N", dec=2), F("b_mx", "tassi", "b10", "Messico", "america", "IRLTLT01MXM156N", dec=2),
] + [F("b_" + c, "tassi", "b10", n, "europa", "IRLTLT01%sM156N" % c, dec=2) for c, n in [("DE", "Germania"), ("FR", "Francia"), ("IT", "Italia"), ("ES", "Spagna"), ("NL", "Paesi Bassi"), ("PT", "Portogallo"),
                                                                                       ("GR", "Grecia"), ("IE", "Irlanda"), ("GB", "Regno Unito"), ("CH", "Svizzera"), ("SE", "Svezia"), ("PL", "Polonia")]] + [
    F("b_jp", "tassi", "b10", "Giappone", "asia", "IRLTLT01JPM156N", dec=2), F("b_kr", "tassi", "b10", "Corea del Sud", "asia", "IRLTLT01KRM156N", dec=2),
    F("b_au", "tassi", "b10", "Australia", "asia", "IRLTLT01AUM156N", dec=2), F("b_nz", "tassi", "b10", "Nuova Zelanda", "asia", "IRLTLT01NZM156N", dec=2),
    F("b_za", "tassi", "b10", "Sudafrica", "mondo", "IRLTLT01ZAM156N", dec=2),
    # ---- credito e insolvenze
    F("dl_mut", "credito", "insol", "USA · mutui casa in ritardo nei pagamenti", "america", "DRSFRMACBS", fr="Q", bene=-1, dec=2), F("dl_cc", "credito", "insol", "USA · carte di credito in ritardo", "america", "DRCCLACBS", fr="Q", bene=-1, dec=2),
    F("dl_all", "credito", "insol", "USA · tutti i prestiti in ritardo", "america", "DRALACBS", fr="Q", bene=-1, dec=2), F("dl_biz", "credito", "insol", "USA · prestiti alle imprese in ritardo", "america", "DRBLACBS", fr="Q", bene=-1, dec=2),
    F("co_cc", "credito", "insol", "USA · carte di credito perdite definitive", "america", "CORCCACBS", fr="Q", bene=-1, dec=2),
    F("cc_rate", "credito", "cred", "USA · interesse medio sulle carte di credito", "america", "TERMCBCCALLNS", fr="Q", dec=1),
    F("cons_us", "credito", "cred", "USA · credito al consumo, su base annua", "america", "TOTALSL", tr="yoy"), F("rev_us", "credito", "cred", "USA · credito revolving, su base annua", "america", "REVOLSL", tr="yoy"),
    F("biz_us", "credito", "cred", "USA · prestiti alle imprese, su base annua", "america", "TOTCI", tr="yoy", per=52, fr="W"),
    F("hy_us", "credito", "spread", "USA · spread «high yield» (rischio delle imprese più fragili)", "america", "BAMLH0A0HYM2", fr="D", bene=-1, dec=2),
    F("hy_eu", "credito", "spread", "Europa · spread «high yield»", "europa", "BAMLHE00EHYIOAS", fr="D", bene=-1, dec=2),
    F("hy_em", "credito", "spread", "Mercati emergenti · spread delle imprese", "mondo", "BAMLEMCBPIOAS", fr="D", bene=-1, dec=2),
    # ---- cambi, materie prime, incertezza
    F("usd", "mercati", "cambi", "Dollaro contro le principali valute", "mondo", "DTWEXBGS", fr="D", u="", dec=1),
    F("eur", "mercati", "cambi", "Euro: dollari per 1 euro", "europa", "DEXUSEU", fr="D", u="$", dec=3), F("jpy", "mercati", "cambi", "Yen per 1 dollaro", "asia", "DEXJPUS", fr="D", u="", dec=1),
    F("cny", "mercati", "cambi", "Yuan per 1 dollaro", "asia", "DEXCHUS", fr="D", u="", dec=3), F("krw", "mercati", "cambi", "Won per 1 dollaro", "asia", "DEXKOUS", fr="D", u="", dec=0),
    F("inr", "mercati", "cambi", "Rupie per 1 dollaro", "asia", "DEXINUS", fr="D", u="", dec=2),
    F("brent", "mercati", "mat", "Petrolio Brent ($ al barile)", "mondo", "POILBREUSDM", u="$", dec=1), F("rame", "mercati", "mat", "Rame ($ alla tonnellata)", "mondo", "PCOPPUSDM", u="$", dec=0),
    F("food", "mercati", "mat", "Prezzi alimentari mondiali, su base annua", "mondo", "PFOODINDEXM", tr="yoy"), F("comm", "mercati", "mat", "Tutte le materie prime, su base annua", "mondo", "PALLFNFINDEXM", tr="yoy"),
    F("gepu", "mercati", "inc", "Incertezza politica globale", "mondo", "GEPUCURRENT", u="", bene=-1, dec=0), F("epu_us", "mercati", "inc", "Incertezza politica USA (giornaliera)", "america", "USEPUINDXD", fr="D", u="", bene=-1, dec=0),
]

GINFO = {
    "infl": ("Inflazione annua", "Quanto sono saliti i prezzi al consumo rispetto a 12 mesi prima.", "Le banche centrali puntano al 2%: molto sopra riduce il potere d'acquisto e spinge i tassi in alto; molto sotto (o negativa) segnala domanda debole. «Migliora» = si avvicina al 2%."),
    "infl2": ("Prezzi, salari e attese (USA)", "Altri pezzi dell'inflazione: prezzi alla produzione, casa, alimentari, salari, attese dei consumatori.", "Salari e abitazione che salgono troppo mantengono alta l'inflazione. Per le attese conta la distanza dal 2%."),
    "infl_a": ("Inflazione annua media (Banca Mondiale)", "Variazione media dei prezzi nell'anno, per paese e mondo. Dato annuale, esce con ritardo.", "Serve a confrontare paesi che non hanno dati mensili aggiornati in modo gratuito."),
    "disocc": ("Tasso di disoccupazione", "Quota di persone che cercano lavoro e non lo trovano.", "Basso = lavoro solido; in forte salita è un segnale di recessione. Le definizioni cambiano da paese a paese: guarda soprattutto la tendenza."),
    "occ": ("Occupazione e mercato del lavoro (USA)", "Partecipazione, occupati, nuovi posti, posti vacanti, sussidi e regola di Sahm.", "La regola di Sahm si accende (≥0,5) quando la disoccupazione sale in fretta: in passato è coincisa con le recessioni."),
    "pil": ("Crescita dell'economia (PIL reale)", "Quanto è cresciuta la produzione di beni e servizi rispetto a un anno prima, tolta l'inflazione.", "Sopra zero = economia in crescita; sotto zero per due trimestri di fila = recessione tecnica."),
    "cons": ("Produzione e consumi (USA)", "Produzione industriale, vendite al dettaglio, reddito reale e risparmio.", "Reddito e consumi reali in calo sono i primi segnali di rallentamento."),
    "fid": ("Fiducia dei consumatori", "Quanto le famiglie sono ottimiste su economia e bilancio personale. Scale diverse da paese a paese: confronta la tendenza, non i numeri.", "Fiducia in calo anticipa spesso una frenata dei consumi (circa il 60-70% dell'economia di molti paesi)."),
    "mutuo": ("Tassi dei mutui", "Interesse richiesto per comprare casa.", "Tassi alti riducono la domanda di case e i prezzi nel tempo; tassi in calo sostengono il mercato."),
    "prezzi": ("Prezzi delle case", "Variazione annua dei prezzi delle abitazioni (indici reali della BRI, cioè al netto dell'inflazione).", "Cali prolungati colpiscono banche e consumi (come nel 2008); aumenti molto rapidi possono indicare bolle."),
    "us_casa": ("Mercato della casa (USA)", "Prezzi mediani, offerta, cantieri, vendite, affitti e accessibilità.", "Poche case in vendita e prezzi alti con mutui cari = poche vendite. Offerta che sale e vendite in calo = mercato che si raffredda."),
    "dpub": ("Debito pubblico / PIL", "Debito dello Stato diviso per la produzione annua (dati FMI, annuali, con ritardo).", "Più è alto, più interessi pesano sul bilancio. Non indica da solo una crisi: conta anche chi detiene il debito e la valuta."),
    "dpub_t": ("Debito federale USA / PIL", "Dato trimestrale del debito federale rispetto al PIL.", "Sopra il 100% = debito superiore alla produzione di un anno."),
    "dfam": ("Debito delle famiglie / PIL", "Debiti di famiglie e istituzioni senza scopo di lucro rispetto al PIL (BRI, trimestrale).", "Alto = famiglie più vulnerabili ai tassi in salita."),
    "dpriv": ("Debito privato non finanziario / PIL", "Debiti di famiglie e imprese rispetto al PIL (BRI, trimestrale).", "Crescite molto rapide hanno preceduto molte crisi finanziarie."),
    "dfam_us": ("Peso del debito sulle famiglie USA", "Quota del reddito usata per pagare le rate; debito totale.", "Salita = meno spazio per i consumi."),
    "uff": ("Tassi ufficiali delle banche centrali", "Il tasso di riferimento deciso da Fed e BCE.", "Tassi alti frenano l'economia e l'inflazione; tagli la sostengono."),
    "b2": ("Titoli di stato USA e curva dei rendimenti", "Rendimenti a 2 e 30 anni e differenza 10-2 anni.", "Curva invertita (differenza negativa) ha preceduto molte recessioni, con ritardo molto variabile."),
    "b10": ("Rendimento dei titoli di stato a 10 anni", "Interesse annuo richiesto per prestare soldi allo Stato per 10 anni.", "In salita = lo Stato paga di più e i mutui costano di più. Lo scarto tra paesi (es. Italia - Germania) misura la fiducia dei mercati."),
    "insol": ("Insolvenze e ritardi nei pagamenti (USA)", "Quota di prestiti non pagati in tempo (dati delle banche USA, trimestrali).", "In salita = famiglie e imprese in difficoltà: anticipa perdite per le banche."),
    "cred": ("Credito alle famiglie e alle imprese (USA)", "Quanto crescono i prestiti e quanto costa il credito con la carta.", "Credito che si ferma segnala banche prudenti o domanda debole."),
    "spread": ("Rischio delle imprese più fragili (spread high yield)", "Interesse in più richiesto alle imprese con rating basso rispetto ai titoli sicuri.", "Sopra 5-6 punti = paura di insolvenze; sotto 3-4 = mercato tranquillo."),
    "cambi": ("Cambi", "Valore delle principali valute contro il dollaro o l'euro.", "Un dollaro molto forte mette sotto pressione i paesi indebitati in dollari."),
    "mat": ("Materie prime", "Petrolio, rame, alimentari e panieri di materie prime.", "Il rame e il petrolio riflettono la domanda industriale globale; i prezzi alimentari pesano sull'inflazione e sui paesi poveri."),
    "inc": ("Incertezza politica", "Indice basato sulle notizie sull'incertezza economica e politica.", "Valori alti coincidono con investimenti rinviati e mercati più nervosi."),
}


# ---------------------------------------------------------------- fonti
def fetch_fred(code: str) -> pd.Series:
    from . import sources
    import os
    if os.environ.get("FRED_API_KEY", "").strip():
        s = sources.fetch_fred(code)
    else:   # il CSV pubblico di FRED a volte non risponde con l'intestazione «Mozilla»: qui si usa quella standard di requests
        last = None
        for _ in range(2):
            try:
                r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}", timeout=25)
                r.raise_for_status()
                s = sources.parse_fred_csv(r.text)
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            raise RuntimeError(str(last))
    return s[s.index >= "2004-01-01"]


def parse_ecb_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    df["d"] = df["TIME_PERIOD"].map(_periodo)
    return df.assign(v=pd.to_numeric(df["OBS_VALUE"], errors="coerce")).dropna(subset=["d", "v"]).set_index("d")["v"].sort_index()


def _periodo(p) -> pd.Timestamp | None:
    p = str(p)
    try:
        if "-Q" in p:
            return pd.Period(p.replace("-", ""), "Q").to_timestamp()
        return pd.Timestamp(p)
    except Exception:  # noqa: BLE001
        return None


def fetch_ecb(spec: str) -> pd.Series:
    flow, key = spec.split("/", 1)
    last = None
    for _ in range(3):
        try:
            r = requests.get(f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}?startPeriod=2004-01&format=csvdata", timeout=45)
            r.raise_for_status()
            return parse_ecb_csv(r.text)
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(str(last))


def parse_jsonstat(j: dict) -> pd.Series:
    """Risposta JSON-stat di Eurostat con una sola dimensione libera (il tempo)."""
    idx = j["dimension"]["time"]["category"]["index"]
    vals = j.get("value", {})
    rows = {_periodo(t): vals.get(str(i)) for t, i in idx.items()}
    s = pd.Series(rows, dtype=float).dropna()
    return s.sort_index()


def fetch_eurostat(spec: str) -> pd.Series:
    ds, rest = spec.split("|", 1)
    extra = "&indic=BS-CSMCI-BAL&s_adj=SA&unit=BAL" if ds == "ei_bsco_m" else ""
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}?{rest}{extra}&sinceTimePeriod=2004-01&format=JSON&lang=EN"
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    return parse_jsonstat(r.json())


FETCH = {"fred": fetch_fred, "ecb": fetch_ecb, "eurostat": fetch_eurostat}


# ---------------------------------------------------------------- calcolo
def trasforma(s: pd.Series, tr: str, per: int) -> pd.Series:
    s = s.dropna()
    if tr == "yoy":
        s = (s.pct_change(per) * 100).replace([np.inf, -np.inf], np.nan)
    elif tr == "diff":
        s = s.diff()
    return s.dropna()


def valuta(t: pd.Series, bene) -> str:
    """Confronto con un anno prima: ok = migliora, wa = stabile, ba = peggiora, na = indicatore senza giudizio."""
    if bene == 0 or len(t) < 6:
        return "na"
    ult = t.index[-1]
    prima = t[t.index <= ult - pd.Timedelta(days=350)]
    if prima.empty:
        return "na"
    v, y = float(t.iloc[-1]), float(prima.iloc[-1])
    sd = float(t.iloc[-60:].std()) or abs(v) * 0.05 or 1.0
    thr = 0.15 * sd
    delta = (abs(y - 2.0) - abs(v - 2.0)) if bene == "t" else (v - y) * bene
    return "ok" if delta > thr else "ba" if delta < -thr else "wa"


def vecchio(t: pd.Series, fr: str, oggi=None) -> bool:
    oggi = pd.Timestamp(oggi) if oggi is not None else pd.Timestamp.now().normalize()
    return (oggi - t.index[-1]).days - PERIODO.get(fr, 31) > MAXAGE.get(fr, 100)


def scheda(sp: dict, s: pd.Series, oggi=None) -> dict | None:
    t = trasforma(s, sp["tr"], sp["per"])
    if len(t) < 2:
        return None
    ult = t.index[-1]
    anno = t[t.index <= ult - pd.Timedelta(days=350)]
    h = t.resample("MS").last().dropna() if sp["fr"] in ("D", "W") else t
    h = h[h.index >= h.index[-1] - pd.DateOffset(years=15)]
    passo = {"M": 1, "Q": 3, "A": 12}.get(sp["fr"] if sp["fr"] not in ("D", "W") else "M", 1)
    d = sp["dec"] + (2 if sp["tr"] == "yoy" and sp["dec"] < 2 else 0)
    return {"id": sp["id"], "n": sp["n"], "a": sp["a"], "c": sp["cat"], "g": sp["g"], "u": sp["u"] if sp["tr"] != "yoy" else "%", "dec": sp["dec"], "fr": sp["fr"], "bene": sp["bene"],
            "v": round(float(t.iloc[-1]), d), "p": round(float(t.iloc[-2]), d), "y": None if anno.empty else round(float(anno.iloc[-1]), d), "d": str(ult.date()),
            "st": valuta(t, sp["bene"]), "old": vecchio(t, sp["fr"], oggi), "h0": str(h.index[0].date())[:7], "ps": passo, "h": [round(float(x), d) for x in h.values]}


def aggiorna(log=print, catalogo=None, fetch=None) -> dict:
    catalogo = catalogo or CAT
    fetch = fetch or FETCH

    def uno(sp):
        try:
            s = fetch[sp["src"]](sp["code"])
            sc = scheda(sp, s)
            return sp["id"], sc, None if sc else "serie troppo corta"
        except Exception as e:  # noqa: BLE001
            return sp["id"], None, str(e)[:80]
    items, errori = [], {}
    with cf.ThreadPoolExecutor(3) as ex:
        for i, sc, err in ex.map(uno, catalogo):
            if sc:
                items.append(sc)
            else:
                errori[i] = err
    ordine = {sp["id"]: n for n, sp in enumerate(catalogo)}
    items.sort(key=lambda x: ordine[x["id"]])
    d = {"asof": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "aree": AREE, "cats": CATS, "ginfo": GINFO, "items": items, "errori": errori}
    FILE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"[economia] {len(items)} indicatori, {len(errori)} non disponibili: {', '.join(list(errori)[:25])}")
    return d


def carica() -> str | None:
    return FILE.read_text(encoding="utf-8") if FILE.exists() else None


# ---------------------------------------------------------------- pagina
CSS = ("<style>.ecw{margin-top:8px}.ecf{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.ecf button{padding:8px 14px;border:1px solid var(--bd);border-radius:99px;background:var(--card);color:var(--tx);font-weight:600;font-size:13px;cursor:pointer}"
       ".ecf button.on{background:linear-gradient(135deg,var(--ac),#6366f1);color:#fff;border-color:transparent}.ecs{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0}"
       ".ecs span{padding:6px 12px;border-radius:99px;font-size:13px;font-weight:700}.ecs .ok{background:var(--okbg);color:var(--ok)}.ecs .wa{background:var(--warnbg);color:var(--warn)}.ecs .ba{background:var(--badbg);color:var(--bad)}"
       ".ecc{margin:18px 0 6px;font-size:17px}.ecg{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:6px 14px 10px;margin:10px 0;box-shadow:0 1px 2px rgba(15,23,42,.05)}"
       ".ecg h4{margin:10px 0 2px;font-size:15px}.ecr{display:grid;grid-template-columns:1fr auto 70px;gap:4px 10px;align-items:center;padding:9px 0;border-top:1px solid var(--bd);cursor:pointer}"
       ".ecr:first-of-type{border-top:0}.ecn{font-size:13.5px;line-height:1.3}.ecn small{display:block;color:var(--mu);font-size:11.5px}.ecv{text-align:right;font-weight:800;font-size:16px;font-variant-numeric:tabular-nums}"
       ".ecv small{display:block;font-weight:600;font-size:11.5px}.ecr svg{width:70px;height:24px}.ecd{grid-column:1/-1;padding:4px 0}.ecd svg{width:100%;height:150px}"
       ".ok .ecv small{color:var(--ok)}.ba .ecv small{color:var(--bad)}.wa .ecv small{color:var(--warn)}.ecold{color:var(--mu)!important;font-style:italic}.ecdot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--mu)}"
       ".ok .ecdot{background:var(--ok)}.wa .ecdot{background:var(--warn)}.ba .ecdot{background:var(--bad)}</style>")

JS = r"""<script>(function(){var W=document.querySelector('[data-ec]');if(!W||W.dataset.on)return;W.dataset.on=1;var D=null,AREA='',CAT='',OPEN=null;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function nf(x,d){if(x==null)return '—';var s=Number(x).toFixed(d==null?1:d),p=s.split('.');p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');return p.join(',').replace('-','−')}
function dm(s){var a=s.split('-');return a[2]+'/'+a[1]+'/'+a[0]}
function spark(h,w,ht,full){if(!h||h.length<2)return '';var k=h.slice(full?0:-36),mn=Math.min.apply(null,k),mx=Math.max.apply(null,k),r=mx-mn||1,p=k.map(function(v,i){return (i*(w-2)/(k.length-1)+1).toFixed(1)+','+((ht-3)-(v-mn)/r*(ht-6)+1.5).toFixed(1)}).join(' ');
return '<svg viewBox="0 0 '+w+' '+ht+'" preserveAspectRatio="none"><polyline fill="none" stroke="#3b82f6" stroke-width="'+(full?2:1.6)+'" vector-effect="non-scaling-stroke" points="'+p+'"/></svg>'}
function etichetta(x){var m={ok:'in miglioramento',wa:'stabile',ba:'in peggioramento',na:''};return m[x.st]||''}
function chg(x){if(x.y==null)return '';var dl=x.v-x.y,s=(dl>0?'+':'')+nf(dl,x.dec>1?x.dec:Math.max(x.dec,1));return s+(x.u==='%'?' pt':'')+' in un anno'}
function det(x){var h=x.h,mn=Math.min.apply(null,h),mx=Math.max.apply(null,h),y0=+x.h0.slice(0,4),n=h.length;
return '<div class="ecd">'+spark(h,600,150,true)+'<div class="mu" style="font-size:12px">Dal '+x.h0.slice(5)+'/'+x.h0.slice(0,4)+' a oggi · minimo '+nf(mn,x.dec)+' · massimo '+nf(mx,x.dec)+' · fonte aggiornata al '+dm(x.d)+(x.old?'. <b>Dato non recente: la fonte non lo aggiorna da tempo.</b>':'')+'</div></div>'}
function riga(x){var u=x.u==='%'?'%':(x.u&&x.u!=='k'?' '+x.u:'');if(x.u==='$')u=' $';return '<div class="ecr '+x.st+'" data-i="'+esc(x.id)+'"><div class="ecn"><span class="ecdot"></span>'+esc(x.n)+'<small>'+dm(x.d)+(x.old?' · <span class="ecold">dato non recente</span>':'')+'</small></div><div class="ecv">'+nf(x.v,x.dec)+(x.u==='%'?'%':(x.u==='k'?' k':(x.u==='$'?' $':'')))+'<small>'+(x.old?'':etichetta(x)+(etichetta(x)?' · ':''))+chg(x)+'</small></div><div>'+spark(x.h,70,24)+'</div>'+(OPEN===x.id?det(x):'')+'</div>'}
function info(g){var i=D.ginfo[g];return i?'<em class="aii" data-info="'+esc(JSON.stringify({t:i[0],s:[['Cos\'è',i[1]],['Come si legge',i[2]]]}))+'">i</em>':''}
function render(){var it=D.items.filter(function(x){return (!AREA||x.a===AREA)&&(!CAT||x.c===CAT)}),n={ok:0,wa:0,ba:0};it.forEach(function(x){if(!x.old&&n[x.st]!=null)n[x.st]++});
var h='<div class="ecf"><button data-a="" class="'+(AREA===''?'on':'')+'">Tutto il mondo</button>'+D.aree.map(function(a){return '<button data-a="'+a[0]+'" class="'+(AREA===a[0]?'on':'')+'">'+a[1]+'</button>'}).join('')+'</div>';
h+='<div class="ecf"><button data-c="" class="'+(CAT===''?'on':'')+'">Tutti gli argomenti</button>'+D.cats.map(function(c){return '<button data-c="'+c[0]+'" class="'+(CAT===c[0]?'on':'')+'">'+c[1]+'</button>'}).join('')+'</div>';
h+='<div class="ecs"><span class="ok">'+n.ok+' in miglioramento</span><span class="wa">'+n.wa+' stabili</span><span class="ba">'+n.ba+' in peggioramento</span></div><p class="mu">«Miglioramento» e «peggioramento» confrontano il dato con un anno prima e dipendono dall\'indicatore (per la disoccupazione meno è meglio, per l\'inflazione conta la distanza dal 2%). Gli indicatori senza giudizio (tassi, cambi, prezzi) sono solo descritti. Tocca una riga per il grafico. Dati al '+dm(D.asof)+'.</p>';
if(!it.length)h+='<p class="mu">Nessun indicatore per questa combinazione.</p>';
D.cats.forEach(function(c){var ci=it.filter(function(x){return x.c===c[0]});if(!ci.length)return;h+='<h3 class="ecc">'+c[1]+'</h3>';var gs=[];ci.forEach(function(x){if(gs.indexOf(x.g)<0)gs.push(x.g)});
gs.forEach(function(g){var gi=ci.filter(function(x){return x.g===g}),t=(D.ginfo[g]||[g])[0];h+='<div class="ecg"><h4>'+esc(t)+info(g)+'</h4>'+gi.map(riga).join('')+'</div>'})});
var er=Object.keys(D.errori||{});if(er.length)h+='<p class="mu">Indicatori non scaricati nell\'ultimo giro ('+er.length+'): compaiono appena la fonte risponde.</p>';
W.innerHTML=h;W.querySelectorAll('[data-a]').forEach(function(b){b.onclick=function(){AREA=b.dataset.a;OPEN=null;render()}});W.querySelectorAll('[data-c]').forEach(function(b){b.onclick=function(){CAT=b.dataset.c;OPEN=null;render()}});
W.querySelectorAll('.ecr').forEach(function(r){r.onclick=function(e){if(e.target.closest('.aii'))return;var i=r.dataset.i;OPEN=OPEN===i?null:i;render()}})}
function go(j){D=j;if(!D||!D.items||!D.items.length){W.innerHTML='<p class="mu">Dati economici non ancora disponibili: si generano con il lavoro «Economia nel mondo».</p>';return}render()}
var emb=document.getElementById('armor-ec-data');if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/economia.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(go).catch(function(){W.innerHTML='<p class="mu">Dati economici non disponibili (serve la connessione, oppure il lavoro non è ancora girato).</p>'})}
})();</script>"""


def block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-ec-data'>{data_json}</script>" if data_json else ""
    return (f"{CSS}<h2 style='margin-top:26px'>L'economia nel mondo</h2><div class='explain'><p>Inflazione, lavoro, crescita, fiducia dei consumatori, casa e mutui, debito pubblico e privato, tassi dei titoli di stato, insolvenze, cambi e materie prime, "
            "per <b>America, Europa, Asia e Pacifico e Mondo</b>, da fonti ufficiali gratuite (FRED, BCE, Eurostat, Banca Mondiale, FMI, BRI). Ogni riga mostra la data del dato; se una fonte non lo aggiorna da troppo tempo lo segnala. "
            "È una fotografia descrittiva: <b>non prevede</b> cosa farà il mercato e non è una consulenza finanziaria.</p></div>" + emb + "<div class='ecw' data-ec='1'></div>" + JS)
