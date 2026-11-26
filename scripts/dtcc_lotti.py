"""Divide i file grezzi DTCC in lotti (massimo 1,4 GB e 400 file ciascuno: il limite di GitHub e' 2 GB per file)."""
import os
import sys

cartella, uscita = sys.argv[1], sys.argv[2]
files = sorted(f for f in os.listdir(cartella) if f.endswith(".zip"))
lotti, cur, peso = [], [], 0
for f in files:
    s = os.path.getsize(os.path.join(cartella, f))
    if cur and (peso + s > 1_400_000_000 or len(cur) >= 400):
        lotti.append(cur); cur, peso = [], 0
    cur.append(f); peso += s
if cur:
    lotti.append(cur)
for i, l in enumerate(lotti):
    open(f"{uscita}_{i:03d}.txt", "w").write("\n".join(l) + "\n")
print(f"{len(files)} file in {len(lotti)} lotti")
