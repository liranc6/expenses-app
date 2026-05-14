import streamlit as st
import os
import json
from dotenv import load_dotenv

# Shared constants or helper to be imported
CATEGORIES = {
    "Food": "🍕",
    "Transport": "🚗",
    "Travel": "✈️",
    "Bill": "📄",
    "Other": "📦",
}
DEFAULT_USERS = ["Liran", "Vova"]

def init_styles():
    st.markdown("""
        <style>
        /* Floating Action Button (FAB) */
        .fab-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 999;
        }
        .fab-button {
            width: 60px;
            height: 60px;
            background-color: #28a745;
            border-radius: 50%;
            border: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            color: white;
            font-size: 30px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, background-color 0.2s;
        }
        .fab-button:hover {
            transform: scale(1.1);
            background-color: #218838;
        }
        
        /* Sidebar Buttons */
        [data-testid="stSidebarNav"] {
            display: none;
        }
        .sidebar-btn {
            display: block;
            width: 100%;
            padding: 10px;
            margin-bottom: 5px;
            background-color: transparent;
            border: 1px solid #ddd;
            border-radius: 5px;
            text-align: left;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
        }
        .sidebar-btn:hover {
            background-color: #f0f0f0;
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    st.sidebar.title("💰 Expenses App")
    st.sidebar.subheader("Navigation")
    
    # Custom Sidebar Buttons as requested
    if st.sidebar.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")
    if st.sidebar.button("📜 Expenses", use_container_width=True):
        st.switch_page("pages/2_Expenses.py")
    if st.sidebar.button("⚙️ Limits", use_container_width=True):
        st.switch_page("pages/3_Limits.py")
    if st.sidebar.button("🤝 Settlements", use_container_width=True):
        st.switch_page("pages/4_Settlements.py")
    
    st.sidebar.markdown("---")
    active_user = st.sidebar.selectbox("Logged in as", DEFAULT_USERS, index=0)
    return active_user

@st.dialog("➕ Add New Expense")
def add_expense_dialog():
    from expenses_app.store import build_event_store, parse_amount
    from expenses_app.model import Event
    from uuid import uuid4
    
    # Logic from create_expense section in app.py
    col1, col2 = st.columns(2)
    amount_input = col1.text_input("Total amount", key="dlg_amount")
    note_input = col2.text_input("Note", key="dlg_note")
    
    cat = st.selectbox("Category", list(CATEGORIES.keys()), format_func=lambda x: f"{CATEGORIES[x]} {x}")
    payer = st.selectbox("Payer", DEFAULT_USERS)
    
    st.write("**Splits** (Equal)")
    # For simplicity in dialog, default to equal splits for now as basic functionality
    if st.button("Create Expense", type="primary", use_container_width=True):
        try:
            amount_cents = parse_amount(amount_input)
            # Simple equal split logic
            from expenses_app.replay import default_equal_splits
            splits = {u: amount_cents // len(DEFAULT_USERS) for u in DEFAULT_USERS}
            # Handle remainder
            remainder = amount_cents - sum(splits.values())
            splits[payer] += remainder
            
            event = Event.new(
                type="EXPENSE_CREATED",
                payload={
                    "expense_id": uuid4().hex,
                    "amount": amount_cents,
                    "payer": payer,
                    "splits": splits,
                    "category": cat,
                    "note": note_input,
                },
            )
            build_event_store().append(event)
            st.success("Expense created!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

def render_fab():
    # Visually styled FAB with a hidden Streamlit button to trigger the dialog
    st.markdown("""
        <div class="fab-container">
            <button class="fab-button" onclick="document.querySelector('button[kind=\'secondary\'][aria-label=\'fab-trigger\']').click()">+</button>
        </div>
    """, unsafe_allow_html=True)
    
    # Hidden Streamlit button that triggers the dialog
    if st.button("+", key="fab_trigger", help="Add New Expense", label_visibility="collapsed"):
        add_expense_dialog()
