import streamlit as st
from auth.supabase_auth import supabase


# -------------------------------------------------
# HELPER: Extract a stable user_id from session
# -------------------------------------------------
def _get_user_id():
    """
    Returns a user_id suitable for Supabase watchlist.
    For Supabase-authenticated users, this is the auth user.id (UUID).
    For local login, returns None (no DB sync).
    """
    user = st.session_state.get("user")
    if not user:
        return None

    # Supabase user object may be a dict or object with .id
    # Try dict-like first
    if isinstance(user, dict):
        uid = user.get("id")
        if uid:
            return str(uid)
        # Local login stored as {"username": ...} – skip DB persistence
        return None

    # Object-like (Supabase user)
    uid = getattr(user, "id", None)
    if uid:
        return str(uid)

    return None


# -------------------------------------------------
# LOAD WATCHLIST FROM DB
# -------------------------------------------------
def _load_watchlist_from_db(user_id):
    try:
        resp = supabase.table("watchlist") \
            .select("ticker") \
            .eq("user_id", user_id) \
            .execute()

        data = getattr(resp, "data", None) or []
        tickers = [row["ticker"].upper() for row in data]
        return sorted(list(set(tickers)))
    except Exception as e:
        # Fail silently and fall back to in-memory list
        return []


# -------------------------------------------------
# INIT STATE (IN-MEMORY + OPTIONAL DB SYNC)
# -------------------------------------------------
def init_state():
    """
    Initializes watchlist in session state and, if possible,
    loads it from Supabase for authenticated Supabase users.
    """
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

    if "watchlist_loaded" not in st.session_state:
        st.session_state["watchlist_loaded"] = False

    # Only try to sync from DB once per session
    if not st.session_state["watchlist_loaded"]:
        user_id = _get_user_id()
        if user_id:
            tickers = _load_watchlist_from_db(user_id)
            if tickers:
                st.session_state["watchlist"] = tickers
        st.session_state["watchlist_loaded"] = True


# -------------------------------------------------
# ADD TO WATCHLIST (LOCAL + DB)
# -------------------------------------------------
def add_to_watchlist(ticker: str):
    """
    Adds a ticker to the local session watchlist and, if the user
    is a Supabase-authenticated user, also persists it to the DB.
    """
    if not ticker:
        return

    ticker = ticker.upper()

    # Update local state
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

    if ticker not in st.session_state["watchlist"]:
        st.session_state["watchlist"].append(ticker)

    # Try to sync to Supabase
    user_id = _get_user_id()
    if not user_id:
        return  # local-only user

    try:
        supabase.table("watchlist").upsert(
            {
                "user_id": user_id,
                "ticker": ticker
            }
        ).execute()
    except Exception:
        # If DB fails, we still keep local watchlist
        pass


# -------------------------------------------------
# REMOVE FROM WATCHLIST (LOCAL + DB)
# -------------------------------------------------
def remove_from_watchlist(ticker: str):
    """
    Removes a ticker from the local session watchlist and DB (if user is Supabase-authenticated).
    """
    if not ticker:
        return

    ticker = ticker.upper()

    # Update local state
    if "watchlist" in st.session_state and ticker in st.session_state["watchlist"]:
        st.session_state["watchlist"].remove(ticker)

    # Try to sync to Supabase
    user_id = _get_user_id()
    if not user_id:
        return

    try:
        supabase.table("watchlist") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("ticker", ticker) \
            .execute()
    except Exception:
        pass
