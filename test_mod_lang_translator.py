import json
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from mod_lang_translator import translate_mod_lang_files
from translation.mod_classification_cache import (
    load_classification,
    save_classification
)


LANGUAGE_PAIR = "en_estest"


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR
    protected_terms_dir = Path("translation") / LANGUAGE_PAIR
    review_dir = Path("review") / LANGUAGE_PAIR

    try:
        with TemporaryDirectory() as tmp:
            mods_folder = Path(tmp) / "mods"
            mods_folder.mkdir()
            output = Path(tmp) / "resourcepack"

            with zipfile.ZipFile(mods_folder / "moda.jar", "w") as archive:
                archive.writestr(
                    "assets/moda/lang/en_us.json",
                    json.dumps({"item.moda.thing": "Thing"})
                )

            with zipfile.ZipFile(mods_folder / "modb.jar", "w") as archive:
                archive.writestr(
                    "assets/modb/lang/en_us.json",
                    json.dumps({"item.modb.thing": "Other"})
                )
                archive.writestr(
                    "assets/modb/lang/es_es.json",
                    json.dumps({"item.modb.thing": "Otro"})
                )

            first = translate_mod_lang_files(
                mods_folder,
                output,
                source_language="en",
                target_language="estest",
                ai_provider="mock"
            )

            assert first["already_translated_by_mod"] == 1
            assert first["translated_fresh"] == 1
            assert first["reused_from_cache"] == 0
            assert first["mods"] == ["moda"]
            # mock's "[AI] ..." output fails the quality check, so the
            # failure must be recorded instead of silently discarded.
            assert first["pending_items"] == 1
            pending = json.loads(
                Path("review/en_estest/pending.json").read_text(
                    encoding="utf-8"
                )
            )
            assert "Thing" in pending
            assert pending["Thing"]["path"] == "mods/moda/item.moda.thing"

            moda_lang_path = output / "assets" / "moda" / "lang" / "es_es.json"
            assert moda_lang_path.exists()
            moda_lang = json.loads(moda_lang_path.read_text(encoding="utf-8"))
            assert "item.moda.thing" in moda_lang

            assert not (output / "assets" / "modb").exists()
            assert (output / "pack.mcmeta").exists()
            assert cache_dir.joinpath("moda.json").exists()

            second = translate_mod_lang_files(
                mods_folder,
                output,
                source_language="en",
                target_language="estest",
                ai_provider="mock"
            )

            assert second["translated_fresh"] == 0
            assert second["reused_from_cache"] == 1

            icon_source = Path(tmp) / "icon.png"
            icon_source.write_bytes(b"fake png bytes")

            translate_mod_lang_files(
                mods_folder,
                output,
                source_language="en",
                target_language="estest",
                ai_provider="mock",
                pack_icon=icon_source
            )

            assert (output / "pack.png").read_bytes() == b"fake png bytes"

            with zipfile.ZipFile(mods_folder / "modc.jar", "w") as archive:
                archive.writestr(
                    "assets/modc/lang/en_us.json",
                    json.dumps({"option.modc.setting": "Some setting"})
                )

            filtered = translate_mod_lang_files(
                mods_folder,
                output,
                source_language="en",
                target_language="estest",
                ai_provider="mock",
                content_only=True
            )

            assert filtered["skipped_config_only"] == 1
            assert "modc" not in filtered["mods"]

            classification = load_classification(LANGUAGE_PAIR)
            assert classification["modc"] is False
            assert classification["moda"] is True

            # Hand-editing the classification must override the
            # heuristic on the next run instead of being re-derived.
            classification["modc"] = True
            save_classification(classification, LANGUAGE_PAIR)

            overridden = translate_mod_lang_files(
                mods_folder,
                output,
                source_language="en",
                target_language="estest",
                ai_provider="mock",
                content_only=True
            )

            assert overridden["skipped_config_only"] == 0
            assert "modc" in overridden["mods"]

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)
        shutil.rmtree(protected_terms_dir, ignore_errors=True)
        shutil.rmtree(review_dir, ignore_errors=True)

    print("Mod lang translator OK")


if __name__ == "__main__":
    main()
