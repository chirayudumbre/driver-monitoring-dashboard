# utils/helpers.py
import cv2
import os
from datetime import datetime

def save_snapshot(frame, alert_type):
    folder = "data/snapshots"
    os.makedirs(folder, exist_ok=True)
    filename = f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    path = os.path.join(folder, filename)
    cv2.imwrite(path, frame)
    return path
