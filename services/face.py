import cv2

from config import CASCADE_PATH

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise RuntimeError("Could Not Load Haar Cascade XML File")

def detect_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # gray = cv2.equalizeHist(gray)
    # gray = cv2.GaussianBlur(gray, (3, 3), 0)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor = 1.08,
        minNeighbors = 5,
        minSize = (75, 75),
    )
    return faces