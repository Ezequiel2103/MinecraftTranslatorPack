from pathlib import Path

from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


def save_pending(
    items,
    language_pair,
    replace=False,
    review_root=None
):
    """
    Saves texts that require translation review.
    """

    if review_root is None:
        review_root = data_dir() / "review"

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

    if not replace:
        pending = load_json_safe(pending_path, {})

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

    write_json_atomic(pending_path, pending, ensure_ascii=False, indent=4)
