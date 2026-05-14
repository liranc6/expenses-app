import importlib.util
from pathlib import Path

import streamlit as st
from uuid import uuid4
from expenses_app.model import Event
from expenses_app.store import build_event_store, parse_amount

DEFAULT_USERS = ["Liran", "Vova"]
CATEGORIES = {
    "Food": "🍕",
    "Transport": "🚗",
    "Travel": "✈️",
    "Bill": "📄",
    "Other": "📦",
}

def classify_category(note: str) -> str:
    normalized = note.strip().lower()
    if not normalized: return ""
    if any(k in normalized for k in ["pizza", "dinner", "food", "restaurant", "coffee", "drink", "market", "supermarket"]): return "Food"
    if any(k in normalized for k in ["taxi", "uber", "bus", "train", "transport"]): return "Transport"
    if any(k in normalized for k in ["flight", "hotel", "travel"]): return "Travel"
    return ""

def default_equal_splits(amount_cents: int, users: list, payer: str) -> dict:
    base = amount_cents // len(users)
    rem = amount_cents - base * len(users)
    splits = {u: base for u in users}
    splits[payer] += rem
    return splits

PAGES = [
    {"label": "Home", "path": None, "func": None, "module": None},
    {"label": "Dashboard", "path": Path(__file__).parent / "pages" / "1_Dashboard.py", "func": "render_dashboard", "module": "page_dashboard"},
    {"label": "Expenses", "path": Path(__file__).parent / "pages" / "2_Expenses.py", "func": "render_expenses", "module": "page_expenses"},
    {"label": "Limits", "path": Path(__file__).parent / "pages" / "3_Limits.py", "func": "render_limits", "module": "page_limits"},
    {"label": "Settlements", "path": Path(__file__).parent / "pages" / "4_Settlements.py", "func": "render_settlements", "module": "page_settlements"},
]

def load_page_module(page):
    spec = importlib.util.spec_from_file_location(page["module"], str(page["path"]))
    page_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(page_module)
    return page_module

@st.dialog("➕ Add Expense")
def show_add_expense_modal():
    amount_input = st.text_input("Amount (e.g. 15.50)")
    note_input = st.text_input("Note", placeholder="Lunch, Taxi, etc.")
    
    col1, col2 = st.columns(2)
    with col1:
        cat = st.selectbox("Category", list(CATEGORIES.keys()), index=0)
    with col2:
        payer = st.selectbox("Payer", DEFAULT_USERS, index=0)
    
    if st.button("Save Expense", type="primary", use_container_width=True):
        try:
            amt = parse_amount(amount_input)
            splits = default_equal_splits(amt, DEFAULT_USERS, payer)
            event = Event.new(
                type="EXPENSE_CREATED",
                payload={
                    "expense_id": uuid4().hex,
                    "amount": amt,
                    "payer": payer,
                    "splits": splits,
                    "category": cat,
                    "note": note_input,
                },
            )
            build_event_store().append(event)
            st.success("Added!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def main():
    st.set_page_config(page_title="Expenses App", layout="wide", page_icon="💰", initial_sidebar_state="expanded")
    
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            border-color: #28a745 !important;
            color: white !important;
            position: fixed !important;
            bottom: 30px !important;
            right: 30px !important;
            z-index: 99999 !important;
            border-radius: 50px !important;
            width: auto !important;
            padding: 10px 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.sidebar.title("💰 Expenses App")
    page_labels = [page["label"] for page in PAGES]
    selected_page = st.sidebar.radio("Navigation", page_labels, index=0)
    st.sidebar.info("Choose a page below or use the quick add button.")

    if st.sidebar.button("➕ Quick Add", type="primary", use_container_width=False):
        show_add_expense_modal()

    if selected_page != "Home":
        page = next(page for page in PAGES if page["label"] == selected_page)
        module = load_page_module(page)
        render_fn = getattr(module, page["func"], None)
        if callable(render_fn):
            render_fn()
        else:
            st.error("Unable to load the selected page.")
        return

    st.write("### 🚀 Welcome to the Modernized Expenses App")
    st.write("Select a page from the sidebar to begin:")
    st.info("Use the navigation menu on the left to switch between Dashboard, Expenses, Limits, and Settlements.")

    st.markdown("- **1 Dashboard**: Visual summary and budget tracking.")
    st.markdown("- **2 Expenses**: Full history and search.")
    st.markdown("- **3 Limits**: Configure your budgets.")
    st.markdown("- **4 Settlements**: Balance your accounts.")

if __name__ == "__main__":
    main()
