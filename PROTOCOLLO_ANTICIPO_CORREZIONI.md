# Protocollo: cosa si rompe prima di una correzione (da circa 5% fino a oltre 30%) — 25/11/2026 sera

Scritto prima di calcolare risultati. Sostituisce nel metodo il protocollo sui soli crolli ≥ 8% in 5 sedute (ESITO_ANTICIPO_CROLLI.md), che resta come caso particolare.

## Richiesta dell'utente
Il range è più ampio: correzioni di qualunque durata (anche molte sedute), da 5-6% a oltre 20-30%. Trovare cosa si rompe prima e cosa anticipa di almeno un paio di sedute, meglio di 5 o più.

## Definizione di correzione e giorno zero
S&P 500, chiusure giornaliere dal 1990. **Picco** = seduta p la cui chiusura è la massima in [p−20, p+20]. È una **correzione** se nelle 120 sedute dopo la chiusura scende almeno del 5% sotto il picco: profondità D = minimo(chiusure p+1…p+120) / chiusura(p) − 1 ≤ −5%. Giorno zero = p. Ogni correzione pesa uno. Sono 96 (verificato solo il conteggio, non i segnali): 53 moderate (D tra −5% e −10%), 32 forti (−10% e −20%), 11 gravi (oltre −20%, comprese 2000-02, 2008-09, 2020, 2022). Il picco stesso non si conosce in tempo reale: la domanda è se prima di p qualcosa è già diverso dal normale.
Finestre di avviso: W = p−10…p−2 (almeno 2 sedute prima del picco); sotto-finestre W2 = p−3…p−2, W5 = p−6…p−4, W10 = p−10…p−7. Finestra secondaria «inizio discesa» E = p+1…p+5 (info, senza ruolo nella scelta): serve a vedere cosa si rompe appena la discesa parte, quando c'è ancora tutto il calo davanti.
Giorni di base (normali): tutte le sedute dal 1992 non comprese in [p−40, p+10] di alcuna correzione.

## Ipotesi
Le 102 dello studio precedente (stessi dettagli e direzioni: struttura dei prezzi, paura e opzioni, credito e tassi, altri mercati, settori, calendario) più 18 nuove, ritagliate sulle correzioni lente (direzione fissata ora):
N01 giorni nelle ultime 40 sedute con chiusura entro 0,5% dal massimo a 40 giorni (+, «si ferma più volte sotto lo stesso livello»); N02 ampiezza 40 giorni (massimo−minimo)/chiusura (−, mercato compresso); N03 distanza dal massimo a 20 sedute, vicino (+); N04 rendimento a 120 sedute (+); N05 quota dei 9 settori sotto la media a 200 (+, dal 1999); N06 «S&P entro 2% dal massimo a 252» per la quota di settori sotto la media a 50 (+, divergenza); N07 volume dei giorni di rialzo 20/60 (−, rialzi con poco volume); N08 VIX/minimo a 20 giorni (+); N09 variazione VIX a 20 giorni (+); N10 Baa-10 anni var. 60 giorni (+); N11 curva 10 anni-3 mesi var. 60 giorni (−); N12 tasso a 10 anni var. 60 giorni (+); N13 dollaro var. 60 giorni (+); N14 volatilità 60 / 252 (+); N15 giorni sopra +1% nelle ultime 20 (+, sali e scendi); N16 distanza dalla media a 20 (+); N17 differenza fra rendimento 20 giorni di Nasdaq 100 e dell'S&P (−, la tecnologia non traina); N18 rendimento a 60 sedute (S&P) meno rendimento a 60 sedute delle piccole aziende (+, solo i grandi salgono).
Totale N ≈ 120 (esatto dichiarato dallo script). Riferimenti non contati: Indice Crollo, Armor, Minimi.

## Misura e convalida (come prima, adattata)
AUC pesata per episodio in W contro i giorni di base, su percentili espansi (solo passato, minimo 500 giorni). **Selezione** = correzioni con picco fino al 2007 incluso; **verifica** = dal 2008. Soglia contro il caso: 300 spostamenti circolari casuali (≥ 250 sedute) di tutti i picchi; per ognuno si calcola il massimo fra tutte le ipotesi dell'AUC di selezione; soglia = 95° percentile di questi massimi.
Passa la selezione: AUC selezione ≥ 0,60 **e** sopra la soglia caso. Passa la verifica: AUC verifica ≥ 0,56, limite basso dell'intervallo al 90% (ricampionamento degli episodi) > 0,5, AUC in W2 > 0,5. Si riportano anche: AUC per fascia di profondità (moderate / forti / gravi), anticipo tipico (sedute prima di p in cui la misura entra per la prima volta nel 10% più a rischio entro 20 sedute), quota di episodi con segnale, AUC in E.
Parte 1: Indice Crollo, Armor, Minimi nelle stesse finestre (AUC, valore a p−2/−5/−10 per fascia, sedute prima in cui superano 50 e 60).
Se nessuna ipotesi passa si dichiara. Nessuna combinazione fra ipotesi viene provata in verifica; se più ipotesi passano si propone un test in avanti prima di cambiare gli indici.

## Limiti dichiarati
Il picco è definito col senno di poi; episodi vicini (correzioni a catena) non sono indipendenti; le 120 ipotesi alzano la soglia del caso; misure dal 2006 escluse; è una prova di correlazione nel passato.

## Aggiunta (25/11/2026, ore 21:45, prima dei calcoli): solo crisi endogene
Su richiesta dell'utente si studiano **solo le correzioni nate dentro il sistema finanziario**. Si usa la regola già usata in tutte le ricerche del progetto (scratch/classifica_40anni.py): un picco p è **escluso** se una data di shock esterno E della lista ESTERNI (Kuwait 1990, 11 settembre, Iraq 2003, Covid 2020, Ucraina 2022, dazi e Iran 2018-2019, 2025, 2026, ecc.) cade fra 5 sedute prima e 60 sedute dopo p, oppure se p dista meno di 5 sedute da un picco della tabella CLASSIFICA etichettato «esterna», oppure se p dista meno di 5 sedute da una data MISTE_MAX (2015-05-21, 2018-09-20; cause miste: escluse per prudenza). Restano le correzioni endogene (finanziarie). Le finestre ESTERNI e MISTE_MAX (−5/+60 sedute) sono escluse anche dai giorni di base. Tutto il resto (ipotesi, finestre, divisione selezione/verifica 2007/2008, soglia del caso con gli spostamenti applicati ai soli picchi endogeni, criteri) resta invariato. Il numero di episodi endogeni e per fascia di profondità si riporta nell'esito.
