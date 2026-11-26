# Protocollo: indice ibrido (vecchio Crollo + formula di Gemini), 26/11/2026

Pubblicato PRIMA di calcolare. Motivo: ricalcolando per l'app la tabella «dopo un allarme, quante volte e' arrivato il calo del 10% a 60 sedute» (crollo_precisione, solo crisi finanziarie dal 1990), la formula di Gemini (G1) distingue molto peggio del vecchio indice: giorni verdi 28,0%, gialli o peggio 24,8%, tutti 26,8% (vecchio: 7,9% contro 55,9%). G1 alza l'indice prima dei crolli recenti ma non separa i giorni rischiosi da quelli sicuri in generale.

## Candidato unico (fissato ora, nessun altro)
H = media semplice dei percentili (espansi dal 1990) del punteggio del vecchio Crollo (versione 2) e di G1; poi la stessa scala 1-100 dell'indice. Nessun peso ottimizzato.

## Due batterie, entrambe obbligatorie
A (prima/reazione, ESITO_GEMINI_UNIFICATO): sulla VERIFICA (5 picchi dal 2018) rispetto al vecchio indice: stacco prima-calmi +5 punti, AUC contro i calmi +0,03, protezione +0,10, falsi allarmi non oltre +1 punto percentuale; in selezione lo stacco non e' peggiore.
B (precisione): nella tabella per zona dal 1990: (1) tutti i giorni, giallo o peggio contro verde: almeno 2 volte; (2) mercato fra -2% e -7%, giallo o peggio contro verde: almeno 1,5 volte; (3) vicino ai massimi, giallo o peggio contro verde: almeno 1,3 volte.
Passa solo chi supera A e B. Con 5 picchi in verifica resta comunque «da confermare in avanti».
Esito scritto anche se negativo: ESITO_IBRIDO.md.
