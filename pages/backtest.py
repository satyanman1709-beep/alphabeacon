import streamlit as st
import plotly.graph_objects as go

from backtest.backtest_engine import BacktestEngine
from utils.scans import load_today_scans   # NEW: loads from Supabase


def backtest_page():

    st.markdown(
        "<h1 style='color:#003366;'>📈 Backtest Results</h1>",
        unsafe_allow_html=True
    )

    # -------------------------------
    # Load today's scan results
    # -------------------------------
    scan_data = load_today_scans()

    if not scan_data:
        st.warning("No scan results found for today. Please run a scan first.")
        return

    # Convert Supabase rows into ranked list
    ranked = [
        {
            "ticker": row["ticker"],
            "alpha_score": row["alpha_score"]
        }
        for row in scan_data
    ]

    # Sort descending by alpha_score
    ranked = sorted(ranked, key=lambda x: x["alpha_score"], reverse=True)

    # -------------------------------
    # Run Backtest Engine
    # -------------------------------
    engine = BacktestEngine(
        tech_weight=0.6,      # or from user settings later
        sent_weight=0.4,
        lookback_years=2
    )

    data = engine.run_backtest(ranked)

    if not data:
        st.error("Backtest failed: no valid historical data.")
        return

    # -------------------------------
    # Display Metrics
    # -------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Win Rate", f"{data['win_rate']}%")
    col2.metric("Avg Return", f"{data['avg_return']}%")
    col3.metric("Max Drawdown", f"{data['max_drawdown']}%")
    col4.metric("Sharpe", round(data["sharpe"], 2))

    # -------------------------------
    # Plot Equity Curve
    # -------------------------------
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=data["equity_curve"], mode="lines"))
    fig.update_layout(title="Equity Curve", height=350)
    st.plotly_chart(fig, use_container_width=True)
