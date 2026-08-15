from translation.translation_memory import translate_with_memory
from ai.ai_translator import MockAITranslator
from analyzer.translation_validator import validate_translation


class TranslationService:

    def __init__(
        self,
        language_pair,
        ai_translator=None
    ):
        self.language_pair = language_pair

        if ai_translator is None:
            ai_translator = MockAITranslator()

        self.ai_translator = ai_translator

    def translate(
        self,
        text,
        path=None,
        source_language="en",
        target_language="es"
    ):

        # 1. Translation memory

        memory_results = translate_with_memory([
            {
                "text": text,
                "path": path or ""
            }
        ])

        memory_result = memory_results[0]

        if memory_result["translation"]:

            validation = validate_translation(
                text,
                memory_result["translation"]
            )

            if validation["valid"]:

                return {
                    "translation": memory_result["translation"],
                    "source": "memory",
                    "valid": True,
                    "validation_reason": None
                }

        # 2. AI translation

        result = self.ai_translator.translate(
            text,
            source_language,
            target_language
        )

        translation = result["translation"]

        validation = validate_translation(
            text,
            translation
        )

        return {
            "translation": translation,
            "source": result["source"],
            "valid": validation["valid"],
            "validation_reason": validation["reason"]
        }