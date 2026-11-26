# Esito: indice ibrido e seconda lettura della formula di Gemini (26/11/2026)

Protocollo: PROTOCOLLO_IBRIDO.md (commit bebc18a, prima dei calcoli). Script: scratch/ibrido.py; dati: scratch/ibrido_esito.json.

## Scoperta mentre si applicava la scelta dell'utente
Per sostituire l'indice nell'app ho ricalcolato la tabella «dopo un allarme, quante volte e' arrivato il calo del 10% in 60 sedute» (sole crisi finanziarie dal 1990). La formula di Gemini (G1) NON separa i giorni rischiosi dagli altri:
| | vicino ai massimi: verde / giallo+ | fra -2% e -7%: verde / giallo+ | tutti i giorni: verde / giallo+ | rapporto giallo+/verde (tutti) |
|---|---|---|---|---|
| vecchio Crollo | 5,4% / 10,0% | 7,1% / 25,1% | 9,6% / 55,9% | 5,8 |
| G1 (Gemini) | 5,3% / 7,2% | 11,9% / 18,9% | 27,9% / 24,8% | **0,89 (rovesciato)** |
| H ibrido (50/50) | 6,1% / 8,3% | 12,9% / 20,0% | 25,0% / 36,0% | 1,44 |
Con G1 i giorni verdi hanno visto il calo del 10% piu' spesso di quelli gialli: i colori non dicono nulla di affidabile sul rischio generale.

## Verdetto sulle due batterie
- G1: batteria A (prima del picco/reazione) NO solo per lo stacco in selezione; batteria B (precisione) NO (tutti rovesciato).
- H: A NO (stacco in verifica -1,4, protezione 0,33), B NO (1,44 contro 2 richiesto).
- Nessun candidato passa. Il vecchio indice resta nell'app.

## Perche' due misure dicono cose opposte
G1 alza l'indice nei giorni prima dei crolli recenti (2018-2024) e reagisce presto, ma lo fa perche' il «terreno» (CAPE, tassi, credito) era alto in quegli anni; in altre epoche (es. dopo le crisi, con valutazioni basse mentre il mercato scende ancora) lo tiene basso nei giorni peggiori. E' un indice di livello strutturale, non un termometro del rischio a 60 sedute. Il vecchio indice fa l'opposto: bravo a separare i giorni rischiosi (anche perche' include tensione gia' in corso), debole prima dei picchi.

## Stato
Indice nell'app invariato. G1 resta nel registro in avanti (crollo_unificato). Le modifiche non pubblicate all'indice sono in git stash («indice Crollo versione 3 (Gemini) non adottata»).
