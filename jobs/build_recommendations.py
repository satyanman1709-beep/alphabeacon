from __future__ import annotations

import os
import math
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from supabase import create_client

# Your existing modules
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
LOOKBACK_DAYS = 260  # ~1 trading year
MAX_TICKERS_PER_SECTOR_SCAN = None  # None = scan ALL tickers
TOP_N_PER_SECTOR = 10
MAX_WORKERS = 8
MIN_HISTORY_ROWS = 120

MIN_PRICE = 5.0
MIN_AVG_VOL_20D = 500_000

# ATR stop loss config (your choice)
STOP_LOSS_ATR_MULT = 1.5


# =========================
# JSON SAFETY
# =========================
def json_safe(x):
    """Convert pandas / numpy / datetime objects into JSON-serializable primitives."""
    if isinstance(x, pd.Series):
        return x.to_dict()
    if isinstance(x, pd.DataFrame):
        return x.to_dict(orient="records")

    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        v = float(x)
        return None if math.isnan(v) else v
    if isinstance(x, (np.bool_,)):
        return bool(x)

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
# SCORING
# =========================
def compute_alpha_score_from_df(df: pd.DataFrame) -> Optional[Dict]:
    if df is None or len(df) < MIN_HISTORY_ROWS:
        return None

    close_last = _safe_last_float(df["Close"].iloc[-1])
    if close_last is None:
        return None

    vol20 = _safe_last_float(df["Volume"].tail(20).mean())
    if close_last < MIN_PRICE:
        return None
    if vol20 is None or vol20 < MIN_AVG_VOL_20D:
        return None

    mom = int(momentum_score(df))
    trn = int(trend_strength(df))
    vol = int(volume_divergence(df))
    vadj = int(volatility_adjusted(df))

    atr = _safe_last_float(compute_atr(df).iloc[-1])
    atr_pct = round((atr / close_last) * 100.0, 2) if atr and close_last else 0.0

    tech_score = int((mom + trn) / 2)
    sent_score = 70  # placeholder
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
        # Keep ATR dollars too (useful for stop loss / position sizing)
        "atr": atr if atr is not None else None,
    }


def _download_history(ticker: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.download(
            ticker,
            period=f"{LOOKBACK_DAYS}d",
            progress=False,
            auto_adjust=False,
            threads=False,  # avoids some yfinance concurrency weirdness
        )
        if df is None or df.empty:
            return None
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                return None
        df = df.dropna()
        if len(df) < MIN_HISTORY_ROWS:
            return None
        return df
    except Exception:
        return None


def _compute_entry_and_stop(df: pd.DataFrame, factors: Dict) -> Dict[str, Optional[float]]:
    """
    entry_price = last close
    stop_loss = entry_price - (STOP_LOSS_ATR_MULT * ATR)
    """
    entry_price = _safe_last_float(factors.get("last_price"))
    atr = _safe_last_float(factors.get("atr"))

    if entry_price is None:
        entry_price = _safe_last_float(df["Close"].iloc[-1])

    stop_loss = None
    if entry_price is not None and atr is not None and atr > 0:
        stop_loss = entry_price - (STOP_LOSS_ATR_MULT * atr)
        # avoid negative/zero stops
        if stop_loss <= 0:
            stop_loss = None

    return {
        "entry_price": float(entry_price) if entry_price is not None else None,
        "stop_loss": float(stop_loss) if stop_loss is not None else None,
    }


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

    entry_stop = _compute_entry_and_stop(df, factors)

    return {
        "ticker": ticker,
        "alpha_score": int(factors["alpha_score"]),
        "factors": factors,
        "targets": targets,
        "entry_price": entry_stop["entry_price"],
        "stop_loss": entry_stop["stop_loss"],
    }


def rank_sector(sector: str, tickers: List[str]) -> List[Dict]:
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

    results.sort(
        key=lambda r: (
            -int(r["alpha_score"]),
            float(r["factors"].get("atr_percent") or 9999),
        )
    )

    return results[:TOP_N_PER_SECTOR]


# =========================
# SUPABASE
# =========================
def upsert_recommendations(rows: List[Dict]) -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_key:
        print("Supabase credentials missing; skipping upsert.")
        return

    sb = create_client(supabase_url, service_key)

    clean_rows = [json_safe(r) for r in rows]

    batch_size = 200
    for i in range(0, len(clean_rows), batch_size):
        sb.table("daily_recommendations").upsert(
            clean_rows[i : i + batch_size]
        ).execute()


# =========================
# MAIN
# =========================
def main() -> None:
    as_of = dt.date.today().isoformat()
    mapping = sector_to_tickers()

    all_rows: List[Dict] = []

    for sector in SECTORS:
        tickers = mapping.get(sector, [])
        if not tickers:
            continue

        scan_list = (
            tickers[:MAX_TICKERS_PER_SECTOR_SCAN]
            if MAX_TICKERS_PER_SECTOR_SCAN
            else tickers
        )

        ranked = rank_sector(sector, scan_list)

        for idx, rec in enumerate(ranked, start=1):
            all_rows.append(
                {
                    "as_of_date": as_of,
                    "sector": sector,
                    "rank": idx,
                    "ticker": rec["ticker"],
                    "alpha_score": rec["alpha_score"],
                    "entry_price": rec.get("entry_price"),
                    "stop_loss": rec.get("stop_loss"),
                    "factors": rec["factors"],
                    "targets": rec["targets"],
                }
            )

        print(f"[{sector}] stored {len(ranked)} recommendations")

    if not all_rows:
        raise RuntimeError("No recommendations generated.")

    upsert_recommendations(all_rows)
    print(f"Done. Upserted {len(all_rows)} rows for {as_of}.")


if __name__ == "__main__":
    main()
