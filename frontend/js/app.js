/**
 * AI Interview Coach v2 — Frontend Application
 * =============================================
 * Handles:
 *  - Authentication (login/register)
 *  - Dashboard
 *  - CV upload & recruiter-style review
 *  - Interview mode selection
 *  - Adaptive voice interview with real-time tips
 *  - Final report
 */

// ──────────────────────────────────────────────
// State
// ──────────────────────────────────────────────
const state = {
    token: localStorage.getItem("ai_interview_token") || null,
    user: null,
    resumes: [],
    interviews: [],
    currentResume: null,
    currentInterview: null,
    currentQuestion: null,
    answers: [],
    mediaRecorder: null,
    audioStream: null,
    audioBuffers: [],
    audioChunks: [],
    audioBlob: null,
    recordingStartTime: null,
    timerInterval: null,
    audioContext: null,
    analyser: null,
    animFrameId: null,
    selectedSetupMode: "direct",
};

const API_BASE = window.location.origin;

// ──────────────────────────────────────────────
// DOM Helpers
// ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const screens = {
    auth: $("#screen-auth"),
    dashboard: $("#screen-dashboard"),
    cv: $("#screen-cv"),
    mode: $("#screen-mode"),
    prepSetup: $("#screen-prep-setup"),
    interviewSetup: $("#screen-interview-setup"),
    interview: $("#screen-interview"),
    report: $("#screen-report"),
};

function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove("active"));
    screens[name].classList.add("active");
}

function setLoading(btn, loading) {
    const text = btn.querySelector(".btn-text");
    const loader = btn.querySelector(".btn-loader");
    if (text) text.hidden = loading;
    if (loader) loader.hidden = !loading;
    btn.disabled = loading;
}

function showError(message) {
    alert(`Error: ${message}`);
}

// ──────────────────────────────────────────────
// API Helper
// ──────────────────────────────────────────────
async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        ...options,
        headers: {
            ...(options.headers || {}),
        },
    };

    if (state.token) {
        config.headers["Authorization"] = `Bearer ${state.token}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
        config.headers["Content-Type"] = "application/json";
    }

    const res = await fetch(url, config);
    const isAuthEndpoint = endpoint.startsWith("/api/auth/login") || endpoint.startsWith("/api/auth/register");

    if (res.status === 401) {
        if (!isAuthEndpoint) {
            logout();
            throw new Error("Session expired. Please login again.");
        }
        
        let err = "Invalid email or password. If you don't have an account, please click Register.";
        try {
            const data = await res.json();
            if (data && data.detail) err = data.detail;
        } catch (e) {}
        throw new Error(err);
    }

    if (!res.ok) {
        let err = "Request failed";
        try {
            const data = await res.json();
            if (typeof data.detail === "string") {
                err = data.detail;
            } else if (Array.isArray(data.detail)) {
                err = data.detail.map(d => d.msg || JSON.stringify(d)).join(", ");
            } else if (data.detail) {
                err = JSON.stringify(data.detail);
            } else {
                err = JSON.stringify(data);
            }
        } catch (e) {
            err = res.statusText || "An unexpected error occurred.";
        }
        throw new Error(err);
    }

    if (res.status === 204) return null;
    return res.json();
}

// ──────────────────────────────────────────────
// AUTHENTICATION
// ──────────────────────────────────────────────

// Tab switching
$$(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        const tabName = tab.dataset.tab;

        $$(".auth-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");

        $$(".auth-form").forEach((f) => f.classList.remove("active"));
        $(`#${tabName}-form`).classList.add("active");
    });
});

// Login
$("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type='submit']");
    setLoading(btn, true);

    try {
        const data = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: $("#login-email").value,
                password: $("#login-password").value,
            }),
        });

        setToken(data.access_token);
        state.user = data.user;
        loadDashboard();
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(btn, false);
    }
});

// Register
$("#register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type='submit']");
    setLoading(btn, true);

    try {
        const data = await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({
                email: $("#register-email").value,
                password: $("#register-password").value,
                full_name: $("#register-name").value,
            }),
        });

        setToken(data.access_token);
        state.user = data.user;
        loadDashboard();
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(btn, false);
    }
});

function setToken(token) {
    state.token = token;
    localStorage.setItem("ai_interview_token", token);
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem("ai_interview_token");
    showScreen("auth");
}

$("#btn-logout").addEventListener("click", logout);

async function initAuth() {
    if (!state.token) {
        showScreen("auth");
        return;
    }

    try {
        const user = await api("/api/auth/me");
        state.user = user;
        loadDashboard();
    } catch (err) {
        showScreen("auth");
    }
}

// ──────────────────────────────────────────────
// DASHBOARD
// ──────────────────────────────────────────────
async function loadDashboard() {
    showScreen("dashboard");
    $("#user-name").textContent = state.user.full_name;

    try {
        const [resumes, interviews] = await Promise.all([
            api("/api/resumes"),
            api("/api/interviews").catch(() => []),
        ]);
        state.resumes = resumes;
        state.interviews = interviews;
        renderResumesList();
        renderInterviewsList();
        populateResumeSelects();
    } catch (err) {
        showError(err.message);
    }
}

function renderResumesList() {
    const container = $("#resumes-list");

    if (!state.resumes.length) {
        container.innerHTML = '<p class="empty-state">No CVs uploaded yet.</p>';
        return;
    }

    // Show only the latest 3 CVs
    const latest = state.resumes.slice(0, 3);

    container.innerHTML = latest.map((r) => `
        <div class="resume-item" data-id="${r.id}">
            <div class="resume-info" data-id="${r.id}">
                <strong>${r.filename}</strong>
                <span>${r.job_title || "No job title"} • Score: ${r.cv_score || "N/A"}/100</span>
            </div>
            <button class="btn-delete-resume" data-id="${r.id}" title="Remove CV">🗑️</button>
        </div>
    `).join("");

    container.querySelectorAll(".resume-info").forEach((item) => {
        item.addEventListener("click", () => {
            const resume = state.resumes.find((r) => r.id == item.dataset.id);
            if (resume) showCVReview(resume);
        });
    });

    container.querySelectorAll(".btn-delete-resume").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            await deleteResume(parseInt(btn.dataset.id));
        });
    });
}

function renderInterviewsList() {
    const container = $("#interviews-list");

    if (!state.interviews || !state.interviews.length) {
        container.innerHTML = '<p class="empty-state">No interviews yet.</p>';
        return;
    }

    container.innerHTML = state.interviews.map((i) => {
        const statusText = i.status === "in_progress"
            ? "Left uncompleted"
            : i.status.replace("_", " ");
        const progress = i.status === "in_progress"
            ? ` • ${i.answered_count}/${i.total_questions} answered`
            : "";
        return `
        <div class="interview-item" data-id="${i.id}">
            <div class="interview-info" data-id="${i.id}">
                <strong>${i.job_title}</strong>
                <span>${i.mode === "practice" ? "Practice" : "Mock Interview"} • ${statusText}${progress}</span>
            </div>
            <button class="btn-delete-interview" data-id="${i.id}" title="Remove interview">🗑️</button>
        </div>`;
    }).join("");

    container.querySelectorAll(".interview-info").forEach((item) => {
        item.addEventListener("click", () => {
            const interview = state.interviews.find((i) => i.id == item.dataset.id);
            if (!interview) return;

            if (interview.status === "in_progress") {
                // Incomplete interview: offer to continue or view partial results
                const wantsContinue = confirm(
                    `This interview was left incomplete (${interview.answered_count}/${interview.total_questions} questions answered).\n\nOK → Continue the interview\nCancel → View results based on answers given so far`
                );
                if (wantsContinue) {
                    continueInterview(interview.id);
                    return;
                }
                if (!interview.answered_count) {
                    showError("No answers were submitted in this interview, so there are no results to show. Continue the interview instead.");
                    return;
                }
                loadInterviewReport(interview);
            } else {
                loadInterviewReport(interview);
            }
        });
    });

    container.querySelectorAll(".btn-delete-interview").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            await deleteInterview(parseInt(btn.dataset.id));
        });
    });
}

async function deleteInterview(interviewId) {
    if (!confirm("Are you sure you want to remove this interview?")) return;

    try {
        await api(`/api/interviews/${interviewId}`, { method: "DELETE" });
        state.interviews = state.interviews.filter((i) => i.id !== interviewId);
        renderInterviewsList();
    } catch (err) {
        showError(err.message);
    }
}

async function continueInterview(interviewId) {
    try {
        const data = await api(`/api/interviews/${interviewId}`);

        if (data.status !== "in_progress" || data.current_question_index >= data.questions.length) {
            loadInterviewReport(data);
            return;
        }

        state.currentResume = {
            id: data.resume_id,
            job_title: data.job_title,
            parsed_data: data.resume_parsed_data || {},
        };
        state.currentInterview = data;
        // Placeholder entries so sidebar progress reflects previously answered questions
        state.answers = new Array(data.current_question_index).fill({});
        state.currentQuestion = data.questions[data.current_question_index];

        showScreen("interview");
        renderInterviewScreen();
    } catch (err) {
        showError(err.message);
    }
}

async function deleteResume(resumeId) {
    if (!confirm("Are you sure you want to remove this CV?")) return;

    try {
        await api(`/api/resumes/${resumeId}`, { method: "DELETE" });
        state.resumes = state.resumes.filter((r) => r.id !== resumeId);
        renderResumesList();
        populateResumeSelects();
    } catch (err) {
        showError(err.message);
    }
}

$("#btn-goto-upload").addEventListener("click", () => {
    resetCVScreen();
    showScreen("cv");
});

$("#btn-goto-prep").addEventListener("click", () => {
    resetSetupForm("prep");
    showScreen("prepSetup");
});

$("#btn-goto-interview").addEventListener("click", () => {
    resetSetupForm("interview");
    showScreen("interviewSetup");
});

$("#btn-cv-back").addEventListener("click", () => loadDashboard());
$("#btn-prep-setup-back").addEventListener("click", () => loadDashboard());
$("#btn-interview-setup-back").addEventListener("click", () => loadDashboard());

// ──────────────────────────────────────────────
// CV UPLOAD & REVIEW
// ──────────────────────────────────────────────
const cvFileInput = $("#cv-file-input");
const cvUploadZone = $("#cv-upload-zone");
const cvFileName = $("#cv-file-name");
const btnUploadCV = $("#btn-upload-cv");

cvUploadZone.addEventListener("click", () => cvFileInput.click());
cvUploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    cvUploadZone.classList.add("dragover");
});
cvUploadZone.addEventListener("dragleave", () => cvUploadZone.classList.remove("dragover"));
cvUploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    cvUploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
        cvFileInput.files = e.dataTransfer.files;
        handleCVFileSelect();
    }
});
cvFileInput.addEventListener("change", handleCVFileSelect);
$("#cv-job-title").addEventListener("input", checkCVReady);

function handleCVFileSelect() {
    if (cvFileInput.files.length) {
        cvFileName.textContent = `📄 ${cvFileInput.files[0].name}`;
        checkCVReady();
    }
}

function checkCVReady() {
    const hasFile = cvFileInput.files.length > 0;
    btnUploadCV.disabled = !hasFile;
}

btnUploadCV.addEventListener("click", async () => {
    if (!cvFileInput.files.length) return;

    setLoading(btnUploadCV, true);

    try {
        const formData = new FormData();
        formData.append("resume", cvFileInput.files[0]);
        formData.append("job_title", $("#cv-job-title").value.trim());

        const data = await api("/api/resumes/upload", {
            method: "POST",
            body: formData,
        });

        state.currentResume = data;
        state.resumes.unshift(data);
        renderResumesList();
        displayCVReview(data.cv_review);
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(btnUploadCV, false);
    }
});

function displayCVReview(review) {
    $("#cv-upload-section").hidden = true;
    $("#cv-review-section").hidden = false;

    $("#cv-score").textContent = review.score;
    $("#cv-grade").textContent = review.grade;
    $("#cv-summary").textContent = review.summary;

    // Issues
    const issuesContainer = $("#cv-issues-list");
    if (review.issues && review.issues.length) {
        issuesContainer.innerHTML = review.issues.map((issue) => `
            <div class="cv-issue ${issue.severity}">
                <div class="issue-title">${issue.section.toUpperCase()} — ${issue.type.replace("_", " ").toUpperCase()}</div>
                <div class="issue-message">${issue.message}</div>
                <div class="issue-suggestion">💡 ${issue.suggestion}</div>
            </div>
        `).join("");
    } else {
        issuesContainer.innerHTML = '<p class="empty-state">No major issues found!</p>';
    }

    // Strengths
    $("#cv-strengths-list").innerHTML = review.strengths.map((s) => `<li>${s}</li>`).join("");

    // Plan
    $("#cv-plan-list").innerHTML = review.improvement_plan.map((p) => `<li>${p}</li>`).join("");

    // Sections
    const sectionsContainer = $("#cv-sections-list");
    sectionsContainer.innerHTML = Object.entries(review.sections_found).map(([name, found]) => `
        <span class="section-tag ${found ? "found" : "missing"}">${found ? "✓" : "✗"} ${name}</span>
    `).join("");
}

async function showCVReview(resume) {
    state.currentResume = resume;
    showScreen("cv");
    $("#cv-upload-section").hidden = true;
    $("#cv-review-section").hidden = false;

    // If full review data is already on the object, show it directly
    if (resume.cv_review) {
        displayCVReview(resume.cv_review);
        return;
    }

    // Otherwise fetch the stored review from the backend
    try {
        const review = await api(`/api/resumes/${resume.id}/review`);
        displayCVReview(review);
    } catch (err) {
        showError(err.message);
    }
}

function resetCVScreen() {
    state.currentResume = null;
    $("#cv-upload-section").hidden = false;
    $("#cv-review-section").hidden = true;
    cvFileInput.value = "";
    cvFileName.textContent = "";
    $("#cv-job-title").value = "";
    btnUploadCV.disabled = true;
}

$("#btn-upload-another").addEventListener("click", resetCVScreen);

$("#btn-start-interview").addEventListener("click", () => {
    if (!state.currentResume) {
        showError("Please upload a CV first.");
        return;
    }
    showScreen("mode");
});

// ──────────────────────────────────────────────
// SETUP SCREENS (Prep + Mock Interview)
// ──────────────────────────────────────────────
function populateResumeSelects() {
    const prepSelect = $("#prep-resume-select");
    const interviewSelect = $("#interview-resume-select");

    const options = state.resumes.map((r) =>
        `<option value="${r.id}">${r.filename}${r.job_title ? " — " + r.job_title : ""}</option>`
    ).join("");

    const defaultOpt = '<option value="">-- Choose a CV --</option>';

    prepSelect.innerHTML = defaultOpt + options;
    interviewSelect.innerHTML = defaultOpt + options;
}

function resetSetupForm(type) {
    if (type === "prep") {
        $("#prep-resume-select").value = "";
        $("#prep-job-title").value = "";
        // Reset back to the "existing CV" tab and clear the upload tab
        selectPrepTab("existing");
        $("#prep-upload-job-title").value = "";
        prepFileInput.value = "";
        prepFileName.textContent = "";
        btnPrepUploadStart.disabled = true;
    } else {
        $("#interview-resume-select").value = "";
        $("#interview-job-title").value = "";
        selectSetupMode("direct");
    }
    updateStartSetupButton(type);
}

function getSelectedResume(selectId) {
    const id = parseInt($(`#${selectId}`).value);
    return state.resumes.find((r) => r.id === id) || null;
}

function updateStartSetupButton(type) {
    const selectId = type === "prep" ? "prep-resume-select" : "interview-resume-select";
    const btnId = type === "prep" ? "btn-start-prep" : "btn-start-interview-from-setup";
    const resume = getSelectedResume(selectId);
    $(`#${btnId}`).disabled = !resume;
}

$("#prep-resume-select").addEventListener("change", () => updateStartSetupButton("prep"));
$("#interview-resume-select").addEventListener("change", () => updateStartSetupButton("interview"));

// Prep setup tabs: Use Existing CV / Upload New CV
function selectPrepTab(name) {
    $$(".prep-tab").forEach((t) => t.classList.toggle("active", t.dataset.prepTab === name));
    $("#prep-panel-existing").hidden = name !== "existing";
    $("#prep-panel-upload").hidden = name !== "upload";
}

$$(".prep-tab").forEach((tab) => {
    tab.addEventListener("click", () => selectPrepTab(tab.dataset.prepTab));
});

// Prep upload zone (new CV → straight into practice)
const prepFileInput = $("#prep-upload-file");
const prepUploadZone = $("#prep-upload-zone");
const prepFileName = $("#prep-upload-file-name");
const btnPrepUploadStart = $("#btn-prep-upload-start");

prepUploadZone.addEventListener("click", () => prepFileInput.click());
prepUploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    prepUploadZone.classList.add("dragover");
});
prepUploadZone.addEventListener("dragleave", () => prepUploadZone.classList.remove("dragover"));
prepUploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    prepUploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
        prepFileInput.files = e.dataTransfer.files;
        handlePrepFileSelect();
    }
});
prepFileInput.addEventListener("change", handlePrepFileSelect);

function handlePrepFileSelect() {
    if (prepFileInput.files.length) {
        prepFileName.textContent = `📄 ${prepFileInput.files[0].name}`;
        btnPrepUploadStart.disabled = false;
    }
}

btnPrepUploadStart.addEventListener("click", async () => {
    if (!prepFileInput.files.length) return;

    setLoading(btnPrepUploadStart, true);

    try {
        const jobTitle = $("#prep-upload-job-title").value.trim() || "General";

        const formData = new FormData();
        formData.append("resume", prepFileInput.files[0]);
        formData.append("job_title", jobTitle);

        const data = await api("/api/resumes/upload", {
            method: "POST",
            body: formData,
        });

        state.resumes.unshift(data);
        renderResumesList();
        populateResumeSelects();
        await startInterview(data, jobTitle, "practice");
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(btnPrepUploadStart, false);
    }
});

// Interview setup mode cards
function selectSetupMode(mode) {
    state.selectedSetupMode = mode;
    $("#setup-mode-practice").classList.toggle("selected", mode === "practice");
    $("#setup-mode-direct").classList.toggle("selected", mode === "direct");
}

$("#setup-mode-practice").addEventListener("click", () => selectSetupMode("practice"));
$("#setup-mode-direct").addEventListener("click", () => selectSetupMode("direct"));

$("#btn-start-prep").addEventListener("click", async () => {
    const resume = getSelectedResume("prep-resume-select");
    const jobTitle = $("#prep-job-title").value.trim() || "General";
    if (!resume) return;
    await startInterview(resume, jobTitle, "practice");
});

$("#btn-start-interview-from-setup").addEventListener("click", async () => {
    const resume = getSelectedResume("interview-resume-select");
    const jobTitle = $("#interview-job-title").value.trim() || "General";
    if (!resume) return;
    await startInterview(resume, jobTitle, state.selectedSetupMode);
});

// Legacy mode selection screen (from CV review "Continue to Interview")
$("#mode-practice").addEventListener("click", () => startInterview(state.currentResume, state.currentResume?.job_title || $("#cv-job-title").value.trim() || "General", "practice"));
$("#mode-direct").addEventListener("click", () => startInterview(state.currentResume, state.currentResume?.job_title || $("#cv-job-title").value.trim() || "General", "direct"));

async function startInterview(resume, jobTitle, mode) {
    if (!resume) {
        showError("No CV selected.");
        return;
    }

    let btn = null;
    if (document.activeElement?.id === "btn-start-prep") btn = $("#btn-start-prep");
    else if (document.activeElement?.id === "btn-start-interview-from-setup") btn = $("#btn-start-interview-from-setup");
    if (btn) setLoading(btn, true);

    try {
        const data = await api("/api/interviews", {
            method: "POST",
            body: JSON.stringify({
                resume_id: resume.id,
                job_title: jobTitle,
                mode: mode,
            }),
        });

        state.currentResume = resume;
        state.currentInterview = data;
        state.answers = [];
        state.currentQuestion = data.questions[0];

        showScreen("interview");
        renderInterviewScreen();
    } catch (err) {
        showError(err.message);
    } finally {
        if (btn) setLoading(btn, false);
    }
}

async function loadInterviewReport(interview) {
    try {
        const report = await api(`/api/interviews/${interview.id}/report`);
        state.currentInterview = interview;
        $("#report-partial-banner").hidden = interview.status !== "in_progress";
        showScreen("report");
        renderReport(report);
    } catch (err) {
        showError(err.message);
    }
}

// ──────────────────────────────────────────────
// INTERVIEW SCREEN
// ──────────────────────────────────────────────
function renderInterviewScreen() {
    const interview = state.currentInterview;
    const question = state.currentQuestion;

    if (!interview || !question) return;

    // Mode badge
    const modeText = interview.mode === "practice" ? "Practice Mode" : "Direct Interview";
    $("#mode-badge").textContent = modeText;
    $("#mode-badge").style.background = interview.mode === "practice"
        ? "rgba(108, 92, 231, 0.15)"
        : "rgba(0, 206, 201, 0.15)";

    // Question
    const badge = $("#question-badge");
    badge.textContent = question.type.replace("_", " ");
    badge.className = `question-badge ${question.type}`;

    $("#question-count").textContent = `${question.number} / ${interview.total_questions}`;
    $("#question-text").textContent = question.question;

    // Progress
    const progress = (question.number / interview.total_questions) * 100;
    $("#progress-fill").style.width = `${progress}%`;
    $("#progress-text").textContent = `Question ${question.number} of ${interview.total_questions}`;

    // Sidebar
    $("#sidebar-job-title").textContent = interview.job_title;
    $("#sidebar-progress").textContent = `${state.answers.length} / ${interview.total_questions} answered`;
    $("#mini-progress-fill").style.width = `${(state.answers.length / interview.total_questions) * 100}%`;

    const skills = state.currentResume?.parsed_data?.skills || [];
    $("#sidebar-skills-list").innerHTML = skills.slice(0, 8).map((s) => `<span class="skill-tag">${s}</span>`).join("");

    // Reset recording UI
    resetRecordingUI();
    $("#answer-result").hidden = true;
    $("#realtime-tip").hidden = true;
    $("#model-answer-box").hidden = true;
    $("#btn-re-record").hidden = true;
    $("#recording-area").hidden = false;
}

function resetRecordingUI() {
    const micBtn = $("#btn-record");
    micBtn.classList.remove("recording");
    $("#mic-prompt").hidden = false;
    $("#recording-active").hidden = true;
    $("#processing").hidden = true;
    $("#waveform-canvas").hidden = true;
    state.audioChunks = [];
}

// WAV Recording Helpers
function _writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function _encodeWAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    _writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    _writeString(view, 8, "WAVE");
    _writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true); // Subchunk1Size
    view.setUint16(20, 1, true);  // AudioFormat = PCM
    view.setUint16(22, 1, true);  // NumChannels = mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // ByteRate
    view.setUint16(32, 2, true);  // BlockAlign
    view.setUint16(34, 16, true); // BitsPerSample
    _writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
        offset += 2;
    }

    return new Blob([view], { type: "audio/wav" });
}

function _flattenAudioBuffers(buffers) {
    let totalLength = 0;
    for (const b of buffers) totalLength += b.length;
    const result = new Float32Array(totalLength);
    let offset = 0;
    for (const b of buffers) {
        result.set(b, offset);
        offset += b.length;
    }
    return result;
}

// Recording
$("#btn-record").addEventListener("click", startRecording);
$("#btn-stop").addEventListener("click", stopRecording);

async function startRecording() {
    try {
        // Safety: clear any leftover timer from a previous take
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
        $("#timer-display").textContent = "00:00";

        // Request microphone with high-quality audio settings
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,   // Enable echo cancellation to eliminate room echo
                noiseSuppression: true,   // Enable noise suppression to filter background noise
                autoGainControl: true,    // Automatic gain control for clear, balanced voice levels
            },
        });

        // Create audio context for recording + visualizer
        state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        state.audioStream = stream;
        state.audioBuffers = [];
        state.audioChunks = []; // legacy compatibility

        const source = state.audioContext.createMediaStreamSource(stream);

        // Analyser for waveform
        state.analyser = state.audioContext.createAnalyser();
        state.analyser.fftSize = 256;
        source.connect(state.analyser);

        // ScriptProcessor to capture raw PCM
        const processor = state.audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
            const data = e.inputBuffer.getChannelData(0);
            state.audioBuffers.push(new Float32Array(data));
        };
        source.connect(processor);

        // Connect processor to a zero-gain output so it stays active without feedback
        const zeroGain = state.audioContext.createGain();
        zeroGain.gain.value = 0;
        processor.connect(zeroGain);
        zeroGain.connect(state.audioContext.destination);
        state.mediaRecorder = processor;

        state.recordingStartTime = Date.now();

        $("#mic-prompt").hidden = true;
        $("#recording-active").hidden = false;
        $("#waveform-canvas").hidden = false;

        state.timerInterval = setInterval(updateTimer, 1000);
        setupWaveform();
    } catch (err) {
        console.error(err);
        showError("Microphone access denied. Please allow microphone access.");
    }
}

function stopRecording() {
    if (!state.mediaRecorder || !state.audioContext) return;

    // Stop timer immediately and reset display
    clearInterval(state.timerInterval);
    state.timerInterval = null;
    $("#timer-display").textContent = "00:00";

    // Stop microphone
    if (state.audioStream) {
        state.audioStream.getTracks().forEach((t) => t.stop());
    }
    state.audioContext.close();
    cancelAnimationFrame(state.animFrameId);

    $("#recording-active").hidden = true;
    $("#waveform-canvas").hidden = true;
    $("#processing").hidden = false;

    // Build WAV blob and submit
    const samples = _flattenAudioBuffers(state.audioBuffers);
    if (samples.length === 0) {
        $("#processing").hidden = true;
        $("#mic-prompt").hidden = false;
        showError("No audio captured. Please try again.");
        return;
    }
    const sampleRate = state.audioContext.sampleRate;
    state.audioBlob = _encodeWAV(samples, sampleRate);
    submitAnswer();
}

function updateTimer() {
    const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const secs = String(elapsed % 60).padStart(2, "0");
    $("#timer-display").textContent = `${mins}:${secs}`;
}

function setupWaveform() {
    const canvas = $("#waveform-canvas");
    const ctx = canvas.getContext("2d");

    const bufferLength = state.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        state.animFrameId = requestAnimationFrame(draw);
        state.analyser.getByteFrequencyData(dataArray);

        ctx.fillStyle = "rgba(26, 26, 46, 0.3)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * canvas.height;
            const hue = 260 + (dataArray[i] / 255) * 60;
            ctx.fillStyle = `hsla(${hue}, 70%, 60%, 0.8)`;
            ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    }
    draw();
}

async function submitAnswer() {
    const question = state.currentQuestion;
    const interview = state.currentInterview;
    const audioBlob = state.audioBlob;

    if (!question || !audioBlob) return;

    try {
        const formData = new FormData();
        formData.append("question_number", question.number);
        formData.append("audio", audioBlob, `answer_q${question.number}.wav`);

        const result = await api(`/api/interviews/${interview.id}/answer`, {
            method: "POST",
            body: formData,
        });

        state.answers.push(result);
        showAnswerResult(result);
    } catch (err) {
        $("#processing").hidden = true;
        $("#mic-prompt").hidden = false;
        showError(err.message);
    }
}

function showAnswerResult(result) {
    $("#processing").hidden = true;
    $("#recording-area").hidden = true;
    $("#answer-result").hidden = false;

    // Real-time tip
    if (result.real_time_tip && state.currentInterview.mode === "practice") {
        $("#realtime-tip").hidden = false;
        $("#tip-text").textContent = result.real_time_tip;
    }

    // Scores
    animateCircle($("#content-circle"), result.content_score);
    animateCircle($("#confidence-circle"), result.confidence_score);
    $("#content-score-display").textContent = Math.round(result.content_score);
    $("#confidence-score-display").textContent = Math.round(result.confidence_score);

    // Transcription & feedback
    $("#transcription-text").textContent = result.transcription || "No speech detected.";
    $("#feedback-text").textContent = result.content_feedback || "";

    const tipsList = $("#tips-list");
    tipsList.innerHTML = "";
    result.tips.forEach((tip) => {
        const li = document.createElement("li");
        li.textContent = tip;
        tipsList.appendChild(li);
    });

    // Model answer (practice mode only)
    const modelBox = $("#model-answer-box");
    const reRecordBtn = $("#btn-re-record");
    if (state.currentInterview.mode === "practice") {
        reRecordBtn.hidden = false;
        fetchModelAnswer(result.question_number);
    } else {
        modelBox.hidden = true;
        reRecordBtn.hidden = true;
        $("#model-answer-text").textContent = "";
    }

    // Next button
    const isLast = !result.next_question;
    $("#btn-next").textContent = isLast ? "View Final Report 📊" : "Next Question →";

    // Store next question
    state.nextQuestion = result.next_question;
}

async function fetchModelAnswer(questionNumber) {
    try {
        const data = await api(`/api/interviews/${state.currentInterview.id}/model-answer?question_number=${questionNumber}`);
        $("#model-answer-text").textContent = data.model_answer || "No model answer available.";
        $("#model-answer-box").hidden = false;
    } catch (err) {
        console.warn("Could not load model answer:", err);
        $("#model-answer-box").hidden = true;
    }
}

function reRecordAnswer() {
    $("#answer-result").hidden = true;
    $("#realtime-tip").hidden = true;
    $("#model-answer-box").hidden = true;
    $("#recording-area").hidden = false;
    resetRecordingUI();
}

$("#btn-re-record").addEventListener("click", reRecordAnswer);

function animateCircle(circleEl, score) {
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (score / 100) * circumference;
    setTimeout(() => {
        circleEl.style.strokeDashoffset = offset;
    }, 100);
}

$("#btn-next").addEventListener("click", () => {
    if (!state.nextQuestion) {
        loadReport();
        return;
    }

    // Update total questions if new follow-up added
    if (state.nextQuestion.number > state.currentInterview.total_questions) {
        state.currentInterview.total_questions = state.nextQuestion.number;
    }

    state.currentQuestion = state.nextQuestion;
    renderInterviewScreen();
});

$("#btn-exit-interview").addEventListener("click", () => {
    if (confirm("Are you sure you want to exit? Your progress will be lost.")) {
        loadDashboard();
    }
});

// ──────────────────────────────────────────────
// REPORT SCREEN
// ──────────────────────────────────────────────
async function loadReport() {
    $("#report-partial-banner").hidden = true;
    showScreen("report");

    try {
        const report = await api(`/api/interviews/${state.currentInterview.id}/report`);
        renderReport(report);
    } catch (err) {
        showError(err.message);
    }
}

function renderReport(report) {
    $("#overall-score-value").textContent = Math.round(report.overall_score);
    $("#grade-badge").textContent = `Grade: ${report.grade} — ${report.grade_label}`;

    $("#content-bar").style.width = `${report.content_average}%`;
    $("#content-avg-value").textContent = `${Math.round(report.content_average)}%`;
    $("#confidence-bar").style.width = `${report.confidence_average}%`;
    $("#confidence-avg-value").textContent = `${Math.round(report.confidence_average)}%`;

    $("#strengths-list").innerHTML = report.strengths.map((s) => `<li>${s}</li>`).join("");
    $("#weaknesses-list").innerHTML = report.weaknesses.map((w) => `<li>${w}</li>`).join("");
    $("#report-tips-list").innerHTML = report.tips.map((t) => `<li>${t}</li>`).join("");

    const breakdown = $("#question-breakdown-list");
    breakdown.innerHTML = "";
    report.question_results.forEach((qr) => {
        const div = document.createElement("div");
        div.className = "breakdown-item";
        div.innerHTML = `
            <div class="q-header">
                <span class="q-text">Q${qr.question_number}: ${qr.question}</span>
                <div class="q-scores">
                    <span class="content-s">Content: ${Math.round(qr.content_score)}%</span>
                    <span class="confidence-s">Confidence: ${Math.round(qr.confidence_score)}%</span>
                </div>
            </div>
            <p class="q-answer">"${truncate(qr.transcription, 200)}"</p>
        `;
        breakdown.appendChild(div);
    });
}

function truncate(text, maxLen) {
    if (!text) return "No transcription available.";
    return text.length > maxLen ? text.substring(0, maxLen) + "..." : text;
}

$("#btn-report-dashboard").addEventListener("click", loadDashboard);
$("#btn-practice-again").addEventListener("click", () => {
    if (state.currentResume) {
        showScreen("mode");
    } else {
        loadDashboard();
    }
});

$("#btn-export-report").addEventListener("click", async () => {
    try {
        const report = await api(`/api/interviews/${state.currentInterview.id}/report`);
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `interview-report-${state.currentInterview.id}.json`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        showError(err.message);
    }
});

// ──────────────────────────────────────────────
// INITIALIZE
// ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", initAuth);
