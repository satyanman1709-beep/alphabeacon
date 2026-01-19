from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

MIN_HISTORY_ROWS = 120


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def swing_entry_signals(df: pd.DataFrame) -> Dict:
    close = df["Close"]
    sma20 = compute_sma(close, 20)
    sma50 = compute_sma(close, 50)
    rsi14 = compute_rsi(close, 14)

    last_close = close.iloc[-1]
    last_sma20 = sma20.iloc[-1]
    last_sma50 = sma50.iloc[-1]
    last_rsi14 = rsi14.iloc[-1]

    five_day_high = close.tail(5).max()
    distance_to_sma20 = (last_close / last_sma20 - 1.0) * 100.0
    pullback_pct = ((five_day_high - last_close) / five_day_high) * 100.0

    return {
        "close": float(last_close),
        "sma20": float(last_sma20),
        "sma50": float(last_sma50),
        "rsi14": float(last_rsi14),
        "distance_to_sma20": float(distance_to_sma20),
        "pullback_pct": float(pullback_pct),
        "five_day_high": float(five_day_high),
    }


def passes_swing_entry(df: pd.DataFrame) -> Tuple[bool, Dict]:
    if df is None or len(df) < MIN_HISTORY_ROWS:
        return False, {
            "has_min_history": False,
        }

    signals = swing_entry_signals(df)

    trend_ok = signals["close"] > signals["sma50"]
    rsi_ok = 40.0 <= signals["rsi14"] <= 65.0
    distance_ok = -2.0 <= signals["distance_to_sma20"] <= 6.0
    pullback_ok = 1.0 <= signals["pullback_pct"] <= 8.0

    details = {
        **signals,
        "has_min_history": True,
        "trend_ok": trend_ok,
        "rsi_ok": rsi_ok,
        "distance_ok": distance_ok,
        "pullback_ok": pullback_ok,
    }

    return all([trend_ok, rsi_ok, distance_ok, pullback_ok]), details
