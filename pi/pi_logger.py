"""
pi/pi_logger.py
===============
Logger for Raspberry Pi.

Flow:
  1. Save snapshot JPG to SD card (data/snapshots/)
  2. Try to upload snapshot to Supabase Storage
  3. Try to insert alert into Supabase DB directly
  4. If Supabase fails → enqueue in offline SQLite DB
  5. Also append to local CSV as backup
"""

import os
import sys
import csv
import time
import cv2
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class PiLogger:
    SAVE_COOLDOWN = 8   # seconds between snapshots per alert type

    def __init__(self, queue, base_dir: str):
        self._queue       = queue
        self._base_dir    = base_dir
        self._last_saved  = {}   # alert_type -> last save timestamp

        self._snap_dir  = os.path.join(base_dir, "data", "snapshots")
        self._log_file  = os.path.join(base_dir, "data", "alert_log.csv")

        os.makedirs(self._snap_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self._log_file), exist_ok=True)

    def log(self, alert_type: str, frame=None, vehicle_id: str = "UNKNOWN"):
        from utils.supabase_client import insert_alert, upload_snapshot, test_connection

        now           = datetime.now()
        timestamp     = now.strftime("%Y-%m-%d %H:%M:%S")
        snapshot_path = ""
        snapshot_url  = ""

        # ── 1. Save snapshot to SD card (with cooldown) ───────────────────────
        last = self._last_saved.get(alert_type, 0)
        if frame is not None and (time.time() - last) >= self.SAVE_COOLDOWN:
            filename      = f"{alert_type}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            snapshot_path = os.path.join(self._snap_dir, filename)
            cv2.imwrite(snapshot_path, frame)
            self._last_saved[alert_type] = time.time()

            # ── 2. Upload snapshot to Supabase Storage ────────────────────────
            try:
                snapshot_url = upload_snapshot(vehicle_id, filename, snapshot_path)
            except Exception:
                snapshot_url = ""

        # ── 3. Try direct Supabase insert ─────────────────────────────────────
        inserted = False
        try:
            inserted = insert_alert(timestamp, alert_type, vehicle_id, snapshot_url)
        except Exception:
            inserted = False

        # ── 4. If offline → add to SQLite queue ───────────────────────────────
        if not inserted:
            self._queue.enqueue(timestamp, alert_type, vehicle_id, snapshot_url)

        # ── 5. Always write local CSV backup ──────────────────────────────────
        file_exists = os.path.isfile(self._log_file)
        try:
            with open(self._log_file, mode="a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "alert_type", "vehicle_id", "snapshot"])
                writer.writerow([timestamp, alert_type, vehicle_id, snapshot_path])
        except Exception as e:
            print(f"[LOG] CSV write error: {e}")
