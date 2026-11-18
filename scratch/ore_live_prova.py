# -*- coding: utf-8 -*-
"""Confronta il calcolo della pagina (ore_live.js) con quello di ore.py a parità di dati. PYTHONPATH=src python scratch/ore_live_prova.py"""
import json, subprocess
from datetime import datetime, timezone
from armor import ore
t0 = datetime(2026, 11, 18, 15, 40, tzinfo=timezone.utc)
for gap_case, aperto in ((0.0, True), (-0.006, False)):
    m = {"es_ora": 7300 * (1 + gap_case / ore.BETA_ES) if not aperto else 7300, "es_ancora": 7300.0, "fx_ora": 1.10, "fx_ancora": 1.10, "vix": 25.0, "es_24h": -0.002}
    v = {"prezzo": 165.0, "ora": t0, "aperto": aperto}
    r = ore.previsione(t0, v, m, [], sims=40000, seed=5)
    cfg = {"url": "x", "sede": "", "live": {"beta_es": ore.BETA_ES, "beta_fx": ore.BETA_FX, "s_calo": ore.SOGLIA_CALO, "s_calo_forte": ore.SOGLIA_CALO_FORTE, "s_forte": ore.SOGLIA_FORTE}, "vix": 25.0,
           "orizzonti": {k: {"qz": a["qz"], "eventi": False} for k, a in r["orizzonti"].items()}}
    js = open("src/armor/ore_live.js", encoding="utf-8").read()
    prog = "global.window={};global.document={getElementById:()=>null,addEventListener(){}};window.ORE_LIVE=" + json.dumps(cfg) + ";" + js + f";console.log(JSON.stringify(window.OreLive.stats(window.ORE_LIVE.orizzonti['{{K}}'].qz,{r['gap']})))"
    worst = {}
    for k, a in r["orizzonti"].items():
        out = json.loads(subprocess.run(["node", "-e", prog.replace("{K}", k)], capture_output=True, text=True).stdout)
        d = {"su": abs(out["su"] - a["p_su"]), "m15": abs(out["m15"] - a["p_meno15"]), "giu": abs(out["giu"] - a["giu_medio"]), "sale": abs(out["sale"] - a["su_medio"]), "p10": abs(out["p10"] - a["p10"]), "p90": abs(out["p90"] - a["p90"]), "p05": abs(out["p05"] - a["p05"])}
        for kk, vv in d.items(): worst[kk] = max(worst.get(kk, 0), vv)
    print("gap", round(r["gap"], 4), {k: round(v, 5) for k, v in worst.items()})
