// FILE: static/app.js

let accessToken = null;

// Elemente din DOM
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const userInfoEl = document.getElementById("user-info");
const statusBar = document.getElementById("status-bar");

const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");

const registerForm = document.getElementById("register-form");
const registerName = document.getElementById("register-name");
const registerEmail = document.getElementById("register-email");
const registerPassword = document.getElementById("register-password");
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

// ---------- Helpers UI ----------

function showStatus(message, type = "info", timeout = 4000) {
  if (!statusBar) return;

  statusBar.innerHTML = `
    <div class="status-bar-inner ${type === "error" ? "error" : "success"}">
      <span>${message}</span>
      <button class="btn secondary" style="pointer-events:auto;" onclick="(function(){document.getElementById('status-bar').innerHTML='';})();">Închide</button>
    </div>
  `;

  if (timeout > 0) {
    setTimeout(() => {
      if (statusBar) statusBar.innerHTML = "";
    }, timeout);
  }
}

function setLoggedInUser(user) {
  if (user && user.email) {
    userInfoEl.textContent = `Logat ca: ${user.email}`;
  } else {
    userInfoEl.textContent = "";
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

// ---------- Fetch helper ----------

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
  };

  const resp = await fetch(url, finalOptions);
  const text = await resp.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    data = text;
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

    const body = {
      email: registerEmail.value.trim(),
      name: registerName.value.trim(),
      password: registerPassword.value,
      accept_policy: true,
    };

    await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });

    showStatus("Cont creat. Te poți autentifica acum.", "success");
    switchTab("login");
    loginEmail.value = registerEmail.value;
    registerPassword.value = "";
  } catch (err) {
    showStatus(err.message || "Eroare la înregistrare.", "error");
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
    showStatus(err.message || "Eroare la login.", "error");
  }
});

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
    btnSms.onclick = () => sendSmsForOrder(o.id);
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
      smsTokenInput.placeholder =
        "Token deja salvat (lasă gol dacă nu vrei să îl schimbi)";
    } else {
      smsTokenInput.placeholder = "Introdu tokenul API din contul tău SMSAPI.ro";
    }
    if (!cfg.company_name) {
      smsCompanyInput.placeholder = "Adaugă numele firmei tale (obligatoriu pentru SMS)";
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
        balance.points !== null && balance.points !== undefined
          ? String(balance.points)
          : "-";
    } else {
      smsBalancePointsEl.textContent = "-";
      if (balance.error) {
        showStatus(balance.error, "error", 4000);
      }
    }
  } catch (err) {
    smsBalancePointsEl.textContent = "-";
  }

  try {
    const stats = await apiFetch("/api/sms/stats", { method: "GET" });
    smsTotalSentEl.textContent = String(stats.total_sent_success);
    smsTotalErrorsEl.textContent = String(stats.total_sent_error);
  } catch (err) {
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

      // Editează
      const btnEdit = document.createElement("button");
      btnEdit.classList.add("btn", "secondary", "btn-small", "btn-icon");
      const editIcon = document.createElement("span");
      editIcon.classList.add("btn-icon-symbol");
      editIcon.textContent = "✏";
      const editLabel = document.createElement("span");
      editLabel.classList.add("btn-icon-label");
      editLabel.textContent = "Editează";
      btnEdit.appendChild(editIcon);
      btnEdit.appendChild(editLabel);
      btnEdit.onclick = () => {
        productLinkPnkInput.value = l.pnk;
        productLinkUrlInput.value = l.review_url;
      };

      // Șterge
      const btnDelete = document.createElement("button");
      btnDelete.classList.add("btn", "btn-small", "btn-icon", "btn-danger");
      const delIcon = document.createElement("span");
      delIcon.classList.add("btn-icon-symbol");
      delIcon.textContent = "🗑";
      const delLabel = document.createElement("span");
      delLabel.classList.add("btn-icon-label");
      delLabel.textContent = "Șterge";
      btnDelete.appendChild(delIcon);
      btnDelete.appendChild(delLabel);
      btnDelete.onclick = async () => {
        if (!confirm(`Ștergi maparea pentru PNK ${l.pnk}?`)) return;
        try {
          await apiFetch(`/api/product-links/${encodeURIComponent(l.pnk)}`, {
            method: "DELETE",
          });
          showStatus(`Mapare PNK ${l.pnk} ștearsă.`, "success");
          await loadProductLinks();
        } catch (err) {
          showStatus(
            err.message || "Eroare la ștergerea mapării PNK.",
            "error",
            6000
          );
        }
      };

      actions.appendChild(btnEdit);
      actions.appendChild(btnDelete);

      row.appendChild(main);
      row.appendChild(actions);

      productLinksListEl.appendChild(row);
    });
  } catch (err) {
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

    if (!pnk) {
      showStatus("PNK nu poate fi gol.", "error");
      return;
    }
    if (!url) {
      showStatus("URL de recenzie nu poate fi gol.", "error");
      return;
    }

    try {
      const body = { pnk, review_url: url };
      await apiFetch("/api/product-links", {
        method: "POST",
        body: JSON.stringify(body),
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

if (btnShowSmsDoc && smsDocCard) {
  btnShowSmsDoc.addEventListener("click", () => {
    smsDocCard.classList.remove("hidden");
  });
}
if (btnCloseSmsDoc && smsDocCard) {
  btnCloseSmsDoc.addEventListener("click", () => {
    smsDocCard.classList.add("hidden");
  });
}

// ---------- Bootstrap ----------

setAuthState(false);
switchTab("login");
