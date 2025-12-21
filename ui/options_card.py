import streamlit as st

def options_card(data):
    """
    Renders an options strategy suggestion card.
    """

    if data is None:
        return

    strategy = data.get("strategy", "Options Strategy")

    # Build bullet list manually to avoid Markdown/HTML mixing issues
    buy_leg = data.get("buy", "")
    sell_leg = data.get("sell", "")
    note = data.get("note", "")

    bullet_items = ""
    if buy_leg:
        bullet_items += f"<li><strong>{buy_leg}</strong></li>"
    if sell_leg:
        bullet_items += f"<li><strong>{sell_leg}</strong></li>"

    st.markdown(
        f"""
        <div style="
            background:white;
            padding:20px;
            border-radius:12px;
            box-shadow:0px 2px 10px rgba(0,0,0,0.08);
            margin-top:10px;
        ">
            <h4 style="margin:0; color:#003366;">Options Strategy: {strategy}</h4>
            <ul style="line-height:1.6; font-size:15px; margin-top:10px;">
                {bullet_items}
            </ul>
            <p style="margin-top:8px; color:#555;">{note}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
