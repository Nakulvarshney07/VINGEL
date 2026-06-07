import streamlit as st
import pandas as pd
from components.tab_segments import render_segments

result = st.session_state.get("result")
if not result:
    st.info("Run a simulation from the sidebar first.", icon="🎯")
    st.stop()

is_dark = st.session_state.get("theme", "dark") == "dark"
seg_df = pd.DataFrame(result["segment_adoption"])

render_segments(seg_df, result["segments"], is_dark=is_dark)
