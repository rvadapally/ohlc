Below is a self-contained specification your engineers can follow straight away.
Feel free to prune or fine-tune, but it should give them everything they need for v1.

---

## 0 ― Executive summary (one-liner)

> **Goal** : Nightly (or intra-day) pipeline that ingests BTC spot, IBIT ETF and MSTR equity market data, computes standardised z-score signals (price-distance, 30-day realised vol, volume surprise, optional IV-vs-RV), stores the results, and renders a lightweight dashboard that lets a trader click any row to see the full “trade signal card”.

---

## 1 ― Functional scope

| #       | Capability                   | Detail                                                                                                                                                                                                                                                                                                                                    |        |        |          |
| ------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------ | -------- |
| **F-1** | **Automated data ingestion** | Pull **Adj Close** & **Volume** for IBIT, MSTR, BTC-USD once per run (default = end-of-day 16:15 ET).  Source = *yfinance* to start; swap to paid feed later without breaking interface.                                                                                                                                                  |        |        |          |
| **F-2** | **Signal engine**            | For each asset, compute: <br>• `zPrice` (distance of log-price from 20-day SMA, normalised over 60 days) <br>• `zRV30` (annualised 30-day realised σ, normalised over 120 days) <br>• `zVol` (log-volume, 60-day z-score) <br>• `RV30` raw (for IV/RV spread later)<br>All calcs in **Python / pandas**, driven by `signal_dashboard.py`. |        |        |          |
| **F-3** | **Persist signals**          | Append to a **signals** table (CSV in v1, migrate to TimescaleDB or DuckDB when scaling).  Schema = `trade_date                                                                                                                                                                                                                         | metric | ticker | value`. |
| **F-4** | **Dashboard**                | Web UI (Streamlit is fine) that shows: <br>1. **Latest snapshot table** with z-scores for BTC, IBIT, MSTR (colour-graded cells).<br>2. Row click → right-hand “signal card” with: • metric values • quick narrative (“IBIT zPrice −2.4 σ with capitulation volume: mean-reversion long bias”) • link to raw CSV.                          |        |        |          |
| **F-5** | **Scheduler & logging**      | Daily cron / Windows Task Scheduler entry.  Log fetch status, row count, min/max dates, errors.                                                                                                                                                                                                                                           |        |        |          |
| **F-6** | **Config & secrets**         | Simple `.env` for API keys (e.g. paid data later).                                                                                                                                                                                                                                                                                        |        |        |          |
| **F-7** | **Unit tests**               | Happy-path test for each indicator; regression test that yesterday’s run wrote one new date row.                                                                                                                                                                                                                                          |        |        |          |

---

## 2 ― Non-functional requirements

| Topic             | Requirement                                                              |
| ----------------- | ------------------------------------------------------------------------ |
| **Latency**       | v1 EOD run must finish < 60 s on a dev laptop.                           |
| **Refresh**       | Default frequency = daily; allow CLI flag `--intraday` for ad-hoc runs.  |
| **Portability**   | Python 3.11, no OS-specific calls; Dockerfile supplied.                  |
| **Observability** | Console + rolling log file; exit-code 0/1 for scheduler.                 |
| **Security**      | No credentials in code; `.env` git-ignored; optional Vault later.        |
| **Extensibility** | Signal class registry so adding `zIV_RV` or factor residuals is drop-in. |

---

## 3 ― System architecture (logical)

```
┌──────────────┌      fetch + calc      ┌──────────────┐
│ Scheduler    │ ────────────────────► │  ETL/Calc │
│ (cron/Task)  │                        └────────┐
└──────────────┘                             │ writes CSV/DB
                                             │
                                        ┌─────────────────┐
                                        │  Storage  │
                                        └───────────────┘
                                             │ read
                                             │
                                        ┌─────────────────┐
                                        │ Dashboard │◄┌── user clicks
                                        └───────────────┘
```

---

## 4 ― Detailed component spec

### 4.1  ETL/Calc module (`signal_dashboard.py`)

| Section        | Key points                                                                            |
| -------------- | ------------------------------------------------------------------------------------- |
| **Fetch**      | `yfinance.download([...], start, progress=False)['Adj Close']` + `['Volume']`.        |
| **Align**      | Forward-fill BTC to NYSE calendar; drop weekends for equities.                        |
| **Indicators** | Functions `zscore(series, win)` & `realised_vol()`.  Constants at top for look-backs. |
| **Outputs**    | 1) Write full history to `signals.csv` (over-write). 2) Print latest snapshot.        |
| **CLI**        | `python signal_dashboard.py [outfile] [--start 2024-01-01]`.                          |
| **Packaging**  | Place in `/src`.  Use `__main__` guard.                                               |

### 4.2  Dashboard (suggested Streamlit MVP)

| UI element      | Spec                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Table**       | `st.dataframe` of latest snapshot; conditional formatting (green = < −1, grey = -1 … +1, red = > +1).                          |
| **Row click**   | `st.experimental_data_editor` or plain table + radio buttons → capture ticker.                                                 |
| **Signal card** | Pull row dict → template string: <br>“**{ticker}**: zPrice {zp:+.2f}σ; zVol {zv:+.2f}σ; zRV30 {zrv:+.2f}σ. **Bias**: {logic}.” |
| **Download**    | `st.download_button("CSV", data=open('signals.csv','rb'))`.                                                                    |
| **Navigation**  | Left sidebar: date-range filter, refresh button (runs script).                                                                 |

*Optional*: Chart modal showing last-90-days zPrice line.

### 4.3  Storage

* v1 = `signals.csv` in project root.
* v1.1 = DuckDB file for SQL joins; minimal code change.
* v2 = TimescaleDB/Postgres + SQLAlchemy models.

### 4.4  Scheduler / Ops

| Item        | Spec                                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| **Unix**    | `0 16 * * 1-5 /path/to/venv/bin/python /app/src/signal_dashboard.py >> /var/log/btc_sig.log 2>&1`       |
| **Windows** | Task Scheduler daily 16:15-16:20 ET.                                                                    |
| **Docker**  | Multi-stage Dockerfile (`python:3.11-slim`, copy src, `CMD ["python","/app/src/signal_dashboard.py"]`). |

---

## 5 ― File & repo structure

```
/btc-signal-dashboard
│
├── src/
│   ├── signal_dashboard.py
├── dashboard/
│   ├── app.py            # streamlit
├── tests/
│   ├── test_signals.py
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## 6 ― Deliverables & timeline (suggested)

| Week  | Deliverable                                                                        | Owner         |
| ----- | ---------------------------------------------------------------------------------- | ------------- |
| **1** | Repo scaffold, `requirements.txt`, data-ingest script fetching raw prices into CSV | Quant dev     |
| **2** | Full indicator functions + unit tests (pytest)                                     | Quant dev     |
| **3** | Streamlit dashboard MVP (static table, manual refresh)                             | Front-end dev |
| **4** | Scheduler in lower-env, Docker container, logging                                  | DevOps        |
| **5** | UAT: verify metrics vs external Bloomberg; hand-off to trading desk                | QA + Trader   |
| **6** | Nice-to-have: IV-vs-RV column, param panel, chart modal                            | Quant dev     |

---

## 7 ― Acceptance criteria

* **AC-1**: A fresh clone + `pip install -r requirements.txt` + `python signal_dashboard.py` creates `signals.csv` with ≥ 300 trading-day rows.
* **AC-2**: For a known date (supply in test), zPrice, zRV30, zVol match benchmark Excel within ±1e-6.
* **AC-3**: Dashboard loads in < 2 s, shows coloured table, clicking “IBIT” reveals narrative card.
* **AC-4**: Cron job writes a new row the next trading day; log shows “Run OK”.
* **AC-5**: No secrets checked into git; `.env` can override API keys and output path.

---

## 8 ― Future roadmap (out of v1 scope but easy next steps)

1. **Add implied-vol data** via Cboe DataShop → compute `zIV_RV`.
2. **REST API** (FastAPI) to serve `/latest` JSON for other tools.
3. **Alerting**: Slack webhook when `|zPrice| > 2.5` **and** `zVol > 1.5`.
4. **Live intraday micro-cycle**: 5-min candles for BTC vs MSTR with WebSockets.
5. **ML ranking**: feed signals into Gradient Boosting model for %-return forecast.

---

### Hand-off checklist

* [ ] Repo created with structure above
* [ ] This spec committed as `/docs/spec_v1.md`
* [ ] Trello / JIRA tickets mapped to Week column tasks
* [ ] Dev environment instructions in README

Once your team signs off on scope, they can start sprint 1 immediately.
