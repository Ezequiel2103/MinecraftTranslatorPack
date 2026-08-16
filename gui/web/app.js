let currentSettings = null;
let isBusy = false;

function api() {
  return window.pywebview.api;
}

function showView(name) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  document.getElementById(`view-${name}`).classList.remove("hidden");
}

function setBusy(busy) {
  isBusy = busy;
  document.getElementById("btn-translate-modpack").disabled = busy;
  document.getElementById("btn-translate-mods").disabled = busy;
}

function setProgress(percent, label) {
  document.getElementById("progress-fill").style.width = `${percent}%`;
  document.getElementById("progress-label").textContent = label;
}

function setStatus(text) {
  document.getElementById("status-line").textContent = text;
}

function setResult(text, kind) {
  const box = document.getElementById("result-box");
  box.textContent = text;
  box.className = "result-box" + (kind ? ` ${kind}` : "");
}

// ---------------- settings ----------------

async function loadSettings() {
  const data = await api().get_settings();
  currentSettings = data.settings;

  const providerSelect = document.getElementById("select-provider");
  providerSelect.innerHTML = "";
  data.providers.forEach((provider) => {
    const option = document.createElement("option");
    option.value = provider;
    option.textContent = provider;
    providerSelect.appendChild(option);
  });
  providerSelect.value = currentSettings.ai_provider;

  const languageSelect = document.getElementById("select-language");
  languageSelect.innerHTML = "";
  data.languages.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.code;
    option.textContent = lang.label;
    languageSelect.appendChild(option);
  });
  languageSelect.value = currentSettings.target_language;

  document.getElementById("input-api-key").value = currentSettings.api_key || "";
  document.getElementById("input-concurrency").value = currentSettings.concurrency || 4;
  document.getElementById("input-content-only").checked = !!currentSettings.content_only;
  document.getElementById("input-pack-icon").value = currentSettings.last_pack_icon || "";

  document.getElementById("input-modpack-path").value = currentSettings.last_modpack_input || "";
  document.getElementById("input-mods-path").value = currentSettings.last_mods_input || "";
  document.getElementById("input-output-path").value = currentSettings.last_output_folder || "";
}

async function saveSettingsFromForm() {
  const settings = {
    ai_provider: document.getElementById("select-provider").value,
    api_key: document.getElementById("input-api-key").value,
    target_language: document.getElementById("select-language").value,
    concurrency: parseInt(document.getElementById("input-concurrency").value, 10) || 4,
    content_only: document.getElementById("input-content-only").checked,
    last_pack_icon: document.getElementById("input-pack-icon").value
  };

  currentSettings = await api().save_settings(settings);

  const confirmEl = document.getElementById("save-confirm");
  confirmEl.classList.remove("hidden");
  setTimeout(() => confirmEl.classList.add("hidden"), 1500);
}

async function rememberPaths() {
  await api().save_settings({
    last_modpack_input: document.getElementById("input-modpack-path").value,
    last_mods_input: document.getElementById("input-mods-path").value,
    last_output_folder: document.getElementById("input-output-path").value
  });
}

// ---------------- folder pickers ----------------

async function browseInto(inputId) {
  const path = await api().pick_folder();
  if (path) {
    document.getElementById(inputId).value = path;
  }
}

// ---------------- translation actions ----------------

async function translateModpack() {
  if (isBusy) return;

  const inputFolder = document.getElementById("input-modpack-path").value.trim();
  const outputFolder = document.getElementById("input-output-path").value.trim();
  const modsFolder = document.getElementById("input-mods-path").value.trim();

  if (!inputFolder || !outputFolder) {
    setResult("Completá la ruta del modpack y la carpeta de salida.", "error");
    return;
  }

  await rememberPaths();
  setBusy(true);
  setProgress(0, "INICIANDO...");
  setResult("");

  const response = await api().translate_modpack(inputFolder, outputFolder, modsFolder);
  if (!response.ok) {
    setResult(response.error, "error");
    setBusy(false);
  }
}

async function translateMods() {
  if (isBusy) return;

  const modsFolder = document.getElementById("input-mods-path").value.trim();
  const outputFolder = document.getElementById("input-output-path").value.trim();
  const packIcon = document.getElementById("input-pack-icon").value.trim();

  if (!modsFolder || !outputFolder) {
    setResult("Completá la carpeta de mods y la carpeta de salida.", "error");
    return;
  }

  await rememberPaths();
  setBusy(true);
  setProgress(0, "INICIANDO...");
  setResult("");

  const response = await api().translate_mods(modsFolder, outputFolder, packIcon);
  if (!response.ok) {
    setResult(response.error, "error");
    setBusy(false);
  }
}

// ---------------- backend events ----------------

window.onBackendEvent = function (event, payload) {
  if (event === "start") {
    setProgress(0, "TRADUCIENDO...");
    setStatus("");
    return;
  }

  if (event === "file_progress") {
    setStatus(`Archivo ${payload.current}/${payload.total}: ${payload.name}`);
    return;
  }

  if (event === "mod_progress") {
    setStatus(`Mod ${payload.current}/${payload.total}: ${payload.modid}`);
    return;
  }

  if (event === "text_progress") {
    const percent = payload.total ? Math.round((payload.current / payload.total) * 100) : 0;
    setProgress(percent, `TRADUCIENDO: ${percent}%`);
    return;
  }

  if (event === "done") {
    setProgress(100, "COMPLETADO");
    setBusy(false);
    const kindLabel = payload.kind === "mods" ? `Mods traducidos: ${payload.mods}` : `Archivos traducidos: ${payload.files}`;
    setResult(
      `✔ Listo.\n${kindLabel}\nPendientes de revisión: ${payload.pending}\nSalida: ${payload.output_folder}`,
      "success"
    );
    return;
  }

  if (event === "error") {
    setProgress(0, "ERROR");
    setBusy(false);
    setResult(`✖ Error: ${payload.message}`, "error");
  }
};

// ---------------- pending review ----------------

async function loadPending() {
  const list = document.getElementById("pending-list");
  list.innerHTML = "<div class=\"pending-empty\">Cargando...</div>";

  const languagePair = `${currentSettings.source_language || "en"}_${currentSettings.target_language}`;
  const items = await api().get_pending(languagePair);

  if (!items.length) {
    list.innerHTML = "<div class=\"pending-empty\">No hay textos pendientes.</div>";
    return;
  }

  list.innerHTML = "";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "pending-item";
    row.innerHTML = `
      <div class="pending-original">${escapeHtml(item.original)}</div>
      <div class="pending-path">${escapeHtml(item.path || "")} — ${escapeHtml(item.reason || "")}</div>
      <div class="pending-row">
        <input type="text" class="input-field pending-translation" placeholder="Traducción...">
        <button class="btn btn-secondary pending-approve">Aprobar</button>
      </div>
    `;

    row.querySelector(".pending-approve").addEventListener("click", async () => {
      const translation = row.querySelector(".pending-translation").value.trim();
      if (!translation) return;

      const ok = await api().approve_pending(item.original, translation, languagePair);
      if (ok) {
        row.remove();
      }
    });

    list.appendChild(row);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ---------------- wiring ----------------

window.addEventListener("pywebviewready", async () => {
  await loadSettings();

  document.getElementById("btn-settings").addEventListener("click", () => showView("settings"));
  document.getElementById("btn-pending").addEventListener("click", () => {
    showView("pending");
    loadPending();
  });
  document.getElementById("btn-minimize").addEventListener("click", () => api().minimize_window());
  document.getElementById("btn-close").addEventListener("click", () => api().close_window());

  document.getElementById("btn-browse-modpack").addEventListener("click", () => browseInto("input-modpack-path"));
  document.getElementById("btn-browse-mods").addEventListener("click", () => browseInto("input-mods-path"));
  document.getElementById("btn-browse-output").addEventListener("click", () => browseInto("input-output-path"));
  document.getElementById("btn-browse-icon").addEventListener("click", async () => {
    const path = await api().pick_image_file();
    if (path) document.getElementById("input-pack-icon").value = path;
  });

  document.getElementById("btn-translate-modpack").addEventListener("click", translateModpack);
  document.getElementById("btn-translate-mods").addEventListener("click", translateMods);
  document.getElementById("btn-save-settings").addEventListener("click", saveSettingsFromForm);
  document.getElementById("btn-refresh-pending").addEventListener("click", loadPending);

  showView("home");
});
