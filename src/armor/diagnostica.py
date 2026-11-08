"""Auto-diagnostica (Patch 34): il diario cresce? le fonti sono aggiornate? Scrive data/diagnostica.json, mostra un badge, avvisa se qualcosa si ferma.
I «giorni» del diario sono giorni LAVORATIVI (lun-ven) tra l'ultima previsione e oggi: il fine settimana non conta come ritardo. Le festività di Wall Street non sono tolte:
a Pasqua o dopo un altro giorno di chiusura può comparire un giorno di ritardo in più (l'avviso dice solo di controllare Actions)."""
import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from . import store
from .config import DATA

SOGLIA_ALERT = 3        # giorni lavorativi: avviso (ntfy o banner)
SOGLIA_ISSUE = 4        # giorni lavorativi: issue su GitHub
MIN_STANDARD = 10       # giorni di calendario: soglia minima per le serie non elencate in salute.KEY_SERIES (altrimenti 3 × il passo abituale della serie + 60)
REPO = "Stefo818/armor"


def _lavorativi(da: str, a: date) -> int:
    return int(np.busday_count(np.datetime64(da), np.datetime64(a.isoformat())))


def ultima_previsione(base: Path | None = None) -> str | None:
    """Data (asof) dell'ultima riga kind=previsione del diario v3; None se il diario è vuoto o assente."""
    f = (base or DATA) / "journal_v3.csv"
    if not f.exists():
        return None
    ultima = None
    with open(f, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("kind") == "previsione" and r.get("asof") and (ultima is None or r["asof"] > ultima):
                ultima = r["asof"]
    return ultima


def fonti(base: Path | None = None, oggi: date | None = None) -> list[dict]:
    """Per ogni fonte attesa (serie chiave + ogni file in data/series): ultima data, giorni di calendario di ritardo, stato ok / warning / errore."""
    from .salute import KEY_SERIES
    base = base or DATA
    oggi = oggi or date.today()
    soglie = {k: lag for k, _n, lag in KEY_SERIES}
    chiave = set(soglie)
    cartella = base / "series"
    nomi = sorted(set(soglie) | {p.stem for p in cartella.glob("*.csv")}) if cartella.exists() else sorted(soglie)
    try:
        st = json.loads((base / "status.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    out = []
    for n in nomi:
        f = cartella / f"{n}.csv"
        ultima = None
        if f.exists():
            try:
                with open(f, newline="", encoding="utf-8") as fh:
                    rows = list(csv.reader(fh))
                ultima = rows[-1][0] if len(rows) > 1 else None
                if ultima and n not in soglie:
                    ds = [date.fromisoformat(r[0]) for r in rows[-13:] if r and r[0][:2] == "20" or r and r[0][:2] == "19"]
                    gaps = sorted((b - a).days for a, b in zip(ds, ds[1:]))
                    passo = gaps[len(gaps) // 2] if gaps else 1
                    soglie[n] = max(MIN_STANDARD, 3 * passo + 60) if passo > 3 else MIN_STANDARD
            except Exception:  # noqa: BLE001
                ultima = None
        if not ultima:
            out.append({"nome": n, "chiave": n in chiave, "ultima_data": None, "giorni_ritardo": None, "stato": "errore", "nota": (st.get(n) or {}).get("stato", "assente") if isinstance(st.get(n), dict) else "assente"})
            continue
        rit = (oggi - date.fromisoformat(ultima)).days
        out.append({"nome": n, "chiave": n in chiave, "ultima_data": ultima, "giorni_ritardo": rit, "stato": "ok" if rit <= soglie.get(n, MIN_STANDARD) else "warning"})
    return out


def diagnostica_heartbeat(base: Path | None = None, oggi: date | None = None, scrivi: bool = True) -> dict:
    base = base or DATA
    oggi = oggi or date.today()
    ult = ultima_previsione(base)
    g = None if ult is None else _lavorativi(ult, oggi)
    out = {"data_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "oggi": oggi.isoformat(), "ultima_previsione": ult, "giorni_da_ultima": g, "fonti": fonti(base, oggi)}
    if scrivi:
        (base / "diagnostica.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def badge(diag: dict | None = None) -> str:
    """Pallino in cima alla pagina «Salute dei dati»: verde fino a 1 giorno lavorativo, giallo 2-3, rosso da 4."""
    import html as _h
    if diag is None:
        try:
            diag = json.loads((DATA / "diagnostica.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return ""
    g = diag.get("giorni_da_ultima")
    if g is None:
        cls, txt = "warn", "Diario vuoto: nessuna previsione registrata"
    elif g >= 4:
        cls, txt = "bad", f"Diario fermo da {g} giorni"
    elif g >= 2:
        cls, txt = "warn", f"Diario fermo da {g} giorni"
    else:
        cls, txt = "ok", "Diario aggiornato oggi" if g == 0 else "Diario aggiornato (ultima seduta registrata)"
    nf = sum(1 for x in diag.get("fonti", []) if x["stato"] != "ok" and x.get("chiave", True))   # le serie storiche ferme (es. Shiller fino al 2023) restano nel file ma non sporcano il badge
    extra = f" · {nf} fonti da controllare" if nf else " · tutte le fonti regolari"
    return f"<p><span class='badge {cls}'>{_h.escape(txt)}</span> <span class='mu'>ultima previsione: {_h.escape(str(diag.get('ultima_previsione') or '—'))}{extra}</span></p>"


def banner() -> str:
    """Banner rosso se in status.json c'è un avviso sul diario fermo."""
    import html as _h
    a = store.read_status().get("alert_diario")
    if not a:
        return ""
    return f"<div class='vd bad' style='margin:8px 0'>{_h.escape(a.get('testo', ''))} <span class='mu'>({_h.escape(a.get('data', ''))})</span></div>"


# ------------------------------------------------------------------ avvisi
def _http_issue(token: str, repo: str, titolo: str, corpo: str, oggi: date, get=None, post=None, patch=None) -> str:
    """Apre una issue «[Armor] Diario fermo da N giorni»; se ce n'è già una aperta con lo stesso inizio di titolo, aggiunge un commento (una volta al giorno) senza duplicare."""
    import requests
    get, post = get or requests.get, post or requests.post
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{repo}/issues"
    r = get(api, headers=h, params={"state": "open", "per_page": 50}, timeout=20)
    r.raise_for_status()
    prefisso = "[Armor] Diario fermo"
    for it in r.json():
        if it.get("title", "").startswith(prefisso) and "pull_request" not in it:
            if str(it.get("updated_at", ""))[:10] == oggi.isoformat():
                return "esistente"
            post(f"{api}/{it['number']}/comments", headers=h, json={"body": f"{titolo}\n\n```json\n{corpo}\n```"}, timeout=20).raise_for_status()
            return "commentata"
    post(api, headers=h, json={"title": titolo, "body": f"```json\n{corpo}\n```"}, timeout=20).raise_for_status()
    return "aperta"


def avvisi(diag: dict, env=None, scrivi_stato: bool = True, send=None, issue=None) -> dict:
    """ntfy (o banner nello stato) da 3 giorni lavorativi, issue GitHub da 4. Non invia più di un avviso ntfy al giorno."""
    env = os.environ if env is None else env
    g = diag.get("giorni_da_ultima")
    oggi = diag.get("oggi") or date.today().isoformat()
    res = {"ntfy": False, "banner": False, "issue": None}
    st = store.read_status() if scrivi_stato else {}
    if g is None or g < SOGLIA_ALERT:
        if scrivi_stato and ("alert_diario" in st or "alert_diario_ntfy" in st):
            st.pop("alert_diario", None)
            st.pop("alert_diario_ntfy", None)
            store.write_status(st)
        return res
    testo = f"[Armor] Diario fermo da {g} giorni — controlla Actions"
    if env.get("NTFY_TOPIC", "").strip():
        if st.get("alert_diario_ntfy") != oggi:
            from . import alerts
            n = (send or alerts.send)([{"title": "Armor", "message": testo, "priority": 4, "tags": ["warning"]}], env["NTFY_TOPIC"].strip())
            res["ntfy"] = bool(n)
            if scrivi_stato and n:
                st["alert_diario_ntfy"] = oggi
                store.write_status(st)
    elif scrivi_stato:
        st["alert_diario"] = {"testo": testo, "data": oggi}
        store.write_status(st)
        res["banner"] = True
    if g >= SOGLIA_ISSUE and env.get("GITHUB_TOKEN"):
        try:
            res["issue"] = (issue or _http_issue)(env["GITHUB_TOKEN"], env.get("GITHUB_REPOSITORY", REPO), f"[Armor] Diario fermo da {g} giorni",
                                                  json.dumps(diag, ensure_ascii=False, indent=1)[:60000], date.fromisoformat(oggi))
        except Exception as e:  # noqa: BLE001
            res["issue"] = "errore: " + str(e)[:80]
    return res


def esegui(scrivi_stato: bool = True) -> dict:
    d = diagnostica_heartbeat()
    print(f"[diagnostica] ultima previsione {d['ultima_previsione']}, giorni lavorativi di ritardo: {d['giorni_da_ultima']}; "
          f"fonti chiave da controllare: {sum(1 for x in d['fonti'] if x['stato'] != 'ok' and x['chiave'])}", flush=True)
    r = avvisi(d, scrivi_stato=scrivi_stato)
    if r["ntfy"] or r["banner"] or r["issue"]:
        print("[diagnostica] avvisi:", r, flush=True)
    return d
