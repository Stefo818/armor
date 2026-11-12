# -*- coding: utf-8 -*-
"""Modelli a confronto giorno per giorno (novembre 2026): FHS+VIX prevede, Titan misura lo stato di salute, Titan+ gira in ombra, A1 resta come seconda opinione.
Ogni giorno lavorativo si registra in data/ombra_modelli.csv la probabilità di calo di ciascun modello (orizzonti 10 giorni, 1, 3 e 6 mesi, soglia principale).
La tabella «Chi ha sbagliato di meno» mette accanto previsione, realtà e scarto di ogni modello, con un colore dal verde (giusto) al rosso (sbagliato),
e indica il vincitore per giorno, settimana, mese, 3 mesi, 6 mesi e 1 anno. Si usano solo previsioni il cui esito è già noto."""
import html as _h
import json

import numpy as np
import pandas as pd

from .config import DATA, HORIZONS, PRIMARY

FILE = DATA / "ombra_modelli.csv"
HZ = ("10g", "1m", "3m", "6m")
COLS = ["date", "hz", "p_a1", "p_fhsvix", "p_titan", "p_titanplus"]
MOD = {"p_fhsvix": "FHS+VIX", "p_titan": "Titan", "p_titanplus": "Titan+", "p_a1": "A1"}
MODELLI = ("FHS+VIX", "Titan", "Titan+", "A1")
ORIZ = {"10g": "10 giorni (calo ≥5%)", "1m": "1 mese (calo ≥10%)", "3m": "3 mesi (calo ≥10%)", "6m": "6 mesi (calo ≥10%)"}
FINESTRE = (("Giorno", 1), ("Settimana", 5), ("Mese", 21), ("3 mesi", 63), ("6 mesi", 126), ("1 anno", 252))
SOGLIA_PARI = 0.01   # primo e secondo entro l'1% di errore: nessun vincitore netto
SCARTO_ROSSO = 0.40  # uno scarto medio di 40 punti o più è tutto rosso


def carica() -> pd.DataFrame:
    try:
        d = pd.read_csv(FILE, parse_dates=["date"])
        return d.drop_duplicates(["date", "hz"], keep="last")
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=COLS)


def _titan_ultimo(t) -> dict:
    """Probabilità di calo di Titan per ogni orizzonte, ultima riga del suo registro fino alla data t."""
    try:
        from . import titan_registro
        d = titan_registro.carica()
        d = d[d["date"] <= pd.Timestamp(t)]
        out = {}
        for hz, g in d.groupby("hz"):
            if hz in HZ and len(g) and (pd.Timestamp(t) - g["date"].max()).days < 7:
                out[hz] = float(g.sort_values("date")["calo"].iloc[-1])
        return out
    except Exception:  # noqa: BLE001
        return {}


def registra(pred: dict, t, p: pd.Series | None = None, path=None) -> int:
    """Aggiunge (o sostituisce) la riga del giorno t per ogni orizzonte. Non blocca mai il lavoro giornaliero."""
    path = path or FILE
    d0 = pd.Timestamp(t)
    a1, f0 = {}, {}
    for hz in HZ:
        r = pred.get(hz) or {}
        prim = PRIMARY[hz]
        try:
            base = r.get("p_a1") or r.get("p")
            if base:
                a1[hz] = float(base[prim])
            sf = (r.get("sfidante") or {}).get("p")
            if sf:
                f0[hz] = float(sf[prim])
            elif r.get("motore") == "FHS+VIX" and r.get("p"):
                f0[hz] = float(r["p"][prim])
        except Exception:  # noqa: BLE001
            continue
    pt = _titan_ultimo(d0)
    tp_ = {}
    try:
        from . import titan_plus
        tp_ = titan_plus.oggi(d0, f0, pt, p)
    except Exception as e:  # noqa: BLE001
        print("[titan+] non calcolato:", str(e)[:100], flush=True)
    righe = [{"date": d0.strftime("%Y-%m-%d"), "hz": hz, "p_a1": a1.get(hz), "p_fhsvix": f0.get(hz), "p_titan": pt.get(hz), "p_titanplus": tp_.get(hz)}
             for hz in HZ if hz in f0 or hz in a1]
    if not righe:
        return 0
    try:
        old = pd.read_csv(path, parse_dates=["date"]) if path.exists() else pd.DataFrame(columns=COLS)
    except Exception:  # noqa: BLE001
        old = pd.DataFrame(columns=COLS)
    new = pd.DataFrame(righe)
    old = old[~((old["date"] == d0) & old["hz"].isin(new["hz"]))] if len(old) else old
    out = pd.concat([old, new]) if len(old) else new
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["date", "hz"])
    out[COLS].to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.5f")
    return len(new)


def _lunga(mp: pd.DataFrame | None, reg: pd.DataFrame) -> pd.DataFrame:
    """Tutte le previsioni disponibili: date, model, hz, p (storia settimanale dei modelli + registro giornaliero, che ha la precedenza)."""
    parti = []
    if mp is not None and len(mp):
        x = mp[mp["model"].isin(MODELLI)][["date", "model", "hz", "p"]].copy()
        parti.append(x)
    if len(reg):
        y = []
        for col, m in MOD.items():
            if col in reg:
                z = reg[["date", "hz", col]].dropna().rename(columns={col: "p"})
                z["model"] = m
                y.append(z[["date", "model", "hz", "p"]])
        if y:
            parti.append(pd.concat(y))
    if not parti:
        return pd.DataFrame(columns=["date", "model", "hz", "p"])
    d = pd.concat(parti)
    d["date"] = pd.to_datetime(d["date"])
    return d.drop_duplicates(["date", "model", "hz"], keep="last")


def calcola(p: pd.Series | None = None, mp=None, reg=None, modelli=MODELLI) -> dict:
    """{orizzonte: {finestre: [...], giorni: [...], attesa: {...}}} per la tabella a colori. Solo previsioni con esito noto, solo date in cui ci sono tutti i modelli."""
    from .features import closed_sp500
    from .modeleval import fwd_maxdd, outcome
    p = closed_sp500() if p is None else p
    if mp is None:
        from . import modelli_preds
        mp = modelli_preds.carica()
    reg = carica() if reg is None else reg
    L = _lunga(mp, reg)
    out = {"orizzonti": {}, "modelli": list(modelli), "ultima": ""}
    for hz in HZ:
        g = L[L.hz == hz]
        wide = g.pivot(index="date", columns="model", values="p")
        presenti = [m for m in modelli if m in wide.columns and wide[m].notna().sum() > 0]
        if len(presenti) < 2:
            continue
        wide = wide[presenti].dropna().sort_index()
        thr = PRIMARY[hz]
        y = outcome(p, wide.index, hz, "down", thr)
        dd = fwd_maxdd(p, HORIZONS[hz]).reindex(wide.index)
        ok = y.notna()
        w, yy, dm = wide[ok], y[ok], dd[ok]
        if not len(w):
            continue
        pos_fine = p.index.get_loc(w.index[-1]) if w.index[-1] in p.index else None
        fin = []
        for nome, n in FINESTRE:
            if pos_fine is None:
                break
            ini = p.index[max(0, pos_fine - (n - 1))]
            m = (w.index >= ini)
            if not m.any():
                continue
            ws, ys, ds = w[m], yy[m], dm[m]
            cel = {}
            for mo in presenti:
                e2 = float(((ws[mo] - ys) ** 2).mean())
                cel[mo] = {"p": round(float(ws[mo].mean()), 4), "scarto": round(float((ws[mo] - ys).abs().mean()), 4), "err": round(e2, 5)}
            ordine = sorted(cel.items(), key=lambda kv: kv[1]["err"])
            pari = len(ordine) > 1 and (ordine[1][1]["err"] - ordine[0][1]["err"]) <= SOGLIA_PARI * max(ordine[0][1]["err"], 1e-9)
            fin.append({"nome": nome, "n": int(m.sum()), "da": str(ws.index[0].date()), "a": str(ws.index[-1].date()),
                        "reale": round(float(ys.mean()), 4), "calo": round(float(ds.mean()), 4), "modelli": cel, "vince": "Pari" if pari else ordine[0][0]})
        gg = []
        for d_ in w.index[-12:][::-1]:
            cel = {mo: {"p": round(float(w.at[d_, mo]), 4), "scarto": round(float(abs(w.at[d_, mo] - yy.at[d_])), 4), "err": round(float((w.at[d_, mo] - yy.at[d_]) ** 2), 5)} for mo in presenti}
            ordine = sorted(cel.items(), key=lambda kv: kv[1]["err"])
            pari = len(ordine) > 1 and (ordine[1][1]["err"] - ordine[0][1]["err"]) <= SOGLIA_PARI * max(ordine[0][1]["err"], 1e-9)
            gg.append({"data": str(d_.date()), "evento": int(yy.at[d_]), "calo": round(float(dm.at[d_]), 4), "modelli": cel, "vince": "Pari" if pari else ordine[0][0]})
        # previsioni più recenti, ancora senza esito
        att = {}
        rec = wide[~ok]
        if len(rec):
            r = rec.iloc[-1]
            att = {"data": str(rec.index[-1].date()), "modelli": {mo: round(float(r[mo]), 4) for mo in presenti}, "n": int(len(rec))}
        out["orizzonti"][hz] = {"nome": ORIZ[hz], "soglia": thr, "finestre": fin, "giorni": gg, "attesa": att, "modelli": presenti}
        out["ultima"] = max(out["ultima"], str(w.index[-1].date()))
    return out


def _col(s: float) -> str:
    t = max(0.0, min(1.0, s / SCARTO_ROSSO))
    return f"hsl({120 * (1 - t):.0f} 70% 45% / .34)"


def _pc(x: float, d: int = 0) -> str:
    return f"{x * 100:.{d}f}%".replace(".", ",")


CSS = """<style>
.cg-sel{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.cg-sel button{border:1px solid var(--bd,#cbd5e1);background:transparent;color:inherit;border-radius:99px;padding:5px 12px;font-size:13px;cursor:pointer}
.cg-sel button.on{background:#6366f1;color:#fff;border-color:#6366f1}.cg-box{display:none}.cg-box.on{display:block}
.cg-t{width:100%;border-collapse:separate;border-spacing:2px;font-size:13px}.cg-t th{font-weight:600;text-align:center;padding:4px 3px;font-size:12px}
.cg-t td{padding:5px 4px;border-radius:6px;text-align:center;vertical-align:middle;line-height:1.25}.cg-t td.cg-h{text-align:left;background:transparent;font-weight:600}
.cg-t td small,.cg-t th small{display:block;font-weight:400;opacity:.7;font-size:11px}.cg-t td b{font-size:14px}.cg-v{font-weight:700;font-size:12px}
.cg-v i{font-style:normal;display:inline-block;padding:1px 7px;border-radius:99px;background:#6366f1;color:#fff}.cg-v i.p{background:#94a3b8}
.cg-sc{display:flex;align-items:center;gap:6px;font-size:11.5px;margin:6px 0}.cg-sc u{display:inline-block;height:8px;width:140px;border-radius:99px;background:linear-gradient(90deg,hsl(120 70% 45%/.6),hsl(60 70% 45%/.6),hsl(0 70% 45%/.6));text-decoration:none}
.cg-wr{overflow-x:auto}.cg-w{border:1px solid var(--bd,#e2e8f0);border-radius:10px;padding:6px 8px;margin:6px 0;font-size:12.5px}
@media(max-width:560px){.cg-t{font-size:12px}.cg-t td b{font-size:13px}.cg-t th small{display:none}}
</style>"""

JS = """<script>(function(){var R=document.getElementById('cgroot');if(!R||R.dataset.on)return;R.dataset.on=1;
R.addEventListener('click',function(e){var b=e.target.closest('button[data-cg]');if(!b)return;R.querySelectorAll('.cg-sel button').forEach(function(x){x.classList.toggle('on',x===b)});
R.querySelectorAll('.cg-box').forEach(function(x){x.classList.toggle('on',x.dataset.cg===b.dataset.cg)})})})();</script>"""


def _tabella_fin(o: dict, ms: list[str]) -> str:
    h = "<div class='cg-wr'><table class='cg-t'><thead><tr><th>Periodo</th><th>Realtà</th>" + "".join(f"<th>{_h.escape(m)}</th>" for m in ms) + "<th>Vince</th></tr></thead><tbody>"
    for f in o["finestre"]:
        h += (f"<tr><td class='cg-h'>{_h.escape(f['nome'])}<small>{f['n']} previsioni · fino al {f['a'][8:]}/{f['a'][5:7]}/{f['a'][:4]}</small></td>"
              f"<td><b>{_pc(f['reale'])}</b><small>calo avvenuto · peggiore medio −{_pc(abs(f['calo']), 1)}</small></td>")
        for m in ms:
            c = f["modelli"].get(m)
            h += (f"<td style='background:{_col(c['scarto'])}'><b>{_pc(c['p'])}</b><small>scarto {c['scarto'] * 100:.0f} punti</small></td>" if c else "<td>–</td>")
        v = f["vince"]
        h += f"<td class='cg-v'><i class='{'p' if v == 'Pari' else ''}'>{_h.escape(v)}</i></td></tr>"
    return h + "</tbody></table></div>"


def _tabella_giorni(o: dict, ms: list[str]) -> str:
    h = "<div class='cg-wr'><table class='cg-t'><thead><tr><th>Data previsione</th><th>Cosa è successo</th>" + "".join(f"<th>{_h.escape(m)}</th>" for m in ms) + "<th>Vince</th></tr></thead><tbody>"
    a = o.get("attesa")
    if a:
        h += (f"<tr><td class='cg-h'>{a['data'][8:]}/{a['data'][5:7]}<small>ultima, esito non ancora noto</small></td><td><small>in attesa</small></td>"
              + "".join(f"<td><b>{_pc(a['modelli'][m])}</b></td>" if m in a["modelli"] else "<td>–</td>" for m in ms) + "<td class='cg-v'><i class='p'>in attesa</i></td></tr>")
    for g in o["giorni"]:
        ev = "calo avvenuto" if g["evento"] else "nessun calo"
        h += (f"<tr><td class='cg-h'>{g['data'][8:]}/{g['data'][5:7]}/{g['data'][2:4]}</td><td><b>{'Sì' if g['evento'] else 'No'}</b><small>{ev} · peggiore −{_pc(abs(g['calo']), 1)}</small></td>"
              + "".join(f"<td style='background:{_col(g['modelli'][m]['scarto'])}'><b>{_pc(g['modelli'][m]['p'])}</b><small>scarto {g['modelli'][m]['scarto'] * 100:.0f}</small></td>" if m in g["modelli"] else "<td>–</td>" for m in ms)
              + f"<td class='cg-v'><i class='{'p' if g['vince'] == 'Pari' else ''}'>{_h.escape(g['vince'])}</i></td></tr>")
    return h + "</tbody></table></div>"


def html(d: dict | None = None) -> str:
    try:
        d = calcola() if d is None else d
    except Exception as e:  # noqa: BLE001
        print("[confronto-giorni] non calcolato:", str(e)[:100])
        return ""
    oz = d.get("orizzonti") or {}
    if not oz:
        return CSS + "<p class='mu'>La tabella comparirà dopo i primi confronti con la realtà.</p>"
    sel = "".join(f"<button type='button' data-cg='{hz}' class='{'on' if i == 0 else ''}'>{_h.escape(o['nome'])}</button>" for i, (hz, o) in enumerate(oz.items()))
    box = ""
    for i, (hz, o) in enumerate(oz.items()):
        ms = o["modelli"]
        box += (f"<div class='cg-box{' on' if i == 0 else ''}' data-cg='{hz}'><h4>Per periodo</h4>" + _tabella_fin(o, ms)
                + "<h4>Previsione per previsione (le ultime con esito noto)</h4>" + _tabella_giorni(o, ms) + "</div>")
    leg = ("<div class='explain'><p><b>Come leggere la tabella.</b> Ogni modello dice la probabilità che il mercato scenda almeno della soglia indicata. Dopo l'orizzonte si guarda cosa è successo davvero. "
           "<b>Realtà</b> = in quanti casi il calo c'è stato davvero. <b>Scarto</b> = di quanti punti percentuali la previsione era lontana da come è andata "
           "(se il calo non c'è stato e il modello diceva 10%, lo scarto è 10 punti; se c'è stato, è 90). Il colore va dal <b>verde</b> (scarto piccolo) al <b>rosso</b> (scarto grande). "
           "<b>Vince</b> chi ha l'errore medio più basso (con gli errori elevati al quadrato, come nel resto delle valutazioni); se i primi due sono a meno dell'1% di distanza, è «Pari». "
           "Un singolo giorno o una settimana dicono poco: il verdetto serio è nei periodi lunghi. FHS+VIX è il modello che prevede, Titan misura lo stato di salute, Titan+ gira solo in ombra, A1 è la seconda opinione.</p></div>"
           "<div class='cg-sc'><span>scarto piccolo</span><u></u><span>scarto grande</span></div>")
    return CSS + f"<div id='cgroot'>{leg}<div class='cg-sel'>{sel}</div>{box}<p class='md-nota'>Ultima previsione con esito noto: {_h.escape(d.get('ultima', ''))}. Si confrontano solo i giorni in cui ci sono tutti i modelli.</p></div>" + JS
