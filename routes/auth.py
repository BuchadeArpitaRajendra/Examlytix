from flask import render_template, request, redirect, url_for, session, jsonify

from app import app
import database
from utils import *
from services.face import detect_faces
from services.image import decode_data_url_image, save_photo
from services.report import generate_report_pdf, generate_report_xlsx

@app.route("/")
def home():
    if "candidate_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = request.get_json(silent=True) or request.form
    candidate_id = data.get("candidate_id").strip()
    name = data.get("name").strip()
    email = data.get("email").strip()
    password = data.get("password").strip()
    age = data.get("age").strip()
    exam_subject = data.get("exam_subject").strip()
    exam_date = data.get("exam_date").strip()
    exam_time = data.get("exam_time").strip()
    photo_data = data.get("photo_data")
    errors = []
    if database.get_candidate_by_id(candidate_id) is not None:
        errors.append("Candidate ID Already Registered")
    if not errors and database.get_candidate_by_email(email) is not None:
        errors.append("Mail ID Already Registered")
    frame = None
    if not errors:
        try:
            frame = decode_data_url_image(photo_data)
            if frame is None:
                errors.append("Could Not Read Captured Photo, Please Try Again")
        except Exception:
            errors.append("Could Not Read Captured Photo, Please Try Again")
    if not errors:
        faces = detect_faces(frame)
        if len(faces) == 0:
            errors.append("No Face Detected in the Captured Photo, Please Try Again")
        if len(faces) > 1:
            errors.append("Multiple Faces Detected in the Captured Photo, Please Try Again")
    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400
    photo_path = save_photo(candidate_id, frame)
    database.create_candidate(
        candidate_id=candidate_id,
        name=name,
        email=email,
        password=password,
        age=int(age),
        exam_subject=exam_subject,
        exam_date=exam_date,
        exam_time=exam_time,
        photo_path=photo_path,
    )
    return jsonify({
        "success": True,
        "redirect": url_for("login")
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    user = database.login(email, password)
    if user:
        session["candidate_id"] = user["candidate_id"]
        session["name"] = user["name"]
        return redirect(url_for("dashboard"))
    return render_template("login.html", message="Invalid Credentials, Please Try Again")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))