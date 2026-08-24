from translation.translation_service import TranslationService


class CaptureAITranslator:
    def __init__(self):
        self.terminology = None
        self.context = None

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
        self.terminology = terminology
        self.context = context
        return {
            "translation": "Texto traducido",
            "source": "capture_test"
        }


def main():
    translator = CaptureAITranslator()
    service = TranslationService(
        "en_es",
        ai_translator=translator
    )

    result = service.translate(
        "A new machine",
        context="quest.description"
    )

    assert result["valid"] is True
    assert translator.terminology["Machine"] == "Máquina"
    assert translator.context == "quest.description"

    terminology_result = service.translate("Machine")
    assert terminology_result["translation"] == "Máquina"
    assert terminology_result["source"] == "terminology"
    assert terminology_result["attempts"] == 0

    print("Terminology and context OK")


if __name__ == "__main__":
    main()
