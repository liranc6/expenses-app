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

    split_mode = st.radio("Split mode", ["Equal", "By percentage", "By amount"])
    amount_cents = 0
    try:
        amount_cents = parse_amount(amount_input) if amount_input else 0
    except Exception:
        amount_cents = 0

    splits = {}
    validation_error = None

    if split_mode == "Equal":
        if amount_cents > 0:
            splits = default_equal_splits(amount_cents, DEFAULT_USERS, payer)
        st.write("**Equal split**")
        for user, value in splits.items():
            st.write(f"- {user}: ${value / 100:.2f}")

    elif split_mode == "By percentage":
        cols = st.columns(len(DEFAULT_USERS))
        total_percent = 0
        for i, user in enumerate(DEFAULT_USERS):
            percent = cols[i].number_input(f"{user} %", min_value=0, max_value=100, value=0, key=f"split_pct_{i}")
            total_percent += percent
            splits[user] = int(amount_cents * percent / 100)

        if amount_cents > 0 and total_percent != 100:
            validation_error = "Percentages must total 100%."
        st.write("**Split preview**")
        for user, value in splits.items():
            st.write(f"- {user}: ${value / 100:.2f}")

    else:
        cols = st.columns(len(DEFAULT_USERS))
        if len(DEFAULT_USERS) == 2:
            first_user = DEFAULT_USERS[0]
            second_user = DEFAULT_USERS[1]
            first_amount = cols[0].text_input(f"{first_user} amount", value="", key="split_amt_0")
            try:
                first_cents = parse_amount(first_amount) if first_amount else 0
            except Exception:
                first_cents = 0
            second_cents = max(amount_cents - first_cents, 0)
            cols[1].text_input(f"{second_user} amount", value=f"{second_cents / 100:.2f}", disabled=True)
            splits = {first_user: first_cents, second_user: second_cents}
            if amount_cents > 0 and sum(splits.values()) != amount_cents:
                validation_error = "Split amounts must total the full expense amount."
        else:
            for i, user in enumerate(DEFAULT_USERS):
                user_amount = cols[i].text_input(f"{user} amount", value="", key=f"split_amt_{i}")
                try:
                    splits[user] = parse_amount(user_amount) if user_amount else 0
                except Exception:
                    splits[user] = 0
            if amount_cents > 0 and sum(splits.values()) != amount_cents:
                validation_error = "Split amounts must total the full expense amount."

        if splits:
            st.write("**Split preview**")
            for user, value in splits.items():
                st.write(f"- {user}: ${value / 100:.2f}")

    if validation_error:
        st.error(validation_error)

    if st.button("Save Expense", type="primary", use_container_width=True):
        try:
            if amount_cents <= 0:
                raise ValueError("Amount must be positive")
            if not note_input.strip():
                raise ValueError("Note is required")
            if sum(splits.values()) != amount_cents:
                raise ValueError("Split totals must equal the total amount")

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
    st.sidebar.info("Use these buttons to switch pages.")

    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "Dashboard"

    for page in PAGES:
        button_type = "primary" if st.session_state.selected_page == page["label"] else "secondary"
        if st.sidebar.button(page["label"], key=f"nav_{page['label']}", type=button_type, use_container_width=True):
            st.session_state.selected_page = page["label"]
            st.experimental_rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("➕ Quick Add", type="primary", use_container_width=True):
        show_add_expense_modal()

    selected_page = st.session_state.selected_page
    page = next(page for page in PAGES if page["label"] == selected_page)
    module = load_page_module(page)
    render_fn = getattr(module, page["func"], None)
    if callable(render_fn):
        render_fn()
    else:
        st.error("Unable to load the selected page.")

if __name__ == "__main__":
    main()
