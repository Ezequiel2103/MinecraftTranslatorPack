import json
from pathlib import Path
from tempfile import TemporaryDirectory

from translator_app import translate_folder


def main():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        input_folder = root / "input"
        output_folder = root / "output"
        review_root = root / "review"

        (input_folder / "lang").mkdir(parents=True)
        (input_folder / "data").mkdir(parents=True)
        (input_folder / "lang" / "en_us.json").write_text(
            json.dumps({"item": "Diamond"}),
            encoding="utf-8"
        )
        (input_folder / "lang" / "en_us.lang").write_text(
            "# Keep this comment\ntitle=Diamond\n",
            encoding="utf-8"
        )
        (input_folder / "data" / "example.snbt").write_text(
            '{title:"Diamond",count:1b}',
            encoding="utf-8"
        )

        reports = translate_folder(
            input_folder,
            output_folder,
            ai_provider="mock",
            review_root=review_root
        )

        assert len(reports) == 3
        assert json.loads(
            (output_folder / "lang" / "es_es.json").read_text(
                encoding="utf-8"
            )
        )["item"] == "Diamante"
        lang_output = (
            output_folder / "lang" / "es_es.lang"
        ).read_text(encoding="utf-8")
        assert "# Keep this comment" in lang_output
        assert "title=Diamante" in lang_output

        snbt_output_path = output_folder / "data" / "example.snbt"
        from formats.handler import get_handler
        snbt_output = get_handler(snbt_output_path).read(snbt_output_path)
        assert snbt_output["title"] == "Diamante"
        assert int(snbt_output["count"]) == 1

    print("End-to-end formats OK")


if __name__ == "__main__":
    main()
