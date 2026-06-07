import streamlit as st
from components.tab_graph import render_graph

BACKEND = "http://localhost:8000"

result = st.session_state.get("result")
if not result:
    st.info("Run a simulation from the sidebar first.", icon="🌐")
    st.stop()

is_dark = st.session_state.get("theme", "dark") == "dark"
render_graph(BACKEND, result, is_dark=is_dark)
