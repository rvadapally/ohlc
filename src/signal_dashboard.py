#!/usr/bin/env python3
"""
Signal dashboard ETL script.

This module downloads historical price and volume data for IBIT, MSTR and BTC,
computes standardised z-score signals, and writes the full history to a CSV
file. The latest snapshot is also printed to the console.

Usage:
    python signal_dashboard.py [outfile] [--start YYYY-MM-DD]
"""
from __future__ import annotations

import sys
import pathlib
from datetime import date
from typing import Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# configurable look-back windows
TREND_LEN = 20
Z_NORM_PRICE_WINDOW = 60
RV_WINDOW = 30
Z_NORM_RV_WINDOW = 120
Z_NORM_VOLUME_WINDOW = 60
ANNUALISATION_DAYS = 252

TICKERS = {
    "IBIT": "IBIT",
    "MSTR": "MSTR",
    "BTC": "BTC-USD",
}


def zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score with population std-dev."""
    r = series.rolling(window)
    return (series - r.mean()) / r.std(ddof=0)


def realised_vol(log_returns: pd.Series, span: int = RV_WINDOW,
                 trading_days: int = ANNUALISATION_DAYS) -> pd.Series:
    """Annualised realised volatility."""
    return np.sqrt(trading_days) * log_returns.rolling(span).std(ddof=0)


def fetch_data(start: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Download adjusted close and volume."""
    price = yf.download(list(TICKERS.values()), start=start, progress=False)["Adj Close"]
    volume = yf.download(list(TICKERS.values()), start=start, progress=False)["Volume"]
    price = price.rename(columns={v: k for k, v in TICKERS.items()})
    volume = volume.rename(columns={v: k for k, v in TICKERS.items()})
    return price, volume


def align_to_nyse(price: pd.DataFrame, volume: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Force BTC prints onto the NYSE calendar."""
    btc_col = "BTC"
    nyse_days = price.drop(columns=[btc_col]).index
    price.loc[nyse_days, btc_col] = price[btc_col].loc[nyse_days].ffill()
    volume.loc[nyse_days, btc_col] = volume[btc_col].loc[nyse_days].ffill()
    return price.loc[nyse_days], volume.loc[nyse_days]


def build_signals(price: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    log_p = np.log(price)
    ret = log_p.diff()

    dist = log_p - log_p.rolling(TREND_LEN).mean()
    z_price = dist.apply(zscore, window=Z_NORM_PRICE_WINDOW)

    rv30 = ret.apply(realised_vol, span=RV_WINDOW)
    z_rv30 = rv30.apply(zscore, window=Z_NORM_RV_WINDOW)

    log_vol = np.log(volume.replace(0, np.nan))
    z_vol = log_vol.apply(zscore, window=Z_NORM_VOLUME_WINDOW)

    signals = pd.concat({
        "zPrice": z_price,
        "zRV30": z_rv30,
        "zVol": z_vol,
        "RV30": rv30,
    }, axis=1).dropna()

    return signals


def main() -> None:
    outfile = pathlib.Path("signals.csv")
    start = "2024-01-01"

    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        outfile = pathlib.Path(sys.argv[1])
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]

    for i, arg in enumerate(args):
        if arg == "--start" and i + 1 < len(args):
            start = args[i + 1]

    price, volume = fetch_data(start)
    price, volume = align_to_nyse(price, volume)
    signals = build_signals(price, volume)

    signals.to_csv(outfile, float_format="%.6f")
    latest = signals.iloc[-1]

    print(f"\n=== Latest z-scores (as of {latest.name.date()}) ===")
    for col in ["IBIT", "MSTR", "BTC"]:
        zp = latest["zPrice"][col]
        zv = latest["zVol"].get(col, np.nan)
        zrv = latest["zRV30"][col]
        out = f"{col:<5s}  zPrice={zp:+6.2f}  zRV30={zrv:+6.2f}"
        if not np.isnan(zv):
            out += f"  zVol={zv:+6.2f}"
        print(out)

    print(f"\nSignals saved to: {outfile.resolve()}")


if __name__ == "__main__":
    main()
