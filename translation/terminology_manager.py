import json
from pathlib import Path


def load_terminology(language_pair):
    """
    Loads the terminology dictionary for a language pair.
    """

    path = Path(
        "translation"
    ) / language_pair / "terminology.json"

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def find_term(text, terminology):
    """
    Searches for an exact terminology match.
    """

    return terminology.get(text)