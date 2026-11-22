"""Applica la scala tarata dell'Indice Armor (PROTOCOLLO_PILASTRI_7_8, emendamento 1 parte C)."""


def edit(p, pairs):
    b = open(p, "rb").read()
    for o, n in pairs:
        o, n = o.encode(), n.encode()
        assert b.count(o) == 1, (p, o[:70])
        b = b.replace(o, n)
    open(p, "wb").write(b)


VECCHIO = '    df["armor_index"] = clean_series(np.clip(40.5 + (100.0 * (1.0 - bull) - 48.0) * 0.65, 1.0, 100.0), 40.0)'
NUOVO = VECCHIO + """
    # Scala tarata per chi legge (PROTOCOLLO_PILASTRI_7_8.md, emendamento 1 parte C): trasformazione monotona,
    # non cambia l'ordine dei giorni ne' alcun risultato gia' pubblicato, sposta solo i confini. I punti di
    # aggancio sono i percentili dell'Indice Armor sulle sole crisi finanziarie dal 1986 corrispondenti a
    # 40, 60 e 80 del Super Armor. La colonna grezza resta e continua ad alimentare i calcoli interni.
    df["armor_tarato"] = np.interp(df["armor_index"].values, [1.0, 39.43, 49.82, 56.83, 100.0], [1.0, 40.0, 60.0, 80.0, 100.0])"""

edit("src/armor/titan.py", [(VECCHIO, NUOVO)])

L_LEGGI = '        return pd.read_csv(FILE, index_col=0, parse_dates=True).dropna(subset=["armor_index", "super_armor_index"])'
N_LEGGI = '''        d = pd.read_csv(FILE, index_col=0, parse_dates=True).dropna(subset=["armor_index", "super_armor_index"])
        if "armor_tarato" in d:   # scala tarata: 40 difficolta', 60 pericolo, 80 rischio di crollo
            d["armor_index"] = d["armor_tarato"]
        return d'''
L_NOTA = '            + _mini("Indice Armor", "armor", a, "Giudizio rapido: 40 è la soglia di stress.")'
N_NOTA = '            + _mini("Indice Armor", "armor", a, "Da 40 mercato in difficoltà, da 60 in pericolo, da 80 rischio di crollo.")'
L_ZONE = '"<b>40 è la soglia di stress.</b> Zone: sotto 35 tranquillo, 35-40 neutro, 40-45 allarme, da 45 pericolo.</p></div>"'
N_ZONE = ('"<b>Le zone, tarate sulle sole crisi finanziarie dal 1986.</b> Sotto 40 tranquillo: il calo al 10% è poi arrivato nel 12,9% dei casi. "\n'
          '            "Da 40 mercato in difficoltà: 39,8%. Da 60 in pericolo: 85,4%. Da 80 rischio di crollo: in tutti i 66 giorni visti, che però sono due o tre episodi soli. "\n'
          '            "La scala non cambia cosa sa il modello, sposta solo dove cadono i confini.</p></div>"')
edit("src/armor/titan_schede.py", [(L_LEGGI, N_LEGGI), (L_NOTA, N_NOTA), (L_ZONE, N_ZONE)])
print("applicato")
