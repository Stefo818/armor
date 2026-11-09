"""Parte alta della pagina Calendario (Patch 57): prossimi eventi spiegati in parole semplici e notizie raggruppate per giorno."""
import html as _h
from datetime import date, datetime, timedelta, timezone

E = _h.escape
SPIEGA = {"CPI": "Misura quanto sono saliti i prezzi negli Stati Uniti. Se è più alta del previsto, i mercati temono tassi alti più a lungo e spesso scendono.",
          "FOMC": "Riunione della banca centrale americana (la Fed) sui tassi di interesse. Le decisioni e le parole del presidente muovono tutto il mercato.",
          "NFP": "Dati sul lavoro negli Stati Uniti (nuovi posti di lavoro). Mostrano se l'economia regge e influenzano le scelte della Fed.",
          "Opzioni": "Scadenza di contratti sulle azioni: nei giorni intorno i prezzi possono muoversi in modo brusco senza una vera notizia.",
          "PIL": "Misura quanto cresce l'economia. Una frenata improvvisa preoccupa i mercati.",
          "BCE": "Riunione della banca centrale europea sui tassi: conta per i mutui e per le azioni europee."}
IMPORTANZA = {3: ("Molto importante", "ba"), 2: ("Importante", "wa"), 1: ("Di contorno", "ok")}


def eventi(oggi: date | None = None, giorni: int = 30) -> str:
    from . import extra13
    oggi = oggi or date.today()
    ev = [x for x in extra13.all_events(oggi, oggi + timedelta(days=giorni))]
    if not ev:
        return "<p class='mu'>Nessun evento importante nei prossimi giorni.</p>"
    out = ""
    for x in ev[:14]:
        d = datetime.fromisoformat(x["date"]).date()
        tra = (d - oggi).days
        quando = "oggi" if tra == 0 else "domani" if tra == 1 else f"tra {tra} giorni"
        imp, cl = IMPORTANZA.get(x["peso"], IMPORTANZA[1])
        sp = SPIEGA.get(x.get("tipo", ""), "")
        out += (f"<div class='agev'><div class='agd'><b>{d.day}</b><span>{['gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic'][d.month - 1]}</span></div>"
                f"<div class='agb'><b>{E(x['nome'])}</b> <span class='pvch {cl}'>{imp}</span><div class='mu'>{quando}</div>" + (f"<div>{E(sp)}</div>" if sp else "") + "</div></div>")
    return "<div class='agl'>" + out + "</div><p class='mu'>Nei giorni degli eventi importanti i prezzi oscillano di più: non è un motivo per cambiare il piano, ma per non reagire d'istinto.</p>"


def notizie(items: list[dict], giorni: int = 5, per_giorno: int = 5) -> str:
    now = datetime.now(timezone.utc)
    per: dict[str, list] = {}
    for i in items:
        if i.get("kind") not in ("macro", "sector") or not i.get("time"):
            continue
        try:
            t = datetime.fromisoformat(i["time"].replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            continue
        if t < now - timedelta(days=giorni):
            continue
        per.setdefault(t.date().isoformat(), []).append(i)
    if not per:
        return "<p class='mu'>Nessuna notizia recente.</p>"
    out = ""
    for g in sorted(per, reverse=True):
        d = datetime.fromisoformat(g)
        etichetta = "Oggi" if g == now.date().isoformat() else "Ieri" if g == (now.date() - timedelta(days=1)).isoformat() else d.strftime("%d/%m/%Y")
        righe = "".join(f"<div class='nzi {E(str(i.get('label', 'neutro')))}'><b>{E(i['title'].rsplit(' - ', 1)[0])}</b><div class='me'>{E(i.get('source', ''))} · {E(i.get('group', ''))}</div></div>"
                        for i in sorted(per[g], key=lambda x: -float(x.get("score", 0)))[:per_giorno])
        out += f"<h3 class='agg'>{etichetta}</h3>{righe}"
    return out + "<p><a href='#notizie' class='btn pri' data-go='notizie'>Tutte le notizie</a></p><p class='mu'>Rosso = notizia negativa per i mercati, verde = positiva, grigio = neutra. Il giudizio è automatico: serve a orientarsi, non a decidere.</p>"


CSS = """<style>.agl{display:grid;gap:10px;margin:8px 0}.agev{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--bd);border-radius:16px;padding:11px 13px;background:var(--card);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.agd{min-width:50px;text-align:center;border-radius:12px;background:linear-gradient(135deg,var(--ac),#6366f1);color:#fff;padding:6px 0}.agd b{display:block;font-size:22px;line-height:1.1}.agd span{font-size:11px;text-transform:uppercase;letter-spacing:.6px}
.agb{flex:1;font-size:13.5px;line-height:1.4}.agg{margin:16px 0 4px;font-size:15px}.pg .nzi{border-radius:14px;padding:10px 13px;margin:7px 0;border:1px solid var(--bd);border-left-width:5px;background:var(--card)}.pg .nzi.positivo{border-left-color:var(--ok)}.pg .nzi.negativo{border-left-color:var(--bad)}.pg .nzi.neutro{border-left-color:var(--mu)}</style>"""


def pagina(items: list[dict], calendario_html: str, previsioni_recenti: str) -> str:
    return (CSS + "<h2>Calendario: eventi, previsioni e notizie</h2><div class='explain'><p><b>Chiave di lettura.</b> Qui trovi in un posto solo cosa sta per succedere (eventi che muovono i mercati), "
            "come sono andate le previsioni passate e le notizie degli ultimi giorni. Prima gli eventi in arrivo, poi il calendario completo da sfogliare, poi le previsioni e le notizie.</p></div>"
            "<h3>Prossimi eventi</h3>" + eventi() + "<h3 style='margin-top:24px'>Calendario completo</h3>" + calendario_html
            + "<h3 style='margin-top:24px'>Previsioni passate e risultato reale (ultime)</h3>" + previsioni_recenti
            + "<p><a href='#previsioni' class='btn pri' data-go='previsioni'>Tabella completa nelle Previsioni</a></p><h3 style='margin-top:24px'>Notizie degli ultimi giorni</h3>" + notizie(items))
