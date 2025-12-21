import streamlit as st
from ui.watchlist_card import watchlist_card
from utils.state import init_state


def watchlist_page():

    init_state()

    st.markdown(
        """
        <h1 style="font-size:40px; font-weight:900; color:#003366;">
            Your Watchlist
        </h1>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state["watchlist"]:
        st.info("Your watchlist is empty. Add stocks from the sector pages.")
        return

    for ticker in st.session_state["watchlist"]:
        watchlist_card(ticker)
