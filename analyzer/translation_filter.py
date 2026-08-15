import re


TECHNICAL_KEYS = {
    "id",
    "identifier",
    "registry",
    "registry_name",
    "resource_location",
    "namespace",
}


TRANSLATABLE_KEYS = {
    "name",
    "title",
    "description",
    "desc",
    "message",
    "text",
    "label",
    "tooltip",
    "subtitle",
    "hint",
    "button",
}


def is_identifier(text):
    """
    Detects Minecraft-style identifiers.
    """

    pattern = r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$"

    return bool(
        re.match(pattern, text)
    )


def is_numeric(text):
    """
    Detects numeric values.
    """

    try:
        float(text)
        return True

    except ValueError:
        return False


def contains_letters(text):
    """
    Checks whether the text contains alphabetic characters.
    """

    return bool(
        re.search(
            r"[A-Za-zÁÉÍÓÚáéíóúÑñ]",
            text
        )
    )


def should_translate(
    text,
    key=None,
    path=None,
    parent_path=None
):
    """
    Determines whether a text should be considered
    for translation using text and JSON context.
    """

    if not text:
        return False

    text = text.strip()

    if not text:
        return False

    if is_numeric(text):
        return False

    if is_identifier(text):
        return False

    if not contains_letters(text):
        return False

    if key:
        normalized_key = key.lower()

        if normalized_key in TECHNICAL_KEYS:
            return False

        if normalized_key in TRANSLATABLE_KEYS:
            return True

    return True