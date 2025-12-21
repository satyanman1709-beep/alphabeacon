import streamlit as st
import time
import random


def loading_screen():
    messages = [
        "Scanning 2,341 US stocks…",
        "Assessing technical patterns…",
        "Extracting sentiment signals…",
        "Computing ATR-based risk levels…",
        "Building Alpha Score rankings…",
        "Finding today's strongest opportunities…"
    ]

    loading_placeholder = st.empty()

    for msg in messages:
        loading_placeholder.markdown(
            f"""
            <div style='padding:40px; text-align:center;'>
                <h2 style='color:#2ECC71;'>{msg}</h2>
                <img src="https://i.gifer.com/ZKZg.gif" height="70">
            </div>
            """,
            unsafe_allow_html=True
        )
        time.sleep(random.uniform(0.5, 1.0))

    loading_placeholder.empty()
