"""Navigazione a due livelli (Patch 51): cinque sezioni con icona (Oggi, Mercati, Rischio, Grafici, Il mio piano) e, sotto, le pagine di quella sezione.
Patch 57: sette sezioni (nuove: Previsioni e Calendario); «Notizie» e «Calendario» compaiono sia in Oggi sia nella propria sezione."""

def _svg(inner: str) -> str:
    return f"<svg viewBox='0 0 24 24' width='22' height='22' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>{inner}</svg>"


GRUPPI = [
    ("oggi", "Oggi", ["oggi", "notizie", "calendario"], _svg("<path d='M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z'/>")),
    ("mercati", "Mercati", ["mercati", "saldi", "opportunita", "aziende"],
     _svg("<path d='M6 3v3M6 15v3M12 2v4M12 12v6M18 6v3M18 16v4'/><rect x='4' y='6' width='4' height='9' rx='1'/><rect x='10' y='6' width='4' height='6' rx='1'/><rect x='16' y='9' width='4' height='7' rx='1'/>")),
    ("previsioni", "Previsioni", ["previsioni", "modelli", "fiducia"], _svg("<circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/><path d='M3 12h2M19 12h2'/>")),
    ("rischio", "Rischio", ["indici", "regime", "fondi", "valutazioni", "macro", "contesto"],
     _svg("<path d='M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z'/><path d='M8.5 12l2.5 2.5 5-5'/>")),
    ("calendario", "Calendario", ["calendario", "notizie"], _svg("<rect x='3' y='5' width='18' height='16' rx='3'/><path d='M3 10h18M8 3v4M16 3v4'/><path d='M8 14h2M12 14h2M16 14h0M8 17h2'/>")),
    ("grafici", "Grafici", ["grafici", "storico", "archivio"], _svg("<path d='M3 3v18h18'/><path d='M7 15l4-5 3 3 5-7'/>")),
    ("piano", "Piano", ["portafoglio", "allarmi", "verifiche"], _svg("<rect x='3' y='6' width='18' height='14' rx='3'/><path d='M3 10h18M16 15h2'/>")),
]

CSS = """
.navw{position:sticky;top:0;z-index:7;background:var(--bg);margin:0 -2px 10px;padding-top:6px}
.gnav{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(48px,1fr);gap:5px;overflow-x:auto;scrollbar-width:none}.gnav::-webkit-scrollbar{display:none}
.gnav button{display:flex;flex-direction:column;align-items:center;gap:3px;padding:8px 0 7px;border:1px solid var(--bd);border-radius:14px;background:var(--card);color:var(--mu);font:inherit;font-size:9.5px;letter-spacing:-.3px;font-weight:700;cursor:pointer;transition:all .15s}
.gnav button svg{width:21px;height:21px}
.gnav button.on{color:#fff;border-color:transparent;background:linear-gradient(135deg,var(--ac),#6366f1);box-shadow:0 4px 14px rgba(59,130,246,.35)}
.navw .pgnav{position:static;padding:8px 0 6px;margin:0}
.navw .pgnav button[hidden]{display:none}
.navw .pgnav button{padding:7px 13px;font-size:13px}
@media(min-width:700px){.gnav button{flex-direction:row;justify-content:center;gap:8px;font-size:14px;padding:10px;letter-spacing:0}}
.pg.on.swl{animation:swl .24s ease-out}.pg.on.swr{animation:swr .24s ease-out}@keyframes swl{from{opacity:.2;transform:translateX(34px)}to{opacity:1;transform:none}}@keyframes swr{from{opacity:.2;transform:translateX(-34px)}to{opacity:1;transform:none}}
"""


def gruppo_di(chiave: str) -> str:
    for g, _l, pagine, _i in GRUPPI:
        if chiave in pagine:
            return g
    return "oggi"


def html(pages: list[tuple[str, str]]) -> str:
    chiavi = {k for k, _ in pages}
    gb = "".join(f"<button data-g='{g}' type='button'>{ic}<span>{lab}</span></button>" for g, lab, _p, ic in GRUPPI)
    nomi = dict(pages)
    sub = "".join(f"<button data-p='{k}' data-g='{g}'>{nomi[k]}</button>" for g, _l, ps, _i in GRUPPI for k in ps if k in chiavi)
    return f"<style>{CSS}</style><div class='navw'><nav class='gnav'>{gb}</nav><nav class='pgnav'>{sub}</nav></div>"
