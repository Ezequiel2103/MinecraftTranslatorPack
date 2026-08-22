import shutil
from pathlib import Path

from translation.mod_lang_cache import (
    content_hash,
    load_cached_translation,
    patch_cached_translation,
    save_cached_translation
)


LANGUAGE_PAIR = "en_es_cachetest"


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR

    try:
        source_v1 = {"item.testmod.thing": "Thing"}
        hash_v1 = content_hash(source_v1)

        assert load_cached_translation("testmod", hash_v1, LANGUAGE_PAIR) is None

        save_cached_translation(
            "testmod", hash_v1, {"item.testmod.thing": "Cosa"}, LANGUAGE_PAIR
        )

        cached = load_cached_translation("testmod", hash_v1, LANGUAGE_PAIR)
        assert cached == {"item.testmod.thing": "Cosa"}

        # A mod update with different text must invalidate the cache.
        source_v2 = {"item.testmod.thing": "Thing", "item.testmod.new": "New"}
        hash_v2 = content_hash(source_v2)
        assert hash_v2 != hash_v1
        assert load_cached_translation("testmod", hash_v2, LANGUAGE_PAIR) is None

        # patch_cached_translation: fixes one string in an already-cached
        # mod (the "retry a pending item with a different AI" path) while
        # keeping the same source_hash, so the next real run still treats
        # this mod as cached and picks up the fix.
        assert patch_cached_translation(
            "testmod", "item.testmod.thing", "Cosa Mejorada", LANGUAGE_PAIR
        ) is True
        assert load_cached_translation("testmod", hash_v1, LANGUAGE_PAIR) == {
            "item.testmod.thing": "Cosa Mejorada"
        }

        # A mod that was never cached has nothing to patch -- reported
        # back instead of silently creating a bogus cache entry.
        assert patch_cached_translation(
            "nevercached", "item.nevercached.thing", "Algo", LANGUAGE_PAIR
        ) is False

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

    print("Mod lang cache OK")


if __name__ == "__main__":
    main()
