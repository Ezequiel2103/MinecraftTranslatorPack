import re

from translation.translation_memory import translate_with_memory
from ai.ai_translator import MockAITranslator
from analyzer.text_protector import protect_text, restore_text
from analyzer.translation_validator import (
    validate_translation,
    validate_translation_quality
)
from translation.retry_manager import TranslationRetryManager
from translation.terminology_manager import load_terminology


class TranslationService:

    def __init__(
        self,
        language_pair,
        ai_translator=None,
        protected_terms=None
    ):
        self.language_pair = language_pair
        self.terminology = load_terminology(language_pair)
        self.protected_terms = protected_terms or []

        if ai_translator is None:
            ai_translator = MockAITranslator()

        self.ai_translator = ai_translator

        self.retry_manager = TranslationRetryManager(
            max_attempts=3
        )

    def translate(
        self,
        text,
        path=None,
        source_language="en",
        target_language="es",
        terminology=None,
        context=None
    ):

        active_terminology = (
            terminology
            if terminology is not None
            else self.terminology
        )

        # 1. Exact terminology match
        terminology_translation = active_terminology.get(text)

        if terminology_translation:
            validation = validate_translation(
                text,
                terminology_translation
            )

            if validation["valid"]:
                return {
                    "translation": terminology_translation,
                    "source": "terminology",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }

        # 2. Translation memory

        memory_results = translate_with_memory([
            {
                "text": text,
                "path": path or ""
            }
        ], self.language_pair)

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
                    "validation_reason": None,
                    "attempts": 0
                }

        # 3. AI translation with automatic retry

        protected_text, protected_tokens = protect_text(
            text,
            extra_terms=self.protected_terms
        )

        # Nothing left to translate once placeholders/protected terms are
        # removed (e.g. a title that is only a formatting code plus a
        # protected mod name): keep the original text instead of asking
        # the AI to "translate" an empty string.
        if protected_tokens and not re.sub(
            r"__MTP_PROTECTED_\d+__", "", protected_text
        ).strip():
            return {
                "translation": text,
                "source": "fully_protected",
                "valid": True,
                "validation_reason": None,
                "attempts": 0
            }

        previous_translation = None
        validation_error = None

        for attempt in range(
            self.retry_manager.max_attempts
        ):

            result = self.ai_translator.translate(
                protected_text,
                source_language,
                target_language,
                terminology=active_terminology,
                context=context,
                previous_translation=previous_translation,
                validation_error=validation_error
            )

            translation = result.get("translation")
            restored_translation = restore_text(
                translation or "",
                protected_tokens
            )

            validation = validate_translation(
                text,
                restored_translation
            )

            quality = validate_translation_quality(
                text,
                restored_translation
            )

            if validation["valid"] and quality["valid"]:

                return {
                    "translation": restored_translation,
                    "source": result["source"],
                    "valid": True,
                    "validation_reason": None,
                    "attempts": attempt + 1
                }

            previous_translation = translation

            validation_error = (
                validation["reason"]
                if not validation["valid"]
                else quality["reason"]
            )

        return {
            "translation": None,
            "source": "ai_failed",
            "valid": False,
            "validation_reason": validation_error,
            "attempts": self.retry_manager.max_attempts
        }
