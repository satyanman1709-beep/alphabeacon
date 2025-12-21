import streamlit as st


def technical_trend_meter(score):
    if score >= 80:
        label, color = "Strong Uptrend", "#2ECC71"
    elif score >= 65:
        label, color = "Moderate Uptrend", "#58D68D"
    elif score >= 45:
        label, color = "Sideways", "#F1C40F"
    elif score >= 30:
        label, color = "Weak Downtrend", "#E67E22"
    else:
        label, color = "Strong Downtrend", "#E74C3C"

    st.markdown(
        f"""
        <div style="
            background:white;
            border-radius:12px;
            padding:18px;
            text-align:center;
            box-shadow:0 2px 10px rgba(0,0,0,0.1);
            border-left:6px solid {color};
        ">
            <h4 style="margin:0; color:#003366;">Technical Trend</h4>
            <p style="margin:5px 0; font-size:22px; font-weight:700; color:{color};">
                {label}
            </p>
            <p style="margin:0; color:#777;">Score: {score}/100</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def sentiment_trend_meter(score):
    if score >= 80:
        label, color = "Very Positive", "#2ECC71"
    elif score >= 60:
        label, color = "Positive", "#58D68D"
    elif score >= 40:
        label, color = "Neutral", "#F1C40F"
    elif score >= 25:
        label, color = "Negative", "#E67E22"
    else:
        label, color = "Very Negative", "#E74C3C"

    st.markdown(
        f"""
        <div style="
            background:white;
            border-radius:12px;
            padding:18px;
            text-align:center;
            box-shadow:0 2px 10px rgba(0,0,0,0.1);
            border-left:6px solid {color};
        ">
            <h4 style="margin:0; color:#003366;">Sentiment Trend</h4>
            <p style="margin:5px 0; font-size:22px; font-weight:700; color:{color};">
                {label}
            </p>
            <p style="margin:0; color:#777;">Score: {score}/100</p>
        </div>
        """,
        unsafe_allow_html=True
    )
