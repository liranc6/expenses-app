from collections import defaultdict
from typing import Dict, List

from expenses_app.model import Event


def sort_events(events: List[Event]) -> List[Event]:
    return sorted(events, key=lambda event: (event.timestamp_ns, event.event_id))


def derive_expense_state(events: List[Event]) -> Dict[str, Dict]:
    expenses_by_id: Dict[str, List[Event]] = defaultdict(list)
    for event in events:
        if event.type in {"EXPENSE_CREATED", "EXPENSE_EDITED", "EXPENSE_DELETED"}:
            expense_id = event.payload.get("expense_id")
            if expense_id:
                expenses_by_id[expense_id].append(event)
    state: Dict[str, Dict] = {}
    for expense_id, history in expenses_by_id.items():
        ordered = sort_events(history)
        if any(event.type == "EXPENSE_DELETED" for event in ordered):
            continue
        state[expense_id] = ordered[-1].payload
    return state


def derive_settlements(events: List[Event]) -> List[Dict]:
    return [event.payload for event in events if event.type == "SETTLEMENT_CREATED"]


def compute_balances(expenses: Dict[str, Dict], settlements: List[Dict]) -> Dict[str, int]:
    balances: Dict[str, int] = defaultdict(int)
    for expense in expenses.values():
        amount = expense.get("amount", 0)
        payer = expense.get("payer")
        splits = expense.get("splits", {})
        if not isinstance(splits, dict) or payer is None:
            continue
        for user, share in splits.items():
            balances[user] -= int(share)
        balances[payer] += int(amount)
    for settlement in settlements:
        payer = settlement.get("from")
        payee = settlement.get("to")
        amount = int(settlement.get("amount", 0))
        if payer and payee and payer != payee:
            balances[payer] -= amount
            balances[payee] += amount
    return dict(sorted(balances.items()))
