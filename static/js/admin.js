(function () {
  // ---------------- Tab switching ----------------
  const tabs = document.querySelectorAll(".admin-tab");
  const panels = document.querySelectorAll(".admin-panel-body");
  const savedTab = localStorage.getItem("adminTab");
  
  if (savedTab) {
    tabs.forEach(t => t.classList.remove("active"));
    panels.forEach(p => p.classList.remove("active"));
    const activeTab = document.querySelector(`.admin-tab[data-tab="${savedTab}"]`);
    const activePanel = document.getElementById("tab-" + savedTab);
    if (activeTab && activePanel) {
      activeTab.classList.add("active");
      activePanel.classList.add("active");
    }
  }
  
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const panel = document.getElementById("tab-" + tab.dataset.tab);
      if (panel) panel.classList.add("active");
      localStorage.setItem("adminTab", tab.dataset.tab);
    });
  });

  // ---------------- Modal plumbing ----------------
  const overlay = document.getElementById("modalOverlay");
  const modalTitle = document.getElementById("modalTitle");
  const modalEyebrow = document.getElementById("modalEyebrow");
  const modalFields = document.getElementById("modalFields");
  const modalForm = document.getElementById("modalForm");
  const modalErrors = document.getElementById("modalErrors");
  const modalCancel = document.getElementById("modalCancel");

  let currentEndpoint = null;

  function openModal(title, eyebrow, endpoint, fieldsHtml) {
    modalTitle.textContent = title;
    modalEyebrow.textContent = eyebrow;
    modalFields.innerHTML = fieldsHtml;
    modalErrors.innerHTML = "";
    modalErrors.classList.remove("show");
    currentEndpoint = endpoint;
    overlay.classList.add("show");
  }

  function closeModal() {
    overlay.classList.remove("show");
    currentEndpoint = null;
  }

  modalCancel.addEventListener("click", closeModal);
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeModal();
  });

  function field(label, name, value, type) {
    type = type || "text";
    return `
      <div class="field">
        <label>${label}</label>
        <input type="${type}" name="${name}" value="${(value || "").toString().replace(/"/g, '&quot;')}">
      </div>`;
  }

  // ---------------- Edit buttons ----------------
  document.body.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-edit]");
    if (!btn) return;
    const kind = btn.dataset.edit;
    const id = btn.dataset.id;

    if (kind === "candidate") {
      openModal("Edit Candidate", "Candidate #" + id, `/admin/api/candidates/${id}`,
        field("Full Name", "name", btn.dataset.name) +
        field("Email Address", "email", btn.dataset.email, "email") +
        field("Age", "age", btn.dataset.age, "number") +
        field("Exam Subject", "exam_subject", btn.dataset.subject) +
        field("New Password (leave blank to keep current)", "password", "", "password")
      );
    } else if (kind === "session") {
      openModal("Edit Session", "Session #" + id, `/admin/api/sessions/${id}`,
        `<div class="field">
          <label>Status</label>
          <select name="status">
            <option value="Running" ${btn.dataset.status === "Running" ? "selected" : ""}>Running</option>
            <option value="Paused" ${btn.dataset.status === "Paused" ? "selected" : ""}>Paused</option>
            <option value="Completed" ${btn.dataset.status === "Completed" ? "selected" : ""}>Completed</option>
          </select>
        </div>` +
        field("Total Absence Duration (seconds)", "total_absence_duration", btn.dataset.absence, "number") +
        field("Total Tab Switches", "total_tab_switches", btn.dataset.switches, "number")
      );
    } else if (kind === "event") {
      openModal("Edit Event", "Event #" + id, `/admin/api/events/${id}`,
        field("Event Type", "event_type", btn.dataset.eventtype) +
        field("Remarks", "remarks", btn.dataset.remarks)
      );
    }
  });

  // ---------------- Delete buttons ----------------
  document.body.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-delete]");
    if (!btn) return;
    const kind = btn.dataset.delete;
    const id = btn.dataset.id;
    if (!confirm(`Delete this ${kind} record? This action cannot be undone.`)) return;

    const endpointMap = {
      candidate: `/admin/api/candidates/${id}`,
      session: `/admin/api/sessions/${id}`,
      event: `/admin/api/events/${id}`,
    };

    fetch(endpointMap[kind], { method: "DELETE" })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          window.location.reload();
        } else {
          const errors = data.errors || ["Delete failed."];
          alert("Error: " + errors.join("\n"));
        }
      })
      .catch(() => alert("Network error while deleting. Please try again."));
  });

  // ---------------- Submit edit form ----------------
  modalForm.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!currentEndpoint) return;

    const formData = new FormData(modalForm);
    const payload = {};
    formData.forEach((value, key) => {
      if (key === "password" && !value) return;
      payload[key] = value;
    });

    fetch(currentEndpoint, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          window.location.reload();
        } else {
          modalErrors.innerHTML = data.errors ? data.errors.join("<br>") : "Update failed.";
          modalErrors.classList.add("show");
        }
      })
      .catch(() => {
        modalErrors.innerHTML = "Network error. Please try again.";
        modalErrors.classList.add("show");
      });
  });
})();