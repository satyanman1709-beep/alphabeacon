import streamlit as st
from utils.auth_state import logout_user
from auth.supabase_auth import supabase_logout

def settings_page():
    st.title("⚙️ Settings")

    user = st.session_state.get("user")
    if user:
        st.markdown(f"Logged in as: **{user.email}**")

    st.write("---")

    if st.button("Log Out"):
        supabase_logout()
        logout_user()
        st.success("Logged out successfully.")

        # Route back to login page
        st.experimental_set_query_params(page="login")
        st.experimental_rerun()
