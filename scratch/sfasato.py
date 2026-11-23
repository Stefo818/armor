"""Ricerca sfasata. Segue PROTOCOLLO_SFASATO.md."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import indice_crollo as ic, store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX  # noqa: E402

ESCLUSE = {"sp500", "sp_open", "sp_high", "sp_low", "sp_vol", "spy", "vwce_de", "vwce_ls", "urth", "vt"}
crollo = ic.calcola_serie()
cal = crollo.index
sp = store.load("sp500").dropna().reindex(cal).ffill()
base = crollo["indice"]

# ---- perimetro finanziario: nessuna finestra di previsione contiene un evento esterno
fuori = pd.Series(False, index=cal)
for d in ESTERNI:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 63):min(len(cal), p + 61)] = True
for d in MISTE_MAX:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 5):min(len(cal), p + 181)] = True
dd = sp / sp.rolling(252, min_periods=120).max() - 1
fermo = (dd >= -0.05) & (sp.pct_change(5) > -0.02)
ok = (~fuori) & fermo

def mn(a, b):
    return pd.concat([sp.shift(-i) for i in range(a, b + 1)], axis=1).min(axis=1) / sp - 1
m15, m621, m2263, m121, m163 = mn(1, 5), mn(6, 21), mn(22, 63), mn(1, 21), mn(1, 63)
Y = {"E1 giorni": ((m15 <= -0.03)), "E2 settimane": ((m621 <= -0.05) & (m15 > -0.03)), "E3 mesi": ((m2263 <= -0.08) & (m121 > -0.05))}
valid = {"E1 giorni": m15.notna(), "E2 settimane": m621.notna(), "E3 mesi": m2263.notna()}
Y = {k: v.astype(float).where(valid[k]) for k, v in Y.items()}
sel = ok & (cal <= "2014-12-31"); ver = ok & (cal >= "2015-01-01")
anni = sorted(set(cal[ver].year))

def episodi(y, m):
    pos = np.where((y[m] == 1).to_numpy())[0]
    return 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 20).sum())
EP = {k: {"scelta": episodi(Y[k], sel & Y[k].notna()), "verifica": episodi(Y[k], ver & Y[k].notna())} for k in Y}
print("episodi indipendenti:", EP, "| giorni valutati scelta", int(sel.sum()), "verifica", int(ver.sum()))

# ---- candidati
LAG = {"g": 1, "s": 7, "m": 45, "t": 100}
def freq(s):
    d = np.median(np.diff(s.index.values).astype("timedelta64[D]").astype(float)) if len(s) > 3 else 99
    return "g" if d <= 3 else "s" if d <= 10 else "m" if d <= 45 else "t"
def pct(s):
    return s.expanding(min_periods=252).rank(pct=True)
feat = {}; saltate = []
for f in sorted(os.listdir("data/series")):
    sid = f[:-4]
    if sid in ESCLUSE:
        continue
    try:
        s = store.load(sid).dropna()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        if len(s) < 120:
            saltate.append((sid, "corta")); continue
        fr = freq(s)
        s2 = s.copy(); s2.index = s2.index + pd.Timedelta(days=LAG[fr])
        d = s2.reindex(s2.index.union(cal)).ffill().reindex(cal)
        for nome, x in (("T0", d), ("T5", d - d.shift(5)), ("T21", d - d.shift(21)), ("T63", d - d.shift(63))):
            p = pct(x.dropna()).reindex(cal)
            for_ = p.reindex(cal)
            feat[f"{sid}|{nome}"] = for_
    except Exception as e:  # noqa: BLE001
        saltate.append((sid, str(e)[:40]))
F = pd.DataFrame(feat)
cov_s = F[sel].notna().mean(); cov_v = F[ver].notna().mean()
buone = [c for c in F.columns if cov_s[c] >= 0.85 and cov_v[c] >= 0.85]
print(f"candidati: {F.shape[1]} totali, {len(buone)} con copertura >=85%; saltate {len(saltate)}")
F = F[buone]

def aucv(R, y):
    """AUC vettoriale: R = matrice di ranghi (righe x feature), y = 0/1."""
    n1 = y.sum(); n0 = len(y) - n1
    if n1 < 5 or n0 < 5:
        return np.full(R.shape[1], np.nan)
    return (R[y == 1].sum(axis=0) - n1 * (n1 + 1) / 2) / (n1 * n0)

def ranks(m, ev):
    mm = m & Y[ev].notna()
    X = F[mm].fillna(0.5)
    return mm, X.rank(axis=0).to_numpy()

out = {"episodi": EP, "n_candidati": len(buone), "segnali": {}, "combinato": {}}
rng = np.random.default_rng(31)
for ev in Y:
    ms, Rs = ranks(sel, ev); mv, Rv = ranks(ver, ev)
    ys = Y[ev][ms].to_numpy(); yv = Y[ev][mv].to_numpy()
    a_s = aucv(Rs, ys); a_v = aucv(Rv, yv)
    segno = np.where(a_s >= 0.5, 1, -1)
    a_s_o = np.where(segno == 1, a_s, 1 - a_s); a_v_o = np.where(segno == 1, a_v, 1 - a_v)
    # soglia del caso: bersagli di verifica mescolati per blocchi d'anno
    idx_anni = Y[ev][mv].index.year.to_numpy()
    best = []
    for _ in range(60):
        mappa = dict(zip(anni, rng.permutation(anni)))
        fin = np.empty(len(yv)); fin[:] = np.nan
        for a in anni:
            dst = np.where(idx_anni == a)[0]; src = yv[idx_anni == mappa[a]]
            if len(dst) and len(src):
                fin[dst] = np.resize(src, len(dst))
        fin = np.nan_to_num(fin)
        a_ = aucv(Rv, fin)
        a_o = np.where(segno == 1, a_, 1 - a_)
        best.append(np.nanmax(a_o))
    soglia = float(np.percentile(best, 95))
    ammesso = EP[ev]["verifica"] >= 6
    sig = [i for i in range(len(buone)) if ammesso and a_s_o[i] >= 0.58 and a_v_o[i] >= 0.58 and a_v_o[i] > soglia]
    top = sorted(range(len(buone)), key=lambda i: -np.nan_to_num(a_v_o[i]))[:8]
    print(f"\n{ev}: eventi scelta {int(ys.sum())} verifica {int(yv.sum())} | soglia del caso {soglia:.3f} | segnali {len(sig)}")
    for i in top:
        print(f"   {buone[i]:38s} segno {'+' if segno[i] == 1 else '-'} scelta {a_s_o[i]:.3f} verifica {a_v_o[i]:.3f}")
    out["segnali"][ev] = {"soglia_caso": round(soglia, 4), "n": len(sig),
                          "top8": [{"f": buone[i], "segno": int(segno[i]), "scelta": round(float(a_s_o[i]), 4), "verifica": round(float(a_v_o[i]), 4)} for i in top],
                          "segnali": [{"f": buone[i], "segno": int(segno[i]), "scelta": round(float(a_s_o[i]), 4), "verifica": round(float(a_v_o[i]), 4)} for i in sig]}
    # combinato
    usa = sorted(sig, key=lambda i: -a_s_o[i])[:10]
    rb = base.rank(pct=True)
    if usa:
        comb = pd.concat([(F.iloc[:, i] if segno[i] == 1 else 1 - F.iloc[:, i]) for i in usa], axis=1).mean(axis=1)
    else:
        comb = None
    from gara_indici import auc as _auc  # noqa: E402
    r = {}
    for per, mk in (("scelta", sel), ("verifica", ver)):
        mm = mk & Y[ev].notna() & base.notna()
        r[f"BASE_{per}"] = round(float(_auc(Y[ev][mm], base[mm])), 4)
        if comb is not None:
            m2 = mm & comb.notna()
            r[f"COMB_{per}"] = round(float(_auc(Y[ev][m2], comb[m2])), 4)
    out["combinato"][ev] = r
    print("   BASE vs combinato:", r)
ad = sum(1 for ev, r in out["combinato"].items() if "COMB_scelta" in r and r["COMB_scelta"] - r["BASE_scelta"] >= 0.03 and r["COMB_verifica"] - r["BASE_verifica"] >= 0.03)
out["adottabile"] = ad >= 2
print("\nADOTTABILE:", out["adottabile"], "(eventi con +0,03 in entrambi i periodi:", ad, "su 3)")
json.dump(out, open("scratch/sfasato.json", "w"), ensure_ascii=False, indent=1, default=str)
