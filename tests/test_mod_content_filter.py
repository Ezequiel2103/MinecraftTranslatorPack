import json
import tempfile
import zipfile
from pathlib import Path

from analyzer.mod_lang_scanner import has_real_content, scan_mod_lang_sources


def main():
    assert has_real_content({"item.create.wrench": "Wrench"}) is True
    assert has_real_content({"block.create.cogwheel": "Cogwheel"}) is True
    assert has_real_content({
        "option.sodium.description": "Tweak your settings",
        "key.sodium.reload_chunks": "Reload Chunks"
    }) is False
    assert has_real_content({}) is False

    with tempfile.TemporaryDirectory() as tmp:
        mods_folder = Path(tmp)

        with zipfile.ZipFile(mods_folder / "create.jar", "w") as archive:
            archive.writestr(
                "assets/create/lang/en_us.json",
                json.dumps({"item.create.wrench": "Wrench"})
            )

        with zipfile.ZipFile(mods_folder / "sodium.jar", "w") as archive:
            archive.writestr(
                "assets/sodium/lang/en_us.json",
                json.dumps({"option.sodium.description": "Tweak settings"})
            )

        all_sources = scan_mod_lang_sources(mods_folder)
        assert {s["modid"] for s in all_sources} == {"create", "sodium"}

        content_only = scan_mod_lang_sources(mods_folder, content_only=True)
        assert {s["modid"] for s in content_only} == {"create"}

    print("Mod content filter OK")


if __name__ == "__main__":
    main()
