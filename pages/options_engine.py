from datetime import datetime, timedelta


def choose_options_strategy(tech_score, sent_score, atr_percent):
    """
    Returns a recommended strategy based on market conditions.
    """

    # Strong Uptrend + Low Volatility → Debit Call Spread
    if tech_score >= 70 and atr_percent < 2:
        return "Debit Call Spread"

    # Uptrend but volatile → Vertical Call Spread
    if tech_score >= 65 and atr_percent >= 2:
        return "Bull Call Spread"

    # Moderate trend → Long Call
    if tech_score >= 55:
        return "Long Call Option"

    # Sideways + moderate volatility → Iron Condor
    if 40 <= tech_score < 55 and atr_percent >= 2:
        return "Iron Condor"

    # Weak trend → Cash-Secured Put (neutral-bullish)
    if 30 <= tech_score < 40:
        return "Cash-Secured Put"

    # Strong Downtrend → Bear Put Spread
    return "Bear Put Spread"


def generate_options_contracts(ticker, price, atr, strategy):
    """
    Suggests strikes and expiry based on ATR and strategy.
    """

    # Expiry date 30 days out
    expiry = (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    # ----- Strategy-specific contract logic -----

    if strategy == "Debit Call Spread":
        return {
            "strategy": strategy,
            "buy": f"Buy {ticker} {round(price + atr, 2)}C ({expiry})",
            "sell": f"Sell {ticker} {round(price + 2 * atr, 2)}C ({expiry})",
            "note": "Low volatility, strong trend: reward-to-risk efficient.",
        }

    if strategy == "Bull Call Spread":
        return {
            "strategy": strategy,
            "buy": f"Buy {ticker} {round(price + 1.2 * atr, 2)}C ({expiry})",
            "sell": f"Sell {ticker} {round(price + 2.2 * atr, 2)}C ({expiry})",
            "note": "Moderate volatility: defined upside risk.",
        }

    if strategy == "Long Call Option":
        return {
            "strategy": strategy,
            "buy": f"Buy {ticker} {round(price + atr, 2)}C ({expiry})",
            "note": "Directional bullish setup with positive momentum.",
        }

    if strategy == "Cash-Secured Put":
        return {
            "strategy": strategy,
            "sell": f"Sell {ticker} {round(price - atr, 2)}P ({expiry})",
            "note": "Collect premium while potentially entering stock lower.",
        }

    if strategy == "Iron Condor":
        return {
            "strategy": strategy,
            "note": "Sell OTM call + put spread. Market expected to remain range-bound.",
        }

    if strategy == "Bear Put Spread":
        return {
            "strategy": strategy,
            "buy": f"Buy {ticker} {round(price - atr, 2)}P ({expiry})",
            "sell": f"Sell {ticker} {round(price - 2 * atr, 2)}P ({expiry})",
            "note": "Bearish setup with controlled downside.",
        }

    return None
