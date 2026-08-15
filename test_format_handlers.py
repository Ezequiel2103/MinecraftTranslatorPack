import json
from pathlib import Path
from tempfile import TemporaryDirectory

from formats.handler import get_handler
from analyzer.text_replacer import apply_translations


def main():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)

        json_path = root / "en_us.json"
        json_path.write_text(
            json.dumps({"title": "Getting Started"}),
            encoding="utf-8"
        )
        json_data = get_handler(json_path).read(json_path)
        assert json_data["title"] == "Getting Started"

        lang_path = root / "en_us.lang"
        lang_path.write_text(
            "# comment\ntitle=Getting Started\nmessage=Hello\n",
            encoding="utf-8"
        )
        lang_data = get_handler(lang_path).read(lang_path)
        assert lang_data == {
            "title": "Getting Started",
            "message": "Hello"
        }
        lang_data["title"] = "Comenzando"
        get_handler(lang_path).write(lang_data, lang_path)
        lang_output = lang_path.read_text(encoding="utf-8")
        assert "# comment" in lang_output
        assert "title=Comenzando" in lang_output

        snbt_path = root / "example.snbt"
        snbt_path.write_text(
            '{title:"Getting Started",count:1b,items:["Diamond"]}',
            encoding="utf-8"
        )
        snbt_data = get_handler(snbt_path).read(snbt_path)
        assert snbt_data["title"] == "Getting Started"
        assert int(snbt_data["count"]) == 1
        apply_translations(
            snbt_data,
            [{
                "path": "title",
                "translation": "Comenzando",
                "valid": True
            }]
        )
        get_handler(snbt_path).write(snbt_data, snbt_path)
        reread_snbt = get_handler(snbt_path).read(snbt_path)
        assert reread_snbt["title"] == "Comenzando"

    print("Format handlers OK")


if __name__ == "__main__":
    main()
