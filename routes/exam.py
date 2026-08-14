from flask import render_template, redirect, url_for, session, flash
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
    return render_template(
        "dashboard.html",
        name=session["name"],
        datetime=datetime,
        candidate_id=candidate_id,
        latest_session=latest,
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
    generate_report_xlsx(session_id)
    generate_report_pdf(session_id)
    session.pop("active_session_id", None)
    return redirect(url_for("summary", session_id=session_id))