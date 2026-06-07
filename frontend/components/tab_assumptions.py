"""Assumptions tab — metrics grid + radar chart."""
import streamlit as st
import plotly.graph_objects as go
from .charts import get_chart_theme


def render_assumptions(assum: dict, is_dark: bool = True) -> None:

    ac1, ac2 = st.columns(2)
    _left = [
        ("Total Addressable Market", f"{assum['total_addressable_market']:,}"),
        ("Problem Severity",          f"{assum['problem_severity']:.0%}"),
        ("Feature Match",             f"{assum['feature_match']:.0%}"),
        ("Switching Cost",            f"{assum['switching_cost']:.0%}"),
    ]
    _right = [
        ("Brand Recognition", f"{assum['brand_recognition']:.0%}"),
        ("Virality",          f"{assum['virality_coefficient']:.2f}×"),
        ("Marketing Reach",   f"{assum['monthly_marketing_reach']*100:.1f}%"),
        ("Monthly Churn",     f"{assum['churn_rate_monthly']*100:.1f}%"),
    ]
    for lbl, val in _left:  ac1.metric(lbl, val)
    for lbl, val in _right: ac2.metric(lbl, val)

    st.divider()

    # ── Radar chart ───────────────────────────────────────────────────────
    CT = get_chart_theme(is_dark)
    polar_bg   = "#050712"             if is_dark else "#f8f8fc"
    grid_color = "#0c0f22"             if is_dark else "rgba(0,0,0,0.08)"
    tick_color = "#263050"             if is_dark else "#a1a1aa"
    label_color= "#64748b"             if is_dark else "#52525b"
    title_color= "#e2e8f0"             if is_dark else "#18181b"
    paper_bg   = CT["paper_bgcolor"]

    cats = ["Problem Severity","Feature Match","Brand Recognition",
            "Virality","Low Churn","Mktg Reach"]
    vals = [
        assum["problem_severity"],
        assum["feature_match"],
        assum["brand_recognition"],
        min(assum["virality_coefficient"] / 2, 1.0),
        1 - min(assum["churn_rate_monthly"] / 0.2, 1.0),
        min(assum["monthly_marketing_reach"] / 0.06, 1.0),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself",
        fillcolor="rgba(99,102,241,0.16)",
        line=dict(color="#818cf8", width=2.5),
        marker=dict(color="#818cf8", size=7),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=polar_bg,
            radialaxis=dict(
                visible=True, range=[0,1], gridcolor=grid_color,
                tickfont=dict(color=tick_color, size=9), tickcolor=tick_color,
            ),
            angularaxis=dict(gridcolor=grid_color, tickfont=dict(color=label_color, size=11)),
        ),
        paper_bgcolor=paper_bg,
        font=dict(color=label_color),
        showlegend=False, height=400,
        title=dict(text="Product Strength Radar", font=dict(color=title_color, size=14)),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
