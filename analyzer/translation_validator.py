import re


def extract_placeholders(text):
    """
    Extracts placeholders and formatting tokens
    that must remain unchanged.
    """

    patterns = [
        r"%\d*\$?[a-zA-Z]",
        r"\{\{.*?\}\}",
        r"\{.*?\}",
        r"\\n",
        r"\\t",
        r"§[0-9a-fk-or]",
        r"&[0-9a-fk-or]",
    ]

    placeholders = []

    for pattern in patterns:
        placeholders.extend(
            re.findall(
                pattern,
                text,
                re.IGNORECASE
            )
        )

    return placeholders


def validate_translation(
    original,
    translation
):
    """
    Validates that the translation preserves
    important technical elements.
    """

    if not translation:

        return {
            "valid": False,
            "reason": "empty_translation"
        }

    original_tokens = extract_placeholders(
        original
    )

    translation_tokens = extract_placeholders(
        translation
    )

    if sorted(original_tokens) != sorted(
        translation_tokens
    ):

        return {
            "valid": False,
            "reason": "placeholder_mismatch",
            "original_tokens": original_tokens,
            "translation_tokens": translation_tokens
        }

    return {
        "valid": True,
        "reason": None
    }