/* ── Auth state ── */
const auth = {
  token: localStorage.getItem("px_token") || null,
  user:  JSON.parse(localStorage.getItem("px_user") || "null"),
};

function saveAuth(token, user) {
  auth.token = token;
  auth.user  = user;
  localStorage.setItem("px_token", token);
  localStorage.setItem("px_user", JSON.stringify(user));
}

function clearAuth() {
  auth.token = null;
  auth.user  = null;
  localStorage.removeItem("px_token");
  localStorage.removeItem("px_user");
}

function authHeaders() {
  return auth.token ? { "Authorization": `Bearer ${auth.token}` } : {};
}

/* ── Case state ── */
const state = {
  step: 1,
  userType: null,
  caseId: null,
  docResults: {},
  reviewResult: null,
  creditResult: null,
  reportBlob: null,
  reportPassword: null,
  reportSummary: null,
};

/* ── Doc requirements per user type ── */
const DOC_MATRIX = {
  Employee: [
    { id: "payslips",  label: "Payslips",           sub: "3–6 months" },
    { id: "bankstmt",  label: "Personal Bank Statements", sub: "3–6 months, must match payslip timeline" },
    { id: "epf",       label: "EPF Statement",       sub: "Latest" },
    { id: "ea",        label: "EA Form / Form BE",   sub: "Most recent year" },
  ],
  Businessman: [
    { id: "ssm",       label: "SSM Full Set",        sub: "Company registration documents" },
    { id: "co_bank",   label: "Company Bank Statements", sub: "6–12 months" },
    { id: "tax",       label: "Income Tax Forms",    sub: "2 years preferred" },
    { id: "form_be_b", label: "Form BE / Form B",    sub: "Director Fee or Sole Prop/Partnership" },
  ],
  Hybrid: [
    { id: "payslips",  label: "Payslips",            sub: "3–6 months" },
    { id: "bankstmt",  label: "Personal Bank Statements", sub: "3–6 months" },
    { id: "epf",       label: "EPF Statement",        sub: "Latest" },
    { id: "ea",        label: "EA Form / Form BE",    sub: "Employment income" },
    { id: "ssm",       label: "SSM Full Set",         sub: "Company registration" },
    { id: "co_bank",   label: "Company Bank Statements", sub: "6–12 months" },
    { id: "tax",       label: "Income Tax Forms",     sub: "2 years preferred" },
    { id: "form_be_b", label: "Form BE / Form B",     sub: "Business income" },
  ],
};

/* ── Rendering ── */
function render() {
  updateStepper();
  const views = {
    1: renderStep1,
    2: renderStep2,
    3: renderStep3,
    4: renderStep4,
    5: renderStep5,
  };
  document.getElementById("view").innerHTML = "";
  views[state.step]();
}

function updateStepper() {
  document.querySelectorAll(".step").forEach((el, i) => {
    const n = i + 1;
    el.classList.toggle("active", n === state.step);
    el.classList.toggle("done", n < state.step);
  });
}

/* Step 1 — User type selection */
function renderStep1() {
  const view = document.getElementById("view");
  view.innerHTML = `
    <div class="card">
      <h2>Who is this case for?</h2>
      <p class="hint">Select the profile that best describes the customer's income source.</p>
      <div class="type-grid">
        ${["Employee","Businessman","Hybrid"].map(t => `
          <div class="type-btn ${state.userType===t?'selected':''}" data-type="${t}">
            <div class="icon">${{Employee:"👔",Businessman:"🏢",Hybrid:"⚖️"}[t]}</div>
            <div class="label">${t}</div>
            <div class="desc">${{
              Employee:"Salaried, EPF contributor",
              Businessman:"SSM-registered, self-employed",
              Hybrid:"Director fee + employment income"
            }[t]}</div>
          </div>`).join("")}
      </div>
      <div class="action-row">
        <button class="btn btn-primary" id="next1" ${!state.userType?"disabled":""}>
          Continue →
        </button>
      </div>
    </div>`;

  view.querySelectorAll(".type-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.userType = btn.dataset.type;
      state.docResults = {};
      render();
    });
  });
  document.getElementById("next1")?.addEventListener("click", async () => {
    const meta = { age: null, profession: null, location: null, declared_income: null };
    const fd = new FormData();
    fd.append("user_type", state.userType);
    fd.append("customer_meta", JSON.stringify(meta));
    const res = await fetch("/cases/create", { method: "POST", headers: authHeaders(), body: fd });
    if (res.status === 401) { clearAuth(); renderAuthGate(); return; }
    const data = await res.json();
    state.caseId = data.case_id;
    state.step = 2; render();
  });
}

/* Step 2 — Document uploads */
function renderStep2() {
  const docs = DOC_MATRIX[state.userType];
  const view = document.getElementById("view");
  view.innerHTML = `
    <div class="card">
      <h2>Upload Documents</h2>
      <p class="hint">Upload each document one at a time. Each will be validated before the next.</p>
      <div class="upload-list" id="upload-list">
        ${docs.map(d => renderDocItem(d)).join("")}
      </div>
      <div class="action-row">
        <button class="btn btn-ghost" id="back2">← Back</button>
        <button class="btn btn-primary" id="next2" ${allPassed(docs)?"":"disabled"}>
          Proceed to Review →
        </button>
      </div>
    </div>`;

  docs.forEach(d => bindUpload(d));
  document.getElementById("back2").addEventListener("click", () => { state.step = 1; render(); });
  document.getElementById("next2")?.addEventListener("click", () => { state.step = 3; runReview(); });
}

function renderDocItem(doc) {
  const r = state.docResults[doc.id];
  const chip = r
    ? `<span class="status-chip chip-${r.status.toLowerCase()}">${r.status}</span>`
    : `<span class="status-chip chip-pending">Pending</span>`;
  return `
    <div class="upload-item" id="item-${doc.id}">
      <div style="flex:1">
        <div class="doc-label">${doc.label}</div>
        <div class="doc-sub">${doc.sub}</div>
        ${r?.reason ? `<div style="font-size:.74rem;color:#64748b;margin-top:3px">${r.reason}</div>` : ""}
      </div>
      ${chip}
      <label class="upload-btn" for="file-${doc.id}">
        ${r ? "Re-upload" : "Choose File"}
      </label>
      <input type="file" id="file-${doc.id}" accept=".pdf,.jpg,.png" data-docid="${doc.id}">
    </div>`;
}

function bindUpload(doc) {
  document.getElementById(`file-${doc.id}`)?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setChip(doc.id, "loading", "Validating…");
    const result = await uploadDoc(file, doc.id);
    if (result.status === "ENCRYPTED") {
      promptPassword(file, doc);
    } else {
      state.docResults[doc.id] = result;
      refreshUploadList();
    }
  });
}

async function uploadDoc(file, docId, password = null) {
  const fd = new FormData();
  fd.append("case_id", state.caseId);
  fd.append("doc_id", docId);
  fd.append("file", file);
  if (password) fd.append("password", password);
  try {
    const res = await fetch("/cases/upload-doc", { method: "POST", headers: authHeaders(), body: fd });
    if (res.status === 401) { clearAuth(); renderAuthGate(); return { status: "FAIL", reason: "Session expired." }; }
    return await res.json();
  } catch {
    return { status: "FAIL", reason: "Network error.", action_required: null };
  }
}

function promptPassword(file, doc) {
  const overlay = document.createElement("div");
  overlay.className = "overlay";
  overlay.innerHTML = `
    <div class="modal">
      <h3>🔒 Encrypted Document</h3>
      <p>This PDF is password-protected. Enter the password to proceed.</p>
      <input type="text" id="pw-input" placeholder="Enter password" autocomplete="off">
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" id="pw-ok" style="flex:1">Unlock</button>
        <button class="btn btn-ghost" id="pw-cancel">Cancel</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  document.getElementById("pw-cancel").onclick = () => {
    overlay.remove();
    setChip(doc.id, "pending", "");
  };
  document.getElementById("pw-ok").onclick = async () => {
    const pw = document.getElementById("pw-input").value;
    overlay.remove();
    setChip(doc.id, "loading", "Decrypting…");
    const result = await uploadDoc(file, doc.id, pw);
    state.docResults[doc.id] = result;
    refreshUploadList();
  };
}

function setChip(docId, status, reason) {
  state.docResults[docId] = { status: status.toUpperCase(), reason };
  refreshUploadList();
}

function refreshUploadList() {
  const docs = DOC_MATRIX[state.userType];
  document.getElementById("upload-list").innerHTML = docs.map(d => renderDocItem(d)).join("");
  docs.forEach(d => bindUpload(d));
  const next = document.getElementById("next2");
  if (next) next.disabled = !allPassed(docs);
}

function allPassed(docs) {
  return docs.every(d => state.docResults[d.id]?.status === "PASS");
}

/* Step 3 — Management review (auto, shows result) */
function renderStep3() {
  const view = document.getElementById("view");
  view.innerHTML = `
    <div class="card">
      <h2>Cross-Reference Review</h2>
      <p class="hint">Analysing document consistency…</p>
      <div id="review-body" style="text-align:center;padding:32px">
        <div style="font-size:2rem">⏳</div>
        <p style="margin-top:12px;color:#94a3b8">Processing documents…</p>
      </div>
    </div>`;
}

async function runReview() {
  render(); // show loading state
  try {
    const payload = Object.entries(state.docResults).map(([id, r]) => ({ doc: id, ...r }));
    const res = await fetch(`/cases/review?case_id=${state.caseId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    state.reviewResult = await res.json();
  } catch {
    state.reviewResult = { auto_verified: [], clarification_required: [] };
  }
  showReviewResult();
}

function showReviewResult() {
  const r = state.reviewResult;
  const body = document.getElementById("review-body");
  const clarHTML = (r.clarification_required || []).map(c => `
    <div class="clarify-box">
      <strong>⚠ Variance Detected</strong>
      <em>${c.anomaly}</em>
      <p style="margin-top:6px"><b>Question for customer:</b> ${c.question}</p>
    </div>`).join("") || "<p style='color:#94a3b8;font-size:.84rem'>No clarifications required.</p>";

  const autoHTML = (r.auto_verified || []).map(v =>
    `<li>${v}</li>`).join("") || "<li>No items auto-verified.</li>";

  body.innerHTML = `
    <div style="margin-bottom:16px">
      <h3 style="font-size:.9rem;margin-bottom:8px;color:#0d9488">✓ Auto-Verified</h3>
      <ul class="checklist">${autoHTML}</ul>
    </div>
    <div>
      <h3 style="font-size:.9rem;margin-bottom:8px;color:#d97706">Clarification Items</h3>
      ${clarHTML}
    </div>
    <div class="action-row">
      <button class="btn btn-ghost" id="back3">← Back</button>
      <button class="btn btn-primary" id="next3">Run Credit Profile →</button>
    </div>`;

  document.getElementById("back3").onclick = () => { state.step = 2; render(); };
  document.getElementById("next3").onclick = () => { state.step = 4; runCreditProfile(); };
}

/* Step 4 — Credit profile */
function renderStep4() {
  document.getElementById("view").innerHTML = `
    <div class="card">
      <h2>Credit Profile</h2>
      <p class="hint">Analysing CTOS & KYC data…</p>
      <div style="text-align:center;padding:32px">
        <div style="font-size:2rem">🔍</div>
        <p style="margin-top:12px;color:#94a3b8">Running credit profiler…</p>
      </div>
    </div>`;
}

async function runCreditProfile() {
  render();
  // For demo: use mock data. In production this comes from a form or Supabase record.
  const mockInput = {
    age: 35, profession: "Junior Executive", location: "Ipoh, Perak",
    declared_income: 4000, recent_applications: 1,
    ccris: [
      { product: "Housing Loan", history: [0,0,0,0,0,0,0,0,0,0,0,0] },
      { product: "Car Loan",     history: [0,0,0,1,0,0,0,0,0,0,0,0] },
    ],
    ctos_legal: [
      { court: "Magistrate Court", status: "Settled", settlement_date: "15-March-2025" }
    ],
  };
  try {
    const res = await fetch(`/cases/credit-profile?case_id=${state.caseId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(mockInput),
    });
    state.creditResult = await res.json();
  } catch {
    state.creditResult = { Readiness_Score: 0, Red_Flags: [], Preparation_Checklist: [] };
  }
  showCreditResult();
}

function showCreditResult() {
  const cr = state.creditResult;
  const score = cr.Readiness_Score;
  const ringColor = score >= 75 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";

  const flagsHTML = cr.Red_Flags.map(f => {
    const cls = { "High-Risk": "high", "Moderate": "mod", "Low": "low" }[f.severity] || "low";
    return `<div class="flag ${cls}"><strong>[${f.severity}]</strong> <span>${f.detail}</span></div>`;
  }).join("") || "<p style='color:#94a3b8;font-size:.84rem'>No red flags.</p>";

  const checkHTML = cr.Preparation_Checklist.map(c => `<li>${c}</li>`).join("");

  document.getElementById("view").innerHTML = `
    <div class="card">
      <h2>Credit Profile Result</h2>
      <div class="score-ring-wrap">
        <div class="score-ring" style="border-color:${ringColor}">
          <span class="num" style="color:${ringColor}">${score}</span>
          <span class="denom">/ 100</span>
        </div>
        <div>
          <div style="font-weight:600;margin-bottom:4px">Readiness Score</div>
          <div style="font-size:.8rem;color:#64748b">
            ${score >= 75 ? "Ready for preparation" : score >= 50 ? "Conditionally ready — items outstanding" : "Not ready — critical flags present"}
          </div>
        </div>
      </div>
      <h3 style="font-size:.88rem;margin-bottom:8px">Red Flags</h3>
      <div class="flag-list">${flagsHTML}</div>
      <h3 style="font-size:.88rem;margin-bottom:8px">Preparation Checklist</h3>
      <ul class="checklist">${checkHTML}</ul>
      <div class="action-row">
        <button class="btn btn-ghost" id="back4">← Back</button>
        <button class="btn btn-primary" id="next4">Generate Report →</button>
      </div>
    </div>`;

  document.getElementById("back4").onclick = () => { state.step = 3; render(); showReviewResult(); };
  document.getElementById("next4").onclick = () => { state.step = 5; generateReport(); };
}

/* Step 5 — Report generation */
function renderStep5() {
  document.getElementById("view").innerHTML = `
    <div class="card report-card">
      <div class="big-icon">📄</div>
      <h2>Generating Report…</h2>
      <p>Compiling all pipeline outputs into your PDF.</p>
    </div>`;
}

async function generateReport() {
  render();
  // First generate & store the report
  const fd = new FormData();
  fd.append("case_id", state.caseId);
  fd.append("encrypt", "false");

  try {
    const res = await fetch("/cases/generate-report", { method: "POST", headers: authHeaders(), body: fd });
    state.reportBlob = await res.blob();
    state.reportPassword = res.headers.get("X-PDF-Password");
    const sumRaw = res.headers.get("X-Report-Summary");
    state.reportSummary = sumRaw ? JSON.parse(sumRaw) : null;
  } catch (e) {
    state.reportBlob = null;
  }
  showReportResult();
}

async function initiatePayment() {
  try {
    const res = await fetch(`/payments/checkout?case_id=${state.caseId}`, { method: "POST", headers: authHeaders() });
    const data = await res.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    }
  } catch {
    alert("Payment could not be initiated. Please try again.");
  }
}

function showReportResult() {
  const summary = state.reportSummary;
  const isPaid = false; // set true after Stripe webhook confirms payment

  document.getElementById("view").innerHTML = `
    <div class="card report-card">
      <div class="big-icon">${state.reportBlob ? "📄" : "❌"}</div>
      <h2>${state.reportBlob ? "Report Generated" : "Generation Failed"}</h2>
      ${summary ? `<p>Report ID: <strong>${summary.report_id}</strong> &nbsp;|&nbsp;
         Readiness Score: <strong>${summary.readiness_score} / 100</strong></p>` : ""}

      ${state.reportBlob ? `
        <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;padding:14px 18px;margin:16px 0;font-size:.84rem;">
          ✅ Your report has been securely stored. Complete payment below to download it.
        </div>
        <button class="btn btn-primary" style="font-size:1rem;padding:14px 28px" onclick="initiatePayment()">
          💳 Pay RM 29 to Download Report
        </button>
      ` : `<p style="color:#dc2626">Report generation failed. Please try again.</p>`}

      <div class="disclaimer">
        DISCLAIMER: This report is generated strictly based on the data and explanations provided
        by the user. Peraku-Xread is a data processing service and does not act as a regulator,
        judge, or bank representative. This report is for personal financial awareness and
        preparation only, and provides no guarantee of bank approval.
      </div>
      <div class="action-row" style="justify-content:center;margin-top:16px">
        <button class="btn btn-ghost" onclick="newCase()">Start New Case</button>
      </div>
    </div>`;
}

function newCase() {
  Object.assign(state, {
    step: 1, userType: null, caseId: null, docResults: {}, reviewResult: null,
    creditResult: null, reportBlob: null, reportPassword: null, reportSummary: null,
  });
  render();
}

/* ── Auth UI ── */
function renderAuthGate() {
  const isLogin = !window._authMode || window._authMode === "login";
  document.getElementById("view").innerHTML = `
    <div class="card" style="max-width:420px;margin:0 auto">
      <h2 style="margin-bottom:6px">${isLogin ? "Sign In" : "Create Account"}</h2>
      <p class="hint">${isLogin ? "Sign in to access your cases." : "Create a free account to get started."}</p>
      <div style="display:flex;flex-direction:column;gap:12px">
        <input id="auth-email" type="email" placeholder="Email address"
          style="padding:11px 14px;border:1.5px solid #e2e8f0;border-radius:7px;font-size:.9rem">
        <input id="auth-pw" type="password" placeholder="Password"
          style="padding:11px 14px;border:1.5px solid #e2e8f0;border-radius:7px;font-size:.9rem">
        <div id="auth-error" style="color:#dc2626;font-size:.8rem;display:none"></div>
        <button class="btn btn-primary" id="auth-submit" style="width:100%;justify-content:center">
          ${isLogin ? "Sign In →" : "Create Account →"}
        </button>
      </div>
      <p style="text-align:center;margin-top:16px;font-size:.82rem;color:#64748b">
        ${isLogin
          ? `No account? <a href="#" id="auth-toggle" style="color:#0d9488">Sign up</a>`
          : `Already have one? <a href="#" id="auth-toggle" style="color:#0d9488">Sign in</a>`}
      </p>
    </div>`;

  document.getElementById("auth-toggle").onclick = (e) => {
    e.preventDefault();
    window._authMode = isLogin ? "signup" : "login";
    renderAuthGate();
  };

  document.getElementById("auth-submit").onclick = async () => {
    const email = document.getElementById("auth-email").value.trim();
    const pw    = document.getElementById("auth-pw").value;
    const errEl = document.getElementById("auth-error");
    errEl.style.display = "none";

    const endpoint = isLogin ? "/auth/login" : "/auth/signup";
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password: pw }),
    });
    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.detail || "Authentication failed.";
      errEl.style.display = "block";
      return;
    }

    if (isLogin) {
      saveAuth(data.access_token, data.user);
      updateHeaderUser();
      render();
    } else {
      errEl.style.color = "#16a34a";
      errEl.textContent = data.message;
      errEl.style.display = "block";
    }
  };
}

function updateHeaderUser() {
  const el = document.getElementById("header-user");
  if (!el) return;
  if (auth.user) {
    el.innerHTML = `
      <span style="font-size:.78rem;color:#94a3b8">${auth.user.email}</span>
      <button onclick="logout()" style="font-size:.75rem;color:#0d9488;background:none;border:none;cursor:pointer;margin-left:8px">Sign out</button>`;
  } else {
    el.innerHTML = "";
  }
}

async function logout() {
  if (auth.token) {
    await fetch("/auth/logout", {
      method: "POST",
      headers: authHeaders(),
    }).catch(() => {});
  }
  clearAuth();
  updateHeaderUser();
  renderAuthGate();
}

document.addEventListener("DOMContentLoaded", () => {
  updateHeaderUser();
  if (!auth.token) {
    renderAuthGate();
  } else {
    render();
  }
});
