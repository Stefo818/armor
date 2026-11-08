"""Crea scratch/repo.zip (tutto il progetto, senza .git, site, scratch, patch) oppure, con l'argomento 'serie', scratch/series.zip (solo data/series).
Uso dal PC (device_bash): cd $HOME/mnt/Armor && python3 scripts/copia_cloud.py [serie]"""
import os
import sys
import zipfile

ESCLUSI = {".git", "site", "__pycache__", "scratch", "node_modules", ".venv"}
solo_serie = len(sys.argv) > 1 and sys.argv[1] == "serie"
radice = os.path.join("data", "series") if solo_serie else "."
nome = os.path.join("scratch", "series.zip" if solo_serie else "repo.zip")
os.makedirs("scratch", exist_ok=True)
with zipfile.ZipFile(nome, "w", zipfile.ZIP_DEFLATED) as z:
    for r, d, fs in os.walk(radice):
        d[:] = [x for x in d if x not in ESCLUSI]
        for f in fs:
            if not f.startswith("patch"):
                z.write(os.path.join(r, f))
    print(nome, len(z.namelist()), "file")
