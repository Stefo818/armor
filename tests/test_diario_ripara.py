import shutil
from pathlib import Path

from armor import journal3

REALE = Path(__file__).resolve().parents[1] / "data" / "journal_v3.csv"


def _riga(asof, modello, ts="2026-01-01T00:00:00Z"):
    return {"ts_utc": ts, "asof": asof, "kind": "previsione", "model": modello, "variante": modello, "horizon": "tutti", "codice": "x",
            "parametri": "{}", "ingressi": "{}", "risultati": '{"a":1,"b":"x,y"}'}


def test_ripara_righe_doppie(tmp_path):
    f = tmp_path / "j.csv"
    journal3._append([_riga("2026-01-02", "A1"), _riga("2026-01-02", "P")], f)
    base = f.read_text(encoding="utf-8")
    # due esecuzioni partono dallo stesso diario: la seconda scrive righe doppie dopo la prima
    journal3._append([_riga("2026-01-03", "A1"), _riga("2026-01-03", "P")], f)
    seconda = f.read_text(encoding="utf-8")
    f.write_text(base, encoding="utf-8")
    journal3._append([_riga("2026-01-03", "A1", "2026-01-03T01:00:00Z"), _riga("2026-01-03", "P", "2026-01-03T01:00:00Z"), _riga("2026-01-04", "A1")], f)
    righe_b = f.read_text(encoding="utf-8").splitlines()[3:]
    f.write_text(seconda + "\n".join(righe_b) + "\n", encoding="utf-8")   # unione sbagliata: tutte le righe una dopo l'altra
    assert not journal3.verifica_estrema(f)[0]
    scarti = tmp_path / "s.csv"
    sc, rl = journal3.ripara(f, scarti, log=lambda *a: None)
    assert sc == 2 and rl == 1
    ok, n, err = journal3.verifica_estrema(f)
    assert ok and n == 5, (ok, n, err)
    assert scarti.exists() and len(scarti.read_text(encoding="utf-8").splitlines()) == 3


def test_ripara_non_tocca_diario_sano_o_modificato(tmp_path):
    f = tmp_path / "j.csv"
    journal3._append([_riga("2026-01-02", "A1"), _riga("2026-01-03", "A1")], f)
    assert journal3.ripara(f, tmp_path / "s.csv", log=lambda *a: None) == (0, 0)
    t = f.read_text(encoding="utf-8").replace('""a"":1', '""a"":2')
    f.write_text(t, encoding="utf-8")
    assert journal3.ripara(f, tmp_path / "s.csv", log=lambda *a: None) == (0, 0)
    assert not journal3.verifica_estrema(f)[0]


def test_diario_reale_riparabile(tmp_path):
    if not REALE.exists():
        return
    f = tmp_path / "j.csv"
    shutil.copy(REALE, f)
    journal3.ripara(f, tmp_path / "s.csv", log=lambda *a: None)
    assert journal3.verifica_estrema(f)[0]
