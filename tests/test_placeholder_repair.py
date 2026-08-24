import shutil
from pathlib import Path

from ai.ai_translator import AITranslator
from analyzer.translation_validator import attempt_placeholder_repair
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_repairtest"


def test_repair_function_directly():
    # Duplicated color code: the only safe case this repairs.
    repaired = attempt_placeholder_repair("&eKill&f: Zombie", "&e&eMatar&f: Zombi")
    assert repaired == "&eMatar&f: Zombi", repaired

    # A genuinely missing placeholder must NOT be guessed at.
    assert attempt_placeholder_repair("Press %s to open", "Presiona para abrir") is None

    # A hallucinated placeholder that was never in the original: not safe either.
    assert attempt_placeholder_repair("Hello", "Hola %s") is None


class DuplicatingAITranslator(AITranslator):
    """Simulates an AI that duplicates one color code on its first
    attempt, then would answer correctly (proving the repair avoided
    needing that second attempt at all)."""

    def __init__(self):
        self.calls = 0

    def translate(self, text, source_language, target_language, terminology=None,
                  context=None, previous_translation=None, validation_error=None):
        self.calls += 1
        # text here is the *protected* form, e.g. "__MTP_PROTECTED_0__Kill__MTP_PROTECTED_1__: Zombie"
        # Duplicate the first protected token to simulate the failure mode.
        if "__MTP_PROTECTED_0__" in text:
            text = text.replace("__MTP_PROTECTED_0__", "__MTP_PROTECTED_0____MTP_PROTECTED_0__", 1)
        return {"translation": f"Matar {text}", "source": "duplicating_mock"}


def main():
    test_repair_function_directly()

    memory_dir = Path("translation") / LANGUAGE_PAIR
    try:
        translator = DuplicatingAITranslator()
        service = TranslationService(LANGUAGE_PAIR, ai_translator=translator)

        result = service.translate(
            "&eKill: Zombie",
            source_language="en", target_language="es"
        )

        # Repaired on the FIRST attempt: no retry was needed.
        assert result["valid"] is True, result
        assert translator.calls == 1, translator.calls
        assert result["attempts"] == 1

        print("Placeholder repair OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
