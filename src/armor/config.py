"""Configurazione unica di Armor (orizzonti, soglie, variabili del modello)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SERIES = DATA / "series"
ARCHIVE = DATA / "archive"
STATUS_FILE = DATA / "status.json"
JOURNAL = DATA / "journal.csv"
OUTCOMES = DATA / "outcomes.csv"
VALIDATION = DATA / "validation.csv"
CALIBRATION = DATA / "calibration.csv"
RISK_HISTORY = DATA / "risk_history.csv"
BACKTEST_RET = DATA / "backtest_returns.csv"
REPORT_HTML = ROOT / "Armor_dashboard.html"

MODEL_VERSION = "A1"

# orizzonti in giorni di borsa (10 giorni di calendario = 7 sedute)
HORIZONS = {"10g": 7, "1m": 21, "3m": 63, "6m": 126}
HZ_LABEL = {"10g": "10 giorni", "1m": "1 mese", "3m": "3 mesi", "6m": "6 mesi"}
# soglie di calo (%) stimate per ogni orizzonte; la prima volta e' mostrata per prima
TARGETS = {"10g": [5], "1m": [5, 10], "3m": [10, 15], "6m": [10, 20]}
PRIMARY = {"10g": 5, "1m": 10, "3m": 10, "6m": 10}

# variabili del modello: solo prezzi dell'S&P 500 (storia dal 1928, molte crisi)
FEATURES = ["rv21", "rv63", "rv_ratio", "dd252", "ma200", "ma50_200", "mom63", "worst_day"]
BASELINE_FEATURES = ["dd252", "ma200", "mom63"]   # modello semplice di confronto

LOGIT_C = 0.1
MIN_EVENTS = 15
# rapporto tra probabilita' stimata e frequenza storica -> livello
LEVELS = [(0.6, "Basso"), (1.3, "Normale"), (2.0, "Elevato"), (1e9, "Alto")]
VERDICT = {"Basso": "Favorevole", "Normale": "Neutro", "Elevato": "Prudenza", "Alto": "Rischio alto"}
