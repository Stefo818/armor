"""Comandi di Armor: python -m armor <comando>.  'tutto' fa l'aggiornamento giornaliero completo."""
import sys
from datetime import datetime

import pandas as pd

from .config import PRIMARY

from . import journal, sources, store
from .config import DATA, MODEL_VERSION
from .features import closed_sp500, vwce_series
from .model import Engine


def forecast(write: bool = True) -> dict:
    """Calcola le stime di oggi (ultima seduta chiusa) e le registra nel diario."""
    p = closed_sp500()
    from .autoimprove import champion_engine
    eng, mid = champion_engine(p)
    t = eng.F.index[-1]
    fitted = eng.fit(t)
    pred = eng.predict(fitted, t)
    v = vwce_series()
    spot = float(v.reindex([t], method="ffill").iloc[0]) if not v.empty else float("nan")
    n = journal.append(t.strftime("%Y-%m-%d"), spot, pred, model=mid) if write else 0
    print(f"Previsioni del {t.date()}: {n} nuove righe nel diario")
    if write:
        try:   # 4.1 modalita' ombra: i motori sfidanti scrivono nel diario a parte (non influenzano l'app)
            from . import shadow
            shadow.run(p, t, pred, spot)
        except Exception as e:  # noqa: BLE001
            print("[ombra] errore:", str(e)[:100])
    return {"date": t, "pred": pred, "spot": spot, "eng": eng, "fitted": fitted, "model": mid}


def daily_extras(ctx: dict, fetch_news: bool = True) -> None:
    """Notizie, analisi giornaliera e riga del registro. Ogni passo e' protetto: se uno fallisce, gli altri continuano."""
    from . import analysis, live, news, registry, valuations
    from .guard import with_timeout
    from .report import INDICATORS
    nws = news.load_latest()
    if fetch_news and nws.get("model") == "FinBERT":
        try:  # notizie gia' analizzate con FinBERT da poche ore: non si rifanno (il workflow delle notizie ha il modello, quello giornaliero potrebbe no)
            age = (datetime.utcnow() - datetime.strptime(nws["fetched"], "%Y-%m-%dT%H:%M:%SZ")).total_seconds() / 3600
            if age < 6:
                fetch_news = False
        except Exception:  # noqa: BLE001
            pass
    if fetch_news:
        try:
            nws = with_timeout(news.run, 360, "notizie")
        except Exception as e:  # noqa: BLE001
            print("Notizie non scaricate:", str(e)[:100])
    try:
        rep = analysis.generate(ctx["date"], ctx["pred"], ctx["spot"], closed_sp500(), live.load(), nws, valuations.current())
        analysis.save(rep)
        print("Analisi giornaliera salvata:", rep["date"], len(rep["html"]), "caratteri")
    except Exception as e:  # noqa: BLE001
        print("Analisi giornaliera non riuscita:", str(e)[:150])
    try:
        from . import calendario, holdings
        holdings.refresh()
        ev = with_timeout(lambda: calendario.fetch_earnings(dict(news.TOP20)), 120, "trimestrali")
        import json as _j
        (DATA / "calendar.json").write_text(_j.dumps(ev, ensure_ascii=False), encoding="utf-8")
        print("Trimestrali trovate:", len(ev))
    except Exception as e:  # noqa: BLE001
        print("Calendario/composizione non aggiornati:", str(e)[:100])
    try:
        daily_report(ctx, nws)
    except Exception as e:  # noqa: BLE001
        print("Bilancio non generato:", str(e)[:100])
    try:
        run_alerts(ctx)
    except Exception as e:  # noqa: BLE001
        print("Avvisi non elaborati:", str(e)[:100])
    try:
        extra = {}
        try:
            from . import armor_index, outlook
            sp_ = closed_sp500()
            mat = outlook.probability_matrix(sp_)
            extra["modello"] = ctx.get("model", "")
            for hz in mat:
                u = mat[hz]["up"][PRIMARY[hz]]
                extra[f"pup_{hz}"] = round(u["p"], 5)
                extra[f"bup_{hz}"] = round(u["base"], 5)
                for thr, c in mat[hz]["down"].items():
                    extra[f"dn_{hz}_{thr}"] = round(c["p"], 5)
                for thr, c in mat[hz]["up"].items():
                    extra[f"up_{hz}_{thr}"] = round(c["p"], 5)
            try:   # scenari a 3 mesi: media degli indicatori (stessa definizione della pagina Previsioni)
                sg = [x for x in outlook.signal_table(sp_) if x.get("scen") and x["scen"][0] == x["scen"][0]]
                if sg:
                    for i in range(5):
                        extra[f"scen3m_{i}"] = round(float(sum(x["scen"][i] for x in sg) / len(sg)), 5)
            except Exception as e:  # noqa: BLE001
                print("[registro] scenari non salvati:", str(e)[:80])
            aix = armor_index.compute(sp_)
            if aix:
                armor_index.save_history(aix)
                extra["armor_index"] = round(aix["value"], 2)
                for g in aix["groups"]:
                    if g["score"] is not None:
                        extra["aix_" + g["name"].split()[0].lower()] = round(g["score"], 4)
        except Exception as e:  # noqa: BLE001
            print("Probabilità di rialzo / Indice Armor non salvati:", str(e)[:100])
        row = registry.row_for(ctx["date"], ctx["pred"], INDICATORS, ctx["spot"], news.summary(nws), extra)
        miss = registry.check(row)
        if miss:
            print(f"[registro] colonne mancanti ({len(miss)}): {', '.join(miss[:8])}{'...' if len(miss) > 8 else ''}", flush=True)
        n = registry.append(row)
        print("Registro dati:", n, "giorni")
    except Exception as e:  # noqa: BLE001
        print("Registro non aggiornato:", str(e)[:150])


def daily_report(ctx: dict, nws: dict | None, force_week: bool = False) -> None:
    """Bilancio del giorno (e, il venerdi', rapporto settimanale): salvati per la pagina e inviati come avviso."""
    import json as _j
    from . import alerts, bilancio, regime, semafori
    p = closed_sp500()
    sem = semafori.compute(p, __import__("armor.live", fromlist=["x"]).load())
    reg = regime.compute(p)["nome"]
    prev = alerts._load().get("levels")
    d = bilancio.day_summary(ctx["pred"], prev, reg, nws, semaforo=semafori.overall(sem))
    bilancio.REPORTS.mkdir(parents=True, exist_ok=True)
    (bilancio.REPORTS / "bilancio-latest.json").write_text(_j.dumps(d, ensure_ascii=False), encoding="utf-8")
    # nessun avviso quotidiano del bilancio (3.4): l'app lo mostra; l'avviso parte solo per i cambiamenti importanti
    if force_week or datetime.now().weekday() == 4:
        w = bilancio.weekly(ctx["pred"], reg, sem)
        bilancio.weekly_save(w)
        alerts.queue({"title": "Rapporto settimanale pronto", "tags": ["newspaper"],
                      "message": "\n".join(["Da guardare la prossima settimana:"] + [f"{i + 1}. {x}" for i, x in enumerate(w["watch"][:3])])})
        print("Rapporto settimanale salvato")
    try:   # 4.4 rapporto mensile: il 1 del mese (o alla prima esecuzione utile dopo)
        from . import rapporto
        m = rapporto.run(p, force=False)
        if m and m.get("nuovo"):
            alerts.queue(rapporto.message(m))
            print("Rapporto mensile salvato:", m["mese"])
    except Exception as e:  # noqa: BLE001
        print("Rapporto mensile non generato:", str(e)[:100])


def mattina() -> None:
    from . import alerts, bilancio, live
    try:
        live.run()
    except Exception as e:  # noqa: BLE001
        print("Prezzi non aggiornati:", str(e)[:80])
    m = bilancio.morning_message()
    print(m["message"] if m else "Niente da segnalare stamattina")
    if m and bilancio.important_today():   # 3.4: l'agenda parte come notifica solo se oggi c'e' un evento importante
        alerts.notify_once([m])


def run_alerts(ctx: dict) -> None:
    from . import alerts, calendario, live, regime
    r = regime.compute(closed_sp500())
    vx = store.load("vix")
    vix = float(vx.iloc[-1]) if len(vx) else None
    q = live.load().get("quotes", {})
    lv = q.get("vix") or {}
    if lv.get("price"):
        vix = float(lv["price"])
    move = (q.get("vwce") or {}).get("chg")
    ev = calendario.next_big(calendario.events(days=7))
    aix_band, div = None, None
    try:
        from . import armor_index, extra13
        sp_ = closed_sp500()
        aix = armor_index.compute(sp_)
        if aix:
            aix_band = armor_index.band(aix["value"])[0]
            d = extra13.divergence(sp_, aix)
            div = bool(d["active"]) if d else None
    except Exception as e:  # noqa: BLE001
        print("[avvisi] indice/divergenza non disponibili:", str(e)[:80])
    alerts.run(ctx, r["nome"], vix, ev, move * 100 if move is not None else None, aix_band, div)


def fonti_nuove(force: bool = False) -> None:
    """Salute delle aziende, inflazione, liquidità, Europa, storia lunga (PIANO_MODELLO §3) e revisioni degli utili.
    Ogni passo ha un tempo massimo: se una fonte non risponde, il ciclo giornaliero continua."""
    from . import fondamentali
    from .guard import with_timeout
    try:
        st = with_timeout(lambda: fondamentali.aggiorna_fonti(store.read_status(), force), 300 if force else 240, "fonti lente")
        store.write_status(st)
    except Exception as e:  # noqa: BLE001
        print("[fondamentali] fonti lente non aggiornate:", str(e)[:120])
    try:
        with_timeout(fondamentali.raccogli_revisioni, 90, "revisioni utili")
    except Exception as e:  # noqa: BLE001
        print("[fondamentali] revisioni utili non raccolte:", str(e)[:120])


def tutto(skip_download: bool = False) -> None:
    if not skip_download:
        from .guard import with_timeout
        try:
            st = with_timeout(sources.update_all, 840, "download dati")
        except TimeoutError as ex:
            print("ATTENZIONE:", ex)
            st = store.read_status()
        bad = [k for k, v in st.items() if not v["ok"]]
        print(f"Dati aggiornati. Fonti con problemi: {', '.join(bad) if bad else 'nessuna'}")
        try:
            from .archive import archive_spy_options
            print("Archivio opzioni SPY:", with_timeout(archive_spy_options, 240, "opzioni SPY"))
        except Exception as e:  # noqa: BLE001
            print("Archivio opzioni SPY non riuscito:", str(e)[:120])
        fonti_nuove()
    try:   # serie derivate (crescita utili, inflazione annua, liquidità Fed, forza relativa...): veloce, anche senza download
        from . import fondamentali
        fondamentali.aggiorna_derivate()
    except Exception as e:  # noqa: BLE001
        print("[fondamentali] derivate non calcolate:", str(e)[:120])
    try:
        from . import live
        live.run()
    except Exception as e:  # noqa: BLE001
        print('Prezzi live non scaricati:', str(e)[:100])
    ctx = forecast()
    daily_extras(ctx)
    n = journal.update_outcomes(vwce_series(), closed_sp500())
    print(f"Esiti verificati a scadenza: {n}")
    try:
        from . import learning
        t = learning.update(closed_sp500())
        print(f"[apprendimento] confronti con la realtà aggiornati: {len(t)} righe")
    except Exception as e:  # noqa: BLE001
        print("[apprendimento] non aggiornato:", str(e)[:100])
    ok, msg = journal.verify()
    print("Integrita' diario:", msg if ok else "ERRORE - " + msg)
    from .report import build
    build(ctx)


def costruisci_sito(live_first: bool = False) -> None:
    """Cartella site/ pronta per GitHub Pages: pagina, prezzi live, file dell'app per telefono."""
    import shutil
    from . import live
    from .config import ROOT
    from .report import build
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    try:   # se i rapporti P/E e P/S non sono ancora stati salvati (es. dopo un salvataggio fallito), si provano a leggere subito
        if store.load("val_pe_vwce").empty or store.load("val_pe_ndx").empty:
            from . import valuations
            from .guard import with_timeout
            res = with_timeout(valuations.snapshot, 150, "valutazioni")
            for sid, ser in (res or {}).items():
                store.upsert(sid, ser)
    except Exception as e:  # noqa: BLE001
        print("[valuations] non lette dal sito:", str(e)[:100])
    build(forecast(write=False), out=site / "index.html", lazy=True)
    if live.LIVE_FILE.exists():
        shutil.copy(live.LIVE_FILE, site / "live.json")
    for f in (ROOT / "web").glob("*"):
        shutil.copy(f, site / f.name)
    (site / ".nojekyll").write_text("")
    print("Sito pronto in", site)


def stampa_stato(st: dict) -> None:
    """Stampa l'esito di ogni fonte (da incollare a Claude se qualcosa non va)."""
    for k, v in sorted(st.items(), key=lambda kv: (kv[1]["ok"], kv[0])):
        flag = "OK " if v["ok"] else "ERR"
        print(f"{flag} {k:12s} ultima data: {v['last_date']}  righe: {v['rows']:>6}  {v['msg']}")


def diagnosi() -> None:
    stampa_stato(sources.update_all(full=False))


def main() -> None:
    import faulthandler
    faulthandler.dump_traceback_later(600, repeat=True)   # se qualcosa si blocca, il log mostra dove
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tutto"
    if cmd == "tutto":
        tutto()
        import os
        sys.stdout.flush()
        os._exit(0)   # chiusura immediata: nessun thread di rete bloccato può tenere vivo il programma
    elif cmd == "senza-download":
        tutto(skip_download=True)
    elif cmd == "diagnosi":
        diagnosi()
    elif cmd == "valida":
        from . import validate
        r = validate.run()
        print(r[r.model == "armor"].to_string(index=False))
    elif cmd == "valuta-modelli":
        from . import modeleval
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        try:   # 2.2: verifica annuale dei pesi dell'Indice Armor (al massimo una volta l'anno)
            from . import armor_index
            from .features import closed_sp500
            w = armor_index.check_weights(closed_sp500())
            print(f"[pesi indice] adottati: {w['adopted']} (eventi migliorati {w['better_events']}/3, verifica del {w['date']})")
        except Exception as e:  # noqa: BLE001
            print("[pesi indice] errore:", str(e)[:100])
        try:   # indicatori nuovi (credito e PIANO_MODELLO): adozione solo se il test li promuove
            from . import armor_index as _ai
            x = _ai.test_new_indicators(closed_sp500())
            print("[indicatori nuovi] adottati:", x.get("adopted"), {k: (v.get("migliorati"), v.get("peggiorati"), v.get("stato")) for k, v in x.get("dettaglio", {}).items()})
        except Exception as e:  # noqa: BLE001
            print("[indicatori nuovi] errore:", str(e)[:100])
        r = modeleval.evaluate(step=step)
        print(modeleval.table(r))
    elif cmd == "rapporto-mensile":
        from . import rapporto
        r = rapporto.run(closed_sp500(), force=True)
        print(rapporto.html(r)[:2000] if r else "nessun rapporto")
    elif cmd == "sfide":
        from . import challenger
        print(challenger.run().to_string(index=False))
    elif cmd == "notizie":
        ctx = forecast(write=False)
        daily_extras(ctx, fetch_news=True)
    elif cmd == "allarmi":
        from . import allarmi
        allarmi.run()
    elif cmd == "mattina":
        mattina()
    elif cmd == "settimana":
        ctx = forecast(write=False)
        from . import news as _n
        daily_report(ctx, _n.load_latest(), force_week=True)
    elif cmd == "migliora":
        from . import autoimprove
        print(autoimprove.run().tail(3).to_string(index=False))
    elif cmd == "sito":
        costruisci_sito()
    elif cmd == "live":
        from . import live
        live.run()
    elif cmd == "dati-completi":
        stampa_stato(sources.update_all(full=True))
        fonti_nuove(force=True)
    elif cmd == "ricerca":   # PIANO_MODELLO: ricerca del modello (mai sugli anni 2019+ riservati alla prova finale)
        from . import fondamentali, ricerca
        fondamentali.aggiorna_derivate()
        ricerca.run()
    elif cmd == "report":
        from .report import build
        build(forecast())
    elif cmd == "verifica-diario":
        print(journal.verify())
    else:
        print("Comandi: tutto | valuta-modelli | rapporto-mensile | senza-download | diagnosi | valida | sfide | migliora | live | notizie | sito | dati-completi | ricerca | report | verifica-diario")


if __name__ == "__main__":
    main()
