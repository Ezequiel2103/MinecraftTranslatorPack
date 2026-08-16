from pathlib import Path
from tempfile import TemporaryDirectory

from deploy_manager import apply_to_modpack_copy


def main():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)

        instance = root / "instance"
        lang_dir = instance / "config" / "ftbquests" / "quests" / "lang"
        lang_dir.mkdir(parents=True)
        (lang_dir / "en_us.snbt").write_text(
            '{title:"Hello"}', encoding="utf-8"
        )
        (instance / "mods").mkdir()
        (instance / "mods" / "create.jar").write_bytes(b"fake jar")

        output_folder = root / "translated"
        output_folder.mkdir()
        (output_folder / "es_es.snbt").write_text(
            '{title:"Hola"}', encoding="utf-8"
        )

        destination = root / "instance_copy"

        result = apply_to_modpack_copy(
            instance,
            destination,
            "config/ftbquests/quests/lang",
            output_folder
        )

        assert (destination / "mods" / "create.jar").exists()
        assert (
            destination / "config/ftbquests/quests/lang/en_us.snbt"
        ).read_text(encoding="utf-8") == '{title:"Hello"}'
        assert (
            destination / "config/ftbquests/quests/lang/es_es.snbt"
        ).read_text(encoding="utf-8") == '{title:"Hola"}'
        assert result["backup_dir"] is None
        assert (instance / "config/ftbquests/quests/lang/es_es.snbt").exists() is False

        # Re-applying an updated translation must back up the previous one.
        (output_folder / "es_es.snbt").write_text(
            '{title:"Hola de nuevo"}', encoding="utf-8"
        )

        second_result = apply_to_modpack_copy(
            instance,
            destination,
            "config/ftbquests/quests/lang",
            output_folder
        )

        assert (
            destination / "config/ftbquests/quests/lang/es_es.snbt"
        ).read_text(encoding="utf-8") == '{title:"Hola de nuevo"}'
        assert second_result["backup_dir"] is not None
        backed_up = Path(second_result["backed_up_files"][0])
        assert backed_up.read_text(encoding="utf-8") == '{title:"Hola"}'

    print("Deploy manager OK")


if __name__ == "__main__":
    main()
