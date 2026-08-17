(function () {
  const video = document.getElementById("video");
  const canvas = document.getElementById("captureCanvas");
  const viewfinder = document.getElementById("viewfinder");
  const statusChip = document.getElementById("statusChip");
  const statusText = document.getElementById("statusText");
  const faceBoxes = document.getElementById("faceBoxes");
  const currentAbsenceEl = document.getElementById("currentAbsence");
  const totalAbsenceEl = document.getElementById("totalAbsence");
  const tabSwitchesEl = document.getElementById("tabSwitches");
  const logBody = document.getElementById("logBody");
  const logScroll = document.getElementById("logScroll");

  const DETECT_INTERVAL_MS = 1000;
  let detecting = false;
  let logRows = [];
  let cameraStream = null;
  let detectorTimer = null;
  let examEnding = false;
  let lastFaceDetected = true;
  let lastStatus = window.EXAM_STATUS || 'Running';
  let isWindowFocused = true;
  let isPageVisible = true;

  // =============================================
  // CONFIRM END EXAM
  // =============================================
  window.confirmEndExam = function () {
    const ok = confirm("End the Exam Now? This cannot be Undone.");
    if (!ok) {
      return false;
    }
    examEnding = true;
    setTimeout(() => {
      window.location.href = "/end_exam";
    }, 50);
    return false;
  };

  // =============================================
  // LOG FUNCTIONS
  // =============================================
  function addLogRow(eventType, remarks) {
    const time = new Date().toLocaleTimeString();
    logRows.unshift({ time, eventType, remarks });
    logRows = logRows.slice(0, 40);
    renderLog();
  }

  function tagClassFor(eventType) {
    if (eventType == "Face Not Detected" || eventType == "Tab Switched")
      return "bad";
    if (eventType == "Face Detected" || eventType == "Tab Returned")
      return "warn";
    if (eventType == "Exam Paused" || eventType == "Exam Resumed")
      return "ok";
    return "neutral";
  }

  function renderLog() {
    if (logRows.length === 0) {
      logBody.innerHTML = '<tr><td colspan="2" style="color:var(--muted);">Waiting for events…</td></tr>';
      return;
    }
    logBody.innerHTML = logRows.map(r => `
      <tr>
        <td style="white-space:nowrap;">${r.time}</td>
        <td><span class="tag ${tagClassFor(r.eventType)}">${r.eventType}</span></td>
      </tr>
    `).join("");
  }

  // =============================================
  // CAMERA FUNCTIONS
  // =============================================
  async function startCamera() {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: 640,
          height: 480
        },
        audio: false
      });
      video.srcObject = cameraStream;
      setStatus("Face Detected", false);
      startDetectionLoop();
    } catch (err) {
      setStatus("Camera Unavailable", true);
    }
  }

  function stopCamera() {
    faceBoxes.innerHTML = "";
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
      video.srcObject = null;
    }
  }

  window.stopMonitoring = function () {
    stopCamera();
    if(detectorTimer){
      clearInterval(detectorTimer);
      detectorTimer = null;
    }
    detecting = true;
  };

  function setStatus(text, warn) {
    statusText.textContent = text;
    statusChip.classList.toggle("warn", !!warn);
    viewfinder.classList.toggle("alert-state", !!warn);
    // Update face status text
    const faceStatusEl = document.getElementById('faceStatusText');
    if (faceStatusEl) {
      faceStatusEl.textContent = text;
      faceStatusEl.parentElement.style.color = warn ? 'var(--danger)' : 'var(--success)';
    }
  }

  function captureFrame() {
    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.7);
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  async function fetchIntegrityScore() {
    try {
      const res = await fetch(`/api/integrity_score`);
      if (!res.ok)
        return;
      const data = await res.json();
      const scoreEl = document.getElementById("integrityScore");
      if (scoreEl) {
        scoreEl.textContent = data.integrity_score + "%";
        // Update color based on score
        const score = data.integrity_score;
        if (score >= 90) {
          scoreEl.style.color = 'var(--success)';
        } else if (score >= 70) {
          scoreEl.style.color = 'var(--warning)';
        } else {
          scoreEl.style.color = 'var(--danger)';
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  // =============================================
  // DETECTION LOOP
  // =============================================
  async function detectTick() {
    if (detecting || !video.videoWidth) return;
    detecting = true;
    try {
      const image = captureFrame();
      const data = await postJSON("/api/detect_face", { image });
      if (data.error) {
        detecting = false;
        return;
      }
      lastStatus = data.status;
      if (data.status !== "Running") {
        if (cameraStream) {
          stopCamera();
        }
        faceBoxes.innerHTML = "";
        setStatus(data.status === "Paused" ? "Exam Paused" : "Session Ended", data.status === "Paused");
        currentAbsenceEl.textContent = "0s";
        totalAbsenceEl.textContent = `${data.total_absence_duration}s`;
        tabSwitchesEl.textContent = data.tab_switches;
        detecting = false;
        return;
      }
      if (data.face_detected) {
        if (!lastFaceDetected)
          addLogRow("Face Detected", "Candidate's Face is Visible");
        setStatus("Face Detected", false);
        faceBoxes.innerHTML = "";
        const sx = video.clientWidth / video.videoWidth;
        const sy = video.clientHeight / video.videoHeight;
        if (data.face_boxes) {
          data.face_boxes.forEach(face => {
            const box = document.createElement("div");
            box.className = "face-box";
            box.style.left = `${(video.videoWidth - face.x - face.w) * sx}px`;
            box.style.top = `${face.y * sy}px`;
            box.style.width = `${face.w * sx}px`;
            box.style.height = `${face.h * sy}px`;
            faceBoxes.appendChild(box);
          });
        }
      } else {
        faceBoxes.innerHTML = "";
        const sx = video.clientWidth / video.videoWidth;
        const sy = video.clientHeight / video.videoHeight;
        if (data.face_boxes) {
          data.face_boxes.forEach(face => {
            const box = document.createElement("div");
            box.className = "face-box";
            box.style.left = `${face.x * sx}px`;
            box.style.top = `${face.y * sy}px`;
            box.style.width = `${face.w * sx}px`;
            box.style.height = `${face.h * sy}px`;
            faceBoxes.appendChild(box);
          });
        }
        if (lastFaceDetected)
          addLogRow("Face Not Detected", "Candidate's Face is Not Visible");
        setStatus(`Face Not Detected · ${data.absence_duration}s`, true);
      }
      lastFaceDetected = data.face_detected;
      currentAbsenceEl.textContent = `${data.absence_duration}s`;
      totalAbsenceEl.textContent = `${data.total_absence_duration}s`;
      tabSwitchesEl.textContent = data.tab_switches;
      await fetchIntegrityScore();
    } catch (err) {
      // Network Hiccup
    } finally {
      detecting = false;
    }
  }

  function startDetectionLoop() {
    if(detectorTimer)
      clearInterval(detectorTimer);
    detectTick();
    detectorTimer = setInterval(
        detectTick,
        DETECT_INTERVAL_MS
    );
  }

  // =============================================
  // TAB EVENT HANDLING
  // =============================================
  function reportTabEvent(eventType, remarks) {
    if(lastStatus !== "Running")
      return;
    addLogRow(eventType, remarks);
    const payload = {
      event_type: eventType,
      remarks
    };
    if (eventType === "Tab Switched") {
        payload.image = captureFrame();
    }

    postJSON("/api/log_event", payload)
        .then(async (data) => {
            if (data && typeof data.tab_switches === "number") {
                tabSwitchesEl.textContent = data.tab_switches;
            }
            await fetchIntegrityScore();
        })
        .catch(() => {});
  }

  // Tab is Hidden or Become Visible Again
  document.addEventListener("visibilitychange", function () {
    if (examEnding)
      return;
    isPageVisible = !document.hidden;
    if (document.hidden) {
      reportTabEvent("Tab Switched", "Candidate Switched to Another Tab");
    } else {
      reportTabEvent("Tab Returned", "Candidate Returned to the Exam Tab");
    }
  });

  // Tab Loses or Gains Focus
  window.addEventListener("blur", function () {
    if (examEnding)
      return;
    if (isWindowFocused) {
      isWindowFocused = false;
      if (isPageVisible) {
        reportTabEvent("Tab Switched", "Exam Window Lost Focus");
      }
    }
  });
  window.addEventListener("focus", function () {
    if (examEnding)
      return;
    if (!isWindowFocused) {
      isWindowFocused = true;
      if (isPageVisible) {
        reportTabEvent("Tab Returned", "Exam Window Active Again");
      }
    }
  });

  // =============================================
  // INITIALIZATION
  // =============================================
  startCamera();
  renderLog();
  fetchIntegrityScore();

})();