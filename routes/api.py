from flask import request, session, jsonify
import time

from app import app
import database
from utils import *
from services.face import detect_faces
from services.image import decode_data_url_image

@app.route("/api/detect_face", methods=["POST"])
@login_required
def api_detect_face():
    session_id = session.get("active_session_id")
    db_session = database.get_session(session_id) if session_id else None
    face_boxes = []
    if db_session is None:
        return jsonify({
            "error": "No Active Exam Session"
        }), 400
    payload = request.get_json(silent=True) or {}
    image_data = payload.get("image")
    if not image_data:
        return jsonify({""
        "error": "No Image Provided"
    }), 400
    try:
        frame = decode_data_url_image(image_data)
    except Exception:
        return jsonify({
            "error": "Could Not Decode Image"
        }), 400
    if frame is None:
        return jsonify({
            "error": "Could Not Decode Image"
        }), 400
    state = database.get_monitor_state(session_id)
    total_absence = state["total_absence_duration"]
    absence_start = state["current_absence_start"]
    tab_switches = state["total_tab_switches"]
    face_present = bool(state["face_present"])
    face_missing_logged = bool(state["face_missing_logged"])
    prolonged_logged = bool(state["prolonged_logged"])
    if db_session["status"] != "Running":
        database.update_monitor_state(
            session_id,
            total_absence,
            absence_start,
            tab_switches,
            face_present,
            face_missing_logged,
            prolonged_logged
        )
        return jsonify({
            "face_detected": True,
            "face_boxes": face_boxes,
            "absence_duration": 0,
            "total_absence_duration": total_absence,
            "tab_switches": tab_switches,
            "status": db_session["status"],
        })
    faces = detect_faces(frame)
    face_count = len(faces)
    face_boxes = [
        {
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h)
        }
        for (x, y, w, h) in faces
    ]
    candidate_id = session["candidate_id"]
    absence_duration = 0
    if face_count == 1:
        face_present = True
        if absence_start is not None:
            total_absence += int(time.time() - absence_start)
            database.log_event(
                candidate_id, session_id, "Face Detected", "Candidate's Face is Visible"
            )
        absence_start = None
        face_missing_logged = False
        prolonged_logged = False
    else:
        face_present = False
        if absence_start is None:
            absence_start = time.time()
        absence_duration = int(time.time() - absence_start)
        if not face_missing_logged:
            if face_count == 0:
                database.log_event(
                    candidate_id, session_id, "Face Not Detected", "Candidate's Face is Not Visible"
                )
            else:
                database.log_event(
                    candidate_id, session_id, "Face Not Detected", "Multiple  Faces are Visible"
                )
            face_missing_logged = True
        if absence_duration >= 5 and not prolonged_logged:
            screenshot_path = save_screenshot(
                candidate_id, image_data, "face_missing"
            )
            database.log_event(
                candidate_id, session_id, "Face Not Detected", "Face Detection Violation for Over 5s", screenshot_path
            )
            prolonged_logged = True
    database.update_monitor_state(
        session_id,
        total_absence,
        absence_start,
        tab_switches,
        face_present,
        face_missing_logged,
        prolonged_logged
    )
    return jsonify({
        "face_detected": face_count == 1,
        "face_boxes": face_boxes,
        "absence_duration": absence_duration,
        "total_absence_duration": total_absence,
        "tab_switches": tab_switches,
        "status": db_session["status"],
    })

@app.route("/api/log_event", methods=["POST"])
@login_required
def api_log_event():
    session_id = session.get("active_session_id")
    if not session_id:
        return jsonify({
            "error": "No Active Exam Session"
        }), 400
    payload = request.get_json(silent=True) or {}
    event_type = payload.get("event_type", "Unknown Event")
    remarks = payload.get("remarks", "")
    image_data = payload.get("image")
    state = database.get_monitor_state(session_id)
    if event_type == "Tab Switched":
        database.increment_tab_switch(session_id)
        state = database.get_monitor_state(session_id)
    screenshot_path = None
    if event_type == "Tab Switched" and image_data:
        screenshot_path = save_screenshot(
            session["candidate_id"],
            image_data,
            "browser_focus_lost"
        )
    database.log_event(
        session["candidate_id"], session_id, event_type, remarks, screenshot_path
    )
    return jsonify({
        "success": True,
        "tab_switches": state["total_tab_switches"]
    })

@app.route("/api/integrity_score")
@login_required
def get_integrity_score():
    session_id = session.get("active_session_id")
    if not session_id:
        return jsonify({
            "error": "No Active Exam Session"
        }), 400
    db_session = database.get_session(session_id)
    if not db_session:
        return {
            "error": "Session Not Found"
        }, 404
    return {
        "integrity_score": db_session["integrity_score"]
    }

@app.route("/api/session_state")
@login_required
def api_session_state():
    session_id = session.get("active_session_id")
    state = database.get_session_summary(session_id)
    return jsonify({
        "status": state["status"],
        "total_absence_duration": state["total_absence_duration"],
        "tab_switches": state["total_tab_switches"],
    })

@app.route("/api/events")
@login_required
def api_events():
    session_id = session.get("active_session_id")
    if not session_id:
        return jsonify([])
    events = database.get_events_for_session(session_id)
    return jsonify(
        [dict(event) for event in events]
    )