import json
from pathlib import Path
from translation.translation_memory import add_translation

def load_pending(language_pair):
    """
    Loads pending translations.
    """

    path = (
        Path("review")
        / language_pair
        / "pending.json"
    )

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_pending_data(
    pending,
    language_pair
):
    """
    Saves the current pending translations.
    """

    directory = (
        Path("review")
        / language_pair
    )

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    path = directory / "pending.json"

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            pending,
            file,
            ensure_ascii=False,
            indent=4
        )


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
