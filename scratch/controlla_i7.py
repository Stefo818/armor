import sys
sys.path.insert(0, '/home/claude/armor/src')
from armor import semafori
for key in ("fondi_breve", "buffett"):
    s = semafori.series_of(key).dropna()
    r = s.expanding(min_periods=40).rank(pct=True) * 100
    print(key, len(s), s.index[0].date(), s.index[-1].date())
    print(" ultimi valori:", s.tail(4).round(2).tolist())
    print(" percentile in espansione:", r.tail(6).round(1).tolist())
    print(" percentile su tutta la storia:", round(float((s < s.iloc[-1]).mean() * 100), 1))
