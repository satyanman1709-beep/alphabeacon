import streamlit as st
from auth.supabase_auth import supabase_signin, supabase_signup

def init_auth_state():
    if "user" not in st.session_state:
        st.session_state["user"] = None

def login_user(email, password):
    user = supabase_signin(email, password)
    if user:
        st.session_state["user"] = user
        return True
    return False

def signup_user(email, password):
    user = supabase_signup(email, password)
    return user

def logout_user():
    st.session_state["user"] = None

def is_logged_in():
    return st.session_state.get("user") is not None
