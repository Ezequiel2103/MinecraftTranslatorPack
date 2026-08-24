import hashlib
import json
from datetime import datetime, timezone

from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


CACHE_ROOT = data_dir() / "mod_lang_cache"

# Not real mods -- the shared cross-mod glossary and the per-mod content
# classification cache live in this same folder.
_NON_MOD_CACHE_FILES = {"_item_glossary", "content_classification"}


def content_hash(data):
    """Stable hash of a mod's en_us.json content, to detect mod updates."""

    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_path(modid, language_pair="en_es"):
    return CACHE_ROOT / language_pair / f"{modid}.json"


def list_translated_mods(language_pair="en_es"):
    """
    Every mod with a cached translation for this language pair,
    independent of any specific modpack -- the mod cache is shared
    across all of them by design (see save_cached_translation), so a mod
    only needs to show up here once no matter how many modpacks use it.
    """

    directory = CACHE_ROOT / language_pair

    if not directory.is_dir():
        return []

    mods = []

    for path in sorted(directory.glob("*.json")):
        if path.stem in _NON_MOD_CACHE_FILES:
            continue

        cached = load_json_safe(path, None)

        if cached is None:
            continue

        mods.append({
            "modid": path.stem,
            "entry_count": len(cached.get("lang") or {}),
            "last_translated_at": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        })

    mods.sort(key=lambda entry: entry["last_translated_at"], reverse=True)
    return mods


def load_cached_translation(modid, source_hash, language_pair="en_es"):
    """
    Returns the cached translated lang dict for this exact mod content,
    or None if there is no cache entry or the mod's text has changed
    since it was cached (a new mod version with different strings).
    """

    cached = load_json_safe(cache_path(modid, language_pair), None)

    if cached is None or cached.get("source_hash") != source_hash:
        return None

    return cached.get("lang")


def patch_cached_translation(modid, key, translation, language_pair="en_es"):
    """
    Overwrites a single string inside an already-cached mod's translated
    lang dict, keeping the same source_hash so the cache is still a hit
    on the next run -- which is what actually gets the fix into a built
    resource pack, since translate_now() just reuses whatever this cache
    holds for a mod whose English text hasn't changed. Used to patch in
    a better translation for one text that failed validation earlier
    (see gui.api.Api.retry_pending) without redoing the whole mod.
    Returns False if this mod was never cached in the first place --
    nothing to patch.
    """

    path = cache_path(modid, language_pair)
    cached = load_json_safe(path, None)

    if cached is None:
        return False

    cached.setdefault("lang", {})[key] = translation
    write_json_atomic(path, cached, ensure_ascii=False, indent=4)
    return True


def build_text_glossary(source_dict, translated_dict):
    """
    Zips two translation-key -> text dicts (same keys, one language each)
    into an english-text -> translated-text lookup, skipping anything
    empty or left untranslated. This is deliberately smaller than the raw
    dicts it's built from: several translation keys often share identical
    display text (e.g. an item and its block sharing a name), and this
    collapses those into one entry instead of storing the text twice
    alongside a technical key ("block.mekanism.energy_cube") neither side
    actually needs once the pairing is done.
    """

    glossary = {}

    for key, source_text in source_dict.items():
        translated_text = translated_dict.get(key)
        if not source_text or not translated_text:
            continue
        if source_text == translated_text:
            continue
        glossary[source_text] = translated_text

    return glossary


def glossary_path(language_pair="en_es"):
    return CACHE_ROOT / language_pair / "_item_glossary.json"


def _load_glossary_file(language_pair):
    data = load_json_safe(glossary_path(language_pair), {})
    return data.get("pairs", {}), set(data.get("conflicts", []))


def _save_glossary_file(pairs, conflicts, language_pair):
    write_json_atomic(
        glossary_path(language_pair),
        {"pairs": pairs, "conflicts": sorted(conflicts)},
        ensure_ascii=False, indent=4
    )


def save_cached_translation(
    modid, source_hash, translated_lang, language_pair="en_es", source_lang=None
):
    payload = {
        "source_hash": source_hash,
        "lang": translated_lang
    }

    write_json_atomic(
        cache_path(modid, language_pair), payload,
        ensure_ascii=False, indent=4
    )

    if source_lang is not None:
        new_pairs = build_text_glossary(source_lang, translated_lang)
        merge_into_item_glossary(new_pairs, language_pair)


def merge_into_item_glossary(new_pairs, language_pair="en_es"):
    """
    Merges a mod's English->translated pairs into the single glossary
    file shared by every mod for this language pair — one small file
    that's cheap to read on every translation run, instead of a "glossary"
    blob duplicated inside each of the (potentially hundreds of) per-mod
    cache files.

    If two different mods disagree on the translation of the same English
    text, that text is dropped and remembered as a permanent conflict
    (recorded in "conflicts") so a later mod that happens to agree with
    one of the two candidates can't silently resurrect it — quest text
    mentioning it just falls through to a normal translation instead of
    risking the wrong mod's terminology.
    """

    pairs, conflicts = _load_glossary_file(language_pair)

    for english_text, spanish_text in new_pairs.items():
        if english_text in conflicts:
            continue

        existing = pairs.get(english_text)
        if existing is not None and existing != spanish_text:
            conflicts.add(english_text)
            pairs.pop(english_text, None)
            continue

        pairs[english_text] = spanish_text

    _save_glossary_file(pairs, conflicts, language_pair)


def build_mod_item_glossary(language_pair="en_es"):
    """
    Returns the English-text -> translated-text lookup accumulated from
    every mod translated so far for this language pair, so quest text
    that happens to mention an item/block already translated while
    translating its mod can reuse that translation instead of asking the
    AI again. See merge_into_item_glossary() for how it's built and how
    conflicting translations are handled.
    """

    pairs, _ = _load_glossary_file(language_pair)
    return dict(pairs)
