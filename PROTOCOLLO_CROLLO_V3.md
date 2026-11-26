# Protocollo: Indice Crollo versione 3, appreso dai dati (26/11/2026)

Pubblicato PRIMA di calcolare. Obiettivo dell'utente: un Crollo che (1) sia alto nei giorni prima dei crolli e reagisca in pochi giorni, e (2) continui a separare i giorni rischiosi da quelli sicuri. Le prove precedenti hanno mostrato che le due cose si rompono a vicenda con pesi scelti a mano (vecchio Crollo: bravo in (2), debole in (1); formula di Gemini: il contrario). Qui i pesi li impara un modello su tutte e due le cose, con regole fisse e verifica fuori campione.

## Bersagli (etichette)
- Ya «calo imminente»: il minimo delle prossime 10 chiusure sta almeno il 4% sotto la chiusura di oggi.
- Yb «calo profondo»: il minimo delle prossime 60 chiusure sta almeno il 10% sotto il massimo a 252 giorni (come nella tabella dell'app).

## Dati in ingresso (percentili espansi dal 1990, ritardo 1 giorno dove la fonte e' lenta)
- F0: le 12 famiglie del vecchio indice (f1..f12).
- F1 = F0 + le tre parti della formula di Gemini (terreno, anticipo, innesco; cape_m e baa10y al posto dei dati mancanti).
- F2 = F1 + dati nuovi: VIX9D su VIX (dal 2011), VVIX (dal 2007), media dei contributi CISS (banche, monetario, azioni, obbligazioni, cambi), stress dei titoli di Stato europei (area euro pesata, livello e variazione a 20 giorni), rendimento a 20 giorni dei fattori Fama-French momentum, piccole-grandi (SMB) e care-economiche (HML), dispersione dei 49 settori (deviazione standard dei rendimenti a 20 giorni). Dati mancanti = 50 per la logistica, NaN per gli alberi.

## Candidati (dieci, fissati ora; nessuno aggiunto dopo)
Modelli: L = regressione logistica (C=0,5, ingressi 0-1); G = alberi potenziati (HistGradientBoosting, profondita' 3, 150 passi, tasso 0,05, minimo 200 per foglia, regolarizzazione L2 = 1). Bersaglio «a» = solo Ya; «ab» = media dei percentili delle probabilita' dei due modelli addestrati su Ya e su Yb.
C1 L-F1-a · C2 L-F1-ab · C3 G-F1-a · C4 G-F1-ab · C5 L-F2-a · C6 L-F2-ab · C7 G-F2-a · C8 G-F2-ab · C9 L-F0-ab (controllo: stesse famiglie del vecchio indice, solo riponderate) · C10 G-F0-ab.
Addestramento a finestra crescente: ogni 1 gennaio dal 2001 si riaddestra con i dati fino a 70 sedute prima (le etichette guardano avanti di 10 e 60 sedute: nessuna fuga di informazione). Tutte le previsioni sono quindi fuori campione. Probabilita' -> percentile espanso (da 2001, minimo 252) -> stessa scala 1-100 del Crollo (fasce 35/40/60/80).

## Scelta e verifica
Scelta: fra i dieci, il candidato con la media piu' alta fra AUC su Ya e AUC su Yb nel periodo 2001-2014. Verifica: dal 2015 (mai usato per scegliere). Il vecchio Crollo e la formula di Gemini sono ricalcolati sullo stesso periodo come riferimento.
Soglia del caso: massimo dell'AUC su Ya (2015+) fra i dieci candidati con le etichette spostate in circolo (300 spostamenti), 95° percentile.

## Regola di accettazione (tutte insieme, sul vincitore nel 2015+)
(i) AUC su Ya almeno +0,03 sul vecchio Crollo e sopra la soglia del caso;
(ii) tabella per zona (sole crisi finanziarie, come nell'app): giallo o peggio contro verde almeno 2 volte (tutti i giorni), 1,5 volte (fra -2% e -7%), 1,3 volte (vicino ai massimi);
(iii) stacco = media nelle 10 sedute fino al picco dei crolli 2018, 2018, 2022, 2023, 2024 meno la media nei giorni calmi: almeno +5 punti sul vecchio;
(iv) falsi allarmi nei giorni calmi (soglia = 95° percentile dei giorni calmi 2001-2014) non oltre +1 punto percentuale sul vecchio;
(v) protezione (quota di discesa ancora davanti al primo allarme, nessun allarme = 0) almeno +0,10 sul vecchio.
Se passa: diventa l'Indice Crollo dell'app (versione 3), con il vecchio ancora calcolato e registrato, e testi con i numeri nuovi. Se non passa: si dice quale criterio manca e si apre la mossa successiva, senza ritoccare i candidati.
Esito scritto in ESITO_CROLLO_V3.md anche se negativo.
