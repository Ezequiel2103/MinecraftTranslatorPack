from ai.prompt_builder import build_review_prompt
from review.review_manager import load_pending, approve_translation


def ai_review_pending(
    language_pair,
    ai_translator,
    source_language="en",
    target_language="es"
):
    """
    Asks the AI to double-check pending entries that were only rejected
    because the translation came back identical to the original text.
    Confident matches (proper nouns, mod names, loanwords) are approved
    automatically and moved to translation memory; anything else is left
    pending for manual review.
    """

    pending = load_pending(language_pair)
    candidates = [
        text for text, data in pending.items()
        if data.get("reason") == "unchanged_translation"
    ]

    approved = []
    kept = []

    for text in candidates:
        prompt = build_review_prompt(text, source_language, target_language)
        verdict = ai_translator.ask(prompt).strip().upper()

        if verdict.startswith("CORRECT"):
            approve_translation(text, text, language_pair)
            approved.append(text)
        else:
            kept.append(text)

    return {"approved": approved, "kept": kept}
