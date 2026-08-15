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
    )

    return prompt