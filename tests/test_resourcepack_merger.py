import json
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from translation.resourcepack_merger import merge_resourcepacks


def _write_lang(root, modid, locale, data):
    path = Path(root) / "assets" / modid / "lang" / f"{locale}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def main():
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Source A: a plain folder (e.g. the app's own "mods_resourcepack"
        # output), with two mods.
        pack_a = tmp / "pack_a"
        _write_lang(pack_a, "mekanism", "es_es", {"block.mekanism.cube": "Cubo"})
        _write_lang(pack_a, "create", "es_es", {"item.create.wrench": "Llave"})

        # Source B: a zip (e.g. shared by a friend), with one overlapping
        # mod (different translation!) and one new one.
        pack_b_folder = tmp / "pack_b_raw"
        _write_lang(pack_b_folder, "mekanism", "es_es", {"block.mekanism.cube": "OTRO Cubo"})
        _write_lang(pack_b_folder, "thermal", "es_es", {"item.thermal.wrench": "Destornillador"})
        pack_b_zip = tmp / "pack_b.zip"
        with zipfile.ZipFile(pack_b_zip, "w") as archive:
            for path in pack_b_folder.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(pack_b_folder))

        output = tmp / "merged"
        icon = tmp / "icon.png"
        icon.write_bytes(b"fake icon bytes")

        result = merge_resourcepacks([pack_a, pack_b_zip], output, pack_icon=icon)

        assert result["merged_mods"] == ["create", "mekanism", "thermal"]
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["modid"] == "mekanism"

        # The FIRST source's version must be the one that survives.
        merged_mekanism = json.loads(
            (output / "assets" / "mekanism" / "lang" / "es_es.json")
            .read_text(encoding="utf-8")
        )
        assert merged_mekanism == {"block.mekanism.cube": "Cubo"}

        merged_create = json.loads(
            (output / "assets" / "create" / "lang" / "es_es.json")
            .read_text(encoding="utf-8")
        )
        assert merged_create == {"item.create.wrench": "Llave"}

        merged_thermal = json.loads(
            (output / "assets" / "thermal" / "lang" / "es_es.json")
            .read_text(encoding="utf-8")
        )
        assert merged_thermal == {"item.thermal.wrench": "Destornillador"}

        assert (output / "pack.mcmeta").exists()
        assert (output / "pack.png").read_bytes() == b"fake icon bytes"

        # A path that's neither a folder nor a real zip must fail loudly
        # instead of silently merging nothing.
        bogus = tmp / "not_a_pack.txt"
        bogus.write_text("just text", encoding="utf-8")
        try:
            merge_resourcepacks([bogus], tmp / "should_not_matter")
            assert False, "esperaba un ValueError"
        except ValueError:
            pass

    print("Resourcepack merger OK")


if __name__ == "__main__":
    main()
