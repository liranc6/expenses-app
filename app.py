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
    
    st.switch_page("pages/1_Dashboard.py")

if __name__ == "__main__":
    main()
