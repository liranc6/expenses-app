import json
import os
from typing import Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
import plotly.express as px
import streamlit as st

from expenses_app.model import Event
from expenses_app.replay import (
    compute_balances,
    derive_expense_state,
    derive_settlements,
    sort_events,
)
from expenses_app.store import build_event_store, parse_amount, serialize_splits


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DEFAULT_USERS = ["You", "Partner"]
BUDGET_TARGETS = {
    "Food": 20000,
}


def safe_string(value: Optional[str]) -> str:
    return (value or "").strip()


def split_input_to_text(splits: Dict[str, int]) -> str:
    return ", ".join(f"{user}:{amount / 100:.2f}" for user, amount in splits.items())


def classify_category(note: str) -> str:
    normalized = note.strip().lower()
    if not normalized:
        return ""
    if any(keyword in normalized for keyword in ["pizza", "dinner", "food", "restaurant", "coffee", "drink"]):
        return "Food"
    if any(keyword in normalized for keyword in ["taxi", "uber", "bus", "train", "transport"]):
        return "Transport"
    if any(keyword in normalized for keyword in ["groceries", "market", "supermarket"]):
        return "Food"
    if any(keyword in normalized for keyword in ["flight", "hotel", "travel"]):
        return "Travel"
    return ""


def default_equal_splits(amount_cents: int, users: List[str], payer: str) -> Dict[str, int]:
    if payer not in users:
        raise ValueError("Payer must be a valid user")
    number_of_users = len(users)
    base_share = amount_cents // number_of_users
    remainder = amount_cents - base_share * number_of_users
    splits = {user: base_share for user in users}
    if remainder:
        splits[payer] += remainder
    return splits


def parse_splits_text(raw: str) -> Dict[str, int]:
    if not raw.strip():
        return {}
    payload = {}
    for part in raw.split(","):
        if not part.strip():
            continue
        if ":" not in part:
            raise ValueError("Each split must use the form user:amount")
        user, value = part.split(":", 1)
        user = user.strip()
        payload[user] = parse_amount(value.strip())
    return payload


def format_currency(value: int) -> str:
    return f"{value / 100:.2f}"


def show_expense_row(expense_id: str, expense: Dict[str, object]) -> str:
    splits = expense.get("splits", {})
    split_text = ", ".join(f"{k}:{v / 100:.2f}" for k, v in splits.items())
    return f"{expense_id} | {expense['payer']} | {format_currency(expense['amount'])} | {expense.get('category','-')} | {split_text}"


def main() -> None:
    st.set_page_config(page_title="Expenses App", layout="wide")
    st.title("Expenses App — Event-Sourced Ledger")
    active_user = st.sidebar.selectbox("Logged in as", DEFAULT_USERS, index=0)
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_mode = bool(sheet_id and (credentials_path or credentials_json))
    storage_mode = "Google Sheets" if sheet_mode else "Local CSV"
    st.sidebar.markdown(f"**Storage mode:** {storage_mode}")
    if sheet_id and not (credentials_path or credentials_json):
        st.sidebar.warning("GOOGLE_SHEET_ID is set but credentials are missing.")

    event_store = build_event_store()
    events = sort_events(event_store.load())
    expenses = derive_expense_state(events)
    settlements = derive_settlements(events)
    balances = compute_balances(expenses, settlements)

    search_query = safe_string(st.sidebar.text_input("Search notes", value=""))
    filtered_expenses = (
        {
            expense_id: expense
            for expense_id, expense in expenses.items()
            if search_query.lower() in (expense.get("note", "") or "").lower()
        }
        if search_query
        else expenses
    )
    budget_warnings = []
    category_totals = {}
    for expense in filtered_expenses.values():
        category = expense.get("category", "Uncategorized") or "Uncategorized"
        category_totals[category] = category_totals.get(category, 0) + expense["amount"]
    for category, total in category_totals.items():
        budget_target = BUDGET_TARGETS.get(category)
        if budget_target is not None and total >= budget_target:
            budget_warnings.append((category, total, budget_target))

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Current balances")
        if balances:
            balance_rows = [
                {"user": user, "balance": format_currency(amount)}
                for user, amount in sorted(balances.items(), key=lambda item: -item[1])
            ]
            st.table(balance_rows)
            fig = px.bar(
                x=[row["user"] for row in balance_rows],
                y=[float(row["balance"]) for row in balance_rows],
                labels={"x": "User", "y": "Balance"},
                title="Net Balances",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No balances yet. Create your first expense or settlement.")

        if budget_warnings:
            for category, total, target in budget_warnings:
                st.warning(
                    f"Budget reached for {category}: {format_currency(total)} / {format_currency(target)}"
                )

        st.subheader("Active expenses")
        if filtered_expenses:
            active = [
                {
                    "expense_id": expense_id,
                    "payer": expense["payer"],
                    "amount": format_currency(expense["amount"]),
                    "category": expense.get("category", "-"),
                    "note": expense.get("note", ""),
                    "splits": ", ".join(f"{u}:{a/100:.2f}" for u, a in expense["splits"].items()),
                }
                for expense_id, expense in filtered_expenses.items()
            ]
            st.table(active)
            category_fig = px.pie(
                names=list(category_totals.keys()),
                values=list(category_totals.values()),
                title="Expense Category Breakdown",
            )
            st.plotly_chart(category_fig, use_container_width=True)
        else:
            st.info("No matching expenses. Modify the search query or add new entries.")

        st.subheader("Settlements")
        if settlements:
            st.table(
                [
                    {
                        "from": item["from"],
                        "to": item["to"],
                        "amount": format_currency(item["amount"]),
                    }
                    for item in settlements
                ]
            )
        else:
            st.info("No settlements recorded yet.")

    with col2:
        st.subheader("Event log")
        st.write(f"Total events: {len(events)}")
        if events:
            st.dataframe(
                [
                    {
                        "timestamp_ns": event.timestamp_ns,
                        "type": event.type,
                        "request_id": event.request_id,
                        "event_id": event.event_id,
                        "payload": json.dumps(event.payload, sort_keys=True),
                    }
                    for event in events
                ],
                use_container_width=True,
            )

    st.markdown("---")
    st.header("Write events")

    with st.expander("Create a new expense"):
        with st.form("create_expense"):
            payer = st.selectbox("Payer", options=DEFAULT_USERS, index=DEFAULT_USERS.index(active_user))
            note = safe_string(st.text_input("Note / description", value=""))
            amount = safe_string(st.text_input("Total amount (decimal)", value=""))
            category = safe_string(st.text_input("Category", value=""))
            split_text = safe_string(
                st.text_input(
                    "Splits (format: user1:amount1,user2:amount2)",
                    value="",
                )
            )
            submit = st.form_submit_button("Create expense")
            if submit:
                try:
                    amount_cents = parse_amount(amount)
                    splits = parse_splits_text(split_text)
                    if not splits:
                        splits = default_equal_splits(amount_cents, DEFAULT_USERS, payer)
                    if sum(splits.values()) != amount_cents:
                        raise ValueError("Split totals must equal the expense amount.")
                    if payer not in splits:
                        raise ValueError("The payer must appear in the split definition.")
                    if not category:
                        category = classify_category(note)
                    event = Event.new(
                        type="EXPENSE_CREATED",
                        payload={
                            "expense_id": uuid4().hex,
                            "amount": amount_cents,
                            "payer": payer,
                            "splits": splits,
                            "category": category,
                            "note": note,
                        },
                    )
                    event_store.append(event)
                    st.success("Expense event appended successfully. Refresh the page to see updates.")
                except Exception as exc:
                    st.error(str(exc))

    with st.expander("Edit an active expense"):
        if expenses:
            with st.form("edit_expense"):
                selected_expense_id = st.selectbox(
                    "Select expense to edit", sorted(expenses)
                )
                selected_expense = expenses[selected_expense_id]
                payer = st.selectbox("Payer", options=DEFAULT_USERS, index=DEFAULT_USERS.index(selected_expense["payer"]))
                amount = safe_string(
                    st.text_input(
                        "Total amount (decimal)",
                        value=format_currency(selected_expense["amount"]),
                    )
                )
                category = safe_string(
                    st.text_input("Category", value=selected_expense.get("category", ""))
                )
                current_split = split_input_to_text(selected_expense["splits"])
                split_text = safe_string(
                    st.text_input("Splits (format: user1:amount1,user2:amount2)", value=current_split)
                )
                submit = st.form_submit_button("Edit expense")
                if submit:
                    try:
                        amount_cents = parse_amount(amount)
                        splits = parse_splits_text(split_text)
                        if sum(splits.values()) != amount_cents:
                            raise ValueError("Split totals must equal the expense amount.")
                        if payer not in splits:
                            raise ValueError("The payer must appear in the split definition.")
                        event = Event.new(
                            type="EXPENSE_EDITED",
                            payload={
                                "expense_id": selected_expense_id,
                                "amount": amount_cents,
                                "payer": payer,
                                "splits": splits,
                                "category": category,
                            },
                        )
                        event_store.append(event)
                        st.success("Expense edit event appended successfully. Refresh to see updates.")
                    except Exception as exc:
                        st.error(str(exc))
        else:
            st.info("No active expenses available to edit.")

    with st.expander("Delete an active expense"):
        if expenses:
            with st.form("delete_expense"):
                selected_expense_id = st.selectbox(
                    "Select expense to delete", sorted(expenses)
                )
                submit = st.form_submit_button("Delete expense")
                if submit:
                    event = Event.new(
                        type="EXPENSE_DELETED",
                        payload={"expense_id": selected_expense_id},
                    )
                    event_store.append(event)
                    st.success("Delete event appended successfully. Refresh to see updates.")
        else:
            st.info("No active expense to delete.")

    with st.expander("Create a settlement"):
        with st.form("create_settlement"):
            payer = st.selectbox("From", options=DEFAULT_USERS, index=DEFAULT_USERS.index(active_user))
            payee = st.selectbox(
                "To",
                options=[user for user in DEFAULT_USERS if user != payer],
                index=0,
            )
            amount = safe_string(st.text_input("Settlement amount (decimal)", value=""))
            submit = st.form_submit_button("Record settlement")
            if submit:
                try:
                    amount_cents = parse_amount(amount)
                    if not payer or not payee:
                        raise ValueError("Both from and to users are required.")
                    if payer == payee:
                        raise ValueError("Settlement sender and recipient must differ.")
                    event = Event.new(
                        type="SETTLEMENT_CREATED",
                        payload={
                            "from": payer,
                            "to": payee,
                            "amount": amount_cents,
                        },
                    )
                    event_store.append(event)
                    st.success("Settlement event appended successfully. Refresh to see updates.")
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("---")
    st.caption("This application stores events in an append-only ledger and derives state by deterministic replay.")


if __name__ == "__main__":
    main()
