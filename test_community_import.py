import json
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from translation.community_import import import_community_resourcepack
from translation.mod_lang_cache import build_mod_item_glossary


LANGUAGE_PAIR = "en_es_communitytest"


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR

    try:
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # A mod actually installed in the modpack, with its real
            # en_us.json.
            mods_folder = tmp / "mods"
            mods_folder.mkdir()
            with zipfile.ZipFile(mods_folder / "mekanism.jar", "w") as archive:
                archive.writestr(
                    "assets/mekanism/lang/en_us.json",
                    json.dumps({"block.mekanism.energy_cube": "Energy Cube"})
                )
            # A mod NOT installed in this modpack — its translation in
            # the downloaded pack must be ignored, not force-matched.
            with zipfile.ZipFile(mods_folder / "create.jar", "w") as archive:
                archive.writestr(
                    "assets/create/lang/en_us.json",
                    json.dumps({"item.create.wrench": "Wrench"})
                )

            # A downloaded community pack (as a folder here) with a
            # translation for a mod that IS installed, and one for a mod
            # that ISN'T.
            pack_folder = tmp / "community_pack"
            (pack_folder / "assets" / "mekanism" / "lang").mkdir(parents=True)
            (pack_folder / "assets" / "mekanism" / "lang" / "es_es.json").write_text(
                json.dumps({"block.mekanism.energy_cube": "Cubo de Energía"}),
                encoding="utf-8"
            )
            (pack_folder / "assets" / "notinstalledmod" / "lang").mkdir(parents=True)
            (pack_folder / "assets" / "notinstalledmod" / "lang" / "es_es.json").write_text(
                json.dumps({"item.notinstalledmod.thing": "Cosa"}),
                encoding="utf-8"
            )

            result = import_community_resourcepack(
                pack_folder, mods_folder, language_pair=LANGUAGE_PAIR
            )

            assert result["mods_matched"] == 1, result
            assert result["pairs_added"] == 1, result

            glossary = build_mod_item_glossary(LANGUAGE_PAIR)
            assert glossary["Energy Cube"] == "Cubo de Energía"
            assert "Wrench" not in glossary
            assert "Cosa" not in glossary.values()

            # A zip source must work the same way as a folder.
            pack_zip = tmp / "community_pack.zip"
            with zipfile.ZipFile(pack_zip, "w") as archive:
                for path in pack_folder.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(pack_folder))

            result2 = import_community_resourcepack(
                pack_zip, mods_folder, language_pair=LANGUAGE_PAIR
            )
            assert result2["mods_matched"] == 1, result2

            # A path that's neither a folder nor a real zip fails loudly.
            bogus = tmp / "not_a_pack.txt"
            bogus.write_text("nope", encoding="utf-8")
            try:
                import_community_resourcepack(bogus, mods_folder, language_pair=LANGUAGE_PAIR)
                assert False, "esperaba un ValueError"
            except ValueError:
                pass

        print("Community import OK")

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
