// FILE: static/app.js
// Scop:
//   - UI fără XSS (fără innerHTML pentru mesaje).
//   - Auth: access token în memorie + refresh token HttpOnly cookie.
//   - Auto-refresh: dacă API răspunde 401, încercăm /api/auth/refresh o singură dată.
//
// Debug:
//   - Dacă refresh nu merge: verifică fetch credentials: "include" + COOKIE_SECURE=false în dev (http).

let accessToken = null;
let refreshInFlight = null;

// Elemente din DOM
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const userInfoEl = document.getElementById("user-info");
const statusBar = document.getElementById("status-bar");

const btnLogout = document.getElementById("btn-logout");

const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");

const registerForm = document.getElementById("register-form");
const registerFirstName = document.getElementById("register-first-name");
const registerLastName = document.getElementById("register-last-name");
const registerEmail = document.getElementById("register-email");
const registerPassword = document.getElementById("register-password");
const registerPassword2 = document.getElementById("register-password2");
const registerCompanyName = document.getElementById("register-company-name");
const registerCompanyCui = document.getElementById("register-company-cui");
const registerStreet = document.getElementById("register-street");
const registerStreetNo = document.getElementById("register-street-no");
const registerLocality = document.getElementById("register-locality");
const registerCounty = document.getElementById("register-county");
const registerPostal = document.getElementById("register-postal");
const registerCountry = document.getElementById("register-country");
const registerPolicy = document.getElementById("register-policy");

const uploadForm = document.getElementById("upload-form");
const uploadFileInput = document.getElementById("upload-file");

const filterForm = document.getElementById("filter-form");
const filterPage = document.getElementById("filter-page");
const filterPageSize = document.getElementById("filter-page-size");
const ordersMeta = document.getElementById("orders-meta");
const ordersTbody = document.getElementById("orders-tbody");
const btnRefresh = document.getElementById("btn-refresh");

const smsSettingsForm = document.getElementById("sms-settings-form");
const smsTokenInput = document.getElementById("sms-token");
const smsSenderInput = document.getElementById("sms-sender");
const smsCompanyInput = document.getElementById("sms-company-name");

const smsBalancePointsEl = document.getElementById("sms-balance-points");
const smsTotalSentEl = document.getElementById("sms-total-sent");
const smsTotalErrorsEl = document.getElementById("sms-total-errors");
const smsDocCard = document.getElementById("sms-doc-card");
const btnShowSmsDoc = document.getElementById("btn-sms-doc");
const btnCloseSmsDoc = document.getElementById("btn-sms-doc-close");

const productLinkForm = document.getElementById("product-link-form");
const productLinkPnkInput = document.getElementById("product-link-pnk");
const productLinkUrlInput = document.getElementById("product-link-url");
const productLinksListEl = document.getElementById("product-links-list");
const btnProductLinksToggle = document.getElementById("btn-product-links-toggle");

// ---------- Helpers UI (anti-XSS) ----------

function showStatus(message, type = "info", timeout = 4000) {
  if (!statusBar) return;

  statusBar.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = `status-bar-inner ${type === "error" ? "error" : "success"}`;

  const msg = document.createElement("span");
  msg.textContent = String(message || "");
  wrap.appendChild(msg);

  const btn = document.createElement("button");
  btn.className = "btn secondary";
  btn.style.pointerEvents = "auto";
  btn.textContent = "Închide";
  btn.addEventListener("click", () => {
    statusBar.innerHTML = "";
  });
  wrap.appendChild(btn);

  statusBar.appendChild(wrap);

  if (timeout > 0) {
    setTimeout(() => {
      if (statusBar) statusBar.innerHTML = "";
    }, timeout);
  }
}

function setLoggedInUser(user) {
  if (user && user.email) {
    userInfoEl.textContent = `Logat ca: ${user.email}`;
    if (btnLogout) btnLogout.classList.remove("hidden");
  } else {
    userInfoEl.textContent = "";
    if (btnLogout) btnLogout.classList.add("hidden");
  }
}

function switchTab(tab) {
  if (tab === "login") {
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
  } else {
    tabLogin.classList.remove("active");
    tabRegister.classList.add("active");
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
  }
}

function setAuthState(isAuthenticated) {
  if (isAuthenticated) {
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
  } else {
    authSection.classList.remove("hidden");
    appSection.classList.add("hidden");
    setLoggedInUser(null);
    accessToken = null;
  }
}

// ---------- Fetch helper + auto-refresh ----------

async function tryRefresh() {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const resp = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });

    const text = await resp.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = null;
    }

    if (!resp.ok) {
      accessToken = null;
      setAuthState(false);
      throw new Error("Sesiune expirată. Te rugăm să te autentifici din nou.");
    }

    accessToken = data.access_token;
    setLoggedInUser(data.user);
    return true;
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

async function apiFetch(path, options = {}) {
  const url = path.startsWith("http") ? path : path;

  const headers = options.headers || {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const finalOptions = {
    ...options,
    headers,
    credentials: "include",
  };

  const resp = await fetch(url, finalOptions);
  const text = await resp.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    data = text;
  }

  // Auto-refresh pe 401 (o singură dată)
  if (resp.status === 401 && accessToken && !options.__noRetry) {
    await tryRefresh();
    return apiFetch(path, { ...options, __noRetry: true });
  }

  if (!resp.ok) {
    const msg =
      data && data.detail
        ? typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail)
        : `Eroare API (${resp.status})`;
    throw new Error(msg);
  }

  return data;
}

// ---------- Auth ----------

tabLogin.addEventListener("click", () => switchTab("login"));
tabRegister.addEventListener("click", () => switchTab("register"));

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  try {
    if (!registerPolicy.checked) {
      showStatus("Trebuie să accepți politica aplicației.", "error");
      return;
    }

    const companyName = (registerCompanyName.value || "").trim();
    const companyCui = (registerCompanyCui.value || "").trim();

    if ((companyName && !companyCui) || (!companyName && companyCui)) {
      showStatus("Dacă introduci firma, CUI este obligatoriu (și invers).", "error");
      return;
    }

    if (registerPassword.value !== registerPassword2.value) {
      showStatus("Parolele nu coincid.", "error");
      return;
    }

    const body = {
      email: registerEmail.value.trim(),
      first_name: registerFirstName.value.trim(),
      last_name: registerLastName.value.trim(),

      company_name: companyName || null,
      company_cui: companyCui || null,

      street: registerStreet.value.trim(),
      street_no: registerStreetNo.value.trim(),
      locality: registerLocality.value.trim(),
      county: registerCounty.value.trim(),
      postal_code: registerPostal.value.trim(),
      country: registerCountry.value.trim(),

      password: registerPassword.value,
      confirm_password: registerPassword2.value,

      accept_policy: true,
    };

    const out = await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });

    showStatus(out.message || "Cont creat. Verifică emailul.", "success", 7000);
    switchTab("login");

    // UX
    loginEmail.value = registerEmail.value.trim();
    registerPassword.value = "";
    registerPassword2.value = "";
  } catch (err) {
    showStatus(err.message || "Eroare la înregistrare.", "error", 8000);
  }
});

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  try {
    const body = {
      email: loginEmail.value.trim(),
      password: loginPassword.value,
    };

    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });

    accessToken = data.access_token;
    setLoggedInUser(data.user);
    setAuthState(true);

    showStatus("Autentificare reușită.", "success");
    await loadOrders();
    await loadSmsDashboard();
    await loadProductLinks();
  } catch (err) {
    showStatus(err.message || "Eroare la login.", "error", 8000);
  }
});

if (btnLogout) {
  btnLogout.addEventListener("click", async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST", __noRetry: true });
    } catch (_) {}
    accessToken = null;
    setAuthState(false);
    showStatus("Logout reușit.", "success");
  });
}

// ---------- SMS settings (LIPSEA în proiect) ----------

if (smsSettingsForm) {
  smsSettingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
      const body = {
        token: (smsTokenInput.value || "").trim() || null,
        sender: (smsSenderInput.value || "").trim(),
        company_name: (smsCompanyInput.value || "").trim(),
      };

      await apiFetch("/api/settings/sms", {
        method: "POST",
        body: JSON.stringify(body),
      });

      smsTokenInput.value = "";
      showStatus("Setări SMS salvate.", "success");
      await loadSmsDashboard();
    } catch (err) {
      showStatus(err.message || "Eroare la salvarea setărilor SMS.", "error", 8000);
    }
  });
}

// ---------- Upload Excel ----------

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!uploadFileInput.files.length) {
    showStatus("Selectează un fișier .xlsx.", "error");
    return;
  }

  const file = uploadFileInput.files[0];
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    showStatus("Acceptăm doar fișiere .xlsx.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const data = await apiFetch("/api/orders/import", {
      method: "POST",
      body: formData,
    });

    showStatus(`Import reușit: ${data.inserted} comenzi.`, "success", 6000);
    uploadFileInput.value = "";
    filterPage.value = "1";
    await loadOrders();
  } catch (err) {
    showStatus(err.message || "Eroare la import.", "error", 8000);
  }
});

// ---------- Listare comenzi ----------

async function loadOrders() {
  try {
    const page = parseInt(filterPage.value || "1", 10);
    const pageSize = parseInt(filterPageSize.value || "50", 10);

    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });

    const data = await apiFetch(`/api/orders?${query.toString()}`, {
      method: "GET",
    });

    renderOrders(data);
  } catch (err) {
    showStatus(err.message || "Eroare la listarea comenzilor.", "error", 6000);
  }
}

function renderOrders(data) {
  ordersTbody.innerHTML = "";
  if (!data || !data.rows || !data.rows.length) {
    ordersMeta.textContent = "Nu există comenzi importate.";
    return;
  }

  ordersMeta.textContent = `Total: ${data.total} comenzi (se afișează ${data.rows.length}).`;

  data.rows.forEach((o) => {
    const tr = document.createElement("tr");

    const tdId = document.createElement("td");
    tdId.textContent = o.id;
    tr.appendChild(tdId);

    const tdNr = document.createElement("td");
    tdNr.textContent = o.order_number ?? "";
    tr.appendChild(tdNr);

    const tdDate = document.createElement("td");
    tdDate.textContent = o.order_date ? String(o.order_date).replace("T", " ").slice(0, 19) : "";
    tr.appendChild(tdDate);

    const tdProd = document.createElement("td");
    tdProd.textContent = o.product_name ?? "";
    tr.appendChild(tdProd);

    const tdPnk = document.createElement("td");
    tdPnk.textContent = o.pnk ?? "";
    tr.appendChild(tdPnk);

    const tdPhone = document.createElement("td");
    tdPhone.textContent = o.phone_number ?? "";
    tr.appendChild(tdPhone);

    const tdStatus = document.createElement("td");
    const badgeStatus = document.createElement("span");
    badgeStatus.classList.add("badge");
    if (o.order_status && String(o.order_status).toLowerCase().includes("finished")) {
      badgeStatus.classList.add("ok");
    } else {
      badgeStatus.classList.add("warn");
    }
    badgeStatus.textContent = o.order_status ?? "-";
    tdStatus.appendChild(badgeStatus);
    tr.appendChild(tdStatus);

    const tdPay = document.createElement("td");
    const badgePay = document.createElement("span");
    badgePay.classList.add("badge");
    if (o.payment_status && String(o.payment_status).toLowerCase().includes("incas")) {
      badgePay.classList.add("ok");
    } else {
      badgePay.classList.add("warn");
    }
    badgePay.textContent = o.payment_status ?? "-";
    tdPay.appendChild(badgePay);
    tr.appendChild(tdPay);

    const tdSmsStatus = document.createElement("td");
    const badgeSms = document.createElement("span");
    badgeSms.classList.add("badge");
    if (o.sms_sent) {
      badgeSms.classList.add("ok");
      badgeSms.textContent = "Trimis";
    } else {
      badgeSms.classList.add("warn");
      badgeSms.textContent = "Nu";
    }
    tdSmsStatus.appendChild(badgeSms);
    tr.appendChild(tdSmsStatus);

    const tdSmsHistory = document.createElement("td");
    const badgeHist = document.createElement("span");
    badgeHist.classList.add("badge");
    if (o.previous_sms_count && o.previous_sms_count > 0) {
      badgeHist.classList.add("ok");
      badgeHist.textContent = `${o.previous_sms_count} anterior(e)`;
    } else {
      badgeHist.classList.add("warn");
      badgeHist.textContent = "Prima oară";
    }
    tdSmsHistory.appendChild(badgeHist);
    tr.appendChild(tdSmsHistory);

    const tdSms = document.createElement("td");
    const btnSms = document.createElement("button");
    btnSms.textContent = "Trimite SMS";
    btnSms.classList.add("btn", "secondary");
    btnSms.addEventListener("click", () => sendSmsForOrder(o.id));
    tdSms.appendChild(btnSms);
    tr.appendChild(tdSms);

    ordersTbody.appendChild(tr);
  });
}

// ---------- SMS ----------

async function sendSmsForOrder(orderId) {
  if (!confirm(`Trimiți SMS pentru comanda #${orderId}?`)) return;
  try {
    const data = await apiFetch(`/api/sms/order/${orderId}`, {
      method: "POST",
    });
    showStatus(`SMS trimis, ID: ${data.message_id}`, "success");
    await loadOrders();
    await loadSmsDashboard();
  } catch (err) {
    showStatus(err.message || "Eroare la trimiterea SMS-ului.", "error", 8000);
  }
}

// ---------- Filtre & refresh ----------

filterForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  await loadOrders();
});

btnRefresh.addEventListener("click", async () => {
  await loadOrders();
});

// ---------- Setări & dashboard SMS ----------

async function loadSmsSettings() {
  if (!smsSettingsForm) return;
  try {
    const cfg = await apiFetch("/api/settings/sms", { method: "GET" });
    smsSenderInput.value = cfg.sender || "";
    smsTokenInput.value = "";
    smsCompanyInput.value = cfg.company_name || "";
    if (cfg.has_token) {
      smsTokenInput.placeholder = "Token deja salvat (lasă gol dacă nu vrei să îl schimbi)";
    } else {
      smsTokenInput.placeholder = "Introdu tokenul API din contul tău SMSAPI.ro";
    }
  } catch (err) {
    showStatus(err.message || "Nu pot încărca setările SMS.", "error", 4000);
  }
}

async function loadSmsBalanceAndStats() {
  try {
    const balance = await apiFetch("/api/settings/sms/balance", { method: "GET" });
    if (balance.ok) {
      smsBalancePointsEl.textContent =
        balance.points !== null && balance.points !== undefined ? String(balance.points) : "-";
    } else {
      smsBalancePointsEl.textContent = "-";
      if (balance.error) showStatus(balance.error, "error", 4000);
    }
  } catch (_) {
    smsBalancePointsEl.textContent = "-";
  }

  try {
    const stats = await apiFetch("/api/sms/stats", { method: "GET" });
    smsTotalSentEl.textContent = String(stats.total_sent_success);
    smsTotalErrorsEl.textContent = String(stats.total_sent_error);
  } catch (_) {
    smsTotalSentEl.textContent = "-";
    smsTotalErrorsEl.textContent = "-";
  }
}

async function loadSmsDashboard() {
  await loadSmsSettings();
  await loadSmsBalanceAndStats();
}

// ---------- Mapare PNK → URL ----------

async function loadProductLinks() {
  if (!productLinksListEl) return;
  try {
    const data = await apiFetch("/api/product-links", { method: "GET" });
    const links = data.links || [];

    productLinksListEl.innerHTML = "";

    if (!links.length) {
      const p = document.createElement("p");
      p.classList.add("hint");
      p.textContent = "Nu există mapări PNK încă.";
      productLinksListEl.appendChild(p);
      return;
    }

    links.forEach((l) => {
      const row = document.createElement("div");
      row.classList.add("product-links-list-item");

      const main = document.createElement("div");
      main.classList.add("product-links-list-item-main");

      const codeEl = document.createElement("div");
      codeEl.classList.add("product-links-list-item-code");
      codeEl.textContent = `PNK = ${l.pnk}`;

      const urlEl = document.createElement("div");
      urlEl.classList.add("product-links-list-item-url");
      urlEl.textContent = l.review_url;

      main.appendChild(codeEl);
      main.appendChild(urlEl);

      const actions = document.createElement("div");
      actions.classList.add("product-links-list-item-actions");

      const btnEdit = document.createElement("button");
      btnEdit.classList.add("btn", "secondary", "btn-small", "btn-icon");
      btnEdit.textContent = "Editează";
      btnEdit.addEventListener("click", () => {
        productLinkPnkInput.value = l.pnk;
        productLinkUrlInput.value = l.review_url;
      });

      const btnDelete = document.createElement("button");
      btnDelete.classList.add("btn", "btn-small", "btn-icon", "btn-danger");
      btnDelete.textContent = "Șterge";
      btnDelete.addEventListener("click", async () => {
        if (!confirm(`Ștergi maparea pentru PNK ${l.pnk}?`)) return;
        try {
          await apiFetch(`/api/product-links/${encodeURIComponent(l.pnk)}`, { method: "DELETE" });
          showStatus(`Mapare PNK ${l.pnk} ștearsă.`, "success");
          await loadProductLinks();
        } catch (err) {
          showStatus(err.message || "Eroare la ștergerea mapării PNK.", "error", 6000);
        }
      });

      actions.appendChild(btnEdit);
      actions.appendChild(btnDelete);

      row.appendChild(main);
      row.appendChild(actions);

      productLinksListEl.appendChild(row);
    });
  } catch (_) {
    productLinksListEl.innerHTML = "";
    const p = document.createElement("p");
    p.classList.add("hint");
    p.textContent = "Eroare la încărcarea mapărilor PNK.";
    productLinksListEl.appendChild(p);
  }
}

if (productLinkForm) {
  productLinkForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pnk = (productLinkPnkInput.value || "").trim().toUpperCase();
    const url = (productLinkUrlInput.value || "").trim();

    if (!pnk) return showStatus("PNK nu poate fi gol.", "error");
    if (!url) return showStatus("URL de recenzie nu poate fi gol.", "error");

    try {
      await apiFetch("/api/product-links", {
        method: "POST",
        body: JSON.stringify({ pnk, review_url: url }),
      });
      showStatus("Mapare PNK → URL salvată.", "success");
      productLinkPnkInput.value = "";
      productLinkUrlInput.value = "";
      await loadProductLinks();
    } catch (err) {
      showStatus(err.message || "Eroare la salvarea mapării PNK.", "error", 6000);
    }
  });
}

if (btnProductLinksToggle && productLinksListEl) {
  btnProductLinksToggle.addEventListener("click", () => {
    const isHidden = productLinksListEl.classList.contains("hidden");
    if (isHidden) {
      productLinksListEl.classList.remove("hidden");
      btnProductLinksToggle.textContent = "Ascunde lista PNK";
      btnProductLinksToggle.classList.add("expanded");
      loadProductLinks();
    } else {
      productLinksListEl.classList.add("hidden");
      btnProductLinksToggle.textContent = "Afișează lista PNK";
      btnProductLinksToggle.classList.remove("expanded");
    }
  });
}

// ---------- Doc card SMSAPI ----------

if (btnShowSmsDoc && smsDocCard) btnShowSmsDoc.addEventListener("click", () => smsDocCard.classList.remove("hidden"));
if (btnCloseSmsDoc && smsDocCard) btnCloseSmsDoc.addEventListener("click", () => smsDocCard.classList.add("hidden"));

// ---------- Bootstrap ----------

setAuthState(false);
switchTab("login");
