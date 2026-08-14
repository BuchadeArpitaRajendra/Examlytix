import os
import csv
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)

import database
from config import EXPORT_FOLDER

# PDF Report Generation
def generate_report_pdf(session_id):
    db_session = database.get_session(session_id)
    events = database.get_events_for_session(session_id)
    candidate = database.get_candidate_by_id(db_session["candidate_id"])
    filename = f"session_{session_id}_report.pdf"
    path = os.path.join(EXPORT_FOLDER, filename)
    doc = SimpleDocTemplate(path)
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = TA_CENTER
    elements = []
    elements.append(Paragraph("VigilProctor - Exam Monitoring Report", title_style))
    elements.append(Spacer(1, 15))
    # Candidate Summary
    start_time = datetime.fromisoformat(db_session["start_time"])
    end_time = datetime.fromisoformat(db_session["end_time"])
    duration = end_time - start_time
    minutes, seconds = divmod(int(duration.total_seconds()), 60)
    candidate_data = [
        ["Candidate ID", db_session["candidate_id"]],
        ["Candidate Name", candidate["name"] if candidate else ""],
        ["Mail ID", candidate["email"] if candidate else ""],
        ["Exam Subject", candidate["exam_subject"] if candidate else ""],
        ["Session Start Time", start_time.strftime("%d %B %Y, %I:%M:%S %p")],
        ["Session End Time", end_time.strftime("%d %B %Y, %I:%M:%S %p")],
        ["Session Duration", f"{minutes} minutes, {seconds} seconds"],
        ["Integrity Score", f"{db_session['integrity_score']} / 100"],
        ["Face Absence Duration", f"{db_session['total_absence_duration'] or 0} seconds"],
        ["Tab Switches Count", db_session["total_tab_switches"]],
    ]
    candidate_table = Table(candidate_data, colWidths=[150, 300])
    candidate_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elements.append(candidate_table)
    elements.append(Spacer(1, 20))
    # Event Log
    event_rows = [["#", "Date", "Time", "Event", "Remarks"]]
    for i, e in enumerate(events, start=1):
        ts = datetime.fromisoformat(str(e["timestamp"]))
        date_str = ts.strftime("%d %B %Y")
        time_str = ts.strftime("%I:%M:%S %p")
        event_rows.append([
            i,
            date_str,
            time_str,
            e["event_type"],
            e["remarks"]
        ])
    event_table = Table(
        event_rows,
        colWidths=[30, 75, 70, 130, 220],
        repeatRows=1
    )
    event_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    title_style = styles["Heading2"]
    title_style.alignment = TA_CENTER
    elements.append(Paragraph("Event Logs", title_style))
    elements.append(Spacer(1, 5))
    elements.append(event_table)
    elements.append(Spacer(1, 20))
    evidence_events = [e for e in events if e["screenshot_path"]]
    if evidence_events:
        elements.append(Paragraph("Suspicious Events", title_style))
        elements.append(Spacer(1, 5))
    for i, e in enumerate(evidence_events, start=1):
        ts = datetime.fromisoformat(str(e["timestamp"]))
        elements.append(
            Paragraph(
                f"<b>Evidence {i}: {e['event_type']}</b><br/>"
                f"Time: {ts.strftime('%d %b %Y, %I:%M:%S %p')}<br/>"
                f"{e['remarks']}",
                styles["BodyText"]
            )
        )
        if os.path.exists(e["screenshot_path"]):
            img = Image(e["screenshot_path"], width=250, height=180)
            elements.append(img)
        elements.append(Spacer(1, 5))
    doc.build(elements)
    return path

# CSV Report Generation
def generate_report_xlsx(session_id):
    """Generate CSV report (formerly Excel report)"""
    db_session = database.get_session(session_id)
    events = database.get_events_for_session(session_id)
    candidate = database.get_candidate_by_id(db_session["candidate_id"])
    filename = f"session_{session_id}_report.csv"
    path = os.path.join(EXPORT_FOLDER, filename)
    
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow(["VigilProctor - Exam Monitoring Report"])
        writer.writerow([])
        
        # Candidate Summary
        writer.writerow(["CANDIDATE SUMMARY"])
        start_time = datetime.fromisoformat(db_session["start_time"])
        end_time = datetime.fromisoformat(db_session["end_time"])
        duration = end_time - start_time
        minutes, seconds = divmod(int(duration.total_seconds()), 60)
        
        summary_data = [
            ["Candidate ID", db_session["candidate_id"]],
            ["Candidate Name", candidate["name"] if candidate else ""],
            ["Mail ID", candidate["email"] if candidate else ""],
            ["Exam Subject", candidate["exam_subject"] if candidate else ""],
            ["Session Start Time", start_time.strftime("%d %B %Y, %I:%M:%S %p")],
            ["Session End Time", end_time.strftime("%d %B %Y, %I:%M:%S %p")],
            ["Session Duration", f"{minutes} minutes, {seconds} seconds"],
            ["Integrity Score", f"{db_session['integrity_score']} / 100"],
            ["Face Absence Duration", f"{db_session['total_absence_duration'] or 0} seconds"],
            ["Tab Switches Count", db_session["total_tab_switches"]],
        ]
        writer.writerows(summary_data)
        writer.writerow([])
        
        # Event Logs
        writer.writerow(["EVENT LOGS"])
        writer.writerow(["#", "Date", "Time", "Event", "Remarks", "Screenshot Path"])
        for i, e in enumerate(events, start=1):
            ts = datetime.fromisoformat(str(e["timestamp"]))
            writer.writerow([
                i,
                ts.strftime("%d %B %Y"),
                ts.strftime("%I:%M:%S %p"),
                e["event_type"],
                e["remarks"],
                e["screenshot_path"] or "N/A",
            ])
    return path