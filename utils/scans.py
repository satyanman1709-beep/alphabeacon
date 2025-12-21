import streamlit as st
from supabase import create_client

# Load Supabase credentials from .streamlit/secrets.toml
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def load_today_scans():
    """
    Loads today's scan results from the Supabase 'scans' table.
    """

    try:
        response = (
            supabase.table("scans")
            .select("*")
            .order("alpha_score", desc=True)
            .execute()
        )

        data = getattr(response, "data", None)
        return data if data else []

    except Exception as e:
        print("Error loading scans:", e)
        return []
