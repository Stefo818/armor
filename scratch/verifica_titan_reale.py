# -*- coding: utf-8 -*-
"""Rifa' la tabella del motore Titan con i dati MACRO VERI dell'archivio di Armor (data/series),
invece della cache di ricerca dove i dati FRED erano vuoti. Grandi fondi (CFTC, DIX, margin, AAII) dai file di ricerca.
Salva scratch/verifica_titan_reale.json"""
import os, sys, json, warnings
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from armor import titan, titan_dati

WORK = r"E:\Onedrive\Armor test\test_armor"
ns = {}
with open(os.path.join(WORK, "armor_titan_v40.py"), encoding="utf-8", errors="ignore") as f:
    exec(f.read(), ns)

S = titan_dati.raw_da_archivio()
print("serie caricate:", {k: len(v) for k, v in S.items() if len(v) < 50})
base = titan.build_features(titan.market_stage(S))
ext = ns["load_all_titan_data"]()                      # solo per le colonne dei grandi fondi e della struttura opzioni
for c in ["dix_raw", "gex_raw", "finra_margin", "aaii_bull_bear", "cftc_sp_inst", "vol_vix9d", "vol_vix6m", "vol_move", "cred_cur", "cred_baa"]:
    if c in ext:
        base[c] = ext[c].reindex(base.index)
df = titan.build_titan(base)

chiave = ["credit_level", "nfci", "icsa_surge", "ccsa_yoy", "permit_yoy", "indpro_6m", "cpi_yoy", "profits_yoy", "net_liq_ret63", "G_rec_v8", "ebp"]
print("\nCOLONNE MACRO (valori diversi: devono essere molti):")
print({c: int(df[c].nunique()) for c in chiave})
last = df.iloc[-1]
rep = {"oggi": {"data": str(df.index[-1].date()), "armor": round(float(last.armor_index), 1), "super": round(float(last.super_armor_index), 1),
                "radar": round(float(last.lost_decade_radar), 1), "pilastri": [round(float(last[f"p{i}_stress"]), 1) for i in range(1, 7)]}}
print("\nOGGI", rep["oggi"], "(ricerca: armor 44.0, super 46.4, radar 83.0)")

def auc(y, p):
    return float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan")
def bss(y, p, b):
    y, p, b = map(np.asarray, (y, p, b)); return float((1 - np.mean((y - p) ** 2) / (np.mean((y - b) ** 2) + 1e-12)) * 100)
rep["orizzonti"] = {}
for h, th, nome in titan.ORIZZONTI:
    r = titan.walk_forward(df, h, th)
    rec, a, b = r.loc["2019-01-01":], r.loc[:"2012-12-31"], r.loc["2013-01-01":]
    rep["orizzonti"][nome] = {
        "rischio_94_26": [round(auc(r.y_dd, r.p_dd_fhs), 3), round(auc(r.y_dd, r.p_dd_v40), 3)],
        "rischio_19_26": [round(auc(rec.y_dd, rec.p_dd_fhs), 3), round(auc(rec.y_dd, rec.p_dd_v40), 3)],
        "rischio_94_12": [round(auc(a.y_dd, a.p_dd_fhs), 3), round(auc(a.y_dd, a.p_dd_v40), 3)],
        "rischio_13_26": [round(auc(b.y_dd, b.p_dd_fhs), 3), round(auc(b.y_dd, b.p_dd_v40), 3)],
        "bss_19_26": [round(bss(rec.y_dd, rec.p_dd_fhs, rec.hist_base_dd), 1), round(bss(rec.y_dd, rec.p_dd_v40, rec.hist_base_dd), 1)],
        "direz_94_26": [round(auc(r.y_up, r.p_up_fhs), 3), round(auc(r.y_up, r.p_up_v40), 3)],
        "direz_13_26": [round(auc(b.y_up, b.p_up_fhs), 3), round(auc(b.y_up, b.p_up_v40), 3)]}
    print(nome, json.dumps(rep["orizzonti"][nome]))
rep["previsioni_oggi"] = titan.previsioni_oggi(df)
print("\nPREVISIONI OGGI", json.dumps(rep["previsioni_oggi"], ensure_ascii=False))
with open(os.path.join(ROOT, "scratch", "verifica_titan_reale.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1, ensure_ascii=False)
print("\nSalvato scratch\\verifica_titan_reale.json")
