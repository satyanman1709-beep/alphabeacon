import streamlit as st

from pages.login import login_page
from pages.signup import signup_page
from pages.home import home_page
from pages.sector_page import sector_page
from pages.backtest import backtest_page
from pages.watchlist import watchlist_page
from pages.settings import settings_page

from utils.auth_state import init_auth_state, logout_user


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="AlphaBeacon",
    page_icon="📈",
    layout="wide"
)


# -------------------------------------------------
# NAVBAR (SESSION-STATE SAFE + UNIFORM BUTTONS)
# -------------------------------------------------
def navbar():
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] { gap: 10px; }

        div[data-testid="stHorizontalBlock"] button {
            background-color:#003366 !important;
            color:white !important;
            font-weight:700 !important;
            border-radius:10px !important;
            padding:10px 14px !important;

            /* uniform size */
            height:52px !important;

            /* prevent wrapping */
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
        }

        /* Make logout slightly different */
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            border: 1px solid rgba(255,255,255,0.25) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Give longer labels more width so they don't wrap
    cols = st.columns([1.1, 1.5, 1.5, 1.6, 1.7, 1.1, 1.2, 1.4, 1.2, 1.2])

    nav_items = [
        ("Home", "home"),
        ("Technology", "Technology"),
        ("Healthcare", "Healthcare"),
        ("Financials", "Financials"),
        ("Industrials", "Industrials"),
        ("Energy", "Energy"),
        ("Backtest", "Backtest"),
        ("Watchlist", "watchlist"),
        ("Settings", "Settings"),
        ("Logout", "logout"),
    ]

    for col, (label, page) in zip(cols, nav_items):
        with col:
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.page = page
                st.rerun()


# -------------------------------------------------
# ROUTER WITH AUTH GUARD
# -------------------------------------------------
def router(page: str):
    # Public
    if page == "login":
        login_page()
        return

    if page == "signup":
        signup_page()
        return

    # Logout
    if page == "logout":
        logout_user()
        st.session_state.page = "login"
        st.success("Logged out successfully.")
        st.rerun()
        return

    # Auth guard (all private pages)
    if st.session_state.get("user") is None:
        st.session_state.page = "login"
        login_page()
        return

    # Private pages
    if page == "home":
        home_page()

    elif page in ["Technology", "Healthcare", "Financials", "Industrials", "Energy"]:
        sector_page(page)

    elif page == "Backtest":
        backtest_page()

    elif page == "watchlist":
        watchlist_page()

    elif page == "Settings":
        settings_page()

    else:
        st.session_state.page = "home"
        home_page()


# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    init_auth_state()

    # default route
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Navbar only if logged in and not on login/signup
    if st.session_state.get("user") and st.session_state.page not in ("login", "signup"):
        navbar()

    router(st.session_state.page)


if __name__ == "__main__":
    main()
