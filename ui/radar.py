import streamlit as st
import plotly.graph_objects as go


def radar_alpha_chart(momentum, trend, volume, sentiment, volatility):
    categories = [
        "Momentum",
        "Trend Strength",
        "Volume Divergence",
        "Sentiment",
        "Volatility Adjusted"
    ]

    values = [momentum, trend, volume, sentiment, volatility]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor="rgba(46, 204, 113, 0.4)",
        line=dict(color="#2ECC71", width=3)
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        height=420,
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
