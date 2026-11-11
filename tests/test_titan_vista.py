import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import titan_vista as tvista  # noqa: E402


def test_titan_vista_fresco_vecchio_e_spento(tmp_path, monkeypatch):
    idx = pd.bdate_range("2023-01-02", periods=700)
    pd.DataFrame({"armor_index": [45.0] * 700}, index=idx).rename_axis("date").to_csv(tmp_path / "t.csv")
    monkeypatch.setattr(tvista, "FILE", tmp_path / "t.csv")
    assert tvista.serie("armor_index", idx[-1]) is not None
    assert tvista.serie("armor_index", idx[-1] + pd.Timedelta(days=30)) is None   # file vecchio: si usano i valori di prima
    assert tvista.serie("manca", idx[-1]) is None
    monkeypatch.setattr(tvista, "ATTIVO", False)
    assert tvista.serie("armor_index", idx[-1]) is None
    monkeypatch.setattr(tvista, "FILE", tmp_path / "non_esiste.csv")
    monkeypatch.setattr(tvista, "ATTIVO", True)
    assert tvista.serie("armor_index", idx[-1]) is None
