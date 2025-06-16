# BTC Signal Dashboard

This project pulls historical price and volume data for IBIT, MSTR and BTC,
computes z-score based indicators and stores them in `signals.csv`. A simple
Streamlit dashboard displays the latest snapshot.

## Quick start

```
pip install -r requirements.txt
python src/signal_dashboard.py
streamlit run dashboard/app.py
```

Signals are written to `signals.csv`. Customize the output path via `.env` or
the command line argument.
