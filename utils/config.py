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
    """Read the currently active vehicle ID set from the dashboard."""
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("vehicle_id", "UNKNOWN")
        except Exception:
            pass
    return "UNKNOWN"


def set_active_vehicle(vehicle_id: str):
    """Write the active vehicle ID so main.py picks it up."""
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"vehicle_id": vehicle_id}, f)
