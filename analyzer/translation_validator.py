import re
from collections import Counter


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


def attempt_placeholder_repair(original, translation):
    """
    A narrow, safe fix for one specific observed AI failure mode: it
    repeated a placeholder/color code that should only appear once. If
    every token the translation is missing is actually just an EXCESS
    copy of a token that legitimately belongs there (never a token
    that's outright missing, or one that shouldn't exist at all), the
    extra copies are stripped and the result re-validated before being
    returned. Returns None if the mismatch isn't this exact, safe case —
    a missing token is a content decision, not something to guess at.
    """

    if not translation:
        return None

    original_counts = Counter(extract_placeholders(original))
    translation_counts = Counter(extract_placeholders(translation))

    for token, count in translation_counts.items():
        if count > original_counts.get(token, 0) and original_counts.get(token, 0) == 0:
            return None

    for token, count in original_counts.items():
        if translation_counts.get(token, 0) < count:
            return None

    repaired = translation

    for token, count in translation_counts.items():
        extra = count - original_counts.get(token, 0)

        if extra <= 0:
            continue

        pattern = re.compile(re.escape(token))
        removed = 0

        def _strip_extra_occurrences(match):
            nonlocal removed
            if removed < extra:
                removed += 1
                return ""
            return match.group(0)

        repaired = pattern.sub(_strip_extra_occurrences, repaired)

    if repaired == translation:
        return None

    if not validate_translation(original, repaired)["valid"]:
        return None

    return repaired


SCRIPT_PATTERNS = {
    "cjk": re.compile(r"[一-鿿]"),        # Chinese/Japanese Kanji
    "kana": re.compile(r"[぀-ヿ]"),        # Hiragana / Katakana (Japanese)
    "hangul": re.compile(r"[가-힣]"),      # Hangul syllables (Korean)
    "cyrillic": re.compile(r"[Ѐ-ӿ]"),     # Russian and other Cyrillic
    "arabic": re.compile(r"[؀-ۿ]"),
}

# Scripts a translation is *expected* to use for a given target language, so
# the "wrong script" check below only flags a script neither the original
# nor the target language should ever contain — otherwise every correct
# translation into Russian/Chinese/Japanese/Korean would be rejected too.
TARGET_LANGUAGE_SCRIPTS = {
    "zh": {"cjk"},
    "ja": {"cjk", "kana"},
    "ko": {"hangul"},
    "ru": {"cyrillic"},
}


def validate_translation_quality(original, translation, target_language=None):
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

    allowed_scripts = TARGET_LANGUAGE_SCRIPTS.get(target_language, set())

    for script_name, pattern in SCRIPT_PATTERNS.items():
        if script_name in allowed_scripts:
            continue
        if pattern.search(translation_clean) and not pattern.search(original_clean):
            return {
                "valid": False,
                "reason": "wrong_script"
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
