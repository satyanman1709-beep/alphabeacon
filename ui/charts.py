import streamlit as st
import uuid

def tradingview_chart(ticker, height=480):
    """
    Safe TradingView widget with unique DOM ID for multiple charts.
    Prevents overwrite issues when rendering many charts on one page.
    """

    # Use dark/light mode (defaults to light)
    theme = "dark" if st.session_state.get("theme") == "dark" else "light"

    # Unique ID for each chart instance
    widget_id = f"tv_{uuid.uuid4().hex}"

    widget = f"""
    <div class="tradingview-widget-container">
      <div id="{widget_id}"></div>
      <script type="text/javascript">
      new TradingView.widget({{
          "container_id": "{widget_id}",
          "width": "100%",
          "height": {height},
          "symbol": "{ticker}",
          "interval": "D",
          "timezone": "Etc/UTC",
          "theme": "{theme}",
          "style": "1",
          "locale": "en",
          "toolbar_bg": "{'#0D1B2A' if theme == 'dark' else '#F4F7FB'}",
          "enable_publishing": false,
          "hide_top_toolbar": false,
          "hide_legend": false,
          "save_image": false
      }});
      </script>
    </div>
    """

    st.markdown(widget, unsafe_allow_html=True)
