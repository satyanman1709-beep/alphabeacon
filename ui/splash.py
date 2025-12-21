import streamlit as st
import time


def show_splash():
    splash_html = """
    <style>
    .splash-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 90vh;
        background: #0D1B2A;
        animation: fadeIn 1s ease-out;
    }

    .splash-logo {
        height: 120px;
        margin-bottom: 30px;
    }

    .splash-title {
        color: #E0E8F2;
        font-size: 38px;
        font-weight: 800;
        margin-top: 15px;
        text-align: center;
    }

    .splash-subtitle {
        color: #A8BED6;
        font-size: 20px;
        margin-top: 10px;
        text-align: center;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>

    <div class="splash-container">
        <img class="splash-logo" src="assets/logo_dark.png">
        <div class="splash-title">AlphaBeacon</div>
        <div class="splash-subtitle">Your Daily AI-Powered Market Advantage</div>
    </div>
    """

    st.markdown(splash_html, unsafe_allow_html=True)
    time.sleep(1.6)
