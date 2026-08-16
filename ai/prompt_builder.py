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
