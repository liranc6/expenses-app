import streamlit as st
import os
import json
from uuid import uuid4
import plotly.express as px
from expenses_app.model import Event
from expenses_app.replay import (
    compute_balances,
    derive_expense_state,
    derive_settlements,
    sort_events,
)
from expenses_app.store import build_event_store, parse_amount

# Reuse constants and functions from app.py or a common utils file. 
# For now, we will import or redefine if necessary. 
# Better to move them to a common location later.

DEFAULT_USERS = ["Liran", "Vova"]
CATEGORIES = {
    "Food": "🍕",
    "Transport": "🚗",
    "Travel": "✈️",
    "Bill": "📄",
    "Other": "📦",
}

LIMITS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "limits.json")

def load_limits():
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r") as f:
            return json.load(f)
    return {u: {c: 0 for c in CATEGORIES} for u in DEFAULT_USERS}

def format_currency(value: int) -> str:
    return f"{value / 100:.2f}"

def render_dashboard():
    st.title("📊 Dashboard")
    
    event_store = build_event_store()
    events = sort_events(event_store.load())
    expenses = derive_expense_state(events)
    settlements = derive_settlements(events)
    balances = compute_balances(expenses, settlements)
    budget_targets = load_limits()

    active_user = st.sidebar.selectbox("Logged in as", DEFAULT_USERS, index=0)

    # --- SIDEBAR BALANCES ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Live Balances")
    if balances:
        for user, amount in sorted(balances.items(), key=lambda item: -item[1]):
            display_user = user
            if user == "You": display_user = "Liran"
            if user == "Partner": display_user = "Vova"
            
            label = f"{display_user} (You)" if display_user == active_user else display_user
            formatted = f"${format_currency(amount)}"
            st.sidebar.metric(label=label, value=formatted)
    
    # Visual Overview
    category_totals = {}
    payer_totals = {}
    for expense in expenses.values():
        category = expense.get("category", "Other") or "Other"
        category_totals[category] = category_totals.get(category, 0) + expense["amount"]
        payer = expense.get("payer", "Unknown")
        payer_totals[payer] = payer_totals.get(payer, 0) + expense["amount"]

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        if category_totals:
            cat_names = [f"{CATEGORIES.get(k, '')} {k}" for k in category_totals.keys()]
            fig_cat = px.pie(names=cat_names, values=[v/100 for v in category_totals.values()], title="Expenses by Category", hole=.4)
            st.plotly_chart(fig_cat, use_container_width=True)
    with col_p2:
        if payer_totals:
            fig_payer = px.pie(names=list(payer_totals.keys()), values=[v/100 for v in payer_totals.values()], title="Spending Distribution", hole=.4)
            st.plotly_chart(fig_payer, use_container_width=True)

    # Budget Utilization
    st.markdown("---")
    st.subheader(f"Your Budget Utilization ({active_user})")
    internal_user_key = active_user
    if active_user == "Liran": internal_user_key = "You"
    if active_user == "Vova": internal_user_key = "Partner"
    user_limits = budget_targets.get(active_user, {})
    
    if any(limit > 0 for limit in user_limits.values()):
        cols = st.columns(len(CATEGORIES))
        for i, (cat, emoji) in enumerate(CATEGORIES.items()):
            limit = user_limits.get(cat, 0)
            if limit > 0:
                consumed = sum(exp["splits"].get(active_user, 0) or exp["splits"].get(internal_user_key, 0)
                            for exp in expenses.values() if exp.get("category") == cat)
                percent = min(consumed / limit, 1.0)
                with cols[i]:
                    st.write(f"{emoji} **{cat}**")
                    st.progress(percent)
                    if percent >= 1.0: st.error(f"{format_currency(consumed)} / {format_currency(limit)}")
                    elif percent >= 0.85: st.warning(f"{format_currency(consumed)} / {format_currency(limit)}")
                    else: st.info(f"{format_currency(consumed)} / {format_currency(limit)}")

if __name__ == "__main__":
    render_dashboard()
