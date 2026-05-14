import json
import os
import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab, CATEGORIES, DEFAULT_USERS

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
LIMITS_FILE = os.path.join(ROOT_DIR, "limits.json")


def load_limits():
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r") as f:
            return json.load(f)
    return {u: {c: 0 for c in CATEGORIES} for u in DEFAULT_USERS}


def save_limits(limits):
    with open(LIMITS_FILE, "w") as f:
        json.dump(limits, f, indent=4)


def render_limits_page():
    st.title("⚙️ Limits Configuration")
    st.write("Set monthly spending limits per category for each user.")

    limits = load_limits()
    updated = False

    for user in DEFAULT_USERS:
        with st.expander(f"👤 {user} Limits", expanded=True):
            user_limits = limits.get(user, {c: 0 for c in CATEGORIES})
            cols = st.columns(len(CATEGORIES))
            for i, (cat, emoji) in enumerate(CATEGORIES.items()):
                current_limit_cents = user_limits.get(cat, 0)
                new_limit_val = cols[i].number_input(
                    f"{emoji} {cat}",
                    min_value=0.0,
                    value=float(current_limit_cents / 100),
                    step=10.0,
                    key=f"limit_{user}_{cat}",
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
            st.experimental_rerun()


st.set_page_config(page_title="Expenses - Limits", layout="wide", page_icon="⚙️")
init_styles()
render_sidebar()
render_limits_page()
render_fab()
