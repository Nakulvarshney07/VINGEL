import streamlit as st
from components.tab_assumptions import render_assumptions

result = st.session_state.get("result")
if not result:
    st.info("Run a simulation from the sidebar first.", icon="⚙️")
    st.stop()

is_dark = st.session_state.get("theme", "dark") == "dark"
render_assumptions(result["assumptions"], is_dark=is_dark)
