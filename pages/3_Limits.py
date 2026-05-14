import streamlit as st
import os
import json

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

def save_limits(limits):
    with open(LIMITS_FILE, "w") as f:
        json.dump(limits, f, indent=4)

def parse_amount(val) -> int:
    try:
        return int(float(val) * 100)
    except:
        return 0

def format_currency(value: int) -> str:
    return f"{value / 100:.2f}"

def render_limits():
    st.title("⚙️ Limits Configuration")
    limits = load_limits()

    for user in DEFAULT_USERS:
        st.subheader(f"Limits for {user}")
        user_limits = limits.get(user, {c: 0 for c in CATEGORIES})
        cols = st.columns(len(CATEGORIES))
        for i, (cat, emoji) in enumerate(CATEGORIES.items()):
            current_limit = user_limits.get(cat, 0)
            new_val = cols[i].text_input(f"{emoji} {cat}", value=format_currency(current_limit), key=f"limit_{user}_{cat}")
            user_limits[cat] = parse_amount(new_val)
        limits[user] = user_limits

    if st.button("Save Limits", type="primary"):
        save_limits(limits)
        st.success("Limits saved successfully!")

if __name__ == "__main__":
    render_limits()
