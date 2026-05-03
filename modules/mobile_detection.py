"""
Mobile phone detection while driving.

Uses YOLOv8 to detect 'cell phone' (COCO class 67) in the frame.
Alert fires when phone is detected for REQUIRED_FRAMES consecutive frames.
"""

import cv2
import time
from ultralytics import YOLO

# ── YOLOv8 model ──────────────────────────────────────────────────────────────
# yolov8s is more accurate than yolov8n for small objects like phones
_yolo = YOLO("models/yolov8s.pt")

PHONE_CLASS_ID  = 67    # COCO: 'cell phone'
YOLO_CONF       = 0.30  # lower = more sensitive

# ── Stability counters ────────────────────────────────────────────────────────
_phone_frames    = 0
REQUIRED_FRAMES  = 8    # frames phone must be visible before alert
_last_alert_time = 0
ALERT_COOLDOWN   = 4    # seconds


def detect_mobile(frame):
    global _phone_frames, _last_alert_time

    phone_found = False

    results = _yolo(frame, verbose=False, conf=YOLO_CONF, classes=[PHONE_CLASS_ID])

    for r in results:
        for box in r.boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            if cls == PHONE_CLASS_ID:
                phone_found = True
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                cv2.putText(frame, f"Phone {conf:.0%}",
                            (x1, max(y1 - 8, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)

    if phone_found:
        _phone_frames += 1
    else:
        _phone_frames = max(0, _phone_frames - 2)  # decay faster on no-detect

    if _phone_frames >= REQUIRED_FRAMES:
        cv2.putText(frame, "!! MOBILE PHONE USAGE !!",
                    (30, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        if time.time() - _last_alert_time > ALERT_COOLDOWN:
            _last_alert_time = time.time()
            return frame, True  # trigger log + sound

        return frame, False  # still showing text but cooldown active

    return frame, False
