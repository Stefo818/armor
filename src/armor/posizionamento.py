"""Posizionamento del mercato: opzioni (put/call, protezioni) e posizioni dei grandi operatori sui futures dell'S&P 500 (CFTC, settimanale)."""
import io
import zipfile
from datetime import datetime

import pandas as pd
import requests

from . import store
from .config import ARCHIVE

UA = {"User-Agent": "Mozilla/5.0 (Armor personal research)"}
CODE = "13874A"   # E-mini S&P 500 (CME)
CUR = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
HIST = "https://www.cftc.gov/files/dea/history/fut_fin_txt_{y}.zip"
# colonne (per posizione) del file "Traders in Financial Futures - solo futures": apertura 7; dealer 8-10; gestori 11-13; fondi a leva 14-16
IDX = {"oi": 7, "dl": 8, "ds": 9, "al": 11, "as": 12, "ll": 14, "ls": 15}


def parse_cot(text: str) -> pd.DataFrame:
    """Dal testo CFTC ricava, per ogni data, la posizione netta in % dell'open interest di fondi a leva e gestori patrimoniali."""
    import csv
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 17 or r[3].strip() != CODE:
            continue
        try:
            oi = float(r[IDX["oi"]])
            if oi <= 0:
                continue
            rows.append({"date": pd.Timestamp(r[2].strip()), "lev": (float(r[IDX["ll"]]) - float(r[IDX["ls"]])) / oi * 100,
                         "am": (float(r[IDX["al"]]) - float(r[IDX["as"]])) / oi * 100, "dealer": (float(r[IDX["dl"]]) - float(r[IDX["ds"]])) / oi * 100})
        except ValueError:
            continue
    df = pd.DataFrame(rows).drop_duplicates("date").set_index("date").sort_index() if rows else pd.DataFrame(columns=["lev", "am", "dealer"])
    return df[(df.abs() <= 100).all(axis=1)] if len(df) else df   # valori fuori scala = colonne lette male: si scartano


def fetch_cot() -> dict[str, pd.Series]:
    frames = []
    have = store.load("cot_lev_net")
    years = [datetime.now().year] if len(have) > 100 else [datetime.now().year - 2, datetime.now().year - 1, datetime.now().year]
    for y in years:   # storia annuale (solo al primo avvio, poi basta la settimana corrente)
        try:
            z = zipfile.ZipFile(io.BytesIO(requests.get(HIST.format(y=y), headers=UA, timeout=60).content))
            frames.append(parse_cot(z.read(z.namelist()[0]).decode("latin-1")))
        except Exception as e:  # noqa: BLE001
            print(f"[cot] storico {y} non scaricato: {str(e)[:60]}", flush=True)
    frames.append(parse_cot(requests.get(CUR, headers=UA, timeout=40).text))
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if df.empty:
        raise RuntimeError("nessun dato CFTC per l'E-mini S&P 500")
    return {"cot_lev_net": df["lev"], "cot_am_net": df["am"], "cot_dealer_net": df["dealer"]}


def _opt_last() -> tuple[pd.DataFrame | None, pd.Series | None]:
    f = ARCHIVE / "spy_options_summary.csv"
    if not f.exists():
        return None, None
    d = pd.read_csv(f).dropna(subset=["date"])
    return d, d.iloc[-1] if len(d) else None


def _read(col: str, v: float, s: pd.Series, hi_text: str, lo_text: str) -> str:
    if len(s) < 20:
        return f"Storico ancora corto ({len(s)} giorni): la lettura diventa affidabile dopo qualche mese di dati."
    p = (s < v).mean() * 100
    return (hi_text if p >= 80 else (lo_text if p <= 20 else "Livello nella norma rispetto ai dati salvati")) + f" ({p:.0f}° percentile)."


def html() -> str:
    out = []
    d, last = _opt_last()
    if last is not None:
        n = lambda x, dec=2: "n.d." if pd.isna(x) else f"{x:.{dec}f}".replace(".", ",")
        pco, pcv = d["pc_open_interest"].dropna(), d["pc_volume"].dropna()
        rows = [("Put/Call (posizioni aperte)", n(last["pc_open_interest"]), _read("oi", last["pc_open_interest"], pco, "Molte protezioni rispetto al solito: prudenza diffusa (indicatore contrario)", "Poche protezioni: compiacimento")),
                ("Put/Call (volumi di oggi)", n(last["pc_volume"]), _read("v", last["pc_volume"], pcv, "Oggi si comprano molte più protezioni del solito", "Oggi dominano le scommesse al rialzo"))]
        if "iv_atm_30d" in d:
            rows.append(("Volatilità implicita a 30 giorni (SPY)", n(last["iv_atm_30d"] * 100, 1) + "%", _read("iv", last["iv_atm_30d"], d["iv_atm_30d"].dropna(), "Il mercato prezza oscillazioni ampie", "Il mercato prezza oscillazioni contenute")))
        if "put_skew_95" in d:
            rows.append(("Costo delle protezioni al 95% (skew)", n(last["put_skew_95"] * 100, 1) + " punti", _read("sk", last["put_skew_95"], d["put_skew_95"].dropna(), "Le protezioni contro il calo costano molto più del normale", "Le protezioni costano poco")))
        out.append("<h3>Opzioni sull'S&amp;P 500 (ETF SPY)</h3><table><tr><th>Misura</th><th>Oggi</th><th>Come si legge</th></tr>"
                   + "".join(f"<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td></tr>" for a, b, c in rows) + "</table>"
                   f"<p class='mu'>Dati del {last['date']}. Put = opzioni che guadagnano se il mercato scende (si comprano per proteggersi o scommettere al ribasso). "
                   "Un put/call molto alto indica paura: in passato spesso vicino a minimi di breve periodo, quindi non va letto come «scenderà ancora».</p>")
    lev, am = store.load("cot_lev_net"), store.load("cot_am_net")
    if len(lev) >= 5:
        dt = lev.index[-1].strftime("%d/%m/%Y")

        def rowc(name, s, hi, lo):
            v = float(s.iloc[-1])
            p = (s < v).mean() * 100
            note = hi if p >= 85 else (lo if p <= 15 else "Posizione nella norma rispetto agli ultimi anni")
            return f"<tr><td>{name}</td><td><b>{v:+.1f}%</b></td><td>{p:.0f}°</td><td>{note}</td></tr>".replace(".", ",")
        out.append("<h3>Cosa fanno i grandi operatori (futures E-mini S&amp;P 500, CFTC)</h3><table><tr><th>Categoria</th><th>Posizione netta (% open interest)</th><th>Percentile ({} anni)</th><th>Lettura</th></tr>".format(max(1, round(len(lev) / 52)))
                   + rowc("Fondi a leva (hedge fund)", lev, "Molto più lunghi del solito: posizionamento affollato al rialzo, più vulnerabile a una correzione", "Molto corti del solito: scommesse al ribasso affollate; un rialzo può innescare chiusure forzate")
                   + (rowc("Gestori patrimoniali", am, "Molto lunghi: gran parte della fiducia è già nei prezzi", "Molto corti: cautela estrema, poco carburante da vendere") if len(am) >= 5 else "") + "</table>"
                   f"<p class='mu'>Dati CFTC al {dt}, pubblicati ogni venerdì (ritardo di 3 giorni). Il posizionamento estremo non dice quando il mercato girerà, ma quanto è affollata una parte della barca.</p>")
    return "".join(out) or "<p class='mu'>Dati su opzioni e posizionamento non ancora disponibili: compaiono dopo i prossimi aggiornamenti giornalieri.</p>"
