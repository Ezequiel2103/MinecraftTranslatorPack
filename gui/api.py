import json
import os
import sys
import threading
import zipfile
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gui.settings_store import load_settings, save_settings
from mod_lang_translator import translate_mod_lang_files
from modpack_locator import locate_modpack_paths
from review.review_manager import approve_translation, load_pending
from translation.dictionary_io import (
    export_mods_dictionary as export_mods_dictionary_file,
    export_quest_dictionary as export_quest_dictionary_file,
    import_mods_dictionary as import_mods_dictionary_file,
    import_quest_dictionary as import_quest_dictionary_file
)
from translator_app import translate_folder


PROVIDER_ENV_VAR = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY"
}

AI_PROVIDERS = ["mock", "ollama", "openai", "claude", "deepseek"]

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


class Api:
    def __init__(self):
        self._window = None
        self._busy = False

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

    def translate_now(self, modpack_root, output_folder, pack_icon):
        if self._busy:
            return {"ok": False, "error": "Ya hay una traducción en curso."}

        paths = locate_modpack_paths(modpack_root)

        if not paths["quests_lang_folder"] and not paths["mods_folder"]:
            return {
                "ok": False,
                "error": (
                    "No encontré ni misiones ni una carpeta 'mods' dentro "
                    "de esa ruta."
                )
            }

        thread = threading.Thread(
            target=self._run_translate_now,
            args=(paths, output_folder, pack_icon),
            daemon=True
        )
        thread.start()
        return {"ok": True}

    def _run_translate_now(self, paths, output_folder, pack_icon):
        self._busy = True
        settings = load_settings()
        self._apply_api_key(settings)
        output_folder = Path(output_folder)

        summary = {"files": 0, "mods": 0, "pending": 0}

        try:
            self._emit("start", {"phase": "modpack"})

            if paths["quests_lang_folder"]:
                def on_file_progress(current, total, name):
                    self._emit("file_progress", {
                        "current": current, "total": total, "name": name
                    })

                def on_text_progress(current, total):
                    self._emit("text_progress", {
                        "current": current, "total": total
                    })

                reports = translate_folder(
                    paths["quests_lang_folder"],
                    output_folder / "modpack",
                    source_language=settings["source_language"],
                    target_language=settings["target_language"],
                    ai_provider=settings["ai_provider"],
                    mods_folder=paths["mods_folder"],
                    concurrency=settings["concurrency"],
                    on_file_progress=on_file_progress,
                    on_text_progress=on_text_progress
                )
                summary["files"] = len(reports)
                summary["pending"] += sum(
                    len(report["pending_items"]) for report in reports
                )

            if paths["mods_folder"]:
                self._emit("start", {"phase": "mods"})

                def on_mod_progress(current, total, modid):
                    self._emit("mod_progress", {
                        "current": current, "total": total, "modid": modid
                    })

                def on_text_progress_mods(current, total):
                    self._emit("text_progress", {
                        "current": current, "total": total
                    })

                stats = translate_mod_lang_files(
                    paths["mods_folder"],
                    output_folder / "mods_resourcepack",
                    source_language=settings["source_language"],
                    target_language=settings["target_language"],
                    ai_provider=settings["ai_provider"],
                    concurrency=settings["concurrency"],
                    content_only=settings["content_only"],
                    pack_icon=pack_icon or None,
                    on_mod_progress=on_mod_progress,
                    on_text_progress=on_text_progress_mods
                )
                summary["mods"] = len(stats["mods"])
                summary["pending"] += stats["pending_items"]

            self._emit("done", {
                "files": summary["files"],
                "mods": summary["mods"],
                "pending": summary["pending"],
                "output_folder": str(output_folder)
            })

        except Exception as error:
            self._emit("error", {"message": str(error)})

        finally:
            self._busy = False

    def _apply_api_key(self, settings):
        env_var = PROVIDER_ENV_VAR.get(settings["ai_provider"])

        if env_var and settings.get("api_key"):
            os.environ[env_var] = settings["api_key"]

    # --- pending review --------------------------------------------------

    def get_pending(self, language_pair):
        pending = load_pending(language_pair)
        return [
            {"original": original, **data}
            for original, data in pending.items()
        ]

    def approve_pending(self, original, translation, language_pair):
        return approve_translation(original, translation, language_pair)
