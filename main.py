import cv2
from dotenv import load_dotenv
load_dotenv()  # loads SUPABASE_URL and SUPABASE_KEY from .env

from modules.video_capture import start_camera, release_camera
from modules.drowsiness_detection import detect_drowsiness
from modules.head_pose import detect_distraction
from modules.mobile_detection import detect_mobile
from utils.logger import log_alert
from utils.config import get_active_vehicle

cap = start_camera()
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Re-read active vehicle every 30 frames (~1 sec) so switching
    # vehicles on the dashboard takes effect without restarting main.py
    if frame_count % 30 == 0:
        VEHICLE_ID = get_active_vehicle()

    frame, drowsy     = detect_drowsiness(frame)
    frame, distracted = detect_distraction(frame)
    frame, phone      = detect_mobile(frame)

    if drowsy:
        log_alert("DROWSINESS",   frame=frame, vehicle_id=VEHICLE_ID)
    if distracted:
        log_alert("DISTRACTION",  frame=frame, vehicle_id=VEHICLE_ID)
    if phone:
        log_alert("MOBILE_USAGE", frame=frame, vehicle_id=VEHICLE_ID)

    # Show active vehicle on the camera window
    cv2.putText(frame, f"Vehicle: {VEHICLE_ID}", (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)

    cv2.imshow("AI Driver Monitoring System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    frame_count += 1

release_camera(cap)
