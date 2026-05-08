import json
import os
from typing import Dict, List, Optional
from uuid import uuid4
from decimal import Decimal

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


def main() -> None:
    st.set_page_config(page_title="Expenses App", layout="wide")
    st.title("Expenses App — Event-Sourced Ledger")
    active_user = st.sidebar.selectbox("Logged in as", DEFAULT_USERS, index=0)
    
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
    
    category_totals = {}
    for expense in filtered_expenses.values():
        category = expense.get("category", "Uncategorized") or "Uncategorized"
        category_totals[category] = category_totals.get(category, 0) + expense["amount"]

    # Layout: Balances first
    st.subheader("Current balances")
    if balances:
        balance_rows = [
            {"user": user, "balance": format_currency(amount)}
            for user, amount in sorted(balances.items(), key=lambda item: -item[1])
        ]
        st.table(balance_rows)
    else:
        st.info("No balances yet.")

    st.markdown("---")
    st.header("Write events")
    
    with st.expander("Create a new expense", expanded=True):
        # UI Order change: Amount above Note
        amount_input = st.text_input("Total amount (decimal)", value="", key="amount_input")
        note_input = st.text_input("Note / description", value="", key="note_input")
        
        # Immediate auto-categorization UX
        auto_category = classify_category(note_input)
        category_input = st.text_input("Category", value=auto_category, key="category_input")
        
        payer = st.selectbox("Payer", options=DEFAULT_USERS, index=DEFAULT_USERS.index(active_user))
        
        # Splitwise-style splits
        st.write("Splits")
        split_mode = st.radio("Method", ["Equal", "By percentage", "By amount"], horizontal=True, label_visibility="collapsed")
        
        splits = {}
        amount_cents = 0
        try:
            if amount_input:
                amount_cents = parse_amount(amount_input)
        except:
            pass
            
        if split_mode == "Equal":
            if amount_cents > 0:
                splits = default_equal_splits(amount_cents, DEFAULT_USERS, payer)
                for user, val in splits.items():
                    st.text(f"{user}: {format_currency(val)}")
        
        elif split_mode == "By percentage":
            cols = st.columns(len(DEFAULT_USERS))
            total_pct = 0
            # Splitwise UX: calculate the other user automatically
            if len(DEFAULT_USERS) == 2:
                user1 = DEFAULT_USERS[0]
                user2 = DEFAULT_USERS[1]
                p1 = cols[0].number_input(f"{user1} %", min_value=0, max_value=100, value=50, key="p1")
                p2 = 100 - p1
                cols[1].text_input(f"{user2} %", value=str(p2), disabled=True)
                splits[user1] = int(amount_cents * p1 / 100)
                splits[user2] = amount_cents - splits[user1]
            else:
                for i, user in enumerate(DEFAULT_USERS):
                    pct = cols[i].number_input(f"{user} %", min_value=0, max_value=100, value=0, key=f"pct_{user}")
                    total_pct += pct
                    splits[user] = int(amount_cents * pct / 100)
        
        elif split_mode == "By amount":
            cols = st.columns(len(DEFAULT_USERS))
            if len(DEFAULT_USERS) == 2:
                user1 = DEFAULT_USERS[0]
                user2 = DEFAULT_USERS[1]
                a1_str = cols[0].text_input(f"{user1} amount", value="", key="a1")
                try:
                    a1 = parse_amount(a1_str) if a1_str else 0
                    splits[user1] = a1
                    a2 = amount_cents - a1
                    cols[1].text_input(f"{user2} amount", value=format_currency(a2), disabled=True)
                    splits[user2] = a2
                except:
                    splits[user1] = 0
                    splits[user2] = 0
            else:
                for i, user in enumerate(DEFAULT_USERS):
                    amt_str = cols[i].text_input(f"{user} amount", value="", key=f"amt_{user}")
                    try:
                        splits[user] = parse_amount(amt_str) if amt_str else 0
                    except:
                        splits[user] = 0

        if st.button("Create expense"):
            try:
                if not amount_input: raise ValueError("Amount is required")
                if sum(splits.values()) != amount_cents: raise ValueError("Split totals must equal amount")
                
                event = Event.new(
                    type="EXPENSE_CREATED",
                    payload={
                        "expense_id": uuid4().hex,
                        "amount": amount_cents,
                        "payer": payer,
                        "splits": splits,
                        "category": category_input or auto_category,
                        "note": note_input,
                    },
                )
                event_store.append(event)
                st.success("Expense created!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.markdown("---")
    
    # Remove Expense ID (hash) from table
    st.subheader("Active expenses")
    if filtered_expenses:
        active_display = [
            {
                "Payer": expense["payer"],
                "Amount": format_currency(expense["amount"]),
                "Category": expense.get("category", "-"),
                "Note": expense.get("note", ""),
                "Splits": ", ".join(f"{u}:{a/100:.2f}" for u, a in expense["splits"].items()),
            }
            for expense in filtered_expenses.values()
        ]
        st.table(active_display)
    else:
        st.info("No matching expenses.")

    with st.expander("More Controls (Edit/Delete/Settlement)"):
        tabs = st.tabs(["Edit", "Delete", "Settlement"])
        with tabs[1]:
            if expenses:
                del_id = st.selectbox("Select to delete", sorted(expenses))
                if st.button("Delete"):
                    event_store.append(Event.new(type="EXPENSE_DELETED", payload={"expense_id": del_id}))
                    st.rerun()
        with tabs[2]:
            with st.form("settle"):
                f_u = st.selectbox("From", DEFAULT_USERS)
                t_u = st.selectbox("To", [u for u in DEFAULT_USERS if u != f_u])
                s_a = st.text_input("Amount")
                if st.form_submit_button("Settle"):
                    event_store.append(Event.new(type="SETTLEMENT_CREATED", payload={"from": f_u, "to": t_u, "amount": parse_amount(s_a)}))
                    st.rerun()

if __name__ == "__main__":
    main()
