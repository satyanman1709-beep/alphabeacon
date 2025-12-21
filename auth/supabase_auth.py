import streamlit as st
from supabase import create_client, Client

# ------------------------------------------------------
# Load from Streamlit secrets
# ------------------------------------------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------------------------------
# SIGN IN
# ------------------------------------------------------
def supabase_signin(email: str, password: str):
    try:
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        # If sign-in successful, return the user object
        if response.user:
            return response.user

        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None


# ------------------------------------------------------
# SIGN UP
# ------------------------------------------------------
def supabase_signup(email: str, password: str):
    try:
        response = client.auth.sign_up(
            {"email": email, "password": password}
        )

        if response.user:
            return response.user

        return None
    except Exception as e:
        st.error(f"Signup error: {e}")
        return None


# ------------------------------------------------------
# LOG OUT
# ------------------------------------------------------
def supabase_logout():
    try:
        client.auth.sign_out()
        return True
    except:
        return False


# ------------------------------------------------------
# GET CURRENT USER
# ------------------------------------------------------
def supabase_current_user():
    try:
        result = client.auth.get_user()
        return result.user
    except:
        return None
supabase = client
