import numpy as np
import pandas as pd

from armor import difensivita as d


def test_pe_senza_futuro():
    s = pd.Series(np.arange(1, 700, dtype=float), index=pd.bdate_range("2000-01-03", periods=699))
    p = d._pe(s, 504)
    assert p.iloc[:503].isna().all() and p.iloc[-1] == 1.0
