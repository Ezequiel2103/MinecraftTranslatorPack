from ai.ai_translator import AITranslator
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_fallbacktest"


class FakeArgosTranslator(AITranslator):
    """Mimics Argos leaving a word untranslated, same as the real
    provider's known weak spot on short item names."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def translate(self, text, source_language, target_language,
                   terminology=None, context=None,
                   previous_translation=None, validation_error=None):
        self.calls.append(text)
        return {"translation": self.answers[text], "source": "argos_translate"}

    def translate_batch(self, texts_by_id, source_language, target_language,
                         terminology=None, context=None):
        return {
            item_id: self.translate(text, source_language, target_language)
            for item_id, text in texts_by_id.items()
        }


class FakeGoodTranslator(AITranslator):
    """A stronger engine that gets it right the first time."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def translate(self, text, source_language, target_language,
                   terminology=None, context=None,
                   previous_translation=None, validation_error=None):
        self.calls.append(text)
        return {"translation": self.answers[text], "source": "fake_good"}


class FakeAlsoBadTranslator(AITranslator):
    """A fallback that can't do any better either."""

    def translate(self, text, source_language, target_language,
                   terminology=None, context=None,
                   previous_translation=None, validation_error=None):
        return {"translation": text, "source": "fake_bad"}


class AlwaysFailsTranslator(AITranslator):
    """A primary engine whose output never validates, for any reason
    (not just Argos's leftover-words case) -- e.g. a placeholder
    mismatch it can never seem to fix."""

    def translate(self, text, source_language, target_language,
                   terminology=None, context=None,
                   previous_translation=None, validation_error=None):
        return {"translation": "sin marcador", "source": "fake_primary"}


def main():
    # 1. Argos leaves a word untranslated; a configured fallback gets a
    # shot at that specific text and succeeds -- the result should come
    # back valid, from the fallback, with no Pending detour.
    service = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Dye Depot Amber Dye": "Depósito Amber Dye"
        }),
        fallback_ai_translator=FakeGoodTranslator({
            "Dye Depot Amber Dye": "Depósito de Tinte Ámbar"
        })
    )

    result = service.translate(
        "Dye Depot Amber Dye", source_language="en", target_language="es"
    )

    assert result["valid"] is True, result
    assert result["translation"] == "Depósito de Tinte Ámbar", result
    assert result["source"] == "fake_good"

    # 2. No fallback configured -- behaves exactly as before (goes to
    # Pending), proving the feature is opt-in and doesn't change the
    # default path.
    service2 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Dye Depot Amber Dye": "Depósito Amber Dye"
        })
    )

    result2 = service2.translate(
        "Dye Depot Amber Dye", source_language="en", target_language="es"
    )

    assert result2["valid"] is False, result2
    assert result2["validation_reason"] == "possible_untranslated_words"

    # 3. A fallback that can't solve it either -- still ends up in
    # Pending, not silently wrong.
    service3 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Dye Depot Amber Dye": "Depósito Amber Dye"
        }),
        fallback_ai_translator=FakeAlsoBadTranslator()
    )

    result3 = service3.translate(
        "Dye Depot Amber Dye", source_language="en", target_language="es"
    )

    assert result3["valid"] is False, result3
    assert result3["validation_reason"] == "possible_untranslated_words"

    # 4. The fallback also kicks in for a plain retry-loop exhaustion
    # (not just Argos's specific leftover-words case) -- any primary
    # engine that never validates should still get a second opinion.
    service4 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=AlwaysFailsTranslator(),
        fallback_ai_translator=FakeGoodTranslator({
            # protect_text() swaps %s for this token before either
            # translator method ever sees the text.
            "Craft __MTP_PROTECTED_0__ now": "Fabrica __MTP_PROTECTED_0__ ahora"
        })
    )

    result4 = service4.translate(
        "Craft %s now", source_language="en", target_language="es"
    )

    assert result4["valid"] is True, result4
    assert result4["translation"] == "Fabrica %s ahora"
    assert result4["source"] == "fake_good"

    print("Fallback engine OK")


if __name__ == "__main__":
    main()
