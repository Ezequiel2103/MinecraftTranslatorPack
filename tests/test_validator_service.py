from translation.translation_service import (
    TranslationService
)


class BrokenAITranslator:

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):

        return {
            "translation": "Traducción rota",
            "source": "broken_ai"
        }


service = TranslationService(
    "en_es",
    ai_translator=BrokenAITranslator()
)


result = service.translate(
    "Press %s to open %sMachine\\nWelcome!"
)


print("--------------------------------")
print("Validator Service Test")
print("--------------------------------")
print()

print(f"Original:")
print("Press %s to open %sMachine\\nWelcome!")
print()

print(
    f"Translation: {result['translation']}"
)

print(
    f"Source: {result['source']}"
)

print(
    f"Valid: {result['valid']}"
)

print(
    f"Reason: {result['validation_reason']}"
)
