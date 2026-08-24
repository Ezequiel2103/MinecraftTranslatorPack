from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


SETTINGS_PATH = data_dir() / "gui_settings.json"

DEFAULT_SETTINGS = {
    "ui_language": "es",
    "ui_theme": "emerald",
    "ai_provider": "mock",
    "api_key": "",
    "source_language": "en",
    "target_language": "es",
    "concurrency": 4,
    "curseforge_api_key": "",
    "last_modpack_root": ""
}


def load_settings():
    stored = load_json_safe(SETTINGS_PATH, {})
    settings = dict(DEFAULT_SETTINGS)
    settings.update(stored)
    return settings


def save_settings(settings):
    merged = load_settings()
    merged.update(settings)

    write_json_atomic(SETTINGS_PATH, merged, ensure_ascii=False, indent=4)

    return merged
