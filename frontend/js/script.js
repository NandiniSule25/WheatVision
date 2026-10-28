// =========================================================
// WheatVision - Complete Frontend Integration & App Controller
// =========================================================

document.addEventListener("DOMContentLoaded", () => {

    // -----------------------------------------------------
    // API Configuration
    // -----------------------------------------------------
    // Automatically use origin if served via Flask on :5000,
    // or point to http://127.0.0.1:5000 if served via Live Server on :5500.
    const API_BASE = window.location.origin.includes(":5000")
        ? ""
        : "http://127.0.0.1:5000";

    // -----------------------------------------------------
    // DOM Elements - Navigation & Core
    // -----------------------------------------------------
    const menuBtn = document.getElementById("menuBtn");
    const mobileMenu = document.getElementById("mobileMenu");
    const navAuthBtn = document.getElementById("navAuthBtn");
    const navAuthText = document.getElementById("navAuthText");

    // DOM Elements - Authentication
    const authContainer = document.getElementById("authContainer");
    const dashboardPanel = document.getElementById("dashboardPanel");
    const authTitle = document.getElementById("authTitle");
    const authSubtitle = document.getElementById("authSubtitle");
    const authMessage = document.getElementById("authMessage");
    const loginForm = document.getElementById("loginForm");
    const nameGroup = document.getElementById("nameGroup");
    const nameInput = document.getElementById("name");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const passwordToggle = document.getElementById("passwordToggle");
    const loginOptions = document.getElementById("loginOptions");
    const authSubmitBtn = document.getElementById("authSubmitBtn");
    const authSubmitText = document.getElementById("authSubmitText");
    const toggleAuthMode = document.getElementById("toggleAuthMode");
    const toggleAuthPrompt = document.getElementById("toggleAuthPrompt");

    // DOM Elements - Dashboard & User Session
    const loggedUserName = document.getElementById("loggedUserName");
    const loggedUserEmail = document.getElementById("loggedUserEmail");
    const logoutBtn = document.getElementById("logoutBtn");

    // DOM Elements - Analysis & Prediction
    const uploadCard = document.getElementById("uploadCard");
    const grainInput = document.getElementById("grainInput");
    const previewContainer = document.getElementById("previewContainer");
    const imagePreview = document.getElementById("imagePreview");
    const previewFilename = document.getElementById("previewFilename");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const analyzeBtnText = document.getElementById("analyzeBtnText");
    const analyzeBtnIcon = document.getElementById("analyzeBtnIcon");
    const predictionResult = document.getElementById("predictionResult");

    // DOM Elements - History
    const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
    const historyList = document.getElementById("historyList");

    let isRegisterMode = false;
    let selectedFile = null;
    let currentUser = null;

    // -----------------------------------------------------
    // Mobile Navigation
    // -----------------------------------------------------
    if (menuBtn && mobileMenu) {
        menuBtn.addEventListener("click", () => {
            mobileMenu.classList.toggle("show");
            const icon = menuBtn.querySelector("i");
            if (mobileMenu.classList.contains("show")) {
                icon.className = "fa-solid fa-xmark";
            } else {
                icon.className = "fa-solid fa-bars";
            }
        });

        document.querySelectorAll(".mobile-menu a").forEach(link => {
            link.addEventListener("click", () => {
                mobileMenu.classList.remove("show");
                const icon = menuBtn.querySelector("i");
                if (icon) icon.className = "fa-solid fa-bars";
            });
        });
    }

    // -----------------------------------------------------
    // Password Show / Hide Toggle
    // -----------------------------------------------------
    if (passwordToggle && passwordInput) {
        passwordToggle.addEventListener("click", () => {
            if (passwordInput.type === "password") {
                passwordInput.type = "text";
                passwordToggle.innerHTML = '<i class="fa-regular fa-eye-slash"></i>';
            } else {
                passwordInput.type = "password";
                passwordToggle.innerHTML = '<i class="fa-regular fa-eye"></i>';
            }
        });
    }

    // -----------------------------------------------------
    // Smooth Anchor Scrolling
    // -----------------------------------------------------
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", function (e) {
            const targetId = this.getAttribute("href");
            if (targetId && targetId !== "#" && targetId.startsWith("#")) {
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            }
        });
    });

    // -----------------------------------------------------
    // Authentication Helpers & Mode Toggle
    // -----------------------------------------------------
    function showAuthMessage(msg, type = "error") {
        if (!authMessage) return;
        authMessage.textContent = msg;
        authMessage.style.display = "block";
        if (type === "success") {
            authMessage.style.background = "#e7f5ec";
            authMessage.style.color = "#147545";
            authMessage.style.border = "1px solid #b8e0c6";
        } else {
            authMessage.style.background = "#fde8e8";
            authMessage.style.color = "#ba3838";
            authMessage.style.border = "1px solid #f6c0c0";
        }
    }

    function hideAuthMessage() {
        if (authMessage) authMessage.style.display = "none";
    }

    if (toggleAuthMode) {
        toggleAuthMode.addEventListener("click", () => {
            isRegisterMode = !isRegisterMode;
            hideAuthMessage();

            if (isRegisterMode) {
                if (nameGroup) nameGroup.style.display = "block";
                if (nameInput) nameInput.required = true;
                if (loginOptions) loginOptions.style.display = "none";
                if (authTitle) authTitle.innerHTML = 'Create your <span>Account</span>';
                if (authSubtitle) authSubtitle.textContent = 'Register to analyze wheat samples and save prediction history.';
                if (authSubmitText) authSubmitText.textContent = 'Create Account';
                if (toggleAuthPrompt) toggleAuthPrompt.textContent = 'Already have an account?';
                if (toggleAuthMode) toggleAuthMode.textContent = 'Sign In';
            } else {
                if (nameGroup) nameGroup.style.display = "none";
                if (nameInput) nameInput.required = false;
                if (loginOptions) loginOptions.style.display = "flex";
                if (authTitle) authTitle.innerHTML = 'Welcome to <span>WheatVision</span>';
                if (authSubtitle) authSubtitle.textContent = 'Sign in to access your dashboard and start analyzing wheat.';
                if (authSubmitText) authSubmitText.textContent = 'Sign In';
                if (toggleAuthPrompt) toggleAuthPrompt.textContent = "Don't have an account?";
                if (toggleAuthMode) toggleAuthMode.textContent = 'Create Account';
            }
        });
    }

    // -----------------------------------------------------
    // Check Active Session (Current User)
    // -----------------------------------------------------
    async function checkAuthSession() {
        try {
            const res = await fetch(`${API_BASE}/api/auth/me`, {
                method: "GET",
                credentials: "include"
            });

            if (res.ok) {
                const data = await res.json();
                if (data.success && data.user) {
                    setLoggedInState(data.user);
                    return;
                }
            }
        } catch (err) {
            console.warn("Session check offline or unauthenticated:", err);
        }
        setLoggedOutState();
    }

    function setLoggedInState(user) {
        currentUser = user;
        if (authContainer) authContainer.style.display = "none";
        if (dashboardPanel) dashboardPanel.style.display = "block";

        if (loggedUserName) loggedUserName.textContent = user.name || "Researcher";
        if (loggedUserEmail) loggedUserEmail.textContent = user.email || "";

        if (navAuthText) navAuthText.textContent = user.name ? user.name.split(" ")[0] : "Dashboard";
        if (navAuthBtn) navAuthBtn.setAttribute("href", "#login");

        loadHistory();
    }

    function setLoggedOutState() {
        currentUser = null;
        if (authContainer) authContainer.style.display = "block";
        if (dashboardPanel) dashboardPanel.style.display = "none";

        if (navAuthText) navAuthText.textContent = "Login";
        if (navAuthBtn) navAuthBtn.setAttribute("href", "#login");

        if (predictionResult) predictionResult.style.display = "none";
        resetUpload();
    }

    // -----------------------------------------------------
    // Auth Form Submission (Sign In / Register)
    // -----------------------------------------------------
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            hideAuthMessage();

            const email = emailInput?.value.trim();
            const password = passwordInput?.value.trim();
            const name = nameInput?.value.trim();

            if (!email || !password) {
                showAuthMessage("Please fill in all required fields.");
                return;
            }

            if (isRegisterMode && (!name || name.length < 2)) {
                showAuthMessage("Please provide your full name (at least 2 characters).");
                return;
            }

            const endpoint = isRegisterMode
                ? `${API_BASE}/api/auth/register`
                : `${API_BASE}/api/auth/login`;

            const payload = isRegisterMode
                ? { name, email, password }
                : { email, password };

            try {
                if (authSubmitBtn) {
                    authSubmitBtn.disabled = true;
                    if (authSubmitText) authSubmitText.textContent = "Processing...";
                }

                const res = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                    credentials: "include"
                });

                const data = await res.json();

                if (res.ok && data.success) {
                    showAuthMessage(data.message || "Success!", "success");
                    setTimeout(() => {
                        hideAuthMessage();
                        setLoggedInState(data.user);
                    }, 600);
                } else {
                    showAuthMessage(data.error || "Authentication failed.");
                }
            } catch (err) {
                showAuthMessage("Network error: Could not reach the WheatVision backend.");
                console.error("Auth error:", err);
            } finally {
                if (authSubmitBtn) {
                    authSubmitBtn.disabled = false;
                    if (authSubmitText) {
                        authSubmitText.textContent = isRegisterMode ? "Create Account" : "Sign In";
                    }
                }
            }
        });
    }

    // -----------------------------------------------------
    // Logout Action
    // -----------------------------------------------------
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                await fetch(`${API_BASE}/api/auth/logout`, {
                    method: "POST",
                    credentials: "include"
                });
            } catch (err) {
                console.error("Logout error:", err);
            }
            setLoggedOutState();
        });
    }

    // -----------------------------------------------------
    // Drag & Drop / File Selection for Wheat Grain Analysis
    // -----------------------------------------------------
    if (uploadCard && grainInput) {
        uploadCard.addEventListener("click", () => {
            grainInput.click();
        });

        grainInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            handleFileSelection(file);
        });

        uploadCard.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadCard.style.borderColor = "var(--green)";
            uploadCard.style.background = "#f0f7f2";
        });

        uploadCard.addEventListener("dragleave", (e) => {
            e.preventDefault();
            uploadCard.style.borderColor = "#b5c7bb";
            uploadCard.style.background = "#ffffff";
        });

        uploadCard.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadCard.style.borderColor = "#b5c7bb";
            uploadCard.style.background = "#ffffff";
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }

    function handleFileSelection(file) {
        if (!file) return;

        // Validation
        const validTypes = ["image/jpeg", "image/png", "image/webp"];
        if (!validTypes.includes(file.type)) {
            alert("Please select a supported image file (JPEG, PNG, or WEBP).");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert("File size exceeds 5 MB. Please choose a smaller image.");
            return;
        }

        selectedFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            if (imagePreview) imagePreview.src = e.target.result;
            if (previewFilename) previewFilename.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            if (previewContainer) previewContainer.style.display = "block";
            if (analyzeBtn) analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        selectedFile = null;
        if (grainInput) grainInput.value = "";
        if (previewContainer) previewContainer.style.display = "none";
        if (imagePreview) imagePreview.src = "";
        if (previewFilename) previewFilename.textContent = "";
        if (analyzeBtn) analyzeBtn.disabled = true;
    }

    // -----------------------------------------------------
    // Analyze Wheat Sample (POST /api/predict)
    // -----------------------------------------------------
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", async () => {
            if (!selectedFile) return;

            const formData = new FormData();
            formData.append("image", selectedFile);

            analyzeBtn.disabled = true;
            if (analyzeBtnText) analyzeBtnText.textContent = "Analyzing Wheat Sample...";
            if (analyzeBtnIcon) analyzeBtnIcon.className = "fa-solid fa-spinner fa-spin";
            if (predictionResult) {
                predictionResult.style.display = "block";
                predictionResult.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--muted);"><i class="fa-solid fa-circle-notch fa-spin"></i> Processing image through two-stage neural models...</div>';
            }

            try {
                const res = await fetch(`${API_BASE}/api/predict`, {
                    method: "POST",
                    body: formData,
                    credentials: "include"
                });

                const data = await res.json();

                if (res.status === 401) {
                    setLoggedOutState();
                    showAuthMessage("Your session expired. Please sign in again.");
                    return;
                }

                if (res.status === 503) {
                    renderModelUnavailable(data.error);
                    return;
                }

                if (!res.ok || !data.success) {
                    renderAnalysisError(data.error || "Inference failed.");
                    return;
                }

                renderAnalysisResult(data);
                loadHistory(); // Refresh history table immediately
            } catch (err) {
                renderAnalysisError("Network error: Could not complete analysis request.");
                console.error("Predict error:", err);
            } finally {
                analyzeBtn.disabled = false;
                if (analyzeBtnText) analyzeBtnText.textContent = "Analyze Wheat Sample";
                if (analyzeBtnIcon) analyzeBtnIcon.className = "fa-solid fa-microscope";
            }
        });
    }

    // -----------------------------------------------------
    // Render Analysis Result
    // -----------------------------------------------------
    function renderAnalysisResult(data) {
        if (!predictionResult) return;

        const isWheat = data.is_wheat;
        const status = data.status;
        const detConf = (data.detector_confidence * 100).toFixed(1);

        let html = '<div class="result-card">';

        // 1. Stage 1: Wheat Detection Result
        if (status === "non_wheat") {
            html += `
                <div class="result-badge danger">
                    <i class="fa-solid fa-circle-xmark"></i> Non-Wheat Detected (${detConf}% confidence)
                </div>
                <h4 style="font-size: 15px; color: #ba3838; margin-bottom: 6px;">Image Does Not Contain Wheat Grains</h4>
                <p style="font-size: 11px; color: var(--muted); margin-bottom: 12px;">
                    ${data.message || "The wheat detection model evaluated this sample as non-wheat."}
                </p>
            `;
        } else if (status === "uncertain_wheat") {
            html += `
                <div class="result-badge warning">
                    <i class="fa-solid fa-triangle-exclamation"></i> Uncertain Grain Detection (${detConf}%)
                </div>
                <h4 style="font-size: 15px; color: #b37400; margin-bottom: 6px;">Unverified Sample</h4>
                <p style="font-size: 11px; color: var(--muted); margin-bottom: 12px;">
                    ${data.message || "Detection score was below the established 77% threshold."}
                </p>
            `;
        } else {
            // Wheat Confirmed!
            const spec = data.species_analysis || {};
            const specConf = (spec.species_confidence * 100).toFixed(1);
            const isConfident = spec.is_confident_species;

            html += `
                <div class="result-badge success">
                    <i class="fa-solid fa-circle-check"></i> Wheat Verified (${detConf}%)
                </div>
                <div style="margin-bottom: 16px;">
                    <span style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); font-weight: 600;">Species Identification</span>
                    <h3 style="font-size: 19px; color: var(--dark-green); margin: 3px 0 2px;">
                        <em>${spec.scientific_name || "Unknown"}</em>
                    </h3>
                    <p style="font-size: 11px; color: var(--green); font-weight: 500;">
                        ${spec.common_name || ""} &bull; ${specConf}% Confidence
                    </p>
                    <div class="progress-track">
                        <div class="progress-fill ${isConfident ? '' : 'gold'}" style="width: ${specConf}%;"></div>
                    </div>
                    ${!isConfident ? `
                        <small style="color: #b37400; font-size: 10px; display: block; margin-top: -6px; margin-bottom: 10px;">
                            <i class="fa-solid fa-triangle-exclamation"></i> Confidence is below the 93% threshold. Interpret with caution.
                        </small>
                    ` : ''}
                </div>
            `;

            // Species Probabilities Grid
            if (spec.all_species_probabilities && spec.all_species_probabilities.length > 0) {
                html += '<div style="margin-bottom: 14px;"><strong style="font-size: 10px; text-transform: uppercase; color: var(--muted); display: block; margin-bottom: 6px;">Softmax Distribution</strong>';
                spec.all_species_probabilities.forEach(p => {
                    const pct = (p.confidence * 100).toFixed(1);
                    html += `
                        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px;">
                            <span><em>${p.scientific_name}</em></span>
                            <span style="font-weight: 600; color: var(--dark-green);">${pct}%</span>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Literature Insights
            const lit = data.literature_insights;
            if (lit) {
                html += `
                    <div style="border-top: 1px solid var(--border); padding-top: 14px; margin-top: 10px;">
                        <span style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); font-weight: 600;">Literature-Based Reference Insights</span>
                        
                        <div class="info-item" style="margin-top: 8px;">
                            <strong><i class="fa-solid fa-dna" style="color: var(--green); margin-right: 4px;"></i> Typical Protein Range</strong>
                            <p>${lit.protein_range?.min_percent}% – ${lit.protein_range?.max_percent}% ${lit.protein_range?.unit || ''}</p>
                            <small style="font-size: 9px; color: var(--muted);">${lit.protein_range?.description || ''}</small>
                        </div>

                        <div class="info-item">
                            <strong><i class="fa-solid fa-bread-slice" style="color: var(--gold); margin-right: 4px;"></i> Suitable Food Products</strong>
                            <p>${(lit.suitable_food_products || []).join(", ")}</p>
                        </div>
                    </div>
                `;
            }
        }

        // Scientific Disclaimer Card
        if (data.scientific_disclaimer) {
            html += `
                <div class="disclaimer-card">
                    <strong style="color: var(--dark-green); display: block; margin-bottom: 2px;">
                        <i class="fa-solid fa-shield-halved"></i> Scientific Disclaimer
                    </strong>
                    ${data.scientific_disclaimer}
                </div>
            `;
        }

        html += '</div>';
        predictionResult.innerHTML = html;
    }

    function renderModelUnavailable(msg) {
        if (!predictionResult) return;
        predictionResult.innerHTML = `
            <div class="result-card" style="border-left: 4px solid #b37400;">
                <h4 style="font-size: 14px; color: #b37400; margin-bottom: 6px;">
                    <i class="fa-solid fa-circle-exclamation"></i> Models Unavailable (HTTP 503)
                </h4>
                <p style="font-size: 11px; color: var(--muted); line-height: 1.4;">
                    ${msg || "Trained ONNX models are not deployed."}
                </p>
            </div>
        `;
    }

    function renderAnalysisError(msg) {
        if (!predictionResult) return;
        predictionResult.innerHTML = `
            <div class="result-card" style="border-left: 4px solid #ba3838;">
                <h4 style="font-size: 14px; color: #ba3838; margin-bottom: 6px;">
                    <i class="fa-solid fa-triangle-exclamation"></i> Analysis Error
                </h4>
                <p style="font-size: 11px; color: var(--muted); line-height: 1.4;">
                    ${msg}
                </p>
            </div>
        `;
    }

    // -----------------------------------------------------
    // Prediction History Controller
    // -----------------------------------------------------
    async function loadHistory() {
        if (!historyList || !currentUser) return;

        try {
            const res = await fetch(`${API_BASE}/api/history?limit=15`, {
                method: "GET",
                credentials: "include"
            });

            if (!res.ok) return;

            const data = await res.json();
            if (!data.success || !data.history) return;

            if (data.history.length === 0) {
                historyList.innerHTML = '<p style="font-size: 11px; color: var(--muted); text-align: center; padding: 14px;">No previous analysis records found. Upload a wheat image above!</p>';
                return;
            }

            let html = "";
            data.history.forEach(item => {
                const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : "";
                const isWheat = item.prediction_status === "wheat_detected" || item.prediction_status === "uncertain_species";
                const badgeColor = item.prediction_status === "wheat_detected"
                    ? "#147545"
                    : (item.prediction_status === "non_wheat" ? "#ba3838" : "#b37400");

                html += `
                    <div class="history-item" id="history-row-${item.id}">
                        <div style="flex: 1; min-width: 0;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
                                <strong style="color: var(--dark-green); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 130px;">
                                    ${item.original_filename}
                                </strong>
                                <span style="font-size: 9px; padding: 2px 6px; border-radius: 4px; background: #f0f3ee; color: ${badgeColor}; font-weight: 600;">
                                    ${item.prediction_status.replace('_', ' ')}
                                </span>
                            </div>
                            <small style="font-size: 10px; color: var(--muted);">
                                ${item.predicted_species ? `Species: <em>${item.predicted_species}</em> &bull; ` : ''}
                                ${dateStr}
                            </small>
                        </div>
                        <button type="button" class="btn-delete-record" data-id="${item.id}" title="Delete Record">
                            <i class="fa-regular fa-trash-can"></i>
                        </button>
                    </div>
                `;
            });

            historyList.innerHTML = html;

            // Wire delete buttons
            historyList.querySelectorAll(".btn-delete-record").forEach(btn => {
                btn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const recordId = btn.getAttribute("data-id");
                    if (confirm("Are you sure you want to delete this prediction record?")) {
                        await deleteHistoryRecord(recordId);
                    }
                });
            });

        } catch (err) {
            console.error("Failed to load history:", err);
        }
    }

    async function deleteHistoryRecord(id) {
        try {
            const res = await fetch(`${API_BASE}/api/history/${id}`, {
                method: "DELETE",
                credentials: "include"
            });
            const data = await res.json();
            if (res.ok && data.success) {
                const row = document.getElementById(`history-row-${id}`);
                if (row) row.remove();
                if (historyList && historyList.children.length === 0) {
                    historyList.innerHTML = '<p style="font-size: 11px; color: var(--muted); text-align: center; padding: 14px;">No previous analysis records found.</p>';
                }
            } else {
                alert(data.error || "Failed to delete record.");
            }
        } catch (err) {
            alert("Network error while deleting record.");
        }
    }

    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener("click", () => {
            loadHistory();
        });
    }

    // -----------------------------------------------------
    // Contact & Feedback Form Controller
    // -----------------------------------------------------
    const contactForm = document.getElementById("contactForm");
    const contactFormMsg = document.getElementById("contactFormMsg");
    const contactSubmitBtn = document.getElementById("contactSubmitBtn");
    const contactSubmitText = document.getElementById("contactSubmitText");

    if (contactForm) {
        contactForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("contactName")?.value.trim();
            const email = document.getElementById("contactEmail")?.value.trim();
            const message = document.getElementById("contactMessage")?.value.trim();

            if (!name || !email || !message) return;

            try {
                if (contactSubmitBtn) contactSubmitBtn.disabled = true;
                if (contactSubmitText) contactSubmitText.textContent = "Sending...";

                const res = await fetch(`${API_BASE}/api/contact`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, email, message })
                });

                const data = await res.json();
                if (contactFormMsg) {
                    contactFormMsg.style.display = "block";
                    if (res.ok && data.success) {
                        contactFormMsg.style.background = "#e7f5ec";
                        contactFormMsg.style.color = "#147545";
                        contactFormMsg.style.border = "1px solid #b8e0c6";
                        contactFormMsg.textContent = data.message || "Message sent successfully!";
                        contactForm.reset();
                    } else {
                        contactFormMsg.style.background = "#fde8e8";
                        contactFormMsg.style.color = "#ba3838";
                        contactFormMsg.style.border = "1px solid #f6c0c0";
                        contactFormMsg.textContent = data.error || "Failed to send message.";
                    }
                }
            } catch (err) {
                if (contactFormMsg) {
                    contactFormMsg.style.display = "block";
                    contactFormMsg.style.background = "#fde8e8";
                    contactFormMsg.style.color = "#ba3838";
                    contactFormMsg.textContent = "Could not send message. Please check server connection.";
                }
            } finally {
                if (contactSubmitBtn) contactSubmitBtn.disabled = false;
                if (contactSubmitText) contactSubmitText.textContent = "Send Message";
            }
        });
    }

    // -----------------------------------------------------
    // Initialize Session Check on Page Load
    // -----------------------------------------------------
    checkAuthSession();

});
