from pathlib import Path
from tempfile import TemporaryDirectory

from modpack_locator import locate_modpack_paths


def main():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        result = locate_modpack_paths(root)
        assert result == {"mods_folder": None, "quests_lang_folder": None}

        (root / "mods").mkdir()
        lang_dir = root / "config" / "ftbquests" / "quests" / "lang"
        lang_dir.mkdir(parents=True)

        result = locate_modpack_paths(root)
        assert result["mods_folder"] == str(root / "mods")
        assert result["quests_lang_folder"] == str(lang_dir)

    # A quest system nested somewhere else under config/ must still be
    # found via the fallback search.
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        odd_lang_dir = root / "config" / "somequestmod" / "quests" / "lang"
        odd_lang_dir.mkdir(parents=True)

        result = locate_modpack_paths(root)
        assert result["quests_lang_folder"] == str(odd_lang_dir)
        assert result["mods_folder"] is None

    print("Modpack locator OK")


if __name__ == "__main__":
    main()
