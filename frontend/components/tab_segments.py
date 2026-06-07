"""Segments tab — adoption bar chart + parameter table."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from .charts import get_chart_theme, PALETTE


def render_segments(seg_df: pd.DataFrame, segments_raw: list,
                    is_dark: bool = True) -> None:

    CT = get_chart_theme(is_dark)
    title_color = "#e2e8f0" if is_dark else "#18181b"
    text_color  = "#e2e8f0" if is_dark else "#18181b"

    if not seg_df.empty:
        fig = go.Figure([go.Bar(
            x=seg_df.segment_name,
            y=seg_df.adoption_rate,
            marker_color=PALETTE[:len(seg_df)],
            marker_line_width=0,
            text=[f"{v*100:.1f}%" for v in seg_df.adoption_rate],
            textposition="outside",
            textfont=dict(color=text_color, size=13, family="Inter"),
        )])
        fig.update_layout(
            **CT,
            title=dict(text="Final Adoption Rate by Segment", font=dict(color=title_color, size=14)),
            yaxis_tickformat=".0%", height=360, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Segment parameter table ───────────────────────────────────────────
    segs = pd.DataFrame(segments_raw)
    cols_show = ["segment_name","share","price_sensitivity","need_urgency",
                 "trust_threshold","tech_affinity","competitor_loyalty","social_influence"]
    sd = segs[cols_show].rename(columns=lambda c: c.replace("_"," ").title())
    for c in sd.columns[1:]:
        sd[c] = sd[c].apply(lambda v: f"{v:.2f}" if isinstance(v, float) else v)
    st.dataframe(sd, use_container_width=True, hide_index=True)
