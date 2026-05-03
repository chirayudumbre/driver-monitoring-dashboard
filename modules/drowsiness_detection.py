import cv2
import math
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from modules.alert_system import play_alert

# ── FaceLandmarker setup ──────────────────────────────────────────────────────
_base_options = mp_python.BaseOptions(
    model_asset_path="models/face_landmarker.task",
    delegate=mp_python.BaseOptions.Delegate.CPU
)
_options = vision.FaceLandmarkerOptions(
    base_options=_base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1,
    running_mode=vision.RunningMode.IMAGE,
)
_detector = vision.FaceLandmarker.create_from_options(_options)

# Eye landmark indices (same as before — 478-point mesh)
LEFT_EYE  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

EYE_THRESHOLD = 0.25
FRAME_LIMIT   = 15
counter       = 0


def _euclidean(p1, p2, w, h):
    return math.dist((int(p1.x * w), int(p1.y * h)),
                     (int(p2.x * w), int(p2.y * h)))


def _ear(landmarks, w, h):
    def ratio(idx):
        lm = landmarks
        return (
            (_euclidean(lm[idx[1]], lm[idx[5]], w, h) +
             _euclidean(lm[idx[2]], lm[idx[4]], w, h)) /
            (2.0 * _euclidean(lm[idx[0]], lm[idx[3]], w, h) + 1e-6)
        )
    return (ratio(LEFT_EYE) + ratio(RIGHT_EYE)) / 2.0


def detect_drowsiness(frame):
    global counter
    h, w = frame.shape[:2]
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _detector.detect(mp_img)
    drowsy = False

    if result.face_landmarks:
        landmarks = result.face_landmarks[0]
        eye_ratio = _ear(landmarks, w, h)

        if eye_ratio < EYE_THRESHOLD:
            counter += 1
            if counter >= FRAME_LIMIT:
                drowsy = True
                cv2.putText(frame, "DROWSINESS ALERT", (30, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                play_alert()
        else:
            counter = 0

    return frame, drowsy
