# Esito: ricerca libera di oltre 2000 tentativi sui segnali prima di correzioni e crolli endogeni — 25/11/2026

Protocollo: PROTOCOLLO_RICERCA_1000.md (commit dc257c3, prima dei calcoli). Script: scratch/ricerca_1000.py; dati: scratch/ricerca_1000_esito.json.
Bersaglio A: 81 correzioni endogene ≥ 5% (selezione 46 fino al 2007, verifica 35 dal 2008). Bersaglio B: 32 con calo ≥ 10% (17 + 15).
Tentativi: **2073 segnali singoli** (1968 dalla fabbrica generica su 48 serie e 9 finestre, 105 specifici sull'S&P 500) **+ 380 interazioni + 5 combinazioni + 4 modelli addestrati in avanti**.

## Risultati
- **Singoli:** nessuno supera la soglia «migliore fra N» (calcolata sulla selezione, 500 spostamenti). Migliori in selezione (A): rendimento e distanza dal minimo a 20 giorni delle medie aziende (cn_mid), distanza dalla media a 20 giorni dell'S&P, rendimento a 10 giorni: AUC 0,68-0,70; in verifica 0,63-0,67 (limite basso al 90% 0,56-0,61). Bersaglio B: volatilità dei settori (AUC selezione ~0,85, verifica 0,53-0,69).
- **Combinazioni (A):** media dei primi 10, 20, 50 segnali della selezione → AUC in verifica 0,63 (W2 0,72), limite basso al 90% 0,56-0,57, p = 0,002 (con correzione ×10: 0,02): **passano**. Bersaglio B: nessuna passa (p 0,12-0,18).
- **Modelli in avanti (A):** media di 20 segnali scelti anno per anno 0,668 (W2 0,74, p corretto 0,02) e alberi su 50 segnali 0,662 (W2 0,72, p corretto 0,02): **passano**; regressioni logistiche (0,56 e 0,60): non passano.
- Che cosa dicono i segnali: il picco è preceduto da un mercato «tirato», cioè salita rapida e molto sopra le medie/dai minimi recenti, soprattutto nelle medie aziende. Conferma lo studio precedente. L'idea «mercato fermo/ stallo sui massimi» non compare fra i migliori.

## Ma non basta per avvisare (metriche pratiche, verifica dal 2008, allarme = percentile espanso della combinazione)
| regola | crolli con allarme in W (10→2 sedute prima) | di cui 6→4 sedute prima | giorni normali in allarme | precisione (calo ≥5% nelle 20 sedute dopo) | frequenza di base | anticipo mediano |
|---|---|---|---|---|---|---|
| top10, ≥80° pct | 69% | 51% | 20% | 13% | 17% | 14,5 sedute |
| top10, ≥90° | 43% | 29% | 10% | 14% | 17% | 10 |
| top10, ≥95° | 20% | 14% | 5% | 14% | 17% | 11,5 |
Precisione sotto la frequenza di base: i giorni di allarme non sono seguiti da cali ≥ 5% più spesso dei giorni normali. Il segnale c'è in media nelle sedute prima del picco, ma suona molto più spesso di quanto si abbia una correzione: non è un allarme usabile così.

## Limiti e note
- 81/32 episodi correlati; il picco è noto col senno di poi; la soglia del caso è molto alta (0,996 per A) perché negli spostamenti casuali le finestre cadono spesso in periodi turbolenti, rispetto a una base solo calma: è una soglia severa e volutamente prudente. Per questo nessun singolo passa; le combinazioni sono state giudicate dal p-value di verifica.
- Nessuna correzione trovata per i crolli senza preavviso (calo da mercato calmo).
- Prossimo passo suggerito: invece di prevedere il picco, riconoscere l'inizio della discesa (1-5 sedute dopo p) quando restano molti punti di calo; oppure test in avanti dei segnali combinati.
