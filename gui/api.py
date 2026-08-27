import json
import os
import shutil
import sys
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_paths import data_dir
from gui.settings_store import load_settings, save_settings
from mod_lang_translator import translate_mod_lang_files
from modpack_locator import locate_modpack_paths
from review.review_manager import (
    approve_translation,
    load_pending,
    save_pending_data
)
from translation.api_usage import DEFAULT_CHARACTER_LIMIT, get_usage
from translation.concurrent_translate import translate_items_concurrently
from translation.dictionary_io import (
    export_mods_dictionary as export_mods_dictionary_file,
    export_quest_dictionary as export_quest_dictionary_file,
    import_mods_dictionary as import_mods_dictionary_file,
    import_quest_dictionary as import_quest_dictionary_file
)
from translation.community_import import import_community_resourcepack
from translation.curseforge_search import (
    CurseForgeError,
    download_translation_pack,
    search_translation_packs
)
from translation.mod_lang_cache import (
    build_mod_item_glossary,
    list_translated_mods,
    patch_cached_translation
)
from translation.protected_terms_manager import load_protected_terms
from translation.resourcepack_merger import merge_resourcepacks
from translation.translated_registry import (
    list_translated_modpacks,
    record_modpack_translation
)
from translation.translation_memory import add_translation, load_memory
from translation.translation_service import TranslationService
from translator_app import DEFAULT_LOCALES, create_ai_translator, translate_folder


PROVIDER_ENV_VAR = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "google": "GOOGLE_TRANSLATE_API_KEY"
}

AI_PROVIDERS = ["mock", "ollama", "argos", "openai", "claude", "deepseek", "google"]
UI_LANGUAGES = ["es", "en"]

PACK_ICON_PATH = Path(__file__).resolve().parent / "assets" / "pack_icon.png"
LOCALES_DIR = Path(__file__).resolve().parent / "web" / "locales"

TARGET_LANGUAGES = [
    {"code": "es", "label": "Español (ES)"},
    {"code": "pt", "label": "Português (PT)"},
    {"code": "fr", "label": "Français (FR)"},
    {"code": "de", "label": "Deutsch (DE)"},
    {"code": "it", "label": "Italiano (IT)"},
    {"code": "ru", "label": "Русский (RU)"},
    {"code": "zh", "label": "中文 (ZH)"},
    {"code": "ja", "label": "日本語 (JA)"},
    {"code": "ko", "label": "한국어 (KO)"}
]


def _apply_pending_fix(path, original_text, translation, language_pair):
    """
    Saves a successfully retried pending translation to wherever
    translate_now() will actually look for it next time: a mod's cached
    lang file for a "mods/<modid>/<key>" pending path, or the quest
    translation memory for anything else. Patching the cache in place
    (instead of clearing it) is what lets a plain re-run pick this fix
    up without redoing the whole mod.
    """

    if path and path.startswith("mods/"):
        parts = path.split("/", 2)

        if len(parts) == 3:
            _, modid, key = parts
            if patch_cached_translation(modid, key, translation, language_pair):
                return

    add_translation(original_text, translation, language_pair=language_pair)


class Api:
    def __init__(self):
        self._window = None
        self._busy = False
        self._cancel_event = None
        self._resume_event = None

    def set_window(self, window):
        self._window = window

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def close_window(self):
        if self._window:
            self._window.destroy()

    def _emit(self, event, payload):
        if not self._window:
            return

        self._window.evaluate_js(
            f"window.onBackendEvent({json.dumps(event)}, {json.dumps(payload)})"
        )

    def _throttled_progress_emitter(self, event, min_interval=0.15):
        """
        Wraps _emit for a per-item progress callback so it fires at most
        a few times a second instead of once per item. Reporting every
        item individually (needed so the bar doesn't sit still for
        minutes on a slow engine like Argos, batched or not) means
        thousands of evaluate_js calls into the window on a big modpack,
        which is exactly what made the window itself feel laggy while
        translating. The last item always gets through regardless of
        timing, so the count on screen still lands on the real total.
        """

        state = {"last": 0.0}

        def emit_progress(current, total):
            now = time.monotonic()

            if current >= total or now - state["last"] >= min_interval:
                state["last"] = now
                self._emit(event, {"current": current, "total": total})

        return emit_progress

    # --- settings -----------------------------------------------------

    def get_settings(self):
        settings = load_settings()
        return {
            "settings": settings,
            "providers": AI_PROVIDERS,
            "languages": TARGET_LANGUAGES
        }

    def save_settings(self, settings):
        return save_settings(settings)

    def get_memory_stats(self):
        settings = load_settings()
        language_pair = f"{settings['source_language']}_{settings['target_language']}"
        return {
            "quest_count": len(load_memory(language_pair)),
            "glossary_count": len(build_mod_item_glossary(language_pair))
        }

    def get_translated_modpacks(self):
        settings = load_settings()
        language_pair = f"{settings['source_language']}_{settings['target_language']}"
        return list_translated_modpacks(language_pair)

    def get_translated_mods(self):
        settings = load_settings()
        language_pair = f"{settings['source_language']}_{settings['target_language']}"
        return list_translated_mods(language_pair)

    def get_google_usage(self):
        usage = get_usage()
        used = usage["characters_used"]
        return {
            "month": usage["month"],
            "used": used,
            "limit": DEFAULT_CHARACTER_LIMIT,
            "percent": min(100, round(used / DEFAULT_CHARACTER_LIMIT * 100, 1))
        }

    def get_locale(self, lang_code):
        if lang_code not in UI_LANGUAGES:
            lang_code = "es"

        path = LOCALES_DIR / f"{lang_code}.json"

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    # --- file / folder pickers -------------------------------------------

    def pick_folder(self):
        if not self._window:
            return None

        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    def pick_image_file(self):
        if not self._window:
            return None

        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            file_types=("Imágenes (*.png;*.jpg;*.jpeg)",)
        )
        return result[0] if result else None

    def pick_open_file(self, file_types):
        if not self._window:
            return None

        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            file_types=tuple(file_types)
        )
        return result[0] if result else None

    def pick_save_file(self, default_name, file_types):
        if not self._window:
            return None

        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=default_name,
            file_types=tuple(file_types)
        )
        return result[0] if result else None

    def pick_open_files_multiple(self, file_types):
        if not self._window:
            return []

        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=tuple(file_types)
        )
        return list(result) if result else []

    # --- resource pack merging ---------------------------------------------

    def merge_resourcepacks_now(self, source_paths, output_folder):
        try:
            result = merge_resourcepacks(
                source_paths, output_folder,
                pack_icon=PACK_ICON_PATH if PACK_ICON_PATH.exists() else None
            )
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            return {"ok": False, "error": str(error)}

        return {"ok": True, **result}

    # --- community translation search (CurseForge) --------------------------

    def search_community_translations(self, modpack_root):
        settings = load_settings()
        api_key = settings.get("curseforge_api_key")

        if not api_key:
            return {"ok": False, "error": "curseforge_key_missing"}

        modpack_name = Path(modpack_root).name

        try:
            results = search_translation_packs(modpack_name, api_key)
        except CurseForgeError as error:
            return {"ok": False, "error": str(error)}

        return {"ok": True, "results": results, "query": modpack_name}

    def import_community_translation(self, download_url, file_name, modpack_root):
        paths = locate_modpack_paths(modpack_root)

        if not paths["mods_folder"]:
            return {
                "ok": False,
                "error": "No encontré una carpeta de mods en ese modpack."
            }

        settings = load_settings()
        language_pair = f"{settings['source_language']}_{settings['target_language']}"
        target_locale = DEFAULT_LOCALES.get(
            settings["target_language"].lower(), settings["target_language"].lower()
        )

        destination = (
            data_dir() / "community_downloads" / (file_name or "community_pack.zip")
        )

        try:
            download_translation_pack(download_url, destination)
            result = import_community_resourcepack(
                destination, paths["mods_folder"],
                language_pair=language_pair, target_locale=target_locale
            )
        except (CurseForgeError, OSError, ValueError, zipfile.BadZipFile) as error:
            return {"ok": False, "error": str(error)}

        return {"ok": True, **result}

    # --- modpack discovery ------------------------------------------------

    def scan_modpack(self, modpack_root):
        return locate_modpack_paths(modpack_root)

    # --- dictionaries (import = load a shared file, export = share yours) --

    def import_quest_dictionary(self, file_path):
        settings = load_settings()
        pair = f"{settings['source_language']}_{settings['target_language']}"

        try:
            result = import_quest_dictionary_file(file_path, pair)
        except (OSError, json.JSONDecodeError) as error:
            return {"ok": False, "error": f"No se pudo leer el diccionario: {error}"}

        return {"ok": True, **result}

    def import_mods_dictionary(self, file_path):
        settings = load_settings()
        pair = f"{settings['source_language']}_{settings['target_language']}"

        try:
            result = import_mods_dictionary_file(file_path, pair)
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
            return {"ok": False, "error": f"No se pudo leer el diccionario: {error}"}

        return {"ok": True, **result}

    def export_quest_dictionary(self, save_path):
        settings = load_settings()
        pair = f"{settings['source_language']}_{settings['target_language']}"
        path = export_quest_dictionary_file(save_path, pair)
        return {"ok": True, "path": path}

    def export_mods_dictionary(self, save_path):
        settings = load_settings()
        pair = f"{settings['source_language']}_{settings['target_language']}"
        path = export_mods_dictionary_file(save_path, pair)
        return {"ok": True, "path": path}

    # --- translation (the actual AI-backed run) ---------------------------

    def translate_now(self, modpack_root, translate_quests=True, translate_mods=True):
        if self._busy:
            return {"ok": False, "error": "Ya hay una traducción en curso."}

        if not translate_quests and not translate_mods:
            return {
                "ok": False,
                "error": "Elegí al menos una cosa para traducir (misiones o mods)."
            }

        paths = locate_modpack_paths(modpack_root)

        if not paths["quests_lang_folder"] and not paths["mods_folder"]:
            return {
                "ok": False,
                "error": (
                    "No encontré ni misiones ni una carpeta 'mods' dentro "
                    "de esa ruta."
                )
            }

        self._cancel_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()

        thread = threading.Thread(
            target=self._run_translate_now,
            args=(paths, modpack_root, translate_quests, translate_mods),
            daemon=True
        )
        thread.start()
        return {"ok": True}

    def pause_translation(self):
        if self._resume_event:
            self._resume_event.clear()
            self._emit("paused", {})

    def resume_translation(self):
        if self._resume_event:
            self._resume_event.set()
            self._emit("resumed", {})

    def cancel_translation(self):
        if self._cancel_event:
            self._cancel_event.set()

        # A cancel while paused would otherwise block forever on
        # resume_event.wait() and never see the cancellation.
        if self._resume_event:
            self._resume_event.set()

    def _run_translate_now(self, paths, modpack_root, translate_quests, translate_mods):
        self._busy = True
        settings = load_settings()
        self._apply_api_key(settings)
        modpack_root = Path(modpack_root)
        cancel_event = self._cancel_event
        resume_event = self._resume_event

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = modpack_root / "_translator_backups" / timestamp
        backed_up = False

        summary = {"files": 0, "mods": 0, "pending": 0, "total_items": 0}
        quota_exceeded = False

        try:
            self._emit("start", {"phase": "modpack"})

            if paths["quests_lang_folder"] and translate_quests:
                def on_file_progress(current, total, name):
                    self._emit("file_progress", {
                        "current": current, "total": total, "name": name
                    })

                on_text_progress = self._throttled_progress_emitter("text_progress")

                quests_lang_folder = paths["quests_lang_folder"]

                reports = translate_folder(
                    quests_lang_folder,
                    # Write straight into the modpack's own quests/lang
                    # folder -- output_folder == input_folder -- instead
                    # of a separate copy the user would have to merge in
                    # by hand. Anything this overwrites is backed up
                    # first (see backup_dir below).
                    quests_lang_folder,
                    source_language=settings["source_language"],
                    target_language=settings["target_language"],
                    ai_provider=settings["ai_provider"],
                    mods_folder=paths["mods_folder"],
                    concurrency=settings["concurrency"],
                    on_file_progress=on_file_progress,
                    on_text_progress=on_text_progress,
                    cancel_event=cancel_event,
                    resume_event=resume_event,
                    backup_dir=backup_dir
                )
                summary["files"] = len(reports)
                summary["pending"] += sum(
                    len(report["pending_items"]) for report in reports
                )
                summary["total_items"] += sum(
                    len(report["translatable_texts"]) for report in reports
                )
                quota_exceeded = quota_exceeded or any(
                    report.get("quota_exceeded") for report in reports
                )
                backed_up = backed_up or any(
                    report.get("backed_up_to") for report in reports
                )

            if paths["mods_folder"] and translate_mods and not cancel_event.is_set():
                self._emit("start", {"phase": "mods"})

                def on_mod_progress(current, total, modid):
                    self._emit("mod_progress", {
                        "current": current, "total": total, "modid": modid
                    })

                on_text_progress_mods = self._throttled_progress_emitter("text_progress")

                target_locale = DEFAULT_LOCALES.get(
                    settings["target_language"].lower(),
                    settings["target_language"].lower()
                )
                resourcepack_dir = (
                    modpack_root / "resourcepacks"
                    / f"Traduccion_Mods_{target_locale}"
                )

                # This folder is a build artifact of a previous run, not
                # something the player hand-edits -- back the whole thing
                # up and regenerate it fresh rather than overlaying, so a
                # mod that got removed from the pack doesn't leave a
                # stale translated entry behind.
                if resourcepack_dir.exists():
                    moved_to = backup_dir / "resourcepacks" / resourcepack_dir.name
                    moved_to.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(resourcepack_dir), str(moved_to))
                    backed_up = True

                stats = translate_mod_lang_files(
                    paths["mods_folder"],
                    resourcepack_dir,
                    source_language=settings["source_language"],
                    target_language=settings["target_language"],
                    ai_provider=settings["ai_provider"],
                    concurrency=settings["concurrency"],
                    content_only=True,
                    pack_icon=PACK_ICON_PATH if PACK_ICON_PATH.exists() else None,
                    on_mod_progress=on_mod_progress,
                    on_text_progress=on_text_progress_mods,
                    cancel_event=cancel_event,
                    resume_event=resume_event
                )
                summary["mods"] = len(stats["mods"])
                summary["pending"] += stats["pending_items"]
                summary["total_items"] += stats["total_items"]
                quota_exceeded = quota_exceeded or stats.get("quota_exceeded", False)

            translated_items = summary["total_items"] - summary["pending"]
            percent_translated = (
                round(translated_items / summary["total_items"] * 100)
                if summary["total_items"] else 100
            )

            payload = {
                "files": summary["files"],
                "mods": summary["mods"],
                "pending": summary["pending"],
                "total_items": summary["total_items"],
                "percent_translated": percent_translated,
                "percent_pending": 100 - percent_translated,
                "modpack_root": str(modpack_root),
                "backup_dir": str(backup_dir) if backed_up else None
            }

            language_pair = f"{settings['source_language']}_{settings['target_language']}"
            record_modpack_translation(modpack_root, language_pair, summary)

            if quota_exceeded:
                usage = get_usage()
                self._emit("quota_exceeded", {
                    **payload,
                    "used": usage["characters_used"],
                    "limit": DEFAULT_CHARACTER_LIMIT
                })
            else:
                done_event = "cancelled" if cancel_event.is_set() else "done"
                self._emit(done_event, payload)

        except Exception as error:
            self._emit("error", {"message": str(error)})

        finally:
            self._busy = False

    def _apply_api_key(self, settings):
        self._apply_provider_api_key(settings["ai_provider"], settings.get("api_key"))

    def _apply_provider_api_key(self, provider, api_key):
        env_var = PROVIDER_ENV_VAR.get(provider)

        if env_var and api_key:
            os.environ[env_var] = api_key

    # --- pending review --------------------------------------------------

    def get_pending(self, language_pair):
        pending = load_pending(language_pair)
        return [
            {"original": original, **data}
            for original, data in pending.items()
        ]

    def approve_pending(self, original, translation, language_pair):
        return approve_translation(original, translation, language_pair)

    def retry_pending(self, language_pair):
        if self._busy:
            return {"ok": False, "error": "Ya hay una traducción en curso."}

        pending = load_pending(language_pair)

        if not pending:
            return {"ok": False, "error": "No hay nada pendiente para reintentar."}

        self._cancel_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()

        thread = threading.Thread(
            target=self._run_retry_pending,
            args=(language_pair,),
            daemon=True
        )
        thread.start()
        return {"ok": True, "count": len(pending)}

    def _run_retry_pending(self, language_pair):
        self._busy = True
        settings = load_settings()
        self._apply_api_key(settings)
        cancel_event = self._cancel_event
        resume_event = self._resume_event

        try:
            pending = load_pending(language_pair)
            items = [
                {"text": original, "path": entry.get("path"), "parent_path": None}
                for original, entry in pending.items()
            ]

            service = TranslationService(
                language_pair,
                ai_translator=create_ai_translator(settings["ai_provider"], None),
                protected_terms=load_protected_terms(language_pair),
                mod_item_glossary=build_mod_item_glossary(language_pair),
                cancel_event=cancel_event
            )

            self._emit("retry_start", {"total": len(items)})

            on_progress = self._throttled_progress_emitter("retry_progress")

            results = translate_items_concurrently(
                items, service,
                source_language=settings["source_language"],
                target_language=settings["target_language"],
                concurrency=settings["concurrency"],
                on_progress=on_progress,
                cancel_event=cancel_event,
                resume_event=resume_event
            )
            service.save_new_translations()

            fixed = 0

            for item, result in zip(items, results):
                if result["translation"] and result["valid"]:
                    _apply_pending_fix(
                        item["path"], item["text"], result["translation"],
                        language_pair
                    )
                    del pending[item["text"]]
                    fixed += 1

            save_pending_data(pending, language_pair)

            self._emit("retry_done", {
                "retried": len(items),
                "fixed": fixed,
                "still_pending": len(pending)
            })

        except Exception as error:
            self._emit("retry_error", {"message": str(error)})

        finally:
            self._busy = False
