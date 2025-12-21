import streamlit as st
from utils.auth_state import login_user

def login_page():
    st.title("🔐 Login to AlphaBeacon")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_user(email, password):
            st.success("Logged in successfully")

            # 🔑 THIS WAS MISSING
            st.session_state.page = "home"
            st.rerun()
        else:
            st.error("Invalid email or password")

    st.write("---")
    st.write("Don't have an account?")
    if st.button("Create Account"):
        st.session_state.page = "signup"
        st.rerun()
