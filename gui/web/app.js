let currentSettings = null;
let isBusy = false;
let lastScan = null;
let currentLocale = {};

function api() {
  return window.pywebview.api;
}

// ---------------- i18n ----------------

async function loadLocale(langCode) {
  currentLocale = await api().get_locale(langCode);
  document.documentElement.lang = langCode;
  applyLocale();
}

function t(key, vars) {
  let text = currentLocale[key] || key;

  if (vars) {
    Object.keys(vars).forEach((name) => {
      text = text.replace(`{${name}}`, vars[name]);
    });
  }

  return text;
}

function applyLocale() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });

  // Elements not currently showing user-entered content get their default
  // label back; anything with real state (progress %, scan results, a
  // result message) is refreshed by whatever last set it, not here.
  if (!isBusy) {
    setProgress(0, t("progress_waiting"));
  }
}

// ---------------- small state setters ----------------

function showView(name) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  document.getElementById(`view-${name}`).classList.remove("hidden");
}

function setBusy(busy) {
  isBusy = busy;
  document.getElementById("btn-translate-now").disabled = busy;
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

  await loadLocale(currentSettings.ui_language || "es");
  document.getElementById("select-ui-language").value = currentSettings.ui_language || "es";

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

  document.getElementById("input-modpack-path").value = currentSettings.last_modpack_root || "";
  document.getElementById("input-output-path").value = currentSettings.last_output_folder || "";

  if (currentSettings.last_modpack_root) {
    scanModpackPath(currentSettings.last_modpack_root);
  }
}

async function saveSettingsFromForm() {
  const newLanguage = document.getElementById("select-ui-language").value;
  const languageChanged = newLanguage !== (currentSettings.ui_language || "es");

  const settings = {
    ui_language: newLanguage,
    ai_provider: document.getElementById("select-provider").value,
    api_key: document.getElementById("input-api-key").value,
    target_language: document.getElementById("select-language").value,
    concurrency: parseInt(document.getElementById("input-concurrency").value, 10) || 4,
    content_only: document.getElementById("input-content-only").checked
  };

  currentSettings = await api().save_settings(settings);

  if (languageChanged) {
    await loadLocale(newLanguage);
  }

  const confirmEl = document.getElementById("save-confirm");
  confirmEl.classList.remove("hidden");
  setTimeout(() => confirmEl.classList.add("hidden"), 1500);
}

async function changeUiLanguage(langCode) {
  await loadLocale(langCode);
  currentSettings = await api().save_settings({ ui_language: langCode });
}

async function rememberPaths() {
  await api().save_settings({
    last_modpack_root: document.getElementById("input-modpack-path").value,
    last_output_folder: document.getElementById("input-output-path").value
  });
}

// ---------------- modpack path scanning ----------------

async function scanModpackPath(path) {
  const statusEl = document.getElementById("scan-status");

  if (!path) {
    statusEl.innerHTML = "";
    lastScan = null;
    return;
  }

  statusEl.textContent = t("scan_searching");
  lastScan = await api().scan_modpack(path);

  const questsMark = lastScan.quests_lang_folder
    ? `<span class="found">${t("scan_quests_found")}</span>`
    : `<span class="missing">${t("scan_quests_missing")}</span>`;
  const modsMark = lastScan.mods_folder
    ? `<span class="found">${t("scan_mods_found")}</span>`
    : `<span class="missing">${t("scan_mods_missing")}</span>`;

  statusEl.innerHTML = `${questsMark} &nbsp;·&nbsp; ${modsMark}`;
}

// ---------------- folder pickers ----------------

async function browseInto(inputId) {
  const path = await api().pick_folder();
  if (path) {
    document.getElementById(inputId).value = path;
  }
}

// ---------------- dictionaries: import (load a shared file) ----------------

async function importModpackDictionary() {
  const path = await api().pick_open_file([t("file_type_quest_dictionary_json")]);
  if (!path) return;

  const result = await api().import_quest_dictionary(path);
  if (result.ok) {
    setResult(t("result_import_modpack_success", { added: result.added, total: result.total }), "success");
  } else {
    setResult(t("result_error", { message: result.error }), "error");
  }
}

async function importModsDictionary() {
  const path = await api().pick_open_file([t("file_type_mods_dictionary_zip")]);
  if (!path) return;

  const result = await api().import_mods_dictionary(path);
  if (result.ok) {
    setResult(
      t("result_import_mods_success", {
        added_mods: result.added_mods,
        added_classifications: result.added_classifications
      }),
      "success"
    );
  } else {
    setResult(t("result_error", { message: result.error }), "error");
  }
}

// ---------------- dictionaries: export (share yours) ----------------

async function exportModpackDictionary() {
  const path = await api().pick_save_file(
    t("save_default_name_quest"),
    [t("file_type_quest_dictionary_json")]
  );
  if (!path) return;

  const result = await api().export_quest_dictionary(path);
  if (result.ok) {
    setResult(t("result_export_modpack_success", { path: result.path }), "success");
  }
}

async function exportModsDictionary() {
  const path = await api().pick_save_file(
    t("save_default_name_mods"),
    [t("file_type_mods_dictionary_zip")]
  );
  if (!path) return;

  const result = await api().export_mods_dictionary(path);
  if (result.ok) {
    setResult(t("result_export_mods_success", { path: result.path }), "success");
  }
}

// ---------------- translate now ----------------

async function translateNow() {
  if (isBusy) return;

  const modpackRoot = document.getElementById("input-modpack-path").value.trim();
  const outputFolder = document.getElementById("input-output-path").value.trim();

  if (!modpackRoot || !outputFolder) {
    setResult(t("error_missing_paths"), "error");
    return;
  }

  await rememberPaths();
  setBusy(true);
  setProgress(0, t("progress_starting"));
  setStatus("");
  setResult("");

  const response = await api().translate_now(modpackRoot, outputFolder);
  if (!response.ok) {
    setResult(response.error, "error");
    setBusy(false);
  }
}

// ---------------- backend events ----------------

window.onBackendEvent = function (event, payload) {
  if (event === "start") {
    setProgress(0, t(payload.phase === "mods" ? "progress_translating_mods" : "progress_translating_quests"));
    setStatus("");
    return;
  }

  if (event === "file_progress") {
    setStatus(t("status_file_progress", payload));
    return;
  }

  if (event === "mod_progress") {
    setStatus(t("status_mod_progress", payload));
    return;
  }

  if (event === "text_progress") {
    const percent = payload.total ? Math.round((payload.current / payload.total) * 100) : 0;
    setProgress(percent, t("progress_percent", { percent }));
    return;
  }

  if (event === "done") {
    setProgress(100, t("progress_done"));
    setBusy(false);
    setResult(
      t("result_done", {
        files: payload.files,
        mods: payload.mods,
        pending: payload.pending,
        output: payload.output_folder
      }),
      "success"
    );
    return;
  }

  if (event === "error") {
    setProgress(0, t("progress_error"));
    setBusy(false);
    setResult(t("result_error", { message: payload.message }), "error");
  }
};

// ---------------- pending review ----------------

async function loadPending() {
  const list = document.getElementById("pending-list");
  list.innerHTML = `<div class="pending-empty">${t("pending_loading")}</div>`;

  const languagePair = `${currentSettings.source_language || "en"}_${currentSettings.target_language}`;
  const items = await api().get_pending(languagePair);

  if (!items.length) {
    list.innerHTML = `<div class="pending-empty">${t("pending_empty")}</div>`;
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
        <input type="text" class="input-field pending-translation" placeholder="${escapeHtml(t("placeholder_pending_translation"))}">
        <button class="btn btn-secondary pending-approve">${t("btn_approve")}</button>
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

  document.getElementById("select-ui-language").addEventListener("change", (event) => {
    changeUiLanguage(event.target.value);
  });

  document.getElementById("btn-home").addEventListener("click", () => showView("home"));
  document.getElementById("btn-settings").addEventListener("click", () => showView("settings"));
  document.getElementById("btn-pending").addEventListener("click", () => {
    showView("pending");
    loadPending();
  });
  document.getElementById("btn-minimize").addEventListener("click", () => api().minimize_window());
  document.getElementById("btn-close").addEventListener("click", () => api().close_window());

  document.getElementById("btn-browse-modpack").addEventListener("click", async () => {
    await browseInto("input-modpack-path");
    scanModpackPath(document.getElementById("input-modpack-path").value.trim());
  });
  document.getElementById("input-modpack-path").addEventListener("change", (event) => {
    scanModpackPath(event.target.value.trim());
  });
  document.getElementById("btn-browse-output").addEventListener("click", () => browseInto("input-output-path"));

  document.getElementById("btn-import-modpack-dict").addEventListener("click", importModpackDictionary);
  document.getElementById("btn-import-mods-dict").addEventListener("click", importModsDictionary);
  document.getElementById("link-export-modpack-dict").addEventListener("click", (event) => {
    event.preventDefault();
    exportModpackDictionary();
  });
  document.getElementById("link-export-mods-dict").addEventListener("click", (event) => {
    event.preventDefault();
    exportModsDictionary();
  });

  document.getElementById("btn-translate-now").addEventListener("click", translateNow);
  document.getElementById("btn-save-settings").addEventListener("click", saveSettingsFromForm);
  document.getElementById("btn-refresh-pending").addEventListener("click", loadPending);

  showView("home");
});
