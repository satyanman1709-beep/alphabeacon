# output/commentary_engine.py

import yfinance as yf
from datetime import datetime, timedelta
from analysis.atr_engine import ATREngine

class CommentaryEngine:

    def __init__(self, tech_weight=0.6, sent_weight=0.4, atr_mode="moderate"):
        self.tech_weight = tech_weight
        self.sent_weight = sent_weight
        self.atr_engine = ATREngine(atr_mode)

    def get_price(self, ticker):
        try:
            df = yf.download(ticker, period="5d", interval="1d")
            if df.empty:
                return None
            return float(df["Close"].iloc[-1])
        except:
            return None

    def next_expiry(self):
        today = datetime.today()
        month = today.month
        year = today.year

        for _ in range(2):
            d = datetime(year, month, 1)
            while d.weekday() != 4:
                d += timedelta(days=1)
            expiry = d + timedelta(days=14)
            if expiry > today:
                return expiry.strftime("%b %d, %Y")

            month += 1
            if month == 13:
                month = 1
                year += 1

    def generate_commentary(self, ticker, df, tech_score, sent_score, final_score, sector):
        price = self.get_price(ticker)
        atr = self.atr_engine.generate_levels(df)

        if final_score >= 75:
            action = "Strong Buy"
        elif final_score >= 60:
            action = "Buy"
        elif final_score >= 50:
            action = "Hold"
        else:
            action = "Avoid"

        exp_days = max(10, round((100 - sent_score) / 3))

        opt = None
        if price and price > 50 and tech_score > 70 and sent_score > 65:
            strike = round(price * 1.03, 2)
            expiry = self.next_expiry()
            opt = f"Consider CALL option @ strike ${strike}, expiry {expiry}"

        reasoning = []
        if tech_score > 75: reasoning.append("strong uptrend")
        if sent_score > 65: reasoning.append("positive sentiment")
        reasoning.append(f"sector: {sector}")

        return {
            "ticker": ticker,
            "sector": sector,
            "action": action,
            "price": price,
            "expected_days": exp_days,
            "atr_info": atr,
            "option_comment": opt,
            "reasoning": "; ".join(reasoning),
        }
