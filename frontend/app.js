const API_BASE = "";

let userId = null;
let batchId = null;

const loginForm = document.getElementById("login-form");
const coursesSection = document.getElementById("courses-section");
const coursesList = document.getElementById("courses-list");
const generateBtn = document.getElementById("generate-btn");
const progressSection = document.getElementById("progress-section");
const progressList = document.getElementById("progress-list");
const downloadSection = document.getElementById("download-section");
const downloadList = document.getElementById("download-list");
const loginStatus = document.getElementById("login-status");

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const canvasUrl = document.getElementById("canvas-url").value;
  const canvasToken = document.getElementById("canvas-token").value;

  loginStatus.textContent = "Connecting...";
  loginStatus.className = "";

  try {
    const resp = await fetch(`${API_BASE}/auth/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_url: canvasUrl, canvas_token: canvasToken }),
    });

    if (!resp.ok) throw new Error("Invalid credentials");

    const data = await resp.json();
    userId = data.user_id;
    loginStatus.textContent = `Connected as ${data.name}`;
    loginStatus.className = "success";

    await loadCourses();
  } catch (err) {
    loginStatus.textContent = "Connection failed. Check URL and token.";
    loginStatus.className = "error";
  }
});

async function loadCourses() {
  const resp = await fetch(`${API_BASE}/courses?user_id=${userId}`);
  const courses = await resp.json();

  coursesList.innerHTML = courses
    .map(
      (c) => `
    <label class="course-item">
      <input type="checkbox" value="${c.id}"> ${c.name}
    </label>
  `
    )
    .join("");

  document.getElementById("login-section").classList.add("hidden");
  coursesSection.classList.remove("hidden");
}

generateBtn.addEventListener("click", async () => {
  const checked = [...coursesList.querySelectorAll("input:checked")];
  if (checked.length === 0) {
    alert("Select at least one course");
    return;
  }

  const courseIds = checked.map((c) => c.value);

  const resp = await fetch(`${API_BASE}/scrape/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, course_ids: courseIds }),
  });

  const data = await resp.json();
  batchId = data.batch_id;

  coursesSection.classList.add("hidden");
  progressSection.classList.remove("hidden");

  pollStatus();
});

async function pollStatus() {
  const resp = await fetch(`${API_BASE}/status/${batchId}`);
  const data = await resp.json();

  progressList.innerHTML = data.jobs
    .map(
      (j) => `
    <div class="job-item ${j.status}">
      <span>${j.course_id}</span>
      <span class="status-badge">${j.status}</span>
      ${j.error ? `<span class="error-msg">${j.error}</span>` : ""}
    </div>
  `
    )
    .join("");

  const allDone = data.jobs.every(
    (j) => j.status === "completed" || j.status === "failed"
  );

  if (allDone) {
    showDownloads(data.jobs.filter((j) => j.status === "completed"));
  } else {
    setTimeout(pollStatus, 3000);
  }
}

function showDownloads(completedJobs) {
  progressSection.classList.add("hidden");
  downloadSection.classList.remove("hidden");

  downloadList.innerHTML = completedJobs
    .map(
      (j) => `
    <div class="download-item">
      <span>${j.course_id}</span>
      <a href="${API_BASE}/download/${j.course_id}/md" target="_blank">Markdown</a>
      <a href="${API_BASE}/download/${j.course_id}/html" target="_blank">HTML</a>
      <a href="${API_BASE}/download/${j.course_id}/pdf" target="_blank">PDF</a>
    </div>
  `
    )
    .join("");
}
