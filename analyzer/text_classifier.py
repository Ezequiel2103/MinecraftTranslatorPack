import re


def classify_text(text):
    """
    Classifies text as:
    - technical: probably should not be translated
    - translatable: probably human-readable text
    - uncertain: requires further review
    """

    text = text.strip()

    if not text:
        return "uncertain"

    # Minecraft color codes: &a, &6, etc.
    if re.fullmatch(r"(&[0-9a-fk-or])+", text, re.IGNORECASE):
        return "technical"

    # Minecraft/mod IDs:
    # minecraft:diamond
    # modern_industrialization:bronze_machine
    if re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", text):
        return "technical"

    # URLs
    if re.match(r"^(https?://|www\.)", text, re.IGNORECASE):
        return "technical"

    # Text containing no letters
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", text):
        return "technical"

    return "translatable"