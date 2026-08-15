import json
from pathlib import Path


def save_pending(
    items,
    language_pair,
    replace=False,
    review_root="review"
):
    """
    Saves texts that require translation review.
    """

    review_directory = (
        Path(review_root)
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

    if not replace and pending_path.exists():

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

        entry = {
            "path": item["path"],
            "status": "pending",
            "reason": reason
        }

        if "source" in item:
            entry["source"] = item["source"]

        if "attempts" in item:
            entry["attempts"] = item["attempts"]

        pending[text] = entry

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
