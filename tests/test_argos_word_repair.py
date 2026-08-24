from ai.ai_translator import AITranslator
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_argosrepairtest"

# Single-word pairs a real cross-mod glossary would already have from
# other, already-translated mods.
ITEM_GLOSSARY = {
    "Iron": "Hierro",
    "Copper": "Cobre",
    "Ingot": "Lingote",
    "Ore": "Mineral",
}


class FakeArgosTranslator(AITranslator):
    """
    Mimics Argos's real weak spot: it translates part of a short phrase
    and silently leaves the rest untouched, still tagging the result as
    "argos_translate" like the real provider does.
    """

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


class FakeOtherTranslator(AITranslator):
    """Same partial-leftover output, but from a provider that isn't
    Argos — the leftover-word safety net must not apply to it."""

    def __init__(self, answers):
        self.answers = answers

    def translate(self, text, source_language, target_language,
                   terminology=None, context=None,
                   previous_translation=None, validation_error=None):
        return {"translation": self.answers[text], "source": "openai_single"}


def main():
    # 1. Argos left "Iron" untranslated; the glossary knows that single
    # word, so the repair step should quietly fix it before anything
    # gets flagged.
    service = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Iron Ingot": "Iron Lingote"
        }),
        mod_item_glossary=ITEM_GLOSSARY
    )

    result = service.translate(
        "Iron Ingot", source_language="en", target_language="es"
    )

    assert result["valid"] is True, result
    assert result["translation"] == "Hierro Lingote", result
    assert result["source"] == "argos_translate"

    # 2. Argos leaves a word the glossary has never seen. Repair can't
    # fix it, so it must come back invalid (-> Pending) instead of
    # shipping a half-English string, and without looping retries (Argos
    # would just return the exact same thing every time).
    service2 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Compressed Cobblestone": "Compressed Adoquín"
        }),
        mod_item_glossary=ITEM_GLOSSARY
    )

    result2 = service2.translate(
        "Compressed Cobblestone", source_language="en", target_language="es"
    )

    assert result2["valid"] is False, result2
    assert result2["validation_reason"] == "possible_untranslated_words", result2
    assert result2["attempts"] == 1, result2
    assert service2.ai_translator.calls == ["Compressed Cobblestone"], (
        "should not retry a deterministic Argos miss"
    )

    # 3. The same kind of leftover text from a non-Argos provider is left
    # alone entirely -- the safety net is specific to Argos's known
    # weakness, not a general-purpose check.
    service3 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeOtherTranslator({
            "Compressed Cobblestone": "Compressed Adoquín"
        }),
        mod_item_glossary=ITEM_GLOSSARY
    )

    result3 = service3.translate(
        "Compressed Cobblestone", source_language="en", target_language="es"
    )

    assert result3["valid"] is True, result3
    assert result3["translation"] == "Compressed Adoquín"

    # 4. A protected mod name left untouched on purpose must never be
    # mistaken for a leftover-word failure. protect_text() swaps the mod
    # name for a placeholder before the AI ever sees the text, so the
    # fake's answer works on that placeholder form, same as the real
    # provider would.
    service4 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "__MTP_PROTECTED_0__ Wrench": "Llave __MTP_PROTECTED_0__"
        }),
        mod_item_glossary=ITEM_GLOSSARY,
        protected_terms=["Mekanism"]
    )

    result4 = service4.translate(
        "Mekanism Wrench", source_language="en", target_language="es"
    )

    assert result4["valid"] is True, result4
    assert result4["translation"] == "Llave Mekanism"

    # 5. Same repair/flag behavior through the batch path (Argos has no
    # native batch call, so it goes through the base one-by-one fallback,
    # but the service must still apply the same checks per item).
    service5 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            "Iron Ingot": "Iron Lingote",
            "Compressed Cobblestone": "Compressed Adoquín"
        }),
        mod_item_glossary=ITEM_GLOSSARY
    )

    results5 = service5.translate_batch(
        [
            {"text": "Iron Ingot", "path": "a"},
            {"text": "Compressed Cobblestone", "path": "b"}
        ],
        source_language="en", target_language="es"
    )

    assert results5[0]["valid"] is True
    assert results5[0]["translation"] == "Hierro Lingote"
    assert results5[1]["valid"] is False
    assert results5[1]["validation_reason"] == "possible_untranslated_words"

    # 6. A word that was NEVER saved on its own -- only ever seen inside
    # multi-word phrases -- still gets repaired, because it can be
    # inferred from minimal pairs already sitting in the glossary
    # ("Iron Ingot"/"Copper Ingot" reveal "Ingot" -> "Lingote", and
    # "Iron Ingot"/"Iron Ore" reveal "Iron" -> "Hierro"/"Ore" ->
    # "Mineral", all without a single standalone word entry anywhere).
    inferable_glossary = {
        "Iron Ingot": "Lingote de Hierro",
        "Copper Ingot": "Lingote de Cobre",
        "Iron Ore": "Mineral de Hierro",
    }

    service6 = TranslationService(
        LANGUAGE_PAIR,
        ai_translator=FakeArgosTranslator({
            # Argos hispanicized the made-up mod prefix but left the
            # real English word "Ingot" untouched.
            "Netherite Ingot": "Netherita Ingot"
        }),
        mod_item_glossary=inferable_glossary
    )

    result6 = service6.translate(
        "Netherite Ingot", source_language="en", target_language="es"
    )

    assert result6["valid"] is True, result6
    assert result6["translation"] == "Netherita Lingote", result6

    print("Argos word repair OK")


if __name__ == "__main__":
    main()
