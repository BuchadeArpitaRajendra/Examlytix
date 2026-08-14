import os
import base64
import cv2
import numpy as np

from config import PHOTO_FOLDER

def decode_data_url_image(data_url):
    if "," in data_url:
        header, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    binary = base64.b64decode(encoded)
    arr = np.frombuffer(binary, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame

def save_photo(candidate_id, frame):
    filename = f"{candidate_id}.jpg"
    path = os.path.join(PHOTO_FOLDER, filename)
    cv2.imwrite(path, frame)
    return os.path.join("photos", filename)