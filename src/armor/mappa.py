"""Mappa settimanale dei segnali (tutti gli indicatori + rendimenti VWCE e S&P 500) e calendario giorno/settimana/mese
con rendimento previsto, reale e scostamento. I dati vanno in due JSON (series/mappa.json e series/cal.json, caricati a richiesta);
nel file locale (non lazy) sono incorporati nella pagina."""
import json
import math

import numpy as np
import pandas as pd

from . import armor_index, bande, semafori, store
from .config import DATA

WEEKS = 520            # 10 anni di settimane
WEEKS_CAL = 160        # settimane nel calendario
MONTHS_CAL = 40
DAYS_CAL = 1100        # giorni nel calendario
EXTRA = [("epu", "Incertezza politica ed economica (EPU)", "Sentimento e ampiezza", "Indice di incertezza sulle notizie di politica economica: sale con crisi e scontri politici.",
          "Valori alti rispetto agli ultimi 10 anni indicano più incertezza: spesso accompagna volatilità.")]
FAMW = {g: v[0] for g, v in armor_index.GROUPS.items()}


def _num(x, d=2):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:  # noqa: BLE001
        return None
    return None if (math.isnan(x) or math.isinf(x)) else round(x, d)


def _asof(s: pd.Series, dates) -> pd.Series:
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(s.index.union(dates)).ffill().reindex(dates)


def _row_meta(key: str):
    if key in semafori.SPEC_BY:
        sp = semafori.SPEC_BY[key]
        return {"n": sp[1], "u": sp[6].strip(), "d": min(int(sp[7]), 2), "rd": sp[8], "wo": sp[9], "zn": semafori.zone_text(sp)}
    if key == "risk_1m":
        return {"n": "Probabilità di calo a 1 mese (Armor)", "u": "%", "d": 1, "rd": "La probabilità stimata dal modello statistico Armor di un calo ≥10% entro 1 mese.",
                "wo": "Sopra la sua media storica il modello vede più rischio del solito.", "zn": "colore dal confronto con gli ultimi 10 anni della stessa stima"}
    if key == "risk_3m":
        return {"n": "Probabilità di calo a 3 mesi (Armor)", "u": "%", "d": 1, "rd": "La probabilità stimata dal modello statistico Armor di un calo ≥10% entro 3 mesi.",
                "wo": "Sopra la sua media storica il modello vede più rischio del solito.", "zn": "colore dal confronto con gli ultimi 10 anni della stessa stima"}
    for k, n, _g, rd, wo in EXTRA:
        if k == key:
            return {"n": n, "u": "", "d": 0, "rd": rd, "wo": wo, "zn": "colore dal confronto con gli ultimi 10 anni dello stesso indicatore"}
    return {"n": key, "u": "", "d": 1, "rd": "", "wo": "", "zn": ""}


def build_mappa(sp: pd.Series, aix: dict, vw: pd.Series) -> dict | None:
    if not aix:
        return None
    sp = sp.dropna()
    wk = pd.Series(sp.index, index=sp.index).groupby(pd.Grouper(freq="W-FRI")).last().dropna()
    wk = pd.DatetimeIndex(wk.values)
    wk = wk[-(WEEKS + 6):]
    W = wk[6:]
    prev = wk[5:-1]
    spw = sp.reindex(wk)
    vww = _asof(vw, wk) if len(vw) else pd.Series(np.nan, index=wk)
    if len(vw):
        vww[vww.index > vw.dropna().index[-1] + pd.Timedelta(days=4)] = np.nan
    r_sp = ((spw / spw.shift(1) - 1) * 100).reindex(W)
    r_vw = ((vww / vww.shift(1) - 1) * 100).reindex(W)
    # cosa e' successo nelle 4 settimane dopo (solo descrittivo)
    sp_all = sp
    f4 = []
    f4v = []
    vwa = _asof(vw, sp_all.index) if len(vw) else pd.Series(np.nan, index=sp_all.index)
    if len(vw):
        vwa[vwa.index > vw.dropna().index[-1] + pd.Timedelta(days=4)] = np.nan
    for t in W:
        i = sp_all.index.get_loc(t)
        j = min(i + 20, len(sp_all) - 1)
        if j - i < 20:
            f4.append(None)
            f4v.append(None)
        else:
            f4.append(_num((sp_all.iloc[j] / sp_all.iloc[i] - 1) * 100, 1))
            f4v.append(_num((vwa.iloc[j] / vwa.iloc[i] - 1) * 100, 1) if pd.notna(vwa.iloc[i]) and pd.notna(vwa.iloc[j]) else None)
    fut = pd.Series([np.nan if x is None else x for x in f4], index=W)
    S, G = aix["S"], aix["G"]
    rows = []

    def add(key, name, typ, grp, sc, v, meta=None, scale=None):
        row = {"k": key, "n": name, "t": typ, "g": grp, "sc": [None if (x is None or pd.isna(x)) else int(round(x)) for x in sc],
               "v": [_num(x, 3) for x in v]}
        if meta:
            row.update({k: meta[k] for k in ("u", "d", "rd", "wo", "zn") if k in meta})
        # scala: quale valore reale corrisponde a ciascun colore
        if typ == "ind" and scale is not None:
            sca = []
            for tg in (10, 30, 50, 70, 90):
                m = scale[(scale["s"] - tg).abs() <= 8]["v"].dropna()
                sca.append(_num(m.median(), 3) if len(m) >= 5 else None)
            row["sv"] = sca
        # statistiche descrittive: S&P a 4 settimane dopo, per fascia di colore
        arr = pd.Series([np.nan if x is None else x for x in row["sc"]], index=W, dtype=float)
        st = {}
        for nm, msk in (("lo", arr <= 33), ("mid", (arr > 33) & (arr < 67)), ("hi", arr >= 67)):
            fv = fut[msk & fut.notna()]
            st[nm] = [int(len(fv)), _num(fv.mean(), 2) if len(fv) else None, _num((fv <= -5).mean() * 100, 0) if len(fv) else None]
        if typ != "ret":
            row["st"] = st
        rows.append(row)

    add("vwce", "VWCE · % settimana", "ret", "Rendimenti reali", [np.nan] * len(W), r_vw.values)
    add("sp500", "S&P 500 · % settimana", "ret", "Rendimenti reali", [np.nan] * len(W), r_sp.values)
    hist = aix["hist"].dropna()
    add("armor", "Indice Armor", "idx", "Indice", _asof(hist, W).values, _asof(hist, W).values)
    fam = {}
    for g in aix["G"].columns:
        sc = (G[g] - 0.10) / 0.75
        sc = (1 + 99 * sc.clip(0, 1))
        a = _asof(sc, W)
        add("fam:" + g, g, "fam", g, a.values, a.values)
        fam[g] = {"w": FAMW.get(g, 0), "keys": []}
    seen = set()
    for g, (_w, items) in armor_index.GROUPS.items():
        for key, *_ in items:
            if key not in S or S[key].dropna().empty:
                continue
            try:
                raw = armor_index._raw_series(key, sp)
                raw = raw[~raw.index.duplicated(keep="last")].dropna()
                rawd = raw.reindex(raw.index.union(S.index)).ffill(limit=armor_index._limit(key)).reindex(S.index)
                rw = _asof(raw, W) if False else rawd.reindex(W, method="ffill")
                if key.startswith("risk_"):
                    rw, rawd = rw * 100, rawd * 100
                scw = (S[key] * 100).reindex(W, method="ffill")
                sc_df = pd.DataFrame({"s": (S[key] * 100).reindex(S.index[-2600:]), "v": rawd.reindex(S.index[-2600:])})
                add(key, _row_meta(key)["n"], "ind", g, scw.values, rw.values, _row_meta(key), sc_df)
                fam[g]["keys"].append(key)
                seen.add(key)
            except Exception:  # noqa: BLE001
                continue
    for key, name, grp, _rd, _wo in EXTRA:
        try:
            s = store.load(key).dropna()
            if len(s) < 100:
                continue
            a = s.reindex(s.index.union(sp.index)).ffill(limit=45).reindex(sp.index)
            pr = a.rolling(armor_index.WINDOW, min_periods=250).rank(pct=True) * 100
            add(key, name, "ind", grp, pr.reindex(W, method="ffill").values, a.reindex(W, method="ffill").values, _row_meta(key),
                pd.DataFrame({"s": pr.iloc[-2600:], "v": a.iloc[-2600:]}))
            if grp in fam:
                fam[grp]["keys"].append(key)
        except Exception:  # noqa: BLE001
            continue
    for key in armor_index.NEW_IND:   # indicatori di credito monitorati (ANFCI, SLOOS, gap credito/PIL), anche se non ancora nell'Indice
        if key in seen:
            continue
        try:
            s = semafori.series_of(key, sp).dropna()
            if len(s) < 60:
                continue
            a = s.reindex(s.index.union(sp.index)).ffill(limit=armor_index._limit(key)).reindex(sp.index)
            pr = a.rolling(armor_index.WINDOW, min_periods=250).rank(pct=True) * 100
            add(key, _row_meta(key)["n"], "ind", "Credito e liquidità", pr.reindex(W, method="ffill").values, a.reindex(W, method="ffill").values, _row_meta(key),
                pd.DataFrame({"s": pr.iloc[-2600:], "v": a.iloc[-2600:]}))
            rows[-1]["ni"] = 1
        except Exception:  # noqa: BLE001
            continue
    # indicatori nuovi del PIANO_MODELLO (monitorati, non nell'Indice): colore = rischio (per quelli «bassi = rischio» il percentile si inverte)
    for key in ("eps_g12", "claims_up", "delinq_biz", "core_yoy", "ciss", "rel_small", "rel_cicl", "net_liq_13w"):
        if key in seen or key not in armor_index.NEW_IND_FOND:
            continue
        try:
            fam_k, kind, _y, _r = armor_index.NEW_IND_FOND[key]
            s = semafori.series_of(key, sp).dropna()
            if len(s) < 60:
                continue
            a = s.reindex(s.index.union(sp.index)).ffill(limit=armor_index._limit(key) + 30).reindex(sp.index)
            pr = a.rolling(armor_index.WINDOW, min_periods=250).rank(pct=True) * 100
            if kind == "lo":
                pr = 100 - pr
            grp = semafori.SPEC_BY[key][2] if key in semafori.SPEC_BY else fam_k
            add(key, _row_meta(key)["n"], "ind", grp, pr.reindex(W, method="ffill").values, a.reindex(W, method="ffill").values, _row_meta(key),
                pd.DataFrame({"s": pr.iloc[-2600:], "v": a.iloc[-2600:]}))
            rows[-1]["ni"] = 1
        except Exception:  # noqa: BLE001
            continue
    return {"w": [t.strftime("%Y-%m-%d") for t in W], "rows": rows, "fam": fam, "f4": f4, "f4v": f4v, "asof": str(W[-1].date()),
            "bz": [_num(x, 4) for x in (lambda g: (g[9], g[49], g[89]))(bande.zgrid(5, pd.Timestamp(W[-1])))],
            "pc": "Put/Call sulle opzioni SPY: l'archivio ha iniziato a raccogliere il dato da poco; la riga comparirà quando ci saranno abbastanza giorni."}


# ------------------------------------------------------------------ calendario
def build_cal(sp: pd.Series, vw: pd.Series, vix: pd.Series, aix: dict | None, today: pd.Timestamp, events: list[dict]) -> dict:
    sp = sp.dropna()
    sp = sp[sp.index <= today]
    vix = vix.dropna()
    vix = vix[~vix.index.duplicated(keep="last")]
    vw = vw.dropna()
    vw = vw[~vw.index.duplicated(keep="last")] if len(vw) else vw
    r_sp = sp.pct_change() * 100
    r_vw = vw.pct_change() * 100 if len(vw) else pd.Series(dtype=float)
    cm = r_sp.index.intersection(r_vw.index)
    cm = cm[cm >= today - pd.Timedelta(days=1100)]
    ratio = float(r_vw.reindex(cm).std() / r_sp.reindex(cm).std()) if len(cm) > 100 else 1.0
    drift = float(r_sp[r_sp.index >= "1990-01-01"].mean())    # tendenza storica media giornaliera (%)
    hist = aix["hist"].dropna() if aix else pd.Series(dtype=float)
    vlast = float(vix.iloc[-1]) if len(vix) else 18.0
    vprev = vix.shift(1)
    start = today - pd.Timedelta(days=DAYS_CAL)
    days = sorted(set(r_sp.index[r_sp.index >= start]) | set(r_vw.index[r_vw.index >= start]))
    D = []
    for t in days:
        v0 = vprev.asof(t) if len(vprev) else np.nan
        v0 = vlast if pd.isna(v0) else float(v0)
        b = bande.band(v0, 1, t)
        a0 = hist[hist.index < t]
        rs, rv = r_sp.get(t), r_vw.get(t)
        ps = _num(bande.pct_of(float(rs), v0, 1, t), 0) if rs is not None and pd.notna(rs) else None
        pv = _num(bande.pct_of(float(rv) / ratio, v0, 1, t), 0) if rv is not None and pd.notna(rv) else None
        D.append([t.strftime("%Y-%m-%d"), _num(rs, 2), _num(rv, 2), _num(b["lo"], 2), _num(b["med"], 2), _num(b["hi"], 2),
                  _num(b["lo"] * ratio, 2), _num(b["med"] * ratio, 2), _num(b["hi"] * ratio, 2), ps, pv,
                  _num(a0.iloc[-1], 0) if len(a0) else None, _num(v0, 1),
                  _num(sp.get(t), 2), _num(vw.get(t), 2), _num(vix.get(t), 2)])   # 13-15: chiusure del giorno (S&P, VWCE, VIX)
    rh = DATA / "risk_history.csv"
    rk = pd.read_csv(rh, parse_dates=["date"]).set_index("date") if rh.exists() else pd.DataFrame()

    def periods(freq: str, n: int, hh: int, pcol: str):
        pr_sp = sp.index.to_period(freq)
        c_sp = sp.groupby(pr_sp).last()
        s_sp = c_sp.shift(1)
        dd_sp = (sp / pd.Series(pr_sp.map(s_sp).values, index=sp.index) - 1).groupby(pr_sp).min().clip(upper=0) * 100
        if len(vw):
            pr_vw = vw.index.to_period(freq)
            c_vw = vw.groupby(pr_vw).last()
            s_vw = c_vw.shift(1)
            dd_vw = (vw / pd.Series(pr_vw.map(s_vw).values, index=vw.index) - 1).groupby(pr_vw).min().clip(upper=0) * 100
        c_h = hist.groupby(hist.index.to_period(freq)).last() if len(hist) else pd.Series(dtype=float)
        c_v = vix.groupby(vix.index.to_period(freq)).last()
        nday = sp.groupby(pr_sp).size()
        cur = pd.Period(today, freq)
        out = []
        pers = [cur - i for i in range(n)][::-1] + [cur + 1, cur + 2] if freq == "M" else [cur - i for i in range(n)][::-1] + [cur + 1]
        for p in pers:
            a = p.start_time
            b_ = p.end_time.normalize()
            rs = (c_sp.get(p) / s_sp.get(p) - 1) * 100 if p in c_sp.index and pd.notna(s_sp.get(p)) else None
            rv = (c_vw.get(p) / s_vw.get(p) - 1) * 100 if len(vw) and p in c_vw.index and pd.notna(s_vw.get(p)) else None
            v0 = c_v.get(p - 1)
            v0 = vlast if v0 is None or pd.isna(v0) else float(v0)
            b = bande.band(v0, hh, a)
            a0 = c_h.get(p - 1) if len(c_h) else None
            a1 = c_h.get(p) if len(c_h) and p in c_h.index else None
            pk = None
            if len(rk) and pcol in rk:
                z = rk[pcol][rk.index < a].dropna()
                pk = _num(z.iloc[-1] * 100, 1) if len(z) else None
            ps = _num(bande.pct_of(float(rs), v0, hh, a), 0) if rs is not None else None
            pv = _num(bande.pct_of(float(rv) / ratio, v0, hh, a), 0) if rv is not None else None
            out.append([a.strftime("%Y-%m-%d"), b_.strftime("%Y-%m-%d"), _num(rs, 2), _num(rv, 2),
                        _num(b["lo"], 2), _num(b["med"], 2), _num(b["hi"], 2), _num(b["lo"] * ratio, 2), _num(b["med"] * ratio, 2), _num(b["hi"] * ratio, 2), ps, pv,
                        _num(a0, 0), _num(a1, 0), pk, _num(dd_sp.get(p), 2) if p in dd_sp.index else None,
                        _num(dd_vw.get(p), 2) if len(vw) and p in dd_vw.index else None, int(nday.get(p, 0)), _num(v0, 1), _num(b["pup"] * 100, 0)])
        return out

    W = periods("W", WEEKS_CAL, 5, "p_10g")
    M = periods("M", MONTHS_CAL, 21, "p_1m")
    ev = {}
    for x in events:
        if x["peso"] >= 2 or x["tipo"] == "Opzioni":
            ev.setdefault(x["date"], []).append([x["tipo"], x["nome"]])
    ev_ = bande.load_eval()
    return {"today": today.strftime("%Y-%m-%d"), "ratio": round(ratio, 2), "cov": {k: ev_.get(k) for k in ("g", "s", "m")},
            "d": D, "w": W, "m": M, "ev": ev, "vlast": _num(vlast, 1)}


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


# ------------------------------------------------------------------ componenti HTML + JS
MAPPA_CSS = """
.mpw{margin:8px 0}.mpbar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:6px 0}.mpbar button,.c2bar button{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:99px;padding:6px 13px;font:inherit;font-size:13px;cursor:pointer}
.mpbar button.on,.c2bar button.on{background:var(--ac);color:#fff;border-color:var(--ac);font-weight:700}
.mpleg{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mu);margin:6px 0}.mpleg .gr{display:flex;align-items:center;gap:6px}.mpleg i{display:block;width:120px;height:10px;border-radius:5px}
.mpsc{font-size:13px;margin:4px 0;min-height:20px}.mpsc span{display:inline-block;padding:2px 8px;border-radius:6px;color:#fff;font-weight:700;margin:2px 4px 2px 0;font-size:12px}
.mpscroll{overflow:auto;max-height:78vh;border:1px solid var(--bd);border-radius:10px;background:var(--card);-webkit-overflow-scrolling:touch}
.mpt{border-collapse:separate;border-spacing:2px;font-size:10px}.mpt th,.mpt td{border:0;padding:0;text-align:center}
.mpt thead th{position:sticky;top:0;background:var(--card);z-index:3;font-size:9px;color:var(--mu);font-weight:600;height:28px;min-width:26px;line-height:1.1}
.mpt .rl{position:sticky;left:0;z-index:2;background:var(--card);text-align:left;white-space:nowrap;font-size:12px;font-weight:600;color:var(--tx);padding:0 8px 0 6px;min-width:128px;max-width:128px;overflow:hidden;text-overflow:ellipsis;cursor:pointer;border-right:1px solid var(--bd)}
.mpt thead .rl{z-index:4}.mpt .rl.fm{font-weight:800}.mpt .rl.ind{font-weight:500;padding-left:16px;font-size:11px;color:var(--mu)}.mpt .rl.sel{outline:2px solid var(--ac);outline-offset:-2px}
.mpt tr.sec td{height:22px}.mpt .rl.secl{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--ac);cursor:default;border-right:1px solid var(--bd)}
.mpt td.c{min-width:26px;height:26px;border-radius:5px;color:#fff;font-weight:700;cursor:pointer;font-size:10px;text-shadow:0 0 2px rgba(0,0,0,.45)}
.mpt td.c.n{background:var(--bg);cursor:default}.mpt td.c.on{outline:2px solid #fff;outline-offset:-1px;box-shadow:0 0 0 2px var(--ac)}
.mpt tr.sep td{height:6px}
.mpop{position:fixed;z-index:40;max-width:340px;width:calc(100vw - 20px);background:var(--card);color:var(--tx);border:1px solid var(--ac);border-radius:12px;padding:12px 14px;box-shadow:0 10px 30px rgba(0,0,0,.5);font-size:13px;line-height:1.45;display:none}
.mpop b.t{font-size:14px}.mpop .big{font-size:22px;font-weight:800}.mpop ul{margin:6px 0;padding-left:18px}.mpop .x{position:absolute;right:6px;top:2px;border:0;background:transparent;color:var(--mu);font-size:22px;cursor:pointer}
.mpop .tag{display:inline-block;padding:1px 8px;border-radius:99px;color:#fff;font-weight:700;font-size:12px}.mpop .mu{color:var(--mu);font-size:12px}
.c2w{margin:6px 0}.c2bar{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 8px}.c2nav{display:flex;justify-content:space-between;align-items:center;margin:6px 0}
.c2g{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.c2g .cw{text-align:center;font-size:12px;color:var(--mu);font-weight:700}
.c2d{min-height:62px;border:1px solid var(--bd);border-radius:8px;padding:3px 3px 2px;font-size:11px;background:var(--card);display:flex;flex-direction:column;gap:0;overflow:hidden;cursor:pointer;color:var(--tx);line-height:1.2}
.c2d.o{border:0;background:transparent;cursor:default}.c2d.e{color:var(--mu)}.c2d b{font-size:12px}.c2d small{font-size:10px;font-weight:700;white-space:nowrap}.c2d small.v{opacity:.85;font-weight:600}.c2d small.px{font-size:9px;font-weight:500;opacity:.75}
.c2d.today{outline:2px solid var(--ac)}.c2d.sel{outline:3px solid var(--ac)}.c2d .ev{color:#fff}
.c2l{display:grid;gap:4px}.c2r{display:grid;grid-template-columns:1.25fr 1fr 1fr 40px;gap:6px;align-items:center;border:1px solid var(--bd);border-radius:10px;padding:7px 9px;background:var(--card);cursor:pointer;font-size:12px}
.c2r.sel{outline:2px solid var(--ac)}.c2r.fut{opacity:.6}.c2r .ds{font-weight:700}.c2r .pill{display:inline-block;min-width:34px;text-align:center;border-radius:6px;padding:2px 4px;color:#fff;font-weight:800;text-shadow:0 0 2px rgba(0,0,0,.55)}
.c2h{display:grid;grid-template-columns:1.25fr 1fr 1fr 40px;gap:6px;font-size:11px;color:var(--mu);padding:0 9px;position:sticky;top:0;background:var(--card);z-index:2}
.c2p{border:1px solid var(--ac);border-radius:12px;padding:12px 14px;margin:10px 0;background:var(--card);font-size:13px}.c2p table{font-size:13px}.c2p h4{margin:0 0 6px;font-size:15px}
.c2p td,.c2p th{padding:5px 4px;font-size:12px}.c2p td .nw{white-space:nowrap}.c2p td:first-child{white-space:nowrap}.dv{font-weight:800}
"""

MAPPA_JS = r"""
<script>
(function(){
function nf(x,d){return x==null?'n.d.':x.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function sg(x,d){return x==null?'n.d.':(x>0?'+':'')+nf(x,d)+'%'}
var BANDS=[[20,'molto basso'],[40,'basso'],[60,'moderato'],[80,'elevato'],[101,'molto alto']];
function bandName(v){for(var i=0;i<BANDS.length;i++)if(v<BANDS[i][0])return BANDS[i][1];return 'molto alto'}
function col(v){var h=125*(1-Math.min(Math.max((v-1)/99,0),1));return 'hsl('+h.toFixed(0)+',70%,42%)'}
function rcol(x){var t=Math.max(-1,Math.min(1,x/4));return 'hsl('+(60+t*62).toFixed(0)+',68%,'+(40+(1-Math.abs(t))*4)+'%)'}
function dm(s){var a=s.split('-');return a[2]+'/'+a[1]+'/'+a[0]}
var MES=['gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic'];
var pop=document.getElementById('mpop');if(!pop){pop=document.createElement('div');pop.id='mpop';pop.className='mpop';document.body.appendChild(pop)}
var pinned=false;
function showPop(html,el){pop.innerHTML='<button class="x" aria-label="Chiudi">×</button>'+html;pop.style.display='block';var r=el.getBoundingClientRect(),w=pop.offsetWidth,h=pop.offsetHeight;
var x=Math.min(Math.max(8,r.left+r.width/2-w/2),window.innerWidth-w-8),y=r.top-h-8;if(y<8)y=Math.min(r.bottom+8,window.innerHeight-h-8);pop.style.left=x+'px';pop.style.top=Math.max(8,y)+'px'}
pop.addEventListener('click',function(e){if(e.target.className==='x'){pinned=false;pop.style.display='none'}});
document.addEventListener('click',function(e){if(!e.target.closest||(!e.target.closest('.mpop')&&!e.target.closest('.mpt td.c'))){pinned=false;pop.style.display='none'}});
function init(root){
if(root.dataset.on)return;root.dataset.on='1';
var D=null,per=+(root.dataset.per||156),open=root.dataset.open==='1',selRow=null,selCell=null;
root.innerHTML='<p class="mu">Caricamento della mappa…</p>';
var emb=document.getElementById('armor-mappa-data');
function go(j){D=j;draw()}
if(window.__ARMOR_MAPPA){go(window.__ARMOR_MAPPA)}else if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/mappa.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){window.__ARMOR_MAPPA=j;go(j)}).catch(function(){root.innerHTML='<p class="mu">Mappa non disponibile (serve la connessione).</p>'})}
function idx(k){for(var i=0;i<D.rows.length;i++)if(D.rows[i].k===k)return i;return -1}
function valTxt(r,c){var v=r.v[c];if(v==null)return 'n.d.';if(r.t==='ret')return sg(v,2);if(r.t==='idx'||r.t==='fam')return nf(v,0)+'/100';return nf(v,r.d==null?1:r.d)+(r.u?(r.u==='%'?'%':' '+r.u):'')}
function drivers(c){var out=[];D.rows.forEach(function(r){if(r.t==='fam'&&r.sc[c]!=null){var w=(D.fam[r.g]||{}).w||0;out.push([r.g,r.sc[c],w])}});return out}
function detail(ri,c){var r=D.rows[ri],d=dm(D.w[c]),h='',sc=r.sc[c];
var i4=D.f4[c],i4v=D.f4v[c],aft=(i4==null?'':'<div class="mu">Dopo questa settimana (descrittivo): S&amp;P 500 a 4 settimane '+sg(i4,1)+(i4v!=null?', VWCE '+sg(i4v,1):'')+'.</div>');
if(r.t==='ret'){
 var rs=D.rows[idx('sp500')],rv=D.rows[idx('vwce')],ar=D.rows[idx('armor')],vx=D.rows[idx('vix')];var a0=c>0?ar.sc[c-1]:null,v0=(vx&&c>0)?vx.v[c-1]:null,sig=v0?v0/7.1:null,rr=r.v[c],bz=D.bz;
 h='<b class="t">'+r.n.split(' · ')[0]+' · settimana al '+d+'</b><div class="big" style="color:'+rcol(rr==null?0:rr)+'">'+sg(rr,2)+'</div><ul>'+
 '<li>S&amp;P 500: '+sg(rs.v[c],2)+' · VWCE: '+sg(rv.v[c],2)+'</li>'+
 (a0!=null?'<li>Indice Armor a inizio settimana: <b>'+a0+'</b> ('+bandName(a0)+').</li>':'')+
 (bz&&v0?'<li>VIX a inizio settimana '+nf(v0,1)+' → il mercato si aspettava tra <b>'+nf(bz[0]*v0/7.1,1)+'%</b> e <b>'+sg(bz[2]*v0/7.1,1)+'</b> (8 casi su 10, centro '+sg(bz[1]*v0/7.1,1)+'). '+(rr!=null&&r.k==='sp500'?(rr<bz[0]*v0/7.1?'La settimana è stata <b>peggiore</b> del 90% dei casi.':(rr>bz[2]*v0/7.1?'La settimana è stata <b>migliore</b> del 90% dei casi.':'La settimana è rimasta nella fascia prevista.')):'')+'</li>':'')+'</ul>'+aft}
else if(r.t==='idx'){
 var dr=drivers(c).map(function(x){return [x[0],x[1],x[1]*x[2]]}).sort(function(a,b){return b[2]-a[2]}),prev=c>0?r.sc[c-1]:null;
 h='<b class="t">Indice Armor · settimana al '+d+'</b><div class="big" style="color:'+col(sc)+'">'+(sc==null?'n.d.':sc)+'<span style="font-size:14px"> /100 · rischio '+(sc==null?'':bandName(sc))+'</span></div><ul>'+
 (prev!=null?'<li>Rispetto alla settimana prima: '+(sc-prev>0?'+':'')+(sc-prev)+' punti.</li>':'')+
 '<li>Spingono l\'indice <b>in alto</b>: '+dr.slice(0,3).map(function(x){return x[0]+' ('+Math.round(x[1])+')'}).join(', ')+'.</li>'+
 '<li>Lo tengono <b>basso</b>: '+dr.slice(-2).reverse().map(function(x){return x[0]+' ('+Math.round(x[1])+')'}).join(', ')+'.</li></ul>'+
 '<div class="mu">1 = calma, 100 = stress estremo. Media pesata delle 8 famiglie di indicatori.</div>'+aft+stats(r)}
else if(r.t==='fam'){
 var ms=((D.fam[r.g]||{}).keys||[]).map(function(k){var q=D.rows[idx(k)];return q&&q.sc[c]!=null?[q,q.sc[c]]:null}).filter(Boolean).sort(function(a,b){return b[1]-a[1]});
 h='<b class="t">'+r.n+' · settimana al '+d+'</b><div class="big" style="color:'+col(sc)+'">'+(sc==null?'n.d.':sc)+'<span style="font-size:14px"> /100</span></div>'+
 '<div class="mu">Peso nell\'Indice Armor: '+((D.fam[r.g]||{}).w||0)+'%. È la media dei suoi indicatori:</div><ul>'+ms.map(function(x){return '<li>'+x[0].n+': <b>'+valTxt(x[0],c)+'</b> → rischio '+x[1]+'</li>'}).join('')+'</ul>'+aft+stats(r)}
else{
 var sv=r.sv,prev2=c>0?r.v[c-1]:null,ch=(prev2!=null&&r.v[c]!=null)?r.v[c]-prev2:null;
 h='<b class="t">'+r.n+' · settimana al '+d+'</b><div class="big" style="color:'+(sc==null?'inherit':col(sc))+'">'+valTxt(r,c)+'</div>'+
 (sc!=null?'<div>Rischio <span class="tag" style="background:'+col(sc)+'">'+sc+'/100 · '+bandName(sc)+'</span></div>':'')+
 '<ul>'+(r.rd?'<li><b>Cosa misura:</b> '+r.rd+'</li>':'')+(r.wo?'<li><b>Quando preoccupa:</b> '+r.wo+'</li>':'')+(r.zn?'<li><b>Perché questo colore:</b> '+r.zn+'.</li>':'')+
 (ch!=null?'<li>Rispetto alla settimana prima: '+(ch>0?'+':'')+nf(ch,r.d==null?1:r.d)+'.</li>':'')+(r.ni?'<li>Monitorato ma <b>non ancora nell\'Indice Armor</b>: entra solo se il test automatico mensile lo promuove.</li>':'<li>Fa parte di «'+r.g+'» (peso '+((D.fam[r.g]||{}).w||0)+'% dell\'indice).</li>')+'</ul>'+
 (sv?'<div class="mu">Scala reale: '+[10,30,50,70,90].map(function(t,i){return sv[i]==null?'':'<span class="tag" style="background:'+col(t)+'">'+nf(sv[i],r.d==null?1:r.d)+'</span> '}).join('')+'(dal verde al rosso)</div>':'')+aft+stats(r)}
return h}
function stats(r){var s=r.st;if(!s)return '';function f(n,x){return x&&x[0]>=8?nf(x[1],1)+'% (calo ≥5% nel '+nf(x[2],0)+'% dei casi, '+x[0]+' settimane)':'dati insufficienti'}
return '<div class="mu" style="margin-top:6px">Storia di questa riga (descrittiva, non una previsione). S&amp;P 500 nelle 4 settimane dopo: <br>verde (≤33) '+f(0,s.lo)+'<br>rosso (≥67) '+f(0,s.hi)+'</div>'}
function draw(){
 var n=D.w.length,c0=Math.max(0,n-per),cols=[];for(var c=c0;c<n;c++)cols.push(c);
 var head='<tr><th class="rl">settimane →</th>',lm=-1;
 cols.forEach(function(c){var a=D.w[c].split('-'),m=+a[1];var lab=(m!==lm)?MES[m-1]+'<br>'+a[0].slice(2):'<br>'+a[2];lm=m;head+='<th>'+lab+'</th>'});head+='</tr>';
 var body='',grp='';
 function rowHtml(r,i){var cl=r.t==='fam'?'rl fm':(r.t==='ind'?'rl ind':'rl'),lab=r.n;
  if(r.t==='fam'){var kc=((D.fam[r.g]||{}).keys||[]).length;lab=(kc?(open?'▾ ':'▸ '):'')+r.n}
  var s='<tr data-r="'+i+'"><td class="'+cl+(selRow===i?' sel':'')+'" title="'+r.n+'">'+lab+'</td>';
  cols.forEach(function(c){var v=(r.t==='ret')?r.v[c]:r.sc[c];if(v==null){s+='<td class="c n"></td>';return}
   var bg=r.t==='ret'?rcol(v):col(r.t==='ind'?(v):v),tx=r.t==='ret'?(Math.abs(v)<10?nf(v,1).replace('-','−'):nf(v,0)):v;s+='<td class="c" data-c="'+c+'" style="background:'+bg+'">'+tx+'</td>'});return s+'</tr>'}
 D.rows.forEach(function(r,i){
  if(r.t==='ind'&&!open)return;
  var sec=r.t==='ret'?'Rendimenti reali':(r.t==='idx'||r.t==='fam'?(r.t==='idx'?'Indice e famiglie':''):'');
  if(sec&&sec!==grp){body+='<tr class="sec"><td class="rl secl">'+sec+'</td><td colspan="'+cols.length+'"></td></tr>';grp=sec}
  if(r.t==='ind'&&r.g!==grp){grp=r.g}
  body+=rowHtml(r,i);if(r.k==='sp500')body+='<tr class="sep"><td colspan="'+(cols.length+1)+'"></td></tr>'});
 root.innerHTML='<div class="mpbar"><b>Periodo:</b>'+[[52,'1 anno'],[156,'3 anni'],[260,'5 anni'],[520,'10 anni']].map(function(p){return '<button data-per="'+p[0]+'"'+(per===p[0]?' class="on"':'')+'>'+p[1]+'</button>'}).join('')+
 '<button data-open="1"'+(open?' class="on"':'')+'>'+(open?'Nascondi i singoli indicatori':'Mostra tutti gli indicatori')+'</button></div>'+
 '<div class="mpleg"><span class="gr">Rischio: calma <i style="background:linear-gradient(90deg,'+col(1)+','+col(35)+','+col(60)+','+col(100)+')"></i> stress</span>'+
 '<span class="gr">Rendimento: −4% <i style="background:linear-gradient(90deg,'+rcol(-4)+','+rcol(0)+','+rcol(4)+')"></i> +4%</span></div>'+
 '<div class="mpsc" id="mpsc"></div><div class="mpscroll"><table class="mpt"><thead>'+head+'</thead><tbody>'+body+'</tbody></table></div>'+
 '<div class="mu" style="margin-top:6px">Tocca (o passa il mouse su) un quadratino per sapere perché ha quel colore. Tocca il nome di una riga per vedere a quali valori reali corrispondono i colori. '+D.pc+'</div>';
 var sc=root.querySelector('.mpscroll');sc.scrollLeft=sc.scrollWidth;showScale()}
function showScale(){var el=root.querySelector('#mpsc');if(!el)return;if(selRow==null){el.innerHTML='';return}var r=D.rows[selRow],h='';
 if(r.sv){h='<b>'+r.n+'</b> — a che valori corrispondono i colori: '+[10,30,50,70,90].map(function(t,i){return r.sv[i]==null?'':'<span style="background:'+col(t)+'">'+nf(r.sv[i],r.d==null?1:r.d)+(r.u==='%'?'%':'')+'</span>'}).join('')+' (verde → rosso)'}
 else if(r.t==='ret'){h='<b>'+r.n+'</b> — verde = settimana in rialzo, rosso = in calo; il colore pieno si raggiunge a ±4%.'}
 else{h='<b>'+r.n+'</b> — 1–20 molto basso, 20–40 basso, 40–60 moderato, 60–80 elevato, 80–100 molto alto.'}el.innerHTML=h}
root.addEventListener('click',function(e){var b=e.target.closest('button');if(b&&b.dataset.per){per=+b.dataset.per;draw();return}if(b&&b.dataset.open){open=!open;draw();return}
 var rl=e.target.closest('td.rl');if(rl){var i=+rl.parentNode.dataset.r;var r=D.rows[i];if(r&&r.t==='fam'&&((D.fam[r.g]||{}).keys||[]).length&&e.offsetX<18){open=!open;draw();return}selRow=(selRow===i)?null:i;root.querySelectorAll('td.rl').forEach(function(x){x.classList.toggle('sel',x===rl&&selRow===i)});showScale();return}
 var td=e.target.closest('td.c');if(td&&td.dataset.c){e.stopPropagation();pinned=true;showPop(detail(+td.parentNode.dataset.r,+td.dataset.c),td)}});
root.addEventListener('mouseover',function(e){if(pinned||!window.matchMedia('(hover:hover)').matches)return;var td=e.target.closest('td.c');if(td&&td.dataset.c)showPop(detail(+td.parentNode.dataset.r,+td.dataset.c),td)});
root.addEventListener('mouseout',function(e){if(pinned)return;var td=e.target.closest('td.c');if(td)pop.style.display='none'});
}
window.armorMappa=function(scope){(scope||document).querySelectorAll('.mpw[data-mappa]').forEach(init)};
window.armorMappa();
})();
</script>
"""

CAL2_JS = r"""
<script>
(function(){
function nf(x,d){return x==null?'n.d.':x.toLocaleString('it-IT',{minimumFractionDigits:d,maximumFractionDigits:d})}
function sg(x,d){return x==null?'—':(x>0?'+':'')+nf(x,d)+'%'}
function pcol(p,a){var z=Math.max(-1,Math.min(1,(p-50)/45));return z>=0?'rgba(31,143,85,'+(0.18+0.5*z).toFixed(2)+')':'rgba(192,57,43,'+(0.18+0.5*(-z)).toFixed(2)+')'}
var MESI=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
var BN=[[20,'molto basso'],[40,'basso'],[60,'moderato'],[80,'elevato'],[101,'molto alto']];
function bn(v){for(var i=0;i<BN.length;i++)if(v<BN[i][0])return BN[i][1];return 'molto alto'}
function acol(v){var h=125*(1-Math.min(Math.max((v-1)/99,0),1));return 'hsl('+h.toFixed(0)+',70%,40%)'}
function dm(s){var a=s.split('-');return a[2]+'/'+a[1]+'/'+a[0]}
function dd(s){var a=s.split('-');return new Date(+a[0],+a[1]-1,+a[2])}
var SIG={FOMC:'Fed',CPI:'CPI','Lavoro USA':'Lav',Opzioni:'Opz',Trimestrale:'Tri'};
function pos(p){if(p==null)return '';return p<5?'molto sotto il previsto':(p<20?'sotto il previsto':(p<=80?'in linea con il previsto':(p<=95?'sopra il previsto':'molto sopra il previsto')))}
function init(root){
if(root.dataset.on)return;root.dataset.on='1';
var D=null,mode='g',ym=null,sel=null,byD={};root.innerHTML='<p class="mu">Caricamento…</p>';
var emb=document.getElementById('armor-cal-data');
function go(j){D=j;var t=dd(j.today);ym=[t.getFullYear(),t.getMonth()];draw()}
if(window.__ARMOR_CAL){go(window.__ARMOR_CAL)}else if(emb){go(JSON.parse(emb.textContent))}else{fetch('series/cal.json?'+Date.now()).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){window.__ARMOR_CAL=j;go(j)}).catch(function(){root.innerHTML='<p class="mu">Calendario non disponibile (serve la connessione).</p>'})}
function mk(){if(Object.keys(byD).length)return;D.d.forEach(function(r){byD[r[0]]=r})}
function px(x){return x==null?'':nf(x,2)}
function line(nm,real,lo,med,hi,p,cl){var dv=real==null?null:real-med;
 return '<tr><td><b>'+nm+'</b></td><td><span class="nw"><b>'+sg(med,1)+'</b></span><div class="mu nw">8 casi su 10:<br>'+nf(lo,1)+'% … '+sg(hi,1)+'</div></td><td><b style="color:'+(real==null?'inherit':(real>=0?'var(--ok)':'var(--bad)'))+'">'+sg(real,2)+'</b>'+(cl!=null?'<div class="mu nw">chiusura '+nf(cl,2)+'</div>':'')+'</td><td class="dv" style="color:'+(p!=null&&(p<10||p>90)?'var(--bad)':'inherit')+'">'+(dv==null?'—':(dv>0?'+':'')+nf(dv,2)+' pp<div class="mu">'+nf(p,0)+'° percentile · '+pos(p)+'</div>')+'</td></tr>'}
function evtxt(d){var e=D.ev[d];return e?e.map(function(x){return x[1]}).join(' · '):''}
var NOTA='<p class="mu">«Previsto» = valore centrale (mediana) della distribuzione storica dei rendimenti, scalata sul VIX della sera prima; «8 casi su 10» = dal 10° al 90° percentile (fascia asimmetrica: i cali sono più ampi dei rialzi). Verificata dal 2000: contiene il reale nel 77-79% dei casi, con fasce circa un terzo più strette della vecchia ±VIX. Il percentile dice dove è caduto il reale nella distribuzione prevista (50 = al centro). <b>Direzione:</b> nessun indicatore provato (Indice Armor, VIX, momentum…) ha previsto il segno meglio della frequenza storica: per questo non c\'è una freccia su/giù, ma la fascia e la frequenza storica di rialzo.</p>';
function panelDay(d){var r=byD[d];if(!r){return '<div class="c2p"><h4>'+dm(d)+'</h4><p class="mu">Giorno senza seduta (weekend o festivo).</p>'+(evtxt(d)?'<p>Evento: '+evtxt(d)+'</p>':'')+'</div>'}
 var fut=r[1]==null&&r[2]==null;
 return '<div class="c2p"><h4>'+dm(d)+(fut?' · previsione':'')+'</h4><table><tr><th></th><th>Previsto</th><th>Reale</th><th>Scostamento</th></tr>'+line('S&amp;P 500',r[1],r[3],r[4],r[5],r[9],r[13])+line('VWCE',r[2],r[6],r[7],r[8],r[10],r[14])+'</table>'+
 (r[15]!=null?'<p>Chiusure del giorno: S&amp;P 500 <b>'+nf(r[13],2)+'</b> · VWCE <b>'+nf(r[14],2)+' €</b> · VIX <b>'+nf(r[15],2)+'</b>.</p>':'')+
 '<p>Indice Armor del giorno prima: <b style="color:'+acol(r[11]||1)+'">'+(r[11]==null?'n.d.':r[11]+' ('+bn(r[11])+')')+'</b> · VIX della sera prima: <b>'+nf(r[12],2)+'</b>.</p>'+(evtxt(d)?'<p>Eventi: <b>'+evtxt(d)+'</b></p>':'')+NOTA+'</div>'}
function panelPer(r,kind){var ph=kind==='w'?'settimana':'mese',fut=r[2]==null&&r[3]==null,partial=!fut&&r[1]>=D.today;
 var a=r[0],b=r[1],tit=kind==='w'?'Settimana '+dm(a)+' – '+dm(b):MESI[+a.split('-')[1]-1]+' '+a.split('-')[0];
 var thr=kind==='w'?'calo ≥5% entro 10 giorni':'calo ≥10% entro 1 mese',lim=kind==='w'?-5:-10;
 return '<div class="c2p"><h4>'+tit+(partial?' · in corso':'')+(fut?' · previsione':'')+'</h4><table><tr><th></th><th>Previsto</th><th>'+(partial?'Finora':'Reale')+'</th><th>Scostamento</th></tr>'+line('S&amp;P 500',r[2],r[4],r[5],r[6],r[10])+line('VWCE',r[3],r[7],r[8],r[9],r[11])+'</table>'+
 '<p>Indice Armor a inizio '+ph+': <b style="color:'+acol(r[12]||1)+'">'+(r[12]==null?'n.d.':r[12]+' ('+bn(r[12])+')')+'</b>'+(r[13]!=null?' → a fine '+ph+': <b style="color:'+acol(r[13])+'">'+r[13]+' ('+bn(r[13])+')</b>':'')+'.</p>'+
 '<p>Storicamente l\'S&amp;P 500 sale nel <b>'+nf(r[19],0)+'%</b> delle '+(kind==='w'?'settimane':'mesi')+'.</p>'+
 (r[14]!=null?'<p>Probabilità di '+thr+' stimata da Armor a inizio '+ph+': <b>'+nf(r[14],0)+'%</b>. '+(r[15]!=null?'Cosa è successo: peggior calo dall\'inizio '+ph+' <b>S&amp;P '+sg(r[15],1)+(r[16]!=null?', VWCE '+sg(r[16],1):'')+'</b> → '+(r[15]<=lim?'<b style="color:var(--bad)">la soglia è stata raggiunta</b>':'soglia non raggiunta')+'.':'')+'</p>':(r[15]!=null?'<p>Peggior calo dall\'inizio: S&amp;P '+sg(r[15],1)+'.</p>':''))+
 '<p class="mu">Sedute considerate: '+r[17]+'. VIX a inizio '+ph+': '+nf(r[18],1)+'.</p>'+NOTA+'</div>'}
function dayCell(y,m,d){var s=y+'-'+('0'+(m+1)).slice(-2)+'-'+('0'+d).slice(-2),r=byD[s],t=D.today,fut=s>t,c='c2d'+(s===t?' today':'')+(sel===s?' sel':'')+(fut?' e':'');
 var bg='',tx='',ev=D.ev[s]?D.ev[s].map(function(x){return '<em class="ev w'+(x[0]==='Opzioni'?2:3)+'">'+(SIG[x[0]]||x[0].slice(0,3))+'</em>'}).join(''):'';
 if(r&&r[1]!=null){bg='style="background:'+pcol(r[9])+'"';tx='<small>S '+sg(r[1],1)+'</small>'+(r[13]!=null?'<small class="px">'+nf(r[13],0)+'</small>':'')+(r[2]!=null?'<small class="v">V '+sg(r[2],1)+'</small>'+(r[14]!=null?'<small class="px">'+nf(r[14],2)+'</small>':''):'')+((r[9]<5||r[9]>95)?'<small>!</small>':'')}
 else if(r&&fut){tx='<small>'+nf(r[3],1)+' … '+sg(r[5],1)+'</small>'}
 return '<div class="'+c+'" '+bg+' data-d="'+s+'"><b>'+d+'</b>'+tx+ev+'</div>'}
function drawGrid(){mk();var y=ym[0],m=ym[1],first=new Date(y,m,1),off=(first.getDay()+6)%7,n=new Date(y,m+1,0).getDate(),cells='';
 for(var i=0;i<off;i++)cells+='<div class="c2d o"></div>';for(var d=1;d<=n;d++){cells+=dayCell(y,m,d)}
 var tmin=dd(D.d[0][0]);var canP=new Date(y,m-1,1)>=new Date(tmin.getFullYear(),tmin.getMonth(),1),canN=new Date(y,m+1,1)<=new Date(dd(D.today).getFullYear(),dd(D.today).getMonth()+2,1);
 return '<div class="c2nav"><button class="btn" data-nv="-1"'+(canP?'':' disabled')+'>‹</button><b>'+MESI[m][0].toUpperCase()+MESI[m].slice(1)+' '+y+'</b><button class="btn" data-nv="1"'+(canN?'':' disabled')+'>›</button></div>'+
 '<div class="c2g">'+['L','M','M','G','V','S','D'].map(function(x){return '<div class="cw">'+x+'</div>'}).join('')+cells+'</div>'+
 '<div class="mu" style="margin:6px 0">Ogni giorno: <b>S</b> = S&amp;P 500, <b>V</b> = VWCE, con sotto il prezzo di chiusura (VWCE: chiusura serale Lang &amp; Schwarz). Colore = dove è caduto il reale nella distribuzione prevista (verde = sopra il previsto, rosso = sotto, trasparente = in linea); «!» = tra il 5% più estremo. Giorni futuri: fascia di 8 casi su 10. Tocca un giorno per il dettaglio.</div>'+(sel&&sel.slice(0,7)===y+'-'+('0'+(m+1)).slice(-2)?panelDay(sel):'')}
function drawList(kind){var L=kind==='w'?D.w:D.m,h='<div class="c2h"><span>'+(kind==='w'?'Settimana':'Mese')+'</span><span>S&amp;P prev. → reale</span><span>VWCE prev. → reale</span><span>Armor</span></div><div class="c2l">';
 var order=L.slice().reverse();order.forEach(function(r){var fut=r[2]==null&&r[3]==null,id=r[0],lab=kind==='w'?dm(r[0]).slice(0,5)+'–'+dm(r[1]).slice(0,5):MESI[+r[0].split('-')[1]-1].slice(0,3)+' '+r[0].slice(2,4);
  var pill=r[12]==null?'':'<span class="pill" style="background:'+acol(r[12])+'">'+r[12]+'</span>';
  function cl(x){return x==null?'inherit':(x>=0?'var(--ok)':'var(--bad)')}
  h+='<div class="c2r'+(fut?' fut':'')+(sel===id?' sel':'')+'" data-p="'+id+'"><span><b>'+lab+'</b></span><span>'+sg(r[5],1)+' → <b style="color:'+cl(r[2])+'">'+sg(r[2],1)+'</b></span><span>'+sg(r[8],1)+' → <b style="color:'+cl(r[3])+'">'+sg(r[3],1)+'</b></span><span>'+pill+'</span></div>';
  if(sel===id)h+=panelPer(r,kind)});
 return h+'</div>'}
function draw(){var body=mode==='g'?drawGrid():drawList(mode);
 root.innerHTML='<div class="c2bar">'+[['g','Giorni'],['w','Settimane'],['m','Mesi']].map(function(x){return '<button data-m="'+x[0]+'"'+(mode===x[0]?' class="on"':'')+'>'+x[1]+'</button>'}).join('')+'</div>'+body;
 var s=root.querySelector('.c2r.sel');if(s&&s.scrollIntoView)s.scrollIntoView({block:'nearest'})}
root.addEventListener('click',function(e){var b=e.target.closest('button');if(b&&b.dataset.m){mode=b.dataset.m;sel=null;draw();return}if(b&&b.dataset.nv){var d=new Date(ym[0],ym[1]+ +b.dataset.nv,1);ym=[d.getFullYear(),d.getMonth()];sel=null;draw();return}
 var c=e.target.closest('.c2d');if(c&&c.dataset.d){sel=(sel===c.dataset.d)?null:c.dataset.d;draw();return}
 var r=e.target.closest('.c2r');if(r){sel=(sel===r.dataset.p)?null:r.dataset.p;draw()}});
}
window.armorCal2=function(scope){(scope||document).querySelectorAll('.c2w[data-cal2]').forEach(init)};
window.armorCal2();
})();
</script>
"""


def mappa_block(open_: bool = False, per: int = 156, data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-mappa-data'>{data_json}</script>" if data_json else ""
    return f"{emb}<div class='mpw' data-mappa='1' data-per='{per}' data-open='{1 if open_ else 0}'></div>{MAPPA_JS}"


def cal_block(data_json: str | None = None) -> str:
    emb = f"<script type='application/json' id='armor-cal-data'>{data_json}</script>" if data_json else ""
    return f"{emb}<div class='c2w' data-cal2='1'></div>{CAL2_JS}"
