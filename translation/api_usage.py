import json
from datetime import datetime, timezone
from pathlib import Path


USAGE_PATH = Path("translation") / "google_translate_usage.json"

# Google's free tier is 500,000 characters/month; a safety margin is kept
# below that so a run stops itself before the account could ever actually
# be charged, even if several translations land right at the edge.
DEFAULT_CHARACTER_LIMIT = 480_000


def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_usage():
    """
    Returns {"month": "YYYY-MM", "characters_used": N} for the current
    calendar month, resetting automatically when the month changes (same
    as Google's own free-tier quota resets).
    """

    if not USAGE_PATH.exists():
        return {"month": _current_month(), "characters_used": 0}

    try:
        with USAGE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"month": _current_month(), "characters_used": 0}

    if data.get("month") != _current_month():
        return {"month": _current_month(), "characters_used": 0}

    return {
        "month": data["month"],
        "characters_used": data.get("characters_used", 0)
    }


def record_usage(characters):
    usage = get_usage()
    usage["characters_used"] += characters

    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_PATH.open("w", encoding="utf-8") as file:
        json.dump(usage, file, ensure_ascii=False, indent=4)

    return usage


def would_exceed(characters, limit=DEFAULT_CHARACTER_LIMIT):
    return get_usage()["characters_used"] + characters > limit


def remaining_characters(limit=DEFAULT_CHARACTER_LIMIT):
    return max(0, limit - get_usage()["characters_used"])
