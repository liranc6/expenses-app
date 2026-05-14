import streamlit as st
import os
from uuid import uuid4
from expenses_app.model import Event
from expenses_app.replay import (
    derive_expense_state,
    sort_events,
)
from expenses_app.store import build_event_store, parse_amount

DEFAULT_USERS = ["Liran", "Vova"]
CATEGORIES = {
    "Food": "🍕",
    "Transport": "🚗",
    "Travel": "✈️",
    "Bill": "📄",
    "Other": "📦",
}

def format_currency(value: int) -> str:
    return f"{value / 100:.2f}"

def safe_string(value) -> str:
    return (value or "").strip()

def render_expenses():
    st.title("📜 Expenses Ledger")
    
    event_store = build_event_store()
    events = sort_events(event_store.load())
    expenses = derive_expense_state(events)

    search_query = safe_string(st.text_input("🔍 Search notes", value=""))
    filtered_expenses = (
        {k: v for k, v in expenses.items() if search_query.lower() in (v.get("note") or "").lower()}
        if search_query else expenses
    )

    if filtered_expenses:
        active_display = [
            {
                "Payer": f"👤 {exp['payer']}",
                "Amount": f"${format_currency(exp['amount'])}",
                "Category": f"{CATEGORIES.get(exp.get('category', 'Other'), '📦')} {exp.get('category', 'Other')}",
                "Note": exp.get("note", ""),
                "Splits": ", ".join(f"{u}: {a/100:.2f}" for u, a in exp["splits"].items()),
            }
            for exp in reversed(list(filtered_expenses.values()))
        ]
        st.dataframe(active_display, use_container_width=True)
        
        with st.expander("🛠️ Admin (Delete)"):
            del_id = st.selectbox("Select to delete", sorted(filtered_expenses.keys()), format_func=lambda x: f"{filtered_expenses[x].get('note')} (${format_currency(filtered_expenses[x]['amount'])})")
            if st.button("Delete"):
                event_store.append(Event.new(type="EXPENSE_DELETED", payload={"expense_id": del_id}))
                st.rerun()
    else:
        st.info("No expenses found.")

if __name__ == "__main__":
    render_expenses()
