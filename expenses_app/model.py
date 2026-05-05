from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

EVENT_TYPES = {
    "EXPENSE_CREATED",
    "EXPENSE_EDITED",
    "EXPENSE_DELETED",
    "SETTLEMENT_CREATED",
}


@dataclass
class Event:
    event_id: str
    request_id: str
    timestamp_ns: int
    type: str
    payload: Dict[str, Any]

    @staticmethod
    def now_ns() -> int:
        return time.time_ns()

    @staticmethod
    def new(
        type: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None,
        timestamp_ns: Optional[int] = None,
    ) -> "Event":
        if type not in EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {type}")
        return Event(
            event_id=uuid4().hex,
            request_id=request_id or uuid4().hex,
            timestamp_ns=timestamp_ns or Event.now_ns(),
            type=type,
            payload=payload,
        )

    def to_record(self) -> Dict[str, str]:
        return {
            "event_id": self.event_id,
            "request_id": self.request_id,
            "timestamp_ns": str(self.timestamp_ns),
            "type": self.type,
            "payload_json": json.dumps(self.payload, separators=(",", ":"), sort_keys=True),
        }

    @staticmethod
    def from_record(record: Dict[str, str]) -> "Event":
        return Event(
            event_id=record["event_id"],
            request_id=record["request_id"],
            timestamp_ns=int(record["timestamp_ns"]),
            type=record["type"],
            payload=json.loads(record["payload_json"]),
        )
