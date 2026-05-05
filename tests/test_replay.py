import pytest

from expenses_app.model import Event
from expenses_app.replay import compute_balances, derive_expense_state, derive_settlements, sort_events


def test_sort_events_orders_by_timestamp_and_id():
    events = [
        Event(event_id="b", request_id="1", timestamp_ns=10, type="EXPENSE_CREATED", payload={"expense_id": "x"}),
        Event(event_id="a", request_id="2", timestamp_ns=10, type="EXPENSE_CREATED", payload={"expense_id": "x"}),
        Event(event_id="c", request_id="3", timestamp_ns=5, type="EXPENSE_CREATED", payload={"expense_id": "x"}),
    ]
    ordered = sort_events(events)
    assert [event.event_id for event in ordered] == ["c", "a", "b"]


def test_derive_expense_state_deletes_expense_when_deleted():
    events = [
        Event(event_id="1", request_id="a", timestamp_ns=1, type="EXPENSE_CREATED", payload={"expense_id": "x", "amount": 100, "payer": "userA", "splits": {"userA": 100}}),
        Event(event_id="2", request_id="b", timestamp_ns=2, type="EXPENSE_DELETED", payload={"expense_id": "x"}),
        Event(event_id="3", request_id="c", timestamp_ns=3, type="EXPENSE_EDITED", payload={"expense_id": "x", "amount": 200, "payer": "userA", "splits": {"userA": 200}}),
    ]
    state = derive_expense_state(events)
    assert state == {}


def test_compute_balances_with_expense_and_settlement():
    expenses = {
        "x": {"amount": 10000, "payer": "userA", "splits": {"userA": 6000, "userB": 4000}},
    }
    settlements = [{"from": "userA", "to": "userB", "amount": 2000}]
    balances = compute_balances(expenses, settlements)
    assert balances["userA"] == 2000
    assert balances["userB"] == -2000


def test_derive_settlements_filters_only_settlement_events():
    events = [
        Event(event_id="1", request_id="a", timestamp_ns=1, type="SETTLEMENT_CREATED", payload={"from": "userA", "to": "userB", "amount": 5000}),
        Event(event_id="2", request_id="b", timestamp_ns=2, type="EXPENSE_CREATED", payload={"expense_id": "x"}),
    ]
    settlements = derive_settlements(events)
    assert settlements == [{"from": "userA", "to": "userB", "amount": 5000}]
