import cv2

def start_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception("Webcam not accessible")
    return cap

def release_camera(cap):
    cap.release()
    cv2.destroyAllWindows()
