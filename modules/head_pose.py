# modules/head_pose.py
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

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

HEAD_TURN_THRESHOLD = 0.35


def detect_distraction(frame):
    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _detector.detect(mp_img)
    distracted = False

    if result.face_landmarks:
        lm        = result.face_landmarks[0]
        nose      = lm[1]
        left_eye  = lm[33]
        right_eye = lm[263]

        ratio = (nose.x - left_eye.x) / (right_eye.x - left_eye.x + 1e-6)

        if ratio < HEAD_TURN_THRESHOLD or ratio > (1 - HEAD_TURN_THRESHOLD):
            distracted = True
            cv2.putText(frame, "DISTRACTION ALERT!", (30, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    return frame, distracted
