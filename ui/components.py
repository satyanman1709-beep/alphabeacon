import streamlit as st


def sector_card(name, count):
    st.markdown(
        f"""
        <div style="
            background:white;
            border-radius:12px;
            padding:20px;
            box-shadow:0px 4px 10px rgba(0,0,0,0.08);
            cursor:pointer;
            transition:0.2s;
            border-left:6px solid #2ECC71;
        "
        onmouseover="this.style.transform='scale(1.01)'"
        onmouseout="this.style.transform='scale(1)'"
        >
            <h3 style="margin:0; color:#003366;">{name}</h3>
            <p style="margin:0; color:#666;">Top Picks: {count}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def cta_button(label):
    st.markdown(
        f"""
        <a style="
            display:inline-block;
            background:#FF6B3D;
            padding:10px 20px;
            border-radius:8px;
            color:white;
            font-weight:600;
            text-decoration:none;
            margin-top:10px;
        "
        href="#">
            {label}
        </a>
        """,
        unsafe_allow_html=True
    )
