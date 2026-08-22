from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


CACHE_ROOT = data_dir() / "mod_lang_cache"


def classification_path(language_pair="en_es"):
    return CACHE_ROOT / language_pair / "content_classification.json"


def load_classification(language_pair="en_es"):
    """
    Loads the persisted {modid: has_real_content} classification for a
    language pair. Editable by hand: flipping a value overrides the
    automatic heuristic for that mod from then on.
    """

    return load_json_safe(classification_path(language_pair), {})


def save_classification(classification, language_pair="en_es"):
    write_json_atomic(
        classification_path(language_pair), classification,
        ensure_ascii=False, indent=4, sort_keys=True
    )
