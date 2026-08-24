import json
from pathlib import Path
from tempfile import TemporaryDirectory

from translator_app import translate_folder


def main():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        # output_folder == input_folder: translating straight into the
        # modpack's own lang folder, same as the GUI now does.
        lang_folder = root / "config" / "ftbquests" / "quests" / "lang"
        review_root = root / "review"
        backup_dir = root / "_translator_backups" / "20260101_000000"

        lang_folder.mkdir(parents=True)
        (lang_folder / "en_us.snbt").write_text(
            '{title:"Diamond",count:1b}',
            encoding="utf-8"
        )

        # 1. First run: no es_es.snbt exists yet, so nothing to back up,
        # and the translated file lands right next to the source.
        reports = translate_folder(
            lang_folder,
            lang_folder,
            ai_provider="mock",
            review_root=review_root,
            backup_dir=backup_dir
        )

        assert len(reports) == 1
        assert reports[0]["backed_up_to"] is None
        assert (lang_folder / "en_us.snbt").exists(), (
            "the original source file must never be touched"
        )

        from formats.handler import get_handler
        translated = get_handler(lang_folder / "es_es.snbt").read(
            lang_folder / "es_es.snbt"
        )
        assert translated["title"] == "Diamante", translated

        # 2. A fan translation (or a previous run's output) already sits
        # at es_es.snbt -- a second run must back it up before
        # overwriting it, never just silently discard it.
        (lang_folder / "es_es.snbt").write_text(
            '{title:"Traduccion vieja",count:1b}',
            encoding="utf-8"
        )

        reports2 = translate_folder(
            lang_folder,
            lang_folder,
            ai_provider="mock",
            review_root=review_root,
            backup_dir=backup_dir
        )

        backed_up_path = Path(reports2[0]["backed_up_to"])
        assert backed_up_path.exists(), reports2
        assert backed_up_path.read_text(encoding="utf-8") == (
            '{title:"Traduccion vieja",count:1b}'
        )
        # And the real file now has the fresh translation, not the old one.
        refreshed = get_handler(lang_folder / "es_es.snbt").read(
            lang_folder / "es_es.snbt"
        )
        assert refreshed["title"] == "Diamante", refreshed

        # 3. Without backup_dir, behavior is unchanged (plain overwrite,
        # same as every other caller of translate_folder relies on).
        reports3 = translate_folder(
            lang_folder, lang_folder, ai_provider="mock", review_root=review_root
        )
        assert reports3[0]["backed_up_to"] is None

        print("Translate in place OK")


if __name__ == "__main__":
    main()
