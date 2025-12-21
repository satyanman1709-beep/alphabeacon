import numpy as np
import pandas as pd
import yfinance as yf


# ----------------------------------------------------------
# INTERNAL HELPERS
# ----------------------------------------------------------
def _to_series(x: pd.Series | pd.DataFrame):
    """
    yfinance sometimes returns a DataFrame for Close/High/Low/Volume (e.g., multi-index columns).
    This normalizes it into a 1D Series.
    """
    if isinstance(x, pd.DataFrame):
        # If multiple columns exist, pick the first column
        return x.iloc[:, 0]
    return x


def _safe_float(x, default=np.nan) -> float:
    """
    Convert scalar/Series to float safely.
    """
    try:
        if isinstance(x, pd.Series):
            # reduce to a scalar if it's a Series
            x = x.dropna()
            if len(x) == 0:
                return float(default)
            x = x.iloc[-1]
        return float(x)
    except Exception:
        return float(default)


def _clip_int(value, low=0, high=100, default=50) -> int:
    """
    Clip and cast to int safely.
    """
    v = _safe_float(value, default=np.nan)
    if np.isnan(v) or np.isinf(v):
        return int(default)
    return int(np.clip(v, low, high))


# ----------------------------------------------------------
# HELPER: ATR Calculation
# ----------------------------------------------------------
def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR) using High/Low/Close.

    Returns a Series aligned with df index.
    """
    high = _to_series(df.get("High"))
    low = _to_series(df.get("Low"))
    close = _to_series(df.get("Close"))

    if high is None or low is None or close is None:
        return pd.Series(index=df.index, dtype=float)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


# ----------------------------------------------------------
# MOMENTUM SCORE (0-100)
# % above 50-day moving average
# ----------------------------------------------------------
def momentum_score(df: pd.DataFrame) -> int:
    close = _to_series(df.get("Close"))
    if close is None or len(close) < 60:
        return 50

    ma50 = close.rolling(50).mean()
    denom = ma50.replace(0, np.nan)

    pct = (close - ma50) / denom * 100.0
    last_pct = pct.iloc[-1]

    # scaled: pct * 2, clipped into 0..100
    return _clip_int(last_pct * 2, 0, 100, default=50)


# ----------------------------------------------------------
# TREND STRENGTH SCORE (0-100)
# Based on slope of 20-day regression
# ----------------------------------------------------------
def trend_strength(df: pd.DataFrame) -> int:
    close = _to_series(df.get("Close"))
    if close is None or len(close) < 25:
        return 50

    window = close.tail(20).dropna()
    if len(window) < 10:
        return 50

    x = np.arange(len(window))
    y = window.values

    try:
        slope = np.polyfit(x, y, 1)[0]
    except Exception:
        return 50

    # normalize relative to last price
    last_price = y[-1]
    if last_price == 0 or np.isnan(last_price):
        return 50

    score = (slope / last_price) * 50000
    return _clip_int(score, 0, 100, default=50)


# ----------------------------------------------------------
# VOLUME DIVERGENCE SCORE (0-100)
# Volume Z-score
# ----------------------------------------------------------
def volume_divergence(df: pd.DataFrame) -> int:
    vol = _to_series(df.get("Volume"))
    if vol is None or len(vol) < 25:
        return 50

    ma20 = vol.rolling(20).mean()
    std20 = vol.rolling(20).std()

    last_vol = vol.iloc[-1]
    last_ma = ma20.iloc[-1]
    last_std = std20.iloc[-1]

    if pd.isna(last_std) or last_std == 0:
        return 50

    z = (last_vol - last_ma) / last_std
    score = (z + 2) * 25  # roughly normalize to 0..100
    return _clip_int(score, 0, 100, default=50)


# ----------------------------------------------------------
# VOLATILITY ADJUSTED SCORE (0-100)
# Lower ATR% = Higher score
# ----------------------------------------------------------
def volatility_adjusted(df: pd.DataFrame) -> int:
    close = _to_series(df.get("Close"))
    if close is None or len(close) < 20:
        return 50

    atr_series = compute_atr(df)
    atr = atr_series.iloc[-1]
    last_close = close.iloc[-1]

    if pd.isna(atr) or pd.isna(last_close) or last_close == 0:
        return 50

    atr_pct = (atr / last_close) * 100.0
    if atr_pct <= 0 or np.isnan(atr_pct):
        return 50

    score = 100 - min(atr_pct * 10, 100)
    return _clip_int(score, 0, 100, default=50)


# ----------------------------------------------------------
# MASTER FUNCTION TO COMPUTE ALL FACTORS
# ----------------------------------------------------------
def compute_alpha_factors(ticker: str, lookback: int = 200):
    """
    Downloads data for a ticker and computes alpha factors.
    Returns dict or None.
    """
    df = yf.download(ticker, period=f"{lookback}d", progress=False)

    if df is None or len(df) < 60:
        return None

    close = _to_series(df.get("Close"))
    if close is None or len(close) < 60:
        return None

    atr_series = compute_atr(df)
    atr = atr_series.iloc[-1]
    last_close = close.iloc[-1]

    if pd.isna(atr) or pd.isna(last_close) or last_close == 0:
        atr_pct = np.nan
    else:
        atr_pct = (atr / last_close) * 100.0

    return {
        "ticker": ticker,
        "momentum": momentum_score(df),
        "trend_strength": trend_strength(df),
        "volume": volume_divergence(df),
        "vol_adj": volatility_adjusted(df),
        "atr_percent": round(float(atr_pct), 2) if not pd.isna(atr_pct) else None,
    }
