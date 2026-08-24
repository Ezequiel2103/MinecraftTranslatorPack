import json
from pathlib import Path
from tempfile import TemporaryDirectory

from translator_app import translate_file


def main():
    count = 15

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        input_path = root / "en_us.json"
        output_path = root / "es_es.json"

        data = {f"item{i}": f"Item {i}" for i in range(count)}
        input_path.write_text(json.dumps(data), encoding="utf-8")

        report = translate_file(
            input_path,
            output_path,
            ai_provider="mock",
            concurrency=5,
            review_root=str(root / "review")
        )

        # Results are collected from concurrent workers as they finish, not
        # necessarily in submission order; they must still be reassembled to
        # match translatable_texts' original order by index.
        translatable_paths = [
            item["path"] for item in report["translatable_texts"]
        ]
        result_paths = [result["path"] for result in report["results"]]
        assert result_paths == translatable_paths
        assert len(report["results"]) == count

    print("Concurrency order OK")


if __name__ == "__main__":
    main()
