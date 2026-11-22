"""Correzione delle previsioni a ore (PROTOCOLLO_MINIMI.md, emendamento 1).

Due difetti misurati:
1. la spinta di rimbalzo si accendeva senza guardare la tendenza, ma su due anni di dati orari il
   rimbalzo esiste solo sopra la media a 200 giorni (57% a 6 ore) e si rovescia sotto (46%);
2. era una quantita' fissa, non proporzionale a quanto il mercato puo' muoversi: a mercati chiusi il
   rumore va a zero, la spinta resta intera e la probabilita' di rialzo schizza.
"""


def edit(p, pairs):
    b = open(p, "rb").read()
    for o, n in pairs:
        o, n = o.encode(), n.encode()
        assert b.count(o) == 1, (p, o[:70])
        b = b.replace(o, n)
    open(p, "wb").write(b)


VECCHIO_COST = '''DERIVA_RIMBALZO = {1.0: 0.0002, 3.0: 0.0004, 6.0: 0.0007, 12.0: 0.0011}
SOGLIA_RIMBALZO = -0.010'''
NUOVO_COST = '''# La deriva è espressa in frazione dello scarto tipico, non in punti fissi: così sparisce da sola quando
# i mercati sono chiusi e non può più muoversi nulla (prima restava intera e la probabilità di rialzo schizzava).
DERIVA_RIMBALZO = {1.0: 0.095, 3.0: 0.111, 6.0: 0.134, 12.0: 0.149}
SOGLIA_RIMBALZO = -0.010
# Emendamento 1: su 13.710 ore (2024-2026) il rimbalzo dopo un calo dell'1% esiste solo con l'indice sopra
# la media a 200 giorni (sale nel 55-57% dei casi, 1.111 ore). Sotto quella media si rovescia: 46-50%
# (380 ore), e con il mercato oltre il 7% sotto il massimo 46-49% con mediana negativa. Sotto la media
# la deriva viene quindi azzerata: si toglie una spinta che i dati contraddicono, senza scommettere al
# contrario su un campione piccolo.'''

VECCHIO_USO = '''        rimb = mercato.get("es_24h") is not None and mercato["es_24h"] <= SOGLIA_RIMBALZO
        if rimb:
            x = x + DERIVA_RIMBALZO[h]'''
NUOVO_USO = '''        rimb = (mercato.get("es_24h") is not None and mercato["es_24h"] <= SOGLIA_RIMBALZO
                and not mercato.get("sotto_ma200", False))
        if rimb:
            x = x + DERIVA_RIMBALZO[h] * scala'''

edit("src/armor/ore.py", [(VECCHIO_COST, NUOVO_COST), (VECCHIO_USO, NUOVO_USO)])

VECCHIO_MERC = '''    vun = vx[vx.index <= ora - pd.Timedelta(minutes=58)]'''
NUOVO_MERC = '''    try:   # tendenza di fondo: sotto la media a 200 giorni il rimbalzo dopo i cali non c'è (emendamento 1)
        from . import store
        sp = store.load("sp500").dropna()
        if len(sp) > 200:
            rec["sotto_ma200"] = bool(float(sp.iloc[-1]) < float(sp.rolling(200).mean().iloc[-1]))
    except Exception:  # noqa: BLE001
        pass
    vun = vx[vx.index <= ora - pd.Timedelta(minutes=58)]'''
edit("src/armor/ore.py", [(VECCHIO_MERC, NUOVO_MERC)])
print("applicato")
