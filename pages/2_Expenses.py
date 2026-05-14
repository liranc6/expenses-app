import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab, CATEGORIES

st.set_page_config(page_title="Expenses - List", layout="wide", page_icon="📜")
init_styles()
render_sidebar()

st.title("📜 Expenses List")

from expenses_app.store import build_event_store
from expenses_app.replay import sort_events, derive_expense_state

event_store = build_event_store()
expenses = derive_expense_state(sort_events(event_store.load()))

if expenses:
    active_display = [
        {
            "Payer": f"👤 {exp['payer']}",
            "Amount": f"${exp['amount']/100:.2f}",
            "Category": f"{CATEGORIES.get(exp.get('category', 'Other'), '📦')} {exp.get('category', 'Other')}",
            "Note": exp.get("note", ""),
            "Splits": ", ".join(f"{u}: {a/100:.2f}" for u, a in exp["splits"].items()),
        }
        for exp in expenses.values()
    ]
    st.dataframe(active_display, use_container_width=True)
else:
    st.info("No expenses found.")

render_fab()
