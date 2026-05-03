"""
Cloud data layer — reads alerts from Supabase using requests (Python 3.14 compatible).
Falls back to local CSV if Supabase is not configured.
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.supabase_client import fetch_alerts, test_connection


def load_alerts(vehicle_id: str = None) -> pd.DataFrame:
    """Load alerts from Supabase, fall back to local CSV."""

    # ── Try Supabase ──────────────────────────────────────────────────────────
    rows = fetch_alerts(vehicle_id=vehicle_id, limit=5000)
    if rows:
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)  # remove timezone
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        if "snapshot_url" in df.columns and "snapshot" not in df.columns:
            df = df.rename(columns={"snapshot_url": "snapshot"})
        if "snapshot" not in df.columns:
            df["snapshot"] = ""
        if "vehicle_id" not in df.columns:
            df["vehicle_id"] = vehicle_id or "UNKNOWN"
        return df

    # ── Fallback: local CSV ───────────────────────────────────────────────────
    LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "alert_log.csv")
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=["timestamp", "alert_type", "vehicle_id", "snapshot"])

    data = []
    with open(LOG_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("timestamp"):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                atype = parts[1].strip()
                if atype not in ("DROWSINESS", "DISTRACTION", "MOBILE_USAGE"):
                    continue
                data.append({
                    "timestamp":  parts[0].strip(),
                    "alert_type": atype,
                    "vehicle_id": parts[2].strip() if len(parts) > 2 else "UNKNOWN",
                    "snapshot":   parts[3].strip() if len(parts) > 3 else "",
                })

    if not data:
        return pd.DataFrame(columns=["timestamp", "alert_type", "vehicle_id", "snapshot"])

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    df = df.dropna(subset=["timestamp"])
    # ensure no timezone info
    if hasattr(df["timestamp"].dtype, "tz") and df["timestamp"].dtype.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    if vehicle_id:
        own = df[df["vehicle_id"] == vehicle_id]
        return own if not own.empty else df

    return df


def is_cloud_connected() -> bool:
    return test_connection()
