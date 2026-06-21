"""
pi/offline_queue.py
===================
SQLite-backed offline queue.

When internet is available  → insert alert directly to Supabase.
When internet is unavailable → save to local SQLite DB on SD card.
Background sync thread       → retries all pending rows every 30 seconds.

This guarantees ZERO data loss even on poor/no connectivity.
"""

import os
import sys
import sqlite3
import time
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class OfflineQueue:
    SYNC_INTERVAL = 30   # seconds between sync attempts

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._lock = threading.Lock()

    # ── DB setup ──────────────────────────────────────────────────────────────
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT    NOT NULL,
                    alert_type   TEXT    NOT NULL,
                    vehicle_id   TEXT    NOT NULL,
                    snapshot_url TEXT    DEFAULT '',
                    synced       INTEGER DEFAULT 0,
                    created_at   REAL    DEFAULT (strftime('%s','now'))
                )
            """)
            conn.commit()

    # ── Add to queue ──────────────────────────────────────────────────────────
    def enqueue(self, timestamp: str, alert_type: str,
                vehicle_id: str, snapshot_url: str = ""):
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO queue (timestamp, alert_type, vehicle_id, snapshot_url) "
                    "VALUES (?, ?, ?, ?)",
                    (timestamp, alert_type, vehicle_id, snapshot_url)
                )
                conn.commit()

    # ── Count pending ─────────────────────────────────────────────────────────
    def pending_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("SELECT COUNT(*) FROM queue WHERE synced=0")
                return cur.fetchone()[0]
        except Exception:
            return 0

    # ── Sync one batch to Supabase ────────────────────────────────────────────
    def _sync_batch(self) -> int:
        """Try to push all pending rows to Supabase. Returns number synced."""
        try:
            from utils.supabase_client import insert_alert, test_connection
        except Exception:
            return 0

        if not test_connection():
            return 0

        synced = 0
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT id, timestamp, alert_type, vehicle_id, snapshot_url "
                    "FROM queue WHERE synced=0 ORDER BY id LIMIT 50"
                ).fetchall()

                for row_id, ts, atype, vid, snap_url in rows:
                    ok = insert_alert(ts, atype, vid, snap_url)
                    if ok:
                        conn.execute("UPDATE queue SET synced=1 WHERE id=?", (row_id,))
                        synced += 1
                    else:
                        break   # stop on first failure, retry next cycle

                conn.commit()

        return synced

    # ── Background sync loop ──────────────────────────────────────────────────
    def sync_loop(self):
        """Runs forever in a background thread. Call once at startup."""
        print("[SYNC] Background sync thread running")
        while True:
            try:
                pending = self.pending_count()
                if pending > 0:
                    n = self._sync_batch()
                    if n > 0:
                        print(f"[SYNC] Synced {n} alert(s) to Supabase "
                              f"({self.pending_count()} remaining)")
                    else:
                        print(f"[SYNC] No internet — {pending} alert(s) queued on SD card")
            except Exception as e:
                print(f"[SYNC] Error: {e}")

            time.sleep(self.SYNC_INTERVAL)
