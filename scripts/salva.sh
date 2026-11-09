#!/usr/bin/env bash
# Salva nel repository le cartelle indicate, SENZA mai fallire per conflitti:
# se il rebase non riesce, riparte dall'ultima versione online e ci rimette sopra i dati appena calcolati.
set -u
MSG="$1"; shift
git config user.name "armor-bot"
git config user.email "armor-bot@users.noreply.github.com"
for d in "$@"; do [ -e "$d" ] && git add "$d" 2>/dev/null; done   # un percorso mancante non blocca gli altri
git diff --cached --quiet && { echo "Niente da salvare"; exit 0; }
git commit -q -m "$MSG"
for i in 1 2 3 4 5; do
  git fetch -q origin main
  if git rebase -q -X theirs origin/main 2>/dev/null && git push -q origin HEAD:main; then echo "Salvato"; exit 0; fi
  git rebase --abort 2>/dev/null || true
  # via sicura: copia i nostri dati, riparti da origin/main, rimettili sopra
  T=$(mktemp -d)
  for d in "$@"; do [ -e "$d" ] && mkdir -p "$T/$(dirname "$d")" && cp -a "$d" "$T/$(dirname "$d")/"; done
  git reset -q --hard origin/main
  (cd "$T" && find . -type f) | while read -r f; do mkdir -p "$(dirname "$f")"; cp -a "$T/$f" "$f"; done
  for d in "$@"; do [ -e "$d" ] && git add "$d" 2>/dev/null; done
  git diff --cached --quiet && { echo "Niente da salvare"; exit 0; }
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then echo "Salvato (via sicura)"; exit 0; fi
  sleep $((i*5))
done
echo "ERRORE: salvataggio non riuscito"; exit 1
