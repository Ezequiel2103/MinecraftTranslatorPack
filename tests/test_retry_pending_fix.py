import shutil
from pathlib import Path

from gui.api import _apply_pending_fix
from translation.mod_lang_cache import cache_path, save_cached_translation
from translation.translation_memory import load_memory, memory_path


LANGUAGE_PAIR = "en_es_retryfixtest"


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR

    try:
        # A retried mod text patches that mod's own cache entry, not the
        # quest memory -- this is what lets a plain re-run pick it up
        # without redoing the whole mod.
        save_cached_translation(
            "testmod", "somehash", {"item.testmod.thing": "Thing"}, LANGUAGE_PAIR
        )

        _apply_pending_fix(
            "mods/testmod/item.testmod.thing", "Thing", "Cosa", LANGUAGE_PAIR
        )

        assert cache_path("testmod", LANGUAGE_PAIR).exists()
        import json
        cached = json.loads(cache_path("testmod", LANGUAGE_PAIR).read_text(encoding="utf-8"))
        assert cached["lang"]["item.testmod.thing"] == "Cosa", cached
        # A mod-path fix must not also pollute the quest memory.
        assert "Thing" not in load_memory(LANGUAGE_PAIR)

        # A quest-path (or any non-"mods/" path) fix goes to the shared
        # translation memory instead.
        _apply_pending_fix(
            "quest.ABC123.title", "Craft your first machine", "Fabrica tu primera máquina",
            LANGUAGE_PAIR
        )

        memory = load_memory(LANGUAGE_PAIR)
        assert memory["Craft your first machine"]["translation"] == "Fabrica tu primera máquina"

        # A "mods/" path for a mod that was never cached falls back to
        # the shared memory too, instead of silently losing the fix.
        _apply_pending_fix(
            "mods/nevercached/item.nevercached.thing", "Something", "Algo",
            LANGUAGE_PAIR
        )
        memory = load_memory(LANGUAGE_PAIR)
        assert memory["Something"]["translation"] == "Algo"

        print("Retry pending fix OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)
        shutil.rmtree(cache_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
