# 4. Write Protocol (STRICT)

Each operation:

1. Generate `request_id` (`uuid4.hex`)
2. Append event to Google Sheets
3. Confirm write success
4. Rely on idempotency on future retries
