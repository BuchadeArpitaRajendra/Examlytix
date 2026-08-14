from flask import redirect, url_for, session
import os
import base64
from datetime import datetime

from config import PHOTO_FOLDER

def login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("candidate_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped

def admin_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped

def save_screenshot(candidate_id, image_data, event_type):
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    candidate_folder = os.path.join(
        PHOTO_FOLDER,
        f"Candidate_{candidate_id}"
    )
    os.makedirs(candidate_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    filename = f"{event_type}_{timestamp}.jpg"
    file_path = os.path.join(candidate_folder, filename)
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(image_data))
    return file_path.replace("\\", "/")