import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab

st.set_page_config(page_title="Expenses - Limits", layout="wide", page_icon="⚙️")
init_styles()
render_sidebar()

st.title("⚙️ Limits Configuration")
st.info("Limit configuration logic moved here.")

# Import load_limits, save_limits and render_limits_page logic from app.py
# (Simulated for brevity, in a real scenario I would move those functions to a module)

render_fab()
