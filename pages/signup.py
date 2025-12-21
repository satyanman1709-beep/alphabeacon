import streamlit as st
from utils.auth_state import signup_user

def signup_page():
    st.title("📝 Create Your AlphaBeacon Account")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        user = signup_user(email, password)
        if user:
            st.success("Account created! Please verify your email.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Signup failed.")

    st.write("---")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()
