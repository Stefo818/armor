import json

import numpy as np
import pandas as pd

from armor import alerts, controlli, cosa_oggi, lungo_periodo, minimi, pagella, ribasso, stato_app


def _o(verd):
    sc = {}
    for k, (h, t) in minimi.SCALE.items():
        sc[k] = {"nome": minimi.NOMI[k], "sedute": h, "tolleranza": t, "dal_minimo": 0.0, "minimo_data": "2026-01-02", "candidato": True, "q": 0.8 if verd.get(k) == "probabile" else 0.4,
                 "q_grezza": 0.5, "r50": .01, "r80": .02, "r95": .04, "verdetto": verd.get(k, "non_ancora"), "etichetta": "verificata", "fasce": None, "copertura80": None}
    return {"data": "2026-11-12", "prezzo": 100.0, "scale": sc}


def test_ribasso_fasce_e_sott_acqua():
    assert ribasso.fascia_di(0.02) == "vicino ai massimi" and ribasso.fascia_di(0.15) == "correzione" and ribasso.fascia_di(0.45) == "crisi"
    idx = pd.bdate_range("2000-01-03", periods=900)
    v = np.concatenate([np.linspace(100, 150, 300), np.linspace(150, 90, 300), np.linspace(90, 160, 300)])
    p = pd.Series(v, index=idx)
    f = ribasso.per_fascia(p)
    assert len(f) == 5 and sum(x["giorni"] for x in f) == 900
    s = ribasso.sott_acqua(p)
    assert abs(s["calo_max"] - 0.4) < 0.01 and s["anni_piu_lungo"] > 1.0 and s["dal_massimo_oggi"] == 0.0


def test_pagella_registra_una_volta_e_misura_esiti(tmp_path, monkeypatch):
    monkeypatch.setattr(pagella, "REG", tmp_path / "reg.csv")
    o = _o({"1s": "probabile"})
    assert pagella.registra(o) == 4 and pagella.registra(o) == 0
    idx = pd.bdate_range("2026-10-01", periods=40)
    p = pd.Series(100.0 + np.arange(40) * 0.1, index=idx)   # sale sempre: ogni minimo tiene
    o["data"] = str(idx[2].date())
    monkeypatch.setattr(pagella, "REG", tmp_path / "reg2.csv")
    pagella.registra(o)
    r = pagella.riepilogo(pd.read_csv(tmp_path / "reg2.csv"), {"usd": p})
    s = r["serie"]["usd"]["1s"]["verdetti"]["probabile"]
    assert s["n"] == 1 and s["maturi"] == 1 and s["tenuto"] == 1.0
    assert r["serie"]["usd"]["1a"]["verdetti"]["non_ancora"]["maturi"] == 0   # 252 sedute non ancora passate


def test_cosa_oggi_regole():
    e = cosa_oggi.extra(_o({"1m": "probabile"}), "sana")
    assert e["livello"] == "forte"
    assert cosa_oggi.extra(_o({"1m": "probabile"}), "contrazione")["livello"] == "debole"   # in contrazione serve 3m o 1a
    assert cosa_oggi.extra(_o({"1a": "probabile"}), "contrazione")["livello"] == "forte"
    assert cosa_oggi.extra(_o({}), "sana")["livello"] == "nessuna"
    assert cosa_oggi.cautela("persistente", "sana", 0.02, False)["livello"] == "alta"
    assert cosa_oggi.cautela("normale", "contrazione", 0.02, True)["livello"] == "bassa"
    assert cosa_oggi.cautela("normale", "sana", 0.15, False)["livello"] == "alta"
    h = cosa_oggi.html(_o({}), None, {"nome": "Espansione sana", "codice": "sana"}, "normale", 0.02)
    assert "Cosa fare oggi" in h and "Continua come sempre" in h


def test_controlli_file_rotti(tmp_path):
    (tmp_path / "series").mkdir()
    (tmp_path / "minimi_oggi.json").write_text("{rotto", encoding="utf-8")
    gravi, avvisi = controlli.verifica(base=tmp_path)
    assert any("minimi_oggi.json" in g for g in gravi)
    (tmp_path / "minimi_oggi.json").write_text("{}", encoding="utf-8")
    gravi, _ = controlli.verifica(base=tmp_path)
    assert not any("minimi_oggi.json" in g for g in gravi)


def test_stato_app_html():
    righe = [{"key": "sp500", "name": "S&P 500", "last": "2026-11-12", "age": 2, "light": "ok", "msg": "", "ok": True},
             {"key": "x", "name": "Fonte ferma", "last": "2026-10-01", "age": 40, "light": "ba", "msg": "", "ok": False}]
    h = stato_app.html(righe, [{"nome": "Radar", "data": "2026-11-12", "eta": 1, "luce": "ok"}], {"ok": True, "righe": 10, "errore": None})
    assert "1 cose da controllare" in h and "Fonte ferma" in h and "catena valida" in h


def test_avviso_minimo_probabile_solo_al_cambio():
    pred = {}
    st = {}
    m1, st = alerts.detect(st, pred, None, None, None, None, "2026-11-12", minimi=_o({"3m": "probabile"}), fase="Espansione sana")
    assert any("Minimo probabile a 3 mesi" in m["title"] for m in m1)
    m2, st = alerts.detect(st, pred, None, None, None, None, "2026-11-13", minimi=_o({"3m": "probabile"}), fase="Espansione sana")
    assert not any("Minimo probabile" in m["title"] for m in m2)
    m3, _ = alerts.detect(st, pred, None, None, None, None, "2026-11-14", minimi=_o({}), fase="Rischio di contrazione lunga")
    assert any("fase di lungo periodo" in m["title"] for m in m3)


def test_variante_tassi_confronto_su_dati_finti():
    rng = np.random.default_rng(3)
    idx = pd.date_range("1880-01-31", periods=1500, freq="ME")
    cape = np.exp(np.cumsum(rng.normal(0, .03, len(idx))) * 0.3 + 2.7)
    idxv = np.cumprod(1 + rng.normal(0.004, .04, len(idx)))
    df = pd.DataFrame({"idx": idxv, "cape": cape, "tr": rng.normal(.02, .01, len(idx))}, index=idx)
    r = lungo_periodo.confronta_b(df, 5)
    assert {"r2_a_prima", "r2_b_dopo", "delta_prima", "adottata"} <= set(r) and isinstance(r["adottata"], bool)
    p = lungo_periodo.previsione_b(df, 5, 25.0, 0.01)
    assert p["p10"] < p["p90"]
