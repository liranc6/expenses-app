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
    st.set_page_config(page_title="Expenses App", layout="wide", page_icon="💰")
    
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
    st.sidebar.info("Welcome! Use the navigation menu to switch pages.")
    
    if st.button("➕ Quick Add", type="primary", use_container_width=False):
        show_add_expense_modal()

    st.write("### 🚀 Welcome to the Modernized Expenses App")
    st.write("Select a page below or from the sidebar to begin:")
    st.info("Use the left sidebar navigation to switch between Dashboard, Expenses, Limits, and Settlements.")

    st.markdown("- **1 Dashboard**: Visual summary and budget tracking.")
    st.markdown("- **2 Expenses**: Full history and search.")
    st.markdown("- **3 Limits**: Configure your budgets.")
    st.markdown("- **4 Settlements**: Balance your accounts.")

if __name__ == "__main__":
    main()
