import hashlib
import json
from pathlib import Path


CACHE_ROOT = Path("mod_lang_cache")


def content_hash(data):
    """Stable hash of a mod's en_us.json content, to detect mod updates."""

    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_path(modid, language_pair="en_es"):
    return CACHE_ROOT / language_pair / f"{modid}.json"


def load_cached_translation(modid, source_hash, language_pair="en_es"):
    """
    Returns the cached translated lang dict for this exact mod content,
    or None if there is no cache entry or the mod's text has changed
    since it was cached (a new mod version with different strings).
    """

    path = cache_path(modid, language_pair)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        cached = json.load(file)

    if cached.get("source_hash") != source_hash:
        return None

    return cached.get("lang")


def save_cached_translation(modid, source_hash, translated_lang, language_pair="en_es"):
    path = cache_path(modid, language_pair)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "source_hash": source_hash,
                "lang": translated_lang
            },
            file,
            ensure_ascii=False,
            indent=4
        )
