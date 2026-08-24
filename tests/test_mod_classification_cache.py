import shutil
from pathlib import Path

from translation.mod_classification_cache import (
    load_classification,
    save_classification
)


LANGUAGE_PAIR = "en_es_classtest"


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR

    try:
        assert load_classification(LANGUAGE_PAIR) == {}

        save_classification(
            {"create": True, "sodium": False}, LANGUAGE_PAIR
        )

        loaded = load_classification(LANGUAGE_PAIR)
        assert loaded == {"create": True, "sodium": False}

        # Hand-editing the file (simulated here as a direct save) must be
        # able to override a mod's classification.
        loaded["sodium"] = True
        save_classification(loaded, LANGUAGE_PAIR)
        assert load_classification(LANGUAGE_PAIR)["sodium"] is True

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

    print("Mod classification cache OK")


if __name__ == "__main__":
    main()
