import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from deploy_manager import build_curseforge_import_zip


def main():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        instance = root / "instance"
        instance.mkdir()

        manifest = {
            "minecraft": {
                "version": "1.21.1",
                "modLoaders": [{"id": "neoforge-21.1.232", "primary": True}]
            },
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "Original Pack",
            "version": "old",
            "author": "someone",
            "files": [{"projectID": 1, "fileID": 2, "required": True}],
            "overrides": "overrides"
        }
        (instance / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (instance / "minecraftinstance.json").write_text("{}", encoding="utf-8")

        (instance / "mods").mkdir()
        (instance / "mods" / "create.jar").write_bytes(b"fake jar bytes")

        lang_dir = instance / "config" / "ftbquests" / "quests" / "lang"
        lang_dir.mkdir(parents=True)
        (lang_dir / "en_us.snbt").write_text('{title:"Hello"}', encoding="utf-8")
        (lang_dir / "es_es.snbt").write_text('{title:"Hola"}', encoding="utf-8")

        # A leftover zip from a previous manual packaging attempt, sitting
        # right at the instance root, must never be bundled as content.
        (instance / "old_manual_export.zip").write_bytes(b"0" * 1024)

        output_zip = root / "pack.zip"

        result_path = build_curseforge_import_zip(
            instance,
            output_zip,
            pack_name="Translated Pack"
        )

        assert result_path == str(output_zip)

        with zipfile.ZipFile(output_zip) as archive:
            names = set(archive.namelist())

            assert "manifest.json" in names
            assert "overrides/mods/create.jar" not in names
            assert "overrides/minecraftinstance.json" not in names
            assert "overrides/old_manual_export.zip" not in names
            assert (
                "overrides/config/ftbquests/quests/lang/es_es.snbt" in names
            )

            packaged_manifest = json.loads(archive.read("manifest.json"))
            assert packaged_manifest["name"] == "Translated Pack"
            assert packaged_manifest["overrides"] == "overrides"
            assert packaged_manifest["files"] == [
                {"projectID": 1, "fileID": 2, "required": True}
            ]

            lang_content = archive.read(
                "overrides/config/ftbquests/quests/lang/es_es.snbt"
            ).decode("utf-8")
            assert lang_content == '{title:"Hola"}'

    print("CurseForge zip packaging OK")


if __name__ == "__main__":
    main()
