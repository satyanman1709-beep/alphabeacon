import streamlit as st
import yfinance as yf

from utils.supabase_client import get_supabase_client

from ui.charts import tradingview_chart
from ui.analytics_cards import volatility_meter, confidence_gauge, target_cards
from ui.radar import radar_alpha_chart
from ui.trend_meters import technical_trend_meter, sentiment_trend_meter
from ui.options_card import options_card

from pages.commentary_engine import generate_commentary
from pages.options_engine import choose_options_strategy, generate_options_contracts
from utils.state import add_to_watchlist


def _fetch_latest_sector_recos(sector: str, limit: int = 3):
    sb = get_supabase_client()

    # 1) get latest date for this sector
    resp = (
        sb.table("daily_recommendations")
        .select("as_of_date")
        .eq("sector", sector)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        return None, []

    latest_date = resp.data[0]["as_of_date"]

    # 2) get top N rows for that sector/date
    resp2 = (
        sb.table("daily_recommendations")
        .select("rank,ticker,alpha_score,factors,targets")
        .eq("sector", sector)
        .eq("as_of_date", latest_date)
        .order("rank", desc=False)
        .limit(limit)
        .execute()
    )

    return latest_date, (resp2.data or [])


def sector_page(sector):
    st.markdown(
        f"""
        <h1 style='color:#003366; font-size:40px; font-weight:900;'>
            {sector} Sector — Top Picks
        </h1>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    as_of_date, recos = _fetch_latest_sector_recos(sector, limit=3)

    if not recos:
        st.warning(
            "No precomputed recommendations found yet. "
            "Run the daily job (GitHub Actions) once, or check Supabase table."
        )
        return

    st.caption(f"Updated: **{as_of_date}** (precomputed)")

    for rec in recos:
        t = rec["ticker"]
        alpha_score = rec["alpha_score"]
        factors = rec.get("factors") or {}
        targets = rec.get("targets") or {}

        # Pull last price for options card
        df5 = yf.download(t, period="5d", progress=False)
        last_price = df5["Close"].iloc[-1] if df5 is not None and len(df5) else None

        tech_score = int(factors.get("tech_score", 50))
        sent_score = int(factors.get("sent_score", 70))

        st.subheader(f"📌 {t} — Alpha Score {alpha_score}")

        if st.button(f"Add {t} to Watchlist", key=f"add_{sector}_{t}"):
            add_to_watchlist(t)
            st.success(f"{t} added to Watchlist!")

        col1, col2 = st.columns([2, 1])

        with col1:
            tradingview_chart(t)

        with col2:
            volatility_meter(float(factors.get("atr_percent", 0.0)))
            st.write("")
            confidence = int((tech_score + sent_score) / 2)
            # If your confidence_gauge already accepts a key, pass it.
            # Otherwise your previous fix in ui/analytics_cards.py should be fine.
            try:
                confidence_gauge(confidence, key=f"conf_{sector}_{t}")
            except TypeError:
                confidence_gauge(confidence)

        st.write("")
        st.markdown("### Alpha Score Breakdown")

        radar_alpha_chart(
            int(factors.get("momentum", 0)),
            int(factors.get("trend_strength", 0)),
            int(factors.get("volume", 0)),
            int(factors.get("sent_score", 70)),
            int(factors.get("vol_adj", 0)),
        )

        st.write("")
        st.markdown("### Trend Signals")

        colA, colB = st.columns(2)
        with colA:
            technical_trend_meter(tech_score)
        with colB:
            sentiment_trend_meter(sent_score)

        st.write("")
        st.markdown("### Targets & Risk")

        target_cards(
            buy_low=targets.get("buy_low"),
            buy_high=targets.get("buy_high"),
            tp1=targets.get("tp1"),
            tp2=targets.get("tp2"),
            sl=targets.get("sl"),
            rr=targets.get("rr"),
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

        st.markdown(
            f"""
            <div style="
                background:#0f1720;
                padding:20px;
                border-radius:12px;
                border:1px solid rgba(255,255,255,0.08);
                line-height:1.6;
                font-size:16px;
            ">
                {commentary}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        st.markdown("### Options Strategy Suggestion")

        strategy_name = choose_options_strategy(
            tech_score=tech_score,
            sent_score=sent_score,
            atr_percent=float(factors.get("atr_percent", 0.0)),
        )

        if last_price is not None:
            options_data = generate_options_contracts(
                ticker=t,
                price=float(last_price),
                atr=float(factors.get("atr_percent", 0.0)),
                strategy=strategy_name,
            )
            options_card(options_data)
        else:
            st.info("Could not fetch latest price for options suggestions right now.")

        st.markdown("---")
