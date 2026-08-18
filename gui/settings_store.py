import json
from pathlib import Path


SETTINGS_PATH = Path("gui_settings.json")

DEFAULT_SETTINGS = {
    "ui_language": "es",
    "ai_provider": "mock",
    "api_key": "",
    "source_language": "en",
    "target_language": "es",
    "concurrency": 4,
    "content_only": True,
    "last_modpack_root": "",
    "last_output_folder": ""
}


def load_settings():
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)

    with SETTINGS_PATH.open("r", encoding="utf-8") as file:
        stored = json.load(file)

    settings = dict(DEFAULT_SETTINGS)
    settings.update(stored)
    return settings


def save_settings(settings):
    merged = load_settings()
    merged.update(settings)

    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(merged, file, ensure_ascii=False, indent=4)

    return merged
