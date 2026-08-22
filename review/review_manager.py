from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic
from translation.translation_memory import add_translation

def load_pending(language_pair):
    """
    Loads pending translations.
    """

    path = (
        data_dir() / "review"
        / language_pair
        / "pending.json"
    )

    return load_json_safe(path, {})


def save_pending_data(
    pending,
    language_pair
):
    """
    Saves the current pending translations.
    """

    path = (
        data_dir() / "review"
        / language_pair
        / "pending.json"
    )

    write_json_atomic(path, pending, ensure_ascii=False, indent=4)


def approve_translation(
    original,
    translation,
    language_pair
):
    """
    Approves a translation,
    stores it in translation memory,
    and removes it from pending.
    """

    pending = load_pending(
        language_pair
    )

    if original not in pending:
        return False

    # Add to translation memory

    add_translation(
        original,
        translation,
        language_pair=language_pair
    )

    # Remove from pending

    del pending[original]

    save_pending_data(
        pending,
        language_pair
    )

    return True
