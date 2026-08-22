from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


def protected_terms_path(language_pair="en_es"):
    return data_dir() / "translation" / language_pair / "protected_terms.json"


def load_protected_terms(language_pair="en_es"):
    """
    Loads the list of terms (such as mod names) that must never be
    translated for a given language pair.
    """

    return load_json_safe(protected_terms_path(language_pair), [])


def save_protected_terms(terms, language_pair="en_es"):
    """
    Saves the list of protected terms so it can be reviewed and edited
    by hand before the next translation run.
    """

    write_json_atomic(
        protected_terms_path(language_pair), sorted(set(terms)),
        ensure_ascii=False, indent=4
    )
