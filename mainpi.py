"""
AI Driver Monitoring System — Raspberry Pi Edition
- Drowsiness detection via Eye Aspect Ratio (MediaPipe FaceMesh)
- Distraction detection via head pose ratio
- Mobile phone detection via YOLOv8n (nano — Pi-friendly)
- Alerts logged to Supabase DB + local CSV
- Snapshots uploaded to Supabase Storage
- Active vehicle synced from Supabase
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import os
import csv
import math
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Try importing YOLO (skip gracefully if not available on Pi) ───────────────
try:
    from ultralytics import YOLO
    _yolo = YOLO("models/yolov8n.pt")   # nano model — lightest option
    YOLO_AVAILABLE = True
    print("YOLO loaded (yolov8n)")
except Exception as e:
    _yolo = None
    YOLO_AVAILABLE = False
    print(f"YOLO not available ({e}) — phone detection disabled")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Drowsiness
EAR_THRESHOLD        = 0.25
DROWSY_CONSEC_FRAMES = 15

# Distraction
HEAD_TURN_THRESHOLD  = 0.35
DISTRACT_CONSEC      = 10

# Phone (YOLO)
PHONE_CLASS_ID       = 67
PHONE_CONF           = 0.30
PHONE_CONSEC_FRAMES  = 8
PHONE_COOLDOWN       = 4     # seconds

# Snapshots
SNAPSHOT_DIR         = "data/snapshots"
LOG_FILE             = "data/alert_log.csv"
SAVE_COOLDOWN        = 3     # seconds between snapshots per alert type

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def _headers(extra=None):
    h = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }
    if extra:
        h.update(extra)
    return h


def supabase_insert(timestamp, alert_type, vehicle_id, snapshot_url=""):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/alerts",
            headers=_headers(),
            json={
                "timestamp":    timestamp,
                "alert_type":   alert_type,
                "vehicle_id":   vehicle_id,
                "snapshot_url": snapshot_url,
            },
            timeout=5
        )
    except Exception as e:
        print(f"Supabase insert error: {e}")


def supabase_upload(vehicle_id, filename, filepath):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return ""
    try:
        storage_path = f"{vehicle_id}/{filename}"
        endpoint     = f"{SUPABASE_URL}/storage/v1/object/snapshots/{storage_path}"
        with open(filepath, "rb") as f:
            r = requests.post(
                endpoint,
                headers={
                    "apikey":        SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type":  "image/jpeg",
                    "x-upsert":      "true",
                },
                data=f, timeout=10
            )
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/snapshots/{storage_path}"
    except Exception as e:
        print(f"Snapshot upload error: {e}")
    return ""


def get_active_vehicle():
    """Read active vehicle from Supabase, fallback to local JSON."""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/active_vehicle",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                params={"select": "vehicle_id", "id": "eq.1"},
                timeout=5
            )
            if r.status_code == 200 and r.json():
                vid = r.json()[0].get("vehicle_id", "")
                if vid:
                    return vid
        except Exception:
            pass
    # Fallback: local JSON
    local = os.path.join("dashboard", "active_vehicle.json")
    if os.path.exists(local):
        try:
            return json.load(open(local)).get("vehicle_id", "PI_CAM")
        except Exception:
            pass
    return "PI_CAM"


def log_alert_local(timestamp, alert_type, vehicle_id, snapshot_path=""):
    """Append alert to local CSV backup."""
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "alert_type", "vehicle_id", "snapshot"])
        writer.writerow([timestamp, alert_type, vehicle_id, snapshot_path])

# ══════════════════════════════════════════════════════════════════════════════
# MEDIAPIPE SETUP
# ══════════════════════════════════════════════════════════════════════════════

mp_face_mesh = mp.solutions.face_mesh
face_mesh    = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

LEFT_EYE_IDX  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]


def _ear(eye_pts):
    """Eye Aspect Ratio from 6 (x,y) points."""
    v1 = np.linalg.norm(eye_pts[1] - eye_pts[5])
    v2 = np.linalg.norm(eye_pts[2] - eye_pts[4])
    h  = np.linalg.norm(eye_pts[0] - eye_pts[3])
    return (v1 + v2) / (2.0 * h + 1e-6)


def get_eye_ratio(landmarks, w, h):
    def pts(indices):
        return np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in indices])
    left  = _ear(pts(LEFT_EYE_IDX))
    right = _ear(pts(RIGHT_EYE_IDX))
    return (left + right) / 2.0


def get_head_ratio(landmarks):
    nose      = landmarks[1]
    left_eye  = landmarks[33]
    right_eye = landmarks[263]
    return (nose.x - left_eye.x) / (right_eye.x - left_eye.x + 1e-6)

# ══════════════════════════════════════════════════════════════════════════════
# ALERT + SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════

_last_saved = {}

def trigger_alert(alert_type, frame, vehicle_id):
    now           = datetime.now()
    timestamp     = now.strftime("%Y-%m-%d %H:%M:%S")
    snapshot_path = ""
    snapshot_url  = ""

    # Snapshot with cooldown
    last = _last_saved.get(alert_type, 0)
    if time.time() - last >= SAVE_COOLDOWN:
        filename      = f"{alert_type}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        snapshot_path = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(snapshot_path, frame)
        _last_saved[alert_type] = time.time()
        print(f"[{timestamp}] {alert_type} snapshot saved")

        # Upload to Supabase Storage (non-blocking best-effort)
        snapshot_url = supabase_upload(vehicle_id, filename, snapshot_path)

    # Insert to Supabase + local CSV
    supabase_insert(timestamp, alert_type, vehicle_id, snapshot_url)
    log_alert_local(timestamp, alert_type, vehicle_id, snapshot_path)
    print(f"[{timestamp}] ALERT: {alert_type} | Vehicle: {vehicle_id}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("Starting AI Driver Monitoring System (Pi Edition)...")

    # Camera — works with USB webcam or PiCamera (with libcamera/v4l2 driver)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera. Check connection.")
        return

    # Lower resolution for Pi performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS,          15)

    # Counters
    drowsy_counter   = 0
    distract_counter = 0
    phone_counter    = 0
    frame_count      = 0
    _last_phone_alert = 0

    VEHICLE_ID = get_active_vehicle()
    print(f"Active vehicle: {VEHICLE_ID}")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed.")
            break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # Re-read vehicle every 5 seconds (~75 frames at 15fps)
        if frame_count % 75 == 0:
            VEHICLE_ID = get_active_vehicle()

        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        drowsy     = False
        distracted = False
        phone      = False

        # ── Face detection ────────────────────────────────────────────────────
        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark

            # Drowsiness
            ear = get_eye_ratio(lm, w, h)
            if ear < EAR_THRESHOLD:
                drowsy_counter += 1
            else:
                drowsy_counter = 0
            if drowsy_counter >= DROWSY_CONSEC_FRAMES:
                drowsy = True
                cv2.putText(frame, "DROWSINESS ALERT!", (30, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

            # Distraction
            ratio = get_head_ratio(lm)
            if ratio < HEAD_TURN_THRESHOLD or ratio > (1 - HEAD_TURN_THRESHOLD):
                distract_counter += 1
            else:
                distract_counter = 0
            if distract_counter >= DISTRACT_CONSEC:
                distracted = True
                cv2.putText(frame, "DISTRACTION ALERT!", (30, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)

            cv2.putText(frame, f"EAR:{ear:.2f}  HEAD:{ratio:.2f}", (10, h - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        else:
            drowsy_counter   = 0
            distract_counter = 0

        # ── Phone detection (YOLO) ────────────────────────────────────────────
        if YOLO_AVAILABLE and frame_count % 3 == 0:   # run YOLO every 3rd frame
            yolo_results = _yolo(frame, verbose=False, conf=PHONE_CONF,
                                 classes=[PHONE_CLASS_ID])
            phone_found = False
            for r in yolo_results:
                for box in r.boxes:
                    if int(box.cls[0]) == PHONE_CLASS_ID:
                        phone_found = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                        cv2.putText(frame, f"Phone {float(box.conf[0]):.0%}",
                                    (x1, max(y1 - 8, 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            if phone_found:
                phone_counter += 1
            else:
                phone_counter = max(0, phone_counter - 2)

            if phone_counter >= PHONE_CONSEC_FRAMES:
                cv2.putText(frame, "MOBILE PHONE USAGE!", (30, 160),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                if time.time() - _last_phone_alert > PHONE_COOLDOWN:
                    phone = True
                    _last_phone_alert = time.time()

        # ── Trigger alerts ────────────────────────────────────────────────────
        if drowsy:
            trigger_alert("DROWSINESS",   frame, VEHICLE_ID)
        if distracted:
            trigger_alert("DISTRACTION",  frame, VEHICLE_ID)
        if phone:
            trigger_alert("MOBILE_USAGE", frame, VEHICLE_ID)

        # ── HUD ───────────────────────────────────────────────────────────────
        cv2.putText(frame, f"Vehicle: {VEHICLE_ID}", (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (w - 80, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("AI Driver Monitor (Pi)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    print("Monitoring stopped.")


if __name__ == "__main__":
    main()
