import os
import csv
import cv2
import time
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE     = os.path.join(_BASE, "data", "alert_log.csv")
SNAPSHOT_DIR = os.path.join(_BASE, "data", "snapshots")

# ── Cooldown ──────────────────────────────────────────────────────────────────
_last_saved   = {}
SAVE_COOLDOWN = 3  # seconds between snapshots per alert type


def log_alert(alert_type, frame=None, vehicle_id="UNKNOWN"):
    from utils.supabase_client import insert_alert, upload_snapshot

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    now           = datetime.now()
    timestamp     = now.strftime("%Y-%m-%d %H:%M:%S")
    snapshot_path = ""
    snapshot_url  = ""

    # ── Save snapshot locally with cooldown ───────────────────────────────────
    last = _last_saved.get(alert_type, 0)
    if frame is not None and (time.time() - last) >= SAVE_COOLDOWN:
        filename      = f"{alert_type}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        snapshot_path = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(snapshot_path, frame)
        _last_saved[alert_type] = time.time()

        # Upload to Supabase Storage
        snapshot_url = upload_snapshot(vehicle_id, filename, snapshot_path)

    # ── Insert into Supabase DB ───────────────────────────────────────────────
    insert_alert(timestamp, alert_type, vehicle_id, snapshot_url)

    # ── Local CSV backup ──────────────────────────────────────────────────────
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "alert_type", "vehicle_id", "snapshot"])
        writer.writerow([timestamp, alert_type, vehicle_id, snapshot_path])
