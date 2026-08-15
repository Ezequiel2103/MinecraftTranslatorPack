from analyzer.translation_filter import should_translate
from analyzer.text_classifier import classify_text


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


def decide_translation(item):
    """
    Determines what should happen with a text entry.

    Possible actions:
    - translate
    - ignore
    - review
    """

    text = item.get("text", "")
    key = item.get("key")
    path = item.get("path")
    parent_path = item.get("parent_path")

    # Basic filter
    if not should_translate(
        text,
        key,
        path,
        parent_path
    ):
        return {
            "action": "ignore",
            "reason": "technical_or_non_translatable"
        }

    # General text classification
    classification = classify_text(text)

    if classification == "technical":

        return {
            "action": "ignore",
            "reason": "technical_text"
        }

    # Explicit technical keys
    if key:
        normalized_key = key.lower()

        if normalized_key in TECHNICAL_KEYS:

            return {
                "action": "ignore",
                "reason": "technical_key"
            }

        # Explicit human-readable keys
        if normalized_key in TRANSLATABLE_KEYS:

            return {
                "action": "translate",
                "reason": "human_readable_key"
            }

    # Normal Minecraft localization entries
    #
    # Example:
    # item.minecraft.diamond -> Diamond
    # block.minecraft.stone -> Stone
    #
    # The key itself is technical, but the VALUE is human-readable.

    if classification == "translatable":

        return {
            "action": "translate",
            "reason": "human_readable_text"
        }

    # Anything that reaches this point
    # should be manually reviewed.

    return {
        "action": "review",
        "reason": "uncertain_context"
    }