from datetime import datetime, timezone
from pathlib import Path

from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


REGISTRY_PATH = data_dir() / "translated_modpacks.json"


def record_modpack_translation(modpack_root, language_pair, stats):
    """
    Remembers that this modpack was translated (or at least attempted),
    so the "modpacks traducidos" list can show it without the app having
    to guess from anything else. Keyed by the modpack's resolved path,
    so translating the same modpack again updates the same entry instead
    of piling up duplicates.
    """

    registry = load_json_safe(REGISTRY_PATH, {})
    pair_registry = registry.setdefault(language_pair, {})
    key = str(Path(modpack_root).resolve())

    pair_registry[key] = {
        "name": Path(modpack_root).name,
        "path": key,
        "last_translated_at": datetime.now(timezone.utc).isoformat(),
        "files": stats.get("files", 0),
        "mods": stats.get("mods", 0),
        "pending": stats.get("pending", 0)
    }

    write_json_atomic(REGISTRY_PATH, registry, ensure_ascii=False, indent=4)


def list_translated_modpacks(language_pair):
    registry = load_json_safe(REGISTRY_PATH, {})
    entries = list(registry.get(language_pair, {}).values())
    entries.sort(key=lambda entry: entry.get("last_translated_at", ""), reverse=True)
    return entries
