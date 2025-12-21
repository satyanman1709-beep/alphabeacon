# analysis/universe.py
from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests


CACHE_PATH = Path(__file__).with_name("_cache_sp500.csv")

# Source 1 (CSV) - usually easiest/most stable
DATAHUB_SP500_CSV = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"

# Source 2 (HTML) - fallback
WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _http_get(url: str, timeout: int = 30) -> str:
    headers = {
        # A more realistic browser UA reduces 403s
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def load_sp500_universe(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns a DataFrame with at least:
      - Symbol
      - Security (if available)
      - GICS Sector (or Sector)
    Uses cache to avoid repeated network calls.
    """
    if CACHE_PATH.exists() and not force_refresh:
        return pd.read_csv(CACHE_PATH)

    # ---- Try Source 1: DataHub CSV ----
    try:
        df = pd.read_csv(DATAHUB_SP500_CSV)
        # DataHub columns: Symbol, Name, Sector
        df = df.rename(columns={"Name": "Security", "Sector": "GICS Sector"})
        df["Symbol"] = df["Symbol"].astype(str).str.strip()
        df["GICS Sector"] = df["GICS Sector"].astype(str).str.strip()
        df.to_csv(CACHE_PATH, index=False)
        return df
    except Exception:
        pass

    # ---- Try Source 2: Wikipedia HTML ----
    try:
        html = _http_get(WIKI_SP500_URL)
        tables = pd.read_html(html)
        df = tables[0].copy()

        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]

        # Wikipedia columns typically include: Symbol, Security, GICS Sector, GICS Sub-Industry
        if "Symbol" not in df.columns:
            raise ValueError("Wikipedia table missing Symbol column")

        # yfinance uses BRK-B not BRK.B
        df["Symbol"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)

        # Make sure sector column exists
        if "GICS Sector" not in df.columns and "Sector" in df.columns:
            df = df.rename(columns={"Sector": "GICS Sector"})

        df.to_csv(CACHE_PATH, index=False)
        return df
    except Exception as e:
        raise RuntimeError(
            f"Failed to load S&P 500 universe from both DataHub and Wikipedia. Last error: {e}"
        )


def sector_to_tickers(force_refresh: bool = False) -> dict[str, list[str]]:
    """
    Maps GICS sector -> list of tickers.
    """
    df = load_sp500_universe(force_refresh=force_refresh)

    # Ensure expected columns
    if "GICS Sector" not in df.columns or "Symbol" not in df.columns:
        raise ValueError("Universe missing required columns: Symbol / GICS Sector")

    mapping: dict[str, list[str]] = {}
    for sector, group in df.groupby("GICS Sector"):
        tickers = group["Symbol"].dropna().astype(str).str.strip().tolist()
        # Remove empty strings
        tickers = [t for t in tickers if t]
        mapping[str(sector).strip()] = tickers

    return mapping
