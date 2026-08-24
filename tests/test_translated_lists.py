import shutil
from pathlib import Path

from translation.mod_lang_cache import list_translated_mods, save_cached_translation
from translation.translated_registry import (
    list_translated_modpacks,
    record_modpack_translation
)


LANGUAGE_PAIR = "en_es_listtest"


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR
    registry_path = Path("translated_modpacks.json")

    try:
        # 1. list_translated_mods: empty when nothing cached yet.
        assert list_translated_mods(LANGUAGE_PAIR) == []

        save_cached_translation(
            "testmod", "hash1",
            {"item.testmod.a": "Cosa A", "item.testmod.b": "Cosa B"},
            LANGUAGE_PAIR
        )
        save_cached_translation(
            "othermod", "hash2", {"item.othermod.a": "Otra Cosa"}, LANGUAGE_PAIR
        )

        mods = list_translated_mods(LANGUAGE_PAIR)
        by_id = {entry["modid"]: entry for entry in mods}

        assert set(by_id) == {"testmod", "othermod"}, mods
        assert by_id["testmod"]["entry_count"] == 2
        assert by_id["othermod"]["entry_count"] == 1
        assert all("last_translated_at" in entry for entry in mods)

        # The shared glossary/classification files living in the same
        # folder must never show up as if they were mods.
        assert "_item_glossary" not in by_id
        assert "content_classification" not in by_id

        # 2. record_modpack_translation / list_translated_modpacks:
        # translating the same modpack twice updates one entry, not two.
        assert list_translated_modpacks(LANGUAGE_PAIR) == []

        record_modpack_translation(
            "C:/Fake/MyModpack", LANGUAGE_PAIR,
            {"files": 1, "mods": 10, "pending": 3}
        )
        record_modpack_translation(
            "C:/Fake/OtherPack", LANGUAGE_PAIR,
            {"files": 2, "mods": 5, "pending": 0}
        )

        packs = list_translated_modpacks(LANGUAGE_PAIR)
        assert len(packs) == 2, packs
        assert {entry["name"] for entry in packs} == {"MyModpack", "OtherPack"}

        record_modpack_translation(
            "C:/Fake/MyModpack", LANGUAGE_PAIR,
            {"files": 1, "mods": 12, "pending": 0}
        )
        packs = list_translated_modpacks(LANGUAGE_PAIR)
        assert len(packs) == 2, "re-translating must update, not duplicate"

        updated = next(entry for entry in packs if entry["name"] == "MyModpack")
        assert updated["mods"] == 12
        assert updated["pending"] == 0

        # A different language pair's registry is kept separate.
        assert list_translated_modpacks("en_es_listtest_other") == []

        print("Translated lists OK")

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)
        registry_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
