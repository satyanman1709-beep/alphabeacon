# backtest/backtest_engine.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class BacktestEngine:

    def __init__(self, tech_weight=0.6, sent_weight=0.4, lookback_years=2):
        self.tech_weight = tech_weight
        self.sent_weight = sent_weight
        self.lookback_years = lookback_years

    # ---------------------------------------------------
    # Load 2 years of price data
    # ---------------------------------------------------
    def load_history(self, ticker):
        period_days = int(self.lookback_years * 365)

        try:
            df = yf.download(ticker, period=f"{period_days}d", interval="1d")
            if df.empty:
                return None
            return df["Close"]
        except:
            return None

    # ---------------------------------------------------
    # Daily strategy: Buy Top-K and hold for 10 days
    # ---------------------------------------------------
    def run_backtest(self, ranked_data, K=3, hold_days=10):
        """
        ranked_data: list of dicts (from recommendations.py)
        """

        all_returns = []
        equity_curve = [1]

        for item in ranked_data[:K]:
            ticker = item["ticker"]
            fs = item["final_score"]

            prices = self.load_history(ticker)
            if prices is None or len(prices) < hold_days + 1:
                continue

            entry = prices.iloc[-hold_days - 1]
            exit_ = prices.iloc[-1]

            ret = (exit_ - entry) / entry
            all_returns.append(ret)

            # Equity curve
            equity_curve.append(equity_curve[-1] * (1 + ret))

        if not all_returns:
            return None

        all_returns = np.array(all_returns)

        # Metrics
        win_rate = float((all_returns > 0).mean())
        avg_return = float(all_returns.mean())
        max_drawdown = float(np.min(all_returns))
        sharpe = float(np.mean(all_returns) / np.std(all_returns)) if np.std(all_returns) > 0 else 0

        return {
            "win_rate": round(win_rate * 100, 2),
            "avg_return": round(avg_return * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "sharpe": round(sharpe, 2),
            "equity_curve": equity_curve,
        }
