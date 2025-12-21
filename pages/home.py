import streamlit as st

def home_page():
    st.title("🏠 AlphaBeacon Dashboard")

    st.write("Welcome to the AI-powered Stock Intelligence Platform!")

    st.markdown("""
        ### Key Features
        - Real-time sentiment scoring  
        - Sector-level analysis  
        - Backtesting engine  
        - Watchlist with alerts  
        - AI commentary engine  
    """)

    st.info("Use the navigation bar above to explore the platform.")
