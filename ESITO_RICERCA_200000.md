# Esito: ricerca estesa (oltre 240000 + oltre 600000 tentativi, dati dal 1928) — 25/11/2026 notte

Protocollo scritto e salvato prima dei calcoli: PROTOCOLLO_RICERCA_200000.md (commit 3155741). Il numero di tentativi era fissato: non ci si è fermati al primo successo. Scritto qualunque fosse l'esito.

## Quanti tentativi
- **Fase 1:** 240056 segnali (gruppo P, solo prezzi S&P 500 dal 1928 e dati macro lunghi: 144319 = 9328 singoli [5256 statistiche in varie finestre e ritardi, 3652 rapporti fra finestre, 420 macro, incluse curvatura del prezzo tipo LPPLS, volatilità EWMA/asimmetrica/HAR, salti, indice di coda] + 134991 accoppiamenti casuali; gruppo A, dati dal 1990: 95737 = 5752 singoli [anche assorbimento e turbolenza su 6 e 15 indici] + 89985 accoppiamenti), ciascuno su 3 bersagli.
- **Fase 2** (sui migliori scelti solo in selezione): 6 × 102000 = 612000 insiemi pesati e regole a soglia.
- **Modelli:** 99 per gruppo (11 algoritmi × 3 insiemi × 3 bersagli) = 198.
- **Totale ≈ 852000.**

## Periodi
VECCHIO 1932-1989 (mai usato prima: solo gruppo P), SELEZIONE 1992-2007, VERIFICA 2008-oggi. Solo crisi endogene.

## Risultati
1. **Soglia «migliore fra tanti» (caso):** con 144000 segnali la soglia sale a AUC 0,82 (T1), 0,87 (T2), 0,80 (T3). **Nessun segnale la supera** (miglior reale 0,805 / 0,860 / 0,781). Gruppo A: soglie 0,80 / 0,85 / 0,78, miglior reale 0,769 / 0,836 / 0,782 (un solo segnale passa per T3, di misura). Esito formale della fase 1: **nessun segnale singolo o coppia passa la regola del protocollo.**
2. **Coerenza fra epoche (descrittiva):** fra i 100 migliori in selezione, l'AUC mediano nel VECCHIO (1932-1989, mai visto) è 0,67 (T1), 0,69 (T2), 0,64 (T3) e in verifica 0,66 / 0,68 / 0,61; l'80-91% ha AUC ≥ 0,55 nel vecchio. Migliaia di segnali sono coerenti nelle tre epoche. Sono tutti della stessa famiglia: **volatilità recente alta / turbolenza / mercato già in discesa**.
3. **La sola volatilità a 60 sedute fa altrettanto:** AUC T1 0,674 (vecchio) / 0,757 (selezione) / 0,675 (verifica); T2 0,685 / 0,812 / 0,687; T3 0,646 / 0,697 / 0,661. I migliori insiemi pesati della fase 2 (AUC in verifica 0,60-0,71; nel vecchio 0,60-0,69) **non fanno meglio in modo stabile** della sola volatilità: 612000 tentativi di raffinamento non aggiungono informazione.
4. **Fase 2 (p-value con 20000 spostamenti, ×10):** P: confermati (AUC ≥ 0,60, lift ≥ 1,25, p < 0,05 su tutti i periodi non usati per la scelta) 2/10 per T1, 7/10 per T2, 1/10 per T3. A: 10/10 per T1 e T2, 0/10 per T3. Sono quasi tutte combinazioni di volatilità (S&P, Nasdaq, indici medi, credito/stress finanziario) e turbolenza.
5. **Modelli:** addestrati **solo sul 1932-1989** e provati su dati mai visti: T1 AUC 0,70 (verifica) e 0,73-0,77 (1992-2007), lift ~2,5; T2 fino a 0,77, lift 3,8 (ma 0,65 nel 1992-2007); T3 fino a 0,73. Passano 33/33 (T1), 24/33 (T2), 29/33 (T3). Walk-forward dal 2008 (gruppo A): T1 13/33, miglior 0,68; T2 10/33, miglior 0,71 (lift 3,3); T3 2/33, miglior 0,64.
6. **Domanda decisiva: anticipano il picco dopo un periodo calmo? No.**
   - Nei **giorni calmi** (volatilità sotto la mediana) l'AUC dei modelli migliori è 0,51-0,60 con p-value 0,2-0,5: nessuna capacità dimostrata.
   - Dei **97 picchi endogeni preceduti da calma** (64 nel 1932-1989, 19 nel 1992-2007, 14 dal 2008) la volatilità non ne copre nessuno (0%); i candidati migliori da 0% a 21% (pochi episodi).
   - Copertura dei picchi in generale (allarme da 10 sedute prima a 5 dopo): 9-34% dal 2008, spesso perché il mercato era già agitato.

## Conclusione onesta
Esiste un segnale **robusto e confermato in tre epoche (1932-89, 1992-2007, 2008-oggi)**: dopo giorni di volatilità alta, nelle 20-40 sedute successive un calo di almeno 5% (T1) o 8% (T2) è circa 2-3 volte più probabile del normale. Questo è un **riconoscimento della fase di discesa/turbolenza in corso**, non un preavviso: non vede il picco che nasce da un mercato calmo. Oltre 850000 tentativi, includendo letteratura (assorbimento, turbolenza, LPPLS, rialzi lunghi, valutazioni, spread, inflazione, volatilità condizionata, coda, salti), non hanno trovato nessun segnale che anticipi un picco dopo calma: i rischi di peak da calma restano invisibili con i dati pubblici usati. Più tentativi hanno alzato la soglia del caso e non hanno creato informazione; i raffinamenti non battono la volatilità semplice.

## Limiti dichiarati
Dati di sola chiusura prima del 1990 (Saturdays pre-1952 contati come sedute); classificazione esterno/endogeno prima del 1990 grossolana; picchi calmi pochi (97); verifica 2008+ semi-pulita (studi precedenti); la soglia del caso è molto alta per l'autocorrelazione dei segnali (pochi episodi indipendenti), quindi il «nessun segnale supera la soglia» non esclude effetti reali modesti. Allarme pratico: precisione 20-60% contro frequenza di base 12-15%, copertura bassa: non adatto come regola automatica.

File: scratch/r200k_*.py, scratch/r200k_*.json (sum, p2_P/A, mod_P/A, cop_P/A, calm).
