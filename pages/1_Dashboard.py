import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab

st.set_page_config(page_title="Expenses - Dashboard", layout="wide", page_icon="💰")
init_styles()
active_user = render_sidebar()

st.title("📊 Dashboard")
st.write(f"Welcome, {active_user}!")

# Dashboard logic from app.py
from expenses_app.store import build_event_store
from expenses_app.replay import sort_events, derive_expense_state, derive_settlements, compute_balances
import plotly.express as px
from expenses_app.ui_components import CATEGORIES

event_store = build_event_store()
events = sort_events(event_store.load())
expenses = derive_expense_state(events)
settlements = derive_settlements(events)
balances = compute_balances(expenses, settlements)

# Live Balances in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Live Balances")
for user, amount in balances.items():
    st.sidebar.metric(label=user, value=f"${amount/100:.2f}")

# Visuals
col1, col2 = st.columns(2)
category_totals = {}
for exp in expenses.values():
    cat = exp.get("category", "Other")
    category_totals[cat] = category_totals.get(cat, 0) + exp["amount"]

with col1:
    if category_totals:
        fig = px.pie(names=list(category_totals.keys()), values=[v/100 for v in category_totals.values()], title="By Category")
        st.plotly_chart(fig, use_container_width=True)

render_fab()
