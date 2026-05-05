# External Setup Actions Required

This app can run locally with `events.csv`, but Google Sheets support requires external credentials and configuration.

## Required actions from you

1. Activate the Conda environment:

```bash
conda activate expenses-app
```

2. If you want to use Google Sheets storage, provide the following environment variables in your shell or environment:

- `GOOGLE_SHEET_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
  - Path to the service account JSON credentials file
  - OR `GOOGLE_SERVICE_ACCOUNT_JSON`
  - Raw JSON content of the service account credentials

3. Save these values in a local `.env` file at the repo root if you prefer not to export them in your shell every time. The app will automatically load `.env` when it starts.

```env
GOOGLE_SHEET_ID=1Hewm-VWxq9GnECuOBHN6-7K7bZvMLpw08Wl7vq417E8
GOOGLE_APPLICATION_CREDENTIALS=/Users/liranc6/Desktop/play_with_code/expenses-app/private/expensesapp-495423-8a98bfdef311.json
```

4. Create a Google Sheet and share it with the service account email.

4. If you use local storage only, no additional setup is required.

## Google Sheets configuration details

- `GOOGLE_SHEET_ID` should be the ID from the sheet URL.
- The app expects the first worksheet to exist and will use it as the event log.
- The worksheet must have headers:
  - `event_id`
  - `request_id`
  - `timestamp_ns`
  - `type`
  - `payload_json`

## Notes

- If `GOOGLE_SHEET_ID` is set but credentials are missing, the app will warn you and fall back to local storage.
- No secret values are stored in the repository.
- Use the Streamlit UI to confirm the active storage mode.
