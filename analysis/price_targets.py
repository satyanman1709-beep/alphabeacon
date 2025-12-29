import numpy as np
import yfinance as yf
from analysis.alpha_factors import compute_atr


def compute_price_targets_from_df(df):
    if df is None or len(df) < 20:
        return None

    close = df["Close"].iloc[-1]

    atr_series = compute_atr(df)
    atr = atr_series.iloc[-1]

    buy_low = round(close - (0.5 * atr), 2)
    buy_high = round(close + (0.2 * atr), 2)

    tp1 = round(close + (1.2 * atr), 2)
    tp2 = round(close + (2.0 * atr), 2)

    sl = round(close - (1.0 * atr), 2)

    try:
        rr = round((tp1 - buy_high) / (buy_high - sl), 2)
    except ZeroDivisionError:
        rr = 1.0

    return {
        "buy_low": buy_low,
        "buy_high": buy_high,
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "rr": rr,
    }


def compute_price_targets(ticker):
    df = yf.download(ticker, period="100d", progress=False)
    return compute_price_targets_from_df(df)
