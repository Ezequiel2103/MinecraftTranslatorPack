import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from translation.dictionary_io import (
    export_mods_dictionary,
    export_quest_dictionary,
    import_mods_dictionary,
    import_quest_dictionary
)
from translation.translation_memory import add_translation, load_memory


LANGUAGE_PAIR = "en_es_dicttest"
OTHER_PAIR = "en_es_dicttest_other"


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR
    other_memory_dir = Path("translation") / OTHER_PAIR
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR
    other_cache_dir = Path("mod_lang_cache") / OTHER_PAIR

    try:
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # --- quest dictionary export/import ---
            add_translation("Diamond", "Diamante", language_pair=LANGUAGE_PAIR)
            add_translation("Iron", "Hierro", language_pair=LANGUAGE_PAIR)

            quest_file = tmp / "quests.json"
            export_quest_dictionary(quest_file, LANGUAGE_PAIR)
            assert quest_file.exists()

            # Another user already has their own local translation for
            # "Diamond" that must survive the import untouched.
            add_translation("Diamond", "Diamante Local", language_pair=OTHER_PAIR)

            result = import_quest_dictionary(quest_file, OTHER_PAIR)
            assert result["added"] == 1  # only "Iron" was new

            merged = load_memory(OTHER_PAIR)
            assert merged["Diamond"]["translation"] == "Diamante Local"
            assert merged["Iron"]["translation"] == "Hierro"

            # --- mods dictionary export/import ---
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "create.json").write_text(
                json.dumps({"source_hash": "abc", "lang": {"item.create.wrench": "Llave"}}),
                encoding="utf-8"
            )
            (cache_dir / "content_classification.json").write_text(
                json.dumps({"create": True, "sodium": False}),
                encoding="utf-8"
            )

            mods_file = tmp / "mods.zip"
            export_mods_dictionary(mods_file, LANGUAGE_PAIR)
            assert mods_file.exists()

            other_cache_dir.mkdir(parents=True, exist_ok=True)
            (other_cache_dir / "content_classification.json").write_text(
                json.dumps({"sodium": True}),  # deliberately conflicting
                encoding="utf-8"
            )

            mods_result = import_mods_dictionary(mods_file, OTHER_PAIR)
            assert mods_result["added_mods"] == 1
            assert mods_result["added_classifications"] == 1  # only "create" was new

            assert (other_cache_dir / "create.json").exists()
            classification = json.loads(
                (other_cache_dir / "content_classification.json").read_text(encoding="utf-8")
            )
            assert classification["sodium"] is True  # local value preserved
            assert classification["create"] is True  # imported value added

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)
        shutil.rmtree(other_memory_dir, ignore_errors=True)
        shutil.rmtree(cache_dir, ignore_errors=True)
        shutil.rmtree(other_cache_dir, ignore_errors=True)

    print("Dictionary import/export OK")


if __name__ == "__main__":
    main()
