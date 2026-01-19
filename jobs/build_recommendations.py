from __future__ import annotations

# Daily recommendation builder:
# - Scans sector universe
# - Filters tickers using swing-entry rules
# - Scores remaining tickers
# - Saves TOP rows into Supabase table: daily_recommendations
#
# Requires Supabase table column:
#   entry jsonb
#
# Env vars (GitHub Actions secrets):
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY

import os
import math
import datetime as dt
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from supabase import create_client

from analysis.alpha_factors import (
    momentum_score,
    trend_strength,
    volume_divergence,
    volatility_adjusted,
    compute_atr,
)
from analysis.price_targets import compute_price_targets_from_df
from analysis.swing_entry import passes_swing_entry
from analysis.universe import sector_to_tickers

# =========================
# CONFIG
# =========================
SECTORS = ["Technology", "Healthcare", "Financials", "Industrials", "Energy"]

LOOKBACK_DAYS = 260          # ~1 trading year
MIN_HISTORY_ROWS = 120

MAX_WORKERS = 8              # moderate to avoid throttling
PER_SECTOR_TARGET = 15       # build more, then pick globally
TOTAL_DAILY_ROWS = 50        # HARD CAP total rows stored per day (your requirement)

# Liquidity / tradability filters
MIN_PRICE = 5.0
MIN_AVG_VOL_20D = 500_000

YFINANCE_LOGGERS = ("yfinance", "yfinance.base", "urllib3")


def _configure_logging() -> None:
    for name in YFINANCE_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message=".*No data found for this date range.*")


# =========================
# JSON SAFETY
# =========================
def json_safe(x):
    """Convert pandas / numpy / datetime objects into JSON-serializable primitives."""
    if isinstance(x, pd.Series):
        return x.to_dict()
    if isinstance(x, pd.DataFrame):
        return x.to_dict(orient="records")
    if isinstance(x, np.ndarray):
        return [json_safe(v) for v in x.tolist()]

    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        v = float(x)
        return None if math.isnan(v) else v
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.generic):
        return json_safe(x.item())

    if isinstance(x, (pd.Timestamp, dt.datetime, dt.date)):
        return x.isoformat()

    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    if isinstance(x, dict):
        return {k: json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_safe(v) for v in x]

    return x


def _safe_last_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (pd.Series, pd.DataFrame, np.ndarray, list)):
            x = np.array(x).reshape(-1)[-1]
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


# =========================
# DOWNLOAD / SCORING
# =========================
def _download_history(ticker: str) -> Optional[pd.DataFrame]:
    """
    Robust yfinance download wrapper.
    Returns a OHLCV df with required columns, or None.
    """
    try:
        df = yf.download(
            ticker,
            period=f"{LOOKBACK_DAYS}d",
            progress=False,
            auto_adjust=False,
            threads=False,
            timeout=20,
        )
        if df is None or df.empty:
            return None

        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                return None

        df = df.dropna()
        if len(df) < MIN_HISTORY_ROWS:
            return None

        return df
    except Exception:
        return None


def compute_alpha_score_from_df(df: pd.DataFrame) -> Optional[Dict]:
    """
    Computes alpha factors + composite score.
    Returns dict, or None if fails filters.
    """
    if df is None or len(df) < MIN_HISTORY_ROWS:
        return None

    close_last = _safe_last_float(df["Close"].iloc[-1])
    if close_last is None or close_last <= 0:
        return None

    # liquidity filter
    vol20 = _safe_last_float(df["Volume"].tail(20).mean())
    if close_last < MIN_PRICE:
        return None
    if vol20 is None or vol20 < MIN_AVG_VOL_20D:
        return None

    try:
        mom = int(momentum_score(df))
        trn = int(trend_strength(df))
        vol = int(volume_divergence(df))
        vadj = int(volatility_adjusted(df))
    except Exception:
        return None

    atr_val = _safe_last_float(compute_atr(df).iloc[-1])
    if atr_val is None or atr_val <= 0:
        atr_pct = 0.0
    else:
        atr_pct = round((atr_val / close_last) * 100.0, 2)

    tech_score = int((mom + trn) / 2)
    sent_score = 70  # placeholder until sentiment wired
    alpha_score = int((tech_score + sent_score) / 2)

    return {
        "momentum": mom,
        "trend_strength": trn,
        "volume": vol,
        "vol_adj": vadj,
        "atr_percent": atr_pct,
        "tech_score": tech_score,
        "sent_score": sent_score,
        "alpha_score": alpha_score,
        "last_price": close_last,
        "avg_vol_20d": vol20,
    }


def score_ticker(ticker: str) -> Optional[Dict]:
    """
    Downloads history, applies swing-entry filter, scores alpha, computes targets.
    """
    df = _download_history(ticker)
    if df is None:
        return None

    passes_entry, entry = passes_swing_entry(df)
    if not passes_entry:
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
        "entry": entry,
    }


def _rank_items(items: List[Dict], top_n: int) -> List[Dict]:
    """
    Sort by alpha_score desc, then atr% asc (prefer lower vol tie-break).
    """
    items.sort(
        key=lambda r: (
            -int(r["alpha_score"]),
            float(r["factors"].get("atr_percent") or 9999),
        )
    )
    return items[:top_n]


def rank_sector(sector: str, tickers: List[str], top_n: int) -> List[Dict]:
    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(score_ticker, t): t for t in tickers}
        for fut in as_completed(futures):
            try:
                item = fut.result()
            except Exception:
                item = None
            if item:
                results.append(item)

    return _rank_items(results, top_n)


# =========================
# SUPABASE
# =========================
def _get_supabase_client():
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(supabase_url, service_key)


def replace_today_rows(sb, as_of: str) -> None:
    """
    Delete today's rows so reruns don't create duplicates / rank conflicts.
    """
    sb.table("daily_recommendations").delete().eq("as_of_date", as_of).execute()


def upsert_rows(sb, rows: List[Dict]) -> None:
    clean_rows = [json_safe(r) for r in rows]
    batch_size = 200
    for i in range(0, len(clean_rows), batch_size):
        sb.table("daily_recommendations").upsert(clean_rows[i : i + batch_size]).execute()


# =========================
# MAIN
# =========================
def main() -> None:
    _configure_logging()
    as_of = dt.date.today().isoformat()

    mapping = sector_to_tickers()

    # 1) Generate candidates per sector
    sector_candidates: List[Dict] = []

    for sector in SECTORS:
        tickers = mapping.get(sector, [])
        if not tickers:
            print(f"[{sector}] no tickers available")
            continue

        ranked = rank_sector(sector, tickers, top_n=PER_SECTOR_TARGET)

        for rec in ranked:
            sector_candidates.append(
                {
                    "sector": sector,
                    "ticker": rec["ticker"],
                    "alpha_score": rec["alpha_score"],
                    "factors": rec["factors"],
                    "targets": rec["targets"],
                    "entry": rec["entry"],
                }
            )

        print(f"[{sector}] candidates: {len(ranked)}")

    if not sector_candidates:
        raise RuntimeError("No recommendations generated (all filtered out).")

    # 2) Pick TOP TOTAL_DAILY_ROWS globally
    sector_candidates = _rank_items(sector_candidates, TOTAL_DAILY_ROWS)

    # 3) Assign global ranks within each sector for UI convenience
    #    (rank column in DB is still required; we’ll rank within sector)
    per_sector_rank: Dict[str, int] = {s: 0 for s in SECTORS}
    rows: List[Dict] = []

    for rec in sector_candidates:
        sec = rec["sector"]
        per_sector_rank[sec] = per_sector_rank.get(sec, 0) + 1
        rows.append(
            {
                "as_of_date": as_of,
                "sector": sec,
                "rank": per_sector_rank[sec],
                "ticker": rec["ticker"],
                "alpha_score": int(rec["alpha_score"]),
                "factors": rec["factors"],
                "targets": rec["targets"],
                "entry": rec["entry"],
            }
        )

    # 4) Save to Supabase (replace today's run)
    sb = _get_supabase_client()
    replace_today_rows(sb, as_of)
    upsert_rows(sb, rows)

    print(f"Done. Saved {len(rows)} rows for {as_of}.")
    # quick summary
    for s in SECTORS:
        print(f"  {s}: {per_sector_rank.get(s,0)} rows")


if __name__ == "__main__":
    main()

