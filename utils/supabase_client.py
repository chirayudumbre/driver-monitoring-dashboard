"""
Lightweight Supabase client using only 'requests' — no httpx/httpcore needed.
Works on Python 3.14 and Streamlit Cloud (reads from st.secrets with os.environ fallback).
"""
import os
import json
from datetime import datetime
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


def get_active_vehicle_cloud():
    """Read the active vehicle ID from Supabase (set by cloud dashboard)."""
    url, key = _get_credentials()
    if not url or not key:
        return None
    try:
        endpoint = f"{url}/rest/v1/active_vehicle"
        headers  = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.get(endpoint, headers=headers,
                         params={"select": "vehicle_id", "id": "eq.1"}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0].get("vehicle_id")
    except Exception as e:
        print("get_active_vehicle_cloud error:", e)
    return None


def set_active_vehicle_cloud(vehicle_id: str):
    """Write the active vehicle ID to Supabase (called by dashboard on login/switch)."""
    url, key = _get_credentials()
    if not url or not key:
        return False
    try:
        endpoint = f"{url}/rest/v1/active_vehicle"
        headers  = {
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        }
        r = requests.post(endpoint, headers=headers,
                          json={"id": 1, "vehicle_id": vehicle_id,
                                "updated_at": datetime.utcnow().isoformat()},
                          timeout=5)
        return r.status_code in (200, 201)
    except Exception as e:
        print("set_active_vehicle_cloud error:", e)
    return False


def test_connection() -> bool:
    """Returns True if Supabase is reachable and returns data."""
    try:
        url, key = _get_credentials()
        if not url or not key:
            return False
        endpoint = f"{url}/rest/v1/alerts"
        headers  = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.get(endpoint, headers=headers,
                         params={"limit": 1, "select": "*"}, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — Admin, Vehicle, Driver CRUD via Supabase
# ══════════════════════════════════════════════════════════════════════════════

import hashlib


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get(table: str, params: dict = None) -> list:
    url, key = _get_credentials()
    if not url or not key:
        return []
    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/rest/v1/{table}",
                         headers=headers, params=params or {}, timeout=8)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"Supabase GET {table} error:", e)
        return []


def _post(table: str, data: dict) -> bool:
    url, key = _get_credentials()
    if not url or not key:
        return False
    try:
        r = requests.post(f"{url}/rest/v1/{table}",
                          headers=_headers(), json=data, timeout=8)
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"Supabase POST {table} error:", e)
        return False


def _patch(table: str, match_col: str, match_val: str, data: dict) -> bool:
    url, key = _get_credentials()
    if not url or not key:
        return False
    try:
        headers = {**_headers(), "Prefer": "return=minimal"}
        r = requests.patch(f"{url}/rest/v1/{table}",
                           headers=headers,
                           params={match_col: f"eq.{match_val}"},
                           json=data, timeout=8)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"Supabase PATCH {table} error:", e)
        return False


def _delete(table: str, match_col: str, match_val: str) -> bool:
    url, key = _get_credentials()
    if not url or not key:
        return False
    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.delete(f"{url}/rest/v1/{table}",
                            headers=headers,
                            params={match_col: f"eq.{match_val}"}, timeout=8)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"Supabase DELETE {table} error:", e)
        return False


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_exists() -> bool:
    rows = _get("admins", {"limit": 1, "select": "id"})
    return len(rows) > 0


def create_admin(username: str, password: str) -> bool:
    return _post("admins", {
        "username": username.strip(),
        "password": _hash(password),
    })


def verify_admin(username: str, password: str) -> bool:
    rows = _get("admins", {
        "username": f"eq.{username.strip()}",
        "password": f"eq.{_hash(password)}",
        "select":   "id",
        "limit":    1,
    })
    return len(rows) > 0


def update_admin_password(username: str, new_password: str) -> bool:
    return _patch("admins", "username", username.strip(),
                  {"password": _hash(new_password)})


# ── Vehicles ──────────────────────────────────────────────────────────────────

def fetch_vehicles() -> list:
    return _get("vehicles", {"order": "registration_date.desc", "select": "*"})


def create_vehicle(vehicle_number: str, vehicle_password: str,
                   vehicle_model: str = "", status: str = "Active") -> bool:
    return _post("vehicles", {
        "vehicle_number":   vehicle_number.strip().upper(),
        "vehicle_password": _hash(vehicle_password),
        "vehicle_model":    vehicle_model,
        "status":           status,
    })


def update_vehicle(vehicle_number: str, data: dict) -> bool:
    if "vehicle_password" in data and data["vehicle_password"]:
        data["vehicle_password"] = _hash(data["vehicle_password"])
    return _patch("vehicles", "vehicle_number",
                  vehicle_number.strip().upper(), data)


def delete_vehicle(vehicle_number: str) -> bool:
    return _delete("vehicles", "vehicle_number",
                   vehicle_number.strip().upper())


def verify_vehicle(vehicle_number: str, password: str) -> dict | None:
    """Returns vehicle row if credentials match, else None."""
    rows = _get("vehicles", {
        "vehicle_number":   f"eq.{vehicle_number.strip().upper()}",
        "vehicle_password": f"eq.{_hash(password)}",
        "select":           "*",
        "limit":            1,
    })
    return rows[0] if rows else None


# ── Drivers ───────────────────────────────────────────────────────────────────

def fetch_drivers() -> list:
    return _get("drivers", {"order": "created_at.desc", "select": "*"})


def create_driver(driver_name: str, username: str, password: str,
                  phone_number: str = "", vehicle_id: str = "") -> bool:
    return _post("drivers", {
        "driver_name":  driver_name.strip(),
        "username":     username.strip(),
        "password":     _hash(password),
        "phone_number": phone_number,
        "vehicle_id":   vehicle_id.strip().upper() if vehicle_id else None,
    })


def update_driver(username: str, data: dict) -> bool:
    if "password" in data and data["password"]:
        data["password"] = _hash(data["password"])
    return _patch("drivers", "username", username.strip(), data)


def delete_driver(username: str) -> bool:
    return _delete("drivers", "username", username.strip())


def verify_driver(username: str, password: str) -> dict | None:
    """Returns driver row if credentials match, else None."""
    rows = _get("drivers", {
        "username": f"eq.{username.strip()}",
        "password": f"eq.{_hash(password)}",
        "select":   "*",
        "limit":    1,
    })
    return rows[0] if rows else None
