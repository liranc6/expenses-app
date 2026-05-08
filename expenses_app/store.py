import csv
import json
import os
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from expenses_app.model import Event


gsheet_support = False
try:
    import gspread
    from google.oauth2.service_account import Credentials
    gsheet_support = True
except ImportError:
    gsheet_support = False


class LocalEventStore:
    HEADER = ["event_id", "request_id", "timestamp_ns", "type", "payload_json"]

    def __init__(self, path: str = "events.csv"):
        self.path = path
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True) if os.path.dirname(self.path) else None
            with open(self.path, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.HEADER)
                writer.writeheader()
        self.events = self.load()
        self.request_index = {event.request_id for event in self.events}
        self.event_index = {event.event_id for event in self.events}

    def load(self) -> List[Event]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return [Event.from_record(row) for row in reader if row.get("event_id")]

    def append(self, event: Event) -> Event:
        if event.request_id in self.request_index or event.event_id in self.event_index:
            return event
        with open(self.path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.HEADER)
            writer.writerow(event.to_record())
        self.events.append(event)
        self.request_index.add(event.request_id)
        self.event_index.add(event.event_id)
        return event


class GoogleSheetsEventStore:
    HEADER = ["event_id", "request_id", "timestamp_ns", "type", "payload_json"]

    def __init__(self, sheet_id: str, credentials_path: Optional[str] = None, credentials_json: Optional[str] = None):
        if not gsheet_support:
            raise RuntimeError("Google Sheets support is not available. Install gspread and google-auth.")
        self.sheet_id = sheet_id
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.client = self._build_client()
        self.sheet = self.client.open_by_key(self.sheet_id)
        self.worksheet = self.sheet.get_worksheet(0)
        if self.worksheet is None:
            self.sheet.add_worksheet(title="Events", rows=1000, cols=10)
            self.worksheet = self.sheet.get_worksheet(0)
        self._ensure_header()
        self.events = self.load()
        self.request_index = {event.request_id for event in self.events}
        self.event_index = {event.event_id for event in self.events}

    def _build_client(self):
        if self.credentials_path:
            return gspread.service_account(filename=self.credentials_path)
        credentials_data = json.loads(self.credentials_json) if self.credentials_json else None
        if credentials_data:
            creds = Credentials.from_service_account_info(credentials_data)
            return gspread.authorize(creds)
        raise ValueError("Google Sheets credentials are required via path or JSON string")

    def _ensure_header(self) -> None:
        values = self.worksheet.row_values(1)
        if values != self.HEADER:
            self.worksheet.insert_row(self.HEADER, index=1)

    def load(self) -> List[Event]:
        records = self.worksheet.get_all_records()
        return [Event.from_record({
            "event_id": record.get("event_id", ""),
            "request_id": record.get("request_id", ""),
            "timestamp_ns": str(record.get("timestamp_ns", "0")),
            "type": record.get("type", ""),
            "payload_json": record.get("payload_json", "{}"),
        }) for record in records if record.get("event_id")]

    def append(self, event: Event) -> Event:
        if event.request_id in self.request_index or event.event_id in self.event_index:
            return event
        record = [
            event.event_id,
            event.request_id,
            str(event.timestamp_ns),
            event.type,
            json.dumps(event.payload, separators=(",", ":"), sort_keys=True),
        ]
        self.worksheet.append_row(record, value_input_option="RAW")
        self.events.append(event)
        self.request_index.add(event.request_id)
        self.event_index.add(event.event_id)
        return event


def parse_amount(value: str) -> int:
    normalized = value.strip().replace(",", ".")
    if not normalized:
        raise ValueError("Amount is required")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a decimal number") from exc
    cents = int((parsed * Decimal("100")).to_integral_value())
    if cents < 0:
        raise ValueError("Amount must be positive")
    return cents


def serialize_splits(splits: Dict[str, int]) -> str:
    return json.dumps(splits, sort_keys=True)


def build_event_store() -> LocalEventStore:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sheet_id and (credentials_path or credentials_json):
        return GoogleSheetsEventStore(
            sheet_id=sheet_id,
            credentials_path=credentials_path,
            credentials_json=credentials_json,
        )
    return LocalEventStore()
