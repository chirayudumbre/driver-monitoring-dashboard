"""
AI Driver Monitoring System — Raspberry Pi 4
============================================
Hardware:
  - Raspberry Pi 4
  - USB or CSI Camera
  - Active Buzzer on GPIO 17 (Pin 11)
  - Car 12V → USB-C 5V/3A power supply

Features:
  - Drowsiness detection  (MediaPipe EAR)
  - Distraction detection (MediaPipe head pose)
  - Mobile phone detection (YOLOv8n — lightweight for Pi)
  - GPIO buzzer alert
  - Offline SQLite queue  → auto-sync to Supabase when internet available
  - Auto-start on boot via systemd

Usage:
  python3 main_pi.py
"""

import cv2
import os
import sys
import time
import threading

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from pi.buzzer          import Buzzer
from pi.offline_queue   import OfflineQueue
from pi.pi_logger       import PiLogger
from pi.pi_detection    import PiDetector

# ── Config ────────────────────────────────────────────────────────────────────
BUZZER_GPIO    = 17          # GPIO pin number (BCM)
CAMERA_INDEX   = 0           # 0 = first USB cam, or use /dev/video0
FRAME_WIDTH    = 640
FRAME_HEIGHT   = 480
VEHICLE_ID_FILE = os.path.join(BASE_DIR, "dashboard", "active_vehicle.json")


def get_vehicle_id() -> str:
    """Read vehicle ID from local JSON (set via dashboard login)."""
    import json
    if os.path.exists(VEHICLE_ID_FILE):
        try:
            with open(VEHICLE_ID_FILE, encoding="utf-8") as f:
                return json.load(f).get("vehicle_id", "UNKNOWN")
        except Exception:
            pass
    return os.environ.get("VEHICLE_ID", "UNKNOWN")


def main():
    print("=" * 50)
    print("  AI Driver Monitoring System — Raspberry Pi 4")
    print("=" * 50)

    # ── Hardware init ─────────────────────────────────────────────────────────
    buzzer = Buzzer(pin=BUZZER_GPIO)
    buzzer.beep(times=2, duration=0.2)   # startup beep: 2 short beeps
    print("[HW]  Buzzer initialized on GPIO", BUZZER_GPIO)

    # ── Offline queue + background sync thread ────────────────────────────────
    queue  = OfflineQueue(db_path=os.path.join(BASE_DIR, "data", "offline_queue.db"))
    logger = PiLogger(queue=queue, base_dir=BASE_DIR)
    print("[DB]  Offline queue ready:", queue.pending_count(), "pending items")

    # Start background sync thread
    sync_thread = threading.Thread(target=queue.sync_loop, daemon=True)
    sync_thread.start()
    print("[NET] Background sync thread started")

    # ── Detection models ──────────────────────────────────────────────────────
    print("[AI]  Loading detection models...")
    detector = PiDetector(base_dir=BASE_DIR)
    print("[AI]  Models loaded")

    # ── Camera init ───────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 15)       # 15fps is enough, saves CPU on Pi

    if not cap.isOpened():
        print("[ERR] Cannot open camera. Check connection.")
        buzzer.beep(times=5, duration=0.1)
        sys.exit(1)

    print("[CAM] Camera opened:", FRAME_WIDTH, "x", FRAME_HEIGHT, "@ 15fps")
    print("[OK]  Monitoring started. Press Ctrl+C to stop.\n")

    frame_count  = 0
    vehicle_id   = get_vehicle_id()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Frame grab failed, retrying...")
                time.sleep(0.1)
                continue

            # Re-read vehicle ID every 150 frames (~10 sec)
            if frame_count % 150 == 0:
                vehicle_id = get_vehicle_id()

            # ── Run detections ────────────────────────────────────────────────
            frame, drowsy     = detector.detect_drowsiness(frame)
            frame, distracted = detector.detect_distraction(frame)
            frame, phone      = detector.detect_mobile(frame)

            # ── Handle alerts ─────────────────────────────────────────────────
            if drowsy:
                print(f"[ALERT] DROWSINESS  | Vehicle: {vehicle_id}")
                buzzer.beep(times=3, duration=0.3)
                logger.log(alert_type="DROWSINESS", frame=frame, vehicle_id=vehicle_id)

            if distracted:
                print(f"[ALERT] DISTRACTION | Vehicle: {vehicle_id}")
                buzzer.beep(times=2, duration=0.2)
                logger.log(alert_type="DISTRACTION", frame=frame, vehicle_id=vehicle_id)

            if phone:
                print(f"[ALERT] MOBILE_USAGE| Vehicle: {vehicle_id}")
                buzzer.beep(times=4, duration=0.15)
                logger.log(alert_type="MOBILE_USAGE", frame=frame, vehicle_id=vehicle_id)

            # ── OSD overlay ───────────────────────────────────────────────────
            cv2.putText(frame, f"Vehicle: {vehicle_id}",
                        (10, frame.shape[0] - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"Queue: {queue.pending_count()}",
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)

            # Show frame only if display is connected (headless Pi skips this)
            if os.environ.get("DISPLAY"):
                cv2.imshow("AI Driver Monitoring", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_count += 1

    except KeyboardInterrupt:
        print("\n[STOP] Monitoring stopped by user.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        buzzer.beep(times=1, duration=0.5)   # shutdown beep
        buzzer.cleanup()
        print("[DONE] Camera released. Goodbye.")


if __name__ == "__main__":
    main()
