import json
import tempfile
import zipfile
from pathlib import Path

from analyzer.mod_lang_scanner import scan_mod_lang_sources


def main():
    with tempfile.TemporaryDirectory() as tmp:
        mods_folder = Path(tmp)

        with zipfile.ZipFile(mods_folder / "create.jar", "w") as archive:
            archive.writestr(
                "assets/create/lang/en_us.json",
                json.dumps({"item.create.wrench": "Wrench"})
            )

        with zipfile.ZipFile(mods_folder / "translated_mod.jar", "w") as archive:
            archive.writestr(
                "assets/translatedmod/lang/en_us.json",
                json.dumps({"item.translatedmod.thing": "Thing"})
            )
            archive.writestr(
                "assets/translatedmod/lang/es_es.json",
                json.dumps({"item.translatedmod.thing": "Cosa"})
            )

        with zipfile.ZipFile(mods_folder / "library.jar", "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "no lang here")

        sources = scan_mod_lang_sources(mods_folder)
        by_modid = {item["modid"]: item for item in sources}

        assert set(by_modid) == {"create", "translatedmod"}
        assert by_modid["create"]["has_es_es"] is False
        assert by_modid["create"]["en_us"] == {"item.create.wrench": "Wrench"}
        assert by_modid["translatedmod"]["has_es_es"] is True

    print("Mod lang scanner OK")


if __name__ == "__main__":
    main()
