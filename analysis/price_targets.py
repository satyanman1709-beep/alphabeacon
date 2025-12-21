import yfinance as yf
import numpy as np

from analysis.alpha_factors import compute_atr


def _to_series(x):
    """Normalize yfinance columns to a 1D Series."""
    if x is None:
        return None
    # If DataFrame (multi-index), take first column
    if hasattr(x, "ndim") and x.ndim == 2:
        return x.iloc[:, 0]
    return x


def compute_price_targets(ticker: str):
    df = yf.download(ticker, period="120d", progress=False)

    if df is None or len(df) < 30:
        return None

    close_col = _to_series(df.get("Close"))
    if close_col is None or len(close_col) == 0:
        return None

    try:
        close = float(close_col.iloc[-1])
    except Exception:
        return None

    # ATR
    atr_series = compute_atr(df)
    if atr_series is None or len(atr_series) == 0:
        return None

    atr_val = atr_series.iloc[-1]
    if atr_val is None or np.isnan(atr_val) or atr_val == 0:
        return None

    atr = float(atr_val)

    # ----- BUY RANGE -----
    buy_low = round(close - (0.5 * atr), 2)      # safer entry
    buy_high = round(close + (0.2 * atr), 2)     # chase zone

    # ----- TAKE PROFITS -----
    tp1 = round(close + (1.2 * atr), 2)
    tp2 = round(close + (2.0 * atr), 2)

    # ----- STOP LOSS -----
    sl = round(close - (1.0 * atr), 2)

    # ----- RISK/REWARD -----
    denom = (buy_high - sl)
    if denom == 0:
        rr = 1.0
    else:
        rr = round((tp1 - buy_high) / denom, 2)

    # Extra safety: clamp RR to a sane range for UI
    if np.isnan(rr) or np.isinf(rr):
        rr = 1.0
    rr = float(max(0.1, min(rr, 10.0)))

    return {
        "buy_low": buy_low,
        "buy_high": buy_high,
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "rr": rr,
    }
