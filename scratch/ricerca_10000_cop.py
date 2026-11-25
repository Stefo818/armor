import numpy as np, json
exec(open("scratch/ricerca_10000.py").read().split("# ---------------- segnali")[0])
allp = [p for p in range(20, N - 120) if Cn[p] == Cn[p - 20:p + 21].max() and Cn[p + 1:p + 121].min() / Cn[p] - 1 <= -0.05]
ext_pos = [posd(d) for d in ESTERNI]; mix_pos = [posd(d) for d in MISTE_MAX]; cls_ext = [posd(m) for m, _, nat, _ in CLASSIFICA if nat == "esterna" and pd.Timestamp(m) >= cal[0]]
esterno = lambda p: any(p - 5 <= e <= p + 60 for e in ext_pos) or any(abs(p - e) < 5 for e in cls_ext + mix_pos)
T = np.array([p for p in allp if not esterno(p) and yrs[p] >= 2008]); print("correzioni endogene dal 2008:", len(T))
out = {}
for tg, k in (("T1", "nb_30"), ("T1", "et_300"), ("T3", "nb_300"), ("T2", "nb_30")):
    p = np.load(f"/tmp/pred_{tg}.npy", allow_pickle=True).item()[k]; mk = MASK[tg]; rows_v = np.where(mk & (yrs >= 2008))[0]; cut = np.nanpercentile(p[rows_v], 90); al = p >= cut
    pre = np.mean([al[max(0, t - 10):t - 1].any() for t in T]); post = np.mean([al[t + 1:t + 6].any() for t in T]); anyw = np.mean([al[max(0, t - 5):t + 6].any() for t in T])
    rem = []
    for t in T:
        seg = np.where(al[t + 1:t + 6])[0]
        if len(seg):
            i = t + 1 + seg[0]; rem.append(float(Cn[i + 1:t + 121].min() / Cn[i] - 1) if i + 1 < t + 121 else np.nan)
    gd = float(al[(yrs >= 2008) & np.isfinite(p)].mean())
    out[f"{tg}_{k}"] = dict(allarme_prima_W=float(pre), allarme_dopo_1_5=float(post), allarme_intorno_pm5=float(anyw), calo_residuo_mediano_al_primo_allarme=(float(np.nanmedian(rem)) if rem else None), giorni_in_allarme=gd)
    print(tg, k, {a: (round(b, 2) if b is not None else None) for a, b in out[f"{tg}_{k}"].items()})
json.dump(out, open("scratch/ricerca_10000_cop.json", "w"), indent=1)
