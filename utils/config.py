# utils/config.py
import os
import json

_BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_FILE = os.path.join(_BASE, "dashboard", "active_vehicle.json")

# Drowsiness
EYE_AR_THRESHOLD = 0.25
EYE_FRAME_LIMIT  = 15

# Distraction
HEAD_TURN_THRESHOLD = 20

# Alert
ALERT_COOLDOWN = 3


def get_active_vehicle() -> str:
    """
    Read the currently active vehicle ID.
    Priority: Supabase (cloud dashboard) → st.session_state → local JSON file.
    """
    # 1. Try Supabase — works for both cloud and local when internet is available
    try:
        from utils.supabase_client import get_active_vehicle_cloud
        vid = get_active_vehicle_cloud()
        if vid and vid != "UNKNOWN":
            return vid
    except Exception:
        pass

    # 2. Try session state (local dashboard)
    try:
        import streamlit as st
        vid = st.session_state.get("vehicle_id", "")
        if vid:
            return vid
    except Exception:
        pass

    # 3. Fall back to local JSON file
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("vehicle_id", "UNKNOWN")
        except Exception:
            pass
    return "UNKNOWN"


def set_active_vehicle(vehicle_id: str):
    """Write the active vehicle ID to Supabase + local JSON so main.py picks it up."""
    # Write to Supabase (picked up by main.py via get_active_vehicle_cloud)
    try:
        from utils.supabase_client import set_active_vehicle_cloud
        set_active_vehicle_cloud(vehicle_id)
    except Exception:
        pass
    # Also write local JSON as fallback
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"vehicle_id": vehicle_id}, f)
