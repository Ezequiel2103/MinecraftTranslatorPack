import json


def build_translation_prompt(
    text,
    source_language,
    target_language,
    terminology=None,
    context=None
):
    """
    Builds the prompt used by the AI translator.
    """

    terminology = terminology or {}

    prompt = f"""
You are a professional translator specialized in Minecraft
mods and modpacks.

Translate the following text from
{source_language} to {target_language}.

Important rules:

- Preserve placeholders exactly.
- Preserve Minecraft formatting codes.
- Preserve escaped characters such as \\n and \\t.
- Do not translate technical identifiers.
- Keep the meaning and context of the original text.
- Use the provided terminology consistently.

"""

    if terminology:

        prompt += "\nRequired terminology:\n"

        for original, translation in terminology.items():

            prompt += (
                f"- {original} → {translation}\n"
            )

    if context:

        prompt += (
            f"\nContext:\n{context}\n"
        )

    prompt += (
        f"\nText to translate:\n{text}\n"
        "\nOutput requirements:\n"
        "- Return only the translated text.\n"
        "- Do not explain, analyze, quote, or label the result.\n"
        "- Do not repeat these instructions.\n"
    )

    return prompt


def build_batch_translation_prompt(
    texts_by_id,
    source_language,
    target_language,
    terminology=None
):
    """
    Builds a prompt that asks for many independent translations in a
    single request, so the fixed cost of these instructions is paid once
    instead of once per text — the same JSON-in/JSON-out shape used for a
    single text, just keyed by an arbitrary id so a scrambled or
    incomplete AI response can still be matched back to the right item
    instead of silently misaligning by position.
    """

    terminology = terminology or {}

    prompt = f"""
You are a professional translator specialized in Minecraft
mods and modpacks.

Translate every value in the JSON object below from
{source_language} to {target_language}.

Important rules:

- Preserve placeholders exactly.
- Preserve Minecraft formatting codes.
- Preserve escaped characters such as \\n and \\t.
- Do not translate technical identifiers.
- Keep the meaning and context of each text.
- Use the provided terminology consistently.
- Translate every entry independently: they are unrelated texts, not
  parts of one passage.

"""

    if terminology:
        prompt += "\nRequired terminology:\n"

        for original, translation in terminology.items():
            prompt += f"- {original} → {translation}\n"

    prompt += (
        "\nTexts to translate (JSON object, id -> text):\n"
        + json.dumps(texts_by_id, ensure_ascii=False)
        + "\n\nOutput requirements:\n"
        "- Return ONLY a JSON object with the exact same ids as keys.\n"
        "- Each value must be the translation of that id's text, nothing else.\n"
        "- Do not add, remove, merge, or reorder ids.\n"
        "- Do not wrap the JSON in markdown, explanations, or code fences.\n"
    )

    return prompt


def build_review_prompt(text, source_language, target_language):
    """
    Builds the prompt used to double-check a translation that came back
    identical to the original text, in a Minecraft mod/modpack context.
    """

    return f"""
You are reviewing a {source_language} to {target_language} translation used
in a Minecraft mod or modpack.

The following {target_language} output was left identical to the original
{source_language} text:

Text: {text}

Decide whether leaving it unchanged is CORRECT (it is a proper noun, a mod
or brand name, an acronym, or a word spelled the same in both languages) or
INCORRECT (it is ordinary {source_language} text that should have been
translated into {target_language} but was not).

Answer with exactly one word: CORRECT or INCORRECT.
"""
