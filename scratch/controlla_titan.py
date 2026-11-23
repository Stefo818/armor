import pandas as pd
n = pd.read_csv('/home/claude/armor/data/titan_storia.csv', index_col=0, parse_dates=True)
o = pd.read_csv('/tmp/titan_storia_old.csv', index_col=0, parse_dates=True)
print(n.columns.tolist()[-6:], len(n), len(o))
print(n[['a_paura', 'a_liquidita', 'a_rimbalzo', 'a_stress', 'a_ciclo']].tail(3).round(1))
c = ['armor_index', 'super_armor_index', 'p3_stress']
print((n[c].reindex(o.index) - o[c]).abs().max())
print(n[['a_rimbalzo', 'a_stress', 'a_ciclo']].describe().round(1))
