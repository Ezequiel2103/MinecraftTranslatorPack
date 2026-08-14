import json
from pathlib import Path


LOCALIZATION_PATH = Path(__file__).parent


def load_interface(language="es"):
    file_path = (
        LOCALIZATION_PATH
        / language
        / "interface.json"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Localization file not found: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)