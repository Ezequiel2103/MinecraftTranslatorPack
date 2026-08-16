import json
from pathlib import Path


CACHE_ROOT = Path("mod_lang_cache")


def classification_path(language_pair="en_es"):
    return CACHE_ROOT / language_pair / "content_classification.json"


def load_classification(language_pair="en_es"):
    """
    Loads the persisted {modid: has_real_content} classification for a
    language pair. Editable by hand: flipping a value overrides the
    automatic heuristic for that mod from then on.
    """

    path = classification_path(language_pair)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_classification(classification, language_pair="en_es"):
    path = classification_path(language_pair)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            classification,
            file,
            ensure_ascii=False,
            indent=4,
            sort_keys=True
        )
