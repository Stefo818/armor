# Esito: «territori di rischio endogeno» e modello a punteggio

Calcolato il **24/11/2026** con le regole di PROTOCOLLO_TERRITORI.md (+ addendum), una sola esecuzione (`scratch/territori.py`, risultati in `scratch/territori_esito.json`). 15 stati (13 + modello A + modello B) × 3 bersagli = 45 prove. Dati dal 1971 al 23/11/2026.

## Verdetto: NESSUNO stato è «dimostrato», NESSUNO è «indizio». Tutti «non supportato».
Soglia del «migliore fra 45 prove» sul 2015-2026: DR 0,89 (alta perché con pochi giorni accesi il caso produce differenze enormi); nessuno stato la raggiunge sul periodo di verifica.

## Cosa si è visto
- **Il credito (M3) funzionava fino al 2014, poi no.** 1990-2014: quando era caldo, un calo −8% in 63 sedute capitava nel 52% dei casi contro 12% (DR +0,40, IC90 0,25–0,51). Dal 2015: 10,5% contro 12% (DR −0,01). Lo stesso per lo stress europeo (M5): +0,14 prima, +0,04 dopo (IC include 0).
- **Prezzi da bolla (M1) e dollaro (M6)** hanno fatto il contrario: sotto zero fino al 2014 (le bolle salgono a lungo prima di rompersi), positivi dal 2015 (M1 +0,13, IC90 0,01–0,30; M6 +0,23, IC90 0,00–0,50). Segno instabile → non fidabile.
- **Leva (M2), concentrazione (M0), «obbligazioni drenano» (M4) e le combinazioni BOLLA, LEVA, DRENAGGIO**: nessuna relazione stabile; spesso il segno è opposto a quello atteso, specie dal 2015.
- **Convergenza (K ≥ 2, 3, 4)**: DR positivo per B1 in entrambi i periodi ma con intervalli che includono 0; K ≥ 3 e K ≥ 4 non migliorano; per B3 il dopo-2015 è negativo. Un solo risultato (K4 dal 2015, 75 giorni) ha DR +0,25 ma solo 1 episodio e nel 1990-2014 K4 era sotto zero.
- **Modello A (media dei meccanismi)**: AUC 0,59 sul 2015-2026 (IC90 0,42–0,72, soglia del caso 0,71). Nel 1990-2014 era sotto 0,5. Non distinguibile dal caso.
- **Modello B (logistica adattata sul 1990-2014)**: AUC 0,83–0,88 sul periodo di addestramento, **0,40–0,47 sul 2015-2026, cioè peggio del caso**. Classico caso di adattamento al passato che non regge.
- **Cattura dei picchi** (13 picchi endogeni 1987-2024): K ≥ 2 li segnala 11 su 13, ma K ≥ 2 è acceso il 39% dei giorni; K ≥ 3: 8 su 13 (13% dei giorni); modello A: 8 su 13 (11% dei giorni). Segnalare molti picchi suonando spesso non è prevedere: la probabilità di calo nei giorni «accesi» non è significativamente più alta.
- Senza il 1973-75 le conclusioni non cambiano.

## Cosa significa per le cause della tabella
I crolli di leva nascosta in derivati (Volmageddon, Archegos, fondi UK, carry trade yen) e di liquidità lampo (Flash Crash) **non lasciano tracce nelle serie pubbliche giornaliere che abbiamo dal 1971**: esplodono dentro pochi giorni da posizioni che nessun indice pubblico misura. Quelli di credito e banche (1990, 2007-08, 2011) avevano segnali, ma il segnale del credito che ha funzionato prima del 2015 non ha funzionato dopo (le banche centrali intervengono prima, il credito privato è passato fuori dalle banche). Le bolle (1990 Giappone, 2000 dot-com) salgono anni prima di rompersi: i prezzi alti non datano il crollo.

## Oggi (23/11/2026)
Meccanismi caldi: **prezzi da bolla (0,90), obbligazioni che drenano (0,87), dollaro forte (0,81)**; freddi: concentrazione 0,44 (il livello alto di Sovraccarico resta una storia di attesa), leva 0,68, credito 0,56, Europa 0,51. Convergenza K = 3; punteggio A 0,93 (decile alto); probabilità del modello B 6,7% (bassa). Per le regole sopra, **questa è un'informazione sul contesto, non un avviso di crollo provato**.

## Cosa entra nell'app (deciso dal protocollo)
- Nessun avviso rosso/giallo «crollo probabile».
- Una striscia informativa «Le 4 cause dei crolli di pancia: cosa è acceso oggi» con i 7 meccanismi caldi/freddi e frase onesta («non è dimostrato che l'accensione preveda i crolli»), peso zero.
- Registro giornaliero `data/territori_registro.csv` per la verifica in avanti. Il verdetto in avanti si scrive in un nuovo protocollo (sotto), non adesso.

## Verifica in avanti (da oggi, regole fissate ora)
Finestra 24/11/2026 → 24/05/2027. Si guarda per ogni meccanismo caldo e per K ≥ 3 e per il modello A se la frequenza dei cali (−8% in 63 sedute) nei giorni accesi supera quella nei giorni spenti. Servono almeno 6 episodi indipendenti: nella finestra è improbabile, quindi l'esito probabile è «insufficiente». Gli avvisi restano informativi finché non c'è una prova.

## Addendum: modello «per tipo di crisi» (24/11/2026, scratch/tipi.py)
Metodo: per ogni tipo, frazione di sedute con il meccanismo compatibile acceso nelle 126 prima dei picchi del tipo, contro 500 estrazioni di giorni casuali lontani dai picchi e dagli shock esterni.
- **CREDITO (M3 + M5): «riconosce».** Acceso in media il 34% delle sedute prima dei suoi 4 picchi (1990, 2007, 2011, 2023), contro 11% a caso (95° percentile 24%) e 10% prima dei picchi degli altri tipi. 4 catturati su 4.
- **BOLLA (M1 + M0): «indizio».** 73% contro 20% (95° percentile 51%), 2 su 2. Solo 2 episodi: non una prova.
- **LEVA (M2 + M0): non supportato.** 32% contro 15% a caso, ma sotto il 95° percentile (36%): coerente col fatto che la leva nascosta nei derivati non lascia tracce pubbliche.
- **VALUTE (M6): non supportato** (un solo caso, 1997, 39% contro soglia 50%).
Cautele: pochi episodi per tipo (1-4); tipi assegnati dopo aver conosciuto gli esiti (con regole scritte prima del calcolo, ma non e' una vera verifica fuori campione); la prova dice che il meccanismo era acceso *prima* dei picchi, non quanto spesso e' acceso senza crolli (parzialmente coperto dal confronto con i giorni casuali), e il test sulle probabilita' di calo (sopra) mostrava che il credito dal 2015 non e' piu' predittivo.
Oggi: BOLLA acceso (62% delle ultime 126 sedute, contro 20% a caso: sopra il 95° percentile), CREDITO spento (0%), LEVA 60% (ma non supportato), VALUTE 3%. Nell'app: una riga sul clima piu' simile a un tipo solo per i tipi «riconosce» o «indizio» e sopra il 30%.
