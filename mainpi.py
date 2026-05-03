"""
AI Driver Monitoring System (Single File)
- Drowsiness detection via Eye Aspect Ratio (EAR)
- Distraction detection via head orientation (ratio method)
- Alerts displayed on screen and snapshots saved on trigger
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import os
from datetime import datetime

# ========================== CONFIGURATION ==========================
# Drowsiness
EAR_THRESHOLD = 0.25           # Eye Aspect Ratio below which eyes are considered closed
DROWSY_CONSEC_FRAMES = 3       # Number of consecutive low EAR frames to trigger alert

# Distraction (from your head_pose.py)
HEAD_TURN_THRESHOLD = 0.35      # Horizontal ratio threshold (0=far left, 1=far right)
DISTRACTED_CONSEC_FRAMES = 3    # Consecutive frames to avoid flickering

# Snapshot directory
SNAPSHOT_DIR = "alerts"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
# ===================================================================

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,      # Get refined landmarks around eyes
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Indices for eyes (MediaPipe)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

def eye_aspect_ratio(eye_landmarks):
    """
    Calculate Eye Aspect Ratio (EAR) given six landmarks of an eye.
    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    vertical1 = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
    vertical2 = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
    horizontal = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear

def detect_drowsiness(landmarks, frame):
    """
    Detect drowsiness using Eye Aspect Ratio.
    Returns: (ear_value, is_drowsy)
    """
    h, w = frame.shape[:2]
    left_eye = []
    right_eye = []
    for idx in LEFT_EYE_INDICES:
        lm = landmarks.landmark[idx]
        left_eye.append([lm.x * w, lm.y * h])
    for idx in RIGHT_EYE_INDICES:
        lm = landmarks.landmark[idx]
        right_eye.append([lm.x * w, lm.y * h])

    left_eye = np.array(left_eye)
    right_eye = np.array(right_eye)

    ear_left = eye_aspect_ratio(left_eye)
    ear_right = eye_aspect_ratio(right_eye)
    ear = (ear_left + ear_right) / 2.0

    # Draw eye landmarks
    for (x, y) in left_eye.astype(int):
        cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
    for (x, y) in right_eye.astype(int):
        cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

    drowsy = ear < EAR_THRESHOLD
    return ear, drowsy

def detect_distraction(landmarks, frame):
    """
    Distraction detection using your head_pose.py logic.
    Returns: distracted (bool)
    """
    # Nose tip = landmark 1, Left eye = 33, Right eye = 263
    nose = landmarks.landmark[1]
    left_eye = landmarks.landmark[33]
    right_eye = landmarks.landmark[263]

    # Calculate horizontal ratio (0=left,1=right)
    ratio = (nose.x - left_eye.x) / (right_eye.x - left_eye.x + 1e-6)

    # Check if head is turned beyond threshold
    distracted = (ratio < HEAD_TURN_THRESHOLD) or (ratio > (1 - HEAD_TURN_THRESHOLD))

    # Optionally draw the ratio on frame
    cv2.putText(frame, f"Head ratio: {ratio:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    return distracted

def save_snapshot(frame, alert_type):
    """
    Save a snapshot of the frame when an alert is triggered.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = os.path.join(SNAPSHOT_DIR, f"{alert_type}_{timestamp}.jpg")
    cv2.imwrite(filename, frame)
    print(f"Snapshot saved: {filename}")

def main():
    # Open laptop camera
    cap = z2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # For FPS calculation
    fps_counter = 0
    fps = 0
    fps_start_time = time.time()

    # Alert counters (to avoid flickering)
    drowsy_counter = 0
    distracted_counter = 0

    # Flags to prevent saving multiple snapshots for the same alert event
    last_drowsy_alert = False
    last_distracted_alert = False

    print("Driver Monitoring System Started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # Mirror horizontally for natural view
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process with MediaPipe
        results = face_mesh.process(rgb_frame)

        drowsy = False
        distracted = False

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]

            # ---- Drowsiness detection ----
            ear, drowsy_now = detect_drowsiness(landmarks, frame)
            if drowsy_now:
                drowsy_counter += 1
            else:
                drowsy_counter = 0
            if drowsy_counter >= DROWSY_CONSEC_FRAMES:
                drowsy = True

            # ---- Distraction detection (your method) ----
            distracted_now = detect_distraction(landmarks, frame)
            if distracted_now:
                distracted_counter += 1
            else:
                distracted_counter = 0
            if distracted_counter >= DISTRACTED_CONSEC_FRAMES:
                distracted = True

            # Display EAR
            cv2.putText(frame, f"EAR: {ear:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        else:
            # No face detected – reset counters
            drowsy_counter = 0
            distracted_counter = 0

        # Handle alerts
        if drowsy and not last_drowsy_alert:
            save_snapshot(frame, "DROWSY")
        if distracted and not last_distracted_alert:
            save_snapshot(frame, "DISTRACTED")

        last_drowsy_alert = drowsy
        last_distracted_alert = distracted

        # Draw alert texts
        if drowsy:
            cv2.putText(frame, "DROWSY ALERT!", (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        if distracted:
            cv2.putText(frame, "DISTRACTION ALERT!", (50, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        # Calculate and show FPS
        fps_counter += 1
        if time.time() - fps_start_time >= 1.0:
            fps = fps_counter / (time.time() - fps_start_time)
            fps_counter = 0
            fps_start_time = time.time()
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Driver Monitoring", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()

if __name__ == "__main__":
    main()