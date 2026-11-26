# Report: l'indice Crollo — come funziona, cosa abbiamo provato, cosa promette (26/11/2026)

## 1. In una pagina
- L'indice Crollo (da 1 a 100) dice **quanto il mercato è teso adesso**: paura, prezzo sotto le sue medie, costo del credito, fuga dai settori rischiosi, scosse sui tassi. Oggi: 84 (mercato in panico).
- **Cosa sa fare:** riconoscere in fretta una discesa che è già iniziata, e distinguere i giorni "tesi" da quelli tranquilli. Nei crolli lenti (1997-2000, 2007-2009, 2022) sale molto prima del fondo.
- **Cosa non sa fare:** vedere il massimo in anticipo. Nei 5 giorni prima del picco dei 12 crolli nati dentro la finanza vale in media **24,2**, contro **22,5** dei giorni calmi. In 5 crolli su 12 resta sotto 10 fino al picco. Hai ragione a dire che, a pochi giorni dal picco, l'indice non sta prevedendo il crollo.
- **Non è un difetto di taratura, è il limite dei dati:** in oltre un milione di tentativi (prezzi, volatilità, credito, economia, 23 mercati, dati nuovi) nessuna misura vede in anticipo i massimi preceduti da mercato calmo. Chi promette di farlo con questi dati sta adattando il passato.
- **Cosa conviene fare:** puntare sulla **reazione rapida** (accorgersi in pochi giorni dall'inizio del crollo). Il candidato più promettente è registrato per la prova in avanti (parte 6).

## 2. Come viene calcolato
1. Si prendono sei gruppi di misure ("famiglie") e ogni misura si trasforma in **percentile sulla sua storia**: 90 vuol dire "più alta del 90% dei giorni passati". Così misure diverse si possono sommare.
2. Pesi fissati prima di guardare i risultati (versione 2, 25/11/2026):
   | famiglia | peso | cosa guarda |
   |---|---|---|
   | paura del mercato | 30% | livello del VIX |
   | paura a breve più alta che a tre mesi | 30% | VIX diviso VIX a 3 mesi |
   | tendenza | 25% | prezzo sotto le medie a 50 e 200 giorni, giorni sotto la media lunga |
   | costo del debito delle aziende | 15% | differenziale Baa e sua variazione a 20 giorni |
   | fuga dai settori rischiosi | 15% | semiconduttori, piccole aziende, banche, rame/oro rispetto alle loro medie |
   | scosse sui tassi americani | 15% | variazioni a 5 e 20 giorni del 10 anni e curva rovesciata |
   (I pesi si rinormalizzano a 100.) Calcolate ma a peso zero: salto del VIX, costo delle assicurazioni sul ribasso (SKEW e put), volatilità, nervosismo obbligazionario, distanza dal massimo (tolta su richiesta) e l'Indice Armor.
3. Il punteggio pesato si trasforma ancora in percentile (storia dal 1990) e poi nella scala 1-100: fino a 35 verde, 36-40 grigio, 41-60 giallo, 61-80 rosso, 81-100 viola. Le fasce sono tarate sul numero di giorni che cadono in ognuna.
4. Dati con 1 giorno di ritardo dove la fonte è lenta (tassi, credito).

## 3. Cosa dicono le prove sull'indice
- **Verifica dal 2015, sole crisi finanziarie (ESITO_INDICE_CROLLO):** AUC 0,75 (0,5 = caso), ma la fascia viola ha troppi pochi giorni per essere valutata: etichetta **«Non coerente»** (R2 non superata). Quando il mercato è già tra il 2% e il 7% sotto il massimo, una lettura gialla o rossa vale 23-28% di rischio di calo del 10%, contro il 6,5% di una lettura verde: **è qui l'unico uso solido**. Vicino ai massimi distingue poco (11,7% contro 5,5%).
- **Agire sul numero farebbe perdere:** uscendo su rosso o viola dal 2015 si ottiene +142% contro +236% restando investiti, con la stessa perdita massima. Le letture alte arrivano durante il panico, vicino ai minimi.
- **Crolli lenti:** l'indice supera 60 per la prima volta 53-60 sedute prima del picco in 1997, 1998, 2000, 2001, 2002, 2008 e 2022. Valore 2 sedute prima: ≥85 in sei di questi crolli.
- **Crolli partiti da mercato calmo:** 2010, 2011, 2018 (due volte), 2024 (e, in altre prove, 2015 e 2020): l'indice è a 2-9 fino al picco. Nessuno strumento li vede.
- **Il confronto sbagliato:** la scheda mostrava "prima di un crollo" contro la media storica (36,1). Quella media comprende le discese già in corso, dove l'indice è altissimo per definizione. Il confronto giusto è con i giorni calmi (22,5). Ora la scheda dice così e usa 10 sedute, con la media delle ultime 5.

## 4. Tutti i tentativi di migliorarlo (e come sono andati)
| prova | cosa | esito |
|---|---|---|
| Indice crollo, 5 modelli (media, composito a pesi, regola a due chiavi, regressione, alberi) | scelta 1990-2014, verifica dal 2015 | vince il composito M2 (AUC 0,7545), ma l'Indice Armor di riferimento fa uguale: «Non coerente» |
| Cosa precede un crollo ≥8% in 5 sedute (102 ipotesi) | 13 crolli dal 1990, selezione/verifica | nessuna supera il caso (soglia 0,868). Gruppo coerente: volatilità che si allarga (VIX sopra la media a 60 giorni: 0,725). Mercato fermo sui massimi: il contrario (0,28-0,50) |
| Indice crollo 2 (16 punteggi) | 4 varianti (senza distanza dal massimo, con CAPE) + 6 idee dalla letteratura | nessuno batte l'attuale: guadagni +0,006/+0,009, dentro il rumore. Resta l'indice attuale. Il CAPE non aggiunge anticipo a 5 giorni |
| Crollo × Stato | prodotto, minimo, doppia soglia | non migliora il Crollo da solo; registrati X2 e X3 per la prova in avanti |
| Ricerca 200.000 (≈852.000 tentativi) | prezzi dal 1928, macro, volatilità, assorbimento, 11 algoritmi | la volatilità recente è un riconoscitore robusto ma debole della discesa in corso (AUC 0,67-0,69); 0 picchi su 97 dopo mercati calmi coperti |
| Multimercato (23 mercati, 160.043 tentativi) | stessi test su borse di tutto il mondo | AUC 0,57-0,60 solo sui mercati mai usati per scegliere; nulla vicino ai massimi |
| Crollo prima (26/11, con dati nuovi) | + volatilità, ampiezza, titoli di Stato europei, contributi CISS | nessun candidato passa la verifica; i dati europei migliorano molto fino al 2011 e crollano dopo (illusione del passato) |
| Reazione rapida (26/11) | indice più veloce, con VIX9D e VVIX nuovi | il candidato 2 reagisce in 5 sedute con il 74% della discesa ancora davanti, ma con 9 falsi allarmi su 100 giorni calmi (limite 6): non adottato, **registrato in avanti** |

## 5. I tentativi più promettenti
1. **Volatilità che si allarga** (VIX sopra la sua media a 60 giorni, ampiezza giornaliera, volatilità a 10 su 60 giorni): AUC 0,70-0,725 in entrambe le metà, segnale in 10 crolli su 13, anticipo mediano 11-17 sedute. È l'unica famiglia coerente in tutte le prove.
2. **Reazione rapida con VIX9D e VVIX (dati nuovi):** allarme dopo mediamente 5 sedute dal picco, con il 74% della discesa ancora da fare; il costo è un falso allarme ogni 11 giorni calmi.
3. **Modelli addestrati solo sul periodo 1932-1989:** raggiungono 0,70-0,77 sui dati nuovi: la struttura è stabile nei decenni.
4. **Indizi per la prova in avanti (non adottati):** stretta di liquidità e tassi (N6) e terreno fragile × innesco (N5) su orizzonti di settimane (AUC 0,70-0,84 su soli 8 e 3 episodi); X2 e X3 (Crollo × Stato) a 21 giorni.

## 6. Cosa succede adesso
- **Fatto:** la scheda dice la verità (confronto coi mercati calmi, 10 sedute, ultime 5); da oggi il registro giornaliero (data/indizi_registro.csv) scrive anche il candidato «reazione rapida» e il suo allarme.
- **Da fare con i dati nuovi quando saranno abbastanza:** rifare la prova fra 6 mesi con VIX9D, VVIX, SKEW, DTCC (CDS veri) e fattori Fama-French dal 1926; la cosa più utile sarà un crollo vero osservato in avanti dal candidato rapido.
- **Cosa non faremo:** ritoccare pesi guardando i 12 crolli finché la media «prima» non sale: l'indice salirebbe anche nei giorni calmi e perderebbe valore.

## 7. Limiti
Dodici crolli nati dentro la finanza e solo cinque dopo il 2011: ogni numero ha un margine ampio e un singolo episodio pesa molto. Le soglie dell'indice sono calibrate sul passato. Non è un consiglio di investimento.
