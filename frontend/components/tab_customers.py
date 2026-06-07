"""Customers tab — active users over time + acquisition vs churn bar."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
from .charts import get_chart_theme


def render_customers(base_df: pd.DataFrame, p10_df: pd.DataFrame,
                     p50_df: pd.DataFrame, p90_df: pd.DataFrame,
                     is_dark: bool = True) -> None:

    CT = get_chart_theme(is_dark)
    title_color = "#e2e8f0" if is_dark else "#18181b"
    grid_color  = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.06)"
    axis_color  = "#334165" if is_dark else "#a1a1aa"

    # ── Active customers fan ──────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=p90_df.month, y=p90_df.total_customers,
        fill=None, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=p10_df.month, y=p10_df.total_customers,
        fill="tonexty", mode="lines", line=dict(width=0),
        fillcolor="rgba(139,92,246,0.12)", name="P10–P90 band",
    ))
    fig.add_trace(go.Scatter(
        x=p50_df.month, y=p50_df.total_customers,
        mode="lines", line=dict(color="#a78bfa", width=1.8, dash="dot"), name="P50 median",
    ))
    fig.add_trace(go.Scatter(
        x=base_df.month, y=base_df.total_customers,
        mode="lines", line=dict(color="#f472b6", width=2.5), name="Base scenario",
    ))
    fig.update_layout(
        **CT,
        title=dict(text="Active Customers Over Time", font=dict(color=title_color, size=14)),
        xaxis_title="Month", yaxis_title="Customers", hovermode="x unified", height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Acquisition vs churn waterfall ────────────────────────────────────
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(
        x=base_df.month, y=base_df.new_customers,
        name="New", marker_color="#34d399",
        marker_line_width=0, opacity=0.85,
    ), secondary_y=False)
    fig2.add_trace(go.Bar(
        x=base_df.month, y=-base_df.churned_customers,
        name="Churned", marker_color="#f87171",
        marker_line_width=0, opacity=0.85,
    ), secondary_y=False)
    fig2.add_trace(go.Scatter(
        x=base_df.month, y=base_df.churn_rate * 100,
        mode="lines+markers", name="Churn rate (%)",
        line=dict(color="#fbbf24", width=2), marker=dict(size=3),
    ), secondary_y=True)
    fig2.update_layout(
        **CT,
        title=dict(text="Monthly Acquisition vs Churn", font=dict(color=title_color, size=14)),
        barmode="overlay", height=330, hovermode="x unified",
    )
    fig2.update_yaxes(title_text="Customers", secondary_y=False,
                      gridcolor=grid_color, color=axis_color)
    fig2.update_yaxes(title_text="Churn %",   secondary_y=True,
                      gridcolor=grid_color, color=axis_color, showgrid=False)
    st.plotly_chart(fig2, use_container_width=True)
