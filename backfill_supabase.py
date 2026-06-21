"""
One-time script to backfill all local CSV data into Supabase.
Run this AFTER restoring your Supabase project:
    python backfill_supabase.py
"""
import os, sys, csv, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from utils.supabase_client import insert_alert, test_connection

LOG_FILE = os.path.join("data", "alert_log.csv")

if not test_connection():
    print("❌ Cannot reach Supabase. Restore your project first.")
    sys.exit(1)

print("✅ Supabase connected. Starting backfill...")

inserted = 0
skipped  = 0

with open(LOG_FILE, encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()
        if not line or line.lower().startswith("timestamp"):
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        atype = parts[1].strip()
        if atype not in ("DROWSINESS", "DISTRACTION", "MOBILE_USAGE"):
            skipped += 1
            continue
        timestamp  = parts[0].strip()
        vehicle_id = parts[2].strip() if len(parts) > 2 else "UNKNOWN"
        ok = insert_alert(timestamp, atype, vehicle_id, snapshot_url="")
        if ok:
            inserted += 1
        else:
            skipped += 1
        time.sleep(0.05)  # avoid rate limiting

print(f"Done. Inserted: {inserted} | Skipped/failed: {skipped}")
