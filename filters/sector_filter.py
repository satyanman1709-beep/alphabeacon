# filters/sector_filter.py

import yfinance as yf
import pickle
import os

class SectorFilter:

    CACHE_FILE = "cache/sector_map.pkl"

    def __init__(self, max_per_sector=3):
        self.max_per_sector = max_per_sector

        # Load sector cache if exists
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "rb") as f:
                self.sector_map = pickle.load(f)
        else:
            self.sector_map = {}

    # ---------------------------------------------------------
    # Fetch sector for each ticker
    # ---------------------------------------------------------
    def get_sector(self, ticker):
        if ticker in self.sector_map:
            return self.sector_map[ticker]

        try:
            info = yf.Ticker(ticker).info
            sector = info.get("sector", "Unknown")
        except:
            sector = "Unknown"

        self.sector_map[ticker] = sector

        with open(self.CACHE_FILE, "wb") as f:
            pickle.dump(self.sector_map, f)

        return sector

    # ---------------------------------------------------------
    # Build sector dictionary for all tickers
    # ---------------------------------------------------------
    def build_sector_map(self, tickers):
        mapping = {}
        for t in tickers:
            mapping[t] = self.get_sector(t)
        return mapping

    # ---------------------------------------------------------
    # Apply max-per-sector diversification rule
    # ---------------------------------------------------------
    def filter_by_sector(self, ranked_list):
        sector_count = {}
        filtered = []

        for item in ranked_list:
            sec = item["sector"]
            if sec not in sector_count:
                sector_count[sec] = 0

            if sector_count[sec] < self.max_per_sector:
                filtered.append(item)
                sector_count[sec] += 1

        return filtered

    # ---------------------------------------------------------
    # Get count summary
    # ---------------------------------------------------------
    def sector_summary(self, ranked_list):
        summary = {}
        for item in ranked_list:
            sec = item["sector"]
            summary[sec] = summary.get(sec, 0) + 1
        return summary
