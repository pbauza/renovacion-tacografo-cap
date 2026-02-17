const { apiPrefix } = window.APP_CONFIG;

const logEl = document.getElementById("log");
const clientsTable = document.getElementById("clientsTable");
const documentsTable = document.getElementById("documentsTable");
const alertsTable = document.getElementById("alertsTable");
const selectedClientEl = document.getElementById("selectedClient");
const documentClientIdInput = document.getElementById("documentClientId");

let selectedClientId = null;
let lastCreatedClientId = null;
let lastCreatedDocumentId = null;
let pendingCreateClientPhoto = null;

function log(message) {
  const time = new Date().toLocaleTimeString();
  logEl.textContent = `[${time}] ${message}\n${logEl.textContent}`;
}

async function api(path, options = {}) {
  const response = await fetch(`${apiPrefix}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function queryStringFromForm(form) {
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form).entries()) {
    if (value) params.append(key, value);
  }
  return params.toString();
}

function boolValue(form, name) {
  return form.querySelector(`[name=${name}]`).checked;
}

function parseCreatePayload(form) {
  const payload = {};
  for (const [key, value] of new FormData(form).entries()) {
    if (value === "") continue;
    payload[key] = value;
  }

  payload.flag_fran = boolValue(form, "flag_fran");
  payload.flag_ciusaba = boolValue(form, "flag_ciusaba");
  payload.flag_permiso_c = boolValue(form, "flag_permiso_c");
  payload.flag_permiso_d = boolValue(form, "flag_permiso_d");
  payload.client_id = Number(payload.client_id);

  return payload;
}

function parseEditPayload(form) {
  const payload = {};
  for (const [key, value] of new FormData(form).entries()) {
    if (key === "id") continue;
    if (value !== "") payload[key] = value;
  }

  if (form.querySelector("[name=flag_fran]")) payload.flag_fran = boolValue(form, "flag_fran");
  if (form.querySelector("[name=flag_ciusaba]")) payload.flag_ciusaba = boolValue(form, "flag_ciusaba");
  if (form.querySelector("[name=flag_permiso_c]")) payload.flag_permiso_c = boolValue(form, "flag_permiso_c");
  if (form.querySelector("[name=flag_permiso_d]")) payload.flag_permiso_d = boolValue(form, "flag_permiso_d");

  return payload;
}

function installDropzone(elementId, handler) {
  const zone = document.getElementById(elementId);
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
    const file = event.dataTransfer.files?.[0];
    if (!file) return;
    await handler(file);
  });
}

function setDropzoneImagePreview(elementId, file) {
  const zone = document.getElementById(elementId);
  const reader = new FileReader();
  reader.onload = () => {
    zone.innerHTML = `
      <div class="preview-wrap">
        <img class="dropzone-preview" src="${reader.result}" alt="preview" />
        <p>${file.name}</p>
      </div>
    `;
  };
  reader.readAsDataURL(file);
}

async function uploadClientPhoto(clientId, file) {
  const form = new FormData();
  form.append("photo", file);
  await api(`/clients/${clientId}/photo`, { method: "POST", body: form });
}

async function uploadDocumentFile(documentId, file) {
  const form = new FormData();
  form.append("document_file", file);
  await api(`/documents/${documentId}/file`, { method: "POST", body: form });
}

function setSelectedClient(client) {
  selectedClientId = client.id;
  documentClientIdInput.value = String(client.id);
  selectedClientEl.textContent = `${client.id} - ${client.full_name} (${client.nif})`;
  document.getElementById("clientEditForm").querySelector("[name=id]").value = client.id;
}

async function refreshDashboard() {
  const data = await api("/reporting/dashboard");
  document.getElementById("due30").textContent = data.due_in_30_days;
  document.getElementById("due60").textContent = data.due_in_60_days;
  document.getElementById("due90").textContent = data.due_in_90_days;
  document.getElementById("documentsTotal").textContent = data.documents_total;
  document.getElementById("alertsTotal").textContent = data.alerts_total;
  document.getElementById("alertsDue").textContent = data.alerts_due_today_or_older;
}

async function refreshClients(query = "") {
  const clients = await api(`/clients${query ? `?${query}` : ""}`);
  clientsTable.innerHTML = clients
    .map((c) => `<tr data-id="${c.id}"><td>${c.id}</td><td>${c.full_name}</td><td>${c.nif}</td><td>${c.company ?? ""}</td><td>${c.phone}</td><td>${c.photo_path ?? ""}</td></tr>`)
    .join("");

  clientsTable.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      const id = Number(row.dataset.id);
      const client = clients.find((x) => x.id === id);
      if (client) {
        setSelectedClient(client);
        log(`Cliente seleccionado: ${client.full_name}`);
      }
    });
  });
}

async function refreshDocuments() {
  const docs = await api("/documents");
  documentsTable.innerHTML = docs
    .map((d) => `<tr><td>${d.id}</td><td>${d.client_id}</td><td>${d.doc_type}</td><td>${d.expiry_date ?? ""}</td><td>${d.pdf_path ?? ""}</td></tr>`)
    .join("");
}

async function refreshAlerts() {
  const alerts = await api("/alerts");
  alertsTable.innerHTML = alerts
    .map((a) => `<tr><td>${a.id}</td><td>${a.client_id}</td><td>${a.document_id ?? ""}</td><td>${a.expiry_date}</td><td>${a.alert_date}</td></tr>`)
    .join("");
}

async function refreshAll() {
  await Promise.all([refreshDashboard(), refreshClients(), refreshDocuments(), refreshAlerts()]);
}

function bindSearch() {
  const form = document.getElementById("searchForm");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await refreshClients(queryStringFromForm(form));
      log("Búsqueda ejecutada");
    } catch (error) {
      log(`Error búsqueda: ${error.message}`);
    }
  });
}

function bindClientForms() {
  document.getElementById("clientCreateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      const created = await api("/clients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      lastCreatedClientId = created.id;
      if (pendingCreateClientPhoto) {
        await uploadClientPhoto(created.id, pendingCreateClientPhoto);
        pendingCreateClientPhoto = null;
      }
      setSelectedClient(created);
      form.reset();
      await refreshAll();
      log(`Cliente creado: ${created.id}`);
    } catch (error) {
      log(`Error crear cliente: ${error.message}`);
    }
  });

  document.getElementById("clientEditForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const clientId = Number(form.querySelector("[name=id]").value);
    const payload = parseEditPayload(form);

    try {
      await api(`/clients/${clientId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refreshAll();
      log(`Cliente actualizado: ${clientId}`);
    } catch (error) {
      log(`Error editar cliente: ${error.message}`);
    }
  });
}

function bindDocumentForms() {
  document.getElementById("documentCreateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!selectedClientId) {
      log("Selecciona un cliente antes de crear documento");
      return;
    }

    try {
      const created = await api("/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parseCreatePayload(form)),
      });
      lastCreatedDocumentId = created.id;
      document.getElementById("documentEditForm").querySelector("[name=id]").value = created.id;
      form.reset();
      documentClientIdInput.value = String(selectedClientId);
      await refreshAll();
      log(`Documento creado: ${created.id} (alerta automática generada si hay caducidad)`);
    } catch (error) {
      log(`Error crear documento: ${error.message}`);
    }
  });

  document.getElementById("documentEditForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const documentId = Number(form.querySelector("[name=id]").value);
    const payload = parseEditPayload(form);

    try {
      await api(`/documents/${documentId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refreshAll();
      log(`Documento actualizado: ${documentId}`);
    } catch (error) {
      log(`Error editar documento: ${error.message}`);
    }
  });
}

function bindDropzones() {
  installDropzone("createPhotoDropzone", async (file) => {
    if (!file.type || !file.type.startsWith("image/")) {
      log("Solo se permiten imagenes para foto de cliente");
      return;
    }
    pendingCreateClientPhoto = file;
    setDropzoneImagePreview("createPhotoDropzone", file);
    log(`Foto en espera: ${file.name}. Se subira cuando el cliente se cree.`);
  });

  installDropzone("editPhotoDropzone", async (file) => {
    if (!file.type || !file.type.startsWith("image/")) {
      log("Solo se permiten imagenes para foto de cliente");
      return;
    }
    setDropzoneImagePreview("editPhotoDropzone", file);
    const clientId = Number(document.getElementById("clientEditForm").querySelector("[name=id]").value);
    if (!clientId) {
      log("Indica ID de cliente en editar cliente");
      return;
    }
    try {
      await uploadClientPhoto(clientId, file);
      await refreshAll();
      log(`Foto reemplazada para cliente ${clientId}`);
    } catch (error) {
      log(`Error reemplazo foto: ${error.message}`);
    }
  });

  installDropzone("createDocumentDropzone", async (file) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      log("Solo se permiten archivos PDF para documentos");
      return;
    }
    if (!lastCreatedDocumentId) {
      log("Primero crea un documento para subir su PDF");
      return;
    }
    try {
      await uploadDocumentFile(lastCreatedDocumentId, file);
      await refreshAll();
      log(`PDF cargado en documento ${lastCreatedDocumentId}`);
    } catch (error) {
      log(`Error subida PDF: ${error.message}`);
    }
  });

  installDropzone("editDocumentDropzone", async (file) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      log("Solo se permiten archivos PDF para documentos");
      return;
    }
    const documentId = Number(document.getElementById("documentEditForm").querySelector("[name=id]").value);
    if (!documentId) {
      log("Indica ID de documento en editar documento");
      return;
    }
    try {
      await uploadDocumentFile(documentId, file);
      await refreshAll();
      log(`PDF reemplazado para documento ${documentId}`);
    } catch (error) {
      log(`Error reemplazo PDF: ${error.message}`);
    }
  });
}

document.getElementById("refreshDashboard").addEventListener("click", async () => {
  try {
    await refreshDashboard();
    log("Dashboard actualizado");
  } catch (error) {
    log(`Error dashboard: ${error.message}`);
  }
});

(async function init() {
  bindSearch();
  bindClientForms();
  bindDocumentForms();
  bindDropzones();

  try {
    await refreshAll();
    log("GUI lista");
  } catch (error) {
    log(`Error inicial: ${error.message}`);
  }
})();
