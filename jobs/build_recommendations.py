from __future__ import annotations

"""
Daily recommendation builder (Top 50 total):
- Loads sector universe (S&P 500 mapping)
- Downloads OHLCV for each ticker (yfinance)
- Filters out illiquid / penny stocks
- Scores using your alpha factors
- Computes targets (TP/SL) and derives entry_price, expected_return_pct, horizon_days, confidence
- Computes "repeat in last 30 days" stats and "since last recommendation" performance
- Saves TOP 50 rows into Supabase table: public.daily_recommendations

Required GitHub Actions secrets:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
"""

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
from analysis.universe import sector_to_tickers


# =========================
# CONFIG
# =========================
SECTORS = ["Technology", "Healthcare", "Financials", "Industrials", "Energy"]

LOOKBACK_DAYS = 260          # ~1 trading year
MIN_HISTORY_ROWS = 120

MAX_WORKERS = 10             # keep moderate, yfinance can throttle
PER_SECTOR_TARGET = 18       # gather more per sector, then pick global top 50
TOTAL_DAILY_ROWS = 50        # YOUR requirement

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
    """Convert pandas/numpy/datetime objects into JSON-serializable primitives."""
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
    Returns OHLCV df with required columns, or None.
    """
    try:
        df = yf.download(
            ticker,
            period=f"{LOOKBACK_DAYS}d",
            progress=False,
            auto_adjust=False,
            threads=False,
            timeout=25,
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
    atr_pct = round((atr_val / close_last) * 100.0, 2) if atr_val and close_last else 0.0

    tech_score = int((mom + trn) / 2)
    sent_score = 70  # placeholder until real sentiment is wired
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


def _estimate_horizon_days(atr_percent: float, alpha_score: int) -> int:
    """
    Simple transparent heuristic:
    - Higher volatility (ATR%) -> reaches targets faster, but less stable
    - Higher score -> slightly shorter horizon
    """
    atr_percent = float(atr_percent or 0.0)
    base = 7

    if atr_percent >= 5:
        base = 4
    elif atr_percent >= 3:
        base = 5
    elif atr_percent >= 2:
        base = 6
    else:
        base = 8

    # Better score => slightly shorter expected time to move
    if alpha_score >= 80:
        base -= 1
    elif alpha_score <= 55:
        base += 1

    return int(max(3, min(14, base)))


def _confidence(alpha_score: int, atr_percent: float, rr: float) -> int:
    """
    Confidence is a UI-friendly number (0-100),
    derived from score + slightly penalize extreme ATR,
    slightly reward reasonable risk/reward.
    """
    a = int(alpha_score)
    atr = float(atr_percent or 0.0)
    rr = float(rr or 0.0)

    penalty = 0
    if atr >= 6:
        penalty += 10
    elif atr >= 4:
        penalty += 6
    elif atr >= 3:
        penalty += 3

    bonus = 0
    if rr >= 2.0:
        bonus += 6
    elif rr >= 1.4:
        bonus += 3

    return int(max(0, min(100, a - penalty + bonus)))


def score_ticker(ticker: str) -> Optional[Dict]:
    """
    Downloads history, scores alpha, computes targets.
    Returns dict for candidate list.
    """
    df = _download_history(ticker)
    if df is None:
        return None

    factors = compute_alpha_score_from_df(df)
    if factors is None:
        return None

    targets = compute_price_targets_from_df(df)
    if not targets:
        return None

    entry_price = float(factors["last_price"])
    stop_loss = float(targets["sl"])
    tp1 = float(targets["tp1"])
    rr = float(targets.get("rr") or 0.0)

    expected_return_pct = round(((tp1 - entry_price) / entry_price) * 100.0, 2) if entry_price else None
    horizon_days = _estimate_horizon_days(factors["atr_percent"], int(factors["alpha_score"]))
    conf = _confidence(int(factors["alpha_score"]), float(factors["atr_percent"]), rr)

    return {
        "ticker": ticker,
        "alpha_score": int(factors["alpha_score"]),
        "factors": factors,
        "targets": targets,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "expected_return_pct": expected_return_pct,
        "horizon_days": horizon_days,
        "confidence": conf,
    }


def _rank_items(items: List[Dict], top_n: int) -> List[Dict]:
    """
    Sort by alpha_score desc, then expected_return desc, then atr% asc
    """
    items.sort(
        key=lambda r: (
            -int(r["alpha_score"]),
            -(float(r.get("expected_return_pct") or -9999)),
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
    sb.table("daily_recommendations").delete().eq("as_of_date", as_of).execute()


def upsert_rows(sb, rows: List[Dict]) -> None:
    clean_rows = [json_safe(r) for r in rows]
    batch_size = 200
    for i in range(0, len(clean_rows), batch_size):
        sb.table("daily_recommendations").upsert(clean_rows[i : i + batch_size]).execute()


def enrich_repeat_stats(sb, as_of: str, rows: List[Dict]) -> List[Dict]:
    """
    For the final TOP 50 only:
    - repeat_30d: how many times ticker appeared in last 30 days (excluding today)
    - last_reco_date: most recent recommendation date before today
    - pct_change_since_last_reco: % change from last entry_price to today's entry_price
    """
    if not rows:
        return rows

    tickers = sorted({r["ticker"] for r in rows})
    start = (dt.date.fromisoformat(as_of) - dt.timedelta(days=30)).isoformat()

    # Fetch last 30 days of past recos for these tickers
    resp = (
        sb.table("daily_recommendations")
        .select("ticker, as_of_date, entry_price")
        .in_("ticker", tickers)
        .gte("as_of_date", start)
        .lt("as_of_date", as_of)
        .order("as_of_date", desc=True)
        .execute()
    )
    hist = resp.data or []

    # Build per-ticker history
    by_ticker: Dict[str, List[Dict]] = {}
    for r in hist:
        by_ticker.setdefault(r["ticker"], []).append(r)

    for r in rows:
        t = r["ticker"]
        past = by_ticker.get(t, [])
        r["repeat_30d"] = len(past)

        if past:
            last = past[0]
            r["last_reco_date"] = last.get("as_of_date")

            prev_entry = last.get("entry_price")
            cur_entry = r.get("entry_price")
            if prev_entry is not None and cur_entry is not None and float(prev_entry) != 0:
                r["pct_change_since_last_reco"] = round(((float(cur_entry) / float(prev_entry)) - 1.0) * 100.0, 2)
            else:
                r["pct_change_since_last_reco"] = None
        else:
            r["last_reco_date"] = None
            r["pct_change_since_last_reco"] = None

    return rows


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
                    "entry_price": rec["entry_price"],
                    "stop_loss": rec["stop_loss"],
                    "expected_return_pct": rec["expected_return_pct"],
                    "horizon_days": rec["horizon_days"],
                    "confidence": rec["confidence"],
                }
            )

        print(f"[{sector}] candidates: {len(ranked)}")

    if not sector_candidates:
        raise RuntimeError("No recommendations generated (all filtered out).")

    # 2) Pick TOP TOTAL_DAILY_ROWS globally
    top = _rank_items(sector_candidates, TOTAL_DAILY_ROWS)

    # 3) Assign ranks within sector
    per_sector_rank: Dict[str, int] = {s: 0 for s in SECTORS}
    rows: List[Dict] = []
    for rec in top:
        sec = rec["sector"]
        per_sector_rank[sec] = per_sector_rank.get(sec, 0) + 1

        rows.append(
            {
                "as_of_date": as_of,
                "sector": sec,
                "rank": per_sector_rank[sec],
                "ticker": rec["ticker"],
                "alpha_score": int(rec["alpha_score"]),
                "entry_price": rec["entry_price"],
                "stop_loss": rec["stop_loss"],
                "expected_return_pct": rec["expected_return_pct"],
                "horizon_days": rec["horizon_days"],
                "confidence": rec["confidence"],
                "repeat_30d": None,
                "last_reco_date": None,
                "pct_change_since_last_reco": None,
                "factors": rec["factors"],
                "targets": rec["targets"],
            }
        )

    # 4) Enrich with 30-day repeat + perf stats, then save
    sb = _get_supabase_client()
    rows = enrich_repeat_stats(sb, as_of, rows)

    replace_today_rows(sb, as_of)
    upsert_rows(sb, rows)

    print(f"Done. Saved {len(rows)} rows for {as_of}.")
    for s in SECTORS:
        print(f"  {s}: {per_sector_rank.get(s, 0)} rows")


if __name__ == "__main__":
    main()
