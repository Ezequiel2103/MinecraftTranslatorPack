let currentSettings = null;
let isBusy = false;
let isPaused = false;
let lastScan = null;
let currentLocale = {};

// ---------------- estimated time remaining ----------------
// Recalibrated every time a phase starts (quests, then mods) since the
// two can translate at very different speeds.
//
// The estimate is driven by actual TEXTS translated, not by files/mods
// completed -- a modpack can have hundreds of mods, so tracking progress
// by "files done" barely moves while working through the first one and
// makes the estimate look frozen. Instead this tracks a running total of
// items already translated (etaItemsDoneCumulative, topped up with the
// current file's progress) against a projected grand total: the items
// already accounted for, plus an estimate for files not started yet
// based on the average items-per-file seen so far. A skipped/cached
// file (no AI work needed) contributes 0 to that average, which is
// correct -- it costs no time, so it shouldn't count as "a file's worth
// of work" when projecting what's left.
let etaPhaseStart = null;
let etaFilesTotal = 0;
let etaFileIndex = 0;
let etaCurrentFileTotal = 0;
let etaItemsDoneCumulative = 0;
let etaPauseStart = null;

function resetEta() {
  etaPhaseStart = Date.now();
  etaFilesTotal = 0;
  etaFileIndex = 0;
  etaCurrentFileTotal = 0;
  etaItemsDoneCumulative = 0;
  document.getElementById("eta-line").textContent = "";
}

function clearEta() {
  etaPhaseStart = null;
  document.getElementById("eta-line").textContent = "";
}

function advanceEtaFile(current, total) {
  // A new file/mod just started -- whatever the previous one's item
  // total was is now fully "done" (it wouldn't be starting a new one
  // otherwise), so bank it before resetting for the new file.
  if (etaCurrentFileTotal > 0) {
    etaItemsDoneCumulative += etaCurrentFileTotal;
  }
  etaFilesTotal = total;
  etaFileIndex = current;
  etaCurrentFileTotal = 0;
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) return `${hours} h ${minutes} min`;
  if (minutes > 0) return `${minutes} min ${seconds}s`;
  return `${seconds}s`;
}

function updateEta(itemCurrent, itemTotal) {
  if (!etaPhaseStart || !itemTotal) return;

  etaCurrentFileTotal = itemTotal;

  const itemsDoneNow = etaItemsDoneCumulative + itemCurrent;
  const itemsKnownSoFar = etaItemsDoneCumulative + etaCurrentFileTotal;
  const filesSeen = Math.max(1, etaFileIndex);
  const avgItemsPerFile = itemsKnownSoFar / filesSeen;
  const filesRemaining = Math.max(0, etaFilesTotal - etaFileIndex);
  const estimatedTotalItems = itemsKnownSoFar + (filesRemaining * avgItemsPerFile);

  if (estimatedTotalItems <= 0) return;

  if (itemsDoneNow <= 0) return;

  const overallFraction = itemsDoneNow / estimatedTotalItems;
  const elapsedMs = Date.now() - etaPhaseStart;
  const remainingMs = (elapsedMs / overallFraction) - elapsedMs;

  document.getElementById("eta-line").textContent = t("label_eta", {
    time: formatDuration(remainingMs)
  });
}

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
  updatePauseButtonLabel();
}

// ---------------- small state setters ----------------

function showView(name) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  document.getElementById(`view-${name}`).classList.remove("hidden");
}

function setBusy(busy) {
  isBusy = busy;
  document.getElementById("btn-translate-now").disabled = busy;
  document.getElementById("run-controls").classList.toggle("hidden", !busy);

  if (!busy) {
    isPaused = false;
  }
  updatePauseButtonLabel();
}

function updatePauseButtonLabel() {
  document.getElementById("btn-pause-resume").textContent = t(isPaused ? "btn_resume" : "btn_pause");
}

async function togglePauseResume() {
  if (isPaused) {
    await api().resume_translation();
    isPaused = false;
  } else {
    await api().pause_translation();
    isPaused = true;
  }
  updatePauseButtonLabel();
}

async function cancelTranslation() {
  if (!confirm(t("confirm_cancel"))) return;
  await api().cancel_translation();
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
    option.textContent = t(`provider_${provider}`);
    providerSelect.appendChild(option);
  });
  providerSelect.value = currentSettings.ai_provider;
  toggleGoogleUsageVisibility();

  const fallbackSelect = document.getElementById("select-fallback-provider");
  fallbackSelect.innerHTML = "";
  ["none", ...data.providers].forEach((provider) => {
    const option = document.createElement("option");
    option.value = provider;
    option.textContent = t(`provider_${provider}`);
    fallbackSelect.appendChild(option);
  });
  fallbackSelect.value = currentSettings.fallback_ai_provider || "none";
  document.getElementById("input-fallback-api-key").value = currentSettings.fallback_api_key || "";

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
  document.getElementById("input-curseforge-key").value = currentSettings.curseforge_api_key || "";

  document.getElementById("input-modpack-path").value = currentSettings.last_modpack_root || "";

  if (currentSettings.last_modpack_root) {
    scanModpackPath(currentSettings.last_modpack_root);
  }
}

function toggleGoogleUsageVisibility() {
  const isGoogle = document.getElementById("select-provider").value === "google";
  document.getElementById("google-usage-box").classList.toggle("hidden", !isGoogle);
  if (isGoogle) {
    loadGoogleUsage();
  }
}

async function loadGoogleUsage() {
  const usage = await api().get_google_usage();
  const fill = document.getElementById("google-usage-fill");
  const text = document.getElementById("google-usage-text");

  fill.style.width = `${usage.percent}%`;
  fill.classList.toggle("usage-warning", usage.percent >= 90);
  text.textContent = t("google_usage_text", {
    used: usage.used.toLocaleString(),
    limit: usage.limit.toLocaleString(),
    percent: usage.percent
  });
}

async function saveSettingsFromForm() {
  const newLanguage = document.getElementById("select-ui-language").value;
  const languageChanged = newLanguage !== (currentSettings.ui_language || "es");

  const settings = {
    ui_language: newLanguage,
    ai_provider: document.getElementById("select-provider").value,
    api_key: document.getElementById("input-api-key").value,
    fallback_ai_provider: document.getElementById("select-fallback-provider").value,
    fallback_api_key: document.getElementById("input-fallback-api-key").value,
    target_language: document.getElementById("select-language").value,
    concurrency: parseInt(document.getElementById("input-concurrency").value, 10) || 4,
    content_only: document.getElementById("input-content-only").checked,
    curseforge_api_key: document.getElementById("input-curseforge-key").value
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
  refreshProviderLabels();
}

function refreshProviderLabels() {
  document.querySelectorAll("#select-provider option, #select-fallback-provider option").forEach((option) => {
    option.textContent = t(`provider_${option.value}`);
  });
}

async function rememberPaths() {
  await api().save_settings({
    last_modpack_root: document.getElementById("input-modpack-path").value
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

// ---------------- memory stats (how much has been "learned") ----------------

async function refreshMemoryStats() {
  const stats = await api().get_memory_stats();
  document.getElementById("memory-stats").textContent = t("label_memory_stats", {
    quests: stats.quest_count.toLocaleString(),
    glossary: stats.glossary_count.toLocaleString()
  });
}

// ---------------- dictionaries: import (load a shared file) ----------------

async function importModpackDictionary() {
  const path = await api().pick_open_file([t("file_type_quest_dictionary_json")]);
  if (!path) return;

  const result = await api().import_quest_dictionary(path);
  if (result.ok) {
    setResult(t("result_import_modpack_success", { added: result.added, total: result.total }), "success");
    refreshMemoryStats();
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
    refreshMemoryStats();
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

// ---------------- resource pack merging ----------------

async function mergeResourcepacks() {
  const paths = await api().pick_open_files_multiple([
    t("file_type_resourcepack_zip")
  ]);
  if (!paths || paths.length < 2) {
    if (paths && paths.length === 1) {
      setResult(t("result_merge_need_two"), "error");
    }
    return;
  }

  const outputFolder = await api().pick_folder();
  if (!outputFolder) return;

  const result = await api().merge_resourcepacks_now(paths, outputFolder);
  if (result.ok) {
    setResult(
      t("result_merge_success", {
        mods: result.merged_mods.length,
        conflicts: result.conflicts.length,
        output: result.output_path
      }),
      "success"
    );
  } else {
    setResult(t("result_error", { message: result.error }), "error");
  }
}

// ---------------- community translation search (CurseForge) ------------

async function searchCommunityTranslations() {
  const modpackRoot = document.getElementById("input-modpack-path").value.trim();
  const resultsBox = document.getElementById("community-results");

  if (!modpackRoot) {
    setResult(t("error_missing_paths"), "error");
    return;
  }

  resultsBox.classList.remove("hidden");
  resultsBox.innerHTML = `<div class="pending-empty">${t("community_searching")}</div>`;

  const response = await api().search_community_translations(modpackRoot);

  if (!response.ok) {
    if (response.error === "curseforge_key_missing") {
      resultsBox.innerHTML = `<div class="pending-empty">${t("community_key_missing")}</div>`;
    } else {
      resultsBox.innerHTML = `<div class="pending-empty">${escapeHtml(response.error)}</div>`;
    }
    return;
  }

  if (!response.results.length) {
    resultsBox.innerHTML = `<div class="pending-empty">${t("community_no_results", { query: response.query })}</div>`;
    return;
  }

  resultsBox.innerHTML = "";
  response.results.forEach((candidate) => {
    const row = document.createElement("div");
    row.className = "pending-item";
    row.innerHTML = `
      <div class="pending-original">${escapeHtml(candidate.name)}</div>
      <div class="pending-path">${escapeHtml(candidate.summary || "")} — ${candidate.download_count.toLocaleString()} descargas</div>
      <div class="pending-row">
        <button class="btn btn-secondary community-use">${t("btn_use_this")}</button>
      </div>
    `;

    row.querySelector(".community-use").addEventListener("click", async () => {
      row.querySelector(".community-use").disabled = true;
      row.querySelector(".community-use").textContent = t("community_importing");

      const importResult = await api().import_community_translation(
        candidate.download_url, candidate.file_name, modpackRoot
      );

      if (importResult.ok) {
        setResult(
          t("result_community_import_success", {
            mods: importResult.mods_matched,
            pairs: importResult.pairs_added
          }),
          "success"
        );
        resultsBox.classList.add("hidden");
        resultsBox.innerHTML = "";
        refreshMemoryStats();
      } else {
        setResult(t("result_error", { message: importResult.error }), "error");
        row.querySelector(".community-use").disabled = false;
        row.querySelector(".community-use").textContent = t("btn_use_this");
      }
    });

    resultsBox.appendChild(row);
  });
}

// ---------------- translate now ----------------

async function translateNow() {
  if (isBusy) return;

  const modpackRoot = document.getElementById("input-modpack-path").value.trim();
  const translateQuests = document.getElementById("input-translate-quests").checked;
  const translateMods = document.getElementById("input-translate-mods").checked;

  if (!modpackRoot) {
    setResult(t("error_missing_paths"), "error");
    return;
  }

  if (!translateQuests && !translateMods) {
    setResult(t("error_nothing_selected"), "error");
    return;
  }

  await rememberPaths();
  setBusy(true);
  setProgress(0, t("progress_starting"));
  setStatus("");
  setResult("");
  clearEta();

  const response = await api().translate_now(modpackRoot, translateQuests, translateMods);
  if (!response.ok) {
    setResult(response.error, "error");
    setBusy(false);
  }
}

function resultMessage(key, payload) {
  let message = t(key, {
    files: payload.files,
    mods: payload.mods,
    pending: payload.pending,
    used: payload.used ? payload.used.toLocaleString() : undefined,
    limit: payload.limit ? payload.limit.toLocaleString() : undefined
  });

  if (payload.backup_dir) {
    message += "\n" + t("result_backup_note", { backup: payload.backup_dir });
  }

  return message;
}

// ---------------- backend events ----------------

window.onBackendEvent = function (event, payload) {
  if (event === "start") {
    setProgress(0, t(payload.phase === "mods" ? "progress_translating_mods" : "progress_translating_quests"));
    setStatus("");
    resetEta();
    return;
  }

  if (event === "file_progress") {
    setStatus(t("status_file_progress", payload));
    advanceEtaFile(payload.current, payload.total);
    return;
  }

  if (event === "mod_progress") {
    setStatus(t("status_mod_progress", payload));
    advanceEtaFile(payload.current, payload.total);
    return;
  }

  if (event === "text_progress") {
    const percent = payload.total ? Math.round((payload.current / payload.total) * 100) : 0;
    setProgress(percent, t("progress_percent", { percent }));
    updateEta(payload.current, payload.total);
    return;
  }

  if (event === "done") {
    setProgress(100, t("progress_done"));
    setBusy(false);
    clearEta();
    setResult(resultMessage("result_done", payload), "success");
    toggleGoogleUsageVisibility();
    refreshMemoryStats();
    return;
  }

  if (event === "quota_exceeded") {
    setProgress(0, t("progress_quota_exceeded"));
    setBusy(false);
    clearEta();
    setResult(resultMessage("result_quota_exceeded", payload), "error");
    toggleGoogleUsageVisibility();
    return;
  }

  if (event === "cancelled") {
    setProgress(0, t("progress_cancelled"));
    setBusy(false);
    clearEta();
    setResult(resultMessage("result_cancelled", payload), "success");
    refreshMemoryStats();
    return;
  }

  if (event === "paused") {
    setStatus(t("status_paused"));
    etaPauseStart = Date.now();
    return;
  }

  if (event === "resumed") {
    setStatus(t("status_resumed"));
    if (etaPauseStart && etaPhaseStart) {
      // Shift the phase start forward by however long the pause lasted,
      // so the paused time doesn't get counted as "slow" translating.
      etaPhaseStart += Date.now() - etaPauseStart;
    }
    etaPauseStart = null;
    return;
  }

  if (event === "error") {
    setProgress(0, t("progress_error"));
    setBusy(false);
    clearEta();
    setResult(t("result_error", { message: payload.message }), "error");
    return;
  }

  if (event === "retry_start") {
    document.getElementById("retry-status").textContent = t("retry_starting", { total: payload.total });
    return;
  }

  if (event === "retry_progress") {
    document.getElementById("retry-status").textContent = t("retry_progress", payload);
    return;
  }

  if (event === "retry_done") {
    isBusy = false;
    document.getElementById("btn-retry-pending").disabled = false;
    document.getElementById("retry-status").textContent = t("retry_result", payload);
    loadPending();
    return;
  }

  if (event === "retry_error") {
    isBusy = false;
    document.getElementById("btn-retry-pending").disabled = false;
    document.getElementById("retry-status").textContent = t("retry_error_prefix", { message: payload.message });
  }
};

// ---------------- pending review ----------------

function currentLanguagePair() {
  return `${currentSettings.source_language || "en"}_${currentSettings.target_language}`;
}

async function retryPending() {
  if (isBusy) return;

  const statusEl = document.getElementById("retry-status");
  const response = await api().retry_pending(currentLanguagePair());

  if (!response.ok) {
    statusEl.textContent = response.error;
    return;
  }

  isBusy = true;
  document.getElementById("btn-retry-pending").disabled = true;
  statusEl.textContent = t("retry_starting", { total: response.count });
}

async function loadPending() {
  const list = document.getElementById("pending-list");
  list.innerHTML = `<div class="pending-empty">${t("pending_loading")}</div>`;

  const languagePair = currentLanguagePair();
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
  refreshMemoryStats();

  document.getElementById("select-ui-language").addEventListener("change", (event) => {
    changeUiLanguage(event.target.value);
  });

  document.getElementById("btn-home").addEventListener("click", () => showView("home"));
  document.getElementById("btn-settings").addEventListener("click", () => {
    showView("settings");
    toggleGoogleUsageVisibility();
  });

  document.getElementById("select-provider").addEventListener("change", toggleGoogleUsageVisibility);
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
  document.getElementById("link-merge-resourcepacks").addEventListener("click", (event) => {
    event.preventDefault();
    mergeResourcepacks();
  });
  document.getElementById("btn-search-community").addEventListener("click", searchCommunityTranslations);

  document.getElementById("btn-translate-now").addEventListener("click", translateNow);
  document.getElementById("btn-pause-resume").addEventListener("click", togglePauseResume);
  document.getElementById("btn-cancel").addEventListener("click", cancelTranslation);
  document.getElementById("btn-save-settings").addEventListener("click", saveSettingsFromForm);
  document.getElementById("btn-refresh-pending").addEventListener("click", loadPending);
  document.getElementById("btn-retry-pending").addEventListener("click", retryPending);

  showView("home");
});
