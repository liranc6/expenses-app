import streamlit as st
from expenses_app.model import Event
from expenses_app.store import build_event_store, parse_amount

DEFAULT_USERS = ["Liran", "Vova"]

def render_settlements():
    st.title("🤝 Settlements")
    
    event_store = build_event_store()

    with st.form("settle_form"):
        f_u = st.selectbox("From", DEFAULT_USERS)
        t_u = st.selectbox("To", [u for u in DEFAULT_USERS if u != f_u])
        s_a = st.text_input("Amount (e.g. 50.00)")
        if st.form_submit_button("Record Settlement", use_container_width=True):
            try:
                amt = parse_amount(s_a)
                if amt <= 0: raise ValueError("Amount must be positive")
                event_store.append(Event.new(type="SETTLEMENT_CREATED", payload={"from": f_u, "to": t_u, "amount": amt}))
                st.success(f"Settlement of ${s_a} from {f_u} to {t_u} recorded!")
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    render_settlements()
