import pickle, json, numpy as np
OUT = {}
for G in ("P", "A"):
    D = pickle.load(open(f"/tmp/r200k_{G}.pkl", "rb")); names = np.array(D["names"], dtype=object)
    for tg in ("T1", "T2", "T3"):
        f = D["fin"][tg]; st = f["st"]; sel = st["sel"]; ver, old, lv, lo = st["ver"], st["old"], st["lver"], st["lold"]
        ok = np.isfinite(sel); order = np.argsort(-np.where(ok, sel, -1))[:100]
        passa = ok & (sel > f["soglia"]) & (sel >= 0.58)
        coer = ok & (sel >= 0.58) & (ver >= 0.56) & (lv >= 1.25)
        if G == "P": coer_all = coer & (old >= 0.55) & (lo >= 1.15)
        else: coer_all = coer
        r = dict(n=len(names), n_validi=int(ok.sum()), soglia=f["soglia"], miglior=f["best"], passano_selezione=int(passa.sum()), sel_ge_058=int((ok & (sel >= 0.58)).sum()), top100_ver=float(np.nanmean(ver[order])), top100_ver_med=float(np.nanmedian(ver[order])), top100_lift=float(np.nanmedian(lv[order])),
                 coerenti_sel_ver=int(coer.sum()), coerenti_tutti=int(coer_all.sum()))
        if G == "P":
            r["top100_old"] = float(np.nanmean(old[order])); r["top100_old_med"] = float(np.nanmedian(old[order])); r["top100_lift_old"] = float(np.nanmedian(lo[order]))
            r["old_ge_055_fra_top100"] = float(np.mean(old[order] >= 0.55))
            sc = np.where(np.isfinite(old) & np.isfinite(ver) & ok, np.minimum(old, ver), -1); b = np.argsort(-sc)[:5]
            r["migliori_coerenti"] = [dict(nome=str(names[j])[:110], sel=float(sel[j]), ver=float(ver[j]), old=float(old[j]), lv=float(lv[j]), lo=float(lo[j])) for j in b]
        else:
            b = np.argsort(-np.where(ok & np.isfinite(ver), np.minimum(sel, ver) , -1))[:5]
            r["migliori_coerenti"] = [dict(nome=str(names[j])[:110], sel=float(sel[j]), ver=float(ver[j]), lv=float(lv[j])) for j in b]
        OUT[f"{G}/{tg}"] = r; print(G, tg, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "migliori_coerenti"})
        for m in r["migliori_coerenti"][:3]: print("    ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()})
json.dump(OUT, open("scratch/r200k_sum.json", "w"), indent=1, default=float)
