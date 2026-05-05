# Expenses App

An event-sourced expense ledger with Streamlit UI.

## Features

- Append-only event store
- Expense creation, editing, deletion
- Settlement events
- Deterministic replay and balance computation
- Local CSV event storage with optional Google Sheets connector

## Run locally

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Start the Streamlit app:

```bash
streamlit run app.py
```

3. Open the URL shown in the terminal.

## Storage

- Default storage: `events.csv`
- Optional Google Sheets storage via environment variables or `.env` file:
  - `GOOGLE_SHEET_ID`
  - `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SERVICE_ACCOUNT_JSON`

## Charts

- Uses Plotly for visual balance and category charts in the Streamlit UI.

## Notes

This application follows the app specification in `app_description/`:
- event log is the single source of truth
- state is derived by sorting events by `(timestamp_ns, event_id)`
- expense edit replaces full expense state
- expense deletion wins over prior history
- balances are derived from expense splits and settlement events
