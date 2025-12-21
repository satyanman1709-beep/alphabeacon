import streamlit as st
import yfinance as yf
from utils.state import remove_from_watchlist


def watchlist_card(ticker):

    df = yf.download(ticker, period="5d", progress=False)
    last_price = round(df["Close"].iloc[-1], 2)

    st.markdown(
        f"""
        <div style="
            background:white;
            border-radius:12px;
            padding:18px;
            box-shadow:0 2px 10px rgba(0,0,0,0.08);
            margin-bottom:12px;
        ">
            <h3 style="margin:0; color:#003366;">{ticker}</h3>
            <p style="margin:5px 0; color:#555;">Last Price: ${last_price}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(f"Remove {ticker}", key=f"rm_{ticker}"):
        remove_from_watchlist(ticker)
        st.experimental_rerun()
