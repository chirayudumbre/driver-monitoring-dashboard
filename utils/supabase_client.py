"""
Lightweight Supabase client using only 'requests' — no httpx/httpcore needed.
Works on Python 3.14.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}


def insert_alert(timestamp, alert_type, vehicle_id, snapshot_url=""):
    """Insert one alert row into Supabase alerts table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        url  = f"{SUPABASE_URL}/rest/v1/alerts"
        data = {
            "timestamp":    timestamp,
            "alert_type":   alert_type,
            "vehicle_id":   vehicle_id,
            "snapshot_url": snapshot_url,
        }
        r = requests.post(url, headers=HEADERS, json=data, timeout=5)
        return r.status_code in (200, 201)
    except Exception as e:
        print("Supabase insert error:", e)
        return False


def upload_snapshot(vehicle_id, filename, filepath):
    """Upload image to Supabase Storage bucket 'snapshots'."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return ""
    try:
        storage_path = f"{vehicle_id}/{filename}"
        url = f"{SUPABASE_URL}/storage/v1/object/snapshots/{storage_path}"
        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type":  "image/jpeg",
            "x-upsert":      "true",
        }
        with open(filepath, "rb") as f:
            r = requests.post(url, headers=headers, data=f, timeout=10)
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/snapshots/{storage_path}"
    except Exception as e:
        print("Snapshot upload error:", e)
    return ""


def fetch_alerts(vehicle_id=None, limit=2000):
    """Fetch alerts from Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        url     = f"{SUPABASE_URL}/rest/v1/alerts"
        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        params = {
            "order":  "timestamp.desc",
            "limit":  limit,
            "select": "*",
        }
        if vehicle_id:
            params["vehicle_id"] = f"eq.{vehicle_id}"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("Supabase fetch error:", e)
    return []


def test_connection():
    """Returns True if Supabase is reachable."""
    try:
        result = fetch_alerts(limit=1)
        return True
    except Exception:
        return False
