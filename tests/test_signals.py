import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import numpy as np

from signal_dashboard import zscore, realised_vol, build_signals


def test_zscore_simple():
    s = pd.Series([1, 1, 1, 1, 1], dtype=float)
    result = zscore(s, window=5)
    assert pd.isna(result.iloc[-1])


def test_realised_vol():
    ret = pd.Series([0.0, 0.1, -0.1, 0.05], dtype=float)
    rv = realised_vol(ret, span=2, trading_days=2)
    assert len(rv.dropna()) > 0


def test_build_signals():
    dates = pd.date_range('2024-01-01', periods=65, freq='B')
    price = pd.DataFrame({'IBIT': np.linspace(1, 65, 65),
                          'MSTR': np.linspace(1, 65, 65),
                          'BTC': np.linspace(1, 65, 65)}, index=dates)
    volume = pd.DataFrame({'IBIT': 1, 'MSTR': 1, 'BTC': 1}, index=dates)
    sig = build_signals(price, volume)
    assert {'zPrice', 'zRV30', 'zVol', 'RV30'} <= set(sig.columns.get_level_values(0))
