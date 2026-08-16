import shutil
from pathlib import Path

from translation.mod_lang_cache import (
    content_hash,
    load_cached_translation,
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

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

    print("Mod lang cache OK")


if __name__ == "__main__":
    main()
