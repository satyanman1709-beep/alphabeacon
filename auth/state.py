import streamlit as st

def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None

def login_user(user):
    st.session_state.user = user

def logout_user():
    st.session_state.user = None

def is_logged_in():
    return st.session_state.user is not None
