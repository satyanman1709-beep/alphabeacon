from __future__ import annotations

import os
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from supabase import create_client

# Your existing modules
from analysis.alpha_factors import momentum_score, trend_strength, volume_divergence, volatility_adjusted, compute_atr
from analysis.price_targets import compute_price_targets_from_df
from analysis.universe import sector_to_tickers


SECTORS = ["Technology", "Healthcare", "Financials", "Industrials", "Energy"]
LOOKBACK_DAYS = 260  # ~1 trading year
MAX_TICKERS_PER_SECTOR_SCAN = None  # None = scan ALL tickers in that sector
TOP_N_PER_SECTOR = 10
MAX_WORKERS = 8  # keep moderate to avoid throttling
MIN_HISTORY_ROWS = 120

# Basic tradability filters
MIN_PRICE = 5.0
MIN_AVG_VOL_20D = 500_000


def _safe_last_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (pd.Series, pd.DataFrame, np.ndarray, list)):
            # take last value if series-like
            x = np.array(x).reshape(-1)[-1]
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def compute_alpha_score_from_df(df: pd.DataFrame) -> Optional[Dict]:
    """
    Returns dict with factors + alpha_score, or None if insufficient data.
    """
    if df is None or len(df) < MIN_HISTORY_ROWS:
        return None

    close_last = _safe_last_float(df["Close"].iloc[-1])
    if close_last is None:
        return None

    # Liquidity filter using 20d avg volume
    vol20 = df["Volume"].tail(20).mean()
    vol20 = _safe_last_float(vol20)
    if close_last < MIN_PRICE:
        return None
    if vol20 is None or vol20 < MIN_AVG_VOL_20D:
        return None

    # Factors (0-100)
    mom = int(momentum_score(df))
    trn = int(trend_strength(df))
    vol = int(volume_divergence(df))
    vadj = int(volatility_adjusted(df))

    # ATR%
    atr = compute_atr(df).iloc[-1]
    atr = _safe_last_float(atr)
    atr_pct = None
    if atr is not None and close_last is not None and close_last != 0:
        atr_pct = round((atr / close_last) * 100.0, 2)

    # Simple composite score (you can evolve this)
    tech_score = int((mom + trn) / 2)
    sent_score = 70  # placeholder until you wire real sentiment
    alpha_score = int((tech_score + sent_score) / 2)

    return {
        "momentum": mom,
        "trend_strength": trn,
        "volume": vol,
        "vol_adj": vadj,
        "atr_percent": atr_pct if atr_pct is not None else 0.0,
        "tech_score": tech_score,
        "sent_score": sent_score,
        "alpha_score": alpha_score,
        "last_price": close_last,
        "avg_vol_20d": vol20,
    }


def _download_history(ticker: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.download(ticker, period=f"{LOOKBACK_DAYS}d", progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None
        # Standardize columns capitalization, just in case
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                return None
        return df.dropna()
    except Exception:
        return None


def score_ticker(ticker: str) -> Optional[Dict]:
    df = _download_history(ticker)
    if df is None:
        return None

    factors = compute_alpha_score_from_df(df)
    if factors is None:
        return None

    targets = compute_price_targets_from_df(df)
    if targets is None:
        return None

    return {
        "ticker": ticker,
        "alpha_score": int(factors["alpha_score"]),
        "factors": factors,
        "targets": targets,
    }


def rank_sector(sector: str, tickers: List[str]) -> List[Dict]:
    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(score_ticker, t): t for t in tickers}
        for fut in as_completed(futures):
            item = fut.result()
            if item is not None:
                results.append(item)

    # Sort: alpha_score desc, then atr_percent asc (prefer lower vol) as tiebreak
    results.sort(
        key=lambda r: (
            -int(r["alpha_score"]),
            float(r["factors"].get("atr_percent") or 9999),
        )
    )
    return results[:TOP_N_PER_SECTOR]


def upsert_recommendations(rows: List[Dict]) -> None:
    supabase_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # server-side only
    sb = create_client(supabase_url, service_key)

    # Insert in batches (safe for moderate size)
    batch_size = 200
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        # primary key is (as_of_date, sector, rank) -> upsert ok
        sb.table("daily_recommendations").upsert(batch).execute()


def main() -> None:
    as_of = dt.date.today().isoformat()

    mapping = sector_to_tickers()  # expects dict: sector -> tickers list

    all_rows: List[Dict] = []

    for sector in SECTORS:
        sector_list = mapping.get(sector, [])
        if not sector_list:
            continue

        tickers = sector_list[:MAX_TICKERS_PER_SECTOR_SCAN] if MAX_TICKERS_PER_SECTOR_SCAN else sector_list

        ranked = rank_sector(sector, tickers)

        for idx, rec in enumerate(ranked, start=1):
            all_rows.append(
                {
                    "as_of_date": as_of,
                    "sector": sector,
                    "rank": idx,
                    "ticker": rec["ticker"],
                    "alpha_score": int(rec["alpha_score"]),
                    "factors": rec["factors"],
                    "targets": rec["targets"],
                }
            )

        print(f"[{sector}] stored {len(ranked)} recommendations")

    if not all_rows:
        raise RuntimeError("No recommendations generated. Universe may be empty or data downloads failed.")

    upsert_recommendations(all_rows)
    print(f"Done. Upserted {len(all_rows)} rows for {as_of}.")


if __name__ == "__main__":
    main()
