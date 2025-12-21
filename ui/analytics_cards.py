import streamlit as st
import plotly.graph_objects as go


def _card(title: str, value_lines, border_color: str):
    """
    Simple reusable HTML card with forced dark text.
    value_lines can be list[str] or a single str.
    """
    if isinstance(value_lines, str):
        value_lines = [value_lines]

    body = "<br>".join([f"<div style='font-size:20px; font-weight:800;'>{v}</div>" for v in value_lines])

    return f"""
    <div style="
        background:#ffffff;
        color:#0f172a;
        padding:22px;
        border-radius:16px;
        box-shadow:0 6px 18px rgba(0,0,0,0.10);
        border-left:7px solid {border_color};
        min-height:110px;
    ">
        <div style="font-size:22px; font-weight:900; margin-bottom:10px;">{title}</div>
        {body}
    </div>
    """


def volatility_meter(atr_percent: float, key: str = "vol_meter"):
    """
    Shows a small gauge-like indicator using Plotly.
    """
    atr_percent = float(atr_percent) if atr_percent is not None else 0.0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=atr_percent,
            number={"suffix": "%"},
            title={"text": "Volatility (ATR%)"},
            gauge={
                "axis": {"range": [0, 10]},
                "bar": {"thickness": 0.3},
            },
        )
    )
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))

    st.plotly_chart(fig, use_container_width=True, key=key)


def confidence_gauge(confidence: int, key: str = "confidence"):
    """
    Fixes duplicate Plotly element IDs by requiring a key.
    """
    confidence = int(confidence) if confidence is not None else 0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence,
            number={"suffix": "/100"},
            title={"text": "Confidence"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"thickness": 0.3},
            },
        )
    )
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))

    st.plotly_chart(fig, use_container_width=True, key=key)


def target_cards(buy_low, buy_high, tp1, tp2, sl, rr):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            _card(
                "Buy Range",
                [f"${buy_low} – ${buy_high}"],
                border_color="#22c55e",
            ),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            _card(
                "Take Profit",
                [f"TP1: ${tp1}", f"TP2: ${tp2}"],
                border_color="#f59e0b",
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            _card(
                "Risk",
                [f"Stop Loss: ${sl}", f"R/R: {rr}"],
                border_color="#ef4444",
            ),
            unsafe_allow_html=True,
        )
