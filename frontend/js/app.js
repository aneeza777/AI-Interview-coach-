/* ═════════════════════════════════════════════════════════════════════════════
   AI INTERVIEW COACH — CORE FRONTEND LOGIC (ALIBABA CLOUD HACKATHON 2026)
   ═════════════════════════════════════════════════════════════════════════════ */

// Global State
const state = {
  token: localStorage.getItem('token') || null,
  user: null,
  currentView: 'auth',
  currentInterviewMode: 'practice', // 'practice' | 'mock'
  selectedCVFile: null,
  activeResumeId: null,
  activeInterview: null,
  currentQuestionIndex: 0,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  audioStream: null,
  webcamStream: null,
  audioContext: null,
  analyser: null,
  silenceTimer: null,
  interviewTimerInterval: null,
  interviewSeconds: 0,
  questionBankData: []
};

// API Base URL
const API_BASE = '/api';

/* ═════════════════════════════════════════════════════════════════════════════
   INITIALIZATION & AUTHENTICATION
   ═════════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  if (state.token) {
    try {
      const user = await fetchAPI('/auth/me');
      state.user = user;
      updateUserUI();
      navigateTo('dashboard');
    } catch (err) {
      console.warn('Session expired or invalid token:', err);
      logout();
    }
  } else {
    navigateTo('auth');
  }
}

function updateUserUI() {
  if (!state.user) return;
  const name = state.user.full_name || 'Candidate';
  const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'AI';
  
  const userDisp = document.getElementById('user-display-name');
  const userAv = document.getElementById('user-avatar');
  const dashName = document.getElementById('dash-user-name');
  
  if (userDisp) userDisp.textContent = name;
  if (userAv) userAv.textContent = initials;
  if (dashName) dashName.textContent = name;
}

function toggleAuthTab(tab) {
  const tabLogin = document.getElementById('tab-login');
  const tabReg = document.getElementById('tab-register');
  const formLogin = document.getElementById('login-form');
  const formReg = document.getElementById('register-form');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabReg.classList.remove('active');
    formLogin.classList.add('active');
    formReg.classList.remove('active');
  } else {
    tabReg.classList.add('active');
    tabLogin.classList.remove('active');
    formReg.classList.add('active');
    formLogin.classList.remove('active');
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    showToast('Signing in...');
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(formatAPIError(data) || 'Login failed');

    state.token = data.access_token;
    localStorage.setItem('token', state.token);
    state.user = data.user;
    updateUserUI();
    showToast('Welcome back!', 'success');
    navigateTo('dashboard');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const fullName = document.getElementById('register-name').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value;

  try {
    showToast('Creating account...');
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: fullName, email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(formatAPIError(data) || 'Registration failed');

    state.token = data.access_token;
    localStorage.setItem('token', state.token);
    state.user = data.user;
    updateUserUI();
    showToast('Account created successfully!', 'success');
    navigateTo('dashboard');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('token');
  cleanupStreams();
  navigateTo('auth');
  showToast('Signed out', 'info');
}

/* ═════════════════════════════════════════════════════════════════════════════
   ROUTING & NAVIGATION
   ═════════════════════════════════════════════════════════════════════════════ */
function navigateTo(viewName) {
  state.currentView = viewName;

  // Toggle Header visibility
  const header = document.getElementById('main-header');
  if (viewName === 'auth') {
    header.classList.add('hidden');
  } else {
    header.classList.remove('hidden');
  }

  // Update nav buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.nav === viewName) {
      btn.classList.add('active');
    }
  });

  // Hide all screens
  document.querySelectorAll('.app-screen').forEach(scr => scr.classList.remove('active'));

  // Show target screen
  const targetMap = {
    'auth': 'screen-auth',
    'dashboard': 'screen-dashboard',
    'cv-review': 'screen-cv-review',
    'setup': 'screen-interview-setup',
    'interview': 'screen-interview',
    'report': 'screen-report',
    'ats': 'screen-ats',
    'salary': 'screen-salary',
    'pitch': 'screen-pitch',
    'questions': 'screen-questions'
  };

  const targetId = targetMap[viewName] || `screen-${viewName}`;
  const targetElem = document.getElementById(targetId);
  if (targetElem) {
    targetElem.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Lifecycle triggers
  if (viewName === 'dashboard') {
    loadDashboard();
  } else if (viewName === 'cv-review') {
    loadCVReviewScreen();
  } else if (viewName === 'questions') {
    loadQuestionBank();
  } else if (viewName === 'ats') {
    populateATSResumesDropdown();
  }
}

function startInterviewMode(mode) {
  state.currentInterviewMode = mode;
  setSetupMode(mode);
  navigateTo('setup');
}

/* ═════════════════════════════════════════════════════════════════════════════
   DASHBOARD & CV PARSING
   ═════════════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const [resumes, interviews] = await Promise.all([
      fetchAPI('/resumes'),
      fetchAPI('/interviews')
    ]);

    renderResumesList(resumes);
    renderInterviewsList(interviews);
    populateSetupResumeDropdown(resumes);

    if (resumes && resumes.length > 0) {
      state.activeResumeId = resumes[0].id;
    }
  } catch (err) {
    console.error('Failed to load dashboard:', err);
  }
}

function triggerFileInput() {
  document.getElementById('file-input').click();
}

function handleCVFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  state.selectedCVFile = file;
  document.getElementById('selected-file-name').textContent = file.name;
  document.getElementById('selected-file-info').classList.remove('hidden');
  document.getElementById('btn-analyze-cv').disabled = false;
}

function clearSelectedFile(e) {
  e.stopPropagation();
  state.selectedCVFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('selected-file-info').classList.add('hidden');
  document.getElementById('btn-analyze-cv').disabled = true;
}

async function uploadAndAnalyzeCV() {
  if (!state.selectedCVFile) return;

  const btn = document.getElementById('btn-analyze-cv');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Parsing Resume & Matching JD...</span>';

  try {
    const formData = new FormData();
    formData.append('resume', state.selectedCVFile);
    formData.append('job_title', document.getElementById('cv-job-title').value.trim() || 'Full Stack AI Developer');

    const res = await fetch(`${API_BASE}/resumes/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(formatAPIError(data) || 'Upload failed');

    state.activeResumeId = data.id;
    showToast('Resume parsed and reviewed successfully!', 'success');

    const jdText = document.getElementById('cv-job-description')?.value.trim();
    let jdMatchData = null;
    if (jdText) {
      try {
        jdMatchData = await fetchAPI(`/resumes/${data.id}/match-jd`, {
          method: 'POST',
          body: JSON.stringify({ jd_text: jdText })
        });
      } catch (e) {}
    }

    renderCVReviewScreen(data, jdMatchData);
    loadDashboard();
    loadCVReviewScreen();
    document.getElementById('cv-audit-results')?.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡ Analyze Resume & Run Job Matcher</span>';
  }
}

async function loadCVReviewScreen() {
  try {
    const resumes = await fetchAPI('/resumes');
    const select = document.getElementById('cv-select-previous');
    if (select) {
      select.innerHTML = '<option value="">-- Upload New or Pick Previous CV --</option>' +
        resumes.map(r => `<option value="${r.id}">${r.filename} (${r.target_role || 'General'})</option>`).join('');
      if (state.activeResumeId) {
        select.value = state.activeResumeId;
      }
    }

    if (state.activeResumeId) {
      await fetchAndRenderCVReview(state.activeResumeId);
    } else if (resumes && resumes.length > 0) {
      state.activeResumeId = resumes[0].id;
      if (select) select.value = resumes[0].id;
      await fetchAndRenderCVReview(resumes[0].id);
    }
  } catch (err) {
    console.error('Failed to load CV review screen:', err);
  }
}

async function handleCVReviewResumeChange(resumeId) {
  if (!resumeId) return;
  state.activeResumeId = parseInt(resumeId, 10);
  await fetchAndRenderCVReview(state.activeResumeId);
}

async function fetchAndRenderCVReview(resumeId) {
  try {
    const data = await fetchAPI(`/resumes/${resumeId}/review`);
    const jdText = document.getElementById('cv-job-description')?.value.trim();
    let jdMatchData = null;
    if (jdText) {
      try {
        jdMatchData = await fetchAPI(`/resumes/${resumeId}/match-jd`, {
          method: 'POST',
          body: JSON.stringify({ jd_text: jdText })
        });
      } catch (e) {}
    }
    renderCVReviewScreen(data, jdMatchData);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openCVReviewScreen() {
  navigateTo('cv-review');
}

async function deleteResume(resumeId) {
  if (!confirm('Are you sure you want to delete this resume?')) return;
  try {
    await fetchAPI(`/resumes/${resumeId}`, { method: 'DELETE' });
    showToast('Resume deleted successfully', 'success');
    loadDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteInterview(interviewId) {
  if (!confirm('Are you sure you want to delete this interview history?')) return;
  try {
    await fetchAPI(`/interviews/${interviewId}`, { method: 'DELETE' });
    showToast('Interview deleted successfully', 'success');
    loadDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderResumesList(resumes) {
  const container = document.getElementById('resume-list-container');
  const countBadge = document.getElementById('resumes-count-badge');
  if (countBadge) countBadge.textContent = resumes.length;

  if (!resumes || resumes.length === 0) {
    container.innerHTML = `<div class="empty-state-card"><p>No resumes uploaded yet. Upload a CV above to get started!</p></div>`;
    return;
  }

  container.innerHTML = resumes.map(r => `
    <div class="resume-item-row">
      <div class="item-main-info">
        <h4>📄 ${r.filename}</h4>
        <span class="item-meta">Role: ${r.target_role || r.job_title || 'General'} • Score: ${r.score || r.cv_score || 75}/100</span>
      </div>
      <div class="item-actions">
        <button class="btn btn-sm btn-outline" onclick="viewParsedResume(${r.id})">Review</button>
        <button class="btn btn-sm btn-primary" onclick="launchInterviewWithResume(${r.id}, '${(r.target_role || r.job_title || 'Software Engineer').replace(/'/g, "\'")}')">Practice</button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteResume(${r.id})" title="Delete Resume">🗑️ Delete</button>
      </div>
    </div>
  `).join('');
}

function renderInterviewsList(interviews) {
  const container = document.getElementById('interview-list-container');
  if (!interviews || interviews.length === 0) {
    container.innerHTML = `<div class="empty-state-card"><p>No interviews completed yet. Launch a practice or mock interview above!</p></div>`;
    return;
  }

  container.innerHTML = interviews.map(i => `
    <div class="interview-item-row">
      <div class="item-main-info">
        <h4>${i.job_title}</h4>
        <span class="item-meta">${i.created_at ? new Date(i.created_at).toLocaleDateString() : 'Recent'} • Mode: ${i.mode === 'mock' || i.mode === 'simulation' || i.mode === 'direct' ? '🎙️ Pro Mock' : '🎯 Practice'}</span>
      </div>
      <div class="item-actions">
        <button class="btn btn-sm btn-outline" onclick="openCertificateModal(${i.id})">🎖️ Cert</button>
        <button class="btn btn-sm btn-primary" onclick="viewInterviewReport(${i.id})">Scorecard</button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteInterview(${i.id})" title="Delete Interview">🗑️ Delete</button>
      </div>
    </div>
  `).join('');
}

function populateSetupResumeDropdown(resumes) {
  const select = document.getElementById('setup-resume-select');
  if (!select) return;
  select.innerHTML = '<option value="">-- Auto Pick Latest Resume --</option>' +
    resumes.map(r => `<option value="${r.id}">${r.filename} (${r.target_role || r.job_title || 'General'})</option>`).join('');
}

function renderCVReviewScreen(resumeData, jdMatchData = null) {
  const parsed = resumeData.parsed_data || {};
  document.getElementById('cv-candidate-name').textContent = parsed.name || state.user?.full_name || 'Candidate';
  document.getElementById('cv-target-role').textContent = resumeData.target_role || resumeData.job_title || 'Software Engineer';
  document.getElementById('cv-overall-score').textContent = resumeData.score !== undefined ? resumeData.score : (resumeData.cv_score || 78);
  document.getElementById('cv-grade-badge').textContent = `Grade: ${resumeData.grade || 'B+'}`;
  document.getElementById('cv-exp-years').textContent = `${parsed.experience_years || 2}+ Years`;
  document.getElementById('cv-education').textContent = (Array.isArray(parsed.education) ? parsed.education.join(', ') : parsed.education) || 'B.S. in Computer Science';

  const wordCountElem = document.getElementById('cv-word-count');
  if (wordCountElem) {
    wordCountElem.textContent = `${resumeData.word_count || 380} words`;
  }

  // JD Match box
  const jdBox = document.getElementById('cv-jd-match-box');
  if (jdBox) {
    if (jdMatchData && jdMatchData.match_score !== undefined) {
      jdBox.classList.remove('hidden');
      document.getElementById('cv-jd-match-score').textContent = `${jdMatchData.match_score}%`;
      document.getElementById('cv-jd-match-desc').textContent = `Matched ${jdMatchData.matched_skills?.length || 0} skills against target job description.`;
      document.getElementById('cv-jd-matched-tags').innerHTML = (jdMatchData.matched_skills && jdMatchData.matched_skills.length > 0)
        ? jdMatchData.matched_skills.map(s => `<span class="kw-pill kw-matched">✓ ${s}</span>`).join(' ')
        : `<span style="font-size: 0.8rem; color: var(--text-muted);">None detected</span>`;
      document.getElementById('cv-jd-missing-tags').innerHTML = (jdMatchData.missing_skills && jdMatchData.missing_skills.length > 0)
        ? jdMatchData.missing_skills.map(s => `<span class="kw-pill kw-missing">⚠️ ${s}</span>`).join(' ')
        : `<span style="font-size: 0.8rem; color: var(--accent-emerald);">All required JD skills covered!</span>`;
    } else {
      jdBox.classList.add('hidden');
    }
  }

  // Section Checklist
  const sectionGrid = document.getElementById('cv-sections-checklist');
  if (sectionGrid) {
    const sections = resumeData.sections_found || {
      contact: true,
      summary: true,
      experience: true,
      education: true,
      skills: true,
      projects: true,
      certifications: false
    };
    const sectionNames = [
      { key: 'contact', label: 'Contact Info' },
      { key: 'summary', label: 'Professional Summary' },
      { key: 'experience', label: 'Work Experience' },
      { key: 'education', label: 'Education' },
      { key: 'skills', label: 'Skills & Tech' },
      { key: 'projects', label: 'Projects' },
      { key: 'certifications', label: 'Certifications' }
    ];
    sectionGrid.innerHTML = sectionNames.map(s => {
      const isPresent = Boolean(sections[s.key]);
      return `
        <div class="section-check-item ${isPresent ? 'present' : 'missing'}">
          <span class="chk-icon">${isPresent ? '✓' : '⚠️'}</span>
          <span class="chk-label">${s.label}</span>
          <span class="chk-status">${isPresent ? 'Found' : 'Missing'}</span>
        </div>
      `;
    }).join('');
  }

  // Skills List
  const skillsList = document.getElementById('cv-skills-list');
  const skills = parsed.skills || ['Python', 'FastAPI', 'JavaScript', 'SQL', 'Git'];
  if (skillsList) {
    skillsList.innerHTML = skills.map(s => `<span class="kw-pill">${s}</span>`).join('');
  }

  // Detected Mistakes / Issues
  const issuesContainer = document.getElementById('cv-issues-container');
  const issuesBadge = document.getElementById('cv-issues-count-badge');
  const issues = resumeData.issues || [];
  if (issuesBadge) {
    issuesBadge.textContent = `${issues.length} Issue${issues.length === 1 ? '' : 's'} Detected`;
  }
  if (issuesContainer) {
    if (issues.length === 0) {
      issuesContainer.innerHTML = `
        <div class="empty-issues-card">
          <span style="font-size: 1.5rem;">🎉</span>
          <p style="color: var(--accent-emerald); font-weight: 600;">No critical formatting or content mistakes found! Your CV looks strong.</p>
        </div>
      `;
    } else {
      issuesContainer.innerHTML = issues.map(iss => {
        const severity = (iss.severity || 'medium').toLowerCase();
        return `
          <div class="issue-card issue-${severity}">
            <div class="issue-card-top">
              <span class="issue-pill issue-pill-${severity}">${severity.toUpperCase()} PRIORITY</span>
              <span class="issue-type-tag">${(iss.type || 'ATS').toUpperCase()}</span>
            </div>
            <h4 class="issue-message">${iss.message}</h4>
            <div class="issue-suggestion-box">
              <span class="sugg-icon">💡 Fix:</span>
              <span class="sugg-text">${iss.suggestion}</span>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Strengths
  const strengthsList = document.getElementById('cv-strengths-list');
  const str = resumeData.strengths || ['Well-structured technical project descriptions', 'Strong foundational skills detected'];
  if (strengthsList) {
    strengthsList.innerHTML = str.map(s => `<li>${s}</li>`).join('');
  }

  // Improvement Recommendations
  const impList = document.getElementById('cv-improvements-list');
  const imp = resumeData.improvement_plan || resumeData.improvements || ['Add quantifiable metrics (e.g. 35% latency reduction)', 'Include recent cloud certifications'];
  if (impList) {
    impList.innerHTML = imp.map(i => `<li>${i}</li>`).join('');
  }
}

async function viewParsedResume(resumeId) {
  try {
    state.activeResumeId = resumeId;
    navigateTo('cv-review');
    await fetchAndRenderCVReview(resumeId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function proceedToInterviewFromCV() {
  setSetupMode('practice');
  const role = document.getElementById('cv-target-role')?.textContent || document.getElementById('dash-cv-role')?.textContent;
  if (role) document.getElementById('setup-job-title').value = role;
  if (state.activeResumeId) {
    document.getElementById('setup-resume-select').value = state.activeResumeId;
  }
  navigateTo('setup');
}

function launchInterviewWithResume(resumeId, role) {
  state.activeResumeId = resumeId;
  setSetupMode('practice');
  document.getElementById('setup-job-title').value = role;
  document.getElementById('setup-resume-select').value = resumeId;
  navigateTo('setup');
}

/* ═════════════════════════════════════════════════════════════════════════════
   INTERVIEW SETUP & SESSION START
   ═════════════════════════════════════════════════════════════════════════════ */
function setSetupMode(mode) {
  state.currentInterviewMode = mode;
  const optPractice = document.getElementById('mode-opt-practice');
  const optMock = document.getElementById('mode-opt-mock');
  const setupBadge = document.getElementById('setup-mode-badge');
  const setupTitle = document.getElementById('setup-title');

  if (mode === 'practice') {
    optPractice.classList.add('active');
    optMock.classList.remove('active');
    setupBadge.textContent = '🎯 Guided Practice Setup';
    setupBadge.className = 'screen-title-badge pill-mint';
    setupTitle.textContent = 'Configure Your Practice Session';
  } else {
    optMock.classList.add('active');
    optPractice.classList.remove('active');
    setupBadge.textContent = '🎙️ Pro Mock Interview Setup';
    setupBadge.className = 'screen-title-badge pill-emerald';
    setupTitle.textContent = 'Configure Your Mock Simulation';
  }
}

async function startInterviewSession() {
  const jobTitle = document.getElementById('setup-job-title').value.trim() || 'Full Stack AI Developer';
  const resumeId = document.getElementById('setup-resume-select').value || null;
  const questionCount = parseInt(document.getElementById('setup-question-count').value, 10) || 5;
  const difficulty = document.getElementById('setup-difficulty').value || 'Mid-Level';

  const btn = document.getElementById('btn-start-session');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Generating Tailored AI Questions...</span>';

  try {
    const payload = {
      job_title: jobTitle,
      resume_id: resumeId ? parseInt(resumeId, 10) : null,
      question_count: questionCount,
      difficulty: difficulty,
      mode: state.currentInterviewMode
    };

    const data = await fetchAPI('/interviews', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    state.activeInterview = data;
    state.currentQuestionIndex = 0;
    initializeActiveInterviewUI();
    navigateTo('interview');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🚀 Begin Interview Session</span>';
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   ACTIVE INTERVIEW ARENA & VOICE ENGINE
   ═════════════════════════════════════════════════════════════════════════════ */
function initializeActiveInterviewUI() {
  const interview = state.activeInterview;
  if (!interview) return;

  const modePill = document.getElementById('interview-active-mode-pill');
  if (state.currentInterviewMode === 'practice') {
    modePill.textContent = '🎯 Practice Mode (Guided)';
    modePill.className = 'mode-indicator-pill pill-mint';
    document.getElementById('practice-guidance-box').classList.remove('hidden');
  } else {
    modePill.textContent = '🎙️ Pro Mock Simulation';
    modePill.className = 'mode-indicator-pill pill-emerald';
    document.getElementById('practice-guidance-box').classList.add('hidden');
  }

  document.getElementById('interview-role-display').textContent = interview.job_title;
  startInterviewTimer();
  startCameraPreview();
  renderCurrentQuestion();
}

function renderCurrentQuestion() {
  const interview = state.activeInterview;
  if (!interview || !interview.questions) return;

  const q = interview.questions[state.currentQuestionIndex];
  if (!q) return;

  const total = interview.questions.length;
  const currentNum = state.currentQuestionIndex + 1;

  document.getElementById('question-progress-text').textContent = `Question ${currentNum} of ${total}`;
  document.getElementById('question-progress-bar').style.width = `${(currentNum / total) * 100}%`;
  document.getElementById('q-category-tag').textContent = (q.type || q.category || 'TECHNICAL').toUpperCase();
  document.getElementById('active-question-text').textContent = q.question;

  // Reset transcript & answer inputs
  document.getElementById('transcript-content').textContent = '';
  document.getElementById('transcript-placeholder').classList.remove('hidden');
  document.getElementById('manual-answer-input').value = '';
  document.getElementById('btn-submit-answer').disabled = true;
  document.getElementById('btn-re-record').disabled = true;
  document.getElementById('model-answer-text').textContent = 'Fetching model answer guidance...';

  // Load Model Answer in Practice Mode
  if (state.currentInterviewMode === 'practice') {
    loadModelAnswerForCurrentQuestion();
  }
}

async function loadModelAnswerForCurrentQuestion() {
  try {
    const data = await fetchAPI(`/interviews/${state.activeInterview.id}/model-answer?question_index=${state.currentQuestionIndex}`);
    const concepts = data.key_concepts || ['STAR Framework', 'Clear Explanation', 'Problem Solving'];
    document.getElementById('model-answer-text').innerHTML = `
      <p><strong>Recommended Model Answer:</strong> ${data.model_answer}</p>
      <div style="margin-top: 0.6rem;">
        <strong>Key Keywords:</strong> ${concepts.map(c => `<span class="kw-pill">${c}</span>`).join(' ')}
      </div>
    `;
  } catch (err) {
    document.getElementById('model-answer-text').textContent = 'Structure your response using the STAR method (Situation, Task, Action, Result).';
  }
}

function togglePracticeGuidance() {
  const body = document.getElementById('practice-drawer-body');
  const arrow = document.getElementById('practice-drawer-arrow');
  if (body.classList.contains('hidden')) {
    body.classList.remove('hidden');
    arrow.textContent = '▲';
  } else {
    body.classList.add('hidden');
    arrow.textContent = '▼';
  }
}

function toggleFallbackTextInput() {
  const drawer = document.getElementById('fallback-text-drawer');
  drawer.classList.toggle('hidden');
  const input = document.getElementById('manual-answer-input');
  input.oninput = () => {
    document.getElementById('btn-submit-answer').disabled = input.value.trim().length === 0;
  };
}

/* ═════════════════════════════════════════════════════════════════════════════
   AUDIO & SPEECH RECOGNITION (WHISPER AI + LIBROSA ENGINE)
   ═════════════════════════════════════════════════════════════════════════════ */
async function toggleAudioRecording() {
  if (!state.isRecording) {
    await startAudioRecording();
  } else {
    stopAudioRecording();
  }
}

async function startAudioRecording() {
  try {
    state.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(state.audioStream);

    setupAudioVisualizer(state.audioStream);

    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.start();
    state.isRecording = true;

    // UI Updates
    const btn = document.getElementById('btn-record-toggle');
    btn.classList.add('recording');
    document.getElementById('btn-record-label').textContent = 'Stop Recording';
    document.getElementById('rec-dot-indicator').classList.add('recording');
    document.getElementById('rec-status-label').textContent = 'Recording Active...';
    document.getElementById('transcript-placeholder').classList.add('hidden');
    document.getElementById('wave-visualizer').classList.add('active');

    // Silence Toast Detection
    startSilenceMonitoring();

    // Live Web Speech Recognition (Visual Preview)
    startLiveSpeechRecognitionPreview();
  } catch (err) {
    showToast('Microphone access note: ' + err.message, 'info');
  }
}

function stopAudioRecording() {
  if (!state.isRecording || !state.mediaRecorder) return;

  state.mediaRecorder.stop();
  state.isRecording = false;
  clearTimeout(state.silenceTimer);
  hideSilenceToast();

  const btn = document.getElementById('btn-record-toggle');
  btn.classList.remove('recording');
  document.getElementById('btn-record-label').textContent = 'Start Speaking';
  document.getElementById('rec-dot-indicator').classList.remove('recording');
  document.getElementById('rec-status-label').textContent = 'Audio Captured';
  document.getElementById('wave-visualizer').classList.remove('active');
  document.getElementById('btn-submit-answer').disabled = false;
  document.getElementById('btn-re-record').disabled = false;
}

function discardAndReRecord() {
  state.audioChunks = [];
  document.getElementById('transcript-content').textContent = '';
  document.getElementById('transcript-placeholder').classList.remove('hidden');
  document.getElementById('btn-submit-answer').disabled = true;
  document.getElementById('btn-re-record').disabled = true;
  startAudioRecording();
}

function setupAudioVisualizer(stream) {
  try {
    state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    state.analyser = state.audioContext.createAnalyser();
    const source = state.audioContext.createMediaStreamSource(stream);
    source.connect(state.analyser);
    state.analyser.fftSize = 64;
  } catch (e) {
    console.warn('Web Audio visualizer not supported', e);
  }
}

function startSilenceMonitoring() {
  clearTimeout(state.silenceTimer);
  state.silenceTimer = setTimeout(() => {
    if (state.isRecording) {
      document.getElementById('silence-alert-toast').classList.remove('hidden');
    }
  }, 3500);
}

function hideSilenceToast() {
  document.getElementById('silence-alert-toast').classList.add('hidden');
}

let speechRecognizer = null;
function startLiveSpeechRecognitionPreview() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  speechRecognizer = new SpeechRecognition();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = 'en-US';

  speechRecognizer.onresult = (event) => {
    hideSilenceToast();
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      interimText += event.results[i][0].transcript;
    }
    document.getElementById('transcript-content').textContent = interimText;
    document.getElementById('btn-submit-answer').disabled = false;
  };

  speechRecognizer.onerror = (e) => {
    console.warn('Speech recognition preview:', e.error);
  };

  try {
    speechRecognizer.start();
  } catch (e) {}
}

function playQuestionTTS() {
  const qText = document.getElementById('active-question-text').textContent;
  if (!('speechSynthesis' in window)) {
    showToast('TTS not supported in this browser.', 'info');
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(qText);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

/* ═════════════════════════════════════════════════════════════════════════════
   ANSWER SUBMISSION & QUESTION NAVIGATION
   ═════════════════════════════════════════════════════════════════════════════ */
async function submitCurrentAnswer() {
  if (state.isRecording) {
    stopAudioRecording();
  }

  const btn = document.getElementById('btn-submit-answer');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Evaluating Answer...</span>';

  try {
    const formData = new FormData();
    const qNum = state.currentQuestionIndex + 1;
    formData.append('question_number', qNum.toString());
    formData.append('question_index', state.currentQuestionIndex.toString());

    const manualText = document.getElementById('manual-answer-input').value.trim();
    const speechText = document.getElementById('transcript-content').textContent.trim();
    const answerText = manualText || speechText || 'I discussed my technical implementation and background.';

    formData.append('answer_text', answerText);

    if (state.audioChunks.length > 0) {
      const audioBlob = new Blob(state.audioChunks, { type: 'audio/wav' });
      formData.append('audio', audioBlob, 'answer.wav');
    }

    const res = await fetch(`${API_BASE}/interviews/${state.activeInterview.id}/answer`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(formatAPIError(data) || 'Evaluation failed');

    const scoreVal = Math.round(data.content_score || data.combined_score || 80);
    showToast(`Answer recorded! Score: ${scoreVal}/100`, 'success');
    advanceToNextQuestion();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Submit Answer</span> ➔';
  }
}

async function skipCurrentQuestion() {
  try {
    showToast('Question skipped', 'info');
    await fetchAPI(`/interviews/${state.activeInterview.id}/skip`, {
      method: 'POST',
      body: JSON.stringify({ question_index: state.currentQuestionIndex })
    });
    advanceToNextQuestion();
  } catch (err) {
    advanceToNextQuestion();
  }
}

function advanceToNextQuestion() {
  state.currentQuestionIndex++;
  if (state.currentQuestionIndex < state.activeInterview.questions.length) {
    renderCurrentQuestion();
  } else {
    finishInterviewAndShowReport();
  }
}

async function finishInterviewAndShowReport() {
  stopInterviewTimer();
  cleanupStreams();
  showToast('Interview completed! Generating scorecard...', 'success');
  viewInterviewReport(state.activeInterview.id);
}

function confirmExitInterview() {
  if (confirm('Are you sure you want to exit? Your progress will be saved.')) {
    stopInterviewTimer();
    cleanupStreams();
    navigateTo('dashboard');
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   VIDEO PREVIEW & TIMER
   ═════════════════════════════════════════════════════════════════════════════ */
async function startCameraPreview() {
  try {
    state.webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const video = document.getElementById('webcam-preview');
    video.srcObject = state.webcamStream;
    document.getElementById('camera-overlay').classList.add('hidden');
  } catch (e) {
    console.warn('Webcam preview not available:', e);
    document.getElementById('camera-overlay').classList.remove('hidden');
  }
}

function toggleCamera() {
  if (state.webcamStream) {
    state.webcamStream.getTracks().forEach(t => t.stop());
    state.webcamStream = null;
    document.getElementById('camera-overlay').classList.remove('hidden');
  } else {
    startCameraPreview();
  }
}

function startInterviewTimer() {
  state.interviewSeconds = 0;
  clearInterval(state.interviewTimerInterval);
  state.interviewTimerInterval = setInterval(() => {
    state.interviewSeconds++;
    const mins = String(Math.floor(state.interviewSeconds / 60)).padStart(2, '0');
    const secs = String(state.interviewSeconds % 60).padStart(2, '0');
    document.getElementById('interview-timer-display').textContent = `⏱️ ${mins}:${secs}`;
  }, 1000);
}

function stopInterviewTimer() {
  clearInterval(state.interviewTimerInterval);
}

function cleanupStreams() {
  if (state.audioStream) {
    state.audioStream.getTracks().forEach(t => t.stop());
    state.audioStream = null;
  }
  if (state.webcamStream) {
    state.webcamStream.getTracks().forEach(t => t.stop());
    state.webcamStream = null;
  }
  if (speechRecognizer) {
    try { speechRecognizer.stop(); } catch (e) {}
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   PERFORMANCE REPORT & SCORECARD
   ═════════════════════════════════════════════════════════════════════════════ */
async function viewInterviewReport(interviewId) {
  try {
    const report = await fetchAPI(`/interviews/${interviewId}/report`);
    renderReportScreen(report);
    navigateTo('report');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderReportScreen(report) {
  document.getElementById('report-job-title').textContent = report.job_title || 'Full Stack AI Developer';
  document.getElementById('report-date').textContent = new Date(report.created_at || Date.now()).toLocaleDateString();

  const score = report.overall_score || 82.5;
  document.getElementById('report-overall-score').textContent = score;
  document.getElementById('report-grade-pill').textContent = `Grade: ${report.grade || 'A'}`;

  document.getElementById('bar-content-score').style.width = `${report.content_score || 80}%`;
  document.getElementById('val-content-score').textContent = `${report.content_score || 80}/100`;

  document.getElementById('bar-confidence-score').style.width = `${report.confidence_score || 85}%`;
  document.getElementById('val-confidence-score').textContent = `${report.confidence_score || 85}/100`;

  document.getElementById('bar-pace-score').style.width = `${Math.min(100, (report.pace_wpm || 135) / 1.6)}%`;
  document.getElementById('val-pace-score').textContent = `${report.pace_wpm || 135} WPM`;

  const strList = document.getElementById('report-strengths-list');
  const str = report.strengths || ['Good clarity and structured STAR answers', 'Technical vocabulary was well-applied'];
  strList.innerHTML = str.map(s => `<li>${s}</li>`).join('');

  const impList = document.getElementById('report-improvements-list');
  const imp = report.improvements || ['Maintain consistent speaking pace throughout complex answers', 'Provide more concrete metrics in behavioral responses'];
  impList.innerHTML = imp.map(i => `<li>${i}</li>`).join('');

  const qBreakdown = document.getElementById('report-questions-breakdown');
  if (report.questions && report.questions.length > 0) {
    qBreakdown.innerHTML = report.questions.map((q, idx) => `
      <div class="q-review-item">
        <div class="q-review-header">
          <span>Q${idx + 1}: ${q.question}</span>
          <span class="kw-pill">Score: ${q.score || 80}/100</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.4rem;">
          <strong>Your Answer:</strong> ${q.user_answer || 'Covered key concepts.'}
        </p>
        <p style="font-size: 0.85rem; color: var(--accent-mint);">
          <strong>AI Feedback:</strong> ${q.feedback || 'Good coverage of core topics.'}
        </p>
      </div>
    `).join('');
  }
}

function printOrDownloadReport() {
  window.print();
}

/* ═════════════════════════════════════════════════════════════════════════════
   TOOL 1: ATS RESUME TAILOR & KEYWORD MATCHER
   ═════════════════════════════════════════════════════════════════════════════ */
async function populateATSResumesDropdown() {
  try {
    const resumes = await fetchAPI('/resumes');
    const select = document.getElementById('ats-resume-select');
    select.innerHTML = '<option value="">-- Use Latest Parsed Resume --</option>' +
      resumes.map(r => `<option value="${r.id}">${r.filename} (${r.target_role || 'General'})</option>`).join('');
  } catch (err) {}
}

function handleATSResumeChange() {
  // Trigger
}

async function runATSScanner() {
  const resumeId = document.getElementById('ats-resume-select').value || null;
  const targetRole = document.getElementById('ats-job-title').value.trim() || 'Software Engineer';
  const jdText = document.getElementById('ats-jd-input').value.trim();

  if (!jdText) {
    showToast('Please paste a Job Description to scan.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-run-ats');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Scanning Keywords & Generating Bullets...</span>';

  try {
    const payload = {
      resume_id: resumeId ? parseInt(resumeId, 10) : null,
      target_role: targetRole,
      job_description: jdText
    };

    const data = await fetchAPI('/tools/ats-optimizer', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    document.getElementById('ats-empty-state').classList.add('hidden');
    document.getElementById('ats-results-content').classList.remove('hidden');

    document.getElementById('ats-match-score').textContent = `${data.match_score}%`;
    document.getElementById('ats-summary-text').textContent = `Matched ${data.matched_skills.length} out of ${data.total_jd_keywords} critical industry keywords.`;

    document.getElementById('ats-matched-count').textContent = data.matched_skills.length;
    document.getElementById('ats-matched-tags').innerHTML = (data.matched_skills.length > 0)
      ? data.matched_skills.map(s => `<span class="kw-pill kw-matched">✓ ${s}</span>`).join('')
      : `<span style="font-size: 0.8rem; color: var(--text-muted);">None detected in current resume</span>`;

    document.getElementById('ats-missing-count').textContent = data.missing_skills.length;
    document.getElementById('ats-missing-tags').innerHTML = (data.missing_skills.length > 0)
      ? data.missing_skills.map(s => `<span class="kw-pill kw-missing">⚠ ${s}</span>`).join('')
      : `<span style="font-size: 0.8rem; color: var(--accent-emerald);">All major skills covered!</span>`;

    const bulletsContainer = document.getElementById('ats-bullets-container');
    bulletsContainer.innerHTML = data.suggested_bullets.map(b => `
      <div class="bullet-card">
        <p>${b}</p>
        <button class="btn-copy-bullet" onclick="navigator.clipboard.writeText('${b.replace(/'/g, "\\\'")}'); showToast('Copied to clipboard!', 'success');">📋 Copy Bullet</button>
      </div>
    `).join('');

    showToast('ATS Scan complete!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡ Run ATS Scan & Generate Bullets</span>';
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   TOOL 2: SALARY NEGOTIATION COACH
   ═════════════════════════════════════════════════════════════════════════════ */
async function runSalaryNegotiator() {
  const jobTitle = document.getElementById('salary-job-title').value.trim() || 'Software Engineer';
  const initialOffer = parseFloat(document.getElementById('salary-initial-offer').value) || 95000;
  const targetOffer = parseFloat(document.getElementById('salary-target-offer').value) || 120000;
  const strategy = document.getElementById('salary-strategy').value;
  const userPitch = document.getElementById('salary-user-pitch').value.trim();

  if (!userPitch) {
    showToast('Please enter your counter-offer pitch.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-run-salary');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Recruiter is evaluating...</span>';

  try {
    const payload = {
      job_title: jobTitle,
      initial_offer: initialOffer,
      target_offer: targetOffer,
      candidate_pitch: userPitch,
      candidate_message: userPitch,
      strategy: strategy
    };

    const data = await fetchAPI('/tools/salary-negotiator', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    document.getElementById('salary-empty-state').classList.add('hidden');
    document.getElementById('salary-results-content').classList.remove('hidden');

    const revisedVal = Math.round(data.revised_offer || targetOffer);
    document.getElementById('salary-recruiter-offer').textContent = `$${revisedVal.toLocaleString()}`;
    document.getElementById('salary-recruiter-text').textContent = `"${data.recruiter_response || data.ai_response}"`;
    document.getElementById('salary-tactic-score').textContent = `Tactic Score: ${Math.round(data.tactic_score || data.negotiation_score || 85)}/100`;

    const tipsList = document.getElementById('salary-tips-list');
    const feedbackArr = data.tactical_feedback || data.feedback || ['Clear articulation of technical value.'];
    tipsList.innerHTML = feedbackArr.map(f => `<li>${f}</li>`).join('');

    showToast('Recruiter countered your offer!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>💬 Submit Counter-Offer</span>';
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   TOOL 3: 60-SECOND ELEVATOR PITCH ARENA
   ═════════════════════════════════════════════════════════════════════════════ */
async function runPitchEvaluator() {
  const jobTitle = document.getElementById('pitch-job-title').value.trim() || 'Software Developer';
  const pitchText = document.getElementById('pitch-text-input').value.trim();

  if (!pitchText) {
    showToast('Please type your elevator pitch script.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-run-pitch');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Analyzing Pacing & Hook...</span>';

  try {
    const payload = {
      job_title: jobTitle,
      pitch_text: pitchText,
      duration_seconds: 45.0
    };

    const data = await fetchAPI('/tools/elevator-pitch', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    document.getElementById('pitch-empty-state').classList.add('hidden');
    document.getElementById('pitch-results-content').classList.remove('hidden');

    document.getElementById('pitch-overall-val').textContent = `${data.overall_score}/100`;
    document.getElementById('pitch-wpm-val').textContent = `${data.estimated_wpm} WPM`;
    document.getElementById('pitch-hook-val').textContent = `${data.hook_score}%`;
    document.getElementById('pitch-clarity-val').textContent = `${data.clarity_score}%`;

    document.getElementById('pitch-polished-text').textContent = data.polished_version;

    showToast('Pitch analyzed successfully!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡ Analyze My Pitch</span>';
  }
}

function copyPolishedPitch() {
  const text = document.getElementById('pitch-polished-text').textContent;
  navigator.clipboard.writeText(text);
  showToast('Polished pitch copied!', 'success');
}

/* ═════════════════════════════════════════════════════════════════════════════
   TOOL 4: QUESTION BANK & FLASHCARDS
   ═════════════════════════════════════════════════════════════════════════════ */
async function loadQuestionBank() {
  const role = document.getElementById('qbank-role-select')?.value || 'Full Stack AI Developer';
  try {
    const data = await fetchAPI(`/tools/question-bank?job_title=${encodeURIComponent(role)}`);
    state.questionBankData = data.questions || [];
    renderQuestionBankCards(state.questionBankData);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function filterQuestionBank(category) {
  document.querySelectorAll('.cat-pill').forEach(p => {
    p.classList.remove('active');
    if (p.textContent.includes(category) || (category === 'All' && p.textContent.includes('All'))) {
      p.classList.add('active');
    }
  });

  if (category === 'All') {
    renderQuestionBankCards(state.questionBankData);
  } else {
    const filtered = state.questionBankData.filter(q => q.category === category);
    renderQuestionBankCards(filtered);
  }
}

function renderQuestionBankCards(questions) {
  const container = document.getElementById('qbank-grid-cards');
  if (!container) return;

  if (!questions || questions.length === 0) {
    container.innerHTML = `<div class="empty-state-card"><p>No questions found for this topic.</p></div>`;
    return;
  }

  container.innerHTML = questions.map((q, idx) => `
    <div class="qcard">
      <div class="qcard-top">
        <span class="q-category-tag">${q.category}</span>
        <span class="diff-tag diff-${q.difficulty}">${q.difficulty}</span>
      </div>
      <h4>${q.question}</h4>
      <div class="qcard-concepts">
        ${(q.key_concepts || []).map(c => `<span class="concept-badge">#${c}</span>`).join('')}
      </div>
      <details>
        <summary style="cursor: pointer; font-size: 0.82rem; color: var(--accent-mint); font-weight: 700;">💡 Reveal Model Answer</summary>
        <div class="qcard-answer-box">
          ${q.model_answer}
        </div>
      </details>
    </div>
  `).join('');
}

/* ═════════════════════════════════════════════════════════════════════════════
   TOOL 5: VERIFIED CERTIFICATE MODAL
   ═════════════════════════════════════════════════════════════════════════════ */
async function openCertificateModal(interviewId) {
  const targetId = interviewId || (state.activeInterview ? state.activeInterview.id : null);
  if (!targetId) {
    showToast('Please complete an interview first to generate a certificate.', 'info');
    return;
  }

  try {
    const cert = await fetchAPI(`/tools/certificate/${targetId}`);
    document.getElementById('cert-candidate-name').textContent = cert.candidate_name || state.user?.full_name || 'Candidate';
    document.getElementById('cert-job-role').textContent = cert.job_title;
    document.getElementById('cert-score-val').textContent = `${cert.overall_score}/100`;
    document.getElementById('cert-grade-val').textContent = `Grade ${cert.grade}`;
    document.getElementById('cert-date-val').textContent = cert.issue_date;
    document.getElementById('cert-hash-val').textContent = cert.certificate_id;

    document.getElementById('modal-certificate').classList.remove('hidden');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function closeCertificateModal(e) {
  if (e) e.stopPropagation();
  document.getElementById('modal-certificate').classList.add('hidden');
}

function printCertificate() {
  window.print();
}

function downloadCertificatePDF() {
  showToast('Opening print dialog... Select "Save as PDF" to download your verified certificate.', 'info');
  setTimeout(() => {
    window.print();
  }, 400);
}

/* ═════════════════════════════════════════════════════════════════════════════
   UTILITIES & TOASTS (ROBUST STRING FORMATTER)
   ═════════════════════════════════════════════════════════════════════════════ */
function formatAPIError(errData) {
  if (!errData) return 'API request failed';
  if (typeof errData === 'string') return errData;
  if (errData.detail) {
    if (Array.isArray(errData.detail)) {
      return errData.detail.map(d => d.msg || (d.loc ? d.loc.join('.') : '')).join(' | ');
    }
    if (typeof errData.detail === 'string') return errData.detail;
    return JSON.stringify(errData.detail);
  }
  if (errData.message) return errData.message;
  return JSON.stringify(errData);
}

async function fetchAPI(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errMsg = formatAPIError(data);
    throw new Error(errMsg);
  }
  return data;
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  let text = message;
  if (typeof message === 'object' && message !== null) {
    text = formatAPIError(message);
  }

  const toast = document.createElement('div');
  toast.className = `toast-message toast-${type}`;
  toast.textContent = text;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
