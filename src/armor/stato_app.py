# -*- coding: utf-8 -*-
"""Pagina «Stato dell'app»: i dati chiave sono aggiornati? i calcoli di oggi sono stati fatti? il diario è integro?"""
import html as _h
import json
from datetime import date

import pandas as pd

from . import salute
from .config import DATA

# (nome mostrato, file, come leggere la data dentro il file, giorni oltre i quali il calcolo è «vecchio»)
CALCOLI = [("Radar dei minimi (S&P 500)", "minimi_oggi.json", ("json", "data"), 5), ("Radar dei minimi (VWCE in euro)", "minimi_eur_oggi.json", ("json", "data"), 5),
           ("Tipo di ribasso", "ribasso.json", ("json", "data"), 5), ("Lungo periodo", "lungo_periodo.json", ("json", "asof"), 5),
           ("Pagella dei segnali", "pagella_minimi.json", ("json", "fine"), 5), ("Indice Occasione", "occasione.json", ("json", "data"), 5),
           ("Semaforo del rischio", "semaforo_rischio_oggi.json", ("json", "data"), 7), ("Valutazione dei modelli", "model_eval.json", ("mtime", None), 45)]


def _data_file(nome: str, how: tuple) -> str | None:
    f = DATA / nome
    if not f.exists():
        return None
    try:
        if how[0] == "json":
            d = json.loads(f.read_text(encoding="utf-8")).get(how[1])
            if d:
                return str(d)[:10]
    except Exception:  # noqa: BLE001
        pass
    return str(pd.Timestamp(f.stat().st_mtime, unit="s").date())


def calcoli(oggi: date | None = None) -> list[dict]:
    oggi = pd.Timestamp(oggi or date.today())
    out = []
    for nome, f, how, lim in CALCOLI:
        d = _data_file(f, how)
        if d is None:
            out.append({"nome": nome, "data": None, "eta": None, "luce": "na"})
            continue
        eta = (oggi - pd.Timestamp(d)).days
        out.append({"nome": nome, "data": d, "eta": eta, "luce": "ok" if eta <= lim else "ba"})
    return out


def diario() -> dict:
    try:
        from . import journal3
        ok, n, err = journal3.verifica_estrema()
        return {"ok": bool(ok), "righe": n, "errore": err}
    except Exception as e:  # noqa: BLE001
        return {"ok": None, "righe": 0, "errore": type(e).__name__}


LUCE = {"ok": ("ok", "aggiornato"), "ba": ("bad", "fermo"), "na": ("warn", "n/d"), "wa": ("warn", "in ritardo")}


def _riga(nome, data, eta, luce, nota=""):
    k, t = LUCE.get(luce, LUCE["na"])
    d = "—" if not data else f"{data[8:10]}/{data[5:7]}/{data[:4]}"
    e = "" if eta is None else f"{eta} gg fa"
    return f"<tr><td>{_h.escape(nome)}</td><td>{d}</td><td>{e}</td><td><span class='badge {k}'>{t}</span> <span class='small'>{_h.escape(nota)}</span></td></tr>"


def html(righe_dati: list[dict] | None = None, calc: list[dict] | None = None, dia: dict | None = None) -> str:
    righe_dati = salute.compute() if righe_dati is None else righe_dati
    calc = calcoli() if calc is None else calc
    dia = diario() if dia is None else dia
    tot = len(righe_dati) + len(calc) + 1
    bad = [r["name"] for r in righe_dati if r["light"] == "ba"] + [c["nome"] for c in calc if c["luce"] == "ba"] + ([] if dia.get("ok") in (True, None) else ["Diario delle previsioni"])
    hero_k = "" if not bad else "b"
    hero_t = "Tutto aggiornato" if not bad else f"{len(bad)} cose da controllare"
    hero_d = (f"Controllati {tot} elementi: dati, calcoli di oggi e diario delle previsioni." if not bad else "Da controllare: " + ", ".join(_h.escape(x) for x in bad[:8]) + ("…" if len(bad) > 8 else "") + ".")
    css = ("<style>.sa .hero{border-radius:18px;padding:16px 20px;border:1px solid var(--bd);background:linear-gradient(135deg,var(--card),var(--okbg));margin-bottom:12px}"
           ".sa .hero.b{background:linear-gradient(135deg,var(--card),var(--badbg))}.sa .hero b.big{font-size:21px;display:block;margin-bottom:4px}"
           ".sa table{width:100%;border-collapse:collapse;font-size:13.5px}.sa td,.sa th{padding:7px 8px;border-bottom:1px solid var(--bd);text-align:left}.sa th{font-size:12px;color:var(--mu)}"
           ".sa .small{font-size:12px;color:var(--mu)}.sa .scroll{overflow-x:auto}</style>")
    dk = {True: ("ok", "catena valida"), False: ("bad", "catena rotta"), None: ("warn", "non controllabile")}[dia.get("ok")]
    return (css + "<div class='sa'><h2>Stato dell'app</h2>"
            f"<div class='hero {hero_k}'><b class='big'>{hero_t}</b>{hero_d}</div>"
            "<p class='small'>Chiave di lettura: «aggiornato» = l'ultimo dato è recente rispetto a quanto è normale per quella fonte (i dati di mercato sono giornalieri, quelli economici mensili). «Fermo» = da controllare: le stime che li usano sono meno affidabili.</p>"
            "<h3>Dati chiave</h3><div class='card scroll'><table><tr><th>Fonte</th><th>Ultimo dato</th><th>Età</th><th>Stato</th></tr>"
            + "".join(_riga(r["name"], r.get("last"), r.get("age"), r["light"], r.get("msg", "")) for r in righe_dati) + "</table></div>"
            "<h3>Calcoli di oggi</h3><div class='card scroll'><table><tr><th>Calcolo</th><th>Data</th><th>Età</th><th>Stato</th></tr>"
            + "".join(_riga(c["nome"], c["data"], c["eta"], c["luce"]) for c in calc) + "</table></div>"
            f"<h3>Diario delle previsioni</h3><div class='card'><span class='badge {dk[0]}'>{dk[1]}</span> <span class='small'>{dia.get('righe', 0)} righe controllate. Ogni riga è legata alla precedente: se qualcuno la modifica, la catena si rompe e l'app lo segnala.</span></div></div>")
