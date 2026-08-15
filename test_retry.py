from translation.translation_service import (
    TranslationService
)

from ai.ai_translator import (
    RetryMockAITranslator
)


translator = RetryMockAITranslator()


service = TranslationService(
    "en_es",
    ai_translator=translator
)


result = service.translate(
    "Press %s to open %sMachine\\nWelcome!"
)


print("--------------------------------")
print("Automatic Retry Test")
print("--------------------------------")
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

print(
    f"Attempts: {result['attempts']}"
)