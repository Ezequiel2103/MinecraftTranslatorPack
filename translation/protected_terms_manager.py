import json
from pathlib import Path


def protected_terms_path(language_pair="en_es"):
    return Path("translation") / language_pair / "protected_terms.json"


def load_protected_terms(language_pair="en_es"):
    """
    Loads the list of terms (such as mod names) that must never be
    translated for a given language pair.
    """

    path = protected_terms_path(language_pair)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_protected_terms(terms, language_pair="en_es"):
    """
    Saves the list of protected terms so it can be reviewed and edited
    by hand before the next translation run.
    """

    path = protected_terms_path(language_pair)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            sorted(set(terms)),
            file,
            ensure_ascii=False,
            indent=4
        )
