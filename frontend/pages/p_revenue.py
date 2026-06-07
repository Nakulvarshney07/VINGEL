import streamlit as st
import pandas as pd
from components.tab_revenue import render_revenue

result = st.session_state.get("result")
if not result:
    st.info("Run a simulation from the sidebar first.", icon="📊")
    st.stop()

is_dark = st.session_state.get("theme", "dark") == "dark"
base_df = pd.DataFrame(result["base_monthly"])
p10_df  = pd.DataFrame(result["mc_p10"])
p50_df  = pd.DataFrame(result["mc_p50"])
p90_df  = pd.DataFrame(result["mc_p90"])

render_revenue(base_df, p10_df, p50_df, p90_df, is_dark=is_dark)
