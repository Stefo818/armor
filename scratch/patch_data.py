p='src/armor/quadro.py'
s=open(p,'rb').read().decode('utf-8')
a="def leggi() -> dict | None:"
b='''def _freschezza(data: str) -> str:
    """Dice con chiarezza a quando si riferiscono i dati: ultima chiusura di Borsa, oppure avviso se sono vecchi."""
    import datetime as _dt
    d = pd.Timestamp(data).normalize()
    oggi = pd.Timestamp.now(tz="Europe/Rome").tz_localize(None)
    # l'ultima seduta americana completa: ieri se e' un giorno feriale, altrimenti il venerdi'
    att = oggi.normalize() - pd.Timedelta(days=1)
    while att.weekday() > 4:
        att -= pd.Timedelta(days=1)
    if oggi.weekday() <= 4 and oggi.hour >= 23:   # dopo la chiusura americana anche oggi e' completo
        att = oggi.normalize()
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    et = f"{d.day} {mesi[d.month - 1]}"
    if d >= att:
        return f"ultima chiusura di Borsa: {et}"
    return f"<span style='color:var(--bad);font-weight:700'>dati fermi al {et}: da aggiornare</span>"


def leggi() -> dict | None:'''
assert a in s; s=s.replace(a,b,1)
a="Quadro di oggi · {_h.escape(d['data'])} · tocca un numero per il grafico · freccia = andamento in una settimana</div>"
assert a in s
s=s.replace(a,"Quadro di oggi · {_freschezza(d['data'])} · tocca un numero per il grafico · freccia = andamento in una settimana</div>",1)
open(p,'wb').write(s.encode('utf-8'))
