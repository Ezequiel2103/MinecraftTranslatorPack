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


def validate_translation_quality(original, translation):
    """Rejects common AI outputs that are not a clean translation."""

    if not translation:
        return {
            "valid": False,
            "reason": "empty_translation"
        }

    original_clean = original.strip()
    translation_clean = translation.strip()

    if translation_clean == original_clean:
        return {
            "valid": False,
            "reason": "unchanged_translation"
        }

    if re.search(
        r"(?:^|\n)\s*(translation|traducción|traduccion|answer|respuesta)\s*:",
        translation_clean,
        re.IGNORECASE
    ):
        return {
            "valid": False,
            "reason": "output_label"
        }

    if re.match(r"^\[(ai|ollama|openai).*?\]\s+", translation_clean, re.IGNORECASE):
        return {
            "valid": False,
            "reason": "output_label"
        }

    explanation_markers = (
        "translation using",
        "the translation is",
        "here is the translation",
        "texto a traducir",
        "let's translate",
        "first,"
    )

    if any(
        marker in translation_clean.lower()
        for marker in explanation_markers
    ):
        return {
            "valid": False,
            "reason": "explanation_detected"
        }

    if (
        original_clean
        and original_clean in translation_clean
        and len(translation_clean) >= len(original_clean) * 1.5
    ):
        return {
            "valid": False,
            "reason": "extra_output"
        }

    max_length = max(len(original_clean) * 4 + 100, 300)

    if len(translation_clean) > max_length:
        return {
            "valid": False,
            "reason": "excessive_output"
        }

    return {
        "valid": True,
        "reason": None
    }
