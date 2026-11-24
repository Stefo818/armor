"""Ricerca «Concentrazione del mercato». Segue PROTOCOLLO_CONCENTRAZIONE.md + Emendamento 1 (nessuna regola cambiata dopo la pubblicazione)."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scratch")
from armor import accumulo, store  # noqa: E402
from armor import indice_crollo as ic  # noqa: E402
from classifica_40anni import CLASSIFICA, ESTERNI, MISTE_MAX, PRIMA, finestra  # noqa: E402
from elementi_esterni import lag, pct_esp  # noqa: E402

SIMBOLI = {"IXIC": "^IXIC", "NYA": "^NYA", "NDX": "^NDX", "GSPC": "^GSPC", "OEX": "^OEX", "MID": "^MID", "XLK": "XLK", "SPY": "SPY", "RSP": "RSP", "SPXEW": "^SPXEW"}
PROXY = {"TEC1": ("IXIC", "NYA"), "TEC2": ("NDX", "GSPC"), "TEC3": ("XLK", "SPY"), "GRA1": ("OEX", "GSPC"), "GRA2": ("GSPC", "MID"), "GRA3": ("SPY", "RSP"), "GRA4": ("GSPC", "SPXEW")}
PRE86 = [("1976-09-21", "finanziaria"), ("1980-11-28", "finanziaria"), ("1983-10-10", "finanziaria"), ("1973-01-11", "mista")]
ORIZ = [("21g -5%", 21, 0.05), ("63g -8%", 63, 0.08), ("63g -12%", 63, 0.12)]
SOGLIA = 0.80
rng = np.random.default_rng(7)


def scarica() -> dict:
    out = {}
    for k, s in SIMBOLI.items():
        d = accumulo.chart(s, "1d", "1960-01-01")
        out[k] = d["c"][d["c"] > 0]
        print(f"  {k:6s} dal {out[k].index[0].date()} ({len(out[k])})", flush=True)
    return out


def zroll(x: pd.Series, fin=1260, minimo=750) -> pd.Series:
    return (x - x.rolling(fin, min_periods=minimo).mean()) / x.rolling(fin, min_periods=minimo).std()


def proxy_misure(P: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    liv, acc, zz = {}, {}, {}
    for nome, (a, b) in PROXY.items():
        r = np.log(P[a] / P[b].reindex(P[a].index)).dropna()
        z = zroll(r)
        d63 = r - r.shift(63)
        a1 = zroll(d63)
        a2 = zroll(d63 - d63.shift(63))
        liv[nome] = pct_esp(z.dropna())
        acc[nome] = (pct_esp(a1.dropna()).reindex(a2.dropna().index.union(a1.dropna().index)) + pct_esp(a2.dropna()).reindex(a2.dropna().index.union(a1.dropna().index))) / 2
        zz[nome] = z
    return pd.DataFrame(liv), pd.DataFrame(acc), pd.DataFrame(zz)


def inneschi(cal: pd.DatetimeIndex) -> pd.DataFrame:
    L = lambda k: store.load(k).dropna()
    r1 = pct_esp(lag(L("dgs10"), 1).diff(63).dropna())
    r2 = pct_esp(lag(L("fedfunds"), 1).diff(126).dropna())
    spread_m = (L("baa_lungo") - L("gs10_m").reindex(L("baa_lungo").index)).dropna()
    c_m = pct_esp(lag(spread_m, 35).diff(3).dropna())
    c_d = pct_esp(lag(L("baa10y"), 1).diff(63).dropna())
    c1 = pd.concat([c_m[c_m.index < "1986-06-01"], c_d[c_d.index >= "1986-06-01"]])
    f1 = pct_esp(lag(L("nfci"), 5).diff(13).dropna())
    df = pd.DataFrame({k: s.reindex(cal, method="ffill") for k, s in {"R1": r1, "R2": r2, "C1": c1, "F1": f1}.items()})
    vera = (df >= SOGLIA)
    disp = df.notna()
    rt = (vera.sum(axis=1) >= 2) & (disp.sum(axis=1) >= 2)
    return pd.DataFrame({**{k: vera[k] & disp[k] for k in df}, "RT": rt, "n_disp": disp.sum(axis=1)})


def bersagli(sp: pd.Series) -> pd.DataFrame:
    out = {}
    for nome, h, th in ORIZ:
        fwd = pd.concat([sp.shift(-i) for i in range(1, h + 1)], axis=1).min(axis=1)
        y = ((fwd / sp - 1) <= -th).astype(float)
        y[sp.shift(-h).isna()] = np.nan
        out[nome] = y
    return pd.DataFrame(out)


def episodi_indip(stato: pd.Series, gap=126) -> int:
    idx = np.flatnonzero(stato.to_numpy())
    if not len(idx):
        return 0
    return int(1 + (np.diff(idx) >= gap).sum())


def dr(y: np.ndarray, s: np.ndarray, ok: np.ndarray):
    m = ok & ~np.isnan(y)
    a, b = m & s, m & ~s
    if a.sum() < 30 or b.sum() < 30:
        return np.nan, int(a.sum()), np.nan, np.nan
    pa, pb = y[a].mean(), y[b].mean()
    return pa - pb, int(a.sum()), float(pa), float(pb)


def ic_dr(y, s, ok, anni, giri=400):
    ua = np.unique(anni)
    ix = {a: np.flatnonzero(anni == a) for a in ua}
    v = []
    for _ in range(giri):
        sel = np.concatenate([ix[a] for a in rng.choice(ua, len(ua), replace=True)])
        d = dr(y[sel], s[sel], ok[sel])[0]
        if not np.isnan(d):
            v.append(d)
    return [round(float(np.percentile(v, 5)), 4), round(float(np.percentile(v, 95)), 4)] if len(v) > 50 else None


def main():
    P = scarica()
    sp = P["GSPC"].copy()
    sp_store = store.load("sp500").dropna()
    sp = sp_store[sp_store.index >= "1971-01-01"]
    # controllo date degli episodi pre-1986 sui prezzi
    ctrl = {}
    for d, nat in PRE86:
        w = sp[(sp.index >= pd.Timestamp(d) - pd.Timedelta(days=60)) & (sp.index <= pd.Timestamp(d) + pd.Timedelta(days=60))]
        ctrl[d] = {"natura": nat, "massimo_reale_vicino": str(w.idxmax().date()), "scarto_giorni": int(abs((w.idxmax() - pd.Timestamp(d)).days))}
    liv, acc, zz = proxy_misure(P)
    cal = sp.index[sp.index >= "1971-06-01"]
    LIV, ACC = liv.mean(axis=1).reindex(cal, method="ffill"), acc.mean(axis=1).reindex(cal, method="ffill")
    Z = zz.mean(axis=1).reindex(cal, method="ffill")
    alto, acce = LIV >= SOGLIA, ACC >= SOGLIA
    rec = (LIV.rolling(126, min_periods=1).max() >= SOGLIA)
    L = rec & (Z < Z.rolling(63, min_periods=40).mean())
    inn = inneschi(cal)
    RT = inn["RT"]
    stati = {"S1 sbilanciato+accelera": alto & acce, "S2 S1 con tassi/credito calmi": alto & acce & ~RT, "S3 S1 + rottura (tassi/credito)": alto & acce & RT,
             "S4 sbilanciato + inversione": alto & L, "S5 S4 + rottura": alto & L & RT, "S6 sbilanciato + rottura (senza accel.)": alto & RT, "S7 solo rottura": RT}
    Y = bersagli(sp).reindex(cal)
    fuori = finestra(cal, ESTERNI + ["1973-10-17"])
    for d in MISTE_MAX:
        pos = cal.searchsorted(pd.Timestamp(d))
        fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
    ok_base = (~fuori).to_numpy()
    ok_sens = ok_base & ~((cal >= "1973-01-01") & (cal <= "1975-06-30"))
    anni = cal.year.to_numpy()
    blocchi = {"1971-1989": cal.year <= 1989, "1990-2014": (cal.year >= 1990) & (cal.year <= 2014), "2015-2026": cal.year >= 2015, "tutto": np.ones(len(cal), bool)}
    ris = {}
    for sn, s in stati.items():
        sa = s.to_numpy()
        ris[sn] = {"frazione_giorni": round(float(sa[ok_base].mean()), 4), "episodi_indipendenti": episodi_indip(s)}
        for yn in Y.columns:
            y = Y[yn].to_numpy()
            rr = {}
            for bn, bm in blocchi.items():
                okb = ok_base & bm
                d, n, pa, pb = dr(y, sa, okb)
                rr[bn] = {"DR": None if np.isnan(d) else round(float(d), 4), "n_dentro": n, "P_dentro": None if pa is None or np.isnan(pa) else round(pa, 4), "P_fuori": None if pb is None or np.isnan(pb) else round(pb, 4),
                          "IC90": ic_dr(y[bm], sa[bm], ok_base[bm], anni[bm]) if bn in ("1990-2014", "2015-2026", "1971-1989") and not np.isnan(d) else None}
            d_s, *_ = dr(y, sa, ok_sens)
            rr["senza_1973-75"] = None if np.isnan(d_s) else round(float(d_s), 4)
            ris[sn][yn] = rr
    # soglia del migliore tra N: spostamento circolare dello stato
    n = len(cal)
    nulli = []
    for _ in range(500):
        k = int(rng.integers(756, n - 756))
        mx = -9
        for sn, s in stati.items():
            sh = np.roll(s.to_numpy(), k)
            for yn in Y.columns:
                d, *_ = dr(Y[yn].to_numpy(), sh, ok_base & blocchi["2015-2026"])
                if not np.isnan(d):
                    mx = max(mx, d)
        nulli.append(mx)
    soglia_N = round(float(np.percentile(nulli, 95)), 4)
    # cattura degli episodi finanziari (stato acceso in qualche giorno dei 40 fino al massimo)
    eps = [(d, c, "finanziaria") for d, c, nat, _ in CLASSIFICA if nat == "finanziaria" and c <= -8 and pd.Timestamp(d) >= cal[0]] + [(d, None, nat) for d, nat in PRE86 if nat == "finanziaria"]
    cattura = {}
    for sn, s in stati.items():
        ok_e, tot = [], 0
        for d, c, nat in sorted(eps):
            pos = cal.searchsorted(pd.Timestamp(d))
            if pos >= len(cal) or pos < 100:
                continue
            tot += 1
            if s.iloc[max(0, pos - 40):pos + 1].any():
                ok_e.append(d)
        cattura[sn] = {"segnalati": len(ok_e), "su": tot, "elenco": ok_e}
    # valore aggiunto dal 1990 sopra l'Indice crollo basso
    try:
        crollo = ic.calcola_serie()["indice"].reindex(cal, method="ffill")
        basso = (crollo < 41).to_numpy() & (cal >= "1990-01-01")
        va = {}
        for sn in ("S1 sbilanciato+accelera", "S3 S1 + rottura (tassi/credito)", "S5 S4 + rottura", "S7 solo rottura"):
            sa = stati[sn].to_numpy()
            va[sn] = {yn: (lambda r: None if np.isnan(r[0]) else {"DR": round(float(r[0]), 4), "n_dentro": r[1], "P_dentro": round(r[2], 4), "P_fuori": round(r[3], 4)})(dr(Y[yn].to_numpy(), sa, ok_base & basso)) for yn in Y.columns}
    except Exception as e:  # noqa: BLE001
        va = {"errore": str(e)[:100]}
    oggi = {"data": str(cal[-1].date()), "livello_pct": round(float(LIV.iloc[-1]), 3), "accelerazione_pct": round(float(ACC.iloc[-1]), 3), "z_composito": round(float(Z.iloc[-1]), 2), "inversione": bool(L.iloc[-1]),
            "inneschi": {k: bool(inn[k].iloc[-1]) for k in ("R1", "R2", "C1", "F1")}, "rottura": bool(RT.iloc[-1]), "stati_attivi": [k for k, s in stati.items() if bool(s.iloc[-1])],
            "proxy_oggi": {k: round(float(liv[k].dropna().iloc[-1]), 2) for k in liv}}
    storia = pd.DataFrame({"livello": LIV, "accelerazione": ACC, "z": Z, "rottura": RT.astype(int)}).dropna(how="all")
    storia.round(4).to_csv("scratch/concentrazione_storia.csv", index_label="date")
    out = {"controllo_date_pre1986": ctrl, "soglia_migliore_tra_21": soglia_N, "risultati": ris, "cattura_episodi": cattura, "valore_aggiunto_indice_crollo_basso": va, "oggi": oggi,
           "giorni": int(len(cal)), "giorni_esclusi": int(fuori.sum())}
    json.dump(out, open("scratch/concentrazione.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"soglia_N": soglia_N, "oggi": oggi, "ctrl": ctrl}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
