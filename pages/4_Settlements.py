import streamlit as st
from expenses_app.ui_components import render_sidebar, init_styles, render_fab

st.set_page_config(page_title="Expenses - Settlements", layout="wide", page_icon="🤝")
init_styles()
render_sidebar()

st.title("🤝 Settlements")

from expenses_app.store import build_event_store
from expenses_app.replay import sort_events, derive_settlements

event_store = build_event_store()
settlements = derive_settlements(sort_events(event_store.load()))

if settlements:
    st.write(settlements)
else:
    st.info("No settlements found.")

render_fab()
