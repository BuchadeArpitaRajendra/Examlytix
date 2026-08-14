(function () {
  const video = document.getElementById("video");
  const canvas = document.getElementById("capturedCanvas");
  const statusChip = document.getElementById("statusChip");
  const statusText = document.getElementById("statusText");
  const captureBtn = document.getElementById("captureBtn");
  const retakeBtn = document.getElementById("retakeBtn");
  const submitBtn = document.getElementById("submitBtn");
  const camHint = document.getElementById("camHint");
  const errorBox = document.getElementById("errorBox");
  const form = document.getElementById("registerForm");

  let stream = null;
  let photoDataUrl = null;

  function setStatus(text, warn) {
    statusText.textContent = text;
    statusChip.classList.toggle("warn", !!warn);
  }

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: 640,
          height: 480
        },
        audio: false
      });
      video.srcObject = stream;
      setStatus("Camera Live");
      camHint.innerHTML = "Center your Face in the Frame, then Click <strong>Capture Photo</strong>. This becomes your Identity Record for the Exam Session.";
    } catch (err) {
      setStatus("Camera Unavailable", true);
      camHint.innerHTML = "Could not Access your Web Camera. Please <strong>Allow Camera Permission</strong> in the Browser and Reload this Page.";
      captureBtn.disabled = true;
    }
  }

  function capturePhoto() {
    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    photoDataUrl = canvas.toDataURL("image/jpeg", 0.92);
    video.style.display = "none";
    canvas.style.display = "block";
    captureBtn.style.display = "none";
    retakeBtn.style.display = "inline-flex";
    submitBtn.disabled = false;
    setStatus("Photo Captured");
  }

  function retake() {
    video.style.display = "block";
    canvas.style.display = "none";
    captureBtn.style.display = "inline-flex";
    retakeBtn.style.display = "none";
    submitBtn.disabled = true;
    photoDataUrl = null;
    setStatus("Camera Live");
  }

  function showErrors(errors) {
    errorBox.innerHTML = "";
    const div = document.createElement("div");
    div.className = "alert alert-error";
    div.innerHTML = errors.map(e => `${e}`).join("<br>");
    errorBox.appendChild(div);
  }

  captureBtn.addEventListener("click", capturePhoto);
  retakeBtn.addEventListener("click", retake);

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const email = document.getElementById("email").value.trim();
    const emailRegex = /^[\w.-]+@[\w.-]+\.\w+$/;
    if (!emailRegex.test(email)) {
      showErrors(["Enter a Valid Mail ID"]);
      return;
    }
    if (!photoDataUrl) {
      showErrors(["Please Capture a Photo before Submitting"]);
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting…";
    const payload = {
      candidate_id: document.getElementById("candidate_id").value.trim(),
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim(),
      age: document.getElementById("age").value.trim(),
      exam_subject: document.getElementById("exam_subject").value,
      exam_date: document.getElementById("exam_date").value,
      exam_time: document.getElementById("exam_time").value,
      password: document.getElementById("password").value,
      photo_data: photoDataUrl,
    };
    console.log(payload);
    try {
      const res = await fetch(form.action || window.location.pathname, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        errorBox.innerHTML = '<div class="alert alert-info">Registration Complete. Redirecting to Sign In...</div>';
        setTimeout(() => { window.location.href = data.redirect; }, 900);
      } else {
        showErrors(data.errors || ["Something Went Wrong, Please Try Again"]);
        submitBtn.disabled = false;
        submitBtn.textContent = "Complete Registration";
      }
    } catch (err) {
      showErrors(["Network Error, Please Try Again"]);
      submitBtn.disabled = false;
      submitBtn.textContent = "Complete Registration";
    }
  });

  window.addEventListener("DOMContentLoaded", () => {
    const now = new Date();
    document.getElementById("exam_date").value = now.toISOString().split("T")[0];
    now.setHours(now.getHours() + 1);
    now.setMinutes(0);
    now.setSeconds(0);
    now.setMilliseconds(0);
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    document.getElementById("exam_time").value = `${hours}:${minutes}`;
  });

  startCamera();
})();
