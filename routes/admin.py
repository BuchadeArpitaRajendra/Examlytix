from flask import render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import re

from app import app
import database
from utils import *
from config import ADMIN_EMAIL, ADMIN_PASSWORD

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    if email == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        session["is_admin"] = True
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html", message="Invalid Credentials, Please Try Again")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    candidate_filter = request.args.get("candidate_id", "").strip()
    event_filter = request.args.get("event_type", "").strip()
    date_filter = request.args.get("date", "").strip()
    candidates = database.get_all_candidates()
    sessions = database.get_all_sessions()
    events = database.get_all_events()
    
    # Convert to dict for JSON serialization
    candidates_dict = [dict(c) for c in candidates]
    sessions_dict = [dict(s) for s in sessions]
    events_dict = [dict(e) for e in events]
    
    integrity_scores = [
        s["integrity_score"]
        for s in sessions
        if s["integrity_score"] is not None
    ]
    
    analytics = {
        "total_candidates": len(candidates),
        "total_sessions": len(sessions),
        "total_logs": len(events),
        "face_absence_events": sum(
            1 for e in events
            if e["event_type"] == "Face Not Detected"
        ),
        "face_detected_events": sum(
            1 for e in events
            if e["event_type"] == "Face Detected"
        ),
        "browser_focus_loss_events": sum(
            1 for e in events
            if e["event_type"] == "Tab Switched"
        ),
        "browser_focus_return_events": sum(
            1 for e in events
            if e["event_type"] == "Tab Returned"
        ),
        "exam_started": sum(
            1 for e in events
            if e["event_type"] == "Exam Started"
        ),
        "exam_completed": sum(
            1 for s in sessions
            if s["status"] == "Completed"
        ),
        "running_sessions": sum(
            1 for s in sessions
            if s["status"] == "Running"
        ),
        "paused_sessions": sum(
            1 for s in sessions
            if s["status"] == "Paused"
        ),
        "screenshots_captured": sum(
            1 for e in events
            if e["screenshot_path"]
        ),
        "highest_integrity_score": max(integrity_scores, default=0),
        "lowest_integrity_score": min(integrity_scores, default=0),
        "average_integrity_score": (
            round(sum(integrity_scores) / len(integrity_scores), 2)
            if integrity_scores else 0
        ),
    }
    
    # Get risk distribution for pie chart
    risk_distribution = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0
    }
    
    # Get students by risk category
    students_by_risk = {
        "Low": [],
        "Medium": [],
        "High": [],
        "Critical": []
    }
    
    # Get latest session for each candidate
    for candidate in candidates:
        latest_session = database.get_latest_session(candidate["candidate_id"])
        if latest_session and latest_session["integrity_score"] is not None:
            score = latest_session["integrity_score"]
            # Determine risk category
            if score >= 90:
                risk_category = "Low"
            elif score >= 75:
                risk_category = "Medium"
            elif score >= 50:
                risk_category = "High"
            else:
                risk_category = "Critical"
            
            risk_distribution[risk_category] += 1
            students_by_risk[risk_category].append({
                "candidate_id": candidate["candidate_id"],
                "name": candidate["name"],
                "email": candidate["email"],
                "integrity_score": score,
                "risk_category": risk_category,
                "session_id": latest_session["session_id"]
            })
    
    analytics["risk_distribution"] = risk_distribution
    analytics["students_by_risk"] = students_by_risk
    
    analytics["event_distribution"] = {
        "Face Not Detected": analytics["face_absence_events"],
        "Face Detected": analytics["face_detected_events"],
        "Tab Switched": analytics["browser_focus_loss_events"],
        "Tab Returned": analytics["browser_focus_return_events"],
        "Exam Paused": sum(
            1 for e in events if e["event_type"] == "Exam Paused"
        ),
        "Exam Resumed": sum(
            1 for e in events if e["event_type"] == "Exam Resumed"
        ),
        "Exam Started": analytics["exam_started"],
        "Exam Ended": sum(
            1 for e in events if e["event_type"] == "Exam Ended"
        ),
    }
    analytics["session_status"] = {
        "Completed": analytics["exam_completed"],
        "Running": analytics["running_sessions"],
        "Paused": analytics["paused_sessions"],
    }
    analytics["integrity_distribution"] = {
        "0-49": sum(1 for s in integrity_scores if s < 50),
        "50-69": sum(1 for s in integrity_scores if 50 <= s < 70),
        "70-84": sum(1 for s in integrity_scores if 70 <= s < 85),
        "85-100": sum(1 for s in integrity_scores if s >= 85),
    }
    
    if candidate_filter:
        candidate_filter = candidate_filter.upper()
        events = [
            e for e in events
            if candidate_filter in str(e["candidate_id"]).upper()
        ]
        # Also convert filtered events to dict
        events_dict = [dict(e) for e in events]
    else:
        events_dict = events_dict
    
    if event_filter:
        events = [
            e for e in events
            if e["event_type"] == event_filter
        ]
        events_dict = [dict(e) for e in events]
    
    if date_filter:
        events = [
            e for e in events
            if str(e["timestamp"]).startswith(date_filter)
        ]
        events_dict = [dict(e) for e in events]
    
    event_types = [
        "Face Not Detected",
        "Face Detected",
        "Tab Switched",
        "Tab Returned",
        "Exam Paused",
        "Exam Resumed",
        "Exam Started",
        "Exam Ended",
    ]
    
    return render_template(
        "admin.html",
        datetime=datetime,
        candidates=candidates_dict,
        sessions=sessions_dict,
        events=events_dict,
        analytics=analytics,
        event_types=event_types,
    )

@app.route("/admin/api/candidates/<candidate_id>", methods=["PUT", "DELETE"])
@admin_required
def admin_api_candidate(candidate_id):
    if request.method == "DELETE":
        ok = database.delete_candidate(candidate_id)
        return jsonify({"success": ok})
    data = request.get_json(silent=True) or {}
    errors = []
    email = data.get("email", "").strip()
    if email and re.match(r"[^@]+@[^@]+\.[^@]+", email) is None:
        errors.append("Invalid Mail Format")
    age = data.get("age", "")
    if age not in (None, "") and not str(age).isdigit():
        errors.append("Age Must be a Number")
    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400
    fields = {
        "name": data.get("name", "").strip(),
        "email": email,
        "exam_subject": data.get("exam_subject", "").strip(),
        "age": int(age),
    }
    if data.get("password"):
        fields["password"] = data["password"]
    ok = database.update_candidate_fields(candidate_id, fields)
    return jsonify({
        "success": ok
    })

@app.route("/admin/api/sessions/<int:session_id>", methods=["PUT", "DELETE"])
@admin_required
def admin_api_session(session_id):
    if request.method == "DELETE":
        ok = database.delete_session(session_id)
        return jsonify({
            "success": ok
        })
    data = request.get_json(silent=True) or {}
    fields = {
        "status": data.get("status"),
        "total_absence_duration": int(data["total_absence_duration"]) if str(data.get("total_absence_duration", "")).isdigit() else None,
        "total_tab_switches": int(data["total_tab_switches"]) if str(data.get("total_tab_switches", "")).isdigit() else None,
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    ok = database.update_session_fields(session_id, fields)
    return jsonify({
        "success": ok
    })

@app.route("/admin/api/events/<int:event_id>", methods=["PUT", "DELETE"])
@admin_required
def admin_api_event(event_id):
    if request.method == "DELETE":
        ok = database.delete_event(event_id)
        return jsonify({
            "success": ok
        })
    data = request.get_json(silent=True) or {}
    fields = {
        "event_type": data.get("event_type", "").strip(),
        "remarks": data.get("remarks", "").strip(),
    }
    ok = database.update_event_fields(event_id, fields)
    return jsonify({
        "success": ok
    })