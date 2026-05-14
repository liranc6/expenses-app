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
        
        /* Hide the ugly standard Streamlit button we use as a trigger */
        div[data-testid="stVerticalBlock"] > div:has(button[aria-label="fab-real-trigger"]) {
            display: none;
        }
        .stButton > button[aria-label="fab-real-trigger"] {
            display: none;
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
        st.switch_page("app.py")
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
    from expenses_app.replay import default_equal_splits
    from uuid import uuid4
    
    col1, col2 = st.columns(2)
    amount_input = col1.text_input("Total amount (e.g. 15.50)", key="dlg_amount")
    note_input = col2.text_input("Note", key="dlg_note")
    
    cat = st.selectbox("Category", list(CATEGORIES.keys()), format_func=lambda x: f"{CATEGORIES[x]} {x}", key="dlg_cat")
    payer = st.selectbox("Payer", DEFAULT_USERS, key="dlg_payer")
    
    st.markdown("---")
    st.write("**Splits**")
    split_mode = st.radio("Method", ["Equal", "By percentage", "By amount"], horizontal=True, key="dlg_split_mode")
    
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
            st.caption(f"Equal splits: {amount_cents/200:.2f} each")
    
    elif split_mode == "By percentage":
        cols = st.columns(len(DEFAULT_USERS))
        if len(DEFAULT_USERS) == 2:
            user1, user2 = DEFAULT_USERS[0], DEFAULT_USERS[1]
            p1 = cols[0].number_input(f"{user1} %", min_value=0, max_value=100, value=50, key="dlg_p1")
            p2 = 100 - p1
            cols[1].text_input(f"{user2} %", value=str(p2), disabled=True, key="dlg_p2")
            splits[user1] = int(amount_cents * p1 / 100)
            splits[user2] = amount_cents - splits[user1]
        
    elif split_mode == "By amount":
        cols = st.columns(len(DEFAULT_USERS))
        if len(DEFAULT_USERS) == 2:
            user1, user2 = DEFAULT_USERS[0], DEFAULT_USERS[1]
            a1_str = cols[0].text_input(f"{user1} amount", value="", key="dlg_a1")
            try:
                a1 = parse_amount(a1_str) if a1_str else 0
                splits[user1] = a1
                a2 = amount_cents - a1
                cols[1].text_input(f"{user2} amount", value=f"{a2/100:.2f}", disabled=True, key="dlg_a2")
                splits[user2] = a2
            except:
                splits[user1] = 0
                splits[user2] = 0

    if st.button("Create Expense", type="primary", use_container_width=True):
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
    # Robust JS trigger that tries both parent and local document context
    st.markdown("""
        <div class="fab-container">
            <button class="fab-button" onclick="
                const findAndClick = (ctx) => {
                    const btn = Array.from(ctx.querySelectorAll('button')).find(el => el.innerText === 'hidden_fab_trigger');
                    if (btn) { btn.click(); return true; }
                    return false;
                };
                if (!findAndClick(document)) {
                    findAndClick(parent.document);
                }
            ">+</button>
        </div>
    """, unsafe_allow_html=True)
    
    # Text matches the JS query. We'll make it almost invisible or rely on the CSS 'display: none'
    if st.button("hidden_fab_trigger", key="fab_real_trigger", help="Add New Expense"):
        add_expense_dialog()
