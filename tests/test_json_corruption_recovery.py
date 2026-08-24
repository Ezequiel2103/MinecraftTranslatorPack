import shutil
from pathlib import Path

from json_io import load_json_safe, write_json_atomic
from translation.mod_lang_cache import (
    build_mod_item_glossary,
    cache_path,
    content_hash,
    glossary_path,
    load_cached_translation,
    save_cached_translation
)
from translation.translation_memory import load_memory, memory_path


LANGUAGE_PAIR = "en_es_corruptiontest"


def _corrupt(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # A truncated/empty file is exactly what's left behind by a process
    # killed mid-write (force-closing the app instead of Cancel) --
    # the real failure mode this is guarding against.
    path.write_text("", encoding="utf-8")


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR

    try:
        # 1. load_json_safe: a corrupt file returns the default instead
        # of raising, and a real file still parses normally.
        write_json_atomic(memory_path(LANGUAGE_PAIR), {"a": 1}, ensure_ascii=False)
        assert load_json_safe(memory_path(LANGUAGE_PAIR), None) == {"a": 1}

        _corrupt(memory_path(LANGUAGE_PAIR))
        assert load_json_safe(memory_path(LANGUAGE_PAIR), "fallback") == "fallback"

        # 2. Translation memory: a corrupt memory.json (e.g. from an
        # earlier interrupted run) must not crash every future call --
        # it degrades to "empty memory", same as if the file never
        # existed, not a hard failure that blocks the whole app.
        _corrupt(memory_path(LANGUAGE_PAIR))
        assert load_memory(LANGUAGE_PAIR) == {}

        # 3. Mod cache: a corrupt per-mod cache file must be treated as
        # "not cached" (forcing a fresh translation for that one mod)
        # instead of crashing the entire mods-translation run -- this is
        # the exact scenario that broke a real run.
        source = {"item.testmod.thing": "Thing"}
        source_hash = content_hash(source)
        save_cached_translation(
            "testmod", source_hash, {"item.testmod.thing": "Cosa"}, LANGUAGE_PAIR
        )
        assert load_cached_translation("testmod", source_hash, LANGUAGE_PAIR) == {
            "item.testmod.thing": "Cosa"
        }

        _corrupt(cache_path("testmod", LANGUAGE_PAIR))
        assert load_cached_translation("testmod", source_hash, LANGUAGE_PAIR) is None

        # 4. The shared item glossary: same tolerance, and
        # build_mod_item_glossary (used on every translation run) must
        # not crash either.
        _corrupt(glossary_path(LANGUAGE_PAIR))
        assert build_mod_item_glossary(LANGUAGE_PAIR) == {}

        print("JSON corruption recovery OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)
        shutil.rmtree(cache_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
