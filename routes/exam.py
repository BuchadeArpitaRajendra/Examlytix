from flask import render_template, redirect, url_for, session, flash, Response
from datetime import datetime
import time

from app import app
import database
from utils import *
from services.report import generate_report_pdf, generate_report_xlsx

@app.route("/dashboard")
@login_required
def dashboard():
    candidate_id = session["candidate_id"]
    latest = database.get_latest_session(candidate_id)
    
    # Get all sessions for the candidate - using existing function
    # Since get_sessions_by_candidate might not exist, let's use a different approach
    all_sessions = []
    if latest:
        # Get all sessions by querying directly
        con = database.get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT *
            FROM session
            WHERE candidate_id=?
            ORDER BY session_id DESC
        """, (candidate_id,))
        all_sessions = cur.fetchall()
        con.close()
    
    # Get recent events for the latest session - SHOW ONLY LAST 5
    recent_events = []
    if latest:
        recent_events = database.get_events_for_session(latest["session_id"])
        # Get only last 5 events
        recent_events = recent_events[-5:] if len(recent_events) > 5 else recent_events
        # Reverse to show newest first
        recent_events = list(reversed(recent_events))
    
    # Calculate face presence ratio
    face_presence_ratio = 100
    if recent_events:
        face_detected = sum(1 for e in recent_events if e["event_type"] == "Face Detected")
        face_not_detected = sum(1 for e in recent_events if e["event_type"] == "Face Not Detected")
        total_face_events = face_detected + face_not_detected
        if total_face_events > 0:
            face_presence_ratio = round((face_detected / total_face_events) * 100)
    
    # Get events logged count
    events_logged = 0
    if latest:
        events_logged = len(database.get_events_for_session(latest["session_id"]))
    
    return render_template(
        "dashboard.html",
        name=session["name"],
        datetime=datetime,
        candidate_id=candidate_id,
        latest_session=latest,
        sessions=all_sessions,
        recent_events=recent_events,
        face_presence_ratio=face_presence_ratio,
        events_logged=events_logged,
    )

@app.route("/start_exam")
@login_required
def start_exam():
    candidate_id = session["candidate_id"]
    latest = database.get_latest_session(candidate_id)
    if latest and latest["status"] in ("Running", "Paused"):
        session["active_session_id"] = latest["session_id"]
        return redirect(url_for("exam"))
    session_id = database.start_session(candidate_id)
    session["active_session_id"] = session_id
    database.log_event(
        candidate_id, session_id, "Exam Started", "Candidate Started the Exam"
    )
    return redirect(url_for("exam"))

@app.route("/exam")
@login_required
def exam():
    session_id = session.get("active_session_id")
    if not session_id:
        return redirect(url_for("dashboard"))
    db_session = database.get_session(session_id)
    if db_session is None or db_session["status"] != "Running":
        return redirect(url_for("dashboard"))
    return render_template(
        "exam.html",
        name=session["name"],
        candidate_id=session["candidate_id"],
        session_id=session_id,
        status=db_session["status"],
        integrity_score=db_session["integrity_score"],
    )

@app.route("/pause_exam")
@login_required
def pause_exam():
    session_id = session.get("active_session_id")
    db_session = database.get_session(session_id) if session_id else None
    if db_session is None:
        flash("No Session Found, Please Start the Exam First")
        return redirect(url_for("dashboard"))
    if db_session["status"] == "Running":
        state = database.get_monitor_state(session_id)
        total_absence = state["total_absence_duration"]
        absence_start = state["current_absence_start"]
        if absence_start is not None:
            total_absence += int(time.time() - absence_start)
        database.update_monitor_state(
            session_id,
            total_absence,
            None,
            state["total_tab_switches"],
            bool(state["face_present"]),
            bool(state["face_missing_logged"]),
            bool(state["prolonged_logged"])
        )
        database.update_session_status(session_id, "Paused")
        database.log_event(
            session["candidate_id"], session_id, "Exam Paused", "Candidate Paused the Exam"
        )
    return redirect(url_for("dashboard"))

@app.route("/resume_exam")
@login_required
def resume_exam():
    session_id = session.get("active_session_id")
    db_session = database.get_session(session_id) if session_id else None
    if db_session is None:
        flash("No Session Found, Please Start the Exam First")
        return redirect(url_for("dashboard"))
    if db_session["status"] == "Paused":
        print("Updating status to Running")
        database.update_session_status(session_id, "Running")
        database.log_event(
            session["candidate_id"], session_id, "Exam Resumed", "Candidate Resumed the Exam"
        )
    return redirect(url_for("exam"))

@app.route("/end_exam")
@login_required
def end_exam():
    session_id = session.get("active_session_id")
    db_session = database.get_session(session_id) if session_id else None
    if db_session is None:
        flash("No Session Found, Please Start the Exam First")
        return redirect(url_for("dashboard"))
    
    state = database.get_monitor_state(session_id)
    total_absence = state["total_absence_duration"]
    current_absence_start = state["current_absence_start"]
    if current_absence_start is not None:
        total_absence += int(time.time() - current_absence_start)
    
    database.log_event(
        session["candidate_id"], session_id, "Exam Ended", "Exam Completed Successfully"
    )
    database.end_session(session_id, total_absence, state["total_tab_switches"])
    
    # Generate reports
    generate_report_xlsx(session_id)
    generate_report_pdf(session_id)
    
    # Get session data for results modal
    updated_session = database.get_session(session_id)
    events = database.get_events_for_session(session_id)
    
    # Calculate duration
    start_time = datetime.fromisoformat(db_session["start_time"])
    end_time = datetime.fromisoformat(updated_session["end_time"])
    duration_seconds = int((end_time - start_time).total_seconds())
    
    # Get events count
    total_events = len(events)
    
    # Store data in session for results modal
    session["exam_results"] = {
        "integrity_score": updated_session["integrity_score"],
        "tab_switches": updated_session["total_tab_switches"],
        "total_absence_duration": updated_session["total_absence_duration"],
        "total_events": total_events,
        "duration": duration_seconds,
        "session_id": session_id
    }
    
    session.pop("active_session_id", None)
    return redirect(url_for("exam_results"))

@app.route("/exam_results")
@login_required
def exam_results():
    """Show results modal after exam completion"""
    results = session.get("exam_results")
    if not results:
        return redirect(url_for("dashboard"))
    
    # Clear results from session after showing
    session.pop("exam_results", None)
    
    return render_template(
        "exam_results.html",
        name=session["name"],
        results=results
    )

@app.route("/export_data")
@login_required
def export_data():
    """Export all candidate data as CSV"""
    candidate_id = session["candidate_id"]
    candidate = database.get_candidate_by_id(candidate_id)
    sessions = database.get_sessions_by_candidate(candidate_id)
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["VigilProctor - Candidate Data Export"])
    writer.writerow([])
    writer.writerow(["Candidate Information"])
    writer.writerow(["Candidate ID", candidate["candidate_id"]])
    writer.writerow(["Name", candidate["name"]])
    writer.writerow(["Email", candidate["email"]])
    writer.writerow(["Age", candidate["age"]])
    writer.writerow(["Exam Subject", candidate["exam_subject"]])
    writer.writerow([])
    
    writer.writerow(["Session History"])
    writer.writerow(["Session ID", "Status", "Start Time", "End Time", "Integrity Score", "Absence Duration", "Tab Switches"])
    
    for s in sessions:
        writer.writerow([
            s["session_id"],
            s["status"],
            s["start_time"],
            s["end_time"],
            s["integrity_score"],
            s["total_absence_duration"],
            s["total_tab_switches"]
        ])
    
    # Create response
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=candidate_{candidate_id}_data.csv"
    return response