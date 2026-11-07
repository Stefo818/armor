"""Comandi di Armor: python -m armor <comando>.  'tutto' fa l'aggiornamento giornaliero completo."""
import sys
from datetime import datetime

import pandas as pd

from . import journal, sources, store
from .config import MODEL_VERSION
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
    return {"date": t, "pred": pred, "spot": spot, "eng": eng, "fitted": fitted}


def tutto(skip_download: bool = False) -> None:
    if not skip_download:
        st = sources.update_all()
        bad = [k for k, v in st.items() if not v["ok"]]
        print(f"Dati aggiornati. Fonti con problemi: {', '.join(bad) if bad else 'nessuna'}")
        try:
            from .archive import archive_spy_options
            print("Archivio opzioni SPY:", archive_spy_options())
        except Exception as e:  # noqa: BLE001
            print("Archivio opzioni SPY non riuscito:", str(e)[:120])
    try:
        from . import live
        live.run()
    except Exception as e:  # noqa: BLE001
        print('Prezzi live non scaricati:', str(e)[:100])
    ctx = forecast()
    n = journal.update_outcomes(vwce_series(), closed_sp500())
    print(f"Esiti verificati a scadenza: {n}")
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
    build(forecast(write=False), out=site / "index.html")
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
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tutto"
    if cmd == "tutto":
        tutto()
    elif cmd == "senza-download":
        tutto(skip_download=True)
    elif cmd == "diagnosi":
        diagnosi()
    elif cmd == "valida":
        from . import validate
        r = validate.run()
        print(r[r.model == "armor"].to_string(index=False))
    elif cmd == "sfide":
        from . import challenger
        print(challenger.run().to_string(index=False))
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
    elif cmd == "report":
        from .report import build
        build(forecast())
    elif cmd == "verifica-diario":
        print(journal.verify())
    else:
        print("Comandi: tutto | senza-download | diagnosi | valida | sfide | migliora | live | sito | dati-completi | report | verifica-diario")


if __name__ == "__main__":
    main()
