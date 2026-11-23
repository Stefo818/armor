def rw(p, fn):
    s = open(p, 'rb').read().decode('utf-8'); n = fn(s); assert n != s, p; open(p, 'wb').write(n.encode('utf-8'))
def sub(a, b):
    def f(s):
        assert a in s, a[:70]; return s.replace(a, b, 1)
    return f
def chain(*fs):
    def f(s):
        for g in fs: s = g(s)
        return s
    return f
rw('src/armor/titan.py', chain(
 sub('''    fast = ((1.0 - df["p3_stress"] / 100.0) + (1.0 - df["p6_stress"] / 100.0)
            + expit(clean_series(df["holo_rebound_z"]) + 0.35 * df["credit_lead_10d"] + 0.25 * df["z_dark_pool_buy"] - 0.20 * df["z_cot_inst_exit"])) / 3.0''',
     '''    reb = expit(clean_series(df["holo_rebound_z"]) + 0.35 * df["credit_lead_10d"] + 0.25 * df["z_dark_pool_buy"] - 0.20 * df["z_cot_inst_exit"])
    fast = ((1.0 - df["p3_stress"] / 100.0) + (1.0 - df["p6_stress"] / 100.0) + reb) / 3.0'''),
 sub('''    bull = 0.30 * fast + 0.70 * slow
''', '''    bull = 0.30 * fast + 0.70 * slow
    # parti dell'Indice Armor, in "rischio" 1-100 (solo per mostrarle: non cambiano il calcolo)
    wst = 0.40 * (1.0 - w_mod) + 0.25 * w_mod
    dir_rest = (slow - wst * (1.0 - st)) / (1.0 - wst)
    df["a_paura"] = df["p3_stress"]
    df["a_liquidita"] = df["p6_stress"]
    df["a_rimbalzo"] = np.clip(100.0 * (1.0 - reb), 1.0, 100.0)
    df["a_stress"] = np.clip(100.0 * st, 1.0, 100.0)
    df["a_ciclo"] = np.clip(100.0 * (1.0 - dir_rest), 1.0, 100.0)
'''),
))
rw('src/armor/titan_job.py', sub('cols = ["armor_index", "armor_tarato", "super_armor_index", "lost_decade_radar"] + [f"p{i}_stress" for i in range(1, 7)]',
   'cols = ["armor_index", "armor_tarato", "super_armor_index", "lost_decade_radar"] + [f"p{i}_stress" for i in range(1, 7)] + ["a_paura", "a_liquidita", "a_rimbalzo", "a_stress", "a_ciclo"]'))
