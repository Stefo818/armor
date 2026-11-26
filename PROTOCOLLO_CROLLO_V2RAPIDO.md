# Protocollo: formula di Gemini (V2b) combinata con l'allarme veloce (26/11/2026)
Scritto PRIMA di calcolare. Segue ESITO_CROLLO_V2MOLT.md (V2b: 3 criteri su 5; mancano AUC e protezione). Idea: l'allarme veloce (punteggio_rapido: VIX9D, VVIX, salto del VIX) dovrebbe recuperare la protezione.
Tutte le serie sono in percentile espanso dal 2001 (p_V2b, p_rapido, p_vecchio). Quattro candidati fissati ora:
K1 = media(p_V2b, p_rapido) · K2 = max(p_V2b, p_rapido) · K3 = media(p_V2b, p_vecchio) · K4 = media(p_V2b, p_vecchio, p_rapido).
Scelta in 2001-2014 con la media AUC(Ya) e AUC(Yb); verifica dal 2015; soglia del caso, criteri (i)-(v) e riferimento (vecchio indice) identici a PROTOCOLLO_CROLLO_V2MOLT.md, con la soglia del caso calcolata sul vincitore. Se il vincitore passa tutti: diventa il Crollo dell'app. Altrimenti il vecchio resta e il vincitore e' proposto come riga "in prova". Esito in ESITO_CROLLO_V2RAPIDO.md.
