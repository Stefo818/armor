"""Le etichette di direzione vanno misurate contro il normale, non contro il 50%.

Su 9.290 giorni dal 1990 la Borsa sale nel 53,6% dei casi: sopra la media a 200 giorni nel 54,1%,
sotto nel 52,2%. Quindi «53% di rialzo» e' la normalita', non una tendenza al rialzo. Le soglie
vengono ricentrate sul 53%.
"""


def edit(p, pairs):
    b = open(p, "rb").read()
    for o, n in pairs:
        o, n = o.encode(), n.encode()
        assert b.count(o) == 1, (p, o[:70])
        b = b.replace(o, n)
    open(p, "wb").write(b)


VECCHIO = '''def _direzione(a: dict) -> tuple[str, str]:
    """Etichetta di direzione dalla probabilità di stare sopra o sotto il prezzo attuale."""
    su = a["p_su"]
    if su >= 0.58:
        return "Più probabile un rialzo", "pos"
    if su >= 0.53:
        return "Lieve tendenza al rialzo", "pos"
    if su <= 0.42:
        return "Più probabile un calo", "neg"
    if su <= 0.47:
        return "Lieve tendenza al calo", "neg"
    return "Direzione indecisa", ""'''

NUOVO = '''# Dal 1990 la Borsa chiude in rialzo nel 53,6% dei giorni (54,1% sopra la media a 200 giorni, 52,2% sotto):
# una probabilità di rialzo del 53% è la normalità, non una tendenza. Le soglie sono centrate lì, non sul 50%.
NORMALE_SU = 0.535


def _direzione(a: dict) -> tuple[str, str]:
    """Etichetta di direzione, misurata contro il normale (53%) e non contro il 50%."""
    su = a["p_su"]
    if su >= NORMALE_SU + 0.07:
        return "Più probabile un rialzo", "pos"
    if su >= NORMALE_SU + 0.03:
        return "Lieve tendenza al rialzo", "pos"
    if su <= NORMALE_SU - 0.09:
        return "Più probabile un calo", "neg"
    if su <= NORMALE_SU - 0.05:
        return "Lieve tendenza al calo", "neg"
    return "Come al solito", ""'''

edit("src/armor/ore_ui.py", [(VECCHIO, NUOVO)])
print("applicato")
