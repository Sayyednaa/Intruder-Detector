import cv2
import numpy as np

_hog = cv2.HOGDescriptor()
_hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

_prev_frames = {}  # token -> gray frame

def detect_motion(token: str, frame_bgr, sensitivity=0.15):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    prev = _prev_frames.get(token)
    _prev_frames[token] = gray
    if prev is None:
        return 0.0, None
    diff = cv2.absdiff(prev, gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    motion_score = (np.sum(thresh > 0) / thresh.size)
    return float(motion_score), thresh

def detect_person(frame_bgr):
    rects, weights = _hog.detectMultiScale(frame_bgr, winStride=(8,8))
    if len(rects) == 0:
        return False, 0.0
    return True, float(max(weights) if len(weights) else 0.0)
