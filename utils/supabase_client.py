from __future__ import annotations

from supabase import create_client, Client
import streamlit as st


def get_supabase_client() -> Client:
    """
    Streamlit app client (READ-ONLY with anon key).
    Uses .streamlit/secrets.toml or Streamlit Cloud secrets.
    """
    url = st.secrets["supabase"]["url"]
    anon_key = st.secrets["supabase"]["anon_key"]
    return create_client(url, anon_key)
