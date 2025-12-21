# analysis/atr_engine.py

import pandas as pd
import numpy as np

class ATREngine:

    def __init__(self, atr_mode="moderate"):
        self.atr_mode = atr_mode
        self.multipliers = {
            "conservative": {"sl": 1.5, "tp": 2.0},
            "moderate": {"sl": 1.2, "tp": 2.5},
            "aggressive": {"sl": 1.0, "tp": 3.0},
        }

    def compute_atr(self, df, period=14):
        df = df.copy()

        df["H-L"] = df["High"] - df["Low"]
        df["H-PC"] = abs(df["High"] - df["Close"].shift(1))
        df["L-PC"] = abs(df["Low"] - df["Close"].shift(1))

        df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
        df["ATR"] = df["TR"].rolling(period).mean()

        df.dropna(inplace=True)
        return df["ATR"].iloc[-1]

    def generate_levels(self, df):
        if df is None or df.empty:
            return None

        atr = self.compute_atr(df)
        last_price = df["Close"].iloc[-1]
        mult = self.multipliers[self.atr_mode]

        stop_loss = round(last_price - atr * mult["sl"], 2)
        target = round(last_price + atr * mult["tp"], 2)

        risk = last_price - stop_loss
        reward = target - last_price
        rr = round(reward / risk, 2) if risk > 0 else None

        atr_percent = round((atr / last_price) * 100, 2)

        return {
            "atr": round(atr, 2),
            "atr_percent": atr_percent,
            "stop_loss": stop_loss,
            "target_price": target,
            "risk_reward": rr,
            "volatility":
                "High" if atr_percent > 3 else
                "Medium" if atr_percent > 1.5 else "Low"
        }
