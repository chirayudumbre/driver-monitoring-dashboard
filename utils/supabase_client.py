"""
Lightweight Supabase client using only 'requests' — no httpx/httpcore needed.
Works on Python 3.14 and Streamlit Cloud (reads from st.secrets with os.environ fallback).
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


def _get_credentials():
    """
    Read Supabase credentials.
    Priority: st.secrets (Streamlit Cloud) → os.environ (.env locally).
    """
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        return url, key
    except Exception:
        return os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")


def _headers():
    _, key = _get_credentials()
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def insert_alert(timestamp, alert_type, vehicle_id, snapshot_url=""):
    """Insert one alert row into Supabase alerts table."""
    url, key = _get_credentials()
    if not url or not key:
        return False
    try:
        endpoint = f"{url}/rest/v1/alerts"
        data = {
            "timestamp":    timestamp,
            "alert_type":   alert_type,
            "vehicle_id":   vehicle_id,
            "snapshot_url": snapshot_url,
        }
        r = requests.post(endpoint, headers=_headers(), json=data, timeout=5)
        return r.status_code in (200, 201)
    except Exception as e:
        print("Supabase insert error:", e)
        return False


def upload_snapshot(vehicle_id, filename, filepath):
    """Upload image to Supabase Storage bucket 'snapshots'."""
    url, key = _get_credentials()
    if not url or not key:
        return ""
    try:
        storage_path = f"{vehicle_id}/{filename}"
        endpoint = f"{url}/storage/v1/object/snapshots/{storage_path}"
        headers = {
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Content-Type":  "image/jpeg",
            "x-upsert":      "true",
        }
        with open(filepath, "rb") as f:
            r = requests.post(endpoint, headers=headers, data=f, timeout=10)
        if r.status_code in (200, 201):
            return f"{url}/storage/v1/object/public/snapshots/{storage_path}"
    except Exception as e:
        print("Snapshot upload error:", e)
    return ""


def fetch_alerts(vehicle_id=None, limit=2000):
    """Fetch alerts from Supabase."""
    url, key = _get_credentials()
    if not url or not key:
        return []
    try:
        endpoint = f"{url}/rest/v1/alerts"
        headers  = {
            "apikey":        key,
            "Authorization": f"Bearer {key}",
        }
        params = {
            "order":  "timestamp.desc",
            "limit":  limit,
            "select": "*",
        }
        if vehicle_id:
            params["vehicle_id"] = f"eq.{vehicle_id}"
        r = requests.get(endpoint, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("Supabase fetch error:", e)
    return []


def test_connection():
    """Returns True if Supabase is reachable."""
    try:
        url, key = _get_credentials()
        if not url or not key:
            return False
        fetch_alerts(limit=1)
        return True
    except Exception:
        return False
