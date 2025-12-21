# pages/sector_page.py
from __future__ import annotations

import streamlit as st
import yfinance as yf
import pandas as pd

from ui.charts import tradingview_chart
from ui.analytics_cards import volatility_meter, confidence_gauge, target_cards
from ui.radar import radar_alpha_chart
from ui.trend_meters import technical_trend_meter, sentiment_trend_meter
from ui.options_card import options_card

from analysis.alpha_factors import compute_alpha_factors
from analysis.price_targets import compute_price_targets
from analysis.universe import sector_to_tickers

from pages.commentary_engine import generate_commentary
from pages.options_engine import choose_options_strategy, generate_options_contracts

from utils.state import add_to_watchlist


# Map your navbar labels -> dataset sector names
SECTOR_NAME_MAP = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Financials": "Financials",
    "Industrials": "Industrials",
    "Energy": "Energy",
}


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)  # 6 hours
def _get_sector_universe() -> dict[str, list[str]]:
    return sector_to_tickers(force_refresh=False)


@st.cache_data(ttl=60 * 30, show_spinner=False)  # 30 minutes
def _score_sector(sector_label: str, max_names: int = 35) -> list[dict]:
    """
    Returns ranked list of dicts:
      {ticker, alpha_score, tech_score, sent_score, factors}
    max_names limits how many tickers we score to keep it fast.
    """
    mapping = _get_sector_universe()

    gics_name = SECTOR_NAME_MAP.get(sector_label, sector_label)
    tickers = mapping.get(gics_name, [])

    if not tickers:
        # fallback: if sector label already matches keys
        tickers = mapping.get(sector_label, [])

    # Limit to keep app responsive (you can increase later)
    tickers = tickers[:max_names]

    ranked = []
    for t in tickers:
        factors = compute_alpha_factors(t)
        if not factors:
            continue

        tech_score = int((factors["momentum"] + factors["trend_strength"]) / 2)
        sent_score = 70  # placeholder for now
        alpha_score = int((tech_score + sent_score) / 2)

        ranked.append(
            {
                "ticker": t,
                "alpha_score": alpha_score,
                "tech_score": tech_score,
                "sent_score": sent_score,
                "factors": factors,
            }
        )

    ranked.sort(key=lambda x: x["alpha_score"], reverse=True)
    return ranked


def sector_page(sector_label: str):
    st.markdown(
        f"""
        <h1 style='color:#003366; font-size:40px; font-weight:900; margin-bottom:0;'>
            {sector_label} Sector — Top Picks
        </h1>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    with st.spinner("Scoring sector universe..."):
        ranked = _score_sector(sector_label)

    if not ranked:
        st.error("No ranked results available for this sector right now.")
        st.caption("Tip: try again in a minute, or increase max_names in _score_sector.")
        return

    top3 = ranked[:3]

    st.caption(
        f"Showing top {len(top3)} picks (ranked from the first ~{min(35, len(ranked))} names in sector universe)."
    )

    for item in top3:
        t = item["ticker"]
        factors = item["factors"]
        tech_score = item["tech_score"]
        sent_score = item["sent_score"]
        alpha_score = item["alpha_score"]

        st.subheader(f"📌 {t} — Alpha Score {alpha_score}")

        if st.button(f"Add {t} to Watchlist", key=f"add_{sector_label}_{t}"):
            add_to_watchlist(t)
            st.success(f"{t} added to Watchlist!")

        # Price
        df5 = yf.download(t, period="5d", progress=False)
        if df5 is None or df5.empty:
            st.warning("Price feed unavailable right now.")
            st.markdown("---")
            continue
        last_price = float(df5["Close"].iloc[-1])

        col1, col2 = st.columns([2, 1])

        with col1:
            tradingview_chart(t)

        with col2:
            volatility_meter(factors["atr_percent"], key=f"vol_{sector_label}_{t}")
            st.write("")
            confidence = int((tech_score + sent_score) / 2)
            confidence_gauge(confidence, key=f"conf_{sector_label}_{t}")

        st.write("")
        st.markdown("### Alpha Score Breakdown")

        radar_alpha_chart(
            factors["momentum"],
            factors["trend_strength"],
            factors["volume"],
            sent_score,
            factors["vol_adj"],
        )

        st.write("")
        st.markdown("### Trend Signals")

        colA, colB = st.columns(2)
        with colA:
            technical_trend_meter(tech_score)
        with colB:
            sentiment_trend_meter(sent_score)

        targets = compute_price_targets(t)
        if not targets:
            st.warning("Targets unavailable.")
            st.markdown("---")
            continue

        st.write("")
        st.markdown("### Targets & Risk")

        target_cards(
            buy_low=targets["buy_low"],
            buy_high=targets["buy_high"],
            tp1=targets["tp1"],
            tp2=targets["tp2"],
            sl=targets["sl"],
            rr=targets["rr"],
        )

        st.write("")
        st.markdown("### Analysis Commentary")

        commentary = generate_commentary(
            ticker=t,
            factors=factors,
            tech_score=tech_score,
            sent_score=sent_score,
            targets=targets,
        )
        st.info(commentary)

        st.write("")
        st.markdown("### Options Strategy Suggestion")

        strategy_name = choose_options_strategy(
            tech_score=tech_score,
            sent_score=sent_score,
            atr_percent=factors["atr_percent"],
        )

        options_data = generate_options_contracts(
            ticker=t,
            price=last_price,
            atr=factors["atr_percent"],
            strategy=strategy_name,
        )

        options_card(options_data)

        st.markdown("---")
