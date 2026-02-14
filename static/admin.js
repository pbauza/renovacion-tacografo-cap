(function () {
  const body = document.body;
  const apiPrefix = body.dataset.apiPrefix || "/api/v1";
  const page = body.dataset.page || "";

  const state = {
    clients: [],
    documents: [],
    alerts: [],
    selectedClient: null,
    pendingCreatePhotoFile: null,
    schemas: {
      client: null,
      alert: null,
      documentTypes: null,
    },
  };

  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebarNav");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  ["dragenter", "dragover", "drop"].forEach((eventName) => {
    window.addEventListener(eventName, (event) => {
      event.preventDefault();
    });
    document.addEventListener(eventName, (event) => {
      event.preventDefault();
    });
  });

  async function api(path, options = {}) {
    const response = await fetch(`${apiPrefix}${path}`, options);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${text}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function loadJSON(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Cannot load ${path}`);
    return response.json();
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function renderEmptyRow(colspan, text) {
    return `<tr><td colspan="${colspan}" class="text-muted text-center py-4">${text}</td></tr>`;
  }

  function installDropzone(zoneId, onFile) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.stopPropagation();
      zone.classList.add("dragging");
    });

    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));

    zone.addEventListener("drop", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      zone.classList.remove("dragging");
      const file = event.dataTransfer.files?.[0];
      if (!file) return;
      await onFile(file);
    });
  }

  function setImagePreview(imgId, file) {
    const img = document.getElementById(imgId);
    if (!img) return;

    const reader = new FileReader();
    reader.onload = () => {
      img.src = String(reader.result);
      img.classList.remove("d-none");
    };
    reader.readAsDataURL(file);
  }

  function resolveStorageUrl(path) {
    if (!path) return "";
    const normalized = String(path).replace(/\\/g, "/");
    if (normalized.startsWith("http://") || normalized.startsWith("https://")) return normalized;
    if (normalized.startsWith("/")) return normalized;
    if (normalized.startsWith("storage/")) return `/${normalized}`;
    return `/storage/${normalized.replace(/^storage\//, "")}`;
  }

  function isImagePath(path) {
    const lower = String(path || "").toLowerCase();
    return [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"].some((ext) => lower.endsWith(ext));
  }

  function createFieldHTML(field, prefix = "") {
    const colClass = field.col || "col-md-6";
    const name = `${prefix}${field.name}`;

    if (field.type === "checkbox") {
      return `<div class="${colClass}"><label class="form-label mb-1">${field.label}</label><div class="form-check"><input class="form-check-input" type="checkbox" name="${name}" id="${name}"><label class="form-check-label" for="${name}">${field.label}</label></div></div>`;
    }

    const inputType = field.type === "number" ? "number" : field.type === "email" ? "email" : field.type === "date" ? "date" : "text";
    return `<div class="${colClass}"><label class="form-label mb-1" for="${name}">${field.label}</label><input class="form-control" id="${name}" name="${name}" type="${inputType}" ${field.required ? "required" : ""}></div>`;
  }

  function renderFields(containerId, fields) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = fields.map((f) => createFieldHTML(f)).join("");
  }

  function getFormValues(form) {
    const out = {};
    form.querySelectorAll("input,select,textarea").forEach((el) => {
      if (!el.name) return;
      if (el.type === "checkbox") {
        out[el.name] = el.checked;
        return;
      }
      if (el.value === "") return;
      out[el.name] = el.value;
    });
    return out;
  }

  function buildDocumentPayload(form, schema) {
    const docType = form.querySelector("[name=doc_type]")?.value;
    const typeDef = schema.types[docType];

    const payload = {
      client_id: Number(form.querySelector("[name=client_id]")?.value || 0),
      doc_type: docType,
    };

    if (!typeDef) return payload;

    for (const field of typeDef.fields) {
      const input = form.querySelector(`[name=${field.name}]`);
      if (!input) continue;

      if (field.type === "checkbox") {
        payload[field.name] = input.checked;
      } else if (input.value !== "") {
        payload[field.name] = input.value;
      }
    }

    return payload;
  }

  function renderDocumentDynamicFields(docType) {
    const schema = state.schemas.documentTypes;
    if (!schema) return;

    const typeDef = schema.types[docType];
    const container = document.getElementById("documentDynamicFields");
    if (!container) return;

    if (!typeDef) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = typeDef.fields.map((field) => createFieldHTML(field)).join("");
  }

  function resetDocumentForm(createForm, docTypeSelect) {
    if (!createForm) return;
    createForm.reset();

    const editIdInput = createForm.querySelector("[name=document_id]");
    if (editIdInput) editIdInput.value = "";

    const editBanner = document.getElementById("documentEditBanner");
    const submitBtn = document.getElementById("documentSubmitBtn");
    const tableBody = document.getElementById("documentsTableBody");
    if (editBanner) editBanner.classList.add("d-none");
    if (submitBtn) submitBtn.textContent = "Create Document";
    if (tableBody) tableBody.querySelectorAll("tr").forEach((row) => row.classList.remove("table-active"));

    if (docTypeSelect) {
      renderDocumentDynamicFields(docTypeSelect.value);
    }
  }

  function fillDocumentForm(createForm, docTypeSelect, documentData) {
    if (!createForm || !docTypeSelect || !documentData) return;

    const editIdInput = createForm.querySelector("[name=document_id]");
    if (editIdInput) editIdInput.value = String(documentData.id);

    const clientIdInput = createForm.querySelector("[name=client_id]");
    if (clientIdInput) clientIdInput.value = String(documentData.client_id ?? "");

    docTypeSelect.value = documentData.doc_type;
    renderDocumentDynamicFields(docTypeSelect.value);

    const typeDef = state.schemas.documentTypes?.types?.[documentData.doc_type];
    if (typeDef) {
      typeDef.fields.forEach((field) => {
        const input = createForm.querySelector(`[name=${field.name}]`);
        if (!input) return;

        const value = documentData[field.name];
        if (field.type === "checkbox") {
          input.checked = Boolean(value);
        } else {
          input.value = value == null ? "" : String(value);
        }
      });
    }

    const editBanner = document.getElementById("documentEditBanner");
    const editIdText = document.getElementById("documentEditingIdText");
    const submitBtn = document.getElementById("documentSubmitBtn");
    if (editBanner) editBanner.classList.remove("d-none");
    if (editIdText) editIdText.textContent = `#${documentData.id}`;
    if (submitBtn) submitBtn.textContent = "Update Document";
  }

  async function refreshHeaderStats() {
    const summary = await api("/reporting/dashboard");
    setText("headerStat30", summary.due_in_30_days);
    setText("headerStat60", summary.due_in_60_days);
    setText("headerStat90", summary.due_in_90_days);

    setText("kpi30", summary.due_in_30_days);
    setText("kpi60", summary.due_in_60_days);
    setText("kpi90", summary.due_in_90_days);
    const missingDocs = await api("/documents?missing_pdf=true");
    const docs = await api("/documents?expiration_status=expired");
    setText("kpiMissing", missingDocs.length);
    setText("kpiExpired", docs.length);
  }

  async function loadClients(filters = "") {
    state.clients = await api(`/clients${filters ? `?${filters}` : ""}`);

    const bodyEl = document.getElementById("clientsTableBody");
    if (!bodyEl) return;

    if (!state.clients.length) {
      bodyEl.innerHTML = renderEmptyRow(6, "No clients found.");
      return;
    }

    bodyEl.innerHTML = state.clients
      .map((c) => `<tr data-id="${c.id}"><td>${c.id}</td><td>${c.full_name}</td><td>${c.nif}</td><td>${c.company ?? ""}</td><td>${c.phone}</td><td>${c.email ?? ""}</td></tr>`)
      .join("");

    bodyEl.querySelectorAll("tr[data-id]").forEach((row) => {
      row.addEventListener("click", async () => {
        await selectClient(Number(row.dataset.id));
      });
    });
  }

  async function selectClient(clientId) {
    const client = state.clients.find((x) => x.id === clientId) || await api(`/clients/${clientId}`);
    state.selectedClient = client;

    setText("detailFullName", client.full_name || "--");
    setText("detailNif", client.nif || "--");
    setText("detailCompany", client.company || "--");
    setText("detailPhone", client.phone || "--");

    const selected = document.getElementById("selectedClientId");
    if (selected) selected.value = String(client.id);

    const form = document.getElementById("clientEditForm");
    if (form) {
      form.querySelector("[name=full_name]").value = client.full_name || "";
      form.querySelector("[name=company]").value = client.company || "";
      form.querySelector("[name=nif]").value = client.nif || "";
      form.querySelector("[name=phone]").value = client.phone || "";
      form.querySelector("[name=email]").value = client.email || "";
    }

    const preview = document.getElementById("clientPhotoPreview");
    if (preview) {
      if (client.photo_path && isImagePath(client.photo_path)) {
        preview.src = resolveStorageUrl(client.photo_path);
        preview.classList.remove("d-none");
      } else {
        preview.classList.add("d-none");
      }
    }
  }

  async function loadDocuments(filters = "") {
    state.documents = await api(`/documents${filters ? `?${filters}` : ""}`);
    const tbody = document.getElementById("documentsTableBody");
    if (!tbody) return;

    if (!state.documents.length) {
      tbody.innerHTML = renderEmptyRow(6, "No documents found.");
      return;
    }

    const clientById = Object.fromEntries(state.clients.map((c) => [c.id, c]));
    tbody.innerHTML = state.documents
      .map((d) => {
        const client = clientById[d.client_id];
        return `<tr>
          <td>${d.id}</td>
          <td>${client ? `${client.full_name} (${client.nif})` : d.client_id}</td>
          <td>${d.doc_type}</td>
          <td>${d.expiry_date ?? ""}</td>
          <td>${d.pdf_path ? "yes" : "no"}</td>
          <td><button class="btn btn-sm btn-outline-danger" data-delete-doc="${d.id}">Delete</button></td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll("tr").forEach((row, index) => {
      row.addEventListener("click", () => {
        const documentData = state.documents[index];
        if (!documentData) return;

        const createForm = document.getElementById("documentCreateForm");
        const docTypeSelect = createForm ? createForm.querySelector("[name=doc_type]") : null;
        fillDocumentForm(createForm, docTypeSelect, documentData);
        tbody.querySelectorAll("tr").forEach((r) => r.classList.remove("table-active"));
        row.classList.add("table-active");
      });
    });

    tbody.querySelectorAll("button[data-delete-doc]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const id = Number(btn.dataset.deleteDoc);
        if (!confirm(`Delete document ${id}?`)) return;
        await api(`/documents/${id}`, { method: "DELETE" });
        await refreshDocumentsPage();
      });
    });

    renderMissingDocsReport();
  }

  function renderMissingDocsReport() {
    const report = document.getElementById("missingDocsReport");
    if (!report) return;

    const byType = state.documents.reduce((acc, d) => {
      if (!d.pdf_path) acc[d.doc_type] = (acc[d.doc_type] || 0) + 1;
      return acc;
    }, {});

    if (!Object.keys(byType).length) {
      report.textContent = "No missing PDF documents.";
      return;
    }

    report.innerHTML = `<ul class="list-group list-group-flush">${Object.entries(byType)
      .map(([type, count]) => `<li class="list-group-item d-flex justify-content-between"><span>${type}</span><span class="badge text-bg-danger">${count}</span></li>`)
      .join("")}</ul>`;
  }

  async function loadAlerts(filters = "") {
    state.alerts = await api(`/alerts${filters ? `?${filters}` : ""}`);
    const tbody = document.getElementById("alertsTableBody");
    const dbTbody = document.getElementById("dashboardAlertsBody");

    const clientById = Object.fromEntries(state.clients.map((c) => [c.id, c]));
    const docById = Object.fromEntries(state.documents.map((d) => [d.id, d]));

    if (tbody) {
      if (!state.alerts.length) {
        tbody.innerHTML = renderEmptyRow(6, "No alerts found.");
      } else {
        tbody.innerHTML = state.alerts
          .map((a) => {
            const client = clientById[a.client_id];
            const doc = a.document_id ? docById[a.document_id] : null;
            return `<tr>
              <td>${a.id}</td>
              <td>${client ? client.full_name : a.client_id}</td>
              <td>${doc ? doc.doc_type : "--"}</td>
              <td>${a.expiry_date}</td>
              <td>${a.alert_date}</td>
              <td><a class="btn btn-sm btn-outline-secondary" href="/clients?client_id=${a.client_id}">View Client</a></td>
            </tr>`;
          })
          .join("");
      }
    }

    if (dbTbody) {
      const top = state.alerts.slice(0, 10);
      dbTbody.innerHTML = top.length
        ? top.map((a) => {
            const client = clientById[a.client_id];
            const doc = a.document_id ? docById[a.document_id] : null;
            return `<tr><td>${client ? client.full_name : a.client_id}</td><td>${doc ? doc.doc_type : "--"}</td><td>${a.expiry_date}</td><td>${a.alert_date}</td></tr>`;
          }).join("")
        : renderEmptyRow(4, "No alerts loaded yet.");
    }
  }

  function renderDashboardClients() {
    const tbody = document.getElementById("dashboardClientsBody");
    if (!tbody) return;
    const rows = state.clients.slice(0, 10);
    tbody.innerHTML = rows.length
      ? rows.map((c) => `<tr><td>${c.id}</td><td>${c.full_name}</td><td>${c.nif}</td><td>${c.company ?? ""}</td></tr>`).join("")
      : renderEmptyRow(4, "No clients loaded yet.");
  }

  function renderDashboardDocuments() {
    const tbody = document.getElementById("dashboardDocumentsBody");
    if (!tbody) return;
    const clientById = Object.fromEntries(state.clients.map((c) => [c.id, c]));
    const rows = state.documents.slice(0, 10);
    tbody.innerHTML = rows.length
      ? rows.map((d) => `<tr><td>${d.id}</td><td>${clientById[d.client_id]?.full_name ?? d.client_id}</td><td>${d.doc_type}</td><td>${d.expiry_date ?? ""}</td></tr>`).join("")
      : renderEmptyRow(4, "No documents loaded yet.");
  }

  async function refreshDashboardPage() {
    await Promise.all([refreshHeaderStats(), loadClients(), loadDocuments(), loadAlerts()]);
    renderDashboardClients();
    renderDashboardDocuments();
  }

  async function refreshClientsPage(filters = "") {
    await loadClients(filters);
  }

  async function refreshAlertsPage(filters = "") {
    await Promise.all([loadClients(), loadDocuments(), loadAlerts(filters)]);
  }

  async function refreshDocumentsPage(filters = "") {
    await Promise.all([loadClients(), loadDocuments(filters)]);
  }

  async function bindClientsPage() {
    const form = document.getElementById("clientsSearchForm");
    const refreshBtn = document.getElementById("refreshClientsBtn");

    if (form) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await refreshClientsPage(new URLSearchParams(getFormValues(form)).toString());
      });
    }
    if (refreshBtn) refreshBtn.addEventListener("click", async () => refreshClientsPage());

    const editForm = document.getElementById("clientEditForm");
    if (editForm) {
      editForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const id = Number(document.getElementById("selectedClientId")?.value || "0");
        if (!id) return;
        await api(`/clients/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(getFormValues(editForm)),
        });
        await refreshClientsPage();
        await selectClient(id);
      });
    }

    const deleteBtn = document.getElementById("deleteClientBtn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        const id = Number(document.getElementById("selectedClientId")?.value || "0");
        if (!id || !confirm(`Delete client ${id}?`)) return;
        await api(`/clients/${id}`, { method: "DELETE" });
        await refreshClientsPage();
      });
    }

    const uploadClientPhoto = async (file) => {
      const isImage = file.type.startsWith("image/");
      const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!isImage && !isPdf) return;
      if (isImage) setImagePreview("clientPhotoPreview", file);

      const id = Number(document.getElementById("selectedClientId")?.value || "0");
      if (!id) return;

      const data = new FormData();
      data.append("photo", file);
      await api(`/clients/${id}/photo`, { method: "POST", body: data });
      await refreshClientsPage();
      await selectClient(id);
    };

    installDropzone("clientPhotoDropzone", uploadClientPhoto);

    const genClientPdfBtn = document.getElementById("generateClientPdfBtn");
    if (genClientPdfBtn) {
      genClientPdfBtn.addEventListener("click", async () => {
        const id = Number(document.getElementById("selectedClientId")?.value || "0");
        if (!id) return;
        const result = await api(`/tools/pdf/client/${id}`, { method: "POST" });
        alert(`PDF generated: ${result.path}`);
      });
    }

    await refreshClientsPage();
    const qs = new URLSearchParams(window.location.search);
    const clientId = Number(qs.get("client_id") || "0");
    if (clientId) await selectClient(clientId);
  }

  async function bindAlertsPage() {
    if (state.schemas.alert) {
      renderFields("alertCreateFields", state.schemas.alert.fields);
    }

    const filterForm = document.getElementById("alertsFilterForm");
    if (filterForm) {
      filterForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await refreshAlertsPage(new URLSearchParams(getFormValues(filterForm)).toString());
      });
    }

    const createForm = document.getElementById("alertCreateForm");
    if (createForm) {
      createForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = getFormValues(createForm);
        payload.client_id = Number(payload.client_id);
        if (payload.document_id) payload.document_id = Number(payload.document_id);
        await api("/alerts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        createForm.reset();
        await refreshAlertsPage();
      });
    }

    const refreshBtn = document.getElementById("refreshAlertsBtn");
    if (refreshBtn) refreshBtn.addEventListener("click", async () => refreshAlertsPage());

    await refreshAlertsPage();
  }

  async function bindDocumentsPage() {
    const createForm = document.getElementById("documentCreateForm");
    const filtersForm = document.getElementById("documentsFilterForm");
    const refreshBtn = document.getElementById("refreshDocumentsBtn");
    const pdfUpload = document.getElementById("documentPdfUpload");
    const finderInput = document.getElementById("documentClientFinder");
    const finderResults = document.getElementById("documentClientFinderResults");
    const cancelEditBtn = document.getElementById("cancelDocumentEditBtn");

    const docTypeSelect = createForm ? createForm.querySelector("[name=doc_type]") : null;
    if (docTypeSelect && state.schemas.documentTypes) {
      renderDocumentDynamicFields(docTypeSelect.value);
      docTypeSelect.addEventListener("change", () => renderDocumentDynamicFields(docTypeSelect.value));
    }

    async function runClientFinder(query) {
      if (!finderResults) return;
      if (!query || query.trim().length < 2) {
        finderResults.innerHTML = "";
        finderResults.classList.add("d-none");
        return;
      }

      const clients = await api(`/clients?q=${encodeURIComponent(query.trim())}`);
      if (!clients.length) {
        finderResults.innerHTML = '<div class="list-group-item text-muted">No clients found</div>';
        finderResults.classList.remove("d-none");
        return;
      }

      finderResults.innerHTML = clients
        .slice(0, 8)
        .map((c) => `<button type="button" class="list-group-item list-group-item-action" data-client-id="${c.id}" data-client-name="${c.full_name}" data-client-nif="${c.nif}">${c.full_name} (${c.nif})${c.company ? ` - ${c.company}` : ""}</button>`)
        .join("");

      finderResults.classList.remove("d-none");
      finderResults.querySelectorAll("[data-client-id]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const clientId = btn.getAttribute("data-client-id");
          const fullName = btn.getAttribute("data-client-name");
          const nif = btn.getAttribute("data-client-nif");

          const clientIdInput = createForm?.querySelector("[name=client_id]");
          if (clientIdInput) clientIdInput.value = clientId || "";
          if (finderInput) finderInput.value = `${fullName} (${nif})`;

          finderResults.classList.add("d-none");
          finderResults.innerHTML = "";
        });
      });
    }

    if (finderInput) {
      let finderTimer = null;
      finderInput.addEventListener("input", () => {
        if (finderTimer) clearTimeout(finderTimer);
        finderTimer = setTimeout(() => {
          runClientFinder(finderInput.value).catch((err) => console.error(err));
        }, 220);
      });

      finderInput.addEventListener("focus", () => {
        if (finderInput.value.trim().length >= 2) {
          runClientFinder(finderInput.value).catch((err) => console.error(err));
        }
      });
    }

    if (createForm) {
      createForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = buildDocumentPayload(createForm, state.schemas.documentTypes);
        const editingId = Number(createForm.querySelector("[name=document_id]")?.value || "0");

        const saved = editingId
          ? await api(`/documents/${editingId}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            })
          : await api("/documents", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });

        if (pdfUpload && pdfUpload.files && pdfUpload.files[0]) {
          const formData = new FormData();
          formData.append("document_file", pdfUpload.files[0]);
          await api(`/documents/${saved.id}/file`, { method: "POST", body: formData });
          pdfUpload.value = "";
        }

        resetDocumentForm(createForm, docTypeSelect);
        await refreshDocumentsPage();
      });
    }

    if (cancelEditBtn) {
      cancelEditBtn.addEventListener("click", () => {
        resetDocumentForm(createForm, docTypeSelect);
      });
    }

    if (filtersForm) {
      filtersForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await refreshDocumentsPage(new URLSearchParams(getFormValues(filtersForm)).toString());
      });
    }

    if (refreshBtn) refreshBtn.addEventListener("click", async () => refreshDocumentsPage());

    resetDocumentForm(createForm, docTypeSelect);
    await refreshDocumentsPage();
  }

  async function bindToolsPage() {
    if (state.schemas.client) {
      renderFields("toolCreateClientFields", state.schemas.client.fields);
    }

    const createForm = document.getElementById("toolCreateClientForm");
    const photoInput = document.getElementById("toolCreatePhotoInput");
    const photoDropzone = document.getElementById("toolCreatePhotoDropzone");
    const importInput = document.getElementById("importFileInput");
    const runImportBtn = document.getElementById("runImportBtn");
    const importResult = document.getElementById("importResult");
    const generateBulkPdfBtn = document.getElementById("generateBulkPdfBtn");
    const pdfResult = document.getElementById("pdfResult");
    const refreshLogsBtn = document.getElementById("refreshLogsBtn");
    const logsEl = document.getElementById("systemLogs");

    const setPendingPhoto = (file) => {
      const isImage = file.type.startsWith("image/");
      const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!isImage && !isPdf) return;
      state.pendingCreatePhotoFile = file;
      const preview = document.getElementById("toolCreatePhotoPreview");
      if (isImage) {
        setImagePreview("toolCreatePhotoPreview", file);
      } else if (preview) {
        preview.classList.add("d-none");
      }
    };

    installDropzone("toolCreatePhotoDropzone", async (file) => setPendingPhoto(file));

    if (photoDropzone && photoInput) {
      photoDropzone.addEventListener("click", () => photoInput.click());
      photoInput.addEventListener("change", () => {
        const file = photoInput.files?.[0];
        if (file) setPendingPhoto(file);
      });
    }

    if (createForm) {
      createForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const created = await api("/clients", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(getFormValues(createForm)),
        });

        if (state.pendingCreatePhotoFile) {
          const photo = new FormData();
          photo.append("photo", state.pendingCreatePhotoFile);
          await api(`/clients/${created.id}/photo`, { method: "POST", body: photo });
          state.pendingCreatePhotoFile = null;
        }

        createForm.reset();
        alert(`Client created: ${created.id}`);
      });
    }

    if (runImportBtn) {
      runImportBtn.addEventListener("click", async () => {
        if (!importInput || !importInput.files || !importInput.files[0]) return;
        const data = new FormData();
        data.append("file", importInput.files[0]);
        const result = await api("/tools/import/clients", { method: "POST", body: data });
        if (importResult) importResult.textContent = JSON.stringify(result, null, 2);
      });
    }

    if (generateBulkPdfBtn) {
      generateBulkPdfBtn.addEventListener("click", async () => {
        const result = await api("/tools/pdf/bulk", { method: "POST" });
        if (pdfResult) pdfResult.textContent = JSON.stringify(result, null, 2);
      });
    }

    async function refreshLogs() {
      if (!logsEl) return;
      const result = await api("/tools/logs?limit=200");
      logsEl.textContent = result.lines.join("\n") || "No logs yet.";
    }

    if (refreshLogsBtn) refreshLogsBtn.addEventListener("click", refreshLogs);
    await refreshLogs();
  }

  async function loadSchemas() {
    const [clientSchema, alertSchema, docSchema] = await Promise.all([
      loadJSON("/static/config/forms/client.json"),
      loadJSON("/static/config/forms/alert.json"),
      loadJSON("/static/config/forms/document_types.json"),
    ]);

    state.schemas.client = clientSchema;
    state.schemas.alert = alertSchema;
    state.schemas.documentTypes = docSchema;
  }

  async function bootstrap() {
    await loadSchemas();
    await refreshHeaderStats();

    if (page === "dashboard") {
      await refreshDashboardPage();
      return;
    }
    if (page === "clients") {
      await bindClientsPage();
      return;
    }
    if (page === "alerts") {
      await bindAlertsPage();
      return;
    }
    if (page === "documents") {
      await bindDocumentsPage();
      return;
    }
    if (page === "tools") {
      await bindToolsPage();
      return;
    }
  }

  bootstrap().catch((err) => {
    console.error(err);
    alert(`UI error: ${err.message}`);
  });
})();
