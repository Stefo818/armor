"""Comandi di Armor: python -m armor <comando>.  'tutto' fa l'aggiornamento giornaliero completo."""
import json
import sys
from datetime import datetime

import pandas as pd

from .config import PRIMARY

from . import journal, sources, store
from .config import DATA, MODEL_VERSION
from .features import closed_sp500, vwce_series
from .model import Engine


def controllo_diario() -> None:
    """Rilegge la catena di hash del diario v3. Se è rotta il processo termina con errore (il workflow diventa rosso)."""
    from . import journal3
    ok, n, err = journal3.verifica_estrema()
    if ok:
        print(f"[diario] integrità ok: {n} righe, catena valida", flush=True)
        return
    print(f"[diario] ERRORE: catena rotta alla riga {n} — {err}", flush=True)
    raise SystemExit(1)


def forecast(write: bool = True) -> dict:
    """Calcola le stime di oggi (ultima seduta chiusa) e le registra nel diario."""
    p = closed_sp500()
    from .autoimprove import champion_engine
    eng, mid = champion_engine(p)
    t = eng.F.index[-1]
    fitted = eng.fit(t)
    pred = eng.predict(fitted, t)
    import copy
    pred_a1 = copy.deepcopy(pred)
    try:   # sfidante in prova (FHS+VIX): affiancato in pred[hz]['sfidante'], NON sostituisce A1 (PIANO_ARMOR3 Fase 0)
        from . import campioni
        pred = campioni.sfidante(pred, p, t)
        av = campioni.avvisi_coerenza(pred)
        if av:
            print("[coerenza] A1 non monotono tra orizzonti:", "; ".join(av), flush=True)
            for r in pred.values():
                r["avviso_coerenza"] = av
    except Exception as e:  # noqa: BLE001
        print("[sfidante] non calcolato:", str(e)[:100])
    try:   # indice di affidabilità a segnali (PIANO_ARMOR3 Fase 4)
        from . import affidabilita
        aff = affidabilita.calcola(pred, p, t)
        print(f"[affidabilità] {aff['livello']} ({aff['n_accesi']} segnali accesi)", flush=True)
    except Exception as e:  # noqa: BLE001
        print("[affidabilità] non calcolata:", str(e)[:100])
    po = None
    try:   # motore unico di percorsi (PIANO_ARMOR3 Fase 2): scenari + adozione orizzonte per orizzonte solo se la verifica storica del protocollo l'ha promosso
        from . import journal3, percorsi
        po = percorsi.oggi(p, t)
        pred, mid = percorsi.applica_adozione(pred, po, mid)
        ing = {"vix": po.get("vix"), "vix3m": po.get("vix3m"), "rapporti": po.get("rapporti"), "ultimi_dati": journal3.ultimi_dati()}
        d0 = t.strftime("%Y-%m-%d")
        if write:
            journal3.append_previsione(d0, "A1", "A1", {"modello": "regressione logistica"}, ing,
                                       {hz: {"p": {str(k): v for k, v in r["p_a1"].items()} if r.get("p_a1") else {str(k): v for k, v in r["p"].items()},
                                             "base": {str(k): v for k, v in r["base"].items()}} for hz, r in pred.items()})
            for var, res in po["varianti"].items():
                journal3.append_previsione(d0, "Percorsi", var, res["_diag"], ing, {hz: x for hz, x in res.items() if not hz.startswith("_")})
    except Exception as e:  # noqa: BLE001
        print("[percorsi] non calcolati:", str(e)[:120])
    if write:
        controllo_diario()
    try:   # scenari stimati sui rendimenti di VWCE in euro (serie a segmenti dichiarati)
        from . import serie_eur
        serie_eur.oggi()
        from . import pacsim
        pacsim.aggiorna()
    except Exception as e:  # noqa: BLE001
        print("[euro] scenari o percorsi del PAC non calcolati:", str(e)[:100])
    v = vwce_series()
    spot = float(v.reindex([t], method="ffill").iloc[0]) if not v.empty else float("nan")
    n = journal.append(t.strftime("%Y-%m-%d"), spot, pred, model=mid) if write else 0
    print(f"Previsioni del {t.date()}: {n} nuove righe nel diario")
    if write:
        try:   # 4.1 modalita' ombra: i motori sfidanti scrivono nel diario a parte (non influenzano l'app)
            from . import shadow
            shadow.run(p, t, pred_a1, spot)
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
        from . import eventi_esiti
        print("Risultati trimestrali salvati:", with_timeout(lambda: eventi_esiti.aggiorna_trimestrali(dict(news.TOP20)), 180, "risultati trimestrali"))
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
    try:
        from . import scadenze
        scadenze.notifica()
        from . import armor_lungo
        armor_lungo.aggiorna()
    except Exception as e:  # noqa: BLE001
        print("[scadenze] non controllate:", str(e)[:80])


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
    try:   # salute delle prime 30 aziende di VWCE (bilanci Yahoo, una volta a settimana)
        from . import aziende
        with_timeout(lambda: aziende.aggiorna(force=force), 240, "bilanci aziende")
    except Exception as e:  # noqa: BLE001
        print("[aziende] bilanci non aggiornati:", str(e)[:120])


def tutto(skip_download: bool = False) -> None:
    if not skip_download:
        from .guard import with_timeout
        try:
            st = with_timeout(sources.update_all, 840, "download dati")
        except TimeoutError as ex:
            print("ATTENZIONE:", ex)
            st = store.read_status()
        bad = [k for k, v in st.items() if isinstance(v, dict) and "ok" in v and not v["ok"]]
        print(f"Dati aggiornati. Fonti con problemi: {', '.join(bad) if bad else 'nessuna'}")
        try:
            from .archive import archive_spy_options
            print("Archivio opzioni SPY:", with_timeout(archive_spy_options, 240, "opzioni SPY"))
        except Exception as e:  # noqa: BLE001
            print("Archivio opzioni SPY non riuscito:", str(e)[:120])
        fonti_nuove()
        try:   # coerenza dei dati (VIX contro la tabella di riferimento, date allineate, VWCE L&S contro Xetra): non blocca mai il ciclo
            from . import audit_dati
            audit_dati.esegui()
        except Exception as e:  # noqa: BLE001
            print("[audit] non riuscito:", str(e)[:100])
        try:   # P/E e P/S previsti dell'S&P 500 (una volta a settimana, ~5 minuti)
            from . import previsti
            print("[previsti]", with_timeout(previsti.aggiorna, 1000, "P/E previsti"))
        except Exception as e:  # noqa: BLE001
            print("[previsti] non riusciti:", str(e)[:100])
        try:   # «Regime di tensione» (PROTOCOLLO_REGIME.md): esperimento rifatto ogni ~30 giorni, usa la cache di A1
            from . import tensione
            import time as _t
            if not tensione.FILE.exists() or _t.time() - tensione.FILE.stat().st_mtime > 30 * 86400:
                tensione.run()
        except Exception as e:  # noqa: BLE001
            print("[regime] esperimento non riuscito:", str(e)[:100])
    try:   # serie derivate (crescita utili, inflazione annua, liquidità Fed, forza relativa...): veloce, anche senza download
        from . import fondamentali
        fondamentali.aggiorna_derivate()
    except Exception as e:  # noqa: BLE001
        print("[fondamentali] derivate non calcolate:", str(e)[:120])
    try:   # inclinazione del mercato: tendenza di fondo e verdetto di direzione (registrato ogni giorno, verificato sugli esiti)
        from . import inclinazione
        from .features import closed_sp500 as _cs
        _p = _cs()
        from . import store as _st
        inclinazione.aggiorna(_p[_p.index >= "1985-01-01"], _st.load("vix"), _st.load("armor_index"))
    except Exception as e:  # noqa: BLE001
        print("[inclinazione] non aggiornata:", str(e)[:120])
    try:   # segnali classici, mesi simili e modelli in ombra a 6-12 mesi (PIANO_MODELLO, Fase C)
        from . import ciclico
        ciclico.aggiorna()
    except Exception as e:  # noqa: BLE001
        print("[ciclico] non aggiornato:", str(e)[:120])
    try:
        from . import live
        live.run()
        from . import archivio_dati
        archivio_dati.registra_live()
    except Exception as e:  # noqa: BLE001
        print('Prezzi live non scaricati:', str(e)[:100])
    try:   # impronta del protocollo di verifica (una volta per versione del file)
        from . import verifica
        verifica.registra_protocollo()
        from . import vrp
        vrp.registra_protocollo()
    except Exception as e:  # noqa: BLE001
        print("[protocollo] non registrato:", str(e)[:100])
    ctx = forecast()
    daily_extras(ctx)
    n = journal.update_outcomes(vwce_series(), closed_sp500())
    print(f"Esiti verificati a scadenza: {n}")
    try:   # semaforo del rischio di calo a 5 stati (isteresi 3 sedute), da A1 e FHS+VIX di oggi
        from . import semaforo_rischio
        print("[semaforo]", semaforo_rischio.aggiorna(ctx["pred"], str(closed_sp500().index[-1].date())) and "ok")
    except Exception as e:  # noqa: BLE001
        print("[semaforo] non aggiornato:", str(e)[:100])
    try:   # motore Titan v47: indici e previsioni del giorno (data/titan.json, data/titan_storia.csv)
        from . import titan_job
        _t = titan_job.esegui()
        print(f"[titan] armor {_t['armor_index']:.1f} · super {_t['super_armor']:.1f} · radar {_t['radar_decennio']:.1f}")
    except Exception as e:  # noqa: BLE001
        print("[titan] non calcolato:", str(e)[:120])
    try:   # Super Armor Index: valore del giorno nella storia (ricostruita dal 2000, poi reale)
        from . import super_armor, armor_index
        _p = closed_sp500()
        _o = super_armor.calcola(armor_index.compute(_p), _p)
        if _o:
            super_armor.registra(_o)
            print(f"[super armor] {_o['sai']:.0f}/100 ({_o['concordanza']})")
    except Exception as e:  # noqa: BLE001
        print("[super armor] non registrato:", str(e)[:100])
    try:   # grandi fondi (peso zero): percentili, prova storica, registro giornaliero
        from . import grandi_fondi
        grandi_fondi.run(closed_sp500())
        from . import candidati
        candidati.run(closed_sp500())
    except Exception as e:  # noqa: BLE001
        print("[grandi fondi] non aggiornati:", str(e)[:100])
    try:   # classifica dei modelli (voto 1-100), una riga per modello al giorno
        from . import classifica
        classifica.registra(str(closed_sp500().index[-1].date()))
    except Exception as e:  # noqa: BLE001
        print("[classifica] non registrata:", str(e)[:100])
    try:
        from . import journal3
        print(f"[diario v3] esiti nuovi: {journal3.update_outcomes(closed_sp500())}; {journal3.verify()[1]}")
    except Exception as e:  # noqa: BLE001
        print("[diario v3] errore:", str(e)[:100])
    try:
        from . import learning
        t = learning.update(closed_sp500())
        print(f"[apprendimento] confronti con la realtà aggiornati: {len(t)} righe")
    except Exception as e:  # noqa: BLE001
        print("[apprendimento] non aggiornato:", str(e)[:100])
    ok, msg = journal.verify()
    print("Integrita' diario:", msg if ok else "ERRORE - " + msg)
    controllo_diario()
    try:   # copia settimanale del diario (tiene le ultime 12)
        from . import journal3
        creato = journal3.backup_settimanale()
        if creato:
            print(f"[backup] creato {creato}", flush=True)
    except Exception as e:  # noqa: BLE001
        print("[backup] non riuscito:", str(e)[:100])
    try:   # heartbeat: il diario cresce? le fonti sono aggiornate? avvisi se si ferma
        from . import diagnostica
        diagnostica.esegui()
    except Exception as e:  # noqa: BLE001
        print("[diagnostica] non riuscita:", str(e)[:100])
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
    try:
        from . import perche
        (site / "perche.html").write_text(perche.html(perche.carica()), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print("[perche] scheda non scritta:", str(e)[:80])
    for f in (ROOT / "web").glob("*"):
        shutil.copy(f, site / f.name)
    try:
        from . import archivio_dati
        (site / "archivio_dati.csv").write_text(archivio_dati.csv_text(), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print("[archivio dati] CSV non scritto:", str(e)[:80])
    if (DATA / "pac_sim.json").exists():   # percorsi mensili del simulatore PAC
        shutil.copy(DATA / "pac_sim.json", site / "pac_sim.json")
    (site / ".nojekyll").write_text("")
    print("Sito pronto in", site)


def stampa_stato(st: dict) -> None:
    """Stampa l'esito di ogni fonte (da incollare a Claude se qualcosa non va)."""
    for k, v in sorted(((k, v) for k, v in st.items() if isinstance(v, dict) and "ok" in v), key=lambda kv: (kv[1]["ok"], kv[0])):
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
    elif cmd == "titan":
        from . import titan_job
        print(titan_job.esegui())
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
        try:   # motore per ogni orizzonte, con la regola fissa di campioni.py
            from . import campioni
            campioni.aggiorna()
        except Exception as e:  # noqa: BLE001
            print("[campioni] errore:", str(e)[:100])
        try:   # verifica rigorosa con margini d'errore (PIANO_ARMOR3 Fase 1): rifatta ogni mese
            from . import verifica
            print(verifica.tabella_testo(verifica.run_storica(step=step)))
        except Exception as e:  # noqa: BLE001
            print("[verifica] errore:", str(e)[:100])
        try:   # VWCE in euro: segmenti e confronto tra motori, rifatto ogni mese
            from . import serie_eur
            serie_eur.run()
        except Exception as e:  # noqa: BLE001
            print("[euro] errore:", str(e)[:100])
    elif cmd == "serie-euro":   # segmenti, confronto tra serie e tra motori su VWCE in euro (~1 minuto)
        from . import serie_eur
        print(serie_eur.run())
    elif cmd == "previsti":
        from . import previsti
        print(previsti.aggiorna(forza=True))
    elif cmd == "esperimento-regime":   # Patch 43: regime di tensione, 4 varianti walk-forward (~1 minuto)
        from . import tensione
        r = tensione.run()
        print("variante scelta:", r["scelta"], "| adozione:", r["adozione"])
    elif cmd == "mercati-mondo":   # Patch 44: classifiche per periodo (Yahoo, a blocchi); lo lancia mercati.yml dopo la chiusura USA
        from . import mondo
        d = mondo.aggiorna()
        print({"attività": len(d["items"]), "mancanti": d["mancanti"][:40]})
    elif cmd == "titoli-aggiorna":   # Patch 45: universo, prezzi, filtri, classifiche → data/titoli_top.json (lento: 20-40 minuti la prima volta)
        from . import titoli
        d = titoli.aggiorna()
        print({"titoli_in_classifica": len(d["items"]), "universo_filtrato": d["universo"], "dati_al": d["asof"]})
    elif cmd == "saldi-aggiorna":   # Patch 46: fondamentali, notizie, punteggio Salute e report per i candidati (dopo titoli-aggiorna)
        from . import saldi
        d = saldi.aggiorna()
        print({"titoli": len(d["titoli"]), "dati_al": d["asof"]})
    elif cmd == "serie-azioni":   # storico dei maggiori titoli del VWCE per il grafico interattivo
        from . import grafico
        grafico.aggiorna()
    elif cmd == "economia-aggiorna":   # Patch 54: finestra sul mondo (FRED, BCE, Eurostat) → data/economia.json
        from . import economia
        d = economia.aggiorna()
        print({"indicatori": len(d["items"]), "non_disponibili": len(d["errori"]), "dati_al": d["asof"]})
    elif cmd == "economia-prova":   # elenca gli indicatori che la fonte non ha dato e il motivo
        from . import economia
        d = economia.aggiorna()
        for k, v in d["errori"].items():
            print(k, "->", v)
        print("vecchi:", [x["id"] for x in d["items"] if x["old"]])
    elif cmd == "opportunita-aggiorna":   # Patch 47: le 30 aziende della settimana con punteggio Potenziale (sabato)
        from . import opportunita
        d = opportunita.aggiorna()
        print({"scelte": len(d["ordine"]), "dati_al": d["asof"]})
    elif cmd == "armor-lungo":   # Patch 79: prova dell'Indice Armor su 1950-oggi (regole in PROTOCOLLO_ARMOR_LUNGO.md)
        from . import armor_lungo
        ok = armor_lungo.aggiorna(force=True)
        d = armor_lungo.carica() if ok else None
        print("[armor-lungo]", "non calcolato" if not d else f"{d['verdetto']} (soglia {d['regola1']}, valore aggiunto {d['regola2']}, tenuta {d['regola3']})")
    elif cmd == "scadenza-fatta":   # python -m armor scadenza-fatta <id>: segna una verifica come fatta
        from . import scadenze
        print("Segnata come fatta." if len(sys.argv) > 2 and scadenze.segna_fatta(sys.argv[2]) else "Indicare un id valido (es. opp_v2, sem_6m, regime_6m, fondi_6m, brevetti_12m, armor_pesi, armor_evento).")
    elif cmd == "opportunita-valuta-v2":   # Patch 71: confronto dei pesi v2 con quelli ufficiali (regola scritta in anticipo)
        from . import opportunita, titoli
        arch = titoli.carica_prezzi()
        c_all = arch["close"]
        vt = c_all["VT"] if "VT" in c_all else c_all["SPY"]
        print(json.dumps(opportunita.valuta_v2(c_all, vt), ensure_ascii=False, indent=1))
    elif cmd == "opportunita-rinfresca":   # prezzi e storico delle scelte, senza ricalcolare il punteggio (giornaliero)
        from . import opportunita
        opportunita.rinfresca()
    elif cmd == "titoli-prova":   # python -m armor titoli-prova NVDA : mostra indicatori, eventi 8-K e notizie classificate di un solo titolo
        from . import titoli_prova
        titoli_prova.main(sys.argv[2] if len(sys.argv) > 2 else "NVDA")
    elif cmd == "audit-dati":
        from . import audit_dati
        raise SystemExit(0 if audit_dati.esegui()["ok"] else 1)
    elif cmd == "diagnostica":   # solo controllo del diario e avvisi (usato dal controllo del mattino, che non scrive nel repository)
        from . import diagnostica
        diagnostica.esegui(scrivi_stato=False)
    elif cmd == "esperimento-vrp":   # Fase 6: premio di volatilità e HAR in ombra (~10 minuti)
        from . import vrp
        r = vrp.run()
        print({m: x["promettente"] for m, x in r["promettenti"].items()})
    elif cmd == "brevetti-sonda":   # prova di accesso ai file dei brevetti (PatentsView) e dell'elenco SEC; mostra gli abbinamenti nome → simbolo
        from . import brevetti
        print(brevetti.sonda())
    elif cmd == "brevetti-aggiorna":   # scarica i brevetti concessi, li abbina alle società quotate → data/brevetti.json
        from . import brevetti
        brevetti.aggiorna()
    elif cmd == "brevetti-locale":   # legge i due file già scaricati sul PC (cartella indicata) e scrive data/brevetti.json
        from . import brevetti
        print(brevetti.aggiorna(cartella=sys.argv[2] if len(sys.argv) > 2 else r"D:\Armor\Brevetti"))
    elif cmd == "sec-sonda":   # prova di accesso ai dati SEC: elenco, nomi dei file, intestazioni
        from . import sec_dati
        print(sec_dati.sonda())
    elif cmd == "sec-aggiorna":   # scarica (a pezzi) 13F, insider, 13D e ricalcola i segnali dei Grandi fondi
        from . import sec_dati, grandi_fondi
        sec_dati.aggiorna_tutto(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
        r = grandi_fondi.run()
        print({k: (v["stato"], v["prova"].get("verdetto")) for k, v in r["segnali"].items()})
    elif cmd == "taratura":   # taratura annidata di A1 e FHS+VIX (PROTOCOLLO_TARATURA.md, lento)
        from . import taratura
        cache = "/tmp/armor_taratura_cache.pkl"
        r = taratura.run(cache=cache)
        print(r.get("verdetto") if isinstance(r, dict) else r)
        from . import semaforo_rischio   # tabella storica dei colori, riusa le stesse previsioni passate
        t = semaforo_rischio.run(cache=cache)
        print("semaforo, colori in ordine:", t["monotona"])
        from . import super_armor
        from .features import closed_sp500 as _cs
        print("Super Armor Index, fasce in ordine:", super_armor.valuta(_cs())["ordine"])
        from . import semaforo_mercati
        print("semaforo su altri mercati:", {k: v.get("monotona") for k, v in semaforo_mercati.run()["mercati"].items()})
    elif cmd == "classifica":   # classifica dei modelli con voto da 1 a 100
        from . import classifica
        from .features import closed_sp500
        for r in classifica.calcola():
            print(r["posto"], r["modello"], r["voto"])
        print("registrata:", classifica.registra(str(closed_sp500().index[-1].date())))
    elif cmd == "verifica-percorsi":   # 12 varianti del motore di percorsi contro A1, con la regola di adozione del protocollo (lento: ~15 minuti)
        from . import percorsi
        r = percorsi.run_verifica()
        print({hz: (o["passano"], o["scelta"]) for hz, o in r["orizzonti"].items()}, "mostrata:", r["mostrata"])
    elif cmd == "verifica":
        from . import verifica
        print(verifica.tabella_testo(verifica.run_storica()))
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
    elif cmd == "perche":   # Patch 80: «Perché si muove oggi» (settori, aziende, notizie)
        from . import perche
        perche.aggiorna()
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
    elif cmd == "ricerca-finale":   # prova UNICA sugli anni 2019-oggi (se esiste già, mostra il risultato salvato)
        from . import ricerca
        print(json.dumps(ricerca.prova_finale(), ensure_ascii=False, indent=1, default=str)[:3000])
    elif cmd == "report":
        from .report import build
        build(forecast())
    elif cmd == "verifica-diario":
        print(journal.verify())
        from . import journal3
        print(journal3.verify())
    else:
        print("Comandi: tutto | titan | valuta-modelli | rapporto-mensile | senza-download | diagnosi | valida | sfide | migliora | live | notizie | sito | dati-completi | ricerca | report | verifica-diario")


if __name__ == "__main__":
    main()
