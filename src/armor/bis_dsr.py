"""Importazione dei Debt Service Ratios BIS tramite API SDMX pubblica.

I dati sono trimestrali. Il modulo li salva come serie grezze; chi li usa in una
ricerca predittiva deve applicare un ritardo di pubblicazione conservativo.
Non modifica gli indici di produzione di Armor.
"""
from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd
import requests

from . import store

BASE_URL = "https://stats.bis.org/api/v1/data/WS_DSR/{}"
ACCEPT = "application/vnd.sdmx.data+json;version=1.0.0"
COUNTRIES = {"US": "us", "XM": "xm", "JP": "jp", "GB": "gb", "CA": "ca"}
SECTORS = {"P": "private", "H": "households", "N": "corporate"}


def _period_end(value: str) -> pd.Timestamp:
    """Converte un periodo BIS trimestrale (es. 1999-Q1) in fine trimestre."""
    value = str(value).strip()
    m = re.fullmatch(r"(\d{4})[- ]?Q([1-4])", value, flags=re.I)
    if not m:
        raise ValueError(f"Periodo BIS non riconosciuto: {value!r}")
    return pd.Period(f"{m.group(1)}Q{m.group(2)}", freq="Q").end_time.normalize()


def parse_sdmx_json(payload: str | dict[str, Any]) -> dict[str, pd.Series]:
    """Estrae tutte le serie paese/settore da una risposta SDMX-JSON BIS.

    Il parser si basa sugli indici dichiarati in structure.dimensions, non
    sull'ordine fisso delle dimensioni. Supporta dataset SDMX con una o più
    serie nella risposta.
    """
    obj = json.loads(payload) if isinstance(payload, str) else payload
    datasets = obj.get("dataSets") or []
    structure = obj.get("structure") or {}
    dims = structure.get("dimensions") or {}
    series_dims = dims.get("series") or []
    obs_dims = dims.get("observation") or []
    if not datasets or not series_dims or not obs_dims:
        raise ValueError("Risposta BIS SDMX senza dataSets/dimensions attesi")

    def dim_index(names: set[str]) -> int:
        for i, d in enumerate(series_dims):
            if str(d.get("id", "")).upper() in names:
                return i
        return -1

    country_pos = dim_index({"BORROWERS_CTY", "REF_AREA", "REFAREA", "COUNTRY"})   # per il DSR la BIS usa BORROWERS_CTY
    sector_pos = dim_index({"DSR_BORROWERS", "BORROWERS", "SECTOR"})
    time_dim = next((d for d in obs_dims if str(d.get("id", "")).upper() in {"TIME_PERIOD", "TIMEPERIOD"}), None)
    if country_pos < 0 or sector_pos < 0 or time_dim is None:
        raise ValueError("Dimensioni BIS BORROWERS_CTY/DSR_BORROWERS/TIME_PERIOD mancanti: " + ", ".join(str(d.get("id")) for d in series_dims))

    periods = [v.get("id", v.get("name", "")) for v in time_dim.get("values", [])]
    series_block = datasets[0].get("series") or {}
    if not series_block:
        raise ValueError("Risposta BIS priva di serie osservate")

    out: dict[str, pd.Series] = {}
    for key, block in series_block.items():
        try:
            positions = [int(x) for x in str(key).split(":")]
            country_code = str(series_dims[country_pos]["values"][positions[country_pos]]["id"]).upper()
            sector_code = str(series_dims[sector_pos]["values"][positions[sector_pos]]["id"]).upper()
        except (IndexError, KeyError, ValueError, TypeError):
            continue
        if country_code not in COUNTRIES or sector_code not in SECTORS:
            continue
        obs = block.get("observations") or {}
        vals: dict[pd.Timestamp, float] = {}
        for obs_key, raw in obs.items():
            try:
                period = periods[int(obs_key)]
                value = float(raw[0])
                if pd.notna(value):
                    vals[_period_end(period)] = value
            except (IndexError, TypeError, ValueError):
                continue
        if vals:
            sid = f"bis_dsr_{COUNTRIES[country_code]}_{SECTORS[sector_code]}"
            out[sid] = pd.Series(vals, dtype=float).sort_index().rename(sid)
    if not out:
        raise ValueError("Nessuna osservazione DSR BIS riconosciuta")
    return out


# Ritardo prudente fra la fine del trimestre e il momento in cui il dato e' davvero pubblico. Solo un'ipotesi:
# dopo i primi aggiornamenti dal vivo conta la data di «prima vista» salvata in data/bis_dsr_meta.json.
DISPONIBILE_DOPO_GIORNI = 150
META = None  # percorso del file con le date di prima vista (impostato in aggiorna())


def _request_key(key: str, start_period: str) -> dict[str, pd.Series]:
    url = BASE_URL.format(key)
    response = requests.get(
        url,
        params={"startPeriod": start_period},
        headers={"Accept": ACCEPT, "User-Agent": "Armor personal quantitative research"},
        timeout=45,
    )
    response.raise_for_status()
    return parse_sdmx_json(response.text)


def fetch_all(full: bool = False, errori: dict[str, str] | None = None) -> dict[str, pd.Series]:
    """Scarica DSR USA + principali aree investibili; nessuna API key richiesta.

    Prima richiesta: da 1999. Aggiornamenti successivi: finestra mobile di 3 anni
    per incorporare eventuali revisioni dei trimestri più recenti.
    """
    total_ids = [f"bis_dsr_{COUNTRIES[c]}_private" for c in COUNTRIES]
    old_dates = []
    for sid in total_ids:
        old = store.load(sid)
        if not old.empty:
            old_dates.append(old.index.max())
    if full or not old_dates:
        start = "1999-Q1"
    else:
        start_date = min(old_dates) - pd.DateOffset(years=3)
        start = f"{start_date.year}-Q{((start_date.month - 1) // 3) + 1}"

    out: dict[str, pd.Series] = {}
    # Tentativo aggregato per ridurre il numero di richieste.
    errori = errori if errori is not None else {}
    try:
        out.update(_request_key("Q.US+XM+JP+GB+CA.P", start))
    except Exception as exc:  # noqa: BLE001 - registrato, poi si prova area per area
        errori["Q.US+XM+JP+GB+CA.P"] = str(exc)[:120]

    # Fallback per singola area: non basta che la query aggregata restituisca
    # una sola serie per considerare complete tutte le altre aree.
    for country, slug in COUNTRIES.items():
        sid = f"bis_dsr_{slug}_private"
        if sid in out:
            continue
        try:
            out.update(_request_key(f"Q.{country}.P", start))
        except Exception as exc:  # noqa: BLE001
            errori[f"Q.{country}.P"] = str(exc)[:120]
            continue

    # Breakdown USA: famiglie e imprese non finanziarie.
    try:
        out.update(_request_key("Q.US.H+N", start))
    except Exception as exc:  # noqa: BLE001
        errori["Q.US.H+N"] = str(exc)[:120]
    for sector, slug in (("H", "households"), ("N", "corporate")):
        sid = f"bis_dsr_us_{slug}"
        if sid in out:
            continue
        try:
            out.update(_request_key(f"Q.US.{sector}", start))
        except Exception as exc:  # noqa: BLE001
            errori[f"Q.US.{sector}"] = str(exc)[:120]
            continue
    return out


def registra_prima_vista(serie: dict[str, pd.Series], oggi: str, percorso=None) -> int:
    """Salva, per ogni trimestre, il giorno in cui Armor l'ha visto per la prima volta: da li' in poi si sa quando il dato era davvero noto."""
    from .config import DATA
    percorso = percorso or (DATA / "bis_dsr_meta.json")
    try:
        meta = json.loads(percorso.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        meta = {}
    nuovi = 0
    for sid, ser in serie.items():
        vis = meta.setdefault(sid, {})
        for d in ser.index:
            k = str(pd.Timestamp(d).date())
            if k not in vis:
                vis[k] = oggi
                nuovi += 1
    percorso.write_text(json.dumps(meta, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    return nuovi


ATTESE = ["bis_dsr_us_private", "bis_dsr_us_households", "bis_dsr_us_corporate", "bis_dsr_xm_private",
          "bis_dsr_jp_private", "bis_dsr_gb_private", "bis_dsr_ca_private"]


def aggiorna(full: bool = False, log=print, status: dict | None = None) -> dict[str, int]:
    """Scarica e salva le serie BIS. Peso zero. Ogni richiesta fallita e ogni serie mancante resta scritta in data/status.json."""
    proprio = status is None
    status = store.read_status() if proprio else status
    risultati: dict[str, int] = {}
    errori: dict[str, str] = {}
    try:
        series = fetch_all(full=full, errori=errori)
        if not series:
            raise RuntimeError("BIS non ha restituito serie DSR utilizzabili" + (f" ({'; '.join(f'{k}: {v}' for k, v in errori.items())})" if errori else ""))
        for sid, values in series.items():
            added = store.upsert(sid, values)
            store.set_status(status, sid, True, "Fonte: BIS DSR (SDMX API)", added)
            risultati[sid] = added
        for sid in ATTESE:
            if sid not in series:
                store.set_status(status, sid, False, "BIS DSR: serie non restituita dalla fonte" + (f" ({errori[k]})" if (k := next((k for k in errori if sid.split('_')[2].upper() in k), None)) else "") + "; mantenuto lo storico se presente")
        from datetime import date
        registra_prima_vista(series, str(date.today()))
        log(f"[BIS DSR] aggiornate {len(series)} serie, richieste fallite: {len(errori)}")
    except Exception as exc:  # la mancata risposta BIS non deve bloccare le altre fonti
        store.set_status(status, "bis_dsr", False, f"BIS DSR: {str(exc)[:150]}")
        log(f"[BIS DSR] fonte non disponibile: {str(exc)[:150]}")
    if proprio:
        store.write_status(status)
    return risultati
