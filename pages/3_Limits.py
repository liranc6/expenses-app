import json
import os
import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab, CATEGORIES

st.set_page_config(page_title="Expenses - Limits", layout="wide", page_icon="⚙️")
init_styles()
render_sidebar()

st.title("⚙️ Limits Configuration")
st.info("Limit configuration logic moved here.")

def load_limits():
    try:
        with open("limits.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_limits(limits):
    with open("limits.json", "w") as f:
        json.dump(limits, f, indent=4)

def render_limits_page():
    st.subheader("Monthly Limits")
    limits = load_limits()
    
    new_limits = {}
    for category, icon in CATEGORIES.items():
        limit_value = limits.get(category)
        new_limit = st.number_input(
            f"{icon} {category}", 
            value=limit_value, 
            min_value=0, 
            step=50,
            key=f"limit_{category}"
        )
        if new_limit is not None:
            new_limits[category] = new_limit
            
    if st.button("Save Limits"):
        save_limits(new_limits)
        st.success("Limits saved successfully!")
        st.rerun()

render_limits_page()
render_fab()
