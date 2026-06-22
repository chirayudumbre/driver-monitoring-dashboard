"""
pi/pi_detection.py — Raspberry Pi 5
Optimised detection with live EAR/ratio feedback for tuning.
"""

import cv2, math, os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

LEFT_EYE  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


class PiDetector:
    # ── Tunable thresholds ────────────────────────────────────────────────────
    # Calibrated from live data:
    # Eyes open EAR: 0.24-0.33  Eyes closed: 0.11-0.17
    # Head straight HEAD: 0.50-0.62  Head turned: <0.35 or >0.70
    EAR_THRESHOLD        = 0.20
    EAR_FRAME_LIMIT      = 2     # only 2 frames = ~0.13s
    HEAD_THRESHOLD       = 0.38
    HEAD_THRESHOLD_HIGH  = 0.72
    DISTRACT_FRAME_LIMIT = 2     # only 2 frames
    PHONE_CLASS_ID       = 67
    PHONE_CONF           = 0.20
    PHONE_REQ_FRAMES     = 2     # only 2 frames
    YOLO_SKIP_FRAMES     = 1     # every frame

    def __init__(self, base_dir: str):
        model_path = os.path.join(base_dir, "models", "face_landmarker.task")
        base_opts  = mp_python.BaseOptions(
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
        self._det = vision.FaceLandmarker.create_from_options(opts)

        from ultralytics import YOLO
        yolo_s = os.path.join(base_dir, "models", "yolov8s.pt")
        yolo_n = os.path.join(base_dir, "models", "yolov8n.pt")
        yolo_path = yolo_s if os.path.exists(yolo_s) else yolo_n
        self._yolo = YOLO(yolo_path)
        print(f"[AI]  YOLO: {os.path.basename(yolo_path)}")

        self._drown_ctr   = 0
        self._dist_ctr    = 0
        self._phone_ctr   = 0
        self._yolo_skip   = 0
        self._last_phone  = False

    @staticmethod
    def _dist(p1, p2, w, h):
        return math.dist((p1.x*w, p1.y*h), (p2.x*w, p2.y*h))

    def _ear(self, lm, w, h):
        def r(idx):
            return ((self._dist(lm[idx[1]], lm[idx[5]], w, h) +
                     self._dist(lm[idx[2]], lm[idx[4]], w, h)) /
                    (2.0 * self._dist(lm[idx[0]], lm[idx[3]], w, h) + 1e-6))
        return (r(LEFT_EYE) + r(RIGHT_EYE)) / 2.0

    def _get_face(self, frame):
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._det.detect(mp_img)
        if result.face_landmarks:
            return result.face_landmarks[0]
        return None

    # ── Drowsiness ────────────────────────────────────────────────────────────
    def detect_drowsiness(self, frame):
        h, w   = frame.shape[:2]
        lm     = self._get_face(frame)
        drowsy = False

        if lm:
            ear = self._ear(lm, w, h)
            print(f"\r[EAR]={ear:.3f} thr={self.EAR_THRESHOLD} ctr={self._drown_ctr}  ", end="", flush=True)

            if ear < self.EAR_THRESHOLD:
                self._drown_ctr += 1
                if self._drown_ctr >= self.EAR_FRAME_LIMIT:
                    drowsy = True
                    print()
                    cv2.putText(frame, "DROWSINESS ALERT",
                                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
            else:
                self._drown_ctr = 0

            cv2.putText(frame, f"EAR:{ear:.2f}", (10,25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 1)
        else:
            self._drown_ctr = 0
            cv2.putText(frame, "No face", (10,25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,255), 1)

        return frame, drowsy

    # ── Distraction ───────────────────────────────────────────────────────────
    def detect_distraction(self, frame):
        h, w       = frame.shape[:2]
        lm         = self._get_face(frame)
        distracted = False

        if lm:
            nose  = lm[1];  le = lm[33];  re = lm[263]
            ew    = abs(re.x - le.x)
            if ew < 0.04:                  # partial face — skip
                self._dist_ctr = 0
                return frame, False

            ratio = (nose.x - le.x) / (re.x - le.x + 1e-6)

            if ratio < self.HEAD_THRESHOLD or ratio > self.HEAD_THRESHOLD_HIGH:
                self._dist_ctr += 1
                if self._dist_ctr >= self.DISTRACT_FRAME_LIMIT:
                    distracted = True
                    print()
                    cv2.putText(frame, "DISTRACTION ALERT",
                                (20,100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,165,255), 3)
            else:
                self._dist_ctr = 0

            cv2.putText(frame, f"HEAD:{ratio:.2f}", (10,45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,200,0), 1)
        else:
            self._dist_ctr = 0

        return frame, distracted

    # ── Phone ─────────────────────────────────────────────────────────────────
    def detect_mobile(self, frame):
        self._yolo_skip += 1
        if self._yolo_skip >= self.YOLO_SKIP_FRAMES:
            self._yolo_skip   = 0
            phone_found = False
            res = self._yolo(frame, verbose=False,
                             conf=self.PHONE_CONF, classes=[self.PHONE_CLASS_ID])
            for r in res:
                for box in r.boxes:
                    if int(box.cls[0]) == self.PHONE_CLASS_ID:
                        phone_found = True
                        x1,y1,x2,y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,165,255), 2)
                        cv2.putText(frame, f"Phone {conf:.0%}",
                                    (x1, max(y1-8,10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,165,255), 2)
            self._last_phone = phone_found

        if self._last_phone:
            self._phone_ctr += 1
        else:
            self._phone_ctr = max(0, self._phone_ctr - 1)

        if self._phone_ctr >= self.PHONE_REQ_FRAMES:
            cv2.putText(frame, "!! MOBILE PHONE !!",
                        (20,150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
            if self._phone_ctr == self.PHONE_REQ_FRAMES:
                return frame, True

        return frame, False
