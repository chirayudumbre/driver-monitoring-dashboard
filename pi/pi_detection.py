"""
pi/pi_detection.py
==================
Detection pipeline optimised for Raspberry Pi 5.

Features:
  - Face validation before any detection (full face must be in frame)
  - Single FaceLandmarker shared by drowsiness + distraction
  - YOLOv8n for phone detection
  - Frame skip for YOLO to save CPU
"""

import cv2
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


# ── Landmark indices ──────────────────────────────────────────────────────────
LEFT_EYE  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Face boundary landmarks to check if full face is in frame
FACE_BOUNDARY = [10, 338, 297, 332, 284, 251, 389, 356,
                 454, 323, 361, 288, 397, 365, 379, 378,
                 400, 377, 152, 148, 176, 149, 150, 136,
                 172, 58,  132, 93,  234, 127, 162, 21,
                 54,  103, 67,  109]


class PiDetector:
    # Drowsiness
    EAR_THRESHOLD   = 0.22
    EAR_FRAME_LIMIT = 8

    # Distraction — NO face validation needed, just head ratio
    HEAD_THRESHOLD       = 0.33
    DISTRACT_FRAME_LIMIT = 6

    # Phone — use yolov8s for better accuracy on Pi 5
    PHONE_CLASS_ID   = 67
    PHONE_CONF       = 0.20
    PHONE_REQ_FRAMES = 4
    YOLO_SKIP_FRAMES = 2

    # Face validation — only for drowsiness
    FACE_MARGIN = 0.03

    def __init__(self, base_dir: str):
        model_path = os.path.join(base_dir, "models", "face_landmarker.task")

        # ── Single shared FaceLandmarker ──────────────────────────────────────
        base_opts = mp_python.BaseOptions(
            model_asset_path=model_path,
            delegate=mp_python.BaseOptions.Delegate.CPU
        )
        opts = vision.FaceLandmarkerOptions(
            base_options=base_opts,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
            running_mode=vision.RunningMode.IMAGE,
        )
        self._face_detector = vision.FaceLandmarker.create_from_options(opts)

        # ── YOLOv8s for better phone detection on Pi 5 ───────────────────────
        from ultralytics import YOLO
        # Try yolov8s first (more accurate), fall back to yolov8n
        yolo_s = os.path.join(base_dir, "models", "yolov8s.pt")
        yolo_n = os.path.join(base_dir, "models", "yolov8n.pt")
        yolo_path = yolo_s if os.path.exists(yolo_s) else yolo_n
        self._yolo = YOLO(yolo_path)
        print(f"[AI]  YOLO model: {os.path.basename(yolo_path)}")

        # ── State ─────────────────────────────────────────────────────────────
        self._drown_counter    = 0
        self._distract_counter = 0
        self._phone_frames     = 0
        self._yolo_skip        = 0
        self._last_phone_det   = False
        self._face_valid       = False   # is full face in frame?

    # ── Face validation ───────────────────────────────────────────────────────
    def _is_face_valid(self, landmarks, w, h) -> bool:
        """Check if all key face landmarks are well within the frame."""
        margin_x = int(w * self.FACE_MARGIN)
        margin_y = int(h * self.FACE_MARGIN)

        for idx in FACE_BOUNDARY:
            lm = landmarks[idx]
            px = int(lm.x * w)
            py = int(lm.y * h)
            if px < margin_x or px > w - margin_x:
                return False
            if py < margin_y or py > h - margin_y:
                return False
        return True

    # ── EAR helper ────────────────────────────────────────────────────────────
    @staticmethod
    def _euclidean(p1, p2, w, h):
        return math.dist(
            (int(p1.x * w), int(p1.y * h)),
            (int(p2.x * w), int(p2.y * h))
        )

    def _ear(self, landmarks, w, h):
        def ratio(idx):
            lm = landmarks
            return (
                (self._euclidean(lm[idx[1]], lm[idx[5]], w, h) +
                 self._euclidean(lm[idx[2]], lm[idx[4]], w, h)) /
                (2.0 * self._euclidean(lm[idx[0]], lm[idx[3]], w, h) + 1e-6)
            )
        return (ratio(LEFT_EYE) + ratio(RIGHT_EYE)) / 2.0

    # ── Drowsiness ────────────────────────────────────────────────────────────
    def detect_drowsiness(self, frame):
        h, w = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._face_detector.detect(mp_img)
        drowsy = False

        if result.face_landmarks:
            lm = result.face_landmarks[0]

            # Validate full face in frame
            self._face_valid = self._is_face_valid(lm, w, h)

            if self._face_valid:
                ear = self._ear(lm, w, h)

                if ear < self.EAR_THRESHOLD:
                    self._drown_counter += 1
                    if self._drown_counter >= self.EAR_FRAME_LIMIT:
                        drowsy = True
                        cv2.putText(frame, "DROWSINESS ALERT",
                                    (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                    1, (0, 0, 255), 3)
                else:
                    self._drown_counter = 0

                # Draw face status
                cv2.putText(frame, f"EAR:{ear:.2f} Face:OK",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 1)
            else:
                self._drown_counter = 0
                cv2.putText(frame, "Face not fully visible",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 165, 255), 1)
        else:
            self._face_valid = False
            self._drown_counter = 0
            cv2.putText(frame, "No face detected",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 0, 255), 1)

        return frame, drowsy

    # ── Distraction ───────────────────────────────────────────────────────────
    def detect_distraction(self, frame):
        """Detect head turn — works even if face partially visible."""
        distracted = False
        h, w = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._face_detector.detect(mp_img)

        if result.face_landmarks:
            lm        = result.face_landmarks[0]
            nose      = lm[1]
            left_eye  = lm[33]
            right_eye = lm[263]

            eye_width = abs(right_eye.x - left_eye.x)

            # If eyes too close together (partial face) skip
            if eye_width < 0.05:
                self._distract_counter = 0
                return frame, False

            ratio = (nose.x - left_eye.x) / (right_eye.x - left_eye.x + 1e-6)

            if ratio < self.HEAD_THRESHOLD or ratio > (1 - self.HEAD_THRESHOLD):
                self._distract_counter += 1
                if self._distract_counter >= self.DISTRACT_FRAME_LIMIT:
                    distracted = True
                    cv2.putText(frame, "DISTRACTION ALERT!",
                                (30, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                1, (0, 165, 255), 2)
            else:
                self._distract_counter = 0
        else:
            self._distract_counter = 0

        return frame, distracted

    # ── Mobile phone ──────────────────────────────────────────────────────────
    def detect_mobile(self, frame):
        # Run YOLO every YOLO_SKIP_FRAMES
        self._yolo_skip += 1
        if self._yolo_skip >= self.YOLO_SKIP_FRAMES:
            self._yolo_skip = 0
            phone_found = False
            results = self._yolo(
                frame, verbose=False,
                conf=self.PHONE_CONF,
                classes=[self.PHONE_CLASS_ID]
            )
            for r in results:
                for box in r.boxes:
                    if int(box.cls[0]) == self.PHONE_CLASS_ID:
                        phone_found = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                        cv2.putText(frame, f"Phone {conf:.0%}",
                                    (x1, max(y1 - 8, 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 165, 255), 2)
            self._last_phone_det = phone_found

        # Update stability counter
        if self._last_phone_det:
            self._phone_frames += 1
        else:
            self._phone_frames = max(0, self._phone_frames - 1)

        if self._phone_frames >= self.PHONE_REQ_FRAMES:
            cv2.putText(frame, "!! MOBILE PHONE USAGE !!",
                        (30, 150), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 0, 255), 3)
            if self._phone_frames == self.PHONE_REQ_FRAMES:
                return frame, True

        return frame, False
