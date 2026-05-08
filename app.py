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

DEFAULT_USERS = ["Liran", "Vova"]
CATEGORIES = {
    "Food": "🍕",
    "Transport": "🚗",
    "Travel": "✈️",
    "Bill": "📄",
    "Other": "📦",
}

LIMITS_FILE = os.path.join(os.path.dirname(__file__), "limits.json")

def load_limits():
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r") as f:
            return json.load(f)
    return {u: {c: 0 for c in CATEGORIES} for u in DEFAULT_USERS}

def save_limits(limits):
    with open(LIMITS_FILE, "w") as f:
        json.dump(limits, f, indent=4)


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


def render_limits_page():
    st.header("⚙️ Limits Configuration")
    st.write("Set monthly spending limits per category for each user.")
    
    limits = load_limits()
    updated = False
    
    for user in DEFAULT_USERS:
        with st.expander(f"👤 {user} Limits", expanded=True):
            user_limits = limits.get(user, {c: 0 for c in CATEGORIES})
            cols = st.columns(len(CATEGORIES))
            for i, (cat, emoji) in enumerate(CATEGORIES.items()):
                current_limit_cents = user_limits.get(cat, 0)
                # Show as float in UI
                new_limit_val = cols[i].number_input(
                    f"{emoji} {cat}", 
                    min_value=0.0, 
                    value=float(current_limit_cents / 100),
                    step=10.0,
                    key=f"limit_{user}_{cat}"
                )
                new_limit_cents = int(new_limit_val * 100)
                if new_limit_cents != current_limit_cents:
                    user_limits[cat] = new_limit_cents
                    limits[user] = user_limits
                    updated = True
    
    if updated:
        if st.button("Save Changes", type="primary"):
            save_limits(limits)
            st.success("Limits updated successfully!")
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Expenses App", layout="wide", page_icon="💰")
    
    # Custom CSS for Green Buttons and Performance (Minimalistic)
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            transition: background-color 0.1s ease-in-out;
        }
        /* Green primary button style */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            border-color: #28a745 !important;
            color: white !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #218838 !important;
            border-color: #1e7e34 !important;
        }
        </style>
    """, unsafe_allow_html=True) 

    st.sidebar.title("💰 Expenses App")
    page = st.sidebar.radio("Go to", ["Dashboard", "Limits Configuration"])
    
    if page == "Limits Configuration":
        render_limits_page()
        return

    st.sidebar.header("Navigation")
    active_user = st.sidebar.selectbox("Logged in as", DEFAULT_USERS, index=0)
    
    # Persistent State for inputs
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = ""
    if "active_payer" not in st.session_state:
        st.session_state.active_payer = active_user

    event_store = build_event_store()
    events = sort_events(event_store.load())
    expenses = derive_expense_state(events)
    settlements = derive_settlements(events)
    balances = compute_balances(expenses, settlements)
    
    budget_targets = load_limits()

    # --- SIDEBAR BALANCES ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Live Balances")
    if balances:
        for user, amount in sorted(balances.items(), key=lambda item: -item[1]):
            # Mapping for backward compatibility
            display_user = user
            if user == "You": display_user = "Liran"
            if user == "Partner": display_user = "Vova"
            
            label = f"{display_user} (You)" if display_user == active_user else display_user
            formatted = f"${format_currency(amount)}"
            st.sidebar.metric(label=label, value=formatted)
            
            # BUDGET WARNINGS
            user_limits = budget_targets.get(display_user, {})
            for cat, limit in user_limits.items():
                if limit <= 0: continue
                consumed = 0
                for exp in expenses.values():
                    if exp.get("category") == cat:
                        consumed += exp["splits"].get(user, 0)
                
                if consumed >= limit * 0.85:
                    scat = f"{CATEGORIES.get(cat, '')} {cat}"
                    if consumed >= limit:
                        st.sidebar.error(f"🚨 {display_user}: {scat} LIMIT EXCEEDED! ({format_currency(consumed)}/${format_currency(limit)})")
                    else:
                        st.sidebar.warning(f"⚠️ {display_user}: {scat} at 85%+ ({format_currency(consumed)}/${format_currency(limit)})")
    else:
        st.sidebar.info("No balances yet.")
    
    st.sidebar.markdown("---")
    search_query = safe_string(st.sidebar.text_input("🔍 Search notes", value=""))
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
    payer_totals = {}
    for expense in filtered_expenses.values():
        category = expense.get("category", "Other") or "Other"
        category_totals[category] = category_totals.get(category, 0) + expense["amount"]
        payer = expense.get("payer", "Unknown")
        payer_totals[payer] = payer_totals.get(payer, 0) + expense["amount"]

    # --- TOP SECTION: Visual Overview ---
    st.subheader("Summary Visualization")
    col_p1, col_p2 = st.columns([1, 1])
    
    with col_p1:
        if category_totals:
            # Map labels to include emojis
            cat_names = [f"{CATEGORIES.get(k, '')} {k}" for k in category_totals.keys()]
            fig_cat = px.pie(
                names=cat_names, 
                values=[v/100 for v in category_totals.values()], 
                title="Expenses by Category",
                hole=.4
            )
            st.plotly_chart(fig_cat, use_container_width=True)

    with col_p2:
        if payer_totals:
            fig_payer = px.pie(
                names=list(payer_totals.keys()), 
                values=[v/100 for v in payer_totals.values()], 
                title="Spending Distribution (Payer)",
                hole=.4
            )
            st.plotly_chart(fig_payer, use_container_width=True)

    # --- BUDGET UTILIZATION SECTION (Active User Only) ---
    st.markdown("---")
    st.subheader(f"📊 Your Budget Utilization ({active_user})")
    user_limits = budget_targets.get(active_user, {})
    if any(limit > 0 for limit in user_limits.values()):
        cols = st.columns(len(CATEGORIES))
        for i, (cat, emoji) in enumerate(CATEGORIES.items()):
            limit = user_limits.get(cat, 0)
            if limit > 0:
                consumed = sum(
                    exp["splits"].get(active_user, 0)
                    for exp in expenses.values()
                    if exp.get("category") == cat
                )
                percent = min(consumed / limit, 1.0)
                
                with cols[i]:
                    st.write(f"{emoji} **{cat}**")
                    st.progress(percent)
                    color = "normal"
                    if percent >= 1.0:
                        st.error(f"{format_currency(consumed)} / {format_currency(limit)}")
                    elif percent >= 0.85:
                        st.warning(f"{format_currency(consumed)} / {format_currency(limit)}")
                    else:
                        st.info(f"{format_currency(consumed)} / {format_currency(limit)}")
    else:
        st.info("No limits set for your account. Go to 'Limits Configuration' to set them.")

    st.markdown("---")
    st.header("Write events")
    
    with st.expander("➕ Create a new expense", expanded=True):
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            amount_input = st.text_input("Total amount (e.g. 15.50)", value="", key="amount_input")
        with col_input2:
            note_input = st.text_input("Note / description", value="", key="note_input", placeholder="Dinner, Taxi, etc.")
        
        # Auto-detect category
        detected_cat = classify_category(note_input)
        if detected_cat and st.session_state.selected_category == "":
            st.session_state.selected_category = detected_cat

        # Category Buttons
        st.write("**Category**")
        cat_list = list(CATEGORIES.keys())
        # Use a form or a container to prevent multiple reruns if possible, 
        # but Streamlit reruns on button click. Let's optimize by checking if change is needed.
        cat_cols = st.columns(len(cat_list))
        for i, cat in enumerate(cat_list):
            emoji = CATEGORIES[cat]
            is_selected = (st.session_state.selected_category == cat)
            btn_type = "primary" if is_selected else "secondary"
            if cat_cols[i].button(f"{emoji} {cat}", key=f"btn_cat_{cat}", type=btn_type, use_container_width=True):
                if st.session_state.selected_category != cat:
                    st.session_state.selected_category = cat
                    st.rerun()

        # Payer Buttons
        st.write("**Payer**")
        pay_cols = st.columns(len(DEFAULT_USERS))
        for i, user in enumerate(DEFAULT_USERS):
            is_active = (st.session_state.active_payer == user)
            p_type = "primary" if is_active else "secondary"
            if pay_cols[i].button(f"👤 {user}", key=f"btn_pay_{user}", type=p_type, use_container_width=True):
                if st.session_state.active_payer != user:
                    st.session_state.active_payer = user
                    st.rerun()
        
        st.markdown("---")
        # Splitwise-style splits
        st.write("**Splits**")
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
                splits = default_equal_splits(amount_cents, DEFAULT_USERS, st.session_state.active_payer)
                st.caption(f"Equal splits: {format_currency(splits[DEFAULT_USERS[0]])} each")
        
        elif split_mode == "By percentage":
            cols = st.columns(len(DEFAULT_USERS))
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

        if st.button("Create expense", key="create_btn", type="primary", use_container_width=True):
            try:
                if not amount_input: raise ValueError("Amount is required")
                if sum(splits.values()) != amount_cents: raise ValueError("Split totals must equal amount")
                
                event = Event.new(
                    type="EXPENSE_CREATED",
                    payload={
                        "expense_id": uuid4().hex,
                        "amount": amount_cents,
                        "payer": st.session_state.active_payer,
                        "splits": splits,
                        "category": st.session_state.selected_category or detected_cat,
                        "note": note_input,
                    },
                )
                event_store.append(event)
                st.session_state.selected_category = "" # Reset
                st.success("Expense created!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.markdown("---")
    
    # Remove Expense ID (hash) from table
    st.subheader("📜 Recent Activity")
    if filtered_expenses:
        active_display = [
            {
                "Payer": f"👤 {expense['payer']}",
                "Amount": f"${format_currency(expense['amount'])}",
                "Category": f"{CATEGORIES.get(expense.get('category', 'Other'), '📦')} {expense.get('category', 'Other')}",
                "Note": expense.get("note", ""),
                "Splits": ", ".join(f"{u}: {a/100:.2f}" for u, a in expense["splits"].items()),
            }
            for expense in filtered_expenses.values()
        ]
        st.dataframe(active_display, use_container_width=True)
    else:
        st.info("No matching expenses.")

    st.markdown("---")
    with st.expander("🛠️ Admin Controls (Edit/Delete/Settlement)"):
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
