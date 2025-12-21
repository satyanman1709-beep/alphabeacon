import streamlit as st

class AuthState:
    @staticmethod
    def init():
        """Initialize session state variables."""
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False
        if "user_email" not in st.session_state:
            st.session_state["user_email"] = None

    @staticmethod
    def login(email: str):
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email

    @staticmethod
    def logout():
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = None

    @staticmethod
    def is_logged_in():
        return st.session_state.get("authenticated", False)
