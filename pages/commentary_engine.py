def generate_commentary(ticker, factors, tech_score, sent_score, targets):
    """
    Creates a professional, structured commentary paragraph for a ticker.
    """

    momentum = factors["momentum"]
    trend = factors["trend_strength"]
    volume = factors["volume"]
    vol_adj = factors["vol_adj"]
    atr = factors["atr_percent"]

    buy_low = targets["buy_low"]
    buy_high = targets["buy_high"]
    tp1 = targets["tp1"]
    tp2 = targets["tp2"]
    sl = targets["sl"]
    rr = targets["rr"]

    # --- Trend interpretation ---
    if tech_score >= 80:
        trend_text = "a strong and accelerating uptrend"
    elif tech_score >= 65:
        trend_text = "a steadily improving upward trend"
    elif tech_score >= 45:
        trend_text = "a neutral sideways trend with potential upside"
    elif tech_score >= 30:
        trend_text = "a weakening trend that requires caution"
    else:
        trend_text = "a strong downward trend"

    # --- Sentiment interpretation ---
    if sent_score >= 80:
        sent_text = "very bullish sentiment across news and market chatter"
    elif sent_score >= 60:
        sent_text = "moderately positive sentiment"
    elif sent_score >= 40:
        sent_text = "neutral sentiment"
    elif sent_score >= 25:
        sent_text = "slightly negative sentiment"
    else:
        sent_text = "bearish sentiment signals"

    # --- Volatility interpretation ---
    if atr < 1.5:
        vol_text = "low volatility, making entries more stable"
    elif atr < 3:
        vol_text = "moderate volatility, offering good swing-trading potential"
    else:
        vol_text = "high volatility — suitable for experienced traders"

    # --- Risk/Reward interpretation ---
    if rr >= 3:
        rr_text = "excellent risk/reward"
    elif rr >= 2:
        rr_text = "strong risk/reward"
    elif rr >= 1.5:
        rr_text = "reasonable risk/reward balance"
    else:
        rr_text = "weak risk/reward — trade with caution"

    # --- Build commentary paragraph ---
    commentary = f"""
**{ticker}** shows **{trend_text}**, supported by a momentum score of **{momentum}** 
and trend strength of **{trend}**. Volume divergence of **{volume}** suggests 
{'accumulation' if volume > 50 else 'light buying activity'}, while sentiment data indicates 
**{sent_text}**.

The stock is currently displaying **{vol_text}** with an ATR of **{atr}%**, placing it 
within a calculated buy zone of **${buy_low}–${buy_high}**.

Targets sit at **TP1 ${tp1}** and **TP2 ${tp2}**, with a stop-loss reference at 
**${sl}**. This setup provides **{rr_text} (R/R = {rr})**, which aligns with a 
short-term expected move toward the target zones over the next **10–20 trading days**.

Overall, the technical and sentiment combination gives this setup a **balanced 
opportunity profile**, especially if price pulls back closer to the lower buy range.
"""

    return commentary
