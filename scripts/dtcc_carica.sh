#!/usr/bin/env bash
# Carica i file grezzi DTCC come pochi pacchetti .tar (un pacchetto = fino a 400 file) e annota in data/dtcc_archiviati.txt quelli caricati.
set -u
[ -d data_raw/dtcc ] || { echo "Nessun file grezzo"; exit 0; }
rm -f /tmp/lotto_*.txt
python3 scripts/dtcc_lotti.py data_raw/dtcc /tmp/lotto
ts=$(date -u +%Y%m%d_%H%M%S)
for l in /tmp/lotto_*.txt; do
  [ -e "$l" ] || exit 0
  n=$(basename "$l" .txt); n=${n#lotto_}
  pacco="/tmp/dtcc_raw_${ts}_${n}.tar"
  tar -C data_raw/dtcc -cf "$pacco" -T "$l"
  ok=0
  for t in 1 2 3 4; do
    if gh release upload dtcc-raw "$pacco" --clobber; then ok=1; break; fi
    echo "Caricamento non riuscito (tentativo $t): attendo"; sleep $((t*90))
  done
  if [ $ok = 1 ]; then cat "$l" >> data/dtcc_archiviati.txt; echo "Caricato $pacco ($(wc -l < "$l") file)"; else echo "ERRORE: $pacco non caricato"; fi
  rm -f "$pacco"
done
sort -u data/dtcc_archiviati.txt -o data/dtcc_archiviati.txt
