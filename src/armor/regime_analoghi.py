"""Periodi analoghi del passato per il Regime di tensione (Patch 77).
Si prendono le medie dell'Indice Armor di oggi su 4 finestre (ultimi 7 giorni = 5 sedute, 1 mese = 21, 3 mesi = 63, 6 mesi = 126 sedute di Borsa)
e si cercano nella storia (dal 2000) le date in cui le stesse quattro medie erano le più simili. Per ogni periodo trovato si guarda cosa ha fatto l'S&P 500 nei 6 mesi dopo.
Regole: si usano solo date i cui 6 mesi successivi sono già finiti (nessun «futuro»); i periodi scelti distano almeno 63 sedute l'uno dall'altro, così non sono lo stesso episodio ripetuto.
Sono frequenze storiche su pochi episodi, non previsioni."""
import html as _h
import numpy as np
import pandas as pd

from . import store
from .features import closed_sp500, fwd_maxdd, fwd_ret

FINESTRE = (("m7", 5, "Ultimi 7 giorni", "5 sedute"), ("m1", 21, "Ultimo mese", "21 sedute"), ("m3", 63, "Ultimi 3 mesi", "63 sedute"), ("m6", 126, "Ultimi 6 mesi", "126 sedute"))
ORIZZ = 126
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _zona(x: float) -> tuple[str, str]:
    return ("calma", "#16a34a") if x < 35 else ("normale", "#64748b") if x < 45 else ("tensione", "#d97706") if x < 55 else ("tensione alta", "#dc2626")


def calcola(a: pd.Series | None = None, p: pd.Series | None = None, k: int = 6, sep: int = 63) -> dict | None:
    try:
        a = store.load("armor_index") if a is None else a
        p = closed_sp500() if p is None else p
        a = a.dropna()
        a = a[~a.index.duplicated(keep="last")].sort_index()
        pp = p.reindex(a.index).ffill()
        n = len(a)
        if n < 126 + ORIZZ + 200:
            return None
        M = pd.DataFrame({c: a.rolling(w).mean() for c, w, _, _ in FINESTRE})
        oggi = M.iloc[-1]
        pos = np.arange(n)
        mature = (pos >= 125) & (pos <= n - 1 - ORIZZ)
        sd = M[mature].std().replace(0, 1.0)
        dist = np.sqrt((((M - oggi) / sd) ** 2).mean(axis=1)).where(mature)
        r6, dd6 = fwd_ret(pp, ORIZZ), fwd_maxdd(pp, ORIZZ)
        scelti: list[int] = []
        for i in np.argsort(dist.fillna(1e9).values):
            if not mature[i]:
                continue
            if all(abs(i - j) >= sep for j in scelti):
                scelti.append(int(i))
            if len(scelti) >= k:
                break
        lista = []
        for i in sorted(scelti, key=lambda i: dist.iloc[i]):
            d = a.index[i]
            sp = (pp.iloc[i - 63:i + ORIZZ + 1] / pp.iloc[i] * 100).values[::3]
            lista.append({"data": str(d.date()), "somiglianza": float(100 * max(0.0, 1 - dist.iloc[i] / 0.4)),
                          "medie": {c: float(M[c].iloc[i]) for c, *_ in FINESTRE},
                          "r1": float(pp.iloc[i + 21] / pp.iloc[i] - 1), "r3": float(pp.iloc[i + 63] / pp.iloc[i] - 1), "r6": float(r6.iloc[i]), "dd6": float(dd6.iloc[i]),
                          "spark": [round(float(x), 1) for x in sp], "marker": 21})
        if not lista:
            return None
        m = mature & r6.notna().values
        base = {"dd10": float((dd6[m] <= -0.10).mean()), "neg": float((r6[m] < 0).mean()), "r6_med": float(r6[m].median())}
        agg = {"n": len(lista), "dd10": int(sum(x["dd6"] <= -0.10 for x in lista)), "neg": int(sum(x["r6"] < 0 for x in lista)), "r6_med": float(np.median([x["r6"] for x in lista]))}
        medie = {}
        for c, w, nome, sed in FINESTRE:
            s = M[c].dropna()
            medie[c] = {"v": float(oggi[c]), "pct": float((s <= oggi[c]).mean() * 100), "nome": nome, "sedute": sed}
        dif = float(oggi["m7"] - oggi["m6"])
        return {"data": str(a.index[-1].date()), "dal": str(a.index[0].date()), "medie": medie, "direzione": "salita" if dif > 3 else "discesa" if dif < -3 else "stabile", "dif": dif,
                "analoghi": lista, "agg": agg, "base": base}
    except Exception as e:  # noqa: BLE001
        print("Periodi analoghi non calcolati:", str(e)[:100], flush=True)
        return None


def _it(d: str) -> str:
    return f"{MESI[int(d[5:7]) - 1]} {d[:4]}"


def _pc(x: float, segno: bool = False) -> str:
    if round(x * 100) == 0:
        return "0%"
    return (f"{x * 100:+.0f}%" if segno else f"{x * 100:.0f}%").replace("-", "−")


def _spark(x: dict) -> str:
    s, mk = x["spark"], x["marker"]
    lo, hi = min(s + [100]), max(s + [100])
    W, H = 300, 74
    X = lambda i: i / (len(s) - 1) * W  # noqa: E731
    Y = lambda v: H - 6 - (v - lo) / ((hi - lo) or 1) * (H - 12)  # noqa: E731
    pts = lambda r: " ".join(f"{X(i):.1f},{Y(s[i]):.1f}" for i in r)  # noqa: E731
    col = "#16a34a" if x["r6"] >= 0 else "#dc2626"
    return (f"<svg viewBox='0 0 {W} {H}' class='an-sp' preserveAspectRatio='none'><line x1='0' x2='{W}' y1='{Y(100):.1f}' y2='{Y(100):.1f}' stroke='currentColor' opacity='.25' stroke-dasharray='3 3'/>"
            f"<polyline points='{pts(range(0, mk + 1))}' fill='none' stroke='#94a3b8' stroke-width='2' vector-effect='non-scaling-stroke'/>"
            f"<polyline points='{pts(range(mk, len(s)))}' fill='none' stroke='{col}' stroke-width='2.5' vector-effect='non-scaling-stroke'/>"
            f"<line x1='{X(mk):.1f}' x2='{X(mk):.1f}' y1='0' y2='{H}' stroke='currentColor' opacity='.5'/></svg>")


def _esito(v: float) -> str:
    c = "#16a34a" if v >= 0 else "#dc2626"
    return f"<b style='color:{c}'>{_pc(v, True)}</b>"


def html(d: dict | None) -> str:
    if not d:
        return "<p class='an-t'>Il confronto con i periodi del passato compare quando c'è abbastanza storia dell'Indice Armor.</p>"
    E = _h.escape
    tiles = ""
    for c, *_ in FINESTRE:
        m = d["medie"][c]
        z, col = _zona(m["v"])
        tiles += (f"<div class='an-tile' style='border-top:4px solid {col}'><small>{E(m['nome'])}</small><b style='color:{col}'>{m['v']:.0f}</b><em>{z}</em>"
                  f"<div class='an-pb'><i style='width:{m['pct']:.0f}%;background:{col}'></i></div><span>più alta del {m['pct']:.0f}% dei giorni dal {d['dal'][:4]}</span></div>")
    dirz = {"salita": ("▲", "#dc2626", f"La media recente ({d['medie']['m7']['v']:.0f}) è più alta di quella a 6 mesi ({d['medie']['m6']['v']:.0f}): la tensione sta <b>salendo</b>."),
            "discesa": ("▼", "#16a34a", f"La media recente ({d['medie']['m7']['v']:.0f}) è più bassa di quella a 6 mesi ({d['medie']['m6']['v']:.0f}): la tensione sta <b>scendendo</b>."),
            "stabile": ("=", "#64748b", f"La media recente ({d['medie']['m7']['v']:.0f}) è vicina a quella a 6 mesi ({d['medie']['m6']['v']:.0f}): la tensione è <b>stabile</b>.")}[d["direzione"]]
    sezione1 = (f"<h4 class='an-h'>La tensione in media: 4 orizzonti</h4><div class='an-tiles'>{tiles}</div>"
                f"<div class='an-dir'><i style='color:{dirz[1]}'>{dirz[0]}</i><span>{dirz[2]}</span></div>"
                "<p class='an-t'>Ogni riquadro è la <b>media dell'Indice Armor</b> (0–100) nelle ultime sedute di Borsa aperta consecutive. Il colore dice se quella media è in calma, normale o tensione; "
                "la barra dice quanto è alta rispetto a tutta la storia.</p>")
    ag, base = d["agg"], d["base"]
    cards = ""
    for x in d["analoghi"]:
        mini = "".join(f"<span>{lab}<b>{x['medie'][c]:.0f}</b></span>" for c, lab in (("m7", "7g"), ("m1", "1m"), ("m3", "3m"), ("m6", "6m")))
        cards += (f"<div class='an-card'><div class='an-ch'><b>{_it(x['data'])}</b><span class='an-sim'><i style='width:{x['somiglianza']:.0f}%'></i></span><em>{x['somiglianza']:.0f}% simile</em></div>"
                  f"<div class='an-mini'>Medie di allora: {mini}</div>{_spark(x)}"
                  "<div class='an-leg'><span>◄ 3 mesi prima</span><span>giorno analogo</span><span>6 mesi dopo ►</span></div>"
                  f"<div class='an-out'><div>Dopo 1 mese<br>{_esito(x['r1'])}</div><div>Dopo 3 mesi<br>{_esito(x['r3'])}</div><div>Dopo 6 mesi<br>{_esito(x['r6'])}</div>"
                  f"<div>Peggior calo<br><b style='color:#dc2626'>{_pc(x['dd6'])}</b></div></div></div>")
    pallini = "".join(f"<i style='background:{'#dc2626' if x['dd6'] <= -0.10 else '#16a34a'}'></i>" for x in d["analoghi"])
    lettura = (f"<div class='an-ver'><div class='an-dots'>{pallini}</div><div><b>In {ag['dd10']} {'periodo simile' if ag['dd10'] == 1 else 'periodi simili'} su {ag['n']}</b> l'S&amp;P 500 ha perso almeno il 10% nei 6 mesi dopo "
               f"(media storica su tutti i giorni dal 2000: {_pc(base['dd10'])} delle volte). Alla fine dei 6 mesi era sceso in {ag['neg']} {'caso' if ag['neg'] == 1 else 'casi'} su {ag['n']}; risultato mediano {_pc(ag['r6_med'], True)} "
               f"(mediana storica su tutti i giorni: {_pc(base['r6_med'], True)}).</div></div>")
    sezione2 = ("<h4 class='an-h'>Quando la tensione era così, in passato</h4>"
                "<p class='an-t'>Abbiamo cercato nella storia i giorni in cui le <b>quattro medie</b> erano più simili a quelle di oggi, scegliendo periodi distinti (almeno 3 mesi uno dall'altro). "
                "Ecco cosa ha fatto l'S&amp;P 500 dopo. Il grafico: linea grigia = i 3 mesi prima, linea verde o rossa = i 6 mesi dopo (verde = chiuso in positivo, rosso = in negativo); la linea tratteggiata è il livello del giorno analogo.</p>"
                f"<div class='an-cards'>{cards}</div>{lettura}"
                "<p class='an-t'><b>Attenzione:</b> sono pochi episodi e il passato non si ripete uguale. È un'indicazione di contesto, non una previsione né un consiglio di comprare o vendere.</p>")
    info = ("<details class='an-info'><summary><i>i</i> Come funziona il confronto con il passato</summary><div>"
            "<p><b>1.</b> Si calcola la media dell'Indice Armor su 5, 21, 63 e 126 sedute di Borsa (circa 7 giorni, 1 mese, 3 mesi, 6 mesi).</p>"
            "<p><b>2.</b> Per ogni giorno del passato (dal 2000) si calcolano le stesse quattro medie e si misura quanto sono lontane da quelle di oggi (ogni media pesa uguale, "
            "misurata in «quanto è normale che varî»). Più la distanza è piccola, più il giorno è simile.</p>"
            "<p><b>3.</b> Si tengono i 6 giorni più simili che distano tra loro almeno 63 sedute, così non sono lo stesso episodio contato più volte. "
            "Si escludono gli ultimi 6 mesi, perché di quei giorni non si sa ancora cosa è successo dopo.</p>"
            "<p><b>4.</b> Per ciascuno si misura cosa ha fatto l'S&amp;P 500 dopo 1, 3 e 6 mesi e il peggior calo dei 6 mesi, poi si confronta con la media storica di tutti i giorni dal 2000.</p></div></details>")
    return CSS + sezione1 + sezione2 + info


CSS = """<style>
.an-h{margin:18px 0 6px;font-size:15px}.an-t{font-size:12.5px;line-height:1.5;color:var(--mu);margin:6px 0}.an-t b{color:var(--tx)}
.an-tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}@media(max-width:560px){.an-tiles{grid-template-columns:1fr 1fr}}
.an-tile{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:8px 10px;text-align:center}.an-tile small{display:block;font-size:11.5px;color:var(--mu)}
.an-tile b{display:block;font-size:34px;line-height:1.1;font-weight:800}.an-tile em{font-style:normal;font-size:12px;font-weight:700}.an-tile span{display:block;font-size:10.5px;color:var(--mu);line-height:1.3;margin-top:4px}
.an-pb{height:6px;border-radius:99px;background:var(--bd);margin-top:6px;overflow:hidden}.an-pb i{display:block;height:100%;border-radius:99px}
.an-dir{display:flex;gap:10px;align-items:center;margin:10px 0;border:1px dashed var(--bd);border-radius:12px;padding:8px 12px;font-size:13.5px}.an-dir i{font-style:normal;font-size:22px;font-weight:800}
.an-cards{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:560px){.an-cards{grid-template-columns:1fr}}
.an-card{background:var(--bg);border:1px solid var(--bd);border-radius:14px;padding:10px 12px}.an-ch{display:flex;align-items:center;gap:8px;font-size:15px}.an-ch em{font-style:normal;font-size:11.5px;color:var(--mu);white-space:nowrap}
.an-sim{flex:1;height:7px;border-radius:99px;background:var(--bd);overflow:hidden}.an-sim i{display:block;height:100%;background:var(--tx);opacity:.6}
.an-mini{font-size:11.5px;color:var(--mu);margin:6px 0}.an-mini span{margin-left:8px}.an-mini b{color:var(--tx);margin-left:3px}
.an-sp{width:100%;height:74px;color:var(--tx);display:block}.an-leg{display:flex;justify-content:space-between;font-size:10px;color:var(--mu);margin-top:2px}
.an-out{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;text-align:center;font-size:11px;color:var(--mu);margin-top:8px;line-height:1.4}.an-out b{font-size:14px}
.an-ver{display:flex;gap:12px;align-items:center;background:var(--bg);border:1px solid var(--bd);border-radius:14px;padding:10px 12px;margin:10px 0;font-size:13.5px;line-height:1.5}
.an-dots{display:grid;grid-template-columns:repeat(3,16px);gap:4px}.an-dots i{width:16px;height:16px;border-radius:50%}
.an-info{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;margin:10px 0 0;font-size:13px;line-height:1.5}.an-info summary{cursor:pointer;font-weight:700}
.an-info summary i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;border-radius:50%;background:var(--tx);color:var(--bg);font-style:normal;font-size:12px;margin-right:6px}.an-info p{margin:8px 0}
</style>"""
