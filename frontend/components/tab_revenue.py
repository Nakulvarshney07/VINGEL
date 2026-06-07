"""Revenue tab — MRR fan chart + cumulative revenue."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from .charts import get_chart_theme


def render_revenue(base_df: pd.DataFrame, p10_df: pd.DataFrame,
                   p50_df: pd.DataFrame, p90_df: pd.DataFrame,
                   is_dark: bool = True) -> None:

    CT = get_chart_theme(is_dark)
    title_color = "#e2e8f0" if is_dark else "#18181b"

    # ── MRR Monte Carlo fan ───────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=p90_df.month, y=p90_df.mrr,
        fill=None, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=p10_df.month, y=p10_df.mrr,
        fill="tonexty", mode="lines", line=dict(width=0),
        fillcolor="rgba(129,140,248,0.13)", name="P10–P90 uncertainty",
    ))
    fig.add_trace(go.Scatter(
        x=p50_df.month, y=p50_df.mrr,
        mode="lines", line=dict(color="#818cf8", width=1.8, dash="dot"), name="P50 median",
    ))
    fig.add_trace(go.Scatter(
        x=base_df.month, y=base_df.mrr,
        mode="lines", line=dict(color="#f472b6", width=2.5), name="Base scenario",
        fill="tozeroy", fillcolor="rgba(244,114,182,0.04)",
    ))
    fig.update_layout(
        **CT,
        title=dict(text="Monthly Recurring Revenue", font=dict(color=title_color, size=14)),
        xaxis_title="Month", yaxis_title="MRR ($)", hovermode="x unified", height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Cumulative revenue ────────────────────────────────────────────────
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=p90_df.month, y=p90_df.cumulative_revenue,
        fill=None, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig2.add_trace(go.Scatter(
        x=p10_df.month, y=p10_df.cumulative_revenue,
        fill="tonexty", mode="lines", line=dict(width=0),
        fillcolor="rgba(6,182,212,0.10)", name="P10–P90 band",
    ))
    fig2.add_trace(go.Scatter(
        x=base_df.month, y=base_df.cumulative_revenue,
        mode="lines", line=dict(color="#06b6d4", width=2.5), name="Cumulative revenue",
        fill="tozeroy", fillcolor="rgba(6,182,212,0.04)",
    ))
    fig2.update_layout(
        **CT,
        title=dict(text="Cumulative Revenue", font=dict(color=title_color, size=14)),
        xaxis_title="Month", yaxis_title="Revenue ($)", hovermode="x unified", height=330,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw data expander ─────────────────────────────────────────────────
    with st.expander("📋 Raw monthly data"):
        bd = base_df.copy()
        bd["mrr"]                = bd["mrr"].apply(lambda x: f"${x:,.0f}")
        bd["cumulative_revenue"] = bd["cumulative_revenue"].apply(lambda x: f"${x:,.0f}")
        bd["adoption_rate"]      = bd["adoption_rate"].apply(lambda x: f"{x*100:.2f}%")
        bd["churn_rate"]         = bd["churn_rate"].apply(lambda x: f"{x*100:.2f}%")
        bd.columns = [c.replace("_"," ").title() for c in bd.columns]
        st.dataframe(bd, use_container_width=True, hide_index=True)

        mc_tbl = pd.DataFrame({
            "Month":         p50_df.month,
            "P10 MRR":       p10_df.mrr.apply(lambda x: f"${x:,.0f}"),
            "P50 MRR":       p50_df.mrr.apply(lambda x: f"${x:,.0f}"),
            "P90 MRR":       p90_df.mrr.apply(lambda x: f"${x:,.0f}"),
            "P10 Customers": p10_df.total_customers,
            "P50 Customers": p50_df.total_customers,
            "P90 Customers": p90_df.total_customers,
        })
        st.dataframe(mc_tbl, use_container_width=True, hide_index=True)
