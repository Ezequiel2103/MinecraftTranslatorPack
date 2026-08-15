import json
from pathlib import Path


def save_pending(
    items,
    language_pair
):
    """
    Saves texts that require translation review.
    """

    if not items:
        return

    review_directory = (
        Path("review")
        / language_pair
    )

    review_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    pending_path = (
        review_directory
        / "pending.json"
    )

    pending = {}

    if pending_path.exists():

        with pending_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            pending = json.load(file)

    for item in items:

        text = item["original"]

        reason = item.get(
            "reason",
            "translation_not_found"
        )

        pending[text] = {
            "path": item["path"],
            "status": "pending",
            "reason": reason
        }

    with pending_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            pending,
            file,
            ensure_ascii=False,
            indent=4
        )