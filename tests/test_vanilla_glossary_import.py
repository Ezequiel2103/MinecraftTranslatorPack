import json
import shutil
import zipfile
from pathlib import Path

from import_vanilla_glossary import import_vanilla_glossary
from translation.translation_memory import memory_path


def _build_fake_minecraft_root(root):
    versions_dir = root / "versions" / "1.99.9"
    versions_dir.mkdir(parents=True)
    jar_path = versions_dir / "1.99.9.jar"

    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr(
            "assets/minecraft/lang/en_us.json",
            json.dumps({
                "item.minecraft.diamond": "Diamond",
                "block.minecraft.dirt": "Dirt",
                "gui.done": "Done",
                "unchanged.entry": "Same"
            })
        )

    indexes_dir = root / "assets" / "indexes"
    indexes_dir.mkdir(parents=True)
    object_hash = "abc123deadbeef"
    objects_dir = root / "assets" / "objects" / object_hash[:2]
    objects_dir.mkdir(parents=True)
    (objects_dir / object_hash).write_text(
        json.dumps({
            "item.minecraft.diamond": "Diamante",
            "block.minecraft.dirt": "Tierra",
            "gui.done": "Hecho",
            "unchanged.entry": "Same"
        }),
        encoding="utf-8"
    )

    index_path = indexes_dir / "1.json"
    index_path.write_text(
        json.dumps({
            "objects": {
                "minecraft/lang/es_es.json": {"hash": object_hash, "size": 1}
            }
        }),
        encoding="utf-8"
    )

    return jar_path, index_path


def main():
    tmp_root = Path("tmp_fake_minecraft_root")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir()

    language_pair = "en_zz_test_vanilla"
    test_memory_path = memory_path(language_pair)
    if test_memory_path.exists():
        test_memory_path.unlink()

    try:
        _build_fake_minecraft_root(tmp_root)

        # Pre-seed one entry that the importer must NOT overwrite.
        test_memory_path.parent.mkdir(parents=True, exist_ok=True)
        test_memory_path.write_text(
            json.dumps({
                "Dirt": {
                    "translation": "Tierra (manual)",
                    "type": "manual",
                    "source": "manual"
                }
            }),
            encoding="utf-8"
        )

        result = import_vanilla_glossary(
            minecraft_root=tmp_root,
            language_pair=language_pair
        )

        # "Diamond" is new -> added. "Dirt" already existed -> left alone.
        # "Done" (gui.done) has real different translation -> added.
        # "unchanged.entry" has identical en/es text -> skipped, not useful.
        assert result["added"] == 2, result
        assert result["skipped_existing"] == 1, result

        memory = json.loads(test_memory_path.read_text(encoding="utf-8"))
        assert memory["Diamond"]["translation"] == "Diamante"
        assert memory["Diamond"]["source"] == "minecraft_official"
        assert memory["Dirt"]["translation"] == "Tierra (manual)"
        assert memory["Done"]["translation"] == "Hecho"
        assert "Same" not in memory

        print("Vanilla glossary import OK")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        if test_memory_path.exists():
            test_memory_path.unlink()
        if test_memory_path.parent.exists():
            shutil.rmtree(test_memory_path.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
