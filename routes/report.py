import os
from flask import render_template, redirect, url_for, session, send_from_directory, send_file, abort
from datetime import datetime

from app import app
import database
from utils import *
from config import EXPORT_FOLDER

@app.route("/summary/<int:session_id>")
@login_required
def summary(session_id):
    db_session = database.get_session(session_id)
    if db_session is None or db_session["candidate_id"] != session["candidate_id"]:
        return redirect(url_for("dashboard"))
    events = database.get_events_for_session(session_id)
    start_time = datetime.fromisoformat(db_session["start_time"])
    end_time = datetime.fromisoformat(db_session["end_time"])
    formatted_start = start_time.strftime("%d %b %Y, %I:%M:%S %p")
    formatted_end = end_time.strftime("%d %b %Y, %I:%M:%S %p")
    duration = end_time - start_time
    minutes, seconds = divmod(int(duration.total_seconds()), 60)
    exam_duration = f"{minutes} minutes, {seconds} seconds"
    xlsx_filename = f"session_{session_id}_report.xlsx"
    pdf_filename = f"session_{session_id}_report.pdf"
    return render_template(
        "summary.html",
        name=session["name"],
        db_session=db_session,
        datetime=datetime,
        formatted_start=formatted_start,
        formatted_end=formatted_end,
        exam_duration=exam_duration,
        events=events,
        xlsx_filename=xlsx_filename,
        pdf_filename=pdf_filename,
    )

@app.route("/evidence/<int:event_id>")
@login_required
def evidence(event_id):
    event = database.get_event(event_id)
    if event is None:
        abort(404)
    if event["candidate_id"] != session["candidate_id"]:
        abort(403)
    if not event["screenshot_path"]:
        abort(404)
    return send_file(event["screenshot_path"])

@app.route("/download_xlsx/<path:filename>")
@login_required
def download_xlsx(filename):
    # Support both CSV and XLSX files
    csv_filename = filename.replace('.xlsx', '.csv')
    if os.path.exists(os.path.join(EXPORT_FOLDER, csv_filename)):
        return send_from_directory(EXPORT_FOLDER, csv_filename, as_attachment=True)
    return send_from_directory(EXPORT_FOLDER, filename, as_attachment=True)

@app.route("/download_pdf/<path:filename>")
@login_required
def download_pdf(filename):
    return send_from_directory(EXPORT_FOLDER, filename, as_attachment=True)