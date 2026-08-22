from app_paths import resource_dir
from json_io import load_json_safe


def load_terminology(language_pair):
    """
    Loads the terminology dictionary for a language pair.
    """

    path = resource_dir() / "translation" / language_pair / "terminology.json"
    return load_json_safe(path, {})


def find_term(text, terminology):
    """
    Searches for an exact terminology match.
    """

    return terminology.get(text)