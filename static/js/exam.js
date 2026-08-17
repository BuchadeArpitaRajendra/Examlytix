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
  let lastReportedEvent = null;
  let eventCooldown = false;
  let isMinimized = false;
  let wasMinimized = false;

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
    if (eventType == "Face Not Detected" || eventType == "Tab Switched" || eventType == "Window Minimized")
      return "bad";
    if (eventType == "Face Detected" || eventType == "Tab Returned" || eventType == "Window Restored")
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
  // DETECT WINDOW MINIMIZATION
  // =============================================
  function checkWindowMinimized() {
    // Method 1: Check if document is hidden AND window is not focused
    // When minimized, document.hidden = true and window loses focus
    if (document.hidden && !document.hasFocus()) {
      isMinimized = true;
    } else if (document.hasFocus() && !document.hidden) {
      isMinimized = false;
    }
    
    // Method 2: Check window outer dimensions (for older browsers)
    // When minimized, outerHeight and outerWidth are very small
    if (window.outerHeight !== undefined && window.outerWidth !== undefined) {
      // Some browsers report 0 or very small values when minimized
      if (window.outerHeight < 100 && window.outerWidth < 100) {
        isMinimized = true;
      }
    }
    
    return isMinimized;
  }

  // =============================================
  // TAB EVENT HANDLING - WITH MINIMIZATION DETECTION
  // =============================================
  function reportTabEvent(eventType, remarks) {
    if(lastStatus !== "Running") return;
    
    // Prevent duplicate events from firing too quickly
    if (eventCooldown) return;
    
    // Don't report if exam is ending
    if (examEnding) return;
    
    // Only report Tab Switched events (not Tab Returned) for counting
    // But we log both for tracking purposes
    addLogRow(eventType, remarks);
    
    const payload = {
        event_type: eventType,
        remarks: remarks
    };
    
    // Only capture screenshot for Tab Switched events
    if (eventType === "Tab Switched" || eventType === "Window Minimized") {
        payload.image = captureFrame();
        // Set cooldown to prevent multiple rapid events
        eventCooldown = true;
        setTimeout(() => {
            eventCooldown = false;
        }, 2000); // 2 second cooldown
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

  // Tab is Hidden (Tab Switch or Minimization detected)
  document.addEventListener("visibilitychange", function () {
    if (examEnding) return;
    
    const wasHidden = !isPageVisible;
    isPageVisible = !document.hidden;
    
    // Check if window is minimized
    const minimized = checkWindowMinimized();
    
    // If window was minimized before and now restored
    if (wasMinimized && !minimized && !document.hidden) {
      // Window was restored
      reportTabEvent("Window Restored", "Window Restored from Minimized");
      wasMinimized = false;
      lastReportedEvent = null;
      return;
    }
    
    // If document became hidden
    if (document.hidden) {
      // Check if it's actually minimized (not just tab switch)
      if (minimized) {
        wasMinimized = true;
        if (lastReportedEvent !== 'minimized' && lastReportedEvent !== 'tab_switch') {
          reportTabEvent("Window Minimized", "Candidate Minimized the Window");
          lastReportedEvent = 'minimized';
        }
      } else {
        // Just tab switch
        if (lastReportedEvent !== 'tab_switch' && lastReportedEvent !== 'minimized') {
          reportTabEvent("Tab Switched", "Candidate Switched to Another Tab");
          lastReportedEvent = 'tab_switch';
        }
      }
    } else {
      // Tab became visible again (returned)
      if (lastReportedEvent === 'tab_switch' || lastReportedEvent === 'minimized') {
        reportTabEvent("Tab Returned", "Candidate Returned to the Exam Tab");
        setTimeout(() => {
          lastReportedEvent = null;
        }, 3000);
      }
    }
  });

  // Tab Loses Focus (Blur event - also fires on minimization)
  window.addEventListener("blur", function () {
    if (examEnding) return;
    
    // Check if minimized
    const minimized = checkWindowMinimized();
    
    if (isWindowFocused) {
      isWindowFocused = false;
      
      // If minimized, report as window minimized
      if (minimized) {
        wasMinimized = true;
        if (lastReportedEvent !== 'minimized' && lastReportedEvent !== 'tab_switch') {
          reportTabEvent("Window Minimized", "Candidate Minimized the Window");
          lastReportedEvent = 'minimized';
        }
      } else if (isPageVisible && lastReportedEvent !== 'tab_switch' && lastReportedEvent !== 'minimized') {
        // Only report if page is visible and we haven't already reported
        reportTabEvent("Tab Switched", "Exam Window Lost Focus");
        lastReportedEvent = 'tab_switch';
      }
    }
  });

  // Tab Gains Focus (Focus event)
  window.addEventListener("focus", function () {
    if (examEnding) return;
    
    // Check if minimized
    const minimized = checkWindowMinimized();
    
    if (!isWindowFocused) {
      isWindowFocused = true;
      
      // If was minimized and now restored
      if (wasMinimized && !minimized && isPageVisible) {
        reportTabEvent("Window Restored", "Window Restored from Minimized");
        wasMinimized = false;
        setTimeout(() => {
          lastReportedEvent = null;
        }, 3000);
      } else if (isPageVisible) {
        reportTabEvent("Tab Returned", "Exam Window Active Again");
        setTimeout(() => {
          lastReportedEvent = null;
        }, 3000);
      }
    }
  });

  // =============================================
  // PERIODIC MINIMIZATION CHECK (Backup detection)
  // =============================================
  setInterval(function() {
    if (examEnding) return;
    
    const minimized = checkWindowMinimized();
    
    // If minimized state changed
    if (minimized && !wasMinimized && isPageVisible) {
      // Window just got minimized
      wasMinimized = true;
      if (lastReportedEvent !== 'minimized') {
        reportTabEvent("Window Minimized", "Candidate Minimized the Window");
        lastReportedEvent = 'minimized';
      }
    } else if (!minimized && wasMinimized) {
      // Window just got restored
      wasMinimized = false;
      if (lastReportedEvent === 'minimized') {
        reportTabEvent("Window Restored", "Window Restored from Minimized");
        setTimeout(() => {
          lastReportedEvent = null;
        }, 3000);
      }
    }
  }, 2000); // Check every 2 seconds

  // =============================================
  // PAGE UNLOAD HANDLER
  // =============================================
  window.addEventListener('beforeunload', function() {
    if (!examEnding && lastStatus === 'Running') {
      // Try to log that user is leaving
      navigator.sendBeacon('/api/log_event', JSON.stringify({
        event_type: 'Tab Switched',
        remarks: 'Page Unloaded (User may have closed the browser)'
      }));
    }
  });

  // =============================================
  // INITIALIZATION
  // =============================================
  startCamera();
  renderLog();
  fetchIntegrityScore();

  console.log('Exam monitoring initialized with window minimization detection');
})();